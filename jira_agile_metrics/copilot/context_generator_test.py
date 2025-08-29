"""
Unit tests for AI context generator.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta

from ..conftest import (
    FauxJIRA as JIRA,
    FauxIssue as Issue,
    FauxChange as Change,
    FauxFieldValue as Value,
)
from ..querymanager import QueryManager
from .context_generator import AIContextGenerator


@pytest.fixture
def mock_query_manager():
    """Create a mock query manager with test data."""
    jira = JIRA(
        fields=[
            {'id': 'customfield_001', 'name': 'Team', 'custom': True, 'type': 'text'},
            {'id': 'customfield_002', 'name': 'Story Points', 'custom': True, 'type': 'number'},
        ],
        issues=[
            Issue(
                "PROJ-123",
                summary="Test story in progress",
                issuetype=Value("Story", "story"),
                status=Value("In Progress", "in-progress"),
                resolution=None,
                resolutiondate=None,
                created="2025-08-15 09:00:00",
                customfield_001="Alpha Team",
                customfield_002=Value(None, 5),
                assignee=Value("Alice Smith", "alice"),
                changes=[
                    Change("2025-08-20 10:00:00", [("status", "To Do", "In Progress")])
                ],
            ),
            Issue(
                "PROJ-456",
                summary="Blocked issue needs review",
                issuetype=Value("Bug", "bug"),
                status=Value("Code Review", "code-review"),
                resolution=None,
                resolutiondate=None,
                created="2025-08-10 14:30:00",
                customfield_001="Alpha Team",
                customfield_002=Value(None, 3),
                assignee=Value("Bob Jones", "bob"),
                flagged=Value("Impediment", "impediment"),
                changes=[
                    Change("2025-08-12 11:00:00", [("status", "To Do", "In Progress")]),
                    Change("2025-08-25 15:00:00", [("status", "In Progress", "Code Review")]),
                    Change("2025-08-26 09:00:00", [("Flagged", None, "Impediment")])
                ],
            ),
            Issue(
                "PROJ-789",
                summary="Completed story",
                issuetype=Value("Story", "story"),
                status=Value("Done", "done"),
                resolution=Value("Fixed", "fixed"),
                resolutiondate="2025-08-28 16:00:00",
                created="2025-08-18 10:00:00",
                customfield_001="Alpha Team",
                customfield_002=Value(None, 8),
                assignee=Value("Charlie Brown", "charlie"),
                changes=[
                    Change("2025-08-19 09:00:00", [("status", "To Do", "In Progress")]),
                    Change("2025-08-27 14:00:00", [("status", "In Progress", "Code Review")]),
                    Change("2025-08-28 16:00:00", [("status", "Code Review", "Done")])
                ],
            )
        ]
    )
    
    return QueryManager(jira, {'query': 'project = PROJ'})


@pytest.fixture
def test_settings():
    """Test settings configuration."""
    return {
        'team_name': 'Alpha Team',
        'sprint_info': {
            'current_sprint': 'Sprint 23',
            'sprint_start': '2025-08-21T00:00:00Z',
            'sprint_end': '2025-09-03T23:59:59Z'
        },
        'jira_query': 'project = PROJ AND team = "Alpha Team"',
        'analysis_period_days': 14,
        'workflow': {
            'todo': ['To Do', 'Backlog'],
            'in_progress': ['In Progress', 'Code Review'],
            'done': ['Done', 'Closed']
        }
    }


class TestAIContextGenerator:
    """Test context generator functionality."""
    
    def test_init(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        assert generator.query_manager == mock_query_manager
        assert generator.settings == test_settings
        assert generator.context_data == {}
    
    def test_run_generates_context(self, mock_query_manager, test_settings):
        # Mock calculator results
        mock_results = {
            'CycleTimeCalculator': {
                'cycle_time_data': [
                    {'ticket_id': 'PROJ-789', 'cycle_time': 10.0},
                    {'ticket_id': 'PROJ-456', 'cycle_time': None}  # Still in progress
                ]
            },
            'ThroughputCalculator': {
                'weekly_throughput': [2.5, 2.1, 1.8]
            }
        }
        
        generator = AIContextGenerator(mock_query_manager, test_settings, mock_results)
        
        # Mock the file writing to avoid creating actual files
        with patch('builtins.open', mock_open()) as mock_file:
            result = generator.run()
        
        # Verify structure
        assert 'metadata' in result
        assert 'metrics_summary' in result
        assert 'specific_issues' in result
        assert 'patterns_detected' in result
        assert 'workflow_analysis' in result
        
        # Verify metadata content
        metadata = result['metadata']
        assert metadata['team_name'] == 'Alpha Team'
        assert metadata['analysis_period_days'] == 14
        assert metadata['jira_query'] == 'project = PROJ AND team = "Alpha Team"'
        assert metadata['total_issues_analyzed'] == 3
        
        # Verify issues are included
        issues = result['specific_issues']
        assert len(issues) == 3
        
        # Find specific issues
        proj_123 = next(issue for issue in issues if issue['ticket_id'] == 'PROJ-123')
        proj_456 = next(issue for issue in issues if issue['ticket_id'] == 'PROJ-456')
        proj_789 = next(issue for issue in issues if issue['ticket_id'] == 'PROJ-789')
        
        assert proj_123['status'] == 'In Progress'
        assert proj_123['assignee'] == 'Alice Smith'
        assert proj_456['blocked'] is True
        assert proj_789['status'] == 'Done'
    
    def test_analyze_cycle_time_metrics(self, mock_query_manager, test_settings):
        mock_cycle_time_data = [
            {'ticket_id': 'PROJ-789', 'cycle_time': 10.0},
            {'ticket_id': 'PROJ-456', 'cycle_time': None},  # In progress
            {'ticket_id': 'PROJ-111', 'cycle_time': 5.0},   # Historical
            {'ticket_id': 'PROJ-222', 'cycle_time': 15.0}   # Historical
        ]
        
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        result = generator._analyze_cycle_time_metrics(mock_cycle_time_data)
        
        assert 'current_average' in result
        assert 'previous_average' in result
        assert 'trend' in result
        
        # Should calculate average of completed items (10.0, 5.0, 15.0)
        assert result['current_average'] == 10.0  # Average of [10.0, 5.0, 15.0]
        assert result['completed_count'] == 3
    
    def test_analyze_throughput_metrics(self, mock_query_manager, test_settings):
        mock_throughput_data = [3.0, 2.5, 2.1, 1.8, 2.2]  # 5 weeks of data
        
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        result = generator._analyze_throughput_metrics(mock_throughput_data)
        
        assert 'current_week' in result
        assert 'previous_week' in result
        assert 'trend' in result
        
        assert result['current_week'] == 3.0
        assert result['previous_week'] == 2.5
        assert result['trend'] == 'improving'  # 3.0 > 2.5
    
    def test_analyze_wip_metrics(self, mock_query_manager, test_settings):
        # Mock WIP data - 2 items in progress
        mock_wip_data = {
            'current_wip': 2,
            'wip_by_status': {
                'In Progress': 1,
                'Code Review': 1
            }
        }
        
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        result = generator._analyze_wip_metrics(mock_wip_data, wip_limit=3)
        
        assert result['current_count'] == 2
        assert result['limit'] == 3
        assert result['status'] == 'within_limit'
        assert result['by_status']['In Progress'] == 1
        assert result['by_status']['Code Review'] == 1
    
    def test_detect_patterns_review_bottleneck(self, mock_query_manager, test_settings):
        # Create issues with long review times
        issues_data = [
            {
                'ticket_id': 'PROJ-456',
                'status': 'Code Review',
                'days_in_current_status': 5,  # Long time in review
                'blocked': True
            },
            {
                'ticket_id': 'PROJ-789',
                'status': 'Code Review',
                'days_in_current_status': 3,
                'blocked': False
            }
        ]
        
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        patterns = generator._detect_patterns(issues_data, {})
        
        # Should detect review bottleneck
        review_pattern = next((p for p in patterns if p['pattern_type'] == 'review_bottleneck'), None)
        assert review_pattern is not None
        assert review_pattern['confidence'] > 0.7
        assert 'Code Review' in review_pattern['description']
    
    def test_detect_patterns_blocked_items(self, mock_query_manager, test_settings):
        issues_data = [
            {
                'ticket_id': 'PROJ-456',
                'status': 'In Progress',
                'blocked': True
            },
            {
                'ticket_id': 'PROJ-123',
                'status': 'Code Review',
                'blocked': True
            }
        ]
        
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        patterns = generator._detect_patterns(issues_data, {})
        
        # Should detect blocked items pattern
        blocked_pattern = next((p for p in patterns if p['pattern_type'] == 'blocked_items'), None)
        assert blocked_pattern is not None
        assert '2 blocked items' in blocked_pattern['description']
    
    def test_calculate_days_in_status(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        # Mock issue with status change 3 days ago
        issue = Mock()
        issue.key = 'PROJ-123'
        issue.fields.status.name = 'In Progress'
        
        # Mock changelog with status change
        change = Mock()
        change.created = '2025-08-26T10:00:00.000+0000'  # 3 days ago from test date
        change_item = Mock()
        change_item.field = 'status'
        change_item.toString = 'In Progress'
        change.items = [change_item]
        
        issue.changelog.histories = [change]
        
        with patch('jira_agile_metrics.copilot.context_generator.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 8, 29, 10, 0, 0)
            mock_datetime.strptime.return_value = datetime(2025, 8, 26, 10, 0, 0)
            
            days = generator._calculate_days_in_status(issue)
            assert days == 3
    
    def test_is_blocked_issue(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        # Test blocked issue
        blocked_issue = Mock()
        blocked_issue.fields.flagged = Mock()
        blocked_issue.fields.flagged.value = 'Impediment'
        
        assert generator._is_blocked(blocked_issue) is True
        
        # Test non-blocked issue
        normal_issue = Mock()
        normal_issue.fields.flagged = None
        
        assert generator._is_blocked(normal_issue) is False
    
    def test_write_creates_json_file(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        # Set up test data
        test_context = {
            'metadata': {'team_name': 'Alpha Team'},
            'metrics_summary': {},
            'specific_issues': [],
            'patterns_detected': []
        }
        
        generator._results[generator.__class__] = test_context
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_settings['output_directory'] = temp_dir
            
            generator.write()
            
            # Verify file was created
            expected_file = os.path.join(temp_dir, 'ai_context.json')
            assert os.path.exists(expected_file)
            
            # Verify content
            with open(expected_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['metadata']['team_name'] == 'Alpha Team'
    
    def test_format_issue_data(self, mock_query_manager, test_settings):
        generator = AIContextGenerator(mock_query_manager, test_settings, {})
        
        # Mock issue
        issue = Mock()
        issue.key = 'PROJ-123'
        issue.fields.summary = 'Test issue summary'
        issue.fields.status.name = 'In Progress'
        issue.fields.assignee.displayName = 'Alice Smith'
        issue.fields.issuetype.name = 'Story'
        issue.fields.priority.name = 'High'
        issue.fields.flagged = None
        
        with patch.object(generator, '_calculate_days_in_status', return_value=5):
            with patch.object(generator, '_is_blocked', return_value=False):
                result = generator._format_issue_data(issue)
        
        assert result['ticket_id'] == 'PROJ-123'
        assert result['title'] == 'Test issue summary'
        assert result['status'] == 'In Progress'
        assert result['assignee'] == 'Alice Smith'
        assert result['issue_type'] == 'Story'
        assert result['priority'] == 'High'
        assert result['days_in_current_status'] == 5
        assert result['blocked'] is False
