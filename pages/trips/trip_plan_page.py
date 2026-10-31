from playwright.sync_api import Page

from pages.base.base_page import BasePage


class TripPlanPage(BasePage):
    def save(self) -> None:
        save_icon = self.page.get_by_test_id("SaveIcon")
        save_icon.wait_for(state="visible")
        save_icon.click()
        self.save_current_state("trip-saved-state.json")
