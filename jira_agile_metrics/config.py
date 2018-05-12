import yaml
import datetime
import os.path

from pydicti import odicti

from .utils import StatusTypes

from .calculators.cycletime import CycleTimeCalculator
from .calculators.cfd import CFDCalculator
from .calculators.scatterplot import ScatterplotCalculator
from .calculators.histogram import HistogramCalculator
from .calculators.percentiles import PercentilesCalculator
from .calculators.throughput import ThroughputCalculator
from .calculators.burnup import BurnupCalculator
from .calculators.wip import WIPChartCalculator
from .calculators.netflow import NetFlowChartCalculator
from .calculators.ageingwip import AgeingWIPChartCalculator
from .calculators.forecast import BurnupForecastCalculator

CALCULATORS = (
    CycleTimeCalculator,  # should come first -- others depend on results from this one
    CFDCalculator,        # needs to come before burn-up charts, wip charts, and net flow charts
    ScatterplotCalculator,
    HistogramCalculator,
    PercentilesCalculator,
    ThroughputCalculator,
    BurnupCalculator,
    WIPChartCalculator,
    NetFlowChartCalculator,
    AgeingWIPChartCalculator,
    BurnupForecastCalculator,
)

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
    return list(val) if isinstance(val, (list, tuple,)) else [val]

def expand_key(key):
    return str(key).replace('_', ' ').lower()

def config_to_options(data):
    try:
        config = ordered_load(data, yaml.SafeLoader)
    except Exception:
        raise ConfigError("Unable to parse YAML configuration file.") from None

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
            'attributes': {},
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
            try:
                options['settings']['quantiles'] = list(map(float, config['output']['quantiles']))
            except ValueError:
                raise ConfigError("Could not convert value `%s` for key `quantiles` to a list of decimals" % (config['output']['quantiles'],)) from None

        # int values
        for key in [
            'burnup_forecast_chart_throughput_window',
            'burnup_forecast_chart_target',
            'burnup_forecast_chart_trials',
        ]:
            if expand_key(key) in config['output']:
                value = config['output'][expand_key(key)]
                try:
                    options['settings'][key] = int(value)
                except ValueError:
                    raise ConfigError("Could not convert value `%s` for key `%s` to integer" % (value, expand_key(key),)) from None
        
        # float values
        for key in [
            'burnup_forecast_chart_deadline_confidence',
        ]:
            if expand_key(key) in config['output']:
                value = config['output'][expand_key(key)]
                try:
                    options['settings'][key] = float(value)
                except ValueError:
                    raise ConfigError("Could not convert value `%s` for key `%s` to decimal" % (value, expand_key(key),)) from None

        # date values
        for key in [
            'burnup_forecast_chart_throughput_window_end',
            'burnup_forecast_chart_deadline',
        ]:
            if expand_key(key) in config['output']:
                value = config['output'][expand_key(key)]
                if not isinstance(value, datetime.date):
                    raise ConfigError("Value `%s` for key `%s` is not a date" % (value, expand_key(key),))
                options['settings'][key] = value
        
        # file name values
        for key in [
            'cycle_time_data',
            'cfd_data',
            'scatterplot_data',
            'histogram_data',
            'throughput_data',
            'percentiles_data',
            'scatterplot_chart',
            'histogram_chart',
            'cfd_chart',
            'throughput_chart',
            'burnup_chart',
            'burnup_forecast_chart',
            'wip_chart',
            'ageing_wip_chart',
            'net_flow_chart',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = os.path.basename(config['output'][expand_key(key)])

        # string values that copy straight over
        for key in [
            'backlog_column',
            'committed_column',
            'final_column',
            'done_column',
            'throughput_frequency',
            'scatterplot_chart_title',
            'histogram_chart_title',
            'cfd_chart_title',
            'throughput_chart_title',
            'burnup_chart_title',
            'burnup_forecast_chart_title',
            'wip_chart_title',
            'wip_chart_frequency',
            'ageing_wip_chart_title',
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

    if len(config['workflow'].keys()) < 3:
        raise ConfigError("`Workflow` section must contain at least three statuses")

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
        options['settings']['attributes'] = dict(config['attributes'])

    if 'known values' in config:
        for name, values in config['known values'].items():
            options['settings']['known_values'][name] = force_list(values)

    return options
