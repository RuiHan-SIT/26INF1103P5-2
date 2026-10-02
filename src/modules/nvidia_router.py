import requests
import json
from src.utils.openai_client import client 
from src.utils.logger import logger
import openai

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


# Validate the data from the response and handle errors 
def validate_llm_ouput():
    

#input can be either string or Array
def send_to_llm(user_input: str):
    try: 
        # Rough placeholder prompt — to be replaced by llm_prompt.py in Step 4.
        system_prompt = (
            "Business rules to come"
            )

        MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
        completion = (
            client.with_options(timeout=300, max_retries=3).chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                    ],
                temperature=1,
                max_tokens=8192,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": True},
                    "reasoning_budget": 2048,
                    },
                stream=False,
            )
        )
    
        content = completion.choices[0].message.content
        print(content)

    #400 - bad request exceeding context of 128k
    #401 - Invalid Authentication or api key rejected
    #401 - incorrect api key 
    #404 - model not found
    #429 rate limit openai.APITimeoutError / APIConnectionError
    # What it means: Network drops, DNS issues, or the server took too long to complete generation.
    #openai.InternalServerError (HTTP 500 / 502 / 503 / 504) 


    # --- Specific OpenAI API Errors ---
    except openai.BadRequestError as e:
        logger.error("Bad Request parameters: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": "Invalid request sent to AI service. Check parameter constraints or file size.",
        }
    except openai.AuthenticationError as e:
        logger.critical("Auth failed: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": "Authentication failed: NVIDIA API key is missing, invalid, or expired.",
        }
    except openai.NotFoundError as e:
        logger.error("Model not found: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": "The requested AI model name was not recognized or is temporarily unhosted.",
        }
    except openai.RateLimitError as e:
        logger.warning("Rate limit hit: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": "Rate limit exceeded (40 RPM limit). Please wait 30 seconds before trying again.",
        }

    except (openai.APITimeoutError, openai.APIConnectionError) as e:
        logger.error("Network connection error: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": "Network timeout: Unable to reach NVIDIA servers. Check your internet connection.",
        }


    # --- Pydantic Validation Errors ---


    # --- Final Safety Catch-All ---
    except Exception as e:
        logger.exception("Unexpected unhandled exception in LLM pipeline: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": f"An unexpected system error occurred: {str(e)}",
        }






send_to_llm("what is 67")







