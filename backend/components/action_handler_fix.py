# Fix for the re module import issue in the process_llm_response function
def process_llm_response_fixed(self,
                       session_id: str,
                       user_input: str,  # Needed for storing turn data
                       response_data: dict = None
                       ):
    """
    Processes the LLM response, detects signals, performs actions.
    """
    # Ensure re is imported at function scope
    import re
    import json
    from datetime import datetime
    
    self.logger.info(f"Processing LLM response for session {session_id}, user {self.user_id}")
    
    if not response_data or not isinstance(response_data, dict) or "llm_response" not in response_data:
        self.logger.error(f"Invalid or missing response_data received from LLM for session {session_id}.")
        return "break", "LLM response was invalid or missing.", "error"

    try:
        llm_resp_obj = response_data["llm_response"]
        tier3_response = llm_resp_obj.get("response_tiers", {}).get("tier3", "")
        self.logger.info(f"Extracted tier3_response (first 50 chars): {tier3_response[:50]}...")

        if not tier3_response:
            self.logger.error(f"LLM response structure valid, but tier3 content missing for session {session_id}.")
            self.contextual_memory.process_assistant_message(response_data, user_input, session_id)
            return "break", "LLM response was missing content.", "error"
            
        # Just return the response directly without any signal detection
        # Store the turn
        self.contextual_memory.process_assistant_message(response_data, user_input)
        
        # Yield a final response chunk with the tier3 content
        yield {
            "type": "final",
            "content": tier3_response,
            "timestamp": datetime.now().isoformat()
        }
        
        # Signal to break and return the tier3 response
        return "break", tier3_response, "answer"
        
    except Exception as proc_ex:
        self.logger.error(f"!!! EXCEPTION during LLM response processing in ActionHandler: {proc_ex} !!!", exc_info=True)
        # Attempt to store turn data even if processing failed
        if response_data:
            self.contextual_memory.process_assistant_message(response_data, user_input)
        return "break", f"Error processing LLM response: {proc_ex}", "error"
