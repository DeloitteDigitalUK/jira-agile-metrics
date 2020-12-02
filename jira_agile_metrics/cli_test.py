import json
import tempfile

from .cli import (
    override_options,
    run_command_line,
    configure_argument_parser,
    get_trello_client
)

def test_override_options():

    class FauxArgs:
        def __init__(self, opts):
            self.__dict__.update(opts)
            for k, v in opts.items():
                setattr(self, k, v)

    options = {'one': 1, 'two': 2}
    override_options(options, FauxArgs({}))
    assert json.dumps(options) == json.dumps({'one': 1, 'two': 2})
    
    options = {'one': 1, 'two': 2}
    override_options(options, FauxArgs({'one': 11}))
    assert json.dumps(options) == json.dumps({'one': 11, 'two': 2})

    options = {'one': 1, 'two': 2}
    override_options(options, FauxArgs({'three': 3}))
    assert json.dumps(options) == json.dumps({'one': 1, 'two': 2})

def test_run_command_line_with_trello_client(mocker):

    config = """
Connection:
  Type: trello

Query: project = "JLF"

Workflow:
  Backlog: Open
  In Progress:
    - In Progress
    - Reopened
  Done:
    - Resolved
    - Closed

Output:

    # CSV files with raw data for input to other tools or further analysis in a spreadsheet
    # If you use .json or .xlsx as the extension, you can get JSON data files or Excel
    # spreadsheets instead

    Cycle time data:
        - cycletime.csv
        - cycletime.json
    CFD data: cfd.csv    
"""
    mock_get_trello_client = mocker.patch('jira_agile_metrics.cli.get_trello_client')
    mocker.patch('jira_agile_metrics.cli.QueryManager')
    with tempfile.NamedTemporaryFile(delete=False) as config_file:
        config_file.write(config)
        config_file.flush()
        parser = configure_argument_parser()
        args = parser.parse_args([config_file.name])
        run_command_line(parser, args)
        mock_get_trello_client.assert_called_once()

def test_get_trello_client(mocker):

    mock_trello = mocker.patch('jira_agile_metrics.cli.TrelloClient')

    my_trello = get_trello_client({'username': 'me',
                                   'key': 'my_key',
                                   'token': 'my_token'}, {})

    mock_trello.assert_called_once()