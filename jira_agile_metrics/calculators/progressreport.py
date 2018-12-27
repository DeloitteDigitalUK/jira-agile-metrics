import io
import logging
import random
import math
import base64
import datetime
import dateutil

import numpy as np
import pandas as pd
import scipy.stats
import statsmodels.formula.api as sm
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import jinja2

from ..calculator import Calculator
from ..utils import set_chart_style

from .cycletime import calculate_cycle_times
from .throughput import calculate_throughput
from .forecast import throughput_sampler
from .cfd import calculate_cfd_data
from .scatterplot import calculate_scatterplot_data

logger = logging.getLogger(__name__)

jinja_env = jinja2.Environment(
    loader=jinja2.PackageLoader('jira_agile_metrics', 'calculators'),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

class ProgressReportCalculator(Calculator):
    """Output a progress report based on Monte Carlo forecast to completion
    """

    def run(self, now=None, trials=1000):
        if 'progress_report' not in self.settings:
            return

        # Prepare and validate configuration options
        
        cycle = self.settings['cycle']
        cycle_names = [s['name'] for s in cycle]
        quantiles = self.settings['quantiles']

        backlog_column = self.settings['backlog_column']
        if backlog_column not in cycle_names:
            logger.error("Backlog column %s does not exist", backlog_column)
            return None

        done_column = self.settings['done_column']
        if done_column not in cycle_names:
            logger.error("Done column %s does not exist", done_column)
            return None
        
        epic_query_template = self.settings['progress_report_epic_query_template']
        if not epic_query_template:
            if (
                len(self.settings['progress_report_outcomes']) == 0 or
                any(map(lambda o: o['epic_query'] is None, self.settings['progress_report_outcomes']))
            ):
                logger.error("`Progress report epic query template` is required unless all outcomes have `Epic query` set.")
                return None

        story_query_template = self.settings['progress_report_story_query_template']
        if not story_query_template:
            logger.error("`Progress report story query template` is required")
            return
        
        # if not set, we only show forecast completion date, no RAG/deadline
        epic_deadline_field = self.settings['progress_report_epic_deadline_field']
        if epic_deadline_field:
            epic_deadline_field = self.query_manager.field_name_to_id(epic_deadline_field)

        epic_min_stories_field = self.settings['progress_report_epic_min_stories_field']
        if epic_min_stories_field:
            epic_min_stories_field = self.query_manager.field_name_to_id(epic_min_stories_field)

        epic_max_stories_field = self.settings['progress_report_epic_max_stories_field']
        if not epic_max_stories_field:
            epic_max_stories_field = epic_min_stories_field
        else:
            epic_max_stories_field = self.query_manager.field_name_to_id(epic_max_stories_field)

        epic_team_field = self.settings['progress_report_epic_team_field']
        if epic_team_field:
            epic_team_field = self.query_manager.field_name_to_id(epic_team_field)

        teams = self.settings['progress_report_teams']

        if not teams:
            logger.error("At least one team must be set up under `Progress report teams`.")
            return None

        for team in teams:
            if not team['name']:
                logger.error("Teams must have a name.")
                return None
            if not team['wip'] or team['wip'] < 1:
                logger.error("Team WIP must be >= 1")
                return None
            if team['min_throughput'] or team['max_throughput']:
                if not (team['min_throughput'] and team['max_throughput']):
                    logger.error("If one of `Min throughput` or `Max throughput` is specified, both must be specified.")
                    return None
                if team['min_throughput'] > team['max_throughput']:
                    logger.error("`Min throughput` must be less than or equal to `Max throughput`.")
                    return None
            elif not team['throughput_samples']:
                logger.error("`Throughput samples` is required if `Min/max throughput` is not specified.")
                return None
            
        # if there is only one team and we don't record an epic's team, always use data for that one team
        if not epic_team_field and len(teams) != 1:
            logger.error("`Progress report epic team field` is required if there is more than one team under `Progress report teams`.")
            return None

        # if not set, we use a single epic query and don't group by outcomes
        
        outcomes = [
            Outcome(
                name=o['name'],
                key=o['key'] if o['key'] else o['name'],
                epic_query=(
                    o['epic_query'] if o['epic_query']
                    else epic_query_template.format(outcome='"%s"' % (o['key'] if o['key'] else o['name']))
                )
            ) for o in self.settings['progress_report_outcomes']
        ]
        
        if len(outcomes) > 0:
            for outcome in outcomes:
                if not outcome.name:
                    logger.error("Outcomes must have a name.")
                    return None
        else:
            outcomes = [Outcome(name=None, key=None, epic_query=epic_query_template)]

        # Calculate a throughput sampler function for each team.

        teams = [
            Team(
                name=team['name'],
                wip=team['wip'],
                min_throughput=team['min_throughput'],
                max_throughput=team['max_throughput'],
                throughput_samples=team['throughput_samples'],
                throughput_samples_window=team['throughput_samples_window'],
            ) for team in teams
        ]

        for team in teams:
            update_team_sampler(
                team=team,
                query_manager=self.query_manager,
                cycle=cycle,
                backlog_column=backlog_column,
                done_column=done_column,
            )

        team_lookup = {team.name: team for team in teams}
        team_epics = {team.name: [] for team in teams}

        default_team = None

        # Degenerate case: single team and no epic team field
        if not epic_team_field:
            default_team = teams[0]

        # Calculate epic progress for each outcome
        #  - Run `epic_query_template` to find relevant epics
        #  - Run `story_query_template` to find stories, count by backlog, in progress, done
        
        for outcome in outcomes:
            for epic in find_epics(
                query_manager=self.query_manager,
                epic_min_stories_field=epic_min_stories_field,
                epic_max_stories_field=epic_max_stories_field,
                epic_team_field=epic_team_field,
                epic_deadline_field=epic_deadline_field,
                outcome=outcome
            ):
                if not epic_team_field:
                    epic.team = default_team
                else:
                    epic.team = team_lookup.get(epic.team_name, None)

                    if epic.team is None:
                        logger.warning("Cannot find team %s for epic %s. Ignoring epic." % (epic.team_name, epic.key,))
                        continue
                
                outcome.epics.append(epic)
                team_epics[epic.team.name].append(epic)
                
                epic.story_query = story_query_template.format(
                    epic='"%s"' % epic.key,
                    team='"%s"' % epic.team_name if epic.team_name else None,
                    outcome='"%s"' % outcome.key,
                )

                update_story_counts(
                    epic=epic,
                    query_manager=self.query_manager,
                    cycle=cycle,
                    backlog_column=backlog_column,
                    done_column=done_column
                )

        # Run Monte Carlo simulation to complete
        
        for team in teams:
            forecast_to_complete(team, team_epics[team.name], quantiles, trials=trials, now=now)

        return {
            'outcomes': outcomes,
            'teams': teams
        }
    
    def write(self):
        output_file = self.settings['progress_report']
        if not output_file:
            logger.debug("No output file specified for progress report")
            return

        data = self.get_result()
        if not data:
            logger.warning("No data found for progress report")
            return

        cycle_names = [s['name'] for s in self.settings['cycle']]
        backlog_column = self.settings['backlog_column']
        quantiles = self.settings['quantiles']

        template = jinja_env.get_template('progressreport_template.html')
        today = datetime.date.today()

        with open(output_file, 'w') as of:
            of.write(template.render(
                jira_url=self.query_manager.jira._options['server'],
                title=self.settings['progress_report_title'],
                story_query_template=self.settings['progress_report_story_query_template'],
                epic_deadline_field=self.settings['progress_report_epic_deadline_field'],
                epic_min_stories_field=self.settings['progress_report_epic_min_stories_field'],
                epic_max_stories_field=self.settings['progress_report_epic_max_stories_field'],
                epic_team_field=self.settings['progress_report_epic_team_field'],
                outcomes=data['outcomes'],
                teams=data['teams'],
                enumerate=enumerate,
                future_date=lambda weeks: forward_weeks(today, weeks),
                color_code=lambda q: (
                    'primary' if q is None else
                    'danger' if q <= 0.7 else
                    'warning' if q <= 0.9 else
                    'success'
                ),
                percent_complete=lambda epic: (
                    int(round(((epic.stories_done or 0) / epic.max_stories) * 100))
                ),
                team_charts={team.name: {
                    'cfd': plot_cfd(team.throughput_samples_cycle_times, cycle_names, backlog_column),
                    'throughput': plot_throughput(team.throughput_samples_cycle_times),
                    'scatterplot': plot_scatterplot(team.throughput_samples_cycle_times, quantiles)
                } for team in data['teams']},
                epic_charts={epic.key: {
                    'cfd': plot_cfd(epic.story_cycle_times, cycle_names, backlog_column),
                    'scatterplot': plot_scatterplot(epic.story_cycle_times, quantiles)
                } for outcome in data['outcomes'] for epic in outcome.epics}
            ))

class Outcome(object):

    def __init__(self, name, key, epic_query=None, epics=None):
        self.name = name
        self.key = key
        self.epic_query = epic_query
        self.epics = epics if epics is not None else []

class Team(object):

    def __init__(self, name, wip,
        min_throughput=None,
        max_throughput=None,
        throughput_samples=None,
        throughput_samples_window=None,
        throughput_samples_cycle_times=None,
        sampler=None
    ):
        self.name = name
        self.wip = wip

        self.min_throughput = min_throughput
        self.max_throughput = max_throughput
        self.throughput_samples = throughput_samples
        self.throughput_samples_window = throughput_samples_window
        self.throughput_samples_cycle_times = throughput_samples_cycle_times
        
        self.sampler = sampler

class Epic(object):

    def __init__(self, key, summary, status, resolution, resolution_date,
        min_stories, max_stories, team_name, deadline,
        story_query=None,
        story_cycle_times=None,
        stories_raised=None,
        stories_in_backlog=None,
        stories_in_progress=None,
        stories_done=None,
        first_story_started=None,
        last_story_finished=None,
        team=None,
        outcome=None,
        forecast=None
    ):
        self.key = key
        self.summary = summary
        self.status = status
        self.resolution = resolution
        self.resolution_date = resolution_date
        self.min_stories = min_stories
        self.max_stories = max_stories
        self.team_name = team_name
        self.deadline = deadline

        self.story_query = story_query
        self.story_cycle_times = story_cycle_times
        self.stories_raised = stories_raised
        self.stories_in_backlog = stories_in_backlog
        self.stories_in_progress = stories_in_progress
        self.stories_done = stories_done
        self.first_story_started = first_story_started
        self.last_story_finished = last_story_finished
        
        self.team = team
        self.outcome = outcome
        self.forecast = forecast

class Forecast(object):

    def __init__(self, quantiles, deadline_quantile=None):
        self.quantiles = quantiles  # pairs of (quantile, weeks)
        self.deadline_quantile = deadline_quantile

def throughput_range_sampler(min, max):
    def get_throughput_range_sample():
        return random.randint(min, max)
    return get_throughput_range_sample

def update_team_sampler(
    team,
    query_manager,
    cycle,
    backlog_column,
    done_column,
    frequency='1W'
):

    # Use query if set
    if team.throughput_samples:

        throughput = calculate_team_throughput(
            team=team,
            query_manager=query_manager,
            cycle=cycle,
            backlog_column=backlog_column,
            done_column=done_column,
            frequency=frequency,
        )

        if throughput is None:
            logger.error("No completed issues found by query `%s`. Unable to calculate throughput. Will use min/max throughput if set." % team.throughput_samples)
        else:
            team.sampler = throughput_sampler(throughput, 0, 10)  # we have to hardcode the buffer size
    
    # Use min/max if set and query either wasn't set, or returned nothing
    if team.sampler is None and team.min_throughput and team.max_throughput:
        team.sampler = throughput_range_sampler(team.min_throughput, max(team.min_throughput, team.max_throughput))
    
    if team.sampler is None:
        logger.error("Unable to calculate throughput for team %s." % team.name)

def calculate_team_throughput(
    team,
    query_manager,
    cycle,
    backlog_column,
    done_column,
    frequency
):

    cycle_times = calculate_cycle_times(
        query_manager=query_manager,
        cycle=cycle,
        attributes={},
        backlog_column=backlog_column,
        done_column=done_column,
        queries=[{'jql': team.throughput_samples, 'value': None}],
        query_attribute=None,
    )

    team.throughput_samples_cycle_times = cycle_times

    if cycle_times['completed_timestamp'].count() == 0:
        return None
    
    return calculate_throughput(cycle_times, frequency=frequency, window=team.throughput_samples_window)


def find_epics(
    query_manager,
    epic_min_stories_field,
    epic_max_stories_field,
    epic_team_field,
    epic_deadline_field,
    outcome
):

    for issue in query_manager.find_issues(outcome.epic_query):

        deadline = None
        if epic_deadline_field is not None:
            deadline = query_manager.resolve_field_value(issue, epic_deadline_field)
            if isinstance(deadline, (str, bytes)):
                deadline = dateutil.parser.parse(deadline)

        yield Epic(
            key=issue.key,
            summary=issue.fields.summary,
            status=issue.fields.status.name,
            resolution=issue.fields.resolution.name if issue.fields.resolution else None,
            resolution_date=dateutil.parser.parse(issue.fields.resolutiondate) if issue.fields.resolutiondate else None,
            min_stories=query_manager.resolve_field_value(issue, epic_min_stories_field) if epic_min_stories_field else None,
            max_stories=query_manager.resolve_field_value(issue, epic_max_stories_field) if epic_max_stories_field else None,
            team_name=query_manager.resolve_field_value(issue, epic_team_field) if epic_team_field else None,
            deadline=deadline,
            outcome=outcome,
        )

def update_story_counts(
    epic,
    query_manager,
    cycle,
    backlog_column,
    done_column
):
    backlog_column_index = [s['name'] for s in cycle].index(backlog_column)
    started_column = cycle[backlog_column_index + 1]['name']  # config parser ensures there is at least one column after backlog
    
    story_cycle_times = calculate_cycle_times(
        query_manager=query_manager,
        cycle=cycle,
        attributes={},
        backlog_column=backlog_column,
        done_column=done_column,
        queries=[{'jql': epic.story_query, 'value': None}],
        query_attribute=None,
    )

    epic.story_cycle_times = story_cycle_times
    epic.stories_raised = len(story_cycle_times)

    if epic.stories_raised == 0:
        epic.stories_in_backlog = 0
        epic.stories_in_progress = 0
        epic.stories_done = 0
    else:
        epic.stories_done = story_cycle_times[done_column].count()
        epic.stories_in_progress = story_cycle_times[started_column].count() - epic.stories_done
        epic.stories_in_backlog = story_cycle_times[backlog_column].count() - (epic.stories_in_progress + epic.stories_done)

        epic.first_story_started = story_cycle_times[started_column].min().date() if epic.stories_in_progress > 0 else None
        epic.last_story_finished = story_cycle_times[done_column].max().date() if epic.stories_done > 0 else None
    
    # if the actual number of stories exceeds min and/or max, adjust accordingly

    if not epic.min_stories or epic.min_stories < epic.stories_raised:
        epic.min_stories = epic.stories_raised
    
    if not epic.max_stories or epic.max_stories < epic.stories_raised:
        epic.max_stories = max(epic.min_stories, epic.stories_raised, 1)

def forecast_to_complete(team, epics, quantiles, trials=1000, max_iterations=9999, now=None):
    
    # Allows unit testing to use a fixed date
    if now is None:
        now = datetime.datetime.utcnow()

    epic_trials = {e.key: pd.Series([np.nan] * trials) for e in epics}

    if team.sampler is None:
        logger.error("Team %s has no sampler. Unable to forecast." % team.name)
        return

    # apply WIP limit to list of epics not yet completed
    def filter_active_epics(trial_values):
        return [t for t in trial_values if t['value'] < t['target']][:team.wip]

    for trial in range(trials):

        # track progress of each epic - target value is randomised
        trial_values = [{
            'epic': e,
            'value': e.stories_done,
            'target': calculate_epic_target(e),
            'weeks': 0
        } for e in epics]

        active_epics = filter_active_epics(trial_values)
        steps = 0

        while len(active_epics) > 0 and steps <= max_iterations:
            steps += 1

            # increment all epics that are not finished
            for ev in trial_values:
                if ev['value'] < ev['target']:
                    ev['weeks'] += 1

            # draw a sample (throughput over a week) for the team and distribute
            # it over the active epics
            sample = team.sampler()
            per_active_epic = int(sample / len(active_epics))
            remainder = sample % len(active_epics)

            for ev in active_epics:
                ev['value'] += per_active_epic
            
            # reset in case some have finished
            active_epics = filter_active_epics(trial_values)

            # apply remainder to a randomly picked epic if sample didn't evenly divide
            if len(active_epics) > 0 and remainder > 0:
                lucky_epic = random.randint(0, len(active_epics) - 1)
                active_epics[lucky_epic]['value'] += remainder

                # reset in case some have finished
                active_epics = filter_active_epics(trial_values)
        
        if steps == max_iterations:
            logger.warning("Trial %d did not complete after %d weeks, aborted." % (trial, max_iterations,))

        # record this trial
        for ev in trial_values:
            epic_trials[ev['epic'].key].iat[trial] = ev['weeks']

    for epic in epics:
        trials = epic_trials[epic.key].dropna()
        
        deadline_quantile = None
        if epic.deadline:
            # how many weeks are there from today until the deadline...
            weeks_to_deadline = math.ceil((epic.deadline.date() - now.date()).days / 7)

            # ...and what trial quantile does that correspond to (higher = more confident)
            deadline_quantile = scipy.stats.percentileofscore(trials, weeks_to_deadline) / 100

        epic.forecast = Forecast(
            quantiles=list(zip(quantiles, trials.quantile(quantiles))),
            deadline_quantile=deadline_quantile
        )

def calculate_epic_target(epic):
    return random.randint(
        max(epic.min_stories, 0),
        max(epic.min_stories, epic.max_stories, 1)
    )

def forward_weeks(date, weeks):
    return (date - datetime.timedelta(days=date.weekday())) + datetime.timedelta(weeks=weeks)

def plot_cfd(cycle_data, cycle_names, backlog_column):

    # Prepare data
    
    if cycle_data is None or len(cycle_data) == 0:
        return None
    
    cfd_data = calculate_cfd_data(cycle_data, cycle_names)
    cfd_data = cfd_data.drop([backlog_column], axis=1)

    backlog_column_index = cycle_names.index(backlog_column)
    started_column = cycle_names[backlog_column_index + 1]  # config parser ensures there is at least one column after backlog

    if cfd_data[started_column].max() <= 0:
        return None
    
    # Plot
    
    fig, ax = plt.subplots()
    fig.autofmt_xdate()

    ax.set_xlabel("Date")
    ax.set_ylabel("Number of items")

    cfd_data.plot.area(ax=ax, stacked=False, legend=False)

    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    bottom = cfd_data[cfd_data.columns[-1]].min()
    top = cfd_data[cfd_data.columns[0]].max()
    ax.set_ylim(bottom=bottom, top=top)

    set_chart_style()

    # Return as base64 encoded string

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)

    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def plot_throughput(cycle_data, frequency='1W'):

    # Prepare data

    if cycle_data is None or len(cycle_data) == 0:
        return None

    throughput_data = calculate_throughput(cycle_data, frequency)
    
    # Calculate regression

    day_zero = throughput_data.index[0]
    throughput_data['day'] = (throughput_data.index - day_zero).days

    fit = sm.ols(formula="count ~ day", data=throughput_data).fit()
    throughput_data['fitted'] = fit.predict(throughput_data)

    # Plot

    fig, ax = plt.subplots()

    ax.set_xlabel("Period starting")
    ax.set_ylabel("Number of items")

    ax.plot(throughput_data.index, throughput_data['count'], marker='o')
    plt.xticks(throughput_data.index, [d.date().strftime('%d/%m/%Y') for d in throughput_data.index], rotation=70, size='small')

    _, top = ax.get_ylim()
    ax.set_ylim(0, top + 1)

    for x, y in zip(throughput_data.index, throughput_data['count']):
        if y == 0:
            continue
        ax.annotate(
            "%.0f" % y,
            xy=(x.toordinal(), y + 0.2),
            ha='center',
            va='bottom',
            fontsize="x-small",
        )

    ax.plot(throughput_data.index, throughput_data['fitted'], '--', linewidth=2)

    set_chart_style()

    # Return as base64 encoded string

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)

    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def plot_scatterplot(cycle_data, quantiles):

    # Prepare data
    
    if cycle_data is None or len(cycle_data) == 0:
        return None
    
    scatterplot_data = calculate_scatterplot_data(cycle_data)

    if len(scatterplot_data) < 2:
        return None
    
    # Plot

    chart_data = pd.DataFrame({
        'completed_date': scatterplot_data['completed_date'].values.astype('datetime64[D]'),
        'cycle_time': scatterplot_data['cycle_time']
    }, index=scatterplot_data.index)

    fig, ax = plt.subplots()
    fig.autofmt_xdate()

    ax.set_xlabel("Completed date")
    ax.set_ylabel("Cycle time (days)")

    ax.plot_date(x=chart_data['completed_date'], y=chart_data['cycle_time'], ms=5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))

    _, top = ax.get_ylim()
    ax.set_ylim(0, top + 1)

    # Add quantiles
    left, right = ax.get_xlim()
    for quantile, value in chart_data['cycle_time'].quantile(quantiles).iteritems():
        ax.hlines(value, left, right, linestyles='--', linewidths=1)
        ax.annotate("%.0f%% (%.0f days)" % ((quantile * 100), value,),
            xy=(left, value),
            xytext=(left, value),
            fontsize="x-small",
            ha="left"
        )

    set_chart_style()

    # Return as base64 encoded string

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)

    return base64.b64encode(buffer.getvalue()).decode('utf-8')
