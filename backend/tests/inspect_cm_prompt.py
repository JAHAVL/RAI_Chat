import os
import sys
import logging
from datetime import datetime
# Removed unused mock imports

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
    from RAI_Chat.prompts import build_system_prompt
except ImportError as e:
    logger.error(f"Failed to import necessary components: {e}")
    logger.error("Ensure the script is run from the project root or the PYTHONPATH is set correctly.")
    sys.exit(1)

# --- Test Function ---
def inspect_prompt_generation(user_input_to_test="What is my favorite color?"):
    """
    Simulates ConversationManager context gathering and prompt building, then prints the result.
    """
    print("\n--- Inspecting ConversationManager Prompt Generation ---")
    test_session_id = f"test_inspect_prompt_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"Using Session ID: {test_session_id}")

    try:
        # 1. Initialize Memory Managers (using default paths)
        logger.info("Initializing Memory Managers...")
        # test_memory_path = os.path.join(project_root, 'data', 'memory_test') # Removed test path
        # os.makedirs(test_memory_path, exist_ok=True) # Removed test path creation
        episodic_memory = EpisodicMemoryManager() # Removed base_path argument
        contextual_memory = ContextualMemoryManager(
            episodic_memory_manager=episodic_memory
            # base_path=test_memory_path # Removed base_path argument
        )
        contextual_memory._ensure_session_exists(test_session_id)
        logger.info("Memory Managers Initialized.")

        # 2. Simulate Conversation History
        logger.info("Simulating conversation history...")
        # Turn 1
        user_msg_1 = "My favorite color is blue."
        contextual_memory.process_user_message(test_session_id, user_msg_1)
        assistant_resp_data_1 = {
            "llm_response": {
                "response_tiers": {"tier1": "Ack color.", "tier2": "User fav color blue.", "tier3": "Okay, blue."},
                "extracted_info": {"preferences": ["favorite_color: blue"]},
                "remember_this": ["User's favorite color is blue."], "forget_this": []
            }, "timestamp": datetime.now().isoformat()
        }
        contextual_memory.process_assistant_message(assistant_resp_data_1, user_msg_1, test_session_id)

        # Turn 2 (The user input we are testing)
        logger.info(f"Processing the target user input: '{user_input_to_test}'")
        contextual_memory.process_user_message(test_session_id, user_input_to_test)
        # We don't simulate the assistant response for this turn, as we want the prompt *before* generation

        # 3. Gather Context Components (Mimicking ConversationManager.get_response)
        logger.info("Gathering context components...")

        # --- Get Available Context ---
        # NOTE: get_tier1_context and get_tier2_context do not exist on ContextualMemoryManager.
        # We will construct the 'contextual_memory' argument for build_system_prompt
        # using only episodic summaries for this test.

        # Episodic Summaries (Depth 0 for simplicity)
        episodic_summaries = episodic_memory.search_episodic_memory(
            user_input_to_test, test_session_id, top_k=5, search_depth=0
        ) or "" # Ensure it's a string
        print(f"[DEBUG] Episodic Summaries (Depth 0):\n{episodic_summaries}\n")

        # Use only episodic summaries for the 'contextual_memory' part of the prompt
        contextual_memory_str = ""
        if episodic_summaries:
             contextual_memory_str = f"RELATED PAST CONVERSATIONS (Summaries):\n{episodic_summaries}"
        print(f"[DEBUG] Contextual Memory String (Episodic Only):\n{contextual_memory_str}\n")

        # Other prompt arguments that ARE available
        conversation_history_str = contextual_memory.get_formatted_history(test_session_id, limit=20)
        print(f"[DEBUG] Formatted History (Limit 20):\n{conversation_history_str}\n")
        remember_this_str = contextual_memory.get_remember_this_content(test_session_id)
        print(f"[DEBUG] Remember This:\n{remember_this_str}\n")
        forget_this_str = contextual_memory.get_forget_this_content(test_session_id)
        print(f"[DEBUG] Forget This:\n{forget_this_str}\n")
        specialized_instructions_str = "" # Assuming none for this test

        # 4. Build the System Prompt
        logger.info("Building the system prompt...")
        system_prompt = build_system_prompt(
            conversation_history=conversation_history_str,
            contextual_memory=contextual_memory_str, # Combined T1/T2/Episodic
            specialized_instructions=specialized_instructions_str,
            remember_this_content=remember_this_str,
            forget_this_content=forget_this_str
        )

        # 5. Print the Results
        print("\n" + "="*30)
        print("   PROMPT INSPECTION RESULT")
        print("="*30)
        print(f"\n--- User Input Sent to LLM Layer ---")
        print(user_input_to_test)
        print("-"*(len(user_input_to_test) + 4))

        print(f"\n--- System Prompt Sent to LLM Layer ---")
        print(system_prompt)
        print("-"*(len("--- System Prompt Sent to LLM Layer ---")))
        print("="*30 + "\n")

        # Optional: Clean up test data
        # logger.info(f"Test complete. Memory data saved in: {test_memory_path}")

    except Exception as e:
        logger.error(f"An error occurred during prompt inspection: {e}", exc_info=True) # Log the full traceback
        print(f"\n[ERROR] Failed during prompt inspection test: {e}") # Print the specific error

# --- Main Execution ---
if __name__ == "__main__":
    # You can change the input message here to test different scenarios
    inspect_prompt_generation(user_input_to_test="What is my favorite color?")
    # inspect_prompt_generation(user_input_to_test="Tell me about yesterday's meeting.") # Example for episodic
    print("\n--- Prompt Inspection Test Complete ---")