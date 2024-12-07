"""Tests for the LocalLLMProvider class."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import requests

from text_humanizer.src.providers.local_llm_provider import LocalLLMProvider
from text_humanizer.src.config import TestingConfig

@pytest.fixture
def provider():
    """Create a LocalLLMProvider instance with test configuration."""
    return LocalLLMProvider(config_name="testing")

def test_init_with_config(provider):
    """Test provider initialization with config settings."""
    assert provider.max_retries == TestingConfig.LLM_MAX_RETRIES
    assert provider.retry_delay == TestingConfig.LLM_RETRY_DELAY
    assert provider.fallback_models == TestingConfig.LLM_FALLBACK_MODELS

@patch('requests.post')
def test_health_check_success(mock_post, provider):
    """Test successful health check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    assert provider.check_model_health("test-model") is True
    mock_post.assert_called_once()

@patch('requests.post')
def test_health_check_failure(mock_post, provider):
    """Test failed health check."""
    mock_post.side_effect = requests.exceptions.RequestException()
    
    assert provider.check_model_health("test-model") is False
    mock_post.assert_called_once()

@patch('requests.post')
def test_health_check_caching(mock_post, provider):
    """Test health check result caching."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    # First call should make the request
    assert provider.check_model_health("test-model") is True
    assert mock_post.call_count == 1
    
    # Second call within cache interval should use cached result
    assert provider.check_model_health("test-model") is True
    assert mock_post.call_count == 1

@patch.object(LocalLLMProvider, 'check_model_health')
@patch.object(LocalLLMProvider, 'switch_model')
def test_fallback_mechanism(mock_switch, mock_health, provider):
    """Test fallback mechanism when primary model fails."""
    # Mock health checks: primary fails, fallback succeeds
    mock_health.side_effect = [False, True]
    mock_switch.return_value = True
    
    provider.verify_connection()
    
    # Should have tried primary model then fallback
    assert mock_health.call_count == 2
    mock_switch.assert_called_once()

@patch('requests.post')
def test_retry_with_fallback_decorator(mock_post, provider):
    """Test retry mechanism with fallback."""
    # Mock first model failing, second succeeding
    mock_post.side_effect = [
        requests.exceptions.RequestException(),  # First try fails
        requests.exceptions.RequestException(),  # Retry fails
        MagicMock(status_code=200)  # Fallback succeeds
    ]
    
    result = provider.infer({"prompt": "test"})
    assert result["status"] == "success"
    assert mock_post.call_count == 3  # Two tries with first model, one with fallback

def test_switch_model_validation(provider):
    """Test model switching with validation."""
    with patch.object(LocalLLMProvider, 'check_model_health') as mock_health:
        mock_health.return_value = False
        
        # Should fail if health check fails
        assert provider.switch_model(model_name="invalid-model") is False
        mock_health.assert_called_once_with("invalid-model")
