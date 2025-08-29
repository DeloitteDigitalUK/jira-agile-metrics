import os
import argparse
import getpass
import logging

from jira import JIRA

from .config import config_to_options, CALCULATORS, ConfigError
from .webapp.app import app as webapp
from .querymanager import QueryManager
from .calculator import run_calculators
from .utils import set_chart_context
from .trello import TrelloClient
from .copilot.cli_commands import (
    AIConfigValidator,
    AIInsightsCommand,
    create_ai_config_from_settings_and_args,
)

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
        "--ai-provider",
        metavar="openai",
        help="AI provider (openai, anthropic, azure)",
    )
    parser.add_argument("--ai-model", metavar="gpt-4o", help="AI model name")
    parser.add_argument(
        "--validate-ai-config",
        action="store_true",
        help="Validate AI configuration and exit",
    )

    return parser


def main():
    parser = configure_argument_parser()
    args = parser.parse_args()

    if args.server:
        run_server(parser, args)
    elif args.validate_ai_config:
        validate_ai_configuration(parser, args)
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

    # Set charting context, which determines how charts are rendered
    set_chart_context("paper")

    # Set output directory if required
    if args.output_directory:
        logger.info("Changing working directory to %s" % args.output_directory)
        os.chdir(args.output_directory)

    # Select data source
    jira = None

    if options["connection"]["type"] == "jira":
        jira = get_jira_client(options["connection"])
    elif options["connection"]["type"] == "trello":
        jira = get_trello_client(
            options["connection"], options["settings"]["type_mapping"]
        )
    else:
        raise ConfigError("Unknown source")
    # Query JIRA and run calculators
    logger.info("Running calculators")
    query_manager = QueryManager(jira, options["settings"])

    # Add AI context generator to calculators if AI is configured
    calculators = list(CALCULATORS)
    if options["settings"].get("ai", {}).get("enabled", False):
        from .copilot.context_generator import AIContextGenerator

        calculators.append(AIContextGenerator)

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


def validate_ai_configuration(parser, args):
    """Validate AI configuration and exit."""
    if not args.config:
        parser.print_usage()
        return

    logging.basicConfig(
        format="[%(asctime)s %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
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

        # Validate configuration
        validator = AIConfigValidator(ai_config)
        is_valid, errors = validator.validate()

        if not is_valid:
            print("❌ AI Configuration Errors:")
            for error in errors:
                print(f"  - {error}")
            config_summary = validator.get_config_summary()
            print(
                f"\nAvailable providers: {', '.join(config_summary['available_providers'])}"
            )
            return

        print("✅ AI configuration is valid")
        config_summary = validator.get_config_summary()
        print(f"Provider: {config_summary['provider']}")
        print(f"Model: {config_summary['model']}")

    except Exception as e:
        print(f"❌ Configuration error: {e}")


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

        # Create command handler
        output_dir = args.output_directory
        command = AIInsightsCommand(ai_config, output_dir)

        # Check prerequisites
        context_file = options["settings"].get(
            "ai_context_file", "ai-context.json"
        )
        is_valid, error_msg = command.validate_prerequisites(context_file)
        if not is_valid:
            print(f"❌ {error_msg}")
            return

        # Generate insights
        print(
            f"🤖 Generating AI insights using {ai_config.get('provider', 'unknown')} provider..."
        )
        success, result_msg, preview = command.generate_insights(context_file)

        if success:
            print(f"✅ {result_msg}")
            print("\nPreview:")
            print("-" * 50)
            print(preview)
        else:
            print(f"❌ {result_msg}")

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Full error details:")

if __name__ == "__main__":
    main()