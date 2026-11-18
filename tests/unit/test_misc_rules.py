"""Departments, passwords, parsing helpers and the rules export used by the frontend."""
import json

import pytest

from backend import rules
from backend.validators import parse_date, parse_time, validate_department, validate_password_change

pytestmark = pytest.mark.unit


class TestDepartment:
    @pytest.mark.parametrize("name, ok", [("", False), ("A", False), ("IT", True), ("D" * 50, True), ("D" * 51, False)])
    def test_name_length(self, name, ok):
        assert ("name" not in validate_department({"name": name})[0]) is ok

    def test_description_limit(self):
        assert "description" in validate_department({"name": "IT", "description": "x" * 201})[0]


class TestPassword:
    def test_valid_change(self):
        assert validate_password_change("old", "Secret123", "Secret123") == {}

    @pytest.mark.parametrize("new, field_message", [
        ("Short1", "at least 8 characters"),
        ("onlyletters", "a letter and a digit"),
        ("12345678", "a letter and a digit"),
    ])
    def test_weak_passwords(self, new, field_message):
        assert field_message in validate_password_change("old", new, new)["new_password"]

    def test_mismatch_and_missing_current(self):
        errors = validate_password_change("", "Secret123", "Secret124")
        assert errors["confirm_password"] == "Passwords do not match"
        assert errors["current_password"] == "Current password is required"


class TestParsers:
    def test_parse_date(self):
        assert parse_date("2024-02-29").isoformat() == "2024-02-29"
        assert parse_date("2023-02-29") is None
        assert parse_date(" 2024-01-01 ").isoformat() == "2024-01-01"

    def test_parse_time(self):
        assert parse_time("23:59").hour == 23
        assert parse_time("24:00") is None


def test_rules_export_is_json_serialisable_and_complete():
    exported = json.loads(json.dumps(rules.as_dict()))
    assert exported["minAge"] == 18 and exported["maxAge"] == 60
    assert exported["minWage"]["Full-time"] == 40000
    assert exported["companyFounded"] == "2010-01-01"
    assert exported["lateAfter"] == "09:15"
