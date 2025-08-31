import pytest
import trello
from mock import Mock
from pandas import DataFrame, NaT, Timestamp

from .calculators.cfd import CFDCalculator
from .calculators.cycletime import CycleTimeCalculator
from .querymanager import QueryManager
from .utils import extend_dict

# Fake a portion of the JIRA API


class FauxFieldValue(object):
    """A complex field value, with a name and a typed value"""

    def __init__(self, name, value):
        self.name = name
        self.value = value


class FauxFields(object):
    """Container for `issue.fields`"""

    def __init__(self, fields):
        self.__dict__.update(fields)


class FauxChangeItem(object):
    """An item in a changelog change"""

    def __init__(self, field, fromString, toString):
        self.field = field
        self.from_ = self.fromString = fromString
        self.to = self.toString = toString


class FauxChange(object):
    """A change in a changelog. Contains a list of change items."""

    def __init__(self, created, items):
        self.created = created
        self.items = [FauxChangeItem(*i) for i in items]


class FauxChangelog(object):
    """A changelog. Contains a list of changes in `histories`."""

    def __init__(self, changes):
        self.histories = changes


class FauxIssue(object):
    """An issue, with a key, change log, and set of fields"""

    def __init__(self, key, changes, **fields):
        self.key = key
        self.fields = FauxFields(fields)
        self.changelog = FauxChangelog(changes)


class FauxJIRA(object):
    """JIRA interface. Initialised with a set of issues, which will be returned
    by `search_issues()`.
    """

    def __init__(
        self,
        fields,
        issues,
        options={"server": "https://example.org"},
        filter=None,
    ):
        self._options = options
        self._fields = fields  # [{ id, name }]
        self._issues = issues
        self._filter = filter

    def fields(self):
        return self._fields

    def search_issues(self, jql, *args, **kwargs):
        return self._issues if self._filter is None else [i for i in self._issues if self._filter(i, jql)]


# Fixtures


@pytest.fixture
def minimal_settings():
    """The smallest `settings` required to build a query manager and cycle time
    calculation.
    """
    return {
        "attributes": {},
        "known_values": {"Release": ["R1", "R3"]},
        "max_results": None,
        "verbose": False,
        "cycle": [
            {"name": "Backlog", "statuses": ["Backlog"]},
            {"name": "Committed", "statuses": ["Next"]},
            {"name": "Build", "statuses": ["Build"]},
            {"name": "Test", "statuses": ["Code review", "QA"]},
            {"name": "Done", "statuses": ["Done"]},
        ],
        "query_attribute": None,
        "queries": [{"jql": "(filter=123)", "value": None}],
        "backlog_column": "Backlog",
        "committed_column": "Committed",
        "done_column": "Done",
    }


@pytest.fixture
def custom_settings(minimal_settings):
    """A `settings` dict that uses custom fields and attributes."""
    return extend_dict(
        minimal_settings,
        {
            "attributes": {
                "Release": "Releases",
                "Team": "Team",
                "Estimate": "Size",
            },
            "known_values": {"Release": ["R1", "R3"]},
        },
    )


# Fields + corresponding columns


@pytest.fixture
def minimal_fields():
    """A `fields` list for all basic fields, but no custom fields."""
    return [
        {"id": "summary", "name": "Summary"},
        {"id": "issuetype", "name": "Issue type"},
        {"id": "status", "name": "Status"},
        {"id": "resolution", "name": "Resolution"},
        {"id": "created", "name": "Created date"},
        {"id": "customfield_100", "name": "Flagged"},
    ]


@pytest.fixture
def custom_fields(minimal_fields):
    """A `fields` list with the three custom fields used
    by `custom_settings`"""
    return minimal_fields + [
        {"id": "customfield_001", "name": "Team"},
        {"id": "customfield_002", "name": "Size"},
        {"id": "customfield_003", "name": "Releases"},
    ]


@pytest.fixture
def minimal_cycle_time_columns():
    """A columns list for the results of CycleTimeCalculator without any
    custom fields.
    """
    return [
        "key",
        "url",
        "issue_type",
        "summary",
        "status",
        "resolution",
        "cycle_time",
        "completed_timestamp",
        "blocked_days",
        "impediments",
        "Backlog",
        "Committed",
        "Build",
        "Test",
        "Done",
    ]


@pytest.fixture
def custom_cycle_time_columns(minimal_fields):
    """A columns list for the results of CycleTimeCalculator with the three
    custom fields from `custom_settings`.
    """
    return [
        "key",
        "url",
        "issue_type",
        "summary",
        "status",
        "resolution",
        "Estimate",
        "Release",
        "Team",
        "cycle_time",
        "completed_timestamp",
        "blocked_days",
        "impediments",
        "Backlog",
        "Committed",
        "Build",
        "Test",
        "Done",
    ]


@pytest.fixture
def cfd_columns():
    """A columns list for the results of the CFDCalculator."""
    return ["Backlog", "Committed", "Build", "Test", "Done"]


# Query manager


@pytest.fixture
def minimal_query_manager(minimal_fields, minimal_settings):
    """A minimal query manager (no custom fields)"""
    jira = FauxJIRA(fields=minimal_fields, issues=[])
    return QueryManager(jira, minimal_settings)


@pytest.fixture
def custom_query_manager(custom_fields, custom_settings):
    """A query manager capable of returning values for custom fields"""
    jira = FauxJIRA(fields=custom_fields, issues=[])
    return QueryManager(jira, custom_settings)


# Results object with rich cycle time data


def _issues(issues):
    return [
        {
            "key": "A-%d" % (idx + 1),
            "url": "https://example.org/browse/A-%d" % (idx + 1),
            "issue_type": "Story",
            "summary": "Generated issue A-%d" % (idx + 1),
            "status": (
                "Done"
                if i["Done"] is not NaT
                else (
                    "Test"
                    if i["Test"] is not NaT
                    else (
                        "Build" if i["Build"] is not NaT else ("Committed" if i["Committed"] is not NaT else "Backlog")
                    )
                )
            ),
            "resoluton": "Done" if i["Done"] is not NaT else None,
            "completed_timestamp": i["Done"] if i["Done"] is not NaT else None,
            "cycle_time": (
                (i["Done"] - i["Committed"]) if (i["Done"] is not NaT and i["Committed"] is not NaT) else None
            ),
            "blocked_days": i.get("blocked_days", 0),
            "impediments": i.get("impediments", []),
            "Backlog": i["Backlog"],
            "Committed": i["Committed"],
            "Build": i["Build"],
            "Test": i["Test"],
            "Done": i["Done"],
        }
        for idx, i in enumerate(issues)
    ]


def _ts(datestring, timestring="00:00:00", freq=None):
    ts = Timestamp(
        "%s %s"
        % (
            datestring,
            timestring,
        )
    )
    if freq is not None:
        ts = ts.to_period(freq).to_timestamp()
    return ts


@pytest.fixture
def minimal_cycle_time_results(minimal_cycle_time_columns):
    """A results dict mimicing a minimal
    result from the CycleTimeCalculator."""
    return {
        CycleTimeCalculator: DataFrame(
            _issues(
                [
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=NaT,
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-02"),
                        Committed=_ts("2018-01-03"),
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-03"),
                        Committed=_ts("2018-01-03"),
                        Build=_ts("2018-01-04"),
                        Test=_ts("2018-01-05"),
                        Done=_ts("2018-01-06"),
                    ),
                    dict(
                        Backlog=_ts("2018-01-04"),
                        Committed=_ts("2018-01-04"),
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                ]
            ),
            columns=minimal_cycle_time_columns,
        )
    }


@pytest.fixture
def large_cycle_time_results(minimal_cycle_time_columns):
    """A results dict mimicing a larger result
    from the CycleTimeCalculator."""
    return {
        CycleTimeCalculator: DataFrame(
            _issues(
                [
                    # three issues in the backlog
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=NaT,
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-02"),
                        Committed=NaT,
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-03"),
                        Committed=NaT,
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                    # three issues started
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-03"),
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-03"),
                        Build=NaT,
                        Test=NaT,
                        Done=NaT,
                    ),
                    # three issues in build
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=_ts("2018-01-03"),
                        Test=NaT,
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=_ts("2018-01-04"),
                        Test=NaT,
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=_ts("2018-01-04"),
                        Test=NaT,
                        Done=NaT,
                    ),
                    # three issues in test
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=_ts("2018-01-03"),
                        Test=_ts("2018-01-04"),
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=_ts("2018-01-03"),
                        Test=_ts("2018-01-05"),
                        Done=NaT,
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=_ts("2018-01-03"),
                        Test=_ts("2018-01-05"),
                        Done=NaT,
                    ),
                    # six issues done, with different cycle times
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=_ts("2018-01-03"),
                        Test=_ts("2018-01-04"),
                        Done=_ts("2018-01-07"),
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-02"),
                        Build=_ts("2018-01-03"),
                        Test=_ts("2018-01-05"),
                        Done=_ts("2018-01-07"),
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-03"),
                        Build=_ts("2018-01-03"),
                        Test=_ts("2018-01-05"),
                        Done=_ts("2018-01-08"),
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-03"),
                        Build=_ts("2018-01-03"),
                        Test=_ts("2018-01-04"),
                        Done=_ts("2018-01-08"),
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-04"),
                        Build=_ts("2018-01-05"),
                        Test=_ts("2018-01-05"),
                        Done=_ts("2018-01-09"),
                    ),
                    dict(
                        Backlog=_ts("2018-01-01"),
                        Committed=_ts("2018-01-05"),
                        Build=_ts("2018-01-06"),
                        Test=_ts("2018-01-08"),
                        Done=_ts("2018-01-09"),
                    ),
                ]
            ),
            columns=minimal_cycle_time_columns,
        )
    }


@pytest.fixture
def minimal_cfd_results(minimal_cycle_time_results, cfd_columns):
    """A results dict mimicing a minimal
    result from the CycleTimeCalculator."""
    return extend_dict(
        minimal_cycle_time_results,
        {
            CFDCalculator: DataFrame(
                [
                    {
                        "Backlog": 1.0,
                        "Committed": 0.0,
                        "Build": 0.0,
                        "Test": 0.0,
                        "Done": 0.0,
                    },
                    {
                        "Backlog": 2.0,
                        "Committed": 0.0,
                        "Build": 0.0,
                        "Test": 0.0,
                        "Done": 0.0,
                    },
                    {
                        "Backlog": 3.0,
                        "Committed": 2.0,
                        "Build": 0.0,
                        "Test": 0.0,
                        "Done": 0.0,
                    },
                    {
                        "Backlog": 4.0,
                        "Committed": 3.0,
                        "Build": 1.0,
                        "Test": 0.0,
                        "Done": 0.0,
                    },
                    {
                        "Backlog": 4.0,
                        "Committed": 3.0,
                        "Build": 1.0,
                        "Test": 1.0,
                        "Done": 0.0,
                    },
                    {
                        "Backlog": 4.0,
                        "Committed": 3.0,
                        "Build": 1.0,
                        "Test": 1.0,
                        "Done": 1.0,
                    },
                ],
                columns=cfd_columns,
                index=[
                    _ts("2018-01-01", "00:00:00", freq="D"),
                    _ts("2018-01-02", "00:00:00", freq="D"),
                    _ts("2018-01-03", "00:00:00", freq="D"),
                    _ts("2018-01-04", "00:00:00", freq="D"),
                    _ts("2018-01-05", "00:00:00", freq="D"),
                    _ts("2018-01-06", "00:00:00", freq="D"),
                ],
            )
        },
    )


@pytest.fixture
def mock_trello_api(mocker):
    TrelloApi = mocker.patch("jira_agile_metrics.trello.TrelloApi")

    mock_api = Mock(spec=trello.TrelloApi)
    mock_members = Mock(spec=trello.members)
    mock_members.get_board = Mock(return_value=[{"name": "my_board", "id": "my_id"}])
    mock_api.members = mock_members

    mock_cards = Mock(spec=trello.cards)
    mock_cards.get = Mock()
    mock_cards.get.side_effect = [
        {
            "labels": [],
            "pos": 16384,
            "manualCoverAttachment": False,
            "id": "56ae35346b23ea1d6843a67f",
            "badges": {
                "votes": 0,
                "attachments": 0,
                "subscribed": False,
                "due": None,
                "comments": 0,
                "checkItemsChecked": 0,
                "fogbugz": "",
                "viewingMemberVoted": False,
                "checkItems": 0,
                "description": False,
            },
            "idBoard": "56ae35260b361ede7bfbb1ba",
            "idShort": 1,
            "due": None,
            "shortUrl": "https://trello.com/c/J6st5pG8",
            "closed": False,
            "email": "worldofchris+7327776194338bb7c60@boards.trello.com",
            "dateLastActivity": "2016-01-31T16:24:36.264Z",
            "idList": "56ae352bee563becb21b3b82",
            "idLabels": [],
            "idMembers": [],
            "checkItemStates": [],
            "desc": "",
            "descData": None,
            "name": "Card One",
            "url": "https://trello.com/c/J6st5pG8/1-card-one",
            "idAttachmentCover": None,
            "idChecklists": [],
        },
        {
            "labels": [{"name": "bug"}],
            "pos": 16384,
            "manualCoverAttachment": False,
            "id": "56ae35346b23ea1d6843a67a",
            "badges": {
                "votes": 0,
                "attachments": 0,
                "subscribed": False,
                "due": None,
                "comments": 0,
                "checkItemsChecked": 0,
                "fogbugz": "",
                "viewingMemberVoted": False,
                "checkItems": 0,
                "description": False,
            },
            "idBoard": "56ae35260b361ede7bfbb1ba",
            "idShort": 1,
            "due": None,
            "shortUrl": "https://trello.com/c/J6st5pG8",
            "closed": False,
            "email": "worldofchris+559248f3a0cca5aeb0@boards.trello.com",
            "dateLastActivity": "2016-01-31T16:24:36.264Z",
            "idList": "56ae352bee563becb21b3b82",
            "idLabels": [],
            "idMembers": [],
            "checkItemStates": [],
            "desc": "",
            "descData": None,
            "name": "Card One",
            "url": "https://trello.com/c/J6st5pG8/1-card-one",
            "idAttachmentCover": None,
            "idChecklists": [],
        },
    ]

    mock_api.cards = mock_cards

    mock_boards = Mock(spec=trello.boards)
    mock_boards.get_action = Mock()

    mock_boards.get_action.side_effect = [
        [
            {
                "type": "updateCard",
                "idMemberCreator": "559248f3a0cca5aeb0277db6",
                "memberCreator": {
                    "username": "worldofchris",
                    "fullName": "Chris Young",
                    "initials": "CY",
                    "id": "559248f3a0cca5aeb0277db6",
                    "avatarHash": "1171b29b10de82b6a77187b79d8b9a41",
                },
                "date": "2016-01-31T16:24:36.269Z",
                "data": {
                    "listBefore": {
                        "name": "Three",
                        "id": "56ae35296061372e997c0321",
                    },
                    "old": {"idList": "56ae35296061372e997c0321"},
                    "board": {
                        "id": "56ae35260b361ede7bfbb1ba",
                        "name": "API Test 001",
                        "shortLink": "l4YiX1fv",
                    },
                    "card": {
                        "idShort": 1,
                        "id": "56ae35346b23ea1d6843a67f",
                        "name": "Card One",
                        "idList": "56ae352bee563becb21b3b82",
                        "shortLink": "J6st5pG8",
                    },
                    "listAfter": {
                        "name": "Four",
                        "id": "56ae352bee563becb21b3b82",
                    },
                },
                "id": "56ae35444acfaca041099908",
            },
            {
                "type": "moveCardToBoard",
                "idMemberCreator": "559248f3a0cca5aeb0277db6",
                "memberCreator": {
                    "username": "worldofchris",
                    "fullName": "Chris Young",
                    "initials": "CY",
                    "id": "559248f3a0cca5aeb0277db6",
                    "avatarHash": "1171b29b10de82b6a77187b79d8b9a41",
                },
                "date": "2016-01-31T16:24:29.768Z",
                "data": {
                    "boardSource": {
                        "name": "API Test 000",
                        "id": "56ae351097460cd456a5f323",
                    },
                    "list": {
                        "name": "Three",
                        "id": "56ae35296061372e997c0321",
                    },
                    "board": {
                        "id": "56ae35260b361ede7bfbb1ba",
                        "name": "API Test 001",
                        "shortLink": "l4YiX1fv",
                    },
                    "card": {
                        "idShort": 1,
                        "id": "56ae35346b23ea1d6843a67f",
                        "name": "Card One",
                        "shortLink": "J6st5pG8",
                    },
                },
                "id": "56ae353d1fd6686e1baa1d93",
            },
            {
                "type": "createCard",
                "idMemberCreator": "559248f3a0cca5aeb0277db6",
                "memberCreator": {
                    "username": "worldofchris",
                    "fullName": "Chris Young",
                    "initials": "CY",
                    "id": "559248f3a0cca5aeb0277db6",
                    "avatarHash": "1171b29b10de82b6a77187b79d8b9a41",
                },
                "date": "2016-01-31T16:24:20.398Z",
                "data": {
                    "list": {
                        "name": "List One",
                        "id": "56ae3514326fd4436da31bbf",
                    },
                    "board": {
                        "name": "API Test 001",
                        "id": "56ae35260b361ede7bfbb1ba",
                    },
                    "card": {
                        "idShort": 1,
                        "id": "56ae35346b23ea1d6843a67f",
                        "name": "Card One",
                        "shortLink": "J6st5pG8",
                    },
                },
                "id": "56ae35346b23ea1d6843a680",
            },
            {
                "type": "createList",
                "idMemberCreator": "559248f3a0cca5aeb0277db6",
                "memberCreator": {
                    "username": "worldofchris",
                    "fullName": "Chris Young",
                    "initials": "CY",
                    "id": "559248f3a0cca5aeb0277db6",
                    "avatarHash": "1171b29b10de82b6a77187b79d8b9a41",
                },
                "date": "2016-01-31T16:24:11.845Z",
                "data": {
                    "list": {
                        "name": "Four",
                        "id": "56ae352bee563becb21b3b82",
                    },
                    "board": {
                        "id": "56ae35260b361ede7bfbb1ba",
                        "name": "API Test 001",
                        "shortLink": "l4YiX1fv",
                    },
                },
                "id": "56ae352bee563becb21b3b83",
            },
            {
                "type": "createList",
                "idMemberCreator": "559248f3a0cca5aeb0277db6",
                "memberCreator": {
                    "username": "worldofchris",
                    "fullName": "Chris Young",
                    "initials": "CY",
                    "id": "559248f3a0cca5aeb0277db6",
                    "avatarHash": "1171b29b10de82b6a77187b79d8b9a41",
                },
                "date": "2016-01-31T16:24:09.766Z",
                "data": {
                    "list": {
                        "name": "Three",
                        "id": "56ae35296061372e997c0321",
                    },
                    "board": {
                        "id": "56ae35260b361ede7bfbb1ba",
                        "name": "API Test 001",
                        "shortLink": "l4YiX1fv",
                    },
                },
                "id": "56ae35296061372e997c0322",
            },
            {
                "type": "createBoard",
                "idMemberCreator": "559248f3a0cca5aeb0277db6",
                "memberCreator": {
                    "username": "worldofchris",
                    "fullName": "Chris Young",
                    "initials": "CY",
                    "id": "559248f3a0cca5aeb0277db6",
                    "avatarHash": "1171b29b10de82b6a77187b79d8b9a41",
                },
                "date": "2016-01-31T16:24:06.359Z",
                "data": {
                    "board": {
                        "id": "56ae35260b361ede7bfbb1ba",
                        "name": "API Test 001",
                        "shortLink": "l4YiX1fv",
                    }
                },
                "id": "56ae35260b361ede7bfbb1bc",
            },
            {
                "type": "createCard",
                "idMemberCreator": "559248f3a0cca5aeb0277db6",
                "memberCreator": {
                    "username": "worldofchris",
                    "fullName": "Chris Young",
                    "initials": "CY",
                    "id": "559248f3a0cca5aeb0277db6",
                    "avatarHash": "1171b29b10de82b6a77187b79d8b9a41",
                },
                "date": "2016-01-31T16:24:20.398Z",
                "data": {
                    "list": {
                        "name": "List One",
                        "id": "56ae3514326fd4436da31bbf",
                    },
                    "board": {
                        "name": "API Test 001",
                        "id": "56ae35260b361ede7bfbb1ba",
                    },
                    "card": {
                        "idShort": 1,
                        "id": "56ae35346b23ea1d6843a67a",
                        "name": "Card Two",
                        "shortLink": "J6st5pG8",
                    },
                },
                "id": "56ae35346b23ea1d6843a680",
            },
        ],
        [],
    ]

    mock_api.boards = mock_boards

    mock_lists = Mock(spec=trello.lists)
    mock_lists.get = Mock(
        return_value={
            "pos": 131071,
            "idBoard": "56ae35260b361ede7bfbb1ba",
            "id": "56ae352bee563becb21b3b82",
            "closed": False,
            "name": "Four",
        }
    )
    mock_api.lists = mock_lists

    TrelloApi.return_value = mock_api
