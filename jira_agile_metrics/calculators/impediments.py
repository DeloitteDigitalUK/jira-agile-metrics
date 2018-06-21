import logging
import pandas as pd
import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import get_extension, breakdown_by_month, breakdown_by_month_sum_days, set_chart_style

from .cycletime import CycleTimeCalculator

logger = logging.getLogger(__name__)

class ImpedimentsCalculator(Calculator):
    """Calculate impediments, charted by month and workflow status, either as
    a count of tickets that were blocked in that month, or as a sum of the total
    number of days of blockage for all tickets in that month.

    Writes to `impediments_chart`, `impediments_days_chart`,
    `impediments_tatus_chart`, and `impediments_status_days_chart`, respectively,
    with corresponding titles. The number of months to output can be restricted
    with `impediments_window`. Raw data can be written to `impediments_data`.
    """

    def run(self):

        # This calculation is expensive. Only run it if we are going to write something
        if not (
            self.settings['impediments_data'] or
            self.settings['impediments_chart'] or
            self.settings['impediments_days_chart'] or
            self.settings['impediments_status_chart'] or
            self.settings['impediments_status_days_chart']
        ):
            logger.debug("Not calculating impediments data as no output files specified")
            return None
        
        backlog_column = self.settings['backlog_column']
        done_column = self.settings['done_column']

        cycle_data = self.get_result(CycleTimeCalculator)
        cycle_data = cycle_data[cycle_data.blocked_days > 0][['key', 'impediments']]
        
        data = []

        for row in cycle_data.itertuples():
            for idx, event in enumerate(row.impediments):
                # Ignore things that were impeded whilst in the backlog and/or done column
                # (these are mostly nonsensical, and don't really indicate blocked/wasted time)

                if event['status'] in (backlog_column, done_column):
                    continue
                data.append({
                    'key': row.key,
                    'status': event['status'],
                    'flag': event['flag'],
                    'start': pd.Timestamp(event['start']),
                    'end': pd.Timestamp(event['end']) if event['end'] else pd.NaT,
                })
        
        return pd.DataFrame(data, columns=['key', 'status', 'flag', 'start', 'end'])

    def write(self):
        data = self.get_result()
        if data is None:
            return

        if self.settings['impediments_data']:
            self.write_data(data, self.settings['impediments_data'])

        if self.settings['impediments_chart']:
            self.write_impediments_chart(data, self.settings['impediments_chart'])
        
        if self.settings['impediments_days_chart']:
            self.write_impediments_days_chart(data, self.settings['impediments_days_chart'])
        
        if self.settings['impediments_status_chart']:
            self.write_impediments_status_chart(data, self.settings['impediments_status_chart'])
        
        if self.settings['impediments_status_days_chart']:
            self.write_impediments_status_days_chart(data, self.settings['impediments_status_days_chart'])
    
    def write_data(self, data, output_file):
        output_extension = get_extension(output_file)

        logger.info("Writing impediments data to %s", output_file)
        if output_extension == '.json':
            data.to_json(output_file, date_format='iso')
        elif output_extension == '.xlsx':
            data.to_excel(output_file, 'Impediments', header=True)
        else:
            data.to_csv(output_file, header=True, date_format='%Y-%m-%d', index=False)

    def write_impediments_chart(self, chart_data, output_file):
        if len(chart_data.index) == 0:
            logger.warning("Cannot draw impediments chart with zero items")
            return
        
        window = self.settings['impediments_window']
        breakdown = breakdown_by_month(chart_data, 'start', 'end', 'key', 'flag')
        
        if window:
            breakdown = breakdown[-window:]

        if len(breakdown.index) == 0:
            logger.warning("Cannot draw impediments chart with zero items")
            return

        fig, ax = plt.subplots()
        
        breakdown.plot.bar(ax=ax, stacked=True)
        
        if self.settings['impediments_chart_title']:
            ax.set_title(self.settings['impediments_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Month", labelpad=20)
        ax.set_ylabel("Number of impediments", labelpad=10)

        labels = [d.strftime("%b %y") for d in breakdown.index]
        ax.set_xticklabels(labels, rotation=90, size='small')

        set_chart_style()

        # Write file
        logger.info("Writing impediments chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
    
    def write_impediments_days_chart(self, chart_data, output_file):
        if len(chart_data.index) == 0:
            logger.warning("Cannot draw impediments days chart with zero items")
            return

        window = self.settings['impediments_window']
        breakdown = breakdown_by_month_sum_days(chart_data, 'start', 'end', 'flag')
        
        if window:
            breakdown = breakdown[-window:]

        if len(breakdown.index) == 0:
            logger.warning("Cannot draw impediments chart with zero items")
            return

        fig, ax = plt.subplots()
        
        breakdown.plot.bar(ax=ax, stacked=True)
        
        if self.settings['impediments_days_chart_title']:
            ax.set_title(self.settings['impediments_days_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Month", labelpad=20)
        ax.set_ylabel("Total impeded days", labelpad=10)

        labels = [d.strftime("%b %y") for d in breakdown.index]
        ax.set_xticklabels(labels, rotation=90, size='small')

        set_chart_style()

        # Write file
        logger.info("Writing impediments days chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
    
    def write_impediments_status_chart(self, chart_data, output_file):
        if len(chart_data.index) == 0:
            logger.warning("Cannot draw impediments status chart with zero items")
            return
        
        window = self.settings['impediments_window']
        cycle_names = [s['name'] for s in self.settings['cycle']]

        breakdown = breakdown_by_month(chart_data, 'start', 'end', 'key', 'status', cycle_names)
        
        if window:
            breakdown = breakdown[-window:]

        if len(breakdown.index) == 0:
            logger.warning("Cannot draw impediments status chart with zero items")
            return

        fig, ax = plt.subplots()
        
        breakdown.plot.bar(ax=ax, stacked=True)
        
        if self.settings['impediments_status_chart_title']:
            ax.set_title(self.settings['impediments_status_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Month", labelpad=20)
        ax.set_ylabel("Number of impediments", labelpad=10)

        labels = [d.strftime("%b %y") for d in breakdown.index]
        ax.set_xticklabels(labels, rotation=90, size='small')

        set_chart_style()

        # Write file
        logger.info("Writing impediments status chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
    
    def write_impediments_status_days_chart(self, chart_data, output_file):
        if len(chart_data.index) == 0:
            logger.warning("Cannot draw impediments status days chart with zero items")
            return

        window = self.settings['impediments_window']
        cycle_names = [s['name'] for s in self.settings['cycle']]

        breakdown = breakdown_by_month_sum_days(chart_data, 'start', 'end', 'status', cycle_names)
        
        if window:
            breakdown = breakdown[-window:]

        if len(breakdown.index) == 0:
            logger.warning("Cannot draw impediments status days chart with zero items")
            return

        fig, ax = plt.subplots()
        
        breakdown.plot.bar(ax=ax, stacked=True)
        
        if self.settings['impediments_status_days_chart_title']:
            ax.set_title(self.settings['impediments_status_days_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Month", labelpad=20)
        ax.set_ylabel("Total impeded days", labelpad=10)

        labels = [d.strftime("%b %y") for d in breakdown.index]
        ax.set_xticklabels(labels, rotation=90, size='small')

        set_chart_style()

        # Write file
        logger.info("Writing impediments status days chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
