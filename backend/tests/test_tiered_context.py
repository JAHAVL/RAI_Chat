import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.contextual_memory import ContextualMemoryManager
import json
import logging

def test_tiered_context():
    """
    Test the tiered context retrieval logic.
    This simulates the process_message method with the iterative context retrieval.
    """
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("TestTieredContext")
    
    # Initialize memory manager
    memory = ContextualMemoryManager()
    session_id = "test_session"
    memory.initialize_empty_session_memory(session_id)
    
    # Add some test data
    user_message = "What is the capital of France?"
    user_tier1 = "u/query=capital_of_France"
    user_tier2 = "User asked about the capital of France"
    memory.process_user_message(session_id, user_message, user_tier1, user_tier2)
    
    # Add assistant response
    assistant_response = {
        "tier1": "a/answer=Paris",
        "tier2": "Assistant answered that Paris is the capital of France",
        "tier3": "The capital of France is Paris, which is also the largest city in the country."
    }
    memory.process_assistant_message(assistant_response, session_id)
    
    # Now simulate the tiered context retrieval process
    print("\n=== Testing Tiered Context Retrieval ===")
    
    # New user query
    new_query = "What is its population?"
    print(f"User query: {new_query}")
    
    # Simulate the process_message method with tiered context retrieval
    for attempt in range(1, 5):  # Max 4 attempts: T1, T2, T3, Episodic
        print(f"\nAttempt {attempt}:")
        
        # Get context for the current tier
        if attempt == 1:
            context = memory.get_context(session_id, "tier1")
            print(f"Tier 1 context: {context}")
        elif attempt == 2:
            context = memory.get_context(session_id, "tier2")
            print(f"Tier 2 context: {context}")
        elif attempt == 3:
            context = memory.get_context(session_id, "tier3")
            print(f"Tier 3 context: {context}")
        elif attempt == 4:
            print("Using Episodic Memory context")
            episodic_memories = memory.get_episodic_memories(session_id, new_query)
            if episodic_memories:
                context = "Relevant past messages:\n"
                for mem in episodic_memories[:3]:
                    context += f"- User: {mem['tiers'].get('tier3', '')}\n"
            else:
                context = "No relevant past messages found in episodic memory."
            print(f"Episodic context: {context}")
        
        # Simulate LLM response
        # In a real implementation, this would call the LLM with the context
        if attempt < 3:
            print("LLM response: [NEED_MORE_CONTEXT]")
            # Continue to next tier
        else:
            # Simulate successful response at Tier 3
            print("LLM response: {")
            print('  "tier1": "a/answer=Paris_population_2.1M",')
            print('  "tier2": "Paris has a population of 2.1 million people",')
            print('  "tier3": "Paris has a population of approximately 2.1 million people within the city limits."')
            print("}")
            break
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_tiered_context()