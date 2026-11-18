"""Builders for valid test data. Tests change ONE field to check ONE rule."""
import random
from datetime import date, timedelta


def years_before(day, years):
    """Same calendar day ``years`` earlier (29 Feb -> 28 Feb)."""
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def random_name(prefix=""):
    """Unique letters-only name so parallel/sequential tests never confuse their records."""
    return prefix + "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(6))


def random_cnic():
    return f"{random.randint(10000, 99999)}-{random.randint(1000000, 9999999)}-{random.randint(0, 9)}"


def employee_data(today=None, **overrides):
    """A fully valid employee payload relative to ``today`` (age 30, hired a year ago)."""
    today = today or date.today()
    hire = today - timedelta(days=365)
    data = {
        "first_name": "Ayesha",
        "last_name": "Malik",
        "email": f"ayesha.{random.randint(100000, 999999)}@company.com",
        "phone": "+92 300 1234567",
        "cnic": random_cnic(),
        "gender": "Female",
        "date_of_birth": years_before(hire, 30).isoformat(),
        "hire_date": hire.isoformat(),
        "department_id": 1,
        "designation": "QA Engineer",
        "employment_type": "Full-time",
        "salary": 85000,
        "status": "Active",
    }
    data.update(overrides)
    return data
