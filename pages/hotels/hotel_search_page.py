import re

from playwright.sync_api import Locator, Page, expect

from data.objects import HotelData
from pages.base.base_page import BasePage


class HotelSearchPage(BasePage):
    def search(
        self,
        data: HotelData,
        *,
        rooms: int = 1,
        additional_adults: int = 1,
        children: int = 1,
    ) -> None:
        if rooms < 1 or additional_adults < 0 or children < 0:
            raise ValueError("Hotel searches require at least one room.")

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

        guest_control = self.page.get_by_role(
            "button", name=re.compile(r"\d+ Room")
        )
        guest_control.click()
        for _ in range(rooms - 1):
            self.page.get_by_role("button", name="Increase rooms").click()
        for _ in range(additional_adults):
            self.page.get_by_role("button", name="Increase adults").first.click()
        for _ in range(children):
            self.page.get_by_role("button", name="Increase children").first.click()
        expected_guests = rooms + additional_adults + children
        expected_summary = re.compile(
            rf"{rooms} Rooms?, {expected_guests} Guests?"
        )
        expect(guest_control).to_contain_text(expected_summary)
        guest_control.click()

        self.page.get_by_role("button", name="Search").click()
        self.save_current_state("hotel-search-submitted-state.json")
