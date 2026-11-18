"""Shared fixtures: an isolated app + temporary SQLite database for every test."""
import pytest

from backend.app import create_app


@pytest.fixture
def app(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True, "SECRET_KEY": "test-secret"})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth(client):
    """A test client that is already signed in as the default administrator."""
    response = client.post("/api/login", json={"email": "admin@hrms.local", "password": "Admin@123"})
    assert response.status_code == 200
    return client
