"""Posts diagrams to Slack after the calculators have run.

To be run as an independent command - no depency to the main application.
"""

try:
    # Optional dependency
    import slack_sdk
except ImportError as e:
    raise ImportError("You need to install slack-sdk package https://pypi.org/project/slack-sdk/") from e

import sys
import os
import argparse
import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)



def configure_argument_parser():
    """Configure an ArgumentParser that manages command line options.
    """
    parser = argparse.ArgumentParser(description='Post JIRA Agile charts to slack.')
    parser.add_argument('--api-key', metavar='api_key', help='Slack API key', required=True)
    parser.add_argument('--channel', metavar='channel', help='Slack channel where to post', required=True)
    parser.add_argument('--diagrams', metavar='diagram_list', help='Slack API key', nargs='+', required=True)
    return parser


def main():
    parser = configure_argument_parser()
    args = parser.parse_args()

    # https://pypi.org/project/slack-sdk/
    client = WebClient(token=args.api_key)

    try:
        logger.info("Posting to %s", args.channel)
        response = client.chat_postMessage(channel=args.channel, text="Hello world!")
        assert response["message"]["text"] == "Hello world!"
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")
