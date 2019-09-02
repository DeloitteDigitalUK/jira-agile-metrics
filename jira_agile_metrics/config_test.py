import datetime
import tempfile
import os.path

from .config import (
    force_list,
    expand_key,
    config_to_options,
    ConfigError
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

    assert options['settings']['backlog_column'] == 'Backlog'
    assert options['settings']['committed_column'] == 'In progress'
    assert options['settings']['final_column'] == 'In progress'
    assert options['settings']['done_column'] == 'Done'
    

def test_config_to_options_maximal():

    options = config_to_options("""\
Connection:
    Domain: https://foo.com
    Username: user1
    Password: apassword
    HTTP Proxy: https://proxy1.local
    HTTPS Proxy: https://proxy2.local

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
    
    Scatterplot window: 30
    Scatterplot data: scatterplot.csv
    Scatterplot chart: scatterplot.png
    Scatterplot chart title: Cycle time scatter plot
    
    Histogram window: 30
    Histogram chart: histogram.png
    Histogram chart title: Cycle time histogram

    CFD window: 30
    CFD data: cfd.csv
    CFD chart: cfd.png
    CFD chart title: Cumulative Flow Diagram

    Histogram data: histogram.csv
    
    Throughput frequency: 1D
    Throughput window: 3
    Throughput data: throughput.csv
    Throughput chart: throughput.png
    Throughput chart title: Throughput trend

    Burnup window: 30
    Burnup chart: burnup.png
    Burnup chart title: Burn-up

    Burnup forecast window: 30
    Burnup forecast chart: burnup-forecast.png
    Burnup forecast chart title: Burn-up forecast
    Burnup forecast chart target: 100
    Burnup forecast chart deadline: 2018-06-01
    Burnup forecast chart deadline confidence: .85
    Burnup forecast chart trials: 50
    Burnup forecast chart throughput window: 30
    Burnup forecast chart throughput window end: 2018-03-01

    WIP frequency: 3D
    WIP window: 3
    WIP chart: wip.png
    WIP chart title: Work in Progress

    Ageing WIP chart: ageing-wip.png
    Ageing WIP chart title: Ageing WIP

    Net flow frequency: 5D
    Net flow window: 3
    Net flow chart: net-flow.png
    Net flow chart title: Net flow

    Impediments data: impediments.csv
    Impediments window: 3
    Impediments chart: impediments.png
    Impediments chart title: Impediments
    Impediments days chart: impediments-days.png
    Impediments days chart title: Total impeded days
    Impediments status chart: impediments-status.png
    Impediments status chart title: Impediments by status
    Impediments status days chart: impediments-status-days.png
    Impediments status days chart title: Total impeded days by status

    Defects query: issueType = Bug
    Defects window: 3
    Defects priority field: Priority
    Defects priority values:
        - Low
        - Medium
        - High
    Defects type field: Type
    Defects type values:
        - Config
        - Data
        - Code
    Defects environment field: Environment
    Defects environment values:
        - SIT
        - UAT
        - PROD
    Defects by priority chart: defects-by-priority.png
    Defects by priority chart title: Defects by priority
    Defects by type chart: defects-by-type.png
    Defects by type chart title: Defects by type
    Defects by environment chart: defects-by-environment.png
    Defects by environment chart title: Defects by environment
    
    Debt query: issueType = "Tech debt"
    Debt window: 3
    Debt priority field: Priority
    Debt priority values:
        - Low
        - Medium
        - High
    Debt chart: tech-debt.png
    Debt chart title: Technical debt
    Debt age chart: tech-debt-age.png
    Debt age chart title: Technical debt age
    Debt age chart bins:
        - 10
        - 20
        - 30

    Waste query: issueType = Story AND resolution IN (Withdrawn, Invalid)
    Waste window: 3
    Waste frequency: 2W-WED
    Waste chart: waste.png
    Waste chart title: Waste

    Progress report: progress.html
    Progress report title: Test progress report
    Progress report epic deadline field: Due date
    Progress report epic team field: Team
    Progress report epic min stories field: Min stories
    Progress report epic max stories field: Max stories
    Progress report epic query template: project = ABC AND type = Epic AND Outcome = {outcome}
    Progress report story query template: project = ABC AND type = Story AND "Epic link" = {epic}
    Progress report teams:
        - Name: Team one
          Min throughput: 5
          Max throughput: 10
        - Name: Team two
          WIP: 2
          Throughput samples: project = ABC AND type = Story AND team = "Team two" AND resolution = "Done"
          Throughput samples window: 6
    Progress report outcomes:
        - Name: Outcome one
          Key: O1
          Deadline: 2019-06-01
        - Name: Outcome two
          Epic query: project = ABS and type = Feature
    Progress report outcome deadline field: Due date
    Progress report outcome query: project = ABC AND type = Outcome AND resolution IS EMPTY
""")

    assert options['connection'] == {
        'domain': 'https://foo.com',
        'jira_client_options': {},
        'password': 'apassword',
        'username': 'user1',
        'http_proxy': 'https://proxy1.local',
        'https_proxy': 'https://proxy2.local',
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

        'cycle_time_data': ['cycletime.csv'],
        
        'ageing_wip_chart': 'ageing-wip.png',
        'ageing_wip_chart_title': 'Ageing WIP',
        
        'burnup_window': 30,
        'burnup_chart': 'burnup.png',
        'burnup_chart_title': 'Burn-up',
        
        'burnup_forecast_window': 30,
        'burnup_forecast_chart': 'burnup-forecast.png',
        'burnup_forecast_chart_deadline': datetime.date(2018, 6, 1),
        'burnup_forecast_chart_deadline_confidence': 0.85,
        'burnup_forecast_chart_target': 100,
        'burnup_forecast_chart_throughput_window': 30,
        'burnup_forecast_chart_throughput_window_end': datetime.date(2018, 3, 1),
        'burnup_forecast_chart_title': 'Burn-up forecast',
        'burnup_forecast_chart_trials': 50,
        
        'cfd_window': 30,
        'cfd_chart': 'cfd.png',
        'cfd_chart_title': 'Cumulative Flow Diagram',
        'cfd_data': ['cfd.csv'],
        
        'histogram_window': 30,
        'histogram_chart': 'histogram.png',
        'histogram_chart_title': 'Cycle time histogram',
        'histogram_data': ['histogram.csv'],
        
        'net_flow_frequency': '5D',
        'net_flow_window': 3,
        'net_flow_chart': 'net-flow.png',
        'net_flow_chart_title': 'Net flow',
        
        'percentiles_data': ['percentiles.csv'],
        
        'scatterplot_window': 30,
        'scatterplot_chart': 'scatterplot.png',
        'scatterplot_chart_title': 'Cycle time scatter plot',
        'scatterplot_data': ['scatterplot.csv'],
        
        'throughput_frequency': '1D',
        'throughput_window': 3,
        'throughput_chart': 'throughput.png',
        'throughput_chart_title': 'Throughput trend',
        'throughput_data': ['throughput.csv'],
        
        'wip_frequency': '3D',
        'wip_window': 3,
        'wip_chart': 'wip.png',
        'wip_chart_title': 'Work in Progress',

        'impediments_data': ['impediments.csv'],
        'impediments_window': 3,
        'impediments_chart': 'impediments.png',
        'impediments_chart_title': 'Impediments',
        'impediments_days_chart': 'impediments-days.png',
        'impediments_days_chart_title': 'Total impeded days',
        'impediments_status_chart': 'impediments-status.png',
        'impediments_status_chart_title': 'Impediments by status',
        'impediments_status_days_chart': 'impediments-status-days.png',
        'impediments_status_days_chart_title': 'Total impeded days by status',

        'defects_query': 'issueType = Bug',
        'defects_window': 3,
        'defects_priority_field': 'Priority',
        'defects_priority_values': ['Low', 'Medium', 'High'],
        'defects_type_field': 'Type',
        'defects_type_values': ['Config', 'Data', 'Code'],
        'defects_environment_field': 'Environment',
        'defects_environment_values': ['SIT', 'UAT', 'PROD'],

        'defects_by_priority_chart': 'defects-by-priority.png',
        'defects_by_priority_chart_title': 'Defects by priority',
        'defects_by_type_chart': 'defects-by-type.png',
        'defects_by_type_chart_title': 'Defects by type',
        'defects_by_environment_chart': 'defects-by-environment.png',
        'defects_by_environment_chart_title': 'Defects by environment',
        
        'debt_query': 'issueType = "Tech debt"',
        'debt_window': 3,
        'debt_priority_field': 'Priority',
        'debt_priority_values': ['Low', 'Medium', 'High'],
        'debt_chart': 'tech-debt.png',
        'debt_chart_title': 'Technical debt',
        'debt_age_chart': 'tech-debt-age.png',
        'debt_age_chart_title': 'Technical debt age',
        'debt_age_chart_bins': [10, 20, 30],

        'waste_query': 'issueType = Story AND resolution IN (Withdrawn, Invalid)',
        'waste_window': 3,
        'waste_frequency': '2W-WED',
        'waste_chart': 'waste.png',
        'waste_chart_title': 'Waste',

        'progress_report': 'progress.html',
        'progress_report_title': 'Test progress report',
        'progress_report_epic_query_template': 'project = ABC AND type = Epic AND Outcome = {outcome}',
        'progress_report_story_query_template': 'project = ABC AND type = Story AND "Epic link" = {epic}',
        'progress_report_epic_deadline_field': 'Due date',
        'progress_report_epic_min_stories_field': 'Min stories',
        'progress_report_epic_max_stories_field': 'Max stories',
        'progress_report_epic_team_field': 'Team',
        'progress_report_teams': [
            {'name': 'Team one', 'max_throughput': 10, 'min_throughput': 5, 'throughput_samples': None, 'throughput_samples_window': None, 'wip': 1},
            {'name': 'Team two', 'max_throughput': None, 'min_throughput': None, 'throughput_samples': 'project = ABC AND type = Story AND team = "Team two" AND resolution = "Done"', 'wip': 2, 'throughput_samples_window': 6}
        ],
        'progress_report_outcomes': [
            {'key': 'O1', 'name': 'Outcome one', 'deadline': datetime.date(2019, 6, 1), 'epic_query': None},
            {'key': None, 'name': 'Outcome two', 'deadline': None, 'epic_query': "project = ABS and type = Feature"}
        ],
        'progress_report_outcome_deadline_field': 'Due date',
        'progress_report_outcome_query': 'project = ABC AND type = Outcome AND resolution IS EMPTY',
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

    assert options['settings']['cycle_time_data'] == ['cycletime.csv']
    assert options['settings']['ageing_wip_chart'] == 'ageing-wip.png'
    assert options['settings']['burnup_chart'] == 'burnup.png'
    assert options['settings']['burnup_forecast_chart'] == 'burnup-forecast.png'
    assert options['settings']['cfd_chart'] == 'cfd.png'
    assert options['settings']['histogram_chart'] == 'histogram.png'
    assert options['settings']['histogram_data'] == ['histogram.csv']
    assert options['settings']['net_flow_chart'] == 'net-flow.png'
    assert options['settings']['percentiles_data'] == ['percentiles.csv']
    assert options['settings']['scatterplot_chart'] == 'scatterplot.png'
    assert options['settings']['scatterplot_data'] == ['scatterplot.csv']
    assert options['settings']['throughput_chart'] == 'throughput.png'
    assert options['settings']['throughput_data'] == ['throughput.csv']
    assert options['settings']['wip_chart'] == 'wip.png'


def test_config_to_options_extends():

    with tempfile.NamedTemporaryFile() as fp:

        # Base file
        fp.write(b"""\
Connection:
    Domain: https://foo.com

Workflow:
    Backlog: Backlog
    In progress: Build
    Done: Done

Attributes:
    Release: Fix version/s
    Team: Assigned team

Output:
    Quantiles:
        - 0.1
        - 0.2

    Backlog column: Backlog
    Committed column: Committed
    Final column: Test
    Done column: Done
""")

        fp.seek(0)

        # Extend the file

        options = config_to_options("""
Extends: %s

Connection:
    Domain: https://bar.com

Query: (filter=123)

Attributes:
    Release: Release number
    Priority: Severity

Output:

    Quantiles:
        - 0.5
        - 0.7

    Cycle time data: cycletime.csv
""" % fp.name, cwd=os.path.abspath(fp.name))

        # overridden
        assert options['connection']['domain'] == 'https://bar.com'
        
        # from extended base
        assert options['settings']['backlog_column'] == 'Backlog'
        assert options['settings']['committed_column'] == 'Committed'
        assert options['settings']['final_column'] == 'Test'
        assert options['settings']['done_column'] == 'Done'

        # from extending file
        assert options['settings']['cycle_time_data'] == ['cycletime.csv']
        
        # overridden
        assert options['settings']['quantiles'] == [0.5, 0.7]

        # merged
        assert options['settings']['attributes'] == {
            'Release': 'Release number',
            'Priority': 'Severity',
            'Team': 'Assigned team'
        }

def test_config_to_options_extends_blocked_if_no_explicit_working_directory():

    with tempfile.NamedTemporaryFile() as fp:

        # Base file
        fp.write(b"""\
Connection:
    Domain: https://foo.com

Workflow:
    Backlog: Backlog
    In progress: Build
    Done: Done

Output:
    Quantiles:
        - 0.1
        - 0.2

    Backlog column: Backlog
    Committed column: Committed
    Final column: Test
    Done column: Done
""")

        fp.seek(0)

        # Extend the file

        try:
            config_to_options("""
Extends: %s

Connection:
    Domain: https://bar.com

Query: (filter=123)

Output:

    Quantiles:
        - 0.5
        - 0.7

    Cycle time data: cycletime.csv
""" % fp.name, cwd=None)

        except ConfigError:
            assert True
        else:
            assert False
