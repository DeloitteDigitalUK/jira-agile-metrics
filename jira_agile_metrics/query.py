import itertools
import datetime
import dateutil.parser
import dateutil.tz

def to_datetime(date):
    """Turn a date into a datetime at midnight.
    """
    return datetime.datetime.combine(date, datetime.datetime.min.time())


def strip_time(datetime):
    """Return a version of the datetime with time set to zero.
    """
    return to_datetime(datetime.date())

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

    def __repr__(self):
        return "<IssueSnapshot change=%s key=%s date=%s status=%s resolution=%s is_resolved=%s>" % (
            self.change, self.key, self.date.isoformat(), self.status, self.resolution, self.is_resolved
        )

class QueryManager(object):
    """Manage and execute queries
    """

    settings = dict(
        queries=[],
        query_attribute=None,
        fields={},
        known_values={},
        max_results=False,
    )

    fields = {}  # resolved at runtime to JIRA fields

    def __init__(self, jira, **kwargs):
        self.jira = jira
        settings = self.settings.copy()
        settings.update(kwargs)

        self.settings = settings
        self.resolve_fields()

    # Helpers

    def resolve_fields(self):
        fields = self.jira.fields()

        for name, field in self.settings['fields'].items():
            try:
                self.fields[name] = next((f['id'] for f in fields if f['name'].lower() == field.lower()))
            except StopIteration:
                raise Exception("JIRA field with name `%s` does not exist (did you try to use the field id instead?)" % field)

    def resolve_field_value(self, issue, name, field_name):
        field_value = getattr(issue.fields, field_name)

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
                        value = next(itertools.ifilter(lambda v: v in values, self.settings['known_values'][name]))
                    except StopIteration:
                        value = None

        if not isinstance(value, (int, float, bool, str, unicode)):
            try:
                value = str(value)
            except TypeError:
                pass

        return value

    def iter_changes(self, issue, include_resolution_changes=True):
        """Yield an IssueSnapshot for each time the issue changed status or
        resolution
        """

        is_resolved = False

        # Find the first status change, if any
        status_changes = filter(
            lambda h: h.field == 'status',
            itertools.chain.from_iterable([c.items for c in issue.changelog.histories])
        )
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

            resolutions = filter(lambda i: i.field == 'resolution', change.items)
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
                    if include_resolution_changes:
                        yield IssueSnapshot(
                            change=item.field,
                            key=issue.key,
                            date=change_date,
                            status=last_status,
                            resolution=last_resolution,
                            is_resolved=is_resolved
                        )

    # Basic queries

    def find_issues(self, criteria={}, jql=None, order='KEY ASC', verbose=False):
        """Return a list of issues with changelog metadata.

        Searches for the `issue_types`, `project`, `valid_resolutions` and
        'jql_filter' set in the passed-in `criteria` object.

        Pass a JQL string to further qualify the query results.
        """

        query = []

        if criteria.get('project', False):
            query.append('project = %s' % criteria['project'])

        if criteria.get('issue_types', False):
            query.append('issueType IN (%s)' % ', '.join(['"%s"' % t for t in criteria['issue_types']]))

        if criteria.get('valid_resolutions', False):
            query.append('(resolution IS EMPTY OR resolution IN (%s))' % ', '.join(['"%s"' % r for r in criteria['valid_resolutions']]))

        if criteria.get('jql_filter') is not None:
            query.append('(%s)' % criteria['jql_filter'])

        if jql is not None:
            query.append('(%s)' % jql)

        queryString = "%s ORDER BY %s" % (' AND '.join(query), order,)

        if verbose:
            print("Fetching issues with query:", queryString)

        issues = self.jira.search_issues(queryString, expand='changelog', maxResults=self.settings['max_results'])

        if verbose:
            print("Fetched", len(issues), "issues")

        return issues
