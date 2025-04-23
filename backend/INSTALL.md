# Installation Guide

This is a Python desktop application that uses PyQt6 for the GUI and DeepSeek local LLM for AI responses.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- macOS 10.14 or higher

## Installation Steps

1. Open Terminal and navigate to the project directory:
```bash
cd /Users/jordanhardison/CascadeProjects/ai_assistant_app
```

2. Create a virtual environment:
```bash
python3 -m venv venv
```

3. Activate the virtual environment:
```bash
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the App

1. Make sure you're in the project directory with the virtual environment activated
2. Run the app:
```bash
python main.py
```

## Features

- Modern dark-themed desktop UI
- Local LLM for AI responses (no API keys needed)
- Calendar integration for creating events
- Natural language processing

## Troubleshooting

### Calendar Access
If calendar access is denied:
1. Open System Settings
2. Go to Privacy & Security > Calendars
3. Find "Python" in the list
4. Toggle the switch to grant access

### Qt Platform Plugin Error
If you see "Could not find Qt platform plugin":
1. Deactivate the virtual environment: `deactivate`
2. Delete it: `rm -rf venv`
3. Create a new one and reinstall:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
