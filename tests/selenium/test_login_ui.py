"""E2E: sign in, sign out and protected pages."""
import pytest

from tests.selenium.pages import DashboardPage, EmployeesPage, LoginPage

pytestmark = pytest.mark.selenium


def test_valid_login_opens_dashboard(driver, live_server):
    LoginPage(driver, live_server).open().login("admin@hrms.local", "Admin@123")
    page = DashboardPage(driver, live_server).wait_url("/dashboard").wait_ready()
    assert page.text("#pageTitle") == "Dashboard"
    assert "Welcome back, HR Administrator" in page.text("#welcome")


def test_wrong_password_shows_error(driver, live_server):
    page = LoginPage(driver, live_server).open().login("admin@hrms.local", "wrong-password")
    assert page.error() == "Invalid email or password"
    assert "/login" in driver.current_url


def test_empty_form_is_validated_in_the_browser(driver, live_server):
    page = LoginPage(driver, live_server).open()
    page.click("#loginBtn")
    assert page.field_error("email") == "Email is required"
    assert page.field_error("password") == "Password is required"


def test_protected_page_redirects_to_login(driver, live_server):
    driver.get(live_server + "/employees")
    LoginPage(driver, live_server).wait_url("/login")


def test_logout(admin, live_server):
    page = EmployeesPage(admin, live_server).open()
    page.logout()
    admin.get(live_server + "/dashboard")
    LoginPage(admin, live_server).wait_url("/login")
