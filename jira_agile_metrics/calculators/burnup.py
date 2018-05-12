import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import set_chart_style

from .cfd import CFDCalculator

class BurnupCalculator(Calculator):
    """Draw a simple burn-up chart.
    """

    def run(self):
        cfd_data = self.get_result(CFDCalculator)
        
        backlog_column = self.settings['backlog_column'] or cfd_data.columns[0]
        done_column = self.settings['done_column'] or cfd_data.columns[-1]

        return cfd_data[[backlog_column, done_column]]
    
    def write(self):
        output_file = self.settings['burnup_chart']
        if not output_file:
            return

        chart_data = self.get_result()

        if len(chart_data.index) == 0:
            print("WARNING: Cannot draw burnup chart with no completed items")
            return

        fig, ax = plt.subplots()
        
        if self.settings['burnup_chart_title']:
            ax.set_title(self.settings['burnup_chart_title'])

        fig.autofmt_xdate()

        ax.set_xlabel("Date")
        ax.set_ylabel("Number of items")

        chart_data.plot.line(ax=ax, legend=True)
        ax.legend(loc=0, title="", frameon=True)

        set_chart_style()

        # Write file
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
