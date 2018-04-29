import argparse
import getpass
import json
import datetime

import dateutil.parser

import numpy as np
import pandas as pd

from jira import JIRA

from .config import config_to_options
from .cycletime import CycleTimeQueries
from . import charting

parser = argparse.ArgumentParser(description='Extract Agile metrics data from JIRA and produce data and charts.')
parser.add_argument('config', metavar='config.yml', help='Configuration file')
parser.add_argument('output', metavar='data.csv', nargs='?', help='Output file. Contains all issues described by the configuration file, metadata, and dates of entry to each state in the cycle.')
parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose output')
parser.add_argument('-n', metavar='N', dest='max_results', type=int, help='Only fetch N most recently updated issues')
parser.add_argument('--format', metavar='csv|json|xlsx', help="Output format for data (default CSV)")
parser.add_argument('--cfd', metavar='cfd.csv', help='Calculate data to draw a Cumulative Flow Diagram and write to file. Hint: Plot as a (non-stacked) area chart.')
parser.add_argument('--scatterplot', metavar='scatterplot.csv', help='Calculate data to draw a cycle time scatter plot and write to file. Hint: Plot as a scatter chart.')
parser.add_argument('--histogram', metavar='histogram.csv', help='Calculate data to draw a cycle time histogram and write to file. Hint: Plot as a column chart.')
parser.add_argument('--throughput', metavar='throughput.csv', help='Calculate daily throughput data and write to file. Hint: Plot as a column chart.')
parser.add_argument('--percentiles', metavar='percentiles.csv', help='Calculate cycle time percentiles and write to file.')

parser.add_argument('--quantiles', metavar='0.3,0.5,0.75,0.85,0.95', help="Quantiles to use when calculating percentiles")
parser.add_argument('--backlog-column', metavar='<name>', help="Name of the backlog column. Defaults to the first column.")
parser.add_argument('--committed-column', metavar='<name>', help="Name of the column from which work is considered committed. Defaults to the second column.")
parser.add_argument('--final-column', metavar='<name>', help="Name of the final 'work' column. Defaults to the penultimate column.")
parser.add_argument('--done-column', metavar='<name>', help="Name of the 'done' column. Defaults to the last column.")
parser.add_argument('--throughput-window', metavar='60', type=int, default=60, help="How many days in the past to use for calculating throughput")
parser.add_argument('--throughput-window-end', metavar=datetime.date.today().isoformat(), help="By default, the throughput window runs to today's date. Use this option to set an alternative end date for the window.")

parser.add_argument('--charts-from', metavar=(datetime.date.today() - datetime.timedelta(days=30)).isoformat(), help="Limit time window when drawing charts to start from this date")
parser.add_argument('--charts-to', metavar=datetime.date.today().isoformat(), help="Limit time window when drawing charts to end at this date")

parser.add_argument('--charts-scatterplot', metavar='scatterplot.png', help="Draw cycle time scatter plot")
parser.add_argument('--charts-scatterplot-title', metavar='"Cycle time scatter plot"', help="Title for cycle time scatter plot")

parser.add_argument('--charts-histogram', metavar='histogram.png', help="Draw cycle time histogram")
parser.add_argument('--charts-histogram-title', metavar='"Cycle time histogram"', help="Title for cycle time histogram")

parser.add_argument('--charts-cfd', metavar='cfd.png', help="Draw Cumulative Flow Diagram")
parser.add_argument('--charts-cfd-title', metavar='"Cumulative Flow Diagram"', help="Title for CFD")

parser.add_argument('--charts-throughput', metavar='throughput.png', help="Draw weekly throughput chart with trend line")
parser.add_argument('--charts-throughput-title', metavar='"Throughput trend"', help="Title for throughput chart")

parser.add_argument('--charts-burnup', metavar='burnup.png', help="Draw simple burn-up chart")
parser.add_argument('--charts-burnup-title', metavar='"Burn-up"', help="Title for burn-up charts_scatterplot")

parser.add_argument('--charts-burnup-forecast', metavar='burnup-forecast.png', help="Draw burn-up chart with Monte Carlo simulation forecast to completion")
parser.add_argument('--charts-burnup-forecast-title', metavar='"Burn-up forecast"', help="Title for burn-up forecast chart")
parser.add_argument('--charts-burnup-forecast-target', metavar='<num stories>', type=int, help="Target completion scope for forecast. Defaults to current size of backlog.")
parser.add_argument('--charts-burnup-forecast-deadline', metavar=datetime.date.today().isoformat(), help="Deadline date for completion of backlog. If set, it will be shown on the chart, and the forecast delta will also be shown.")
parser.add_argument('--charts-burnup-forecast-deadline-confidence', metavar=.85, type=float, help="Quantile to use when comparing deadline to forecast.")
parser.add_argument('--charts-burnup-forecast-trials', metavar='100', type=int, default=100, help="Number of iterations in Monte Carlo simulation.")

parser.add_argument('--charts-wip', metavar='wip', help="Draw weekly WIP box plot")
parser.add_argument('--charts-wip-title', metavar='"Weekly WIP"', help="Title for WIP chart")
parser.add_argument('--charts-wip-window', metavar='6', default=6, type=int, help="Number of weeks in the past for which to draw weekly WIP chart")

parser.add_argument('--charts-ageing-wip', metavar='ageing-wip.png', help="Draw current ageing WIP chart")
parser.add_argument('--charts-ageing-wip-title', metavar='"Ageing WIP"', help="Title for ageing WIP chart")

parser.add_argument('--charts-net-flow', metavar='net-flow.png', help="Draw weekly net flow bar chart")
parser.add_argument('--charts-net-flow-title', metavar='"Net flow"', help="Title for net flow bar chart`")
parser.add_argument('--charts-net-flow-window', metavar='6', default=6, type=int, help="Number of weeks in the past for which to draw net flow chart")

def get_jira_client(connection):
    url = connection['domain']
    username = connection['username']
    password = connection['password']
    jira_client_options = connection['jira-client-options']

    print("Connecting to", url)

    if not username:
        username = input("Username: ")

    if not password:
        password = getpass.getpass("Password: ")

    options = {'server': url}
    options.update(jira_client_options)

    return JIRA(options, basic_auth=(username, password))

def to_json_string(value):
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        return value.encode('utf-8')
    if value in (None, np.NaN, pd.NaT):
        return ""

    try:
        return str(value)
    except TypeError:
        return value

def main():
    args = parser.parse_args()

    if not args.config:
        args.print_usage()
        return

    # Configuration

    with open(args.config) as config:
        options = config_to_options(config.read())

    if args.max_results:
        options['settings']['max_results'] = args.max_results

    quantiles = [0.3, 0.5, 0.75, 0.85, 0.95]

    if args.quantiles:
        try:
            quantiles = [float(s.strip()) for s in args.quantiles.split(',')]
        except (AttributeError, ValueError,):
            print("Invalid value for --quantiles")
            args.print_usage()
            return

    output_format = args.format.lower() if args.format else 'csv'

    throughput_window_end = dateutil.parser.parse(args.throughput_window_end) if args.throughput_window_end else datetime.date.today()
    throughput_window_days = args.throughput_window

    # Query JIRA

    jira = get_jira_client(options['connection'])

    q = CycleTimeQueries(jira, **options['settings'])

    print("Fetching issues (this could take some time)")
    cycle_data = q.cycle_data(verbose=args.verbose)

    cfd_data = q.cfd(cycle_data)
    scatter_data = q.scatterplot(cycle_data)
    histogram_data = q.histogram(cycle_data)
    percentile_data = q.percentiles(cycle_data, percentiles=quantiles)

    daily_throughput_data = q.throughput_data(
        cycle_data[cycle_data['completed_timestamp'] >= (throughput_window_end - datetime.timedelta(days=throughput_window_days))],
    )

    backlog_column = args.backlog_column or cfd_data.columns[0]
    committed_column = args.committed_column or cfd_data.columns[1]
    final_column = args.final_column or cfd_data.columns[-2]
    done_column = args.done_column or cfd_data.columns[-1]

    cycle_names = [s['name'] for s in q.settings['cycle']]
    field_names = sorted(options['settings']['fields'].keys())
    query_attribute_names = [q.settings['query_attribute']] if q.settings['query_attribute'] else []

    # Write files

    if args.output:
        print("Writing cycle data to", args.output)

        header = ['ID', 'Link', 'Name'] + cycle_names + ['Type', 'Status', 'Resolution'] + field_names + query_attribute_names
        columns = ['key', 'url', 'summary'] + cycle_names + ['issue_type', 'status', 'resolution'] + field_names + query_attribute_names

        if output_format == 'json':
            values = [header] + [map(to_json_string, row) for row in cycle_data[columns].values.tolist()]
            with open(args.output, 'w') as out:
                out.write(json.dumps(values))
        elif output_format == 'xlsx':
            cycle_data.to_excel(args.output, 'Cycle data', columns=columns, header=header, index=False)
        else:
            cycle_data.to_csv(args.output, columns=columns, header=header, date_format='%Y-%m-%d', index=False)

    if args.cfd:
        print("Writing Cumulative Flow Diagram data to", args.cfd)
        if output_format == 'json':
            cfd_data.to_json(args.cfd, date_format='iso')
        elif output_format == 'xlsx':
            cfd_data.to_excel(args.cfd, 'CFD')
        else:
            cfd_data.to_csv(args.cfd)

    if args.scatterplot:
        print("Writing cycle time scatter plot data to", args.scatterplot)
        if output_format == 'json':
            scatter_data.to_json(args.scatterplot, date_format='iso')
        elif output_format == 'xlsx':
            scatter_data.to_excel(args.scatterplot, 'Scatter', index=False)
        else:
            scatter_data.to_csv(args.scatterplot, index=False)

    if args.percentiles:
        print("Writing cycle time percentiles", args.percentiles)
        if output_format == 'json':
            percentile_data.to_json(args.percentiles, date_format='iso')
        elif output_format == 'xlsx':
            percentile_data.to_frame(name='percentiles').to_excel(args.percentiles, 'Percentiles', header=True)
        else:
            percentile_data.to_csv(args.percentiles, header=True)

    if args.histogram:
        print("Writing cycle time histogram data to", args.histogram)
        if output_format == 'json':
            histogram_data.to_json(args.histogram, date_format='iso')
        elif output_format == 'xlsx':
            histogram_data.to_frame(name='histogram').to_excel(args.histogram, 'Histogram', header=True)
        else:
            histogram_data.to_csv(args.histogram, header=True)

    if args.throughput:
        print("Writing throughput data to", args.throughput)
        if output_format == 'json':
            daily_throughput_data.to_json(args.throughput, date_format='iso')
        elif output_format == 'xlsx':
            daily_throughput_data.to_excel(args.throughput, 'Throughput', header=True)
        else:
            daily_throughput_data.to_csv(args.throughput, header=True)

    # Output charts (if we have the right things installed)
    charts_from = dateutil.parser.parse(args.charts_from) if args.charts_from is not None else None
    charts_to = dateutil.parser.parse(args.charts_to) if args.charts_to is not None else None

    cycle_data_sliced = cycle_data
    if charts_from is not None:
        cycle_data_sliced = cycle_data[cycle_data['completed_timestamp'] >= charts_from]
    if charts_to is not None:
        cycle_data_sliced = cycle_data_sliced[cycle_data_sliced['completed_timestamp'] <= charts_to]
    
    cfd_data_sliced = cfd_data[slice(charts_from, charts_to)]
    
    charting.set_context()

    if args.charts_scatterplot:
        print("Drawing scatterplot in", args.charts_scatterplot)
        charting.set_style('darkgrid')
        try:
            ax = charting.cycle_time_scatterplot(
                cycle_data_sliced,
                percentiles=quantiles,
                title=args.charts_scatterplot_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_scatterplot, bbox_inches='tight', dpi=300)

    if args.charts_histogram:
        print("Drawing histogram in", args.charts_histogram)
        charting.set_style('darkgrid')
        try:
            ax = charting.cycle_time_histogram(
                cycle_data_sliced,
                percentiles=quantiles,
                title=args.charts_histogram_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_histogram, bbox_inches='tight', dpi=300)

    if args.charts_cfd:
        print("Drawing CFD in", args.charts_cfd)
        charting.set_style('whitegrid')
        try:
            ax = charting.cfd(
                cfd_data_sliced,
                title=args.charts_cfd_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_cfd, bbox_inches='tight', dpi=300)

    if args.charts_throughput:
        print("Drawing throughput chart in", args.charts_throughput)
        charting.set_style('darkgrid')
        try:
            ax = charting.throughput_trend_chart(
                daily_throughput_data,
                title=args.charts_throughput_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_throughput, bbox_inches='tight', dpi=300)

    if args.charts_burnup:
        print("Drawing burnup chart in", args.charts_burnup)
        charting.set_style('whitegrid')
        try:
            ax = charting.burnup(
                cfd_data_sliced,
                backlog_column=backlog_column,
                done_column=done_column,
                title=args.charts_burnup_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_burnup, bbox_inches='tight', dpi=300)

    if args.charts_burnup_forecast:
        target = args.charts_burnup_forecast_target or None
        trials = args.charts_burnup_forecast_trials or 100
        deadline = dateutil.parser.parse(args.charts_burnup_forecast_deadline) if args.charts_burnup_forecast_deadline else None
        deadline_confidence = args.charts_burnup_forecast_deadline_confidence
        
        print("Drawing burnup forecast chart in", args.charts_burnup_forecast)
        charting.set_style('whitegrid')
        try:
            ax = charting.burnup_forecast(
                cfd_data_sliced,
                daily_throughput_data,
                trials=trials,
                target=target,
                backlog_column=backlog_column,
                done_column=done_column,
                percentiles=quantiles,
                deadline=deadline,
                deadline_confidence=deadline_confidence,
                title=args.charts_burnup_forecast_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_burnup_forecast, bbox_inches='tight', dpi=300)

    if args.charts_wip:
        print("Drawing WIP chart in", args.charts_wip)
        charting.set_style('darkgrid')
        try:
            ax = charting.wip_chart(
                q.cfd(cycle_data[cycle_data[backlog_column] >= (datetime.date.today() - datetime.timedelta(weeks=(args.charts_wip_window or 6)))]),
                start_column=committed_column,
                end_column=final_column,
                title=args.charts_wip_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_wip, bbox_inches='tight', dpi=300)

    if args.charts_ageing_wip:
        print("Drawing ageing WIP chart in", args.charts_ageing_wip)
        charting.set_style('whitegrid')
        try:
            ax = charting.ageing_wip_chart(
                cycle_data,
                start_column=committed_column,
                end_column=final_column,
                done_column=done_column,
                title=args.charts_ageing_wip_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_ageing_wip, bbox_inches='tight', dpi=300)

    if args.charts_net_flow:
        print("Drawing net flow chart in", args.charts_net_flow)
        charting.set_style('darkgrid')
        try:
            ax = charting.net_flow_chart(
                q.cfd(cycle_data[cycle_data[backlog_column] >= (datetime.date.today() - datetime.timedelta(weeks=(args.charts_net_flow_window or 6)))]),
                start_column=committed_column,
                end_column=done_column,
                title=args.charts_net_flow_title
            )
        except charting.UnchartableData as e:
            print("** WARNING: Did not draw chart:", e)
        else:
            fig = ax.get_figure()
            fig.savefig(args.charts_net_flow, bbox_inches='tight', dpi=300)

    print("Done")
