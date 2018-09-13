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
        '0.0 to 1.0',
        '1.0 to 2.0',
        '2.0 to 3.0',
        '3.0 to 4.0',
        '4.0 to 5.0',
        '5.0 to 6.0',
        '6.0 to 7.0',
        '7.0 to 8.0',
        '8.0 to 9.0',
        '9.0 to 10.0'
    ]

    assert list(data) == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

def test_calculate_histogram(query_manager, settings, results):
    calculator = HistogramCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.index) == [
        '0.0 to 1.0',
        '1.0 to 2.0',
        '2.0 to 3.0',
        '3.0 to 4.0',
        '4.0 to 5.0',
        '5.0 to 6.0'
    ]
    assert list(data) == [0, 0, 0, 0, 1, 5]
