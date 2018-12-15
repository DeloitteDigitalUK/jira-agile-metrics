import pytest
from pandas import DataFrame

from .cycletime import CycleTimeCalculator
from .throughput import ThroughputCalculator

from ..utils import extend_dict

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
        'throughput_frequency': 'D',
        'throughput_window': None,
    })

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

    calculator = ThroughputCalculator(query_manager, settings, results)

    data = calculator.run()
    assert list(data.columns) == ['count']
    assert len(data.index) == 0


def test_columns(query_manager, settings, results):
    calculator = ThroughputCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.columns) == ['count']

def test_calculate_throughput(query_manager, settings, results):
    calculator = ThroughputCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [{'count': 2}, {'count': 2}, {'count': 2}]

def test_calculate_throughput_with_wider_window(query_manager, settings, results):

    settings = extend_dict(settings, {
        'throughput_frequency': 'D',
        'throughput_window': 5,
    })

    calculator = ThroughputCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [{'count': 0.0}, {'count': 0.0}, {'count': 2}, {'count': 2}, {'count': 2}]

def test_calculate_throughput_with_narrower_window(query_manager, settings, results):

    settings = extend_dict(settings, {
        'throughput_frequency': 'D',
        'throughput_window': 2,
    })

    calculator = ThroughputCalculator(query_manager, settings, results)

    data = calculator.run()

    assert data.to_dict('records') == [{'count': 2}, {'count': 2}]
