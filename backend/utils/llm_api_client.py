"""
LLM API Client for RAI Chat
Provides a consistent interface to communicate with the standalone LLM Engine via HTTP
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class LLMAPIClient:
    """
    HTTP client for communicating with the standalone LLM Engine
    """
    
    def __init__(self):
        # Get the LLM Engine URL from environment variables with a Docker-friendly default
        self.llm_api_url = os.environ.get('LLM_API_URL', 'http://llm-engine:6101')
        logger.info(f"Initializing LLM API client with URL: {self.llm_api_url}")
    
    def generate_response(self, prompt: str, system_message: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a response from the LLM Engine API using the /api/generate endpoint
        
        Args:
            prompt: The user's message to send to the LLM
            system_message: Optional system instructions 
            options: Optional parameters like temperature, max_tokens, etc.
            
        Returns:
            Dict containing the LLM's response and any additional data
        """
        try:
            # Prepare the request data
            data = {
                "prompt": prompt,
                "system_prompt": system_message or ""
            }
            
            # Add any additional options
            if options:
                data.update(options)
            
            # Use the /api/generate endpoint without trailing slash per API requirements
            response = requests.post(f"{self.llm_api_url}/api/generate", json=data)
            
            # Check if the request was successful
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"LLM API request failed with status code: {response.status_code}")
                return {
                    "response": f"Error: LLM API request failed with status code {response.status_code}",
                    "error": True
                }
        
        except Exception as e:
            logger.error(f"Error generating response from LLM API: {str(e)}")
            return {
                "response": f"Error connecting to LLM service: {str(e)}",
                "error": True
            }
    
    def chat_completion(self, messages: list, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a chat completion from the LLM Engine API using the /api/chat/completions endpoint
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            options: Optional parameters like temperature, max_tokens, etc.
            
        Returns:
            Dict containing the LLM's response and any additional data
        """
        try:
            # Prepare the request data
            data = {
                "messages": messages
            }
            
            # Add any additional options
            if options:
                data.update(options)
            
            # Use the /api/chat/completions endpoint without trailing slash per API requirements
            response = requests.post(f"{self.llm_api_url}/api/chat/completions", json=data)
            
            # Check if the request was successful
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"LLM API chat completion request failed with status code: {response.status_code}")
                return {
                    "response": f"Error: LLM API request failed with status code {response.status_code}",
                    "error": True
                }
        
        except Exception as e:
            logger.error(f"Error generating chat completion from LLM API: {str(e)}")
            return {
                "response": f"Error connecting to LLM service: {str(e)}",
                "error": True
            }

# Singleton instance
_llm_api_client = None

def get_llm_api():
    """Get the LLM API client instance"""
    global _llm_api_client
    if _llm_api_client is None:
        _llm_api_client = LLMAPIClient()
    return _llm_api_client

# For backward compatibility
def get_llm_engine():
    """Alias for get_llm_api() to maintain backward compatibility"""
    return get_llm_api()
