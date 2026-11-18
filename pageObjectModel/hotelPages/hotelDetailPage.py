import re
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from pageObjectModel.basePage.basePage import BasePage

class HotelDetailPage(BasePage):
    def has_book_now_button(self) -> bool:
        button = self.page.locator("button").filter(has_text="Book Now").first
        try:
            button.wait_for(state="visible", timeout=15_000)
        except PlaywrightTimeoutError:
            return False
        return True
    
    def is_sold_out(self) -> bool:
        return self.page.get_by_text(
            re.compile(r"We are sold out!|Sorry we are sold out!", re.IGNORECASE)
        ).is_visible()

    def search_other_hotels_if_sold_out(self) -> None:
        search_other = self.page.get_by_role(
            "button", name="Search other Hotels"
        ).first
        if search_other.is_visible():
            search_other.click()
            self.wait_for_network()
            return
        self.page.go_back()
        self.wait_for_network()

    def click_book_now(self) -> bool:
        book_now = self.page.locator("button").filter(has_text="Book Now").first
        if not book_now.is_visible():
            if self.is_sold_out():
                self.log_step("Hotel detail page is sold out; booking is unavailable.")
            else:
                self.log_step("Book Now button was not found on hotel detail page.")
            return False

        book_now.click()
        email_field = self.page.locator('input[name="email"]')
        price_error = self.page.get_by_text(
            "Sorry, There is a problem in checking price!", exact=True
        )
        try:
            email_field.wait_for(state="visible", timeout=45_000)
        except PlaywrightTimeoutError as error:
            if price_error.is_visible():
                self.log_step("Hotel price check failed; booking is unavailable.")
                self.page.get_by_role("button", name="×").click()
                self.save_current_state("hotel-booking-error-state.json")
                return False

            loading_state = self.page.get_by_text("Please wait...", exact=True)
            if loading_state.is_visible():
                raise RuntimeError(
                    "Hotel price check remained in a loading state for 45 seconds."
                ) from error

            raise RuntimeError(
                "Book Now was accepted, but the hotel guest form did not open "
                "within 45 seconds."
            ) from error

        self.save_current_state("hotel-guest-details-state.json")
        return True