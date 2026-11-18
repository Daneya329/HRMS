"""
SQLite database: connection handling, schema and initial data.

The database is a single file (default: ``hrms.db`` in the project folder) that is
created automatically on first start - nothing to install.
The schema repeats the most important business rules as constraints
(UNIQUE, CHECK, FOREIGN KEY), so invalid data is rejected even if application code
had a bug ("defence in depth").
"""
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

from . import rules

DEFAULT_ADMIN_EMAIL = "admin@hrms.local"
DEFAULT_ADMIN_PASSWORD = "Admin@123"
DEFAULT_DEPARTMENTS = ["Human Resources", "Engineering", "Finance", "Sales", "Marketing", "Operations"]

SCHEMA_TEMPLATE = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT    NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT
);

CREATE TABLE IF NOT EXISTS departments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(name) BETWEEN 2 AND 50),
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS employees (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code   TEXT    NOT NULL UNIQUE,
    first_name      TEXT    NOT NULL,
    last_name       TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    phone           TEXT    NOT NULL,
    cnic            TEXT    NOT NULL UNIQUE,
    gender          TEXT    NOT NULL CHECK (gender IN ('Male', 'Female', 'Other')),
    date_of_birth   TEXT    NOT NULL,
    hire_date       TEXT    NOT NULL CHECK (hire_date >= '{founded}'),
    department_id   INTEGER NOT NULL REFERENCES departments(id),
    designation     TEXT    NOT NULL,
    employment_type TEXT    NOT NULL CHECK (employment_type IN ('Full-time', 'Part-time', 'Contract')),
    salary          REAL    NOT NULL CHECK (salary > 0),
    status          TEXT    NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Inactive')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees(department_id);

CREATE TABLE IF NOT EXISTS attendance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    date        TEXT    NOT NULL,
    status      TEXT    NOT NULL CHECK (status IN ('Present', 'Late', 'Half Day', 'Absent')),
    check_in    TEXT,
    check_out   TEXT,
    CHECK (check_out IS NULL OR check_in IS NULL OR check_out > check_in),
    UNIQUE (employee_id, date)
);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);

CREATE TABLE IF NOT EXISTS leave_requests (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id  INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type   TEXT    NOT NULL CHECK (leave_type IN ('Annual', 'Sick', 'Casual')),
    start_date   TEXT    NOT NULL,
    end_date     TEXT    NOT NULL,
    days         INTEGER NOT NULL CHECK (days > 0),
    reason       TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    remarks      TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS idx_leave_employee ON leave_requests(employee_id);
"""
SCHEMA = SCHEMA_TEMPLATE.replace("{founded}", rules.COMPANY_FOUNDED.isoformat())


def connect(path):
    conn = sqlite3.connect(path, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """One connection per request, closed automatically at the end of the request."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path):
    """Create tables (if missing), the default administrator and default departments."""
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("HR Administrator", DEFAULT_ADMIN_EMAIL, generate_password_hash(DEFAULT_ADMIN_PASSWORD)),
            )
        if conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0] == 0:
            conn.executemany("INSERT INTO departments (name) VALUES (?)", [(d,) for d in DEFAULT_DEPARTMENTS])
        conn.commit()
    finally:
        conn.close()
