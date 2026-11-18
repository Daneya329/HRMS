"""Leave API: application, overlaps, yearly balance and the approval workflow."""
import pytest

from tests.api.helpers import create_employee, iso

pytestmark = pytest.mark.api


def apply(client, employee_id, start=5, end=6, leave_type="Annual", reason="Family event"):
    return client.post("/api/leaves", json={"employee_id": employee_id, "leave_type": leave_type,
                                            "start_date": iso(start), "end_date": iso(end), "reason": reason})


@pytest.fixture
def employee(auth):
    return create_employee(auth)


def test_apply_creates_pending_request(auth, employee):
    response = apply(auth, employee["id"])
    assert response.status_code == 201
    body = response.get_json()
    assert (body["status"], body["days"]) == ("Pending", 2)


def test_overlapping_request_is_rejected(auth, employee):
    apply(auth, employee["id"], 10, 12)
    response = apply(auth, employee["id"], 12, 14, leave_type="Casual")
    assert response.status_code == 409
    assert "Overlaps" in response.get_json()["errors"]["start_date"]


def test_adjacent_request_is_allowed(auth, employee):
    apply(auth, employee["id"], 10, 12)
    assert apply(auth, employee["id"], 13, 14).status_code == 201


def test_rejected_request_does_not_block_new_one(auth, employee):
    leave = apply(auth, employee["id"], 10, 12).get_json()
    auth.post(f"/api/leaves/{leave['id']}/reject", json={"remarks": "Peak season"})
    assert apply(auth, employee["id"], 10, 12).status_code == 201


def test_server_validates_dates(auth, employee):
    assert apply(auth, employee["id"], -1, 0).status_code == 400
    assert apply(auth, employee["id"], 5, 4).status_code == 400
    assert apply(auth, employee["id"], 5, 20).status_code == 400          # 16 days


def test_annual_balance_cannot_be_exceeded(auth, employee):
    """20 Annual days per year: 15 + 5 are fine, the 21st day is not (requests in the same year)."""
    import datetime
    year = datetime.date.today().year + 1
    def req(start, end):  # noqa: E306
        return auth.post("/api/leaves", json={"employee_id": employee["id"], "leave_type": "Annual",
                                              "start_date": f"{year}-{start}", "end_date": f"{year}-{end}",
                                              "reason": "Annual vacation"})
    assert req("03-01", "03-15").status_code == 201        # 15 days
    assert req("04-01", "04-05").status_code == 201        # 5 days  -> 20 used
    response = req("05-01", "05-01")                        # 21st day
    assert response.status_code == 400
    assert response.get_json()["errors"]["leave_type"] == \
        "Not enough Annual leave: 0 day(s) left this year, 1 requested"


def test_leave_balance_endpoint(auth, employee):
    apply(auth, employee["id"], 5, 7, leave_type="Sick", reason="Medical rest")
    balance = auth.get(f"/api/employees/{employee['id']}/leave-balance").get_json()
    assert balance["Sick"] == {"entitlement": 10, "used": 3, "remaining": 7}
    assert balance["Annual"]["remaining"] == 20


def test_approve(auth, employee):
    leave = apply(auth, employee["id"]).get_json()
    response = auth.post(f"/api/leaves/{leave['id']}/approve", json={"remarks": "Enjoy"})
    assert response.get_json()["status"] == "Approved"


def test_reject_requires_remarks(auth, employee):
    leave = apply(auth, employee["id"]).get_json()
    response = auth.post(f"/api/leaves/{leave['id']}/reject", json={"remarks": ""})
    assert response.status_code == 400
    assert auth.get("/api/leaves?status=Pending").get_json()[0]["id"] == leave["id"]


def test_reject_with_remarks(auth, employee):
    leave = apply(auth, employee["id"]).get_json()
    body = auth.post(f"/api/leaves/{leave['id']}/reject", json={"remarks": "Project deadline"}).get_json()
    assert (body["status"], body["remarks"]) == ("Rejected", "Project deadline")


def test_decided_request_cannot_be_decided_again(auth, employee):
    leave = apply(auth, employee["id"]).get_json()
    auth.post(f"/api/leaves/{leave['id']}/approve", json={})
    response = auth.post(f"/api/leaves/{leave['id']}/reject", json={"remarks": "Changed my mind"})
    assert response.status_code == 409
    assert response.get_json()["message"] == "This request is already Approved"


def test_unknown_leave_returns_404(auth):
    assert auth.post("/api/leaves/999/approve", json={}).status_code == 404


def test_list_filters_and_pending_first(auth, employee):
    first = apply(auth, employee["id"], 5, 5).get_json()
    apply(auth, employee["id"], 8, 8)
    auth.post(f"/api/leaves/{first['id']}/approve", json={})
    statuses = [l["status"] for l in auth.get("/api/leaves").get_json()]  # noqa: E741
    assert statuses == ["Pending", "Approved"]
    assert len(auth.get("/api/leaves?status=Approved").get_json()) == 1
    assert len(auth.get(f"/api/leaves?employee_id={employee['id']}").get_json()) == 2


def test_dashboard_counts(auth):
    a = create_employee(auth)
    b = create_employee(auth)
    c = create_employee(auth)
    create_employee(auth, status="Inactive")
    auth.post("/api/attendance",
              json={"employee_id": a["id"], "date": iso(0), "status": "Present", "check_in": "09:00"})
    auth.post("/api/attendance", json={"employee_id": b["id"], "date": iso(0), "status": "Absent"})
    leave = apply(auth, c["id"], 0, 0, leave_type="Sick", reason="Doctor visit").get_json()
    auth.post(f"/api/leaves/{leave['id']}/approve", json={})
    apply(auth, a["id"], 3, 3)
    d = auth.get("/api/dashboard").get_json()
    assert (d["total_employees"], d["active_employees"]) == (4, 3)
    assert (d["present_today"], d["absent_today"], d["on_leave_today"], d["not_marked_today"]) == (1, 1, 1, 0)
    assert d["pending_leaves"] == 1
