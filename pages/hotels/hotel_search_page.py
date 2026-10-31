import re

from playwright.sync_api import Page, expect

from data.objects import HotelData
from pages.base.base_page import BasePage


class HotelSearchPage(BasePage):
    def search(self, data: HotelData) -> None:
        expect(self.page).to_have_url(re.compile(r".*hotel/search"))
        self.page.get_by_role(
            "textbox", name="What hotel you looking for?"
        ).fill(data.location_query)
        self.page.wait_for_timeout(2_000)
        self.page.locator("div").filter(
            has_text=re.compile(rf"^{re.escape(data.location_option)}$")
        ).first.click()

        self.page.get_by_role("button", name="showing selected date").click()
        check_in = data.check_in_days_from_today
        stay_length = data.stay_length_days
        self.select_calendar_date(check_in)
        self.select_calendar_date(check_in + stay_length)
        self.page.keyboard.press("Escape")

        self.page.get_by_role("button", name="Room, 1 Guest").click()
        self.page.get_by_role("button", name="Increase adults").click()
        self.page.get_by_role("button", name="Increase children").click()
        self.page.get_by_role("button", name="Search").click()
        self.save_current_state("hotel-search-submitted-state.json")
