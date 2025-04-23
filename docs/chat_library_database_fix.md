# Chat Library Database Fix

## Issues

The chat library was not loading chats and was showing several errors:

1. **Connection Error**: `Could not load chats: connect ECONNREFUSED ::1:5002`
2. **LLM API Error**: `Error generating response: HTTPConnectionPool(host='localhost', port=6301): Max retries exceeded with url: /api/chat/completions (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x114dfdb20>': Failed to establish a new connection: [Errno 61] Connection refused'))`
3. **Authentication Error**: `Could not load chats: Request failed with status code 401`

## Root Cause Analysis

After investigating the codebase, several issues were identified:

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

4. **Authentication Token Not Set in API Client**:
   - The `AuthContext.tsx` file was initializing the auth state with the token from localStorage, but it wasn't setting the token in the API client during initialization.
   - This caused the API client to make requests without the Authorization header, resulting in 401 Unauthorized errors.

5. **Incorrect API Call in RAIContext**:
   - The `sendMessage` method in `RAIContext.tsx` was calling `raiAPIClient.sendMessage(message)` with just the message string.
   - However, the `sendMessage` method in `rai_api.ts` was expecting an object with `message`, `session_id`, and optionally `token` properties.
   - This caused the API client to make incorrect requests, resulting in errors.

6. **Incorrect Import Path**:
   - The `RAIContext.tsx` file was importing the `Message` type from `../types/chat`, but the correct path was `../pages/Main_Chat_UI/chat.d`.
   - This caused TypeScript errors and potential runtime issues.

7. **Missing Authorization Headers in IPC Handlers**:
   - The `chat:getSessions` and `chat:deleteSession` IPC handlers in `electron.js` were not including the Authorization header.
   - The handlers were trying to get the token from the renderer process using `event.sender.webContents.executeJavaScript()`, which was undefined.
   - This caused the API requests to fail with 401 Unauthorized errors.

8. **Incomplete ChatFileManager Implementation**:
   - The `chat_api.py` file had placeholders where it should have been using the `ChatFileManager` methods.
   - This prevented the chat library from properly loading and saving chat sessions.

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

3. **Fixed Authentication Token Initialization**:
   - Updated `AuthContext.tsx` to set the token in the API client during initialization:
     ```typescript
     useEffect(() => {
       const token = localStorage.getItem('authToken');
       if (token) {
         raiAPIClient.setAuthToken(token);
         console.log("Set auth token from localStorage in API client on mount");
       }
     }, []);
     ```

4. **Implemented ChatFileManager Integration**:
   - Updated `chat_api.py` to use the `ChatFileManager` methods instead of placeholders:
     - Replaced placeholder code in `endpoint_create_session` to use `ChatFileManager.save_session_transcript`
     - Replaced placeholder code in `endpoint_list_sessions` to use `ChatFileManager.list_sessions`
     - Replaced placeholder code in `endpoint_get_session` to use `ChatFileManager.list_sessions` and filter by session ID
     - Replaced placeholder code in `endpoint_delete_session` to use `ChatFileManager.delete_session`
     - Replaced placeholder code in `endpoint_get_messages` to use `ChatFileManager.get_session_transcript`

## Verification

After making these changes and restarting the application:

1. The chat library now loads chats correctly.
2. New chats are added to the library as soon as the first message is sent.
3. The application can properly clean up server processes when it's closed.

5. **Fixed API Call in RAIContext**:
   - Updated the `sendMessage` method in `RAIContext.tsx` to pass the correct parameters to `raiAPIClient.sendMessage()`:
     ```typescript
     const response = await raiAPIClient.sendMessage({
       message,
       session_id: null // Use null to create a new session or pass a session ID if available
     });
     ```

6. **Fixed Import Path**:
   - Updated the import path in `RAIContext.tsx` to use the correct path for the `Message` type:
     ```typescript
     import type { Message } from '../pages/Main_Chat_UI/chat.d'; // Import Message type from correct location
     ```

7. **Fixed IPC Handlers to Accept Token Parameter**:
   - Updated the `chat:getSessions` and `chat:deleteSession` IPC handlers in `electron.js` to accept a token parameter:
     ```javascript
     ipcMain.handle('chat:getSessions', async (event, token) => {
       // ...
       const headers = { 'Content-Type': 'application/json' };
       if (token) {
         headers['Authorization'] = `Bearer ${token}`;
         console.log('Added Authorization header with token for chat:getSessions');
       }
       // ...
     });
     ```

8. **Updated ChatLibrary Component to Pass Token**:
   - Modified the `ChatLibrary.tsx` component to get the token from localStorage and pass it to the IPC handlers:
     ```typescript
     // Get token from localStorage
     const token = localStorage.getItem('authToken');
     log(`ChatLibrary: Using token from localStorage: ${token ? 'Present' : 'Absent'}`);
     
     // Use window.api for IPC call, passing the token
     const response = await window.api!.getChatSessions(token);
     ```

9. **Updated TypeScript Definitions and Preload Script**:
   - Updated the TypeScript definitions in `electron.d.ts` to include the token parameter:
     ```typescript
     getChatSessions: (token?: string | null) => Promise<...>;
     deleteChatSession: (sessionId: string, token?: string | null) => Promise<...>;
     ```
   - Updated the preload script to pass the token to the IPC handlers:
     ```javascript
     getChatSessions: (token) => ipcRenderer.invoke('chat:getSessions', token),
     deleteChatSession: (sessionId, token) => ipcRenderer.invoke('chat:deleteSession', sessionId, token),
     ```

## Additional Notes

- The `ChatFileManager` class is designed to work with a database backend, storing session metadata in the database and message transcripts in files.
- The port configuration should be centralized in a single location to avoid similar issues in the future.
- Consider adding a health check at startup to verify that the API server is running on the expected port.