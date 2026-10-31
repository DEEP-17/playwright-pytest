from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage


class TripSavedTripsPage(BasePage):
    def clean_up_and_create(self) -> Page:
        self.page.wait_for_url("**/tripplanner/saved-trips", timeout=30_000)
        self.wait_for_dom()
        self.save_current_state("saved-trips-state.json")
        self.page.on("dialog", lambda dialog: dialog.accept())

        delete_button = self.page.get_by_role("button", name="Delete").first
        if delete_button.is_visible():
            delete_button.click(force=True)
            self.log_step("Old trip deleted.")
            self.wait_for_network()
        else:
            self.log_step("Delete button was not found. Skipping.")

        create_trip = self.page.locator("button").filter(has_text="Create Trip").first
        create_trip.wait_for(state="visible", timeout=45_000)
        try:
            with self.page.expect_popup(timeout=30_000) as popup:
                create_trip.click()
        except PlaywrightTimeoutError as error:
            raise RuntimeError("Create Trip did not open a new planner tab.") from error
        self.save_current_state("trip-planner-created-state.json")
        return popup.value
