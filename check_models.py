import os
import requests
from dotenv import load_dotenv

load_dotenv()

headers = {
    "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
    "Content-Type": "application/json"
}

response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)

print("Models your key actually has access to:")
for model in response.json().get("data", []):
    print(model["id"])