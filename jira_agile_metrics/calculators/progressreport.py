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
import matplotlib.transforms

import jinja2

from ..calculator import Calculator
from ..utils import set_chart_style, to_days_since_epoch

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
        
        # TODO: Add output option to produce a per-outcome simple burnup chart.
        # Show total stories in backlog + flat "max" line + progress of stories
        # to date.

        if self.settings['progress_report'] is None:
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
                self.settings['progress_report_outcome_query'] is not None or
                self.settings['progress_report_outcomes'] is None or
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

        teams = self.settings['progress_report_teams'] or []

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
                if team['throughput_samples']:
                    logger.error("`Throughput samples` cannot be used if `Min/max throughput` is already specified.")
                
                # Note: If neither min/max throughput or samples are specified, we turn off forecasting

        # If we aren't recording teams against epics, there can be either no teams
        # at all, or a single, default team, but not multiple.
        if not epic_team_field and len(teams) > 1:
            logger.error("`Progress report epic team field` is required if there is more than one team under `Progress report teams`.")
            return None

        # Find outcomes, either in the config file or by querying JIRA (or both).
        # If none set, we use a single epic query and don't group by outcomes

        outcomes = [
            Outcome(
                name=o['name'],
                key=o['key'] if o['key'] else o['name'],
                deadline=datetime.datetime.combine(o['deadline'], datetime.datetime.min.time()) if o['deadline'] else None,
                epic_query=(
                    o['epic_query'] if o['epic_query']
                    else epic_query_template.format(outcome='"%s"' % (o['key'] if o['key'] else o['name']))
                )
            ) for o in self.settings['progress_report_outcomes']
        ]

        outcome_query = self.settings['progress_report_outcome_query']
        if outcome_query:
            outcome_deadline_field = self.settings['progress_report_outcome_deadline_field']
            if outcome_deadline_field:
                outcome_deadline_field = self.query_manager.field_name_to_id(outcome_deadline_field)

            outcomes.extend(find_outcomes(self.query_manager, outcome_query, outcome_deadline_field, epic_query_template))
        
        if len(outcomes) > 0:
            if not all([bool(outcome.name) for outcome in outcomes]):
                logger.error("Outcomes must have a name.")
                return None
        else:
            outcomes = [Outcome(name=None, key=None, epic_query=epic_query_template)]

        # Calculate a throughput sampler function for each team.

        # It is possible for there to be zero teams, in which case we will
        # create teams on-the-fly from the `epic_team_field`.

        teams = [
            Team(
                name=team['name'],
                wip=team['wip'],
                min_throughput=team['min_throughput'],
                max_throughput=team['max_throughput'],
                throughput_samples=team['throughput_samples'].format(
                    team='"%s"' % team['name'],
                ) if team['throughput_samples'] else None,
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

        team_lookup = {team.name.lower(): team for team in teams}
        team_epics = {team.name.lower(): [] for team in teams}

        # Degenerate case: single team and no epic team field - all forecasts
        # use this team
        default_team = teams[0] if not epic_team_field and len(teams) == 1 else None

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
                    epic.team = default_team  # single defined team, or None
                else:
                    epic.team = team_lookup.get(epic.team_name.lower(), None)

                    if epic.team is None:
                        logger.info("Cannot find team %s for epic %s. Dynamically adding a non-forecasted team." % (epic.team_name, epic.key,))
                        epic.team = Team(name=epic.team_name)
                        teams.append(epic.team)
                        team_lookup[epic.team.name.lower()] = epic.team
                        team_epics[epic.team.name.lower()] = []
                
                outcome.epics.append(epic)

                if epic.team is not None:
                    team_epics[epic.team.name.lower()].append(epic)
                
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
            if team.sampler is not None:
                forecast_to_complete(team, team_epics[team.name.lower()], quantiles, trials=trials, now=now)

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

        epics_by_team = {}
        have_outcomes = False
        have_forecasts = False
        for outcome in data['outcomes']:
            if outcome.name is not None:
                have_outcomes = True

            for epic in outcome.epics:
                if epic.forecast is not None:
                    have_forecasts = True
                if epic.team is not None:
                    if epic.team.name not in epics_by_team:
                        epics_by_team[epic.team.name] = []
                    epics_by_team[epic.team.name].append(epic)

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
                num_teams=len(data['teams']),
                have_teams=len(data['teams']) > 1,
                have_outcomes=have_outcomes,
                have_forecasts=have_forecasts,
                epics_by_team=epics_by_team,
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
                outcome_charts={outcome.key: {
                    'cfd': plot_cfd(
                        cycle_data=pd.concat([e.story_cycle_times for e in outcome.epics]),
                        cycle_names=cycle_names,
                        backlog_column=backlog_column,
                        target=sum([e.max_stories or 0 for e in outcome.epics]),
                        deadline=outcome.deadline
                    ) if len(outcome.epics) > 0 else None,
                } for outcome in data['outcomes']},
                team_charts={team.name: {
                    'cfd': plot_cfd(team.throughput_samples_cycle_times, cycle_names, backlog_column),
                    'throughput': plot_throughput(team.throughput_samples_cycle_times),
                    'scatterplot': plot_scatterplot(team.throughput_samples_cycle_times, quantiles)
                } for team in data['teams']},
                epic_charts={epic.key: {
                    'cfd': plot_cfd(epic.story_cycle_times, cycle_names, backlog_column, target=epic.max_stories, deadline=epic.deadline),
                    'scatterplot': plot_scatterplot(epic.story_cycle_times, quantiles)
                } for outcome in data['outcomes'] for epic in outcome.epics}
            ))

class Outcome(object):

    def __init__(self, name, key, deadline=None, epic_query=None, epics=None):
        self.name = name
        self.key = key
        self.epic_query = epic_query
        self.deadline = deadline
        self.epics = epics if epics is not None else []

class Team(object):

    def __init__(self, name,
        wip=1,
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

def find_outcomes(
    query_manager,
    query,
    outcome_deadline_field,
    epic_query_template
):
    for issue in query_manager.find_issues(query):
        yield Outcome(
            name=issue.fields.summary,
            key=issue.key,
            deadline=date_value(query_manager, issue, outcome_deadline_field),
            epic_query=epic_query_template.format(outcome='"%s"' % issue.key),
        )

def find_epics(
    query_manager,
    epic_min_stories_field,
    epic_max_stories_field,
    epic_team_field,
    epic_deadline_field,
    outcome
):

    for issue in query_manager.find_issues(outcome.epic_query):
        yield Epic(
            key=issue.key,
            summary=issue.fields.summary,
            status=issue.fields.status.name,
            resolution=issue.fields.resolution.name if issue.fields.resolution else None,
            resolution_date=dateutil.parser.parse(issue.fields.resolutiondate) if issue.fields.resolutiondate else None,
            min_stories=int_or_none(query_manager.resolve_field_value(issue, epic_min_stories_field)) if epic_min_stories_field else None,
            max_stories=int_or_none(query_manager.resolve_field_value(issue, epic_max_stories_field)) if epic_max_stories_field else None,
            team_name=query_manager.resolve_field_value(issue, epic_team_field) if epic_team_field else None,
            deadline=date_value(query_manager, issue, epic_deadline_field, default=outcome.deadline),
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

        if any(trials):  # if all trials resulted in zero weeks, don't record a forecast
            deadline_quantile = None
            if epic.deadline:
                # how many weeks are there from today until the deadline...
                weeks_to_deadline = math.ceil((epic.deadline.date() - now.date()).days / 7)

                # ...and what trial quantile does that correspond to (higher = more confident)
                deadline_quantile = scipy.stats.percentileofscore(trials, weeks_to_deadline, kind='weak') / 100

            epic.forecast = Forecast(
                quantiles=list(zip(quantiles, trials.quantile(quantiles))),
                deadline_quantile=deadline_quantile
            )
        else:
            epic.forecast = None

def calculate_epic_target(epic):
    return random.randint(
        max(epic.min_stories, 0),
        max(epic.min_stories, epic.max_stories, 1)
    )

def forward_weeks(date, weeks):
    return (date - datetime.timedelta(days=date.weekday())) + datetime.timedelta(weeks=weeks)

def plot_cfd(cycle_data, cycle_names, backlog_column, target=None, deadline=None):

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

    transform_horizontal = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)

    ax.set_xlabel(None)
    ax.set_ylabel("Number of items")

    cfd_data.plot.area(ax=ax, stacked=False, legend=False)

    # Deadline

    if deadline is not None:
        bottom, top = ax.get_ylim()
        left, right = ax.get_xlim()

        deadline_dse = to_days_since_epoch(deadline.date())

        ax.vlines(deadline, bottom, target, color='r', linestyles='-', linewidths=0.5)
        ax.annotate("Due: %s" % (deadline.strftime("%d/%m/%Y"),),
            xy=(deadline, target),
            xytext=(0, 10),
            textcoords='offset points',
            fontsize="x-small",
            ha="right",
            color='black',
            backgroundcolor="#ffffff"
        )

        # Make sure we can see deadline line
        if right < deadline_dse:
            ax.set_xlim(left, deadline_dse + 1)

    # Target line

    if target is not None:
        left, right = ax.get_xlim()
        ax.hlines(target, left, right, linestyles='--', linewidths=1)
        ax.annotate("Target: %d" % (target,),
            xy=(0.02, target),
            xycoords=transform_horizontal,
            fontsize="x-small",
            ha="left",
            va="center",
            backgroundcolor="#ffffff"
        )

    # Legend

    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    # Spacing

    bottom = cfd_data[cfd_data.columns[-1]].min()
    top = max(cfd_data[cfd_data.columns[0]].max(), 0 if target is None else target)
    ax.set_ylim(bottom=bottom, top=top + (0 if target is None else 5))

    set_chart_style()

    # Return as base64 encoded string

    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=220)
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
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=220)
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
    fig.savefig(buffer, format='png', bbox_inches='tight', dpi=220)
    plt.close(fig)

    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def int_or_none(value):
    return value if isinstance(value, int) else \
           int(value) if isinstance(value, (str, bytes)) and value.isdigit() \
           else None

def date_value(query_manager, issue, field_name, default=None):
    value = default
    if field_name is not None:
        value = query_manager.resolve_field_value(issue, field_name)
        if isinstance(value, (str, bytes)) and value != "":
            value = dateutil.parser.parse(value)
        elif value is None:
            value = default
    return value
