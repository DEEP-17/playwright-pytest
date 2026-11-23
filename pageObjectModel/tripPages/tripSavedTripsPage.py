from urllib.parse import urljoin, urlsplit
from playwright.sync_api import (
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)
from pageObjectModel.basePage.basePage import BasePage

class TripSavedTripsPage(BasePage):
    def _wait_for_saved_trips(self) -> None:
        self.page.wait_for_url("**/tripplanner/saved-trips", timeout=30_000)

    @staticmethod
    def is_user_plans_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and urlsplit(response.url).path.startswith("/api/v1/get_user_plan/")
        )

    def reload_and_wait_for_plans(
        self, expected_trip_id: str | None = None
    ) -> None:
        with self.page.expect_response(
            self.is_user_plans_response, timeout=60_000
        ) as response_info:
            self.page.reload(wait_until="domcontentloaded")
        response = response_info.value
        if not response.ok:
            raise RuntimeError(
                f"Loading saved trips failed with HTTP {response.status}."
            )
        self.wait_for_plans(response, expected_trip_id)

    def wait_for_plans(
        self, response: Response, expected_trip_id: str | None = None
    ) -> None:
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("The saved-trips response was not a JSON object.")
        new_trip_plans = payload.get("newTripPlan")
        ai_trip_plans = payload.get("AITripPlanResponse")
        if not isinstance(new_trip_plans, list) or not isinstance(
            ai_trip_plans, list
        ):
            raise RuntimeError("The saved-trips response had an invalid plan list.")
        if expected_trip_id is not None and not any(
            isinstance(plan, dict) and plan.get("_id") == expected_trip_id
            for plan in new_trip_plans + ai_trip_plans
        ):
            raise AssertionError(
                f"Saved-trips response did not contain trip {expected_trip_id!r}."
            )
        expect(
            self.page.get_by_role("button", name="Delete")
        ).to_have_count(len(new_trip_plans) + len(ai_trip_plans), timeout=60_000)

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
