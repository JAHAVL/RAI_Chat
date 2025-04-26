import json
import time
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Generator

class ResponseProcessor:
    """
    Handles the processing and streaming of conversation responses.
    Manages response formatting, chunking, and error handling.
    """
    
    def __init__(self, logger=None, llm_api=None, action_handler=None, contextual_memory=None):
        """
        Initialize the ResponseProcessor.
        
        Args:
            logger: Logger instance
            llm_api: API client for the language model
            action_handler: Handler for processing actions in responses
            contextual_memory: Memory management for storing responses
        """
        self.logger = logger or logging.getLogger(__name__)
        self.llm_api = llm_api
        self.action_handler = action_handler
        self.contextual_memory = contextual_memory
        
    def generate_response(self, user_input: str, system_prompt: str, context: Dict[str, Any], 
                     session_id: str, user_id: str) -> Generator[Dict[str, Any], None, None]:
        """
        Generate a response from the LLM and process it incrementally.
        
        Args:
            user_input: The user's message
            system_prompt: System prompt to provide to the LLM
            context: Conversation context including history and facts
            session_id: Current session ID
            user_id: User ID
            
        Yields:
            Processed response chunks
        """
        if not self.llm_api:
            error_msg = "No LLM API available"
            self.logger.error(error_msg)
            yield {
                'type': 'error',
                'content': error_msg,
                'timestamp': datetime.now().isoformat()
            }
            return
        
        try:
            # Get the response from the LLM
            llm_response = self.llm_api.generate_response(user_input, system_prompt)
            
            # Log the raw response for debugging
            self.logger.debug(f"Raw LLM response: {json.dumps(llm_response) if isinstance(llm_response, dict) else llm_response}")
            
            # Handle direct action signals ([SEARCH:query] format without JSON wrapping)
            if isinstance(llm_response, str) and llm_response.strip().startswith('[') and (':' in llm_response):
                # This looks like a direct action signal
                self.logger.info(f"Detected direct action signal format: {llm_response}")
                
                # For direct action signals, we need to check if it's a valid action
                if '[SEARCH:' in llm_response or '[WEB_SEARCH:' in llm_response:
                    # Directly pass it to the action handler
                    if self.action_handler:
                        action_signal, action_result, action_type = self.action_handler.process_llm_response(
                            session_id=session_id,
                            user_input=user_input,
                            response_data=llm_response  # Pass the raw string
                        )
                        
                        # The action handler should take care of everything for direct actions
                        # We'll just yield empty content since the action handler will generate the appropriate response
                        return
            
            # Process for special action signals
            if self.action_handler:
                action_signal, action_result, action_type = self.action_handler.process_llm_response(
                    session_id=session_id,
                    user_input=user_input,
                    response_data=llm_response
                )
                
                if action_signal:
                    self.logger.info(f"Detected action signal: {action_type}")
                    
                    # Handle ACTION_BREAK (interrupting actions like REQUEST_TIER)
                    if action_signal == "ACTION_BREAK":
                        self.logger.info(f"Received ACTION_BREAK for action type: {action_type}")
                        
                        # Add a brief delay to allow any processing to complete
                        time.sleep(1)
                        
                        # For tier requests, we need to make sure facts are present in the follow-up
                        if "REQUEST_TIER" in action_type:
                            # Extract tier info if available
                            tier_info = re.search(r'\[REQUEST_TIER:(\d+):([^\]]+)\]', action_result)
                            if tier_info:
                                tier_level = tier_info.group(1)
                                content_request = tier_info.group(2)
                                self.logger.info(f"REQUEST_TIER detected - tier: {tier_level}, content: {content_request}")
                        
                        # Explicitly load remembered facts
                        remembered_facts = ""
                        if self.contextual_memory:
                            remembered_facts = self.contextual_memory.get_remember_this_content()
                            self.logger.info(f"Loaded remembered facts for follow-up: {remembered_facts[:100]}...")
                        
                        # Generate a new response with enhanced system prompt that includes the facts
                        new_system_prompt = f"{system_prompt}\n\nIMPORTANT: Previous request required additional information."
                        
                        # Make sure remembered facts are prominently included
                        if remembered_facts:
                            # Add debug logging to confirm facts are properly retrieved
                            self.logger.info(f"Memory facts being included for follow-up: {remembered_facts}")
                            new_system_prompt += f"\n\nREMEMBER_THIS (CRITICAL - READ CAREFULLY):\n{remembered_facts}"
                        
                        self.logger.info("Generating new response after ACTION_BREAK with enhanced memory context")
                        
                        # Make a new API call with updated context
                        new_llm_response = self.llm_api.generate_response(user_input, new_system_prompt)
                        
                        # Extract the actual content string from the new response
                        content_to_return = self._extract_content_from_response(new_llm_response)
                        content_to_return = self._final_cleanup(content_to_return)
                        
                        # Return the new response
                        for chunk in self._chunk_response(content_to_return):
                            if isinstance(chunk, str):
                                # First remove all action signals from output (more aggressive approach)
                                chunk = self._final_cleanup(chunk)
                            
                            yield {
                                'type': 'assistant',
                                'content': chunk,
                                'timestamp': datetime.now().isoformat()
                            }
                        return  # Exit the generator
                    
                    # Handle failed actions
                    if not action_result:
                        error_msg = f"Failed to execute action: {action_type}"
                        self.logger.error(error_msg)
                        yield {
                            'type': 'error',
                            'content': error_msg,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Retry with a more explicit system prompt
                        retry_system_prompt = f"{system_prompt}\n\nIMPORTANT: Previous attempt to {action_type} failed. Please respond normally without requiring any special actions."
                        self.logger.info("Retrying with modified system prompt after action failure")
                        
                        time.sleep(1)
                        
                        # Retry LLM API call
                        llm_response = self.llm_api.generate_response(user_input, retry_system_prompt)
                        
                        # Process the retried response
                        action_signal, action_result, action_type = self.action_handler.process_llm_response(
                            session_id=session_id,
                            user_input=user_input,
                            response_data=llm_response
                        )
                        
                        if action_signal:
                            self.logger.warning("Still getting action signal after retry, proceeding with best effort")
            
            # Store the assistant's response
            self._store_assistant_response(llm_response, session_id)
            
            # Extract the actual content string from the response
            content_to_return = self._extract_content_from_response(llm_response)
            
            # Apply final cleanup to remove action signals
            content_to_return = self._final_cleanup(content_to_return)
            
            # Return response in chunks
            for chunk in self._chunk_response(content_to_return):
                yield {
                    'type': 'assistant',
                    'content': chunk,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}", exc_info=True)
            yield {
                'type': 'error',
                'content': f"Error generating response: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _extract_content_from_response(self, response_data) -> str:
        """
        Extract clean content string from potentially complex response object.
        
        Args:
            response_data: The response data from LLM, could be string, dict, or other
            
        Returns:
            Clean content string for frontend display
        """
        content = ""
        
        try:
            # Log the raw response for debugging
            if isinstance(response_data, dict):
                self.logger.info(f"Processing response: {str(response_data)[:200]}...")
            elif isinstance(response_data, str):
                self.logger.info(f"Processing response string: {response_data[:200]}...")
            else:
                self.logger.info(f"Processing response type: {type(response_data)}")
                
            # CASE 1: Special flags for fallback and error responses
            if isinstance(response_data, dict):
                # Critical error flag - always prioritize this check
                if response_data.get("_fallback_error_message", False):
                    self.logger.warning("CRITICAL ERROR: LLM Engine not available - displaying error message to user")
                    return " SYSTEM ERROR: " + response_data.get("response", "LLM Engine unavailable.")
                    
                # Regular fallback check
                if response_data.get("is_fallback", False):
                    self.logger.warning("Detected fallback response - LLM engine not available")
                    return " SYSTEM MESSAGE: " + response_data.get("response", "LLM Engine unavailable.")
                
            # CASE 2: Direct dictionary with proper tier structure - most reliable method
            if isinstance(response_data, dict):
                # Direct access to llm_response structure
                if "llm_response" in response_data:
                    llm_resp = response_data["llm_response"]
                    # Tiered response format
                    if isinstance(llm_resp, dict) and "response_tiers" in llm_resp:
                        tiers = llm_resp["response_tiers"]
                        if "tier3" in tiers and tiers["tier3"]:
                            content = tiers["tier3"]
                            self.logger.info(f"Directly extracted tier3 content from structured response (length: {len(content)})")
                            # Ensure proper newlines and return immediately
                            return content.replace("\\n", "\n")
                
                # DockerLLMAPI cleaned response with text field
                if response_data.get("cleaned", False) and "text" in response_data:
                    text_content = response_data["text"]
                    self.logger.info(f"Using cleaned text from DockerLLMAPI (length: {len(text_content)})")
                    # Replace escaped newlines
                    text_content = text_content.replace("\\n", "\n")
                    
                    # If text content contains JSON, check if it's our tier structure
                    if (text_content.strip().startswith('{') or "```json" in text_content) and ('"tier3"' in text_content or '"response_tiers"' in text_content):
                        self.logger.info("Detected JSON format in cleaned response - attempting to extract tier3")
                        try:
                            # Clean up any markdown code block markers
                            cleaned_text = text_content
                            if "```json" in cleaned_text:
                                cleaned_text = cleaned_text.replace("```json", "").replace("```", "").strip()
                            
                            # Extract JSON part if necessary
                            import re
                            json_match = re.search(r'(\{.*\})', cleaned_text, re.DOTALL)
                            if json_match:
                                cleaned_text = json_match.group(1).strip()
                            
                            import json
                            json_data = json.loads(cleaned_text)
                            
                            # Extract from the tiered structure
                            if "llm_response" in json_data and "response_tiers" in json_data["llm_response"]:
                                tiers = json_data["llm_response"]["response_tiers"]
                                if "tier3" in tiers and tiers["tier3"]:
                                    content = tiers["tier3"]
                                    # Ensure proper newlines
                                    return content.replace("\\n", "\n")
                        except Exception as e:
                            self.logger.error(f"Failed to parse JSON from cleaned text: {e}")
                            # Fall through to use the original text_content
                    
                    # If not JSON or JSON parsing failed, just return the text content
                    return text_content
            
            # CASE 3: String that contains JSON in markdown code blocks
            if isinstance(response_data, str) and ("```json" in response_data or response_data.strip().startswith('{')):
                self.logger.info("Attempting to extract JSON from string response")
                try:
                    # Extract JSON from code blocks if present
                    import re
                    json_str = response_data
                    
                    # Handle markdown code blocks
                    json_block_match = re.search(r'```json\s*({.*?})\s*```', response_data, re.DOTALL)
                    if json_block_match:
                        json_str = json_block_match.group(1)
                    elif response_data.strip().startswith('{') and response_data.strip().endswith('}'):
                        json_str = response_data
                    
                    # Parse the JSON
                    import json
                    json_data = json.loads(json_str)
                    
                    # Check for tiered structure
                    if "llm_response" in json_data and "response_tiers" in json_data["llm_response"]:
                        tiers = json_data["llm_response"]["response_tiers"]
                        if "tier3" in tiers and tiers["tier3"]:
                            content = tiers["tier3"]
                            self.logger.info(f"Extracted tier3 from JSON string (length: {len(content)})")
                            return content.replace("\\n", "\n")
                except Exception as e:
                    self.logger.warning(f"Failed to extract JSON from string: {e}")
                    # Fall through to traditional extraction methods
            
            # CASE 4: Fallback to traditional extraction methods
            # Handle different response formats (fallback to existing methods)
            if response_data is None:
                content = "I'm sorry, but I couldn't generate a response at this time."
            elif isinstance(response_data, str):
                # Direct string response
                content = response_data
            elif isinstance(response_data, dict):
                # Try various common key patterns
                if "response" in response_data:
                    content = response_data["response"]
                elif "text" in response_data:
                    content = response_data["text"]
                elif "content" in response_data:
                    content = response_data["content"]
                elif len(response_data) > 0:
                    # Just take the first key's value as a fallback
                    first_key = list(response_data.keys())[0]
                    content = str(response_data[first_key])
                
            # Make sure we actually have content
            if not content:
                content = "I'm sorry, but I couldn't generate a meaningful response."
                self.logger.warning("No content extracted from response")
                
            # If content is a dict or other object, convert to JSON string
            if not isinstance(content, str):
                self.logger.warning(f"Content is not a string, converting from {type(content)}")
                content = json.dumps(content)
                
            # Apply minimal cleanup - just fix newlines and trailing JSON fragments
            content = content.replace("\\n", "\n")
            
            # Only remove trailing JSON fragments that are clearly not part of content
            import re
            content = re.sub(r'\s*[\}\]\)]{3,}\s*$', '', content)
                
            return content
                
        except Exception as e:
            self.logger.error(f"Error extracting content from response: {str(e)}", exc_info=True)
            return "I encountered an error processing the response."
    
    def _final_cleanup(self, content: str) -> str:
        """
        Apply final cleanup to response content before sending to frontend.
        
        Args:
            content: Raw content string
            
        Returns:
            Cleaned content string
        """
        if not content:
            return content
            
        # Log the content before cleaning for debugging
        self.logger.debug(f"Cleaning content (first 100 chars): {content[:100]}...")
        
        # More aggressive pattern to catch all action signals - use lookahead to handle nested brackets
        cleaned_content = re.sub(r'\[(REQUEST_TIER|SEARCH|WEB_SEARCH|REMEMBER|FORGET_THIS|CORRECT|CALCULATE|COMMAND|EXECUTE|SEARCH_EPISODIC)[^\]]*\]', '', content)
        
        # Additional cleanup for any missed action signals with more complex structure
        action_patterns = [
            r'\[REQUEST_TIER:[^\]]+\]',
            r'\[SEARCH:[^\]]+\]',
            r'\[WEB_SEARCH:[^\]]+\]',
            r'\[REMEMBER:[^\]]+\]',
            r'\[FORGET_THIS:[^\]]+\]',
            r'\[CORRECT:[^\]]+:[^\]]+\]',
            r'\[CALCULATE:[^\]]+\]',
            r'\[COMMAND:[^\]]+\]',
            r'\[EXECUTE:[^\]]+\]',
            r'\[SEARCH_EPISODIC:[^\]]+\]'
        ]
        
        # Apply each pattern individually for maximum coverage
        for pattern in action_patterns:
            cleaned_content = re.sub(pattern, '', cleaned_content)
        
        # Clean up any extra whitespace resulting from removals
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content)
        cleaned_content = cleaned_content.strip()
        
        # Log the content after cleaning for debugging
        self.logger.debug(f"Content after cleaning (first 100 chars): {cleaned_content[:100]}...")
        
        return cleaned_content
    
    def _store_assistant_response(self, response: str, session_id: str) -> None:
        """
        Store the assistant's response in the memory system.
        
        Args:
            response: The assistant's response
            session_id: The session ID
        """
        if not self.contextual_memory:
            return
            
        try:
            # In the updated memory manager, we use process_user_message for both 
            # user and assistant messages - the role is determined in the message object
            # The message is already extracted within the process_user_message method
            self.contextual_memory.process_user_message(session_id, response)
            self.logger.debug(f"Stored assistant response in memory for session {session_id}")
            
            # Note: fact extraction is now handled within the process_user_message method
            # so we don't need the separate extract_and_store_facts call
            
        except Exception as e:
            self.logger.error(f"Error storing assistant response: {str(e)}", exc_info=True)
    
    def _chunk_response(self, response: str, chunk_size: int = 500) -> Generator[str, None, None]:
        """
        Return the response as a single chunk for display.
        
        Args:
            response: The complete response
            chunk_size: Not used, kept for backward compatibility
            
        Yields:
            The complete response as a single chunk
        """
        yield response