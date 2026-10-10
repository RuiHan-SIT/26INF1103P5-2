# AI Handover Auditor — Master Test Case Table

## 1. Purpose

This document defines the test cases used to verify the reliability and correctness of the AI Handover Auditor. It covers handover input processing, AI response validation, error handling, and automated testing without live API calls.

## 2. Master Test Case Table

| Test ID | Test Category       | Test Scenario                      | Test Input                                                  | Expected Result                                                                    | Priority |
| ------- | ------------------- | ---------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------- | -------- |
| TC01    | Valid Input         | Complete handover document         | Handover containing task, owner, and deadline               | Handover is processed and task information is extracted correctly                  | High     |
| TC02    | Incomplete Input    | Missing task owner                 | Handover containing a task without an owner                 | Missing owner is identified or represented according to the application schema     | High     |
| TC03    | Incomplete Input    | Missing deadline                   | Handover containing a task without a deadline               | Missing deadline is identified or represented according to the application schema  | High     |
| TC04    | Unstructured Input  | Messy or poorly formatted handover | Free-form notes containing task information                 | System processes identifiable information or reports appropriate validation issues | Medium   |
| TC05    | Empty Input         | Empty handover file                | Empty text file                                             | System handles empty input safely without an uncontrolled crash                    | High     |
| TC06    | Multiple Tasks      | Handover contains several tasks    | Document containing multiple task entries                   | All identifiable tasks are processed according to the expected schema              | High     |
| TC07    | Valid AI Response   | AI returns valid JSON              | JSON containing all required fields with correct data types | JSON is parsed and passes schema validation                                        | High     |
| TC08    | Invalid AI Response | AI returns malformed JSON          | `{invalid json`                                             | JSON parsing fails safely and an appropriate error is handled                      | High     |
| TC09    | Invalid AI Response | Required field is missing          | Valid JSON with a required field omitted                    | Schema validation fails and identifies the missing field                           | High     |
| TC10    | Invalid AI Response | Incorrect data type                | JSON containing a field with an invalid data type           | Schema validation rejects the response or reports a validation error               | High     |
| TC11    | Invalid AI Response | AI returns an empty response       | Empty string                                                | System handles the response safely without an uncontrolled crash                   | High     |
| TC12    | Invalid AI Response | Unexpected additional field        | Valid JSON containing an extra field                        | Additional field is accepted or rejected according to the documented schema policy | Medium   |
| TC13    | Error Handling      | Multiple validation errors         | JSON with multiple missing or invalid fields                | Validation failures are handled without an uncontrolled crash                      | High     |
| TC14    | Error Handling      | AI/API exception                   | Mock AI client raises an exception                          | Application handles the exception according to its error-handling policy           | High     |
| TC15    | Automated Testing   | AI response is mocked              | Predefined valid AI response                                | Test runs without requiring a live AI API call                                     | High     |
| TC16    | Automated Testing   | Invalid AI response is mocked      | Predefined malformed or invalid response                    | Error-handling behaviour is tested without a live AI API call                      | High     |

## 3. Test Case Details

### TC01 — Valid Handover

**Objective:** Verify that the system processes a complete handover correctly.

**Input:** A handover containing a task description, owner, and deadline.

**Expected result:** The system extracts the task information and produces data that conforms to the application's schema.

**Pass criteria:** The output matches the expected structure and values.

### TC02 — Missing Task Owner

**Objective:** Verify that missing ownership information is handled correctly.

**Input:** A handover containing a task and deadline but no owner.

**Expected result:** The missing owner is identified, represented, or flagged according to the application's requirements.

**Pass criteria:** The missing information is not silently replaced with an invented owner.

### TC03 — Missing Deadline

**Objective:** Verify that incomplete deadline information is handled correctly.

**Input:** A handover containing a task and owner but no deadline.

**Expected result:** The missing deadline is identified or represented according to the application's requirements.

**Pass criteria:** The system does not invent a deadline.

### TC07 — Valid AI Response

**Objective:** Verify that valid AI output passes parsing and schema validation.

**Input:** A JSON response containing all required fields with appropriate values and data types.

**Expected result:** The response is successfully parsed and validated.

**Pass criteria:** No parsing or schema validation errors occur.

### TC08 — Malformed JSON

**Objective:** Verify that malformed AI output is handled safely.

**Input:**
`{invalid json`

**Expected result:** JSON parsing fails and the application handles the error appropriately.

**Pass criteria:** The malformed response is not treated as successfully validated data.

### TC09 — Missing Required Field

**Objective:** Verify that the schema rejects responses missing mandatory fields.

**Input:** A JSON object that omits a required field from the Pydantic model.

**Expected result:** Schema validation fails.

**Pass criteria:** The missing field is reported or the validation failure is otherwise handled correctly.

### TC10 — Incorrect Data Type

**Objective:** Verify that fields contain values of the required types.

**Input:** A JSON response with a field containing an invalid data type.

**Expected result:** The response is rejected or a validation error is raised, depending on the schema and Pydantic configuration.

**Pass criteria:** The response does not silently pass validation when it violates the defined type requirements.

### TC11 — Empty AI Response

**Objective:** Verify that an empty response does not cause an uncontrolled crash.

**Input:** An empty string.

**Expected result:** The application handles the empty response with an appropriate error or failure result.

**Pass criteria:** The empty response is not treated as valid task data.

### TC12 — Unexpected Additional Field

**Objective:** Verify that additional fields follow the intended schema policy.

**Input:** A JSON response containing the expected fields and an additional field such as `"extra_info"`.

**Expected result:** The additional field is handled according to the Pydantic model configuration.

**Pass criteria:** Actual behaviour matches the documented policy.

### TC15 — No Live API Calls

**Objective:** Ensure automated tests do not depend on an external AI service.

**Input:** A predefined AI response supplied through a mock.

**Expected result:** The test executes using the mock response.

**Pass criteria:** No live AI API request is made during the test.

## 4. General Pass/Fail Criteria

A test passes when the observed behaviour matches the expected result.

A test fails when:

* Valid input is incorrectly rejected.
* Invalid AI output is incorrectly accepted.
* Required information is silently lost.
* The system invents missing task details.
* An error causes an uncontrolled application crash.
* Automated unit tests unexpectedly call the live AI API.

## 5. Notes

* Required fields and data types must match the project's actual Pydantic models.
* Error messages should be tested against the application's implemented error-handling behaviour.
* Additional-field behaviour must be confirmed from the Pydantic configuration.
* Automated tests should use mocks or fixtures for AI responses.
* Expected results should be refined when the application's actual interfaces and validation rules are confirmed.
