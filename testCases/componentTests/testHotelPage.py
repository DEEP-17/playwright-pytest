from unittest.mock import Mock

import pytest

from pageObjectModel.hotelPages.hotelDetailPage import HotelDetailPage
from pageObjectModel.hotelPages.hotelSearchPage import HotelSearchPage


def testHotelLocationWaitsForAutocompleteWithoutFixedSleep() -> None:
    page = Mock()
    textbox = page.get_by_role.return_value
    location_option = page.locator.return_value.filter.return_value.first

    HotelSearchPage(page)._select_location(
        "hyderabad", "HYD, Hyderabad, India"
    )

    textbox.fill.assert_called_once_with("hyderabad")
    location_option.wait_for.assert_called_once_with(
        state="visible", timeout=30_000
    )
    location_option.click.assert_called_once_with(timeout=10_000)
    page.wait_for_timeout.assert_not_called()


def testHotelBookNowWaitsUntilButtonBecomesVisible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = Mock()
    button_locator = Mock()
    book_now = Mock()
    button_locator.filter.return_value.first = book_now
    email_field = Mock()
    page.locator.side_effect = lambda selector: (
        button_locator if selector == "button" else email_field
    )
    monkeypatch.setattr(HotelDetailPage, "save_current_state", lambda *_: None)

    assert HotelDetailPage(page).click_book_now()

    book_now.wait_for.assert_called_once_with(state="visible", timeout=15_000)
    book_now.click.assert_called_once()
    book_now.is_visible.assert_not_called()
