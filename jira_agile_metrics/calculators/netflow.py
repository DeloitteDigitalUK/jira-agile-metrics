import logging
import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import set_chart_style

from .cfd import CFDCalculator

logger = logging.getLogger(__name__)

class NetFlowChartCalculator(Calculator):
    """Draw a net flow chart
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

        frequency = self.settings['net_flow_frequency']
        logger.debug("Calculating net flow at frequency %s", frequency)
        
        net_flow_data = cfd_data[[start_column, done_column]].resample(frequency, label='left').max()
        net_flow_data['arrivals'] = net_flow_data[start_column].diff().fillna(net_flow_data[start_column])
        net_flow_data['departures'] = net_flow_data[done_column].diff().fillna(net_flow_data[done_column])
        net_flow_data['net_flow'] = net_flow_data['arrivals'] - net_flow_data['departures']
        net_flow_data['positive'] = net_flow_data['net_flow'] >= 0

        return net_flow_data
    
    def write(self):
        output_file = self.settings['net_flow_chart']
        if not output_file:
            logger.debug("No output file specified for net flow chart")
            return

        chart_data = self.get_result()

        if len(chart_data.index) == 0:
            logger.warning("Cannot draw net flow chart with zero items")
            return

        fig, ax = plt.subplots()
        
        if self.settings['net_flow_chart_title']:
            ax.set_title(self.settings['net_flow_chart_title'])

        ax.set_xlabel("Period starting")
        ax.set_ylabel("Net flow (departures - arrivals)")

        net_flow_data = chart_data[['net_flow', 'positive']]

        window = self.settings['net_flow_window']
        if window:
            net_flow_data = net_flow_data[-window:]

        net_flow_data['net_flow'].plot.bar(ax=ax, color=net_flow_data['positive'].map({True: 'r', False: 'b'}),)

        labels = [d.strftime("%d/%m/%Y") for d in net_flow_data.index]
        ax.set_xticklabels(labels, rotation=70, size='small')

        set_chart_style()

        # Write file
        logger.info("Writing ageing WIP chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
