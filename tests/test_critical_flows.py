import re

import pytest
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, expect

from data.objects import FlightData, HotelData, TestData
from pages.common.home_page import HomePage
from pages.flights.flight_listing_page import FlightListingPage
from pages.flights.flight_search_page import FlightSearchPage
from pages.flights.flight_seat_map_page import FlightSeatMapPage
from pages.flights.flight_trip_summary_page import FlightTripSummaryPage
from pages.flights.flight_traveller_info_page import FlightTravellerInfoPage
from pages.hotels.hotel_detail_page import HotelDetailPage
from pages.hotels.hotel_guest_info_page import HotelGuestInfoPage
from pages.hotels.hotel_listing_page import HotelListingPage
from pages.hotels.hotel_search_page import HotelSearchPage
from utils.config import Settings


@pytest.mark.critical
@pytest.mark.regression
@pytest.mark.parametrize("booking_form", ("flight", "hotel"))
def test_c7_invalid_contact_details_block_booking(
    booking_form: str,
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    flight_trip_summary_page: FlightTripSummaryPage,
    flight_seat_map_page: FlightSeatMapPage,
    hotel_search_page: HotelSearchPage,
    hotel_listing_page: HotelListingPage,
    test_data: TestData,
    settings: Settings,
) -> None:
    form_page = authenticated_page
    if booking_form == "flight":
        _open_flight_checkout(
            home_page,
            flight_search_page,
            flight_listing_page,
            flight_trip_summary_page,
            flight_seat_map_page,
            test_data.flight,
        )
        FlightTravellerInfoPage(form_page).fill_info(
            test_data.flight, _required_email(settings)
        )
    else:
        form_page = _open_hotel_guest_form(
            home_page,
            hotel_search_page,
            hotel_listing_page,
            test_data.hotel,
        )
        HotelGuestInfoPage(form_page).fill_info(
            test_data.hotel, _required_email(settings)
        )

    for selector, value in (
        ('input[name="email"]', "not-an-email"),
        ('input[name="phone"]', "12"),
        ('input[name="zipcode"]', "not-a-zip"),
    ):
        field = form_page.locator(selector)
        expect(field).to_be_visible()
        field.fill(value)

    submit = _booking_submit_button(form_page)
    if submit.is_enabled():
        submit.click()

    _expect_validation_feedback(
        form_page,
        'input[name="email"], input[name="phone"], input[name="zipcode"]',
    )
    expect(form_page.locator('input[name="email"]')).to_be_visible()


@pytest.mark.critical
@pytest.mark.regression
def test_c5_flight_without_seats_can_continue_gracefully(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    flight_trip_summary_page: FlightTripSummaryPage,
    flight_seat_map_page: FlightSeatMapPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(test_data.flight)
    flight_listing_page.filter_and_select()
    flight_trip_summary_page.proceed()

    no_seats_available = flight_seat_map_page.handle_seats()
    if no_seats_available:
        expect(
            authenticated_page.get_by_role(
                "heading",
                name="Seat booking is not available for this flight",
                level=4,
            )
        ).to_be_visible()
    expect(
        authenticated_page.locator('input[name^="firstName"]').first
    ).to_be_visible(timeout=60_000)


@pytest.mark.critical
@pytest.mark.regression
def test_c6_flight_checkout_requires_passenger_details(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    flight_trip_summary_page: FlightTripSummaryPage,
    flight_seat_map_page: FlightSeatMapPage,
    test_data: TestData,
) -> None:
    _open_flight_checkout(
        home_page,
        flight_search_page,
        flight_listing_page,
        flight_trip_summary_page,
        flight_seat_map_page,
        test_data.flight,
    )
    first_name = authenticated_page.locator('input[name^="firstName"]').first
    expect(first_name).to_be_visible(timeout=60_000)
    assert first_name.input_value() == ""

    submit = _booking_submit_button(authenticated_page)
    if submit.is_enabled():
        submit.click()

    _expect_validation_feedback(
        authenticated_page, 'input[name^="firstName"], input[name^="lastName"]'
    )
    expect(first_name).to_be_visible()


@pytest.mark.critical
@pytest.mark.regression
def test_c8_hotel_sold_out_or_price_error_has_a_recovery_state(
    authenticated_page: Page,
    home_page: HomePage,
    hotel_search_page: HotelSearchPage,
    hotel_listing_page: HotelListingPage,
    test_data: TestData,
) -> None:
    assert authenticated_page is home_page.page
    detail_page = _open_hotel_detail(
        home_page,
        hotel_search_page,
        hotel_listing_page,
        test_data.hotel,
    )
    detail = HotelDetailPage(detail_page)
    if not detail.has_book_now_button():
        recovery_message = detail_page.get_by_text(
            re.compile(r"sold out|search other hotels", re.IGNORECASE)
        )
        expect(recovery_message.first).to_be_visible()
        return

    detail_page.locator("button").filter(has_text="Book Now").first.click()
    price_error = detail_page.get_by_text(
        "Sorry, There is a problem in checking price!", exact=True
    )
    try:
        price_error.wait_for(state="visible", timeout=15_000)
    except PlaywrightTimeoutError:
        proceed_to_pay = detail_page.get_by_role("button", name="Proceed to Pay")
        try:
            proceed_to_pay.wait_for(state="visible", timeout=15_000)
        except PlaywrightTimeoutError:
            loading_state = detail_page.get_by_text("Please wait...", exact=True)
            if loading_state.is_visible():
                pytest.fail(
                    "Hotel price check remained in a loading state; "
                    "the fallback could not be verified."
                )

            recovery_message = detail_page.get_by_text(
                re.compile(r"sold out|search other hotels", re.IGNORECASE)
            )
            expect(recovery_message.first).to_be_visible()


@pytest.mark.critical
@pytest.mark.regression
def test_c9_hotel_guest_age_is_required_and_validated(
    authenticated_page: Page,
    home_page: HomePage,
    hotel_search_page: HotelSearchPage,
    hotel_listing_page: HotelListingPage,
    test_data: TestData,
) -> None:
    assert authenticated_page is home_page.page
    guest_page = _open_hotel_guest_form(
        home_page,
        hotel_search_page,
        hotel_listing_page,
        test_data.hotel,
    )
    age = guest_page.get_by_role("textbox", name="Ex. 35")
    age.fill("")

    submit = _booking_submit_button(guest_page)
    if submit.is_enabled():
        submit.click()

    _expect_validation_feedback(guest_page, 'input[placeholder="Ex. 35"]')
    expect(age).to_be_visible()


@pytest.mark.critical
@pytest.mark.regression
def test_c10_unknown_attractions_location_is_rejected_without_navigation(
    page: Page,
) -> None:
    page.goto("/tours/search", wait_until="networkidle")
    search_field = page.get_by_role("textbox", name="Where are you going?")
    search_field.fill("NoSuchDestinationForEmptyState")
    page.get_by_role("button", name="Search").click()

    expect(page.get_by_text("Location is required")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/tours/search$"))


@pytest.mark.regression
def test_e4_search_attractions_and_open_details(page: Page) -> None:
    page.goto("/tours/search", wait_until="networkidle")
    expect(
        page.get_by_role("heading", name="Search attractions")
    ).to_be_visible()
    search_field = page.get_by_role("textbox", name="Where are you going?")
    expect(search_field).to_be_visible()
    search_field.fill("San Francisco")
    page.get_by_role("button", name="Search").click()

    destination_heading = page.get_by_role(
        "heading", name="San Francisco", exact=True
    )
    expect(destination_heading).to_be_visible()
    destination_heading.click()
    expect(page).to_have_url(re.compile(r"/tours/[^/?]+/\d+"))
    tour_heading = page.get_by_role("heading", level=2).first
    expect(tour_heading).to_be_visible()

    with page.expect_popup() as detail_page_info:
        tour_heading.click()
    detail_page = detail_page_info.value
    expect(detail_page).to_have_url(re.compile(r"/tours/[^/?]+/packages/.+"))
    expect(detail_page.get_by_role("heading", level=1)).to_be_visible(
        timeout=60_000
    )


@pytest.mark.critical
@pytest.mark.regression
def test_c13_extreme_flight_price_filter_reduces_results_and_reset_restores_them(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(test_data.flight)
    if not flight_listing_page.wait_for_results():
        pytest.fail(
            "Flight results did not load; the price-filter behavior could not be verified."
        )
    if not authenticated_page.get_by_role("slider").count():
        pytest.fail("Flight results do not expose an accessible price slider.")
    initial_count = _flight_result_count(authenticated_page)
    _set_price_filter_to_extreme(authenticated_page)
    _expect_filtered_flights_and_reset(authenticated_page, initial_count)


@pytest.mark.critical
@pytest.mark.regression
def test_c15_back_and_forward_restore_flight_and_hotel_navigation(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    hotel_search_page: HotelSearchPage,
    hotel_listing_page: HotelListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(test_data.flight)
    flight_listing_page.filter_and_select()
    selected_url = authenticated_page.url
    expect(authenticated_page).to_have_url(re.compile(r"/flights/trip-summary/"))

    authenticated_page.go_back()
    expect(authenticated_page).to_have_url(re.compile(r"/flights/listing-flights/"))
    expect(
        authenticated_page.locator("div.flex > section.flex > div.flex").first
    ).to_be_visible(timeout=30_000)
    authenticated_page.go_forward()
    expect(authenticated_page).to_have_url(selected_url)
    expect(authenticated_page.get_by_role("heading", name="Trip Summary")).to_be_visible()

    home_page.navigate_to_hotels()
    hotel_search_page.search(test_data.hotel)
    expect(authenticated_page).to_have_url(re.compile(r"/hotel/listing-stay/"))
    hotel_results_url = authenticated_page.url
    hotel_detail_page = hotel_listing_page.open_hotel_detail()

    if hotel_detail_page is authenticated_page:
        authenticated_page.go_back()
        expect(authenticated_page).to_have_url(hotel_results_url)
        expect(
            authenticated_page.locator("button").filter(has_text="Select").first
        ).to_be_visible(timeout=60_000)
        authenticated_page.go_forward()
        expect(authenticated_page).to_have_url(re.compile(r"/hotel/"))
    else:
        authenticated_page.go_back()
        expect(authenticated_page).to_have_url(re.compile(r"/hotel/search"))
        authenticated_page.go_forward()
        expect(authenticated_page).to_have_url(hotel_results_url)
        expect(
            authenticated_page.locator("button").filter(has_text="Select").first
        ).to_be_visible(timeout=60_000)


@pytest.mark.critical
@pytest.mark.regression
def test_c21_combined_flight_filters_narrow_results_and_reset_restores_them(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(test_data.flight)
    if not flight_listing_page.wait_for_results():
        pytest.fail(
            "Flight results did not load; combined filters could not be verified."
        )
    initial_count = _flight_result_count(authenticated_page)
    stop_filter = authenticated_page.get_by_text(re.compile(r"^2 Stops?$")).first
    airline_filter = authenticated_page.locator('[id="Air Canada"]').first
    if not stop_filter.count() or not stop_filter.is_visible():
        pytest.fail("The available flight results do not show the two-stop filter.")
    if not airline_filter.count() or not airline_filter.is_visible():
        pytest.fail("The available flight results do not show the Air Canada filter.")
    stop_filter.click(force=True)
    airline_filter.click()
    _set_price_filter_to_extreme(authenticated_page)
    _expect_filtered_flights_and_reset(
        authenticated_page, initial_count, allow_empty=True
    )


@pytest.mark.critical
@pytest.mark.regression
def test_c22_refresh_during_flight_checkout_recovers_selected_itinerary(
    authenticated_page: Page,
    home_page: HomePage,
    flight_search_page: FlightSearchPage,
    flight_listing_page: FlightListingPage,
    flight_trip_summary_page: FlightTripSummaryPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_flights()
    flight_search_page.search_flight(test_data.flight)
    flight_listing_page.filter_and_select()
    flight_trip_summary_page.proceed()
    FlightSeatMapPage(authenticated_page).handle_seats()

    authenticated_page.reload(wait_until="domcontentloaded")

    expect(authenticated_page).to_have_url(re.compile(r"/flights/travellerinfo/"))
    expect(
        authenticated_page.locator('input[name^="firstName"]').first
    ).to_be_visible(timeout=30_000)


def _open_flight_checkout(
    home_page: HomePage,
    search_page: FlightSearchPage,
    listing_page: FlightListingPage,
    summary_page: FlightTripSummaryPage,
    seat_map_page: FlightSeatMapPage,
    flight_data: FlightData,
) -> None:
    home_page.navigate_to_flights()
    search_page.search_flight(flight_data)
    listing_page.filter_and_select()
    summary_page.proceed()
    seat_map_page.handle_seats()


def _open_hotel_detail(
    home_page: HomePage,
    search_page: HotelSearchPage,
    listing_page: HotelListingPage,
    hotel_data: HotelData,
) -> Page:
    home_page.navigate_to_hotels()
    search_page.search(hotel_data)
    select_button = listing_page.page.locator("button").filter(has_text="Select").first
    try:
        select_button.wait_for(state="visible", timeout=15_000)
    except PlaywrightTimeoutError as error:
        loading_state = listing_page.page.get_by_text(
            re.compile(r"please wait|loading", re.IGNORECASE)
        )
        if loading_state.is_visible():
            pytest.fail(
                "Hotel inventory remained in a loading state; "
                "the detail-page flow could not be verified."
            )
        raise RuntimeError(
            "Hotel search did not display a selectable result or loading state."
        ) from error
    return listing_page.open_hotel_detail()


def _open_hotel_guest_form(
    home_page: HomePage,
    search_page: HotelSearchPage,
    listing_page: HotelListingPage,
    hotel_data: HotelData,
) -> Page:
    hotel_page = _open_hotel_detail(home_page, search_page, listing_page, hotel_data)
    if not HotelDetailPage(hotel_page).click_book_now():
        pytest.fail(
            "The selected hotel is unavailable for booking; "
            "the guest-form validation could not be verified."
        )
    email_field = hotel_page.locator('input[name="email"]')
    try:
        email_field.wait_for(state="visible", timeout=15_000)
    except PlaywrightTimeoutError as error:
        loading_state = hotel_page.get_by_text(
            re.compile(r"please wait|loading", re.IGNORECASE)
        )
        if loading_state.is_visible():
            pytest.fail(
                "Hotel booking form remained in a loading state; "
                "form validation could not be verified."
            )
        raise RuntimeError(
            "Book Now was accepted, but the hotel contact form did not open."
        ) from error
    return hotel_page


def _booking_submit_button(page: Page):
    submit = page.get_by_role(
        "button",
        name=re.compile(r"continue|submit|confirm|book|payment|next", re.IGNORECASE),
    )
    if submit.count() == 0:
        submit = page.locator('button[type="submit"]')
    assert submit.count() > 0, "Booking form has no submit or continue action."
    return submit.last


def _expect_validation_feedback(page: Page, field_selector: str) -> None:
    invalid_fields = page.locator(
        f":is({field_selector}):invalid, "
        f":is({field_selector})[aria-invalid='true']"
    )
    if invalid_fields.count() > 0:
        expect(invalid_fields.first).to_be_visible()
        return

    validation_message = page.get_by_text(
        re.compile(
            r"required|invalid|enter a valid|please provide|must be",
            re.IGNORECASE,
        )
    )
    expect(validation_message.first).to_be_visible()


def _set_price_filter_to_extreme(page: Page) -> None:
    slider = page.get_by_role("slider").first
    expect(slider).to_be_visible()
    slider.press("End")
    maximum_price = slider.get_attribute("aria-valuemax")
    assert maximum_price is not None, "Price filter does not expose its maximum value."
    expect(slider).to_have_attribute("aria-valuenow", maximum_price)


def _flight_result_count(page: Page) -> int:
    match = re.search(r"(\d+)\s+results found", page.locator("body").inner_text())
    assert match is not None, "Flight listing does not show its result count."
    return int(match.group(1))


def _expect_filtered_flights_and_reset(
    page: Page, initial_count: int, *, allow_empty: bool = False
) -> None:
    page.wait_for_function(
        """(previousCount) => {
            const match = document.body.innerText.match(/(\\d+)\\s+results found/);
            return match !== null && Number(match[1]) < previousCount;
        }""",
        arg=initial_count,
        timeout=30_000,
    )
    filtered_count = _flight_result_count(page)
    assert filtered_count < initial_count
    if not allow_empty:
        assert filtered_count > 0

    clear_all = page.get_by_text("Clear all", exact=True)
    expect(clear_all).to_be_visible()
    clear_all.click()
    page.wait_for_function(
        """(previousCount) => {
            const match = document.body.innerText.match(/(\\d+)\\s+results found/);
            return match !== null && Number(match[1]) === previousCount;
        }""",
        arg=initial_count,
        timeout=30_000,
    )
    expect(page.locator("div.flex > section.flex > div.flex").first).to_be_visible()


def _required_email(settings: Settings) -> str:
    if not settings.user_email:
        pytest.fail("USER_EMAIL is required for the booking validation cases.")
    return settings.user_email
