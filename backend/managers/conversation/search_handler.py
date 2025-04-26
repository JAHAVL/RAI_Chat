import re
import logging
from datetime import datetime
from typing import Dict, Any, Generator, Tuple, Optional

class SearchHandler:
    """
    Handles the web search functionality extracted from the conversation manager.
    This class properly implements the search processing and error handling.
    """
    
    def __init__(self, logger=None, contextual_memory=None):
        """
        Initialize the SearchHandler.
        
        Args:
            logger: Logger instance
            contextual_memory: ContextualMemory instance for storing search results
        """
        self.logger = logger or logging.getLogger(__name__)
        self.contextual_memory = contextual_memory
        
    def process_search_request(self, user_input: str, current_session_id: str) -> Generator[Dict[str, Any], None, None]:
        """
        Process a direct search request from user input.
        
        Args:
            user_input: User's message containing a search request
            current_session_id: Current active session ID
            
        Yields:
            Search status and result messages
        """
        if '[SEARCH:' not in user_input:
            return
            
        try:
            direct_search_match = re.search(r"\[SEARCH:\s*(.+?)\s*\]", user_input)
            if direct_search_match:
                query = direct_search_match.group(1).strip()
                self.logger.info(f"Direct web search requested for: {query}")
                
                # Create a system message indicating search is happening
                yield {
                    'type': 'system',
                    'action': 'web_search',
                    'status': 'active',
                    'content': f"Searching the web for: {query}",
                    'timestamp': datetime.now().isoformat(),
                    'session_id': current_session_id
                }
                
                try:
                    # Attempt to perform the search
                    from components.action_handler import perform_search
                    search_results = perform_search(query=query)
                    
                    # Send the results directly
                    yield {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'complete',
                        'content': search_results,
                        'raw_results': search_results,
                        'timestamp': datetime.now().isoformat(),
                        'session_id': current_session_id
                    }
                    
                    # Store search results in contextual memory as a system message
                    # This ensures the search results are part of the conversation history
                    search_system_message = {
                        'role': 'system',
                        'content': f"Search results for '{query}':\n\n{search_results}",
                        'timestamp': datetime.now().isoformat(),
                        'type': 'search_results'
                    }
                    
                    # Add to contextual memory
                    try:
                        if self.contextual_memory:
                            # Store as a system message in the conversation
                            system_message_data = {
                                'content': search_system_message['content'],
                                'type': 'search_results'
                            }
                            self.contextual_memory.add_system_message(system_message_data, current_session_id)
                            self.logger.info(f"Added search results to contextual memory for session {current_session_id}")
                            
                            # Also try to extract key facts from the search results
                            # This helps the system remember important information from searches
                            extraction_text = f"Important information from search about '{query}':\n\n{search_results}"
                            self.contextual_memory.extract_and_store_facts(extraction_text, current_session_id)
                            self.logger.info("Extracted key facts from search results")
                    except Exception as mem_ex:
                        self.logger.error(f"Error storing search results in memory: {str(mem_ex)}", exc_info=True)
                except Exception as search_ex:
                    self.logger.error(f"Error performing direct web search: {search_ex}")
                    yield {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'error',
                        'content': f"Error performing web search: {str(search_ex)}",
                        'timestamp': datetime.now().isoformat(),
                        'session_id': current_session_id
                    }
        except Exception as ex:
            self.logger.error(f"Error processing search request: {str(ex)}", exc_info=True)
            yield {
                'type': 'system',
                'action': 'web_search',
                'status': 'error',
                'content': f"Error processing search request: {str(ex)}",
                'timestamp': datetime.now().isoformat(),
                'session_id': current_session_id
            }