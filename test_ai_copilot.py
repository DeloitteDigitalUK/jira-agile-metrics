#!/usr/bin/env python3
"""
Standalone test runner for AI copilot functionality.
Now works with Python 3.11 and proper pandas installation.
"""

import sys
import os
from unittest.mock import Mock, patch, mock_open

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jira_agile_metrics'))


def run_test_method(test_class, method_name):
    """Run a single test method and return (success, error_message)."""
    try:
        test_instance = test_class()
        test_method = getattr(test_instance, method_name)
        test_method()
        return True, None
    except Exception as e:
        return False, str(e)


def run_test_suite():
    """Run the AI copilot test suite."""
    
    print("🚀 Running AI Copilot Test Suite")
    print("=" * 50)
    
    # Import test modules after mocking pandas
    from jira_agile_metrics.copilot.providers_test import (
        TestOpenAIProvider,
        TestAnthropicProvider, 
        TestAzureOpenAIProvider,
        TestLLMFactory,
        TestSystemPrompt
    )
    
    from jira_agile_metrics.copilot.insights_generator_test import TestInsightsGenerator
    from jira_agile_metrics.copilot.cli_commands_test import (
        TestAIConfigValidator,
        TestAIInsightsCommand,
        TestCreateAIConfigFromSettingsAndArgs,
        TestIntegration
    )
    
    # Define test cases to run
    test_cases = [
        # Provider tests
        (TestOpenAIProvider, 'test_init_with_config'),
        (TestOpenAIProvider, 'test_validate_config_with_api_key'),
        (TestOpenAIProvider, 'test_validate_config_without_api_key'),
        (TestOpenAIProvider, 'test_generate_insights_success'),
        (TestOpenAIProvider, 'test_generate_insights_api_error'),
        (TestOpenAIProvider, 'test_generate_insights_no_api_key'),
        
        (TestAnthropicProvider, 'test_generate_insights_success'),
        (TestAzureOpenAIProvider, 'test_generate_insights_success'),
        
        (TestLLMFactory, 'test_create_openai_provider'),
        (TestLLMFactory, 'test_create_anthropic_provider'),
        (TestLLMFactory, 'test_create_azure_provider'),
        (TestLLMFactory, 'test_create_unsupported_provider'),
        (TestLLMFactory, 'test_validate_provider_config_valid'),
        (TestLLMFactory, 'test_validate_provider_config_missing_provider'),
        (TestLLMFactory, 'test_list_available_providers'),
        
        (TestSystemPrompt, 'test_system_prompt_contains_constraints'),
        
        # Insights generator tests
        (TestInsightsGenerator, 'test_init'),
        (TestInsightsGenerator, 'test_generate_daily_insights_success'),
        (TestInsightsGenerator, 'test_generate_daily_insights_file_not_found'),
        (TestInsightsGenerator, 'test_generate_chat_response_success'),
        (TestInsightsGenerator, 'test_calculate_sprint_day'),
        (TestInsightsGenerator, 'test_format_metrics_for_prompt'),
        (TestInsightsGenerator, 'test_format_issues_for_prompt'),
        (TestInsightsGenerator, 'test_extract_ticket_references'),
        (TestInsightsGenerator, 'test_format_daily_insights_structure'),
        
        # CLI command tests
        (TestAIConfigValidator, 'test_validate_success'),
        (TestAIConfigValidator, 'test_validate_errors'),
        (TestAIConfigValidator, 'test_get_config_summary'),
        
        (TestAIInsightsCommand, 'test_validate_prerequisites_success'),
        (TestAIInsightsCommand, 'test_validate_prerequisites_invalid_config'),
        (TestAIInsightsCommand, 'test_validate_prerequisites_missing_context'),
        (TestAIInsightsCommand, 'test_generate_insights_success'),
        (TestAIInsightsCommand, 'test_generate_insights_error'),
        
        (TestCreateAIConfigFromSettingsAndArgs, 'test_merge_settings_and_args'),
        (TestCreateAIConfigFromSettingsAndArgs, 'test_no_ai_settings'),
        (TestCreateAIConfigFromSettingsAndArgs, 'test_no_args_override'),
        
        (TestIntegration, 'test_full_insights_workflow'),
    ]
    
    # Run tests
    passed = 0
    failed = 0
    errors = []
    
    for test_class, method_name in test_cases:
        test_name = f"{test_class.__name__}.{method_name}"
        print(f"Running {test_name}...", end=" ")
        
        success, error = run_test_method(test_class, method_name)
        
        if success:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            errors.append(f"{test_name}: {error}")
    
    # Print summary
    total = passed + failed
    print("\n" + "=" * 50)
    print(f"Tests run: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if errors:
        print("\nFAILURES:")
        for error in errors:
            print(f"- {error}")
    
    success = failed == 0
    print(f"\n{'✅ ALL TESTS PASSED' if success else '❌ SOME TESTS FAILED'}")
    
    return success


if __name__ == '__main__':
    success = run_test_suite()
    sys.exit(0 if success else 1)
