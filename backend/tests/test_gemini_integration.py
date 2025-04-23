"""
Test script for Gemini integration
This script checks if the Gemini 2.5 Pro integration is working correctly.
"""
import os
import sys
import logging
import json
import time
from pprint import pprint
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import relevant modules
from llm_Engine.engines.gemini_engine import GeminiEngine
from llm_Engine.config import LLM_ENGINE_CONFIG

def test_api_key_availability():
    """Test if the Gemini API key is available"""
    print("\n--- Testing API Key Availability ---")
    
    # Check environment variable
    api_key = os.environ.get('GEMINI_API_KEY')
    if api_key:
        print("✅ API key found in environment variables")
    else:
        print("❌ API key not found in environment variables")
    
    # Try initializing the engine
    engine = GeminiEngine(model_name="models/gemini-2.5-pro-exp-03-25")
    if engine.api_key:
        print(f"✅ API key found by the engine (source: {'environment' if api_key else 'config/file'})")
    else:
        print("❌ Engine could not find an API key")
    
    return engine.api_key is not None

def test_gemini_connection(engine=None):
    """Test connection to Gemini API"""
    print("\n--- Testing Gemini API Connection ---")
    
    if engine is None:
        engine = GeminiEngine(model_name="models/gemini-2.5-pro-exp-03-25")
    
    if not engine.api_key:
        print("❌ No API key available, skipping connection test")
        return False
    
    if engine.server_available:
        print("✅ Connection to Gemini API successful")
        return True
    else:
        print("❌ Could not connect to Gemini API")
        return False

def test_chat_completion(engine=None):
    """Test chat completion with Gemini"""
    print("\n--- Testing Chat Completion ---")
    
    if engine is None:
        engine = GeminiEngine(model_name="models/gemini-2.5-pro-exp-03-25")
    
    if not engine.server_available:
        print("❌ Gemini API not available, skipping chat completion test")
        return False
    
    try:
        # Simple test message
        messages = [
            {"role": "user", "content": "Hello, what's your name and what LLM are you?"}
        ]
        
        start_time = time.time()
        response = engine.chat_completion(messages, temperature=0.7, max_tokens=100)
        elapsed_time = time.time() - start_time
        
        print(f"✅ Chat completion successful (took {elapsed_time:.2f} seconds)")
        print("\nResponse:")
        print("-" * 50)
        print(response["choices"][0]["message"]["content"])
        print("-" * 50)
        return True
    except Exception as e:
        print(f"❌ Chat completion failed: {str(e)}")
        return False

def test_system_message_handling(engine=None):
    """Test system message handling with Gemini"""
    print("\n--- Testing System Message Handling ---")
    
    if engine is None:
        engine = GeminiEngine(model_name="models/gemini-2.5-pro-exp-03-25")
    
    if not engine.server_available:
        print("❌ Gemini API not available, skipping system message test")
        return False
    
    try:
        # Test with system message
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant named Gemini Helper."},
            {"role": "user", "content": "What's your name?"}
        ]
        
        response = engine.chat_completion(messages, temperature=0.7, max_tokens=100)
        
        print("✅ Chat completion with system message successful")
        print("\nResponse:")
        print("-" * 50)
        print(response["choices"][0]["message"]["content"])
        print("-" * 50)
        return True
    except Exception as e:
        print(f"❌ System message test failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("\n===== GEMINI 2.5 PRO INTEGRATION TEST =====\n")
    
    # Step 1: Test API key
    api_key_available = test_api_key_availability()
    if not api_key_available:
        print("\n❌ Test failed: No API key available")
        print("Please set your Gemini API key using:")
        print("python -m llm_Engine.set_gemini_key --key YOUR_API_KEY")
        return
    
    # Initialize engine once for all tests
    engine = GeminiEngine(model_name="models/gemini-2.5-pro-exp-03-25")
    
    # Step 2: Test connection
    connection_success = test_gemini_connection(engine)
    if not connection_success:
        print("\n❌ Test failed: Could not connect to Gemini API")
        return
    
    # Step 3: Test chat completion
    chat_success = test_chat_completion(engine)
    
    # Step 4: Test system message handling
    system_msg_success = test_system_message_handling(engine)
    
    # Summary
    print("\n===== TEST SUMMARY =====")
    print(f"API Key: {'✅ Available' if api_key_available else '❌ Not available'}")
    print(f"API Connection: {'✅ Success' if connection_success else '❌ Failed'}")
    print(f"Chat Completion: {'✅ Success' if chat_success else '❌ Failed'}")
    print(f"System Message: {'✅ Success' if system_msg_success else '❌ Failed'}")
    
    if all([api_key_available, connection_success, chat_success, system_msg_success]):
        print("\n🎉 All tests passed! Your Gemini integration is working correctly.")
        print("\nTo start using Gemini with your AI Assistant, make sure the LLM API server is")
        print("running with the following command:")
        print("\nPYTHONPATH=. LLM_API_PORT=6000 python -m llm_Engine.llm_api_server")
    else:
        print("\n❌ Some tests failed. Review the issues above and try again.")

if __name__ == "__main__":
    main()
