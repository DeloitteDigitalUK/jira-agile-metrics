import pytest
from pandas import Timestamp

from ..conftest import (
    FauxJIRA as JIRA,
    FauxIssue as Issue,
    FauxFieldValue as Value,
    FauxChange as Change
)

from ..utils import extend_dict

from ..querymanager import QueryManager
from .waste import WasteCalculator

@pytest.fixture
def fields(minimal_fields):
    return minimal_fields + []

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
        'waste_query': 'issueType = Story AND resolution IN (Withdrawn, Invalid)',
        'waste_window': 3,
        'waste_frequency': '2W-WED',
        'waste_chart': 'waste.png',
        'waste_chart_title': 'Waste',
    })

@pytest.fixture
def jira(fields):
    return JIRA(fields=fields, issues=[
        Issue("A-1",
            summary="Withdrawn from QA",
            issuetype=Value("Story", "story"),
            status=Value("Done", "done"),
            created="2018-01-03 01:01:01",
            resolution=Value("Withdrawn", "withdrawn"),
            resolutiondate="2018-01-06 02:02:02",
            changes=[
                Change("2018-01-03 02:02:02", [("status", "Backlog", "Next",)]),
                Change("2018-01-04 02:02:02", [("status", "Next", "Build",)]),
                Change("2018-01-05 02:02:02", [("status", "Build", "QA",)]),
                Change("2018-01-06 02:02:02", [("status", "QA", "Done",)]),
            ],
        ),
        Issue("A-2",
            summary="Withdrawn from Next",
            issuetype=Value("Story", "story"),
            status=Value("Done", "done"),
            created="2018-01-03 01:01:01",
            resolution=Value("Withdrawn", "withdrawn"),
            resolutiondate="2018-01-07 02:02:02",
            changes=[
                Change("2018-01-03 02:02:02", [("status", "Backlog", "Next",)]),
                Change("2018-01-07 02:02:02", [("status", "Next", "Done",)]),
            ],
        ),
        Issue("A-3",
            summary="Withdrawn from Done",
            issuetype=Value("Story", "story"),
            status=Value("Done", "done"),
            created="2018-01-03 01:01:01",
            resolution=Value("Withdrawn", "withdrawn"),
            resolutiondate="2018-01-08 02:02:02",
            changes=[
                Change("2018-01-03 02:02:02", [("status", "Backlog", "Next",)]),
                Change("2018-01-04 02:02:02", [("status", "Next", "Build",)]),
                Change("2018-01-05 02:02:02", [("status", "Build", "QA",)]),
                Change("2018-01-06 02:02:02", [("status", "QA", "Done",)]),
                Change("2018-01-08 02:02:02", [("status", "Done", "Done",)]),
            ],
        ),
        Issue("A-4",
            summary="Withdrawn from Backlog",
            issuetype=Value("Story", "story"),
            status=Value("Done", "done"),
            created="2018-01-03 01:01:01",
            resolution=Value("Withdrawn", "withdrawn"),
            resolutiondate="2018-01-09 02:02:02",
            changes=[
                Change("2018-01-09 02:02:02", [("status", "Backlog", "Done",)]),
            ],
        ),
        Issue("A-5",
            summary="Unresolved",
            issuetype=Value("Story", "story"),
            status=Value("Done", "done"),
            created="2018-01-03 01:01:01",
            resolution=None,
            resolutiondate=None,
            changes=[
                Change("2018-01-03 02:02:02", [("status", "Backlog", "Next",)]),
                Change("2018-01-04 02:02:02", [("status", "Next", "Build",)]),
                Change("2018-01-05 02:02:02", [("status", "Build", "QA",)]),
                Change("2018-01-06 02:02:02", [("status", "QA", "Done",)]),
            ],
        ),
        Issue("A-6",
            summary="Unmapped state",
            issuetype=Value("Story", "story"),
            status=Value("Done", "done"),
            created="2018-01-03 01:01:01",
            resolution=Value("Withdrawn", "withdrawn"),
            resolutiondate="2018-01-06 02:02:02",
            changes=[
                Change("2018-01-03 02:02:02", [("status", "Backlog", "Next",)]),
                Change("2018-01-04 02:02:02", [("status", "Next", "Build",)]),
                Change("2018-01-05 02:02:02", [("status", "Build", "foobar",)]),
                Change("2018-01-06 02:02:02", [("status", "foobar", "Done",)]),
            ],
        ),
        Issue("A-7",
            summary="No changes",
            issuetype=Value("Story", "story"),
            status=Value("Done", "done"),
            created="2018-01-06 02:02:02",
            resolution=Value("Withdrawn", "withdrawn"),
            resolutiondate="2018-01-06 02:02:02",
            changes=[],
        ),
    ])

def test_no_query(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    settings = extend_dict(settings, {
        'waste_query': None
    })
    calculator = WasteCalculator(query_manager, settings, results)

    data = calculator.run()
    assert data is None

def test_columns(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = WasteCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.columns) == ['key', 'last_status', 'resolution', 'withdrawn_date']

def test_empty(fields, settings):
    jira = JIRA(fields=fields, issues=[])
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = WasteCalculator(query_manager, settings, results)

    data = calculator.run()

    assert len(data.index) == 0

def test_query(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = WasteCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'A-1', 'last_status': 'Test',      'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-06 02:02:02')},
        {'key': 'A-2', 'last_status': 'Committed', 'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-07 02:02:02')},
        {'key': 'A-6', 'last_status': 'foobar',    'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-06 02:02:02')},
        {'key': 'A-7', 'last_status': None,        'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-06 02:02:02')},
    ]

def test_different_backlog_column(jira, settings):
    settings = extend_dict(settings, {
        'backlog_column': 'Committed'
    })

    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = WasteCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'A-1', 'last_status': 'Test',      'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-06 02:02:02')},
        {'key': 'A-4', 'last_status': 'Backlog',   'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-09 02:02:02')},
        {'key': 'A-6', 'last_status': 'foobar',    'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-06 02:02:02')},
        {'key': 'A-7', 'last_status': None,        'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-06 02:02:02')},
    ]

def test_different_done_column(jira, settings):
    settings = extend_dict(settings, {
        'done_column': 'Test'
    })

    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = WasteCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'A-2', 'last_status': 'Committed', 'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-07 02:02:02')},
        {'key': 'A-3', 'last_status': 'Done',      'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-08 02:02:02')},
        {'key': 'A-6', 'last_status': 'foobar',    'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-06 02:02:02')},
        {'key': 'A-7', 'last_status': None,        'resolution': 'Withdrawn', 'withdrawn_date': Timestamp('2018-01-06 02:02:02')},
    ]
