import pytest
from playwright.sync_api import Browser, Page, expect

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
from data.objects import TestData
from utils.session_state import (
    BrowserStateFiles,
    restore_session_storage,
    state_files,
)
from utils.test_data import load_test_data


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_environment()


@pytest.fixture
def browser_context_args(
    browser_context_args: dict[str, object],
    settings: Settings,
    request: pytest.FixtureRequest,
) -> dict[str, object]:
    if not settings.base_url:
        raise pytest.UsageError("Set BASE_URL in your environment or .env file.")
    base_url = settings.base_url.rstrip("/")
    context_args = {**browser_context_args, "base_url": base_url}
    if "authenticated_page" in request.fixturenames:
        authenticated_state = request.getfixturevalue("authenticated_state")
        context_args["storage_state"] = str(authenticated_state.storage_state)
    return context_args


@pytest.fixture(scope="session")
def test_data() -> TestData:
    return load_test_data()


@pytest.fixture(scope="session")
def authenticated_state(
    browser: Browser, settings: Settings
) -> BrowserStateFiles:
    if not settings.base_url:
        raise pytest.UsageError("Set BASE_URL in your environment or .env file.")
    if not settings.user_email or not settings.user_password:
        raise pytest.UsageError(
            "Set USER_EMAIL and USER_PASSWORD in your environment or .env file."
        )

    context = browser.new_context(base_url=settings.base_url)
    try:
        page = context.new_page()
        LoginPage(page).login(settings.user_email, settings.user_password)
    finally:
        context.close()
    return state_files("authenticated-state.json")


@pytest.fixture
def authenticated_page(
    page: Page, authenticated_state: BrowserStateFiles
) -> Page:
    restore_session_storage(page.context, authenticated_state.session_storage)
    page.goto("/")
    expect(
        page.get_by_role("link", name="Tripplanner saved trips")
    ).to_be_visible(timeout=30_000)
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
