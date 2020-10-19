import math

from pandas import DataFrame, Timedelta
import pytest

from ..utils import extend_dict
from .cycletime import CycleTimeCalculator
from .percentiles import PercentilesCalculator


@pytest.fixture(name="settings")
def fixture_settings(minimal_settings):
    return extend_dict(minimal_settings, {"quantiles": [0.1, 0.5, 0.9]})


@pytest.fixture(name="query_manager")
def fixture_query_manager(minimal_query_manager):
    return minimal_query_manager


@pytest.fixture(name="results")
def fixture_results(large_cycle_time_results):
    return extend_dict(large_cycle_time_results, {})


def test_empty(query_manager, settings, minimal_cycle_time_columns):
    results = {CycleTimeCalculator: DataFrame([], columns=minimal_cycle_time_columns, index=[])}

    calculator = PercentilesCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.index) == [0.1, 0.5, 0.9]
    assert math.isnan(list(data)[0])
    assert math.isnan(list(data)[1])
    assert math.isnan(list(data)[2])


def test_calculate_percentiles(query_manager, settings, results):
    calculator = PercentilesCalculator(query_manager, settings, results)

    data = calculator.run()

    assert list(data.index) == [0.1, 0.5, 0.9]
    assert list(data) == [Timedelta("4 days 12:00:00"), Timedelta("5 days 00:00:00"), Timedelta("5 days 00:00:00")]
