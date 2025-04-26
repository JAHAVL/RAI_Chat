#!/bin/bash
# Find all Python files in the backend directory
find /Users/jordanhardison/Documents/Code\ Projects/RAI/RAI_Chat_V2/backend -name "*.py" -type f | while read file; do
    # Search for "from backend" or "import backend" in each file
    grep -l "from backend\|import backend" "$file" 
done
