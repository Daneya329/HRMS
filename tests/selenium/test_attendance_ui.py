"""E2E: daily attendance sheet, validation rules and duplicate prevention."""
from datetime import date

import pytest

from tests.factories import employee_data
from tests.selenium.pages import AttendancePage

pytestmark = pytest.mark.selenium


@pytest.fixture
def employee(api):
    return api.post("/api/employees", json=employee_data(first_name="Attendee")).get_json()


def test_mark_present(admin, live_server, employee):
    page = AttendancePage(admin, live_server).open()
    page.mark_row(employee["employee_code"], "Present", "09:00", "17:30")
    page.toast("Present saved")
    assert page.saved_status(employee["employee_code"], "Present")
    assert page.text(f'tr[data-code="{employee["employee_code"]}"] .row-save') == "Update"


def test_late_check_in_must_be_marked_late(admin, live_server, employee):
    page = AttendancePage(admin, live_server).open()
    page.mark_row(employee["employee_code"], "Present", "09:30")
    assert page.row_error(employee["employee_code"]) == "Check-in after 09:15 must be marked as Late"
    page.mark_row(employee["employee_code"], "Late", "09:30")
    assert page.saved_status(employee["employee_code"], "Late")


def test_check_out_before_check_in_is_rejected(admin, live_server, employee):
    page = AttendancePage(admin, live_server).open()
    page.mark_row(employee["employee_code"], "Present", "09:00", "08:00")
    assert page.row_error(employee["employee_code"]) == "Check-out must be later than check-in"
    assert page.text(f'tr[data-code="{employee["employee_code"]}"] .saved') == "Not marked"


def test_duplicate_attendance_is_prevented(admin, live_server, employee):
    page = AttendancePage(admin, live_server).open()
    page.mark_row(employee["employee_code"], "Present", "09:00")
    page.saved_status(employee["employee_code"], "Present")
    # second record for the same employee and day through the quick-entry form
    page.select("#quickEmployee", f"{employee['full_name']} ({employee['employee_code']})")
    page.select("#quickStatus", "Absent")
    page.set_value("#quickIn", "")
    page.click("#quickSaveBtn")
    assert "is already marked" in page.field_error("date")


def test_update_existing_record(admin, live_server, employee):
    page = AttendancePage(admin, live_server).open()
    page.mark_row(employee["employee_code"], "Present", "09:00")
    page.saved_status(employee["employee_code"], "Present")
    page.mark_row(employee["employee_code"], "Half Day", "09:00", "13:00")
    assert page.saved_status(employee["employee_code"], "Half Day")


def test_future_date_cannot_be_selected(admin, live_server):
    page = AttendancePage(admin, live_server).open()
    assert page.find("#attDate").get_attribute("max") == date.today().isoformat()


def test_history_shows_marked_record(admin, live_server, employee):
    page = AttendancePage(admin, live_server).open()
    page.mark_row(employee["employee_code"], "Present", "08:45", "17:00")
    page.saved_status(employee["employee_code"], "Present")
    page.click("#tabHistory")
    page.select("#historyEmployee", f"{employee['full_name']} ({employee['employee_code']})")
    page.click("#historyBtn")
    page.wait.until(lambda d: "08:45" in page.text("#historyTable"))
    assert "8.25" in page.text("#historyTable")
