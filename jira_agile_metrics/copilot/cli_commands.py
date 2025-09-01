"""
CLI command implementations for AI copilot functionality.
Separates business logic from console output formatting.
"""

import logging
import os
from typing import Any, Dict, List, Tuple

from .insights_generator import InsightsGenerator
from .providers import LLMFactory

logger = logging.getLogger(__name__)


class AIConfigValidator:
    """Handles AI configuration validation logic."""

    def __init__(self, ai_config: Dict):
        self.ai_config = ai_config

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate AI configuration. Returns (is_valid, error_messages)."""
        errors = LLMFactory.validate_provider_config(self.ai_config)
        return len(errors) == 0, errors

class AIInsightsCommand:
    """Handles AI insights generation logic."""

    def __init__(self, ai_config: Dict, output_dir: str | None = None, dry_run : bool = False):
        self.ai_config = ai_config
        self.output_dir = output_dir
        self.dry_run = dry_run

    def _get_context_file_path(self, context_file: str) -> str:
        """Return the full path to the context file."""
        if self.output_dir and not os.path.isabs(context_file):
            return os.path.join(self.output_dir, context_file)
        return context_file

    def validate_prerequisites(self, context_file: str) -> Tuple[bool, str]:
        """Check if all prerequisites are met. Returns (is_valid, error_message)."""
        # Validate AI configuration, skipping if in dry-run mode

        if not self.dry_run:
            validator = AIConfigValidator(self.ai_config)
            is_valid, errors = validator.validate()
            if not is_valid:
                return False, f"AI Configuration Errors: {'; '.join(errors)}"

        # Check context file exists
        full_path = self._get_context_file_path(context_file)
        if not os.path.exists(full_path):
            return (
                False,
                f"Context file not found: {full_path}. Run regular metrics analysis first.",
            )

        return True, ""

    def generate_insights(self, context_file: str, output_file: str) -> Tuple[bool, str, str]:
        """
        Generate AI insights.
        Returns (success, result_message, preview_text).
        """
        try:
            # Get full paths for context and output files
            context_file_path = self._get_context_file_path(context_file)
            output_file_path = os.path.join(self.output_dir, output_file) if self.output_dir else output_file

            # Generate insights
            generator = InsightsGenerator(self.ai_config, self.dry_run)
            insights = generator.generate_daily_insights(context_file_path, output_file_path)

            # Handle dry run case
            if self.dry_run:
                return True, f"Dry run complete. Would write insights to: {output_file_path}", insights

            # Create preview for actual insights
            preview = insights[:500] + "..." if len(insights) > 500 else insights

            return True, f"Daily insights generated: {output_file_path}", preview

        except Exception as e:
            logger.exception("Error generating insights")
            return False, f"Error generating insights: {str(e)}", ""

