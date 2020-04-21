import pytest
import datetime
from pandas import DataFrame

from .cycletime import CycleTimeCalculator
from .ageingwip import AgeingWIPChartCalculator

from ..utils import extend_dict

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
        'ageing_wip_chart': 'ageingwip.png'  # without a file to write the calculator will stop
    })

@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager

@pytest.fixture
def results(large_cycle_time_results):
    return extend_dict(large_cycle_time_results, {})

@pytest.fixture
def today():
    return datetime.date(2018, 1, 10)

def test_empty(query_manager, settings, minimal_cycle_time_columns, today):
    results = {
        CycleTimeCalculator: DataFrame([], columns=minimal_cycle_time_columns, index=[])
    }

    calculator = AgeingWIPChartCalculator(query_manager, settings, results)

    data = calculator.run(today)
    assert list(data.columns) == [
        'key',
        'summary',
        'status',
        'age',
        'Committed',
        'Build',
        'Test'
    ]
    assert len(data.index) == 0


def test_columns(query_manager, settings, results, today):
    calculator = AgeingWIPChartCalculator(query_manager, settings, results)

    data = calculator.run(today)

    assert list(data.columns) == [
        'key',
        'summary',
        'status',
        'age',
        'Committed',
        'Build',
        'Test'
    ]

def test_calculate_ageing_wip(query_manager, settings, results, today):
    calculator = AgeingWIPChartCalculator(query_manager, settings, results)

    data = calculator.run(today)

    assert data[['key', 'status', 'age']].to_dict('records') == [
        {'key': 'A-4', 'status': 'Committed', 'age': 8.0},
        {'key': 'A-5', 'status': 'Committed', 'age': 7.0},
        {'key': 'A-6', 'status': 'Committed', 'age': 7.0},
        {'key': 'A-7', 'status': 'Build', 'age': 8.0},
        {'key': 'A-8', 'status': 'Build', 'age': 8.0},
        {'key': 'A-9', 'status': 'Build', 'age': 8.0},
        {'key': 'A-10', 'status': 'Test', 'age': 8.0},
        {'key': 'A-11', 'status': 'Test', 'age': 8.0},
        {'key': 'A-12', 'status': 'Test', 'age': 8.0},
    ]

def test_calculate_ageing_wip_with_different_columns(query_manager, settings, results, today):
    settings.update({
        'committed_column': 'Committed',
        'final_column': 'Build',
        'done_column': 'Test',
    })

    calculator = AgeingWIPChartCalculator(query_manager, settings, results)

    data = calculator.run(today)

    assert data[['key', 'status', 'age']].to_dict('records') == [
        {'key': 'A-4', 'status': 'Committed', 'age': 8.0},
        {'key': 'A-5', 'status': 'Committed', 'age': 7.0},
        {'key': 'A-6', 'status': 'Committed', 'age': 7.0},
        {'key': 'A-7', 'status': 'Build', 'age': 8.0},
        {'key': 'A-8', 'status': 'Build', 'age': 8.0},
        {'key': 'A-9', 'status': 'Build', 'age': 8.0}
    ]
