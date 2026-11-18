"""E2E: dashboard figures and the settings / business-rules page."""
import pytest

from tests.factories import employee_data
from tests.selenium.pages import DashboardPage, BasePage

pytestmark = pytest.mark.selenium


def test_dashboard_counts_follow_the_data(admin, live_server, api):
    before = DashboardPage(admin, live_server).open().stat("statTotal")
    api.post("/api/employees", json=employee_data(first_name="Counted"))
    page = DashboardPage(admin, live_server).open()
    assert page.stat("statTotal") == before + 1


def test_navigation_menu(admin, live_server):
    page = DashboardPage(admin, live_server).open()
    for key, title in [("employees", "Employees"), ("departments", "Departments"), ("attendance", "Attendance"),
                       ("leaves", "Leave Management"), ("settings", "Settings & Rules")]:
        page.click(f"#nav-{key}")
        page.wait_url(f"/{key}")
        page.wait.until(lambda d: d.find_element("id", "pageTitle").text == title)


class SettingsPage(BasePage):
    path = "/settings"


def test_business_rules_are_listed(admin, live_server):
    page = SettingsPage(admin, live_server).open()
    page.wait.until(lambda d: "Minimum wage" in page.text("#rulesTable"))
    rules = page.text("#rulesTable")
    assert "18 to 60 years" in rules
    assert "PKR 40,000 / month" in rules
    assert "01 Jan 2010" in rules


def test_password_change_validation(admin, live_server):
    page = SettingsPage(admin, live_server).open()
    page.type("#current_password", "Admin@123")
    page.type("#new_password", "short")
    page.type("#confirm_password", "different")
    page.click("#changePasswordBtn")
    assert page.field_error("new_password") == "New password must be at least 8 characters"
    assert page.field_error("confirm_password") == "Passwords do not match"


def test_unknown_page_shows_404(driver, live_server):
    driver.get(live_server + "/no-such-page")
    assert BasePage(driver, live_server).text("#errorCode") == "404"
