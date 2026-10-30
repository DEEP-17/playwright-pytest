from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage
from pages.hotels.hotel_detail_page import HotelDetailPage


class HotelListingPage(BasePage):
    def open_hotel_detail(self) -> Page:
        self.wait_for_network()
        select_button = self.page.locator("button").filter(has_text="Select").first
        select_button.wait_for(state="visible", timeout=60_000)

        hotel_page = None
        try:
            with self.page.expect_popup(timeout=20_000) as popup:
                select_button.click()
            hotel_page = popup.value
        except PlaywrightTimeoutError:
            self.page.wait_for_load_state("domcontentloaded")
            hotel_page = self.page

        hotel_page.wait_for_load_state("domcontentloaded")
        hotel_page.wait_for_load_state("networkidle")
        if not HotelDetailPage(hotel_page).has_book_now_button():
            raise RuntimeError(
                "Hotel detail page loaded, but no Book Now button was found."
            )
        return hotel_page
