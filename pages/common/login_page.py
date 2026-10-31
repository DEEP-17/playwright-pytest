import re

from playwright.sync_api import Page, expect

from pages.base.base_page import BasePage


class LoginPage(BasePage):
    def login(self, email: str, password: str) -> None:
        self.log_step("Opening the application")
        self.page.goto("/", wait_until="domcontentloaded")
        self.log_step("Opening the login page")
        self.page.get_by_role("link", name="Sign in or join using your").click()
        expect(self.page).to_have_url(re.compile(r".*/login(?:[?#].*)?$"))
        self.log_step("Entering login credentials")
        self.page.get_by_role("textbox", name="Email").fill(email)
        self.page.get_by_role("textbox", name="Password").fill(password)
        self.page.get_by_role("checkbox", name="Remember me").check()
        self.log_step("Submitting login")
        self.page.get_by_role("button", name="Sign In").click()
        self.wait_for_network()
        expect(self.page).not_to_have_url(
            re.compile(r".*/login(?:[?#].*)?$"), timeout=15_000
        )
        self.save_current_state("authenticated-state.json")
        self.log_step("Login completed")
 