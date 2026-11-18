"""
REQ-EMP-07..13  Format rules for names, email, phone, CNIC, gender, department,
designation and status. Technique: equivalence partitioning (valid / invalid classes).
"""
from datetime import date

import pytest

from backend.validators import validate_employee
from tests.factories import employee_data

pytestmark = pytest.mark.unit
TODAY = date(2026, 6, 15)


def errors_for(**overrides):
    return validate_employee(employee_data(TODAY, **overrides), TODAY)[0]


def test_complete_valid_employee_has_no_errors():
    assert errors_for() == {}


def test_cleaned_data_is_normalised():
    _, cleaned = validate_employee(employee_data(TODAY, first_name="  Ali ", email=" Ali.Khan@Company.COM "), TODAY)
    assert cleaned["first_name"] == "Ali"
    assert cleaned["email"] == "ali.khan@company.com"


def test_empty_form_reports_every_required_field():
    errors, _ = validate_employee({}, TODAY)
    assert set(errors) == {"first_name", "last_name", "email", "phone", "cnic", "gender", "date_of_birth",
                           "hire_date", "department_id", "designation", "employment_type", "salary"}


class TestNames:
    @pytest.mark.parametrize("name", ["Al", "Muhammad Ali", "O'Brien", "Anne-Marie", "A" * 50])
    def test_valid_names(self, name):
        assert "first_name" not in errors_for(first_name=name)

    @pytest.mark.parametrize("name, message", [
        ("", "First name is required"),
        ("A", "First name must be at least 2 characters"),
        ("A" * 51, "First name must be at most 50 characters"),
        ("Ali3", "First name may only contain letters, spaces, apostrophes and hyphens"),
        ("<script>", "First name may only contain letters, spaces, apostrophes and hyphens"),
        ("-Ali", "First name may only contain letters, spaces, apostrophes and hyphens"),
    ])
    def test_invalid_first_names(self, name, message):
        assert errors_for(first_name=name)["first_name"] == message

    def test_last_name_uses_same_rules(self):
        assert errors_for(last_name="X")["last_name"] == "Last name must be at least 2 characters"


class TestEmail:
    @pytest.mark.parametrize("email", ["a@b.co", "first.last+hr@sub.company.com"])
    def test_valid_emails(self, email):
        assert "email" not in errors_for(email=email)

    @pytest.mark.parametrize("email", ["plainaddress", "@company.com", "name@company", "name@@company.com",
                                       "name@company..com", "name @company.com"])
    def test_invalid_emails(self, email):
        assert errors_for(email=email)["email"] == "Enter a valid email address, e.g. name@company.com"

    def test_too_long_email(self):
        assert "at most 100" in errors_for(email="a" * 95 + "@x.com")["email"]


class TestPhone:
    @pytest.mark.parametrize("phone", ["0300 1234567", "+92 300 1234567", "03001234567", "1234567890",
                                       "+" + "1" * 15])
    def test_valid_phones(self, phone):
        assert "phone" not in errors_for(phone=phone)

    @pytest.mark.parametrize("phone", ["123456789", "+" + "1" * 16])
    def test_wrong_number_of_digits(self, phone):
        assert errors_for(phone=phone)["phone"] == "Phone number must have 10 to 15 digits"

    @pytest.mark.parametrize("phone", ["0300-ABC-4567", "(0300) 1234567", "92+3001234567"])
    def test_invalid_characters(self, phone):
        assert "may only contain digits" in errors_for(phone=phone)["phone"]


class TestCnic:
    def test_valid_cnic(self):
        assert "cnic" not in errors_for(cnic="35202-1234567-1")

    @pytest.mark.parametrize("cnic", ["3520212345671", "35202-123456-1", "35202-1234567-12", "ABCDE-1234567-1",
                                      "35202 1234567 1"])
    def test_invalid_cnic(self, cnic):
        assert errors_for(cnic=cnic)["cnic"] == "CNIC must be in the format 12345-1234567-1"


class TestSelections:
    @pytest.mark.parametrize("gender", ["", "male", "Unknown"])
    def test_invalid_gender(self, gender):
        assert errors_for(gender=gender)["gender"] == "Please select a gender"

    @pytest.mark.parametrize("value", [None, "", "abc", 0, -3])
    def test_invalid_department(self, value):
        assert errors_for(department_id=value)["department_id"] == "Please select a department"

    def test_department_as_string_number_is_accepted(self):
        assert "department_id" not in errors_for(department_id="2")

    @pytest.mark.parametrize("designation, ok", [("QA", True), ("X", False), ("D" * 60, True), ("D" * 61, False)])
    def test_designation_length(self, designation, ok):
        assert ("designation" not in errors_for(designation=designation)) is ok

    def test_status_defaults_to_active(self):
        _, cleaned = validate_employee(employee_data(TODAY, status=""), TODAY)
        assert cleaned["status"] == "Active"

    def test_invalid_status(self):
        assert errors_for(status="Retired")["status"] == "Status must be Active or Inactive"
