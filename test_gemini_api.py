import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key found: {'Yes' if api_key else 'No'}")

try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents="Say hello"
    )
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
