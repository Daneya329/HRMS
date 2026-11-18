"""
Pure validation functions - no database, no Flask.

Every function returns a tuple ``(errors, cleaned)``:
  * ``errors``  - dict {field_name: "human readable message"}; empty when valid
  * ``cleaned`` - normalised values ready to be stored (only meaningful when valid)

"today" is always passed in, so tests are deterministic whatever day they run.
"""
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from . import rules


# --------------------------------------------------------------------- helpers

def parse_date(value):
    """Strict ISO date (YYYY-MM-DD) -> date, or None when missing/invalid."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_time(value):
    """HH:MM (24h) -> time, or None when missing/invalid."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value.strip()):
        return None
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return None


def age_on(birth_date, on_date):
    """Completed years of age on a given date (birthday counts on the day itself)."""
    years = on_date.year - birth_date.year
    if (on_date.month, on_date.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def worked_hours(check_in, check_out):
    """Hours between two times on the same day, rounded to 2 decimals."""
    start = datetime.combine(date.min, check_in)
    end = datetime.combine(date.min, check_out)
    return round((end - start).total_seconds() / 3600, 2)


def _text(data, key):
    value = data.get(key)
    return value.strip() if isinstance(value, str) else ""


def _check_name(errors, field, label, value):
    if not value:
        errors[field] = f"{label} is required"
    elif len(value) < rules.NAME_MIN_LENGTH:
        errors[field] = f"{label} must be at least {rules.NAME_MIN_LENGTH} characters"
    elif len(value) > rules.NAME_MAX_LENGTH:
        errors[field] = f"{label} must be at most {rules.NAME_MAX_LENGTH} characters"
    elif not re.fullmatch(rules.NAME_PATTERN, value):
        errors[field] = f"{label} may only contain letters, spaces, apostrophes and hyphens"


def minimum_wage(employment_type):
    return rules.MIN_WAGE.get(employment_type)


# ------------------------------------------------------------------- employees

def validate_employee(data, today):
    """Validate an employee form. Department existence and uniqueness are checked by the service."""
    errors, cleaned = {}, {}

    first_name = _text(data, "first_name")
    last_name = _text(data, "last_name")
    _check_name(errors, "first_name", "First name", first_name)
    _check_name(errors, "last_name", "Last name", last_name)
    cleaned["first_name"], cleaned["last_name"] = first_name, last_name

    # email
    email = _text(data, "email").lower()
    if not email:
        errors["email"] = "Email is required"
    elif len(email) > rules.EMAIL_MAX_LENGTH:
        errors["email"] = f"Email must be at most {rules.EMAIL_MAX_LENGTH} characters"
    elif not re.fullmatch(rules.EMAIL_PATTERN, email) or ".." in email:
        errors["email"] = "Enter a valid email address, e.g. name@company.com"
    cleaned["email"] = email

    # phone
    phone = _text(data, "phone")
    digits = re.sub(r"[\s\-]", "", phone)
    if not phone:
        errors["phone"] = "Phone number is required"
    elif not re.fullmatch(r"\+?\d+", digits):
        errors["phone"] = "Phone number may only contain digits, spaces, dashes and a leading +"
    elif not rules.PHONE_DIGITS_MIN <= len(digits.lstrip("+")) <= rules.PHONE_DIGITS_MAX:
        errors["phone"] = (f"Phone number must have {rules.PHONE_DIGITS_MIN} to "
                           f"{rules.PHONE_DIGITS_MAX} digits")
    cleaned["phone"] = phone

    # national ID (CNIC)
    cnic = _text(data, "cnic")
    if not cnic:
        errors["cnic"] = "CNIC is required"
    elif not re.fullmatch(rules.CNIC_PATTERN, cnic):
        errors["cnic"] = "CNIC must be in the format 12345-1234567-1"
    cleaned["cnic"] = cnic

    # gender
    gender = _text(data, "gender")
    if gender not in rules.GENDERS:
        errors["gender"] = "Please select a gender"
    cleaned["gender"] = gender

    # dates: date of birth, hire date and the age rule that links them
    dob = parse_date(data.get("date_of_birth"))
    hire = parse_date(data.get("hire_date"))
    if dob is None:
        errors["date_of_birth"] = "Enter a valid date of birth (YYYY-MM-DD)"
    elif dob >= today:
        errors["date_of_birth"] = "Date of birth must be in the past"
    elif dob.year < 1900:
        errors["date_of_birth"] = "Date of birth is not realistic"

    if hire is None:
        errors["hire_date"] = "Enter a valid hire date (YYYY-MM-DD)"
    elif hire < rules.COMPANY_FOUNDED:
        errors["hire_date"] = (f"Hire date cannot be before the company was founded "
                               f"({rules.COMPANY_FOUNDED.isoformat()})")
    elif hire > today + timedelta(days=rules.MAX_HIRE_DAYS_AHEAD):
        errors["hire_date"] = (f"Hire date cannot be more than {rules.MAX_HIRE_DAYS_AHEAD} "
                               f"days in the future")

    if dob and hire and "date_of_birth" not in errors and "hire_date" not in errors:
        age = age_on(dob, hire)
        if age < rules.MIN_AGE:
            errors["date_of_birth"] = (f"Employee must be at least {rules.MIN_AGE} years old on "
                                       f"the hire date (would be {age})")
        elif age > rules.MAX_AGE:
            errors["date_of_birth"] = (f"Employee cannot be older than {rules.MAX_AGE} on the "
                                       f"hire date (would be {age})")
    cleaned["date_of_birth"] = dob.isoformat() if dob else None
    cleaned["hire_date"] = hire.isoformat() if hire else None

    # department (existence checked by the service)
    try:
        department_id = int(data.get("department_id"))
        if department_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        department_id = None
        errors["department_id"] = "Please select a department"
    cleaned["department_id"] = department_id

    designation = _text(data, "designation")
    if not designation:
        errors["designation"] = "Designation is required"
    elif not rules.DESIGNATION_MIN_LENGTH <= len(designation) <= rules.DESIGNATION_MAX_LENGTH:
        errors["designation"] = (f"Designation must be {rules.DESIGNATION_MIN_LENGTH}-"
                                 f"{rules.DESIGNATION_MAX_LENGTH} characters")
    cleaned["designation"] = designation

    employment_type = _text(data, "employment_type")
    if employment_type not in rules.EMPLOYMENT_TYPES:
        errors["employment_type"] = "Please select an employment type"
    cleaned["employment_type"] = employment_type

    # salary and the minimum wage rule
    salary = None
    raw_salary = data.get("salary")
    if isinstance(raw_salary, bool) or raw_salary is None or str(raw_salary).strip() == "":
        errors["salary"] = "Salary is required"
    else:
        try:
            salary = Decimal(str(raw_salary).strip())
            if not salary.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            salary = None
            errors["salary"] = "Salary must be a number"
    if salary is not None:
        if salary.as_tuple().exponent < -2:
            errors["salary"] = "Salary may have at most 2 decimal places"
        elif salary > rules.MAX_SALARY:
            errors["salary"] = f"Salary cannot exceed {rules.CURRENCY} {rules.MAX_SALARY:,}"
        elif employment_type in rules.MIN_WAGE and salary < rules.MIN_WAGE[employment_type]:
            errors["salary"] = (f"Salary is below the minimum wage for {employment_type} "
                                f"employees ({rules.CURRENCY} {rules.MIN_WAGE[employment_type]:,})")
        elif salary <= 0:
            errors["salary"] = "Salary must be greater than zero"
    cleaned["salary"] = float(salary) if salary is not None else None

    status = _text(data, "status") or "Active"
    if status not in rules.EMPLOYEE_STATUSES:
        errors["status"] = "Status must be Active or Inactive"
    cleaned["status"] = status

    return errors, cleaned


# ----------------------------------------------------------------- departments

def validate_department(data):
    errors = {}
    name = _text(data, "name")
    description = _text(data, "description")
    if not name:
        errors["name"] = "Department name is required"
    elif not rules.DEPARTMENT_NAME_MIN_LENGTH <= len(name) <= rules.DEPARTMENT_NAME_MAX_LENGTH:
        errors["name"] = (f"Department name must be {rules.DEPARTMENT_NAME_MIN_LENGTH}-"
                          f"{rules.DEPARTMENT_NAME_MAX_LENGTH} characters")
    if len(description) > 200:
        errors["description"] = "Description must be at most 200 characters"
    return errors, {"name": name, "description": description}


# ------------------------------------------------------------------ attendance

def validate_attendance(data, employee, today):
    """``employee`` is a dict with at least 'hire_date' (ISO) and 'status'."""
    errors, cleaned = {}, {}

    day = parse_date(data.get("date"))
    if day is None:
        errors["date"] = "Enter a valid date (YYYY-MM-DD)"
    elif day > today:
        errors["date"] = "Attendance cannot be marked for a future date"
    elif employee and day < parse_date(employee["hire_date"]):
        errors["date"] = f"Attendance cannot be before the hire date ({employee['hire_date']})"
    cleaned["date"] = day.isoformat() if day else None

    if employee and employee.get("status") != "Active":
        errors["employee_id"] = "Attendance can only be marked for active employees"

    status = _text(data, "status")
    if status not in rules.ATTENDANCE_STATUSES:
        errors["status"] = "Please select a valid status"
    cleaned["status"] = status

    raw_in, raw_out = _text(data, "check_in"), _text(data, "check_out")
    check_in = parse_time(raw_in) if raw_in else None
    check_out = parse_time(raw_out) if raw_out else None
    if raw_in and check_in is None:
        errors["check_in"] = "Check-in must be a valid time (HH:MM)"
    if raw_out and check_out is None:
        errors["check_out"] = "Check-out must be a valid time (HH:MM)"

    if status == "Absent":
        if raw_in or raw_out:
            errors["check_in"] = "An absent employee cannot have check-in or check-out times"
    elif status in rules.ATTENDANCE_STATUSES and "check_in" not in errors:
        if check_in is None:
            errors["check_in"] = f"Check-in time is required for status '{status}'"
        elif check_in < rules.EARLIEST_CHECK_IN:
            errors["check_in"] = f"Check-in cannot be earlier than {rules.EARLIEST_CHECK_IN:%H:%M}"
        elif status == "Present" and check_in > rules.LATE_AFTER:
            errors["status"] = f"Check-in after {rules.LATE_AFTER:%H:%M} must be marked as Late"
        elif status == "Late" and check_in <= rules.LATE_AFTER:
            errors["status"] = f"'Late' requires a check-in after {rules.LATE_AFTER:%H:%M}"

    if check_in and check_out and "check_out" not in errors:
        if check_out <= check_in:
            errors["check_out"] = "Check-out must be later than check-in"
        else:
            hours = worked_hours(check_in, check_out)
            if hours > rules.MAX_WORK_HOURS:
                errors["check_out"] = f"A shift cannot be longer than {rules.MAX_WORK_HOURS} hours"
            elif status == "Half Day" and hours > rules.HALF_DAY_MAX_HOURS:
                errors["status"] = (f"A Half Day cannot exceed {rules.HALF_DAY_MAX_HOURS} worked "
                                    f"hours ({hours} h recorded)")
    if status == "Half Day" and check_in and not check_out and "status" not in errors:
        errors["check_out"] = "Check-out time is required for a Half Day"

    cleaned["check_in"] = check_in.strftime("%H:%M") if check_in and status != "Absent" else None
    cleaned["check_out"] = check_out.strftime("%H:%M") if check_out and status != "Absent" else None
    return errors, cleaned


# ----------------------------------------------------------------------- leave

def leave_days(start, end):
    """Calendar days covered by a leave request, both ends inclusive."""
    return (end - start).days + 1


def validate_leave(data, employee, today, days_already_used=0):
    """
    ``days_already_used`` = days of the same leave type already approved or pending in
    the same calendar year (computed by the service). Overlaps are checked by the service.
    """
    errors, cleaned = {}, {}

    leave_type = _text(data, "leave_type")
    if leave_type not in rules.LEAVE_ENTITLEMENT:
        errors["leave_type"] = "Please select a leave type"
    cleaned["leave_type"] = leave_type

    start = parse_date(data.get("start_date"))
    end = parse_date(data.get("end_date"))
    if start is None:
        errors["start_date"] = "Enter a valid start date"
    elif start < today:
        errors["start_date"] = "Leave cannot start in the past"
    elif employee and start < parse_date(employee["hire_date"]):
        errors["start_date"] = "Leave cannot start before the hire date"
    if end is None:
        errors["end_date"] = "Enter a valid end date"
    elif start and end < start:
        errors["end_date"] = "End date cannot be before the start date"

    if start and end and not errors.get("start_date") and not errors.get("end_date"):
        days = leave_days(start, end)
        cleaned["days"] = days
        if days > rules.MAX_LEAVE_DAYS_PER_REQUEST:
            errors["end_date"] = (f"A single request cannot exceed "
                                  f"{rules.MAX_LEAVE_DAYS_PER_REQUEST} days")
        elif leave_type in rules.LEAVE_ENTITLEMENT:
            remaining = rules.LEAVE_ENTITLEMENT[leave_type] - days_already_used
            if days > remaining:
                errors["leave_type"] = (f"Not enough {leave_type} leave: {remaining} day(s) left "
                                        f"this year, {days} requested")
    cleaned["start_date"] = start.isoformat() if start else None
    cleaned["end_date"] = end.isoformat() if end else None

    if employee and employee.get("status") != "Active":
        errors["employee_id"] = "Only active employees can apply for leave"

    reason = _text(data, "reason")
    if not rules.REASON_MIN_LENGTH <= len(reason) <= rules.REASON_MAX_LENGTH:
        errors["reason"] = (f"Reason must be {rules.REASON_MIN_LENGTH}-{rules.REASON_MAX_LENGTH} "
                            f"characters")
    cleaned["reason"] = reason
    return errors, cleaned


def validate_rejection(remarks):
    remarks = remarks.strip() if isinstance(remarks, str) else ""
    if len(remarks) < rules.REASON_MIN_LENGTH:
        return {"remarks": f"Please give a rejection reason (at least {rules.REASON_MIN_LENGTH} "
                           f"characters)"}, remarks
    return {}, remarks


# -------------------------------------------------------------------- accounts

def validate_password_change(current, new, confirm):
    errors = {}
    if not current:
        errors["current_password"] = "Current password is required"
    if not new or len(new) < rules.PASSWORD_MIN_LENGTH:
        errors["new_password"] = f"New password must be at least {rules.PASSWORD_MIN_LENGTH} characters"
    elif not (re.search(r"[A-Za-z]", new) and re.search(r"\d", new)):
        errors["new_password"] = "New password must contain a letter and a digit"
    if new != confirm:
        errors["confirm_password"] = "Passwords do not match"
    return errors
