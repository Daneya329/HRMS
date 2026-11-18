"""
REQ-EMP-01  An employee must be at least MIN_AGE (18) years old on the hire date.
REQ-EMP-02  An employee cannot be older than MAX_AGE (60) on the hire date.
Technique: boundary value analysis on the age at the hire date.
"""
from datetime import date

import pytest

from backend import rules
from backend.validators import age_on, validate_employee
from tests.factories import employee_data, years_before

pytestmark = pytest.mark.unit
TODAY = date(2026, 6, 15)
HIRE = date(2026, 1, 15)


def errors_for(**overrides):
    errors, _ = validate_employee(employee_data(TODAY, hire_date=HIRE.isoformat(), **overrides), TODAY)
    return errors


class TestAgeCalculation:
    def test_birthday_today_counts_as_full_year(self):
        assert age_on(date(2000, 3, 10), date(2018, 3, 10)) == 18

    def test_one_day_before_birthday_is_still_younger(self):
        assert age_on(date(2000, 3, 10), date(2018, 3, 9)) == 17

    def test_leap_day_birthday(self):
        assert age_on(date(2004, 2, 29), date(2022, 2, 28)) == 17
        assert age_on(date(2004, 2, 29), date(2022, 3, 1)) == 18


class TestMinimumAge:
    def test_exactly_18_on_hire_date_is_accepted(self):
        assert "date_of_birth" not in errors_for(date_of_birth=years_before(HIRE, 18).isoformat())

    def test_18th_birthday_is_one_day_after_hire_date_is_rejected(self):
        dob = date(HIRE.year - 18, HIRE.month, HIRE.day + 1)
        errors = errors_for(date_of_birth=dob.isoformat())
        assert errors["date_of_birth"] == "Employee must be at least 18 years old on the hire date (would be 17)"

    @pytest.mark.parametrize("age", [0, 10, 16, 17])
    def test_under_18_is_rejected(self, age):
        errors = errors_for(date_of_birth=years_before(HIRE, age).isoformat())
        assert "at least 18" in errors["date_of_birth"]

    def test_age_is_checked_against_hire_date_not_today(self):
        # 17 on the hire date, but already 18 today -> still rejected
        dob = date(HIRE.year - 18, HIRE.month + 1, 1)
        assert age_on(dob, TODAY) == 18
        assert "at least 18" in errors_for(date_of_birth=dob.isoformat())["date_of_birth"]


class TestMaximumAge:
    def test_exactly_60_is_accepted(self):
        assert "date_of_birth" not in errors_for(date_of_birth=years_before(HIRE, 60).isoformat())

    def test_one_day_before_61st_birthday_is_accepted(self):
        dob = date(HIRE.year - 61, HIRE.month, HIRE.day + 1)
        assert age_on(dob, HIRE) == 60
        assert "date_of_birth" not in errors_for(date_of_birth=dob.isoformat())

    @pytest.mark.parametrize("age", [61, 65, 90])
    def test_older_than_60_is_rejected(self, age):
        errors = errors_for(date_of_birth=years_before(HIRE, age).isoformat())
        assert errors["date_of_birth"] == f"Employee cannot be older than 60 on the hire date (would be {age})"

    def test_rules_constants(self):
        assert (rules.MIN_AGE, rules.MAX_AGE) == (18, 60)


class TestDateOfBirthFormat:
    @pytest.mark.parametrize("value", ["", None, "15-01-1990", "1990/01/15", "1990-02-30", "abc", 19900115])
    def test_invalid_dates_are_rejected(self, value):
        assert errors_for(date_of_birth=value)["date_of_birth"] == "Enter a valid date of birth (YYYY-MM-DD)"

    def test_birth_date_today_is_rejected(self):
        assert errors_for(date_of_birth=TODAY.isoformat())["date_of_birth"] == "Date of birth must be in the past"

    def test_birth_date_in_future_is_rejected(self):
        assert errors_for(date_of_birth="2030-01-01")["date_of_birth"] == "Date of birth must be in the past"

    def test_unrealistic_birth_year_is_rejected(self):
        assert errors_for(date_of_birth="1899-12-31")["date_of_birth"] == "Date of birth is not realistic"
