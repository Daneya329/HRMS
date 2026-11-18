"""E2E: departments."""
import random

import pytest

from tests.factories import employee_data
from tests.selenium.pages import DepartmentsPage

pytestmark = pytest.mark.selenium


def test_create_department(admin, live_server):
    name = f"Research {random.randint(1000, 9999)}"
    page = DepartmentsPage(admin, live_server).open()
    page.create(name, "Product research")
    assert name in page.toast("created")
    assert page.row(name).find_element("css selector", ".count").text == "0"


def test_duplicate_department_name_is_rejected(admin, live_server):
    page = DepartmentsPage(admin, live_server).open()
    page.create("finance")
    assert page.field_error("name") == "A department named 'finance' already exists"


def test_department_name_too_short(admin, live_server):
    page = DepartmentsPage(admin, live_server).open()
    page.create("X")
    assert page.field_error("name") == "Department name must be 2-50 characters"


def test_department_with_employees_cannot_be_deleted(admin, live_server, api):
    dept = api.post("/api/departments", json={"name": f"Busy {random.randint(1000, 9999)}"}).get_json()
    api.post("/api/employees", json=employee_data(department_id=dept["id"]))
    page = DepartmentsPage(admin, live_server).open()
    page.click(f'tr[data-name="{dept["name"]}"] button.delete')
    page.click("#confirmOk")
    assert "still has 1 employee(s)" in page.toast("still has")


def test_rename_department(admin, live_server, api):
    dept = api.post("/api/departments", json={"name": f"Old {random.randint(1000, 9999)}"}).get_json()
    new_name = dept["name"].replace("Old", "New")
    page = DepartmentsPage(admin, live_server).open()
    page.click(f'tr[data-name="{dept["name"]}"] button.edit')
    page.type("#editName", new_name)
    page.click("#dialogSubmit")
    page.toast("Department updated")
    assert page.row(new_name)


def test_delete_empty_department(admin, live_server, api):
    dept = api.post("/api/departments", json={"name": f"Empty {random.randint(1000, 9999)}"}).get_json()
    page = DepartmentsPage(admin, live_server).open()
    page.click(f'tr[data-name="{dept["name"]}"] button.delete')
    page.click("#confirmOk")
    page.toast("deleted")
    page.wait.until(lambda d: not page.find_all(f'tr[data-name="{dept["name"]}"]'))
