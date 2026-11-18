# HRMS – Human Resource Management System

A simple, well-tested HR web application for a **Software Quality Engineering** project.

* **Frontend:** plain HTML, CSS and JavaScript (no frameworks)
* **Backend:** Python + Flask, SQLite database (a single file, created automatically, nothing to install)
* **Testing:** pytest (unit + API/database) and Selenium WebDriver (browser), with coverage,
  HTML reports, static analysis (flake8) and mutation testing

> New on the team? Follow **[SETUP-GUIDE.md](SETUP-GUIDE.md)** for step-by-step installation on Windows.
> The test strategy and requirement traceability are in **[docs/TEST_PLAN.md](docs/TEST_PLAN.md)**.

---

## Features

| Module | What you can do |
|---|---|
| **Login** | Administrator sign-in, sign-out, lock-out after 5 failed attempts, change password |
| **Dashboard** | Totals, present / absent / on leave / not marked today, pending leave, employees per department, recent hires |
| **Employees** | Add, edit, delete (with confirmation), search by name / ID / email / CNIC, filter by department and status. Auto-generated IDs (`EMP-0001`) |
| **Departments** | Create, rename, delete (only when empty), employee count |
| **Attendance** | Daily sheet for any past date, quick entry, update existing records, history with filters |
| **Leave** | Apply (Annual / Sick / Casual), live balance, approve, reject with reason, filter by status |
| **Settings & Rules** | Every business rule listed in one place; change password |

## Business rules (all enforced in the browser **and** on the server)

Defined once in [`backend/rules.py`](backend/rules.py). Change a value there and the server, the browser
validation and the hints all follow.

| Rule | Value |
|---|---|
| Age on the hire date | **18 – 60** years |
| Minimum monthly wage | **Full-time PKR 40,000 · Part-time PKR 20,000 · Contract PKR 40,000** |
| Maximum salary | PKR 5,000,000 (catches typing mistakes), max. 2 decimals |
| Earliest hire date | **2010-01-01** (the company did not exist before) |
| Latest hire date | **today + 90 days** |
| Names | 2–50 letters (spaces, `'` and `-` allowed) |
| Email / CNIC | valid format, **unique**; CNIC format `12345-1234567-1` |
| Phone | 10–15 digits |
| Attendance | one record per employee per day; not in the future; not before the hire date; only active employees; not on a day of approved leave |
| Late arrival | check-in after **09:15** must be *Late*; *Late* requires a check-in after 09:15 |
| Working hours | check-in from 06:00; check-out after check-in; max **16 h**; *Half Day* max **5 h** |
| Leave | not in the past; end ≥ start; max **15 days** per request; no overlaps; yearly entitlement Annual 20 / Sick 10 / Casual 10 |
| Leave decision | only *Pending* requests; a rejection needs a reason |
| Departments | unique name (case-insensitive); cannot delete a department that still has employees |

## Project structure

```
hrms-python/
├── app.py                    Start the web app:  python app.py
├── seed_demo.py              Optional demo data: python seed_demo.py
├── run_quality_checks.py     All quality checks + reports in one command
├── requirements.txt          Python packages (exact versions)
├── pytest.ini  .coveragerc  .flake8
├── backend/
│   ├── rules.py              Business rules (single source of truth)
│   ├── validators.py         Pure validation functions (no database) – unit tested
│   ├── services.py           Business operations: uniqueness, overlaps, balances …
│   ├── database.py           SQLite schema with UNIQUE / CHECK / FOREIGN KEY constraints
│   └── app.py                Flask: JSON API under /api + serves the frontend
├── frontend/
│   ├── *.html                login, dashboard, employees, employee-form, departments,
│   │                         attendance, leaves, settings, 404
│   ├── css/style.css         The whole design (no frameworks)
│   └── js/                   api.js (fetch helper), layout.js (menu, toasts, dialogs),
│                             validation.js (browser-side copy of the rules)
├── tests/
│   ├── unit/                 199 tests – business rules, boundary values
│   ├── api/                  98 tests – API + database integration
│   ├── selenium/             51 tests – real Chrome browser (Page Object Model)
│   ├── factories.py          Valid test data builders
│   └── conftest.py           Fixtures: temporary database per test
├── quality/mutation_check.py Mutation testing (14 deliberate bugs, all must be caught)
├── docs/TEST_PLAN.md         Strategy, techniques, traceability matrix, defect log
└── reports/                  Generated: test-report.html, coverage/
```

## Quick start

Requirements: **Python 3.10 or newer** (3.12/3.13 recommended) and **Google Chrome** (for the Selenium tests).

Windows (PowerShell), inside the project folder:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:8000** and sign in with **admin@hrms.local / Admin@123**.
Optional: `python seed_demo.py` (with the app stopped) loads 12 demo employees with attendance and leave.

The database file `hrms.db` is created automatically in the project folder. Delete it to start over.

## Running the tests

Activate the virtual environment first (`.venv\Scripts\activate` on Windows).

| What | Command | Tests |
|---|---|---|
| Everything + reports + coverage check | `python run_quality_checks.py` | 348 |
| Everything except the browser | `python run_quality_checks.py --fast` | 297 |
| Unit tests only | `pytest tests/unit` | 199 |
| API + database tests only | `pytest tests/api` | 98 |
| Selenium browser tests only | `pytest tests/selenium` | 51 |
| By marker | `pytest -m unit` · `pytest -m api` · `pytest -m selenium` | |
| One file / one test | `pytest tests/unit/test_salary_rules.py` · `pytest -k minimum_wage` | |
| Code style (static analysis) | `flake8` | |
| Mutation testing | `python quality/mutation_check.py` | 14 mutants |

**Selenium:** Chrome opens and runs each scenario automatically. The matching ChromeDriver is downloaded by
Selenium Manager on the first run (internet needed once). To hide the browser window:

* Windows PowerShell: `$env:HRMS_HEADLESS = "1"; pytest tests/selenium`
* macOS / Linux: `HRMS_HEADLESS=1 pytest tests/selenium`

The browser tests start their own copy of the app on a free port with a temporary database, so you do
**not** need to start `app.py`, and your own data is never touched.

### Reports

| Report | Where |
|---|---|
| HTML test report (every test, pass/fail, duration, screenshots of failures) | `reports/test-report.html` |
| Code coverage (line + branch, per file) | `reports/coverage/index.html` |
| Selenium failure screenshots | `reports/screenshots/` |

Results of the last verified run are summarised in [`reports/RESULTS.md`](reports/RESULTS.md).

## Quality techniques used

* **Boundary value analysis** – every limit is tested just below, at and just above (age 17/18/60/61,
  wage 39,999.99/40,000, hire date 2009-12-31/2010-01-01, today+90/+91, 09:15/09:16 …).
* **Equivalence partitioning** – valid and invalid classes for names, emails, phones, CNICs, dates.
* **Three test levels** – unit (rules), integration (API + real SQLite), system/E2E (Selenium in Chrome).
* **Defence in depth** – rules checked in the browser, in the server and by database constraints;
  tests prove the server rejects bad data even if the browser is bypassed.
* **Page Object Model** for maintainable Selenium tests; automatic screenshots on failure.
* **Code coverage** with a 90 % minimum (currently 98 %).
* **Static analysis** with flake8.
* **Mutation testing** – 14 deliberate bugs are injected; the suite must detect every one (score 100 %).
* **Deterministic tests** – "today" is passed into the validators; every test gets a fresh database.

## Security notes

Passwords are hashed (Werkzeug/scrypt), sessions use HttpOnly + SameSite cookies, every API endpoint
except login and rules requires a session, SQL uses parameters only (no string building), and all output
in the browser is HTML-escaped. This is a teaching project: before real use, change the default password,
set `HRMS_SECRET_KEY`, and run it behind HTTPS with a production server (e.g. waitress or gunicorn).

## Limitations (by design, to keep the project basic)

* One administrator role (no employee self-service portal, no multiple companies).
* Leave is counted in calendar days (weekends and public holidays are not excluded); a request is counted
  against the year in which it starts.
* Attendance assumes day shifts (no check-out after midnight).
* No email notifications, no payroll, no file uploads.
