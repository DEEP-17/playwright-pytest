import re
from dataclasses import replace

import pytest
from playwright.sync_api import Page, expect

from data.objects import TestData
from pages.common.home_page import HomePage
from pages.trips.trip_plan_page import TripPlanPage
from pages.trips.trip_planner_page import TripPlannerPage
from pages.trips.trip_saved_trips_page import TripSavedTripsPage
from pages.trips.trip_search_page import TripSearchPage


@pytest.mark.regression
@pytest.mark.all
def test_e12_trip_planner_creation_flow(
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
def test_e13_saved_itinerary_remains_in_saved_trips(
    authenticated_page: Page,
    home_page: HomePage,
    test_data: TestData,
) -> None:
    assert authenticated_page is home_page.page
    saved_trips_tab = home_page.open_saved_trips()
    saved_trips_page = TripSavedTripsPage(saved_trips_tab)
    existing_trip_count = saved_trips_page.saved_trip_count()
    planner_tab = saved_trips_page.create_trip_planner()
    TripPlannerPage(planner_tab).dismiss_popup()

    fresh_trip = replace(
        test_data.trip,
        start_days_from_today=test_data.trip.start_days_from_today + 3,
    )
    trip_plan_tab = TripSearchPage(planner_tab).search_and_plan(fresh_trip)
    trip_plan_page = TripPlanPage(trip_plan_tab)
    trip_plan_page.save()
    trip_plan_page.save_current_state("trip-planned-state.json")

    saved_trips_tab.reload(wait_until="domcontentloaded")
    expect(
        saved_trips_tab.get_by_role("button", name="Delete")
    ).to_have_count(existing_trip_count + 1, timeout=30_000)


@pytest.mark.regression
def test_e14_delete_old_trip_create_fresh_trip_and_verify_after_refresh(
    authenticated_page: Page,
    home_page: HomePage,
    test_data: TestData,
) -> None:
    assert authenticated_page is home_page.page
    saved_trips_tab = home_page.open_saved_trips()
    saved_trips_page = TripSavedTripsPage(saved_trips_tab)
    existing_trip_count = saved_trips_page.delete_first_trip()
    planner_tab = saved_trips_page.create_trip_planner()
    TripPlannerPage(planner_tab).dismiss_popup()

    fresh_trip = replace(
        test_data.trip,
        start_days_from_today=test_data.trip.start_days_from_today + 10,
    )
    trip_plan_tab = TripSearchPage(planner_tab).search_and_plan(fresh_trip)
    trip_plan_page = TripPlanPage(trip_plan_tab)
    trip_plan_page.save()

    saved_trips_tab.reload(wait_until="domcontentloaded")
    expect(
        saved_trips_tab.get_by_role("button", name="Delete")
    ).to_have_count(existing_trip_count, timeout=30_000)
