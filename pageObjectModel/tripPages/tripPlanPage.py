from dataclasses import dataclass
from urllib.parse import quote, urlsplit, urlunsplit

from playwright.sync_api import Page, Response
from pageObjectModel.basePage.basePage import BasePage


@dataclass(frozen=True)
class SavedTripReference:
    plan_id: str
    api_base_url: str


class TripPlanPage(BasePage):
    def save(self) -> SavedTripReference:
        save_icon = self.page.get_by_test_id("SaveIcon")
        save_icon.wait_for(state="visible")
        with self.page.expect_response(
            self._is_create_plan_response, timeout=60_000
        ) as response_info:
            save_icon.click()
        response = response_info.value
        if not response.ok:
            raise RuntimeError(
                f"Saving the trip failed with HTTP {response.status}."
            )

        payload = response.json()
        new_trip_plan = payload.get("newTripPlan")
        if not isinstance(new_trip_plan, dict):
            raise RuntimeError("The save response did not contain a new trip plan.")
        plan_id = new_trip_plan.get("_id")
        if not isinstance(plan_id, str) or not plan_id:
            raise RuntimeError("The save response did not contain a trip ID.")

        parsed_url = urlsplit(response.url)
        api_base_url = urlunsplit(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path.rsplit("/", 1)[0],
                "",
                "",
            )
        )
        self.save_current_state("trip-saved-state.json")
        return SavedTripReference(plan_id, api_base_url)

    @staticmethod
    def _is_create_plan_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and urlsplit(response.url).path.endswith("/api/v1/create_plan")
        )

    def delete_saved_trip(self, trip: SavedTripReference) -> None:
        response = self.page.request.delete(
            f"{trip.api_base_url}/delete/{quote(trip.plan_id, safe='')}"
        )
        if not response.ok:
            raise RuntimeError(
                f"Removing the test-created trip failed with HTTP {response.status}."
            )
