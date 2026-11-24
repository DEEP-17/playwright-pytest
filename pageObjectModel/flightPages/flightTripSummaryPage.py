from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pageObjectModel.basePage.basePage import BasePage
from pageObjectModel.flightPages.flightListingPage import FlightListingPage


class FlightTripSummaryPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.continue_button = page.get_by_role(
            "button", name="Continue to Checkout", exact=False
        )
        self.expired_hold_message = page.get_by_text(
            "Your ticket hold has expired. Please select your flight again.",
            exact=True,
        )
        self.go_back_button = page.get_by_role("button", name="Go back", exact=True)
        self.click_here_link = page.locator('u:has-text("Click here")')

    # --- Actions ---
    def proceed(self) -> None:
        self.log_step("Waiting for trip summary")
        self.wait_for_dom()
        try:
            self.continue_button.wait_for(state="visible", timeout=20_000)
        except PlaywrightTimeoutError:
            if self.expired_hold_message.is_visible():
                self.log_step("Ticket hold expired; selecting a fresh flight")
                self.go_back_button.click()
                listing_page = FlightListingPage(self.page)
                if not listing_page.wait_for_results():
                    raise RuntimeError(
                        "The ticket hold expired and flight results did not reload."
                    )
                listing_page.select_first_result()
                try:
                    self.continue_button.wait_for(state="visible", timeout=20_000)
                except PlaywrightTimeoutError as error:
                    raise RuntimeError(
                        f"Continue to Checkout button did not load after "
                        f"reselecting a flight at {self.page.url}"
                    ) from error
            else:
                self.log_step("Trip summary is still loading; waiting for checkout")
                try:
                    self.continue_button.wait_for(state="visible", timeout=40_000)
                except PlaywrightTimeoutError as error:
                    raise RuntimeError(
                        "Continue to Checkout button did not load after "
                        f"60 seconds at {self.page.url}"
                    ) from error
        self.log_step("Continuing to checkout")
        self.continue_button.click()
        try:
            self.click_here_link.wait_for(state="visible", timeout=2_000)
        except PlaywrightTimeoutError:
            pass
        else:
            self.log_step("Opening the seat-selection step")
            self.click_here_link.click()
        self.wait_for_dom()
        self.log_step("Checkout step opened")
        self.save_current_state("flight-checkout-state.json")
