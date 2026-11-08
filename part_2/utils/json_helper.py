import logging
import re
from typing import Any, Dict
import json_repair

logger = logging.getLogger(__name__)


def clean_llm_json(raw_text: str | None) -> Dict[str, Any]:
    """
    Sanitizes raw LLM output and converts it into a Python dictionary.
    Strips markdown code fences, locates JSON object boundaries, and repairs syntax errors.

    :param raw_text: Raw string response received from an LLM.
    :return: Sanitized dictionary parsed from the JSON string.
    :raises ValueError: If response is empty or cannot be parsed into a dictionary.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("LLM returned an empty or null response.")

    text = raw_text.strip()

    # Strip Markdown code fences if the model wrapped the JSON
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()

    # Locate outermost JSON object boundaries
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No valid JSON object found in response: {text[:100]}")

    json_str = text[start : end + 1]

    try:
        parsed = json_repair.loads(json_str)
        if not isinstance(parsed, dict):
            raise ValueError(f"Parsed JSON must be a dictionary, got {type(parsed).__name__}")
        return parsed
    except Exception as err:
        logger.error("Failed to repair or parse JSON from LLM: %s", err)
        raise ValueError(f"Malformed JSON from LLM: {err}") from err
