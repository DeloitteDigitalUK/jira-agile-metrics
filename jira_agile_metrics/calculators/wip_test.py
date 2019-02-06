import pytest
import datetime
from pandas import DataFrame, Timestamp, date_range

from .cfd import CFDCalculator
from .wip import WIPChartCalculator

from ..utils import extend_dict

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
    })

@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager

@pytest.fixture
def results(query_manager, settings, large_cycle_time_results):
    
    # CFD data frame and WIP
    #
    #              Backlog  Committed  Build  Test  Done
    # 2018-01-01     16.0        0.0    0.0   0.0   0.0     -->  0
    # 2018-01-02     17.0        9.0    0.0   0.0   0.0     -->  9
    # 2018-01-03     18.0       13.0    8.0   0.0   0.0     --> 13
    # 2018-01-04     18.0       14.0   10.0   3.0   0.0     --> 14
    # 2018-01-05     18.0       15.0   11.0   8.0   0.0     --> 15
    # 2018-01-06     18.0       15.0   12.0   8.0   0.0     --> 15
    # 2018-01-07     18.0       15.0   12.0   8.0   2.0     --> 13
    # 2018-01-08     18.0       15.0   12.0   9.0   4.0     --> 11
    # 2018-01-09     18.0       15.0   12.0   9.0   6.0     -->  9
    #

    return extend_dict(large_cycle_time_results, {
        CFDCalculator: CFDCalculator(query_manager, settings, large_cycle_time_results).run()
    })

def test_empty(query_manager, settings, minimal_cycle_time_columns):
    results = {
        CFDCalculator: DataFrame([], columns=['Backlog', 'Committed', 'Build', 'Test', 'Done'], index=date_range(start=datetime.date(2018, 1, 1), periods=0, freq='D'))
    }

    calculator = WIPChartCalculator(query_manager, settings, results)

    data = calculator.run()
    assert list(data.columns) == ['wip']
    assert len(data.index) == 0


def test_columns(query_manager, settings, results):
    calculator = WIPChartCalculator(query_manager, settings, results)

    data = calculator.run()
    assert list(data.columns) == ['wip']

def test_calculate_wip(query_manager, settings, results):
    calculator = WIPChartCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.index) == [
        Timestamp('2018-01-01 00:00:00', freq='D'),
        Timestamp('2018-01-02 00:00:00', freq='D'),
        Timestamp('2018-01-03 00:00:00', freq='D'),
        Timestamp('2018-01-04 00:00:00', freq='D'),
        Timestamp('2018-01-05 00:00:00', freq='D'),
        Timestamp('2018-01-06 00:00:00', freq='D'),
        Timestamp('2018-01-07 00:00:00', freq='D'),
        Timestamp('2018-01-08 00:00:00', freq='D'),
        Timestamp('2018-01-09 00:00:00', freq='D')
    ]

    assert data.to_dict('records') == [
        {'wip':  0.0},
        {'wip':  9.0},
        {'wip': 13.0},
        {'wip': 14.0},
        {'wip': 15.0},
        {'wip': 15.0},
        {'wip': 13.0},
        {'wip': 11.0},
        {'wip':  9.0},
    ]

def test_calculate_wip_different_columns(query_manager, settings, results):

    settings.update({
        'committed_column': 'Build',
        'done_column': 'Test',
    })

    calculator = WIPChartCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.index) == [
        Timestamp('2018-01-01 00:00:00', freq='D'),
        Timestamp('2018-01-02 00:00:00', freq='D'),
        Timestamp('2018-01-03 00:00:00', freq='D'),
        Timestamp('2018-01-04 00:00:00', freq='D'),
        Timestamp('2018-01-05 00:00:00', freq='D'),
        Timestamp('2018-01-06 00:00:00', freq='D'),
        Timestamp('2018-01-07 00:00:00', freq='D'),
        Timestamp('2018-01-08 00:00:00', freq='D'),
        Timestamp('2018-01-09 00:00:00', freq='D')
    ]

    assert data.to_dict('records') == [
        {'wip': 0.0},
        {'wip': 0.0},
        {'wip': 8.0},
        {'wip': 7.0},
        {'wip': 3.0},
        {'wip': 4.0},
        {'wip': 4.0},
        {'wip': 3.0},
        {'wip': 3.0},
    ]
