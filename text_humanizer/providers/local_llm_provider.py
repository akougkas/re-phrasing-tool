"""
Implementation of local LLM provider.
Handles communication with a locally hosted LLM endpoint.
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
import requests
from requests.exceptions import RequestException
import time
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import psutil
import hashlib

from text_humanizer.providers.base_llm_provider import BaseLLMProvider, LLMConfig
from text_humanizer.utils.logger import logger
try:
    from text_humanizer.config import config as llm_config
except ImportError:
    # Default configuration if module not found
    class DefaultConfig:
        LLM_MAX_RETRIES = 3
        LLM_RETRY_DELAY = 1
        LLM_FALLBACK_MODELS = ["gpt2", "gpt2-medium"]
        LLM_HEALTH_CHECK_INTERVAL = 60
        LLM_HEALTH_CHECK_TIMEOUT = 5
        LLM_CACHE_TTL = 3600  # 1 hour default
    llm_config = {"default": DefaultConfig}

class LocalLLMProvider(BaseLLMProvider):
    """Provider for interacting with local LLM endpoint with fallback and retry mechanisms."""
    
    def __init__(self, endpoint_url: Optional[str] = None,
                 model_name: Optional[str] = None,
                 config_name: str = "default"):
        """Initialize the provider with configuration."""
        config_class = llm_config.get(config_name, llm_config["default"])()
        
        # Get LLM settings from config
        llm_settings = getattr(config_class, 'llm_settings', {})
        
        # Create LLM config with defaults
        llm_config_obj = LLMConfig(
            endpoint_url=endpoint_url or os.getenv('LLM_ENDPOINT_URL', 'http://localhost:1234'),
            model_name=model_name or getattr(config_class, 'LLM_FALLBACK_MODELS', ["gpt2"])[0],
            timeout=llm_settings.get('request_timeout', 30),
            max_tokens=getattr(config_class, 'LLM_MAX_TOKENS', 2048)
        )
        
        # Initialize base class
        super().__init__(llm_config_obj)
        
        # Store configuration values with defaults
        self.max_retries = llm_settings.get('max_retries', 3)
        self.retry_delay = llm_settings.get('retry_delay', 1)
        self.fallback_models = getattr(config_class, 'LLM_FALLBACK_MODELS', ["gpt2", "gpt2-medium"])
        self.health_check_interval = llm_settings.get('health_check_interval', 60)
        self.health_check_timeout = llm_settings.get('health_check_timeout', 5)
        
        # Performance metrics
        self.metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_latency': 0,
            'avg_latency': 0,
            'last_resource_usage': None
        }
        
        # Cache configuration
        self.cache_ttl = getattr(config_class, 'LLM_CACHE_TTL', 3600)  # 1 hour default
        self.cache = {}
        self.cache_timestamps = {}
        
        # Initialize health tracking
        self.health_status = {}
        self.last_health_check = {}
        
        # Verify connection with more graceful handling
        try:
            self.verify_connection()
        except Exception as e:
            logger.warning(f"Initial connection verification failed: {str(e)}")

    def _get_cache_key(self, prompt: str, **kwargs) -> str:
        """Generate a unique cache key based on prompt and parameters."""
        cache_dict = {'prompt': prompt, **kwargs}
        cache_str = json.dumps(cache_dict, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _update_metrics(self, latency: float, cache_hit: bool):
        """Update performance metrics."""
        self.metrics['total_requests'] += 1
        self.metrics['total_latency'] += latency
        self.metrics['avg_latency'] = self.metrics['total_latency'] / self.metrics['total_requests']
        
        if cache_hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1

    def _track_resource_usage(self):
        """Track system resource usage."""
        process = psutil.Process()
        self.metrics['last_resource_usage'] = {
            'memory_percent': process.memory_percent(),
            'cpu_percent': process.cpu_percent(),
            'threads': len(process.threads())
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Return current performance metrics."""
        self._track_resource_usage()
        return self.metrics

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid based on TTL."""
        if cache_key not in self.cache_timestamps:
            return False
        age = time.time() - self.cache_timestamps[cache_key]
        return age < self.cache_ttl

    def retry_with_fallback(func):
        """Decorator to implement retry logic with fallback models."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            
            # Try cache first
            if 'prompt' in kwargs:
                cache_key = self._get_cache_key(kwargs['prompt'], **kwargs)
                if cache_key in self.cache and self._is_cache_valid(cache_key):
                    latency = time.time() - start_time
                    self._update_metrics(latency, cache_hit=True)
                    return self.cache[cache_key]
            
            # If not in cache or cache invalid, proceed with actual request
            last_error = None
            
            # Try with current model
            for attempt in range(self.max_retries):
                try:
                    result = func(self, *args, **kwargs)
                    
                    # Cache the result
                    if 'prompt' in kwargs:
                        self.cache[cache_key] = result
                        self.cache_timestamps[cache_key] = time.time()
                    
                    latency = time.time() - start_time
                    self._update_metrics(latency, cache_hit=False)
                    return result
                    
                except (RequestException, ConnectionError) as e:
                    last_error = e
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(self.retry_delay * (2 ** attempt))
            
            # Try fallback models
            current_model_idx = self.fallback_models.index(self.config.model_name)
            for model in self.fallback_models[current_model_idx + 1:]:
                try:
                    logger.info(f"Attempting fallback to model: {model}")
                    self.switch_model(model_name=model)
                    result = func(self, *args, **kwargs)
                    
                    # Cache the result
                    if 'prompt' in kwargs:
                        self.cache[cache_key] = result
                        self.cache_timestamps[cache_key] = time.time()
                    
                    latency = time.time() - start_time
                    self._update_metrics(latency, cache_hit=False)
                    return result
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"Fallback to {model} failed: {str(e)}")
            
            # If all attempts fail, raise the last error
            raise last_error
        
        return wrapper

    def clear_cache(self):
        """Clear the response cache."""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Response cache cleared")

    def check_model_health(self, model_name: str) -> bool:
        """Check if a specific model is healthy and available."""
        try:
            # Check cache first
            now = datetime.now()
            if model_name in self.last_health_check:
                cache_age = (now - self.last_health_check[model_name]).total_seconds()
                if cache_age < self.health_check_interval:
                    return self.health_status.get(model_name, False)
            
            # Perform health check
            url = f"{self.config.endpoint_url}/health"
            response = requests.get(url, timeout=self.health_check_timeout)
            is_healthy = response.status_code == 200
            
            # Update cache
            self.health_status[model_name] = is_healthy
            self.last_health_check[model_name] = now
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"[ERROR] Health check failed for model {model_name}: {str(e)}")
            return False

    def verify_connection(self) -> bool:
        """Verify connection to LLM endpoint with improved error handling."""
        try:
            # First try a basic health check
            response = requests.get(f"{self.config.endpoint_url}/health", 
                                 timeout=self.health_check_timeout)
            if response.status_code == 200:
                logger.info("[INFO] Successfully connected to LLM endpoint")
                return True
                
            # If health check fails, try model info as fallback
            response = requests.get(f"{self.config.endpoint_url}/models",
                                 timeout=self.health_check_timeout)
            if response.status_code == 200:
                logger.info("[INFO] Successfully connected to LLM endpoint")
                return True
                
            # Both checks failed with non-200 status
            logger.error(f"Failed to connect to LLM endpoint. Status code: {response.status_code}")
            return False
            
        except RequestException as e:
            # Handle connection errors gracefully
            logger.warning(f"Connection verification failed: {str(e)}")
            return False

    @retry_with_fallback
    def infer(self, enhanced_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send inference request to local LLM endpoint with retry and fallback mechanisms.
        
        Args:
            enhanced_input: Dictionary containing prompt and context
            
        Returns:
            Dict[str, Any]: LLM response with status and metadata
        """
        try:
            # Prepare the request payload
            payload = {
                "model": self.config.model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that rephrases text in a natural way."},
                ]
            }
            
            # Add the user's query
            query = enhanced_input.get("prompt", enhanced_input.get("query", ""))
            if not query:
                raise ValueError("No prompt or query provided in input")
            
            payload["messages"].append({"role": "user", "content": query})
            
            # Add max tokens if configured
            if hasattr(self.config, 'max_tokens'):
                payload["max_tokens"] = self.config.max_tokens
                
            headers = {
                "Content-Type": "application/json"
            }
            
            # Send actual request to the LLM endpoint
            response = requests.post(
                f"{self.config.endpoint_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the actual response content
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                if not content:
                    raise ValueError("Empty response content from LLM")
                    
                return {
                    "response": content,
                    "status": "success",
                    "metadata": {
                        "model": result.get("model", self.config.model_name),
                        "usage": result.get("usage", {}),
                    }
                }
            else:
                logger.error(f"Unexpected LLM response format: {result}")
                raise ValueError("Invalid response format from LLM")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise ConnectionError(f"Failed to connect to LLM endpoint: {str(e)}")
        except Exception as e:
            logger.error(f"Error during inference: {str(e)}")
            raise

    def switch_model(self, endpoint: Optional[str] = None, model_name: Optional[str] = None) -> bool:
        """
        Switch to a different model or endpoint with health verification.
        
        Args:
            endpoint: New endpoint URL
            model_name: New model name
            
        Returns:
            bool: True if switch was successful
        """
        try:
            old_endpoint = self.config.endpoint_url
            old_model = self.config.model_name
            
            if endpoint:
                self.config.endpoint_url = endpoint
            if model_name:
                self.config.model_name = model_name
            
            # Verify the new configuration works
            if not self.check_model_health(self.config.model_name):
                # Try to find a healthy fallback model
                for model in self.fallback_models:
                    if self.check_model_health(model):
                        logger.info(f"Switching to healthy model: {model}")
                        self.switch_model(model_name=model)
                        return True
                raise ConnectionError("No healthy models available")
            
            logger.info(f"Successfully switched to model: {self.config.model_name} at {self.config.endpoint_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching model: {str(e)}")
            return False

    def generate_text(self, text: str, stream: bool = False, **kwargs) -> Any:
        """
        Generate text with optional streaming support.
        
        Args:
            text: Input text to process
            stream: If True, return a generator that yields response chunks
            **kwargs: Additional parameters for the model
            
        Returns:
            If stream=True: Generator yielding response chunks
            If stream=False: Complete response as a string
        """
        try:
            # Prepare the request payload
            payload = {
                "model": self.config.model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that rephrases text in a natural way."},
                    {"role": "user", "content": text}
                ],
                "stream": stream
            }
            
            # Add additional parameters
            if hasattr(self.config, 'max_tokens'):
                payload["max_tokens"] = kwargs.get('max_tokens', self.config.max_tokens)
            if 'temperature' in kwargs:
                payload["temperature"] = kwargs['temperature']
                
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if stream else "application/json"
            }
            
            # Send request to the LLM endpoint
            response = requests.post(
                f"{self.config.endpoint_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.config.timeout,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                def generate():
                    for line in response.iter_lines():
                        if line:
                            try:
                                # Remove 'data: ' prefix if present
                                line = line.decode('utf-8')
                                if line.startswith('data: '):
                                    line = line[6:]
                                if line == '[DONE]':
                                    break
                                    
                                # Parse the JSON response
                                chunk = json.loads(line)
                                if chunk and "choices" in chunk and len(chunk["choices"]) > 0:
                                    content = chunk["choices"][0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to decode JSON from chunk: {line}")
                            except Exception as e:
                                logger.error(f"Error processing chunk: {str(e)}")
                                
                return generate()
            else:
                result = response.json()
                if result and "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0].get("message", {}).get("content", "")
                else:
                    raise ValueError("Invalid response format from LLM")
                    
        except Exception as e:
            logger.error(f"Error in generate_text: {str(e)}")
            raise
