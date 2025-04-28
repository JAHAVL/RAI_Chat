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
            # Log the full system prompt for debugging
            self.logger.info("===== FULL SYSTEM PROMPT WITH CONTEXTUAL MEMORY =====")
            self.logger.info(system_prompt)
            self.logger.info("===== END OF FULL SYSTEM PROMPT =====")
            
            # Write the full prompt to a debug file for easier analysis
            try:
                debug_path = "/app/logs/full_prompt_debug.txt"
                with open(debug_path, "w") as f:
                    f.write("===== FULL SYSTEM PROMPT =====\n")
                    f.write(system_prompt)
                    f.write("\n\n===== CONTEXT INFO =====\n")
                    f.write(json.dumps(context, indent=2))
                    f.write("\n\n===== USER INPUT =====\n")
                    f.write(user_input)
                self.logger.info(f"Full prompt and context written to {debug_path}")
                
                # Create a timestamped log file in the system_prompt_logs directory
                import os
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_dir = "/app/logs/system_prompt_logs"
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, f"system_prompt_{timestamp}.log")
                with open(log_file, "w") as f:
                    f.write("===== FULL SYSTEM PROMPT =====\n")
                    f.write(system_prompt)
                    f.write("\n\n===== CONTEXT INFO =====\n")
                    f.write(json.dumps(context, indent=2))
                    f.write("\n\n===== USER INPUT =====\n")
                    f.write(user_input)
                self.logger.info(f"System prompt log created at {log_file}")
                
                # Also create a timestamped log file in the local system_prompt_logs directory
                local_log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../backend/logs/system_prompt_logs"))
                os.makedirs(local_log_dir, exist_ok=True)
                local_log_file = os.path.join(local_log_dir, f"system_prompt_{timestamp}.log")
                with open(local_log_file, "w") as f:
                    f.write("===== FULL SYSTEM PROMPT =====\n")
                    f.write(system_prompt)
                    f.write("\n\n===== CONTEXT INFO =====\n")
                    f.write(json.dumps(context, indent=2))
                    f.write("\n\n===== USER INPUT =====\n")
                    f.write(user_input)
                self.logger.info(f"Local system prompt log created at {local_log_file}")
                
                # Also write to current_llm_prompt.md in the project root for easier viewing
                try:
                    import os
                    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
                    md_path = os.path.join(root_path, "current_llm_prompt.md")
                    with open(md_path, "w") as f:
                        f.write(system_prompt)
                    self.logger.info(f"Current LLM prompt written to {md_path}")
                except Exception as md_err:
                    self.logger.error(f"Error writing to current_llm_prompt.md: {md_err}")
            except Exception as e:
                self.logger.error(f"Error writing debug file: {e}")
            
            # Get the response from the LLM
            llm_response = self.llm_api.generate_response(user_input, system_prompt)
            
            # Log the raw response for debugging
            self.logger.debug(f"Raw LLM response: {json.dumps(llm_response) if isinstance(llm_response, dict) else llm_response}")
            
            # Process any special instructions like UPGRADE_MESSAGE requests
            llm_response = self.process_response(llm_response, user_input, session_id)
            
            # Check for error flags or messages in the response
            if isinstance(llm_response, dict) and ('error' in llm_response or '_error' in llm_response or 'error_message' in llm_response):
                error_msg = llm_response.get('error') or llm_response.get('_error') or llm_response.get('error_message', "Unknown API error")
                self.logger.error(f"LLM API returned an error: {error_msg}")
                
                # Format a user-friendly error message
                user_friendly_error = self._format_user_friendly_error(error_msg)
                
                yield {
                    'type': 'error',
                    'content': user_friendly_error,
                    'timestamp': datetime.now().isoformat()
                }
                return
                
            # Check for string error messages that might contain specific error phrases
            if isinstance(llm_response, str) and (
                'error with the' in llm_response.lower() or 
                'api error' in llm_response.lower() or
                'finish_reason' in llm_response.lower() or
                'copyrighted material' in llm_response.lower()
            ):
                self.logger.error(f"Detected error message in LLM response: {llm_response[:100]}...")
                
                # Format a user-friendly error message
                user_friendly_error = self._format_user_friendly_error(llm_response)
                
                yield {
                    'type': 'error',
                    'content': user_friendly_error,
                    'timestamp': datetime.now().isoformat()
                }
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
                        
                        # For web search requests, generate a follow-up response after search is complete
                        if "SEARCH" in action_type:
                            self.logger.info(f"Web search detected - checking for results and generating follow-up")
                            
                            # Update context with latest information
                            updated_context = context.copy()
                            
                            # Get the latest remembered facts
                            if self.contextual_memory:
                                remembered_facts = self.contextual_memory.get_remember_this_content()
                                updated_context["remembered_facts"] = remembered_facts
                                
                            # Delay to allow search to complete
                            time.sleep(2)
                            
                            # Check if we have web search results in the context
                            web_search_results = self.contextual_memory.get_web_search_results(session_id)
                            if web_search_results:
                                updated_context["web_search_results"] = web_search_results
                                self.logger.info("Web search results found, generating follow-up response")
                                
                                # Generate a follow-up response with the updated context
                                follow_up_prompt = system_prompt + "\n\nIMPORTANT: Web search has been completed for this query. Use the search results to formulate your response."
                                
                                follow_up_response = self.llm_api.generate_response(
                                    user_input, 
                                    follow_up_prompt,
                                    updated_context
                                )
                                
                                # Extract and yield the follow-up response content
                                extracted_content = self._extract_content_from_response(follow_up_response)
                                cleaned_content = self._final_cleanup(extracted_content)
                                
                                yield {
                                    'type': 'final',
                                    'content': cleaned_content,
                                    'timestamp': datetime.now().isoformat()
                                }
                                return
                            else:
                                self.logger.warning("No web search results found after search action")
                                # Continue with normal handling
                        
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
            
            # Detect special directives
            cleaned_content, directives = self._detect_special_directives(content_to_return)
            
            # Process special directives
            additional_context = self._process_special_directives(directives, session_id)
            
            # Add additional context to the response
            if additional_context:
                content_to_return += "\n\n" + additional_context
            
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
    
    def process_response(self, response_data, user_input, session_id):
        """
        Process the response from the LLM.
        Handle any special instructions like tier upgrading.
        
        Args:
            response_data: The response data from the LLM
            user_input: The user input that triggered this response
            session_id: The session ID
            
        Returns:
            The processed response
        """
        response_content = ""
        
        # Extract the response content
        if isinstance(response_data, dict):
            if "content" in response_data:
                response_content = response_data["content"]
            elif "llm_response" in response_data:
                llm_response = response_data["llm_response"]
                if "response_tiers" in llm_response and "tier3" in llm_response["response_tiers"]:
                    response_content = llm_response["response_tiers"]["tier3"]
                elif "response" in llm_response:
                    response_content = llm_response["response"]
        
        # Handle any tier upgrade requests
        if response_content:
            response_content = self._process_tier_upgrade_requests(response_content, session_id)
            
            # Update the response content in the response data
            if "content" in response_data:
                response_data["content"] = response_content
            elif "llm_response" in response_data:
                if "response_tiers" in response_data["llm_response"] and "tier3" in response_data["llm_response"]["response_tiers"]:
                    response_data["llm_response"]["response_tiers"]["tier3"] = response_content
                elif "response" in response_data["llm_response"]:
                    response_data["llm_response"]["response"] = response_content
        
        return response_data
    
    def _process_tier_upgrade_requests(self, content, session_id):
        """
        Process any UPGRADE_MESSAGE requests in the content.
        
        Args:
            content: The response content
            session_id: The session ID
            
        Returns:
            The content with UPGRADE_MESSAGE requests removed
        """
        # Define regex pattern to find upgrade requests
        import re
        pattern = r"UPGRADE_MESSAGE:\s*([a-zA-Z0-9-]+)\s*TO\s*TIER\s*([123])"
        
        # Find all upgrade requests
        matches = re.findall(pattern, content)
        
        if matches:
            self.logger.info(f"Found {len(matches)} tier upgrade requests")
            
            # Process each upgrade request
            for message_id, tier in matches:
                try:
                    # Try to get the contextual memory manager
                    from managers.memory.contextual_memory import get_memory_manager
                    memory_manager = get_memory_manager()
                    
                    if memory_manager:
                        # Ensure current session is active
                        if memory_manager.active_session_id != session_id:
                            memory_manager.load_session_context(session_id)
                        
                        # Upgrade the message tier
                        success = memory_manager.tier_manager.upgrade_message_tier(message_id, int(tier))
                        
                        if success:
                            self.logger.info(f"Successfully upgraded message {message_id[:8]} to tier {tier}")
                        else:
                            self.logger.warning(f"Failed to upgrade message {message_id[:8]} to tier {tier}")
                except Exception as e:
                    self.logger.error(f"Error processing tier upgrade request: {e}")
            
            # Remove the upgrade requests from the content
            content = re.sub(pattern, "", content)
            # Clean up any resulting double spaces
            content = re.sub(r"\s+", " ", content).strip()
        
        return content
    
    def auto_upgrade_important_messages(self, session_id: str, user_id: str):
        """
        Automatically upgrade important messages in the history to ensure they remain in context.
        
        Args:
            session_id: The session ID to upgrade messages for
            user_id: The user's ID
        """
        try:
            # Skip if no contextual memory
            if not self.contextual_memory:
                self.logger.warning("No contextual memory available for auto-upgrading messages")
                return
                
            # Get the session history
            session_history = self.contextual_memory.get_session_history(session_id)
            if not session_history:
                self.logger.info(f"No history found for session {session_id}")
                return
                
            # Analyze messages for important content
            # This is a simpler implementation that doesn't rely on tier messages
            important_messages = []
            for message in session_history:
                # Check if content contains specific markers indicating importance
                if message.get('content') and any(marker in str(message.get('content')).lower() 
                                             for marker in ['important', 'remember', 'key point', 'critical']):
                    important_messages.append(message)
                    
            self.logger.info(f"Found {len(important_messages)} potentially important messages")
            
            # If there are important messages, ensure they're part of the active context
            if important_messages and self.contextual_memory:
                # Just store information about important messages - no need to do anything special yet
                self.logger.info(f"Flagged {len(important_messages)} messages as important for later reference")
                
        except Exception as e:
            self.logger.error(f"Error in auto_upgrade_important_messages: {e}", exc_info=True)
    
    def _extract_content_from_response(self, response_data) -> str:
        """
        Extract clean content string from potentially complex response object.
        This prioritizes [LLM_START]/[LLM_END] markers for extraction,
        and falls back to various response formats if markers aren't found.
        
        Args:
            response_data: The response data from the LLM
            
        Returns:
            Extracted content as string
        """
        try:
            # Starting with an empty result
            result = ""
            
            # If response is None, return empty string
            if response_data is None:
                self.logger.warning("Response data is None, returning empty string")
                return ""
                
            # If response is a string, use it directly
            if isinstance(response_data, str):
                text_to_check = response_data
            else:
                # For dict or other types, we need to extract the relevant content
                text_to_check = self._extract_text_from_object(response_data)
                
            # Now that we have text to check, prioritize finding content between markers
            marker_content = self._extract_content_from_markers(text_to_check)
            if marker_content:
                result = marker_content
            else:
                # If no markers found, just use the extracted text after removing action signals
                result = self._remove_action_signals(text_to_check)
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting content from response: {e}", exc_info=True)
            return ""
            
    def _remove_action_signals(self, text: str) -> str:
        """
        Remove action signals that should not be shown to the user.
        
        Args:
            text: Text to process
            
        Returns:
            Text with action signals removed
        """
        try:
            # First, split the text into lines
            lines = text.splitlines()
            
            # Filter out lines containing action signals 
            # (those that match our action signal patterns)
            filtered_lines = []
            
            for line in lines:
                # Skip lines that are pure action signals
                if (re.match(r'\s*\[(SEARCH|WEB_SEARCH):[^\]]+\]\s*$', line) or
                    re.match(r'\s*\[REQUEST_TIER:\d+:[^\]]+\]\s*$', line)):
                    self.logger.info(f"Removing action signal line: {line}")
                    continue
                    
                # Keep all other lines
                filtered_lines.append(line)
                
            # Rejoin the filtered lines
            return "\n".join(filtered_lines)
            
        except Exception as e:
            self.logger.error(f"Error removing action signals: {e}", exc_info=True)
            return text  # Return original text if there's an error
    
    def _extract_text_from_object(self, obj: Dict[str, Any]) -> str:
        """
        Extract the relevant text from a response object.
        
        Args:
            obj: The response object
            
        Returns:
            Extracted text
        """
        # Direct access to llm_response structure with tier3 content
        if "llm_response" in obj:
            llm_resp = obj["llm_response"]
            # Tiered response format
            if isinstance(llm_resp, dict) and "response_tiers" in llm_resp:
                tiers = llm_resp["response_tiers"]
                if "tier3" in tiers and tiers["tier3"]:
                    return tiers["tier3"]
        
        # Check common response keys in priority order
        for key in ["response", "text", "content", "message", "answer"]:
            if key in obj:
                return obj[key]
        
        # If no standard keys found, use first available key
        if len(obj) > 0:
            first_key = list(obj.keys())[0]
            return str(obj[first_key])
        
        # Default to empty string
        return ""
    
    def _final_cleanup(self, content: str) -> str:
        """
        Perform final cleanup on the content before sending to the user.
        Removes system artifacts, action signals, etc.
        
        Args:
            content: The content to clean up
            
        Returns:
            The cleaned up content
        """
        try:
            # If empty content, return empty string
            if not content:
                return ""
                
            # Make sure we're working with a string
            if not isinstance(content, str):
                content = str(content)
                
            # Remove [LLM_START] and [LLM_END] markers
            content = re.sub(r'\[LLM_START\]|\[LLM_END\]', '', content)
            
            # Remove lingering action signals (should not be inside content, but just in case)
            # For each line, check if it contains only an action signal and remove it
            cleaned_lines = []
            for line in content.split('\n'):
                # Skip lines that are purely action signals
                if (re.match(r'^\s*\[(SEARCH|WEB_SEARCH|REQUEST_TIER|REMEMBER|FORGET_THIS|CORRECT|CALCULATE|COMMAND|EXECUTE|SEARCH_EPISODIC):[^\]]+\]\s*$', line)):
                    continue
                    
                # For other lines, keep them but remove any action signals embedded in them
                cleaned_line = re.sub(r'\[(SEARCH|WEB_SEARCH|REQUEST_TIER|REMEMBER|FORGET_THIS|CORRECT|CALCULATE|COMMAND|EXECUTE|SEARCH_EPISODIC):[^\]]+\]', '', line)
                cleaned_lines.append(cleaned_line)
                
            # Rejoin the lines, preserving all newlines and formatting
            content = '\n'.join(cleaned_lines)
            
            # Preserve markdown formatting while removing any internal JSON syntax
            # First, remove any JSON syntax that might be in the response but keep markdown intact
            content = re.sub(r'{"[^}]+}', '', content)
            
            # Ensure newlines in markdown are preserved
            # Double newlines for paragraph breaks
            content = re.sub(r'\n\s*\n', '\n\n', content)
            
            # Fix common markdown issues
            # Ensure headings have space after #
            content = re.sub(r'(^|\n)#([^#\s])', r'\1# \2', content)
            content = re.sub(r'(^|\n)##([^#\s])', r'\1## \2', content)
            content = re.sub(r'(^|\n)###([^#\s])', r'\1### \2', content)
            
            # Clean up any excessive whitespace but preserve intentional whitespace in code blocks
            # Detect if we're in a code block
            lines = content.split('\n')
            in_code_block = False
            for i, line in enumerate(lines):
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                    
                if not in_code_block:
                    # Only trim outside code blocks
                    lines[i] = line.rstrip()
                    
            content = '\n'.join(lines)
            
            # Ensure we have sensible content
            if content.strip() == '':
                return "I'm not sure how to respond to that. Could you please try again or rephrase your question?"
                
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"Error in _final_cleanup: {e}", exc_info=True)
            return content
    
    def _extract_content_from_markers(self, content: str) -> str:
        """
        Extract content between [LLM_START] and [LLM_END] markers.
        
        Args:
            content: The content to extract from
            
        Returns:
            Extracted content, or original content if markers not found
        """
        if not content:
            return content
            
        # Using regex to extract content between [LLM_START] and [LLM_END]
        import re
        marker_pattern = r'\[LLM_START\](.*?)\[LLM_END\]'
        match = re.search(marker_pattern, content, re.DOTALL)
        
        if match:
            extracted = match.group(1)
            self.logger.info(f"Successfully extracted content between LLM markers (length: {len(extracted)})")
            return extracted.strip()
        
        # If no markers found, return original content
        return content
    
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
    
    def _handle_direct_action_signals(self, user_input: str, response: Dict[str, Any], tier: int,
                                     system_prompt: str, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        Check for direct action signals and handle accordingly.
        Returns the modified response.
        """
        try:
            # Ensure we have an action handler
            if not self.action_handler:
                self.logger.warning("No action handler available to process direct actions")
                return response
                
            # Get the content from the response
            tier_content = response.get(f"tier{tier}", "")
            
            # Check for search command in the raw content
            search_pattern = r"\[(SEARCH|WEB_SEARCH):([^\]]+)\]"
            search_match = re.search(search_pattern, tier_content, re.IGNORECASE)
            
            if search_match:
                search_query = search_match.group(2).strip()
                self.logger.info(f"Detected direct search action in tier{tier}: {search_query}")
                
                # Clear the response to prevent the search command from being shown to the user
                response[f"tier{tier}"] = ""
                
                # Directly initiate the search rather than waiting for another response generation
                time.sleep(0.5)  # Small delay to ensure processing
                
                # Process the search using the action handler
                search_result = ""
                for item in self.action_handler.process_search_request(search_query, session_id, user_input):
                    if isinstance(item, dict) and item.get('content'):
                        search_result = item.get('content')
                
                self.logger.info(f"Search completed with result size: {len(search_result)}")
                return response  # Return immediately, don't append search command
                
            # Check for other direct actions
            action_result, action_content, action_type = self.action_handler.detect_action(tier_content, user_input, session_id)
            
            if action_result != "ACTION_NONE":
                self.logger.info(f"Direct action detected: {action_result}, type: {action_type}")
                
                # Handle specific action types
                if "SEARCH" in action_type:
                    # Already handled above, but just in case there's another search pattern:
                    response[f"tier{tier}"] = ""
                    return response
            
            # No direct action, return the original response
            return response
            
        except Exception as e:
            self.logger.error(f"Error handling direct action signals: {e}", exc_info=True)
            return response
    
    def _detect_special_directives(self, text):
        """
        Detects if the response contains special directives like tier upgrade requests.
        Returns a tuple (cleaned_text, found_directives)
        """
        directives = {
            "tier_upgrades": [],
            "memory_recall": [],
            "memory_search": []
        }
        
        cleaned_text = text
        
        # Detect tier upgrade requests
        tier_upgrade_pattern = r"UPGRADE_MESSAGE:\s*([a-fA-F0-9-]+)\s*TO\s*TIER\s*([123])"
        for match in re.finditer(tier_upgrade_pattern, text):
            message_id = match.group(1)
            tier_level = int(match.group(2))
            directives["tier_upgrades"].append({"message_id": message_id, "tier_level": tier_level})
            
            # Remove the directive from the text
            cleaned_text = cleaned_text.replace(match.group(0), "")
            
        # Detect memory recall requests
        memory_recall_pattern = r"RECALL_MESSAGE:\s*([a-fA-F0-9-]+)"
        for match in re.finditer(memory_recall_pattern, text):
            message_id = match.group(1)
            directives["memory_recall"].append({"message_id": message_id})
            
            # Remove the directive from the text
            cleaned_text = cleaned_text.replace(match.group(0), "")
        
        # Detect memory search requests
        memory_search_pattern = r"SEARCH_MEMORY:\s*(.+?)(?:\n|$)"
        for match in re.finditer(memory_search_pattern, text):
            query = match.group(1).strip()
            directives["memory_search"].append({"query": query})
            
            # Remove the directive from the text
            cleaned_text = cleaned_text.replace(match.group(0), "")
            
        return cleaned_text.strip(), directives
        
    def _process_special_directives(self, directives, session_id):
        """
        Process all detected special directives.
        Returns additional context to be added to the response.
        """
        additional_context = []
        
        # Process tier upgrades
        if directives.get("tier_upgrades"):
            for upgrade in directives["tier_upgrades"]:
                message_id = upgrade["message_id"]
                tier_level = upgrade["tier_level"]
                success = self._upgrade_message_tier(session_id, message_id, tier_level)
                if success:
                    additional_context.append(f"Upgraded message {message_id[:8]} to tier {tier_level}.")
                else:
                    additional_context.append(f"Failed to upgrade message {message_id[:8]} to tier {tier_level}.")
        
        # Process memory recall requests
        if directives.get("memory_recall"):
            for recall in directives["memory_recall"]:
                message_id = recall["message_id"]
                success = self.contextual_memory_manager.recall_message(message_id)
                if success:
                    additional_context.append(f"Recalled message {message_id[:8]} from episodic memory.")
                else:
                    additional_context.append(f"Failed to recall message {message_id[:8]} from episodic memory.")
        
        # Process memory search requests
        if directives.get("memory_search"):
            for search in directives["memory_search"]:
                query = search["query"]
                results = self.contextual_memory_manager.search_episodic_memory(query)
                if results and "No matching messages found" not in results:
                    additional_context.append(f"Memory search results for '{query}':\n{results}")
                else:
                    additional_context.append(f"No results found in episodic memory for '{query}'.")
        
        return "\n\n".join(additional_context)
        
    def _format_user_friendly_error(self, error_msg: str) -> str:
        """
        Format an error message to be more user-friendly.
        
        Args:
            error_msg: The original error message
            
        Returns:
            A user-friendly version of the error message
        """
        
        # Convert to lower case for easier matching
        lower_error = error_msg.lower()
        
        # Handle copyright-related errors
        if 'copyright' in lower_error or 'copyrighted material' in lower_error:
            return """I encountered an error generating your content. Let me try again with a different approach.

If you're still seeing this message, please try rephrasing your request slightly or providing more specific details about what you'd like to include in the document.

For legal documents like lease agreements, you might want to specify:
- The key terms you want to include
- Any specific clauses that are important to you
- The level of detail you're looking for

This will help me generate a more tailored document that meets your needs."""
            
        # Handle content policy violations
        elif any(term in lower_error for term in ['policy', 'violation', 'prohibited', 'not allowed', 'restricted']):
            return """I'm sorry, but I can't provide that content due to content policy restrictions.

I'm designed to be helpful, harmless, and honest, which means there are certain topics I can't assist with. Let's discuss something else that I can help you with."""
            
        # Handle backend/technical errors
        elif any(term in lower_error for term in ['internal error', 'backend', 'server', 'timeout', 'unavailable']):
            return """I'm experiencing a technical issue connecting to my knowledge systems. 

This is a temporary problem on my end, not yours. Please try again in a moment, or rephrase your question slightly differently."""
            
        # Handle API specific errors
        elif 'api' in lower_error or 'finish_reason' in lower_error:
            return """Let me try to answer your question in a different way.

I might have run into a technical limitation with my usual response method. Try asking more specifically about the elements you'd like to include, and I'll work on creating that content for you."""
            
        # Default error message for anything else
        else:
            return """I apologize, but I encountered an unexpected issue while processing your request. 

Please try again or rephrase your question. If the problem persists, it might be a temporary system limitation."""