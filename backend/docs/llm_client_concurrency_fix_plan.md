# Plan: LLM Client Concurrency Fix

**Date:** 2025-03-31

**Author:** Roo

## 1. Goal

To resolve the issue where concurrent chat requests can lead to LLM responses being mixed up between different chat sessions. This is caused by a shared `LLMClient` instance with mutable session state (`self.session_id`) being used across multiple requests.

## 2. Root Cause Analysis

-   `rai_api_server.py` handles concurrent requests using multiple threads.
-   `user_session_manager.py` correctly provides distinct `ConversationManager` instances per user/session.
-   `llm_api_bridge.py`'s `get_llm_api()` provides a new `LLMAPI` instance per request.
-   **Problem:** `LLMAPI` instances currently retrieve a **single, shared global `_llm_client` instance** via `get_llm_client()`.
-   **Problem:** This shared `LLMClient` instance (`llm_Engine/llm_client.py`) uses synchronous `requests` calls and contains a mutable `self.session_id` attribute that is updated based on the response received (line 143), creating a race condition and state corruption potential between concurrent requests.

## 3. Proposed Solution

Implement changes to ensure complete isolation of LLM client resources per API request.

### 3.1. Isolate `LLMClient` Instances

-   **File:** `llm_Engine/llm_api_bridge.py`
-   **Changes:**
    1.  Remove the global `_llm_client` variable.
    2.  Modify the `get_llm_client` function:
        -   Remove the `reset` parameter.
        -   Remove the logic checking for an existing `_llm_client`.
        -   Ensure the function *always* creates and returns a *new* `LLMClient` instance on every call.
    3.  Verify that `LLMAPI.__init__` correctly calls this modified `get_llm_client` to receive its own unique client instance.

### 3.2. Make `LLMClient` Stateless (Regarding Session)

-   **File:** `llm_Engine/llm_client.py`
-   **Changes:**
    1.  Remove the `self.session_id` attribute:
        -   Delete its initialization in `__init__`.
        -   Delete the assignment `self.session_id = data['session_id']` within the `chat_completion` method (around line 143).
    2.  Ensure the `chat_completion` method continues to use the `session_id` passed as an *argument* when constructing the request payload (line 92).
    3.  **Note:** Methods `get_session_info` and `delete_session` currently rely on `self.session_id`. These methods appear unused in the core chat flow. Accept that they will be broken by this change and will require refactoring (to accept `session_id` as a parameter) if their functionality is needed in the future. Prioritize fixing the core concurrency bug.

## 4. Verification Steps

1.  After implementing the changes, restart the application (`python start_all.py`).
2.  Open two separate chat sessions in the frontend UI.
3.  Send a message requiring LLM processing in the first session.
4.  Quickly switch to the second session and send another message requiring LLM processing *before* the first response returns.
5.  Observe the responses in both sessions. Confirm that each response correctly corresponds to the message sent in its respective session and that no mix-up occurs.
6.  Repeat several times to ensure consistency.

## 5. Risks and Mitigation

-   **Risk:** Minor performance overhead from creating new `LLMClient` objects per request.
    -   **Mitigation:** This is negligible compared to LLM API latency. Underlying HTTP connection pooling likely mitigates TCP overhead. Benefit of stability outweighs performance concern.
-   **Risk:** Breaking `LLMClient.get_session_info` and `LLMClient.delete_session` methods.
    -   **Mitigation:** These methods seem unused in the primary chat workflow. Accept this risk; refactor later if needed.