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
from .debt import DebtCalculator

@pytest.fixture
def fields(minimal_fields):
    return minimal_fields + [
        {'id': 'priority',  'name': 'Priority'},
    ]

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
        'debt_query': 'issueType = "Tech Debt"',
        'debt_priority_field': 'Priority',
        'debt_priority_values': ['Low', 'Medium', 'High'],
        'debt_chart': 'debt-chart.png',
        'debt_chart_title': 'Debt chart',
        'debt_window': 3,
        'debt_age_chart': 'debt-age-chart.png',
        'debt_age_chart_title': 'Debt age',
        'debt_age_chart_bins': [10, 20, 30]
    })

@pytest.fixture
def jira(fields):
    return JIRA(fields=fields, issues=[
        Issue("D-1",
            summary="Debt 1",
            issuetype=Value("Tech Debt", "Tech Debt"),
            status=Value("Closed", "closed"),
            created="2018-01-01 01:01:01",
            resolution="Done",
            resolutiondate="2018-03-20 02:02:02",
            priority=Value("High", "High"),
            changes=[],
        ),
        Issue("D-2",
            summary="Debt 2",
            issuetype=Value("Tech Debt", "Tech Debt"),
            status=Value("Closed", "closed"),
            created="2018-01-02 01:01:01",
            resolution="Done",
            resolutiondate="2018-01-20 02:02:02",
            priority=Value("Medium", "Medium"),
            changes=[],
        ),
        Issue("D-3",
            summary="Debt 3",
            issuetype=Value("Tech Debt", "Tech Debt"),
            status=Value("Closed", "closed"),
            created="2018-02-03 01:01:01",
            resolution="Done",
            resolutiondate="2018-03-20 02:02:02",
            priority=Value("High", "High"),
            changes=[],
        ),
        Issue("D-4",
            summary="Debt 4",
            issuetype=Value("Tech Debt", "Tech Debt"),
            status=Value("Closed", "closed"),
            created="2018-01-04 01:01:01",
            resolution=None,
            resolutiondate=None,
            priority=Value("Medium", "Medium"),
            changes=[],
        ),
        Issue("D-5",
            summary="Debt 5",
            issuetype=Value("Tech Debt", "Tech Debt"),
            status=Value("Closed", "closed"),
            created="2018-02-05 01:01:01",
            resolution="Done",
            resolutiondate="2018-02-20 02:02:02",
            priority=Value("High", "High"),
            changes=[],
        ),
        Issue("D-6",
            summary="Debt 6",
            issuetype=Value("Tech Debt", "Tech Debt"),
            status=Value("Closed", "closed"),
            created="2018-03-06 01:01:01",
            resolution=None,
            resolutiondate=None,
            priority=Value("Medium", "Medium"),
            changes=[],
        ),
    ])

def test_no_query(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    settings = extend_dict(settings, {
        'debt_query': None
    })
    calculator = DebtCalculator(query_manager, settings, results)

    data = calculator.run()
    assert data is None

def test_columns(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DebtCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.columns) == ['key', 'priority', 'created', 'resolved', 'age']

def test_empty(fields, settings):
    jira = JIRA(fields=fields, issues=[])
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DebtCalculator(query_manager, settings, results)

    data = calculator.run()

    assert len(data.index) == 0


def test_breakdown(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DebtCalculator(query_manager, settings, results)

    data = calculator.run(now=datetime.datetime(2018, 3, 21, 2, 2, 2))

    assert data.to_dict('records') == [
        {'key': 'D-1', 'created': Timestamp('2018-01-01 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'age': Timedelta('78 days 01:01:01'), 'priority': 'High'},
        {'key': 'D-2', 'created': Timestamp('2018-01-02 01:01:01'), 'resolved': Timestamp('2018-01-20 02:02:02'), 'age': Timedelta('18 days 01:01:01'), 'priority': 'Medium'},
        {'key': 'D-3', 'created': Timestamp('2018-02-03 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'age': Timedelta('45 days 01:01:01'), 'priority': 'High'},
        {'key': 'D-4', 'created': Timestamp('2018-01-04 01:01:01'), 'resolved': NaT,                              'age': Timedelta('76 days 01:01:01'), 'priority': 'Medium'},
        {'key': 'D-5', 'created': Timestamp('2018-02-05 01:01:01'), 'resolved': Timestamp('2018-02-20 02:02:02'), 'age': Timedelta('15 days 01:01:01'), 'priority': 'High'},
        {'key': 'D-6', 'created': Timestamp('2018-03-06 01:01:01'), 'resolved': NaT,                              'age': Timedelta('15 days 01:01:01'), 'priority': 'Medium'},
    ]


def test_no_priority_field(jira, settings):
    settings = extend_dict(settings, {
        'debt_priority_field': None
    })

    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = DebtCalculator(query_manager, settings, results)

    data = calculator.run(now=datetime.datetime(2018, 3, 21, 2, 2, 2))

    assert data.to_dict('records') == [
        {'key': 'D-1', 'created': Timestamp('2018-01-01 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'age': Timedelta('78 days 01:01:01'), 'priority': None},
        {'key': 'D-2', 'created': Timestamp('2018-01-02 01:01:01'), 'resolved': Timestamp('2018-01-20 02:02:02'), 'age': Timedelta('18 days 01:01:01'), 'priority': None},
        {'key': 'D-3', 'created': Timestamp('2018-02-03 01:01:01'), 'resolved': Timestamp('2018-03-20 02:02:02'), 'age': Timedelta('45 days 01:01:01'), 'priority': None},
        {'key': 'D-4', 'created': Timestamp('2018-01-04 01:01:01'), 'resolved': NaT,                              'age': Timedelta('76 days 01:01:01'), 'priority': None},
        {'key': 'D-5', 'created': Timestamp('2018-02-05 01:01:01'), 'resolved': Timestamp('2018-02-20 02:02:02'), 'age': Timedelta('15 days 01:01:01'), 'priority': None},
        {'key': 'D-6', 'created': Timestamp('2018-03-06 01:01:01'), 'resolved': NaT,                              'age': Timedelta('15 days 01:01:01'), 'priority': None},
    ]
