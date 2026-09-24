import requests
import json
from dotenv import load_dotenv

# Load variables from the .env file into environment
load_dotenv()

api_base_url = os.getenv("OPENROUTER_URL")
api_key = os.getenv("OPEN_ROUTER_API_KEY")

# First API call with reasoning
response = requests.post(
  url=api_base_url,
  headers={
    "Authorization": 'Bearer ' + api_key,
    "Content-Type": "application/json",
  },
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