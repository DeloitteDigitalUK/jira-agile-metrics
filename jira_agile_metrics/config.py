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
from .calculators.impediments import ImpedimentsCalculator
from .calculators.debt import DebtCalculator
from .calculators.defects import DefectsCalculator
from .calculators.waste import WasteCalculator

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
    ImpedimentsCalculator,
    DebtCalculator,
    DefectsCalculator,
    WasteCalculator,
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
            'http_proxy': None,
            'https_proxy': None,
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

            'cycle_time_data': None,
            'percentiles_data': None,

            'scatterplot_window': None,
            'scatterplot_data': None,
            'scatterplot_chart': None,
            'scatterplot_chart_title': None,
            
            'histogram_window': None,
            'histogram_data': None,
            'histogram_chart': None,
            'histogram_chart_title': None,

            'cfd_window': None,
            'cfd_data': None,
            'cfd_chart': None,
            'cfd_chart_title': None,
            
            'throughput_frequency': '1W-MON',
            'throughput_window': None,
            'throughput_data': None,
            'throughput_chart': None,
            'throughput_chart_title': None,
            
            'burnup_window': None,
            'burnup_chart': None,
            'burnup_chart_title': None,

            'burnup_forecast_window': None,
            'burnup_forecast_chart': None,
            'burnup_forecast_chart_title': None,
            'burnup_forecast_chart_target': None,
            'burnup_forecast_chart_deadline': None,
            'burnup_forecast_chart_deadline_confidence': None,
            'burnup_forecast_chart_trials': 100,
            'burnup_forecast_chart_throughput_window': 60,
            'burnup_forecast_chart_throughput_window_end': None,

            'wip_frequency': '1W-MON',
            'wip_window': None,
            'wip_chart': None,
            'wip_chart_title': None,

            'ageing_wip_chart': None,
            'ageing_wip_chart_title': None,

            'net_flow_frequency': '1W-MON',
            'net_flow_window': None,
            'net_flow_chart': None,
            'net_flow_chart_title': None,

            'impediments_data': None,
            'impediments_window': None,
            'impediments_chart': None,
            'impediments_chart_title': None,
            'impediments_days_chart': None,
            'impediments_days_chart_title': None,
            'impediments_status_chart': None,
            'impediments_status_chart_title': None,
            'impediments_status_days_chart': None,
            'impediments_status_days_chart_title': None,
            
            'defects_query': None,
            'defects_window': None,
            'defects_priority_field': None,
            'defects_priority_values': None,
            'defects_type_field': None,
            'defects_type_values': None,
            'defects_environment_field': None,
            'defects_environment_values': None,

            'defects_by_priority_chart': None,
            'defects_by_priority_chart_title': None,
            'defects_by_type_chart': None,
            'defects_by_type_chart_title': None,
            'defects_by_environment_chart': None,
            'defects_by_environment_chart_title': None,
        
            'debt_query': None,
            'debt_window': None,
            'debt_priority_field': None,
            'debt_priority_values': None,
            'debt_chart': None,
            'debt_chart_title': None,
            'debt_age_chart': None,
            'debt_age_chart_title': None,
            'debt_age_chart_bins': [30, 60, 90],

            'waste_query': None,
            'waste_window': None,
            'waste_frequency': 'MS',
            'waste_chart': None,
            'waste_chart_title': None,
        }
    }

    # Parse and validate Connection

    if 'domain' in config['connection']:
        options['connection']['domain'] = config['connection']['domain']

    if 'username' in config['connection']:
        options['connection']['username'] = config['connection']['username']

    if 'password' in config['connection']:
        options['connection']['password'] = config['connection']['password']
    
    if 'http proxy' in config['connection']:
        options['connection']['http_proxy'] = config['connection']['http proxy']
    
    if 'https proxy' in config['connection']:
        options['connection']['https_proxy'] = config['connection']['https proxy']

    if 'jira client options' in config['connection']:
        options['connection']['jira_client_options'] = config['connection']['jira client options']

    # Parse and validate output options
    if 'output' in config:

        if 'quantiles' in config['output']:
            try:
                options['settings']['quantiles'] = list(map(float, config['output']['quantiles']))
            except ValueError:
                raise ConfigError("Could not convert value `%s` for key `quantiles` to a list of decimals" % (config['output']['quantiles'],)) from None

        # int values
        for key in [
            'scatterplot_window',
            'histogram_window',
            'wip_window',
            'net_flow_window',
            'throughput_window',
            'cfd_window',
            'burnup_window',
            'burnup_forecast_window',
            'burnup_forecast_chart_throughput_window',
            'burnup_forecast_chart_target',
            'burnup_forecast_chart_trials',
            'impediments_window',
            'defects_window',
            'debt_window',
            'waste_window',
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
            'impediments_data',
            'impediments_chart',
            'impediments_days_chart',
            'impediments_status_chart',
            'impediments_status_days_chart',
            'defects_by_priority_chart',
            'defects_by_type_chart',
            'defects_by_environment_chart',
            'debt_chart',
            'debt_age_chart',
            'waste_chart',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = os.path.basename(config['output'][expand_key(key)])

        # list values
        for key in [
            'defects_priority_values',
            'defects_type_values',
            'defects_environment_values',
            'debt_priority_values',
            'debt_age_chart_bins',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = force_list(config['output'][expand_key(key)])

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
            'wip_frequency',
            'ageing_wip_chart_title',
            'net_flow_chart_title',
            'net_flow_frequency',
            'impediments_chart_title',
            'impediments_days_chart_title',
            'impediments_status_chart_title',
            'impediments_status_days_chart_title',
            'defects_query',
            'defects_by_priority_chart_title',
            'defects_priority_field',
            'defects_by_type_chart_title',
            'defects_type_field',
            'defects_by_environment_chart_title',
            'defects_environment_field',
            'debt_query',
            'debt_priority_field',
            'debt_chart_title',
            'debt_age_chart_title',
            'waste_query',
            'waste_frequency',
            'waste_chart_title',
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

    if options['settings']['backlog_column'] is None:
        options['settings']['backlog_column'] = options['settings']['cycle'][0]['name']
    if options['settings']['committed_column'] is None:
        options['settings']['committed_column'] = options['settings']['cycle'][1]['name']
    if options['settings']['final_column'] is None:
        options['settings']['final_column'] = options['settings']['cycle'][-2]['name']
    if options['settings']['done_column'] is None:
        options['settings']['done_column'] = options['settings']['cycle'][-1]['name']

    # Parse attributes (fields)

    if 'attributes' in config:
        options['settings']['attributes'] = dict(config['attributes'])

    if 'known values' in config:
        for name, values in config['known values'].items():
            options['settings']['known_values'][name] = force_list(values)

    return options
