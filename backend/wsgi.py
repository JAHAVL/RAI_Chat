# RAI_Chat/Backend/wsgi.py
import os
import sys

# Add the current directory to the path so we can import app
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# When running in Docker, PYTHONPATH is set properly in docker-compose.yml
# No need to modify the path for llm_Engine as we're using HTTP API integration

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Use environment variable RAI_API_PORT, default to 6102 if not set
    port = int(os.environ.get('RAI_API_PORT', 6102))
    
    # Try to use waitress if available, otherwise fall back to Flask dev server
    try:
        from waitress import serve
        print(f"RAI API Server is running at http://localhost:{port}")
        serve(app, host='0.0.0.0', port=port, threads=8)
    except ImportError:
        print(f"Waitress not found. Using Flask development server (not recommended for production).")
        app.run(host='0.0.0.0', port=port, debug=False)
