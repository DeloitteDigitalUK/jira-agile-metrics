import yaml
import dateutil.parser

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

def expand_key(key):
    return str(key).replace('_', ' ')

def config_to_options(data):
    config = ordered_load(data, yaml.SafeLoader)
    options = {
        'connection': {
            'domain': None,
            'username': None,
            'password': None,
            'jira_client_options': {}
        },
        'settings': {
            'queries': [],
            'query_attribute': None,
            'fields': {},
            'known_values': {},
            'cycle': [],
            'max_results': None,
            'verbose': False,
        
            'quantiles': [0.5, 0.85, 0.95],

            'backlog_column': None,
            'committed_column': None,
            'final_column': None,
            'done_column': None,

            'throughput_frequency': '1W-MON',
            
            'cycle_time_data': None,
            'cfd_data': None,
            'scatterplot_data': None,
            'histogram_data': None,
            'throughput_data': None,
            'percentiles_data': None,

            'scatterplot_chart': None,
            'scatterplot_chart_title': None,
            
            'histogram_chart': None,
            'histogram_chart_title': None,

            'cfd_chart': None,
            'cfd_chart_title': None,
            
            'throughput_chart': None,
            'throughput_chart_title': None,
            
            'burnup_chart': None,
            'burnup_chart_title': None,

            'burnup_forecast_chart': None,
            'burnup_forecast_chart_title': None,
            'burnup_forecast_chart_target': None,
            'burnup_forecast_chart_deadline': None,
            'burnup_forecast_chart_deadline_confidence': None,
            'burnup_forecast_chart_trials': 100,
            'burnup_forecast_chart_throughput_window': 60,
            'burnup_forecast_chart_throughput_window_end': None,

            'wip_chart': None,
            'wip_chart_title': None,
            'wip_chart_frequency': '1W-MON',

            'ageing_wip_chart': None,
            'ageing_wip_chart_title': None,

            'net_flow_chart': None,
            'net_flow_chart_title': None,
            'net_flow_chart_frequency': '1W-MON',
        }
    }

    # Parse and validate Connection

    if 'domain' in config['connection']:
        options['connection']['domain'] = config['connection']['domain']

    if 'username' in config['connection']:
        options['connection']['username'] = config['connection']['username']

    if 'password' in config['connection']:
        options['connection']['password'] = config['connection']['password']

    if 'jira_client_options' in config['connection']:
        options['connection']['jira_client_options'] = config['connection']['jira_client_options']

    # Parse and validate output options
    if 'output' in config:

        if 'quantiles' in config['output']:
            options['settings']['quantiles'] = list(map(float, config['output']['quantiles']))

        # int values
        for key in [
            'burnup_forecast_chart_throughput_window',
            'burnup_forecast_chart_target',
            'burnup_forecast_chart_trials',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = int(config['output'][expand_key(key)])
        
        # float values
        for key in [
            'burnup_forecast_chart_deadline_confidence',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = float(config['output'][expand_key(key)])

        # date values
        for key in [
            'burnup_forecast_chart_throughput_window_end',
            'burnup_forecast_chart_deadline',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = dateutil.parser.parse(config['output'][expand_key(key)])

        # string values that copy straight over
        for key in [
            'backlog_column',
            'committed_column',
            'final_column',
            'done_column',

            'throughput_frequency',

            'cycle_time_data',
            'cfd_data',
            'scatterplot_data',
            'histogram_data',
            'throughput_data',
            'percentiles_data',

            'scatterplot_chart',
            'scatterplot_chart_title',
            
            'histogram_chart',
            'histogram_chart_title',

            'cfd_chart',
            'cfd_chart_title',
            
            'throughput_chart',
            'throughput_chart_title',
            
            'burnup_chart',
            'burnup_chart_title',

            'burnup_forecast_chart',
            'burnup_forecast_chart_title',
        
            'wip_chart',
            'wip_chart_title',
            'wip_chart_frequency',

            'ageing_wip_chart',
            'ageing_wip_chart_title',

            'net_flow_chart',
            'net_flow_chart_title',
            'net_flow_chart_frequency',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = config['output'][expand_key(key)]

    # Parse Queries and/or a single Query

    if 'queries' in config:
        options['settings']['query_attribute'] = config['queries'].get('attribute', None)
        for query in config['queries']['criteria']:
            options['settings']['queries'].append({
                'value': query.get('value', None),
                'jql': query.get('jql', None),
            })

    if 'query' in config:
        options['settings']['queries'].append({
            'value': None,
            'jql': config['query'],
        })

    if len(options['settings']['queries']) == 0:
        raise ConfigError("No `Query` value or `Queries` section found")

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
