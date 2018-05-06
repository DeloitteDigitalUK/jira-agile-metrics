import pytest

# Fake a portion of the JIRA API

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
        self.items = [FauxChangeItem(*i) for i in items]

class FauxChangelog(object):
    def __init__(self, changes):
        self.histories = changes

class FauxIssue(object):
    def __init__(self, key, changes, **fields):
        self.key = key
        self.fields = FauxFields(fields)
        self.changelog = FauxChangelog(changes)

class FauxJIRA(object):

    def __init__(self, fields, issues, options={'server': 'https://example.org'}):
        self._options = options
        self._fields = fields  # [{ id, name }]
        self._issues = issues

    def fields(self):
        return self._fields

    def search_issues(self, jql, *args, **kwargs):
        return self._issues

# Simple `settings` object that can be extended

@pytest.fixture
def basic_settings():
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
