import pytest
from playwright.sync_api import Page

from data.objects import TestData
from pages.common.home_page import HomePage
from pages.hotels.hotel_detail_page import HotelDetailPage
from pages.hotels.hotel_guest_info_page import HotelGuestInfoPage
from pages.hotels.hotel_listing_page import HotelListingPage
from pages.hotels.hotel_search_page import HotelSearchPage
from utils.config import Settings


@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.all
def test_hotel_booking_flow(
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
