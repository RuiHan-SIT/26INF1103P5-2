import pytest
from utils.json_helper import clean_llm_json


def test_clean_llm_json_valid_dictionary():
    raw = '{"outstanding_tasks": [], "bau_tasks": [], "important_information": []}'
    result = clean_llm_json(raw)
    assert result == {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": []
    }


def test_clean_llm_json_strips_markdown_code_fences():
    raw = """
    ```json
    {
      "task": "Review security patches"
    }
    ```
    """
    result = clean_llm_json(raw)
    assert result == {"task": "Review security patches"}


def test_clean_llm_json_repairs_broken_json():
    # Trailing commas and single quotes
    raw = "{'task': 'Deploy app', 'owners': ['Bob',],}"
    result = clean_llm_json(raw)
    assert result["task"] == "Deploy app"
    assert result["owners"] == ["Bob"]


def test_clean_llm_json_rejects_empty_or_whitespace():
    with pytest.raises(ValueError, match="empty or null"):
        clean_llm_json("   ")


def test_clean_llm_json_rejects_no_json_object():
    with pytest.raises(ValueError, match="No valid JSON object found"):
        clean_llm_json("Here is some random explanation without braces")

    with pytest.raises(ValueError, match="No valid JSON object found"):
        clean_llm_json("[1, 2, 3]")
