@echo off

REM Activate virtual environment if it exists
IF EXIST venv (
    call venv\Scripts\activate.bat
)

REM Run the application
python main.py
