import google.generativeai as genai
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key from .env file (created by set_gemini_key.py)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
logger.info(f"Loading .env file from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found in .env file or environment variables.")
    logger.error("GEMINI_API_KEY not found.")
else:
    try:
        # Mask most of the key for logging
        masked_key = f"...{api_key[-4:]}" if len(api_key) > 4 else api_key
        print(f"Using API Key: {masked_key}")
        logger.info(f"Configuring Gemini with API Key: {masked_key}")
        genai.configure(api_key=api_key)

        # 1. Verify connection by listing models
        print("\n--- Listing Models ---")
        models_listed = False
        try:
            for m in genai.list_models():
                 # Check if the desired model is supported for generateContent
                 if 'generateContent' in m.supported_generation_methods:
                     print(f"Model available: {m.name}")
                     models_listed = True
            if not models_listed:
                 print("No models found or API key issue.")
                 logger.warning("No models found or API key issue during listing.")
        except Exception as list_err:
             print(f"ERROR listing models: {list_err}")
             logger.error(f"Error listing models: {list_err}", exc_info=True)
        print("----------------------")

        # Proceed only if models were listed (indicates key is likely valid)
        if models_listed:
            # 2. Try a simple generation with explicit safety settings
            print("\n--- Testing Generation ---")
            # Use the default model from gemini_engine.py
            model_name_to_test = "gemini-2.5-pro" # Changed from gemini-1.5-flash-latest
            print(f"Using model: {model_name_to_test}")
            logger.info(f"Attempting generation with model: {model_name_to_test}")
            model = genai.GenerativeModel(
                model_name=model_name_to_test,
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            )
            prompt = "What is 1 + 1?"
            print(f"Prompt: {prompt}")
            logger.info(f"Sending prompt: {prompt}")
            response = model.generate_content(prompt)
            logger.info("Received response object from generate_content.")

            print("\n--- Response ---")
            try:
                # Attempt to access the text directly
                response_text = response.text
                print(f"Text: {response_text}")
                logger.info(f"Response text: {response_text}")
            except Exception as text_err:
                # If .text fails, log the error and check for blocking feedback
                print(f"ERROR accessing response.text: {text_err}")
                logger.warning(f"Could not access response.text: {text_err}")
                print("Checking prompt feedback...")
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                     feedback_str = str(response.prompt_feedback)
                     print(f"Prompt Feedback: {feedback_str}")
                     logger.warning(f"Prompt Feedback: {feedback_str}")
                     # Explicitly check for BLOCKING reason
                     if "BLOCK_REASON_SAFETY" in feedback_str:
                          print(">>> Safety blocking confirmed via prompt_feedback.")
                          logger.warning("Safety blocking confirmed via prompt_feedback.")
                else:
                     print("No prompt feedback available.")
                     logger.info("No prompt feedback available in response object.")
                # Log the full response object for detailed debugging
                try:
                    full_response_str = str(response)
                    print(f"Full Response Object: {full_response_str}")
                    logger.info(f"Full Response Object: {full_response_str}")
                except Exception as str_err:
                    print(f"Could not convert full response object to string: {str_err}")
                    logger.error(f"Could not convert full response object to string: {str_err}")
            print("----------------")
        else:
            print("\nSkipping generation test as model listing failed.")
            logger.warning("Skipping generation test due to model listing failure.")

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        logger.error(f"An unexpected error occurred during the minimal SDK test: {e}", exc_info=True)

print("\n--- Minimal SDK Test Complete ---")