import requests
import json

# Configuration
RAI_API_URL = "http://127.0.0.1:5002" # Changed port to 5002
CHAT_ENDPOINT = f"{RAI_API_URL}/api/chat"

def test_chat_endpoint(message="Hello, assistant!", session_id=None):
    """
    Sends a message to the /api/chat endpoint and prints the response.
    """
    payload = {
        "message": message
    }
    if session_id:
        payload["session_id"] = session_id

    print(f"Sending message to {CHAT_ENDPOINT}: {message}")
    print(f"Payload: {json.dumps(payload)}")

    try:
        response = requests.post(CHAT_ENDPOINT, json=payload, timeout=60) # Increased timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        response_data = response.json()
        print("\n--- Response ---")
        print(f"Status Code: {response.status_code}")
        print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        print("----------------\n")

        # Return the session ID for potential follow-up requests
        return response_data.get("session_id")

    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Connection refused. Is the RAI API server running at {RAI_API_URL}?")
        print("Please ensure 'rai_api_server.py' is running.")
    except requests.exceptions.Timeout:
        print("\n[ERROR] Request timed out. The server might be busy or unresponsive.")
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] An error occurred during the request: {e}")
        if e.response is not None:
            print(f"Response Status Code: {e.response.status_code}")
            try:
                print(f"Response Body: {e.response.text}")
            except Exception:
                print("Could not decode response body.")
    except json.JSONDecodeError:
        print("\n[ERROR] Failed to decode JSON response from the server.")
        print(f"Raw Response Text: {response.text}")

    return None

if __name__ == "__main__":
    print("--- Testing /api/chat Endpoint ---")
    # First message (creates a new session)
    current_session_id = test_chat_endpoint(message="What is the capital of France?")

    # Follow-up message (uses the same session)
    if current_session_id:
        print(f"\n--- Sending follow-up message in session {current_session_id} ---")
        test_chat_endpoint(message="What about the capital of Spain?", session_id=current_session_id)
    else:
        print("\nSkipping follow-up message as no session ID was received.")

    print("\n--- Test Complete ---")