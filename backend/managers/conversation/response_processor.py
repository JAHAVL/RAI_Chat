import json
import time
import logging
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
            
            # Process for special action signals
            if self.action_handler:
                action_signal, action_result, action_type = self.action_handler.process_llm_response(
                    session_id=session_id,
                    user_input=user_input,
                    response_data=llm_response
                )
                
                if action_signal:
                    self.logger.info(f"Detected action signal: {action_type}")
                    
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
            # Handle different response formats
            if response_data is None:
                content = "I'm sorry, but I couldn't generate a response at this time."
            elif isinstance(response_data, str):
                # Response is already a string
                content = response_data
            elif isinstance(response_data, dict):
                # Try various common key patterns
                if "llm_response" in response_data:
                    llm_resp = response_data["llm_response"]
                    if isinstance(llm_resp, dict) and "content" in llm_resp:
                        content = llm_resp["content"]
                    elif isinstance(llm_resp, str):
                        content = llm_resp
                    elif isinstance(llm_resp, dict) and "text" in llm_resp:
                        content = llm_resp["text"]
                elif "response" in response_data:
                    content = response_data["response"]
                elif "text" in response_data:
                    content = response_data["text"]
                elif "content" in response_data:
                    content = response_data["content"]
                elif "message" in response_data:
                    message = response_data["message"]
                    if isinstance(message, dict) and "content" in message:
                        content = message["content"]
                    else:
                        content = str(message)
                elif "answer" in response_data:
                    content = response_data["answer"]
                elif len(response_data) > 0:
                    # Just take the first key's value as a fallback
                    first_key = list(response_data.keys())[0]
                    content = str(response_data[first_key])
            else:
                # For any other type, convert to string
                content = str(response_data)
                
            # Make sure we actually have content
            if not content:
                content = "I'm sorry, but I couldn't generate a meaningful response."
                self.logger.warning("No content extracted from response")
                
            # If content is a dict or other object, convert to JSON string
            if not isinstance(content, str):
                self.logger.warning(f"Content is not a string, converting from {type(content)}")
                content = json.dumps(content)
                
            return content
                
        except Exception as e:
            self.logger.error(f"Error extracting content from response: {str(e)}", exc_info=True)
            return "I encountered an error processing the response."
    
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
    
    def _chunk_response(self, response: str, chunk_size: int = 100) -> Generator[str, None, None]:
        """
        Split a response into smaller chunks for streaming.
        
        Args:
            response: The complete response
            chunk_size: Size of each chunk in characters
            
        Yields:
            Response chunks
        """
        # For very short responses, return as a single chunk
        if len(response) <= chunk_size:
            yield response
            return
            
        # Break response into sentences or paragraphs for more natural chunking
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = response.split('\n\n')
        
        for paragraph in paragraphs:
            # If paragraph is longer than chunk_size, split by sentences
            if len(paragraph) > chunk_size:
                sentences = paragraph.replace('. ', '.\n').split('\n')
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) <= chunk_size:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "
            else:
                if len(current_chunk) + len(paragraph) <= chunk_size:
                    current_chunk += paragraph + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph + "\n\n"
                    
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        for chunk in chunks:
            yield chunk