"""
Unit tests for CLI command handlers.
"""

import os
from unittest.mock import Mock, patch

from .cli_commands import AIConfigValidator, AIInsightsCommand, create_ai_config_from_settings_and_args


class TestAIConfigValidator:
    """Test AI configuration validator."""

    @patch("jira_agile_metrics.copilot.cli_commands.LLMFactory.validate_provider_config")
    def test_validate_success(self, mock_validate):
        mock_validate.return_value = []  # No errors

        config = {"provider": "openai", "model": "gpt-4o"}
        validator = AIConfigValidator(config)

        is_valid, errors = validator.validate()

        assert is_valid is True
        assert errors == []
        mock_validate.assert_called_once_with(config)

    @patch("jira_agile_metrics.copilot.cli_commands.LLMFactory.validate_provider_config")
    def test_validate_errors(self, mock_validate):
        mock_validate.return_value = ["API key not found", "Invalid model"]

        config = {"provider": "openai"}
        validator = AIConfigValidator(config)

        is_valid, errors = validator.validate()

        assert is_valid is False
        assert len(errors) == 2
        assert "API key not found" in errors

    @patch("jira_agile_metrics.copilot.cli_commands.LLMFactory.list_available_providers")
    def test_get_config_summary(self, mock_list_providers):
        mock_list_providers.return_value = ["openai", "anthropic"]

        config = {"provider": "openai", "model": "gpt-4o"}
        validator = AIConfigValidator(config)

        summary = validator.get_config_summary()

        assert summary["provider"] == "openai"
        assert summary["model"] == "gpt-4o"
        assert summary["available_providers"] == ["openai", "anthropic"]


class TestAIInsightsCommand:
    """Test AI insights command handler."""

    def test_validate_prerequisites_success(self):
        ai_config = {"provider": "openai", "model": "gpt-4o"}
        command = AIInsightsCommand(ai_config)

        with patch("jira_agile_metrics.copilot.cli_commands.AIConfigValidator") as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate.return_value = (True, [])
            mock_validator_class.return_value = mock_validator

            with patch("os.path.exists", return_value=True):
                is_valid, error = command.validate_prerequisites("context.json")

        assert is_valid is True
        assert error == ""

    def test_validate_prerequisites_invalid_config(self):
        ai_config = {}  # Invalid config
        command = AIInsightsCommand(ai_config)

        with patch("jira_agile_metrics.copilot.cli_commands.AIConfigValidator") as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate.return_value = (
                False,
                ["Provider not specified"],
            )
            mock_validator_class.return_value = mock_validator

            is_valid, error = command.validate_prerequisites("context.json")

        assert is_valid is False
        assert "AI Configuration Errors" in error

    def test_validate_prerequisites_missing_context(self):
        ai_config = {"provider": "openai"}
        command = AIInsightsCommand(ai_config)

        with patch("jira_agile_metrics.copilot.cli_commands.AIConfigValidator") as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate.return_value = (True, [])
            mock_validator_class.return_value = mock_validator

            with patch("os.path.exists", return_value=False):
                is_valid, error = command.validate_prerequisites("missing.json")

        assert is_valid is False
        assert "Context file not found" in error

    def test_validate_prerequisites_skips_validation_on_dry_run(self):
        # Config is invalid, but should pass with dry_run
        ai_config = {"provider": "openai", "dry_run": True}
        command = AIInsightsCommand(ai_config)

        with patch(
            "jira_agile_metrics.copilot.cli_commands.AIConfigValidator.validate",
        ) as mock_validate, patch("os.path.exists", return_value=True):
            is_valid, error = command.validate_prerequisites("context.json")

        assert is_valid is True
        assert error == ""
        mock_validate.assert_not_called()

    @patch("jira_agile_metrics.copilot.cli_commands.InsightsGenerator")
    def test_generate_insights_success(self, mock_insights_generator_class):
        mock_generator = Mock()
        mock_generator.generate_daily_insights.return_value = "# Daily Briefing\nTest insights content"
        mock_insights_generator_class.return_value = mock_generator

        ai_config = {"provider": "openai"}
        command = AIInsightsCommand(ai_config)

        success, message, preview = command.generate_insights("context.json", "output.md")

        assert success is True
        assert "Daily insights generated" in message
        assert "Test insights content" in preview
        mock_insights_generator_class.assert_called_once_with(ai_config)

    @patch("jira_agile_metrics.copilot.cli_commands.InsightsGenerator")
    def test_generate_insights_with_output_dir(self, mock_insights_generator_class):
        """Test that file paths are correctly constructed when an output dir is given."""
        ai_config = {"dry_run": True}
        output_dir = "test_output"
        context_filename = "context.json"
        insights_filename = "insights.md"

        # Mock generator
        mock_generator = Mock()
        mock_generator.generate_daily_insights.return_value = "Dry run insights"
        mock_insights_generator_class.return_value = mock_generator

        command = AIInsightsCommand(ai_config, output_dir=output_dir)

        # Test insights generation
        command.generate_insights(context_filename, insights_filename)

        # Verify that the generator was called with correctly joined paths
        expected_context_path = os.path.join(output_dir, context_filename)
        expected_insights_path = os.path.join(output_dir, insights_filename)
        mock_generator.generate_daily_insights.assert_called_once_with(expected_context_path, expected_insights_path)

    @patch("jira_agile_metrics.copilot.cli_commands.InsightsGenerator")
    def test_generate_insights_error(self, mock_insights_generator_class):
        mock_generator = Mock()
        mock_generator.generate_daily_insights.side_effect = Exception("AI service unavailable")
        mock_insights_generator_class.return_value = mock_generator

        ai_config = {"provider": "openai"}
        command = AIInsightsCommand(ai_config)

        success, message, preview = command.generate_insights("context.json", "insights.md")

        assert success is False
        assert "Error generating insights" in message
        assert preview == ""


class TestCreateAIConfigFromSettingsAndArgs:
    """Test AI config creation from settings and args."""

    def test_uses_settings_without_overrides(self):
        settings = {"ai": {"provider": "openai", "model": "gpt-4o", "temperature": 0.3}}

        args = Mock()
        args.dry_run = False

        result = create_ai_config_from_settings_and_args(settings, args)

        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"
        assert result["temperature"] == 0.3

    def test_no_ai_settings(self):
        settings = {}  # No AI config
        args = Mock()
        args.dry_run = False

        result = create_ai_config_from_settings_and_args(settings, args)

        assert result == {}

    def test_no_args_override(self):
        settings = {"ai": {"provider": "openai", "model": "gpt-4o"}}
        args = Mock()
        args.dry_run = False

        result = create_ai_config_from_settings_and_args(settings, args)

        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"

    def test_dry_run_arg(self):
        settings = {"ai": {"provider": "openai"}}
        args = Mock()
        args.dry_run = True

        result = create_ai_config_from_settings_and_args(settings, args)

        assert result["provider"] == "openai"
        assert result["dry_run"] is True


class TestIntegration:
    """Integration tests for CLI commands."""

    def test_full_insights_workflow(self):
        """Test complete insights generation workflow."""
        ai_config = {"provider": "openai", "model": "gpt-4o"}
        command = AIInsightsCommand(ai_config)

        # Mock all dependencies
        with patch("jira_agile_metrics.copilot.cli_commands.AIConfigValidator") as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate.return_value = (True, [])
            mock_validator_class.return_value = mock_validator

            with patch("os.path.exists", return_value=True):
                with patch("jira_agile_metrics.copilot.cli_commands.InsightsGenerator") as mock_gen_class:
                    mock_generator = Mock()
                    mock_generator.generate_daily_insights.return_value = "Test insights"
                    mock_gen_class.return_value = mock_generator

                    # Validate prerequisites
                    is_valid, error = command.validate_prerequisites("context.json")
                    assert is_valid is True

                    # Generate insights
                    success, message, preview = command.generate_insights("context.json", "insights.md")
                    assert success is True
                    assert "Test insights" in preview
