import pytest
from pandas import DataFrame, NaT, Timestamp, Timedelta

from ..conftest import FauxJIRA as JIRA

from ..querymanager import QueryManager
from .cycletime import CycleTimeCalculator
from .cfd import CFDCalculator

cycle_time_columns = [
    'key', 'url', 'issue_type', 'summary', 'status', 'resolution',
    'Estimate', 'Release', 'Team',
    'cycle_time', 'completed_timestamp',
    'Backlog', 'Committed', 'Build', 'Test', 'Done'
]

@pytest.fixture
def settings(basic_settings):
    basic_settings.update({
        
    })
    return basic_settings

@pytest.fixture
def query_manager(basic_fields, settings):
    jira = JIRA(fields=basic_fields, issues=[])
    return QueryManager(jira, settings)

@pytest.fixture
def results():
    return {
        CycleTimeCalculator: DataFrame([{
            'key': 'A-1', 'url': 'https://example.org/browse/A-1', 'issue_type': 'Story', 'summary': 'Just created',
            'status': 'Backlog', 'resolution': None,
            'Estimate': 10, 'Release': 'R3', 'Team': 'Team 1',
            'completed_timestamp': NaT, 'cycle_time': NaT,

            'Backlog': Timestamp('2018-01-01 01:01:01'),
            'Committed': NaT,
            'Build': NaT,
            'Test': NaT,
            'Done': NaT,
        }, {
            'key': 'A-2', 'url': 'https://example.org/browse/A-2', 'issue_type': 'Story', 'summary': 'Started',
            'status': 'Next', 'resolution': None,
            'Estimate': 20, 'Release': 'None', 'Team': 'Team 1',
            'completed_timestamp': NaT, 'cycle_time': NaT,

            'Backlog': Timestamp('2018-01-02 01:01:01'),
            'Committed': Timestamp('2018-01-03 01:01:01'),
            'Build': NaT,
            'Test': NaT,
            'Done': NaT,
        }, {
            'key': 'A-3', 'url': 'https://example.org/browse/A-3', 'summary': 'Completed', 'issue_type': 'Story',
            'status': 'Done', 'resolution': 'Done',
            'Estimate': 30, 'Release': 'None', 'Team': 'Team 1',
            'completed_timestamp': Timestamp('2018-01-06 01:01:01'), 'cycle_time': Timedelta('3 days 00:00:00'),

            'Backlog': Timestamp('2018-01-03 01:01:01'),
            'Committed': Timestamp('2018-01-03 01:01:01'),
            'Build': Timestamp('2018-01-04 01:01:01'),
            'Test': Timestamp('2018-01-05 01:01:01'),
            'Done': Timestamp('2018-01-06 01:01:01'),
        }, {
            'key': 'A-4', 'url': 'https://example.org/browse/A-4', 'summary': 'Moved back', 'issue_type': 'Story',
            'status': 'Next', 'resolution': None,
            'Estimate': 30, 'Release': 'None', 'Team': 'Team 1',
            'completed_timestamp': NaT, 'cycle_time': NaT,

            'Backlog': Timestamp('2018-01-04 01:01:01'),
            'Committed': Timestamp('2018-01-04 01:01:01'),
            'Build': NaT,
            'Test': NaT,
            'Done': NaT,
        }], columns=cycle_time_columns)
    }

def test_empty(query_manager, settings):
    results = {
        CycleTimeCalculator: DataFrame([], columns=cycle_time_columns)
    }

    calculator = CFDCalculator(query_manager, settings, results)

    data = calculator.run()
    assert len(data.index) == 0

def test_columns(query_manager, settings, results):
    calculator = CFDCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.columns) == [
        'Backlog',
        'Committed',
        'Build',
        'Test',
        'Done'
    ]

def test_calculate_cfd(query_manager, settings, results):
    calculator = CFDCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.index) == [
        Timestamp('2018-01-01 00:00:00', freq='D'),
        Timestamp('2018-01-02 00:00:00', freq='D'),
        Timestamp('2018-01-03 00:00:00', freq='D'),
        Timestamp('2018-01-04 00:00:00', freq='D'),
        Timestamp('2018-01-05 00:00:00', freq='D'),
        Timestamp('2018-01-06 00:00:00', freq='D')
    ]

    assert data.to_dict('records') == [
        {'Backlog': 1.0, 'Build': 0.0, 'Committed': 0.0, 'Done': 0.0, 'Test': 0.0},
        {'Backlog': 2.0, 'Build': 0.0, 'Committed': 0.0, 'Done': 0.0, 'Test': 0.0},
        {'Backlog': 3.0, 'Build': 0.0, 'Committed': 2.0, 'Done': 0.0, 'Test': 0.0},
        {'Backlog': 4.0, 'Build': 1.0, 'Committed': 3.0, 'Done': 0.0, 'Test': 0.0},
        {'Backlog': 4.0, 'Build': 1.0, 'Committed': 3.0, 'Done': 0.0, 'Test': 1.0},
        {'Backlog': 4.0, 'Build': 1.0, 'Committed': 3.0, 'Done': 1.0, 'Test': 1.0},
    ]
