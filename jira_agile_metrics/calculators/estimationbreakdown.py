import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from ..calculator import Calculator
from ..utils import set_chart_style

from .cycletime import CycleTimeCalculator

logger = logging.getLogger(__name__)


class EstimationBreakdownCalculator(Calculator):
    """Visually compare developer estimation to actual cycles spent on the issue.

    Creates two stacked bar chart horizontal rows per issue.
    First one is the estimation and the second one is realised.
    """

    def run(self, today=None):
        """Break down raw cycle data to split rows where the first row is actual and second row is estimation."""
        # short circuit relatively expensive calculation if it won't be used
        if not self.settings['estimation_breakdown_chart']:
            return None

        cycle_data = self.get_result(CycleTimeCalculator)
        cycle_names = [s['name'] for s in self.settings['cycle']]

        # All states between "Backlog" and "Done"
        active_cycle_names = cycle_names[1:-1]

        output = []

        def get_good_duration(val):
            if pd.isnull(val):
                return 0
            else:
                return val.total_seconds() / (24 * 3600)

        for idx, row in cycle_data.iterrows():

            # Crop too long summaries
            label = (row["key"] + " " + row["summary"])[0:45]

            estimation_row = {"Estimation": row["estimation_days"]}
            estimation_row["label"] = label + " (est)"

            actual_row = dict([(state, get_good_duration(row[f"{state} duration"])) for state in active_cycle_names])
            actual_row["label"] = label

            output.append(estimation_row)
            output.append(actual_row)

        return pd.DataFrame(output, columns=['label', 'Estimation'] + active_cycle_names)

    def write(self):
        output_file = self.settings['estimation_breakdown_chart']
        if not output_file:
            logger.debug("No output file specified for estimation breakdown chart")
            return

        chart_data = self.get_result()

        if len(chart_data.index) == 0:
            logger.warning("Unable to draw estimation breakdown without items")
            return

        cycle_names = [s['name'] for s in self.settings['cycle']]

        # All states between "Backlog" and "Done"
        active_cycle_names = cycle_names[1:-1]

        # https://matplotlib.org/3.1.1/gallery/lines_bars_and_markers/horizontal_barchart_distribution.html#sphx-glr-gallery-lines-bars-and-markers-horizontal-barchart-distribution-py
        # https://stackoverflow.com/a/61741058/315168
        chart_data.pivot(
            index='label',
            columns=['Estimation'] + active_cycle_names)

        fig, ax = plt.subplots(figsize=(10, len(chart_data) / 2))

        chart_data.plot(ax=ax, kind='barh', stacked=True)

        # https://stackoverflow.com/questions/54162981/how-to-display-data-values-in-stacked-horizontal-bar-chart-in-matplotlib
        for idx, row in chart_data.iterrows():
            xpos = 0

            # print(row["label"])

            if "(est)" in row["label"]:
                # Estimation row
                xpos = (row["Estimation"] or 0) + 1
                val = row["Estimation"]
                if val:
                    if val <= 1:
                        label = "< 1 day"
                    else:
                        label = "{:1.0f} days".format(val)
                else:
                    label = "(missing)"
            else:
                # Stacked cycle time row
                total = sum([0 if pd.isnull(row[state]) else row[state] for state in active_cycle_names], 0)
                parts = ["{:1.0f} ({})".format(row[state], state) for state in active_cycle_names if not pd.isnull(row[state])]
                label = " + ".join(parts)
                label += " = {:1.0f} days".format(total)
                val = total
                xpos = val + 1

            if label:
                # ax.text(xpos + 1, idx - 0.05, label, color='black')
                ax.text(xpos, idx - 0.1, label, color='black')

        # Remove ticket name from the estimation label
        def friendly_label(label):
            if "(est)" in label:
                return "Estimation"
            return label

        ax.set_yticklabels(map(friendly_label, chart_data["label"].tolist()), minor=False)

        set_chart_style()

        # Write file
        logger.info("Writing estimation breakdown chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
