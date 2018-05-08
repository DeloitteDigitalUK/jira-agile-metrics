import pytest
from pandas import DataFrame, Timestamp, NaT

from .querymanager import QueryManager
from .calculators.cycletime import CycleTimeCalculator

# Fake a portion of the JIRA API

class FauxFieldValue(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class FauxFields(object):
    def __init__(self, fields):
        self.__dict__.update(fields)

class FauxChangeItem(object):
    def __init__(self, field, fromString, toString):
        self.field = field
        self.from_ = self.fromString = fromString
        self.to = self.toString = toString

class FauxChange(object):
    def __init__(self, created, items):
        self.created = created
        self.items = [FauxChangeItem(*i) for i in items]

class FauxChangelog(object):
    def __init__(self, changes):
        self.histories = changes

class FauxIssue(object):
    def __init__(self, key, changes, **fields):
        self.key = key
        self.fields = FauxFields(fields)
        self.changelog = FauxChangelog(changes)

class FauxJIRA(object):

    def __init__(self, fields, issues, options={'server': 'https://example.org'}):
        self._options = options
        self._fields = fields  # [{ id, name }]
        self._issues = issues

    def fields(self):
        return self._fields

    def search_issues(self, jql, *args, **kwargs):
        return self._issues

# Simple `settings` object that can be extended in other tests

@pytest.fixture
def minimal_settings():
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
    minimal_settings.update({
        'attributes': {
            'Release': 'Releases',
            'Team': 'Team',
            'Estimate': 'Size'
        },
        'known_values': {
            'Release': ['R1', 'R3']
        },
    })
    return minimal_settings

# Fields + corresponding columns

@pytest.fixture
def minimal_fields():
    return [
        {'id': 'summary',    'name': 'Summary'},
        {'id': 'issuetype',  'name': 'Issue type'},
        {'id': 'status',     'name': 'Status'},
        {'id': 'resolution', 'name': 'Resolution'},
        {'id': 'created',    'name': 'Created date'},
    ]

@pytest.fixture
def custom_fields(minimal_fields):
    return minimal_fields + [
        {'id': 'customfield_001',  'name': 'Team'},
        {'id': 'customfield_002',  'name': 'Size'},
        {'id': 'customfield_003',  'name': 'Releases'},
    ]

@pytest.fixture
def minimal_cycle_time_columns():
    return [
        'key', 'url', 'issue_type', 'summary', 'status', 'resolution',
        'cycle_time', 'completed_timestamp',
        'Backlog', 'Committed', 'Build', 'Test', 'Done'
    ]

@pytest.fixture
def custom_cycle_time_columns(minimal_fields):
    return [
        'key', 'url', 'issue_type', 'summary', 'status', 'resolution',
        'Estimate', 'Release', 'Team',
        'cycle_time', 'completed_timestamp',
        'Backlog', 'Committed', 'Build', 'Test', 'Done'
    ]

# Query manager

@pytest.fixture
def minimal_query_manager(minimal_fields, minimal_settings):
    jira = FauxJIRA(fields=minimal_fields, issues=[])
    return QueryManager(jira, minimal_settings)

@pytest.fixture
def custom_query_manager(custom_fields, custom_settings):
    jira = FauxJIRA(fields=custom_fields, issues=[])
    return QueryManager(jira, custom_settings)


# Results object with rich cycle time data


_issue_counter = 0
def _issue(Backlog, Committed, Build, Test, Done):
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
    return {
        CycleTimeCalculator: DataFrame([
            _issue(Backlog=Timestamp('2018-01-01 01:01:01'), Committed=NaT, Build=NaT, Test=NaT, Done=NaT),
            _issue(Backlog=Timestamp('2018-01-02 01:01:01'), Committed=Timestamp('2018-01-03 01:01:01'), Build=NaT, Test=NaT, Done=NaT),
            _issue(Backlog=Timestamp('2018-01-03 01:01:01'), Committed=Timestamp('2018-01-03 01:01:01'), Build=Timestamp('2018-01-04 01:01:01'), Test=Timestamp('2018-01-05 01:01:01'), Done=Timestamp('2018-01-06 01:01:01')),
            _issue(Backlog=Timestamp('2018-01-04 01:01:01'), Committed=Timestamp('2018-01-04 01:01:01'), Build=NaT, Test=NaT, Done=NaT),
        ], columns=minimal_cycle_time_columns)
    }
