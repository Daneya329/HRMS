"""REQ-SEC-01..04  Authentication, protected endpoints, lock-out and password change."""
import pytest

pytestmark = pytest.mark.api

PROTECTED = [
    ("GET", "/api/dashboard"), ("GET", "/api/employees"), ("POST", "/api/employees"),
    ("GET", "/api/employees/1"), ("PUT", "/api/employees/1"), ("DELETE", "/api/employees/1"),
    ("GET", "/api/departments"), ("POST", "/api/departments"), ("DELETE", "/api/departments/1"),
    ("GET", "/api/attendance"), ("POST", "/api/attendance"), ("GET", "/api/attendance/history"),
    ("GET", "/api/leaves"), ("POST", "/api/leaves"), ("POST", "/api/leaves/1/approve"),
    ("GET", "/api/me"), ("POST", "/api/account/password"),
]


def login(client, email="admin@hrms.local", password="Admin@123"):
    return client.post("/api/login", json={"email": email, "password": password})


def test_login_with_default_admin(client):
    response = login(client)
    assert response.status_code == 200
    assert response.get_json()["user"]["email"] == "admin@hrms.local"


def test_login_email_is_case_insensitive(client):
    assert login(client, email="ADMIN@HRMS.LOCAL").status_code == 200


@pytest.mark.parametrize("email, password", [("admin@hrms.local", "wrong"), ("nobody@x.com", "Admin@123")])
def test_wrong_credentials_give_a_generic_message(client, email, password):
    response = login(client, email, password)
    assert response.status_code == 400
    assert response.get_json()["message"] == "Invalid email or password"


@pytest.mark.parametrize("body", [{}, {"email": "admin@hrms.local"}, {"password": "x"}, None])
def test_missing_credentials(client, body):
    response = client.post("/api/login", json=body) if body is not None else client.post("/api/login")
    assert response.status_code == 400
    assert response.get_json()["message"] == "Email and password are required"


def test_account_locks_after_five_failed_attempts(client):
    for _ in range(5):
        assert login(client, password="wrong").status_code == 400
    locked = login(client)                       # correct password, but locked
    assert locked.status_code == 400
    assert "locked" in locked.get_json()["message"]


def test_failed_counter_resets_after_successful_login(client):
    for _ in range(4):
        login(client, password="wrong")
    assert login(client).status_code == 200
    for _ in range(4):
        login(client, password="wrong")
    assert login(client).status_code == 200      # would be locked if the counter had not reset


@pytest.mark.parametrize("method, url", PROTECTED)
def test_endpoints_require_login(client, method, url):
    response = client.open(url, method=method, json={})
    assert response.status_code == 401
    assert response.get_json()["message"] == "Please sign in first"


def test_logout_ends_the_session(auth):
    assert auth.get("/api/me").status_code == 200
    auth.post("/api/logout")
    assert auth.get("/api/me").status_code == 401


def test_rules_are_public(client):
    assert client.get("/api/rules").get_json()["minWage"]["Part-time"] == 20000


def test_change_password(auth, client):
    response = auth.post("/api/account/password", json={
        "current_password": "Admin@123", "new_password": "NewSecret9", "confirm_password": "NewSecret9"})
    assert response.status_code == 200
    auth.post("/api/logout")
    assert login(client).status_code == 400
    assert login(client, password="NewSecret9").status_code == 200


def test_change_password_with_wrong_current_password(auth):
    response = auth.post("/api/account/password", json={
        "current_password": "nope", "new_password": "NewSecret9", "confirm_password": "NewSecret9"})
    assert response.status_code == 400
    assert response.get_json()["errors"]["current_password"] == "Current password is incorrect"


def test_pages_are_served(client):
    for path in ["/", "/login", "/dashboard", "/employees", "/employee-form", "/attendance", "/leaves",
                 "/departments", "/settings", "/css/style.css", "/js/validation.js", "/favicon.svg"]:
        with client.get(path) as response:          # "with" closes the served file
            assert response.status_code == 200, path
    with client.get("/dashboard.html") as response:
        assert response.status_code == 302
    with client.get("/does-not-exist") as response:
        assert response.status_code == 404
    assert client.get("/api/does-not-exist").get_json() == {"message": "Not found"}
