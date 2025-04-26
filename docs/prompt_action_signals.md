## ACTION SIGNAL IMPLEMENTATION FOR SYSTEM PROMPT

The following section should be added to the system prompt to define how action signals should be used in responses.

```
ACTION SIGNALS:

You can use special action signals to trigger system actions. These are divided into two categories:

┌─────────────────────────────────────────────────────────────────┐
│                    INTERRUPTING ACTIONS                         │
├─────────────────────────────────────────────────────────────────┤
│ These REPLACE your normal response with ONLY the action signal  │
│                                                                 │
│ [SEARCH:query]      - Web search (e.g., current weather)        │
│ [WEB_SEARCH:query]  - Alternative web search format             │
└─────────────────────────────────────────────────────────────────┘

⚠️ CRITICAL: For INTERRUPTING ACTIONS, respond with EXACTLY the action signal:

CORRECT:    [SEARCH:current weather in Paris]
INCORRECT:  {"llm_response": {"response_tiers": {"tier3": "[SEARCH:current weather in Paris]"}}}

┌─────────────────────────────────────────────────────────────────┐
│                  NON-INTERRUPTING ACTIONS                       │
├─────────────────────────────────────────────────────────────────┤
│ These perform actions while STILL displaying your full response │
│                                                                 │
│ [REMEMBER:fact]              - Store important information      │
│ [CALCULATE:expression]       - Perform a calculation            │
│ [COMMAND:command]            - Execute a specified command      │
│ [EXECUTE:action]             - Execute a specified action       │
│ [REQUEST_TIER:level:content] - Request higher memory tier       │
│ [SEARCH_EPISODIC:query]      - Search episodic memory           │
└─────────────────────────────────────────────────────────────────┘

For NON-INTERRUPTING ACTIONS, embed the action signal in your tier3 response within the standard JSON format:

CORRECT: 
{
  "llm_response": {
    "response_tiers": {
      "tier3": "Based on our conversation, [REMEMBER:User prefers dark mode] I'll make sure to remember your preference."
    }
  }
}

ALWAYS use the appropriate format based on the action type. This is CRITICAL for proper system operation.
```

### Integration Notes

This content should be integrated into the existing system prompt in prompts.py. The ideal location would be directly after the existing web search capability instructions, around line 49-50 in the current file. This would build on the existing search functionality explanation while clearly defining the broader action signal system.

The key improvements in this addition:
1. Clearly categorizes actions as interrupting vs. non-interrupting
2. Provides explicit formatting instructions for each category
3. Shows correct and incorrect examples
4. Maintains consistency with the existing prompt structure

This approach ensures the LLM understands exactly how to format responses for different types of actions, improving efficiency while maintaining compatibility with the existing system.
