import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import set_chart_style

from .cfd import CFDCalculator

class NetFlowChartCalculator(Calculator):
    """Draw a net flow chart
    """

    def run(self):
        cfd_data = self.get_result(CFDCalculator)
        cycle_names = [s['name'] for s in self.settings['cycle']]

        start_column = self.settings['committed_column'] or cycle_names[1]
        end_column = self.settings['done_column'] or cycle_names[-1]
        frequency = self.settings['net_flow_chart_frequency']
        
        net_flow_data = cfd_data[[start_column, end_column]].resample(frequency, label='left').max()
        net_flow_data['arrivals'] = net_flow_data[start_column].diff().fillna(net_flow_data[start_column])
        net_flow_data['departures'] = net_flow_data[end_column].diff().fillna(net_flow_data[end_column])
        net_flow_data['net_flow'] = net_flow_data['arrivals'] - net_flow_data['departures']
        net_flow_data['positive'] = net_flow_data['net_flow'] >= 0

        return net_flow_data
    
    def write(self):
        output_file = self.settings['net_flow_chart']
        if not output_file:
            return

        chart_data = self.get_result()

        if len(chart_data.index) == 0:
            print("WARNING: Cannot draw net flow chart with no completed items")
            return

        fig, ax = plt.subplots()
        
        if self.settings['net_flow_chart_title']:
            ax.set_title(self.settings['net_flow_chart_title'])

        ax.set_xlabel("Week")
        ax.set_ylabel("Net flow (departures - arrivals)")

        chart_data['net_flow'].plot.bar(ax=ax, color=chart_data['positive'].map({True: 'r', False: 'b'}),)

        labels = [d.strftime("%d/%m/%Y") for d in chart_data.index]
        ax.set_xticklabels(labels, rotation=70, size='small')

        set_chart_style()

        # Write file
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
