"""REQ-DEP-01..03  Department create / rename / delete rules."""
import pytest

from tests.api.helpers import create_employee

pytestmark = pytest.mark.api


def test_default_departments_exist(auth):
    names = [d["name"] for d in auth.get("/api/departments").get_json()]
    assert names == sorted(["Human Resources", "Engineering", "Finance", "Sales", "Marketing", "Operations"])


def test_create_department(auth):
    response = auth.post("/api/departments", json={"name": " Research ", "description": "R&D"})
    assert response.status_code == 201
    assert response.get_json()["name"] == "Research"


@pytest.mark.parametrize("name", ["finance", "FINANCE", "Finance"])
def test_duplicate_names_are_rejected_case_insensitively(auth, name):
    response = auth.post("/api/departments", json={"name": name})
    assert response.status_code == 409
    assert "already exists" in response.get_json()["errors"]["name"]


def test_invalid_name(auth):
    assert auth.post("/api/departments", json={"name": "X"}).status_code == 400


def test_rename_department(auth):
    response = auth.put("/api/departments/2", json={"name": "Software Engineering"})
    assert response.get_json()["name"] == "Software Engineering"


def test_rename_to_existing_name_is_rejected(auth):
    assert auth.put("/api/departments/2", json={"name": "Finance"}).status_code == 409


def test_cannot_delete_department_with_employees(auth):
    create_employee(auth, department_id=1)
    response = auth.delete("/api/departments/1")
    assert response.status_code == 409
    assert "still has 1 employee(s)" in response.get_json()["message"]


def test_delete_empty_department(auth):
    assert auth.delete("/api/departments/3").status_code == 200
    assert auth.delete("/api/departments/3").status_code == 404


def test_employee_count_per_department(auth):
    create_employee(auth, department_id=2)
    create_employee(auth, department_id=2)
    counts = {d["name"]: d["employee_count"] for d in auth.get("/api/departments").get_json()}
    assert counts["Engineering"] == 2
