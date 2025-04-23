# Video Metadata System Documentation

## Overview

The AI Assistant App now features a comprehensive video metadata tracking system that stores and retrieves important information about processed videos. This document provides technical details about how the system works, the data flow, and the integration with the contextual memory system.

## Metadata Tracked

The system tracks the following metadata for each video:

1. **Video Length**: The total duration of the video in seconds, calculated from the timestamps in key points
2. **Key Points Count**: The number of key moments identified in the video
3. **Reels Count**: The number of reels created from the video

## Data Flow

### Video Processing Flow

```
User uploads video → VideoProcessor processes video → ContextualMemoryManager.process_video stores video data
```

1. **Initial Processing**:
   - `VideoProcessor` extracts transcript and key points
   - `VideoUI.handle_processing_finished` calls `ContextualMemoryManager.process_video`
   - `process_video` calculates metadata and stores it in all tiers

2. **Reel Creation**:
   - User selects key moments and clicks "Create Reels"
   - `VideoUI.on_reels_finished` is called when reels are created
   - This method calls `ContextualMemoryManager.update_video_metadata` to update the reels count

### Video Retrieval Flow

```
User asks about video → ConversationManager detects query → _get_video_context retrieves video data → AI responds with metadata
```

1. **Query Detection**:
   - `ConversationManager._is_video_related_query` detects video-related queries
   - Includes detection for metadata-specific queries like "how many key moments"

2. **Context Retrieval**:
   - `ConversationManager._get_video_context` retrieves video context from contextual memory
   - Falls back to legacy system if not found in contextual memory

3. **Summary Generation**:
   - `ConversationManager.summarize_video` includes metadata in the summary
   - The LLM incorporates this metadata into its response

## Technical Implementation

### Key Classes and Methods

#### ContextualMemoryManager

1. **process_video**:
   ```python
   def process_video(self, session_id: str, video_path: str, transcript: str, key_points: List[Dict[str, Any]]) -> Tuple[str, str, str]:
       # Calculates video metadata (length, key points count, reels count)
       # Stores video information in all three tiers
       # Returns the IDs for the entries in each tier
   ```

2. **update_video_metadata**:
   ```python
   def update_video_metadata(self, session_id: str, video_filename: str, metadata_updates: Dict[str, Any]) -> None:
       # Updates specific metadata fields for a video
       # Used primarily to update the reels count when reels are created
       # Updates both Tier 1 and Tier 3 storage
   ```

3. **_create_video_summary**:
   ```python
   def _create_video_summary(self, video_filename: str, transcript: str, key_points: List[Dict[str, Any]], 
                           video_length: float = 0, key_points_count: int = 0, reels_count: int = 0) -> str:
       # Creates a summary for Tier 2 storage
       # Includes metadata in the summary
   ```

#### VideoUI

1. **on_reels_finished**:
   ```python
   def on_reels_finished(self, result, status_widget):
       # Called when reel creation is complete
       # Updates the reels count in contextual memory
       # Displays a system message with the number of reels created
   ```

#### ConversationManager

1. **_is_video_related_query**:
   ```python
   def _is_video_related_query(self, query: str) -> bool:
       # Enhanced to detect metadata-specific queries
       # Checks for phrases like "how many key moments" or "video length"
   ```

2. **summarize_video**:
   ```python
   def summarize_video(self, video_filename: str = None):
       # Retrieves video transcript, key points, and metadata
       # Includes metadata in the prompt sent to the LLM
       # Returns a comprehensive summary with metadata
   ```

### Memory Structure

#### Tier 1 (Shorthand Context)

```json
"tier1": {
  "video": {
    "current_video": "video_filename.mp4",
    "video_length": 120.5,
    "key_points_count": 5,
    "reels_count": 2
  }
}
```

#### Tier 2 (Summarized Content)

```
[VIDEO SUMMARY] Video: video_filename.mp4 | Length: 120.5s | Key Points: 5 | Reels: 2
The video discusses... [summary content]
Key moments include:
- 00:10 - 00:15: Key point 1
- 00:30 - 00:35: Key point 2
```

#### Tier 3 (Raw Storage)

```json
{
  "role": "system",
  "content_type": "video",
  "video_path": "/path/to/video.mp4",
  "video_filename": "video_filename.mp4",
  "transcript": "Full transcript text...",
  "key_points": [
    {"start": 10.5, "end": 15.2, "text": "Key point 1"},
    {"start": 30.1, "end": 35.8, "text": "Key point 2"}
  ],
  "video_length": 120.5,
  "key_points_count": 5,
  "reels_count": 2,
  "session_id": "session_id",
  "timestamp": "2025-03-22T11:30:31"
}
```

## Backward Compatibility

The system maintains backward compatibility with the legacy memory system:

1. **Prioritized Retrieval**: The system first tries to retrieve video information from the contextual memory system, then falls back to the legacy system if needed.

2. **Consistent Data Structure**: The data structure is designed to be compatible with both systems, ensuring that no information is lost during the transition.

3. **Graceful Degradation**: If metadata is not available (e.g., for videos processed before this update), the system will still function correctly without it.

## Error Handling

The system includes comprehensive error handling:

1. **Missing Metadata**: If metadata is not available, the system uses default values (0 for numeric fields).

2. **Video Not Found**: If a video is not found in the contextual memory system, the system falls back to the legacy system.

3. **Invalid Data**: The system validates data before storing it, ensuring that only valid metadata is saved.

## Future Enhancements

Potential future enhancements to the video metadata system:

1. **Additional Metadata**: Track more metadata such as video resolution, format, and source.

2. **User Annotations**: Allow users to add annotations to videos and track them in the metadata.

3. **Enhanced Analytics**: Provide more detailed analytics about video content and usage.

4. **Export Functionality**: Allow users to export video metadata and summaries.

## Conclusion

The video metadata system provides a comprehensive solution for tracking and retrieving important information about videos. By integrating with the contextual memory system, it ensures that this information is readily available to the AI assistant, enhancing the user experience and providing more detailed responses to video-related queries.
