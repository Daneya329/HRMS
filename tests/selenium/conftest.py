"""
Selenium fixtures.

* ``live_server`` - starts the real application in a background thread on a free port,
  using a temporary database (your real hrms.db is never touched).
* ``driver``      - Google Chrome. Selenium Manager downloads the matching ChromeDriver
  automatically. Set HRMS_HEADLESS=1 to hide the browser window.
  Optional: CHROME_BINARY / CHROMEDRIVER_PATH to use specific executables.
* ``api``         - a signed-in API client on the same database, used to prepare test data quickly.
* On failure a screenshot is saved to reports/screenshots/ and attached to the HTML report.
"""
import logging
import os
import threading
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from werkzeug.serving import make_server

from backend.app import create_app
from tests.selenium.pages import LoginPage

SCREENSHOTS = Path(__file__).resolve().parents[2] / "reports" / "screenshots"


@pytest.fixture(scope="session")
def live_app(tmp_path_factory):
    db = tmp_path_factory.mktemp("selenium") / "selenium.db"
    return create_app({"DATABASE": str(db), "TESTING": True, "SECRET_KEY": "selenium-secret"})


@pytest.fixture(scope="session")
def live_server(live_app):
    logging.getLogger("werkzeug").setLevel(logging.ERROR)     # keep the test output readable
    server = make_server("127.0.0.1", 0, live_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def api(live_app):
    client = live_app.test_client()
    assert client.post("/api/login", json={"email": "admin@hrms.local", "password": "Admin@123"}).status_code == 200
    return client


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    if os.environ.get("HRMS_HEADLESS", "").lower() in ("1", "true", "yes"):
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-search-engine-choice-screen")
    if os.environ.get("CHROME_BINARY"):
        options.binary_location = os.environ["CHROME_BINARY"]
        options.add_argument("--no-sandbox")
    service = Service(executable_path=os.environ["CHROMEDRIVER_PATH"]) if os.environ.get("CHROMEDRIVER_PATH") else None
    browser = webdriver.Chrome(options=options, service=service)
    browser.implicitly_wait(0)
    yield browser
    browser.quit()


@pytest.fixture
def admin(driver, live_server):
    """Browser already signed in as the administrator, showing the dashboard."""
    LoginPage(driver, live_server).open().login("admin@hrms.local", "Admin@123")
    LoginPage(driver, live_server).wait_url("/dashboard")
    return driver


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed and "driver" in item.funcargs:
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOTS / f"{item.name}.png"
        try:
            item.funcargs["driver"].save_screenshot(str(path))
            html_plugin = item.config.pluginmanager.getplugin("html")
            if html_plugin is not None:
                extras = getattr(report, "extras", [])
                extras.append(html_plugin.extras.png(item.funcargs["driver"].get_screenshot_as_base64()))
                report.extras = extras
        except Exception:  # noqa: BLE001 - never hide the real failure
            pass
