import json
import logging
import datetime
import dateutil
import pandas as pd
from enum import Enum

from ..calculator import Calculator
from ..utils import get_extension, to_json_string, StatusTypes, Timespans

logger = logging.getLogger(__name__)


class BackwardsTransitionHandling(Enum):
    """How to handle backwards movement in the state graph."""

    #: When an issue re-enters a state, the previous
    #: calculated time is cleared
    reset = "reset"

    #: When an issue re-enters a state, the new
    #: time spent on the
    accumulate = "accumulate"


class CycleTimeCalculator(Calculator):
    """Basic cycle time data, fetched from JIRA.

    Builds a numerically indexed data frame with the following 'fixed'
    columns: `key`, 'url', 'issue_type', `summary`, `status`, and
    `resolution` from JIRA, as well as the value of any fields set in
    the `fields` dict in `settings`. If `known_values` is set (a dict of
    lists, with field names as keys and a list of known values for each
    field as values) and a field in `fields` contains a list of values,
    only the first value in the list of known values will be used.

    If 'query_attribute' is set in `settings`, a column with this name
    will be added, and populated with the `value` key, if any, from each
    criteria block under `queries` in settings.

    In addition, `cycle_time` will be set to the time delta between the
    first `accepted`-type column and the first `complete` column, or None.

    The remaining columns are the names of the items in the configured
    cycle, in order.

    Each cell contains the last date/time stamp when the relevant status
    was set.

    If an item moves backwards through the cycle, subsequent date/time
    stamps in the cycle are erased.
    """

    def run(self, now=None):

        return calculate_cycle_times(
            self.query_manager,
            self.settings['cycle'],
            self.settings['attributes'],
            self.settings['committed_column'],
            self.settings['done_column'],
            self.settings['queries'],
            self.settings['query_attribute'],
            now=now,
            backwards_transitions=BackwardsTransitionHandling(self.settings['backwards_transitions']),
            )

    def write(self):
        output_files = self.settings['cycle_time_data']

        if not output_files:
            logger.debug("No output file specified for cycle time data")
            return

        cycle_data = self.get_result()

        cycle_names = [s['name'] for s in self.settings['cycle']]
        cycle_duration_labels = [s['name'] + " duration" for s in self.settings['cycle']]
        attribute_names = sorted(self.settings['attributes'].keys())
        query_attribute_names = [self.settings['query_attribute']] if self.settings['query_attribute'] else []

        header = ['ID', 'Link', 'Name'] + cycle_names + cycle_duration_labels + ['Type', 'Status', 'Resolution'] + attribute_names + query_attribute_names + ['Blocked Days']
        columns = ['key', 'url', 'summary'] + cycle_names + cycle_duration_labels + ['issue_type', 'status', 'resolution'] + attribute_names + query_attribute_names + ['blocked_days']

        def duration_as_days(val):
            """Convert pd.Timedelta to float days"""
            return val.total_seconds() / (24 * 3600)

        # Format durations as days as float
        for duration_col in cycle_duration_labels:
            cycle_data[duration_col] = cycle_data[duration_col].apply(duration_as_days)

        for output_file in output_files:

            logger.info("Writing cycle time data to %s", output_file)
            output_extension = get_extension(output_file)

            if output_extension == '.json':
                values = [header] + [list(map(to_json_string, row)) for row in cycle_data[columns].values.tolist()]
                with open(output_file, 'w') as out:
                    out.write(json.dumps(values))
            elif output_extension == '.xlsx':
                cycle_data.to_excel(output_file, 'Cycle data', columns=columns, header=header, index=False)
            else:
                cycle_data.to_csv(output_file, columns=columns, header=header, date_format='%Y-%m-%d', index=False)


def calculate_cycle_times(
    query_manager,
    cycle,                  # [{name:"", statuses:[""], type:""}]
    attributes,             # [{key:value}]
    committed_column,       # "" in `cycle`
    done_column,            # "" in `cycle`
    queries,                # [{jql:"", value:""}]
    query_attribute=None,   # ""
    now=None,
    backwards_transitions: BackwardsTransitionHandling = None,
):

    # Allows unit testing to use a fixed date
    if now is None:
        now = datetime.datetime.utcnow()

    # Default to reset cycle time on state transition loops
    if backwards_transitions is None:
        backwards_transitions = BackwardsTransitionHandling.reset

    cycle_names = [s['name'] for s in cycle]
    cycle_duration_names = [s['name'] + " duration" for s in cycle]  # For Pandas columns
    active_columns = cycle_names[cycle_names.index(committed_column):cycle_names.index(done_column)]

    cycle_lookup = {}
    for idx, cycle_step in enumerate(cycle):
        for status in cycle_step['statuses']:
            cycle_lookup[status.lower()] = dict(
                index=idx,
                name=cycle_step['name'],
            )

    unmapped_statuses = set()

    series = {
        'key': {'data': [], 'dtype': 'str'},
        'url': {'data': [], 'dtype': 'str'},
        'issue_type': {'data': [], 'dtype': 'str'},
        'summary': {'data': [], 'dtype': 'str'},
        'status': {'data': [], 'dtype': 'str'},
        'resolution': {'data': [], 'dtype': 'str'},
        'cycle_time': {'data': [], 'dtype': 'timedelta64[ns]'},
        'completed_timestamp': {'data': [], 'dtype': 'datetime64[ns]'},
        'blocked_days': {'data': [], 'dtype': 'int'},
        'estimation_days': {'data': [], 'dtype': 'float'},
        'impediments': {'data': [], 'dtype': 'object'},  # list of {'start', 'end', 'status', 'flag'}
    }

    for cycle_name in cycle_names:
        # In output Pandas data, describe how to map
        # datetime and timedelta to Pandas columns
        series[cycle_name] = {'data': [], 'dtype': 'datetime64[ns]'}
        series[f'{cycle_name} duration'] = {'data': [], 'dtype': 'timedelta64[ns]'}

    for name in attributes:
        series[name] = {'data': [], 'dtype': 'object'}

    if query_attribute:
        series[query_attribute] = {'data': [], 'dtype': 'str'}

    for criteria in queries:
        for issue in query_manager.find_issues(criteria['jql']):

            item = {
                'key': issue.key,
                'url': "%s/browse/%s" % (query_manager.jira._options['server'], issue.key,),
                'issue_type': issue.fields.issuetype.name,
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'resolution': issue.fields.resolution.name if issue.fields.resolution else None,
                # Note that a workign day is 8 hours, not 24 hours
                'estimation_days': issue.fields.timeoriginalestimate / (8 * 3600) if issue.fields.timeoriginalestimate else 0,
                'cycle_time': None,
                'completed_timestamp': None,
                'blocked_days': 0,
                'impediments': []
            }

            logger.debug("Issue %s estimation is %f days", issue.key, item["estimation_days"])

            for name in attributes:
                item[name] = query_manager.resolve_attribute_value(issue, name)

            if query_attribute:
                item[query_attribute] = criteria.get('value', None)

            for cycle_name in cycle_names:
                item[cycle_name] = None

            last_status = None # Name of the workflow state the last snapshot was in
            impediment_flag = None
            impediment_start_status = None
            impediment_start = None

            # Initialze mapping of cycle name -> Timespans
            # Each timespan tracks enters and exit dates of a cycle
            timespans = dict([(name, Timespans()) for name in cycle_names])

            # Record date of status and impediments flag changes
            for snapshot in query_manager.iter_changes(issue, ['status', 'Flagged']):

                if snapshot.change == 'status':
                    snapshot_cycle_step = cycle_lookup.get(snapshot.to_string.lower(), None)
                    if snapshot_cycle_step is None:
                        logger.info("Issue %s transitioned to unknown JIRA status %s", issue.key, snapshot.to_string)
                        unmapped_statuses.add(snapshot.to_string)
                        continue

                    logger.debug("Issue state transition %s: %s -> %s (%s) at %s", issue.key, last_status, snapshot_cycle_step["name"], snapshot.to_string, snapshot.date)

                    # Looks like JIRA lib dates can be both offset-naive and offset-aware
                    # so we just normalise here to offset-naive
                    # Issue state transition FB-4281: None -> Backlog (Product Backlog) at 2020-10-09 07:43:43.681000-05:00
                    # Issue state transition FB-4281: Backlog -> Backlog (Ready for Dev) at 2020-10-09 07:43:56.041000
                    timepoint = snapshot.date.replace(tzinfo=None)

                    # Exit from the previous timespan if there was one:
                    if last_status:
                        timespans[last_status].leave(timepoint)

                    last_status = snapshot_cycle_step_name = snapshot_cycle_step['name']

                    # Track enter of a new timespan for this cycle
                    timespans[snapshot_cycle_step_name].enter(timepoint)

                    # Wipe any subsequent dates, in case this was a move backwards
                    if backwards_transitions == BackwardsTransitionHandling.reset:
                        found_cycle_name = False
                        for cycle_name in cycle_names:
                            if not found_cycle_name and cycle_name == snapshot_cycle_step_name:
                                found_cycle_name = True
                                continue
                            elif found_cycle_name and item[cycle_name] is not None:
                                logger.info("Issue %s moved backwards to %s [JIRA: %s -> %s], wiping data for subsequent step %s", issue.key, snapshot_cycle_step_name, snapshot.from_string, snapshot.to_string, cycle_name)
                                timespans[cycle_name].reset()

                elif snapshot.change == 'Flagged':
                    if snapshot.from_string == snapshot.to_string is None:
                        # Initial state from None -> None
                        continue
                    elif snapshot.to_string is not None and snapshot.to_string != "":
                        impediment_flag = snapshot.to_string
                        impediment_start = snapshot.date.date()
                        impediment_start_status = last_status
                    elif snapshot.to_string is None or snapshot.to_string == "":
                        if impediment_start is None:
                            logger.warning("Issue %s had impediment flag cleared before being set. This should not happen.", issue.key)
                            continue

                        if impediment_start_status in active_columns:
                            item['blocked_days'] += (snapshot.date.date() - impediment_start).days
                        item['impediments'].append({
                            'start': impediment_start,
                            'end': snapshot.date.date(),
                            'status': impediment_start_status,
                            'flag': impediment_flag,
                        })

                        # Reset for next time
                        impediment_flag = None
                        impediment_start = None
                        impediment_start_status = None

            # If an impediment flag was set but never cleared: treat as resolved on the ticket
            # resolution date if the ticket was resolved, else as still open until today.
            if impediment_start is not None:
                if issue.fields.resolutiondate:
                    resolution_date = dateutil.parser.parse(issue.fields.resolutiondate).date()
                    if impediment_start_status in active_columns:
                        item['blocked_days'] += (resolution_date - impediment_start).days
                    item['impediments'].append({
                        'start': impediment_start,
                        'end': resolution_date,
                        'status': impediment_start_status,
                        'flag': impediment_flag,
                    })
                else:
                    if impediment_start_status in active_columns:
                        item['blocked_days'] += (now.date() - impediment_start).days
                    item['impediments'].append({
                        'start': impediment_start,
                        'end': None,
                        'status': impediment_start_status,
                        'flag': impediment_flag,
                    })
                impediment_flag = None
                impediment_start = None
                impediment_start_status = None

            # calculate cycle time

            committed_timestamp = None
            done_timestamp = None

            if timespans[committed_column].filled:
                committed_timestamp = timespans[committed_column].start

            if timespans[done_column].filled:
                done_timestamp = timespans[done_column].last_start

            if committed_timestamp is not None and done_timestamp is not None:
                item['cycle_time'] = done_timestamp - committed_timestamp
                assert(item['cycle_time'] >= datetime.timedelta(seconds=0))
                item['completed_timestamp'] = done_timestamp

            # The legacy data handling assumes columns [state name: date] so we export these,
            # but we also export durations in another column.
            # Raw Timespans object is not exported ATM,
            # but could be added in the future if there is need for it.
            for workflow_state_name, timespans in timespans.items():

                if timespans.filled:
                    # Did we have any cycles for this issue
                    start = timespans.start.date()
                    duration = timespans.duration
                else:
                    start = None
                    duration = None

                item[workflow_state_name] = start
                item[f'{workflow_state_name} duration'] = duration

                if duration:
                    days = duration.total_seconds() / (24 * 3600)
                else:
                    days = 0

                # Try to be helpful with the logging output to
                # allow effective diagnose of transition issues
                logger.debug("Calculated duration for state %s, with spans %s as %f days", workflow_state_name, timespans, days)

            for k, v in item.items():
                # logger.debug("Adding %s %s", k, v)
                series[k]['data'].append(v)

    if len(unmapped_statuses) > 0:
        logger.warn("The following JIRA statuses were found, but not mapped to a workflow state, and have been ignored: %s", ', '.join(sorted(unmapped_statuses)))

    data = {}
    for k, v in series.items():
        data[k] = pd.Series(v['data'], dtype=v['dtype'])

    return pd.DataFrame(data,
        columns=['key', 'url', 'issue_type', 'summary', 'status', 'resolution', 'estimation_days'] +
                sorted(attributes.keys()) +
                ([query_attribute] if query_attribute else []) +
                ['cycle_time', 'completed_timestamp', 'blocked_days', 'impediments'] +
                cycle_duration_names +
                cycle_names   # Must be the last item due to legacy reasons

    )
