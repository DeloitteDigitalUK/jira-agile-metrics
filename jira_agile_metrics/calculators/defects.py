import logging
import dateutil.parser

import pandas as pd
import matplotlib.pyplot as plt

from ..calculator import Calculator
from ..utils import breakdown_by_month

logger = logging.getLogger(__name__)

class DefectsCalculator(Calculator):
    """Calculate defect concentration

    Queries JIRA with JQL set in `defects_query` and creates three stacked
    bar charts, presuming their file name values are set. Each shows the
    concentration of defects by month. The number of months to show can be
    limited with `defects_window`.

    - `defects_by_priority_chart`: Grouped by priority
      (`defects_priority_field`), optionally limited to a list of known values
      in order (`defects_priority_values`) and with title
      `defects_by_priority_chart_title`.
    - `defects_by_type_chart`: Grouped by type
      (`defects_type_field`), optionally limited to a list of known values
      in order (`defects_type_values`) and with title
      `defects_by_type_chart_title`.
    - `defects_by_environment_chart`: Grouped by environment
      (`defects_environment_field`), optionally limited to a list of known values
      in order (`defects_environment_values`) and with title
      `defects_by_environment_chart_title`.
    """

    def run(self):

        query = self.settings['defects_query']

        # This calculation is expensive. Only run it if we have a query.
        if not query:
            logger.debug("Not calculating defects chart data as no query specified")
            return None


        # Get the fields

        priority_field = self.settings['defects_priority_field']
        priority_field_id = self.query_manager.field_name_to_id(priority_field) if priority_field else None

        type_field = self.settings['defects_type_field']
        type_field_id = self.query_manager.field_name_to_id(type_field) if type_field else None

        environment_field = self.settings['defects_environment_field']
        environment_field_id = self.query_manager.field_name_to_id(environment_field) if environment_field else None

        # Get the fields
        fixversion_field = self.settings['defects_fixversion_field']
        fixversion_field_id = self.query_manager.field_name_to_id(fixversion_field) if fixversion_field else None
        # Get the fields
        team_field = self.settings['defects_team_field']
        team_field_id = self.query_manager.field_name_to_id(team_field) if fixversion_field else None

        # Build data frame
        columns = ['key', 'priority', 'type', 'environment', 'created', 'resolved','fixversion','team']
        series = {
            'key': {'data': [], 'dtype': 'str'},
            'priority': {'data': [], 'dtype': 'str'},
            'type': {'data': [], 'dtype': 'str'},
            'environment': {'data': [], 'dtype': 'str'},
            'created': {'data': [], 'dtype': 'datetime64[ns]'},
            'resolved': {'data': [], 'dtype': 'datetime64[ns]'},
            'fixversion': {'data': [], 'dtype': 'str'},
            'team': {'data': [], 'dtype': 'str'},
        }

        for issue in self.query_manager.find_issues(query, expand=None):
            series['key']['data'].append(issue.key)
            series['priority']['data'].append(self.query_manager.resolve_field_value(issue, priority_field_id) if priority_field else None)
            series['type']['data'].append(self.query_manager.resolve_field_value(issue, type_field_id) if type_field else None)
            series['environment']['data'].append(self.query_manager.resolve_field_value(issue, environment_field_id) if environment_field else None)
            series['created']['data'].append(dateutil.parser.parse(issue.fields.created))
            series['resolved']['data'].append(dateutil.parser.parse(issue.fields.resolutiondate) if issue.fields.resolutiondate else None)
            series['fixversion']['data'].append(self.query_manager.resolve_field_value(issue, fixversion_field_id) if fixversion_field else None)
            series['team']['data'].append(self.query_manager.resolve_field_value(issue, team_field_id) if team_field else None)

        data = {}
        for k, v in series.items():
            data[k] = pd.Series(v['data'], dtype=v['dtype'])

        return pd.DataFrame(data, columns=columns)

    def write(self):
        chart_data = self.get_result()
        fixversion_field = self.settings['defects_fixversion_field']
        x_label=self.settings['defects_fixversion_label']
        team_values = self.settings['defects_team_values']
        if chart_data is None:
            return

        if len(chart_data.index) == 0:
            logger.warning("Cannot draw defect charts with zero items")
            return

        if self.settings['defects_by_priority_chart']:
            self.write_defects_by_priority_chart(chart_data, self.settings['defects_by_priority_chart'],fixversion_field,x_label)

        if self.settings['defects_by_type_chart']:
            self.write_defects_by_type_chart(chart_data, self.settings['defects_by_type_chart'],fixversion_field,x_label)

        if self.settings['defects_by_environment_chart']:
            self.write_defects_by_environment_chart(chart_data, self.settings['defects_by_environment_chart'],fixversion_field,x_label)

        if self.settings['defects_by_team_chart']:
            for team in team_values:
                self.write_defects_by_team_chart(chart_data, self.settings['defects_by_team_chart'],fixversion_field,x_label,team)

    def write_defects_by_priority_chart(self, chart_data, output_file,fixversion_field,x_label):
        window = self.settings['defects_window']
        priority_values = self.settings['defects_priority_values']


        if fixversion_field:
            breakdown = chart_data.pivot_table(index=['fixversion'],values='key',columns=['priority'],aggfunc='count')
        else:
            breakdown = breakdown_by_month(chart_data, 'created', 'resolved', 'key', 'priority', priority_values)



        if window:
            breakdown = breakdown[-window:]

        if len(breakdown.index) == 0 or len(breakdown.columns) == 0:
            logger.warning("Cannot draw defects by priority chart with zero items")
            return

        fig, ax = plt.subplots()

        breakdown.plot.bar(ax=ax, stacked=True)

        if self.settings['defects_by_priority_chart_title']:
            ax.set_title(self.settings['defects_by_priority_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel(x_label, labelpad=20)
        ax.set_ylabel("Number of Defects", labelpad=10)

        if not fixversion_field:
            labels = [d.strftime("%b %y") for d in breakdown.index]
            ax.set_xticklabels(labels, rotation=90, size='small')
            ax.set_xlabel("Month", labelpad=20)


        # set_chart_style()

        # Write file
        logger.info("Writing defects by priority chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)

    def write_defects_by_type_chart(self, chart_data, output_file,fixversion_field,x_label):
        window = self.settings['defects_window']
        type_values = self.settings['defects_type_values']
        # print("Chart Data \n"+chart_data)
        # breakdown = breakdown_by_month(chart_data, 'created', 'resolved', 'key', 'type', type_values)

        if fixversion_field:
            breakdown = chart_data.pivot_table(index=['fixversion'],values='key',columns=['type'],aggfunc='count')
        else:
            breakdown = breakdown_by_month(chart_data, 'created', 'resolved', 'key', 'type', type_values)

        if window:
            breakdown = breakdown[-window:]

        if len(breakdown.index) == 0 or len(breakdown.columns) == 0:
            logger.warning("Cannot draw defects by type chart with zero items")
            return

        fig, ax = plt.subplots()

        breakdown.plot.bar(ax=ax, stacked=True)

        if self.settings['defects_by_type_chart_title']:
            ax.set_title(self.settings['defects_by_type_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel(x_label, labelpad=20)
        ax.set_ylabel("Number of Defects", labelpad=10)

        if not fixversion_field:
            labels = [d.strftime("%b %y") for d in breakdown.index]
            ax.set_xticklabels(labels, rotation=90, size='small')
            ax.set_xlabel("Month", labelpad=20)

        # set_chart_style()

        # Write file
        logger.info("Writing defects by type chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)

    def write_defects_by_environment_chart(self, chart_data, output_file,fixversion_field,x_label):
        window = self.settings['defects_window']
        environment_values = self.settings['defects_environment_values']


        if fixversion_field:
            breakdown = chart_data.pivot_table(index=['fixversion'],values='key',columns=['environment'],aggfunc='count')
        else:
            breakdown = breakdown_by_month(chart_data, 'created', 'resolved', 'key', 'environment', environment_values)

        if window:
            breakdown = breakdown[-window:]

        if len(breakdown.index) == 0 or len(breakdown.columns) == 0:
            logger.warning("Cannot draw defects by environment chart with zero items")
            return

        fig, ax = plt.subplots()

        breakdown.plot.bar(ax=ax, stacked=True)

        if self.settings['defects_by_environment_chart_title']:
            ax.set_title(self.settings['defects_by_environment_chart_title'])

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel(x_label, labelpad=20)
        ax.set_ylabel("Number of Defects", labelpad=10)

        if not fixversion_field:
            labels = [d.strftime("%b %y") for d in breakdown.index]
            ax.set_xticklabels(labels, rotation=90, size='small')
            ax.set_xlabel("Month", labelpad=20)

        # set_chart_style()

        # Write file
        logger.info("Writing defects by environment chart to %s", output_file)
        fig.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close(fig)

    def write_defects_by_team_chart(self, chart_data, output_file,fixversion_field,x_label,team):
        window = self.settings['defects_window']
        sc= chart_data.copy()
        sc.sort_values(by=['team'])
        # sc = sc.loc['team']
        # making boolean series for a team name
        filter = sc['team']==team
        # filtering data
        sc.where(filter, inplace = True)
        # sc.sort_values("team", inplace = True)

        # breakdown = breakdown_by_fixversion(chart_data,'fixversion','key', 'priority' ,fixversion_values)
        breakdown = sc.pivot_table(index=['fixversion'],values='key',columns=['priority'],aggfunc='count')
        # print(breakdown)
        if window:
            breakdown = breakdown[-window:]

        if len(breakdown.index) == 0 or len(breakdown.columns) == 0:
            logger.warning("Cannot draw defects by priority chart with zero items")
            return

        fig, ax = plt.subplots()
        # y_pos = np.arange(len('fixversion'))
        breakdown.plot.bar(ax=ax, stacked=True)
        # ax.barh(y_pos, performance, xerr=T, align='center')

        if self.settings['defects_by_team_chart_title']:
            ax.set_title(self.settings['defects_by_team_chart_title']+"- "+team)

        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_xlabel("Team - "+team, labelpad=20)
        ax.set_ylabel("Number of Defects", labelpad=10)

        # labels = breakdown.index
        # ax.set_xticklabels(labels, rotation=90, size='small')

        # set_chart_style()
        if team.find("/") !=-1:
            team=team.replace("/","_")
        # Write file
        logger.info("Writing defects by fix fixVersion chart to %s", output_file)
        fig.savefig('defects-by-team-'+team+'.png', bbox_inches='tight', dpi=300)
        plt.close(fig)
