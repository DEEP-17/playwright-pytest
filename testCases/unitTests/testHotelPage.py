from unittest.mock import Mock

import pytest

from pageObjectModel.hotelPages.hotelDetailPage import HotelDetailPage


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
