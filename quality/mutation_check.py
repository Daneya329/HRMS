"""
Mutation testing - "do the tests really catch bugs?"

Each mutant changes ONE business rule slightly (e.g. minimum age 18 -> 17). The unit and
API tests are run against the mutated code; a good test suite must FAIL ("kill" the mutant).
The original code is always restored, even if the script is interrupted.

    python quality/mutation_check.py
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MUTANTS = [
    ("backend/rules.py", "MIN_AGE = 18", "MIN_AGE = 17", "Minimum age lowered to 17"),
    ("backend/rules.py", "MAX_AGE = 60", "MAX_AGE = 61", "Maximum age raised to 61"),
    ("backend/rules.py", '"Full-time": 40000', '"Full-time": 39999', "Full-time minimum wage lowered"),
    ("backend/rules.py", '"Part-time": 20000', '"Part-time": 19999', "Part-time minimum wage lowered"),
    ("backend/rules.py", "COMPANY_FOUNDED = date(2010, 1, 1)", "COMPANY_FOUNDED = date(2009, 12, 31)",
     "Hiring allowed before the company was founded"),
    ("backend/rules.py", "MAX_HIRE_DAYS_AHEAD = 90", "MAX_HIRE_DAYS_AHEAD = 91", "Hire window extended by a day"),
    ("backend/rules.py", "LATE_AFTER = time(9, 15)", "LATE_AFTER = time(9, 16)", "Late threshold moved"),
    ("backend/validators.py", "if age < rules.MIN_AGE:", "if age <= rules.MIN_AGE:", "Off-by-one in age check"),
    ("backend/validators.py", "if check_out <= check_in:", "if check_out < check_in:",
     "Check-out equal to check-in allowed"),
    ("backend/validators.py", "elif start < today:", "elif start <= today:", "Leave starting today rejected"),
    ("backend/validators.py", "if days > remaining:", "if days >= remaining:", "Off-by-one in leave balance"),
    ("backend/services.py", 'if db.execute("SELECT 1 FROM attendance WHERE employee_id = ? AND date = ?",',
     'if False and db.execute("SELECT 1 FROM attendance WHERE employee_id = ? AND date = ?",',
     "Duplicate-attendance check removed"),
    ("backend/services.py", "AND start_date <= ? AND end_date >= ?", "AND start_date < ? AND end_date > ?",
     "Leave overlap check weakened"),
    ("backend/services.py", "if count:", "if False:", "Department-in-use check removed"),
]


def clear_bytecode():
    """Python reuses compiled .pyc files when size and modification second are unchanged - a mutant such as
    90 -> 91 has the same size, so stale bytecode would silently run. Always start from source."""
    for folder in ROOT.rglob("__pycache__"):
        if ".venv" not in folder.parts:
            shutil.rmtree(folder, ignore_errors=True)


def run_tests():
    clear_bytecode()
    command = [sys.executable, "-m", "pytest", "tests/unit", "tests/api", "-x", "-q", "-p", "no:cacheprovider"]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=env).returncode


def main():
    print("Baseline: running tests on the original code ...")
    if run_tests() != 0:
        print("The test suite fails on the original code - fix that first.")
        return 1
    killed = 0
    for number, (file, original, mutated, description) in enumerate(MUTANTS, start=1):
        path = ROOT / file
        source = path.read_text(encoding="utf-8")
        if source.count(original) != 1:
            print(f"  [{number:2}] SKIPPED  {description} (pattern not found exactly once)")
            continue
        try:
            path.write_text(source.replace(original, mutated), encoding="utf-8")
            started = time.time()
            failed = run_tests() != 0
        finally:
            path.write_text(source, encoding="utf-8")
            clear_bytecode()
        killed += failed
        print(f"  [{number:2}] {'KILLED  ' if failed else 'SURVIVED'} {description}  ({time.time() - started:.1f}s)")
    score = killed / len(MUTANTS) * 100
    print(f"\nMutation score: {killed}/{len(MUTANTS)} mutants killed ({score:.0f}%)")
    return 0 if killed == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
