# RAI Chat Advanced Memory Architecture

**Date:** 2025-04-24

## Overview

RAI Chat implements a sophisticated multi-tier memory system designed to maintain perfect coherence across extremely long conversations while optimizing token usage. This document outlines the architecture, components, and operational flow of this system.

## Core Concepts

### Tiered Representation

Each exchange in a conversation (both user message and LLM response) is stored in multiple representation tiers:

1. **Tier 1 (Syntax/Key-Value Format)**
   - Ultra-concise representation (e.g., `user_name = Jordan`, `project = RAI Chat`)
   - Minimal token footprint (~10-20% of original size)
   - Default tier for most exchanges in context

2. **Tier 2 (Brief Summary)**
   - Condensed semantic summary of the exchange
   - Moderate token footprint (~30-40% of original size)
   - Used when Tier 1 is insufficient but full detail isn't necessary

3. **Tier 3 (Full/Raw)**
   - Complete original content
   - Maximum token footprint (100%)
   - Used only when detailed context is critical

### Adaptive Memory Selection

The system tracks which tier level is required for each exchange and dynamically provides the appropriate level of detail in future contexts:

```
Turn 1: Send as Tier 1 -> LLM determines Tier 1 is sufficient
Turn 2: Send as Tier 1 -> LLM determines Tier 1 is sufficient
Turn 3: Send as Tier 1 -> LLM requests Tier 3 for this exchange
Turn 4: System automatically sends:
       - Turn 1: Tier 1
       - Turn 2: Tier 1
       - Turn 3: Tier 3 (directly, without requiring a request)
       - Turn 4: New message (current)
```

### Two-Layer Memory System

1. **Contextual Memory**
   - Active conversation window (default 30K token limit)
   - Stores all exchanges with their tier preferences
   - Provides immediate access to recent conversation

2. **Episodic Memory**
   - Long-term indexed storage of all conversations
   - Exchanges pruned from contextual memory are archived here
   - Retrievable through semantic search when needed

## Operational Flow

### Normal Processing

1. User sends a message
2. System constructs context using appropriate tier levels for each previous exchange
3. LLM receives the context and current message
4. LLM generates response with tier information for both the user message and its response
5. System stores all tiers and updates tier preferences

### Tier Request Processing

If the LLM determines it needs more context:

1. LLM can request a higher tier for specific exchanges: `[REQUEST_TIER:2:msg_456]`
2. System retrieves the requested tier for that exchange
3. Context is reconstructed with the higher tier information
4. LLM processes again with enhanced context
5. System updates the required tier level for that exchange

### Episodic Memory Retrieval

When information is needed from beyond the contextual window:

1. LLM indicates it needs historical information: `[SEARCH_EPISODIC: query about earlier conversation]`
2. System performs semantic search in episodic memory
3. Relevant episodes are retrieved and added to context
4. LLM processes again with the historical information

## Memory Pruning

When the contextual memory exceeds the token limit (default: 30K tokens):

1. Oldest exchanges are identified for pruning
2. Complete exchanges are archived to episodic memory
3. Contextual memory is updated to remain within token limits
4. Embeddings are generated for efficient future retrieval

## Token Efficiency Analysis

### Costs
1. **Tier Generation**: Each exchange requires generating multiple tiers
2. **Processing Overhead**: Additional tokens for tier management instructions

### Savings
1. **Reduced Context Size**: Most exchanges only need Tier 1 in future context
2. **Selective Detail**: Only critical exchanges get upgraded to higher tiers

This approach becomes token-efficient after approximately 10-15 conversation turns, making it ideal for extended interactions.

## Implementation Components

### Database Schema Extensions

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    message_id VARCHAR(36) UNIQUE,
    session_id VARCHAR(36),
    user_id INTEGER,
    content TEXT,                 -- Original/Tier 3 content
    tier1_content TEXT,           -- Tier 1 (syntax) version
    tier2_content TEXT,           -- Tier 2 (summary) version
    required_tier_level INTEGER DEFAULT 1,
    role VARCHAR(20),
    timestamp DATETIME,
    metadata JSON
);
```

### Core Logic Components

1. **TierManager**: Generates and stores different tiers for each exchange
2. **ContextBuilder**: Constructs context using appropriate tier levels
3. **RequestParser**: Detects and processes tier and episodic memory requests
4. **MemoryPruner**: Manages contextual window size and archives to episodic memory

## Technical Implementation

### Tier Generation Implementation

1. **LLM-Based Tier Generation**:
   ```python
   def generate_tiers(message_content, role):
       # For user messages, we need to generate tier1 and tier2
       if role == "user":
           tier_prompt = f"""
           Convert the following user message into two tiers:
           
           Tier 1: Key-value pairs representing core information (e.g., user_name=Jordan)
           Tier 2: A brief 1-2 sentence summary capturing the essential meaning
           
           User message: {message_content}
           
           Output format:
           TIER1: key1=value1, key2=value2, ...
           TIER2: Brief summary here.
           """
           
           result = llm_api.generate_text(tier_prompt)
           
           # Parse the response
           tier1 = extract_between(result, "TIER1:", "TIER2:").strip()
           tier2 = extract_after(result, "TIER2:").strip()
           
           return {
               "tier1_content": tier1,
               "tier2_content": tier2,
               "tier3_content": message_content  # Original message
           }
       
       # For assistant messages, we need all three tiers
       elif role == "assistant":
           # For assistant messages, we expect the LLM to generate all tiers directly
           # This should be part of the response generation process
           if isinstance(message_content, dict) and "response_tiers" in message_content:
               return {
                   "tier1_content": message_content["response_tiers"]["tier1"],
                   "tier2_content": message_content["response_tiers"]["tier2"],
                   "tier3_content": message_content["response_tiers"]["tier3"]
               }
           else:
               # Fallback if tiers aren't included
               return generate_tiers_for_assistant_message(message_content)
   ```

### Context Building With Tiered History

```python
def build_tiered_context(current_message, session_id, user_id):
    # Get all messages in this session
    messages = db.query(Message)\
                 .filter_by(session_id=session_id)\
                 .order_by(Message.timestamp.asc())\
                 .all()
                 
    context_parts = []
    
    # Construct a header that explains the tier system to the LLM
    context_parts.append("""
    CONVERSATION HISTORY:
    The following conversation history is provided with different detail levels (tiers).
    - Tier 1: Key-value format with essential information
    - Tier 2: Brief summary
    - Tier 3: Complete exchange
    
    If you need more context about a specific exchange, you can request it with:
    [REQUEST_TIER:2:message_id] or [REQUEST_TIER:3:message_id]
    
    For information from past conversations, use:
    [SEARCH_EPISODIC: your query here]
    """)
    
    # Add each message with its appropriate tier level
    for msg in messages:
        if msg.required_tier_level == 1:
            content = msg.tier1_content
        elif msg.required_tier_level == 2:
            content = msg.tier2_content
        else:  # tier 3
            content = msg.tier3_content
            
        context_parts.append(f"MESSAGE[{msg.message_id}] ({msg.role.upper()}, Tier {msg.required_tier_level}):\n{content}")
    
    # Add the current message
    context_parts.append(f"CURRENT MESSAGE:\n{current_message}")
    
    return "\n\n".join(context_parts)
```

### Request Parsing Implementation

```python
def process_llm_response(response_text, session_id):
    # Check for tier request
    tier_request_match = re.search(r"\[REQUEST_TIER:(\d+):(\w+)\]", response_text)
    if tier_request_match:
        tier_level = int(tier_request_match.group(1))
        message_id = tier_request_match.group(2)
        
        # Update the required tier level for this message
        db.query(Message)\
          .filter_by(message_id=message_id)\
          .update({"required_tier_level": tier_level})
        db.commit()
        
        # Remove the request marker from the response
        clean_response = re.sub(r"\[REQUEST_TIER:\d+:\w+\]", "", response_text).strip()
        
        # Flag that we need to regenerate with updated context
        return {
            "need_regeneration": True,
            "clean_response": clean_response
        }
    
    # Check for episodic memory request
    episodic_match = re.search(r"\[SEARCH_EPISODIC:\s*(.+?)\s*\]", response_text)
    if episodic_match:
        query = episodic_match.group(1)
        
        # Search episodic memory
        episodes = search_episodic_memory(query, session_id)
        
        # Flag that we need to regenerate with episodic context
        return {
            "need_regeneration": True,
            "episodic_context": episodes,
            "clean_response": re.sub(r"\[SEARCH_EPISODIC:\s*(.+?)\s*\]", "", response_text).strip()
        }
    
    # No special request
    return {
        "need_regeneration": False,
        "clean_response": response_text
    }
```

### Memory Pruning Implementation

```python
def prune_contextual_memory(session_id, token_limit=30000):
    # Get all messages for this session
    messages = db.query(Message)\
                .filter_by(session_id=session_id)\
                .order_by(Message.timestamp.asc())\
                .all()
    
    # Calculate current token count (approximate)
    current_tokens = 0
    for msg in messages:
        # Get the content based on required tier level
        if msg.required_tier_level == 1:
            content = msg.tier1_content
        elif msg.required_tier_level == 2:
            content = msg.tier2_content
        else:  # tier 3
            content = msg.tier3_content
            
        # Approximate token count (chars / 4 is a common heuristic)
        current_tokens += len(content) // 4
    
    # Check if we need to prune
    if current_tokens <= token_limit:
        return False  # No pruning needed
    
    # Determine how many tokens to prune
    tokens_to_prune = current_tokens - token_limit + 5000  # Extra 5K buffer
    
    # Identify oldest messages to prune
    pruned_tokens = 0
    messages_to_archive = []
    
    for msg in messages:
        # Skip if this would leave us with too few messages (keep at least 5)
        if len(messages) - len(messages_to_archive) <= 5:
            break
            
        # Archive this message
        messages_to_archive.append(msg)
        
        # Add its tokens to our pruned count
        content = msg.tier3_content  # Use full content for archiving
        pruned_tokens += len(content) // 4
        
        # Check if we've pruned enough
        if pruned_tokens >= tokens_to_prune:
            break
    
    # Archive messages to episodic memory
    for msg in messages_to_archive:
        # Create episodic memory entry with full context
        create_episodic_memory_entry(msg)
        
        # Delete from contextual memory
        db.delete(msg)
    
    db.commit()
    return True  # Pruning performed
```

### Integration with Conversation Flow

```python
def process_user_message(user_input, session_id, user_id):
    # Check if we need to prune memory first
    prune_contextual_memory(session_id)
    
    # Generate tiers for user message and store
    tiers = generate_tiers(user_input, "user")
    new_message = Message(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=user_id,
        content=user_input,  # Original/Tier 3
        tier1_content=tiers["tier1_content"],
        tier2_content=tiers["tier2_content"],
        required_tier_level=1,  # Start with tier 1
        role="user",
        timestamp=datetime.utcnow()
    )
    db.add(new_message)
    db.commit()
    
    # Build context with tiered history
    context = build_tiered_context(user_input, session_id, user_id)
    
    # Process with LLM
    response = llm_api.generate_response(context)
    
    # Check for tier requests or episodic memory requests
    processed = process_llm_response(response, session_id)
    
    # If regeneration is needed, do it
    if processed["need_regeneration"]:
        # Rebuild context
        updated_context = build_tiered_context(user_input, session_id, user_id)
        
        # If we have episodic context, add it
        if "episodic_context" in processed:
            updated_context += f"\n\nRELEVANT_EPISODIC_MEMORY:\n{processed['episodic_context']}"
        
        # Regenerate response
        response = llm_api.generate_response(updated_context)
        processed = process_llm_response(response, session_id)
    
    # Extract and store tiers for assistant response
    assistant_tiers = extract_tiers_from_response(processed["clean_response"])
    
    # Create assistant message
    assistant_message = Message(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=user_id,
        content=assistant_tiers["tier3_content"],  # Full response
        tier1_content=assistant_tiers["tier1_content"],
        tier2_content=assistant_tiers["tier2_content"],
        required_tier_level=1,  # Start with tier 1
        role="assistant",
        timestamp=datetime.utcnow()
    )
    db.add(assistant_message)
    db.commit()
    
    return processed["clean_response"]
```

## Benefits

1. **Perfect Coherence**: System never loses information, even across extremely long conversations
2. **Token Efficiency**: Optimizes token usage by providing appropriate detail levels
3. **Adaptive Detail**: Automatically adjusts to conversation complexity needs
4. **Unlimited Memory**: Combination of tiered representation and episodic retrieval creates effectively unbounded memory

## Future Optimizations

1. **Selective Tier Generation**: Only generate tiers for complex exchanges
2. **Relevance-Based Selection**: Include only contextually relevant past exchanges
3. **Embedding-Based Retrieval**: Enhance episodic memory search with fine-tuned embeddings
4. **Automatic Tier Downgrading**: Allow dropping to lower tiers when higher detail is no longer needed
