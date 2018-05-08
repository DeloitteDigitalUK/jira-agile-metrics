import pytest
from pandas import DataFrame, Timestamp

from .cycletime import CycleTimeCalculator
from .cfd import CFDCalculator

from ..utils import extend_dict

@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {})

@pytest.fixture
def columns(minimal_cycle_time_columns):
    return minimal_cycle_time_columns

def test_empty(query_manager, settings, columns):
    results = {
        CycleTimeCalculator: DataFrame([], columns=columns)
    }

    calculator = CFDCalculator(query_manager, settings, results)

    data = calculator.run()
    assert len(data.index) == 0

def test_columns(query_manager, settings, minimal_cycle_time_results):
    calculator = CFDCalculator(query_manager, settings, minimal_cycle_time_results)

    data = calculator.run()

    assert list(data.columns) == [
        'Backlog',
        'Committed',
        'Build',
        'Test',
        'Done'
    ]

def test_calculate_cfd(query_manager, settings, minimal_cycle_time_results):
    calculator = CFDCalculator(query_manager, settings, minimal_cycle_time_results)

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
        {'Backlog': 1.0, 'Committed': 0.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
        {'Backlog': 2.0, 'Committed': 0.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
        {'Backlog': 3.0, 'Committed': 2.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
        {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 0.0, 'Done': 0.0},
        {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 1.0, 'Done': 0.0},
        {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 1.0, 'Done': 1.0},
    ]
