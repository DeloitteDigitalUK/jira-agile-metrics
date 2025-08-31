"""
CLI command implementations for AI copilot functionality.
Separates business logic from console output formatting.
"""

import os
import logging
from typing import Dict, List, Tuple
from .providers import LLMFactory
from .insights_generator import InsightsGenerator

logger = logging.getLogger(__name__)


class AIConfigValidator:
    """Handles AI configuration validation logic."""

    def __init__(self, ai_config: Dict):
        self.ai_config = ai_config

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate AI configuration. Returns (is_valid, error_messages)."""
        errors = LLMFactory.validate_provider_config(self.ai_config)
        return len(errors) == 0, errors

    def get_config_summary(self) -> Dict[str, str]:
        """Get summary of current configuration."""
        return {
            "provider": self.ai_config.get("provider", "not specified"),
            "model": self.ai_config.get("model", "not specified"),
            "available_providers": LLMFactory.list_available_providers(),
        }


class AIInsightsCommand:
    """Handles AI insights generation logic."""

    def __init__(self, ai_config: Dict, output_dir: str = None):
        self.ai_config = ai_config
        self.output_dir = output_dir

    def validate_prerequisites(self, context_file: str) -> Tuple[bool, str]:
        """Check if all prerequisites are met. Returns (is_valid, error_message)."""
        # Validate AI configuration, skipping if in dry-run mode
        if not self.ai_config.get("dry_run", False):
            validator = AIConfigValidator(self.ai_config)
            is_valid, errors = validator.validate()
            if not is_valid:
                return False, f"AI Configuration Errors: {'; '.join(errors)}"

        # Check context file exists
        if not os.path.exists(context_file):
            return (
                False,
                f"Context file not found: {context_file}. Run regular metrics analysis first.",
            )

        return True, ""

    def generate_insights(
        self, context_file: str, output_file: str = "daily-insights.md"
    ) -> Tuple[bool, str, str]:
        """
        Generate AI insights.
        Returns (success, result_message, preview_text).
        """
        try:
            # Change to output directory if specified
            if self.output_dir:
                os.chdir(self.output_dir)

            # Generate insights
            generator = InsightsGenerator(self.ai_config)
            insights = generator.generate_daily_insights(
                context_file, output_file
            )

            # Create preview
            preview = (
                insights[:500] + "..." if len(insights) > 500 else insights
            )

            return True, f"Daily insights generated: {output_file}", preview

        except Exception as e:
            logger.exception("Error generating insights")
            return False, f"Error generating insights: {str(e)}", ""


def create_ai_config_from_settings_and_args(settings: Dict, args) -> Dict:
    """Create AI config by merging settings with command line arguments."""
    ai_config = settings.get("ai", {})

    # Override with command line arguments
    if hasattr(args, "ai_provider") and args.ai_provider:
        ai_config["provider"] = args.ai_provider
    if hasattr(args, "ai_model") and args.ai_model:
        ai_config["model"] = args.ai_model
    if hasattr(args, "dry_run") and args.dry_run:
        ai_config["dry_run"] = args.dry_run

    return ai_config
