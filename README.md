# AI Handover Management System

> **INF1103 Programming Project (Group P5-2)**  
> An intelligent system for extracting, sanitizing, validating, and tracking employee work handovers using Google Gemini AI.

---

## 📖 About the Project

When an employee resigns, goes on temporary reassignment, or takes extended leave, they prepare a handover document for the colleagues taking over their responsibilities. In practice, handover notes are often unstructured or incomplete—missing critical details such as task owners, deadlines, recurring frequencies, or subtask dependencies, or inadvertently containing sensitive personal data (PII).

This repository encompasses **both phases** of the project:
- **Part 1**: An interactive **Terminal / CLI Prototype** that validates user inputs, scrubs PII, extracts tasks via Gemini AI, checks business rules in memory, and persists records to flat JSON files with audit logs. Its code is kept in `part_1/` for reference only and is not part of the running Part 2 application.
- **Part 2 (`part_2/`)**: A full-featured **Django Web Application** backed by **SQLite**, featuring Word (`.docx`) template parsing, a 2-pass AI clarification workflow, deterministic offline table fallback, 3-tier employee identity matching, daily workload conflict detection, interactive calendar task execution with subtask dependency enforcement, and `.docx` handover export.

---

## 🔄 Evolution: Part 1 (CLI) vs. Part 2 (Django Web App)

| Capability | Part 1: CLI Prototype | Part 2: Django Web Application (`part_2/`) |
| :--- | :--- | :--- |
| **Interface** | Interactive terminal menu (`main.py`) | Multi-page responsive Django web UI with session state & AJAX status updates |
| **Authentication** | Manual entry of Name, Department & 7-digit Employee ID per session | Django authentication linked 1-to-1 with `Employee` profiles (`load_employees`) |
| **Supported Input** | Free-form terminal text or `.txt` files (`<= 5 MB`) | Word `.docx` handover documents (`<= 10 MB`, paragraphs + structured tables) |
| **PII Sanitization** | `scrubadub` + regex checks (`NRIC/FIN`, `Passport`, sensitive keywords) | `InputValidator` (`scrubadub` + regex checks) on both `.docx` uploads and clarification answers |
| **AI Integration** | Single-pass Gemini extraction (`gemini_router.py`) + `json-repair` + Pydantic | 2-pass `HandoverCoordinator` & `Gemini` (`LLMService`) + `JsonHelper` + Pydantic schemas (`apps/schema/`) |
| **Offline / AI Outage Handling** | Raises error / halts creation if API fails | Deterministic **Table Fallback Parser** extracts tasks directly from `.docx` tables + allows saving as `Needs Clarification` |
| **Clarification Workflow** | Terminal prompt loop (`fill_missing_information`) for missing fields | Interactive **AI Clarification Q&A** (`Refine with AI`) during draft review and on saved handovers |
| **Owner Matching** | Exact/fuzzy matching against `data/employees.json` in CLI | **3-Tier `EmployeeIdentityMatcher`** (Exact $\rightarrow$ Name Components $\rightarrow$ Fuzzy $\ge 70\%$) with mandatory reviewer confirmation |
| **Task Breakdown & Dependencies** | Flat `outstanding_tasks` (with deadlines) and `bau_tasks` (with frequencies) | Parent `Task` + ordered `Subtask` graph (`depends_on` M2M) with topological & chronological validation |
| **Workload Validation** | Not available | **`WorkloadValidator`** flags any employee assigned $> 4$ items on a single day across existing + proposed handovers |
| **Task Execution Tracking** | Read-only terminal view | Interactive **"My Tasks" Calendar** projecting one-off deadlines, planned subtasks, and recurring BAU dates (`TaskCompletion`) |
| **Data Persistence** | Local JSON files (`data/completed/*.json`) | Relational **SQLite** database (`Employee`, `Handover`, `Upload`, `Task`, `Subtask`, `TaskCompletion`) via CQRS (`HandoverRepository` & `HandoverQuery`) |
| **Document Export** | Formatted console report (`output.py`) | Downloadable formatted Word document (`CompletedHandoverDocumentGenerator` $\rightarrow$ `.docx`) |

---

## 🗂 Repository Structure

```text
26INF1103P5-2/
│
├── part_2/                                  # 🌟 Part 2: Django Web Application (SQLite)
│   ├── manage.py                            # Django management CLI
│   ├── requirements.txt                     # Part 2 Python dependencies
│   ├── .env.example                         # Environment template (DEBUG, SECRET_KEY, GEMINI_API_KEY, DISABLE_AI)
│   ├── config/                              # Django project settings, URLs, WSGI/ASGI
│   ├── apps/
│   │   ├── handovers/                       # Core handover web application
│   │   │   ├── views.py                     # HandoverController HTTP endpoints
│   │   │   ├── forms.py                     # HandoverUploadForm (.docx validation)
│   │   │   ├── urls.py                      # App routing
│   │   │   ├── input_handler/               # FileValidator, DocumentReader (.docx), InputValidator (PII)
│   │   │   ├── services/                    # Draft, Clarification, TaskExecution, Workload, Coordinator, Gemini
│   │   │   ├── logic_manager/               # Pure-Python domain rules (Handover, Task, Matcher, WorkloadValidator)
│   │   │   ├── data_manager/                # CQRS persistence (HandoverRepository, HandoverQuery, DataManagerError)
│   │   │   ├── models/                      # ORM models (Employee, Handover, Upload, Task, Subtask, TaskCompletion)
│   │   │   ├── output/                      # CompletedHandoverDocumentGenerator (.docx export)
│   │   │   ├── fixtures/employees.json      # Pre-configured employee directory for demo accounts
│   │   │   └── management/commands/         # `load_employees` management command
│   │   └── schema/                          # Pydantic schemas (HandoverSchema, OutstandingTaskSchema, BAUTaskSchema, SubtaskSchema)
│   ├── utils/                               # JsonHelper (json-repair) & HANDOVER_REVIEW_PROMPT
│   ├── templates/                           # HTML templates (home/review, my_tasks, history, handover_detail, login)
│   └── static/                              # CSS, JS, and downloadable template assets
│
├── part_1/                                  # 💻 Part 1 CLI prototype, kept for reference only (not part of the Part 2 app)
├── tests/                                   # 🧪 Comprehensive pytest suite for Part 2 & core modules
├── requirements.txt                         # Root Python dependencies
├── .env.example                             # Root environment variables template
├── Dockerfile                               # Container definition
└── update.ps1                               # Helper script to pull latest changes and build Docker image
```

---

## ⚙️ Prerequisites & Initial Setup

### 1. Prerequisites
- **Python 3.11+** (tested up to Python 3.14)
- **Google Gemini API Key** (optional if testing Offline Fallback Mode via `DISABLE_AI=True`)
- **Git** and (optional) **Docker Desktop**

### 2. Clone & Virtual Environment Setup

From PowerShell or your terminal at the repository root:

```powershell
# 1. Clone the repository
git clone https://github.com/RuiHan-SIT/26INF1103P5-2.git
cd 26INF1103P5-2

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
pip install -r part_2/requirements.txt
```

### 3. Configure Environment Variables (`.env`)

Create a `.env` file in the root directory **and** inside `part_2/` (or copy from `.env.example`):

```powershell
Copy-Item .env.example .env
Copy-Item part_2\.env.example part_2\.env
```

Edit `part_2/.env` (and root `.env` for Part 1):

```env
DEBUG=True
SECRET_KEY=change-this-in-production-to-a-secure-random-key
GEMINI_API_KEY=your-actual-gemini-api-key
DISABLE_AI=False
```

> [!TIP]
> Set `DISABLE_AI=True` in `part_2/.env` at any time to simulate a Gemini API outage and test the deterministic table fallback workflow without making external API calls.

---

## 🌐 Part 2 Guide: Django Web Application

### 1. Initialize the SQLite Database & Demo Accounts

Navigate into `part_2/`, run migrations, and seed the employee accounts from `apps/handovers/fixtures/employees.json`:

```powershell
cd part_2

# 1. Create/update SQLite database tables
python manage.py migrate

# 2. Seed registered employees and their login accounts (default password: handover123)
python manage.py load_employees

# 3. (Optional) Create a Django admin superuser
python manage.py createsuperuser
```

#### Pre-configured Demo Employee Logins
Running `python manage.py load_employees` creates the following login accounts (all using the default password **`handover123`**, or a custom password via `python manage.py load_employees --password <your_password>`):

| Username (Employee ID) | Employee Name | Department | Default Password |
| :--- | :--- | :--- | :--- |
| `2604707` | Goh Rui Han | Information Technology | `handover123` |
| `2601624` | Lim Ti Seng | Finance | `handover123` |
| `2604218` | Nur Shakira Binte Jamil | Human Resources | `handover123` |
| `2604249` | Rania Binte Mohammad Fadli | Marketing | `handover123` |
| `2603056` | Muhammad Haziq Bin Hamkah | Operations | `handover123` |
| `2601532` | Aqmar Haziq So Mohamed Kassim | Sales | `handover123` |

### 2. Start the Web Server

```powershell
python manage.py runserver
```

- **Web Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Django Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

### 🧭 Part 2 Full Demo Walkthrough

#### Step 1: Log In & Upload a `.docx` Handover Document
1. Sign in at `http://127.0.0.1:8000/accounts/login/` using one of the 7-digit Employee IDs above (e.g., `2604707` / `handover123`).
2. On the **Home** page, download the blank Word template if needed (`part_2/static/documents/Handover_Template.docx`), fill it in and upload it (must be `.docx`, non-empty, $\le 10\text{ MB}$).
3. **PII Guardrail**: `HandoverInputHandler` scans the document text using `scrubadub` and custom regex detectors (`NRIC/FIN`, `Passport`, `"password"`). If sensitive data is present, the upload is immediately blocked with an actionable error message before reaching Gemini AI.
4. **In-Flight Cancellation**: While Gemini is analyzing the document, clicking **Cancel** sends the request UUID token to `CancellationTracker` to abort processing and clean up any temporary upload.

#### Step 2: AI Extraction, Clarification Questions & Refinement (`Pass 1` $\rightarrow$ `Pass 2`)
1. Once extracted, the draft is stored in `PendingDraftSession` and displayed in the **Review Handover** screen, split into **One-off tasks** (`outstanding_tasks`) and **Recurring BAU tasks** (`bau_tasks`).
2. **BAU Frequency Protection**: If a recurring task had no frequency selected in the source Word table, `HandoverCoordinator.preserve_bau_frequencies()` prevents the AI from guessing one and prompts: *"What frequency should this recurring task use: weekly, monthly, or yearly?"*
3. Answer at least one clarification question per flagged task and click **Refine with AI**. Gemini updates the draft using your answers (after checking your answers for PII) while preserving task order and owner selections.

#### Step 3: 3-Tier Employee Identity Matching
1. For every owner name extracted from the document, `EmployeeIdentityMatcher` searches the employee directory across 3 levels:
   - **Level 1 (`Exact name match`)**: Case- and space-insensitive full name match.
   - **Level 2 (`Name parts match`)**: Matches all name components in any word order.
   - **Level 3 (`Possible spelling match`)**: Fuzzy `SequenceMatcher` ratio $\ge 70\%$.
2. Confirm the suggested employee or select a registered employee from the department/employee dropdowns. Every task must have at least one confirmed registered owner.

#### Step 4: Daily Workload Warning Check
1. `WorkloadReviewService` compares the proposed schedule (planned subtask dates for one-off tasks + recurring occurrences for BAU tasks over the next 365 days) against each owner's existing database tasks.
2. If any assigned owner exceeds **4 scheduled tasks on the same date**, a warning banner lists the overloaded dates and tasks. You can either adjust the dates or tick the **Acknowledge workload warning** checkbox (validated via a SHA-256 `workload_review_token`) to proceed.

#### Step 5: Offline / AI Fallback Mode & `Needs Clarification` Status
1. To demo AI failure resilience, set `DISABLE_AI=True` in `part_2/.env` and upload a `.docx` file.
2. `HandoverCoordinator.build_table_fallback_data()` automatically extracts tasks directly from the Word document tables and displays a warning banner.
3. If fields are still incomplete when saving during an AI outage, the handover is saved under **`Needs clarification`** status (instead of blocking submission) so work is never lost.

#### Step 6: Handover History, Detail Editing & `.docx` Export
1. Navigate to **Handover History** (`/history/`) to search handovers by ID (e.g., `H-0001`) or filter by status (`Completed` vs. `Needs Clarification`).
2. Click any handover to open its **Detail View**:
   - Click **Edit handover** to modify task fields, deadlines, BAU schedules, or subtasks.
   - Click **Ask AI to refine** to generate non-destructive AI suggestions (`request_ai_refinement`) that you can preview and either **Apply** or **Discard**.
   - Click **Save and recheck** to re-run `LogicHandover` validation; once all required fields are valid, a `Needs Clarification` handover automatically transitions to `Completed`.
3. Click **Download Word document** to generate and download `handover-XXXX.docx` via `CompletedHandoverDocumentGenerator`.

#### Step 7: Executing Assigned Tasks in "My Tasks" Calendar
1. Log in as an assigned task owner and visit **My Tasks** (`/my-tasks/`).
2. View scheduled items on the interactive calendar:
   - **Planned Subtasks** (`planned_date`)
   - **One-off Task Deadlines** (`deadline`)
   - **Recurring BAU Tasks** (projected dynamically by `weekly`, `monthly`, or `yearly` rules)
3. **Dependency Enforcement**:
   - Attempting to mark a subtask as complete before its prerequisite `depends_on` subtask(s) are complete returns a `409 Conflict` error.
   - Attempting to uncheck a prerequisite subtask while a later dependent subtask is still marked complete is also blocked.
   - Attempting to mark a parent one-off task complete before all of its subtasks are complete is blocked.

---

## 🧪 Running Automated Tests

### Run the Primary Test Suite (Root / Part 2)

From the project root:

```powershell
python -m pytest -v
```

Or using Django's test runner from inside `part_2/`:

```powershell
cd part_2
python manage.py test apps.handovers
```

The root `tests/` suite covers:
- `test_file_validator.py`, `test_document_reader.py`, `test_input_validator.py`, `test_handover_input_handler.py` (Upload & PII guardrails)
- `test_json_helper.py`, `test_handover_schema.py`, `test_handover_coordinator.py` (AI parsing, schema normalization & table fallback)
- `test_logic_manager_part2.py`, `test_handover_service.py` (Pure domain rules, subtask dependencies, employee matching & workload validation)
- `test_data_manager.py` (Repository & Query CRUD operations and `DataManagerError` handling)
- `test_refactored_services.py`, `test_needs_clarification_flow.py`, `test_webapp_views.py` (End-to-end service and controller flows)

---

## 🐳 Docker Instructions

### Running Part 2 (Django Web Application) in Docker

You can run the Part 2 Django web server inside a container from the project root:

```powershell
# 1. Build the image
docker build -t handover-app .

# 2. Run migrations, load demo employees, and launch the Django server on port 8000
docker run --rm -it -p 8000:8000 --env-file part_2/.env -w /app/part_2 handover-app sh -c "python manage.py migrate && python manage.py load_employees && python manage.py runserver 0.0.0.0:8000"
```

Then open [http://localhost:8000/](http://localhost:8000/) in your browser.

---

## 🔒 Security & Git Hygiene

- **API Keys & Secrets**: Never commit `.env` or `part_2/.env` to version control. Always use `.env.example` as the template.
- **PII Protection**: The application enforces strict pre-LLM PII detection (`NRIC/FIN`, `Passport`, passwords, and `scrubadub` detectors) so sensitive personal identifiers are blocked before any external API call or database write.
- **Local Databases & Uploads**: SQLite database files (`*.sqlite3`) and uploaded/generated documents (`part_2/media/`) are excluded via `.gitignore`.
