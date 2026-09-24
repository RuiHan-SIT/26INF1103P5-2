import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from the .env file into environment
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Point directly to the .env in the root
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

api_base_url = os.getenv("OPENROUTER_URL")
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("API_KEY is not set. Check your .env file!")


headers = {
    "Authorization": f"Bearer {api_key.strip()}",
}

# First API call with reasoning
response = requests.post(
  url=api_base_url,
  headers=headers,
  data=json.dumps({
    "model": "nvidia/nemotron-3.5-lightning:free",
    "messages": [
        {
          "role": "user",
          "content": "How many r's are in the word 'strawberry'?"
        }
      ],
    "reasoning": {"enabled": True}
  })
)

if response.status_code == 200:
    data = response.json()
    
    # Check if the API returned an error object inside the JSON
    if "error" in data:
        print("API Error:", data["error"])
    else:
        answer = data["choices"][0]["message"]["content"]
        print("Model Response:\n", answer)
else:
    print(f"Request failed with HTTP {response.status_code}: {response.text}")


# # Extract the assistant message with reasoning_details
# response = response.json()
# response = response['choices'][0]['message']

# # Preserve the assistant message with reasoning_details
# messages = [
#   {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
#   {
#     "role": "assistant",
#     "content": response.get('content'),
#     "reasoning_details": response.get('reasoning_details')  # Pass back unmodified
#   },
#   {"role": "user", "content": "Are you sure? Think carefully."}
# ]

# # Second API call - model continues reasoning from where it left off
# response2 = requests.post(
#   url="https://openrouter.ai/api/v1/chat/completions",
#   data=json.dumps({
#     "model": "nvidia/nemotron-3.5-lightning:free",
#     "messages": messages,  # Includes preserved reasoning_details
#     "reasoning": {"enabled": True}
#   })
# )