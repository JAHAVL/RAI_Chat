#!/bin/bash
# Main startup script for RAI Chat application

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory structure if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs/startup"
mkdir -p "$SCRIPT_DIR/logs/backend"
mkdir -p "$SCRIPT_DIR/logs/frontend"
mkdir -p "$SCRIPT_DIR/logs/llm_engine"

# Use the startup logs directory for this script's logs
LOG_FILE="$SCRIPT_DIR/logs/startup/start_app_$(date +%Y%m%d_%H%M%S).log"

# Function to log messages
log() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# Function to check if a port is in use
is_port_in_use() {
    lsof -i :"$1" > /dev/null 2>&1
    return $?
}

# Function to kill processes using a specific port
kill_process_on_port() {
    log "Checking if port $1 is in use..."
    if is_port_in_use "$1"; then
        log "Port $1 is in use. Attempting to kill the process..."
        lsof -ti :"$1" | xargs kill -9 2>/dev/null
        sleep 1
        if is_port_in_use "$1"; then
            log "Failed to kill process on port $1. Please terminate it manually."
            return 1
        else
            log "Successfully killed process on port $1."
            return 0
        fi
    else
        log "Port $1 is not in use."
        return 0
    fi
}

# Function to clean up processes on exit
cleanup() {
    log "Cleaning up processes..."
    
    # Kill processes in reverse order
    if [ -n "$FRONTEND_PID" ]; then
        log "Terminating frontend process (PID: $FRONTEND_PID)..."
        kill -TERM "$FRONTEND_PID" 2>/dev/null || kill -9 "$FRONTEND_PID" 2>/dev/null
    fi
    
    if [ -n "$BACKEND_PID" ]; then
        log "Terminating backend process (PID: $BACKEND_PID)..."
        kill -TERM "$BACKEND_PID" 2>/dev/null || kill -9 "$BACKEND_PID" 2>/dev/null
    fi
    
    if [ -n "$LLM_PID" ]; then
        log "Terminating LLM engine process (PID: $LLM_PID)..."
        kill -TERM "$LLM_PID" 2>/dev/null || kill -9 "$LLM_PID" 2>/dev/null
    fi
    
    log "Cleanup complete."
}

# Set up trap to call cleanup function on script exit
trap cleanup EXIT INT TERM

log "Starting RAI Chat Application..."

# Define the ports for each component
LLM_API_PORT=6101
BACKEND_PORT=6102
FRONTEND_PORT=8081

# Kill any processes using our ports
kill_process_on_port "$LLM_API_PORT" || { log "Failed to free up LLM API port. Exiting."; exit 1; }
kill_process_on_port "$BACKEND_PORT" || { log "Failed to free up Backend port. Exiting."; exit 1; }
kill_process_on_port "$FRONTEND_PORT" || { log "Failed to free up Frontend port. Exiting."; exit 1; }

# Set environment variables
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
export RAI_API_PORT="$BACKEND_PORT"
export LLM_API_PORT="$LLM_API_PORT"
export PORT="$FRONTEND_PORT"  # For the React frontend

# Check if .env file exists and load it
ENV_FILE="$SCRIPT_DIR/RAI_Chat/backend/.env"
if [ -f "$ENV_FILE" ]; then
    log "Loading environment variables from $ENV_FILE"
    # Export variables from .env file
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    log "Warning: .env file not found at $ENV_FILE"
fi

# 1. Start LLM Engine
log "Starting LLM Engine on port $LLM_API_PORT..."
python "$SCRIPT_DIR/llm_Engine/llm_api_server.py" --port "$LLM_API_PORT" > "$SCRIPT_DIR/logs/llm_engine.log" 2>&1 &
LLM_PID=$!
log "LLM Engine started with PID: $LLM_PID"

# Wait for LLM Engine to initialize
sleep 5
if ! ps -p "$LLM_PID" > /dev/null; then
    log "Error: LLM Engine failed to start. Check logs at $SCRIPT_DIR/logs/llm_engine.log"
    exit 1
fi

# 2. Start Backend Server
log "Starting Backend Server on port $BACKEND_PORT..."
cd "$SCRIPT_DIR/RAI_Chat/backend"
python wsgi.py > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"  # Return to script directory
log "Backend Server started with PID: $BACKEND_PID"

# Wait for Backend to initialize
sleep 5
if ! ps -p "$BACKEND_PID" > /dev/null; then
    log "Error: Backend Server failed to start. Check logs at $SCRIPT_DIR/logs/backend.log"
    exit 1
fi

# 3. Start Frontend
log "Starting Frontend on port $FRONTEND_PORT..."
cd "$SCRIPT_DIR/RAI_Chat/frontend"
npm start > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"  # Return to script directory
log "Frontend started with PID: $FRONTEND_PID"

# Wait for Frontend to initialize
sleep 5
if ! ps -p "$FRONTEND_PID" > /dev/null; then
    log "Error: Frontend failed to start. Check logs at $SCRIPT_DIR/logs/frontend.log"
    exit 1
fi

log "All components started successfully!"
log "- LLM Engine: http://localhost:$LLM_API_PORT"
log "- Backend Server: http://localhost:$BACKEND_PORT"
log "- Frontend: http://localhost:$FRONTEND_PORT"
log "Visit http://localhost:$FRONTEND_PORT in your browser to use the application."

# Keep the script running to maintain the processes
log "Press Ctrl+C to stop all components and exit."
while true; do
    # Check if all processes are still running
    if ! ps -p "$LLM_PID" > /dev/null || ! ps -p "$BACKEND_PID" > /dev/null || ! ps -p "$FRONTEND_PID" > /dev/null; then
        log "One or more components have stopped unexpectedly."
        if ! ps -p "$LLM_PID" > /dev/null; then
            log "LLM Engine (PID: $LLM_PID) is not running."
        fi
        if ! ps -p "$BACKEND_PID" > /dev/null; then
            log "Backend Server (PID: $BACKEND_PID) is not running."
        fi
        if ! ps -p "$FRONTEND_PID" > /dev/null; then
            log "Frontend (PID: $FRONTEND_PID) is not running."
        fi
        log "Exiting..."
        exit 1
    fi
    sleep 5
done
