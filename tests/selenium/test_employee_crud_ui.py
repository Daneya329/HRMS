"""E2E: add, view, edit, search, filter and delete employees."""
import pytest

from tests.factories import employee_data, random_cnic
from tests.selenium.pages import EmployeeFormPage, EmployeesPage

pytestmark = pytest.mark.selenium


def test_add_employee_appears_in_directory(admin, live_server):
    email = f"omar.{random_cnic()[:5]}@company.com"
    data = employee_data()
    EmployeeFormPage(admin, live_server).open().fill({
        "first_name": "Omar", "last_name": "Farooq", "gender": "Male", "date_of_birth": data["date_of_birth"],
        "cnic": random_cnic(), "email": email, "phone": "0333 1112223", "department": "Engineering",
        "designation": "Backend Developer", "hire_date": data["hire_date"], "employment_type": "Contract",
        "salary": "150000"}).save()
    page = EmployeesPage(admin, live_server).wait_url("/employees").wait_ready()
    message = page.toast("added successfully")
    code = message.split("(")[1].split(")")[0]
    row = page.row(code)
    assert "Omar Farooq" in row.text
    assert row.find_element("css selector", ".department").text == "Engineering"
    assert row.find_element("css selector", ".designation").text == "Backend Developer"
    assert row.find_element("css selector", ".salary").text == "PKR 150,000"


def test_edit_employee(admin, live_server, api):
    employee = api.post("/api/employees", json=employee_data(first_name="Edit")).get_json()
    page = EmployeeFormPage(admin, live_server).open(f"?id={employee['id']}")
    assert page.find("#employee_code").get_attribute("value") == employee["employee_code"]
    page.type("#designation", "Senior QA Engineer")
    page.type("#salary", "99000")
    page.save()
    directory = EmployeesPage(admin, live_server).wait_url("/employees").wait_ready()
    assert "updated successfully" in directory.toast("updated")
    row = directory.row(employee["employee_code"])
    assert row.find_element("css selector", ".designation").text == "Senior QA Engineer"
    assert row.find_element("css selector", ".salary").text == "PKR 99,000"


def test_edit_cannot_break_the_minimum_wage_rule(admin, live_server, api):
    employee = api.post("/api/employees", json=employee_data()).get_json()
    page = EmployeeFormPage(admin, live_server).open(f"?id={employee['id']}")
    page.type("#salary", "1000")
    page.save()
    assert "below the minimum wage" in page.field_error("salary")


def test_search_by_name_and_id(admin, live_server, api):
    unique = api.post("/api/employees", json=employee_data(first_name="Zubair", last_name="Qureshi")).get_json()
    page = EmployeesPage(admin, live_server).open()
    page.search("Zubair")
    assert page.codes() == [unique["employee_code"]]
    page.search(unique["employee_code"])
    assert page.codes() == [unique["employee_code"]]
    page.search("no-such-person")
    assert "No employees match" in page.text("#noResults")


def test_filter_by_status(admin, live_server, api):
    inactive = api.post("/api/employees", json=employee_data(first_name="Inactive", status="Inactive")).get_json()
    page = EmployeesPage(admin, live_server).open()
    page.select("#filterStatus", "Inactive")
    page.wait.until(lambda d: page.codes() and all(
        r.find_element("css selector", ".status").text == "Inactive" for r in page.find_all("tr[data-code]")))
    assert inactive["employee_code"] in page.codes()


def test_delete_employee_with_confirmation(admin, live_server, api):
    employee = api.post("/api/employees", json=employee_data(first_name="Temporary")).get_json()
    page = EmployeesPage(admin, live_server).open()
    page.delete(employee["employee_code"])
    assert "Temporary Malik was deleted" in page.toast("was deleted")
    page.wait.until(lambda d: employee["employee_code"] not in page.codes())


def test_cancel_delete_keeps_employee(admin, live_server, api):
    employee = api.post("/api/employees", json=employee_data(first_name="Keeper")).get_json()
    page = EmployeesPage(admin, live_server).open()
    page.click(f'tr[data-code="{employee["employee_code"]}"] button.delete')
    page.click("#confirmCancel")
    assert employee["employee_code"] in page.codes()
