from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage


class FlightSeatMapPage(BasePage):
    def handle_seats(self) -> None:
        flights = (
            self.page.locator("div.mb-40 > div.flex > div.flex")
            .first.get_by_role("button", name="Flight", exact=False)
        )
        flights.first.wait_for(state="visible")

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
                self.log_step(f"Found available seat in Flight {index + 1}")
                break

        seat_label = self.page.locator("label").first
        try:
            seat_label.click(force=True)
        except PlaywrightTimeoutError:
            self.page.locator('input[type="radio"]').first.click(force=True)
        self.page.get_by_role(
            "button", name="Skip/Move to Checkout..."
        ).click(force=True)
