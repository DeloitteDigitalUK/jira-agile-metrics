import yaml
from pydicti import odicti

from .cycletime import StatusTypes

class ConfigError(Exception):
    pass

# From http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts
def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=odicti):
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping
    )

    return yaml.load(stream, OrderedLoader)

def force_list(val):
    return val if isinstance(val, (list, tuple,)) else [val]

def config_to_options(data):
    config = ordered_load(data, yaml.SafeLoader)
    options = {
        'connection': {
            'domain': None,
            'username': None,
            'password': None,
            'jira-client-options': {}
        },
        'settings': {
            'queries': [],
            'query_attribute': None,
            'fields': {},
            'known_values': {},
            'cycle': []
        }
    }

    # Parse and validate Connection

    if 'connection' not in config:
        raise ConfigError("`Connection` section not found")

    if 'domain' not in config['connection']:
        raise ConfigError("No `Domain` set in the `Connection` section")

    options['connection']['domain'] = config['connection']['domain']

    if 'username' in config['connection']:
        options['connection']['username'] = config['connection']['username']

    if 'password' in config['connection']:
        options['connection']['password'] = config['connection']['password']

    if 'jira-client-options' in config['connection']:
        options['connection']['jira-client-options'] = config['connection']['jira-client-options']

    # Parse Queries (list of Criteria) and/or a single Criteria

    if 'queries' in config:
        options['settings']['query_attribute'] = config['queries'].get('attribute', None)
        for query in config['queries']['criteria']:
            options['settings']['queries'].append({
                'value': query.get('value', None),
                'project': query.get('project', None),
                'issue_types': force_list(query.get('issue types', [])),
                'valid_resolutions': force_list(query.get('valid resolutions', [])),
                'jql_filter': query.get('jql', None)
            })

    if 'criteria' in config:
        options['settings']['queries'].append({
            'value': config['criteria'].get('value', None),
            'project': config['criteria'].get('project', None),
            'issue_types': force_list(config['criteria'].get('issue types', [])),
            'valid_resolutions': force_list(config['criteria'].get('valid resolutions', [])),
            'jql_filter': config['criteria'].get('jql', None)
        })

    if len(options['settings']['queries']) == 0:
        raise ConfigError("No `Criteria` or `Queries` section found")

    # Parse Workflow. Assume first status is backlog and last status is complete.

    if 'workflow' not in config:
        raise ConfigError("`Workflow` section not found")

    if len(config['workflow'].keys()) < 2:
        raise ConfigError("`Workflow` section must contain at least two statuses")

    for name, statuses in config['workflow'].items():
        statuses = force_list(statuses)

        options['settings']['cycle'].append({
            "name": name,
            "type": StatusTypes.accepted,
            "statuses": statuses
        })

    options['settings']['cycle'][0]['type'] = StatusTypes.backlog
    options['settings']['cycle'][-1]['type'] = StatusTypes.complete

    # Parse attributes (fields)

    if 'attributes' in config:
        options['settings']['fields'] = dict(config['attributes'])

    if 'known values' in config:
        for name, values in config['known values'].items():
            options['settings']['known_values'][name] = force_list(values)

    return options
