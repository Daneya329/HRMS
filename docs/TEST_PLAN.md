# HRMS – Test Plan and Quality Report

## 1. Purpose and scope

This document describes how the quality of the HRMS is assured: what is tested, at which level, with which
techniques, and how each requirement is traced to automated tests.

**In scope:** login and session security, employees, departments, attendance, leave, dashboard, business
rules, server-side validation, database integrity, user interface behaviour in Chrome.
**Out of scope:** performance/load testing, cross-browser testing (only Chrome), accessibility audit,
penetration testing.

## 2. Test levels

| Level | Tool | What it proves | Location | Count |
|---|---|---|---|---|
| **Unit** | pytest | Every business rule in isolation (pure functions, fixed "today") | `tests/unit` | 199 |
| **Integration** | pytest + Flask test client + SQLite | API, services and database work together; server rejects invalid data even if the browser is bypassed; DB constraints | `tests/api` | 98 |
| **System / end-to-end** | Selenium WebDriver + Chrome | Real user workflows and the messages a user sees | `tests/selenium` | 51 |
| **Static analysis** | flake8 | Code style, unused imports, undefined names | whole project | – |
| **Mutation testing** | `quality/mutation_check.py` | The tests actually detect bugs in the rules | – | 14 mutants |

## 3. Test design techniques

* **Boundary value analysis (BVA)** – for every numeric/date limit the values *just below*, *on* and
  *just above* the boundary are tested.
* **Equivalence partitioning (EP)** – inputs are split into valid and invalid classes (e.g. CNIC: correct
  format / missing dashes / wrong group length / letters / spaces) and one value per class is tested.
* **Decision table / combination testing** – attendance status × check-in time × check-out time
  (e.g. *Present* + check-in 09:16 → must be *Late*; *Absent* + any time → rejected).
* **State transition testing** – leave request: Pending → Approved / Rejected; decided requests cannot change again.
* **Negative testing** – missing fields, wrong types, duplicates, unknown IDs, unauthenticated access.
* **Error guessing** – leap-day birthdays, 30 February, NaN/Infinity salaries, case-insensitive duplicates,
  script tags in names.

### Boundary values used

| Rule | Below (rejected) | On (accepted) | Above |
|---|---|---|---|
| Minimum age on hire date (18) | 17 / one day before the 18th birthday | exactly 18 | – |
| Maximum age on hire date (60) | – | 60 / one day before 61st birthday | 61 rejected |
| Full-time minimum wage (40,000) | 39,999.99 · 39,999 | 40,000 | 40,001 accepted |
| Part-time minimum wage (20,000) | 19,999.99 · 19,999 | 20,000 | 20,001 accepted |
| Maximum salary (5,000,000) | – | 5,000,000 | 5,000,001 rejected |
| Earliest hire date (2010-01-01) | 2009-12-31 | 2010-01-01 | – |
| Latest hire date (today + 90) | – | today + 90 | today + 91 rejected |
| Late threshold (09:15) | – | 09:15 = Present | 09:16 must be Late |
| Earliest check-in (06:00) | 05:59 | 06:00 | – |
| Shift length (16 h) | – | 16:00 h | 16:01 h rejected |
| Half day (5 h) | – | 5:00 h | 5:01 h rejected |
| Leave length (15 days) | – | 15 days | 16 days rejected |
| Annual balance (20 days) | – | uses exactly the remaining days | one day more rejected |
| Name length (2–50) | 1 | 2 and 50 | 51 rejected |
| Phone digits (10–15) | 9 | 10 and 15 | 16 rejected |
| Reason length (5–200) | 4 | 5 and 200 | 201 rejected |

## 4. Requirements traceability matrix

| ID | Requirement | Unit tests | API / DB tests | Selenium tests |
|---|---|---|---|---|
| REQ-EMP-01 | Employee is at least 18 on the hire date | `test_employee_age_rules.py::TestMinimumAge` | `test_employee_api.py::test_server_rejects_rule_violations` | `test_employee_rules_ui.py::test_underage_candidate_is_rejected`, `test_boundary_values_are_accepted` |
| REQ-EMP-02 | Employee is at most 60 on the hire date | `TestMaximumAge` | `test_server_rejects_rule_violations` | `test_candidate_older_than_60_is_rejected` |
| REQ-EMP-03 | Salary ≥ minimum wage of the employment type | `test_salary_rules.py::TestMinimumWage` | `test_minimum_wage_boundary_through_api`, `test_update_with_invalid_salary_keeps_old_value` | `test_salary_below_full_time_minimum_wage_is_rejected`, `test_part_time_minimum_wage_is_lower`, `test_edit_cannot_break_the_minimum_wage_rule` |
| REQ-EMP-04 | Salary ≤ 5,000,000, numeric, max 2 decimals | `TestSalaryLimitsAndFormat` | – | – |
| REQ-EMP-05 | No hire before the company was founded (2010-01-01) | `test_hire_date_rules.py` | `test_server_rejects_rule_violations`, `test_database_constraints_block_invalid_rows_directly` | `test_hire_date_before_company_was_founded_is_rejected` |
| REQ-EMP-06 | Hire date at most 90 days ahead | `test_hire_date_rules.py` | `test_server_rejects_rule_violations` | `test_hire_date_too_far_in_future_is_rejected` |
| REQ-EMP-07 | Name, email, phone, CNIC formats | `test_employee_field_rules.py` | `test_server_rejects_rule_violations` | `test_format_rules` |
| REQ-EMP-08 | Email and CNIC are unique | – | `test_duplicates_are_rejected_with_409`, `test_update_cannot_take_another_employees_email` | `test_duplicate_email_is_reported_by_the_server` |
| REQ-EMP-09 | Sequential employee IDs | – | `test_create_employee_generates_sequential_ids` | `test_add_employee_appears_in_directory` |
| REQ-EMP-10 | Add, edit, search, filter, delete with confirmation | – | `test_update_employee`, `test_search_and_filters`, `test_delete_employee_removes_attendance_and_leave` | `test_employee_crud_ui.py` (7 tests) |
| REQ-DEP-01 | Unique department names (case-insensitive) | `test_misc_rules.py::TestDepartment` | `test_duplicate_names_are_rejected_case_insensitively` | `test_duplicate_department_name_is_rejected` |
| REQ-DEP-02 | Department with employees cannot be deleted | – | `test_cannot_delete_department_with_employees` | `test_department_with_employees_cannot_be_deleted` |
| REQ-ATT-01 | No future dates, not before hire date | `test_attendance_rules.py::TestDates` | `test_rules_enforced_by_server`, `test_not_before_hire_date` | `test_future_date_cannot_be_selected` |
| REQ-ATT-02 | One record per employee per day | – | `test_duplicate_attendance_is_rejected` | `test_duplicate_attendance_is_prevented` |
| REQ-ATT-03 | Only active employees, not on approved leave | `TestDates::test_inactive_employee_is_rejected` | `test_inactive_employee_cannot_be_marked`, `test_cannot_mark_attendance_on_approved_leave` | – |
| REQ-ATT-04 | Late rule (09:15) | `TestLateRule` | `test_rules_enforced_by_server` | `test_late_check_in_must_be_marked_late` |
| REQ-ATT-05 | Check-out after check-in, max 16 h, half day max 5 h | `TestWorkingHours` | `test_rules_enforced_by_server` | `test_check_out_before_check_in_is_rejected`, `test_update_existing_record` |
| REQ-LEA-01 | No leave in the past; end ≥ start | `test_leave_rules.py::TestDates` | `test_server_validates_dates` | `test_leave_in_the_past_is_rejected`, `test_end_before_start_is_rejected` |
| REQ-LEA-02 | Max 15 days per request | `TestLength` | `test_server_validates_dates` | `test_more_than_15_days_is_rejected` |
| REQ-LEA-03 | Yearly entitlement not exceeded | `TestBalance` | `test_annual_balance_cannot_be_exceeded`, `test_leave_balance_endpoint` | `test_sick_leave_balance_is_enforced` |
| REQ-LEA-04 | No overlapping requests | – | `test_overlapping_request_is_rejected`, `test_adjacent_request_is_allowed` | `test_overlapping_request_is_rejected` |
| REQ-LEA-05 | Approve / reject (reason required), decided once | `TestReasonAndStatus` | `test_reject_requires_remarks`, `test_decided_request_cannot_be_decided_again` | `test_apply_and_approve`, `test_reject_requires_a_reason` |
| REQ-SEC-01 | Login with hashed passwords, generic error message | – | `test_auth_api.py` (login tests) | `test_valid_login_opens_dashboard`, `test_wrong_password_shows_error` |
| REQ-SEC-02 | Every API endpoint requires a session | – | `test_endpoints_require_login` (17 endpoints) | `test_protected_page_redirects_to_login` |
| REQ-SEC-03 | Lock-out after 5 failed logins | – | `test_account_locks_after_five_failed_attempts` | – |
| REQ-SEC-04 | Change password with validation | `TestPassword` | `test_change_password*` | `test_password_change_validation` |
| REQ-DSH-01 | Dashboard figures are correct | – | `test_dashboard_counts` | `test_dashboard_counts_follow_the_data` |

## 5. Test environment and data

* Each unit test uses a fixed "today" (2026-06-15) → results never depend on the day the tests run.
* Each API test gets a **new temporary SQLite database** (pytest `tmp_path`) → full isolation.
* Selenium tests start the real app on a free port with a separate temporary database; test data is created
  quickly through the API and names/IDs are randomised so tests never interfere with each other.
* Your development database `hrms.db` is never used by any test.

## 6. Entry and exit criteria

**Entry:** code compiles/imports, `pip install -r requirements.txt` succeeds.
**Exit (release criteria):**

1. flake8 reports no issues.
2. 100 % of the 348 automated tests pass.
3. Line + branch coverage of `backend/` ≥ 90 % (enforced by `run_quality_checks.py`).
4. Mutation score 100 % (all 14 mutants killed).

## 7. Defects found during development

Real problems found by testing while the project was built, and how they were fixed:

| # | Found by | Defect | Fix |
|---|---|---|---|
| D1 | Manual browser smoke test | The login page reloaded endlessly: its "already signed in?" check got 401 and the API helper redirected to `/login` again | The helper no longer redirects when already on the login page |
| D2 | Visual review of screenshots | Attendance and leave tables overflowed next to the side form; *Mark/Approve* buttons were cut off at 1440 px | Forms moved into a horizontal bar; overflow verified to be 0 px at desktop and mobile widths |
| D3 | Visual review | Minimum-wage hint duplicated the error text under the salary field | Hints are hidden while a field shows an error |
| D4 | Selenium (intermittent) | Tests sometimes failed with *StaleElementReference* because tables re-render after saving | Page objects ignore stale elements while waiting and retry clicks |
| D5 | Selenium (order-dependent) | A leave test passed alone but failed in the full run: several tests created employees with the same name | Test data uses random unique names |
| D6 | Mutation testing | Mutation results were wrong: Python reused cached bytecode of a mutated file with the same size and timestamp | The script clears `__pycache__` and disables bytecode writing for every run |
| D7 | pytest warnings (`-W error`) | Tests left SQLite connections and served files open (*ResourceWarning*) | Connections and responses are closed with context managers |

## 8. How to execute

```text
python run_quality_checks.py              # flake8 + all tests + coverage ≥ 90 % + HTML reports
python run_quality_checks.py --fast       # without Selenium
python run_quality_checks.py --mutation   # additionally mutation testing
```

Reports: `reports/test-report.html`, `reports/coverage/index.html`, `reports/screenshots/` (failures only).
