import logging
import time
import json
from typing import Dict, Any, Generator, List, Optional
from datetime import datetime

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
            
            # Process for special action signals
            if self.action_handler:
                action_signal, action_result, action_type = self.action_handler.process_llm_response(llm_response)
                
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
                        action_signal, action_result, action_type = self.action_handler.process_llm_response(llm_response)
                        
                        if action_signal:
                            self.logger.warning("Still getting action signal after retry, proceeding with best effort")
            
            # Store the assistant's response
            self._store_assistant_response(llm_response, session_id)
            
            # Return response in chunks 
            for chunk in self._chunk_response(llm_response):
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
            assistant_message = {
                'role': 'assistant',
                'content': response,
                'timestamp': datetime.now().isoformat()
            }
            
            self.contextual_memory.add_assistant_message(assistant_message, session_id)
            self.logger.debug(f"Stored assistant response in memory for session {session_id}")
            
            # Optionally extract facts from assistant's response
            self.contextual_memory.extract_and_store_facts(response, session_id)
            
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