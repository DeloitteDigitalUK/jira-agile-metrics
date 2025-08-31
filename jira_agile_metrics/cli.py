import os
import argparse
import getpass
import logging
import datetime

from jira import JIRA

from .config import config_to_options, CALCULATORS, ConfigError
from .webapp.app import app as webapp
from .querymanager import QueryManager
from .calculator import run_calculators
from .utils import set_chart_context, set_current_time_override
from .trello import TrelloClient
from .copilot.cli_commands import (
    AIConfigValidator,
    AIInsightsCommand,
    create_ai_config_from_settings_and_args,
)
from .datasources.csv_source import CSVDataSource
from .calculators.defects import DefectsCalculator
from .calculators.debt import DebtCalculator
from .calculators.waste import WasteCalculator
from .calculators.progressreport import ProgressReportCalculator

logger = logging.getLogger(__name__)


def configure_argument_parser():
    """Configure an ArgumentParser that manages command line options."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract Agile metrics data from JIRA/"
            "Trello and produce data and charts."
        )
    )

    # Basic options
    parser.add_argument(
        "config", metavar="config.yml", nargs="?", help="Configuration file"
    )
    parser.add_argument(
        "-v", dest="verbose", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "-vv",
        dest="very_verbose",
        action="store_true",
        help="Even more verbose output",
    )
    parser.add_argument(
        "-n",
        metavar="N",
        dest="max_results",
        type=int,
        help="Only fetch N most recently updated issues",
    )

    parser.add_argument(
        "--server",
        metavar="127.0.0.1:8080",
        help=(
            "Run as a web server instead of a command line tool, "
            "on the given host and/or port."
            "The remaining options do not apply."
        ),
    )

    # Output directory
    parser.add_argument(
        "--output-directory",
        "-o",
        metavar="metrics",
        help=(
            "Write output files to this directory,"
            "rather than the current working directory."
        ),
    )

    # Connection options
    parser.add_argument(
        "--domain", metavar="https://my.jira.com", help="JIRA domain name"
    )
    parser.add_argument(
        "--username", metavar="user", help="JIRA/Trello user name"
    )
    parser.add_argument("--password", metavar="password", help="JIRA password")
    parser.add_argument("--key", metavar="key", help="Trello API key")
    parser.add_argument("--token", metavar="token", help="Trello API password")
    parser.add_argument(
        "--http-proxy", metavar="https://proxy.local", help="URL to HTTP Proxy"
    )
    parser.add_argument(
        "--https-proxy",
        metavar="https://proxy.local",
        help="URL to HTTPS Proxy",
    )
    parser.add_argument(
        "--jira-server-version-check",
        type=bool,
        metavar="True",
        help=(
            "If true it will fetch JIRA server version info first"
            "to determine if some API calls are available"
        ),
    )

    # AI Copilot options
    parser.add_argument(
        "--generate-insights",
        action="store_true",
        help="Generate AI-powered daily insights from metrics data",
    )
    parser.add_argument(
        "--cycle-data-file",
        metavar="path/to/cycletime.csv",
        help=(
            "Path to an exported cycletime.csv or cycletime.json that can be used to preload cycle data instead of querying JIRA"
        ),
    )
    parser.add_argument(
        "--ai-context-file",
        metavar="ai-context.json",
        help=(
            "Override the Copilot context file path (defaults to settings.ai_context_file or ai-context.json)"
        ),
    )
    # Provider/model are configured in YAML; no CLI overrides required
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print AI prompts and payloads without making API calls. For use with --generate-insights.",
    )

    # Date override for testing and historical analysis
    parser.add_argument(
        "--current-date",
        metavar="YYYY-MM-DD",
        help=(
            "Override the current date for calculations. "
            "Useful for testing or analyzing historical data. "
            "Format: YYYY-MM-DD (e.g., 2024-01-15)"
        ),
    )

    return parser


def main():
    parser = configure_argument_parser()
    args = parser.parse_args()

    if args.server:
        run_server(parser, args)
    elif args.generate_insights:
        generate_ai_insights(parser, args)
    else:
        run_command_line(parser, args)


def run_server(parser, args):
    host = None
    port = args.server

    if ":" in args.server:
        (host, port) = args.server.split(":")
    port = int(port)

    set_chart_context("paper")
    webapp.run(host=host, port=port)


def run_command_line(parser, args):
    if not args.config:
        parser.print_usage()
        return

    logging.basicConfig(
        format="[%(asctime)s %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=(
            logging.DEBUG
            if args.very_verbose
            else logging.INFO if args.verbose else logging.WARNING
        ),
    )

    # Configuration and settings
    # (command line arguments override config file options)

    logger.debug("Parsing options from %s", args.config)
    with open(args.config) as config:
        options = config_to_options(
            config.read(), cwd=os.path.dirname(os.path.abspath(args.config))
        )

    # Allow command line arguments to override options
    override_options(options["connection"], args)
    override_options(options["settings"], args)

    # Handle current date override if specified
    if args.current_date:
        try:
            override_date = datetime.datetime.strptime(args.current_date, "%Y-%m-%d")
            set_current_time_override(override_date)
            logger.info("Using override date: %s", args.current_date)
        except ValueError:
            raise ConfigError(
                f"Invalid date format '{args.current_date}'. "
                "Expected format: YYYY-MM-DD (e.g., 2024-01-15)"
            )

    # Set charting context, which determines how charts are rendered
    set_chart_context("paper")

    # Resolve CSV file path before changing directories
    csv_file_path = None
    if args.cycle_data_file:
        csv_file_path = os.path.abspath(args.cycle_data_file)
        logger.info("Using offline CSV data source: %s", csv_file_path)

    # Set output directory if required
    if args.output_directory:
        logger.info("Changing working directory to %s" % args.output_directory)
        os.chdir(args.output_directory)

    # Select data source (online JIRA/Trello or offline CSV)
    jira = None
    data_source = None
    if csv_file_path:
        data_source = CSVDataSource(csv_file_path, options["settings"])
    elif options["connection"]["type"] == "jira":
        jira = get_jira_client(options["connection"])
    elif options["connection"]["type"] == "trello":
        jira = get_trello_client(options["connection"], options["settings"]["type_mapping"])
    else:
        raise ConfigError("Unknown source")
        # Query JIRA and run calculators
    logger.info("Running calculators")
    query_manager = QueryManager(jira, options["settings"], data_source=data_source)

    # Build calculators list
    calculators = list(CALCULATORS)
    
    # Check for unsafe calculators when using CSV data source
    if args.cycle_data_file:
        validate_csv_calculator_compatibility(calculators, options["settings"])
    
    # Append AIContextGenerator only when AI options are configured and core workflow settings exist
    settings_dict = options["settings"]
    has_core_workflow = (
        bool(settings_dict.get("cycle"))
        and ("committed_column" in settings_dict)
        and ("done_column" in settings_dict)
        and ("backlog_column" in settings_dict)
    )
    # Copilot configured via settings (ai dict or ai_context_file)
    ai_settings = settings_dict.get("ai", {}) or {}
    has_ai_options = (
        bool(ai_settings)  # any copilot settings present
        or bool(settings_dict.get("ai_context_file"))  # Copilot Context file configured in Output
    )
    if has_core_workflow and has_ai_options:
        from .copilot.context_generator import AIContextGenerator

        calculators.append(AIContextGenerator)
    else:
        logger.info(
            "Skipping Copilot context generation (copilot options or required workflow settings missing)"
        )

    run_calculators(calculators, query_manager, options["settings"])


def override_options(options, arguments):
    """Update `options` dict with settings from `arguments`
    with the same key.
    """
    for key in options.keys():
        if getattr(arguments, key, None) is not None:
            options[key] = getattr(arguments, key)


def get_jira_client(connection):
    url = connection["domain"]
    username = connection["username"]
    password = connection["password"]
    http_proxy = connection["http_proxy"]
    https_proxy = connection["https_proxy"]
    jira_server_version_check = connection["jira_server_version_check"]

    jira_client_options = connection["jira_client_options"]

    logger.info("Connecting to %s", url)

    if not username:
        username = input("Username: ")

    if not password:
        password = getpass.getpass("Password: ")

    options = {"server": url}
    proxies = None

    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy:
            proxies["http"] = http_proxy
        if https_proxy:
            proxies["https"] = https_proxy

    options.update(jira_client_options)

    return JIRA(
        options,
        basic_auth=(username, password),
        proxies=proxies,
        get_server_info=jira_server_version_check,
    )


def get_trello_client(connection, type_mapping):
    username = connection["username"]
    key = connection["key"]
    token = connection["token"]

    if not username:
        username = input("Username: ")

    if not key:
        key = getpass.getpass("Key: ")

    if not token:
        token = getpass.getpass("Token: ")

    return TrelloClient(username, key, token, type_mapping=type_mapping)


    # duplicate removed; single definition exists above


def generate_ai_insights(parser, args):
    """Generate AI insights from existing context file."""
    if not args.config:
        parser.print_usage()
        return

    logging.basicConfig(
        format="[%(asctime)s %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO if args.verbose else logging.WARNING,
    )

    try:
        with open(args.config) as config:
            options = config_to_options(
                config.read(),
                cwd=os.path.dirname(os.path.abspath(args.config)),
            )

        # Create AI config from settings and args
        ai_config = create_ai_config_from_settings_and_args(
            options["settings"], args
        )

        # Determine context file path (allow override)
        context_file = (
            args.ai_context_file
            if args.ai_context_file
            else options["settings"].get("ai_context_file", "ai-context.json")
        )

        # Determine insights output file path
        insights_file = options["settings"].get("ai_insights_file", "daily-insights.md")

        # Create command handler
        output_dir = args.output_directory
        command = AIInsightsCommand(ai_config, output_dir)

        # Check prerequisites (context file must now exist)
        is_valid, error_msg = command.validate_prerequisites(context_file)
        if not is_valid:
            print(f"❌ {error_msg}")
            return

        # Generate insights
        print(
            f"🤖 Generating AI insights using {ai_config.get('provider', 'unknown')} provider..."
        )
        success, result_msg, preview = command.generate_insights(context_file, insights_file)

        if success:
            if args.dry_run:
                print(f"✅ {result_msg}")
                # Preview in dry run contains the prompt and payload
                print(preview)  
            else:
                print(f"✅ {result_msg}")
                print("\nPreview:")
                print("-" * 50)
                print(preview)
        else:
            print(f"❌ {result_msg}")

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Full error details:")


def validate_csv_calculator_compatibility(calculators, settings):
    """Validate that calculators are compatible with CSV data source mode.
    
    Raises ConfigError if any unsafe calculators are configured to run.
    """
    # Define calculators that require JIRA connectivity
    JIRA_DEPENDENT_CALCULATORS = {
        DefectsCalculator: "defects_query",
        DebtCalculator: "debt_query", 
        WasteCalculator: "waste_query",
        ProgressReportCalculator: "progress_report"
    }
    
    unsafe_calculators = []
    
    for calculator_class in calculators:
        if calculator_class in JIRA_DEPENDENT_CALCULATORS:
            setting_key = JIRA_DEPENDENT_CALCULATORS[calculator_class]
            
            # Check if this calculator is actually configured to run
            if settings.get(setting_key):
                unsafe_calculators.append({
                    'name': calculator_class.__name__,
                    'setting': setting_key
                })
    
    if unsafe_calculators:
        error_msg = (
            "Cannot use --cycle-data-file with calculators that require JIRA connectivity.\n"
            "The following calculators are configured but incompatible with CSV mode:\n"
        )
        for calc in unsafe_calculators:
            error_msg += f"  - {calc['name']} (configured via '{calc['setting']}')\n"
        
        error_msg += (
            "\nTo use CSV mode, either:\n"
            "  1. Remove/comment out the incompatible settings from your config file, or\n"
            "  2. Run without --cycle-data-file to use live JIRA data\n"
            "\nCompatible calculators include: cycle time, CFD, scatterplot, histogram, "
            "percentiles, throughput, burnup, WIP, net flow, ageing WIP, forecast, and impediments."
        )
        
        raise ConfigError(error_msg)


if __name__ == "__main__":
    main()