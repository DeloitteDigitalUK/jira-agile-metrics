"""
Unit tests for AI insights generator with offline mocks.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from .insights_generator import InsightsGenerator
from .providers import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, mock_response="Mock AI insight"):
        self.mock_response = mock_response
        self.last_prompt = None
        self.last_context = None
    
    def generate_insights(self, prompt: str, context: dict) -> str:
        self.last_prompt = prompt
        self.last_context = context
        return self.mock_response
    
    def validate_config(self) -> bool:
        return True


class TestInsightsGenerator:
    """Test insights generator with mocked dependencies."""
    
    def test_init(self):
        ai_config = {'provider': 'openai', 'model': 'gpt-4o'}
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider') as mock_factory:
            mock_provider = MockLLMProvider()
            mock_factory.return_value = mock_provider
            
            generator = InsightsGenerator(ai_config)
            assert generator.config == ai_config
            assert generator.llm == mock_provider
    
    def test_generate_daily_insights_success(self):
        # Create test context data
        test_context = {
            "metadata": {
                "generated_at": "2025-08-29T10:00:00Z",
                "team_name": "Test Team",
                "sprint_info": {
                    "current_sprint": "Sprint 23",
                    "sprint_start": "2025-08-21",
                    "days_remaining": 5
                },
                "total_issues_analyzed": 15
            },
            "metrics_summary": {
                "cycle_time": {
                    "current_average": 8.2,
                    "previous_average": 6.1
                },
                "throughput": {
                    "current_week": 2.1,
                    "previous_week": 2.5
                },
                "wip": {
                    "current_count": 12,
                    "limit": 10,
                    "status": "over_limit"
                }
            },
            "specific_issues": [
                {
                    "ticket_id": "PROJ-123",
                    "title": "Test issue",
                    "status": "In Review",
                    "assignee": "John Doe",
                    "days_in_current_status": 6,
                    "blocked": False
                }
            ],
            "patterns_detected": [
                {
                    "pattern_type": "review_bottleneck",
                    "description": "Code reviews taking longer than usual",
                    "confidence": 0.85
                }
            ]
        }
        
        mock_ai_response = """## Top Priorities
1. **Review Bottleneck**: PROJ-123 stuck in review for 6 days
   → Action: Assign additional reviewer or pair review
2. **WIP Overload**: Team has 12 items vs 10 limit
   → Action: Complete 2 items before starting new work"""
        
        ai_config = {'provider': 'test'}
        mock_provider = MockLLMProvider(mock_ai_response)
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider', return_value=mock_provider):
            generator = InsightsGenerator(ai_config)
            
            # Mock file operations
            with patch('builtins.open', mock_open(read_data=json.dumps(test_context))):
                result = generator.generate_daily_insights('test-context.json', 'test-output.md')
            
            # Verify the result contains expected elements
            assert "Daily Agile Team Briefing" in result
            assert "Test Team" in result
            assert "Sprint 23" in result
            assert "PROJ-123" in result
            assert "Review Bottleneck" in result
            
            # Verify the prompt was built correctly
            assert mock_provider.last_prompt is not None
            assert "Test Team" in mock_provider.last_prompt
            assert "Sprint 23" in mock_provider.last_prompt
            assert "PROJ-123" in mock_provider.last_prompt
    
    def test_generate_daily_insights_file_not_found(self):
        ai_config = {'provider': 'test'}
        mock_provider = MockLLMProvider()
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider', return_value=mock_provider):
            generator = InsightsGenerator(ai_config)
            
            result = generator.generate_daily_insights('nonexistent-file.json')
            
            assert "Error: Context file not found" in result
    
    def test_generate_chat_response_success(self):
        test_context = {
            "metadata": {
                "generated_at": "2025-08-29T10:00:00Z",
                "team_name": "Test Team"
            },
            "specific_issues": [
                {
                    "ticket_id": "PROJ-456",
                    "title": "Another test issue",
                    "status": "Done"
                }
            ]
        }
        
        mock_ai_response = "Based on the data, PROJ-456 is completed and in Done status."
        
        ai_config = {'provider': 'test'}
        mock_provider = MockLLMProvider(mock_ai_response)
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider', return_value=mock_provider):
            generator = InsightsGenerator(ai_config)
            
            with patch('builtins.open', mock_open(read_data=json.dumps(test_context))):
                result = generator.generate_chat_response("What is the status of PROJ-456?", 'test-context.json')
            
            assert result['answer'] == mock_ai_response
            assert result['context_timestamp'] == "2025-08-29T10:00:00Z"
            assert 'PROJ-456' in result['sources']
    
    def test_calculate_sprint_day(self):
        ai_config = {'provider': 'test'}
        mock_provider = MockLLMProvider()
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider', return_value=mock_provider):
            generator = InsightsGenerator(ai_config)
            
            # Test with valid sprint start date
            sprint_info = {"sprint_start": "2025-08-25T00:00:00Z"}
            
            # Mock datetime.now() to return a fixed date (timezone-aware)
            with patch('jira_agile_metrics.copilot.insights_generator.datetime') as mock_datetime:
                from datetime import datetime as real_datetime, timezone
                
                # Set up the mock to behave like the real datetime class
                mock_datetime.now.return_value = real_datetime(2025, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
                mock_datetime.fromisoformat = real_datetime.fromisoformat
                
                day = generator._calculate_sprint_day(sprint_info)
                # Start: 2025-08-25, Current: 2025-08-29 = 4 days difference + 1 = day 5
                assert day == 5
    
    def test_format_metrics_for_prompt(self):
        ai_config = {'provider': 'test'}
        mock_provider = MockLLMProvider()
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider', return_value=mock_provider):
            generator = InsightsGenerator(ai_config)
            
            metrics = {
                "cycle_time": {
                    "current_average": 8.5
                },
                "throughput": {
                    "current_week": 2.3
                },
                "wip": {
                    "current_count": 11,
                    "limit": 10,
                    "status": "over_limit"
                }
            }
            
            result = generator._format_metrics_for_prompt(metrics)
            
            assert "Cycle Time: 8.5 days average" in result
            assert "Throughput: 2.3 items/week" in result
            assert "WIP: 11/10 (over_limit)" in result
    
    def test_format_issues_for_prompt(self):
        ai_config = {'provider': 'test'}
        mock_provider = MockLLMProvider()
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider', return_value=mock_provider):
            generator = InsightsGenerator(ai_config)
            
            issues = [
                {
                    "ticket_id": "PROJ-123",
                    "title": "Long title that should be truncated because it exceeds sixty characters",
                    "status": "In Progress",
                    "assignee": "Alice",
                    "days_in_current_status": 3,
                    "blocked": False
                },
                {
                    "ticket_id": "PROJ-456",
                    "title": "Blocked issue",
                    "status": "Code Review",
                    "assignee": "Bob",
                    "blocked": True
                }
            ]
            
            result = generator._format_issues_for_prompt(issues)
            
            assert "PROJ-123" in result
            assert "PROJ-456" in result
            assert "[BLOCKED]" in result
            assert "Alice" in result
            assert "Bob" in result
            assert "(3 days)" in result
    
    def test_extract_ticket_references(self):
        ai_config = {'provider': 'test'}
        mock_provider = MockLLMProvider()
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider', return_value=mock_provider):
            generator = InsightsGenerator(ai_config)
            
            text = """
            Review PROJ-123 and ABC-456 for bottlenecks.
            Also check TEAM-789 but ignore invalid-123 and PROJ-.
            """
            
            references = generator._extract_ticket_references(text)
            
            assert 'PROJ-123' in references
            assert 'ABC-456' in references
            assert 'TEAM-789' in references
            assert 'invalid-123' not in references
            assert 'PROJ-' not in references
            assert len(references) == 3
    
    def test_format_daily_insights_structure(self):
        ai_config = {'provider': 'test'}
        mock_provider = MockLLMProvider()
        
        with patch('jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider', return_value=mock_provider):
            generator = InsightsGenerator(ai_config)
            
            context = {
                "metadata": {
                    "team_name": "Test Team",
                    "sprint_info": {"current_sprint": "Sprint 23"},
                    "jira_query": "project = TEST",
                    "total_issues_analyzed": 20,
                    "analysis_period_days": 14,
                    "generated_at": "2025-08-29T10:00:00Z"
                }
            }
            
            ai_insights = "Test AI insights content"
            
            result = generator._format_daily_insights(ai_insights, context)
            
            # Verify structure
            assert "# Daily Agile Team Briefing" in result
            assert "**Team:** Test Team" in result
            assert "**Sprint:** Sprint 23" in result
            assert "Test AI insights content" in result
            assert "**Verification Notes:**" in result
            assert "20 issues from the last 14 days" in result
            assert "**Next Steps:**" in result
