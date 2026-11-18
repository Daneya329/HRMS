"""
E2E: the Add-employee form enforces the hiring rules and shows clear messages.
(age 18-60 on the hire date, minimum wage per type, hire-date window, formats, duplicates)
"""
from datetime import date, timedelta

import pytest

from tests.factories import random_cnic, years_before
from tests.selenium.pages import EmployeeFormPage, EmployeesPage

pytestmark = pytest.mark.selenium
TODAY = date.today()
HIRE = TODAY - timedelta(days=30)


def valid(**overrides):
    data = {"first_name": "Sara", "last_name": "Ahmed", "gender": "Female",
            "date_of_birth": years_before(HIRE, 28).isoformat(), "cnic": random_cnic(),
            "email": f"sara.{random_cnic()[:5]}@company.com", "phone": "+92 321 7654321",
            "department": "Finance", "designation": "Accountant", "hire_date": HIRE.isoformat(),
            "employment_type": "Full-time", "salary": "65000"}
    data.update(overrides)
    return data


def submit(admin, live_server, **overrides):
    return EmployeeFormPage(admin, live_server).open().fill(valid(**overrides)).save()


def test_underage_candidate_is_rejected(admin, live_server):
    page = submit(admin, live_server, date_of_birth=years_before(HIRE, 17).isoformat())
    assert page.field_error("date_of_birth") == \
        "Employee must be at least 18 years old on the hire date (would be 17)"
    assert "/employee-form" in admin.current_url          # not saved


def test_candidate_older_than_60_is_rejected(admin, live_server):
    page = submit(admin, live_server, date_of_birth=years_before(HIRE, 61).isoformat())
    assert page.field_error("date_of_birth") == "Employee cannot be older than 60 on the hire date (would be 61)"


def test_salary_below_full_time_minimum_wage_is_rejected(admin, live_server):
    page = submit(admin, live_server, salary="39999")
    assert page.field_error("salary") == \
        "Salary is below the minimum wage for Full-time employees (PKR 40,000)"


def test_part_time_minimum_wage_is_lower(admin, live_server):
    page = submit(admin, live_server, employment_type="Part-time", salary="19999")
    assert page.field_error("salary") == "Salary is below the minimum wage for Part-time employees (PKR 20,000)"


def test_hire_date_before_company_was_founded_is_rejected(admin, live_server):
    page = submit(admin, live_server, hire_date="2009-12-31", date_of_birth="1980-05-05")
    assert page.field_error("hire_date") == "Hire date cannot be before the company was founded (2010-01-01)"


def test_hire_date_too_far_in_future_is_rejected(admin, live_server):
    page = submit(admin, live_server, hire_date=(TODAY + timedelta(days=91)).isoformat())
    assert page.field_error("hire_date") == "Hire date cannot be more than 90 days in the future"


@pytest.mark.parametrize("field, value, message", [
    ("cnic", "1234-567", "CNIC must be in the format 12345-1234567-1"),
    ("email", "sara@company", "Enter a valid email address, e.g. name@company.com"),
    ("phone", "12345", "Phone number must have 10 to 15 digits"),
    ("first_name", "S4ra", "First name may only contain letters, spaces, apostrophes and hyphens"),
])
def test_format_rules(admin, live_server, field, value, message):
    page = submit(admin, live_server, **{field: value})
    assert page.field_error(field) == message


def test_empty_form_highlights_required_fields(admin, live_server):
    page = EmployeeFormPage(admin, live_server).open().save()
    assert page.field_error("first_name") == "First name is required"
    assert page.field_error("salary") == "Salary is required"
    assert "highlighted field" in page.text("#formError")


def test_live_hints_show_age_and_minimum_wage(admin, live_server):
    page = EmployeeFormPage(admin, live_server).open()
    page.fill({"hire_date": HIRE.isoformat(), "date_of_birth": years_before(HIRE, 25).isoformat(),
               "employment_type": "Part-time", "salary": "21000"})
    assert page.text("#ageHint") == "Age on hire date: 25 (allowed 18–60)"
    assert page.text("#wageHint") == "Minimum wage for Part-time: PKR 20,000"
    assert "ok" in page.find("#wageHint").get_attribute("class")


def test_duplicate_email_is_reported_by_the_server(admin, live_server, api):
    existing = valid(email="duplicate.check@company.com")
    page = submit(admin, live_server, **existing)
    EmployeesPage(admin, live_server).wait_url("/employees")
    page = submit(admin, live_server, email="duplicate.check@company.com")
    assert page.field_error("email") == "Another employee already uses this email"


def test_boundary_values_are_accepted(admin, live_server):
    """Exactly 18 years old and exactly the minimum wage: both allowed."""
    data = valid(date_of_birth=years_before(HIRE, 18).isoformat(), salary="40000", first_name="Boundary")
    EmployeeFormPage(admin, live_server).open().fill(data).save()
    page = EmployeesPage(admin, live_server).wait_url("/employees")
    assert "Boundary Ahmed" in page.toast("added successfully")
