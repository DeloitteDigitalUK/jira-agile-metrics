import pytest
from pandas import DataFrame

from .cycletime import CycleTimeCalculator
from .histogram import HistogramCalculator

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

    calculator = HistogramCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.index) == [
        '0.0 to 0.1',
        '0.1 to 0.2',
        '0.2 to 0.3',
        '0.3 to 0.4',
        '0.4 to 0.5',
        '0.5 to 0.6',
        '0.6 to 0.7',
        '0.7 to 0.8',
        '0.8 to 0.9',
        '0.9 to 1.0'
    ]

    assert list(data) == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

def test_calculate_histogram(query_manager, settings, results):
    calculator = HistogramCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.index) == [
        '4.0 to 4.1',
        '4.1 to 4.2',
        '4.2 to 4.3',
        '4.3 to 4.4',
        '4.4 to 4.5',
        '4.5 to 4.6',
        '4.6 to 4.7',
        '4.7 to 4.8',
        '4.8 to 4.9',
        '4.9 to 5.0'
    ]
    assert list(data) == [1, 0, 0, 0, 0, 0, 0, 0, 0, 5]
