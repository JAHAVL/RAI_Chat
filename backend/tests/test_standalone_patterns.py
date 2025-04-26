#!/usr/bin/env python
"""
Standalone test for memory pattern detection.
This test doesn't require database connectivity.
"""

import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_tier_requests(text):
    """Simple tier request detection function."""
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
    
    tier_requests = []
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
            except Exception as e:
                logger.error(f"Error parsing tier request match: {e}")
    
    return tier_requests

def find_episodic_searches(text):
    """Simple episodic search detection function."""
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
    
    episodic_searches = []
    for pattern in search_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            query = match.strip()
            if query and len(query) > 2:  # Minimum query length
                # Avoid duplicates
                if query not in episodic_searches:
                    episodic_searches.append(query)
    
    return episodic_searches

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
    
    # Test tier request detection
    tier_success = 0
    tier_total = 3
    
    for i in range(tier_total):
        response = test_responses[i]
        tier_requests = find_tier_requests(response)
        
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
        episodic_searches = find_episodic_searches(response)
        
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
    
    return {
        "tier_accuracy": tier_accuracy,
        "search_accuracy": search_accuracy,
        "overall_accuracy": overall_accuracy,
        "test_passed": overall_accuracy == 100.0
    }

if __name__ == "__main__":
    logger.info("Starting standalone pattern detection test...")
    result = test_pattern_detection()
    logger.info(f"Test results: {result}")
    
    # Test was successful if we achieved 100% pattern detection
    if result["test_passed"]:
        logger.info("✅ All tests PASSED!")
        exit(0)
    else:
        logger.error("❌ Some tests FAILED.")
        exit(1)
