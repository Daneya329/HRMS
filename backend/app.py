"""
Flask application: JSON REST API under /api and the static HTML/CSS/JS frontend.
"""
import os
import secrets
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, request, send_from_directory, session

from . import rules, services
from .database import close_db, init_db
from .services import ConflictError, NotFoundError, ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = PROJECT_ROOT / "frontend"

PAGES = {
    "/": "login.html",
    "/login": "login.html",
    "/dashboard": "dashboard.html",
    "/employees": "employees.html",
    "/employee-form": "employee-form.html",
    "/departments": "departments.html",
    "/attendance": "attendance.html",
    "/leaves": "leaves.html",
    "/settings": "settings.html",
}


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        DATABASE=os.environ.get("HRMS_DATABASE", str(PROJECT_ROOT / "hrms.db")),
        SECRET_KEY=os.environ.get("HRMS_SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)
    app.json.sort_keys = False      # keep rule order as defined in rules.py

    init_db(app.config["DATABASE"])
    app.teardown_appcontext(close_db)
    _register_error_handlers(app)
    _register_pages(app)
    _register_api(app)
    return app


# ---------------------------------------------------------------- helpers

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(message="Please sign in first"), 401
        return view(*args, **kwargs)
    return wrapper


def payload():
    """JSON body as a dict (an empty dict if the body is missing or not an object)."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def validation_error(exc):
        status = 409 if isinstance(exc, ConflictError) else 400
        return jsonify(message=exc.message, errors=exc.errors), status

    @app.errorhandler(NotFoundError)
    def not_found(exc):
        return jsonify(message=str(exc)), 404

    @app.errorhandler(404)
    def page_not_found(_exc):
        if request.path.startswith("/api/"):
            return jsonify(message="Not found"), 404
        return send_from_directory(FRONTEND, "404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(_exc):
        return jsonify(message="Method not allowed"), 405


def _register_pages(app):
    def make_view(filename):
        def view():
            return send_from_directory(FRONTEND, filename)
        return view

    for path, filename in PAGES.items():
        app.add_url_rule(path, endpoint=f"page_{filename}_{path}", view_func=make_view(filename))

    @app.route("/<path:filename>.html")
    def html_alias(filename):
        return redirect("/" + filename)

    @app.route("/css/<path:filename>")
    def css(filename):
        return send_from_directory(FRONTEND / "css", filename)

    @app.route("/js/<path:filename>")
    def js(filename):
        return send_from_directory(FRONTEND / "js", filename)

    @app.route("/favicon.svg")
    def favicon():
        return send_from_directory(FRONTEND, "favicon.svg")


def _register_api(app):
    # ------------------------------------------------------------ public
    @app.get("/api/rules")
    def get_rules():
        return jsonify(rules.as_dict())

    @app.post("/api/login")
    def login():
        data = payload()
        user = services.authenticate(data.get("email"), data.get("password"))
        session.clear()
        session["user_id"] = user["id"]
        return jsonify(user=user)

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(message="Signed out")

    @app.get("/api/me")
    @login_required
    def me():
        user = services.get_user(session["user_id"])
        if user is None:
            session.clear()
            return jsonify(message="Please sign in first"), 401
        return jsonify(user=user)

    @app.post("/api/account/password")
    @login_required
    def change_password():
        data = payload()
        services.change_password(session["user_id"], data.get("current_password"),
                                 data.get("new_password"), data.get("confirm_password"))
        return jsonify(message="Password changed")

    # ------------------------------------------------------------ dashboard
    @app.get("/api/dashboard")
    @login_required
    def dashboard():
        return jsonify(services.dashboard())

    # ------------------------------------------------------------ departments
    @app.get("/api/departments")
    @login_required
    def departments():
        return jsonify(services.list_departments())

    @app.post("/api/departments")
    @login_required
    def create_department():
        return jsonify(services.save_department(payload())), 201

    @app.put("/api/departments/<int:department_id>")
    @login_required
    def update_department(department_id):
        return jsonify(services.save_department(payload(), department_id))

    @app.delete("/api/departments/<int:department_id>")
    @login_required
    def delete_department(department_id):
        services.delete_department(department_id)
        return jsonify(message="Department deleted")

    # ------------------------------------------------------------ employees
    @app.get("/api/employees")
    @login_required
    def employees():
        return jsonify(services.list_employees(request.args.get("q", ""),
                                               request.args.get("department_id", type=int),
                                               request.args.get("status") or None))

    @app.post("/api/employees")
    @login_required
    def create_employee():
        return jsonify(services.save_employee(payload())), 201

    @app.get("/api/employees/<int:employee_id>")
    @login_required
    def employee(employee_id):
        return jsonify(services.get_employee(employee_id))

    @app.put("/api/employees/<int:employee_id>")
    @login_required
    def update_employee(employee_id):
        return jsonify(services.save_employee(payload(), employee_id))

    @app.delete("/api/employees/<int:employee_id>")
    @login_required
    def delete_employee(employee_id):
        services.delete_employee(employee_id)
        return jsonify(message="Employee deleted")

    @app.get("/api/employees/<int:employee_id>/leave-balance")
    @login_required
    def leave_balance(employee_id):
        return jsonify(services.leave_balance(employee_id))

    # ------------------------------------------------------------ attendance
    @app.get("/api/attendance")
    @login_required
    def attendance_sheet():
        day = request.args.get("date") or services.today().isoformat()
        if services.validators.parse_date(day) is None:
            raise ValidationError({"date": "Enter a valid date (YYYY-MM-DD)"})
        return jsonify(date=day, rows=services.attendance_sheet(day))

    @app.get("/api/attendance/history")
    @login_required
    def attendance_history():
        return jsonify(services.attendance_history(request.args.get("employee_id", type=int),
                                                   request.args.get("from") or None,
                                                   request.args.get("to") or None))

    @app.post("/api/attendance")
    @login_required
    def mark_attendance():
        return jsonify(services.mark_attendance(payload())), 201

    @app.put("/api/attendance/<int:attendance_id>")
    @login_required
    def update_attendance(attendance_id):
        return jsonify(services.update_attendance(attendance_id, payload()))

    @app.delete("/api/attendance/<int:attendance_id>")
    @login_required
    def delete_attendance(attendance_id):
        services.delete_attendance(attendance_id)
        return jsonify(message="Attendance record deleted")

    # ------------------------------------------------------------ leave
    @app.get("/api/leaves")
    @login_required
    def leaves():
        return jsonify(services.list_leaves(request.args.get("status") or None,
                                            request.args.get("employee_id", type=int)))

    @app.post("/api/leaves")
    @login_required
    def apply_leave():
        return jsonify(services.apply_leave(payload())), 201

    @app.post("/api/leaves/<int:leave_id>/approve")
    @login_required
    def approve_leave(leave_id):
        return jsonify(services.decide_leave(leave_id, True, payload().get("remarks", "")))

    @app.post("/api/leaves/<int:leave_id>/reject")
    @login_required
    def reject_leave(leave_id):
        return jsonify(services.decide_leave(leave_id, False, payload().get("remarks", "")))
