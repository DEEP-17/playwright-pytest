from unittest.mock import Mock

import pytest

from pageObjectModel.tripPages.tripPlanPage import (
    SavedTripReference,
    TripPlanPage,
)
from pageObjectModel.tripPages.tripSavedTripsPage import TripSavedTripsPage
from pageObjectModel.tripPages.tripSearchPage import TripSearchPage


def testTripLocationWaitsForAutocompleteWithoutFixedSleep() -> None:
    page = Mock()
    textbox = page.get_by_placeholder.return_value
    option = page.get_by_text.return_value

    TripSearchPage(page)._select_location(
        "Where are you from?",
        "amd",
        "AMD -Sardar Vallabhbhai Patel International AirportAhmedabad, India",
    )

    textbox.fill.assert_called_once_with("amd")
    option.wait_for.assert_called_once_with(state="visible", timeout=30_000)
    option.click.assert_called_once_with(timeout=10_000)
    page.wait_for_timeout.assert_not_called()


def testTripSaveWaitsForApiResponseAndReturnsCreatedTripReference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = Mock()
    save_icon = page.get_by_test_id.return_value
    response = Mock(
        ok=True,
        status=201,
        url="https://api.example.test/api/v1/create_plan",
    )
    response.json.return_value = {"newTripPlan": {"_id": "test-plan-id"}}
    response_context = Mock()
    response_context.__enter__ = Mock(return_value=response_context)
    response_context.__exit__ = Mock(return_value=False)
    response_context.value = response
    page.expect_response.return_value = response_context
    monkeypatch.setattr(TripPlanPage, "save_current_state", lambda *_: None)

    reference = TripPlanPage(page).save()

    assert reference == SavedTripReference(
        "test-plan-id", "https://api.example.test/api/v1"
    )
    page.expect_response.assert_called_once()
    save_icon.click.assert_called_once()


def testTripSaveReportsApiFailure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = Mock()
    response = Mock(
        ok=False,
        status=500,
        url="https://api.example.test/api/v1/create_plan",
    )
    response_context = Mock()
    response_context.__enter__ = Mock(return_value=response_context)
    response_context.__exit__ = Mock(return_value=False)
    response_context.value = response
    page.expect_response.return_value = response_context
    monkeypatch.setattr(TripPlanPage, "save_current_state", lambda *_: None)

    with pytest.raises(RuntimeError, match="HTTP 500"):
        TripPlanPage(page).save()


def testCleanupDeletesOnlyTheCreatedTrip() -> None:
    page = Mock()
    page.request.delete.return_value = Mock(ok=True, status=200)
    trip = SavedTripReference(
        "created-plan-id", "https://api.example.test/api/v1"
    )

    TripPlanPage(page).delete_saved_trip(trip)

    page.request.delete.assert_called_once_with(
        "https://api.example.test/api/v1/delete/created-plan-id"
    )


def testSavedTripNavigationWaitsForUrlWithoutNetworkIdle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = Mock()
    saved_trips_page = TripSavedTripsPage(page)
    monkeypatch.setattr(
        saved_trips_page,
        "wait_for_network",
        lambda: pytest.fail("Saved trips must not wait for network idle."),
    )

    saved_trips_page._wait_for_saved_trips()

    page.wait_for_url.assert_called_once_with(
        "**/tripplanner/saved-trips", timeout=30_000
    )


def testSavedTripReloadWaitsForPlanResponse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = Mock()
    response_context = Mock()
    response_context.__enter__ = Mock(return_value=response_context)
    response_context.__exit__ = Mock(return_value=False)
    response_context.value = Mock(
        ok=True,
        status=201,
        json=Mock(
            return_value={"newTripPlan": [], "AITripPlanResponse": []}
        ),
    )
    page.expect_response.return_value = response_context
    count_assertion = Mock()
    monkeypatch.setattr(
        "pageObjectModel.tripPages.tripSavedTripsPage.expect",
        lambda _: count_assertion,
    )

    TripSavedTripsPage(page).reload_and_wait_for_plans()

    page.reload.assert_called_once_with(wait_until="domcontentloaded")
    page.expect_response.assert_called_once_with(
        TripSavedTripsPage.is_user_plans_response,
        timeout=60_000,
    )
    count_assertion.to_have_count.assert_called_once_with(0, timeout=60_000)


def testSavedTripPageWaitsUntilApiPlansAreRendered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = Mock()
    response = Mock()
    response.json.return_value = {
        "newTripPlan": [{"_id": "expected-plan-id"}, {}],
        "AITripPlanResponse": [{}],
    }
    count_assertion = Mock()
    monkeypatch.setattr(
        "pageObjectModel.tripPages.tripSavedTripsPage.expect",
        lambda _: count_assertion,
    )

    TripSavedTripsPage(page).wait_for_plans(
        response, expected_trip_id="expected-plan-id"
    )

    page.get_by_role.assert_called_once_with("button", name="Delete")
    count_assertion.to_have_count.assert_called_once_with(3, timeout=60_000)


def testSavedTripPageFailsWhenExpectedTripIsMissing() -> None:
    page = Mock()
    response = Mock()
    response.json.return_value = {
        "newTripPlan": [{"_id": "different-plan-id"}],
        "AITripPlanResponse": [],
    }

    with pytest.raises(
        AssertionError, match="expected-plan-id"
    ):
        TripSavedTripsPage(page).wait_for_plans(
            response, expected_trip_id="expected-plan-id"
        )
