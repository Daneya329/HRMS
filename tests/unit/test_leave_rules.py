"""
REQ-LEA-01  End date cannot be before the start date; leave cannot start in the past.
REQ-LEA-02  At most 15 days per request.
REQ-LEA-03  Yearly entitlement per type (Annual 20, Sick 10, Casual 10) cannot be exceeded.
REQ-LEA-04  Reason 5-200 characters; only active employees; rejection needs a reason.
"""
from datetime import date, timedelta

import pytest

from backend.validators import leave_days, validate_leave, validate_rejection

pytestmark = pytest.mark.unit
TODAY = date(2026, 6, 15)
EMPLOYEE = {"hire_date": "2025-01-10", "status": "Active"}


def errors_for(used=0, employee=EMPLOYEE, **fields):
    data = {"leave_type": "Annual", "start_date": "2026-07-01", "end_date": "2026-07-03",
            "reason": "Family wedding"}
    data.update(fields)
    return validate_leave(data, employee, TODAY, days_already_used=used)


def test_valid_request_counts_days_inclusively():
    errors, cleaned = errors_for()
    assert errors == {}
    assert cleaned["days"] == 3


def test_single_day_leave():
    assert leave_days(date(2026, 7, 1), date(2026, 7, 1)) == 1


class TestDates:
    def test_starting_today_is_allowed(self):
        assert errors_for(start_date=TODAY.isoformat(), end_date=TODAY.isoformat())[0] == {}

    def test_starting_yesterday_is_rejected(self):
        y = (TODAY - timedelta(days=1)).isoformat()
        assert errors_for(start_date=y, end_date=y)[0]["start_date"] == "Leave cannot start in the past"

    def test_end_before_start_is_rejected(self):
        assert errors_for(start_date="2026-07-05", end_date="2026-07-04")[0]["end_date"] == \
            "End date cannot be before the start date"

    @pytest.mark.parametrize("field", ["start_date", "end_date"])
    def test_missing_dates(self, field):
        assert field in errors_for(**{field: ""})[0]

    def test_before_hire_date_is_rejected(self):
        errors, _ = errors_for(employee={"hire_date": "2026-08-01", "status": "Active"})
        assert errors["start_date"] == "Leave cannot start before the hire date"


class TestLength:
    def test_15_days_is_allowed(self):
        assert errors_for(start_date="2026-07-01", end_date="2026-07-15")[0] == {}

    def test_16_days_is_rejected(self):
        assert errors_for(start_date="2026-07-01", end_date="2026-07-16")[0]["end_date"] == \
            "A single request cannot exceed 15 days"


class TestBalance:
    def test_using_exactly_the_remaining_days_is_allowed(self):
        assert errors_for(used=17)[0] == {}           # 20 - 17 = 3 left, 3 requested

    def test_one_day_over_the_balance_is_rejected(self):
        assert errors_for(used=18)[0]["leave_type"] == \
            "Not enough Annual leave: 2 day(s) left this year, 3 requested"

    @pytest.mark.parametrize("leave_type, entitlement", [("Sick", 10), ("Casual", 10)])
    def test_other_entitlements(self, leave_type, entitlement):
        assert errors_for(leave_type=leave_type, used=entitlement - 3)[0] == {}
        assert "Not enough" in errors_for(leave_type=leave_type, used=entitlement - 2)[0]["leave_type"]

    def test_unknown_leave_type(self):
        assert errors_for(leave_type="Vacation")[0]["leave_type"] == "Please select a leave type"


class TestReasonAndStatus:
    @pytest.mark.parametrize("reason, ok", [("Trip", False), ("Trips", True), ("x" * 200, True), ("x" * 201, False)])
    def test_reason_length(self, reason, ok):
        assert ("reason" not in errors_for(reason=reason)[0]) is ok

    def test_inactive_employee_cannot_apply(self):
        errors, _ = errors_for(employee={"hire_date": "2025-01-10", "status": "Inactive"})
        assert errors["employee_id"] == "Only active employees can apply for leave"

    @pytest.mark.parametrize("remarks, ok", [("", False), ("No", False), (None, False), ("Busy season", True)])
    def test_rejection_needs_a_reason(self, remarks, ok):
        assert (validate_rejection(remarks)[0] == {}) is ok
