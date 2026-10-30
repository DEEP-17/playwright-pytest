from collections.abc import Mapping
from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage


class TripSearchPage(BasePage):
    def _select_location(self, search_label: str, query: str, selection: str) -> None:
        textbox = self.page.get_by_placeholder(search_label, exact=True)
        textbox.click()
        textbox.fill(query)
        self.page.wait_for_timeout(1_000)

        option = self.page.get_by_text(selection, exact=True)
        try:
            option.wait_for(state="visible", timeout=2_000)
        except PlaywrightTimeoutError as error:
            raise RuntimeError(f"Location was not found: {selection}") from error

        try:
            option.click(timeout=3_000)
        except PlaywrightTimeoutError as error:
            raise RuntimeError(f"Cannot select location: {selection}") from error

    def search_and_plan(self, data: Mapping[str, Any]) -> Page:
        self._select_location(
            "Where are you from?", data["fromSearch"], data["fromSelect"]
        )
        self._select_location(
            "Where you want to go?", data["toSearch"], data["toSelect"]
        )
        self.page.get_by_role("button", name="showing selected date").click()
        start_days = data.get("startDaysFromToday", 15)
        trip_length = data.get("tripLengthDays", 1)
        self.select_calendar_date(start_days)
        self.select_calendar_date(start_days + trip_length)

        with self.page.expect_popup(timeout=10_000) as popup:
            self.page.get_by_role("button", name="Start Planning").click()
        return popup.value
