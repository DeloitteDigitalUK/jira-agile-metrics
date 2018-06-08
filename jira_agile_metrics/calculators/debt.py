import logging
import datetime
import dateutil.parser

import pandas as pd
import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import breakdown_by_month, set_chart_style, to_bin

logger = logging.getLogger(__name__)

class DebtCalculator(Calculator):
    """Calculate technical debt over time.

    Queries JIRA with JQL set in `debt_query` and draws a stacked bar
    chart in the file `debt_chart` with title `debt_chart_title`. The bars are
    the last 6 months (or another window set in `debt_window`), grouped by
    priority. The field giving the priority is set with `debt_chart_priority`.
    To force the list of valid values and their order, provide a list of strings
    in `debt_priority_values`.

    Also draw a stacked bar chart in the file `debt_age_chart`, with title
    `debt_age_chart_title`, grouping by item age.
    """

    def run(self, now=None):

        query = self.settings['debt_query']

        # Allows unit testing to use a fixed date
        if now is None:
            now = datetime.datetime.utcnow()

        # This calculation is expensive. Only run it if we have a query.
        if not query:
            logger.debug("Not calculating debt chart data as no query specified")
            return None
        
        # Resolve field name to field id for later lookup
        priority_field = self.settings['debt_priority_field']
        priority_field_id = priority_field_id = self.query_manager.field_name_to_id(priority_field) if priority_field else None

        # Build data frame
        columns = ['key', 'priority', 'created', 'resolved', 'age']
        series = {
            'key': {'data': [], 'dtype': 'str'},
            'priority': {'data': [], 'dtype': 'str'},
            'created': {'data': [], 'dtype': 'datetime64[ns]'},
            'resolved': {'data': [], 'dtype': 'datetime64[ns]'},
            'age': {'data': [], 'dtype': 'timedelta64[ns]'},
        }

        for issue in self.query_manager.find_issues(query, expand=None):
            created_date = dateutil.parser.parse(issue.fields.created)
            resolved_date = dateutil.parser.parse(issue.fields.resolutiondate) if issue.fields.resolutiondate else None

            series['key']['data'].append(issue.key)
            series['priority']['data'].append(self.query_manager.resolve_field_value(issue, priority_field_id) if priority_field else None)
            series['created']['data'].append(created_date)
            series['resolved']['data'].append(resolved_date)
            series['age']['data'].append((resolved_date.replace(tzinfo=None) if resolved_date is not None else now) - created_date.replace(tzinfo=None))

        data = {}
        for k, v in series.items():
            data[k] = pd.Series(v['data'], dtype=v['dtype'])

        return pd.DataFrame(data, columns=columns)

    def write(self):
        chart_data = self.get_result()
        if chart_data is None:
            return

        if len(chart_data.index) == 0:
            logger.warning("Cannot draw debt chart with zero items")
            return
        
        if self.settings['debt_chart']:
            self.write_debt_chart(chart_data, self.settings['debt_chart'])
        
        if self.settings['debt_age_chart']:
            self.write_debt_age_chart(chart_data, self.settings['debt_age_chart'])
    
    def write_debt_chart(self, chart_data, output_file):
        window = self.settings['debt_window']
        priority_values = self.settings['debt_priority_values']

        breakdown = breakdown_by_month(chart_data, 'created', 'resolved', 'key', 'priority', priority_values)
        
        if window:
            breakdown = breakdown[-window:]

        fig, ax = plt.subplots()
        
        breakdown.plot.bar(ax=ax, stacked=True)
        
        if self.settings['debt_chart_title']:
            ax.set_title(self.settings['debt_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Month", labelpad=20)
        ax.set_ylabel("Number of items", labelpad=10)

        labels = [d.strftime("%b %y") for d in breakdown.index]
        ax.set_xticklabels(labels, rotation=90, size='small')

        set_chart_style()

        # Write file
        logger.info("Writing debt chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
    
    def write_debt_age_chart(self, chart_data, output_file):
        priority_values = self.settings['debt_priority_values']
        bins = self.settings['debt_age_chart_bins']
        
        def generate_bin_label(v):
            low, high = to_bin(v, bins)
            return "> %d days" % (low,) if high is None else "%d-%d days" % (low, high,)

        def day_grouper(value):
            if isinstance(value, pd.Timedelta):
                return generate_bin_label(value.days)

        bin_labels = list(map(generate_bin_label, bins + [bins[-1] + 1]))
        breakdown = chart_data.pivot_table(
            index='age',
            columns='priority',
            values='key',
            aggfunc='count'
        ).groupby(day_grouper).sum().reindex(bin_labels).T
        
        if priority_values:
            breakdown = breakdown.reindex(priority_values)

        fig, ax = plt.subplots()
        
        breakdown.plot.barh(ax=ax, stacked=True)
        
        if self.settings['debt_age_chart_title']:
            ax.set_title(self.settings['debt_age_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Number of items", labelpad=20)
        ax.set_ylabel("Priority", labelpad=10)

        set_chart_style()

        # Write file
        logger.info("Writing debt age chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)
