import os
import requests

def test_groq_connection():
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ Error: GROQ_API_KEY is not set in your environment.")
        return

    # We hit the /models endpoint which is a very lightweight way to test authentication
    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print("✅ Successfully connected to the Groq API!")
            # Print the first 3 available models to prove we fetched live data
            models = [m['id'] for m in response.json().get('data', [])]
            print(f"Available models (preview): {models[:3]}")
        else:
            print(f"❌ Connection failed! Status Code: {response.status_code}")
            print(f"Message: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network connection error: {e}")

if __name__ == "__main__":
    test_groq_connection()