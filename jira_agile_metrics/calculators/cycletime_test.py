import pytest
import datetime
from pandas import NaT, Timestamp, Timedelta

from ..conftest import (
    FauxJIRA as JIRA,
    FauxIssue as Issue,
    FauxChange as Change,
    FauxFieldValue as Value
)

from ..querymanager import QueryManager
from .cycletime import CycleTimeCalculator

@pytest.fixture
def jira(custom_fields):
    return JIRA(fields=custom_fields, issues=[
        Issue("A-1",
            summary="Just created",
            issuetype=Value("Story", "story"),
            status=Value("Backlog", "backlog"),
            resolution=None,
            resolutiondate=None,
            created="2018-01-01 01:01:01",
            customfield_001="Team 1",
            customfield_002=Value(None, 10),
            customfield_003=Value(None, ["R2", "R3", "R4"]),
            customfield_100=None,
            changes=[],
        ),
        Issue("A-2",
            summary="Started",
            issuetype=Value("Story", "story"),
            status=Value("Next", "next"),
            resolution=None,
            resolutiondate=None,
            created="2018-01-02 01:01:01",
            customfield_001="Team 1",
            customfield_002=Value(None, 20),
            customfield_003=Value(None, []),
            customfield_100=None,
            changes=[
                Change("2018-01-02 10:01:01", [("Flagged", None, "Impediment")]),
                Change("2018-01-03 01:00:00", [("Flagged", "Impediment", "")]),  # blocked 1 day in the backlog (doesn't count towards blocked days)
                Change("2018-01-03 01:01:01", [("status", "Backlog", "Next",)]),
                Change("2018-01-04 10:01:01", [("Flagged", "", "Impediment")]),
                Change("2018-01-05 08:01:01", [("Flagged", "Impediment", "")]),  # was blocked 1 day
                Change("2018-01-08 10:01:01", [("Flagged", "", "Impediment")]),  # stays blocked until today
            ],
        ),
        Issue("A-3",
            summary="Completed",
            issuetype=Value("Story", "story"),
            status=Value("Done", "done"),
            resolution=Value("Done", "Done"),
            resolutiondate="2018-01-06 01:01:01",
            created="2018-01-03 01:01:01",
            customfield_001="Team 1",
            customfield_002=Value(None, 30),
            customfield_003=Value(None, []),
            customfield_100=None,
            changes=[
                Change("2018-01-03 01:01:01", [("status", "Backlog", "Next",)]),
                Change("2018-01-04 01:01:01", [("status", "Next", "Build",)]),
                Change("2018-01-04 10:01:01", [("Flagged", None, "Impediment")]),  # should clear two days later when issue resolved
                Change("2018-01-05 01:01:01", [("status", "Build", "QA",)]),
                Change("2018-01-06 01:01:01", [("status", "QA", "Done",)]),
            ],
        ),
        Issue("A-4",
            summary="Moved back",
            issuetype=Value("Story", "story"),
            status=Value("Next", "next"),
            resolution=None,
            resolutiondate=None,
            created="2018-01-04 01:01:01",
            customfield_001="Team 1",
            customfield_002=Value(None, 30),
            customfield_003=Value(None, []),
            customfield_100=None,
            changes=[
                Change("2018-01-04 01:01:01", [("status", "Backlog", "Next",)]),
                Change("2018-01-05 01:01:01", [("status", "Next", "Build",)]),
                Change("2018-01-06 01:01:01", [("status", "Build", "Next",)]),
                Change("2018-01-07 01:01:01", [("Flagged", None, "Awaiting input")]),
                Change("2018-01-10 10:01:01", [("Flagged", "Awaiting input", "")]),  # blocked 3 days
            ],
        ),
    ])

@pytest.fixture
def settings(custom_settings):
    return custom_settings

def test_columns(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = CycleTimeCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.columns) == [
        'key',
        'url',
        'issue_type',
        'summary',
        'status',
        'resolution',

        'Estimate',
        'Release',
        'Team',
        
        'cycle_time',
        'completed_timestamp',
        'blocked_days',
        'impediments',
        
        'Backlog',
        'Committed',
        'Build',
        'Test',
        'Done'
    ]

def test_empty(custom_fields, settings):
    jira = JIRA(fields=custom_fields, issues=[])
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = CycleTimeCalculator(query_manager, settings, results)

    data = calculator.run()

    assert len(data.index) == 0

def test_movement(jira, settings):
    query_manager = QueryManager(jira, settings)
    results = {}
    calculator = CycleTimeCalculator(query_manager, settings, results)

    data = calculator.run(now=datetime.datetime(2018, 1, 10, 15, 37, 0))

    assert data.to_dict('records') == [{
        'key': 'A-1',
        'url': 'https://example.org/browse/A-1',
        'issue_type': 'Story',
        'summary': 'Just created',
        'status': 'Backlog',
        'resolution': None,

        'Estimate': 10,
        'Release': 'R3',
        'Team': 'Team 1',

        'completed_timestamp': NaT,
        'cycle_time': NaT,
        'blocked_days': 0,
        'impediments': [],

        'Backlog': Timestamp('2018-01-01 01:01:01'),
        'Committed': NaT,
        'Build': NaT,
        'Test': NaT,
        'Done': NaT,
    }, {
        'key': 'A-2',
        'url': 'https://example.org/browse/A-2',
        'issue_type': 'Story',
        'summary': 'Started',
        'status': 'Next',
        'resolution': None,

        'Estimate': 20,
        'Release': 'None',
        'Team': 'Team 1',

        'completed_timestamp': NaT,
        'cycle_time': NaT,
        'blocked_days': 3,
        'impediments': [
            {'start': datetime.date(2018, 1, 2), 'end': datetime.date(2018, 1, 3), 'status': 'Backlog', 'flag': 'Impediment'},  # doesn't count towards blocked_days
            {'start': datetime.date(2018, 1, 4), 'end': datetime.date(2018, 1, 5), 'status': 'Committed', 'flag': 'Impediment'},
            {'start': datetime.date(2018, 1, 8), 'end': None, 'status': 'Committed', 'flag': 'Impediment'},
        ],

        'Backlog': Timestamp('2018-01-02 01:01:01'),
        'Committed': Timestamp('2018-01-03 01:01:01'),
        'Build': NaT,
        'Test': NaT,
        'Done': NaT,
    }, {
        'key': 'A-3',
        'url': 'https://example.org/browse/A-3',
        'summary': 'Completed',
        'issue_type': 'Story',
        'status': 'Done',
        'resolution': 'Done',

        'Estimate': 30,
        'Release': 'None',
        'Team': 'Team 1',

        'completed_timestamp': Timestamp('2018-01-06 01:01:01'),
        'cycle_time': Timedelta('3 days 00:00:00'),
        'blocked_days': 2,
        'impediments': [{'start': datetime.date(2018, 1, 4), 'end': datetime.date(2018, 1, 6), 'status': 'Build', 'flag': 'Impediment'}],

        'Backlog': Timestamp('2018-01-03 01:01:01'),
        'Committed': Timestamp('2018-01-03 01:01:01'),
        'Build': Timestamp('2018-01-04 01:01:01'),
        'Test': Timestamp('2018-01-05 01:01:01'),
        'Done': Timestamp('2018-01-06 01:01:01'),
    }, {
        'key': 'A-4',
        'url': 'https://example.org/browse/A-4',
        'summary': 'Moved back',
        'issue_type': 'Story',
        'status': 'Next',
        'resolution': None,

        'Estimate': 30,
        'Release': 'None',
        'Team': 'Team 1',
        
        'completed_timestamp': NaT,
        'cycle_time': NaT,
        'blocked_days': 3,
        'impediments': [{'start': datetime.date(2018, 1, 7), 'end': datetime.date(2018, 1, 10), 'status': 'Committed', 'flag': 'Awaiting input'}],

        'Backlog': Timestamp('2018-01-04 01:01:01'),
        'Committed': Timestamp('2018-01-04 01:01:01'),
        'Build': NaT,
        'Test': NaT,
        'Done': NaT,
    }]
