"""
Module loader for AI Assistant App.
Handles loading of modules like video and memory.
"""
import os
import logging
from pathlib import Path
from typing import Tuple, Any, Optional

from config import AppConfig

logger = logging.getLogger(__name__)

# Updated return signature - only returns llm_engine
def load_modules() -> Optional[Any]:
    """
    Load core modules like the LLM engine.
    Memory managers are user-scoped and handled by UserSessionManager.
    Video module is being removed.

    Returns:
        - llm_engine: LLM engine instance or None
    """
    logger.info("Loading modules...")
    
    # Load modules
    # video_module = load_video_module() # Removed call
    llm_engine = load_llm_engine()

    return llm_engine

# Removed load_video_module function

def load_llm_engine() -> Optional[Any]:
    """
    Load the LLM engine.
    
    Returns:
        LLM engine instance or None
    """
    try:
        logger.info("Loading LLM engine...")
        
        # Import the Mock engine from root-level llm folder
        from llm.engines.mock_engine import MockEngine
        
        # Get the model name from config
        model_name = AppConfig.LLM_MODEL or "phi-2.Q4_K_M.gguf"
        
        logger.info(f"Using LLM type: ollama (mock)")
        logger.info(f"Using model name: {model_name}")
        
        # Create the Mock engine
        llm_engine = MockEngine(model_name=model_name)
        
        logger.info(f"LLM engine (mock) loaded successfully with model: {model_name}")
        return llm_engine
    except Exception as e:
        logger.error(f"Error loading LLM engine: {str(e)}")
        logger.exception("Detailed exception information:")
        return None

# Removed load_memory_manager function entirely
