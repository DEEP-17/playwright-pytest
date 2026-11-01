import re
from typing import Literal

from playwright.sync_api import Locator, Page, expect

from data.objects import FlightData
from pages.base.base_page import BasePage


class FlightSearchPage(BasePage):
    def search_flight(
        self,
        data: FlightData,
        *,
        trip_type: Literal["One way", "Round trip"] = "One way",
        cabin_class: Literal["Economy", "Business class"] = "Economy",
        passenger_counts: tuple[int, int, int] | None = None,
    ) -> None:
        self.log_step("Starting flight search")
        expect(self.page).to_have_url(re.compile(r".*flights/search"))
        self.page.get_by_role("tab", name=trip_type).click()

        self.log_step("Selecting departure airport")
        self._select_airport(
            self.page.get_by_role("textbox", name="Departing from?"),
            data.origin_query,
            data.origin_option,
        )

        self.log_step("Selecting destination airport")
        self._select_airport(
            self.page.get_by_role("textbox", name="Going to?"),
            data.destination_query,
            data.destination_option,
        )

        self.log_step("Selecting departure date")
        if trip_type == "One way":
            self.page.locator("#date").click()
        else:
            self.page.get_by_role(
                "button", name="showing selected date"
            ).click()
        self.select_calendar_date(data.departure_days_from_today)
        if trip_type == "Round trip":
            self.select_calendar_date(data.departure_days_from_today + 2)
            self.page.keyboard.press("Escape")

        self.log_step(f"Selecting {cabin_class} cabin")
        self.page.get_by_role("button", name="Economy", exact=True).click()
        self.page.get_by_role("menuitem", name=cabin_class, exact=True).click()
        expect(
            self.page.get_by_role("button", name=cabin_class, exact=True)
        ).to_be_visible()

        if passenger_counts is not None:
            self.set_passenger_counts(*passenger_counts)

        self.log_step("Submitting flight search")
        self.page.get_by_role("button", name="Search").click()
        self.save_current_state("flight-search-submitted-state.json")
        self.log_step("Flight search submitted")

    def search_multi_city(self, data: FlightData) -> None:
        self.log_step("Starting multi-city flight search")
        expect(self.page).to_have_url(re.compile(r".*flights/search"))
        self.page.get_by_role("tab", name="Multi city").click()

        panel = self.page.get_by_role("tabpanel", name="Multi city")
        origin_fields = panel.get_by_role("textbox", name="Departing from?")
        destination_fields = panel.get_by_role("textbox", name="Going to?")
        self._select_airport(
            origin_fields.nth(0), data.origin_query, data.origin_option
        )
        self._select_airport(
            destination_fields.nth(0),
            data.destination_query,
            data.destination_option,
        )
        self._select_multi_city_date(panel, 0, data.departure_days_from_today)

        panel.get_by_role("button", name="+ Add another flight").click()
        expect(origin_fields.nth(1)).to_have_value(
            re.compile(r"(Toronto.*YYZ|YYZ.*Toronto)", re.IGNORECASE)
        )
        self._select_airport(
            destination_fields.nth(1), data.origin_query, data.origin_option
        )
        self._select_multi_city_date(panel, 1, data.departure_days_from_today + 2)

        expect(origin_fields).to_have_count(2)
        expect(destination_fields).to_have_count(2)
        panel.get_by_role("button", name="Search").click()
        self.save_current_state("flight-multi-city-submitted-state.json")

    def set_passenger_counts(
        self, adults: int, children: int = 0, infants: int = 0
    ) -> None:
        if adults < 1 or children < 0 or infants < 0:
            raise ValueError("Flight searches require at least one adult.")

        self.page.get_by_role("button", name=re.compile(r"\d+ Passenger")).click()
        for passenger_type, expected_count in (
            ("adults", adults),
            ("children", children),
            ("infants", infants),
        ):
            row = self.page.get_by_text(passenger_type, exact=True).locator(
                "xpath=../.."
            )
            count_text = row.locator("div").filter(
                has_text=re.compile(r"^\d+$")
            ).last
            current_count = int(count_text.inner_text())
            while current_count != expected_count:
                button_index = 1 if current_count < expected_count else 0
                row.get_by_role("button").nth(button_index).click()
                count_text = row.locator("div").filter(
                    has_text=re.compile(r"^\d+$")
                ).last
                updated_count = int(count_text.inner_text())
                if updated_count == current_count:
                    raise RuntimeError(
                        f"Could not set the {passenger_type} passenger count."
                    )
                current_count = updated_count

        total_passengers = adults + children + infants
        expect(
            self.page.get_by_role(
                "button",
                name=re.compile(rf"^{total_passengers} Passengers?$"),
            )
        ).to_be_visible()

    def _select_airport(
        self, field: Locator, query: str, option: str
    ) -> None:
        field.fill(query)
        suggestion = self.page.locator("div").filter(
            has_text=re.compile(rf"^{re.escape(option)}$")
        ).first
        suggestion.wait_for(state="visible", timeout=30_000)
        suggestion.click()

    def _select_multi_city_date(
        self, panel: Locator, index: int, days_ahead: int
    ) -> None:
        date_buttons = panel.get_by_role(
            "button", name=re.compile(r"^\d{1,2} [A-Z][a-z]{2} \d{4}$")
        )
        date_buttons.nth(index).click()
        self.select_calendar_date(days_ahead)
