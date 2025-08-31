"""
Unit tests for LLM providers with offline mocks.
"""

import pytest
from unittest.mock import Mock, patch
from .providers import (
    OpenAIProvider,
    AnthropicProvider,
    AzureOpenAIProvider,
    LLMFactory,
)


# Realistic JIRA metrics context data for testing
SAMPLE_CONTEXT = {
    "issues": [
        {
            "key": "PROJ-123",
            "summary": "Implement user authentication",
            "issue_type": "Story",
            "status": "Done",
            "cycle_time": 8.5,
            "blocked_days": 2.0,
            "impediments": ["Waiting for API spec"],
            "timestamps": {
                "Backlog": "2024-01-01T09:00:00Z",
                "In Progress": "2024-01-03T10:00:00Z",
                "Code Review": "2024-01-08T14:00:00Z",
                "Done": "2024-01-10T16:00:00Z",
            },
        },
        {
            "key": "PROJ-456",
            "summary": "Fix payment gateway bug",
            "issue_type": "Bug",
            "status": "In Progress",
            "cycle_time": None,
            "blocked_days": 0.0,
            "impediments": [],
            "timestamps": {
                "Backlog": "2024-01-05T09:00:00Z",
                "In Progress": "2024-01-08T11:00:00Z",
            },
        },
        {
            "key": "PROJ-789",
            "summary": "Database performance optimization",
            "issue_type": "Task",
            "status": "Code Review",
            "cycle_time": None,
            "blocked_days": 1.5,
            "impediments": ["DBA review pending"],
            "timestamps": {
                "Backlog": "2024-01-02T09:00:00Z",
                "In Progress": "2024-01-04T10:00:00Z",
                "Code Review": "2024-01-09T15:00:00Z",
            },
        },
    ],
    "metrics": {
        "avg_cycle_time": 8.5,
        "wip_count": 2,
        "throughput_last_week": 3,
        "blocked_items_count": 1,
        "total_blocked_days": 3.5,
    },
    "date_range": {"start": "2024-01-01", "end": "2024-01-10"},
}


class TestOpenAIProvider:
    """Test OpenAI provider with mocked API calls."""

    def test_init_with_config(self):
        config = {
            "model": "gpt-4o",
            "api_key_env": "TEST_OPENAI_KEY",
            "max_tokens": 1500,
            "temperature": 0.2,
        }

        with patch.dict("os.environ", {"TEST_OPENAI_KEY": "test-key-123"}):
            provider = OpenAIProvider(config)

        assert provider.model == "gpt-4o"
        assert provider.api_key == "test-key-123"
        assert provider.max_tokens == 1500
        assert provider.temperature == 0.2

    def test_validate_config_with_api_key(self):
        config = {"api_key_env": "TEST_OPENAI_KEY"}

        with patch.dict("os.environ", {"TEST_OPENAI_KEY": "test-key-123"}):
            provider = OpenAIProvider(config)
            assert provider.validate_config() is True

    def test_validate_config_without_api_key(self):
        config = {"api_key_env": "MISSING_KEY"}

        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAIProvider(config)
            assert provider.validate_config() is False

    @patch("jira_agile_metrics.copilot.providers.requests.post")
    def test_generate_insights_success(self, mock_post):
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test AI insight: Focus on reducing cycle time for PROJ-123."
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        config = {"api_key_env": "TEST_OPENAI_KEY", "model": "gpt-4o"}

        with patch.dict("os.environ", {"TEST_OPENAI_KEY": "test-key-123"}):
            provider = OpenAIProvider(config)
            result = provider.generate_insights(
                "Analyze team performance", SAMPLE_CONTEXT
            )

        assert (
            result
            == "Test AI insight: Focus on reducing cycle time for PROJ-123."
        )

        # Verify API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
        assert "Authorization" in call_args[1]["headers"]
        assert (
            call_args[1]["headers"]["Authorization"] == "Bearer test-key-123"
        )

        # Verify context data is included in the request
        payload = call_args[1]["json"]
        user_message = payload["messages"][1]["content"]
        assert "Context Data:" in user_message
        assert "PROJ-123" in user_message
        assert "PROJ-456" in user_message
        assert "avg_cycle_time" in user_message
        assert "Query: Analyze team performance" in user_message

    @patch("jira_agile_metrics.copilot.providers.requests.post")
    def test_generate_insights_api_error(self, mock_post):
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        config = {"api_key_env": "TEST_OPENAI_KEY"}

        with patch.dict("os.environ", {"TEST_OPENAI_KEY": "invalid-key"}):
            provider = OpenAIProvider(config)

            with pytest.raises(Exception) as exc_info:
                provider.generate_insights("Test prompt", SAMPLE_CONTEXT)

            assert "OpenAI API error (401)" in str(exc_info.value)

    def test_generate_insights_no_api_key(self):
        config = {"api_key_env": "MISSING_KEY"}

        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAIProvider(config)

            with pytest.raises(ValueError) as exc_info:
                provider.generate_insights("Test prompt", SAMPLE_CONTEXT)

            assert "OpenAI API key not found" in str(exc_info.value)

    @patch("jira_agile_metrics.copilot.providers.requests.post")
    def test_generate_insights_empty_context(self, mock_post):
        # Test handling of empty context
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response with no context"}}]
        }
        mock_post.return_value = mock_response

        config = {"api_key_env": "TEST_OPENAI_KEY"}

        with patch.dict("os.environ", {"TEST_OPENAI_KEY": "test-key-123"}):
            provider = OpenAIProvider(config)
            provider.generate_insights("Test prompt", {})

        # Verify empty context is handled gracefully
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        user_message = payload["messages"][1]["content"]
        assert "No context data provided" in user_message

    @patch("jira_agile_metrics.copilot.providers.requests.post")
    def test_generate_insights_dry_run(self, mock_post, capsys):
        # Config with dry_run enabled, no API key needed
        config = {"dry_run": True, "model": "gpt-4o"}

        # No API key in environment
        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAIProvider(config)
            result = provider.generate_insights(
                "Dry run test", SAMPLE_CONTEXT
            )

        # 1. Verify API was not called
        mock_post.assert_not_called()

        # 2. Verify the output was printed
        captured = capsys.readouterr()
        assert "--- PAYLOAD (OpenAI) ---" in captured.out
        assert '"model": "gpt-4o"' in captured.out
        assert "Dry run test" in captured.out
        assert "PROJ-123" in captured.out  # from SAMPLE_CONTEXT
        assert "--- END PAYLOAD ---" in captured.out

        # 3. Verify the return value
        assert "Dry run mode: OpenAI API not called" in result


class TestAnthropicProvider:
    """Test Anthropic provider with mocked API calls."""

    @patch("jira_agile_metrics.copilot.providers.requests.post")
    def test_generate_insights_success(self, mock_post):
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {
                    "text": "Anthropic AI insight: Review bottleneck detected in PROJ-456."
                }
            ]
        }
        mock_post.return_value = mock_response

        config = {
            "api_key_env": "TEST_ANTHROPIC_KEY",
            "model": "claude-3-5-sonnet-20241022",
        }

        with patch.dict("os.environ", {"TEST_ANTHROPIC_KEY": "test-key-456"}):
            provider = AnthropicProvider(config)
            result = provider.generate_insights(
                "Identify bottlenecks", SAMPLE_CONTEXT
            )

        assert (
            result
            == "Anthropic AI insight: Review bottleneck detected in PROJ-456."
        )

        # Verify API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.anthropic.com/v1/messages"
        assert "x-api-key" in call_args[1]["headers"]

        # Verify context data is included in the request
        payload = call_args[1]["json"]
        user_content = payload["messages"][0]["content"]
        assert "Context Data:" in user_content
        assert "PROJ-789" in user_content
        assert "blocked_days" in user_content
        assert "Query: Identify bottlenecks" in user_content

    @patch("jira_agile_metrics.copilot.providers.requests.post")
    def test_generate_insights_dry_run(self, mock_post, capsys):
        config = {"dry_run": True, "model": "claude-3-opus-20240229"}

        with patch.dict("os.environ", {}, clear=True):
            provider = AnthropicProvider(config)
            result = provider.generate_insights(
                "Dry run test", SAMPLE_CONTEXT
            )

        mock_post.assert_not_called()

        captured = capsys.readouterr()
        assert "--- PAYLOAD (Anthropic) ---" in captured.out
        assert '"model": "claude-3-opus-20240229"' in captured.out
        assert "Dry run test" in captured.out
        assert "--- END PAYLOAD ---" in captured.out

        assert "Dry run mode: Anthropic API not called" in result


class TestAzureOpenAIProvider:
    """Test Azure OpenAI provider with mocked API calls."""

    @patch("jira_agile_metrics.copilot.providers.requests.post")
    def test_generate_insights_success(self, mock_post):
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Azure AI insight: WIP limit exceeded, consider pausing new work."
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        config = {
            "api_key_env": "TEST_AZURE_KEY",
            "api_base": "https://test-resource.openai.azure.com",
            "api_version": "2024-02-15-preview",
            "model": "gpt-4-deployment",
        }

        with patch.dict("os.environ", {"TEST_AZURE_KEY": "test-azure-key"}):
            provider = AzureOpenAIProvider(config)
            result = provider.generate_insights(
                "Analyze WIP levels", SAMPLE_CONTEXT
            )

        assert (
            result
            == "Azure AI insight: WIP limit exceeded, consider pausing new work."
        )

        # Verify correct URL construction
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        expected_url = "https://test-resource.openai.azure.com/openai/deployments/gpt-4-deployment/chat/completions?api-version=2024-02-15-preview"
        assert call_args[0][0] == expected_url

        # Verify context data is included in the request
        payload = call_args[1]["json"]
        user_message = payload["messages"][1]["content"]
        assert "Context Data:" in user_message
        assert "wip_count" in user_message
        assert "throughput_last_week" in user_message
        assert "Query: Analyze WIP levels" in user_message

    @patch("jira_agile_metrics.copilot.providers.requests.post")
    def test_generate_insights_dry_run(self, mock_post, capsys):
        config = {
            "dry_run": True,
            "api_base": "https://test-resource.openai.azure.com",
            "model": "gpt-4-deployment",
        }

        with patch.dict("os.environ", {}, clear=True):
            provider = AzureOpenAIProvider(config)
            result = provider.generate_insights(
                "Dry run test", SAMPLE_CONTEXT
            )

        mock_post.assert_not_called()

        captured = capsys.readouterr()
        assert "--- PAYLOAD (Azure OpenAI) ---" in captured.out
        assert "URL: https://test-resource.openai.azure.com" in captured.out
        assert '"role": "user"' in captured.out
        assert "--- END PAYLOAD ---" in captured.out

        assert "Dry run mode: Azure OpenAI API not called" in result


class TestLLMFactory:
    """Test LLM factory for creating providers."""

    def test_create_openai_provider(self):
        config = {"provider": "openai", "model": "gpt-4o"}
        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-4o"

    def test_create_anthropic_provider(self):
        config = {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
        }
        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-3-5-sonnet-20241022"

    def test_create_azure_provider(self):
        config = {
            "provider": "azure",
            "model": "gpt-4-deployment",
            "api_base": "https://test.openai.azure.com",
        }
        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, AzureOpenAIProvider)
        assert provider.deployment_name == "gpt-4-deployment"

    def test_create_unsupported_provider(self):
        config = {"provider": "unsupported-llm"}

        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create_provider(config)

        assert "Unsupported provider: unsupported-llm" in str(exc_info.value)
        assert "openai, anthropic, azure" in str(exc_info.value)

    def test_validate_provider_config_valid(self):
        config = {"provider": "openai", "api_key_env": "TEST_KEY"}

        with patch.dict("os.environ", {"TEST_KEY": "test-key-123"}):
            errors = LLMFactory.validate_provider_config(config)

        assert errors == []

    def test_validate_provider_config_missing_provider(self):
        config = {}
        errors = LLMFactory.validate_provider_config(config)
        assert len(errors) == 1
        assert "AI provider not specified" in errors[0]

    def test_validate_provider_config_invalid_config(self):
        config = {"provider": "openai", "api_key_env": "MISSING_KEY"}

        with patch.dict("os.environ", {}, clear=True):
            errors = LLMFactory.validate_provider_config(config)

        assert len(errors) == 1
        assert "Invalid configuration for openai" in errors[0]

    def test_list_available_providers(self):
        providers = LLMFactory.list_available_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "azure" in providers
        assert len(providers) == 3


class TestSystemPrompt:
    """Test that system prompts contain anti-hallucination constraints."""

    def test_system_prompt_contains_constraints(self):
        config = {"api_key_env": "TEST_KEY"}

        with patch.dict("os.environ", {"TEST_KEY": "test-key"}):
            provider = OpenAIProvider(config)
            system_prompt = provider._get_system_prompt()

        # Verify anti-hallucination constraints are present
        assert (
            "ONLY reference ticket IDs that exist in the provided context"
            in system_prompt
        )
        assert "ONLY use metrics that are explicitly provided" in system_prompt
        assert "Always cite the source data" in system_prompt
        assert "Never invent or extrapolate ticket numbers" in system_prompt
        assert (
            "Include specific ticket IDs in recommendations" in system_prompt
        )
