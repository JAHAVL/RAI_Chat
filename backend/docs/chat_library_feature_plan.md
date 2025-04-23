# Plan: Add Collapsible Chat Library Feature

This document outlines the plan for adding a collapsible chat library panel to the left side of the RAI_Chat frontend application.

## 1. Create the Chat Library Module

*   **Directory:** Create a new directory at `RAI_Chat/frontend/src/modules/chat_library/`.
*   **Component:** Create a new React component file, `ChatLibrary.jsx`, within this directory.
*   **Responsibilities:**
    *   Fetch the list of available chat sessions (using `raiAPIClient` or similar).
    *   Display the list of chat sessions.
    *   Handle selection of a chat session (triggering loading in the main chat area).
    *   Include controls for collapsing/expanding the panel itself.
    *   (Future) Potentially handle chat deletion or renaming.

## 2. Modify Main Layout (`App.jsx`)

*   **Import:** Import the new `ChatLibrary` component into `RAI_Chat/frontend/src/App.jsx`.
*   **State:** Introduce state (e.g., `isChatLibraryOpen`) in `App` or `AppContent` to manage the collapsed state.
*   **Layout Adjustment:** Modify the `MainArea` styled component or its JSX structure to place the `<ChatLibrary>` component to the left of the main `<Content>` area.
*   **Styling:** Apply styles using `styled-components` for:
    *   Defined width when open (e.g., 250px).
    *   Minimal width or `width: 0; overflow: hidden;` when collapsed.
    *   Appropriate background, padding.
    *   Smooth transitions for collapse/expand animations.
    *   Vertical scrolling for the chat list if needed.

## 3. Integrate Chat Selection

*   **Communication:** Implement a callback function passed as a prop from `AppContent` to `ChatLibrary`.
*   **Action:** When a chat session is selected in `ChatLibrary`, this callback will:
    *   Update the `currentSessionId` state in `AppContent`.
    *   Trigger fetching and displaying the messages for the selected session in the main chat view.

## Proposed Layout Structure

```mermaid
graph TD
    App --> Container(Container - flex-direction: column);
    Container --> TitleBar(TitleBar - fixed);
    Container --> MainArea(MainArea - display: flex);

    MainArea --> ChatLibrary(ChatLibrary Panel - Collapsible);
    MainArea --> Content(Content - flex: 1);
    MainArea --> Sidebar(Sidebar - Module Buttons);

    Content --> MessagesArea(MessagesArea);
    Content --> Footer(Footer - Input Area);

    ChatLibrary --> ChatList(List of Chats);
    ChatLibrary --> CollapseButton(Collapse Button);