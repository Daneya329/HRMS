"""
REQ-EMP-03  Salary must be at least the minimum wage of the employment type
            (Full-time 40,000 / Part-time 20,000 / Contract 40,000 PKR per month).
REQ-EMP-04  Salary cannot exceed MAX_SALARY and may have at most 2 decimals.
Technique: boundary value analysis + equivalence partitioning.
"""
from datetime import date

import pytest

from backend import rules
from backend.validators import validate_employee
from tests.factories import employee_data

pytestmark = pytest.mark.unit
TODAY = date(2026, 6, 15)


def salary_error(salary, employment_type="Full-time"):
    errors, cleaned = validate_employee(employee_data(TODAY, salary=salary, employment_type=employment_type), TODAY)
    return errors.get("salary"), cleaned


@pytest.mark.parametrize("employment_type, minimum", list(rules.MIN_WAGE.items()))
class TestMinimumWage:
    def test_exactly_minimum_wage_is_accepted(self, employment_type, minimum):
        assert salary_error(minimum, employment_type)[0] is None

    def test_one_rupee_above_minimum_is_accepted(self, employment_type, minimum):
        assert salary_error(minimum + 1, employment_type)[0] is None

    def test_one_paisa_below_minimum_is_rejected(self, employment_type, minimum):
        error, _ = salary_error(minimum - 0.01, employment_type)
        assert error == (f"Salary is below the minimum wage for {employment_type} employees "
                         f"(PKR {minimum:,})")

    def test_one_rupee_below_minimum_is_rejected(self, employment_type, minimum):
        assert "below the minimum wage" in salary_error(minimum - 1, employment_type)[0]


def test_minimum_wage_values():
    assert rules.MIN_WAGE == {"Full-time": 40000, "Part-time": 20000, "Contract": 40000}


def test_part_time_salary_that_is_too_low_for_full_time_is_accepted():
    assert salary_error(25000, "Part-time")[0] is None
    assert "below the minimum wage" in salary_error(25000, "Full-time")[0]


class TestSalaryLimitsAndFormat:
    def test_maximum_salary_is_accepted(self):
        assert salary_error(rules.MAX_SALARY)[0] is None

    def test_above_maximum_salary_is_rejected(self):
        assert salary_error(rules.MAX_SALARY + 1)[0] == "Salary cannot exceed PKR 5,000,000"

    @pytest.mark.parametrize("value", [0, -1, -50000])
    def test_zero_and_negative_salary_are_rejected(self, value):
        assert "below the minimum wage" in salary_error(value)[0]

    @pytest.mark.parametrize("value", [None, "", "   ", True])
    def test_missing_salary_is_rejected(self, value):
        assert salary_error(value)[0] == "Salary is required"

    @pytest.mark.parametrize("value", ["abc", "40,000", "NaN", "Infinity"])
    def test_non_numeric_salary_is_rejected(self, value):
        assert salary_error(value)[0] == "Salary must be a number"

    def test_three_decimals_are_rejected(self):
        assert salary_error("45000.123")[0] == "Salary may have at most 2 decimal places"

    def test_two_decimals_are_accepted_and_stored_as_number(self):
        error, cleaned = salary_error("45000.50")
        assert error is None
        assert cleaned["salary"] == 45000.5

    def test_numeric_string_is_accepted(self):
        assert salary_error("40000")[0] is None

    def test_salary_is_not_compared_when_type_is_invalid(self):
        errors, _ = validate_employee(employee_data(TODAY, employment_type="Freelance", salary=100), TODAY)
        assert errors["employment_type"] == "Please select an employment type"
        assert "salary" not in errors
