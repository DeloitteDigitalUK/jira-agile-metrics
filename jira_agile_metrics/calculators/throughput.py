import logging
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as sm

from ..calculator import Calculator
from ..utils import get_extension, set_chart_style

from .cycletime import CycleTimeCalculator

logger = logging.getLogger(__name__)

class ThroughputCalculator(Calculator):
    """Build a data frame with columns `completed_timestamp` of the
    given frequency, and `count`, where count is the number of items
    completed at that timestamp (e.g. daily).
    """

    def run(self):
        cycle_data = self.get_result(CycleTimeCalculator)
        
        frequency = self.settings['throughput_frequency']
        window = self.settings['throughput_window']
        
        logger.debug("Calculating throughput at frequency %s", frequency)

        return calculate_throughput(cycle_data, frequency, window)
    
    def write(self):
        data = self.get_result()
        
        if self.settings['throughput_data']:
            self.write_file(data, self.settings['throughput_data'])
        else:
            logger.debug("No output file specified for throughput data")
        
        if self.settings['throughput_chart']:
            self.write_chart(data, self.settings['throughput_chart'])
        else:
            logger.debug("No output file specified for throughput chart")

    def write_file(self, data, output_files):

        for output_file in output_files:
            output_extension = get_extension(output_file)

            logger.info("Writing throughput data to %s", output_file)
            if output_extension == '.json':
                data.to_json(output_file, date_format='iso')
            elif output_extension == '.xlsx':
                data.to_excel(output_file, 'Throughput', header=True)
            else:
                data.to_csv(output_file, header=True)
    
    def write_chart(self, data, output_file):
        chart_data = data.copy()

        if len(chart_data.index) == 0:
            logger.warning("Cannot draw throughput chart with no completed items")
            return
        
        fig, ax = plt.subplots()

        if self.settings['throughput_chart_title']:
            ax.set_title(self.settings['throughput_chart_title'])

        # Calculate zero-indexed days to allow linear regression calculation
        day_zero = chart_data.index[0]
        chart_data['day'] = (chart_data.index - day_zero).days

        # Fit a linear regression (http://stackoverflow.com/questions/29960917/timeseries-fitted-values-from-trend-python)
        fit = sm.ols(formula="count ~ day", data=chart_data).fit()
        chart_data['fitted'] = fit.predict(chart_data)

        # Plot

        ax.set_xlabel("Period starting")
        ax.set_ylabel("Number of items")

        ax.plot(chart_data.index, chart_data['count'], marker='o')
        plt.xticks(chart_data.index, [d.date().strftime('%d/%m/%Y') for d in chart_data.index], rotation=70, size='small')

        _, top = ax.get_ylim()
        ax.set_ylim(0, top + 1)

        for x, y in zip(chart_data.index, chart_data['count']):
            if y == 0:
                continue
            ax.annotate(
                "%.0f" % y,
                xy=(x.toordinal(), y + 0.2),
                ha='center',
                va='bottom',
                fontsize="x-small",
            )

        ax.plot(chart_data.index, chart_data['fitted'], '--', linewidth=2)

        set_chart_style()

        # Write file
        logger.info("Writing throughput chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)

def calculate_throughput(cycle_data, frequency, window=None):
    if len(cycle_data.index) == 0:
        return pd.DataFrame([], columns=['count'], index=[])

    throughput = cycle_data[['completed_timestamp', 'key']] \
        .rename(columns={'key': 'count'}) \
        .groupby('completed_timestamp').count() \
        .resample(frequency).sum()
    
    # make sure we have 0 for periods with no throughput, and force to window if set
    window_start = throughput.index.min()
    window_end = throughput.index.max()
    
    if window:
        window_start = window_end - (pd.tseries.frequencies.to_offset(frequency) * (window - 1))

    if window_start is pd.NaT or window_end is pd.NaT:
        return pd.DataFrame([], columns=['count'], index=[])
    
    return throughput.reindex(index=pd.date_range(start=window_start, end=window_end, freq=frequency)).fillna(0)
