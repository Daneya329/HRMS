"""
Business operations. Combine the pure validators with checks that need the database
(uniqueness, overlaps, leave balances, "department in use" ...).

Errors are raised as exceptions and turned into JSON responses by the API layer.
"""
import sqlite3
from datetime import date, datetime, timedelta

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from . import rules, validators
from .database import get_db

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 5


class ValidationError(Exception):
    """Invalid input. ``errors`` maps field names to messages (HTTP 400)."""

    def __init__(self, errors, message="Please correct the highlighted fields"):
        super().__init__(message)
        self.errors = errors
        self.message = message


class ConflictError(ValidationError):
    """Input clashes with existing data, e.g. a duplicate (HTTP 409)."""


class NotFoundError(Exception):
    """Record does not exist (HTTP 404)."""


def today():
    """Current date. Tests may freeze it with app.config['TODAY']."""
    fixed = current_app.config.get("TODAY")
    return fixed if fixed else date.today()


def _row(row):
    return dict(row) if row is not None else None


# ===================================================================== accounts

def authenticate(email, password):
    """Returns the user dict, or raises ValidationError. Locks the account after repeated failures."""
    if not email or not password:
        raise ValidationError({"login": "Email and password are required"}, "Email and password are required")
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email.strip(),)).fetchone()
    generic = ValidationError({"login": "Invalid email or password"}, "Invalid email or password")
    if user is None:
        raise generic
    now = datetime.now()
    if user["locked_until"] and datetime.fromisoformat(user["locked_until"]) > now:
        raise ValidationError({"login": "Account locked after too many failed attempts. Try again later."},
                              "Account locked after too many failed attempts. Try again later.")
    if not check_password_hash(user["password_hash"], password):
        attempts = user["failed_attempts"] + 1
        locked = (now + timedelta(minutes=LOCK_MINUTES)).isoformat() if attempts >= MAX_FAILED_LOGINS else None
        db.execute("UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                   (0 if locked else attempts, locked, user["id"]))
        db.commit()
        raise generic
    db.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (user["id"],))
    db.commit()
    return {"id": user["id"], "name": user["name"], "email": user["email"]}


def get_user(user_id):
    row = get_db().execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row(row)


def change_password(user_id, current, new, confirm):
    errors = validators.validate_password_change(current, new, confirm)
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise NotFoundError("User not found")
    if current and not check_password_hash(user["password_hash"], current):
        errors["current_password"] = "Current password is incorrect"
    if errors:
        raise ValidationError(errors)
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new), user_id))
    db.commit()


# ================================================================== departments

def list_departments():
    rows = get_db().execute(
        "SELECT d.*, COUNT(e.id) AS employee_count FROM departments d "
        "LEFT JOIN employees e ON e.department_id = d.id GROUP BY d.id ORDER BY d.name").fetchall()
    return [_row(r) for r in rows]


def get_department(department_id):
    row = get_db().execute("SELECT * FROM departments WHERE id = ?", (department_id,)).fetchone()
    if row is None:
        raise NotFoundError("Department not found")
    return _row(row)


def save_department(data, department_id=None):
    errors, clean = validators.validate_department(data)
    if errors:
        raise ValidationError(errors)
    db = get_db()
    if department_id is not None:
        get_department(department_id)
    duplicate = db.execute("SELECT id FROM departments WHERE name = ? COLLATE NOCASE AND id IS NOT ?",
                           (clean["name"], department_id)).fetchone()
    if duplicate:
        raise ConflictError({"name": f"A department named '{clean['name']}' already exists"})
    if department_id is None:
        cur = db.execute("INSERT INTO departments (name, description) VALUES (?, ?)",
                         (clean["name"], clean["description"]))
        department_id = cur.lastrowid
    else:
        db.execute("UPDATE departments SET name = ?, description = ? WHERE id = ?",
                   (clean["name"], clean["description"], department_id))
    db.commit()
    return get_department(department_id)


def delete_department(department_id):
    department = get_department(department_id)
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM employees WHERE department_id = ?", (department_id,)).fetchone()[0]
    if count:
        raise ConflictError({"department": f"'{department['name']}' still has {count} employee(s). "
                                           f"Move them to another department first."},
                            f"'{department['name']}' still has {count} employee(s)")
    db.execute("DELETE FROM departments WHERE id = ?", (department_id,))
    db.commit()


# ==================================================================== employees

EMPLOYEE_SELECT = ("SELECT e.*, d.name AS department_name, e.first_name || ' ' || e.last_name AS full_name "
                   "FROM employees e JOIN departments d ON d.id = e.department_id")


def list_employees(query="", department_id=None, status=None):
    sql, params = EMPLOYEE_SELECT + " WHERE 1 = 1", []
    if query:
        like = f"%{query.strip().lower()}%"
        sql += (" AND (lower(e.first_name || ' ' || e.last_name) LIKE ? OR lower(e.employee_code) LIKE ?"
                " OR lower(e.email) LIKE ? OR e.cnic LIKE ?)")
        params += [like, like, like, like]
    if department_id:
        sql += " AND e.department_id = ?"
        params.append(department_id)
    if status:
        sql += " AND e.status = ?"
        params.append(status)
    sql += " ORDER BY e.employee_code"
    return [_row(r) for r in get_db().execute(sql, params).fetchall()]


def get_employee(employee_id):
    row = get_db().execute(EMPLOYEE_SELECT + " WHERE e.id = ?", (employee_id,)).fetchone()
    if row is None:
        raise NotFoundError("Employee not found")
    return _row(row)


def _next_employee_code(db):
    last = db.execute("SELECT MAX(CAST(substr(employee_code, 5) AS INTEGER)) FROM employees").fetchone()[0]
    return f"EMP-{(last or 0) + 1:04d}"


def save_employee(data, employee_id=None):
    errors, clean = validators.validate_employee(data, today())
    db = get_db()
    if employee_id is not None:
        get_employee(employee_id)
    if clean.get("department_id") and "department_id" not in errors:
        if db.execute("SELECT 1 FROM departments WHERE id = ?", (clean["department_id"],)).fetchone() is None:
            errors["department_id"] = "Selected department does not exist"
    if errors:
        raise ValidationError(errors)

    conflicts = {}
    if db.execute("SELECT 1 FROM employees WHERE email = ? COLLATE NOCASE AND id IS NOT ?",
                  (clean["email"], employee_id)).fetchone():
        conflicts["email"] = "Another employee already uses this email"
    if db.execute("SELECT 1 FROM employees WHERE cnic = ? AND id IS NOT ?",
                  (clean["cnic"], employee_id)).fetchone():
        conflicts["cnic"] = "Another employee already has this CNIC"
    if conflicts:
        raise ConflictError(conflicts)

    fields = ["first_name", "last_name", "email", "phone", "cnic", "gender", "date_of_birth", "hire_date",
              "department_id", "designation", "employment_type", "salary", "status"]
    values = [clean[f] for f in fields]
    try:
        if employee_id is None:
            code = _next_employee_code(db)
            cur = db.execute(f"INSERT INTO employees (employee_code, {', '.join(fields)}) "
                             f"VALUES (?, {', '.join('?' * len(fields))})", [code] + values)
            employee_id = cur.lastrowid
        else:
            db.execute(f"UPDATE employees SET {', '.join(f + ' = ?' for f in fields)} WHERE id = ?",
                       values + [employee_id])
        db.commit()
    except sqlite3.IntegrityError as exc:   # last line of defence (e.g. a concurrent duplicate)
        db.rollback()
        raise ConflictError({"form": f"The record violates a database rule: {exc}"}) from exc
    return get_employee(employee_id)


def delete_employee(employee_id):
    get_employee(employee_id)
    db = get_db()
    db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    db.commit()


# =================================================================== attendance

def attendance_sheet(day):
    """Every active employee hired on/before ``day`` with their record for that day (or None)."""
    db = get_db()
    employees = db.execute(EMPLOYEE_SELECT + " WHERE e.status = 'Active' AND e.hire_date <= ? "
                                             "ORDER BY e.employee_code", (day,)).fetchall()
    records = {r["employee_id"]: _row(r) for r in
               db.execute("SELECT * FROM attendance WHERE date = ?", (day,)).fetchall()}
    return [{"employee": _row(e), "attendance": records.get(e["id"])} for e in employees]


def attendance_history(employee_id=None, date_from=None, date_to=None):
    sql = ("SELECT a.*, e.employee_code, e.first_name || ' ' || e.last_name AS full_name "
           "FROM attendance a JOIN employees e ON e.id = a.employee_id WHERE 1 = 1")
    params = []
    if employee_id:
        sql += " AND a.employee_id = ?"
        params.append(employee_id)
    if date_from:
        sql += " AND a.date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND a.date <= ?"
        params.append(date_to)
    sql += " ORDER BY a.date DESC, e.employee_code"
    return [_row(r) for r in get_db().execute(sql, params).fetchall()]


def _get_attendance(attendance_id):
    row = get_db().execute("SELECT * FROM attendance WHERE id = ?", (attendance_id,)).fetchone()
    if row is None:
        raise NotFoundError("Attendance record not found")
    return _row(row)


def _employee_or_error(employee_id):
    try:
        return get_employee(int(employee_id))
    except (TypeError, ValueError, NotFoundError):
        raise ValidationError({"employee_id": "Please select an existing employee"})


def mark_attendance(data):
    employee = _employee_or_error(data.get("employee_id"))
    errors, clean = validators.validate_attendance(data, employee, today())
    if errors:
        raise ValidationError(errors)
    db = get_db()
    if db.execute("SELECT 1 FROM attendance WHERE employee_id = ? AND date = ?",
                  (employee["id"], clean["date"])).fetchone():
        raise ConflictError({"date": f"Attendance for {employee['full_name']} on {clean['date']} is already "
                                     f"marked. Edit the existing record instead."},
                            "Attendance already marked for this day")
    if db.execute("SELECT 1 FROM leave_requests WHERE employee_id = ? AND status = 'Approved' "
                  "AND ? BETWEEN start_date AND end_date", (employee["id"], clean["date"])).fetchone():
        raise ConflictError({"date": f"{employee['full_name']} is on approved leave on {clean['date']}"},
                            "Employee is on approved leave")
    cur = db.execute("INSERT INTO attendance (employee_id, date, status, check_in, check_out) VALUES (?, ?, ?, ?, ?)",
                     (employee["id"], clean["date"], clean["status"], clean["check_in"], clean["check_out"]))
    db.commit()
    return _get_attendance(cur.lastrowid)


def update_attendance(attendance_id, data):
    record = _get_attendance(attendance_id)
    employee = get_employee(record["employee_id"])
    payload = dict(data, date=record["date"])           # employee and date cannot be changed
    errors, clean = validators.validate_attendance(payload, employee, today())
    if errors:
        raise ValidationError(errors)
    db = get_db()
    db.execute("UPDATE attendance SET status = ?, check_in = ?, check_out = ? WHERE id = ?",
               (clean["status"], clean["check_in"], clean["check_out"], attendance_id))
    db.commit()
    return _get_attendance(attendance_id)


def delete_attendance(attendance_id):
    _get_attendance(attendance_id)
    db = get_db()
    db.execute("DELETE FROM attendance WHERE id = ?", (attendance_id,))
    db.commit()


# ======================================================================== leave

def leave_used(employee_id, leave_type, year, exclude_id=None):
    """Days of a leave type that are approved or pending in a calendar year."""
    row = get_db().execute(
        "SELECT COALESCE(SUM(days), 0) FROM leave_requests WHERE employee_id = ? AND leave_type = ? "
        "AND status IN ('Approved', 'Pending') AND substr(start_date, 1, 4) = ? AND id IS NOT ?",
        (employee_id, leave_type, str(year), exclude_id)).fetchone()
    return row[0]


def leave_balance(employee_id, year=None):
    get_employee(employee_id)
    year = year or today().year
    return {t: {"entitlement": n, "used": leave_used(employee_id, t, year),
                "remaining": n - leave_used(employee_id, t, year)}
            for t, n in rules.LEAVE_ENTITLEMENT.items()}


def apply_leave(data):
    employee = _employee_or_error(data.get("employee_id"))
    start = validators.parse_date(data.get("start_date"))
    used = leave_used(employee["id"], (data.get("leave_type") or "").strip(),
                      start.year if start else today().year)
    errors, clean = validators.validate_leave(data, employee, today(), days_already_used=used)
    if errors:
        raise ValidationError(errors)
    db = get_db()
    overlap = db.execute(
        "SELECT start_date, end_date FROM leave_requests WHERE employee_id = ? AND status IN ('Pending', 'Approved') "
        "AND start_date <= ? AND end_date >= ?", (employee["id"], clean["end_date"], clean["start_date"])).fetchone()
    if overlap:
        raise ConflictError({"start_date": f"Overlaps an existing request ({overlap['start_date']} to "
                                           f"{overlap['end_date']})"}, "Overlaps an existing leave request")
    cur = db.execute(
        "INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, days, reason) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (employee["id"], clean["leave_type"], clean["start_date"], clean["end_date"], clean["days"], clean["reason"]))
    db.commit()
    return get_leave(cur.lastrowid)


def list_leaves(status=None, employee_id=None):
    sql = ("SELECT l.*, e.employee_code, e.first_name || ' ' || e.last_name AS full_name "
           "FROM leave_requests l JOIN employees e ON e.id = l.employee_id WHERE 1 = 1")
    params = []
    if status:
        sql += " AND l.status = ?"
        params.append(status)
    if employee_id:
        sql += " AND l.employee_id = ?"
        params.append(employee_id)
    sql += " ORDER BY CASE l.status WHEN 'Pending' THEN 0 ELSE 1 END, l.start_date DESC"
    return [_row(r) for r in get_db().execute(sql, params).fetchall()]


def get_leave(leave_id):
    row = get_db().execute(
        "SELECT l.*, e.employee_code, e.first_name || ' ' || e.last_name AS full_name "
        "FROM leave_requests l JOIN employees e ON e.id = l.employee_id WHERE l.id = ?", (leave_id,)).fetchone()
    if row is None:
        raise NotFoundError("Leave request not found")
    return _row(row)


def decide_leave(leave_id, approve, remarks=""):
    leave = get_leave(leave_id)
    if leave["status"] != "Pending":
        raise ConflictError({"status": f"Only pending requests can be decided (this one is {leave['status']})"},
                            f"This request is already {leave['status']}")
    if approve:
        remarks = remarks.strip() if isinstance(remarks, str) else ""
    else:
        errors, remarks = validators.validate_rejection(remarks)
        if errors:
            raise ValidationError(errors)
    db = get_db()
    db.execute("UPDATE leave_requests SET status = ?, remarks = ? WHERE id = ?",
               ("Approved" if approve else "Rejected", remarks, leave_id))
    db.commit()
    return get_leave(leave_id)


# ==================================================================== dashboard

def dashboard():
    db = get_db()
    day = today().isoformat()
    one = lambda sql, *p: db.execute(sql, p).fetchone()[0]  # noqa: E731
    active = one("SELECT COUNT(*) FROM employees WHERE status = 'Active'")
    present = one("SELECT COUNT(*) FROM attendance a JOIN employees e ON e.id = a.employee_id "
                  "WHERE a.date = ? AND a.status != 'Absent' AND e.status = 'Active'", day)
    absent = one("SELECT COUNT(*) FROM attendance a JOIN employees e ON e.id = a.employee_id "
                 "WHERE a.date = ? AND a.status = 'Absent' AND e.status = 'Active'", day)
    on_leave = one("SELECT COUNT(DISTINCT l.employee_id) FROM leave_requests l JOIN employees e "
                   "ON e.id = l.employee_id WHERE l.status = 'Approved' AND ? BETWEEN l.start_date AND l.end_date "
                   "AND e.status = 'Active'", day)
    return {
        "today": day,
        "total_employees": one("SELECT COUNT(*) FROM employees"),
        "active_employees": active,
        "present_today": present,
        "absent_today": absent,
        "on_leave_today": on_leave,
        "not_marked_today": max(active - present - absent - on_leave, 0),
        "pending_leaves": one("SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'"),
        "departments": [{"name": d["name"], "count": d["employee_count"]} for d in list_departments()],
        "recent_employees": [_row(r) for r in db.execute(
            EMPLOYEE_SELECT + " ORDER BY e.id DESC LIMIT 5").fetchall()],
    }
