import requests
import json
from utils.openai_client import client 
from utils.logger import logger

""" 
1)i want to throw completion or watever ( done )
2) in this file i want to handle API status and error codes and malform output and 
rate limit and response timeout or api unreachable and empty response from llm 
3) i handle output validation with pydantic schema 


- idempotent handling (  Idempotent = doing something more than once gives the same result as doing it once.)
- ai able to call data.json and verify but asking for user input. 

Business Logic:
IMPORTANT: Main.py should check for exisitng data than fill in the blanks.
1) input 
2) validate user input 
3) pass to llm to organise the data with my system prompt and user prompt ( stream disable not needed for now )
4) llm output is pass to logic manager 
5) logic maanger passes then it will call data manager to save data
6) data manager saves data tagged to the hoto 
"""

input = "what is 67"

def send_message(user_input: str):
  try:
    completion = client.chat.completions.create(
    model="nvidia/nemotron-3.5-lightning-30b-a3b",
    messages=[{"role":"user",
    "content":
    input
    }],
    temperature=1,
    max_tokens=16384,
    extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":16384},
    stream=False
  )

    for chunk in completion:
      if not chunk.choices:
        continue
      reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
      if reasoning:
        print(reasoning, end="")
      if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
  except:
    print(EOFError)

send_message(input)























