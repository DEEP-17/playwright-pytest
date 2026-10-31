import pytest
from playwright.sync_api import Page

from data.objects import TestData
from pages.common.home_page import HomePage
from pages.flights.flight_listing_page import FlightListingPage
from pages.flights.flight_search_page import FlightSearchPage
from pages.flights.flight_seat_map_page import FlightSeatMapPage
from pages.flights.flight_traveller_info_page import FlightTravellerInfoPage
from pages.flights.flight_trip_summary_page import FlightTripSummaryPage
from utils.config import Settings


@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.all
def test_flight_booking_flow(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    flight_trip_summary_page: FlightTripSummaryPage,
    flight_seat_map_page: FlightSeatMapPage,
    flight_traveller_info_page: FlightTravellerInfoPage,
    test_data: TestData,
    settings: Settings,
) -> None:
    assert authenticated_page is home_page.page
    home_page.navigate_to_flights()
    flight_data = test_data.flight
    flight_search_page.search_flight(flight_data)
    flight_search_page.save_current_state("flight-searched-state.json")
    flight_listing_page.filter_and_select()
    flight_listing_page.save_current_state("flight-selected-state.json")
    flight_trip_summary_page.proceed()
    flight_seat_map_page.handle_seats()
    if not settings.user_email:
        pytest.fail("USER_EMAIL is required for the flight booking flow.")
    flight_traveller_info_page.fill_info(flight_data, settings.user_email)
