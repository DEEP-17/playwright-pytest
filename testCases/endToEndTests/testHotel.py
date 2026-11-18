import re
import pytest
from playwright.sync_api import Page, expect
from testData.testDataObjects import TestData
from pageObjectModel.commonPages.homePage import HomePage
from pageObjectModel.hotelPages.hotelDetailPage import HotelDetailPage
from pageObjectModel.hotelPages.hotelGuestInfoPage import HotelGuestInfoPage
from pageObjectModel.hotelPages.hotelListingPage import HotelListingPage
from pageObjectModel.hotelPages.hotelSearchPage import HotelSearchPage
from sharedUtilities.projectConfiguration import Settings

@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.all
def testE2HotelBookingFlow(
    authenticated_page: Page,
    home_page: HomePage,
    hotel_search_page: HotelSearchPage,
    hotel_listing_page: HotelListingPage,
    test_data: TestData,
    settings: Settings,
) -> None:
    assert authenticated_page is home_page.page
    home_page.navigate_to_hotels()
    hotel_data = test_data.hotel
    hotel_search_page.search(hotel_data)
    hotel_search_page.save_current_state("hotel-searched-state.json")
    hotel_page = hotel_listing_page.open_hotel_detail()
    hotel_detail_page = HotelDetailPage(hotel_page)
    if hotel_detail_page.click_book_now():
        if not settings.user_email:
            pytest.fail("USER_EMAIL is required for the hotel booking flow.")
        HotelGuestInfoPage(hotel_page).fill_info(
            hotel_data, settings.user_email
        )

@pytest.mark.regression
def testE10HotelRoomAndGuestCountArePreserved(
    authenticated_page: Page,
    home_page: HomePage,
    hotel_search_page: HotelSearchPage,
    hotel_listing_page: HotelListingPage,
    test_data: TestData,
) -> None:
    home_page.navigate_to_hotels()
    hotel_search_page.search(
        test_data.hotel, rooms=2, additional_adults=1, children=1
    )
    expect(authenticated_page).to_have_url(re.compile(r"/hotel/"))
    select_button = authenticated_page.locator("button").filter(
        has_text="Select"
    ).first
    expect(select_button).to_be_visible(timeout=60_000)
    expect(
        authenticated_page.locator("body")
    ).to_contain_text(re.compile(r"2 Rooms?, 4 Guests?"))