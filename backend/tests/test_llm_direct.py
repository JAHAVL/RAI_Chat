import os
import sys
import json
import logging

# Add project root to sys.path for consistent imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Import the centralized LLM API interface from the api package
    from api.llm_engine.llm_api_interface import get_llm_api
except ImportError as e:
    logger.error(f"Failed to import LLM API interface: {e}")
    logger.error("Ensure the script is run from the project root or the PYTHONPATH is set correctly.")
    sys.exit(1)

def test_direct_llm_chat(message="Hello LLM, are you receiving this?"):
    """
    Tests direct communication with the LLM engine via the llm_api_bridge.
    """
    print("\n--- Testing Direct LLM Chat Completion ---")
    print(f"Message: {message}")

    try:
        # Get the LLM API instance
        llm_api = get_llm_api()
        logger.info("Successfully obtained LLMAPI instance.")

        # Prepare messages in the format expected by chat_completion
        messages = [{"role": "user", "content": message}]

        # Call chat_completion
        # We don't provide a session_id here for a simple stateless test
        response = llm_api.chat_completion(messages=messages, temperature=0.7, max_tokens=150)

        print("\n--- LLM Response ---")
        print(json.dumps(response, indent=2))
        print("--------------------\n")

        if response and response.get("role") == "assistant" and "Error" in response.get("content", ""):
             logger.warning("LLM API reported an error in the response content.")
        elif not response or response.get("role") != "assistant":
             logger.warning("Did not receive a valid assistant response.")


    except Exception as e:
        logger.error(f"An error occurred during the direct LLM test: {e}", exc_info=True)
        print("\n[ERROR] Failed to communicate with the LLM API.")
        print("Ensure the LLM API server ('llm_api_server.py' or similar) is running.")

if __name__ == "__main__":
    test_direct_llm_chat(message="What is 1 + 1?")
    print("\n--- Direct LLM Test Complete ---")