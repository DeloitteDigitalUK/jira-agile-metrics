import pytest
from pandas import DataFrame, Timestamp, NaT

from .querymanager import QueryManager
from .utils import extend_dict

from .calculators.cycletime import CycleTimeCalculator
from .calculators.cfd import CFDCalculator

# Fake a portion of the JIRA API

class FauxFieldValue(object):
    """A complex field value, with a name and a typed value
    """
    def __init__(self, name, value):
        self.name = name
        self.value = value

class FauxFields(object):
    """Container for `issue.fields`
    """
    def __init__(self, fields):
        self.__dict__.update(fields)

class FauxChangeItem(object):
    """An item in a changelog change
    """
    def __init__(self, field, fromString, toString):
        self.field = field
        self.from_ = self.fromString = fromString
        self.to = self.toString = toString

class FauxChange(object):
    """A change in a changelog. Contains a list of change items.
    """
    def __init__(self, created, items):
        self.created = created
        self.items = [FauxChangeItem(*i) for i in items]

class FauxChangelog(object):
    """A changelog. Contains a list of changes in `histories`.
    """
    def __init__(self, changes):
        self.histories = changes

class FauxIssue(object):
    """An issue, with a key, change log, and set of fields
    """
    def __init__(self, key, changes, **fields):
        self.key = key
        self.fields = FauxFields(fields)
        self.changelog = FauxChangelog(changes)

class FauxJIRA(object):
    """JIRA interface. Initialised with a set of issues, which will be returned
    by `search_issues()`.
    """

    def __init__(self, fields, issues, options={'server': 'https://example.org'}):
        self._options = options
        self._fields = fields  # [{ id, name }]
        self._issues = issues

    def fields(self):
        return self._fields

    def search_issues(self, jql, *args, **kwargs):
        return self._issues

# Fixtures

@pytest.fixture
def minimal_settings():
    """The smallest `settings` required to build a query manager and cycle time
    calculation.
    """
    return {
        'attributes': {},
        'known_values': {
            'Release': ['R1', 'R3']
        },
        'max_results': None,
        'verbose': False,
        'cycle': [
            {'name': 'Backlog',   'statuses': ['Backlog'],           'type': 'backlog'},
            {'name': 'Committed', 'statuses': ['Next'],              'type': 'accepted'},
            {'name': 'Build',     'statuses': ['Build'],             'type': 'accepted'},
            {'name': 'Test',      'statuses': ['Code review', 'QA'], 'type': 'accepted'},
            {'name': 'Done',      'statuses': ['Done'],              'type': 'complete'}
        ],
        'query_attribute': None,
        'queries': [{'jql': '(filter=123)', 'value': None}]
    }


@pytest.fixture
def custom_settings(minimal_settings):
    """A `settings` dict that uses custom fields and attributes.
    """
    return extend_dict(minimal_settings, {
        'attributes': {
            'Release': 'Releases',
            'Team': 'Team',
            'Estimate': 'Size'
        },
        'known_values': {
            'Release': ['R1', 'R3']
        },
    })

# Fields + corresponding columns

@pytest.fixture
def minimal_fields():
    """A `fields` list for all basic fields, but no custom fields.
    """
    return [
        {'id': 'summary',    'name': 'Summary'},
        {'id': 'issuetype',  'name': 'Issue type'},
        {'id': 'status',     'name': 'Status'},
        {'id': 'resolution', 'name': 'Resolution'},
        {'id': 'created',    'name': 'Created date'},
    ]

@pytest.fixture
def custom_fields(minimal_fields):
    """A `fields` list with the three custom fields used by `custom_settings`
    """
    return minimal_fields + [
        {'id': 'customfield_001',  'name': 'Team'},
        {'id': 'customfield_002',  'name': 'Size'},
        {'id': 'customfield_003',  'name': 'Releases'},
    ]

@pytest.fixture
def minimal_cycle_time_columns():
    """A columns list for the results of CycleTimeCalculator without any
    custom fields.
    """
    return [
        'key', 'url', 'issue_type', 'summary', 'status', 'resolution',
        'cycle_time', 'completed_timestamp',
        'Backlog', 'Committed', 'Build', 'Test', 'Done'
    ]

@pytest.fixture
def custom_cycle_time_columns(minimal_fields):
    """A columns list for the results of CycleTimeCalculator with the three
    custom fields from `custom_settings`.
    """
    return [
        'key', 'url', 'issue_type', 'summary', 'status', 'resolution',
        'Estimate', 'Release', 'Team',
        'cycle_time', 'completed_timestamp',
        'Backlog', 'Committed', 'Build', 'Test', 'Done'
    ]

@pytest.fixture
def cfd_columns():
    """A columns list for the results of the CFDCalculator.
    """
    return [
        'Backlog',
        'Committed',
        'Build',
        'Test',
        'Done'
    ]

# Query manager

@pytest.fixture
def minimal_query_manager(minimal_fields, minimal_settings):
    """A minimal query manager (no custom fields)
    """
    jira = FauxJIRA(fields=minimal_fields, issues=[])
    return QueryManager(jira, minimal_settings)

@pytest.fixture
def custom_query_manager(custom_fields, custom_settings):
    """A query manager capable of returning values for custom fields
    """
    jira = FauxJIRA(fields=custom_fields, issues=[])
    return QueryManager(jira, custom_settings)


# Results object with rich cycle time data

_issue_counter = 0
def _issue(Backlog, Committed, Build, Test, Done):
    """Simple issue records factory to make it easier to build fixtures with many issues
    """
    global _issue_counter
    _issue_counter += 1
    return {
        'key': 'A-%d' % _issue_counter,
        'url': 'https://example.org/browse/A-%d' % _issue_counter,
        'issue_type': 'Story',
        'summary': 'Generated issue A-%d' % _issue_counter,
        'status': (
            "Done" if Done is not NaT else
            "Test" if Test is not NaT else
            "Build" if Build is not NaT else
            "Committed" if Committed is not NaT else
            "Backlog"
        ),
        'resoluton': "Done" if Done is not NaT else None,
        'completed_timestamp': Done if Done is not NaT else None,
        'cycle_time': (Done - Committed) if (Done is not NaT and Committed is not NaT) else None,
        'Backlog': Backlog,
        'Committed': Committed,
        'Build': Build,
        'Test': Test,
        'Done': Done
    }

@pytest.fixture
def minimal_cycle_time_results(minimal_cycle_time_columns):
    """A results dict mimicing a minimal result from the CycleTimeCalculator.
    """
    return {
        CycleTimeCalculator: DataFrame([
            _issue(Backlog=Timestamp('2018-01-01 01:01:01'), Committed=NaT,                              Build=NaT,                              Test=NaT,                              Done=NaT),
            _issue(Backlog=Timestamp('2018-01-02 01:01:01'), Committed=Timestamp('2018-01-03 01:01:01'), Build=NaT,                              Test=NaT,                              Done=NaT),
            _issue(Backlog=Timestamp('2018-01-03 01:01:01'), Committed=Timestamp('2018-01-03 01:01:01'), Build=Timestamp('2018-01-04 01:01:01'), Test=Timestamp('2018-01-05 01:01:01'), Done=Timestamp('2018-01-06 01:01:01')),
            _issue(Backlog=Timestamp('2018-01-04 01:01:01'), Committed=Timestamp('2018-01-04 01:01:01'), Build=NaT,                              Test=NaT,                              Done=NaT),
        ], columns=minimal_cycle_time_columns)
    }

@pytest.fixture
def minimal_cfd_results(minimal_cycle_time_results, cfd_columns):
    """A results dict mimicing a minimal result from the CycleTimeCalculator.
    """
    return extend_dict(minimal_cycle_time_results, {
        CFDCalculator: DataFrame([
            {'Backlog': 1.0, 'Committed': 0.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
            {'Backlog': 2.0, 'Committed': 0.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
            {'Backlog': 3.0, 'Committed': 2.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
            {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 0.0, 'Done': 0.0},
            {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 1.0, 'Done': 0.0},
            {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 1.0, 'Done': 1.0},
        ], columns=cfd_columns, index=[
            Timestamp('2018-01-01 00:00:00', freq='D'),
            Timestamp('2018-01-02 00:00:00', freq='D'),
            Timestamp('2018-01-03 00:00:00', freq='D'),
            Timestamp('2018-01-04 00:00:00', freq='D'),
            Timestamp('2018-01-05 00:00:00', freq='D'),
            Timestamp('2018-01-06 00:00:00', freq='D')
        ])
    })
