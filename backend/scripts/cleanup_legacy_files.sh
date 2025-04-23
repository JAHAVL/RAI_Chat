#!/bin/bash
# Cleanup script to remove legacy files after restructuring
# This script backs up the old files before removing them

# Create backup directory
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/Users/jordanhardison/CascadeProjects/ai_assistant_app/frontend_backup_$BACKUP_DATE"
mkdir -p "$BACKUP_DIR"

# Backup the current frontend directory
echo "Backing up frontend/src/modules to $BACKUP_DIR..."
cp -r /Users/jordanhardison/CascadeProjects/ai_assistant_app/frontend/src/modules "$BACKUP_DIR/"

# Remove legacy files only after successful backup
if [ $? -eq 0 ]; then
  echo "Backup successful, removing legacy files..."
  
  # Remove the old modules structure
  rm -rf /Users/jordanhardison/CascadeProjects/ai_assistant_app/frontend/src/modules/chat
  rm -rf /Users/jordanhardison/CascadeProjects/ai_assistant_app/frontend/src/modules/code-editor
  rm -rf /Users/jordanhardison/CascadeProjects/ai_assistant_app/frontend/src/modules/video
  
  # Remove temporary React project if it exists
  if [ -d "/Users/jordanhardison/CascadeProjects/ai_assistant_app/temp-react-project" ]; then
    echo "Removing temporary React project..."
    rm -rf /Users/jordanhardison/CascadeProjects/ai_assistant_app/temp-react-project
  fi
  
  echo "Cleanup completed successfully!"
else
  echo "Backup failed, cleanup aborted for safety."
  exit 1
fi
