import requests
import jwt
import time
from datetime import datetime, timedelta
import os
import sys

# Add project root to path to import RAI_Chat components if needed (e.g., for config)
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Configuration ---
# Ensure this matches the key in rai_api_server.py
SECRET_KEY = 'your-very-secret-and-complex-key-here-replace-me'
API_BASE_URL = 'http://localhost:5002' # Ensure this matches the running port
USER_ID_TO_TEST = 1
USERNAME_TO_TEST = 'testuser' # Assumes a user with this username and ID=1 exists
# --- End Configuration ---

def generate_token(user_id, username):
    """Generates a JWT token for the given user."""
    try:
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=1) # 1 hour validity for test
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        # Decode if token is bytes (depends on PyJWT version)
        # if isinstance(token, bytes):
        #     token = token.decode('utf-8')
        return token
    except Exception as e:
        print(f"Error generating JWT: {e}")
        return None

def test_new_chat_save():
    """Tests sending the first message of a new chat."""
    print(f"--- Testing New Chat Save for User ID: {USER_ID_TO_TEST} ---")
    token = generate_token(USER_ID_TO_TEST, USERNAME_TO_TEST)
    if not token:
        print("Failed to generate token. Aborting test.")
        return

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'message': 'Hello, this is the first message of a new chat.',
        'session_id': None # Explicitly null for a new chat
    }
    chat_endpoint = f'{API_BASE_URL}/api/chat'

    print(f"Sending POST request to: {chat_endpoint}")
    print(f"Payload: {payload}")
    print(f"Headers: {{'Authorization': 'Bearer <token>', 'Content-Type': 'application/json'}}") # Don't print full token

    try:
        response = requests.post(chat_endpoint, headers=headers, json=payload, timeout=30) # Added timeout
        print(f"\nResponse Status Code: {response.status_code}")
        try:
            response_data = response.json()
            print("Response JSON:")
            import json
            print(json.dumps(response_data, indent=2))

            if response.status_code == 200 and response_data.get('status') == 'success':
                new_session_id = response_data.get('session_id')
                print(f"\nSUCCESS: API call successful. New session ID: {new_session_id}")
                # Verify file creation (basic check)
                expected_file_path = os.path.join('data', str(USER_ID_TO_TEST), 'chats', f"{new_session_id}.json")
                print(f"Checking for file: {expected_file_path}")
                time.sleep(1) # Give a moment for file system operations
                if os.path.exists(expected_file_path):
                    print(f"VERIFICATION SUCCESS: Chat file '{expected_file_path}' exists.")
                else:
                    print(f"VERIFICATION FAILED: Chat file '{expected_file_path}' does NOT exist.")
            else:
                print("\nERROR: API call failed or returned non-success status.")

        except requests.exceptions.JSONDecodeError:
            print("ERROR: Failed to decode JSON response.")
            print(f"Response Text: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Request failed: {e}")
    except Exception as e:
        print(f"\nERROR: An unexpected error occurred: {e}")

if __name__ == '__main__':
    test_new_chat_save()