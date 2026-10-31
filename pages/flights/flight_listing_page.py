import re

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base.base_page import BasePage


class FlightListingPage(BasePage):
    def wait_for_results(self, timeout: int = 60_000) -> bool:
        first_result = self.page.locator("div.flex > section.flex > div.flex").first
        try:
            first_result.wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError:
            return False
        return True

    def filter_and_select(self) -> None:
        self.log_step("Waiting for flight results")
        self.wait_for_dom()
        if not self.wait_for_results():
            raise RuntimeError("Flight search completed without displaying results.")
        self.save_current_state("flight-results-state.json")

        stop_filter = self.page.get_by_text(re.compile(r"^2 Stops?$")).first
        if stop_filter.count() and stop_filter.is_visible():
            stop_filter.dispatch_event("click")
        else:
            self.log_step("Two-stop filter is not available for these results")

        slider = self.page.locator(".rc-slider").first
        box = slider.bounding_box()
        if box:
            self.log_step("Adjusting the price slider")
            center_y = box["y"] + box["height"] / 2
            self.page.mouse.move(box["x"] + 5, center_y)
            self.page.mouse.down()
            self.page.mouse.move(box["x"] + box["width"] * 0.3, center_y, steps=20)
            self.page.mouse.up()

        airline_filter = self.page.locator('[id="Air Canada"]')
        if airline_filter.count() and airline_filter.first.is_visible():
            self.log_step("Filtering by Air Canada")
            airline_filter.first.click()
            self.wait_for_network()
        else:
            self.log_step("Air Canada filter is not available for these results")

        sort_button = self.page.get_by_role(
            "button", name="Sort by : Price (low to high)"
        )
        if sort_button.count() and sort_button.is_visible():
            self.log_step("Sorting by earliest arrival")
            sort_button.click()
            arrival_sort = self.page.locator("p").filter(
                has_text="Arrival (earliest)"
            ).last
            if arrival_sort.count() and arrival_sort.is_visible():
                arrival_sort.click(force=True)
        self.log_step("Selecting the first matching flight")
        first_result = self.page.locator("div.flex > section.flex > div.flex").first
        first_result.click()
        self.page.wait_for_url("**/flights/trip-summary/**", timeout=60_000)
        self.save_current_state("flight-selected-state.json")
        self.log_step("Flight selected")
