import os
import sys
import logging
import json
from datetime import datetime

# --- Setup Paths ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Import Components ---
try:
    from RAI_Chat.memory.contextual_memory import ContextualMemoryManager
    from RAI_Chat.memory.episodic_memory import EpisodicMemoryManager
    # Note: This test focuses on memory interaction, not LLM calls.
except ImportError as e:
    logger.error(f"Failed to import necessary memory components: {e}")
    logger.error("Ensure the script is run from the project root or the PYTHONPATH is set correctly.")
    sys.exit(1)

# --- Test Function ---
def test_memory_flow():
    """
    Tests the interaction between Contextual and Episodic Memory Managers.
    Simulates adding messages and retrieving context.
    """
    print("\n--- Testing Memory Interaction Flow ---")
    test_session_id = f"test_memory_flow_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"Using Session ID: {test_session_id}")

    try:
        # 1. Initialize Memory Managers
        logger.info("Initializing EpisodicMemoryManager...")
        # Use default paths
        # test_memory_path = os.path.join(project_root, 'data', 'memory_test') # Removed test path
        # os.makedirs(test_memory_path, exist_ok=True) # Removed test path creation
        episodic_memory = EpisodicMemoryManager() # Removed base_path argument

        logger.info("Initializing ContextualMemoryManager...")
        contextual_memory = ContextualMemoryManager(
            episodic_memory_manager=episodic_memory
            # base_path=test_memory_path # Removed base_path argument
        )
        # Ensure session exists in contextual memory
        contextual_memory._ensure_session_exists(test_session_id)
        logger.info("Memory Managers Initialized.")

        # --- Simulate Conversation Turn 1 ---
        user_msg_1 = "My favorite color is blue."
        logger.info(f"Simulating Turn 1 - User: '{user_msg_1}'")
        contextual_memory.process_user_message(test_session_id, user_msg_1)

        # Simulate a basic assistant response structure (as expected by process_assistant_message)
        assistant_resp_data_1 = {
            "llm_response": {
                "response_tiers": {
                    "tier1": "Acknowledged favorite color.",
                    "tier2": "User mentioned favorite color is blue.",
                    "tier3": "Okay, I'll remember that your favorite color is blue."
                },
                "extracted_info": {"preferences": ["favorite_color: blue"]},
                "remember_this": ["User's favorite color is blue."],
                "forget_this": []
            },
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Simulating Turn 1 - Assistant: '{assistant_resp_data_1['llm_response']['response_tiers']['tier3']}'")
        contextual_memory.process_assistant_message(assistant_resp_data_1, user_msg_1, test_session_id)

        # --- Simulate Conversation Turn 2 ---
        user_msg_2 = "What is my favorite color?"
        logger.info(f"Simulating Turn 2 - User: '{user_msg_2}'")
        contextual_memory.process_user_message(test_session_id, user_msg_2)

        assistant_resp_data_2 = {
            "llm_response": {
                "response_tiers": {
                    "tier1": "Recalled favorite color.",
                    "tier2": "User asked about favorite color, recalled it's blue.",
                    "tier3": "Your favorite color is blue."
                },
                 "extracted_info": {}, "remember_this": [], "forget_this": [] # Simplified
            },
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Simulating Turn 2 - Assistant: '{assistant_resp_data_2['llm_response']['response_tiers']['tier3']}'")
        contextual_memory.process_assistant_message(assistant_resp_data_2, user_msg_2, test_session_id)

        # --- Check Memory State ---
        print("\n--- Verifying Memory Contents ---")

        # NOTE: get_tier1_context and get_tier2_context methods do not exist on ContextualMemoryManager.
        # Skipping these checks. We will rely on history and remember_this content.

        # --- Check T1/T2 Context using get_context ---
        tier1_context = contextual_memory.get_context(test_session_id, tier="tier1")
        print(f"\nRetrieved Tier 1 Context:\n{tier1_context}")
        if not tier1_context: logger.warning("Tier 1 context appears empty.")

        tier2_context = contextual_memory.get_context(test_session_id, tier="tier2")
        print(f"\nRetrieved Tier 2 Context:\n{tier2_context}")
        if not tier2_context: logger.warning("Tier 2 context appears empty.")
        # --- End T1/T2 Check ---

        # Check Formatted History
        history = contextual_memory.get_formatted_history(test_session_id, limit=10)
        print(f"\nFormatted History (last 10):\n{history}")
        if "User: My favorite color is blue." not in history: logger.warning("History seems incomplete.")
        if "Assistant: Your favorite color is blue." not in history: logger.warning("History seems incomplete.")

        # Check Remember This
        remember = contextual_memory.get_remember_this_content(test_session_id)
        print(f"\nRemember This Content:\n{remember}")
        if "User's favorite color is blue." not in remember: logger.warning("'Remember This' content might be missing.")

        # Check Episodic Search (Search for 'color')
        print("\nSearching Episodic Memory for 'color'...")
        episodic_results = episodic_memory.search_episodic_memory(
            query="color", session_id=test_session_id, top_k=3
        )
        print(f"\nEpisodic Search Results:\n{episodic_results}")
        if not episodic_results or "blue" not in episodic_results.lower():
             logger.warning("Episodic search results might be missing expected content.")

        # Optional: Clean up test data
        # You might want to manually delete the 'data/memory_test' directory after inspection
        # logger.info(f"Test complete. Memory data saved in: {test_memory_path}")

    except Exception as e:
        logger.error(f"An error occurred during the memory interaction test: {e}", exc_info=True) # Log traceback
        print(f"\n[ERROR] Failed during memory interaction test: {e}") # Print specific error

# --- Main Execution ---
if __name__ == "__main__":
    test_memory_flow()
    print("\n--- Memory Interaction Test Complete ---")
    print(f"NOTE: Test data was potentially written to/read from '{os.path.join(project_root, 'data', 'memory_test')}'")