import requests
import json
from src.utils.openai_client import client 
from src.utils.logger import logger
from src.utils.llm_prompt import SYSTEM_PROMPT
from src.model.handover_model import HandoverReport
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


#input can be either string or Array
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



user_input = r"""Handover Notes - Project Ops & Floor Management (WIP)
Leaving this here since my flight is early Monday and I didn't get to finish the Notion board.

First off, the inventory reconciliation for Q3 is about 85% done. The raw count sheet is sitting on the clipboard next to the label printer in warehouse 2, but the pallet in bay 14 has three unmarked boxes of thermal rolls that weren't added to the auditor file. Ask Priya before entering those into the system—she mentioned the supplier sent a split batch because the courier ran out of space on Tuesday.

Pending supplier stuff:
- Alpha Logistics: their driver (Ken, mobile +65 9123 4567) only delivers before 10 AM on weekdays. If he arrives after that, security won't let the lorry dock at Gate 3 without a manual clearance chit from Dave.
- The packaging tape order is delayed until next Thursday. We have roughly 12 rolls left in the mezzanine rack, which should last until Tuesday if packing doesn't go crazy over the weekend.
- Invoices: Brenda from finance flagged two duplicate PO numbers from August (PO-88219 and PO-88220). Do not approve the payment run on Wednesday until she confirms which one is void.

Key & Access cards:
The spare keycard for the backup server cabinet isn't in the usual keybox. I handed it to Marcus on Thursday because the network switch in comms closet B had a failing fan that was throwing intermittent thermal warnings. Make sure to collect it back from his desk drawer (top left, key is taped underneath). The master padlock code for the rear loading bay roll-up shutter was rotated to 7392 on the 15th after the lock replacement.

Ongoing issues / watchouts:
1. The label applicator machine on line 2 jams whenever using the matte synthetic stock. Engineering knows about it, but the replacement roller won't arrive until mid-October. Keep it on semi-gloss or adjust the feed speed down to 60% if you get an error 404 on the feed sensor.
2. Building management is running a fire alarm pressure test next Friday at 2:30 PM. The loading bay doors will auto-seal for about twenty minutes, so pause any pallet transfers around 2:15 PM so the forklifts don't get trapped outside.
3. Don't touch the thermostat setting in the sample archive room—the sensor calibration is offset by -3 degrees, so setting it to 22C actually drops the room to 19C, which makes condensation form on the metal shelving.

Routine contact list:
- Facility manager: Mr. Tan (office extension 4022)
- Waste disposal vendor: GreenCycle dispatch (+65 6789 0123, account code GC-4490)
- Cleaning supervisor: Madam Halimah (she comes in at 6 PM, leaves the sanitiser restock logs on the breakroom noticeboard)

Good luck, ping me on Slack if anything completely catches fire during your first week!"""
print(send_to_llm(user_input))







