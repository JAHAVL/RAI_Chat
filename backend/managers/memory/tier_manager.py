# RAI_Chat/backend/managers/memory/tier_manager.py

import logging
import json
import re
from typing import Dict, Any, Optional, List, Union
import os
import time

try:
    # Local development import path
    from llm_client.llm_api import get_llm_api
except ImportError:
    # Docker container import path
    try:
        from llm_client.llm_api import get_llm_api
    except ImportError:
        # Define a fallback function if import fails
        def get_llm_api():
            logger.warning("Using fallback LLM API client")
            class FallbackLLMAPI:
                def generate_response(self, prompt, system_prompt=None):
                    return {"text": "LLM API not available. This is a fallback response."}
            return FallbackLLMAPI()

# Import database connection
from models.connection import get_db

logger = logging.getLogger(__name__)

class TierManager:
    """
    Manages the generation and processing of tiered content for messages.
    Creates different representation tiers for conversation history to optimize token usage.
    """
    
    def __init__(self):
        self.llm_api = get_llm_api()
        if not self.llm_api:
            logger.error("Failed to initialize LLM API client for TierManager")
        else:
            logger.info("TierManager initialized with LLM API client")
    
    def generate_tiers(self, message_content: str, role: str) -> Dict[str, str]:
        """
        Generate different tier representations for a message.
        
        Args:
            message_content: The original message content
            role: The role of the message sender (user or assistant)
            
        Returns:
            Dictionary with tier1_content, tier2_content, and the original content
        """
        # For user messages, we need to generate tier1 and tier2
        if role == "user":
            return self._generate_user_message_tiers(message_content)
        # For assistant messages, we need all three tiers
        elif role == "assistant":
            return self._generate_assistant_message_tiers(message_content)
        # For system messages, use default tiers
        else:
            return self._generate_system_message_tiers(message_content)
    
    def _generate_user_message_tiers(self, message_content: str) -> Dict[str, str]:
        """
        Generate tier1 (key-value) and tier2 (summary) for user messages.
        
        Args:
            message_content: The user's message
            
        Returns:
            Dictionary with tier1_content and tier2_content
        """
        tier_prompt = f"""
        Convert the following user message into two tiers of representation:
        
        Tier 1: Key-value pairs representing core information (e.g., user_name=Jordan, project=RAI_Chat)
        Tier 2: A brief 1-2 sentence summary capturing the essential meaning
        
        User message: {message_content}
        
        Output format:
        TIER1: key1=value1, key2=value2, ...
        TIER2: Brief summary here.
        """
        
        try:
            # Generate tiers using LLM
            result = self.llm_api.generate_response(tier_prompt)
            
            # Extract the response content
            if isinstance(result, dict) and "text" in result:
                generated_text = result["text"]
            elif isinstance(result, str):
                generated_text = result
            else:
                logger.warning(f"Unexpected response format from LLM: {type(result)}")
                return self._generate_fallback_tiers(message_content)
            
            # Parse the result to extract tiers
            tier1 = self._extract_section(generated_text, "TIER1:", "TIER2:")
            tier2 = self._extract_after_marker(generated_text, "TIER2:")
            
            # If parsing failed, use fallback
            if not tier1 or not tier2:
                logger.warning("Failed to parse tier content from LLM response")
                return self._generate_fallback_tiers(message_content)
            
            return {
                "tier1_content": tier1.strip(),
                "tier2_content": tier2.strip(),
                "content": message_content  # Original message as tier3
            }
            
        except Exception as e:
            logger.error(f"Error generating tiers for user message: {e}")
            return self._generate_fallback_tiers(message_content)
    
    def _generate_assistant_message_tiers(self, message_content: str) -> Dict[str, str]:
        """
        Handle assistant message tiers - may already be in tiered format.
        
        Args:
            message_content: The assistant's message or structured response
            
        Returns:
            Dictionary with all tier contents
        """
        # Check if the message is already in JSON format with tiers
        if isinstance(message_content, dict):
            # Extract from structured response if available
            if "response_tiers" in message_content:
                tiers = message_content["response_tiers"]
                return {
                    "tier1_content": tiers.get("tier1", ""),
                    "tier2_content": tiers.get("tier2", ""),
                    "content": tiers.get("tier3", message_content)  # Use tier3 or full message
                }
            # If it's a dict but doesn't have tiers, extract content first
            elif "content" in message_content:
                message_text = message_content["content"]
            else:
                # Just convert to string
                message_text = str(message_content)
        else:
            message_text = message_content
        
        # Generate tiers for the text content
        tier_prompt = f"""
        Convert the following assistant message into two concise representation tiers:
        
        Tier 1: Key points in key-value format (e.g., greeting=hello, information=project_details)
        Tier 2: A 1-2 sentence summary capturing the essential information
        
        Assistant message: {message_text}
        
        Output format:
        TIER1: key1=value1, key2=value2, ...
        TIER2: Brief summary here.
        """
        
        try:
            # Generate tiers using LLM
            result = self.llm_api.generate_response(tier_prompt)
            
            # Extract the response content
            if isinstance(result, dict) and "text" in result:
                generated_text = result["text"]
            elif isinstance(result, str):
                generated_text = result
            else:
                logger.warning(f"Unexpected response format from LLM: {type(result)}")
                return self._generate_fallback_tiers(message_text)
            
            # Parse the result to extract tiers
            tier1 = self._extract_section(generated_text, "TIER1:", "TIER2:")
            tier2 = self._extract_after_marker(generated_text, "TIER2:")
            
            # If parsing failed, use fallback
            if not tier1 or not tier2:
                logger.warning("Failed to parse tier content from LLM response")
                return self._generate_fallback_tiers(message_text)
            
            return {
                "tier1_content": tier1.strip(),
                "tier2_content": tier2.strip(),
                "content": message_text  # Original message
            }
            
        except Exception as e:
            logger.error(f"Error generating tiers for assistant message: {e}")
            return self._generate_fallback_tiers(message_text)
    
    def _generate_system_message_tiers(self, message_content: str) -> Dict[str, str]:
        """
        Generate simplified tiers for system messages.
        
        Args:
            message_content: The system message
            
        Returns:
            Dictionary with all tier contents
        """
        # For system messages, tier1 is just the action type if available
        tier1 = ""
        
        # Try to extract action type if it's a JSON
        try:
            if message_content.strip().startswith('{'):
                data = json.loads(message_content)
                if 'action' in data and 'status' in data:
                    tier1 = f"action={data['action']}, status={data['status']}"
        except:
            pass
        
        # If we couldn't extract a meaningful tier1, create a simple one
        if not tier1:
            tier1 = "message_type=system"
        
        # Tier2 is a short version of the content (first 50 chars)
        if isinstance(message_content, str):
            tier2 = message_content[:50] + "..." if len(message_content) > 50 else message_content
        else:
            tier2 = str(message_content)[:50] + "..." if len(str(message_content)) > 50 else str(message_content)
        
        return {
            "tier1_content": tier1,
            "tier2_content": tier2,
            "content": message_content
        }
    
    def _generate_fallback_tiers(self, message_content: str) -> Dict[str, str]:
        """
        Generate basic tiers when LLM generation fails.
        
        Args:
            message_content: The message content
            
        Returns:
            Dictionary with basic tier contents
        """
        # Create a simple key-value representation for tier1
        tier1 = "message=present"
        
        # For tier2, use the first sentence or truncate to 100 chars
        if isinstance(message_content, str):
            first_sentence_match = re.search(r'^(.*?[.!?])\s', message_content)
            if first_sentence_match:
                tier2 = first_sentence_match.group(1)
            else:
                tier2 = message_content[:100] + "..." if len(message_content) > 100 else message_content
        else:
            tier2 = str(message_content)[:100] + "..." if len(str(message_content)) > 100 else str(message_content)
        
        return {
            "tier1_content": tier1,
            "tier2_content": tier2,
            "content": message_content
        }
    
    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> Optional[str]:
        """
        Extract a section of text between two markers.
        
        Args:
            text: The text to search
            start_marker: Start marker
            end_marker: End marker
            
        Returns:
            The extracted content or None
        """
        try:
            # Use raw string for the regex pattern to avoid escape issues
            pattern = rf"{re.escape(start_marker)}\s*(.*?)\s*{re.escape(end_marker)}"
            match = re.search(pattern, text, re.DOTALL)
            
            if match:
                return match.group(1).strip()
            return None
        except Exception as e:
            logger.error(f"Error extracting section: {e}")
            return None
    
    def _extract_after_marker(self, text: str, marker: str) -> Optional[str]:
        """
        Extract text that follows a specific marker.
        
        Args:
            text: The text to search
            marker: The marker
            
        Returns:
            The extracted content or None
        """
        try:
            # Use raw string for the regex pattern to avoid escape issues
            pattern = rf"{re.escape(marker)}\s*(.*)"
            match = re.search(pattern, text, re.DOTALL)
            
            if match:
                return match.group(1).strip()
            return None
        except Exception as e:
            logger.error(f"Error extracting after marker: {e}")
            return None
