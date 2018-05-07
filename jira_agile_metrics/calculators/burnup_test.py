import pytest
from pandas import DataFrame, Timestamp

from ..conftest import FauxJIRA as JIRA

from ..querymanager import QueryManager
from .cfd import CFDCalculator
from .burnup import BurnupCalculator

cfd_columns = [
    'Backlog',
    'Committed',
    'Build',
    'Test',
    'Done'
]

cfd_index = [
    Timestamp('2018-01-01 00:00:00', freq='D'),
    Timestamp('2018-01-02 00:00:00', freq='D'),
    Timestamp('2018-01-03 00:00:00', freq='D'),
    Timestamp('2018-01-04 00:00:00', freq='D'),
    Timestamp('2018-01-05 00:00:00', freq='D'),
    Timestamp('2018-01-06 00:00:00', freq='D')
]

@pytest.fixture
def settings(basic_settings):
    basic_settings.update({
        'backlog_column': None,
        'done_column': None
    })
    return basic_settings

@pytest.fixture
def query_manager(basic_fields, settings):
    jira = JIRA(fields=basic_fields, issues=[])
    return QueryManager(jira, settings)

@pytest.fixture
def results():
    return {
        CFDCalculator: DataFrame([
            {'Backlog': 1.0, 'Committed': 0.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
            {'Backlog': 2.0, 'Committed': 0.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
            {'Backlog': 3.0, 'Committed': 2.0, 'Build': 0.0, 'Test': 0.0, 'Done': 0.0},
            {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 0.0, 'Done': 0.0},
            {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 1.0, 'Done': 0.0},
            {'Backlog': 4.0, 'Committed': 3.0, 'Build': 1.0, 'Test': 1.0, 'Done': 1.0},
        ], columns=cfd_columns, index=cfd_index)
    }

def test_empty(query_manager, settings):
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

def test_calculate_cfd(query_manager, settings, results):
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

def test_calculate_cfd_with_different_columns(query_manager, settings, results):
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
