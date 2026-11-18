"""
Business rules of the HRMS - the SINGLE SOURCE OF TRUTH.

The backend validators enforce these values, the frontend downloads them from
GET /api/rules to show hints and validate forms live, and the tests check every
boundary. Change a value here and everything follows.
"""
from datetime import date, time

CURRENCY = "PKR"

# ----------------------------------------------------------------- employees
MIN_AGE = 18                    # minimum legal working age (on the hire date)
MAX_AGE = 60                    # retirement age - cannot be hired at 61 or older
COMPANY_FOUNDED = date(2010, 1, 1)  # nobody can be hired before the company existed
MAX_HIRE_DAYS_AHEAD = 90        # hire date may be at most 90 days in the future

EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract"]

# Minimum monthly basic salary per employment type
MIN_WAGE = {
    "Full-time": 40000,
    "Part-time": 20000,
    "Contract": 40000,
}
MAX_SALARY = 5_000_000          # upper limit catches typing mistakes (extra zeros)

GENDERS = ["Male", "Female", "Other"]
EMPLOYEE_STATUSES = ["Active", "Inactive"]

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 50
NAME_PATTERN = r"^[A-Za-z][A-Za-z '\-]*[A-Za-z]$"      # letters, spaces, ' and -
EMAIL_PATTERN = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
EMAIL_MAX_LENGTH = 100
PHONE_DIGITS_MIN = 10           # after removing spaces, dashes and a leading +
PHONE_DIGITS_MAX = 15
CNIC_PATTERN = r"^\d{5}-\d{7}-\d$"                     # national ID: 12345-1234567-1
DESIGNATION_MIN_LENGTH = 2
DESIGNATION_MAX_LENGTH = 60

# --------------------------------------------------------------- departments
DEPARTMENT_NAME_MIN_LENGTH = 2
DEPARTMENT_NAME_MAX_LENGTH = 50

# ---------------------------------------------------------------- attendance
ATTENDANCE_STATUSES = ["Present", "Late", "Half Day", "Absent"]
LATE_AFTER = time(9, 15)        # a check-in after 09:15 counts as Late
EARLIEST_CHECK_IN = time(6, 0)
MAX_WORK_HOURS = 16             # longer shifts are rejected as data-entry errors
HALF_DAY_MAX_HOURS = 5          # a Half Day may not exceed 5 worked hours

# --------------------------------------------------------------------- leave
LEAVE_ENTITLEMENT = {           # days per calendar year
    "Annual": 20,
    "Sick": 10,
    "Casual": 10,
}
MAX_LEAVE_DAYS_PER_REQUEST = 15
REASON_MIN_LENGTH = 5
REASON_MAX_LENGTH = 200
LEAVE_STATUSES = ["Pending", "Approved", "Rejected"]

# ------------------------------------------------------------------- accounts
PASSWORD_MIN_LENGTH = 8


def as_dict():
    """Rules in a JSON-friendly form for the frontend."""
    return {
        "currency": CURRENCY,
        "minAge": MIN_AGE,
        "maxAge": MAX_AGE,
        "companyFounded": COMPANY_FOUNDED.isoformat(),
        "maxHireDaysAhead": MAX_HIRE_DAYS_AHEAD,
        "employmentTypes": EMPLOYMENT_TYPES,
        "minWage": MIN_WAGE,
        "maxSalary": MAX_SALARY,
        "genders": GENDERS,
        "employeeStatuses": EMPLOYEE_STATUSES,
        "nameMinLength": NAME_MIN_LENGTH,
        "nameMaxLength": NAME_MAX_LENGTH,
        "namePattern": NAME_PATTERN,
        "emailPattern": EMAIL_PATTERN,
        "phoneDigitsMin": PHONE_DIGITS_MIN,
        "phoneDigitsMax": PHONE_DIGITS_MAX,
        "cnicPattern": CNIC_PATTERN,
        "designationMinLength": DESIGNATION_MIN_LENGTH,
        "designationMaxLength": DESIGNATION_MAX_LENGTH,
        "attendanceStatuses": ATTENDANCE_STATUSES,
        "lateAfter": LATE_AFTER.strftime("%H:%M"),
        "earliestCheckIn": EARLIEST_CHECK_IN.strftime("%H:%M"),
        "maxWorkHours": MAX_WORK_HOURS,
        "halfDayMaxHours": HALF_DAY_MAX_HOURS,
        "leaveEntitlement": LEAVE_ENTITLEMENT,
        "maxLeaveDaysPerRequest": MAX_LEAVE_DAYS_PER_REQUEST,
        "reasonMinLength": REASON_MIN_LENGTH,
        "reasonMaxLength": REASON_MAX_LENGTH,
    }
