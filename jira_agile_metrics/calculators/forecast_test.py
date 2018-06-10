import pytest
import datetime
import numpy as np
from pandas import DataFrame, DatetimeIndex, Timestamp

from .cycletime import CycleTimeCalculator
from .cfd import CFDCalculator
from .burnup import BurnupCalculator
from .forecast import BurnupForecastCalculator

from ..utils import extend_dict

@pytest.fixture
def settings(minimal_settings):
    return extend_dict(minimal_settings, {
        'burnup_forecast_chart_throughput_window_end': None,
        'burnup_forecast_chart_throughput_window': 8,
        'burnup_forecast_chart_target': 30,
        'burnup_forecast_chart_trials': 10,
        'burnup_forecast_chart_deadline': datetime.date(2018, 1, 30),
        'burnup_forecast_chart_deadline_confidence': 0.85,
        'quantiles': [0.1, 0.3, 0.5],
        'burnup_forecast_chart': 'forecast.png'  # without a file, calculator stops
    })

@pytest.fixture
def query_manager(minimal_query_manager):
    return minimal_query_manager

@pytest.fixture
def results(query_manager, settings, large_cycle_time_results):
    results = large_cycle_time_results.copy()
    results.update({CFDCalculator: CFDCalculator(query_manager, settings, results).run()})
    results.update({BurnupCalculator: BurnupCalculator(query_manager, settings, results).run()})
    return results

def test_empty(query_manager, settings, minimal_cycle_time_columns):
    results = {
        CycleTimeCalculator: DataFrame([], columns=minimal_cycle_time_columns),
        BurnupCalculator: DataFrame([], columns=['Backlog', 'Committed', 'Build', 'Test', 'Done'], index=DatetimeIndex(start=datetime.date(2018, 1, 1), periods=0, freq='D'))
    }

    calculator = BurnupForecastCalculator(query_manager, settings, results)

    data = calculator.run()
    assert data is None

def test_columns(query_manager, settings, results):
    calculator = BurnupForecastCalculator(query_manager, settings, results)

    data = calculator.run()
    assert list(data.columns) == [
        'Trial 0',
        'Trial 1',
        'Trial 2',
        'Trial 3',
        'Trial 4',
        'Trial 5',
        'Trial 6',
        'Trial 7',
        'Trial 8',
        'Trial 9'
    ]

def test_calculate_forecast(query_manager, settings, results):
    calculator = BurnupForecastCalculator(query_manager, settings, results)

    data = calculator.run()

    # because of the random nature of this, we don't know exactly how many records
    # there will be, but will assume at least two
    assert len(data.index) > 0
    assert list(data.index)[0] == Timestamp('2018-01-09 00:00:00', freq='D')
    assert list(data.index)[1] == Timestamp('2018-01-10 00:00:00', freq='D')
    
    for i in range(10):
        trial_values = data['Trial %d' % i]

        # remove na values at the end (not all series will need all dates)
        trial_values = trial_values[:trial_values.last_valid_index()]

        # check that series is monotonically increasing
        trial_diff = np.diff(trial_values)
        assert np.all(trial_diff >= 0)

        # we start with the final value in the burnup, on the final day (2018-01-09)
        assert trial_values[0] == 6

        # we reach the target value
        assert trial_values[-1] == 30

def test_calculate_forecast_settings(query_manager, settings, results):

    settings.update({
        'backlog_column': 'Committed',
        'done_column': 'Test',
        'burnup_forecast_chart_throughput_window_end': datetime.date(2018, 1, 6),
        'burnup_forecast_chart_throughput_window': 4,
        'burnup_forecast_chart_target': None,  # use max of backlog column -- 15
        'burnup_forecast_chart_trials': 10,
        'burnup_forecast_chart_deadline': datetime.date(2018, 1, 30),
        'burnup_forecast_chart_deadline_confidence': 0.85,
        'quantiles': [0.1, 0.3, 0.5]
    })

    results.update({CFDCalculator: CFDCalculator(query_manager, settings, results).run()})
    results.update({BurnupCalculator: BurnupCalculator(query_manager, settings, results).run()})

    calculator = BurnupForecastCalculator(query_manager, settings, results)

    data = calculator.run()

    # because of the random nature of this, we don't know exactly how many records
    # there will be, but will assume at least two
    assert len(data.index) > 0
    assert list(data.index)[0] == Timestamp('2018-01-09 00:00:00', freq='D')
    assert list(data.index)[1] == Timestamp('2018-01-10 00:00:00', freq='D')
    
    for i in range(10):
        trial_values = data['Trial %d' % i]

        # remove na values at the end (not all series will need all dates)
        trial_values = trial_values[:trial_values.last_valid_index()]

        # check that series is monotonically increasing
        trial_diff = np.diff(trial_values)
        assert np.all(trial_diff >= 0)

        # we start with the final value in the burnup, on the final day (2018-01-09)
        assert trial_values[0] == 9

        # we reach the target value
        assert trial_values[-1] == 15
