import pytest
import datetime

from .query import QueryManager, IssueSnapshot

# Fake a big chunk of the JIRA API to let us test the query manager

class FauxFieldValue(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class FauxFields(object):
    def __init__(self, fields):
        self.__dict__.update(fields)

class FauxChangeItem(object):
    def __init__(self, field, fromString, toString):
        self.field = field
        self.from_ = self.fromString = fromString
        self.to = self.toString = toString

class FauxChange(object):
    def __init__(self, created, items):
        self.created = created
        self.items = items

class FauxChangelog(object):
    def __init__(self, changes):
        self.histories = changes

class FauxIssue(object):
    def __init__(self, key, fields, changes):
        self.key = key
        self.fields = FauxFields(fields)
        self.changelog = FauxChangelog(changes)

class FauxJIRA(object):

    def __init__(self, fields, issues):
        self._fields = fields  # [{ id, name }]
        self._issues = issues

    def fields(self):
        return self._fields

    def search_issues(self, jql, *args, **kwargs):
        return self._issues


@pytest.fixture
def basic_jira():
    return FauxJIRA(
        fields=[
            {'id': 'summary', 'name': 'Summary'},
            {'id': 'issuetype', 'name': 'Issue type'},
            {'id': 'status', 'name': 'Status'},
            {'id': 'resolution', 'name': 'Resolution'},
            {'id': 'created', 'name': 'Created date'},
            {'id': 'customfield_001', 'name': 'Team'},
            {'id': 'customfield_002', 'name': 'Size'},
            {'id': 'customfield_003', 'name': 'Releases'},
            {'id': 'customfield_004', 'name': 'Unused'},
        ],
        issues=[
            FauxIssue("A-1",
                fields={
                    'summary': "Issue A-1",
                    'issuetype': FauxFieldValue("Story", "story"),
                    'status': FauxFieldValue("Start", "start"),
                    'resolution': None,
                    'created': "2018-01-01 01:01:01",
                    'customfield_001': "Team 1",
                    'customfield_002': FauxFieldValue(None, 30),
                    'customfield_003': FauxFieldValue(None, ["R2", "R3", "R4"]),
                },
                changes=[
                    FauxChange("2018-01-02 01:01:01", [FauxChangeItem("status", "Backlog", "Next")]),
                    FauxChange("2018-01-03 01:01:01", [FauxChangeItem("resolution", None, "Closed"), FauxChangeItem("status", "Next", "Done")]),
                    FauxChange("2018-01-04 01:01:01", [FauxChangeItem("resolution", "Closed", None), FauxChangeItem("status", "Done", "QA")]),
                ]
            )
        ]
    )

@pytest.fixture
def settings():
    return {
        'fields': {
            'Release': 'Releases',
            'Team': 'Team',
            'Estimate': 'Size'
        },
        'known_values': {
            'Release': ['R1', 'R3']
        },
        'max_results': None,
        'verbose': False,
        'cycle': [
            {'name': 'Backlog',   'statuses': ['Start'],             'type': 'backlog'},
            {'name': 'Committed', 'statuses': ['Next'],              'type': 'accepted'},
            {'name': 'Build',     'statuses': ['Build'],             'type': 'accepted'},
            {'name': 'Test',      'statuses': ['Code review', 'QA'], 'type': 'accepted'},
            {'name': 'Done',      'statuses': ['Done'],              'type': 'complete'}
        ],
    }


def test_search(basic_jira, settings):
    qm = QueryManager(basic_jira, settings)
    assert qm.fields == {
        'Team': 'customfield_001',
        'Estimate': 'customfield_002',
        'Release': 'customfield_003',
    }

    issues = qm.find_issues("(filter=123)")
    assert issues == basic_jira._issues

def test_resolve_field_value(basic_jira, settings):
    qm = QueryManager(basic_jira, settings)
    issues = qm.find_issues("(filter=123)")

    assert qm.resolve_field_value(issues[0], "Team") == "Team 1"
    assert qm.resolve_field_value(issues[0], "Estimate") == 30
    assert qm.resolve_field_value(issues[0], "Release") == "R3"  # due to known_value

def test_iter_changes(basic_jira, settings):
    qm = QueryManager(basic_jira, settings)
    issues = qm.find_issues("(filter=123)")
    changes = list(qm.iter_changes(issues[0]))

    assert changes == [
        IssueSnapshot(change=None,     key="A-1", date=datetime.datetime(2018, 1, 1, 1, 1, 1), status="Backlog", resolution=None,     is_resolved=False),
        IssueSnapshot(change="status", key="A-1", date=datetime.datetime(2018, 1, 2, 1, 1, 1), status="Next",    resolution=None,     is_resolved=False),
        IssueSnapshot(change="status", key="A-1", date=datetime.datetime(2018, 1, 3, 1, 1, 1), status="Done",    resolution="Closed", is_resolved=True),
        IssueSnapshot(change="status", key="A-1", date=datetime.datetime(2018, 1, 4, 1, 1, 1), status="QA",      resolution=None,     is_resolved=False)
    ]
