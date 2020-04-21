import logging
import datetime

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.transforms

from ..calculator import Calculator
from ..utils import set_chart_style, to_days_since_epoch

from .cycletime import CycleTimeCalculator
from .burnup import BurnupCalculator

logger = logging.getLogger(__name__)

class BurnupForecastCalculator(Calculator):
    """Draw a burn-up chart with a forecast run to completion
    """

    def run(self):
        burnup_data = self.get_result(BurnupCalculator)
        cycle_data = self.get_result(CycleTimeCalculator)

        if len(cycle_data.index) == 0:
            return None

        # This calculation is expensive. Only run it if we intend to write a file.
        if not self.settings['burnup_forecast_chart']:
            logger.debug("Not calculating burnup forecast chart data as no output file specified")
            return None

        backlog_column = self.settings['backlog_column']
        done_column = self.settings['done_column']

        if backlog_column not in burnup_data.columns:
            logger.error("Backlog column %s does not exist", backlog_column)
            return None
        if done_column not in burnup_data.columns:
            logger.error("Backlog column %s does not exist", done_column)
            return None

        if cycle_data[done_column].max() is pd.NaT:
            logger.warning("Unable to draw burnup forecast chart with zero completed items.")
            return None

        throughput_window_end = self.settings['burnup_forecast_chart_throughput_window_end'] or cycle_data[done_column].max().date()
        throughput_window = self.settings['burnup_forecast_chart_throughput_window']
        throughput_window_start = throughput_window_end - datetime.timedelta(days=throughput_window)
        logger.info("Sampling throughput between %s and %s", throughput_window_start.isoformat(), throughput_window_end.isoformat())

        start_value = burnup_data[done_column].max()
        target = self.settings['burnup_forecast_chart_target'] or burnup_data[backlog_column].max()
        logger.info("Running forecast to completion of %d items", target)

        trials = self.settings['burnup_forecast_chart_trials']
        logger.debug("Running %d trials to calculate probable forecast outcomes", trials)

        throughput_data = calculate_daily_throughput(cycle_data[
            (cycle_data[done_column] >= pd.Timestamp(throughput_window_start)) &
            (cycle_data[done_column] <= pd.Timestamp(throughput_window_end))
        ], done_column, throughput_window_start, throughput_window_end)

        # degenerate case - no steps, abort
        if throughput_data['count'].sum() <= 0:
            logger.warning("No throughput samples available, aborting forecast simulations")
            return None
        
        return burnup_monte_carlo(
            start_value=start_value,
            target_value=target,
            start_date=burnup_data.index.max(),
            frequency=throughput_data.index.freq,
            draw_sample=throughput_sampler(throughput_data, start_value, target),
            trials=trials
        )

    def write(self):
        output_file = self.settings['burnup_forecast_chart']
        if not output_file:
            logger.debug("No output file specified for burnup forecast chart")
            return

        burnup_data = self.get_result(BurnupCalculator)
        if burnup_data is None or len(burnup_data.index) == 0:
            logger.warning("Cannot draw burnup forecast chart with zero items")
            return

        window = self.settings['burnup_forecast_window']
        if window:
            start = burnup_data.index.max() - pd.Timedelta(window, 'D')
            burnup_data = burnup_data[start:]

            if len(burnup_data.index) == 0:
                logger.warning("Cannot draw burnup forecast chart with zero items")
                return

        mc_trials = self.get_result()
        if mc_trials is None:
            logger.warning("Cannot draw burnup forecast chart with zero completed trials")
            return

        deadline = self.settings['burnup_forecast_chart_deadline']
        if deadline:
            logger.debug("Forecasting with deadline %s", deadline.isoformat())

        deadline_confidence = self.settings['burnup_forecast_chart_deadline_confidence']
        if deadline_confidence:
            logger.debug("Forecasting deadline at %.2f%% confidence", deadline_confidence * 100.0)

        quantiles = self.settings['quantiles']
        logger.debug("Showing forecast at quantiles %s", ', '.join(['%.2f' % (q * 100.0) for q in quantiles]))

        backlog_column = self.settings['backlog_column']
        target = self.settings['burnup_forecast_chart_target'] or burnup_data[backlog_column].max()

        fig, ax = plt.subplots()

        if self.settings['burnup_forecast_chart_title']:
            ax.set_title(self.settings['burnup_forecast_chart_title'])

        fig.autofmt_xdate()

        transform_vertical = matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes)
        transform_horizontal = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)

        # plot backlog and burnup to date
        burnup_data.plot.line(ax=ax, legend=False)

        deadline_confidence_date = None

        # plot each monte carlo simulation line
        if mc_trials is not None:

            for col in mc_trials:
                mc_trials[col][mc_trials[col] > target] = target

            mc_trials.plot.line(ax=ax, legend=False, color='#ff9696', linestyle='solid', linewidth=0.1)

            # draw quantiles at finish line
            finish_dates = mc_trials.apply(pd.Series.last_valid_index)
            finish_date_quantiles = finish_dates.quantile(quantiles).dt.normalize()

            if deadline_confidence is not None:
                deadline_confidence_quantiles = finish_dates.quantile([deadline_confidence]).dt.normalize()
                if len(deadline_confidence_quantiles) > 0:
                    deadline_confidence_date = pd.Timestamp(deadline_confidence_quantiles.values[0]).to_pydatetime().date()

            bottom, top = ax.get_ylim()
            for percentile, value in finish_date_quantiles.iteritems():
                ax.vlines(value, bottom, target, linestyles='--', linewidths=0.5)
                ax.annotate("%.0f%% (%s)" % ((percentile * 100), value.strftime("%d/%m/%Y"),),
                    xy=(to_days_since_epoch(value.to_pydatetime().date()), 0.35),
                    xycoords=transform_vertical,
                    rotation="vertical",
                    ha="left",
                    va="top",
                    fontsize="x-small",
                    backgroundcolor="#ffffff"
                )

        # draw deadline (pun not intended...)
        if deadline is not None:
            bottom, top = ax.get_ylim()
            left, right = ax.get_xlim()

            deadline_dse = to_days_since_epoch(deadline)

            ax.vlines(deadline, bottom, target, color='r', linestyles='-', linewidths=0.5)
            ax.annotate("Due: %s" % (deadline.strftime("%d/%m/%Y"),),
                xy=(deadline, target),
                xytext=(0.95, 0.95),
                textcoords='axes fraction',
                arrowprops={
                    'arrowstyle': '->',
                    'color': 'r',
                    'linewidth': 1.1,
                    'connectionstyle': 'arc3,rad=.1',
                },
                fontsize="x-small",
                ha="right",
                color='red',
                backgroundcolor="#ffffff"
            )

            # Make sure we can see deadline line
            if right < deadline_dse:
                ax.set_xlim(left, deadline_dse + 1)

            # Draw deadline warning
            if deadline_confidence_date is not None:
                deadline_delta = (deadline - deadline_confidence_date).days

                ax.text(0.02, 0.5,
                    "Deadline: %s\nForecast (%.0f%%): %s\nSlack: %d days" % (
                        deadline.strftime("%d/%m/%Y"),
                        (deadline_confidence * 100),
                        deadline_confidence_date.strftime("%d/%m/%Y"),
                        deadline_delta
                    ),
                    transform=ax.transAxes,
                    fontsize=14,
                    verticalalignment='center',
                    bbox=dict(boxstyle='round', facecolor='r' if deadline_delta < 0 else 'g', alpha=0.5),
                )

        # Place target line
        left, right = ax.get_xlim()
        ax.hlines(target, left, right, linestyles='--', linewidths=1)
        ax.annotate("Target: %d" % (target,),
            xy=(0.02, target),
            xycoords=transform_horizontal,
            fontsize="x-small",
            ha="left",
            va="center",
            backgroundcolor="#ffffff"
        )

        # Give some headroom above the target line so we can see it
        bottom, top = ax.get_ylim()
        ax.set_ylim(bottom, int(top * 1.05))

        # Place legend underneath graph
        box = ax.get_position()
        handles, labels = ax.get_legend_handles_labels()
        ax.set_position([box.x0, box.y0 + box.height * 0.1, box.width, box.height * 0.9])

        ax.legend(handles[:2], labels[:2], loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2)

        set_chart_style()

        # Write file
        logger.info("Writing burnup forecast chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)

def calculate_daily_throughput(cycle_data, done_column, window_start, window_end):
    return cycle_data[[done_column, 'key']] \
        .rename(columns={'key': 'count', done_column: 'completed_timestamp'}) \
        .groupby('completed_timestamp').count() \
        .resample("1D").sum() \
        .reindex(index=pd.date_range(start=window_start, end=window_end, freq='D')) \
        .fillna(0)

def throughput_sampler(throughput_data, start_value, target):
    """Return a function that can efficiently draw samples from `throughput_data`
    """
    sample_buffer_size = int(2 * (target - start_value) / throughput_data['count'].mean())

    sample_buffer = dict(idx=0, buffer=None)

    def get_throughput_sample():
        if sample_buffer['buffer'] is None or sample_buffer['idx'] >= len(sample_buffer['buffer'].index):
            sample_buffer['buffer'] = throughput_data['count'].sample(sample_buffer_size, replace=True)
            sample_buffer['idx'] = 0

        sample_buffer['idx'] += 1
        return sample_buffer['buffer'].iloc[sample_buffer['idx'] - 1]
    
    return get_throughput_sample

def burnup_monte_carlo(
    start_value,
    target_value,
    start_date,
    frequency,
    draw_sample,
    trials=100,
    max_iterations=9999,
):

    series = {}
    for t in range(trials):
        current_date = start_date
        current_value = start_value

        dates = [current_date]
        steps = [current_value]

        while current_value < target_value and len(steps) <= max_iterations:
            current_date += frequency
            current_value += draw_sample()

            dates.append(current_date)
            steps.append(min(current_value, target_value))  # don't overshoot the target

        series["Trial %d" % t] = pd.Series(steps, index=dates, name="Trial %d" % t)

    return pd.DataFrame(series)
