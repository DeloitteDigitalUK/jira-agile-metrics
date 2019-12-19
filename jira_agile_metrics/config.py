import logging
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
from .calculators.progressreport import ProgressReportCalculator

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
    ProgressReportCalculator,
)

logger = logging.getLogger(__name__)

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

def force_int(key, value):
    try:
        return int(value)
    except ValueError:
        raise ConfigError("Could not convert value `%s` for key `%s` to integer" % (value, expand_key(key),)) from None

def force_float(key, value):
    try:
        return float(value)
    except ValueError:
        raise ConfigError("Could not convert value `%s` for key `%s` to decimal" % (value, expand_key(key),)) from None

def force_date(key, value):
    if not isinstance(value, datetime.date):
        raise ConfigError("Value `%s` for key `%s` is not a date" % (value, expand_key(key),))
    return value

def expand_key(key):
    return str(key).replace('_', ' ').lower()

def to_progress_report_teams_list(value):
    return [{
        'name': val[expand_key('name')] if expand_key('name') in val else None,
        'wip': force_int('wip', val[expand_key('wip')]) if expand_key('wip') in val else 1,
        'min_throughput': force_int('min_throughput', val[expand_key('min_throughput')]) if expand_key('min_throughput') in val else None,
        'max_throughput': force_int('max_throughput', val[expand_key('max_throughput')]) if expand_key('max_throughput') in val else None,
        'throughput_samples': val[expand_key('throughput_samples')] if expand_key('throughput_samples') in val else None,
        'throughput_samples_window': force_int('throughput_samples_window', val[expand_key('throughput_samples_window')]) if expand_key('throughput_samples_window') in val else None,
    } for val in value]

def to_progress_report_outcomes_list(value):
    return [{
        'name': val[expand_key('name')] if expand_key('name') in val else None,
        'key': val[expand_key('key')] if expand_key('key') in val else None,
        'deadline': force_date('deadline', val[expand_key('deadline')]) if expand_key('deadline') in val else None,
        'epic_query': val[expand_key('epic_query')] if expand_key('epic_query') in val else None,
    } for val in value]


def config_to_options(data, cwd=None, extended=False):
    try:
        config = ordered_load(data, yaml.SafeLoader)
    except Exception:
        raise ConfigError("Unable to parse YAML configuration file.") from None
    
    if config is None:
        raise ConfigError("Configuration file is empty") from None

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

            'progress_report': None,
            'progress_report_title': None,
            'progress_report_epic_query_template': None,
            'progress_report_story_query_template': None,
            'progress_report_epic_deadline_field': None,
            'progress_report_epic_min_stories_field': None,
            'progress_report_epic_max_stories_field': None,
            'progress_report_epic_team_field': None,
            'progress_report_teams': None,
            'progress_report_outcomes': None,
            'progress_report_outcome_query': None,
            'progress_report_outcome_deadline_field': None,
        }
    }

    # Recursively parse an `extends` file but only if a base path is given,
    # otherwise we can plausible leak files in server mode.
    if 'extends' in config:
        if cwd is None:
            raise ConfigError("`extends` is not supported here.")

        extends_filename = os.path.abspath(os.path.normpath(os.path.join(cwd, config['extends'].replace('/', os.path.sep))))

        if not os.path.exists(extends_filename):
            raise ConfigError("File `%s` referenced in `extends` not found." % extends_filename) from None
        
        logger.debug("Extending file %s" % extends_filename)
        with open(extends_filename) as extends_file:
            options = config_to_options(extends_file.read(), cwd=os.path.dirname(extends_filename), extended=True)

    # Parse and validate Connection

    if 'connection' in config:

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
                options['settings'][key] = force_int(key, config['output'][expand_key(key)])
        
        # float values
        for key in [
            'burnup_forecast_chart_deadline_confidence',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = force_float(key, config['output'][expand_key(key)])

        # date values
        for key in [
            'burnup_forecast_chart_throughput_window_end',
            'burnup_forecast_chart_deadline',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = force_date(key, config['output'][expand_key(key)])
        
        # file name values
        for key in [
            'scatterplot_chart',
            'histogram_chart',
            'cfd_chart',
            'throughput_chart',
            'burnup_chart',
            'burnup_forecast_chart',
            'wip_chart',
            'ageing_wip_chart',
            'net_flow_chart',
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
            'progress_report',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = os.path.basename(config['output'][expand_key(key)])
        
        # file name list values
        for key in [
            'cycle_time_data',
            'cfd_data',
            'scatterplot_data',
            'histogram_data',
            'throughput_data',
            'percentiles_data',
            
            'impediments_data',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = list(map(os.path.basename, force_list(config['output'][expand_key(key)])))

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
            'progress_report_title',
            'progress_report_epic_query_template',
            'progress_report_story_query_template',
            'progress_report_epic_deadline_field',
            'progress_report_epic_min_stories_field',
            'progress_report_epic_max_stories_field',
            'progress_report_epic_team_field',
            'progress_report_outcome_query',
            'progress_report_outcome_deadline_field',
        ]:
            if expand_key(key) in config['output']:
                options['settings'][key] = config['output'][expand_key(key)]

        # Special objects for progress reports
        if expand_key('progress_report_teams') in config['output']:
            options['settings']['progress_report_teams'] = to_progress_report_teams_list(config['output'][expand_key('progress_report_teams')])
        if expand_key('progress_report_outcomes') in config['output']:
            options['settings']['progress_report_outcomes'] = to_progress_report_outcomes_list(config['output'][expand_key('progress_report_outcomes')])

    # Parse Queries and/or a single Query

    if 'queries' in config:
        options['settings']['query_attribute'] = config['queries'].get('attribute', None)
        options['settings']['queries'] = [{
            'value': q.get('value', None),
            'jql': q.get('jql', None),
        } for q in config['queries']['criteria']]

    if 'query' in config:
        options['settings']['queries'] = [{
            'value': None,
            'jql': config['query'],
        }]

    if not extended and len(options['settings']['queries']) == 0:
        logger.warning("No `Query` value or `Queries` section found. Many calculators rely on one of these.")

    # Parse Workflow. Assume first status is backlog and last status is complete.

    if 'workflow' in config:
        if len(config['workflow'].keys()) < 3:
            raise ConfigError("`Workflow` section must contain at least three statuses")
        
        options['settings']['cycle'] = [{
            "name": name,
            "type": StatusTypes.accepted,
            "statuses": force_list(statuses)
        } for name, statuses in config['workflow'].items()]

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

    # Make sure we have workflow (but only if this file is not being extended by another)
    if not extended and len(options['settings']['cycle']) == 0:
        raise ConfigError("`Workflow` section not found")

    # Parse attributes (fields) - merge from extended file if needed

    if 'attributes' in config:
        options['settings']['attributes'].update(dict(config['attributes']))

    if 'known values' in config:
        for name, values in config['known values'].items():
            options['settings']['known_values'][name] = force_list(values)

    return options
