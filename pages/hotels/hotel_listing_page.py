from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage
from pages.hotels.hotel_detail_page import HotelDetailPage


class HotelListingPage(BasePage):
    def open_hotel_detail(self) -> Page:
        select_button = self.page.locator("button").filter(has_text="Select").first
        select_button.wait_for(state="visible", timeout=60_000)
        self.save_current_state("hotel-results-state.json")

        hotel_page = None
        try:
            with self.page.expect_popup(timeout=20_000) as popup:
                select_button.click()
            hotel_page = popup.value
        except PlaywrightTimeoutError:
            self.page.wait_for_load_state("domcontentloaded")
            hotel_page = self.page

        hotel_page.wait_for_load_state("domcontentloaded")
        detail = HotelDetailPage(hotel_page)
        if (
            not detail.has_book_now_button()
            and not detail.is_sold_out()
        ):
            raise RuntimeError(
                "Hotel detail page loaded without a Book Now button or sold-out state."
            )
        detail.save_current_state("hotel-detail-state.json")
        return hotel_page
