import matplotlib.pyplot as plt
import pandas as pd

from ..calculator import Calculator
from ..utils import set_chart_style

from .cfd import CFDCalculator

class WIPChartCalculator(Calculator):
    """Draw a weekly WIP chart
    """

    def is_enabled(self):
        return self.settings['wip_chart']

    def run(self):
        cfd_data = self.get_result(CFDCalculator)
        cycle_names = [s['name'] for s in self.settings['cycle']]

        start_column = self.settings['committed_column'] or cycle_names[1]
        end_column = self.settings['final_column'] or cycle_names[-2]
        
        wip_data = cfd_data[[start_column, end_column]]
        return pd.DataFrame({'wip': wip_data[start_column] - wip_data[end_column]})
    
    def write(self):
        output_file = self.settings['wip_chart']
        chart_data = self.get_result()

        if len(chart_data.index) < 0:
            print("WARNING: Cannot draw WIP chart with no completed items")
        else:

            fig, ax = plt.subplots()
            
            if self.settings['wip_chart_title']:
                ax.set_title(self.settings['wip_chart_title'])

            frequency = self.settings['wip_chart_frequency']

            groups = chart_data[['wip']].groupby(pd.Grouper(freq=frequency, label='left'))
            labels = [x[0].strftime("%d/%m/%Y") for x in groups]

            groups.boxplot(subplots=False, ax=ax, showmeans=True, return_type='axes')
            ax.set_xticklabels(labels, rotation=70, size='small')

            ax.set_xlabel("Week")
            ax.set_ylabel("WIP")

            set_chart_style('darkgrid')

            fig = ax.get_figure()
            fig.savefig(output_file, bbox_inches='tight', dpi=300)
