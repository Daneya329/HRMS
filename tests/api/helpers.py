from datetime import date, timedelta

from tests.factories import employee_data


def create_employee(client, **overrides):
    response = client.post("/api/employees", json=employee_data(**overrides))
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def iso(days_from_today):
    return (date.today() + timedelta(days=days_from_today)).isoformat()
