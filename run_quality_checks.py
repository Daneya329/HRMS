"""
One command for every quality check of the project.

    python run_quality_checks.py           # everything (needs Google Chrome)
    python run_quality_checks.py --fast    # skip the Selenium browser tests
    python run_quality_checks.py --mutation  # also run mutation testing (slower)

Reports are written to the "reports" folder:
    reports/test-report.html   - every test with pass/fail (open in a browser)
    reports/coverage/index.html - code coverage per line
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COVERAGE_MINIMUM = 90


def step(title, command):
    print(f"\n{'=' * 70}\n  {title}\n{'=' * 70}", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    print(f"  -> {'PASSED' if result.returncode == 0 else 'FAILED'}", flush=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fast", action="store_true", help="skip Selenium browser tests")
    parser.add_argument("--mutation", action="store_true", help="also run mutation testing")
    args = parser.parse_args()

    py = sys.executable
    results = {"Code style (flake8)": step("1. Static code analysis (flake8)", [py, "-m", "flake8"])}

    pytest = [py, "-m", "pytest", "--cov=backend", "--cov-report=term", "--cov-report=html:reports/coverage",
              f"--cov-fail-under={COVERAGE_MINIMUM}", "--html=reports/test-report.html", "--self-contained-html"]
    if args.fast:
        pytest += ["-m", "not selenium"]
    title = "2. Unit + API tests" + ("" if args.fast else " + Selenium browser tests") + \
            f" (coverage must be >= {COVERAGE_MINIMUM}%)"
    results["Tests and coverage"] = step(title, pytest)

    if args.mutation:
        results["Mutation testing"] = step("3. Mutation testing", [py, "quality/mutation_check.py"])

    print(f"\n{'=' * 70}\n  SUMMARY\n{'=' * 70}")
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("\n  Test report:     reports/test-report.html\n  Coverage report: reports/coverage/index.html\n")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
