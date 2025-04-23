"""
Check available Gemini models
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load API key from environment
load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')

if not api_key:
    print("No API key found. Please set your GEMINI_API_KEY first.")
    exit(1)

# Configure the Gemini API
genai.configure(api_key=api_key)

# List all available models
print("Available Gemini models:")
print("-" * 50)

try:
    available_models = genai.list_models()
    
    for model in available_models:
        # Only print Gemini models
        if "gemini" in model.name:
            print(f"Model: {model.name}")
            print(f"Supported methods: {', '.join(model.supported_generation_methods)}")
            print("-" * 50)
            
    if not any("gemini" in model.name for model in available_models):
        print("No Gemini models found with your API key.")
        print("You might need to enable the Gemini API for your Google Cloud project.")
        
except Exception as e:
    print(f"Error listing models: {str(e)}")
    print("\nTrying alternative approach...")
    
    # Hardcoded list of common Gemini models to try
    common_models = [
        "gemini-1.0-pro", 
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro",
        "gemini-pro-vision"
    ]
    
    print("\nCommon Gemini models that might be available:")
    print("-" * 50)
    for model_name in common_models:
        print(f"Model: {model_name}")
    print("-" * 50)
    print("\nTo use one of these models, update config.py with the correct model name.")
