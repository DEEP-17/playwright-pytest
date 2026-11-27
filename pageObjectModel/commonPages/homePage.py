from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pageObjectModel.basePage.basePage import BasePage
from pageObjectModel.tripPages.tripSavedTripsPage import TripSavedTripsPage


class HomePage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)

    # --- Actions ---
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
        saved_trips_page = self.page.context.new_page()
        with self.page.context.expect_event(
            "response",
            predicate=TripSavedTripsPage.is_user_plans_response,
            timeout=60_000,
        ) as response_info:
            saved_trips_page.goto(
                "/tripplanner/saved-trips", wait_until="domcontentloaded"
            )
        try:
            saved_trips_page.wait_for_url(
                "**/tripplanner/saved-trips",
                timeout=30_000,
                wait_until="domcontentloaded",
            )
        except PlaywrightTimeoutError as error:
            raise RuntimeError(
                "The saved trips tab did not reach the saved trips page."
            ) from error
        response = response_info.value
        if not response.ok:
            raise RuntimeError(
                f"Loading saved trips failed with HTTP {response.status}."
            )
        TripSavedTripsPage(saved_trips_page).wait_for_plans(response)
        self.log_step("Saved trips page opened")
        return saved_trips_page
