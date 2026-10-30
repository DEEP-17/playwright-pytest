import re
from collections.abc import Mapping
from typing import Any

from playwright.sync_api import Page, expect

from pages.base.base_page import BasePage


class FlightSearchPage(BasePage):
    def search_flight(self, data: Mapping[str, Any]) -> None:
        self.log_step("Starting flight search")
        expect(self.page).to_have_url(re.compile(r".*flights/search"))
        self.page.get_by_role("tab", name="One way").click()

        self.log_step("Selecting departure airport")
        self.page.get_by_role("textbox", name="Departing from?").fill(data["fromSearch"])
        self.page.locator("div").filter(
            has_text=re.compile(rf"^{re.escape(data['fromSelect'])}$")
        ).first.click()

        self.log_step("Selecting destination airport")
        self.page.get_by_role("textbox", name="Going to?").fill(data["" \
        "toSearch"])
        self.page.locator("div").filter(
            has_text=re.compile(rf"^{re.escape(data['toSelect'])}$")
        ).first.click()

        self.log_step("Selecting departure date")
        self.page.locator("#date").click()
        self.select_calendar_date(data.get("departureDaysFromToday", 15))

        self.log_step("Selecting cabin class and passengers")
        self.page.get_by_role("button", name="Economy").click()
        self.page.get_by_role("menuitem", name="Business class").click()
        self.page.get_by_role("button", name="Passenger").click()
        for passenger_type in ("adults", "children", "infants"):
            passenger_row = self.page.get_by_text(
                passenger_type, exact=True
            ).locator("xpath=../..")
            passenger_row.get_by_role("button").nth(1).click()

        self.log_step("Submitting flight search")
        self.page.get_by_role("button", name="Search").click()
        self.log_step("Flight search submitted")
