import pytest
from pandas import DataFrame, Timestamp, NaT

from mock import Mock
import trello

from .querymanager import QueryManager
from .utils import extend_dict

from .calculators.cycletime import CycleTimeCalculator
from .calculators.cfd import CFDCalculator


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
    """An item in a changelog change
    """
    def __init__(self, field, fieldId, fromString, toString):
        self.field = field
        self.fieldId = fieldId
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
        return (
            self._issues
            if self._filter is None
            else [i for i in self._issues if self._filter(i, jql)]
        )


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
                else "Test"
                if i["Test"] is not NaT
                else "Build"
                if i["Build"] is not NaT
                else "Committed"
                if i["Committed"] is not NaT
                else "Backlog"
            ),
            "resoluton": "Done" if i["Done"] is not NaT else None,
            "completed_timestamp": i["Done"] if i["Done"] is not NaT else None,
            "cycle_time": (i["Done"] - i["Committed"])
            if (i["Done"] is not NaT and i["Committed"] is not NaT)
            else None,
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
    return Timestamp(
        "%s %s"
        % (
            datestring,
            timestring,
        ),
        freq=freq,
    )


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
    mock_members.get_board = Mock(
        return_value=[{"name": "my_board", "id": "my_id"}]
    )
    mock_api.members = mock_members

    mock_cards = Mock(spec=trello.cards)
    mock_cards.get = Mock()
    mock_cards.get.side_effect = [
        {
            u"labels": [],
            u"pos": 16384,
            u"manualCoverAttachment": False,
            u"id": u"56ae35346b23ea1d6843a67f",
            u"badges": {
                u"votes": 0,
                u"attachments": 0,
                u"subscribed": False,
                u"due": None,
                u"comments": 0,
                u"checkItemsChecked": 0,
                u"fogbugz": u"",
                u"viewingMemberVoted": False,
                u"checkItems": 0,
                u"description": False,
            },
            u"idBoard": u"56ae35260b361ede7bfbb1ba",
            u"idShort": 1,
            u"due": None,
            u"shortUrl": u"https://trello.com/c/J6st5pG8",
            u"closed": False,
            u"email": u"worldofchris+7327776194338bb7c60@boards.trello.com",
            u"dateLastActivity": u"2016-01-31T16:24:36.264Z",
            u"idList": u"56ae352bee563becb21b3b82",
            u"idLabels": [],
            u"idMembers": [],
            u"checkItemStates": [],
            u"desc": u"",
            u"descData": None,
            u"name": u"Card One",
            u"url": u"https://trello.com/c/J6st5pG8/1-card-one",
            u"idAttachmentCover": None,
            u"idChecklists": [],
        },
        {
            u"labels": [{u"name": u"bug"}],
            u"pos": 16384,
            u"manualCoverAttachment": False,
            u"id": u"56ae35346b23ea1d6843a67a",
            u"badges": {
                u"votes": 0,
                u"attachments": 0,
                u"subscribed": False,
                u"due": None,
                u"comments": 0,
                u"checkItemsChecked": 0,
                u"fogbugz": u"",
                u"viewingMemberVoted": False,
                u"checkItems": 0,
                u"description": False,
            },
            u"idBoard": u"56ae35260b361ede7bfbb1ba",
            u"idShort": 1,
            u"due": None,
            u"shortUrl": u"https://trello.com/c/J6st5pG8",
            u"closed": False,
            u"email": u"worldofchris+559248f3a0cca5aeb0@boards.trello.com",
            u"dateLastActivity": u"2016-01-31T16:24:36.264Z",
            u"idList": u"56ae352bee563becb21b3b82",
            u"idLabels": [],
            u"idMembers": [],
            u"checkItemStates": [],
            u"desc": u"",
            u"descData": None,
            u"name": u"Card One",
            u"url": u"https://trello.com/c/J6st5pG8/1-card-one",
            u"idAttachmentCover": None,
            u"idChecklists": [],
        },
    ]

    mock_api.cards = mock_cards

    mock_boards = Mock(spec=trello.boards)
    mock_boards.get_action = Mock()

    mock_boards.get_action.side_effect = [
        [
            {
                u"type": u"updateCard",
                u"idMemberCreator": u"559248f3a0cca5aeb0277db6",
                u"memberCreator": {
                    u"username": u"worldofchris",
                    u"fullName": u"Chris Young",
                    u"initials": u"CY",
                    u"id": u"559248f3a0cca5aeb0277db6",
                    u"avatarHash": u"1171b29b10de82b6a77187b79d8b9a41",
                },
                u"date": u"2016-01-31T16:24:36.269Z",
                u"data": {
                    u"listBefore": {
                        u"name": u"Three",
                        u"id": u"56ae35296061372e997c0321",
                    },
                    u"old": {u"idList": u"56ae35296061372e997c0321"},
                    u"board": {
                        u"id": u"56ae35260b361ede7bfbb1ba",
                        u"name": u"API Test 001",
                        u"shortLink": u"l4YiX1fv",
                    },
                    u"card": {
                        u"idShort": 1,
                        u"id": u"56ae35346b23ea1d6843a67f",
                        u"name": u"Card One",
                        u"idList": u"56ae352bee563becb21b3b82",
                        u"shortLink": u"J6st5pG8",
                    },
                    u"listAfter": {
                        u"name": u"Four",
                        u"id": u"56ae352bee563becb21b3b82",
                    },
                },
                u"id": u"56ae35444acfaca041099908",
            },
            {
                u"type": u"moveCardToBoard",
                u"idMemberCreator": u"559248f3a0cca5aeb0277db6",
                u"memberCreator": {
                    u"username": u"worldofchris",
                    u"fullName": u"Chris Young",
                    u"initials": u"CY",
                    u"id": u"559248f3a0cca5aeb0277db6",
                    u"avatarHash": u"1171b29b10de82b6a77187b79d8b9a41",
                },
                u"date": u"2016-01-31T16:24:29.768Z",
                u"data": {
                    u"boardSource": {
                        u"name": u"API Test 000",
                        u"id": u"56ae351097460cd456a5f323",
                    },
                    u"list": {
                        u"name": u"Three",
                        u"id": u"56ae35296061372e997c0321",
                    },
                    u"board": {
                        u"id": u"56ae35260b361ede7bfbb1ba",
                        u"name": u"API Test 001",
                        u"shortLink": u"l4YiX1fv",
                    },
                    u"card": {
                        u"idShort": 1,
                        u"id": u"56ae35346b23ea1d6843a67f",
                        u"name": u"Card One",
                        u"shortLink": u"J6st5pG8",
                    },
                },
                u"id": u"56ae353d1fd6686e1baa1d93",
            },
            {
                u"type": u"createCard",
                u"idMemberCreator": u"559248f3a0cca5aeb0277db6",
                u"memberCreator": {
                    u"username": u"worldofchris",
                    u"fullName": u"Chris Young",
                    u"initials": u"CY",
                    u"id": u"559248f3a0cca5aeb0277db6",
                    u"avatarHash": u"1171b29b10de82b6a77187b79d8b9a41",
                },
                u"date": u"2016-01-31T16:24:20.398Z",
                u"data": {
                    u"list": {
                        u"name": u"List One",
                        u"id": u"56ae3514326fd4436da31bbf",
                    },
                    u"board": {
                        u"name": u"API Test 001",
                        u"id": u"56ae35260b361ede7bfbb1ba",
                    },
                    u"card": {
                        u"idShort": 1,
                        u"id": u"56ae35346b23ea1d6843a67f",
                        u"name": u"Card One",
                        u"shortLink": u"J6st5pG8",
                    },
                },
                u"id": u"56ae35346b23ea1d6843a680",
            },
            {
                u"type": u"createList",
                u"idMemberCreator": u"559248f3a0cca5aeb0277db6",
                u"memberCreator": {
                    u"username": u"worldofchris",
                    u"fullName": u"Chris Young",
                    u"initials": u"CY",
                    u"id": u"559248f3a0cca5aeb0277db6",
                    u"avatarHash": u"1171b29b10de82b6a77187b79d8b9a41",
                },
                u"date": u"2016-01-31T16:24:11.845Z",
                u"data": {
                    u"list": {
                        u"name": u"Four",
                        u"id": u"56ae352bee563becb21b3b82",
                    },
                    u"board": {
                        u"id": u"56ae35260b361ede7bfbb1ba",
                        u"name": u"API Test 001",
                        u"shortLink": u"l4YiX1fv",
                    },
                },
                u"id": u"56ae352bee563becb21b3b83",
            },
            {
                u"type": u"createList",
                u"idMemberCreator": u"559248f3a0cca5aeb0277db6",
                u"memberCreator": {
                    u"username": u"worldofchris",
                    u"fullName": u"Chris Young",
                    u"initials": u"CY",
                    u"id": u"559248f3a0cca5aeb0277db6",
                    u"avatarHash": u"1171b29b10de82b6a77187b79d8b9a41",
                },
                u"date": u"2016-01-31T16:24:09.766Z",
                u"data": {
                    u"list": {
                        u"name": u"Three",
                        u"id": u"56ae35296061372e997c0321",
                    },
                    u"board": {
                        u"id": u"56ae35260b361ede7bfbb1ba",
                        u"name": u"API Test 001",
                        u"shortLink": u"l4YiX1fv",
                    },
                },
                u"id": u"56ae35296061372e997c0322",
            },
            {
                u"type": u"createBoard",
                u"idMemberCreator": u"559248f3a0cca5aeb0277db6",
                u"memberCreator": {
                    u"username": u"worldofchris",
                    u"fullName": u"Chris Young",
                    u"initials": u"CY",
                    u"id": u"559248f3a0cca5aeb0277db6",
                    u"avatarHash": u"1171b29b10de82b6a77187b79d8b9a41",
                },
                u"date": u"2016-01-31T16:24:06.359Z",
                u"data": {
                    u"board": {
                        u"id": u"56ae35260b361ede7bfbb1ba",
                        u"name": u"API Test 001",
                        u"shortLink": u"l4YiX1fv",
                    }
                },
                u"id": u"56ae35260b361ede7bfbb1bc",
            },
            {
                u"type": u"createCard",
                u"idMemberCreator": u"559248f3a0cca5aeb0277db6",
                u"memberCreator": {
                    u"username": u"worldofchris",
                    u"fullName": u"Chris Young",
                    u"initials": u"CY",
                    u"id": u"559248f3a0cca5aeb0277db6",
                    u"avatarHash": u"1171b29b10de82b6a77187b79d8b9a41",
                },
                u"date": u"2016-01-31T16:24:20.398Z",
                u"data": {
                    u"list": {
                        u"name": u"List One",
                        u"id": u"56ae3514326fd4436da31bbf",
                    },
                    u"board": {
                        u"name": u"API Test 001",
                        u"id": u"56ae35260b361ede7bfbb1ba",
                    },
                    u"card": {
                        u"idShort": 1,
                        u"id": u"56ae35346b23ea1d6843a67a",
                        u"name": u"Card Two",
                        u"shortLink": u"J6st5pG8",
                    },
                },
                u"id": u"56ae35346b23ea1d6843a680",
            },
        ],
        [],
    ]

    mock_api.boards = mock_boards

    mock_lists = Mock(spec=trello.lists)
    mock_lists.get = Mock(
        return_value={
            u"pos": 131071,
            u"idBoard": u"56ae35260b361ede7bfbb1ba",
            u"id": u"56ae352bee563becb21b3b82",
            u"closed": False,
            u"name": u"Four",
        }
    )
    mock_api.lists = mock_lists

    TrelloApi.return_value = mock_api
