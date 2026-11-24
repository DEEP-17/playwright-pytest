import re
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pageObjectModel.basePage.basePage import BasePage


class FlightSeatMapPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.flight_buttons = (
            page.locator("div.mb-40 > div.flex > div.flex")
            .first.get_by_role("button", name="Flight", exact=False)
        )
        self.no_seat_heading = page.get_by_role(
            "heading",
            name="Seat booking is not available for this flight",
            level=4,
        )
        self.seat_count_message = page.get_by_text(
            re.compile(r"Please select\s+\d+\s+seat", re.IGNORECASE)
        ).first
        self.available_seat_checkboxes = page.get_by_role("checkbox")
        self.first_name_input = page.locator('input[name^="firstName"]').first
        self.next_flight_button = page.get_by_role("button", name="Next flight")
        self.skip_to_checkout_button = page.get_by_role(
            "button", name="Skip/Move to Checkout..."
        )

    # --- Actions ---
    def handle_seats(self) -> bool:
        self.flight_buttons.first.wait_for(state="visible")
        no_seats_available = False
        for index in range(self.flight_buttons.count()):
            self.flight_buttons.nth(index).click(force=True)
            try:
                self.no_seat_heading.wait_for(state="visible", timeout=1_000)
            except PlaywrightTimeoutError:
                pass
            else:
                no_seats_available = True
                self.log_step(f"No seats are available in Flight {index + 1}")
                continue
            if not self.seat_count_message.is_visible():
                raise RuntimeError(
                    f"Flight {index + 1} has neither a no-seats message "
                    "nor a passenger seat count."
                )
            seat_count_match = re.search(
                r"Please select\s+(\d+)\s+seat",
                self.seat_count_message.inner_text(),
                re.IGNORECASE,
            )
            if seat_count_match is None:
                raise RuntimeError(
                    f"Could not read the number of seats required for Flight {index + 1}."
                )
            required_seats = int(seat_count_match.group(1))
            try:
                self.available_seat_checkboxes.first.wait_for(state="visible", timeout=5_000)
            except PlaywrightTimeoutError:
                pass
            selected = 0
            for seat_index in range(self.available_seat_checkboxes.count()):
                seat = self.available_seat_checkboxes.nth(seat_index)
                if not seat.is_visible() or not seat.is_enabled():
                    continue
                if not seat.is_checked():
                    seat.click(force=True)
                if seat.is_checked():
                    selected += 1
                if selected == required_seats:
                    break
            if selected != required_seats:
                if selected == 0:
                    no_seats_available = True
                    self.log_step(
                        f"No selectable seats are available in Flight {index + 1}"
                    )
                    continue
                raise RuntimeError(
                    f"Flight {index + 1} requires {required_seats} seats, "
                    f"but only {selected} selectable seats were found."
                )
            self.log_step(f"Selected {selected} seats for Flight {index + 1}")
        if self.next_flight_button.count() and self.next_flight_button.is_visible():
            self.next_flight_button.click(force=True)
            try:
                self.first_name_input.wait_for(state="visible", timeout=5_000)
            except PlaywrightTimeoutError:
                pass
        if not self.first_name_input.is_visible():
            repricing_errors: list[str] = []

            def capture_repricing_error(error: Exception) -> None:
                message = str(error)
                if "Unable to get the reprice data" in message:
                    repricing_errors.append(message)
            self.page.on("pageerror", capture_repricing_error)
            try:
                self.skip_to_checkout_button.click(force=True)
                self.page.wait_for_url("**/flights/travellerinfo/**", timeout=60_000)
                self.first_name_input.wait_for(state="visible", timeout=60_000)
            except PlaywrightTimeoutError as error:
                if repricing_errors:
                    raise RuntimeError(
                        "Flight repricing failed while opening passenger details: "
                        f"{repricing_errors[-1]}"
                    ) from error
                raise RuntimeError(
                    "Flight checkout did not finish loading passenger details "
                    f"at {self.page.url}."
                ) from error
            finally:
                self.page.remove_listener("pageerror", capture_repricing_error)
        if no_seats_available:
            self.log_step("Continuing to checkout without selecting a seat")
        self.save_current_state("flight-traveller-details-state.json")
        return no_seats_available
