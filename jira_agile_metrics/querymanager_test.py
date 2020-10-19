import datetime

import pytest

from .conftest import FauxJIRA as JIRA, FauxIssue as Issue, FauxChange as Change, FauxFieldValue as Value
from .querymanager import QueryManager, IssueSnapshot
from .utils import extend_dict


@pytest.fixture(name="jira")
def fixture_jira(custom_fields):
    return JIRA(
        fields=custom_fields,
        issues=[
            Issue(
                "A-1",
                summary="Issue A-1",
                issuetype=Value("Story", "story"),
                status=Value("Backlotg", "backlog"),
                resolution=None,
                created="2018-01-01 01:01:01",
                customfield_001="Team 1",
                customfield_002=Value(None, 30),
                customfield_003=Value(None, ["R2", "R3", "R4"]),
                changes=[
                    # the changes are not in chrnological order, the first change is intentionally the third
                    # status change. This is intended to test that we manage get the correct first status change as
                    # the transition from Backlog to Next
                    Change("2018-01-03 01:01:01", [("resolution", None, "Closed"), ("status", "Next", "Done")]),
                    Change("2018-01-02 01:01:01", [("status", "Backlog", "Next")]),
                    Change("2018-01-02 01:01:01", [("Team", "Team 2", "Team 1")]),
                    Change("2018-01-04 01:01:01", [("resolution", "Closed", None), ("status", "Done", "QA")]),
                ],
            )
        ],
    )


@pytest.fixture(name="settings")
def fixture_settings(custom_settings):
    return extend_dict(custom_settings, {})


def test_search(jira, settings):
    query_manager = QueryManager(jira, settings)
    assert query_manager.attributes_to_fields == {
        "Team": "customfield_001",
        "Estimate": "customfield_002",
        "Release": "customfield_003",
    }

    issues = query_manager.find_issues("(filter=123)")
    assert issues == jira.issues()


def test_resolve_attribute_value(jira, settings):
    query_manager = QueryManager(jira, settings)
    issues = query_manager.find_issues("(filter=123)")

    assert query_manager.resolve_attribute_value(issues[0], "Team") == "Team 1"
    assert query_manager.resolve_attribute_value(issues[0], "Estimate") == 30
    assert query_manager.resolve_attribute_value(issues[0], "Release") == "R3"  # due to known_value


def test_resolve_field_value(jira, settings):
    query_manager = QueryManager(jira, settings)
    issues = query_manager.find_issues("(filter=123)")

    assert query_manager.resolve_field_value(issues[0], "customfield_001") == "Team 1"
    assert query_manager.resolve_field_value(issues[0], "customfield_002") == 30
    assert query_manager.resolve_field_value(issues[0], "customfield_003") == "R3"  # due to known_value


def test_iter_changes(jira, settings):
    query_manager = QueryManager(jira, settings)
    issues = query_manager.find_issues("(filter=123)")
    changes = list(query_manager.iter_changes(issues[0], ["status", "Team"]))

    assert changes == [
        IssueSnapshot(
            change="status",
            key="A-1",
            date=datetime.datetime(2018, 1, 1, 1, 1, 1),
            from_string=None,
            to_string="Backlog",
        ),
        IssueSnapshot(
            change="Team", key="A-1", date=datetime.datetime(2018, 1, 1, 1, 1, 1), from_string=None, to_string="Team 2"
        ),
        IssueSnapshot(
            change="status",
            key="A-1",
            date=datetime.datetime(2018, 1, 2, 1, 1, 1),
            from_string="Backlog",
            to_string="Next",
        ),
        IssueSnapshot(
            change="Team",
            key="A-1",
            date=datetime.datetime(2018, 1, 2, 1, 1, 1),
            from_string="Team 2",
            to_string="Team 1",
        ),
        IssueSnapshot(
            change="status",
            key="A-1",
            date=datetime.datetime(2018, 1, 3, 1, 1, 1),
            from_string="Next",
            to_string="Done",
        ),
        IssueSnapshot(
            change="status", key="A-1", date=datetime.datetime(2018, 1, 4, 1, 1, 1), from_string="Done", to_string="QA"
        ),
    ]
