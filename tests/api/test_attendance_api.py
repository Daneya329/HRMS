"""Attendance API: duplicates, leave clash, update rules, daily sheet and history."""
from datetime import date, timedelta

import pytest

from tests.api.helpers import create_employee, iso

pytestmark = pytest.mark.api


def mark(client, employee_id, **fields):
    data = {"employee_id": employee_id, "date": iso(0), "status": "Present", "check_in": "09:00", "check_out": "17:00"}
    data.update(fields)
    return client.post("/api/attendance", json=data)


def test_mark_attendance(auth):
    e = create_employee(auth)
    response = mark(auth, e["id"])
    assert response.status_code == 201
    assert response.get_json()["status"] == "Present"


def test_duplicate_attendance_is_rejected(auth):
    e = create_employee(auth)
    assert mark(auth, e["id"]).status_code == 201
    second = mark(auth, e["id"], status="Absent", check_in="", check_out="")
    assert second.status_code == 409
    assert "already marked" in second.get_json()["errors"]["date"]


def test_same_employee_on_two_days_is_fine(auth):
    e = create_employee(auth)
    assert mark(auth, e["id"]).status_code == 201
    assert mark(auth, e["id"], date=iso(-1)).status_code == 201


@pytest.mark.parametrize("employee_id", [None, "", "abc", 999])
def test_non_existent_employee(auth, employee_id):
    response = mark(auth, employee_id)
    assert response.status_code == 400
    assert response.get_json()["errors"]["employee_id"] == "Please select an existing employee"


def test_rules_enforced_by_server(auth):
    e = create_employee(auth)
    assert "date" in mark(auth, e["id"], date=iso(1)).get_json()["errors"]
    assert "check_out" in mark(auth, e["id"], check_in="10:00", check_out="09:00").get_json()["errors"]
    assert "status" in mark(auth, e["id"], check_in="09:30").get_json()["errors"]


def test_not_before_hire_date(auth):
    hire = date.today() - timedelta(days=10)
    e = create_employee(auth, hire_date=hire.isoformat(), date_of_birth="1990-01-01")
    response = mark(auth, e["id"], date=(hire - timedelta(days=1)).isoformat())
    assert response.status_code == 400


def test_inactive_employee_cannot_be_marked(auth):
    e = create_employee(auth, status="Inactive")
    assert mark(auth, e["id"]).get_json()["errors"]["employee_id"] == \
        "Attendance can only be marked for active employees"


def test_cannot_mark_attendance_on_approved_leave(auth):
    e = create_employee(auth)
    leave = auth.post("/api/leaves", json={"employee_id": e["id"], "leave_type": "Sick", "start_date": iso(0),
                                           "end_date": iso(0), "reason": "Fever and flu"}).get_json()
    auth.post(f"/api/leaves/{leave['id']}/approve", json={})
    response = mark(auth, e["id"])
    assert response.status_code == 409
    assert "approved leave" in response.get_json()["message"]


def test_update_existing_record(auth):
    e = create_employee(auth)
    record = mark(auth, e["id"]).get_json()
    response = auth.put(f"/api/attendance/{record['id']}",
                        json={"status": "Late", "check_in": "09:40", "check_out": "18:00", "date": "1999-01-01"})
    assert response.status_code == 200
    body = response.get_json()
    assert (body["status"], body["check_in"], body["date"]) == ("Late", "09:40", iso(0))   # date not changeable


def test_invalid_update_is_rejected(auth):
    e = create_employee(auth)
    record = mark(auth, e["id"]).get_json()
    response = auth.put(f"/api/attendance/{record['id']}", json={"status": "Absent", "check_in": "09:00"})
    assert response.status_code == 400


def test_delete_record(auth):
    e = create_employee(auth)
    record = mark(auth, e["id"]).get_json()
    assert auth.delete(f"/api/attendance/{record['id']}").status_code == 200
    assert auth.delete(f"/api/attendance/{record['id']}").status_code == 404
    assert auth.put(f"/api/attendance/{record['id']}", json={}).status_code == 404


def test_daily_sheet_lists_active_employees_hired_by_that_day(auth):
    a = create_employee(auth, first_name="Asad")
    create_employee(auth, first_name="Future", hire_date=iso(30), date_of_birth="1990-01-01")
    create_employee(auth, first_name="Gone", status="Inactive")
    mark(auth, a["id"])
    sheet = auth.get("/api/attendance").get_json()
    assert [r["employee"]["first_name"] for r in sheet["rows"]] == ["Asad"]
    assert sheet["rows"][0]["attendance"]["status"] == "Present"


def test_daily_sheet_rejects_invalid_date(auth):
    assert auth.get("/api/attendance?date=31-12-2025").status_code == 400


def test_history_filters(auth):
    a = create_employee(auth)
    b = create_employee(auth)
    mark(auth, a["id"], date=iso(-2))
    mark(auth, a["id"], date=iso(-1))
    mark(auth, b["id"], date=iso(-1))
    assert len(auth.get("/api/attendance/history").get_json()) == 3
    assert len(auth.get(f"/api/attendance/history?employee_id={a['id']}").get_json()) == 2
    assert len(auth.get(f"/api/attendance/history?from={iso(-1)}&to={iso(-1)}").get_json()) == 2
