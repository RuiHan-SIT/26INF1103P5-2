# AI Handover Auditor — Master Test Case Documentation

## 1. Purpose

This document describes the automated test cases used to verify the reliability, correctness, and error-handling behaviour of the AI Handover Auditor project.

The test suite covers four main areas:

1. Gemini response processing and JSON cleaning.
2. Handover data schema validation using Pydantic.
3. Handover processing, task validation, and deadline handling.
4. Integration testing of file input, mocked AI responses, and core application logic.

The tests are implemented using `pytest`. AI responses are mocked or hardcoded where appropriate to ensure that automated tests can run without depending on live Gemini API calls.

## 2. Test Files and Coverage

| Test File               | Module Under Test                                                 | Purpose                                                                                               |
| ----------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `test_gemini_router.py` | `modules/gemini_router.py`                                        | Tests JSON cleaning, invalid responses, and mocked Gemini API interactions.                           |
| `test_handove_model.py` | `model/handover_model.py`                                         | Tests Pydantic schema validation, missing fields, invalid data types, and unexpected fields.          |
| `test_logic_manager.py` | `modules/logic_manager.py`                                        | Tests deadline validation, task validation, handover processing, task sorting, and output formatting. |
| `test_intergration.py`  | `main.py`, `modules/input_handler.py`, `modules/logic_manager.py` | Tests file input and the handover processing workflow using a mocked AI response.                     |

**Note:** The filenames `test_handove_model.py` and `test_intergration.py` retain their current spellings. If these files are renamed in the project, update the documentation accordingly.

## 3. Master Test Case Table

### 3.1 Gemini Router Tests

**Test file:** `test_gemini_router.py`

| Test ID | Test Scenario                        | Test Input                                   | Expected Result                                                                                        | Priority |
| ------- | ------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------------------------------------ | -------- |
| GR01    | Response contains no JSON object     | Plain text without JSON                      | `ValueError` is raised with a message indicating that no JSON object was found.                        | High     |
| GR02    | Empty AI response                    | Empty string                                 | `ValueError` is raised for an empty or null response.                                                  | High     |
| GR03    | JSON wrapped in Markdown code fences | Valid JSON inside a Markdown code block      | JSON is cleaned and returned as a Python dictionary.                                                   | High     |
| GR04    | Whitespace-only AI response          | String containing only whitespace            | `ValueError` is raised for an empty or null response.                                                  | High     |
| GR05    | Gemini API call is mocked            | Handover text and a predefined fake response | The mocked Gemini client returns the expected parsed dictionary without requiring a real API response. | High     |

### 3.2 Handover Model Tests

**Test file:** `test_handove_model.py`

| Test ID | Test Scenario                                | Test Input                                             | Expected Result                                                                      | Priority |
| ------- | -------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------ | -------- |
| HM01    | Missing required outstanding task field      | Outstanding task without the required `task` field     | Pydantic raises `ValidationError`.                                                   | High     |
| HM02    | Missing required BAU task field              | BAU task without the required `task` field             | Pydantic raises `ValidationError`.                                                   | High     |
| HM03    | Important information without an alert field | Important information containing only `context`        | Validation succeeds and the context is normalized into a string in the output list.  | High     |
| HM04    | Invalid owners data type                     | `owners` supplied as an integer                        | Pydantic raises `ValidationError`.                                                   | High     |
| HM05    | Invalid task data type                       | `task` supplied as an integer                          | Pydantic raises `ValidationError`.                                                   | High     |
| HM06    | Unexpected task field                        | Valid task containing an additional `unexpected_field` | Validation succeeds, and the unexpected field is excluded from the validated output. | Medium   |

### 3.3 Logic Manager Tests

**Test file:** `test_logic_manager.py`

| Test ID | Test Scenario                        | Test Input                                             | Expected Result                                                                        | Priority |
| ------- | ------------------------------------ | ------------------------------------------------------ | -------------------------------------------------------------------------------------- | -------- |
| LM01    | Valid future deadline                | Date seven days in the future                          | `validate_deadline()` returns `True`.                                                  | High     |
| LM02    | Past deadline                        | Date one day in the past                               | `validate_deadline()` returns `False`.                                                 | High     |
| LM03    | Incorrect deadline format            | Deadline in `YYYY-MM-DD` format                        | `validate_deadline()` returns `False`.                                                 | High     |
| LM04    | Empty deadline                       | Empty string                                           | `validate_deadline()` returns `False`.                                                 | High     |
| LM05    | Valid outstanding task               | Outstanding task with valid fields                     | `validate_outstanding_task()` returns an empty error list.                             | High     |
| LM06    | Outstanding task without owner       | Outstanding task with an empty owners list             | Returns `["missing_owner(s)"]`.                                                        | High     |
| LM07    | Outstanding task without description | Outstanding task with an empty description             | Returns `["description"]`.                                                             | High     |
| LM08    | Outstanding task without deadline    | Outstanding task with an empty deadline                | Returns `["missing_deadline"]`.                                                        | High     |
| LM09    | Valid BAU task                       | BAU task with valid fields                             | `validate_bau_task()` returns an empty error list.                                     | High     |
| LM10    | BAU task without owner               | BAU task with an empty owners list                     | Returns `["missing_owner(s)"]`.                                                        | High     |
| LM11    | BAU task without description         | BAU task with an empty description                     | Returns `["description"]`.                                                             | High     |
| LM12    | Handover without tasks               | Empty outstanding task and BAU task lists              | Processing returns an `incomplete` status and identifies `no_tasks`.                   | High     |
| LM13    | Valid handover                       | Handover containing valid outstanding and BAU tasks    | Processing returns a `complete` status without an `errors` key.                        | High     |
| LM14    | Outstanding tasks sorted by deadline | Two valid tasks with different future deadlines        | Tasks are sorted from the earliest deadline to the latest deadline.                    | High     |
| LM15    | Deadline output formatting           | Valid deadline in `DD/MM/YYYY` format                  | Output deadline is formatted as `DD Mon YYYY`, for example, `15 Oct 2026`.             | Medium   |
| LM16    | Realistic handover fixture response  | Hardcoded AI response containing two outstanding tasks | Processing returns a `complete` status and preserves both tasks in the expected order. | High     |

### 3.4 Integration Tests

**Test file:** `test_intergration.py`

| Test ID | Test Scenario                      | Test Input                                                | Expected Result                                                                                           | Priority |
| ------- | ---------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------- |
| IT01    | File input with mocked AI response | `valid_handover.txt` fixture and a predefined AI response | File contents are passed to the mocked AI function, and the resulting handover is processed successfully. | High     |

## 4. Test Execution

### 4.1 Prerequisites

Ensure that Python and the project's required dependencies are installed, including `pytest` and the packages required by the application.

Run the commands from the project root directory.

### 4.2 Run All Tests

```bash
python -m pytest tests/ -v
```

This executes all test files in the `tests/` directory and displays individual test results.

### 4.3 Run Tests by File

Run individual test modules when debugging or verifying changes.

```bash
python -m pytest tests/test_gemini_router.py -v
python -m pytest tests/test_handove_model.py -v
python -m pytest tests/test_logic_manager.py -v
python -m pytest tests/test_intergration.py -v
```

### 4.4 Run a Specific Test

Use `-k` to select tests by part of their function name.

```bash
python -m pytest tests/ -v -k deadline
```

This runs tests whose names contain `deadline`.

## 5. General Pass/Fail Criteria

A test passes when the observed behaviour matches its expected result.

A test fails when one or more of the following occurs:

* Invalid or empty AI responses are accepted without appropriate error handling.
* Valid JSON cannot be cleaned and processed correctly.
* Required handover fields or data types are not validated as expected.
* Missing task owners, descriptions, or deadlines are not identified.
* Invalid deadlines are accepted.
* Valid outstanding tasks are not sorted or formatted correctly.
* An empty handover is incorrectly marked as complete.
* Valid handover data is incorrectly rejected.
* File input does not pass the expected contents to the AI processing function.
* Automated tests unexpectedly depend on a live Gemini API call.

## 6. Mocking and Test Data

The test suite uses predefined responses and fixtures to make test results repeatable.

* **Mocked Gemini API:** The Gemini router test replaces the API client's `generate_content` method with a fake response.
* **Hardcoded AI responses:** Logic manager tests use predefined dictionaries to verify validation and processing behaviour.
* **File fixtures:** The integration test reads `valid_handover.txt` from the test fixtures directory.
* **Mocked user input:** The integration test simulates the user entering a filename.
* **Pydantic validation:** Handover model tests verify that missing fields and invalid data types raise the expected validation errors.

These approaches allow the test suite to focus on application behaviour without requiring live AI responses for every test.

## 7. Limitations and Future Improvements

The current tests cover important validation and processing paths, but the following areas may be added or expanded in future testing:

* Empty handover files and malformed file input.
* Gemini API exceptions and network failures.
* Malformed JSON that contains an opening brace but is syntactically invalid.
* Additional boundary cases for deadline validation.
* Multiple simultaneous validation errors.
* More integration tests for incomplete handovers and invalid AI responses.
* Regression tests for any defects discovered during development.

These are potential improvements and are not claimed to be covered by the current four test files.

## 8. Summary

The automated test suite verifies the AI Handover Auditor at both unit and integration levels.

The four test modules cover Gemini response processing, Pydantic schema validation, core handover logic, and the integration of file input with mocked AI responses. Running the complete suite helps identify regressions and confirms that the tested application behaviour matches the expected requirements.
