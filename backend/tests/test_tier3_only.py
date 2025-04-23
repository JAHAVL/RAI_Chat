import requests
import json

def test_tier3_only():
    """Test that only tier3 content is returned to the frontend"""
    url = "http://localhost:5001/api/chat"
    
    payload = {
        "message": "Hi my name is Jordan. I have two daughters, Adalie and Emmy. I also have a dog named Koda, a husky."
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"\n[USER]: {payload['message']}")
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        response_data = response.json()
        session_id = response_data.get("session_id")
        assistant_response = response_data.get("response")
        
        print(f"\n[FULL RESPONSE DATA]: {json.dumps(response_data, indent=2)}")
        print(f"\n[AI RESPONSE]: {assistant_response}")
        
        # Check if the response contains JSON structure (which would indicate improper parsing)
        if isinstance(assistant_response, str) and (
            assistant_response.strip().startswith("{") or 
            "tier1" in assistant_response or 
            "tier2" in assistant_response or
            "tier3" in assistant_response or
            "user_message_analysis" in assistant_response
        ):
            print("\n[TEST RESULT]: FAILED - Response still contains JSON structure or tier indicators")
        else:
            print("\n[TEST RESULT]: PASSED - Response is clean text without JSON structure")
        
        return session_id, response_data
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None, None

if __name__ == "__main__":
    test_tier3_only()
