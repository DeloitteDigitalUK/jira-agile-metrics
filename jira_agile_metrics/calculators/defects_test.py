import datetime
import pytest
from pandas import Timedelta, Timestamp, NaT

from ..conftest import (
    FauxJIRA as JIRA,
    FauxIssue as Issue,
    FauxFieldValue as Value
)

from ..utils import extend_dict

from ..querymanager import QueryManager
from .defects import DefectsCalculator

@pytest.fixture
def fields(minimal_fields):
    return minimal_fields + [
        {'id': 'priority',  'name': 'Priority'},
        {'id': 'customfield_001',  'name': 'Environment'},
        {'id': 'customfield_002',  'name': 'Defect type'},
    ]

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
        'defects_query': 'issueType = Defect',
        'defects_window': 3,
        'defects_priority_field': 'Priority',
        'defects_priority_values': ['Low', 'Medium', 'High'],
        'defects_type_field': 'Defect type',
        'defects_type_values': ['Config', 'Data', 'Code'],
        'defects_environment_field': 'Environment',
        'defects_environment_values': ['SIT', 'UAT', 'PROD'],

        'defects_by_priority_chart': 'defects-by-priority.png',
        'defects_by_priority_chart_title': 'Defects by priority',
        'defects_by_type_chart': 'defects-by-type.png',
        'defects_by_type_chart_title': 'Defects by type',
        'defects_by_environment_chart': 'defects-by-environment.png',
        'defects_by_environment_chart_title': 'Defects by environment',
    })

@pytest.fixture
def jira(fields):
    return JIRA(fields=fields, issues=[
        Issue("D-1",
            summary="Debt 1",
            issuetype=Value("Bug", "Bug"),
            status=Value("Closed", "closed"),
            created="2018-01-01 01:01:01",
            resolution="Done",
            resolutiondate="2018-03-20 02:02:02",
            priority=Value("High", "High"),
            customfield_001=Value(None, "PROD"),
            customfield_002=Value(None, "Config"),
            changes=[],
        ),
        Issue("D-2",
            summary="Debt 2",
            issuetype=Value("Bug", "Bug"),
            status=Value("Closed", "closed"),
            created="2018-01-02 01:01:01",
            resolution="Done",
            resolutiondate="2018-01-20 02:02:02",
            priority=Value("Medium", "Medium"),
            customfield_001=Value(None, "SIT"),
            customfield_002=Value(None, "Config"),
            changes=[],
        ),
        Issue("D-3",
            summary="Debt 3",
            issuetype=Value("Bug", "Bug"),
            status=Value("Closed", "closed"),
            created="2018-02-03 01:01:01",
            resolution="Done",
            resolutiondate="2018-03-20 02:02:02",
            priority=Value("High", "High"),
            customfield_001=Value(None, "UAT"),
            customfield_002=Value(None, "Config"),
            changes=[],
        ),
        Issue("D-4",
            summary="Debt 4",
            issuetype=Value("Bug", "Bug"),
            status=Value("Closed", "closed"),
            created="2018-01-04 01:01:01",
            resolution=None,
            resolutiondate=None,
            priority=Value("Medium", "Medium"),
            customfield_001=Value(None, "PROD"),
            customfield_002=Value(None, "Data"),
            changes=[],
        ),
        Issue("D-5",
            summary="Debt 5",
            issuetype=Value("Bug", "Bug"),
            status=Value("Closed", "closed"),
            created="2018-02-05 01:01:01",
            resolution="Done",
            resolutiondate="2018-02-20 02:02:02",
            priority=Value("High", "High"),
            customfield_001=Value(None, "SIT"),
            customfield_002=Value(None, "Data"),
            changes=[],
        ),
        Issue("D-6",
            summary="Debt 6",
            issuetype=Value("Bug", "Bug"),
            status=Value("Closed", "closed"),
            created="2018-03-06 01:01:01",
            resolution=None,
            resolutiondate=None,
            priority=Value("Medium", "Medium"),
            customfield_001=Value(None, "UAT"),
            customfield_002=Value(None, "Data"),
            changes=[],
        ),
    ])

def test_no_query(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    settings = extend_dict(settings, {
        'defects_query': None
    })
    calculator = DefectsCalculator(query_manager, settings, results)

    data = calculator.run()
    assert data is None

def test_columns(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DefectsCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.columns) == ['key', 'priority', 'type', 'environment', 'created', 'resolved']

def test_empty(fields, settings):
    jira = JIRA(fields=fields, issues=[])
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DefectsCalculator(query_manager, settings, results)

    data = calculator.run()

    assert len(data.index) == 0


def test_breakdown(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DefectsCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'D-1', 'created': Timestamp('2018-01-01 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'priority': 'High',   'environment': 'PROD', 'type': 'Config'},
        {'key': 'D-2', 'created': Timestamp('2018-01-02 01:01:01'), 'resolved': Timestamp('2018-01-20 02:02:02'), 'priority': 'Medium', 'environment': 'SIT',  'type': 'Config'},
        {'key': 'D-3', 'created': Timestamp('2018-02-03 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'priority': 'High',   'environment': 'UAT',  'type': 'Config'},
        {'key': 'D-4', 'created': Timestamp('2018-01-04 01:01:01'), 'resolved': NaT,                              'priority': 'Medium', 'environment': 'PROD', 'type': 'Data'},
        {'key': 'D-5', 'created': Timestamp('2018-02-05 01:01:01'), 'resolved': Timestamp('2018-02-20 02:02:02'), 'priority': 'High',   'environment': 'SIT',  'type': 'Data'},
        {'key': 'D-6', 'created': Timestamp('2018-03-06 01:01:01'), 'resolved': NaT,                              'priority': 'Medium', 'environment': 'UAT',  'type': 'Data'},
    ]


def test_no_priority_field(jira, settings):
    settings = extend_dict(settings, {
        'defects_priority_field': None
    })

    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DefectsCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'D-1', 'created': Timestamp('2018-01-01 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'priority': None, 'environment': 'PROD', 'type': 'Config'},
        {'key': 'D-2', 'created': Timestamp('2018-01-02 01:01:01'), 'resolved': Timestamp('2018-01-20 02:02:02'), 'priority': None, 'environment': 'SIT',  'type': 'Config'},
        {'key': 'D-3', 'created': Timestamp('2018-02-03 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'priority': None, 'environment': 'UAT',  'type': 'Config'},
        {'key': 'D-4', 'created': Timestamp('2018-01-04 01:01:01'), 'resolved': NaT,                              'priority': None, 'environment': 'PROD', 'type': 'Data'},
        {'key': 'D-5', 'created': Timestamp('2018-02-05 01:01:01'), 'resolved': Timestamp('2018-02-20 02:02:02'), 'priority': None, 'environment': 'SIT',  'type': 'Data'},
        {'key': 'D-6', 'created': Timestamp('2018-03-06 01:01:01'), 'resolved': NaT,                              'priority': None, 'environment': 'UAT',  'type': 'Data'},
    ]

def test_no_type_field(jira, settings):
    settings = extend_dict(settings, {
        'defects_type_field': None
    })

    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DefectsCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'D-1', 'created': Timestamp('2018-01-01 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'priority': 'High',   'environment': 'PROD', 'type': None},
        {'key': 'D-2', 'created': Timestamp('2018-01-02 01:01:01'), 'resolved': Timestamp('2018-01-20 02:02:02'), 'priority': 'Medium', 'environment': 'SIT',  'type': None},
        {'key': 'D-3', 'created': Timestamp('2018-02-03 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'priority': 'High',   'environment': 'UAT',  'type': None},
        {'key': 'D-4', 'created': Timestamp('2018-01-04 01:01:01'), 'resolved': NaT,                              'priority': 'Medium', 'environment': 'PROD', 'type': None},
        {'key': 'D-5', 'created': Timestamp('2018-02-05 01:01:01'), 'resolved': Timestamp('2018-02-20 02:02:02'), 'priority': 'High',   'environment': 'SIT',  'type': None},
        {'key': 'D-6', 'created': Timestamp('2018-03-06 01:01:01'), 'resolved': NaT,                              'priority': 'Medium', 'environment': 'UAT',  'type': None},
    ]

def test_no_environment_field(jira, settings):
    settings = extend_dict(settings, {
        'defects_environment_field': None
    })

    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DefectsCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'D-1', 'created': Timestamp('2018-01-01 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'priority': 'High',   'environment': None, 'type': 'Config'},
        {'key': 'D-2', 'created': Timestamp('2018-01-02 01:01:01'), 'resolved': Timestamp('2018-01-20 02:02:02'), 'priority': 'Medium', 'environment': None, 'type': 'Config'},
        {'key': 'D-3', 'created': Timestamp('2018-02-03 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'priority': 'High',   'environment': None, 'type': 'Config'},
        {'key': 'D-4', 'created': Timestamp('2018-01-04 01:01:01'), 'resolved': NaT,                              'priority': 'Medium', 'environment': None, 'type': 'Data'},
        {'key': 'D-5', 'created': Timestamp('2018-02-05 01:01:01'), 'resolved': Timestamp('2018-02-20 02:02:02'), 'priority': 'High',   'environment': None, 'type': 'Data'},
        {'key': 'D-6', 'created': Timestamp('2018-03-06 01:01:01'), 'resolved': NaT,                              'priority': 'Medium', 'environment': None, 'type': 'Data'},
    ]
