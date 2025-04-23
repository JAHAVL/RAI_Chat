import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.contextual_memory import ContextualMemoryManager
import json
from datetime import datetime

def test_contextual_memory():
    print("\n=== Testing Contextual Memory System ===\n")
    
    # Initialize the memory manager
    memory = ContextualMemoryManager()
    session_id = "test_session"
    
    # Test 1: Process user message with all tiers
    print("=== Test 1: Processing user message with all tiers ===")
    user_message = "Hi. My name is Jordan. I have two daughters, Adalie and Emmy. I have a dog named Koda also."
    user_tier1 = "u/name=Jordan | u/daughters=Adalie,Emmy | u/dog=Koda"
    user_tier2 = "User Jordan introduced himself, mentioned his two daughters Adalie and Emmy, and his dog Koda"
    
    print(f"\nUser message:")
    print(f"Tier 1 (shorthand): {user_tier1}")
    print(f"Tier 2 (summary): {user_tier2}")
    print(f"Tier 3 (full): {user_message}")
    
    message_id = memory.process_user_message(session_id, user_message, user_tier1, user_tier2)
    print(f"\nMessage stored with ID: {message_id}")
    
    # Test 2: Process assistant message with all tiers
    print("\n=== Test 2: Processing assistant message with all tiers ===")
    assistant_response = {
        "tier1": "a/greet=Jordan | a/ack=family",
        "tier2": "Assistant greeted Jordan and acknowledged his family members",
        "tier3": "Nice to meet you, Jordan! Your daughters Adalie and Emmy sound wonderful, and Koda too!"
    }
    
    print("\nAssistant response:")
    print(f"Tier 1 (shorthand): {assistant_response['tier1']}")
    print(f"Tier 2 (summary): {assistant_response['tier2']}")
    print(f"Tier 3 (full): {assistant_response['tier3']}")
    
    message_id = memory.process_assistant_message(assistant_response, session_id)
    print(f"\nMessage stored with ID: {message_id}")
    
    # Test 3: Get context from different tiers
    print("\n=== Test 3: Getting context from different tiers ===")
    for tier in ["tier1", "tier2", "tier3"]:
        context = memory.get_context(session_id, tier)
        print(f"\n{tier.upper()} context:")
        print(context)
    
    # Test 4: Get conversation history from different tiers
    print("\n=== Test 4: Getting conversation history from different tiers ===")
    for tier in ["tier1", "tier2", "tier3"]:
        history = memory.get_conversation_history(session_id, tier)
        print(f"\n{tier.upper()} history:")
        for msg in history:
            print(f"{msg['role']}: {msg['content']}")
    
    # Test 5: Test episodic memory search
    print("\n=== Test 5: Testing episodic memory search ===")
    queries = [
        "What is Jordan's dog's name?",
        "Who are Jordan's daughters?",
        "What are the names of the children?"
    ]
    
    for query in queries:
        print(f"\nSearching for: {query}")
        memories = memory.get_episodic_memories(session_id, query)
        print(f"Found {len(memories)} relevant memories:")
        for memory_obj in memories:
            print("\nRelevant memory:")
            print(f"Tier 1: {memory_obj['tiers']['tier1']}")
            print(f"Tier 2: {memory_obj['tiers']['tier2']}")
            print(f"Tier 3: {memory_obj['tiers']['tier3']}")
    
    # Test 6: Verify final memory state
    print("\n=== Test 6: Final Memory State ===")
    print("\nSession Memories:")
    print(json.dumps(memory.session_memories[session_id], indent=2))

if __name__ == "__main__":
    test_contextual_memory()