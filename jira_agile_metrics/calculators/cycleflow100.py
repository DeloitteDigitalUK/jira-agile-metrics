import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import get_extension, set_chart_style

from .cycletime import CycleTimeCalculator
from .cycleflow import calculate_cycle_flow_data


logger = logging.getLogger(__name__)


class CycleFlow100Calculator(Calculator):
    """Same as cycle flow chart, but uses 100% stacked line graph instead.

    https://stackoverflow.com/questions/29940382/100-area-plot-of-a-pandas-dataframe
    """

    def run(self):
        cycle_data = self.get_result(CycleTimeCalculator)
        # Exclude backlog and done
        active_cycles = self.settings["cycle"][1:-1]
        cycle_names = [s['name'] for s in active_cycles]
        data = calculate_cycle_flow_data(cycle_data, cycle_names)
        if data:
            # Stack cols to 100%
            data = data.divide(data.sum(axis=1), axis=0)
        return data

    def write(self):
        data = self.get_result()

        if self.settings['cycle_flow_100_chart']:
            if data:
                self.write_chart(data, self.settings['cycle_flow_100_chart'])
            else:
                logger.info("Did not match any entries for Cycle flow 100% chart")
        else:
            logger.debug("No output file specified for cycle flow chart")

    def write_chart(self, data, output_file):

        if len(data.index) == 0:
            logger.warning("Cannot draw cycle flow without data")
            return

        fig, ax = plt.subplots()

        ax.set_title("Cycle flow")
        data.plot.area(ax=ax, stacked=True, legend=False)
        ax.set_xlabel("Period of issue complete")
        ax.set_ylabel("Time spent (%)")

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        # bottom = data[data.columns[-1]].min()
        # top = data[data.columns[0]].max()
        # ax.set_ylim(bottom=bottom, top=top)

        set_chart_style()

        # Write file
        logger.info("Writing cycle flow chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)

