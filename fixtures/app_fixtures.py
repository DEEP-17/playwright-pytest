from typing import Any

import pytest
from playwright.sync_api import Page

from pages.common.home_page import HomePage
from pages.common.login_page import LoginPage
from pages.flights.flight_listing_page import FlightListingPage
from pages.flights.flight_search_page import FlightSearchPage
from pages.flights.flight_seat_map_page import FlightSeatMapPage
from pages.flights.flight_traveller_info_page import FlightTravellerInfoPage
from pages.flights.flight_trip_summary_page import FlightTripSummaryPage
from pages.hotels.hotel_detail_page import HotelDetailPage
from pages.hotels.hotel_guest_info_page import HotelGuestInfoPage
from pages.hotels.hotel_listing_page import HotelListingPage
from pages.hotels.hotel_search_page import HotelSearchPage
from pages.trips.trip_plan_page import TripPlanPage
from pages.trips.trip_planner_page import TripPlannerPage
from pages.trips.trip_saved_trips_page import TripSavedTripsPage
from pages.trips.trip_search_page import TripSearchPage
from utils.config import Settings
from utils.test_data import load_test_data


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_environment()


@pytest.fixture(scope="session")
def base_url(settings: Settings) -> str:
    return (settings.base_url or "http://localhost").rstrip("/")


@pytest.fixture(scope="session")
def browser_context_args(
    browser_context_args: dict[str, object], base_url: str
) -> dict[str, object]:
    return {**browser_context_args, "base_url": base_url}


@pytest.fixture(scope="session")
def test_data() -> dict[str, Any]:
    return load_test_data()


@pytest.fixture
def authenticated_page(page: Page, settings: Settings) -> Page:
    if not settings.base_url:
        raise pytest.UsageError("Set BASE_URL in your environment or .env file.")
    if not settings.user_email or not settings.user_password:
        raise pytest.UsageError(
            "Set USER_EMAIL and USER_PASSWORD in your environment or .env file."
        )
    LoginPage(page).login(settings.user_email, settings.user_password)
    return page


@pytest.fixture
def home_page(page: Page) -> HomePage:
    return HomePage(page)


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    return LoginPage(page)


@pytest.fixture
def flight_search_page(page: Page) -> FlightSearchPage:
    return FlightSearchPage(page)


@pytest.fixture
def flight_listing_page(page: Page) -> FlightListingPage:
    return FlightListingPage(page)


@pytest.fixture
def flight_trip_summary_page(page: Page) -> FlightTripSummaryPage:
    return FlightTripSummaryPage(page)


@pytest.fixture
def flight_seat_map_page(page: Page) -> FlightSeatMapPage:
    return FlightSeatMapPage(page)


@pytest.fixture
def flight_traveller_info_page(page: Page) -> FlightTravellerInfoPage:
    return FlightTravellerInfoPage(page)


@pytest.fixture
def hotel_search_page(page: Page) -> HotelSearchPage:
    return HotelSearchPage(page)


@pytest.fixture
def hotel_listing_page(page: Page) -> HotelListingPage:
    return HotelListingPage(page)


@pytest.fixture
def hotel_detail_page(page: Page) -> HotelDetailPage:
    return HotelDetailPage(page)


@pytest.fixture
def hotel_guest_info_page(page: Page) -> HotelGuestInfoPage:
    return HotelGuestInfoPage(page)


@pytest.fixture
def trip_saved_trips_page(page: Page) -> TripSavedTripsPage:
    return TripSavedTripsPage(page)


@pytest.fixture
def trip_planner_page(page: Page) -> TripPlannerPage:
    return TripPlannerPage(page)


@pytest.fixture
def trip_search_page(page: Page) -> TripSearchPage:
    return TripSearchPage(page)


@pytest.fixture
def trip_plan_page(page: Page) -> TripPlanPage:
    return TripPlanPage(page)
