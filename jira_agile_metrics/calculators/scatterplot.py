import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from ..calculator import Calculator
from ..utils import get_extension, set_chart_style

from .cycletime import CycleTimeCalculator

logger = logging.getLogger(__name__)

class ScatterplotCalculator(Calculator):
    """Build scatterplot data for the cycle times: a data frame containing
    only those items in where values are set for `completed_timestamp` and
    `cycle_time`, and with those two columns as the first two, both
    normalised to whole days, and with `completed_timestamp` renamed to
    `completed_date`.
    """

    def run(self):
        cycle_data = self.get_result(CycleTimeCalculator)
        columns = list(cycle_data.columns)
        columns.remove('cycle_time')
        columns.remove('completed_timestamp')
        columns.remove('blocked_days')
        columns.remove('impediments')
        columns = ['completed_timestamp', 'cycle_time', 'blocked_days'] + columns

        data = (
            cycle_data[columns]
            .dropna(subset=['cycle_time', 'completed_timestamp'])
            .rename(columns={'completed_timestamp': 'completed_date'})
        )

        data['cycle_time'] = data['cycle_time'].astype('timedelta64[D]')

        return data
    
    def write(self):
        data = self.get_result()

        if self.settings['scatterplot_data']:
            self.write_file(data, self.settings['scatterplot_data'])
        else:
            logger.debug("No output file specified for scatterplot data")
        
        if self.settings['scatterplot_chart']:
            self.write_chart(data, self.settings['scatterplot_chart'])
        else:
            logger.debug("No output file specified for scatterplot chart")

    def write_file(self, data, output_file):
        output_extension = get_extension(output_file)

        file_data = data.copy()
        file_data['completed_date'] = file_data['completed_date'].map(pd.Timestamp.date)

        logger.info("Writing scatterplot data to %s", output_file)
        if output_extension == '.json':
            file_data.to_json(output_file, date_format='iso')
        elif output_extension == '.xlsx':
            file_data.to_excel(output_file, 'Scatter', index=False)
        else:
            file_data.to_csv(output_file, index=False)
        
    def write_chart(self, data, output_file):
        if len(data.index) < 2:
            logger.warning("Need at least 2 completed items to draw scatterplot")
            return
            
        chart_data = pd.DataFrame({
            'completed_date': data['completed_date'].values.astype('datetime64[D]'),
            'cycle_time': data['cycle_time']
        }, index=data.index)

        window = self.settings['scatterplot_window']
        if window:
            start = chart_data['completed_date'].max().normalize() - pd.Timedelta(window, 'D')
            chart_data = chart_data[chart_data.completed_date >= start]

            if len(data.index) < 2:
                logger.warning("Need at least 2 completed items to draw scatterplot")
                return
        
        quantiles = self.settings['quantiles']
        logger.debug("Showing forecast at quantiles %s", ', '.join(['%.2f' % (q * 100.0) for q in quantiles]))
        
        fig, ax = plt.subplots()
        fig.autofmt_xdate()

        ax.set_xlabel("Completed date")
        ax.set_ylabel("Cycle time (days)")

        if self.settings['scatterplot_chart_title']:
            ax.set_title(self.settings['scatterplot_chart_title'])

        ax.plot_date(x=chart_data['completed_date'], y=chart_data['cycle_time'], ms=5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))

        # Add quantiles
        left, right = ax.get_xlim()
        for quantile, value in chart_data['cycle_time'].quantile(quantiles).iteritems():
            ax.hlines(value, left, right, linestyles='--', linewidths=1)
            ax.annotate("%.0f%% (%.0f days)" % ((quantile * 100), value,),
                xy=(left, value),
                xytext=(left, value + 0.5),
                fontsize="x-small",
                ha="left"
            )

        set_chart_style()

        # Write file
        logger.info("Writing scatterplot chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
