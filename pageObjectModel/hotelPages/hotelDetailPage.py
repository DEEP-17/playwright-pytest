import re
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pageObjectModel.basePage.basePage import BasePage


class HotelDetailPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.book_now_button = page.locator("button").filter(has_text="Book Now").first
        self.sold_out_message = page.get_by_text(
            re.compile(r"We are sold out!|Sorry we are sold out!", re.IGNORECASE)
        )
        self.search_other_hotels_button = page.get_by_role(
            "button", name="Search other Hotels"
        ).first
        self.email_field = page.locator('input[name="email"]')
        self.price_error_message = page.get_by_text(
            "Sorry, There is a problem in checking price!", exact=True
        )
        self.loading_state_message = page.get_by_text("Please wait...", exact=True)
        self.close_dialog_button = page.get_by_role("button", name="×")

    # --- Actions ---
    def has_book_now_button(self) -> bool:
        try:
            self.book_now_button.wait_for(state="visible", timeout=15_000)
        except PlaywrightTimeoutError:
            return False
        return True

    def is_sold_out(self) -> bool:
        return self.sold_out_message.is_visible()

    def search_other_hotels_if_sold_out(self) -> None:
        if self.search_other_hotels_button.is_visible():
            self.search_other_hotels_button.click()
            self.wait_for_network()
            return
        self.page.go_back()
        self.wait_for_network()

    def click_book_now(self) -> bool:
        if not self.has_book_now_button():
            if self.is_sold_out():
                self.log_step("Hotel detail page is sold out; booking is unavailable.")
            else:
                self.log_step("Book Now button was not found on hotel detail page.")
            return False
        self.book_now_button.click()
        try:
            self.email_field.wait_for(state="visible", timeout=45_000)
        except PlaywrightTimeoutError as error:
            if self.price_error_message.is_visible():
                self.log_step("Hotel price check failed; booking is unavailable.")
                self.close_dialog_button.click()
                self.save_current_state("hotel-booking-error-state.json")
                return False
            if self.loading_state_message.is_visible():
                raise RuntimeError(
                    "Hotel price check remained in a loading state for 45 seconds."
                ) from error
            raise RuntimeError(
                "Book Now was accepted, but the hotel guest form did not open "
                "within 45 seconds."
            ) from error
        self.save_current_state("hotel-guest-details-state.json")
        return True
