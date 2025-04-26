#!/bin/bash
# Simple test script for the RAI Chat API
echo "Testing RAI Chat API..."

# Set API URL
API_URL="http://localhost:6102/api/chat"

# Create a unique session ID
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Using session ID: $SESSION_ID"

# Send a test message
echo "Sending test message..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hi, my name is Jordan. Tell me about yourself.\", \"session_id\": \"$SESSION_ID\"}" \
  $API_URL

echo -e "\n\nTest completed!"
