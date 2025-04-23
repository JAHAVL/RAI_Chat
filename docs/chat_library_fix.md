# Chat Library Connection Fix

## Issue

The chat library was not loading chats and was showing an error:

```
Could not load chats: connect ECONNREFUSED ::1:5002
```

This error indicates that the frontend was trying to connect to the RAI API server on port 5002 at the IPv6 loopback address (`::1`), but the connection was being refused because the RAI API server was actually running on port 6102.

## Root Cause Analysis

After investigating the codebase, two issues were identified:

1. **Port Mismatch in `electron.js`**:
   - The `electron.js` file defined the API base URL as `http://localhost:5002/api` on line 15.
   - However, the RAI API server was actually running on port 6102.
   - This mismatch caused the chat library to try to connect to the wrong port.

2. **Inconsistent Port Usage**:
   - The chat send functionality was correctly using port 6102 (line 361 in `electron.js`):
     ```javascript
     const url = `http://localhost:6102/api/chat`;
     ```
   - But other API calls, including the chat library, were using the incorrect port 5002.

3. **Incorrect Port in Cleanup Logic**:
   - The `will-quit` event handler was trying to kill processes on ports 6001 and 5002, but the actual ports in use were 6301 and 6102.

## Solution

1. **Updated API Base URL**:
   - Modified `electron.js` to use the correct port for the API base URL:
     ```javascript
     const API_BASE_URL = 'http://localhost:6102/api';
     ```

2. **Updated Port Cleanup Logic**:
   - Modified the `will-quit` event handler to kill processes on the correct ports:
     ```javascript
     const portsToKill = [6301, 6102]; // LLM and RAI API ports
     ```

## Verification

After making these changes and restarting the application:

1. The chat library now loads chats correctly.
2. New chats are added to the library as soon as the first message is sent.
3. The application can properly clean up server processes when it's closed.

## Additional Notes

- The port configuration should be centralized in a single location to avoid similar issues in the future.
- Consider adding a health check at startup to verify that the API server is running on the expected port.