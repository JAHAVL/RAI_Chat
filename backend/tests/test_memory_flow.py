import sys
import os
import logging
import time
import shutil # For cleanup

# Add project root to path to allow imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from RAI_Chat.memory.episodic_memory import EpisodicMemoryManager
from RAI_Chat.memory.contextual_memory import ContextualMemoryManager
from RAI_Chat.conversation_manager import ConversationManager

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MemoryTest")

# --- Test Config ---
TEST_MEMORY_DIR = "data/memory_test"
TEST_CONTEXTUAL_FILE = os.path.join(TEST_MEMORY_DIR, "contextual_memory_test.json")
NUM_TEST_TURNS = 15 # Reduce turns for quicker test with lowered limits
TEST_TOKEN_LIMIT = 500 # Set a very low limit to force pruning
TEST_PRUNE_AMOUNT = 100 # Prune at least this many tokens

# --- Cleanup ---
if os.path.exists(TEST_MEMORY_DIR):
    logger.warning(f"Removing existing test memory directory: {TEST_MEMORY_DIR}")
    shutil.rmtree(TEST_MEMORY_DIR)

# --- Initialization ---
logger.info("Initializing memory managers...")
episodic_manager = EpisodicMemoryManager(memory_dir=TEST_MEMORY_DIR)
contextual_manager = ContextualMemoryManager(
    episodic_memory_manager=episodic_manager,
    memory_file=TEST_CONTEXTUAL_FILE
)

logger.info("Initializing conversation manager...")
convo_manager = ConversationManager(
    contextual_memory_manager=contextual_manager,
    episodic_memory_manager=episodic_manager
)

logger.info("Starting test conversation...")
current_session_id = convo_manager.current_session # Get the session ID

# --- Temporarily Modify Limits for Testing ---
original_token_limit = ContextualMemoryManager.ACTIVE_TOKEN_LIMIT
original_prune_amount = ContextualMemoryManager.MIN_TOKENS_TO_PRUNE
ContextualMemoryManager.ACTIVE_TOKEN_LIMIT = TEST_TOKEN_LIMIT
ContextualMemoryManager.MIN_TOKENS_TO_PRUNE = TEST_PRUNE_AMOUNT
logger.warning(f"--- Temporarily lowered ContextualMemory limits for test: LIMIT={TEST_TOKEN_LIMIT}, PRUNE={TEST_PRUNE_AMOUNT} ---")

try:
    # --- Test Conversation Simulation ---
    test_inputs = [
        "Hi, my name is Alex.",
        "I live in San Francisco.",
        "What's the weather like there?", 
        "My favorite hobby is hiking.",
        "I have a cat named Luna.",
        "What was the first thing I told you?", 
        "Tell me about photosynthesis.", 
        "Do you remember my cat's name?", 
        "I also enjoy playing the guitar.",
        "What are my hobbies?", 
        "Forget that I like hiking.", 
        "What are my hobbies now?", 
        "Let's discuss the impact of AI on jobs.", 
        "What did I say my name was earlier?", 
        "My favorite food is pizza.",
        # Add more turns if needed, NUM_TEST_TURNS controls actual length
    ] * (NUM_TEST_TURNS // 15 + 1) 

    test_inputs = test_inputs[:NUM_TEST_TURNS] 

    for i, user_input in enumerate(test_inputs):
        logger.info(f"\n--- Turn {i+1}/{NUM_TEST_TURNS} ---")
        logger.info(f"User: {user_input}")

        time.sleep(0.5) 

        try:
            assistant_response = convo_manager.get_response(user_input)
            logger.info(f"Assistant: {assistant_response}")

            assert isinstance(assistant_response, str), f"Expected string response, got {type(assistant_response)}"
            logger.debug("[Assertion Passed] Response type is string.")

            try:
                 current_turns = contextual_manager.session_memories.get(current_session_id, {}).get("messages", [])
                 current_tokens = sum(contextual_manager._estimate_turn_tokens(turn) for turn in current_turns)
                 logger.info(f"Estimated active tokens: ~{current_tokens}")
                 # Check logs from ContextualMemoryManager for "PRUNING TRIGGERED"
            except Exception as e:
                 logger.warning(f"Could not estimate token count: {e}")

            logger.info(f"Current facts: {contextual_manager.session_memories.get(current_session_id, {}).get('user_profile', {}).get('facts', [])}")

        except Exception as e:
            logger.error(f"Error during get_response for turn {i+1}: {e}", exc_info=True)
            break 

    logger.info("\n--- Test Conversation Finished ---")
    logger.info(f"Final contextual memory state saved to: {contextual_manager.memory_file}")
    logger.info(f"Episodic archives (if any) in: {episodic_manager.archive_dir}")
    logger.info(f"Episodic summary index: {episodic_manager.summary_index_file}")
    logger.info("Manual inspection of logs and files recommended to verify archiving, summarization, and recall.")

finally:
    # --- Restore Original Limits ---
    ContextualMemoryManager.ACTIVE_TOKEN_LIMIT = original_token_limit
    ContextualMemoryManager.MIN_TOKENS_TO_PRUNE = original_prune_amount
    logger.warning(f"--- Restored ContextualMemory limits: LIMIT={original_token_limit}, PRUNE={original_prune_amount} ---")