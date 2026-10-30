from collections.abc import Mapping
from typing import Any

from playwright.sync_api import Page

from pages.base.base_page import BasePage


class FlightTravellerInfoPage(BasePage):
    def fill_info(self, data: Mapping[str, Any], email: str) -> None:
        self.page.get_by_text("Passenger Detail #4INFANT(").wait_for(state="visible")

        passenger_count = self.page.locator('input[name^="firstName"]').count()
        for index in range(1, passenger_count + 1):
            first_name = self.page.locator(f'input[name="firstName{index}"]')
            if not first_name.is_visible():
                break
            passenger = data["passenger"]
            first_name.fill(passenger["firstName"])
            self.page.locator(f'input[name="middleName{index}"]').fill(
                passenger["middleName"]
            )
            self.page.locator(f'input[name="lastName{index}"]').fill(
                passenger["lastName"]
            )
            self.page.locator(f'input[name="DOB{index}"]').fill(passenger["dob"])
            self.page.get_by_role("combobox").nth(index * 2 - 1).click()
            self.page.get_by_role("option", name="Male", exact=True).click()

        contact = data["contact"]
        self.page.locator('input[name="adress"]').fill(contact["address"])
        self.page.locator('input[name="zipcode"]').fill(contact["zip"])
        self.page.locator('input[name="city"]').fill(contact["city"])
        self.page.locator('input[name="email"]').fill(email)
        self.page.locator('input[name="phone"]').fill(contact["phone"])
