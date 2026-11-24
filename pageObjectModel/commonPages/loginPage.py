import re
from playwright.sync_api import Page, expect
from pageObjectModel.basePage.basePage import BasePage


class LoginPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.sign_in_link = page.get_by_role("link", name="Sign in or join using your")
        self.email_field = page.get_by_role("textbox", name="Email")
        self.password_field = page.get_by_role("textbox", name="Password")
        self.remember_me_checkbox = page.get_by_role("checkbox", name="Remember me")
        self.sign_in_button = page.get_by_role("button", name="Sign In")

    # --- Actions ---
    def login(self, email: str, password: str) -> None:
        self.log_step("Opening the application")
        self.page.goto("/", wait_until="domcontentloaded")
        self.log_step("Opening the login page")
        self.sign_in_link.click()
        expect(self.page).to_have_url(re.compile(r".*/login(?:[?#].*)?$"))
        self.log_step("Entering login credentials")
        self.email_field.fill(email)
        self.password_field.fill(password)
        self.remember_me_checkbox.check()
        self.log_step("Submitting login")
        self.sign_in_button.click()
        expect(self.page).not_to_have_url(
            re.compile(r".*/login(?:[?#].*)?$"), timeout=15_000
        )
        self.save_current_state("authenticated-state.json")
        self.log_step("Login completed")
