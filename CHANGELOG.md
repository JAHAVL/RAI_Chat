# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-04-08

### Added
- Periodic background polling for chat sessions to keep chat library in sync
- Delayed session fetch mechanism for new chat creation

### Fixed
- System message now correctly transitions from "Searching the web..." to "Searched the web..." after final response
- Chat library update process to ensure new chats appear without manual refresh
- Improved optimistic UI updates for chat creation and session management

### Improvements
- Enhanced logging for chat session creation and update processes
- More robust handling of chat library state synchronization
- Improved error handling and state management in chat creation flow

## [0.1.0] - 2025-04-05

### Fixed

- Resolved issue where chat history would disappear when a "Searching the web..." status message was displayed, particularly during new chat sessions. Refactored frontend state management (`App.tsx`, `ChatPage.tsx`) to handle session ID transitions during streaming more robustly.