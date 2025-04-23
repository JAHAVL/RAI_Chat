#!/usr/bin/env python3
"""
Enable Ollama LLM for RAI Chat

This script patches the necessary files to enable Ollama LLM instead of the mock engine.
It doesn't start any servers or launch any frontend components.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EnableOllamaLLM")

def patch_llm_api_server():
    """Patch the LLM API server to use Ollama by default"""
    try:
        # Path to llm_api_server.py
        server_path = Path("llm_Engine/llm_api_server.py")
        
        if not server_path.exists():
            logger.error(f"Could not find {server_path}. Make sure you're in the right directory.")
            return False
        
        # Read the file
        with open(server_path, "r") as f:
            content = f.read()
        
        # Check if we need to patch
        if 'def get_engine(engine_type="ollama"' in content:
            logger.info("LLM API server already set to use Ollama by default.")
            return True
        
        # Replace the default engine type
        content = content.replace(
            'def get_engine(engine_type="mock",',
            'def get_engine(engine_type="ollama",'
        )
        
        # Update the chat_completion function to use the specified engine
        content = content.replace(
            '# Always use MockEngine for now to ensure reliability\n            from llm_Engine.engines.mock_engine import MockEngine\n            engine = MockEngine(model_name=model_name)',
            'engine = get_engine(engine_type, model_name)'
        )
        
        # Write the file back
        with open(server_path, "w") as f:
            f.write(content)
        
        logger.info("Successfully patched LLM API server to use Ollama by default.")
        return True
    
    except Exception as e:
        logger.error(f"Error patching LLM API server: {str(e)}")
        return False

def main():
    """Main entry point"""
    logger.info("Enabling Ollama LLM for RAI Chat...")
    
    if not patch_llm_api_server():
        logger.error("Failed to patch LLM API server")
        return 1
    
    logger.info("""
Successfully enabled Ollama LLM!

To start the servers:
1. In one terminal: python -m llm_Engine.llm_api_server
2. In another terminal: python -m RAI_Chat.rai_api_server
3. Connect your frontend to RAI API at http://localhost:5001
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
