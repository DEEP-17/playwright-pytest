import re
from dataclasses import replace
import pytest
from playwright.sync_api import Page, expect
from testData.testDataObjects import TestData
from pageObjectModel.commonPages.homePage import HomePage
from pageObjectModel.tripPages.tripPlanPage import TripPlanPage
from pageObjectModel.tripPages.tripPlannerPage import TripPlannerPage
from pageObjectModel.tripPages.tripSavedTripsPage import TripSavedTripsPage
from pageObjectModel.tripPages.tripSearchPage import TripSearchPage

@pytest.mark.regression
@pytest.mark.all
def testE12TripPlannerCreationFlow(
    authenticated_page: Page,
    home_page: HomePage,
    test_data: TestData,
) -> None:
    assert authenticated_page is home_page.page
    saved_trips_tab = home_page.open_saved_trips()
    planner_tab = TripSavedTripsPage(saved_trips_tab).create_trip_planner()
    TripPlannerPage(planner_tab).dismiss_popup()

    trip_plan_tab = TripSearchPage(planner_tab).search_and_plan(test_data.trip)
    expect(trip_plan_tab).to_have_url(re.compile(r".*/tripplanner/.*"))
    expect(trip_plan_tab.get_by_test_id("SaveIcon")).to_be_visible(
        timeout=30_000
    )

@pytest.mark.regression
def testE13SavedItineraryRemainsInSavedTrips(
    authenticated_page: Page,
    home_page: HomePage,
    test_data: TestData,
    request: pytest.FixtureRequest,
) -> None:
    assert authenticated_page is home_page.page
    saved_trips_tab = home_page.open_saved_trips()
    saved_trips_page = TripSavedTripsPage(saved_trips_tab)
    planner_tab = saved_trips_page.create_trip_planner()
    TripPlannerPage(planner_tab).dismiss_popup()
    fresh_trip = replace(
        test_data.trip,
        start_days_from_today=test_data.trip.start_days_from_today + 3,
    )
    trip_plan_tab = TripSearchPage(planner_tab).search_and_plan(fresh_trip)
    trip_plan_page = TripPlanPage(trip_plan_tab)
    created_trip = trip_plan_page.save()
    request.addfinalizer(
        lambda: trip_plan_page.delete_saved_trip(created_trip)
    )
    trip_plan_page.save_current_state("trip-planned-state.json")
    saved_trips_page.reload_and_wait_for_plans(created_trip.plan_id)
    expect(
        saved_trips_tab.get_by_role("button", name="Delete").first
    ).to_be_visible()
    assert saved_trips_page.saved_trip_count() >= 1, (
        "Saved trips page did not show the newly created trip after reload."
    )

@pytest.mark.regression
def testE14DeleteOldTripCreateFreshTripAndVerifyAfterRefresh(
    authenticated_page: Page,
    home_page: HomePage,
    test_data: TestData,
    request: pytest.FixtureRequest,
) -> None:
    assert authenticated_page is home_page.page
    saved_trips_tab = home_page.open_saved_trips()
    saved_trips_page = TripSavedTripsPage(saved_trips_tab)
    saved_trips_page.delete_first_trip()
    planner_tab = saved_trips_page.create_trip_planner()
    TripPlannerPage(planner_tab).dismiss_popup()
    fresh_trip = replace(
        test_data.trip,
        start_days_from_today=test_data.trip.start_days_from_today + 10,
    )
    trip_plan_tab = TripSearchPage(planner_tab).search_and_plan(fresh_trip)
    trip_plan_page = TripPlanPage(trip_plan_tab)
    created_trip = trip_plan_page.save()
    request.addfinalizer(
        lambda: trip_plan_page.delete_saved_trip(created_trip)
    )
    saved_trips_page.reload_and_wait_for_plans(created_trip.plan_id)
    expect(
        saved_trips_tab.get_by_role("button", name="Delete").first
    ).to_be_visible()
    assert saved_trips_page.saved_trip_count() >= 1, (
        "Saved trips page did not show the newly created trip after reload."
    )