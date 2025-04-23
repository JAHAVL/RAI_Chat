"""
RAI_Chat module for AI Assistant app.
Contains all components related to the main chat assistant functionality.
"""

# Imports for backend components are removed from this top-level __init__.
# They should be imported directly where needed, e.g., within Backend modules.
# from RAI_Chat.memory.contextual_memory import ContextualMemoryManager # Moved
# from RAI_Chat.memory.episodic_memory import EpisodicMemoryManager # Moved

# Import conversation manager
# from RAI_Chat.conversation_manager import ConversationManager # Moved

# Import UI components (Commented out - Legacy PyQt6 UI, not needed for React/Electron frontend)
# from RAI_Chat.ui.chat_ui import ChatUI
# from RAI_Chat.ui.chat_library_ui import ChatLibraryUI
# from RAI_Chat.ui.ui_manager import UIManager
# from RAI_Chat.ui.ui_manager_api import UIManagerAPI

__all__ = [
    # List high-level sub-packages if desired, but avoid specific backend classes here.
    # "Backend", # Example, if you want to allow 'from RAI_Chat import Backend'
    # "Frontend" # Example
    # Keep empty for now to avoid exposing internal structure unnecessarily.
    
    # UI components are internal to Backend or Frontend
]
