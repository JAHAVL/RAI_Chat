# Chat Library Immediate Update Plan

**Goal:** Modify the frontend so that a new chat session appears immediately in the Chat Library sidebar when the user sends the first message, without waiting for the backend response.

**Problem:** Currently, the Chat Library only refreshes after the backend confirms the new session creation and returns its ID, causing a noticeable delay.

**Proposed Solution:** Optimistic UI Update

Implement a mechanism where the frontend adds a temporary placeholder for the new chat immediately upon sending the first message, and then updates or removes this placeholder based on the backend's response.

**Detailed Plan:**

1.  **Modify `App.jsx` (`AppContent` component - `handleSendMessage` function):**
    *   Identify when a new chat is being started (e.g., `currentSessionId` is null).
    *   **Before** calling `raiAPIClient.sendMessage`:
        *   Generate a unique temporary client-side ID (e.g., `temp-${Date.now()}`).
        *   Extract an initial title from the user's input (e.g., first 30 characters).
        *   Call a new handler function passed down from `AppLayout` (e.g., `onNewChatPlaceholder(tempId, initialTitle)`).
    *   **After** receiving a successful response from the backend (`response.status === 'success'`):
        *   If a new `response.session_id` was returned:
            *   Extract the real session data (ID: `response.session_id`, Title: Use backend title if provided, otherwise generate from first message).
            *   Call another new handler function passed down from `AppLayout` (e.g., `onConfirmNewChat(tempId, realSessionData)`).
            *   Update the `currentSessionId` state with the *real* ID (`response.session_id`).
    *   **If** the backend API call fails (in the `catch` block):
        *   Call another new handler function passed down from `AppLayout` (e.g., `onFailedNewChat(tempId)`).

2.  **Modify `App.jsx` (`AppLayout` component):**
    *   Define the new handler functions: `handleNewChatPlaceholder`, `handleConfirmNewChat`, `handleFailedNewChat`.
    *   Pass these handlers down as props to the `<ChatLibrary>` component.

3.  **Modify `ChatLibrary.jsx`:**
    *   Accept the new handler props: `onNewChatPlaceholder`, `onConfirmNewChat`, `onFailedNewChat`.
    *   Implement the logic within these handlers (or potentially directly modify state based on props):
        *   `onNewChatPlaceholder(tempId, initialTitle)`:
            *   Create a placeholder chat object: `{ id: tempId, name: initialTitle || "New Chat...", isPlaceholder: true }`.
            *   Update the local `chats` state by adding this placeholder object to the *beginning* of the array.
        *   `onConfirmNewChat(tempId, realSessionData)`:
            *   Find the chat item in the `chats` state where `item.id === tempId`.
            *   Update that item's `id` to `realSessionData.id`, `name` to `realSessionData.title`, and set `isPlaceholder` to `false`.
            *   Ensure the list remains sorted correctly (newly confirmed chat should likely stay at the top).
        *   `onFailedNewChat(tempId)`:
            *   Filter the `chats` state array to remove the item where `item.id === tempId`.
    *   Modify the `onClick` handler for list items (`handleSelect`) to prevent selection if `isPlaceholder` is true or if the ID matches the temporary format.
    *   Review the need for the `refreshKey` prop for *new* chat creation; it might only be needed for deletions or external refreshes now.

**Diagram (Optimistic Flow):**

```mermaid
sequenceDiagram
    participant User
    participant AppContent
    participant AppLayout
    participant ChatLibrary
    participant Backend

    User->>AppContent: Sends first message (new chat)
    AppContent->>AppContent: Generate tempId, initialTitle
    AppContent->>AppLayout: onNewChatPlaceholder(tempId, initialTitle)
    AppLayout->>ChatLibrary: (Propagate call) onNewChatPlaceholder(tempId, initialTitle)
    ChatLibrary->>ChatLibrary: Update local 'chats' state (adds placeholder)
    Note right of ChatLibrary: UI Updates Immediately
    AppContent->>Backend: Send message (session_id=null)
    Backend-->>AppContent: Response (incl. real_session_id, real_title)
    AppContent->>AppLayout: onConfirmNewChat(tempId, realSessionData)
    AppLayout->>ChatLibrary: (Propagate call) onConfirmNewChat(tempId, realSessionData)
    ChatLibrary->>ChatLibrary: Update local 'chats' state (updates placeholder)
    AppContent->>AppLayout: setCurrentSessionId(real_session_id)