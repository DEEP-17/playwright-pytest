from urllib.parse import urljoin

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect

from pages.base.base_page import BasePage


class TripSavedTripsPage(BasePage):
    def _wait_for_saved_trips(self) -> None:
        self.page.wait_for_url("**/tripplanner/saved-trips", timeout=30_000)
        self.wait_for_network()

    def saved_trip_count(self) -> int:
        self._wait_for_saved_trips()
        return self.page.get_by_role("button", name="Delete").count()

    def delete_first_trip(self) -> int:
        self._wait_for_saved_trips()
        self.save_current_state("saved-trips-state.json")
        delete_button = self.page.get_by_role("button", name="Delete").first
        initial_count = self.saved_trip_count()
        if initial_count == 0:
            raise RuntimeError("Cannot delete a saved trip: no saved trips exist.")

        self.page.once("dialog", lambda dialog: dialog.accept())
        delete_button.click(force=True)
        self.log_step("Old trip deletion requested.")
        expect(
            self.page.get_by_role("button", name="Delete")
        ).to_have_count(initial_count - 1, timeout=30_000)
        return initial_count

    def create_trip_planner(self) -> Page:
        self._wait_for_saved_trips()
        self.save_current_state("saved-trips-state.json")
        create_trip = self.page.locator("button").filter(has_text="Create Trip").first
        if not create_trip.count() or not create_trip.is_visible():
            self.log_step(
                "Create Trip is unavailable; opening the Build Now planner flow"
            )
            planner_page = self.page.context.new_page()
            planner_page.goto(
                urljoin(self.page.url, "/ai-trip-planner"),
                wait_until="domcontentloaded",
            )
            build_now = planner_page.get_by_role("link", name="Build Now")
            build_now.wait_for(state="visible", timeout=45_000)
            build_now.click()
            planner_page.wait_for_url(
                "**/tripplanner/personal-trip/search", timeout=30_000
            )
            self.save_current_state("trip-planner-created-state.json")
            return planner_page

        try:
            with self.page.expect_popup(timeout=30_000) as popup:
                create_trip.click()
        except PlaywrightTimeoutError as error:
            raise RuntimeError("Create Trip did not open a new planner tab.") from error
        self.save_current_state("trip-planner-created-state.json")
        return popup.value

    def clean_up_and_create(self) -> Page:
        self.delete_first_trip()
        return self.create_trip_planner()
