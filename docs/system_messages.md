# System Message Update Flow

This document explains the implementation of updatable system messages in the RAI Chat application, focusing on web search operations.

## Overview

The system now supports system messages with persistent IDs and updatable states. This allows the frontend to display dynamic message states (e.g., "Searching the web..." → "Search complete" → "Search results").

## Key Components

### 1. Database Model (`SystemMessage`)

The `SystemMessage` model now includes:
- `status` field to track message state (active, complete, error)
- `updated_at` timestamp that updates automatically when the message is modified

### 2. Backend API

New API endpoints:
- `PUT /api/system/message/<message_id>`: Updates an existing system message status and content

### 3. Frontend Integration

- System messages with persistent IDs can be updated in place using the `UPDATE_SYSTEM_MESSAGE` reducer action
- The `systemMessageService` can update messages locally and send updates to the backend

### 4. Utility Functions

We've added centralized helper functions in `utils/system_message_helpers.py`:
- `create_system_message`: Creates a new message in the database
- `update_system_message`: Updates an existing message's status and content
- `format_system_message_for_api`: Formats database objects for API responses

## Web Search Flow

The web search flow now works as follows:

1. **Detection of Search Patterns**:
   - When the LLM includes a `[SEARCH: query]` pattern in its response, a search is triggered automatically
   - When a user directly enters a message with the `[SEARCH: query]` pattern
   - Both methods create system messages and initiate the search flow

2. **Initial System Message**:
   - A system message with `status='active'` is created
   - The message has a unique ID prefixed with "search_"
   - The frontend displays "Searching the web..."

3. **When search completes successfully**:
   - The same message is updated with `status='complete'`
   - Search results are added to the message content
   - The frontend updates to show "Search complete" with results

4. **If an error occurs**:
   - The message is updated with `status='error'`
   - Error details are added to the message content
   - The frontend updates to show error information

## Usage Example

```python
# Start a search and create an active message
search_message_id = f"search_{str(uuid.uuid4())[:8]}"
db_message = create_system_message(
    content={"query": query, "message": f"Searching for: {query}"},
    message_type='web_search',
    session_id=session_id,
    status='active',
    message_id=search_message_id
)

# Update the message when search completes
updated_db_message = update_system_message(
    message_id=search_message_id,
    new_status='complete',
    new_content={"query": query, "results": results},
    session_id=session_id
)
```

## Frontend Integration

The frontend can update system message displays using:

```typescript
// When receiving a system message with the same ID as an existing message
systemMessageService.updateSystemMessage(
  sessionId,
  messageId,
  'complete',
  updatedContent,
  dispatch
);
```

## Schema Update

A database migration script has been added in `backend/scripts/update_schema.py` to add the required fields to the database. Run this script when deploying the changes.

```bash
python backend/scripts/update_schema.py
```

The script is compatible with both MySQL and SQLite databases.
