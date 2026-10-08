import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load variables from the .env file into environment
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Point directly to the .env in the root
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

api_key = os.getenv("GEMINI_API_KEY")

# Automatic retry for transient failures (rate limits, timeouts, 5xx).
# The SDK retries with exponential backoff + jitter BEFORE raising an
# exception, so send_to_llm's handlers only see errors that survive retries.
#   delay = min(initial_delay * exp_base**(attempt-1) * (1 +/- jitter), max_delay)
_retry_options = types.HttpRetryOptions(
    attempts=5,              # total attempts, including the original request
    initial_delay=1.0,       # seconds before the first retry
    max_delay=30.0,          # cap on backoff between retries
    exp_base=2.0,            # exponential backoff multiplier
    jitter=1.0,              # randomness factor to avoid thundering herd
    # Only these transient status codes are retried; 4xx like 400/401/404 fail fast.
    http_status_codes=[408, 429, 500, 502, 503, 504],
)

# The genai Client reads the key explicitly so misconfiguration fails fast/clearly
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        timeout=300_000,  # per-request timeout in milliseconds (300s)
        retry_options=_retry_options,
    ),
)


__all__ = ["client"]
