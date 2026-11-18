"""
Employee API + database. The server enforces every rule on its own, even if a client
skips the browser-side validation (e.g. Postman or a modified page).
"""
import sqlite3
from contextlib import closing
from datetime import date, timedelta

import pytest

from tests.api.helpers import create_employee, iso
from tests.factories import employee_data, years_before

pytestmark = pytest.mark.api


def test_create_employee_generates_sequential_ids(auth):
    first = create_employee(auth)
    second = create_employee(auth)
    assert first["employee_code"] == "EMP-0001"
    assert second["employee_code"] == "EMP-0002"
    assert first["department_name"] == "Human Resources"
    assert first["full_name"] == "Ayesha Malik"


def test_created_employee_can_be_retrieved_and_listed(auth):
    created = create_employee(auth, first_name="Bilal", email="bilal@company.com")
    assert auth.get(f"/api/employees/{created['id']}").get_json()["email"] == "bilal@company.com"
    assert [e["first_name"] for e in auth.get("/api/employees").get_json()] == ["Bilal"]


@pytest.mark.parametrize("overrides, field", [
    ({"date_of_birth": years_before(date.today(), 17).isoformat(), "hire_date": date.today().isoformat()},
     "date_of_birth"),
    ({"date_of_birth": years_before(date.today(), 61).isoformat(), "hire_date": date.today().isoformat()},
     "date_of_birth"),
    ({"salary": 39999}, "salary"),
    ({"employment_type": "Part-time", "salary": 19999}, "salary"),
    ({"hire_date": "2009-12-31", "date_of_birth": "1980-01-01"}, "hire_date"),
    ({"hire_date": (date.today() + timedelta(days=91)).isoformat()}, "hire_date"),
    ({"cnic": "12345"}, "cnic"),
    ({"email": "bad-email"}, "email"),
])
def test_server_rejects_rule_violations(auth, overrides, field):
    response = auth.post("/api/employees", json=employee_data(**overrides))
    assert response.status_code == 400
    assert field in response.get_json()["errors"]
    assert auth.get("/api/employees").get_json() == []          # nothing was saved


def test_minimum_wage_boundary_through_api(auth):
    assert auth.post("/api/employees", json=employee_data(salary=40000)).status_code == 201
    assert auth.post("/api/employees", json=employee_data(salary=39999.99)).status_code == 400


def test_missing_body_reports_all_required_fields(auth):
    response = auth.post("/api/employees", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert len(response.get_json()["errors"]) == 12


def test_unknown_department_is_rejected(auth):
    response = auth.post("/api/employees", json=employee_data(department_id=999))
    assert response.get_json()["errors"]["department_id"] == "Selected department does not exist"


@pytest.mark.parametrize("field", ["email", "cnic"])
def test_duplicates_are_rejected_with_409(auth, field):
    existing = create_employee(auth)
    value = existing[field].upper() if field == "email" else existing[field]
    response = auth.post("/api/employees", json=employee_data(**{field: value}))
    assert response.status_code == 409
    assert "Another employee" in response.get_json()["errors"][field]


def test_update_employee(auth):
    created = create_employee(auth)
    data = employee_data(**{k: created[k] for k in ("email", "cnic", "date_of_birth", "hire_date")})
    data.update(designation="QA Lead", salary=120000, status="Inactive")
    response = auth.put(f"/api/employees/{created['id']}", json=data)
    assert response.status_code == 200
    body = response.get_json()
    assert (body["designation"], body["salary"], body["status"]) == ("QA Lead", 120000, "Inactive")
    assert body["employee_code"] == created["employee_code"]


def test_update_cannot_take_another_employees_email(auth):
    a = create_employee(auth)
    b = create_employee(auth)
    response = auth.put(f"/api/employees/{b['id']}", json=employee_data(email=a["email"], cnic=b["cnic"]))
    assert response.status_code == 409


def test_update_with_invalid_salary_keeps_old_value(auth):
    created = create_employee(auth, salary=50000)
    response = auth.put(f"/api/employees/{created['id']}", json=employee_data(salary=100, cnic=created["cnic"]))
    assert response.status_code == 400
    assert auth.get(f"/api/employees/{created['id']}").get_json()["salary"] == 50000


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_unknown_employee_returns_404(auth, method):
    response = auth.open("/api/employees/999", method=method, json=employee_data())
    assert response.status_code == 404
    assert response.get_json()["message"] == "Employee not found"


def test_delete_employee_removes_attendance_and_leave(auth, app):
    e = create_employee(auth)
    auth.post("/api/attendance",
              json={"employee_id": e["id"], "date": iso(0), "status": "Present", "check_in": "09:00"})
    auth.post("/api/leaves", json={"employee_id": e["id"], "leave_type": "Casual", "start_date": iso(5),
                                   "end_date": iso(5), "reason": "Personal work"})
    assert auth.delete(f"/api/employees/{e['id']}").status_code == 200
    with closing(sqlite3.connect(app.config["DATABASE"])) as conn:
        assert conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM leave_requests").fetchone()[0] == 0


def test_search_and_filters(auth):
    hr = create_employee(auth, first_name="Hina", department_id=1)
    eng = create_employee(auth, first_name="Usman", department_id=2, status="Inactive")
    names = lambda url: [e["first_name"] for e in auth.get(url).get_json()]  # noqa: E731
    assert names("/api/employees?q=hina") == ["Hina"]
    assert names(f"/api/employees?q={eng['employee_code']}") == ["Usman"]
    assert names(f"/api/employees?q={hr['cnic']}") == ["Hina"]
    assert names("/api/employees?department_id=2") == ["Usman"]
    assert names("/api/employees?status=Active") == ["Hina"]
    assert names("/api/employees?q=nobody") == []


def test_database_constraints_block_invalid_rows_directly(app):
    """Defence in depth: even raw SQL cannot store a hire date before the company was founded."""
    with closing(sqlite3.connect(app.config["DATABASE"])) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO employees (employee_code, first_name, last_name, email, phone, cnic, gender, "
                         "date_of_birth, hire_date, department_id, designation, employment_type, salary) VALUES "
                         "('EMP-9', 'A', 'B', 'a@b.co', '1234567890', '12345-1234567-1', 'Male', '1990-01-01', "
                         "'2005-01-01', 1, 'X', 'Full-time', 50000)")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO employees (employee_code, first_name, last_name, email, phone, cnic, gender, "
                         "date_of_birth, hire_date, department_id, designation, employment_type, salary) VALUES "
                         "('EMP-9', 'A', 'B', 'a@b.co', '1234567890', '12345-1234567-1', 'Robot', '1990-01-01', "
                         "'2015-01-01', 1, 'X', 'Full-time', 50000)")
