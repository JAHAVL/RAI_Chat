# RAI_Chat/backend/managers/memory/request_parser.py

import logging
import re
from typing import Dict, Any, Optional, List, Union

# Import the Message model directly
from models.message import Message

from sqlalchemy.orm import Session as SQLAlchemySession

logger = logging.getLogger(__name__)

class RequestParser:
    """
    Parses and processes special requests in LLM responses, such as
    tier level upgrade requests and episodic memory lookup requests.
    """
    
    def __init__(self, db_session: SQLAlchemySession):
        self.db = db_session
        logger.info("RequestParser initialized")
    
    def process_response(self, 
                        response_text: str, 
                        session_id: str) -> Dict[str, Any]:
        """
        Process an LLM response to handle special requests.
        
        Args:
            response_text: The LLM response text
            session_id: The session ID
            
        Returns:
            Dictionary with processing results including:
            - need_regeneration: Whether response needs to be regenerated
            - clean_response: Response with request markers removed
            - episodic_context: Optional episodic memory context
        """
        result = {
            "need_regeneration": False,
            "clean_response": response_text,
        }
        
        try:
            # Extract tier requests
            tier_requests = self.find_tier_requests(response_text)
            if tier_requests:
                logger.info(f"Found {len(tier_requests)} tier requests")
                result["tier_requests"] = tier_requests
                result["need_regeneration"] = True
                
                # Process tier upgrade requests
                self._process_tier_requests(tier_requests, session_id)
                
                # Remove tier requests from the response
                result["clean_response"] = self._remove_tier_requests(response_text)
            
            # Check for episodic memory search
            episodic_queries = self.find_episodic_searches(response_text)
            if episodic_queries:
                logger.info(f"Found episodic searches: {episodic_queries}")
                result["episodic_queries"] = episodic_queries
                result["need_regeneration"] = True
                
                # Remove episodic search from the response
                for query in episodic_queries:
                    result["clean_response"] = self._remove_episodic_request(result["clean_response"], query)
                
            return result
            
        except Exception as e:
            logger.error(f"Error processing response: {e}", exc_info=True)
            # Return the original response on error
            return {
                "clean_response": response_text,
                "need_regeneration": False
            }
    
    def find_tier_requests(self, text: str) -> List[Dict[str, Any]]:
        """
        Find all tier upgrade requests in the text.
        Returns a list of dictionaries with 'tier_level' and 'message_id'.
        """
        # Improved pattern matching for better recognition
        tier_requests = []
        
        # Multiple regex patterns to catch various formats
        tier_request_patterns = [
            # Patterns the test is looking for
            r"\[REQUEST_TIER:(\d+):([^\]]+)\]",
            r"\[REQUEST_TIER:(\d+):([^\]]+)",
            r"\[REQUEST_TIER (\d+) ([^\]]+)\]",
            # Our custom patterns
            r"\[REQUEST_TIER:\s*upgrade\s+message\s+(\w+)\s+to\s+tier\s+(\d+)\]",
            r"\[REQUEST_TIER:\s*upgrade message (\w+) to tier (\d+)\]",
            r"\[REQUEST_TIER:upgrade message (\w+) to tier (\d+)\]",
            r"\[REQUEST_TIER: upgrade (\w+) to tier (\d+)\]",
            r"\[REQUEST_TIER:upgrade (\w+) to tier (\d+)\]"
        ]
        
        # Try each pattern
        for pattern in tier_request_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    # Handle different pattern formats
                    if len(match) == 2:
                        # Check which format we matched
                        if re.match(r"\d+", match[0]):
                            # First pattern format: [REQUEST_TIER:1:msg_123]
                            tier_level = int(match[0])
                            message_id = match[1].strip()
                        else:
                            # Second pattern format: [REQUEST_TIER:upgrade message msg_123 to tier 2]
                            message_id = match[0].strip()
                            tier_level = int(match[1])
                        
                        # Validate tier level
                        if 1 <= tier_level <= 3:
                            tier_requests.append({
                                "message_id": message_id,
                                "tier_level": tier_level
                            })
                            logger.info(f"Found tier upgrade request: message {message_id} to tier {tier_level}")
                except Exception as e:
                    logger.error(f"Error parsing tier request match: {e}")
        
        return tier_requests
    
    def find_episodic_searches(self, text: str) -> List[str]:
        """
        Find all episodic memory search requests in the text.
        Returns a list of search queries.
        """
        # Improved pattern matching for better recognition
        episodic_searches = []
        
        # Multiple regex patterns to catch various formats
        search_patterns = [
            # Primary pattern the test is looking for
            r"\[SEARCH_EPISODIC:([^\]]+)\]",
            # Additional patterns for robustness
            r"\[SEARCH_EPISODIC:\s*(.*?)\s*\]",
            r"\[SEARCH_EPISODIC:(.*?)\]",
            r"\[SEARCH EPISODIC:\s*(.*?)\s*\]",
            r"\[SEARCH EPISODIC:(.*?)\]"
        ]
        
        # Try each pattern
        for pattern in search_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                query = match.strip()
                if query and len(query) > 2:  # Minimum query length
                    # Avoid duplicates
                    if query not in episodic_searches:
                        episodic_searches.append(query)
                        logger.info(f"Found episodic search request: '{query}'")
        
        return episodic_searches
    
    def _process_tier_requests(self, requests: List[Dict[str, Any]],
                             session_id: str) -> None:
        """
        Process tier upgrade requests by updating the database.
        
        Args:
            requests: List of tier upgrade requests
            session_id: Session ID
        """
        if not requests:
            return
        
        logger.info(f"Processing {len(requests)} tier upgrade requests")
        
        from models.message import Message  # Import here to avoid circular import
        
        try:
            # Process each tier request
            for request in requests:
                message_id = request.get("message_id")
                tier_level = request.get("tier_level")
                
                if not message_id or not tier_level:
                    logger.warning(f"Invalid tier request: {request}")
                    continue
                
                # Clean up the message ID if needed (remove any extraneous characters)
                message_id = message_id.strip().strip('"\'`')
                
                # Validate tier level
                if tier_level not in [1, 2, 3]:
                    logger.warning(f"Invalid tier level: {tier_level}")
                    continue
                
                logger.info(f"Upgrading message {message_id} to tier {tier_level}")
                
                try:
                    # Find the message in the database
                    message = self.db.query(Message).filter(
                        Message.session_id == session_id,
                        Message.message_id.like(f"%{message_id}%")  # Use LIKE for partial matches
                    ).first()
                    
                    if message:
                        # Update the tier level
                        message.required_tier_level = tier_level
                        self.db.commit()
                        logger.info(f"Successfully upgraded message {message_id} to tier {tier_level}")
                    else:
                        logger.warning(f"Message {message_id} not found in session {session_id}")
                        
                except Exception as inner_e:
                    logger.error(f"Error updating message tier: {str(inner_e)}", exc_info=True)
                    self.db.rollback()
            
        except Exception as e:
            logger.error(f"Error processing tier requests: {str(e)}", exc_info=True)
            try:
                self.db.rollback()
            except:
                logger.error("❌ Failed to rollback transaction", exc_info=True)
    
    def _remove_episodic_request(self, text: str, query: str) -> str:
        """
        Remove episodic memory search request from text.
        
        Args:
            text: The text to clean
            query: The query to remove
            
        Returns:
            Cleaned text
        """
        # Standard pattern
        main_pattern = r"\[SEARCH_EPISODIC:\s*" + re.escape(query) + r"\s*\]"
        text = re.sub(main_pattern, "", text)
        
        # Alternative patterns
        alt_patterns = [
            r"\[SEARCH_EPISODIC:" + re.escape(query) + r"\]",
            r"\[SEARCH EPISODIC:\s*" + re.escape(query) + r"\s*\]",
            r"\[SEARCH EPISODIC:" + re.escape(query) + r"\]"
        ]
        
        for pattern in alt_patterns:
            text = re.sub(pattern, "", text)
        
        # Remove any double spaces created
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _remove_tier_requests(self, text: str) -> str:
        """
        Remove all tier request markers from the text.
        
        Args:
            text: The text to clean
            
        Returns:
            Cleaned text
        """
        # Enhanced regex patterns to capture all variations of tier requests
        patterns = [
            # Standard format
            r"\[REQUEST_TIER:(\d+):([^\]]+)\]",
            r"\[REQUEST_TIER:(\d+):([^\]]+)",
            r"\[REQUEST_TIER (\d+) ([^\]]+)\]",
            # Our custom patterns
            r"\[REQUEST_TIER:\s*upgrade\s+message\s+\w+\s+to\s+tier\s+\d+\]",
            r"\[REQUEST_TIER:\s*upgrade message \w+ to tier \d+\]",
            r"\[REQUEST_TIER:upgrade message \w+ to tier \d+\]",
            r"\[REQUEST_TIER: upgrade \w+ to tier \d+\]",
            r"\[REQUEST_TIER:upgrade \w+ to tier \d+\]"
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, "", text)
        
        # Remove any double spaces created
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
