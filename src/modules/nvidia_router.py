import requests
import json
from utils.openai_client import client
from utils.logger import logger
from utils.llm_prompt import SYSTEM_PROMPT
from model.handover_model import HandoverReport
from pydantic import ValidationError
import openai
import re
import json_repair

""" 
1)i want to throw completion or watever ( done )
2) in this file i want to handle API status and error codes and malform output and 
rate limit and response timeout or api unreachable and empty response from llm 
3) i handle output validation with pydantic schema 
"""


# Validate the data from the response and handle errors 
#handles markdown return by LLM
#check for empty data 

#takes a JSON data from the API and return as "JSON"
def clean_llm_json(raw_text: str | None) -> dict[str, Any]:
    """Sanitizes raw LLM output into a dictionary ready for Pydantic."""
    if not raw_text or not raw_text.strip():
        raise ValueError("LLM returned an empty or null response.")

    text = raw_text.strip()

    #Strip Markdown code fences if model wrapped the JSON
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()

    #Locate the outermost JSON object bounds (strips preambles/postscripts)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in response: {text[:80]}")

    json_str = text[start : end + 1]

    try:
        # json_repair fixes missing commas, unescaped quotes, etc. and returns a Python dict
        parsed = json_repair.loads(json_str)
        if not isinstance(parsed, dict):
            raise ValueError(f"Parsed JSON is not an object/dict: {type(parsed).__name__}")
        return parsed
    except Exception as err:
        logger.error("Failed to repair/decode JSON. Faulty snippet:\n%s", json_str[:400])
        raise ValueError(f"Malformed JSON from LLM: {err}") from err

    #Parse to dict
    return json.loads(json_str, strict=False)


def send_to_llm(user_input: str):
    try: 

        MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
        completion = (
            client.with_options(timeout=300, max_retries=3).chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                    ],
                temperature=1,
                max_tokens=16384,
                # response_format={"type": "json_object"},
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": False},
                    "reasoning_budget": 2048,
                    },
                stream=False,
            )
        )
        raw_content = completion.choices[0].message.content 
        # print(raw_content)

        #this model returns everything as text
        parsed_dict = clean_llm_json(raw_content)

        # Step 2: Pass plain dict to standard Pydantic validation
        return HandoverReport.model_validate(parsed_dict)

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
    except ValidationError as e:
        logger.error("LLM schema mismatch (%d errors): %s", e.error_count(), e)
        raise ValueError(f"LLM output did not match expected Handover schema: {e}") from e

    # --- JSON.Load Errors ---
    except (ValueError, json.JSONDecodeError) as e:
        logger.error("JSON formatting error: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": f"Malformed JSON from LLM: {e}",
        }

    # --- Final Safety Catch-All ---
    except Exception as e:
        logger.exception("Unexpected unhandled exception in LLM pipeline: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": f"An unexpected system error occurred: {str(e)}",
        }









