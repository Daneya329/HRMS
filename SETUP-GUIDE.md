# HRMS – Setup Guide (Windows)

Step-by-step instructions to get the project running on a Windows 10/11 computer.
Takes about 10 minutes. You need **Python** and **Google Chrome**; there is **no database to install**.

Run each command on its own and check the result before moving on.
If something goes wrong, see [Common problems](#common-problems) at the end.

---

## Step 1 – Install Python

1. Download **Python 3.13** (or 3.12) from https://www.python.org/downloads/windows/
   → *Windows installer (64-bit)*.
2. Start the installer. On the first screen **tick "Add python.exe to PATH"** at the bottom,
   then click **Install Now**.
3. Open a **new** PowerShell window and check:

```powershell
py --version
```

You should see `Python 3.13.x` (any version 3.10 or newer works).

> Already have Python? Run `py --version`. If it shows 3.10 or newer, you can skip this step.

## Step 2 – Install Google Chrome

Only needed for the Selenium browser tests: https://www.google.com/chrome/

## Step 3 – Unzip the project and open PowerShell there

1. Right-click the zip file → **Extract All…** → e.g. `C:\Projects` → **Extract**.
2. Open the extracted folder until you see **`app.py`**, **`requirements.txt`**, `backend` and `frontend`.
3. Click the File Explorer address bar, type `powershell`, press **Enter**.

Check that you are in the right folder:

```powershell
dir app.py
```

It must list `app.py`. All following commands are run from this folder.

## Step 4 – Create a virtual environment (once)

A virtual environment keeps this project's packages separate from the rest of your computer.

```powershell
py -m venv .venv
```

```powershell
.venv\Scripts\activate
```

Your prompt now starts with **`(.venv)`**.

> **Error "running scripts is disabled on this system"?** Run this once, answer **Y**, then activate again:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

## Step 5 – Install the packages (once)

```powershell
pip install -r requirements.txt
```

Wait until it says `Successfully installed …`.

## Step 6 – Start the application

```powershell
python app.py
```

You will see:

```
  HRMS is running:  http://127.0.0.1:8000
  Default login:    admin@hrms.local / Admin@123
```

Keep this window open: closing it stops the app. To stop it, press **Ctrl + C**.

## Step 7 – Use it

Open **http://127.0.0.1:8000** in Chrome and sign in:

* Email: **admin@hrms.local**
* Password: **Admin@123**

Want a full dashboard for a demo? Stop the app (Ctrl + C), then run:

```powershell
python seed_demo.py
```

```powershell
python app.py
```

This adds 12 employees with 10 days of attendance and some leave requests.

Try the rules:

1. Go to **Employees → Add employee**.
2. Enter a date of birth that makes the person 17 on the hire date, or a Full-time salary of 39,999.
3. The form refuses it and explains why. The *Settings & Rules* page lists every rule.

## Step 8 – Run the tests

Open a **second** PowerShell window in the project folder (or stop the app first), then activate the
environment again:

```powershell
.venv\Scripts\activate
```

Run everything (code style, all 348 tests, coverage check and HTML reports):

```powershell
python run_quality_checks.py
```

Chrome opens and closes by itself many times during the Selenium tests. Don't click in it.
At the end you should see:

```
  PASS  Code style (flake8)
  PASS  Tests and coverage
```

Open the reports:

```powershell
start reports\test-report.html
```

```powershell
start reports\coverage\index.html
```

The first shows every test with its result; the second shows which lines of code the tests ran.

Other useful commands:

| What | Command |
|---|---|
| Without the browser tests (fast) | `python run_quality_checks.py --fast` |
| Unit tests only | `pytest tests/unit` |
| API tests only | `pytest tests/api` |
| Selenium tests only | `pytest tests/selenium` |
| Selenium without a visible window | `$env:HRMS_HEADLESS = "1"; pytest tests/selenium` |
| Mutation testing | `python quality/mutation_check.py` |

## Every time you come back later

```powershell
cd C:\Projects\hrms-python
```

```powershell
.venv\Scripts\activate
```

```powershell
python app.py
```

(Use your own project path in the first command.)

---

## Common problems

| Message | Fix |
|---|---|
| `py` / `python` is not recognized | Python is not installed or not on PATH. Reinstall it and tick **"Add python.exe to PATH"**, then open a new PowerShell window. |
| `running scripts is disabled on this system` | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`, answer **Y**. |
| `No module named flask` (or pytest, selenium) | The environment is not active (no `(.venv)` in the prompt). Run `.venv\Scripts\activate`, then `pip install -r requirements.txt`. |
| `ERROR: Could not open requirements file` | You are in the wrong folder. `cd` into the folder that contains `requirements.txt`. |
| Port 8000 already in use | Another copy is running. Close it, or start on another port: `$env:PORT = "8001"; python app.py` and open http://127.0.0.1:8001 |
| "Invalid email or password" | Use **admin@hrms.local / Admin@123**. If you changed the password and forgot it, stop the app and delete `hrms.db` (this deletes all data). |
| Account locked | Wait 5 minutes (5 wrong passwords lock the account), or restart with a fresh `hrms.db`. |
| Selenium: `SessionNotCreatedException` / driver errors | Update Chrome to the latest version and make sure you are online for the first browser test run. |
| Selenium tests fail only on a slow computer | Run them headless: `$env:HRMS_HEADLESS = "1"; pytest tests/selenium` |
| Want to start with empty data | Stop the app and delete the file `hrms.db` in the project folder. |

When asking for help, send the output of `py --version`, `pip list`, and the error text.

## macOS / Linux

Same steps with these commands: `python3 -m venv .venv`, `source .venv/bin/activate`,
`pip install -r requirements.txt`, `python app.py`, `python run_quality_checks.py`,
headless browser tests: `HRMS_HEADLESS=1 pytest tests/selenium`.
