#!/usr/bin/env python
"""
Validation script to ensure the critical memory instructions are properly included in the system prompt
"""

import sys
import os
import json
import requests
import logging
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our components
from components.prompts import DEFAULT_SYSTEM_PROMPT, build_system_prompt

def validate_memory_instructions():
    """
    Validate that the critical memory instructions are properly included in the system prompt
    """
    # Check the default system prompt
    logger.info("Checking DEFAULT_SYSTEM_PROMPT...")
    if "TIERED MEMORY SYSTEM" in DEFAULT_SYSTEM_PROMPT:
        logger.info("✅ DEFAULT_SYSTEM_PROMPT includes TIERED MEMORY SYSTEM instructions")
    else:
        logger.error("❌ DEFAULT_SYSTEM_PROMPT does NOT include TIERED MEMORY SYSTEM instructions")
    
    # Get our critical memory instructions
    memory_instructions = """
CRITICAL MEMORY INSTRUCTIONS: 
You MUST reliably retain and use ALL information about the user. This is your highest priority.
1. When asked about ANY fact previously mentioned by the user, you MUST request higher tier information
2. For general context, use [REQUEST_TIER:2:message_id] and for specific facts use [REQUEST_TIER:3:message_id]
3. The system prunes older messages after reaching a token limit - if information isn't in current context, use [SEARCH_EPISODIC:keyword]
4. If the user asks "what is my X" or "what did I say about X", IMMEDIATELY use both tier requests and episodic search
5. NEVER guess or make up facts - if information isn't in your current context, request it
6. ALWAYS treat tier upgraded content as absolute truth and fully incorporate it in your response
7. Every time a user asks about a fact, use AT LEAST ONE tier request or episodic search command
8. Relevant user memories MUST be reflected in your tier1, tier2, and tier3 responses
9. REMEMBER: It is BETTER to request tier upgrades too aggressively than to miss information
10. DO NOT respond with "I don't recall" without first attempting retrieval via tier requests
11. If you suspect a fact exists in earlier messages, use appropriate tier requests before responding
"""
    
    # Build a system prompt
    built_prompt = build_system_prompt(
        conversation_history="",
        contextual_memory="",
        specialized_instructions=memory_instructions,
        remember_this_content="",
        forget_this_content="",
        web_search_results=""
    )
    
    # Check if the built prompt includes our critical memory instructions
    if memory_instructions.strip() in built_prompt:
        logger.info("✅ build_system_prompt correctly includes memory instructions")
        
        # Show the location in the prompt
        start_idx = built_prompt.find(memory_instructions.strip())
        end_idx = start_idx + len(memory_instructions.strip())
        prompt_length = len(built_prompt)
        
        # Calculate the position percentage
        position_percent = (start_idx / prompt_length) * 100
        logger.info(f"Memory instructions start at character {start_idx} (Position: {position_percent:.1f}% into the prompt)")
        
        # Check surrounding context
        context_before = built_prompt[max(0, start_idx - 100):start_idx]
        context_after = built_prompt[end_idx:min(prompt_length, end_idx + 100)]
        
        logger.info("Context before memory instructions:")
        print(f"...{context_before}")
        
        logger.info("Context after memory instructions:")
        print(f"{context_after}...")
        
        return True
    else:
        logger.error("❌ build_system_prompt does NOT include memory instructions")
        
        # Try to find parts of the memory instructions
        snippets = memory_instructions.strip().split("\n")
        for snippet in snippets:
            if snippet and len(snippet) > 10 and snippet in built_prompt:
                logger.info(f"Found snippet in prompt: {snippet[:50]}")
        
        return False

if __name__ == "__main__":
    logger.info("Validating memory retention instructions integration...")
    success = validate_memory_instructions()
    sys.exit(0 if success else 1)
