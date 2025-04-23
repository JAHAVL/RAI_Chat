# Backend Troubleshooting Log: ECONNREFUSED ::1:6102

This log details the steps taken to diagnose and resolve the `Error: connect ECONNREFUSED ::1:6102` error encountered when the frontend attempts to connect to the backend services.

## Initial Issue

-   **Symptom:** Frontend displays `Error: connect ECONNREFUSED ::1:6102`.
-   **Initial Diagnosis:** The error indicates the frontend tried to connect to the backend API server at the IPv6 loopback address (`::1`) on port `6102`, but the connection was refused. This usually means the backend service wasn't running or wasn't listening on that specific address/port combination.

## Troubleshooting Steps

1.  **Restart Backend Services:**
    *   **Action:** Executed `python RAI_Chat/Backend/start_all.py` to restart all backend components.
    *   **Result:** The script started, but the user reported the error persisted even after waiting, suggesting the issue wasn't just a temporary shutdown.

2.  **Investigate Backend Startup (`start_all.py`):**
    *   **Action:** Read `RAI_Chat/Backend/start_all.py`.
    *   **Finding:** Confirmed `RAI_API_PORT` was set to `6102`. Noticed the script executed `RAI_Chat/Backend/rai_api_server.py` directly (`python -m ...`) rather than using a WSGI server like `waitress` (which was used for the LLM API server).

3.  **Investigate RAI API Server (`rai_api_server.py`):**
    *   **Action:** Read `RAI_Chat/Backend/rai_api_server.py`.
    *   **Finding:** The script defines a Flask app (`app = Flask(__name__)`) but lacks an `app.run()` or `waitress.serve()` call. It relies entirely on the calling script (`start_all.py`) to serve it.

4.  **Modify `start_all.py` to Use Waitress for RAI API:**
    *   **Action:** Applied a diff to `RAI_Chat/Backend/start_all.py` to change the `start_rai_api_server` function. Instead of `python -m RAI_Chat.Backend.rai_api_server`, it now uses `python -m waitress --host=0.0.0.0 --port=6102 RAI_Chat.Backend.rai_api_server:app`. Binding to `0.0.0.0` ensures listening on both IPv4 and IPv6 loopback addresses.
    *   **Result:** Restarted services.

5.  **Test RAI API Health:**
    *   **Action:** Executed `curl http://localhost:6102/api/health`.
    *   **Result:** Received `{"database_status":"ok","llm_status":"check_not_implemented","service":"rai-chat-api","status":"ok"}`. This confirmed the RAI API server was now running correctly on port 6102 and accessible. The original `ECONNREFUSED` error should be resolved.

6.  **Test Core Functionality (`/api/chat`):**
    *   **Goal:** Verify deeper backend components (auth, managers, LLM connection).
    *   **Action 1:** Register a test user (`testuser`) via `curl` to `/api/auth/register`. (Success)
    *   **Action 2:** Log in as `testuser` via `curl` to `/api/auth/login` to get a token. (Success)
    *   **Action 3:** Send a "Hello, world!" message via `curl` to `/api/chat` using the obtained token.
    *   **Result 3:** Received `{"error":"Token processing error"}`.

7.  **Investigate Token Processing Error (RAI API Log):**
    *   **Action:** Read `RAI_Chat/Backend/logs/rai_api.log`.
    *   **Finding:** Found `sqlalchemy.orm.exc.DetachedInstanceError: Instance <User ...> is not bound to a Session; attribute refresh operation cannot proceed`. This occurred in the `token_required` decorator because `user_model.is_active` was accessed *after* the database session (`with get_db()...`) was closed.

8.  **Fix DetachedInstanceError:**
    *   **Action:** Applied a diff to `RAI_Chat/Backend/rai_api_server.py` to move the checks involving `user_model` (existence, `is_active`, schema creation) *inside* the `with get_db() as db:` block.
    *   **Result:** Restarted services. Retried the `/api/chat` request.
    *   **New Result:** Received `{"response":"I encountered an internal error. Please try again.","session_id":"error_session","status":"error"}`. The authentication error was fixed, but a new internal error occurred.

9.  **Investigate Internal Chat Error (RAI API Log):**
    *   **Action:** Read `RAI_Chat/Backend/logs/rai_api.log` again.
    *   **Finding:** Found `TypeError: EpisodicMemoryManager.__init__() got an unexpected keyword argument 'base_data_path'`. This happened in `UserSessionManager` when initializing `EpisodicMemoryManager`.

10. **Check `EpisodicMemoryManager.__init__`:**
    *   **Action:** Read `RAI_Chat/Backend/managers/memory/episodic_memory.py`.
    *   **Finding:** Confirmed `EpisodicMemoryManager.__init__` only accepts `user_id`.

11. **Fix `EpisodicMemoryManager` Initialization:**
    *   **Action:** Applied a diff to `RAI_Chat/Backend/managers/user_session_manager.py` to remove the `base_data_path` argument when creating `EpisodicMemoryManager`.
    *   **Result:** Restarted services. Retried the `/api/chat` request.
    *   **New Result:** Still received `{"response":"I encountered an internal error. Please try again.","session_id":"error_session","status":"error"}`.

12. **Investigate LLM API Server Crash:**
    *   **Observation:** Inactive terminal logs showed the LLM API server process (PID started by `start_all.py`) terminating unexpectedly (`exit code -9`).
    *   **Action:** Read `RAI_Chat/Backend/logs/llm_api.log`.
    *   **Finding:** Found `ModuleNotFoundError: No module named 'llm_Engine'` when `waitress` tried to import `llm_Engine.llm_api_server`.

13. **Attempt 1: Simplify `PYTHONPATH` in `start_all.py`:**
    *   **Action:** Modified `start_all.py` to remove a potentially duplicate `PYTHONPATH` entry set in `start_llm_api_server`, relying only on the `cwd` prepend in `start_service`.
    *   **Result:** Restarted services. Checked `llm_api.log`. `ModuleNotFoundError` persisted.

14. **Attempt 2: Explicit `PYTHONPATH` in `start_all.py`:**
    *   **Action:** Modified `start_all.py` to explicitly set `PYTHONPATH` to *only* the project root in `start_llm_api_server` and removed the `PYTHONPATH` modification from `start_service`.
    *   **Result:** Restarted services. Checked `llm_api.log`. `ModuleNotFoundError` persisted.

15. **Attempt 3: Self-hosted Waitress & Direct Execution:**
    *   **Action 1:** Modified `llm_Engine/llm_api_server.py` to import `waitress` and call `waitress.serve(app, ...)` within an `if __name__ == '__main__':` block.
    *   **Action 2:** Modified `RAI_Chat/Backend/start_all.py` to execute `llm_Engine/llm_api_server.py` directly (`python llm_Engine/llm_api_server.py`) instead of using `python -m waitress ...`.
    *   **Result:** Restarted services. Checked `llm_api.log`. `ModuleNotFoundError` persisted.

16. **Attempt 4: Programmatic `sys.path` Addition:**
    *   **Action:** Modified `llm_Engine/llm_api_server.py` to calculate the project root path and insert it into `sys.path` *before* the `from llm_Engine.config import ...` line.
    *   **Result:** Restarted services. *Currently waiting to check logs/test API.*

## Progress Update (April 4, 2025, 9:39 PM)

17. **Fixed LLM API Server Port Configuration:**
    * **Issue:** The LLM API server was configured to use port 6101, but the LLM API bridge was trying to connect to port 6001.
    * **Action:** Modified `llm_Engine/llm_api_bridge.py` to use port 6201 as the default port.
    * **Result:** Successfully started the LLM API server on port 6201.

18. **Fixed Missing Methods in Memory Managers:**
    * **Issue 1:** `ContextualMemoryManager` was missing a `get_context()` method that was being called in `prompt_builder.py`.
    * **Action 1:** Modified `prompt_builder.py` to use the existing `get_context_summary()` method instead.
    * **Issue 2:** `EpisodicMemoryManager` was missing a `search_episodic_memory()` method that was being called in `prompt_builder.py`.
    * **Action 2:** Added a compatibility method to `EpisodicMemoryManager` that calls the existing `retrieve_memories()` method.

19. **Fixed ActionHandler Logger:**
    * **Issue:** `ActionHandler` was trying to use a logger attribute that didn't exist.
    * **Action:** Added a proper logger initialization to the `ActionHandler` class.

20. **Fixed Parameter Mismatch:**
    * **Issue:** `ActionHandler` was trying to pass 3 arguments to `ContextualMemoryManager.process_assistant_message()`, but it only accepts 2.
    * **Action:** Updated the calls to only pass the required arguments.

21. **Configured Gemini API Key:**
    * **Issue:** The LLM API server was falling back to the mock engine because it couldn't find a Gemini API key.
    * **Action:** Modified `llm_Engine/llm_api_server.py` to load environment variables from `RAI_Chat/Backend/.env`, which contains a Gemini API key.
    * **Result:** The LLM API server now successfully loads the Gemini API key, but still falls back to the mock engine with a warning: "Gemini API unavailable, falling back to mock engine".

## Resolution (April 4, 2025, 9:45 PM)

22. **Fixed Port Configuration:**
    * **Issue:** The LLM API server was running on port 6201, but the LLM API bridge was trying to connect to port 6001.
    * **Action:** Modified `llm_Engine/llm_api_bridge.py` to use port 6301 as the default port.
    * **Result:** The LLM API bridge now connects to the correct port.

23. **Added Detailed Error Logging:**
    * **Issue:** The error logs didn't provide enough information about why the Gemini API was unavailable.
    * **Action:** Modified the `_verify_server()` method in `GeminiEngine` class to log more detailed error information.
    * **Result:** The logs now provide more information about the error, making it easier to diagnose.

24. **Started New LLM API Server:**
    * **Action:** Started a new LLM API server on port 6301 with the updated code.
    * **Result:** The new LLM API server successfully connected to the Gemini API and generated responses.

25. **Verified End-to-End Functionality:**
    * **Action:** Tested the chat API with a simple "Hello" message.
    * **Result:** Received a proper response from the Gemini API: "Hello! I'm ready to assist you. Please let me know what you need."

## Final Fix (April 4, 2025, 9:50 PM)

26. **Fixed IPv6 Binding Issue:**
    * **Issue:** The RAI API server was binding only to IPv4 interfaces (`0.0.0.0`), but the frontend was trying to connect to the IPv6 loopback address (`::1`).
    * **Action:** Modified `RAI_Chat/Backend/rai_api_server.py` to bind to both IPv4 and IPv6 interfaces by changing the host from `0.0.0.0` to `::0`.
    * **Result:** The RAI API server now listens on both IPv4 and IPv6 interfaces, allowing the frontend to connect to the IPv6 loopback address.

27. **Verified End-to-End Functionality:**
    * **Action:** Restarted the RAI API server and tested the frontend connection.
    * **Result:** The frontend successfully connected to the RAI API server and displayed responses from the Gemini API.

## Current Status

- The RAI API server (port 6102) starts and responds to health checks.
- Authentication (register/login) works.
- The `/api/chat` endpoint works and returns responses from the Gemini API.
- The LLM API server (port 6301) starts successfully and connects to the Gemini API.
- The system is now fully functional and can generate responses using the Gemini API.

## Further Issues & Resolutions (April 5, 2025)

28. **Problem: `start_all.py` Unreliable & Path Issues:**
    * **Symptom:** Continued intermittent startup failures and `ModuleNotFoundError` errors related to `RAI_Chat` when using `start_all.py`.
    * **Action:** Replaced `start_all.py` with a new script `RAI_Chat/Backend/Launch_App.py`. This script uses `subprocess.Popen` to launch each component (LLM API, RAI API, Frontend) individually with appropriate CWDs and environment settings. It also includes process monitoring and cleanup logic.
    * **Result:** More reliable application startup.

29. **Problem: Login Failure ("Invalid username or password"):**
    * **Symptom:** Users could not log in after the application started.
    * **Diagnosis:** RAI API server logs showed `sqlalchemy.exc.ProgrammingError: ... Unknown column 'users.remembered_facts'`. The database schema was out of sync with the `UserModel`, missing the `remembered_facts` column.
    * **Fix Attempt (Alembic):** Generated a migration (`43634ef2ee7f...py`) and modified it to add the column. However, `alembic upgrade` failed due to inconsistent history in the database (`Can't locate revision 3f2724846ff9`). Attempts to fix history (`down_revision`, `stamp`) also failed.
    * **Fix (Direct SQL):** Bypassed Alembic and executed `ALTER TABLE users ADD COLUMN remembered_facts JSON;` directly against the MySQL database using the `mysql` client. Restarted the RAI API server.
    * **Result:** Login became successful.

30. **Problem: Chat Failure ("Internal Error"):**
    * **Symptom:** After successful login, sending a chat message resulted in an internal server error.
    * **Diagnosis 1:** Logs showed `NameError: name 'get_user_memory_dir' is not defined` in `RAI_Chat/Backend/managers/memory/contextual_memory.py`. This function had been removed from `path_manager.py`.
    * **Fix 1:** Modified `contextual_memory.py` to remove the import and usage of `get_user_memory_dir`. Restarted app.
    * **Diagnosis 2:** Error persisted. Logs showed `AttributeError: 'ContextualMemoryManager' object has no attribute 'user_memory_dir'` in `contextual_memory.py` (in a logging statement).
    * **Fix 2:** Modified `contextual_memory.py` to remove the reference to `self.user_memory_dir` in the logging statement. Restarted app.
    * **Diagnosis 3:** Error persisted. Logs showed `TypeError: ContextualMemoryManager.process_forget_command() missing 1 required positional argument: 'user_input'` in `conversation_manager.py`. The method requires a database session.
    * **Fix 3:** Modified `conversation_manager.py` (`get_response` method) to accept a `db` session argument. Modified `rai_api_server.py` (`/api/chat` endpoint) to obtain a `db` session using `get_db()` and pass it to `conversation_manager.get_response`. Restarted app.
    * **Result:** Chat functionality is now working correctly.