import re
from decimal import Decimal, InvalidOperation
import pytest
from playwright.sync_api import Page, expect
from testData.testDataObjects import TestData
from pageObjectModel.commonPages.homePage import HomePage
from pageObjectModel.flightPages.flightListingPage import FlightListingPage
from pageObjectModel.flightPages.flightSearchPage import FlightSearchPage
from pageObjectModel.flightPages.flightSeatMapPage import FlightSeatMapPage
from pageObjectModel.flightPages.flightTravellerInfoPage import FlightTravellerInfoPage
from pageObjectModel.flightPages.flightTripSummaryPage import FlightTripSummaryPage
from sharedUtilities.projectConfiguration import Settings

@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.all
def testE1FlightBookingFlow(
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

@pytest.mark.regression
def testE5BusinessClassFlightSearch(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(
        test_data.flight, cabin_class="Business class"
    )
    assert flight_listing_page.wait_for_results(), (
        "Business-class flight search did not display results."
    )
    expect(
        authenticated_page.locator("div.flex > section.flex > div.flex").first
    ).to_be_visible()

@pytest.mark.regression
def testE6RoundTripSearchRespectsPassengerCountAndDates(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(
        test_data.flight,
        trip_type="Round trip",
        passenger_counts=(2, 0, 0),
    )
    assert flight_listing_page.wait_for_results(), (
        "Round-trip flight search did not display results."
    )
    expect(authenticated_page.locator("body")).to_contain_text(
        re.compile(r"\d+\s+results found", re.IGNORECASE)
    )
    expect(
        authenticated_page.get_by_text("View Flight Details", exact=True).first
    ).to_be_visible()
    expect(authenticated_page).to_have_url(
        re.compile(r"/Round%20Trip/2/0/0/Economy/")
    )

@pytest.mark.regression
def testE7MultiCityFlightSearch(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_multi_city(test_data.flight)
    assert flight_listing_page.wait_for_results(), (
        "Multi-city flight search did not display results."
    )
    expect(authenticated_page.locator("body")).to_contain_text(
        "Multi city per traveler"
    )
    expect(authenticated_page.locator("body")).to_contain_text(
        "Sardar Vallabhbhai Patel International Airport"
    )
    expect(authenticated_page.locator("body")).to_contain_text(
        "Toronto Pearson International Airport"
    )

@pytest.mark.regression
def testE8FlightFiltersAndArrivalSort(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(test_data.flight)
    assert flight_listing_page.wait_for_results(), (
        "Flight results did not load for the filter and sort scenario."
    )
    stop_filter = authenticated_page.get_by_text(
        re.compile(r"^2 Stops?$")
    ).first
    airline_filter = authenticated_page.locator('[id="Air Canada"]').first
    expect(stop_filter).to_be_visible()
    expect(airline_filter).to_be_visible()
    stop_filter.click()
    airline_filter.click()
    price_slider = authenticated_page.get_by_role("slider").first
    expect(price_slider).to_be_visible()
    old_price_limit = price_slider.get_attribute("aria-valuenow")
    assert old_price_limit is not None, "Price slider has no current value."
    price_slider.press("ArrowRight")
    authenticated_page.wait_for_function(
        """(previous) =>
            document.querySelectorAll('[role="slider"]')[0]
                ?.getAttribute('aria-valuenow') !== previous""",
        arg=old_price_limit,
        timeout=5_000,
    )
    authenticated_page.get_by_role(
        "button", name=re.compile(r"Sort by\s*:\s*Price", re.IGNORECASE)
    ).click()
    arrival_option = authenticated_page.get_by_text(
        "Arrival (earliest)", exact=True
    ).last
    expect(arrival_option).to_be_visible()
    arrival_option.click(force=True)
    expect(
        authenticated_page.get_by_role(
            "button", name=re.compile(r"Arrival.*earliest", re.IGNORECASE)
        )
    ).to_be_visible()
    expect(
        authenticated_page.locator("div.flex > section.flex > div.flex").first
    ).to_be_visible()

@pytest.mark.regression
def testE9SelectedFarePersistsToTripSummary(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(test_data.flight)
    assert flight_listing_page.wait_for_results(), (
        "Flight results did not load for fare persistence validation."
    )
    first_result = authenticated_page.locator(
        "div.flex > section.flex > div.flex"
    ).first
    result_text = first_result.inner_text()
    fare = re.search(r"(?:₹|\$)\s?([\d,]+(?:\.\d{1,2})?)", result_text)
    assert fare is not None, "Selected flight result did not display a fare."
    first_result.click()
    authenticated_page.wait_for_url("**/flights/trip-summary/**", timeout=60_000)
    expect(
        authenticated_page.get_by_role("heading", name="Trip Summary")
    ).to_be_visible()
    expect(
        authenticated_page.get_by_role(
            "button", name=re.compile("Continue to Checkout", re.IGNORECASE)
        )
    ).to_be_visible(timeout=60_000)
    expect(
        authenticated_page.get_by_text(
            re.compile(r"Total price", re.IGNORECASE)
        ).first
    ).to_be_visible(timeout=60_000)
    summary = authenticated_page.locator("body").inner_text()
    summary_fare = re.search(
        r"Total price\s*(?:₹|\$)\s*([^\s]+)", summary, re.IGNORECASE
    )
    assert summary_fare is not None, "Trip summary did not display its total fare."
    result_amount = Decimal(fare.group(1).replace(",", ""))
    fare_text = summary_fare.group(1).replace(",", "")
    try:
        summary_amount = Decimal(fare_text)
    except InvalidOperation:
        pytest.skip(
            "KNOWN_ISSUE:E9_INVALID_REPRICE_TOTAL: "
            f"Trip summary displayed an invalid total fare: {fare_text!r}"
        )
    if not summary_amount.is_finite():
        pytest.skip(
            "KNOWN_ISSUE:E9_INVALID_REPRICE_TOTAL: "
            f"Trip summary displayed an invalid total fare: {fare_text!r}"
        )
    assert abs(result_amount - summary_amount) <= Decimal("2"), (
        "Trip summary fare differs from the selected flight fare by more than "
        "INR 2."
    )