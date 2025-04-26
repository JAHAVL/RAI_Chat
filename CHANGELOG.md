# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-04-26

### Fixed
- Fixed backend sending raw LLM response objects to frontend by implementing proper content extraction
- Restored "rememberThis" functionality for automatic fact extraction from messages
- Fixed frontend crashes when receiving non-string content by adding proper type checking
- Added robust JSON serialization for message content in all frontend components
- Ensured consistent string representation of message content in ChatMessageComponent and SystemMessageComponent

### Improved
- Enhanced error handling in message processing pipeline
- Added comprehensive logging for response data processing
- Improved fact extraction using both pattern-based and LLM-based approaches

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