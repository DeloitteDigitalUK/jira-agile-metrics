import pytest
from pandas import DataFrame, Timestamp

from .cfd import CFDCalculator
from .burnup import BurnupCalculator

from ..utils import extend_dict

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
    })

@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager

@pytest.fixture
def results(minimal_cfd_results):
    return extend_dict(minimal_cfd_results, {})

def test_empty(query_manager, settings, cfd_columns):
    results = {
        CFDCalculator: DataFrame([], columns=cfd_columns, index=[])
    }

    calculator = BurnupCalculator(query_manager, settings, results)

    data = calculator.run()
    assert len(data.index) == 0

def test_columns(query_manager, settings, results):
    calculator = BurnupCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.columns) == [
        'Backlog',
        'Done'
    ]

def test_calculate_burnup(query_manager, settings, results):
    calculator = BurnupCalculator(query_manager, settings, results)

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
        {'Backlog': 1.0, 'Done': 0.0},
        {'Backlog': 2.0, 'Done': 0.0},
        {'Backlog': 3.0, 'Done': 0.0},
        {'Backlog': 4.0, 'Done': 0.0},
        {'Backlog': 4.0, 'Done': 0.0},
        {'Backlog': 4.0, 'Done': 1.0},
    ]

def test_calculate_burnup_with_different_columns(query_manager, settings, results):
    settings.update({
        'backlog_column': 'Committed',
        'done_column': 'Test'
    })

    calculator = BurnupCalculator(query_manager, settings, results)

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
        {'Committed': 0.0, 'Test': 0.0},
        {'Committed': 0.0, 'Test': 0.0},
        {'Committed': 2.0, 'Test': 0.0},
        {'Committed': 3.0, 'Test': 0.0},
        {'Committed': 3.0, 'Test': 1.0},
        {'Committed': 3.0, 'Test': 1.0},
    ]
