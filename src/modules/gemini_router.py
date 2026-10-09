import json
from typing import Any

from google.genai import errors, types

from utils.gemini_client import client
from utils.logger import logger
from utils.llm_prompt import SYSTEM_PROMPT
from model.handover_model import HandoverReport
from pydantic import ValidationError
import re
import json_repair

""" 
1) send the user input to Gemini 3.6 Flash and get a completion ( done )
2) handle API status/error codes, malformed output, rate limits,
   response timeouts / API unreachable, and empty responses from the LLM
3) handle output validation with the Pydantic schema

Retry note: transient failures (408/429/5xx, timeouts) are retried
automatically by the client (see utils/gemini_client.py) with exponential
backoff before any exception reaches the handlers below. So a 429/5xx that
lands here means the retry budget was already exhausted.
"""



# Validate the data from the response and handle errors
# handles markdown returned by the LLM
# checks for empty data
# takes JSON text from the API and returns a Python dict
def clean_llm_json(raw_text: str | None) -> dict[str, Any]:
    """Sanitizes raw LLM output into a dictionary ready for Pydantic."""
    if not raw_text or not raw_text.strip():
        raise ValueError("LLM returned an empty or null response.")

    text = raw_text.strip()

    # Strip Markdown code fences if the model wrapped the JSON
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()

    # Locate the outermost JSON object bounds (strips preambles/postscripts)
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


def send_to_llm(user_input: str):
    try:
        MODEL = "gemini-3.6-flash"
        # Gemini 3.6 Flash hard limits (shared by the free tier; free tier only caps RATE):
        #   - input context window : ~1,048,576 tokens (available automatically, no setting needed)
        #   - max output tokens     : 65,536  <- set below so long reports never get truncated
        MAX_OUTPUT_TOKENS = 65536
        response = client.models.generate_content(
            model=MODEL,
            contents=user_input,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=1,
                # Max output the model allows; prevents truncated/incomplete JSON reports
                max_output_tokens=MAX_OUTPUT_TOKENS,
                # Ask Gemini to emit raw JSON directly
                response_mime_type="application/json",
            ),
        )

        raw_content = response.text
        # print(raw_content)

        # Gemini may still wrap/pad the JSON, so sanitize before validating
        parsed_dict = clean_llm_json(raw_content)

        # Pass the plain dict to standard Pydantic validation
        return HandoverReport.model_validate(parsed_dict)

    # --- Gemini API Errors ---
    # Gemini raises errors.ClientError (4xx) and errors.ServerError (5xx),
    # both subclasses of errors.APIError, exposing .code, .status and .message.
    #   400 - bad request / input exceeds context window
    #   401 - invalid authentication or API key rejected
    #   403 - insufficient permissions
    #   404 - model not found / unavailable
    #   429 - rate limit exceeded (free tier RPM/RPD quota) -- retries exhausted
    except errors.ClientError as e:
        if e.code == 400:
            logger.error("Bad request parameters: %s", e)
            message = "Invalid request sent to AI service. Check parameter constraints or file size."
        elif e.code in (401, 403):
            logger.critical("Auth failed: %s", e)
            message = "Authentication failed: Gemini API key is missing, invalid, expired, or lacks permissions."
        elif e.code == 404:
            logger.error("Model not found: %s", e)
            message = "The requested AI model name was not recognized or is temporarily unavailable."
        elif e.code == 429:
            logger.warning("Rate limit hit (retries exhausted): %s", e)
            message = "Rate limit exceeded (free tier quota). Please wait a moment before trying again."
        else:
            logger.error("Gemini client error (%s): %s", e.code, e)
            message = f"AI service rejected the request ({e.code}): {e.message}"
        return {
            "success": False,
            "data": None,
            "error_message": message,
        }

    #   500 / 502 / 503 / 504 - Gemini internal/server-side failures (retries exhausted)
    except errors.ServerError as e:
        logger.error("Gemini server error (%s), retries exhausted: %s", e.code, e)
        return {
            "success": False,
            "data": None,
            "error_message": "Gemini service is temporarily unavailable after retries. Please try again later.",
        }

    # --- Network / timeout / unreachable (not surfaced as APIError) ---
    # The genai SDK sits on httpx; connection drops, DNS failures and
    # read timeouts bubble up as stdlib TimeoutError / ConnectionError
    # once the automatic retry budget is used up.
    except (TimeoutError, ConnectionError) as e:
        logger.error("Network connection error after retries: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": "Network timeout: Unable to reach Gemini servers after retries. Check your internet connection.",
        }

    # --- Any other Gemini API error we didn't special-case ---
    except errors.APIError as e:
        logger.error("Unhandled Gemini API error: %s", e)
        return {
            "success": False,
            "data": None,
            "error_message": f"Unexpected AI service error: {e}",
        }

    # --- Pydantic Validation Errors ---
    except ValidationError as e:
        logger.error("LLM schema mismatch (%d errors): %s", e.error_count(), e)
        raise ValueError(f"LLM output did not match expected Handover schema: {e}") from e

    # --- JSON parsing / sanitization Errors ---
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
