# Action Signals Reference

This document provides a comprehensive list of all action signals recognized by the RAI Chat system. Action signals are special instructions embedded in LLM responses that trigger specific actions or behaviors in the system.

## Action Signal Format

Action signals typically follow this format:
```
[SIGNAL_NAME:parameter]
```

For example:
```
[SEARCH:best restaurants in San Francisco]
```

## Available Action Signals

┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       INTERRUPTING ACTIONS                                              │
├───────────────────────┬────────────────────────────────────┬───────────────────────────────────────────┤
│ Signal Format         │ Description                        │ Example                                   │
├───────────────────────┼────────────────────────────────────┼───────────────────────────────────────────┤
│ `[SEARCH:query]`      │ Performs a web search              │ `[SEARCH:current weather in New York]`    │
│ `[WEB_SEARCH:query]`  │ Alternative web search format      │ `[WEB_SEARCH:latest AI research papers]`  │
└───────────────────────┴────────────────────────────────────┴───────────────────────────────────────────┘

⚠️ **INTERRUPTING ACTIONS** replace the normal response flow with action results.

┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      NON-INTERRUPTING ACTIONS                                           │
├───────────────────────────────┬────────────────────────────────┬───────────────────────────────────────┤
│ Signal Format                 │ Description                    │ Example                               │
├───────────────────────────────┼────────────────────────────────┼───────────────────────────────────────┤
│ `[REMEMBER:fact]`             │ Stores fact in memory          │ `[REMEMBER:User prefers dark mode]`   │
│ `[CALCULATE:expression]`      │ Performs a calculation         │ `[CALCULATE:342 * 15]`                │
│ `[COMMAND:command]`           │ Executes a command             │ `[COMMAND:summarize_conversation]`    │
│ `[EXECUTE:action]`            │ Executes an action             │ `[EXECUTE:delete_last_message]`       │
│ `[REQUEST_TIER:level:content]`│ Elevates memory tier           │ `[REQUEST_TIER:2:User preferences]`   │
│ `[SEARCH_EPISODIC:query]`     │ Searches episodic memory       │ `[SEARCH_EPISODIC:travel plans]`      │
└───────────────────────────────┴────────────────────────────────┴───────────────────────────────────────┘

⚠️ **NON-INTERRUPTING ACTIONS** perform their function while still showing the original response.

## Response Flow Behavior

Action signals can have two different behaviors regarding the response flow:

1. **Interrupting Signals**: Some signals (like `[SEARCH]`) completely interrupt the normal response flow. Instead of showing the LLM's response with the action signal, the system shows the result of the action (e.g., search results).

2. **Non-Interrupting Signals**: Most signals (like `[REMEMBER]`, `[CALCULATE]`, etc.) don't interrupt the normal response flow. The system performs the requested action but still shows the LLM's complete response to the user.

## Internal Action Types

These are the internal action type constants used by the system to categorize and process actions:

| Action Type | Description |
|-------------|-------------|
| `ACTION_ANSWER` | Standard response (no special action) |
| `ACTION_FETCH` | Fetch additional information |
| `ACTION_SEARCH` | Perform a web search |
| `ACTION_SEARCH_DEEPER` | Perform a more detailed search |
| `ACTION_REMEMBER` | Store a fact in memory |
| `ACTION_ERROR` | Error condition |
| `ACTION_CONTINUE` | Signal to continue processing (non-interrupting actions) |
| `ACTION_BREAK` | Signal to stop processing (interrupting actions) |
| `ACTION_SEARCH_DETECTED` | Web search action detected |
| `ACTION_CALCULATE_DETECTED` | Calculation action detected |
| `ACTION_COMMAND_DETECTED` | Command action detected |
| `ACTION_EXECUTE_DETECTED` | Execute action detected |
| `ACTION_REMEMBER_DETECTED` | Remember fact action detected |
| `ACTION_UNKNOWN` | Unknown action |
| `ACTION_NONE` | No action detected |

## Handling in the Code

When the LLM includes an action signal in its response, the system detects it in the `ActionHandler.detect_action()` method, which scans for specific patterns using regular expressions. The action handling flow works like this:

1. The action signal is detected in `detect_action()`
2. The appropriate handler in `process_llm_response()` processes the action
3. The handler returns either:
   - `ACTION_CONTINUE` for non-interrupting actions (normal response still shown)
   - `ACTION_BREAK` for interrupting actions (response replaced with action result)

### Example: SEARCH vs REMEMBER

**[SEARCH] Action (Interrupting)**:
```
1. System detects [SEARCH:query]
2. Handler performs web search
3. Returns ACTION_BREAK with search results
4. Original LLM response is not shown, only search results are displayed
```

**[REMEMBER] Action (Non-Interrupting)**:
```
1. System detects [REMEMBER:fact]
2. Handler stores fact in memory with high importance
3. Returns ACTION_CONTINUE with original message
4. User sees complete LLM response, including the action tag
```

## Example Usage

If a user asks "What's my preference for notifications?", the LLM might include:

```
Based on our conversation, [REMEMBER:User prefers email notifications over push notifications] I can see that you prefer to receive notifications by email rather than through push notifications on your mobile device.
```

The system would store "User prefers email notifications over push notifications" in memory with high importance, while still showing the complete response to the user.

## Notes for Developers

- New action signals can be added by updating the `detect_action()` method in the `ActionHandler` class.
- Each action signal should have corresponding handling logic in the `process_llm_response()` method.
- Consider whether new actions should interrupt the normal response flow by returning either `ACTION_CONTINUE` or `ACTION_BREAK`.
- The system uses constants like `ACTION_SEARCH_DETECTED` to identify the type of action being processed.
