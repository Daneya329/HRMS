"""
REQ-ATT-01  Attendance cannot be in the future or before the hire date.
REQ-ATT-02  Only active employees can be marked.
REQ-ATT-03  Present/Late/Half Day need a check-in; Absent has no times.
REQ-ATT-04  Check-in after LATE_AFTER (09:15) must be 'Late'; 'Late' needs a check-in after 09:15.
REQ-ATT-05  Check-out must be later than check-in; a shift is at most 16 h; a Half Day at most 5 h.
"""
from datetime import date

import pytest

from backend.validators import validate_attendance, worked_hours, parse_time

pytestmark = pytest.mark.unit
TODAY = date(2026, 6, 15)
EMPLOYEE = {"hire_date": "2025-01-10", "status": "Active"}


def errors_for(employee=EMPLOYEE, **fields):
    data = {"date": "2026-06-10", "status": "Present", "check_in": "09:00", "check_out": "17:00"}
    data.update(fields)
    return validate_attendance(data, employee, TODAY)


def test_valid_record():
    errors, cleaned = errors_for()
    assert errors == {}
    assert cleaned == {"date": "2026-06-10", "status": "Present", "check_in": "09:00", "check_out": "17:00"}


class TestDates:
    def test_today_is_allowed(self):
        assert errors_for(date=TODAY.isoformat())[0] == {}

    def test_tomorrow_is_rejected(self):
        assert errors_for(date="2026-06-16")[0]["date"] == "Attendance cannot be marked for a future date"

    def test_on_hire_date_is_allowed(self):
        assert errors_for(date="2025-01-10")[0] == {}

    def test_day_before_hire_date_is_rejected(self):
        assert errors_for(date="2025-01-09")[0]["date"] == "Attendance cannot be before the hire date (2025-01-10)"

    @pytest.mark.parametrize("value", ["", None, "10/06/2026", "2026-06-31"])
    def test_invalid_date(self, value):
        assert errors_for(date=value)[0]["date"] == "Enter a valid date (YYYY-MM-DD)"

    def test_inactive_employee_is_rejected(self):
        errors, _ = errors_for(employee={"hire_date": "2025-01-10", "status": "Inactive"})
        assert errors["employee_id"] == "Attendance can only be marked for active employees"


class TestStatusAndTimes:
    def test_unknown_status(self):
        assert errors_for(status="Holiday")[0]["status"] == "Please select a valid status"

    def test_absent_without_times_is_valid(self):
        errors, cleaned = errors_for(status="Absent", check_in="", check_out="")
        assert errors == {}
        assert cleaned["check_in"] is None and cleaned["check_out"] is None

    def test_absent_with_times_is_rejected(self):
        assert "absent employee cannot have" in errors_for(status="Absent")[0]["check_in"]

    @pytest.mark.parametrize("status", ["Present", "Late", "Half Day"])
    def test_check_in_required(self, status):
        assert errors_for(status=status, check_in="", check_out="")[0]["check_in"] == \
            f"Check-in time is required for status '{status}'"

    def test_check_in_before_6am_is_rejected(self):
        assert errors_for(check_in="05:59")[0]["check_in"] == "Check-in cannot be earlier than 06:00"

    def test_check_in_at_6am_is_allowed(self):
        assert errors_for(check_in="06:00")[0] == {}

    @pytest.mark.parametrize("value", ["9:00", "25:00", "09:60", "nine"])
    def test_invalid_time_format(self, value):
        assert errors_for(check_in=value)[0]["check_in"] == "Check-in must be a valid time (HH:MM)"


class TestLateRule:
    def test_present_at_exactly_0915_is_allowed(self):
        assert errors_for(check_in="09:15")[0] == {}

    def test_present_at_0916_must_be_late(self):
        assert errors_for(check_in="09:16")[0]["status"] == "Check-in after 09:15 must be marked as Late"

    def test_late_at_0916_is_allowed(self):
        assert errors_for(status="Late", check_in="09:16")[0] == {}

    def test_late_at_0915_is_rejected(self):
        assert errors_for(status="Late", check_in="09:15")[0]["status"] == "'Late' requires a check-in after 09:15"


class TestWorkingHours:
    def test_check_out_equal_to_check_in_is_rejected(self):
        assert errors_for(check_in="09:00", check_out="09:00")[0]["check_out"] == \
            "Check-out must be later than check-in"

    def test_check_out_before_check_in_is_rejected(self):
        assert errors_for(check_in="09:00", check_out="08:59")[0]["check_out"] == \
            "Check-out must be later than check-in"

    def test_check_out_is_optional(self):
        assert errors_for(check_out="")[0] == {}

    def test_shift_of_exactly_16_hours_is_allowed(self):
        assert errors_for(check_in="06:00", check_out="22:00")[0] == {}

    def test_shift_longer_than_16_hours_is_rejected(self):
        assert errors_for(check_in="06:00", check_out="22:01")[0]["check_out"] == \
            "A shift cannot be longer than 16 hours"

    def test_half_day_of_5_hours_is_allowed(self):
        assert errors_for(status="Half Day", check_in="09:00", check_out="14:00")[0] == {}

    def test_half_day_longer_than_5_hours_is_rejected(self):
        assert "cannot exceed 5 worked hours" in \
            errors_for(status="Half Day", check_in="09:00", check_out="14:01")[0]["status"]

    def test_half_day_requires_check_out(self):
        assert errors_for(status="Half Day", check_out="")[0]["check_out"] == \
            "Check-out time is required for a Half Day"

    def test_worked_hours_helper(self):
        assert worked_hours(parse_time("09:00"), parse_time("17:30")) == 8.5
