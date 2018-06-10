import pytest
from datetime import date
from pandas import DataFrame, NaT, Timestamp

from .cycletime import CycleTimeCalculator
from .impediments import ImpedimentsCalculator

from ..utils import extend_dict

from ..conftest import _issues

def _ts(datestring, timestring="00:00:00", freq=None):
    return Timestamp('%s %s' % (datestring, timestring,), freq=freq)

@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
        'impediments_data': 'impediments.csv',
        'impediments_chart': 'impediments.png',
        'impediments_days_chart': 'impediments-days.png',
    })

@pytest.fixture
def columns(minimal_cycle_time_columns):
    return minimal_cycle_time_columns

@pytest.fixture
def cycle_time_results(minimal_cycle_time_columns):
    """A results dict mimicing a minimal result from the CycleTimeCalculator.
    """
    return {
        CycleTimeCalculator: DataFrame(_issues([
            dict(Backlog=_ts('2018-01-01'), Committed=NaT, Build=NaT, Test=NaT, Done=NaT, blocked_days=0, impediments=[]),
            dict(Backlog=_ts('2018-01-02'), Committed=_ts('2018-01-03'), Build=NaT, Test=NaT, Done=NaT, blocked_days=4, impediments=[
                {'start': date(2018, 1, 5),  'end': date(2018, 1, 7),  'status': 'Backlog'},      # ignored because it was blocked in backlog
                {'start': date(2018, 1, 10), 'end': date(2018, 1, 12), 'status': 'Committed'},  # included
            ]),
            dict(Backlog=_ts('2018-01-03'), Committed=_ts('2018-01-03'), Build=_ts('2018-01-04'), Test=_ts('2018-01-05'), Done=_ts('2018-01-06'), blocked_days=4, impediments=[
                {'start': date(2018, 1, 4), 'end': date(2018, 1, 5),  'status': 'Build'},  # included
                {'start': date(2018, 1, 7), 'end': date(2018, 1, 10), 'status': 'Done'},  # ignored because it was blocked in done
            ]),
            dict(Backlog=_ts('2018-01-04'), Committed=_ts('2018-01-04'), Build=NaT, Test=NaT, Done=NaT, blocked_days=100, impediments=[
                {'start': date(2018, 1, 5), 'end': None, 'status': 'Committed'},  # open ended, still included
            ]),
        ]), columns=minimal_cycle_time_columns)
    }
    
def test_only_runs_if_charts_set(query_manager, settings, cycle_time_results):
    test_settings = extend_dict(settings, {
        'impediments_data': None,
        'impediments_chart': None,
        'impediments_days_chart': None,
    })

    calculator = ImpedimentsCalculator(query_manager, test_settings, cycle_time_results)
    data = calculator.run()
    assert data is None

    test_settings = extend_dict(settings, {
        'impediments_data': 'impediments.csv',
        'impediments_chart': None,
        'impediments_days_chart': None,
    })

    calculator = ImpedimentsCalculator(query_manager, test_settings, cycle_time_results)
    data = calculator.run()
    assert data is not None

    test_settings = extend_dict(settings, {
        'impediments_data': None,
        'impediments_chart': 'impediments.png',
        'impediments_days_chart': None,
    })

    calculator = ImpedimentsCalculator(query_manager, test_settings, cycle_time_results)
    data = calculator.run()
    assert data is not None

    test_settings = extend_dict(settings, {
        'impediments_data': None,
        'impediments_chart': None,
        'impediments_days_chart': 'days.png',
    })

    calculator = ImpedimentsCalculator(query_manager, test_settings, cycle_time_results)
    data = calculator.run()
    assert data is not None

def test_empty(query_manager, settings, columns):
    results = {
        CycleTimeCalculator: DataFrame([], columns=columns)
    }

    calculator = ImpedimentsCalculator(query_manager, settings, results)

    data = calculator.run()
    assert len(data.index) == 0

def test_columns(query_manager, settings, cycle_time_results):
    calculator = ImpedimentsCalculator(query_manager, settings, cycle_time_results)

    data = calculator.run()

    assert list(data.columns) == ['key', 'status', 'start', 'end']

def test_calculate_impediments(query_manager, settings, cycle_time_results):
    calculator = ImpedimentsCalculator(query_manager, settings, cycle_time_results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'A-2', 'status': 'Committed', 'start': _ts('2018-01-10'), 'end': _ts('2018-01-12')},
        {'key': 'A-3', 'status': 'Build',     'start': _ts('2018-01-04'), 'end': _ts('2018-01-05')},
        {'key': 'A-4', 'status': 'Committed', 'start': _ts('2018-01-05'), 'end': NaT},
    ]

def test_different_backlog_column(query_manager, settings, cycle_time_results):
    settings = extend_dict(settings, {
        'backlog_column': 'Committed',
    })
    calculator = ImpedimentsCalculator(query_manager, settings, cycle_time_results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'A-2', 'status': 'Backlog', 'start': _ts('2018-01-05'), 'end': _ts('2018-01-07')},
        {'key': 'A-3', 'status': 'Build',   'start': _ts('2018-01-04'), 'end': _ts('2018-01-05')},
    ]

def test_different_done_column(query_manager, settings, cycle_time_results):
    settings = extend_dict(settings, {
        'done_column': 'Build',
    })
    calculator = ImpedimentsCalculator(query_manager, settings, cycle_time_results)

    data = calculator.run()

    assert data.to_dict('records') == [
        {'key': 'A-2', 'status': 'Committed', 'start': _ts('2018-01-10'), 'end': _ts('2018-01-12')},
        {'key': 'A-3', 'status': 'Done',      'start': _ts('2018-01-07'), 'end': _ts('2018-01-10')},
        {'key': 'A-4', 'status': 'Committed', 'start': _ts('2018-01-05'), 'end': NaT},
    ]
