import os
import argparse
import getpass
import datetime
import logging

import dateutil.parser

from jira import JIRA

from .config import config_to_options, CALCULATORS
from .webapp.app import app as webapp
from .querymanager import QueryManager
from .calculator import run_calculators
from .utils import set_chart_context

logger = logging.getLogger(__name__)

def to_quantiles(quantiles):
    return [float(s.strip()) for s in quantiles.split(',') if s]

def configure_argument_parser():
    """Configure an ArgumentParser that manages command line options.
    """

    parser = argparse.ArgumentParser(description='Extract Agile metrics data from JIRA and produce data and charts.')

    # Basic options
    parser.add_argument('config', metavar='config.yml', nargs='?', help='Configuration file')
    parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose output')
    parser.add_argument('-vv', dest='very_verbose', action='store_true', help='Even more verbose output')
    parser.add_argument('-n', metavar='N', dest='max_results', type=int, help='Only fetch N most recently updated issues')
    
    parser.add_argument('--server', metavar='127.0.0.1:8080', help='Run as a web server instead of a command line tool, on the given host and/or port. The remaining options do not apply.')

    # Output directory and bulk mode

    parser.add_argument('--output-directory', metavar='metrics', help="Write output files to this directory, rather than the current working directory.")

    # Connection options
    parser.add_argument('--domain', metavar='https://my.jira.com', help='JIRA domain name')
    parser.add_argument('--username', metavar='user', help='JIRA user name')
    parser.add_argument('--password', metavar='password', help='JIRA password')

    # Settings
    parser.add_argument('--quantiles', metavar='0.5,0.85,0.95', type=to_quantiles, help="Quantiles to use when calculating percentiles")
    parser.add_argument('--backlog-column', metavar='<name>', help="Name of the backlog column. Defaults to the first column.")
    parser.add_argument('--committed-column', metavar='<name>', help="Name of the column from which work is considered committed. Defaults to the second column.")
    parser.add_argument('--final-column', metavar='<name>', help="Name of the final 'work' column. Defaults to the penultimate column.")
    parser.add_argument('--done-column', metavar='<name>', help="Name of the 'done' column. Defaults to the last column.")
    
    parser.add_argument('--throughput-frequency', metavar="1W", help="Interval to use for calculating frequency, e.g. 1D for daily or 1W for weekly")

    parser.add_argument('--cycle-time-data', metavar='cycles.csv', help='Output file suitable for processing Actionable Agile. Contains all issues described by the configuration file, metadata, and dates of entry to each state in the cycle.')
    parser.add_argument('--cfd-data', metavar='cfd.csv', help='Calculate data to draw a Cumulative Flow Diagram and write to file. Hint: Plot as a (non-stacked) area chart.')
    parser.add_argument('--scatterplot-data', metavar='scatterplot.csv', help='Calculate data to draw a cycle time scatter plot and write to file. Hint: Plot as a scatter chart.')
    parser.add_argument('--histogram-data', metavar='histogram.csv', help='Calculate data to draw a cycle time histogram and write to file. Hint: Plot as a column chart.')
    parser.add_argument('--throughput-data', metavar='throughput.csv', help='Calculate daily throughput data and write to file. Hint: Plot as a column chart.')
    parser.add_argument('--percentiles-data', metavar='percentiles.csv', help='Calculate cycle time percentiles and write to file.')

    parser.add_argument('--scatterplot-chart', metavar='scatterplot.png', help="Draw cycle time scatter plot")
    parser.add_argument('--scatterplot-chart-title', metavar='"Cycle time scatter plot"', help="Title for cycle time scatter plot")

    parser.add_argument('--histogram-chart', metavar='histogram.png', help="Draw cycle time histogram")
    parser.add_argument('--histogram-chart-title', metavar='"Cycle time histogram"', help="Title for cycle time histogram")

    parser.add_argument('--cfd-chart', metavar='cfd.png', help="Draw Cumulative Flow Diagram")
    parser.add_argument('--cfd-chart-title', metavar='"Cumulative Flow Diagram"', help="Title for CFD")

    parser.add_argument('--throughput-chart', metavar='throughput.png', help="Draw weekly throughput chart with trend line")
    parser.add_argument('--throughput-chart-title', metavar='"Throughput trend"', help="Title for throughput chart")

    parser.add_argument('--burnup-chart', metavar='burnup.png', help="Draw simple burn-up chart")
    parser.add_argument('--burnup-chart-title', metavar='"Burn-up"', help="Title for burn-up charts_scatterplot")

    parser.add_argument('--burnup-forecast-chart', metavar='burnup-forecast.png', help="Draw burn-up chart with Monte Carlo simulation forecast to completion")
    parser.add_argument('--burnup-forecast-chart-title', metavar='"Burn-up forecast"', help="Title for burn-up forecast chart")
    parser.add_argument('--burnup-forecast-chart-target', metavar='<num stories>', type=int, help="Target completion scope for forecast. Defaults to current size of backlog.")
    parser.add_argument('--burnup-forecast-chart-deadline', metavar=datetime.date.today().isoformat(), type=dateutil.parser.parse, help="Deadline date for completion of backlog. If set, it will be shown on the chart, and the forecast delta will also be shown.")
    parser.add_argument('--burnup-forecast-chart-deadline-confidence', metavar=.85, type=float, help="Quantile to use when comparing deadline to forecast.")
    parser.add_argument('--burnup-forecast-chart-trials', metavar='100', type=int, default=100, help="Number of iterations in Monte Carlo simulation.")
    parser.add_argument('--burnup-forecast-chart-throughput-window', metavar='60', type=int, default=60, help="How many days in the past to use for calculating throughput")
    parser.add_argument('--burnup-forecast-chart-throughput-window-end', metavar=datetime.date.today().isoformat(), type=dateutil.parser.parse, help="By default, the throughput window runs to today's date. Use this option to set an alternative end date for the window.")

    parser.add_argument('--wip-chart', metavar='wip', help="Draw weekly WIP box plot")
    parser.add_argument('--wip-chart-title', metavar='"Weekly WIP"', help="Title for WIP chart")
    parser.add_argument('--wip-chart-frequency', metavar='1W-MON', default="1W-MON", help="Frequency interval for WIP chart (1W-Mon means 1 week, starting Mondays)")

    parser.add_argument('--ageing-wip-chart', metavar='ageing-wip.png', help="Draw current ageing WIP chart")
    parser.add_argument('--ageing-wip-chart-title', metavar='"Ageing WIP"', help="Title for ageing WIP chart")

    parser.add_argument('--net-flow-chart', metavar='net-flow.png', help="Draw weekly net flow bar chart")
    parser.add_argument('--net-flow-chart-title', metavar='"Net flow"', help="Title for net flow bar chart`")
    parser.add_argument('--net-flow-chart-frequency', metavar='1W-MON', default="1W-MON", help="Frequency interval for net flow chart (1W-Mon means 1 week, starting Mondays)")

    return parser

def main():
    parser = configure_argument_parser()
    args = parser.parse_args()

    if args.server:
        run_server(parser, args)
    else:
        run_command_line(parser, args)

def run_server(parser, args):
    host = None
    port = args.server
    
    if ':' in args.server:
        (host, port) = args.server.split(':')
    port = int(port)

    set_chart_context("paper")
    webapp.run(host=host, port=port)

def run_command_line(parser, args):
    if not args.config:
        parser.print_usage()
        return
    
    logging.basicConfig(
        format='%(message)s',
        level=(
            logging.DEBUG if args.very_verbose else
            logging.INFO if args.verbose else
            logging.WARNING
        )
    )

    # Configuration and settings (command line arguments override config file options)

    logger.debug("Parsing options from %s", args.config)
    with open(args.config) as config:
        options = config_to_options(config.read())

    # Allow command line arguments to override options
    override_options(options['connection'], args)
    override_options(options['settings'], args)

    # Set charting context, which determines how charts are rendered
    set_chart_context("paper")

    # Set output directory if required
    if args.output_directory:
        logger.info("Changing working directory to %s" % args.output_directory)
        os.chdir(args.output_directory)

    # Query JIRA and run calculators

    jira = get_jira_client(options['connection'])

    logger.info("Running calculators")
    query_manager = QueryManager(jira, options['settings'])
    run_calculators(CALCULATORS, query_manager, options['settings'])

def override_options(options, arguments):
    """Update `options` dict with settings from `arguments`
    with the same key.
    """
    for key in options.keys():
        if getattr(arguments, key, None) is not None:
            options[key] = getattr(arguments, key)

def get_jira_client(connection):
    url = connection['domain']
    username = connection['username']
    password = connection['password']
    jira_client_options = connection['jira_client_options']

    logger.info("Connecting to %s", url)

    if not username:
        username = input("Username: ")

    if not password:
        password = getpass.getpass("Password: ")

    options = {'server': url}
    options.update(jira_client_options)

    return JIRA(options, basic_auth=(username, password))
