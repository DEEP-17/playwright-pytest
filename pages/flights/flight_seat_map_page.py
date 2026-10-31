import re

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage


class FlightSeatMapPage(BasePage):
    def handle_seats(self) -> bool:
        flights = (
            self.page.locator("div.mb-40 > div.flex > div.flex")
            .first.get_by_role("button", name="Flight", exact=False)
        )
        flights.first.wait_for(state="visible")

        no_seats_available = False
        for index in range(flights.count()):
            flights.nth(index).click(force=True)
            no_seat = self.page.get_by_role(
                "heading",
                name="Seat booking is not available for this flight",
                level=4,
            )
            try:
                no_seat.wait_for(state="visible", timeout=1_000)
            except PlaywrightTimeoutError:
                pass
            else:
                no_seats_available = True
                self.log_step(f"No seats are available in Flight {index + 1}")
                continue

            seat_count_message = self.page.get_by_text(
                re.compile(r"Please select\s+\d+\s+seat", re.IGNORECASE)
            ).first
            if not seat_count_message.is_visible():
                raise RuntimeError(
                    f"Flight {index + 1} has neither a no-seats message "
                    "nor a passenger seat count."
                )
            seat_count_match = re.search(
                r"Please select\s+(\d+)\s+seat",
                seat_count_message.inner_text(),
                re.IGNORECASE,
            )
            if seat_count_match is None:
                raise RuntimeError(
                    f"Could not read the number of seats required for Flight {index + 1}."
                )

            required_seats = int(seat_count_match.group(1))
            available_seats = self.page.get_by_role("checkbox")
            selected = 0
            for seat_index in range(available_seats.count()):
                seat = available_seats.nth(seat_index)
                if not seat.is_visible() or not seat.is_enabled():
                    continue
                if not seat.is_checked():
                    seat.click(force=True)
                if seat.is_checked():
                    selected += 1
                if selected == required_seats:
                    break
            if selected != required_seats:
                raise RuntimeError(
                    f"Flight {index + 1} requires {required_seats} seats, "
                    f"but only {selected} selectable seats were found."
                )
            self.log_step(
                f"Selected {selected} seats for Flight {index + 1}"
            )

        first_name = self.page.locator('input[name^="firstName"]').first
        next_flight = self.page.get_by_role("button", name="Next flight")
        if next_flight.count() and next_flight.is_visible():
            next_flight.click(force=True)
            try:
                first_name.wait_for(state="visible", timeout=5_000)
            except PlaywrightTimeoutError:
                pass

        if not first_name.is_visible():
            self.page.get_by_role(
                "button", name="Skip/Move to Checkout..."
            ).click(force=True)
            first_name.wait_for(state="visible", timeout=30_000)
        if no_seats_available:
            self.log_step("Continuing to checkout without selecting a seat")
        self.save_current_state("flight-traveller-details-state.json")
        return no_seats_available
