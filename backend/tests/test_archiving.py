import os
import sys
import logging
from datetime import datetime
import time

# --- Setup Paths ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configure Logging ---
# Ensure logs go to console for easy viewing during test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- Import Components ---
try:
    from RAI_Chat.memory.contextual_memory import ContextualMemoryManager
    from RAI_Chat.memory.episodic_memory import EpisodicMemoryManager
    # We need get_llm_api because EpisodicMemoryManager uses it for summarization
    from llm_Engine.llm_api_bridge import get_llm_api
except ImportError as e:
    logger.error(f"Failed to import necessary components: {e}")
    logger.error("Ensure the script is run from the project root or the PYTHONPATH is set correctly.")
    sys.exit(1)

# --- Test Function ---
def test_archiving_trigger(num_turns=50, chars_per_turn=1000):
    """
    Tests if the archiving process is triggered when token limits are exceeded.
    Simulates conversation turns without actual LLM calls for main responses.
    """
    print("\n--- Testing Episodic Memory Archiving Trigger ---")
    test_session_id = f"test_archiving_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"Using Session ID: {test_session_id}")
    print(f"Simulating {num_turns} turns with approx {chars_per_turn} chars each...")

    # Ensure the LLM API server is running for the summarization call within EpisodicMemoryManager
    llm_api = get_llm_api()
    if not llm_api.client.health_check().get("status") == "ok":
         print("\n[ERROR] LLM API Server is not running or reachable. Archiving summarization will fail.")
         print("Please ensure llm_api_server.py is running.")
         # Optionally exit, or let it fail during summarization
         # sys.exit(1)


    try:
        # 1. Initialize Memory Managers (using default paths)
        logger.info("Initializing Memory Managers...")
        episodic_memory = EpisodicMemoryManager()
        contextual_memory = ContextualMemoryManager(episodic_memory_manager=episodic_memory)
        contextual_memory._ensure_session_exists(test_session_id)
        logger.info("Memory Managers Initialized.")

        # 2. Simulate Conversation Turns
        logger.info("Simulating conversation turns...")
        for i in range(num_turns):
            # Create placeholder user input and assistant response data
            user_input = f"This is simulated user message {i+1}. " + ("a" * (chars_per_turn // 2))
            assistant_t3 = f"This is simulated assistant response {i+1}. " + ("b" * (chars_per_turn // 2))

            # Simulate the structure expected by process_assistant_message
            # Use placeholder T1/T2 summaries
            simulated_response_data = {
                "user_message_analysis": {
                    "timestamp": datetime.now().isoformat(),
                    "speaker": "User",
                    "prompt_tiers": {"tier1": f"User msg {i+1} summary T1", "tier2": f"User msg {i+1} summary T2"}
                },
                "llm_response": {
                    "timestamp": datetime.now().isoformat(),
                    "speaker": "LLM",
                    "response_tiers": {"tier1": f"Assist resp {i+1} T1", "tier2": f"Assist resp {i+1} T2", "tier3": assistant_t3}
                }
            }

            # Process the simulated turn
            # process_user_message is mostly logging now, main action is in process_assistant_message
            contextual_memory.process_user_message(test_session_id, user_input)
            contextual_memory.process_assistant_message(simulated_response_data, user_input, test_session_id)

            # Optional: Add a small delay to mimic real interaction time
            # time.sleep(0.01)

            if (i + 1) % 10 == 0:
                 logger.info(f"Completed simulation of turn {i+1}/{num_turns}")


        logger.info("Finished simulating turns.")
        print("\n--- Archiving Test Complete ---")
        print("Please check the application logs (e.g., logs/contextual_memory.log or console output)")
        print("for messages like '--- PRUNING TRIGGERED ---' and 'Successfully archived chunk...'")
        # print(f"Also check the '{episodic_memory.base_path}' directory for summary files related to session '{test_session_id}'.") # Removed line causing error


    except Exception as e:
        logger.error(f"An error occurred during the archiving test: {e}", exc_info=True)
        print(f"\n[ERROR] Failed during archiving test: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # Adjust num_turns and chars_per_turn based on ACTIVE_TOKEN_LIMIT (30000)
    # and the estimation heuristic (4 chars/token)
    # Target: num_turns * chars_per_turn / 4 > 30000
    # Example: 50 turns * 2500 chars/turn / 4 = 31250 tokens (should trigger)
    test_archiving_trigger(num_turns=50, chars_per_turn=2500)