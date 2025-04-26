#!/usr/bin/env python
"""
Simple script to directly test the modified system prompt with the LLM
"""

import sys
import os
import logging
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our modified system prompt and the build function
from components.prompts import DEFAULT_SYSTEM_PROMPT, build_system_prompt

def test_system_prompt():
    """
    Display the updated system prompt and simulate a test conversation
    """
    logger.info("Loaded the modified system prompt successfully!")
    
    # Print just key sections from the system prompt for validation
    prompt_sections = DEFAULT_SYSTEM_PROMPT.split("\n\n")
    
    # Look for the sections we modified
    tier_section_found = False
    for section in prompt_sections:
        if "TIERED MEMORY SYSTEM" in section:
            print("\n=== Found TIERED MEMORY SYSTEM section in DEFAULT_SYSTEM_PROMPT ===\n")
            print(section)
            tier_section_found = True
            break
    
    if not tier_section_found:
        print("TIERED MEMORY SYSTEM section not found in the DEFAULT_SYSTEM_PROMPT")
    
    # Test if build_system_prompt includes the memory instructions
    print("\n=== Testing if build_system_prompt includes CRITICAL MEMORY INSTRUCTIONS ===\n")
    built_prompt = build_system_prompt(
        user_name="Jordan",
        username="jordan",
        context_items=[],
        temperature=0.7
    )
    
    # Check if the built prompt includes our critical memory instructions
    if "CRITICAL MEMORY INSTRUCTIONS" in built_prompt:
        print(" Success! CRITICAL MEMORY INSTRUCTIONS are included in the built system prompt")
        return True
    else:
        print(" Error! CRITICAL MEMORY INSTRUCTIONS are NOT included in the built system prompt")
        print("The instructions are defined but not properly integrated")
        return False

if __name__ == "__main__":
    success = test_system_prompt()
    sys.exit(0 if success else 1)
