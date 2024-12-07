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

from text_humanizer.providers.base_llm_provider import BaseLLMProvider
from text_humanizer.utils.logger import logger
from text_humanizer.config.model_config import ModelConfigs, ModelType, ModelConfig

class LocalLLMProvider(BaseLLMProvider):
    """Provider for interacting with local LLM endpoint with fallback and retry mechanisms."""
    
    def __init__(self, model_type: ModelType = ModelType.CHAT):
        """Initialize the provider with configuration."""
        self.model_type = model_type
        self.config = ModelConfigs.get_config(model_type)
        self.system_prompt = ModelConfigs.get_system_prompt(model_type)
        
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
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 3600  # 1 hour default
        
        # Health tracking
        self.health_status = {}
        self.last_health_check = {}
        self.health_check_interval = 60
        self.health_check_timeout = 5
        self.max_retries = 3
        self.retry_delay = 1
        
        # Verify connection
        try:
            self.verify_connection()
        except Exception as e:
            logger.warning(f"Initial connection verification failed: {str(e)}")
            
    def configure(self, model_type: ModelType, **kwargs) -> None:
        """
        Configure the provider for a different model type or update settings.
        
        Args:
            model_type: The type of model to configure for
            **kwargs: Additional configuration parameters
        """
        self.model_type = model_type
        self.config = ModelConfigs.get_config(model_type)
        self.system_prompt = ModelConfigs.get_system_prompt(model_type)
        
        # Update config with any provided kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                
        logger.info(f"Configured provider for {model_type.value} with {kwargs}")
        
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
            current_model_idx = ModelConfigs.get_fallback_models(self.model_type).index(self.config.model_name)
            for model in ModelConfigs.get_fallback_models(self.model_type)[current_model_idx + 1:]:
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

    def verify_connection(self):
        """Verify connection to LLM endpoint with improved error handling."""
        try:
            # Check if endpoint is reachable by getting available models
            url = f"{self.config.endpoint_url}/v1/models"
            response = requests.get(url, timeout=self.health_check_timeout)
            response.raise_for_status()
            
            # Update health status
            self.health_status[self.config.model_name] = True
            self.last_health_check[self.config.model_name] = datetime.now()
            
            logger.info("[INFO] Successfully connected to LLM endpoint")
            return True
            
        except RequestException as e:
            self.health_status[self.config.model_name] = False
            logger.error(f"Error verifying connection: {str(e)}")
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
                for model in ModelConfigs.get_fallback_models(self.model_type):
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
            messages = []
            
            # Add system prompt
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
            
            # Add context if available
            if "context" in enhanced_input:
                for ctx in enhanced_input["context"]:
                    messages.append({
                        "role": "assistant",
                        "content": ctx
                    })
            
            # Add the user's query
            query = enhanced_input.get("prompt", enhanced_input.get("query", ""))
            if not query:
                raise ValueError("No prompt or query provided in input")
            
            messages.append({
                "role": "user",
                "content": query
            })
            
            # Prepare the complete payload
            payload = {
                "model": self.config.model_name,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Send request to the LLM endpoint
            response = requests.post(
                f"{self.config.endpoint_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the response content
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                if not content:
                    raise ValueError("Empty response content from LLM")
                
                # Parse the response based on model type
                if self.model_type in [ModelType.HUMANIZE, ModelType.SEARCH]:
                    try:
                        parsed_content = json.loads(content)
                        response_data = parsed_content
                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON response")
                        response_data = {"error": "Invalid JSON response"}
                else:
                    response_data = {"text": content}
                
                return {
                    "response": response_data,
                    "status": "success",
                    "metadata": {
                        "model": result.get("model", self.config.model_name),
                        "usage": result.get("usage", {}),
                        "model_type": self.model_type.value
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

    @retry_with_fallback
    def generate(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Generate chat completion response.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            stream: If True, return a generator that yields response chunks
            **kwargs: Additional parameters for the model
            
        Returns:
            If stream=True: Generator yielding response chunks
            If stream=False: Complete response as a dictionary
        """
        # Prepare the request
        if not messages[0].get('role') == 'system':
            messages.insert(0, {
                'role': 'system',
                'content': self.system_prompt
            })
            
        url = f"{self.config.endpoint_url}/v1/chat/completions"
        headers = {'Content-Type': 'application/json'}
        
        data = {
            'model': self.config.model_name,
            'messages': messages,
            'temperature': kwargs.get('temperature', self.config.temperature),
            'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
            'stream': stream
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=stream, timeout=self.config.timeout)
            response.raise_for_status()
            
            if stream:
                def generate_chunks():
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line.decode('utf-8').removeprefix('data: '))
                                if 'error' in chunk:
                                    raise Exception(f"Error from LLM: {chunk['error']}")
                                if chunk.get('choices', [{}])[0].get('delta', {}).get('content'):
                                    yield chunk['choices'][0]['delta']['content']
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to decode JSON from chunk: {line}")
                            except Exception as e:
                                logger.error(f"Error processing chunk: {str(e)}")
                                raise
                return generate_chunks()
            else:
                result = response.json()
                if 'error' in result:
                    raise Exception(f"Error from LLM: {result['error']}")
                
                # Handle different response formats
                try:
                    if 'choices' in result and result['choices']:
                        choice = result['choices'][0]
                        if 'message' in choice:
                            return {
                                'content': choice['message'].get('content', ''),
                                'role': choice['message'].get('role', 'assistant'),
                                'finish_reason': choice.get('finish_reason', 'stop')
                            }
                        elif 'text' in choice:
                            return {
                                'content': choice['text'],
                                'role': 'assistant',
                                'finish_reason': choice.get('finish_reason', 'stop')
                            }
                    raise ValueError("Unexpected response format from LLM")
                except (KeyError, IndexError) as e:
                    logger.error(f"Error parsing LLM response: {str(e)}, Response: {result}")
                    raise ValueError(f"Invalid response format from LLM: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in generate: {str(e)}")
            raise

    @retry_with_fallback
    def generate_text(self, text: str, stream: bool = False, **kwargs) -> Any:
        """
        Generate text completion using chat endpoint for consistency.
        
        Args:
            text: Input text to process
            stream: If True, return a generator that yields response chunks
            **kwargs: Additional parameters for the model
            
        Returns:
            If stream=True: Generator yielding response chunks
            If stream=False: Complete response as a string
        """
        messages = [{'role': 'user', 'content': text}]
        response = self.generate(messages, stream=stream, **kwargs)
        
        if stream:
            return response
        else:
            return response['content']
