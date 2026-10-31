from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from data.objects import TripData
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

    def search_and_plan(self, data: TripData) -> Page:
        self._select_location(
            "Where are you from?", data.origin_query, data.origin_option
        )
        self._select_location(
            "Where you want to go?",
            data.destination_query,
            data.destination_option,
        )
        self.page.get_by_role("button", name="showing selected date").click()
        start_days = data.start_days_from_today
        trip_length = data.trip_length_days
        self.select_calendar_date(start_days)
        self.select_calendar_date(start_days + trip_length)

        with self.page.expect_popup(timeout=10_000) as popup:
            self.page.get_by_role("button", name="Start Planning").click()
        planner_page = popup.value
        self.save_current_state("trip-planning-search-state.json")
        return planner_page
