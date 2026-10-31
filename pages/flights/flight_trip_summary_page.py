from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage


class FlightTripSummaryPage(BasePage):
    def proceed(self) -> None:
        self.log_step("Waiting for trip summary")
        self.wait_for_dom()
        continue_button = self.page.get_by_role(
            "button", name="Continue to Checkout", exact=False
        )
        try:
            continue_button.wait_for(state="visible", timeout=20_000)
        except PlaywrightTimeoutError:
            self.log_step("Checkout button is not ready; reloading trip summary once")
            self.page.reload(wait_until="domcontentloaded")
            try:
                continue_button.wait_for(state="visible", timeout=20_000)
            except PlaywrightTimeoutError as error:
                raise RuntimeError(
                    f"Continue to Checkout button did not load at {self.page.url}"
                ) from error

        self.log_step("Continuing to checkout")
        continue_button.click()
        click_here_link = self.page.locator('u:has-text("Click here")')
        try:
            click_here_link.wait_for(state="visible", timeout=2_000)
        except PlaywrightTimeoutError:
            pass
        else:
            self.log_step("Opening the seat-selection step")
            click_here_link.click()

        self.wait_for_dom()
        self.log_step("Checkout step opened")
        self.save_current_state("flight-checkout-state.json")
