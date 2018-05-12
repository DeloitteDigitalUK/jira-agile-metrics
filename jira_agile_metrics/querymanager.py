import itertools
import logging
import dateutil.parser
import dateutil.tz

from .config import ConfigError

logger = logging.getLogger(__name__)

class IssueSnapshot(object):
    """A snapshot of the key fields of an issue at a point in its change history
    """

    def __init__(self, change, key, date, fromString, toString):
        self.change = change
        self.key = key
        self.date = date.astimezone(dateutil.tz.tzutc())
        self.fromString = fromString
        self.toString = toString

    def __eq__(self, other):
        return all((
            self.change == other.change,
            self.key == other.key,
            self.date.isoformat() == other.date.isoformat(),
            self.fromString == other.fromString,
            self.toString == other.toString
        ))

    def __repr__(self):
        return "<IssueSnapshot change=%s key=%s date=%s from=%s to=%s>" % (
            self.change, self.key, self.date.isoformat(), self.fromString, self.toString,
        )

class QueryManager(object):
    """Manage and execute queries
    """

    settings = dict(
        attributes={},
        known_values={},
        max_results=False,
    )

    def __init__(self, jira, settings):
        self.jira = jira
        self.settings = self.settings.copy()
        self.settings.update(settings)

        self.attributes_to_fields = {}
        self.fields_to_attributes = {}

        # Look up fields in JIRA and resolve attributes to fields
        logger.debug("Resolving JIRA fields")
        fields = self.jira.fields()
        field_id = None

        for name, field in self.settings['attributes'].items():
            try:
                field_id = next((f['id'] for f in fields if f['name'].lower() == field.lower()))
            except StopIteration:
                raise ConfigError("JIRA field with name `%s` does not exist (did you try to use the field id instead?)" % field) from None
            else:
                self.attributes_to_fields[name] = field_id
                self.fields_to_attributes[field_id] = name

    def resolve_attribute_value(self, issue, attribute_name):
        """Given an attribute name (i.e. one named in the config file and
        mapped to a field in JIRA), return its value from the given issue.
        Respects the `Known Values` settings and tries to resolve complex
        data types.
        """
        field_id = self.attributes_to_fields[attribute_name]
        return self.resolve_field_value(issue, field_id)

    def resolve_field_value(self, issue, field_id):
        """Given a JIRA internal field id, return its value from the given
        issue. Respects the `Known Values` settings and tries to resolve
        complex data types.
        """

        field_value = getattr(issue.fields, field_id)

        if field_value is None:
            return None

        value = getattr(field_value, 'value', field_value)

        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                value = None
            else:
                values = [getattr(v, 'name', v) for v in value]

                # is this a `Known Values` attribute?
                attribute_name = self.fields_to_attributes.get(field_id, None)
                if attribute_name not in self.settings['known_values']:
                    value = values[0]
                    logger.debug("Resolving value for %s to %s as %s is not in known_values", field_id, value, attribute_name)
                else:
                    try:
                        value = next(filter(lambda v: v in values, self.settings['known_values'][attribute_name]))
                        logger.debug("Resolving value for %s to %s as %s from known_values", field_id, value, attribute_name)
                    except StopIteration:
                        value = None

        if not isinstance(value, (int, float, bool, str, bytes)):
            try:
                value = str(value)
            except TypeError:
                pass

        return value

    def iter_changes(self, issue, fields):
        """Yield an IssueSnapshot for each time the issue changed, including an
        initial value. `fields` is a list of fields to monitor, e.g.
        `['status']`.
        """

        for field in fields:
            initial_value = self.resolve_field_value(issue, field)
            try:
                initial_value = next(filter(
                    lambda h: h.field == field,
                    itertools.chain.from_iterable([c.items for c in issue.changelog.histories])
                )).fromString
            except StopIteration:
                pass
            
            yield IssueSnapshot(
                change=field,
                key=issue.key,
                date=dateutil.parser.parse(issue.fields.created),
                fromString=None,
                toString=initial_value,
            )

        for change in issue.changelog.histories:
            change_date = dateutil.parser.parse(change.created)

            for item in change.items:
                if item.field in fields:
                    yield IssueSnapshot(
                        change=item.field,
                        key=issue.key,
                        date=change_date,
                        fromString=item.fromString,
                        toString=item.toString
                    )

    # Basic queries

    def find_issues(self, jql):
        """Return a list of issues with changelog metadata for the given
        JQL.
        """

        max_results = self.settings['max_results']

        logger.info("Fetching issues with query `%s`", jql)
        if max_results:
            logger.info("Limiting to %d results", max_results)

        issues = self.jira.search_issues(jql, expand='changelog', maxResults=max_results)
        logger.info("Fetched %d issues", len(issues))

        return issues
