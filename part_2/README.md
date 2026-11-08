# Handover Management System — Part 2 (Django Web App)

> **INF1103 Programming Project (Group P5-2)**  
> A Django web application designed to help employees prepare, validate, and manage work handover documents using AI task extraction and SQLite.

---

## 📌 Overview

When employees resign, change roles, or take extended leave, handover notes are frequently messy or incomplete—often omitting who owns a task, what is outstanding, or when deadlines fall.

---

## 🛠 Tech Stack

- **Framework**: Django 5+ (Python)
- **Database**: SQLite (`db.sqlite3`)
- **AI / LLM**: Google Gemini API (`google-genai`)
- **PII Scrubbing**: `scrubadub`
- **Validation**: Pydantic
- **Frontend**: Django Templates, Vanilla HTML5 & CSS3

---

## 📁 Directory Structure

```text
part_2/
├── manage.py                  # Django CLI management script
├── db.sqlite3                 # Local SQLite database (ignored by git)
├── requirements.txt           # Python package dependencies
├── .env.example               # Environment variables template
│
├── config/                    # Django project configuration
│   ├── __init__.py
│   ├── settings.py            # SQLite database & app configurations
│   ├── urls.py                # Main URL router
│   ├── asgi.py                # ASGI entrypoint
│   └── wsgi.py                # WSGI entrypoint
│
├── apps/                      # Django application modules
│   ├── __init__.py
│   └── handovers/             # Core handover management app
│       ├── migrations/        # SQLite database migration files
│       ├── admin.py           # Django admin registrations
│       ├── apps.py            # App configuration
│       ├── forms.py           # Forms and user input validation
│       ├── models.py          # SQLite database schema models
│       ├── services.py        # Business logic & AI/Gemini integration
│       ├── urls.py            # Handover route endpoints
│       ├── views.py           # View controllers (request handling)
│       └── tests.py           # App unit tests
│
├── templates/                 # Global HTML templates
│   ├── base.html              # Base HTML skeleton & navigation
│   ├── partials/              # Reusable template components
│   └── handovers/             # Handover app templates (e.g. home.html)
│
├── static/                    # Global static files
│   ├── css/style.css          # App stylesheet
│   ├── js/main.js             # Client-side scripts
│   └── images/                # Static image assets
│
└── media/                     # User uploads (e.g., uploaded handover documents)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ installed
- A Google Gemini API key

### 2. Environment Setup

From the root directory or inside `part_2/`, ensure your virtual environment is active:

```powershell
# Navigate into part_2 (if not already there)
cd part_2

# If virtual environment is not yet created (from project root):
python -m venv ..\.venv

# Activate the virtual environment
..\.venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create your `.env` file by copying the example:

```powershell
Copy-Item .env.example .env
```

Open `.env` and fill in your Gemini API key:
```env
DEBUG=True
SECRET_KEY=your-custom-secret-key
GEMINI_API_KEY=your-actual-gemini-api-key
```

> [!WARNING]
> Never commit your `.env` file containing actual API keys to GitHub. It is protected by `.gitignore`.

---

## 🗄 Database Management (SQLite)

The application uses SQLite as its primary database. The database file `db.sqlite3` lives inside `part_2/`.

### Apply Migrations
To update or initialize tables in your SQLite database:

```powershell
python manage.py migrate
```

### Create New Migrations
When you add or edit database models in `apps/handovers/models.py`:

```powershell
python manage.py makemigrations
python manage.py migrate
```

---

## 🖥 Running the Application

### 1. Create an Admin User (Superuser)
```powershell
python manage.py createsuperuser
```
Follow the interactive prompts to set your username, email, and password.

### 2. Start the Development Server
```powershell
python manage.py runserver
```

Open your browser and navigate to:
- **Application Home**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Admin Dashboard**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🧪 Running Tests

To run the automated test suite:

```powershell
python manage.py test apps.handovers
```
or with pytest from the project root:
```powershell
python -m pytest
```

---

## 👥 Team Guidelines & Best Practices

1. **Keep Secrets Secret**: Keep all API keys in `.env`.
2. **App Architecture**: Place business logic (AI calls, PII redaction) in `apps/handovers/services.py`, keeping views clean.
3. **Database Changes**: Always run `python manage.py makemigrations` and commit your migration files in `apps/handovers/migrations/` (do not commit `db.sqlite3`).
4. **Git Hygiene**: Run `git pull` before starting new features or pushing changes.
