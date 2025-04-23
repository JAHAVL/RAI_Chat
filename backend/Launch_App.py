#!/usr/bin/env python3
import subprocess
import signal
import os
import sys
import time
import logging
from pathlib import Path

# --- Configuration ---
LLM_API_PORT = 6301 # Revert to expected port for RAI API
RAI_API_PORT = 6102 # Assuming this is the default port used by rai_api_server.py

# --- Logging Setup ---
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "launch_app.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout) # Also log to console
    ]
)
logger = logging.getLogger("AppLauncher")

# --- Project Paths ---
# Assumes this script is in RAI_Chat/Backend
BACKEND_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = BACKEND_DIR.parent.parent.resolve()
LLM_ENGINE_DIR = PROJECT_ROOT / "llm_Engine"
RAI_CHAT_DIR = PROJECT_ROOT / "RAI_Chat"
FRONTEND_DIR = RAI_CHAT_DIR / "frontend"

# --- Process Management ---
processes = []

def start_service(name, cmd, cwd, log_file_base):
    """Starts a service as a subprocess and logs its output."""
    global processes
    log_stdout_path = LOG_DIR / f"{log_file_base}.log"
    log_stderr_path = LOG_DIR / f"{log_file_base}_stderr.log"

    logger.info(f"Starting {name}...")
    logger.info(f"  Command: {' '.join(cmd)}")
    logger.info(f"  CWD: {cwd}")
    logger.info(f"  Stdout Log: {log_stdout_path}")
    logger.info(f"  Stderr Log: {log_stderr_path}")

    try:
        # Open log files
        stdout_log = open(log_stdout_path, 'w', encoding='utf-8')
        stderr_log = open(log_stderr_path, 'w', encoding='utf-8')

        # Start the process
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=stdout_log,
            stderr=stderr_log,
            text=True,
            # Use process group to manage child processes if needed (especially for npm)
            preexec_fn=os.setsid if sys.platform != "win32" else None
        )
        processes.append({'name': name, 'process': process, 'stdout_log': stdout_log, 'stderr_log': stderr_log})
        logger.info(f"Started {name} (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Failed to start {name}: {e}", exc_info=True)
        # Close log files if they were opened
        if 'stdout_log' in locals() and stdout_log:
            stdout_log.close()
        if 'stderr_log' in locals() and stderr_log:
            stderr_log.close()
        return None

def cleanup_processes():
    """Terminates all started subprocesses."""
    logger.info("Cleaning up processes...")
    for p_info in reversed(processes): # Terminate in reverse order
        process = p_info['process']
        name = p_info['name']
        stdout_log = p_info['stdout_log']
        stderr_log = p_info['stderr_log']

        if process.poll() is None: # Check if process is still running
            logger.info(f"Terminating {name} (PID: {process.pid})...")
            try:
                # Send SIGTERM to the process group (more reliable for npm/electron)
                # Use os.setsid in Popen for this to work reliably on non-Windows
                if sys.platform != "win32":
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate() # Fallback for Windows

                # Wait for a short period
                process.wait(timeout=5.0)
                logger.info(f"{name} terminated gracefully.")
            except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired): # Catch specific errors
                logger.warning(f"{name} (PID: {process.pid}) did not terminate gracefully after 5s or process group not found, killing...")
                try:
                    if sys.platform != "win32":
                        # Check if pgid exists before killing
                        pgid = os.getpgid(process.pid) # Get pgid again, might fail if process died
                        os.killpg(pgid, signal.SIGKILL) # Force kill group
                    else:
                        process.kill() # Force kill process
                    process.wait(timeout=2.0) # Short wait after kill
                except Exception as kill_err:
                    logger.error(f"Error force killing {name} (PID: {process.pid}): {kill_err}")
            except Exception as e:
                 logger.error(f"Error terminating {name} (PID: {process.pid}): {e}")
        else:
            logger.info(f"{name} (PID: {process.pid}) already terminated.")

        # Close log files
        if stdout_log: stdout_log.close()
        if stderr_log: stderr_log.close()

    processes.clear() # Clear the list
    logger.info("Cleanup complete.")


def signal_handler(sig, frame):
    """Handles termination signals."""
    logger.info(f"Received signal {sig}. Initiating shutdown...")
    cleanup_processes() # Call original cleanup
    sys.exit(0)

# Register signal handlers and atexit cleanup
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
import atexit
atexit.register(cleanup_processes) # Register original cleanup

# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Application Components...")
    logger.info(f"Project Root: {PROJECT_ROOT}")
    # Removed pre-launch port cleanup

    # 1. Start LLM API Server
    llm_cmd = [
        sys.executable,
        str(LLM_ENGINE_DIR / "llm_api_server.py"),
        "--port", str(LLM_API_PORT)
    ]
    start_service("LLM API Server", llm_cmd, PROJECT_ROOT, "llm_api")
    time.sleep(5) # Give server time to initialize

    # 2. Start RAI API Server by directly running the wsgi.py script
    rai_cmd = [
        sys.executable,
        str(BACKEND_DIR / "wsgi.py")
        # Port is configured in the app factory and wsgi.py
    ]
    start_service("RAI API Server", rai_cmd, PROJECT_ROOT, "rai_api")
    time.sleep(5) # Give server time to initialize

    # 3. Start Frontend
    # Using Popen with cwd is generally safer than shell=True
    frontend_cmd = ["npm", "start"]
    start_service("Frontend App", frontend_cmd, FRONTEND_DIR, "frontend_app")

    logger.info("All components launched. Monitoring...")

    # Keep the main script running to monitor child processes
    try:
        while True:
            all_running = True
            for p_info in processes:
                if p_info['process'].poll() is not None:
                    logger.error(f"{p_info['name']} (PID: {p_info['process'].pid}) terminated unexpectedly with exit code {p_info['process'].returncode}. Shutting down.")
                    all_running = False
                    break
            if not all_running:
                break
            time.sleep(5) # Check every 5 seconds
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received in main loop.")
    finally:
        # Cleanup will be called by atexit or signal handler
        logger.info("Exiting main script.")