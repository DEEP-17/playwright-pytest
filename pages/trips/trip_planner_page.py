from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage


class TripPlannerPage(BasePage):
    def dismiss_popup(self) -> None:
        self.wait_for_dom()
        self.page.wait_for_timeout(2_000)
        popup_image = self.page.locator('img[src*="Group 369"]:visible').first
        popup_image.wait_for(state="visible", timeout=15_000)
        popup_image.click(force=True)
        try:
            self.page.wait_for_url(
                "**/tripplanner/personal-trip/search", timeout=5_000
            )
        except PlaywrightTimeoutError:
            self.page.get_by_role("button", name="Start Planning").click()
            self.page.wait_for_url(
                "**/tripplanner/personal-trip/search", timeout=30_000
            )
