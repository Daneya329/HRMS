# Verified test results

Recorded from a full run of `python run_quality_checks.py --mutation` on 2026-11-17
(Linux, Python 3.13, Chrome 153 headless). The HTML reports from that run are in this folder:
`test-report.html` and `coverage/index.html`. Re-run on your machine to regenerate them.

| Check | Result |
|---|---|
| Static analysis (flake8) | **0 issues** |
| Unit tests (`tests/unit`) | **199 / 199 passed** |
| API + database tests (`tests/api`) | **98 / 98 passed** |
| Selenium browser tests (`tests/selenium`) | **51 / 51 passed** |
| **Total** | **348 passed, 0 failed, 0 skipped, 0 warnings** (≈ 2 minutes) |
| Code coverage of `backend/` (line + branch) | **98.15 %** (minimum required: 90 %) |
| Mutation testing | **14 / 14 mutants killed (100 %)** |

## Coverage per file

| File | Statements | Missed | Branches | Coverage |
|---|---|---|---|---|
| backend/app.py | 183 | 3 | 12 | 97 % |
| backend/database.py | 32 | 0 | 8 | 95 % |
| backend/rules.py | 36 | 0 | 0 | 100 % |
| backend/services.py | 262 | 4 | 82 | 99 % |
| backend/validators.py | 256 | 4 | 154 | 98 % |
| **Total** | **769** | **11** | **256** | **98 %** |

## Mutation testing

| # | Injected bug | Detected |
|---|---|---|
| 1 | Minimum age lowered to 17 | ✅ |
| 2 | Maximum age raised to 61 | ✅ |
| 3 | Full-time minimum wage lowered to 39,999 | ✅ |
| 4 | Part-time minimum wage lowered to 19,999 | ✅ |
| 5 | Hiring allowed before the company was founded | ✅ |
| 6 | Hire window extended to 91 days | ✅ |
| 7 | Late threshold moved to 09:16 | ✅ |
| 8 | Off-by-one in the age check (`<` → `<=`) | ✅ |
| 9 | Check-out equal to check-in allowed | ✅ |
| 10 | Leave starting today rejected | ✅ |
| 11 | Off-by-one in the leave balance | ✅ |
| 12 | Duplicate-attendance check removed | ✅ |
| 13 | Leave overlap check weakened | ✅ |
| 14 | Department-in-use check removed | ✅ |

A fresh virtual environment created only from `requirements.txt` was also verified to install and pass
all non-browser tests.
