import datetime

from .config import (
    force_list,
    expand_key,
    config_to_options
)

def test_force_list():
    assert force_list(None) == [None]
    assert force_list("foo") == ["foo"]
    assert force_list(("foo",)) == ["foo"]
    assert force_list(["foo"]) == ["foo"]

def test_expand_key():
    assert expand_key("foo") == "foo"
    assert expand_key("foo_bar") == "foo bar"
    assert expand_key("FOO") == "foo"
    assert expand_key("FOO_bar") == "foo bar"

def test_config_to_options_minimal():

    options = config_to_options("""\
Connection:
    Domain: https://foo.com

Query: (filter=123)

Workflow:
    Backlog: Backlog
    In progress: Build
    Done: Done
""")

    assert options['connection']['domain'] == 'https://foo.com'
    assert options['settings']['queries'][0] == {'value': None, 'jql': '(filter=123)'}

def test_config_to_options_maximal():

    options = config_to_options("""\
Connection:
    Domain: https://foo.com
    Username: user1
    Password: apassword

Queries:
    Attribute: Team
    Criteria:
        - Value: Team 1
          JQL: (filter=123)

        - Value: Team 2
          JQL: (filter=124)

Attributes:
    Team: Team
    Release: Fix version/s

Known values:
    Release:
        - "R01"
        - "R02"
        - "R03"

Workflow:
    Backlog: Backlog
    Committed: Next
    Build: Build
    Test:
        - Code review
        - QA
    Done: Done

Output:
    Quantiles:
        - 0.1
        - 0.2

    Backlog column: Backlog
    Committed column: Committed
    Final column: Test
    Done column: Done

    Cycle time data: cycletime.csv
    Percentiles data: percentiles.csv
    
    Scatterplot data: scatterplot.csv
    Scatterplot chart: scatterplot.png
    Scatterplot chart title: Cycle time scatter plot
    
    Histogram chart: histogram.png
    Histogram chart title: Cycle time histogram

    CFD data: cfd.csv
    CFD chart: cfd.png
    CFD chart title: Cumulative Flow Diagram

    Histogram data: histogram.csv
    
    Throughput data: throughput.csv
    Throughput frequency: 1D
    Throughput chart: throughput.png
    Throughput chart title: Throughput trend
    
    Burnup chart: burnup.png
    Burnup chart title: Burn-up

    Burnup forecast chart: burnup-forecast.png
    Burnup forecast chart title: Burn-up forecast
    Burnup forecast chart target: 100
    Burnup forecast chart deadline: 2018-06-01
    Burnup forecast chart deadline confidence: .85
    Burnup forecast chart trials: 50
    Burnup forecast chart throughput window: 30
    Burnup forecast chart throughput window end: 2018-03-01

    WIP chart: wip.png
    WIP chart title: Work in Progress
    WIP chart frequency: 3D

    Ageing WIP chart: ageing-wip.png
    Ageing WIP chart title: Ageing WIP

    Net flow chart: net-flow.png
    Net flow chart title: Net flow
    Net flow chart frequency: 5D

    Defects query: issueType = Bug
    Defects by priority chart: defects-by-priority.png
    Defects by priority chart title: Defects by priority
    Defects by priority field: Priority
    Defects by priority values:
        - Low
        - Medium
        - High
    Defects by type chart: defects-by-type.png
    Defects by type chart title: Defects by type
    Defects by type field: Type
    Defects by type values:
        - Config
        - Data
        - Code
    Defects by environment chart: defects-by-environment.png
    Defects by environment chart title: Defects by environment
    Defects by environment field: Environment
    Defects by environment values:
        - SIT
        - UAT
        - PROD
    Defects frequency: 4W-MON
    Defects window: 3

    Debt query: issueType = "Tech debt"
    Debt chart: tech-debt.png
    Debt chart title: Technical debt
    Debt priority field: Priority
    Debt priority values:
        - Low
        - Medium
        - High
    Debt frequency: 4W-MON
    Debt window: 3

    Waste query: issueType = Story AND resolution IN (Withdrawn, Invalid)
    Waste chart: waste.png
    Waste chart title: Waste
    Waste frequency: 4W-MON
    Waste window: 3
""")

    assert options['connection'] == {
        'domain': 'https://foo.com',
        'jira_client_options': {},
        'password': 'apassword',
        'username': 'user1'
    }
   
    assert options['settings'] == {
        'cycle': [
            {'name': 'Backlog', 'statuses': ['Backlog'], 'type': 'backlog'},
            {'name': 'Committed', 'statuses': ['Next'], 'type': 'accepted'},
            {'name': 'Build', 'statuses': ['Build'], 'type': 'accepted'},
            {'name': 'Test',
                'statuses': ['Code review', 'QA'],
                'type': 'accepted'},
            {'name': 'Done', 'statuses': ['Done'], 'type': 'complete'}
        ],

        'attributes': {'Release': 'Fix version/s', 'Team': 'Team'},
        'known_values': {'Release': ['R01', 'R02', 'R03']},
        'max_results': None,
        'verbose': False,

        'queries': [{'jql': '(filter=123)', 'value': 'Team 1'},
                    {'jql': '(filter=124)', 'value': 'Team 2'}],
        'query_attribute': 'Team',
                
        'backlog_column': 'Backlog',
        'committed_column': 'Committed',
        'final_column': 'Test',
        'done_column': 'Done',

        'quantiles': [0.1, 0.2],

        'cycle_time_data': 'cycletime.csv',
        
        'ageing_wip_chart': 'ageing-wip.png',
        'ageing_wip_chart_title': 'Ageing WIP',
        
        'burnup_chart': 'burnup.png',
        'burnup_chart_title': 'Burn-up',
        
        'burnup_forecast_chart': 'burnup-forecast.png',
        'burnup_forecast_chart_deadline': datetime.date(2018, 6, 1),
        'burnup_forecast_chart_deadline_confidence': 0.85,
        'burnup_forecast_chart_target': 100,
        'burnup_forecast_chart_throughput_window': 30,
        'burnup_forecast_chart_throughput_window_end': datetime.date(2018, 3, 1),
        'burnup_forecast_chart_title': 'Burn-up forecast',
        'burnup_forecast_chart_trials': 50,
        
        'cfd_chart': 'cfd.png',
        'cfd_chart_title': 'Cumulative Flow Diagram',
        'cfd_data': 'cfd.csv',
        
        'histogram_chart': 'histogram.png',
        'histogram_chart_title': 'Cycle time histogram',
        'histogram_data': 'histogram.csv',
        
        'net_flow_chart': 'net-flow.png',
        'net_flow_chart_frequency': '5D',
        'net_flow_chart_title': 'Net flow',
        
        'percentiles_data': 'percentiles.csv',
        
        'scatterplot_chart': 'scatterplot.png',
        'scatterplot_chart_title': 'Cycle time scatter plot',
        'scatterplot_data': 'scatterplot.csv',
        
        'throughput_chart': 'throughput.png',
        'throughput_chart_title': 'Throughput trend',
        'throughput_data': 'throughput.csv',
        'throughput_frequency': '1D',
        
        'wip_chart': 'wip.png',
        'wip_chart_frequency': '3D',
        'wip_chart_title': 'Work in Progress',

        'defects_query': 'issueType = Bug',
        'defects_by_priority_chart': 'defects-by-priority.png',
        'defects_by_priority_chart_title': 'Defects by priority',
        'defects_by_priority_field': 'Priority',
        'defects_by_priority_values': ['Low', 'Medium', 'High'],
        'defects_by_type_chart': 'defects-by-type.png',
        'defects_by_type_chart_title': 'Defects by type',
        'defects_by_type_field': 'Type',
        'defects_by_type_values': ['Config', 'Data', 'Code'],
        'defects_by_environment_chart': 'defects-by-environment.png',
        'defects_by_environment_chart_title': 'Defects by environment',
        'defects_by_environment_field': 'Environment',
        'defects_by_environment_values': ['SIT', 'UAT', 'PROD'],
        'defects_frequency': '4W-MON',
        'defects_window': 3,

        'debt_query': 'issueType = "Tech debt"',
        'debt_chart': 'tech-debt.png',
        'debt_chart_title': 'Technical debt',
        'debt_priority_field': 'Priority',
        'debt_priority_values': ['Low', 'Medium', 'High'],
        'debt_frequency': '4W-MON',
        'debt_window': 3,

        'waste_query': 'issueType = Story AND resolution IN (Withdrawn, Invalid)',
        'waste_chart': 'waste.png',
        'waste_chart_title': 'Waste',
        'waste_frequency': '4W-MON',
        'waste_window': 3,
    }

def test_config_to_options_strips_directories():

    options = config_to_options("""\
Connection:
    Domain: https://foo.com

Query: (filter=123)

Workflow:
    Backlog: Backlog
    In progress: Build
    Done: Done

Output:
    Cycle time data: tmp/cycletime.csv
    Percentiles data: /tmp/percentiles.csv
    Scatterplot data: ../scatterplot.csv
    Scatterplot chart: /foo/bar/baz/tmp/scatterplot.png
    Histogram chart: tmp/histogram.png
    CFD data: tmp/cfd.csv
    CFD chart: tmp/cfd.png
    Histogram data: tmp/histogram.csv
    Throughput data: tmp/throughput.csv
    Throughput chart: tmp/throughput.png
    Burnup chart: tmp/burnup.png
    Burnup forecast chart: tmp/burnup-forecast.png
    WIP chart: tmp/wip.png
    Ageing WIP chart: tmp/ageing-wip.png
    Net flow chart: tmp/net-flow.png
""")

    assert options['settings']['cycle_time_data'] == 'cycletime.csv'
    assert options['settings']['ageing_wip_chart'] == 'ageing-wip.png'
    assert options['settings']['burnup_chart'] == 'burnup.png'
    assert options['settings']['burnup_forecast_chart'] == 'burnup-forecast.png'
    assert options['settings']['cfd_chart'] == 'cfd.png'
    assert options['settings']['histogram_chart'] == 'histogram.png'
    assert options['settings']['histogram_data'] == 'histogram.csv'
    assert options['settings']['net_flow_chart'] == 'net-flow.png'
    assert options['settings']['percentiles_data'] == 'percentiles.csv'
    assert options['settings']['scatterplot_chart'] == 'scatterplot.png'
    assert options['settings']['scatterplot_data'] == 'scatterplot.csv'
    assert options['settings']['throughput_chart'] == 'throughput.png'
    assert options['settings']['throughput_data'] == 'throughput.csv'
    assert options['settings']['wip_chart'] == 'wip.png'
