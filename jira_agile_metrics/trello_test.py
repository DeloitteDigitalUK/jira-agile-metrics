# -*- coding: utf-8 -*-

from .trello import (
    TrelloClient,
    JiraLikeHistoryItem,
    JiraLikeHistory,
    JiraLikeIssue,
    JiraLikeFields,
)

member = "chrisyoung277"
key = "key"
token = "token"


def test_create(mock_trello_api):
    """
    Create a client and connect to Trello
    """

    my_trello = TrelloClient(member, key, token)
    assert type(my_trello) == TrelloClient


def test_search_issues(mock_trello_api):
    """
    Get back a jira-like set of issues

    To get the complete history of a Trello card you have to use the Board
    actions rather than the Card Actions. This is because Trello re-writes
    the card history when it transitions from one Board to another for
    security reasons.
    """

    my_trello = TrelloClient(member, key, token)
    issues = my_trello.search_issues("my_board")
    assert len(issues) == 2


def test_fields(mock_trello_api):
    """
    Get back a list of jira-like fields requied by the calculators
    """
    my_trello = TrelloClient(member, key, token)
    fields = my_trello.fields()
    assert fields == [
        {"id": "status", "name": "status"},
        {"id": "Flagged", "name": "Flagged"},
    ]


def test_jira_like_history_item():
    """
    The events in the history of a trello card - JIRA style
    """

    my_item = JiraLikeHistoryItem(
        field="status", fromString="Open", toString="Closed"
    )
    assert type(my_item) == JiraLikeHistoryItem


def test_jira_like_history():
    """
    The history of a trello card - JIRA style
    """

    my_history = JiraLikeHistory(
        created="",
        item=JiraLikeHistoryItem(
            field="status", fromString="Open", toString="Closed"
        ),
    )
    assert type(my_history) == JiraLikeHistory


def test_jira_like_issue():
    """
    The trello wrapper returns objects which look to the
    query manager like JIRA issues
    """
    my_jira_like_issue = JiraLikeIssue(
        key="some number",
        url="https://some.where",
        fields=None,
        history=JiraLikeHistory(
            created="",
            item=JiraLikeHistoryItem(
                field="status", fromString="Open", toString="Closed"
            ),
        ),
    )
    assert type(my_jira_like_issue) == JiraLikeIssue


def test_jira_like_fields():
    """
    Wrap up trello card attributes to look like JIRA fields
    """
    my_jira_fields = JiraLikeFields(
        labels=["this", "that", "the other"],
        summary="Fair to middling",
        status="In Progress",
        created="foo",
        issuetype="hmmm",
    )

    assert type(my_jira_fields) == JiraLikeFields


def test_set_type_from_label(mock_trello_api):
    """
    Allow us to identify a type of work - e.g. Failure demand - from
    a specific label
    """

    my_trello = TrelloClient(
        member, key, token, type_mapping={"defect": ["bug"]}
    )
    issues = my_trello.search_issues("my_board")
    assert issues[1].fields.issuetype.name == "defect"
