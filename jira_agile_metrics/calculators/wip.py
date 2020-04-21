import logging
import matplotlib.pyplot as plt
import pandas as pd

from ..calculator import Calculator
from ..utils import set_chart_style

from .cfd import CFDCalculator

logger = logging.getLogger(__name__)

class WIPChartCalculator(Calculator):
    """Draw a weekly WIP chart
    """

    def run(self):
        cfd_data = self.get_result(CFDCalculator)
        cycle_names = [s['name'] for s in self.settings['cycle']]

        start_column = self.settings['committed_column']
        done_column = self.settings['done_column']

        if start_column not in cycle_names:
            logger.error("Committed column %s does not exist", start_column)
            return None
        if done_column not in cycle_names:
            logger.error("Done column %s does not exist", done_column)
            return None
        
        return pd.DataFrame({'wip': cfd_data[start_column] - cfd_data[done_column]}, index=cfd_data.index)
    
    def write(self):
        output_file = self.settings['wip_chart']
        if not output_file:
            logger.debug("No output file specified for WIP chart")
            return

        chart_data = self.get_result()

        if len(chart_data.index) == 0:
            logger.warning("Cannot draw WIP chart with no completed items")
            return

        fig, ax = plt.subplots()
        
        if self.settings['wip_chart_title']:
            ax.set_title(self.settings['wip_chart_title'])

        frequency = self.settings['wip_frequency']
        logger.debug("Calculating WIP chart with frequency %s", frequency)

        wip_data = chart_data[['wip']]

        window = self.settings['wip_window']
        if window:
            start = wip_data.index.max().normalize() - (window * pd.tseries.frequencies.to_offset(frequency))
            wip_data = wip_data[start:]

            if len(wip_data.index) < 2:
                logger.warning("Need at least 2 completed items to draw scatterplot")
                return

        groups = wip_data.groupby(pd.Grouper(freq=frequency, label='left', closed='left'))
        labels = [x[0].strftime("%d/%m/%Y") for x in groups]

        groups.boxplot(subplots=False, ax=ax, showmeans=True, return_type='axes')
        ax.set_xticklabels(labels, rotation=70, size='small')

        ax.set_xlabel("Period starting")
        ax.set_ylabel("WIP")

        set_chart_style()

        # Write file
        logger.info("Writing WIP chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
