import re
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from pageObjectModel.basePage.basePage import BasePage


class FlightListingPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.first_result = page.locator("div.flex > section.flex > div.flex").first
        self.results_count_text = page.get_by_text(
            re.compile(r"\d+\s+results found", re.IGNORECASE)
        ).first
        self.two_stop_filter = page.get_by_text(re.compile(r"^2 Stops?$")).first
        self.price_slider = page.locator(".rc-slider").first
        self.air_canada_filter = page.locator('[id="Air Canada"]')
        self.sort_by_price_button = page.get_by_role(
            "button", name="Sort by : Price (low to high)"
        )
        self.arrival_earliest_option = page.locator("p").filter(
            has_text="Arrival (earliest)"
        ).last

    # --- Actions ---
    def wait_for_results(self, timeout: int = 60_000) -> bool:
        try:
            self.first_result.wait_for(state="visible", timeout=min(timeout, 10_000))
        except PlaywrightTimeoutError:
            try:
                self.results_count_text.wait_for(state="visible", timeout=timeout)
            except PlaywrightTimeoutError:
                return False
            result_count = re.search(r"\d+", self.results_count_text.inner_text())
            return result_count is not None and int(result_count.group()) > 0
        return True

    def filter_and_select(self) -> None:
        self.log_step("Waiting for flight results")
        self.wait_for_dom()
        if not self.wait_for_results():
            raise RuntimeError("Flight search completed without displaying results.")
        self.save_current_state("flight-results-state.json")
        if self.two_stop_filter.count() and self.two_stop_filter.is_visible():
            self.two_stop_filter.dispatch_event("click")
        else:
            self.log_step("Two-stop filter is not available for these results")
        box = self.price_slider.bounding_box()
        if box:
            self.log_step("Adjusting the price slider")
            center_y = box["y"] + box["height"] / 2
            self.page.mouse.move(box["x"] + 5, center_y)
            self.page.mouse.down()
            self.page.mouse.move(box["x"] + box["width"] * 0.3, center_y, steps=20)
            self.page.mouse.up()
        if self.air_canada_filter.count() and self.air_canada_filter.first.is_visible():
            self.log_step("Filtering by Air Canada")
            self.air_canada_filter.first.click()
            self.wait_for_network()
        else:
            self.log_step("Air Canada filter is not available for these results")
        if self.sort_by_price_button.count() and self.sort_by_price_button.is_visible():
            self.log_step("Sorting by earliest arrival")
            self.sort_by_price_button.click()
            if self.arrival_earliest_option.count() and self.arrival_earliest_option.is_visible():
                self.arrival_earliest_option.click(force=True)
        self.select_first_result()

    def select_first_result(self) -> None:
        self.log_step("Selecting the first matching flight")
        self.first_result.wait_for(state="visible", timeout=60_000)
        self.first_result.click()
        self.page.wait_for_url("**/flights/trip-summary/**", timeout=60_000)
        self.save_current_state("flight-selected-state.json")
        self.log_step("Flight selected")
