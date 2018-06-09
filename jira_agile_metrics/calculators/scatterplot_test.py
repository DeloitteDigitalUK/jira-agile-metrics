import pytest
from pandas import DataFrame, Timestamp

from .cycletime import CycleTimeCalculator
from .scatterplot import ScatterplotCalculator

from ..utils import extend_dict

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {})

@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager

@pytest.fixture
def results(large_cycle_time_results):
    return extend_dict(large_cycle_time_results, {})

def test_empty(query_manager, settings, minimal_cycle_time_columns):
    results = {
        CycleTimeCalculator: DataFrame([], columns=minimal_cycle_time_columns, index=[])
    }

    calculator = ScatterplotCalculator(query_manager, settings, results)

    data = calculator.run()
    assert list(data.columns) == [
        'completed_date',
        'cycle_time',
        'blocked_days',
        'key',
        'url',
        'issue_type',
        'summary',
        'status',
        'resolution',
        'Backlog',
        'Committed',
        'Build',
        'Test',
        'Done'
    ]
    assert len(data.index) == 0


def test_columns(query_manager, settings, results):
    calculator = ScatterplotCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.columns) == [
        'completed_date',
        'cycle_time',
        'blocked_days',
        'key',
        'url',
        'issue_type',
        'summary',
        'status',
        'resolution',
        'Backlog',
        'Committed',
        'Build',
        'Test',
        'Done'
    ]

def test_calculate_scatterplot(query_manager, settings, results):
    calculator = ScatterplotCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data[['key', 'completed_date', 'cycle_time']].to_dict('records') == [
        {'key': 'A-13', 'completed_date': Timestamp('2018-01-07 01:01:01'), 'cycle_time': 5.0},
        {'key': 'A-14', 'completed_date': Timestamp('2018-01-07 01:01:01'), 'cycle_time': 5.0},
        {'key': 'A-15', 'completed_date': Timestamp('2018-01-08 01:01:01'), 'cycle_time': 5.0},
        {'key': 'A-16', 'completed_date': Timestamp('2018-01-08 01:01:01'), 'cycle_time': 5.0},
        {'key': 'A-17', 'completed_date': Timestamp('2018-01-09 01:01:01'), 'cycle_time': 5.0},
        {'key': 'A-18', 'completed_date': Timestamp('2018-01-09 01:01:01'), 'cycle_time': 4.0},
    ]
