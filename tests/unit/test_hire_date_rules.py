"""
REQ-EMP-05  Nobody can be hired before the company was founded (COMPANY_FOUNDED = 2010-01-01).
REQ-EMP-06  The hire date may be at most MAX_HIRE_DAYS_AHEAD (90) days in the future.
Technique: boundary value analysis.
"""
from datetime import date, timedelta

import pytest

from backend import rules
from backend.validators import validate_employee
from tests.factories import employee_data, years_before

pytestmark = pytest.mark.unit
TODAY = date(2026, 6, 15)


def hire_errors(hire):
    hire_iso = hire.isoformat() if isinstance(hire, date) else hire
    dob = years_before(hire, 30).isoformat() if isinstance(hire, date) else "1990-01-01"
    errors, _ = validate_employee(employee_data(TODAY, hire_date=hire_iso, date_of_birth=dob), TODAY)
    return errors


def test_company_founded_date():
    assert rules.COMPANY_FOUNDED == date(2010, 1, 1)


def test_hire_on_founding_day_is_accepted():
    assert "hire_date" not in hire_errors(rules.COMPANY_FOUNDED)


def test_hire_one_day_before_founding_is_rejected():
    errors = hire_errors(rules.COMPANY_FOUNDED - timedelta(days=1))
    assert errors["hire_date"] == "Hire date cannot be before the company was founded (2010-01-01)"


@pytest.mark.parametrize("hire", [date(2000, 6, 1), date(1990, 1, 1)])
def test_hire_long_before_founding_is_rejected(hire):
    assert "before the company was founded" in hire_errors(hire)["hire_date"]


def test_hire_today_is_accepted():
    assert "hire_date" not in hire_errors(TODAY)


def test_hire_exactly_90_days_ahead_is_accepted():
    assert "hire_date" not in hire_errors(TODAY + timedelta(days=90))


def test_hire_91_days_ahead_is_rejected():
    errors = hire_errors(TODAY + timedelta(days=91))
    assert errors["hire_date"] == "Hire date cannot be more than 90 days in the future"


@pytest.mark.parametrize("value", ["", None, "2026-13-01", "01/02/2020", "yesterday"])
def test_invalid_hire_date_format_is_rejected(value):
    assert hire_errors(value)["hire_date"] == "Enter a valid hire date (YYYY-MM-DD)"


def test_age_is_not_checked_when_hire_date_is_invalid():
    errors = hire_errors("not-a-date")
    assert "date_of_birth" not in errors
