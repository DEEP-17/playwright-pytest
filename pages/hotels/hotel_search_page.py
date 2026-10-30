import re
from collections.abc import Mapping
from typing import Any

from playwright.sync_api import Page, expect

from pages.base.base_page import BasePage


class HotelSearchPage(BasePage):
    def search(self, data: Mapping[str, Any]) -> None:
        expect(self.page).to_have_url(re.compile(r".*hotel/search"))
        self.page.get_by_role(
            "textbox", name="What hotel you looking for?"
        ).fill(data["location"])
        self.page.wait_for_timeout(2_000)
        self.page.locator("div").filter(
            has_text=re.compile(rf"^{re.escape(data['locationSelect'])}$")
        ).first.click()

        self.page.get_by_role("button", name="showing selected date").click()
        check_in = data.get("checkInDaysFromToday", 15)
        stay_length = data.get("stayLengthDays", 1)
        self.select_calendar_date(check_in)
        self.select_calendar_date(check_in + stay_length)
        self.page.keyboard.press("Escape")

        self.page.get_by_role("button", name="Room, 1 Guest").click()
        self.page.get_by_role("button", name="Increase adults").click()
        self.page.get_by_role("button", name="Increase children").click()
        self.page.get_by_role("button", name="Search").click()
