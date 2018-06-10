import pytest
import datetime
from pandas import DataFrame, DatetimeIndex, Timestamp

from .cfd import CFDCalculator
from .netflow import NetFlowChartCalculator

from ..utils import extend_dict

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
        'net_flow_frequency': 'D'
    })

@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager

@pytest.fixture
def results(query_manager, settings, large_cycle_time_results):
    
    # CFD data frame and net flow:
    #
    #              Backlog  Committed  Build  Test  Done
    # 2018-01-01     16.0        0.0    0.0   0.0   0.0     -->  0
    # 2018-01-02     17.0        9.0    0.0   0.0   0.0     --> +9
    # 2018-01-03     18.0       13.0    8.0   0.0   0.0     --> +4
    # 2018-01-04     18.0       14.0   10.0   3.0   0.0     --> +1
    # 2018-01-05     18.0       15.0   11.0   8.0   0.0     --> +1
    # 2018-01-06     18.0       15.0   12.0   8.0   0.0     -->  0
    # 2018-01-07     18.0       15.0   12.0   8.0   2.0     --> -2
    # 2018-01-08     18.0       15.0   12.0   9.0   4.0     --> -4
    # 2018-01-09     18.0       15.0   12.0   9.0   6.0     --> -6
    #

    return extend_dict(large_cycle_time_results, {
        CFDCalculator: CFDCalculator(query_manager, settings, large_cycle_time_results).run()
    })

def test_empty(query_manager, settings, minimal_cycle_time_columns):
    results = {
        CFDCalculator: DataFrame([], columns=['Backlog', 'Committed', 'Build', 'Test', 'Done'], index=DatetimeIndex(start=datetime.date(2018, 1, 1), periods=0, freq='D'))
    }

    calculator = NetFlowChartCalculator(query_manager, settings, results)

    data = calculator.run()
    assert list(data.columns) == ['Committed', 'Done', 'arrivals', 'departures', 'net_flow', 'positive']
    assert len(data.index) == 0


def test_columns(query_manager, settings, results):
    calculator = NetFlowChartCalculator(query_manager, settings, results)

    data = calculator.run()
    assert list(data.columns) == ['Committed', 'Done', 'arrivals', 'departures', 'net_flow', 'positive']

def test_calculate_net_flow(query_manager, settings, results):
    calculator = NetFlowChartCalculator(query_manager, settings, results)

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

    assert data[['arrivals', 'departures', 'net_flow', 'positive']].to_dict('records') == [
        {'arrivals': 0.0, 'departures': 0.0, 'net_flow':  0.0, 'positive': True},
        {'arrivals': 9.0, 'departures': 0.0, 'net_flow':  9.0, 'positive': True},
        {'arrivals': 4.0, 'departures': 0.0, 'net_flow':  4.0, 'positive': True},
        {'arrivals': 1.0, 'departures': 0.0, 'net_flow':  1.0, 'positive': True},
        {'arrivals': 1.0, 'departures': 0.0, 'net_flow':  1.0, 'positive': True},
        {'arrivals': 0.0, 'departures': 0.0, 'net_flow':  0.0, 'positive': True},
        {'arrivals': 0.0, 'departures': 2.0, 'net_flow': -2.0, 'positive': False},
        {'arrivals': 0.0, 'departures': 2.0, 'net_flow': -2.0, 'positive': False},
        {'arrivals': 0.0, 'departures': 2.0, 'net_flow': -2.0, 'positive': False},
    ]

def test_calculate_net_flow_different_columns(query_manager, settings, results):

    settings.update({
        'committed_column': 'Build',
        'done_column': 'Test',
    })

    calculator = NetFlowChartCalculator(query_manager, settings, results)

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

    assert data[['arrivals', 'departures', 'net_flow', 'positive']].to_dict('records') == [
        {'arrivals': 0.0, 'departures': 0.0, 'net_flow':  0.0, 'positive': True},
        {'arrivals': 0.0, 'departures': 0.0, 'net_flow':  0.0, 'positive': True},
        {'arrivals': 8.0, 'departures': 0.0, 'net_flow':  8.0, 'positive': True},
        {'arrivals': 2.0, 'departures': 3.0, 'net_flow': -1.0, 'positive': False},
        {'arrivals': 1.0, 'departures': 5.0, 'net_flow': -4.0, 'positive': False},
        {'arrivals': 1.0, 'departures': 0.0, 'net_flow':  1.0, 'positive': True},
        {'arrivals': 0.0, 'departures': 0.0, 'net_flow':  0.0, 'positive': True},
        {'arrivals': 0.0, 'departures': 1.0, 'net_flow': -1.0, 'positive': False},
        {'arrivals': 0.0, 'departures': 0.0, 'net_flow':  0.0, 'positive': True},
    ]
