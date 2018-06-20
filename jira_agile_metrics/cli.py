import os
import argparse
import getpass
import logging

from jira import JIRA

from .config import config_to_options, CALCULATORS
from .webapp.app import app as webapp
from .querymanager import QueryManager
from .calculator import run_calculators
from .utils import set_chart_context

logger = logging.getLogger(__name__)

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

    # Output directory
    parser.add_argument('--output-directory', metavar='metrics', help="Write output files to this directory, rather than the current working directory.")

    # Connection options
    parser.add_argument('--domain', metavar='https://my.jira.com', help='JIRA domain name')
    parser.add_argument('--username', metavar='user', help='JIRA user name')
    parser.add_argument('--password', metavar='password', help='JIRA password')
    parser.add_argument('--http-proxy', metavar='https://proxy.local', help='URL to HTTP Proxy')
    parser.add_argument('--https-proxy', metavar='https://proxy.local', help='URL to HTTPS Proxy')

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
    http_proxy = connection['http_proxy']
    https_proxy = connection['https_proxy']

    jira_client_options = connection['jira_client_options']

    logger.info("Connecting to %s", url)

    if not username:
        username = input("Username: ")

    if not password:
        password = getpass.getpass("Password: ")

    options = {'server': url}
    proxies = None

    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy

    options.update(jira_client_options)

    return JIRA(options, basic_auth=(username, password), proxies=proxies)
