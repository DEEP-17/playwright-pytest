from unittest.mock import Mock

import pytest

from pageObjectModel.tripPages.tripPlanPage import (
    SavedTripReference,
    TripPlanPage,
)
from pageObjectModel.tripPages.tripSavedTripsPage import TripSavedTripsPage


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


def testSavedTripReloadWaitsForPlanResponse() -> None:
    page = Mock()
    response_context = Mock()
    response_context.__enter__ = Mock(return_value=response_context)
    response_context.__exit__ = Mock(return_value=False)
    response_context.value = Mock(ok=True, status=201)
    page.expect_response.return_value = response_context

    TripSavedTripsPage(page).reload_and_wait_for_plans()

    page.reload.assert_called_once_with(wait_until="domcontentloaded")
    page.expect_response.assert_called_once_with(
        TripSavedTripsPage.is_user_plans_response,
        timeout=60_000,
    )
