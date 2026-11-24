from unittest.mock import Mock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pageObjectModel.flightPages.flightTripSummaryPage import (
    FlightTripSummaryPage,
)


def testFlightTripSummaryWaitsForCheckoutWithoutReloading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = Mock()
    continue_button = page.get_by_role.return_value
    page.get_by_text.return_value.is_visible.return_value = False
    page.locator.return_value.wait_for.side_effect = PlaywrightTimeoutError(
        "Seat selection link did not appear."
    )
    continue_button.wait_for.side_effect = [
        PlaywrightTimeoutError("Trip summary is still loading."),
        None,
    ]
    summary_page = FlightTripSummaryPage(page)
    monkeypatch.setattr(summary_page, "save_current_state", lambda *_: None)

    summary_page.proceed()

    assert continue_button.wait_for.call_count == 2
    page.reload.assert_not_called()
    continue_button.click.assert_called_once()
