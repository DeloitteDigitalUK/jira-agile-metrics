from .query import QueryManager
import pandas as pd
import numpy as np

class StatusTypes:
    backlog = 'backlog'
    accepted = 'accepted'
    complete = 'complete'

class CycleTimeQueries(QueryManager):
    """Analysis for cycle time data, producing cumulative flow diagrams,
    scatter plots and histograms.

    Initialise with a `cycle`, a list of dicts representing the steps in
    a cycle. Each dict describes that step with keys `name`, `type` (one of
    "backlog", "accepted" or "complete" as per the `StatusTypes` enum) and
    `statuses` (a list of equivalent JIRA workflow statuses that map onto
    this step).
    """

    settings = dict(
        cycle=[  # flow steps, types, and mapped JIRA statuses
            {
                "name": 'todo',
                "type": StatusTypes.backlog,
                "statuses": ["Open", "To Do"],
            },
            {
                "name": 'analysis',
                "type": StatusTypes.accepted,
                "statuses": ["Analysis"],
            },
            {
                "name": 'analysis-done',
                "type": StatusTypes.accepted,
                "statuses": ["Analysis Done"],
            },
            {
                "name": 'development',
                "type": StatusTypes.accepted,
                "statuses": ["In Progress"],
            },
            {
                "name": 'done',
                "type": StatusTypes.complete,
                "statuses": ["Done", "Closed"],
            },
        ]
    )

    def __init__(self, jira, **kwargs):
        settings = super(CycleTimeQueries, self).settings.copy()
        settings.update(self.settings.copy())
        settings.update(kwargs)

        settings['cycle_lookup'] = {}
        for idx, cycle_step in enumerate(settings['cycle']):
            for status in cycle_step['statuses']:
                settings['cycle_lookup'][status.lower()] = dict(
                    index=idx,
                    name=cycle_step['name'],
                    type=cycle_step['type'],
                )

        super(CycleTimeQueries, self).__init__(jira, **settings)

    def cycle_data(self, verbose=False):
        """Build a numerically indexed data frame with the following 'fixed'
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

        cycle_names = [s['name'] for s in self.settings['cycle']]
        accepted_steps = set(s['name'] for s in self.settings['cycle'] if s['type'] == StatusTypes.accepted)
        completed_steps = set(s['name'] for s in self.settings['cycle'] if s['type'] == StatusTypes.complete)

        series = {
            'key': {'data': [], 'dtype': 'str'},
            'url': {'data': [], 'dtype': 'str'},
            'issue_type': {'data': [], 'dtype': 'str'},
            'summary': {'data': [], 'dtype': 'str'},
            'status': {'data': [], 'dtype': 'str'},
            'resolution': {'data': [], 'dtype': 'str'},
            'cycle_time': {'data': [], 'dtype': 'timedelta64[ns]'},
            'completed_timestamp': {'data': [], 'dtype': 'datetime64[ns]'}
        }

        for cycle_name in cycle_names:
            series[cycle_name] = {'data': [], 'dtype': 'datetime64[ns]'}

        for name in self.fields.keys():
            series[name] = {'data': [], 'dtype': 'object'}

        if self.settings['query_attribute']:
            series[self.settings['query_attribute']] = {'data': [], 'dtype': 'str'}

        for criteria in self.settings['queries']:
            for issue in self.find_issues(criteria, order='updatedDate DESC', verbose=verbose):

                item = {
                    'key': issue.key,
                    'url': "%s/browse/%s" % (self.jira._options['server'], issue.key,),
                    'issue_type': issue.fields.issuetype.name,
                    'summary': issue.fields.summary.encode('utf-8'),
                    'status': issue.fields.status.name,
                    'resolution': issue.fields.resolution.name if issue.fields.resolution else None,
                    'cycle_time': None,
                    'completed_timestamp': None
                }

                for name, field_name in self.fields.items():
                    item[name] = self.resolve_field_value(issue, name, field_name)

                if self.settings['query_attribute']:
                    item[self.settings['query_attribute']] = criteria.get('value', None)

                for cycle_name in cycle_names:
                    item[cycle_name] = None

                # Record date of status changes
                for snapshot in self.iter_changes(issue, False):
                    snapshot_cycle_step = self.settings['cycle_lookup'].get(snapshot.status.lower(), None)
                    if snapshot_cycle_step is None:
                        if verbose:
                            print(issue.key, "transitioned to unknown JIRA status", snapshot.status)
                        continue

                    snapshot_cycle_step_name = snapshot_cycle_step['name']

                    # Keep the first time we entered a step
                    if item[snapshot_cycle_step_name] is None:
                        item[snapshot_cycle_step_name] = snapshot.date

                    # Wipe any subsequent dates, in case this was a move backwards
                    found_cycle_name = False
                    for cycle_name in cycle_names:
                        if not found_cycle_name and cycle_name == snapshot_cycle_step_name:
                            found_cycle_name = True
                            continue
                        elif found_cycle_name and item[cycle_name] is not None:
                            if verbose:
                                print(issue.key, "moved backwards to", snapshot_cycle_step_name, "wiping date for subsequent step", cycle_name)
                            item[cycle_name] = None

                # Wipe timestamps if items have moved backwards; calculate cycle time

                previous_timestamp = None
                accepted_timestamp = None
                completed_timestamp = None

                for cycle_name in cycle_names:
                    if item[cycle_name] is not None:
                        previous_timestamp = item[cycle_name]

                        if accepted_timestamp is None and previous_timestamp is not None and cycle_name in accepted_steps:
                            accepted_timestamp = previous_timestamp
                        if completed_timestamp is None and previous_timestamp is not None and cycle_name in completed_steps:
                            completed_timestamp = previous_timestamp

                if accepted_timestamp is not None and completed_timestamp is not None:
                    item['cycle_time'] = completed_timestamp - accepted_timestamp
                    item['completed_timestamp'] = completed_timestamp

                for k, v in item.items():
                    series[k]['data'].append(v)

        data = {}
        for k, v in series.items():
            data[k] = pd.Series(v['data'], dtype=v['dtype'])

        return pd.DataFrame(data,
            columns=['key', 'url', 'issue_type', 'summary', 'status', 'resolution'] +
                    sorted(self.fields.keys()) +
                    ([self.settings['query_attribute']] if self.settings['query_attribute'] else []) +
                    ['cycle_time', 'completed_timestamp'] +
                    cycle_names
        )

    def cfd(self, cycle_data):
        """Return the data to build a cumulative flow diagram: a DataFrame,
        indexed by day, with columns containing cumulative counts for each
        of the items in the configured cycle.

        In addition, a column called `cycle_time` contains the approximate
        average cycle time of that day based on the first "accepted" status
        and the first "complete" status.
        """

        cycle_names = [s['name'] for s in self.settings['cycle']]

        # Build a dataframe of just the "date" columns
        df = cycle_data[cycle_names]

        # Strip out times from all dates
        df = pd.DataFrame(
            np.array(df.values, dtype='<M8[ns]').astype('<M8[D]').astype('<M8[ns]'),
            columns=df.columns,
            index=df.index
        )

        # Replace missing NaT values (happens if a status is skipped) with the subsequent timestamp
        df = df.fillna(method='bfill', axis=1)

        # Count number of times each date occurs, preserving column order
        df = pd.concat({col: df[col].value_counts() for col in df}, axis=1)[cycle_names]

        # Fill missing dates with 0 and run a cumulative sum
        df = df.fillna(0).cumsum(axis=0)

        # Reindex to make sure we have all dates
        start, end = df.index.min(), df.index.max()
        df = df.reindex(pd.date_range(start, end, freq='D'), method='ffill')

        return df


    def histogram(self, cycle_data, bins=10):
        """Return histogram data for the cycle times in `cycle_data`. Returns
        a dictionary with keys `bin_values` and `bin_edges` of numpy arrays
        """
        values, edges = np.histogram(cycle_data['cycle_time'].astype('timedelta64[D]').dropna(), bins=bins)

        index = []
        for i, _ in enumerate(edges):
            if i == 0:
                continue
            index.append("%.01f to %.01f" % (edges[i - 1], edges[i],))

        return pd.Series(values, name="Items", index=index)

    def throughput_data(self, cycle_data, frequency='1D'):
        """Return a data frame with columns `completed_timestamp` of the
        given frequency, and `count`, where count is the number of items
        completed at that timestamp (e.g. daily).
        """
        return cycle_data[['completed_timestamp', 'key']] \
            .rename(columns={'key': 'count'}) \
            .groupby('completed_timestamp').count() \
            .resample(frequency).sum() \
            .fillna(0)

    def scatterplot(self, cycle_data):
        """Return scatterplot data for the cycle times in `cycle_data`. Returns
        a data frame containing only those items in `cycle_data` where values
        are set for `completed_timestamp` and `cycle_time`, and with those two
        columns as the first two, both normalised to whole days, and with
        `completed_timestamp` renamed to `completed_date`.
        """

        columns = list(cycle_data.columns)
        columns.remove('cycle_time')
        columns.remove('completed_timestamp')
        columns = ['completed_timestamp', 'cycle_time'] + columns

        data = (
            cycle_data[columns]
            .dropna(subset=['cycle_time', 'completed_timestamp'])
            .rename(columns={'completed_timestamp': 'completed_date'})
        )

        data['cycle_time'] = data['cycle_time'].astype('timedelta64[D]')
        data['completed_date'] = data['completed_date'].map(pd.Timestamp.date)

        return data

    def percentiles(self, cycle_data, percentiles=(0.3, 0.5, 0.7, 0.85, 0.95,)):
        """Return percentiles for `cycle_time` in cycle data as a DataFrame
        """

        return cycle_data['cycle_time'].dropna().quantile(percentiles)
