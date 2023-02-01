import json
import itertools
import logging
import dateutil.parser
import dateutil.tz

from .config import ConfigError

logger = logging.getLogger(__name__)

def multi_getattr(obj, attr, **kw):
    attributes = attr.split(".")
    for i in attributes:
        try:
            obj = getattr(obj, i)
            if callable(obj):
                obj = obj()
        except AttributeError:
            logger.info("Not able to get data")
        
            if kw.has_key('default'):
                return kw['default']
            else:
                raise
    return obj

class IssueSnapshot(object):
    """A snapshot of the key fields of an issue
    at a point in its change history"""

    def __init__(self, change, key, date, from_string, to_string):
        self.change = change
        self.key = key
        self.date = date
        self.from_string = from_string
        self.to_string = to_string

    def __eq__(self, other):
        return all(
            (
                self.change == other.change,
                self.key == other.key,
                self.date.isoformat() == other.date.isoformat(),
                self.from_string == other.from_string,
                self.to_string == other.to_string,
            )
        )

    def __repr__(self):
        return "<IssueSnapshot change=%s key=%s date=%s from=%s to=%s>" % (
            self.change,
            self.key,
            self.date.isoformat(),
            self.from_string,
            self.to_string,
        )


class QueryManager(object):
    """Manage and execute queries"""

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
        self.jira_fields = self.jira.fields()

        if len(self.jira_fields) == 0:
            raise ConfigError(
                (
                    "No field data retrieved from JIRA. "
                    "This likely means a problem with the JIRA API."
                )
            ) from None

        self.jira_fields_to_names = {
            field["id"]: field["name"] for field in self.jira_fields
        }
        field_id = None

        for name, field in self.settings["attributes"].items():
            field_id = self.field_name_to_id(field)
            self.attributes_to_fields[name] = field_id
            self.fields_to_attributes[field_id] = name

    def field_name_to_id(self, name):
        arr_name = name.split(".")
        first_name = arr_name[0]
        append_text = ("." + ".".join(arr_name[1:])) if len(arr_name) > 1 else ""
        try:
            return next(
                (
                    f["id"]
                    for f in self.jira_fields
                    if f["name"].lower() == name.lower()
                )
            ) + append_text
        except StopIteration:

            # XXX: we are having problems with
            # this falsely claiming fields don't exist
            logger.debug(
                "Failed to look up %s in JIRA fields: %s",
                name,
                json.dumps(self.jira_fields),
            )

            raise ConfigError(
                "JIRA field with name `%s` does not exist"
                "(did you try to use the field id instead?)" % name
            ) from None

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

        try:
            field_value = multi_getattr(issue.fields, field_id)
            
        except AttributeError:
            field_name = self.jira_fields_to_names.get(
                field_id, "Unknown name"
            )
            logger.debug(
                (
                    "Could not get field value for field {}. "
                    "Probably this is a wrong workflow "
                    "field mapping"
                ).format(field_name)
            )
            field_value = None

        if field_value is None:
            return None

        value = getattr(field_value, "value", field_value)

        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                value = None
            else:
                values = [getattr(v, "name", v) for v in value]

                # is this a `Known Values` attribute?
                attribute_name = self.fields_to_attributes.get(field_id, None)
                if attribute_name not in self.settings["known_values"]:
                    value = values[0]
                else:
                    try:
                        value = next(
                            filter(
                                lambda v: v in values,
                                self.settings["known_values"][attribute_name],
                            )
                        )
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
            initial_value = self.resolve_field_value(
                issue, self.field_name_to_id(field)
            )
            try:
                initial_value = next(
                    filter(
                        lambda h: h.field == field,
                        itertools.chain.from_iterable(
                            [
                                c.items
                                for c in sorted(
                                    issue.changelog.histories,
                                    key=lambda c: dateutil.parser.parse(
                                        c.created
                                    ),
                                )
                            ]
                        ),
                    )
                ).fromString
            except StopIteration:
                pass

            yield IssueSnapshot(
                change=field,
                key=issue.key,
                date=dateutil.parser.parse(issue.fields.created),
                from_string=None,
                to_string=initial_value,
            )

        for change in sorted(
            issue.changelog.histories,
            key=lambda c: dateutil.parser.parse(c.created),
        ):
            change_date = dateutil.parser.parse(change.created, ignoretz=True)

            for item in change.items:
                if item.field in fields:
                    yield IssueSnapshot(
                        change=item.field,
                        key=issue.key,
                        date=change_date,
                        from_string=item.fromString,
                        to_string=item.toString,
                    )

    # Basic queries

    def find_issues(self, jql, expand="changelog"):
        """Return a list of issues with changelog metadata for the given
        JQL.
        """

        max_results = self.settings["max_results"]

        logger.info("Fetching issues with query `%s`", jql)
        if max_results:
            logger.info("Limiting to %d results", max_results)

        issues = self.jira.search_issues(
            jql, expand=expand, maxResults=max_results
        )
        logger.info("Fetched %d issues", len(issues))
        return issues
