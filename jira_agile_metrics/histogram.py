import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from .calculator import Calculator
from .cycletime import CycleTimeCalculator
from .utils import get_extension, set_chart_style

class HistogramCalculator(Calculator):
    """Build histogram data for the cycle times in `cycle_data`. Returns
    a dictionary with keys `bin_values` and `bin_edges` of numpy arrays
    """

    def is_enabled(self):
        return self.settings['histogram_data'] or self.settings['histogram_chart']

    def run(self):
        
        cycle_data = self.get_result(CycleTimeCalculator)
        
        values, edges = np.histogram(cycle_data['cycle_time'].astype('timedelta64[D]').dropna(), bins=10)

        index = []
        for i, _ in enumerate(edges):
            if i == 0:
                continue
            index.append("%.01f to %.01f" % (edges[i - 1], edges[i],))

        return pd.Series(values, name="Items", index=index)
    
    def write(self):
        if self.settings['histogram_data']:
            output_file = self.settings['histogram_data']
            output_extension = get_extension(output_file)

            file_data = self.get_result()

            if output_extension == '.json':
                file_data.to_json(output_file, date_format='iso')
            elif output_extension == '.xlsx':
                file_data.to_frame(name='histogram').to_excel(output_file, 'Histogram', header=True)
            else:
                file_data.to_csv(output_file, header=True)
        
        if self.settings['histogram_chart']:
            output_file = self.settings['histogram_chart']
            quantiles = self.settings['quantiles']

            cycle_data = self.get_result(CycleTimeCalculator)
            chart_data = cycle_data[['cycle_time']].dropna(subset=['cycle_time'])
            ct_days = chart_data['cycle_time'].dt.days

            if len(ct_days.index) < 2:
                print("WARNING: Need at least 2 completed items to draw histogram")
            else:

                fig, ax = plt.subplots()

                sns.distplot(ct_days, bins=30, ax=ax, axlabel="Cycle time (days)")
                
                if self.settings['histogram_chart_title']:
                    ax.set_title(self.settings['histogram_chart_title'])

                _, right = ax.get_xlim()
                ax.set_xlim(0, right)

                # Add quantiles
                bottom, top = ax.get_ylim()
                for quantile, value in ct_days.quantile(quantiles).iteritems():
                    ax.vlines(value, bottom, top - 0.001, linestyles='--', linewidths=1)
                    ax.annotate("%.0f%% (%.0f days)" % ((quantile * 100), value,),
                        xy=(value, top),
                        xytext=(value, top - 0.001),
                        rotation="vertical",
                        fontsize="x-small",
                        ha="right"
                    )

                set_chart_style('darkgrid')
                
                fig = ax.get_figure()
                fig.savefig(output_file, bbox_inches='tight', dpi=300)

