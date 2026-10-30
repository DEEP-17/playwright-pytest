from collections.abc import Mapping
from typing import Any

from playwright.sync_api import Page

from pages.base.base_page import BasePage


class HotelGuestInfoPage(BasePage):
    def fill_info(self, data: Mapping[str, Any], email: str) -> None:
        guest = data["guest"]
        self.page.get_by_role("textbox", name="Ex. John").fill(guest["firstName"])
        self.page.get_by_role("textbox", name="Ex. Smith").fill(guest["lastName"])
        self.page.get_by_role("textbox", name="Ex. 35").fill(guest["age"])
        self.page.get_by_role("combobox").filter(
            has_text="Select your gender"
        ).click()
        self.page.get_by_role("option", name="Male", exact=True).click()
        self.page.locator('input[name="adress"]').fill("123 Main St, Anytown, USA")
        self.page.locator('input[name="zipcode"]').fill("382531")
        self.page.locator('input[name="city"]').fill("Anytown")
        self.page.locator('input[name="email"]').fill(email)
        self.page.locator('input[name="phone"]').fill("9512345678")
