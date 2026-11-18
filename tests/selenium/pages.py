"""Page Object Model: one class per screen, so tests read like user stories."""
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

TIMEOUT = 10


class BasePage:
    path = "/"

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url
        # pages re-render tables after saving, so references can go stale: just look again
        self.wait = WebDriverWait(driver, TIMEOUT, ignored_exceptions=[StaleElementReferenceException])

    # ---------------------------------------------------------------- navigation
    def open(self, query=""):
        self.driver.get(self.base_url + self.path + query)
        self.wait_ready()
        return self

    def wait_ready(self):
        """Protected pages are hidden until the login check has finished."""
        if self.path not in ("/", "/login"):
            self.wait.until(EC.visibility_of_element_located((By.ID, "content")))
        return self

    def wait_url(self, fragment):
        self.wait.until(EC.url_contains(fragment))
        return self

    # ---------------------------------------------------------------- elements
    def find(self, css):
        return self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css)))

    def find_all(self, css):
        return self.driver.find_elements(By.CSS_SELECTOR, css)

    def click(self, css):
        for attempt in range(3):
            try:
                element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                element.click()
                return
            except StaleElementReferenceException:
                if attempt == 2:
                    raise

    def type(self, css, text):
        element = self.find(css)
        element.clear()
        element.send_keys(str(text))

    def set_value(self, css, value):
        """Date/time inputs: set the value independently of the browser's locale."""
        element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        self.driver.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", element, value)

    def select(self, css, visible_text):
        def choose(_driver):
            select = Select(self.find(css))
            if not any(o.text == visible_text for o in select.options):
                return False
            select.select_by_visible_text(visible_text)
            return True
        self.wait.until(choose)

    def text(self, css):
        return self.find(css).text

    def field_error(self, field):
        return self.wait.until(
            lambda d: d.find_element(By.CSS_SELECTOR, f'[data-error-for="{field}"]').text or False)

    def no_field_error(self, field):
        return self.driver.find_element(By.CSS_SELECTOR, f'[data-error-for="{field}"]').text == ""

    def toast(self, contains):
        """Waits for a toast notification containing the given text and returns its text."""
        return self.wait.until(lambda d: next((t.text for t in d.find_elements(By.CSS_SELECTOR, ".toast")
                                               if contains in t.text), False))

    def logout(self):
        self.click("#topLogoutBtn")
        self.wait_url("/login")


class LoginPage(BasePage):
    path = "/login"

    def login(self, email, password):
        self.type("#email", email)
        self.type("#password", password)
        self.click("#loginBtn")
        return self

    def error(self):
        return self.wait.until(lambda d: d.find_element(By.ID, "loginError").text or False)


class DashboardPage(BasePage):
    path = "/dashboard"

    def stat(self, element_id):
        self.wait.until(lambda d: d.find_element(By.ID, "heroLine").text != "Loading…")
        return int(self.text(f"#{element_id}"))


class EmployeesPage(BasePage):
    path = "/employees"

    def row(self, code):
        return self.find(f'tr[data-code="{code}"]')

    def codes(self):
        return [r.get_attribute("data-code") for r in self.find_all("#employeeTable tbody tr[data-code]")]

    def search(self, text):
        self.type("#search", text)
        self.wait.until(lambda d: d.find_element(By.ID, "resultCount").text.endswith("employee(s)"))
        self.wait.until(lambda d: all(text.lower() in r.text.lower() for r in self.find_all("tr[data-code]"))
                        or self.find_all("#noResults"))

    def delete(self, code):
        self.click(f'tr[data-code="{code}"] button.delete')
        self.click("#confirmOk")


class EmployeeFormPage(BasePage):
    path = "/employee-form"

    def open(self, query=""):
        super().open(query)
        self.wait.until(lambda d: len(Select(d.find_element(By.ID, "department_id")).options) > 1)
        if "id=" in query:
            self.wait.until(lambda d: d.find_element(By.ID, "first_name").get_attribute("value"))
        return self

    def fill(self, data):
        for field in ("first_name", "last_name", "email", "phone", "cnic", "designation"):
            if field in data:
                self.type(f"#{field}", data[field])
        if "salary" in data:
            self.type("#salary", data["salary"])
        for field in ("date_of_birth", "hire_date"):
            if field in data:
                self.set_value(f"#{field}", data[field])
        for field in ("gender", "employment_type", "status"):
            if field in data:
                self.select(f"#{field}", data[field])
        if "department" in data:
            self.select("#department_id", data["department"])
        return self

    def save(self):
        self.click("#saveBtn")
        return self


class DepartmentsPage(BasePage):
    path = "/departments"

    def create(self, name, description=""):
        self.type("#deptName", name)
        self.type("#deptDescription", description)
        self.click("#addDeptBtn")

    def row(self, name):
        return self.find(f'tr[data-name="{name}"]')


class AttendancePage(BasePage):
    path = "/attendance"

    def open(self, query=""):
        super().open(query)
        self.wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, "#attendanceTable tbody tr"))
        return self

    def mark_row(self, code, status, check_in="", check_out=""):
        row = f'tr[data-code="{code}"]'
        self.select(f"{row} .row-status", status)
        self.set_value(f"{row} .row-in", check_in)
        self.set_value(f"{row} .row-out", check_out)
        self.click(f"{row} .row-save")

    def saved_status(self, code, expected):
        return self.wait.until(
            lambda d: d.find_element(By.CSS_SELECTOR, f'tr[data-code="{code}"] .saved').text == expected)

    def row_error(self, code):
        return self.wait.until(
            lambda d: d.find_element(By.CSS_SELECTOR, f'tr[data-code="{code}"] .row-error').text or False)


class LeavesPage(BasePage):
    path = "/leaves"

    def open(self, query=""):
        super().open(query)
        self.wait.until(lambda d: len(Select(d.find_element(By.ID, "leaveEmployee")).options) > 1)
        return self

    def apply(self, employee_label, leave_type, start, end, reason):
        self.select("#leaveEmployee", employee_label)
        self.select("#leaveType", leave_type)
        self.set_value("#startDate", start)
        self.set_value("#endDate", end)
        self.type("#reason", reason)
        self.click("#applyBtn")

    def status_of(self, employee_name):
        return self.find(f'tr[data-employee="{employee_name}"] .leave-status').text
