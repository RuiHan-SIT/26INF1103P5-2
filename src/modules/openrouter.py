import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI



#check for API status and stop reason for malform ouput or if llm return error code for safety.
#handle rate limit
#strip output before parsing 
#validate output from LLM and parse as JSON pydantic 
#idempotent handling
#AI needs to read from data.json 

# Load variables from the .env file into environment
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Point directly to the .env in the root
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

api_base_url = os.getenv("NVIDABUILD_URL")
api_key = os.getenv("NVDIA_API_KEY")

if not api_key:
    raise ValueError("API_KEY is not set. Check your .env file!")

client = OpenAI(
  base_url = api_base_url,
  api_key = api_key
)

completion = client.chat.completions.create(
  model="nvidia/nemotron-3.5-lightning-30b-a3b",
  messages=[{"role":"user","content":"Write a limerick about the wonders of GPU computing."}],
  temperature=1,
  max_tokens=16384,
  extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":16384},
  stream=True
)

for chunk in completion:
  if not chunk.choices:
    continue
  reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
  if reasoning:
    print(reasoning, end="")
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")























