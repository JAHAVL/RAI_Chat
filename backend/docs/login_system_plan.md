# Login System Implementation Plan

**Goal:** Implement a user authentication system (login/register) for the AI Assistant application. All user data (chats, memory, etc.) must be scoped to the logged-in user.

**Agreed Approach:**

1.  **Scope:** Gate the entire application access behind a login screen.
2.  **Credentials:** Store usernames and securely hashed passwords (using bcrypt) in a local SQLite database (`users.db`).
3.  **Data Storage:** Organize user-specific data within user-ID-based subdirectories (e.g., `data/<user_id>/chats/`, `data/<user_id>/memory/`).
4.  **Session Handling:** The user login establishes an authenticated session. Chat sessions (`session_id`) remain distinct conversation threads *within* the authenticated user's scope.
5.  **API Structure:** Authentication endpoints (`/api/auth/...`) will be added to the existing `RAI_Chat/rai_api_server.py`, but the core credential handling logic will reside in a separate module (`auth_db.py`) to facilitate future CRM integration.

## High-Level Architecture Changes

*   Introduce a new SQLite database (`users.db`) for user credentials.
*   Add authentication endpoints (`/api/auth/login`, `/api/auth/register`, `/api/auth/status`) to the RAI API Server.
*   Modify existing RAI API Server endpoints (e.g., `/api/chat`, `/api/sessions`) to require authentication via JWT (JSON Web Tokens).
*   Update backend components (`ChatFileManager`, memory managers) to handle user-specific data paths based on the authenticated user's ID.
*   Implement Login/Register UI and authentication token (JWT) handling in the Frontend (Electron/React).

## Architecture Diagram

```mermaid
graph TD
    A[User Launches App] --> B{Stored Auth Token?};
    B -- Yes --> C{Validate Token};
    B -- No --> D[Show Login UI];
    C -- Valid --> E[Main App UI];
    C -- Invalid --> D;
    D --> F(User Enters Credentials);
    F --> G[Frontend Sends Login Request];
    G --> H(RAI API: /api/auth/login);
    H --> I[Query User DB];
    I --> J{Verify Hash};
    J -- Valid --> K[Generate JWT];
    K --> L(RAI API Sends JWT);
    L --> M[Frontend Stores JWT];
    M --> E;
    J -- Invalid --> N(RAI API Sends Error);
    N --> D;

    E --> O(User Interacts - e.g., Sends Chat);
    O --> P[Frontend Sends API Request w/ JWT];
    P --> Q(RAI API: Protected Endpoint - e.g., /api/chat);
    Q --> R{Validate JWT};
    R -- Valid --> S[Extract user_id];
    S --> T[Load Data for user_id];
    T --> U[Process Request];
    U --> V[Save Data for user_id];
    V --> W(RAI API Sends Response);
    W --> E;
    R -- Invalid --> X(RAI API Sends 401 Error);
    X --> D;

    subgraph Frontend (Electron/React)
        B; C; D; E; F; G; M; O; P;
    end

    subgraph Backend (RAI API Server)
        H; I; J; K; L; N; Q; R; S; T; U; V; W; X;
    end

    subgraph Storage
        Y[SQLite users.db];
        Z[User Data Folders data/<user_id>/...];
    end

    I --> Y;
    T --> Z;
    V --> Z;

```

## Detailed Plan

**Phase 1: Backend Implementation (Complete)**

1.  **Database Setup:**
    *   **Dependency:** Add `bcrypt` to `requirements.txt`.
    *   **Create `auth_db.py` (or similar utility module):**
        *   Define path for `users.db` (e.g., in `./data/users.db`).
        *   Function `init_db()`: Creates `users.db` and a `users` table (`user_id INTEGER PRIMARY KEY AUTOINCREMENT`, `username TEXT UNIQUE NOT NULL`, `hashed_password TEXT NOT NULL`) if they don't exist.
        *   Function `add_user(username, password)`: Hashes the password using `bcrypt`, inserts the new user. Handles potential username conflicts.
        *   Function `get_user_by_username(username)`: Retrieves user record (including `user_id` and `hashed_password`).
        *   Function `verify_password(hashed_password, provided_password)`: Uses `bcrypt.checkpw()`.
    *   Call `init_db()` on `rai_api_server.py` startup.

2.  **Authentication Logic (`rai_api_server.py`):**
    *   **Dependency:** Add `PyJWT` to `requirements.txt`.
    *   **Configuration:** Define a `SECRET_KEY` for JWT signing (load from environment or config).
    *   **New Endpoints:**
        *   `POST /api/auth/register`: Takes `username`, `password`. Calls `auth_db.add_user()`. Returns success/failure.
        *   `POST /api/auth/login`: Takes `username`, `password`. Calls `auth_db.get_user_by_username()`, then `auth_db.verify_password()`. If valid, generates a JWT containing `{'user_id': user_id, 'username': username, 'exp': expiration_time}`. Returns the JWT token or error.
        *   `GET /api/auth/status`: (Requires Auth) Checks if the request has a valid token. Returns `{ "logged_in": True, "user": {"id": user_id, "username": username} }` or `{ "logged_in": False }`.
    *   **Authentication Decorator/Middleware:**
        *   Create a decorator (e.g., `@token_required`) to protect endpoints.
        *   Checks for `Authorization: Bearer <token>` header.
        *   Decodes/validates the JWT using the `SECRET_KEY`.
        *   If valid, extracts user payload (e.g., `g.current_user`).
        *   If invalid/missing, returns 401 Unauthorized.
    *   **Apply Decorator:** Add `@token_required` to endpoints needing protection (e.g., `/api/chat`, `/api/sessions`, `/api/memory`).

3.  **Data Path & Manager Scoping (`rai_api_server.py`, `utils/chat_file_manager.py`, memory managers):**
    *   **Modify `ChatFileManager.__init__`:** Accept `user_id`, construct user-specific `self.chats_dir` (e.g., `data/<user_id>/chats/`), use this path for all operations.
    *   **Modify Memory Managers (`ContextualMemoryManager`, `EpisodicMemoryManager`):** Accept `user_id`, construct user-specific paths for their data files within `data/<user_id>/memory/`.
    *   **Refactor `rai_api_server.py` Instantiation:** Remove global manager instances. Modify `get_or_create_session` to become `get_user_managers(user_id)` which retrieves/initializes managers scoped to the specific user. Protected routes call this using the authenticated user ID (`g.current_user['user_id']`).

**Phase 2: Frontend Implementation (`RAI_Chat/frontend/`) (Complete)**

4.  **UI Components:**
    *   Created `Login.tsx`, `Register.tsx`, and `AuthPage.tsx` components in `src/components/auth/`.
    *   Styled components using `styled-components` consistent with the application theme.
    *   Modified `App.jsx` to conditionally render `AuthPage` or the main `AppLayout` based on authentication state.

5.  **Authentication Flow:**
    *   **API Client (`src/api/rai_api.js`):** Added `register`, `login`, `setAuthToken` methods. Modified `_request` to include `Authorization` header. Corrected endpoint paths. Added token loading from `localStorage` on initialization.
    *   **State Management:** Created `AuthContext.tsx` (`src/context/`) using `useContext` and `useState` to manage `token`, `user`, `isLoading`, `error` state. Provides `login`, `register`, `logout`, `isAuthenticated` functions. Stores/retrieves JWT from `localStorage`.
    *   **App Startup:** `AuthProvider` in `App.jsx` checks `localStorage` for token on initial load.
    *   **Login/Register Components:** Use `useAuth` hook to call context functions and display loading/error states.
    *   **Logout:** Added logout button to `App.jsx` title bar, calling `logout` function from `AuthContext`.

**Phase 3: Testing & Refinement**

6.  **Testing:** Test registration, login (valid/invalid), protected routes (with/without token), data isolation between users, chat persistence per user, logout.
7.  **Refinement:** Fix bugs, improve error handling, consider security hardening.

**Security Considerations:**

*   **Password Hashing:** Use `bcrypt`.
*   **JWT Secret Key:** Keep secret.
*   **Token Storage (Frontend):** `localStorage` is acceptable for MVP, but be aware of XSS risks.
*   **Input Validation:** Sanitize inputs.

**Future Considerations:**

*   Password reset.
*   Migration to CRM backend.
*   Refresh tokens.
*   Organization-level roles/permissions.