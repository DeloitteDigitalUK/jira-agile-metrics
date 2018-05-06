import pytest
import datetime

from .conftest import (
    FauxJIRA as JIRA,
    FauxIssue as Issue,
    FauxChange as Change,
    FauxFieldValue as Value
)

from .querymanager import QueryManager, IssueSnapshot

@pytest.fixture
def jira(basic_fields):
    return JIRA(fields=basic_fields, issues=[
        Issue("A-1",
            summary="Issue A-1",
            issuetype=Value("Story", "story"),
            status=Value("Start", "start"),
            resolution=None,
            created="2018-01-01 01:01:01",
            customfield_001="Team 1",
            customfield_002=Value(None, 30),
            customfield_003=Value(None, ["R2", "R3", "R4"]),
            changes=[
                Change("2018-01-02 01:01:01", [("status", "Backlog", "Next",)]),
                Change("2018-01-03 01:01:01", [("resolution", None, "Closed",), ("status", "Next", "Done",)]),
                Change("2018-01-04 01:01:01", [("resolution", "Closed", None,), ("status", "Done", "QA",)]),
            ],
        )
    ])

def test_search(jira, basic_settings):
    qm = QueryManager(jira, basic_settings)
    assert qm.fields == {
        'Team': 'customfield_001',
        'Estimate': 'customfield_002',
        'Release': 'customfield_003',
    }

    issues = qm.find_issues("(filter=123)")
    assert issues == jira._issues

def test_resolve_field_value(jira, basic_settings):
    qm = QueryManager(jira, basic_settings)
    issues = qm.find_issues("(filter=123)")

    assert qm.resolve_field_value(issues[0], "Team") == "Team 1"
    assert qm.resolve_field_value(issues[0], "Estimate") == 30
    assert qm.resolve_field_value(issues[0], "Release") == "R3"  # due to known_value

def test_iter_changes(jira, basic_settings):
    qm = QueryManager(jira, basic_settings)
    issues = qm.find_issues("(filter=123)")
    changes = list(qm.iter_changes(issues[0]))

    assert changes == [
        IssueSnapshot(change=None,     key="A-1", date=datetime.datetime(2018, 1, 1, 1, 1, 1), status="Backlog", resolution=None,     is_resolved=False),
        IssueSnapshot(change="status", key="A-1", date=datetime.datetime(2018, 1, 2, 1, 1, 1), status="Next",    resolution=None,     is_resolved=False),
        IssueSnapshot(change="status", key="A-1", date=datetime.datetime(2018, 1, 3, 1, 1, 1), status="Done",    resolution="Closed", is_resolved=True),
        IssueSnapshot(change="status", key="A-1", date=datetime.datetime(2018, 1, 4, 1, 1, 1), status="QA",      resolution=None,     is_resolved=False)
    ]
