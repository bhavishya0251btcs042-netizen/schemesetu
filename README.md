# SchemeSetu — AI Citizen Services Navigator
**Powered by DAC · DBS Global University R&D and S&I Cell**

SchemeSetu helps students and citizens discover which government schemes and
scholarships they are eligible for, understand each one in plain language,
apply with an auto-filled form, and track the application with a tracking ID.

DBS Pitch Compendium — Project 07 (Domain: Government Services).

## Run it (Windows) — the easy way
1. Make sure **Python 3.10+** is installed. Get it from https://www.python.org/downloads/
   and tick **"Add Python to PATH"** during installation.
2. **Double-click `START.bat`.**
   - First run sets everything up automatically (this takes a minute).
   - Your browser opens at **http://127.0.0.1:8000**.
3. To stop: press **CTRL + C** in the black window, or just close it.

## Run it (Mac / Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap
python manage.py runserver
```

## What's inside
- **Eligibility engine** (`core/eligibility.py`) — rule-based matching of a citizen
  profile against each scheme's criteria, with pass/fail reasons.
- **Plain-language explainer** (`core/explainer.py`) — turns a scheme record into
  simple readable sentences.
- **Guided auto-fill** — application form pre-filled from the eligibility check.
- **Status tracking** — every application gets a `DACxxxxxx` tracking ID.
- **Admin panel** at `/admin` (login: `admin` / `admin123`) to add/edit schemes
  and update application status.

## Managing schemes
Log in to `/admin`, open **Schemes**, and add or edit entries. Eligibility rules
(income cap, age range, categories, gender, education level, state, students-only)
are plain fields — no code needed.

## Before a real/public deployment
- Change `SECRET_KEY` and set `DEBUG = False` in `schemesetu/settings.py`.
- Change the admin password.
