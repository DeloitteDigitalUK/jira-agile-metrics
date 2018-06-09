import logging
import pandas as pd
import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import breakdown_by_month, breakdown_by_month_sum_days, set_chart_style

from .cycletime import CycleTimeCalculator

logger = logging.getLogger(__name__)

class BlockedCalculator(Calculator):
    """Calculate blocked items.

    
    """

    def run(self):

        # This calculation is expensive. Only run it if we are going to write something
        if not self.settings['blocked_count_chart'] and not self.settings['blocked_days_chart']:
            logger.debug("Not calculating blocked data as no output files specified")
            return None
        
        backlog_column = self.settings['backlog_column'] or self.settings['cycle'][0]['name']
        done_column = self.settings['done_column'] or self.settings['cycle'][-1]['name']

        cycle_data = self.get_result(CycleTimeCalculator)
        cycle_data = cycle_data[cycle_data.blocked_days > 0][['key', 'blocking_events']]
        
        data = []

        for row in cycle_data.itertuples():
            for idx, event in enumerate(row.blocking_events):
                # Ignore things that became blocked in the backlog and/or done column
                # (these are mostly nonsensical, and don't really indicate blocked/wasted time)

                if event['status'] in (backlog_column, done_column):
                    continue
                data.append({
                    'key': "%s-%d" % (row.key, idx),
                    'status': event['status'],
                    'start': pd.Timestamp(event['start']),
                    'end': pd.Timestamp(event['end']) if event['end'] else pd.NaT,
                })
        
        return pd.DataFrame(data, columns=['key', 'status', 'start', 'end'])

    def write(self):
        chart_data = self.get_result()
        if chart_data is None:
            return

        if len(chart_data.index) == 0:
            logger.warning("Cannot draw blocked charts with zero items")
            return
        
        if self.settings['blocked_count_chart']:
            self.write_count_chart(chart_data, self.settings['blocked_count_chart'])
        
        if self.settings['blocked_days_chart']:
            self.write_days_chart(chart_data, self.settings['blocked_days_chart'])
    
    def write_count_chart(self, chart_data, output_file):
        window = self.settings['blocked_window']
        cycle_names = [s['name'] for s in self.settings['cycle']]

        breakdown = breakdown_by_month(chart_data, 'start', 'end', 'key', 'status', cycle_names)
        
        if window:
            breakdown = breakdown[-window:]

        fig, ax = plt.subplots()
        
        breakdown.plot.bar(ax=ax, stacked=True)
        
        if self.settings['blocked_count_chart_title']:
            ax.set_title(self.settings['blocked_count_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Month", labelpad=20)
        ax.set_ylabel("Number of blocked items", labelpad=10)

        labels = [d.strftime("%b %y") for d in breakdown.index]
        ax.set_xticklabels(labels, rotation=90, size='small')

        set_chart_style()

        # Write file
        logger.info("Writing blocked count chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
    
    def write_days_chart(self, chart_data, output_file):
        window = self.settings['blocked_window']
        cycle_names = [s['name'] for s in self.settings['cycle']]

        breakdown = breakdown_by_month_sum_days(chart_data, 'start', 'end', 'status', cycle_names)
        
        if window:
            breakdown = breakdown[-window:]

        fig, ax = plt.subplots()
        
        breakdown.plot.bar(ax=ax, stacked=True)
        
        if self.settings['blocked_days_chart_title']:
            ax.set_title(self.settings['blocked_days_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Month", labelpad=20)
        ax.set_ylabel("Total days in blocked state", labelpad=10)

        labels = [d.strftime("%b %y") for d in breakdown.index]
        ax.set_xticklabels(labels, rotation=90, size='small')

        set_chart_style()

        # Write file
        logger.info("Writing blocked days chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
