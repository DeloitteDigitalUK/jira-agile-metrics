import itertools
import dateutil.parser
import dateutil.tz

class IssueSnapshot(object):
    """A snapshot of the key fields of an issue at a point in its change history
    """

    def __init__(self, change, key, date, status, resolution, is_resolved):
        self.change = change
        self.key = key
        self.date = date.astimezone(dateutil.tz.tzutc())
        self.status = status
        self.resolution = resolution
        self.is_resolved = is_resolved

    def __hash__(self):
        return hash(self.key)
    
    def __eq__(self, other):
        return all((
            self.change == other.change,
            self.key == other.key,
            self.date.isoformat() == other.date.isoformat(),
            self.status == other.status,
            self.resolution == other.resolution,
            self.is_resolved == other.is_resolved,
        ))

    def __repr__(self):
        return "<IssueSnapshot change=%s key=%s date=%s status=%s resolution=%s is_resolved=%s>" % (
            self.change, self.key, self.date.isoformat(), self.status, self.resolution, self.is_resolved
        )

class QueryManager(object):
    """Manage and execute queries
    """

    settings = dict(
        fields={},
        known_values={},
        max_results=False,
    )

    fields = {}  # resolved at runtime to JIRA fields

    def __init__(self, jira, settings):
        self.jira = jira
        self.settings = self.settings.copy()
        self.settings.update(settings)
        self.fields = {}
        self.resolve_fields()

    # Helpers

    def resolve_fields(self):
        fields = self.jira.fields()

        for name, field in self.settings['fields'].items():
            try:
                self.fields[name] = next((f['id'] for f in fields if f['name'].lower() == field.lower()))
            except StopIteration:
                raise Exception("JIRA field with name `%s` does not exist (did you try to use the field id instead?)" % field)

    def resolve_field_value(self, issue, name):
        field_value = getattr(issue.fields, self.fields[name])

        if field_value is None:
            return None

        value = getattr(field_value, 'value', field_value)

        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                value = None
            else:
                values = [getattr(v, 'name', v) for v in value]
                if name not in self.settings['known_values']:
                    value = values[0]
                else:
                    try:
                        value = next(filter(lambda v: v in values, self.settings['known_values'][name]))
                    except StopIteration:
                        value = None

        if not isinstance(value, (int, float, bool, str, bytes)):
            try:
                value = str(value)
            except TypeError:
                pass

        return value

    def iter_changes(self, issue):
        """Yield an IssueSnapshot for each time the issue changed status
        """

        is_resolved = False

        # Find the first status change, if any
        status_changes = list(filter(
            lambda h: h.field == 'status',
            itertools.chain.from_iterable([c.items for c in issue.changelog.histories])
        ))
        last_status = status_changes[0].fromString if len(status_changes) > 0 else issue.fields.status.name
        last_resolution = None

        # Issue was created
        yield IssueSnapshot(
            change=None,
            key=issue.key,
            date=dateutil.parser.parse(issue.fields.created),
            status=last_status,
            resolution=None,
            is_resolved=is_resolved
        )

        for change in issue.changelog.histories:
            change_date = dateutil.parser.parse(change.created)

            resolutions = list(filter(lambda i: i.field == 'resolution', change.items))
            is_resolved = (resolutions[-1].to is not None) if len(resolutions) > 0 else is_resolved

            for item in change.items:
                if item.field == 'status':
                    # Status was changed
                    last_status = item.toString
                    yield IssueSnapshot(
                        change=item.field,
                        key=issue.key,
                        date=change_date,
                        status=last_status,
                        resolution=last_resolution,
                        is_resolved=is_resolved
                    )
                elif item.field == 'resolution':
                    last_resolution = item.toString

    # Basic queries

    def find_issues(self, jql):
        """Return a list of issues with changelog metadata for the given
        JQL.
        """

        if self.settings.get('verbose', False):
            print("Fetching issues with query:", jql)

        issues = self.jira.search_issues(jql, expand='changelog', maxResults=self.settings['max_results'])

        if self.settings.get('verbose', False):
            print("Fetched", len(issues), "issues")

        return issues
