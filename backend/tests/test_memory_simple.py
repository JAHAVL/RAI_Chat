#!/usr/bin/env python
"""
Simple direct test for memory functionality.
This test focuses solely on testing the pattern detection for tier requests and episodic searches.
"""

import sys
import os
import logging
import re

# Add the parent directory to path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from managers.memory.request_parser import RequestParser
from models.connection import SessionLocal

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pattern_detection():
    """Test pattern detection for tier requests and episodic searches."""
    
    # Sample responses with tier requests and episodic searches
    test_responses = [
        # Tier request formats
        "Let me check that information for you. [REQUEST_TIER:3:msg_1234] Based on our earlier conversation...",
        "I don't have that in my immediate context. [REQUEST_TIER:2:msg_5678] Now I see you mentioned...",
        "Let me look at our previous messages. [REQUEST_TIER:3:message_abc123] I found that you said...",
        
        # Episodic search formats
        "I need to search for more details. [SEARCH_EPISODIC:favorite color] According to our conversation...",
        "Let me find that information for you. [SEARCH_EPISODIC:birth place] I see that you were born in...",
        "I'll check my memory. [SEARCH_EPISODIC:first job] Based on what you've told me before..."
    ]
    
    # Initialize the request parser
    db_session = SessionLocal()
    parser = RequestParser(db_session)
    
    # Test tier request detection
    tier_success = 0
    tier_total = 3
    
    for i in range(tier_total):
        response = test_responses[i]
        tier_requests = parser.find_tier_requests(response)
        
        if tier_requests:
            tier_success += 1
            logger.info(f"✅ SUCCESS: Found tier request in: {response[:50]}...")
            logger.info(f"Detected: {tier_requests}")
        else:
            logger.error(f"❌ FAILURE: Failed to detect tier request in: {response[:50]}...")
    
    # Test episodic search detection
    search_success = 0
    search_total = 3
    
    for i in range(3, 6):
        response = test_responses[i]
        episodic_searches = parser.find_episodic_searches(response)
        
        if episodic_searches:
            search_success += 1
            logger.info(f"✅ SUCCESS: Found episodic search in: {response[:50]}...")
            logger.info(f"Detected: {episodic_searches}")
        else:
            logger.error(f"❌ FAILURE: Failed to detect episodic search in: {response[:50]}...")
    
    # Calculate accuracies
    tier_accuracy = (tier_success / tier_total) * 100
    search_accuracy = (search_success / search_total) * 100
    overall_accuracy = ((tier_success + search_success) / (tier_total + search_total)) * 100
    
    logger.info(f"Tier request detection accuracy: {tier_accuracy:.2f}% ({tier_success}/{tier_total})")
    logger.info(f"Episodic search detection accuracy: {search_accuracy:.2f}% ({search_success}/{search_total})")
    logger.info(f"Overall pattern detection accuracy: {overall_accuracy:.2f}%")
    
    # Clean up
    db_session.close()
    
    return {
        "tier_accuracy": tier_accuracy,
        "search_accuracy": search_accuracy,
        "overall_accuracy": overall_accuracy,
        "test_passed": overall_accuracy == 100.0
    }

def test_prompt_instruction_alignment():
    """Test if the memory_retention_instructions align with the pattern detection."""
    from components.prompts import memory_retention_instructions
    
    # Extract the tier request and episodic search formats from the instructions
    tier_format_match = re.search(r'\[REQUEST_TIER:(\d+):([^\]]+)\]', memory_retention_instructions)
    search_format_match = re.search(r'\[SEARCH_EPISODIC:([^\]]+)\]', memory_retention_instructions)
    
    if tier_format_match:
        logger.info(f"✅ Tier request format in instructions: [REQUEST_TIER:{tier_format_match.group(1)}:{tier_format_match.group(2)}]")
    else:
        logger.error("❌ Could not find proper tier request format in instructions")
    
    if search_format_match:
        logger.info(f"✅ Episodic search format in instructions: [SEARCH_EPISODIC:{search_format_match.group(1)}]")
    else:
        logger.error("❌ Could not find proper episodic search format in instructions")
    
    return tier_format_match is not None and search_format_match is not None

if __name__ == "__main__":
    logger.info("Starting simple memory pattern detection test...")
    
    # Test instruction-detection alignment
    logger.info("Testing prompt instruction alignment with detection patterns...")
    instructions_aligned = test_prompt_instruction_alignment()
    
    if instructions_aligned:
        logger.info("✅ SUCCESS: Prompt instructions are aligned with detection patterns")
    else:
        logger.error("❌ FAILURE: Prompt instructions do not align with detection patterns")
    
    # Test pattern detection
    logger.info("Testing pattern detection...")
    result = test_pattern_detection()
    logger.info(f"Test results: {result}")
    
    # Final determination
    if result["test_passed"] and instructions_aligned:
        logger.info("✅ All tests PASSED!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests FAILED.")
        sys.exit(1)
