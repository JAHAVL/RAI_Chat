#!/usr/bin/env python
"""
Test script to verify that time placeholders are properly replaced in system prompts
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import our components
from components.prompts import build_system_prompt, DEFAULT_SYSTEM_PROMPT

def test_time_placeholder_replacement():
    """Test that time placeholders are properly replaced in the system prompt"""
    
    # Create a test prompt with time placeholder
    test_prompt = DEFAULT_SYSTEM_PROMPT + "\n\nWhat time is it?\nIt's [Placeholder for current time]."
    
    # Build system prompt with our test prompt
    result = build_system_prompt(
        specialized_instructions=test_prompt
    )
    
    # Check if the placeholder was replaced
    if "[Placeholder for current time]" in result:
        logger.error("❌ Time placeholder was NOT replaced in the system prompt")
        return False
    else:
        logger.info("✅ Time placeholder was successfully replaced in the system prompt")
        # Extract the replaced time for verification
        time_index = result.find("It's ")
        if time_index != -1:
            time_text = result[time_index:time_index+20]  # Grab enough text to show the time
            logger.info(f"   Replaced with: {time_text}")
        return True

if __name__ == "__main__":
    logger.info("Testing time placeholder replacement in system prompts...")
    success = test_time_placeholder_replacement()
    if success:
        logger.info("All tests passed successfully!")
    else:
        logger.error("Tests failed!")
        sys.exit(1)
