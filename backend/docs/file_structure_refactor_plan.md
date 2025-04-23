# Plan: File Structure Refactoring

**Date:** 2025-03-31

**Author:** Roo

**Related Plan:** `llm_client_concurrency_fix_plan.md` (This plan should be implemented *after* the concurrency fix)

## 1. Goal

To refactor the storage structure for user data (sessions, memory) to improve organization, clarity, and separation between session-specific context and persistent user-level memory, as requested.

## 2. Target File Structure

```
data/
└── {user_id}/
    ├── sessions/                 # Folder containing all sessions for the user
    │   ├── {session_id_1}/       # Folder for a specific session
    │   │   └── contextual_memory.json  # Session-specific state (turns, summaries)
    │   │   └── transcript.json         # Optional: Full transcript if stored separately
    │   ├── {session_id_2}/
    │   │   └── ...
    │   └── ...
    ├── memory/                   # Folder for user-level persistent memory
    │   ├── episodic/             # User-level episodic data (across all sessions)
    │   │   └── ...               # Specific files/structure for episodic memory store
    │   ├── remember_this.json    # User-level facts/preferences to remember
    │   ├── forget_this.json      # User-level items to forget (if persisted)
    │   └── user_profile.json     # Other user-level profile data?
    └── chat_metadata.json        # User-level index of session IDs, titles, timestamps
```

## 3. Implementation Steps

This refactoring primarily involves modifying how and where different manager classes read and write their data.

### 3.1. Modify `ContextualMemoryManager` (`RAI_Chat/memory/contextual_memory.py`)

-   **Objective:** Make this manager load/save session-specific context from session folders, while handling user-level memory separately.
-   **Changes:**
    1.  Update `__init__`: Load only user-level data (`remember_this`, `forget_this`, `user_profile`?) from `data/{user_id}/memory/`. Store this user-level data in dedicated attributes (e.g., `self.user_profile_data`).
    2.  Remove `self.session_memories` dictionary (which previously held all sessions' context).
    3.  Introduce `self.active_session_context = None` (or similar) to hold the loaded context for the currently active session.
    4.  Implement `_get_session_context_path(session_id)` helper method returning `data/{user_id}/sessions/{session_id}/contextual_memory.json`.
    5.  Implement `load_session_context(session_id)`:
        -   Reads the file at `_get_session_context_path(session_id)`.
        -   Parses the JSON content into `self.active_session_context`.
        -   Handles `FileNotFoundError` by initializing an empty `self.active_session_context` for a new session.
        -   Returns the loaded context (or the new empty structure).
    6.  Implement `save_session_context(session_id)`:
        -   Ensures the directory `data/{user_id}/sessions/{session_id}/` exists.
        -   Writes the current content of `self.active_session_context` to the file at `_get_session_context_path(session_id)`.
    7.  Refactor core methods (`get_context`, `process_user_message`, `process_assistant_message`, `get_formatted_history`, etc.) to operate on `self.active_session_context` instead of `self.session_memories[session_id]`. These methods will need the `session_id` to know which context they are implicitly working with (or it needs to be reliably set beforehand).
    8.  Refactor `reset_session_in_memory(session_id)`:
        -   Clear `self.active_session_context` if it matches `session_id`.
        -   Delete the file at `_get_session_context_path(session_id)`.
        -   Consider if associated episodic memory for the session also needs clearing via `EpisodicMemoryManager`.
    9.  Update methods handling user-level memory (`process_forget_command`, `get_remember_this_content`, etc.) to read/write directly to/from `self.user_profile_data` and save back to the user-level files in `data/{user_id}/memory/`.

### 3.2. Modify `ConversationManager` (`RAI_Chat/conversation_manager.py`)

-   **Objective:** Integrate with the refactored `ContextualMemoryManager` for session loading/saving.
-   **Changes:**
    1.  In `__init__` and `set_current_session(session_id)`: Call `self.contextual_memory.load_session_context(session_id)` after setting `self.current_session`.
    2.  In `save_current_chat()`: Call `self.contextual_memory.save_session_context(self.current_session)` to persist the session's context. Decide if transcript saving via `ChatFileManager` is still needed or if transcript data is now part of `contextual_memory.json`.
    3.  In `load_chat(session_id)`: Primarily rely on `self.contextual_memory.load_session_context(session_id)`. Adjust return value and logic based on whether `ChatFileManager` is still used for transcripts. Ensure `set_current_session` is called correctly.
    4.  In `delete_current_chat()`: Ensure it calls the updated `self.contextual_memory.reset_session_in_memory(self.current_session)`.

### 3.3. Modify `ChatFileManager` (`RAI_Chat/utils/chat_file_manager.py`)

-   **Objective:** Adapt to the new structure, potentially managing transcripts and the user-level session metadata.
-   **Changes:**
    1.  **Option A (Transcript in Contextual Memory):** If transcript data is moved into `contextual_memory.json`, this manager might become simpler, primarily managing the `chat_metadata.json` file.
        -   `list_sessions`: Reads `data/{user_id}/chat_metadata.json`.
        -   `save_session`: Updates/adds entry in `chat_metadata.json`.
        -   `delete_session_file`: Removes entry from `chat_metadata.json` (actual file deletion handled by `ContextualMemoryManager.reset_session_in_memory`).
        -   `get_session_messages`: Might become obsolete or read from `chat_metadata.json`.
    2.  **Option B (Separate Transcript File):** If `transcript.json` remains separate:
        -   Update `_get_session_filepath` to return `data/{user_id}/sessions/{session_id}/transcript.json`.
        -   Implement management of `chat_metadata.json` as described in Option A for listing/metadata purposes.
        -   `save_session` saves the transcript *and* updates metadata.
        -   `delete_session_file` deletes the transcript *and* updates metadata.

### 3.4. Modify `EpisodicMemoryManager` (`RAI_Chat/memory/episodic_memory.py`)

-   **Objective:** Ensure all data is stored within the user-level memory folder.
-   **Changes:**
    1.  Review all file path generation logic within the class.
    2.  Ensure all paths correctly point within `data/{user_id}/memory/episodic/`. Create this directory if it doesn't exist.

### 3.5. Modify API Endpoints (`RAI_Chat/rai_api_server.py`)

-   **Objective:** Ensure API calls correctly interact with the refactored managers.
-   **Changes:**
    1.  Review `/api/sessions` (GET): Ensure it uses the updated `ChatFileManager.list_sessions` (which likely reads `chat_metadata.json`).
    2.  Review `/api/sessions/<id>` (DELETE): Ensure it correctly triggers `ContextualMemoryManager.reset_session_in_memory` and `ChatFileManager.delete_session_file` (or equivalent metadata update).
    3.  Review `/api/sessions/<id>/history` (GET): Ensure it uses the updated `ChatFileManager.get_session_messages` or retrieves data appropriately based on where transcripts are stored.

### 3.6. Data Migration (Optional but Recommended)

-   Create a one-time script (`scripts/migrate_data_structure.py`?).
-   This script would:
    -   Iterate through existing user IDs in `data/`.
    -   Read old chat files (e.g., `data/{user_id}/chats/*.json`).
    -   Read old memory files (e.g., `RAI_Chat/memory/contextual_sessions.json`, user profiles).
    -   Create the new directory structure (`sessions/{id}/`, `memory/`).
    -   Write data into the new locations (`contextual_memory.json`, `transcript.json`, `remember_this.json`, etc.).
    -   Create the `chat_metadata.json` file.
    -   Carefully back up old data before running.

## 4. Verification Steps

1.  Run data migration script (if created).
2.  Restart the application.
3.  **New User/Session:** Register a new user, start a chat, send messages, check file system for correct structure (`sessions/{id}/contextual_memory.json`, `memory/episodic`, etc.).
4.  **Session Persistence:** Close and reopen the chat session, verify history/context is loaded correctly.
5.  **User Memory:** Test "remember this" commands, verify data appears in `memory/remember_this.json` and persists across different sessions for the same user.
6.  **Episodic Memory:** Perform actions that should trigger episodic memory saving/retrieval, verify data in `memory/episodic/` and check if relevant context appears in later sessions.
7.  **Session Listing/Loading:** Verify the chat library UI correctly lists sessions (reading `chat_metadata.json`) and loads them.
8.  **Session Deletion:** Delete a session via UI/API, verify the session folder (`sessions/{id}/`) is removed and the entry disappears from `chat_metadata.json`. Verify associated episodic/contextual memory is cleared if intended.
9.  **Existing User (Post-Migration):** Log in as a user whose data was migrated, verify their sessions and memory are loaded correctly.

## 5. Risks and Mitigation

-   **Risk:** High complexity due to changes in core state management (`ContextualMemoryManager`) and file I/O across multiple classes. High potential for bugs.
    -   **Mitigation:** Implement incrementally if possible. Write thorough unit tests for the refactored manager classes. Perform extensive manual testing (Verification Steps). Implement this *after* the simpler concurrency fix.
-   **Risk:** Data loss or corruption during migration or due to bugs in new save/load logic.
    -   **Mitigation:** **BACK UP** existing `data/` directory before migration/testing. Test migration script thoroughly on sample data first. Add robust error handling and logging to file operations.
-   **Risk:** Incorrectly managing the "active session context" leading to state bleeding between sessions (similar to the original concurrency bug, but caused by logic error instead of shared objects).
    -   **Mitigation:** Careful implementation and testing of `load_session_context`, `save_session_context`, and how `ConversationManager` triggers these.