import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from ..calculator import Calculator
from ..utils import set_chart_style

from .cycletime import CycleTimeCalculator

logger = logging.getLogger(__name__)


class AgeingHistoryChartCalculator(Calculator):
    """Draw a chart showing breakdown of states where issues spent time.

    Unlike Ageing WIP this consideres done items as well,
    so you get historical reference data to better understand the
    status of the current pipeline.
    """

    def run(self, today=None):

        # short circuit relatively expensive calculation if it won't be used
        if not self.settings['ageing_history_chart']:
            return None

        cycle_data = self.get_result(CycleTimeCalculator)
        cycle_names = [s['name'] for s in self.settings['cycle']]

        # All states between "Backlog" and "Done"
        active_cycle_names = cycle_names[1:-1]

        # What Pandas columns we are going to export
        series = {
            'status': {'data': [], 'dtype': 'str'},
            'age': {'data': [], 'dtype': 'float'},
        }
        # Add one column per each state
        # for name in active_cycle_names:
        #    series[name] = {'data': [], 'dtype': 'timedelta64[ns]'}

        # For each issue create one row for each state and then duration spent in that state
        for idx, row in cycle_data.iterrows():
            for state in active_cycle_names:
                # Duration column as pd.timedelta is filled by new cycletime calculator
                duration = row[f"{state} duration"].total_seconds() / (24 * 3600)
                series["status"]["data"].append(state)
                series["age"]["data"].append(duration)

        data = {}
        for k, v in series.items():
            data[k] = pd.Series(v['data'], dtype=v['dtype'])

        return pd.DataFrame(data,
            columns=['status', 'age']
        )

    def write(self):
        output_file = self.settings['ageing_history_chart']
        if not output_file:
            logger.debug("No output file specified for ageing WIP chart")
            return

        chart_data = self.get_result()

        if len(chart_data.index) == 0:
            logger.warning("Unable to draw ageing WIP chart with zero completed items")
            return

        fig, ax = plt.subplots()

        if self.settings['ageing_history_chart_title']:
            ax.set_title(self.settings['ageing_history_chart_title'])

        sns.swarmplot(x='status', y='age', data=chart_data, ax=ax)

        ax.set_xlabel("Status")
        ax.set_ylabel("Age (days)")

        ax.set_xticklabels(ax.xaxis.get_majorticklabels(), rotation=90)

        _, top = ax.get_ylim()
        ax.set_ylim(0, top)

        set_chart_style()

        # Write file
        logger.info("Writing ageing history chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
