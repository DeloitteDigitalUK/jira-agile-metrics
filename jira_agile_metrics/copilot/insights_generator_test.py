"""
Unit tests for AI insights generator with offline mocks.
"""

import json
from unittest.mock import mock_open, patch

from .insights_generator import InsightsGenerator
from .providers import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, mock_response="Mock AI insight"):
        self.mock_response = mock_response
        self.last_prompt = None
        self.last_context = None

    def generate_insights(self, prompt: str, context: dict, dry_run: bool = False) -> str:
        self.last_prompt = prompt
        self.last_context = context
        return self.mock_response

    def validate_config(self) -> bool:
        return True


class TestInsightsGenerator:
    """Test insights generator with mocked dependencies."""

    def test_init(self):
        ai_config = {"provider": "openai", "model": "gpt-4o"}

        with patch("jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider") as mock_factory:
            mock_provider = MockLLMProvider()
            mock_factory.return_value = mock_provider

            generator = InsightsGenerator(ai_config)
            assert generator.config == ai_config
            assert generator.llm == mock_provider

    def test_generate_daily_insights_success(self):
        # Create flow-focused test context data
        test_context = {
            "metadata": {
                "generated_at": "2025-08-29T10:00:00Z",
                "workflow_stages": [
                    "To Do",
                    "In Progress",
                    "Code Review",
                    "Done",
                ],
                "committed_column": "In Progress",
                "done_column": "Done",
            },
            "flow_health": {
                "avg_cycle_time": 8.2,
                "median_cycle_time": 7.0,
                "predictability_ratio": 1.5,
                "total_completed_items": 15,
            },
            "ageing_wip_analysis": {
                "total_wip_items": 12,
                "stuck_items_count": 2,
                "stuck_items": [
                    {
                        "key": "PROJ-123",
                        "summary": "Test issue",
                        "age_days": 15,
                    }
                ],
            },
            "throughput_trends": {
                "recent_avg_throughput": 2.1,
                "trend_direction": "declining",
                "throughput_volatility": 1.2,
            },
            "actionable_items": [
                {
                    "key": "PROJ-123",
                    "summary": "Test issue",
                    "age_days": 15,
                    "reason": "ageing_outlier",
                    "priority": "high",
                }
            ],
        }

        mock_ai_response = """## Flow Health Assessment
Current flow shows declining throughput with 2 stuck items requiring attention.

## Priority Actions
1. **Address Stuck Items**: PROJ-123 has been in progress for 15 days
   → Action: Review blockers and reassign if needed
2. **Improve Throughput**: Recent decline in delivery rate
   → Action: Analyze bottlenecks in Code Review stage"""

        ai_config = {"provider": "test"}
        mock_provider = MockLLMProvider(mock_ai_response)

        with patch(
            "jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider",
            return_value=mock_provider,
        ):
            generator = InsightsGenerator(ai_config)

            # Mock file operations
            with patch("builtins.open", mock_open(read_data=json.dumps(test_context))):
                result = generator.generate_daily_insights("test-context.json", "test-output.md")

            # Verify the result contains expected flow-focused elements
            assert "Daily Flow Metrics Briefing" in result
            assert "Flow Overview" in result
            assert "PROJ-123" in result
            assert "Flow Health Assessment" in result

            # Verify the prompt was built correctly with flow data
            assert mock_provider.last_prompt is not None
            assert "layered analysis" in mock_provider.last_prompt.lower()
            assert "PROJ-123" in mock_provider.last_prompt

    def test_generate_daily_insights_file_not_found(self):
        ai_config = {"provider": "test"}
        mock_provider = MockLLMProvider()

        with patch(
            "jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider",
            return_value=mock_provider,
        ):
            generator = InsightsGenerator(ai_config)

            result = generator.generate_daily_insights("nonexistent-file.json")

            assert "Error: Context file not found" in result

    def test_generate_chat_response_success(self):
        test_context = {
            "metadata": {
                "generated_at": "2025-08-29T10:00:00Z",
                "team_name": "Test Team",
            },
            "specific_issues": [
                {
                    "ticket_id": "PROJ-456",
                    "title": "Another test issue",
                    "status": "Done",
                }
            ],
        }

        mock_ai_response = "Based on the data, PROJ-456 is completed and in Done status."

        ai_config = {"provider": "test"}
        mock_provider = MockLLMProvider(mock_ai_response)

        with patch(
            "jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider",
            return_value=mock_provider,
        ):
            generator = InsightsGenerator(ai_config)

            with patch("builtins.open", mock_open(read_data=json.dumps(test_context))):
                result = generator.generate_chat_response("What is the status of PROJ-456?", "test-context.json")

            assert result["answer"] == mock_ai_response
            assert result["context_timestamp"] == "2025-08-29T10:00:00Z"
            assert "PROJ-456" in result["sources"]

    def test_calculate_sprint_day(self):
        ai_config = {"provider": "test"}
        mock_provider = MockLLMProvider()

        with patch(
            "jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider",
            return_value=mock_provider,
        ):
            generator = InsightsGenerator(ai_config)

            # Test with valid sprint start date
            sprint_info = {"sprint_start": "2025-08-25T00:00:00Z"}

            # Mock datetime.now() to return a fixed date (timezone-aware)
            with patch("jira_agile_metrics.copilot.insights_generator.datetime") as mock_datetime:
                from datetime import datetime as real_datetime
                from datetime import timezone

                # Set up the mock to behave like the real datetime class
                mock_datetime.now.return_value = real_datetime(2025, 8, 29, 10, 0, 0, tzinfo=timezone.utc)
                mock_datetime.fromisoformat = real_datetime.fromisoformat

                day = generator._calculate_sprint_day(sprint_info)
                # Start: 2025-08-25, Current: 2025-08-29 = 4 days difference + 1 = day 5
                assert day == 5

    def test_format_metrics_for_prompt(self):
        ai_config = {"provider": "test"}
        mock_provider = MockLLMProvider()

        with patch(
            "jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider",
            return_value=mock_provider,
        ):
            generator = InsightsGenerator(ai_config)

            metrics = {
                "cycle_time": {"current_average": 8.5},
                "throughput": {"current_week": 2.3},
                "wip": {
                    "current_count": 11,
                    "limit": 10,
                    "status": "over_limit",
                },
            }

            result = generator._format_metrics_for_prompt(metrics)

            assert "Cycle Time: 8.5 days average" in result
            assert "Throughput: 2.3 items/week" in result
            assert "WIP: 11/10 (over_limit)" in result

    def test_format_issues_for_prompt(self):
        ai_config = {"provider": "test"}
        mock_provider = MockLLMProvider()

        with patch(
            "jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider",
            return_value=mock_provider,
        ):
            generator = InsightsGenerator(ai_config)

            issues = [
                {
                    "ticket_id": "PROJ-123",
                    "title": "Long title that should be truncated because it exceeds sixty characters",
                    "status": "In Progress",
                    "assignee": "Alice",
                    "days_in_current_status": 3,
                    "blocked": False,
                },
                {
                    "ticket_id": "PROJ-456",
                    "title": "Blocked issue",
                    "status": "Code Review",
                    "assignee": "Bob",
                    "blocked": True,
                },
            ]

            result = generator._format_issues_for_prompt(issues)

            assert "PROJ-123" in result
            assert "PROJ-456" in result
            assert "[BLOCKED]" in result
            assert "Alice" in result
            assert "Bob" in result
            assert "(3 days)" in result

    def test_extract_ticket_references(self):
        ai_config = {"provider": "test"}
        mock_provider = MockLLMProvider()

        with patch(
            "jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider",
            return_value=mock_provider,
        ):
            generator = InsightsGenerator(ai_config)

            text = """
            Review PROJ-123 and ABC-456 for bottlenecks.
            Also check TEAM-789 but ignore invalid-123 and PROJ-.
            """

            references = generator._extract_ticket_references(text)

            assert "PROJ-123" in references
            assert "ABC-456" in references
            assert "TEAM-789" in references
            assert "invalid-123" not in references
            assert "PROJ-" not in references
            assert len(references) == 3

    def test_format_daily_insights_structure(self):
        ai_config = {"provider": "test"}
        mock_provider = MockLLMProvider()

        with patch(
            "jira_agile_metrics.copilot.insights_generator.LLMFactory.create_provider",
            return_value=mock_provider,
        ):
            generator = InsightsGenerator(ai_config)

            context = {
                "metadata": {
                    "workflow_stages": ["To Do", "In Progress", "Done"],
                    "committed_column": "In Progress",
                    "done_column": "Done",
                    "generated_at": "2025-08-29T10:00:00Z",
                },
                "flow_health": {
                    "avg_cycle_time": 8.5,
                    "predictability_ratio": 1.3,
                },
                "ageing_wip_analysis": {"total_wip_items": 5},
                "throughput_trends": {"trend_direction": "stable"},
            }

            ai_insights = "Test AI insights content"

            result = generator._format_daily_insights(ai_insights, context)

            # Verify flow-focused structure
            assert "# Daily Flow Metrics Briefing" in result
            assert "Flow Overview" in result
            assert "To Do → In Progress → Done" in result
            assert "Current WIP**: 5 items" in result
            assert "Avg Cycle Time**: 8.5 days" in result
            assert "Test AI insights content" in result
            assert "AI Flow Metrics Copilot" in result
