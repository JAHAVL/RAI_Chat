# Refactoring Plan: Centralized Path Management

**Date:** 2025-04-02

**Goal:** Eliminate hardcoded file and directory paths within the Python codebase by defining them in a single, central location. This improves maintainability, readability, and consistency, making it easier to manage file structures and refactor code.

## Problem

Hardcoding paths (e.g., `"data/logs"`, `os.path.join("RAI_Chat", "memory")`) throughout the codebase makes the application brittle. If directory structures change or the application is deployed in a different environment, numerous code locations need modification, increasing the risk of errors.

## Proposed Solution

Create a dedicated Python module (e.g., `utils/path_manager.py`) responsible for defining and providing access to key application paths. Other modules will import and use this central module instead of constructing paths themselves.

**Key Features:**

1.  **Base Path Determination:** Dynamically determine the project's root directory at runtime (using `pathlib` or `os.path`).
2.  **Static Path Definitions:** Define constants or properties for fixed paths relative to the project root (e.g., `LOGS_DIR`, `DATA_DIR`).
3.  **Dynamic Path Functions:** Provide functions to generate paths that depend on runtime data (e.g., `get_user_data_dir(user_id)`).
4.  **Technology:** Utilize Python's `pathlib` module for robust and OS-agnostic path manipulation.

## Scope of Centralization

This system will define paths for:

*   **Shared Directories:** Key directories accessed by multiple parts of the application (e.g., `data/`, `logs/`, `modules/`).
*   **Configuration Files:** Location of primary configuration files.
*   **Entry Points/Key Scripts:** Paths to main executable scripts if needed elsewhere.
*   **Data Patterns:** Functions to generate paths for user-specific data, session files, memory storage, etc.

This system will **not** typically define:

*   Paths to files used strictly *within* a single module (internal implementation details).
*   Paths for short-lived temporary files (unless a central temporary directory is designated).
*   Resource files tightly coupled to a specific module (e.g., local templates).

The focus is on centralizing access to shared resources and structural landmarks.

## Implementation Steps

1.  **Create Module:** Create `utils/path_manager.py`.
2.  **Define Base Root:** Implement logic to find the project root reliably.
3.  **Identify Key Paths:** Review the codebase (using tools like `search_files` for path patterns) to identify critical hardcoded paths.
4.  **Populate `path_manager.py`:** Define constants and functions for the identified paths using `pathlib`.
5.  **Refactor Code:** Replace hardcoded paths throughout the application with imports and calls to `utils.path_manager`.
6.  **Testing:** Thoroughly test application functionality, especially file I/O operations, to ensure paths are resolved correctly.

## Example (Conceptual)

```python
# utils/path_manager.py
from pathlib import Path
from typing import Union

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
# ... other static paths

def get_user_data_dir(user_id: Union[str, int]) -> Path:
    return DATA_DIR / str(user_id)

def get_user_chats_dir(user_id: Union[str, int]) -> Path:
    return get_user_data_dir(user_id) / "chats"

# --- Usage (in another file) ---
# from utils.path_manager import LOGS_DIR, get_user_chats_dir
#
# log_file = LOGS_DIR / "app.log"
# user_chat_file = get_user_chats_dir(current_user_id) / "session_abc.json"
```

## Benefits

*   **Maintainability:** Easier structure changes.
*   **Readability:** Cleaner code.
*   **Consistency:** Uniform path access.
*   **Testability:** Easier path mocking.

## Final Data Structure (Implemented)

The refactoring resulted in the following user-scoped data structure within the main `data/` directory:

```
data/
└── {user_id}/              <-- Directory for each specific user
    ├── chats/            <-- Holds chat session files
    │   ├── {session_id}.json          <-- Message/Turn data for a session
    │   └── metadata_{session_id}.json <-- Metadata (title, timestamp) for a session
    │
    └── memory/           <-- Holds memory-specific files
        ├── archive/      <-- Archived chunks for episodic memory recall
        │   └── {session_id}_{chunk_id}.json
        │
        ├── episodic_summary_index.json   <-- Index mapping episodic chunk IDs to summaries
        └── user_profile.json             <-- Persistent user facts/preferences (semantic memory)
```

**Notes:**

*   The `data/users.db` file remains at the root of `data/` for authentication.
*   `ContextualMemoryManager` no longer persists its entire state to a single file; it loads individual sessions from the `chats/` directory via `ChatFileManager` as needed.
*   Log files are stored centrally under the project's `logs/` directory, typically named based on the component and user ID (e.g., `logs/conversation_user_1.log`, `logs/main_app.log`).