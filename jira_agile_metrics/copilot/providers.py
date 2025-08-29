"""
LLM provider abstraction layer for AI copilot functionality.
Supports multiple providers with bring-your-own-API-key design.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate_insights(self, prompt: str, context: Dict) -> str:
        """Generate insights from the given prompt and context."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate that the provider is properly configured."""
        pass
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for agile coaching."""
        return """You are an expert agile team coach and flow metrics analyst. Your role is to:

1. Analyze agile flow metrics and identify bottlenecks
2. Provide actionable recommendations for team leads
3. Focus on improving delivery flow and team efficiency

CRITICAL CONSTRAINTS:
- ONLY reference ticket IDs that exist in the provided context
- ONLY use metrics that are explicitly provided in the data
- Always cite the source data for any claim (include ticket IDs)
- If asked about data not in context, respond "I don't have that information"
- Never invent or extrapolate ticket numbers, statuses, or team member names
- Include specific ticket IDs in recommendations for verification

Your recommendations should be:
- Actionable (what specific action to take)
- Prioritized (most impactful first)
- Evidence-based (backed by the provided metrics)
- Focused on flow efficiency improvements"""
    
    def _format_user_message(self, prompt: str, context: Dict) -> str:
        """Format user message with context data and query."""
        context_str = json.dumps(context, indent=2) if context else "No context data provided"
        return f"Context Data:\n{context_str}\n\nQuery: {prompt}"


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, config: Dict):
        self.api_key = os.getenv(config.get('api_key_env', 'OPENAI_API_KEY'))
        self.model = config.get('model', 'gpt-4o')
        self.api_base = config.get('api_base', 'https://api.openai.com/v1')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.1)
        
    def generate_insights(self, prompt: str, context: Dict) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': self._get_system_prompt()},
                {'role': 'user', 'content': self._format_user_message(prompt, context)}
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        logger.debug(f"Calling OpenAI API with model {self.model}")
        
        try:
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error ({response.status_code}): {response.text}")
                
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error calling OpenAI API: {str(e)}")
    
    def validate_config(self) -> bool:
        return self.api_key is not None


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, config: Dict):
        self.api_key = os.getenv(config.get('api_key_env', 'ANTHROPIC_API_KEY'))
        self.model = config.get('model', 'claude-3-5-sonnet-20241022')
        self.max_tokens = config.get('max_tokens', 2000)
        
    def generate_insights(self, prompt: str, context: Dict) -> str:
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
            
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        # Anthropic expects system prompt in the message
        full_prompt = f"{self._get_system_prompt()}\n\n{self._format_user_message(prompt, context)}"
        
        payload = {
            'model': self.model,
            'max_tokens': self.max_tokens,
            'messages': [
                {'role': 'user', 'content': full_prompt}
            ]
        }
        
        logger.debug(f"Calling Anthropic API with model {self.model}")
        
        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Anthropic API error ({response.status_code}): {response.text}")
                
            result = response.json()
            return result['content'][0]['text']
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error calling Anthropic API: {str(e)}")
    
    def validate_config(self) -> bool:
        return self.api_key is not None


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider implementation."""
    
    def __init__(self, config: Dict):
        self.api_key = os.getenv(config.get('api_key_env', 'AZURE_OPENAI_API_KEY'))
        self.api_base = config.get('api_base')
        self.api_version = config.get('api_version', '2024-02-15-preview')
        self.deployment_name = config.get('model')  # In Azure, this is the deployment name
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.1)
        
    def generate_insights(self, prompt: str, context: Dict) -> str:
        if not self.api_key or not self.api_base or not self.deployment_name:
            raise ValueError("Azure OpenAI requires api_key, api_base, and deployment name (model).")
            
        headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messages': [
                {'role': 'system', 'content': self._get_system_prompt()},
                {'role': 'user', 'content': self._format_user_message(prompt, context)}
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        url = f"{self.api_base}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        
        logger.debug(f"Calling Azure OpenAI API with deployment {self.deployment_name}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"Azure OpenAI API error ({response.status_code}): {response.text}")
                
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error calling Azure OpenAI API: {str(e)}")
    
    def validate_config(self) -> bool:
        return all([self.api_key, self.api_base, self.deployment_name])


class LLMFactory:
    """Factory for creating LLM provider instances."""
    
    PROVIDERS = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'azure': AzureOpenAIProvider,
    }
    
    @classmethod
    def create_provider(cls, config: Dict) -> LLMProvider:
        """Create an LLM provider instance from configuration."""
        provider_type = config.get('provider', '').lower()
        
        if provider_type not in cls.PROVIDERS:
            available = ', '.join(cls.PROVIDERS.keys())
            raise ValueError(f"Unsupported provider: {provider_type}. Available: {available}")
            
        provider_class = cls.PROVIDERS[provider_type]
        return provider_class(config)
    
    @classmethod
    def validate_provider_config(cls, config: Dict) -> List[str]:
        """Validate provider configuration. Returns list of errors (empty if valid)."""
        errors = []
        
        provider = config.get('provider')
        if not provider:
            errors.append("AI provider not specified")
            return errors
            
        try:
            llm = cls.create_provider(config)
            if not llm.validate_config():
                errors.append(f"Invalid configuration for {provider} provider")
        except Exception as e:
            errors.append(f"Provider setup error: {str(e)}")
            
        return errors
    
    @classmethod
    def list_available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        return list(cls.PROVIDERS.keys())
