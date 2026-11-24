import re
from playwright.sync_api import Page, expect
from testData.testDataObjects import HotelData
from pageObjectModel.basePage.basePage import BasePage


class HotelSearchPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.location_search_field = page.get_by_role(
            "textbox", name="What hotel you looking for?"
        )
        self.date_picker_button = page.get_by_role("button", name="showing selected date")
        self.guest_control_button = page.get_by_role(
            "button", name=re.compile(r"\d+ Room")
        )
        self.increase_rooms_button = page.get_by_role("button", name="Increase rooms")
        self.increase_adults_button = page.get_by_role(
            "button", name="Increase adults"
        ).first
        self.increase_children_button = page.get_by_role(
            "button", name="Increase children"
        ).first
        self.search_button = page.get_by_role("button", name="Search")

    # --- Actions ---
    def _select_location(self, query: str, selection: str) -> None:
        self.location_search_field.fill(query)
        location_option = self.page.locator("div").filter(
            has_text=re.compile(rf"^{re.escape(selection)}$")
        ).first
        location_option.wait_for(state="visible", timeout=30_000)
        location_option.click(timeout=10_000)

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
        self._select_location(data.location_query, data.location_option)
        self.date_picker_button.click()
        check_in = data.check_in_days_from_today
        stay_length = data.stay_length_days
        self.select_calendar_date(check_in)
        self.select_calendar_date(check_in + stay_length)
        self.page.keyboard.press("Escape")
        self.guest_control_button.click()
        for _ in range(rooms - 1):
            self.increase_rooms_button.click()
        for _ in range(additional_adults):
            self.increase_adults_button.click()
        for _ in range(children):
            self.increase_children_button.click()
        expected_guests = rooms + additional_adults + children
        expected_summary = re.compile(rf"{rooms} Rooms?, {expected_guests} Guests?")
        expect(self.guest_control_button).to_contain_text(expected_summary)
        self.guest_control_button.click()
        self.search_button.click()
        self.save_current_state("hotel-search-submitted-state.json")
