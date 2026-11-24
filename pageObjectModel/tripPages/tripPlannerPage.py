from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pageObjectModel.basePage.basePage import BasePage


class TripPlannerPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.popup_image = page.locator('img[src*="Group 369"]:visible').first
        self.start_planning_button = page.get_by_role("button", name="Start Planning")

    # --- Actions ---
    def dismiss_popup(self) -> None:
        self.wait_for_dom()
        try:
            self.popup_image.wait_for(state="visible", timeout=10_000)
        except PlaywrightTimeoutError:
            self.page.wait_for_url(
                "**/tripplanner/personal-trip/search", timeout=30_000
            )
            self.save_current_state("trip-planner-search-state.json")
            return
        self.popup_image.wait_for(state="visible", timeout=15_000)
        self.popup_image.click(force=True)
        try:
            self.page.wait_for_url(
                "**/tripplanner/personal-trip/search", timeout=5_000
            )
        except PlaywrightTimeoutError:
            self.start_planning_button.click()
            self.page.wait_for_url(
                "**/tripplanner/personal-trip/search", timeout=30_000
            )
        self.save_current_state("trip-planner-search-state.json")
