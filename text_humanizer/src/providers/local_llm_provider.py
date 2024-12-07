"""
Implementation of local LLM provider.
Handles communication with a locally hosted LLM endpoint.
"""

import json
import logging
from typing import Dict, Any, Optional
import requests
from requests.exceptions import RequestException

from text_humanizer.src.providers.base_llm_provider import BaseLLMProvider, LLMConfig
from text_humanizer.src.utils.logger import logger

class LocalLLMProvider(BaseLLMProvider):
    """Provider for interacting with local LLM endpoint."""
    
    def __init__(self, endpoint_url: str = "http://127.0.0.1:1234/v1/chat/completions",
                 model_name: str = "internlm2_5-20b-chat"):
        config = LLMConfig(endpoint_url=endpoint_url, model_name=model_name)
        super().__init__(config)
        self.verify_connection()
        
    def verify_connection(self) -> bool:
        """Verify connection to LLM endpoint by checking models endpoint."""
        try:
            base_url = self.config.endpoint_url.rsplit('/', 2)[0]  # Remove 'chat/completions'
            models_url = f"{base_url}/models"
            response = requests.get(models_url, timeout=5)
            response.raise_for_status()
            logger.info("Successfully connected to LLM endpoint")
            return True
        except RequestException as e:
            logger.error(f"Failed to connect to LLM endpoint: {str(e)}")
            raise ConnectionError(f"Cannot connect to LLM endpoint at {self.config.endpoint_url}")
        
    def infer(self, enhanced_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send inference request to local LLM endpoint.
        
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
                    {"role": "system", "content": enhanced_input.get("system_prompt", "You are a helpful assistant.")},
                    {"role": "user", "content": enhanced_input["prompt"]}
                ],
                "max_tokens": self.config.max_tokens
            }
            headers = {
                "Content-Type": "application/json"
            }
            
            # Send actual request to the LLM endpoint
            response = requests.post(
                self.config.endpoint_url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the actual response content
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                return {
                    "response": content,
                    "status": "success",
                    "metadata": {
                        "model": result.get("model", self.config.model_name),
                        "usage": result.get("usage", {}),
                    }
                }
            else:
                raise ValueError("Invalid response format from LLM")
                
        except RequestException as e:
            logger.error(f"LLM request failed: {str(e)}")
            return {
                "response": "Error: Failed to communicate with LLM service",
                "status": "error",
                "metadata": {"error": str(e)}
            }
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Failed to process LLM response: {str(e)}")
            return {
                "response": "Error: Invalid response from LLM service",
                "status": "error",
                "metadata": {"error": str(e)}
            }
    
    def switch_model(self, endpoint: Optional[str] = None, model_name: Optional[str] = None) -> bool:
        """
        Switch to a different model or endpoint.
        
        Args:
            endpoint: New endpoint URL
            model_name: New model name
            
        Returns:
            bool: True if switch was successful
        """
        try:
            if endpoint:
                self.config.endpoint_url = endpoint
            if model_name:
                self.config.model_name = model_name
                
            # MOCK: Verify connection - in production, would make a test request
            logger.info(f"Switched to model: {self.config.model_name} at {self.config.endpoint_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error switching model: {str(e)}")
            return False
