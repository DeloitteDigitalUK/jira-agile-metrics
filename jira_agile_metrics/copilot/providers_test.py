"""
Unit tests for LLM providers with offline mocks.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from .providers import (
    OpenAIProvider, 
    AnthropicProvider, 
    AzureOpenAIProvider, 
    LLMFactory
)


class TestOpenAIProvider:
    """Test OpenAI provider with mocked API calls."""
    
    def test_init_with_config(self):
        config = {
            'model': 'gpt-4o',
            'api_key_env': 'TEST_OPENAI_KEY',
            'max_tokens': 1500,
            'temperature': 0.2
        }
        
        with patch.dict('os.environ', {'TEST_OPENAI_KEY': 'test-key-123'}):
            provider = OpenAIProvider(config)
            
        assert provider.model == 'gpt-4o'
        assert provider.api_key == 'test-key-123'
        assert provider.max_tokens == 1500
        assert provider.temperature == 0.2
    
    def test_validate_config_with_api_key(self):
        config = {'api_key_env': 'TEST_OPENAI_KEY'}
        
        with patch.dict('os.environ', {'TEST_OPENAI_KEY': 'test-key-123'}):
            provider = OpenAIProvider(config)
            assert provider.validate_config() is True
    
    def test_validate_config_without_api_key(self):
        config = {'api_key_env': 'MISSING_KEY'}
        
        with patch.dict('os.environ', {}, clear=True):
            provider = OpenAIProvider(config)
            assert provider.validate_config() is False
    
    @patch('jira_agile_metrics.copilot.providers.requests.post')
    def test_generate_insights_success(self, mock_post):
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Test AI insight: Focus on reducing cycle time for PROJ-123.'
                }
            }]
        }
        mock_post.return_value = mock_response
        
        config = {'api_key_env': 'TEST_OPENAI_KEY', 'model': 'gpt-4o'}
        
        with patch.dict('os.environ', {'TEST_OPENAI_KEY': 'test-key-123'}):
            provider = OpenAIProvider(config)
            result = provider.generate_insights("Test prompt", {})
        
        assert result == 'Test AI insight: Focus on reducing cycle time for PROJ-123.'
        
        # Verify API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://api.openai.com/v1/chat/completions'
        assert 'Authorization' in call_args[1]['headers']
        assert call_args[1]['headers']['Authorization'] == 'Bearer test-key-123'
    
    @patch('jira_agile_metrics.copilot.providers.requests.post')
    def test_generate_insights_api_error(self, mock_post):
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_post.return_value = mock_response
        
        config = {'api_key_env': 'TEST_OPENAI_KEY'}
        
        with patch.dict('os.environ', {'TEST_OPENAI_KEY': 'invalid-key'}):
            provider = OpenAIProvider(config)
            
            with pytest.raises(Exception) as exc_info:
                provider.generate_insights("Test prompt", {})
            
            assert "OpenAI API error (401)" in str(exc_info.value)
    
    def test_generate_insights_no_api_key(self):
        config = {'api_key_env': 'MISSING_KEY'}
        
        with patch.dict('os.environ', {}, clear=True):
            provider = OpenAIProvider(config)
            
            with pytest.raises(ValueError) as exc_info:
                provider.generate_insights("Test prompt", {})
            
            assert "OpenAI API key not found" in str(exc_info.value)


class TestAnthropicProvider:
    """Test Anthropic provider with mocked API calls."""
    
    @patch('jira_agile_metrics.copilot.providers.requests.post')
    def test_generate_insights_success(self, mock_post):
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{
                'text': 'Anthropic AI insight: Review bottleneck detected in PROJ-456.'
            }]
        }
        mock_post.return_value = mock_response
        
        config = {'api_key_env': 'TEST_ANTHROPIC_KEY', 'model': 'claude-3-5-sonnet-20241022'}
        
        with patch.dict('os.environ', {'TEST_ANTHROPIC_KEY': 'test-key-456'}):
            provider = AnthropicProvider(config)
            result = provider.generate_insights("Test prompt", {})
        
        assert result == 'Anthropic AI insight: Review bottleneck detected in PROJ-456.'
        
        # Verify API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == 'https://api.anthropic.com/v1/messages'
        assert 'x-api-key' in call_args[1]['headers']


class TestAzureOpenAIProvider:
    """Test Azure OpenAI provider with mocked API calls."""
    
    @patch('jira_agile_metrics.copilot.providers.requests.post')
    def test_generate_insights_success(self, mock_post):
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Azure AI insight: WIP limit exceeded, consider pausing new work.'
                }
            }]
        }
        mock_post.return_value = mock_response
        
        config = {
            'api_key_env': 'TEST_AZURE_KEY',
            'api_base': 'https://test-resource.openai.azure.com',
            'api_version': '2024-02-15-preview',
            'model': 'gpt-4-deployment'
        }
        
        with patch.dict('os.environ', {'TEST_AZURE_KEY': 'test-azure-key'}):
            provider = AzureOpenAIProvider(config)
            result = provider.generate_insights("Test prompt", {})
        
        assert result == 'Azure AI insight: WIP limit exceeded, consider pausing new work.'
        
        # Verify correct URL construction
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        expected_url = 'https://test-resource.openai.azure.com/openai/deployments/gpt-4-deployment/chat/completions?api-version=2024-02-15-preview'
        assert call_args[0][0] == expected_url


class TestLLMFactory:
    """Test LLM factory for creating providers."""
    
    def test_create_openai_provider(self):
        config = {'provider': 'openai', 'model': 'gpt-4o'}
        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == 'gpt-4o'
    
    def test_create_anthropic_provider(self):
        config = {'provider': 'anthropic', 'model': 'claude-3-5-sonnet-20241022'}
        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, AnthropicProvider)
        assert provider.model == 'claude-3-5-sonnet-20241022'
    
    def test_create_azure_provider(self):
        config = {
            'provider': 'azure',
            'model': 'gpt-4-deployment',
            'api_base': 'https://test.openai.azure.com'
        }
        provider = LLMFactory.create_provider(config)
        assert isinstance(provider, AzureOpenAIProvider)
        assert provider.deployment_name == 'gpt-4-deployment'
    
    def test_create_unsupported_provider(self):
        config = {'provider': 'unsupported-llm'}
        
        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create_provider(config)
        
        assert "Unsupported provider: unsupported-llm" in str(exc_info.value)
        assert "openai, anthropic, azure" in str(exc_info.value)
    
    def test_validate_provider_config_valid(self):
        config = {'provider': 'openai', 'api_key_env': 'TEST_KEY'}
        
        with patch.dict('os.environ', {'TEST_KEY': 'test-key-123'}):
            errors = LLMFactory.validate_provider_config(config)
        
        assert errors == []
    
    def test_validate_provider_config_missing_provider(self):
        config = {}
        errors = LLMFactory.validate_provider_config(config)
        assert len(errors) == 1
        assert "AI provider not specified" in errors[0]
    
    def test_validate_provider_config_invalid_config(self):
        config = {'provider': 'openai', 'api_key_env': 'MISSING_KEY'}
        
        with patch.dict('os.environ', {}, clear=True):
            errors = LLMFactory.validate_provider_config(config)
        
        assert len(errors) == 1
        assert "Invalid configuration for openai" in errors[0]
    
    def test_list_available_providers(self):
        providers = LLMFactory.list_available_providers()
        assert 'openai' in providers
        assert 'anthropic' in providers
        assert 'azure' in providers
        assert len(providers) == 3


class TestSystemPrompt:
    """Test that system prompts contain anti-hallucination constraints."""
    
    def test_system_prompt_contains_constraints(self):
        config = {'api_key_env': 'TEST_KEY'}
        
        with patch.dict('os.environ', {'TEST_KEY': 'test-key'}):
            provider = OpenAIProvider(config)
            system_prompt = provider._get_system_prompt()
        
        # Verify anti-hallucination constraints are present
        assert "ONLY reference ticket IDs that exist in the provided context" in system_prompt
        assert "ONLY use metrics that are explicitly provided" in system_prompt
        assert "Always cite the source data" in system_prompt
        assert "Never invent or extrapolate ticket numbers" in system_prompt
        assert "Include specific ticket IDs in recommendations" in system_prompt
