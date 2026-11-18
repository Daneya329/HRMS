"""E2E: leave application rules and the approval workflow."""
from datetime import date, timedelta

import pytest

from tests.factories import employee_data, random_name
from tests.selenium.pages import LeavesPage

pytestmark = pytest.mark.selenium


def day(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


@pytest.fixture
def employee(api):
    e = api.post("/api/employees", json=employee_data(first_name="Leave", last_name=random_name("Q"))).get_json()
    e["label"] = f"{e['full_name']} ({e['employee_code']})"
    return e


def test_apply_and_approve(admin, live_server, employee):
    page = LeavesPage(admin, live_server).open()
    page.apply(employee["label"], "Annual", day(10), day(12), "Family wedding in Lahore")
    page.toast("submitted")
    assert page.status_of(employee["full_name"]) == "Pending"
    page.click(f'tr[data-employee="{employee["full_name"]}"] .approve')
    page.toast("approved")
    page.wait.until(lambda d: page.status_of(employee["full_name"]) == "Approved")


def test_reject_requires_a_reason(admin, live_server, employee):
    page = LeavesPage(admin, live_server).open()
    page.apply(employee["label"], "Casual", day(3), day(3), "Personal errand")
    page.toast("submitted")
    page.click(f'tr[data-employee="{employee["full_name"]}"] .reject')
    page.click("#dialogSubmit")
    assert page.field_error("remarks") == "Please give a rejection reason (at least 5 characters)"
    page.type("#remarks", "Team is short-staffed")
    page.click("#dialogSubmit")
    page.toast("rejected")
    page.wait.until(lambda d: page.status_of(employee["full_name"]) == "Rejected")


def test_leave_in_the_past_is_rejected(admin, live_server, employee):
    page = LeavesPage(admin, live_server).open()
    page.apply(employee["label"], "Sick", day(-2), day(-1), "Fever last week")
    assert page.field_error("start_date") == "Leave cannot start in the past"


def test_end_before_start_is_rejected(admin, live_server, employee):
    page = LeavesPage(admin, live_server).open()
    page.apply(employee["label"], "Annual", day(10), day(8), "Wrong order of dates")
    assert page.field_error("end_date") == "End date cannot be before the start date"


def test_more_than_15_days_is_rejected(admin, live_server, employee):
    page = LeavesPage(admin, live_server).open()
    page.apply(employee["label"], "Annual", day(10), day(25), "Long holiday abroad")
    assert page.field_error("end_date") == "A single request cannot exceed 15 days"


def test_sick_leave_balance_is_enforced(admin, live_server, employee, api):
    year = date.today().year + 1
    api.post("/api/leaves", json={"employee_id": employee["id"], "leave_type": "Sick", "start_date": f"{year}-02-01",
                                  "end_date": f"{year}-02-09", "reason": "Surgery recovery"})   # 9 of 10 days
    page = LeavesPage(admin, live_server).open()
    page.select("#leaveEmployee", employee["label"])
    page.select("#leaveType", "Sick")
    page.apply(employee["label"], "Sick", f"{year}-03-01", f"{year}-03-02", "Medical follow-up")
    assert page.field_error("leave_type") == "Not enough Sick leave: 1 day(s) left this year, 2 requested"


def test_overlapping_request_is_rejected(admin, live_server, employee, api):
    api.post("/api/leaves", json={"employee_id": employee["id"], "leave_type": "Annual", "start_date": day(20),
                                  "end_date": day(22), "reason": "Booked holiday"})
    page = LeavesPage(admin, live_server).open()
    page.apply(employee["label"], "Casual", day(22), day(23), "Overlapping request")
    assert "Overlaps an existing request" in page.field_error("start_date")
