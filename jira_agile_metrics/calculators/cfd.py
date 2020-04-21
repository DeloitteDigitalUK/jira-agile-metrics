import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import get_extension, set_chart_style

from .cycletime import CycleTimeCalculator

logger = logging.getLogger(__name__)

class CFDCalculator(Calculator):
    """Create the data to build a cumulative flow diagram: a DataFrame,
    indexed by day, with columns containing cumulative counts for each
    of the items in the configured cycle.

    In addition, a column called `cycle_time` contains the approximate
    average cycle time of that day based on the first "accepted" status
    and the first "complete" status.

    Write as a data file and/or a diagram.
    """

    def run(self):
        cycle_data = self.get_result(CycleTimeCalculator)
        cycle_names = [s['name'] for s in self.settings['cycle']]

        return calculate_cfd_data(cycle_data, cycle_names)
    
    def write(self):
        data = self.get_result()

        if self.settings['cfd_data']:
            self.write_file(data, self.settings['cfd_data'])
        else:
            logger.debug("No output file specified for CFD file")
        
        if self.settings['cfd_chart']:
            self.write_chart(data, self.settings['cfd_chart'])
        else:
            logger.debug("No output file specified for CFD chart")

    def write_file(self, data, output_files):
        for output_file in output_files:
            output_extension = get_extension(output_file)

            logger.info("Writing CFD data to %s", output_file)
            if output_extension == '.json':
                data.to_json(output_file, date_format='iso')
            elif output_extension == '.xlsx':
                data.to_excel(output_file, 'CFD')
            else:
                data.to_csv(output_file)
    
    def write_chart(self, data, output_file):
        if len(data.index) == 0:
            logger.warning("Cannot draw CFD with no data")
            return
        
        window = self.settings['cfd_window']
        if window:
            start = data.index.max() - pd.Timedelta(window, 'D')
            data = data[start:]
        
            # Re-check after slicing
            if len(data.index) == 0:
                logger.warning("Cannot draw CFD with no data")
                return

        fig, ax = plt.subplots()
        
        if self.settings['cfd_chart_title']:
            ax.set_title(self.settings['cfd_chart_title'])

        fig.autofmt_xdate()

        ax.set_xlabel("Date")
        ax.set_ylabel("Number of items")

        backlog_column = self.settings['backlog_column']

        if backlog_column not in data.columns:
            logger.error("Backlog column %s does not exist", backlog_column)
            return None

        data = data.drop([backlog_column], axis=1)
        data.plot.area(ax=ax, stacked=False, legend=False)

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        bottom = data[data.columns[-1]].min()
        top = data[data.columns[0]].max()
        ax.set_ylim(bottom=bottom, top=top)

        set_chart_style()

        # Write file
        logger.info("Writing CFD chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)

def calculate_cfd_data(cycle_data, cycle_names):

    # Build a dataframe of just the "date" columns
    cfd_data = cycle_data[cycle_names]

    # Strip out times from all dates
    cfd_data = pd.DataFrame(
        np.array(cfd_data.values, dtype='<M8[ns]').astype('<M8[D]').astype('<M8[ns]'),
        columns=cfd_data.columns,
        index=cfd_data.index
    )

    # Replace missing NaT values (happens if a status is skipped) with the subsequent timestamp
    cfd_data = cfd_data.fillna(method='bfill', axis=1)

    # Count number of times each date occurs, preserving column order
    cfd_data = pd.concat({col: cfd_data[col].value_counts() for col in cfd_data}, axis=1)[cycle_names]

    # Fill missing dates with 0 and run a cumulative sum
    cfd_data = cfd_data.fillna(0).cumsum(axis=0).sort_index()

    # Reindex to make sure we have all dates
    start, end = cfd_data.index.min(), cfd_data.index.max()
    if start is not pd.NaT and end is not pd.NaT:
        cfd_data = cfd_data.reindex(pd.date_range(start, end, freq='D'), method='ffill')

    return cfd_data
