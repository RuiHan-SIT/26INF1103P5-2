import pytest                                                                                                                          
from modules import gemini_router  

# ===========================================================================
# 1. Gemini response JSON cleaning tests
# ===========================================================================

def test_clean_llm_json_rejects_response_without_json():
    with pytest.raises(ValueError, match="No JSON object found"):
        gemini_router.clean_llm_json(
            "The AI could not generate a response."
        )


def test_clean_llm_json_rejects_empty_response():
    with pytest.raises(ValueError, match="empty or null response"):
        gemini_router.clean_llm_json("")


def test_clean_llm_json_removes_markdown_code_fences():
    raw_response = '''```json
    {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": []
    }
    ```'''

    result = gemini_router.clean_llm_json(raw_response)

    assert result == {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [],
    }


def test_clean_llm_json_rejects_whitespace_response():
    with pytest.raises(ValueError, match="empty or null response"):
        gemini_router.clean_llm_json("   \n\t   ")


# ===========================================================================
# 2. Mocked Gemini API test
# ===========================================================================

def test_send_to_llm_uses_mocked_gemini_api(monkeypatch):
    """Verify send_to_llm uses a mock instead of the real Gemini API."""

    fake_response = type(
        "FakeResponse",
        (),
        {
            "text": (
                '{"outstanding_tasks": [], '
                '"bau_tasks": [], '
                '"important_information": []}'
            )
        },
    )()

    def fake_generate_content(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(
        gemini_router.client.models,
        "generate_content",
        fake_generate_content,
    )

    result = gemini_router.send_to_llm("Test handover input")

    assert result == {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [],
    }
