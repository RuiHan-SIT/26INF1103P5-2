# AI Handover Assistant

> **INF1103 Programming Project (Group P5-2)**  
> An intelligent system for processing, sanitizing, and tracking employee work handovers using Gemini AI.

---

## 📖 About the Project

When an employee resigns, takes extended leave, or transfers roles, they prepare a handover for the colleague taking over their responsibilities. These notes often arrive as unstructured text missing critical details such as task ownership, deadlines, or dependencies.

This project uses Gemini AI and natural language processing to:
- Extract and categorize **Outstanding Tasks** vs. **Routine (BAU) Tasks**.
- Validate task owners, deadlines, and priorities.
- Sanitize sensitive personal data (NRIC, passport numbers, passwords).
- Offer both a **CLI prototype (Part 1)** and a **Django Web Application (Part 2)**.

---

## 🗂 Project Structure

```text
26INF1103P5-2/
│
├── part_2/                      # 🌟 Part 2: Django Web Application (SQLite)
│   ├── manage.py                # Django CLI tool
│   ├── config/                  # Django project configuration & settings
│   ├── apps/handovers/          # Handover features (models, views, services, urls)
│   ├── templates/               # Web layout and page templates
│   ├── static/                  # CSS, JS, and image assets
│   ├── media/                   # Uploaded handover files
│   └── README.md                # Detailed guide for Part 2 web application
│
├── src/                         # Part 1: Terminal / CLI Prototype
│   ├── main.py                  # CLI entry point
│   ├── offline_demo.py          # Offline demonstration script
│   ├── modules/                 # Handlers for inputs, gemini router, logic, & storage
│   ├── model/                   # Pydantic schemas for AI output
│   └── utils/                   # Config, logger, and Gemini client
│
├── data/                        # Sample data, employees, & mock responses
├── tests/                       # Unit and integration test suites
│
├── requirements.txt             # Python dependencies (Django, Gemini, Pydantic, etc.)
├── .env.example                 # Template for environment variables (API keys)
├── .gitignore                   # Ignore rules for virtualenvs, keys, SQLite, and media
├── Dockerfile                   # Docker container configuration
└── update.ps1                   # Docker build & test script
```

---

## 🚀 Quick Start Guide

### 1. Initial Setup

1. **Clone the repository and enter the directory**:
   ```powershell
   git clone https://github.com/RuiHan-SIT/26INF1103P5-2.git
   cd 26INF1103P5-2
   ```

2. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Set up API Key**:
   Create a `.env` file in the project root (or inside `part_2/`):
   ```env
   GEMINI_API_KEY=your-gemini-api-key-here
   ```

---

## 🌐 Running Part 2: Django Web Application (Recommended)

Part 2 is the full-featured web app using **Django** and a local **SQLite** database.

```powershell
# 1. Navigate into part_2
cd part_2

# 2. Run database migrations (creates SQLite tables)
python manage.py migrate

# 3. (Optional) Create an admin superuser
python manage.py createsuperuser

# 4. Start the Django web server
python manage.py runserver
```

Open your browser and visit:
- **Web App**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Panel**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

👉 *For detailed architecture, model details, and app guidelines, see [**`part_2/README.md`**](file:///D:/Project/School/26INF1103P5-2/part_2/README.md).*

---

## 💻 Running Part 1: Terminal / CLI Prototype

To run the interactive command-line interface:

```powershell
python src/main.py
```

### CLI Menu Options:
1. **Create a new handover** — Enter employee ID, enter notes or load a `.txt` file from `data/handovers/`.
2. **View a handover** — Search and view handovers by employee ID with audit history.
3. **Delete a handover** — Remove previously saved records.

---

## 🧪 Running Tests

To run the test suite across the project:

```powershell
python -m pytest -v
```

---

## 🐳 Docker (CLI Prototype)

To build and run the CLI application via Docker:

```powershell
# Build image
powershell -ExecutionPolicy Bypass -File .\update.ps1

# Run with persistent data
docker run --rm -it --env-file .env -v "${PWD}/data:/app/data" handover-app
```

---

## 🔒 Security & Git Hygiene

- **API Keys**: Never commit `.env` files to git.
- **Databases**: SQLite databases (`*.sqlite3`) are ignored by [`.gitignore`](file:///D:/Project/School/26INF1103P5-2/.gitignore) and kept local.
- **Uploads**: User media (`media/`) is ignored to prevent cluttering version control.
