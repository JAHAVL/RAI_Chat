"""
LLM Engine API Client for RAI Chat

This module serves as the single entry point for all LLM Engine interactions.
All components should use this interface rather than directly calling the LLM Engine.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, Union, List

logger = logging.getLogger(__name__)

class LLMAPIClient:
    """
    Client for the LLM Engine API
    """
    
    def __init__(self):
        # Get LLM Engine URL from environment with Docker-friendly default
        self.llm_api_url = os.environ.get('LLM_API_URL', 'http://llm-engine:6101')
        self.default_engine = os.environ.get('DEFAULT_ENGINE', 'gemini_default')
        logger.info(f"Initializing LLM API client with URL: {self.llm_api_url}")
    
    def get_available_models(self) -> Dict[str, Any]:
        """
        Get a list of available models from the LLM Engine
        
        Returns:
            Dictionary containing model information
        """
        try:
            response = requests.get(f"{self.llm_api_url}/api/models")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get models. Status code: {response.status_code}")
                return {"error": True, "models": [], "message": f"Error: Status code {response.status_code}"}
        except Exception as e:
            logger.exception(f"Exception getting models: {str(e)}")
            return {"error": True, "models": [], "message": f"Error: {str(e)}"}
    
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, 
                     options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate text using the LLM Engine's /api/generate endpoint
        
        Args:
            prompt: The user's input
            system_prompt: Optional system instructions
            options: Additional parameters like temperature, max_tokens, etc.
            
        Returns:
            Dictionary containing the response text and metadata
        """
        try:
            # Prepare request data
            data = {
                "prompt": prompt,
                "system_prompt": system_prompt or ""
            }
            
            # Add any additional options
            if options:
                data.update(options)
            
            # Send request to LLM Engine API (no trailing slash, per standardization)
            response = requests.post(f"{self.llm_api_url}/api/generate", json=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"LLM API request failed with status code: {response.status_code}"
                logger.error(error_msg)
                return {
                    "response": f"Error: {error_msg}",
                    "error": True
                }
        except Exception as e:
            logger.exception(f"Exception in generate_text: {str(e)}")
            return {
                "response": f"Error connecting to LLM service: {str(e)}",
                "error": True
            }
    
    def chat_completion(self, messages: List[Dict[str, Any]], 
                       session_id: Optional[str] = None,
                       options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a chat completion using the LLM Engine's /api/chat/completions endpoint
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            session_id: Optional session ID for conversation context
            options: Additional parameters like temperature, max_tokens, etc.
            
        Returns:
            Dictionary containing the chat completion response and metadata
        """
        try:
            # Prepare request data
            data = {
                "messages": messages
            }
            
            # Add session_id if provided
            if session_id:
                data["session_id"] = session_id
                
            # Add any additional options
            if options:
                data.update(options)
            
            # Send request to LLM Engine API (no trailing slash, per standardization)
            response = requests.post(f"{self.llm_api_url}/api/chat/completions", json=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"LLM API chat completion request failed with status code: {response.status_code}"
                logger.error(error_msg)
                return {
                    "response": f"Error: {error_msg}",
                    "error": True
                }
        except Exception as e:
            logger.exception(f"Exception in chat_completion: {str(e)}")
            return {
                "response": f"Error connecting to LLM service: {str(e)}",
                "error": True
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if the LLM Engine is healthy
        
        Returns:
            Dictionary containing health status
        """
        try:
            response = requests.get(f"{self.llm_api_url}/api/health")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"LLM Engine health check failed with status code: {response.status_code}")
                return {"status": "error", "message": f"Health check failed: {response.status_code}"}
        except Exception as e:
            logger.exception(f"Exception in health_check: {str(e)}")
            return {"status": "error", "message": f"Health check exception: {str(e)}"}

# Singleton instance for the LLM API client
_llm_api_client = None

def get_llm_api():
    """
    Get the singleton instance of the LLM API client
    
    Returns:
        LLMAPIClient instance
    """
    global _llm_api_client
    if _llm_api_client is None:
        _llm_api_client = LLMAPIClient()
    return _llm_api_client
