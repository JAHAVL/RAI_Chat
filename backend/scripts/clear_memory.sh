#!/bin/bash

# Script to clear AI Assistant memory files and directories
# WARNING: This permanently deletes conversation history and learned facts.
# Ensure the main application (start_all.py) is stopped before running this script.

echo "Attempting to clear AI Assistant memory..."

# Define base directory relative to the script location
BASE_DIR=$(dirname "$0")/..
cd "$BASE_DIR" || exit 1 # Change to project root directory

# Files in the root directory (Should no longer be needed)
# echo "Removing root memory files..."
# rm -f contextual_memory.json
# rm -f episodic_memory.log
# rm -f episodic_memory.json
# rm -f semantic_memory.json
# rm -f working_memory.json

# Files and directories within the consolidated 'RAI_Chat/memory/' directory
echo "Removing contents of 'RAI_Chat/memory/' directory..."
rm -f RAI_Chat/memory/contextual_sessions.json
rm -f RAI_Chat/memory/episodic_summary_index.json
rm -f RAI_Chat/memory/episodic_memory.log # Log file moved here
# Also remove other potentially unused json files found inside RAI_Chat/memory/
echo "Removing legacy JSON files from RAI_Chat/memory/..."
rm -f RAI_Chat/memory/episodic_memory.json
rm -f RAI_Chat/memory/memory.json
rm -f RAI_Chat/memory/persistent_facts.json
rm -f RAI_Chat/memory/semantic_memory.json
rm -f RAI_Chat/memory/working_memory.json
# Remove legacy directories inside RAI_Chat/memory/
echo "Removing legacy directories from RAI_Chat/memory/..."
rm -rf RAI_Chat/memory/archive/ # This is the active archive, should be cleared, not just legacy
rm -rf RAI_Chat/memory/chats/ # Remove legacy chats dir inside here too

# Remove commands for old top-level memory dir contents
# rm -f memory/session_memories.json
# rm -f memory/tier*.json
# rm -rf memory/archive/
# rm -rf memory/chats/
# rm -rf memory/tier3/

# Optional: Clear root chat directories (uncomment if desired)
echo "Removing root chat directories..." # Uncommented
rm -rf chats/ # Uncommented
# rm -rf RAI_Chat/chats/ # This one was already deleted directly

# Remove the entire legacy top-level memory directory
echo "Removing legacy top-level 'memory/' directory..."
rm -rf memory/

echo "Memory clearing process complete."
echo "You can now restart the AI Assistant application."

exit 0