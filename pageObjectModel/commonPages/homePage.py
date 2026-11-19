from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pageObjectModel.basePage.basePage import BasePage
from pageObjectModel.tripPages.tripSavedTripsPage import TripSavedTripsPage

class HomePage(BasePage):
    def navigate_to_flights(self) -> None:
        self.log_step("Navigating to flight search")
        self.page.goto("/flights/search", wait_until="domcontentloaded")
        self.log_step("Flight search page opened")

    def navigate_to_hotels(self) -> None:
        self.log_step("Navigating to hotel search")
        self.page.goto("/hotel/search", wait_until="domcontentloaded")
        self.log_step("Hotel search page opened")

    def open_saved_trips(self) -> Page:
        self.log_step("Opening saved trips")
        self.page.goto("/", wait_until="domcontentloaded")
        saved_trips_link = self.page.get_by_role(
            "link", name="Tripplanner saved trips"
        )
        with self.page.context.expect_event(
            "response",
            predicate=TripSavedTripsPage.is_user_plans_response,
            timeout=60_000,
        ) as response_info:
            try:
                with self.page.expect_popup(timeout=15_000) as popup:
                    saved_trips_link.click()
            except PlaywrightTimeoutError as popup_error:
                if self.page.url.endswith("/tripplanner/saved-trips"):
                    self.log_step("Saved trips page opened in the same tab")
                    saved_trips_page = self.page
                else:
                    raise RuntimeError(
                        "Could not open the saved trips page."
                    ) from popup_error
            else:
                saved_trips_page = popup.value
                try:
                    saved_trips_page.wait_for_url(
                        "**/tripplanner/saved-trips",
                        timeout=30_000,
                        wait_until="domcontentloaded",
                    )
                except PlaywrightTimeoutError as error:
                    raise RuntimeError(
                        "The saved trips tab opened but did not reach the saved trips page."
                    ) from error
        response = response_info.value
        if not response.ok:
            raise RuntimeError(
                f"Loading saved trips failed with HTTP {response.status}."
            )
        TripSavedTripsPage(saved_trips_page).wait_for_plans(response)
        self.log_step("Saved trips page opened")
        return saved_trips_page