# Plan: MySQL Integration, File Structure & Auth Refactor

**Date:** 2025-04-03

**Author:** Roo

**Related Plans:**
*   `docs/file_structure_refactor_plan.md` (Details on filesystem structure, largely superseded or integrated here)
*   `docs/llm_client_concurrency_fix_plan.md` (Concurrency fix should ideally be addressed before or alongside this refactor)

## 1. Goals

1.  **Implement MySQL:** Replace the current SQLite database (`data/users.db`) with MySQL for storing core structured data (users, session metadata).
2.  **Refactor Project Structure:** Organize the project into clear top-level directories: `llm_Engine`, `RAI_Chat` (split into `Frontend` and `Backend`), and `Modules`.
3.  **Refactor Data Storage:**
    *   Utilize MySQL for structured data suitable for relational storage.
    *   Utilize the filesystem structure (based on `docs/file_structure_refactor_plan.md`) for larger, less structured data like session context blobs and transcripts.
    *   Ensure clear separation between user-level persistent data and session-specific data.
4.  **Flexible Authentication:** Implement an authentication system that can support both local user accounts (stored in MySQL) and external authentication providers (e.g., CRM integration) in the future.
5.  **Improve Maintainability:** Establish clearer boundaries between components (frontend, backend, core services, features).

## 2. Proposed Project Structure

```
.
├── llm_Engine/             # Existing LLM engine components
├── RAI_Chat/
│   ├── Frontend/           # React frontend application code
│   │   ├── public/
│   │   ├── src/
│   │   ├── package.json
│   │   └── ...
│   └── Backend/            # Python backend application code
│       ├── api/            # FastAPI endpoints (chat_api.py, etc.)
│       ├── core/           # Core backend services
│       │   ├── auth/       # Authentication service, strategies, models
│       │   ├── config/     # Backend configuration loading
│       │   ├── database/   # SQLAlchemy setup, models, repositories, migrations (Alembic)
│       │   └── logging/    # Logging setup (if needed beyond basic)
│       ├── managers/       # Business logic managers (conversation, memory, user session)
│       ├── utils/          # Backend-specific utilities
│       └── rai_api_server.py # Main backend server entry point (or similar)
├── Modules/                # Contains distinct feature modules (e.g., calendar, code_editor)
│   ├── calendar_module/
│   ├── code_editor_module/
│   └── ...
├── data/                   # User data stored on filesystem
│   └── {user_id}/
│       ├── sessions/
│       │   └── {session_id}/
│       │       ├── contextual_memory.json # Detailed session state blob
│       │       └── transcript.json        # Optional: Separate transcript file
│       └── memory/
│           ├── episodic/            # Files/structure for episodic memory
│           ├── remember_this.json   # User-level facts/preferences
│           └── ...                  # Other user-level memory files
├── docs/                   # Project documentation
├── scripts/                # Utility and maintenance scripts (migration, etc.)
├── tests/                  # Automated tests
├── .env                    # Environment variables (DB credentials, API keys)
├── .gitignore
├── requirements.txt
├── start_all.py            # Main application launcher script
└── README.md
```

```mermaid
graph TD
    A[Project Root] --> B(llm_Engine);
    A --> C(RAI_Chat);
    A --> D(Modules);
    A --> E(config, scripts, docs, data, etc.);

    C --> C1(Frontend);
    C --> C2(Backend);

    C1 --> C1a(src/);
    C1 --> C1b(public/);
    C1 --> C1c(package.json);

    C2 --> C2a(core/);
    C2 --> C2b(api/);
    C2 --> C2c(managers/);
    C2 --> C2d(utils/);
    C2 --> C2e(rai_api_server.py);

    C2a --> C2a1(database/);
    C2a --> C2a2(auth/);
    C2a --> C2a3(config/);

    D --> D1(calendar_module/);
    D --> D2(code_editor_module/);
    D --> D3(...);

    subgraph Filesystem Data Storage
        F[data/] --> F1({user_id}/);
        F1 --> F2(sessions/);
        F1 --> F3(memory/);
        F2 --> F4({session_id}/);
        F4 --> F5(contextual_memory.json);
        F4 --> F6(transcript.json);
        F3 --> F7(episodic/);
        F3 --> F8(remember_this.json);
    end

    C2a1 --> G[MySQL Database];
    F --> C2c; # Managers interact with filesystem data
    G --> C2a1; # Database core interacts with MySQL
    G --> C2a2; # Auth core interacts with MySQL (for local users)
```

## 3. Database Schema (MySQL - High Level)

Technology: **SQLAlchemy** (ORM), **Alembic** (Migrations)

Location: `RAI_Chat/Backend/core/database/models.py`

*   **`users` Table:**
    *   `user_id` (INT, Primary Key, Auto-increment)
    *   `username` (VARCHAR, Unique, Not Null) - For local auth
    *   `hashed_password` (VARCHAR, Nullable) - For local auth
    *   `crm_user_id` (VARCHAR, Nullable, Indexed) - Identifier from external CRM
    *   `auth_provider` (VARCHAR, Not Null, Default: 'local') - Indicates 'local' or CRM name
    *   `email` (VARCHAR, Nullable, Unique)
    *   `created_at` (TIMESTAMP, Default: CURRENT_TIMESTAMP)
    *   `last_login_at` (TIMESTAMP, Nullable)
    *   `is_active` (BOOLEAN, Default: True)
    *   ... (other user profile fields as needed)

*   **`sessions` Table:**
    *   `session_id` (VARCHAR/UUID, Primary Key) - Matches filesystem folder name
    *   `user_id` (INT, Foreign Key -> users.user_id, Not Null, Indexed)
    *   `title` (VARCHAR, Nullable) - User-defined or auto-generated title
    *   `created_at` (TIMESTAMP, Default: CURRENT_TIMESTAMP)
    *   `last_activity_at` (TIMESTAMP, Default: CURRENT_TIMESTAMP, Indexed)
    *   `metadata_json` (JSON, Nullable) - Any other structured metadata about the session

*   **(Optional) `user_memory_facts` Table:**
    *   `fact_id` (INT, Primary Key, Auto-increment)
    *   `user_id` (INT, Foreign Key -> users.user_id, Not Null, Indexed)
    *   `fact_key` (VARCHAR, Not Null)
    *   `fact_value` (TEXT, Not Null)
    *   `created_at` (TIMESTAMP)
    *   `last_accessed_at` (TIMESTAMP)
    *   *(Index on user_id, fact_key)*

## 4. Filesystem Data Structure

Location: `data/` (Managed by backend managers)

*   Uses the structure defined in `docs/file_structure_refactor_plan.md`.
*   `data/{user_id}/sessions/{session_id}/contextual_memory.json`: Stores detailed turn-by-turn context, summaries, state for a specific chat session. Loaded/saved by `ContextualMemoryManager`.
*   `data/{user_id}/sessions/{session_id}/transcript.json` (Optional): If full transcripts are stored separately from context. Managed by `ChatFileManager`.
*   `data/{user_id}/memory/episodic/`: Stores data managed by `EpisodicMemoryManager`.
*   `data/{user_id}/memory/remember_this.json`: Stores user-level facts/preferences (unless moved to `user_memory_facts` table in MySQL). Managed by `ContextualMemoryManager` or a dedicated user memory manager.

## 5. Core Service Implementation (`RAI_Chat/Backend/core/`)

*   **Database (`core/database/`)**
    *   `connection.py`: Setup SQLAlchemy engine, sessionmaker based on `.env` config.
    *   `models.py`: Define SQLAlchemy models (User, Session, etc.).
    *   `repositories.py` (Optional but Recommended): Classes like `UserRepository`, `SessionRepository` to abstract database interactions.
    *   `alembic/`: Alembic migration environment setup.
*   **Authentication (`core/auth/`)**
    *   `service.py`: `AuthService` class.
        *   `authenticate(credentials)` method: Takes username/password or CRM token/code. Determines strategy based on config or credentials type. Returns `User` object or None.
        *   `get_user_by_id(user_id)`: Retrieves user from DB.
        *   `create_local_user(username, password, email)`: Creates user in DB.
    *   `strategies.py`:
        *   `LocalStrategy`: Verifies credentials against `users` table using `UserRepository`.
        *   `CRMStrategy` (Interface/Placeholder): Defines methods needed for CRM auth (e.g., `authenticate_crm(token)`, `get_crm_user_info(token)`). Actual implementation depends on the specific CRM.
    *   `models.py`: Pydantic or dataclass models for user representation passed around the app (distinct from DB models).
*   **Configuration (`core/config/`)**
    *   Load database URL, secrets, auth settings from `.env`.

## 6. Manager Refactoring

*   **`UserSessionManager` (`managers/user_session_manager.py`)**
    *   Remove direct DB interaction (SQLite).
    *   Use `AuthService` to validate user credentials/tokens and get `user_id`.
    *   Instantiate other managers (`ConversationManager`, memory managers, `ChatFileManager`) with the validated `user_id`.
    *   Manage the in-memory cache of active user managers.
*   **`ContextualMemoryManager` (`managers/memory/contextual_memory.py`)**
    *   Adapt to load/save session context from `data/{user_id}/sessions/{session_id}/contextual_memory.json`.
    *   Load/save user-level memory (`remember_this.json`) from `data/{user_id}/memory/` OR interact with `UserMemoryRepository` if moved to MySQL.
    *   Requires `user_id` and `session_id` for its operations.
*   **`ConversationManager` (`managers/conversation_manager.py`)**
    *   Use `SessionRepository` (via injected service) or `ChatFileManager` to get session metadata (like title).
    *   Trigger `ContextualMemoryManager.load_session_context(session_id)` on session load/switch.
    *   Trigger `ContextualMemoryManager.save_session_context(session_id)` on session save.
    *   Interact with `ChatFileManager` if transcripts are stored separately.
*   **`ChatFileManager` (`managers/chat_file_manager.py`)**
    *   If transcripts are separate: Manage `transcript.json` files in `data/{user_id}/sessions/{session_id}/`.
    *   If session listing relies on DB: Remove logic for `chat_metadata.json`. Methods like `list_sessions` would query the `sessions` table via `SessionRepository`.
    *   If session listing uses filesystem: Manage `data/{user_id}/chat_metadata.json` (less likely if DB is used).
*   **`EpisodicMemoryManager` (`managers/memory/episodic_memory.py`)**
    *   Ensure all file paths point within `data/{user_id}/memory/episodic/`.

## 7. Authentication Flow

1.  Frontend sends credentials (local username/password or CRM token/code) to a backend API endpoint (e.g., `/api/auth/login`).
2.  API endpoint calls `AuthService.authenticate(credentials)`.
3.  `AuthService` selects the appropriate strategy (Local or CRM).
4.  **Local:** `LocalStrategy` uses `UserRepository` to query MySQL for the user and verify the password hash.
5.  **CRM:** `CRMStrategy` validates the token/code with the CRM API, retrieves CRM user info. `AuthService` might then:
    *   Look up the user in local DB via `crm_user_id`.
    *   If not found, potentially create a new local user record linked to the `crm_user_id`.
6.  If authentication succeeds, `AuthService` returns a consistent `User` object (containing `user_id`).
7.  Backend generates a session token (e.g., JWT) containing the `user_id` and returns it to the frontend.
8.  Subsequent frontend requests include the session token. Backend middleware verifies the token and extracts the `user_id` to authorize requests and scope data access.

## 8. Migration Strategy

1.  **Backup:** **CRITICAL: Back up the entire existing `data/` directory and `data/users.db` file.**
2.  **Setup MySQL:** Ensure MySQL server is running and accessible. Create the database schema using Alembic migrations (`alembic upgrade head`).
3.  **Migrate Users:**
    *   Create a script (`scripts/migrate_users_sqlite_to_mysql.py`).
    *   Read users from `data/users.db`.
    *   For each user, insert a corresponding record into the MySQL `users` table using SQLAlchemy models/repositories. Hash passwords appropriately if needed (though bcrypt hashes are usually portable).
4.  **Migrate/Organize Filesystem Data:**
    *   Create a script (`scripts/organize_filesystem_data.py`).
    *   Iterate through existing user data locations (e.g., `RAI_Chat/memory/`, `data/{user_id}/chats/`).
    *   Create the new structure: `data/{user_id}/sessions/` and `data/{user_id}/memory/`.
    *   Move/copy existing session files (`*.json`) into corresponding `data/{user_id}/sessions/{session_id}/contextual_memory.json` (or `transcript.json`). Extract `session_id` from filenames.
    *   Move/copy existing user memory files (`contextual_sessions.json` parts, `episodic`, etc.) into `data/{user_id}/memory/`.
5.  **Populate Session Metadata:**
    *   Modify the filesystem migration script (Step 4) or create a new one.
    *   After organizing files, iterate through the `data/{user_id}/sessions/` directories.
    *   For each session found, create an entry in the MySQL `sessions` table (linking `session_id` to the migrated `user_id`). Populate `created_at`, `last_activity_at` from file timestamps if possible, or set defaults.

## 9. Verification Steps

*   Run unit tests for refactored core services and managers.
*   Run migration scripts on test data, verify results in MySQL and filesystem.
*   Perform manual testing as outlined in `docs/file_structure_refactor_plan.md` (Section 4), ensuring:
    *   Local user registration and login work via MySQL.
    *   New sessions create correct DB entries and filesystem folders/files.
    *   Existing sessions (post-migration) load correctly from DB metadata and filesystem context.
    *   User memory persists across sessions (checking DB or files as appropriate).
    *   Session listing and deletion work correctly via DB/filesystem operations.
    *   (Future) Test CRM login flow once implemented.

## 10. Risks and Mitigation

*   **Complexity:** High risk due to simultaneous changes in DB, filesystem structure, core services, and multiple managers.
    *   **Mitigation:** Incremental implementation where possible. Strong unit testing. Thorough manual testing. Address concurrency issues first.
*   **Data Loss/Corruption:** Significant risk during migration and due to potential bugs.
    *   **Mitigation:** **MANDATORY BACKUPS**. Test migration scripts extensively. Add robust error handling and logging.
*   **Performance:** Storing very large JSON blobs (`contextual_memory.json`) might have performance implications if frequently loaded/saved, even on filesystem. Querying large numbers of sessions from the DB needs efficient indexing.
    *   **Mitigation:** Monitor performance. Consider optimizations like lazy loading context, database indexing (`user_id`, `last_activity_at` on `sessions`). Evaluate if parts of `contextual_memory.json` could be stored in structured DB tables if needed later.
*   **Authentication Flaws:** Incorrect implementation of auth strategies or token handling could lead to security vulnerabilities.
    *   **Mitigation:** Follow security best practices for password hashing (bcrypt), token management (JWT recommended), input validation. Careful review of CRM integration logic.