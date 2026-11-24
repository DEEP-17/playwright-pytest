from unittest.mock import Mock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pageObjectModel.flightPages.flightSeatMapPage import FlightSeatMapPage


def testFlightSeatMapContinuesToCheckoutWhenNoSeatsAreSelectable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = Mock()
    flight_container = Mock()
    flight_buttons = Mock()
    flight_buttons.count.return_value = 1
    flight_container.first.get_by_role.return_value = flight_buttons
    first_name_input = Mock()
    first_name = Mock()
    first_name.is_visible.return_value = False
    first_name_input.first = first_name

    def locator(selector: str) -> Mock:
        if selector.startswith("div.mb-40"):
            return flight_container
        return first_name_input

    page.locator.side_effect = locator

    no_seats_message = Mock()
    no_seats_message.wait_for.side_effect = PlaywrightTimeoutError("timeout")
    seat_count_message = Mock()
    seat_count_message.is_visible.return_value = True
    seat_count_message.inner_text.return_value = "Please select 1 seat"
    page.get_by_text.return_value.first = seat_count_message

    available_seats = Mock()
    available_seats.first.wait_for.side_effect = PlaywrightTimeoutError("timeout")
    available_seats.count.return_value = 0
    next_flight = Mock()
    next_flight.count.return_value = 0
    skip_button = Mock()

    def get_by_role(role: str, **kwargs: object) -> Mock:
        if role == "heading":
            return no_seats_message
        if role == "checkbox":
            return available_seats
        if kwargs.get("name") == "Next flight":
            return next_flight
        if kwargs.get("name") == "Skip/Move to Checkout...":
            return skip_button
        raise AssertionError(f"Unexpected role lookup: {role}")

    page.get_by_role.side_effect = get_by_role
    monkeypatch.setattr(FlightSeatMapPage, "save_current_state", lambda *_: None)

    no_seats_available = FlightSeatMapPage(page).handle_seats()

    assert no_seats_available is True
    skip_button.click.assert_called_once_with(force=True)
    first_name.wait_for.assert_called_once_with(
        state="visible", timeout=60_000
    )
