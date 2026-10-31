import pytest
from playwright.sync_api import Page

from data.objects import TestData
from pages.common.home_page import HomePage
from pages.trips.trip_plan_page import TripPlanPage
from pages.trips.trip_planner_page import TripPlannerPage
from pages.trips.trip_saved_trips_page import TripSavedTripsPage
from pages.trips.trip_search_page import TripSearchPage


@pytest.mark.regression
@pytest.mark.all
def test_create_trip_planner_flow(
    authenticated_page: Page,
    home_page: HomePage,
    test_data: TestData,
) -> None:
    assert authenticated_page is home_page.page
    saved_trips_tab = home_page.open_saved_trips()
    planner_tab = TripSavedTripsPage(saved_trips_tab).clean_up_and_create()
    TripPlannerPage(planner_tab).dismiss_popup()

    trip_plan_tab = TripSearchPage(planner_tab).search_and_plan(test_data.trip)
    trip_plan_page = TripPlanPage(trip_plan_tab)
    trip_plan_page.save()
    trip_plan_page.save_current_state("trip-planned-state.json")
