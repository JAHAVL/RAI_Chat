#!/bin/bash
# Launcher script for AI Assistant App

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the app directory
cd "$DIR"

# Print diagnostic information
echo "Launching AI Assistant..."
echo "Current directory: $DIR"

# Use Anaconda Python which has PyQt6 installed
PYTHON_PATH="/opt/anaconda3/bin/python"
echo "Using Python at: $PYTHON_PATH"
$PYTHON_PATH --version

# Set Qt plugin paths
export QT_PLUGIN_PATH="$($PYTHON_PATH -c 'import site; import sys; import os; from pathlib import Path; paths = [str(Path(site.getsitepackages()[0]) / "PyQt6" / "Qt6" / "plugins"), str(Path(sys.executable).parent.parent / "plugins")]; paths = [p for p in paths if os.path.exists(p)]; print(os.pathsep.join(paths))')"
echo "Set QT_PLUGIN_PATH to: $QT_PLUGIN_PATH"

# Enable Qt debugging
export QT_DEBUG_PLUGINS=1

# Run the app
$PYTHON_PATH "$DIR/main.py"

# Keep terminal window open if there's an error
if [ $? -ne 0 ]; then
  echo "Error launching AI Assistant. Press Enter to close this window."
  read
fi
