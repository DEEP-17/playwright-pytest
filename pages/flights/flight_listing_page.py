from pages.base.base_page import BasePage


class FlightListingPage(BasePage):
    def filter_and_select(self) -> None:
        self.log_step("Waiting for flight results")
        self.wait_for_dom()
        self.page.locator("span").filter(has_text="2 Stop").dispatch_event("click")

        slider = self.page.locator(".rc-slider").first
        box = slider.bounding_box()
        if box:
            self.log_step("Adjusting the price slider")
            center_y = box["y"] + box["height"] / 2
            self.page.mouse.move(box["x"] + 5, center_y)
            self.page.mouse.down()
            self.page.mouse.move(box["x"] + box["width"] * 0.3, center_y, steps=20)
            self.page.mouse.up()

        self.log_step("Filtering by Air Canada")
        self.page.locator('[id="Air Canada"]').click()
        self.wait_for_network()

        self.log_step("Sorting by earliest arrival")
        self.page.get_by_role(
            "button", name="Sort by : Price (low to high)"
        ).click()
        self.page.locator("p").filter(has_text="Arrival (earliest)").last.click(force=True)

        self.log_step("Selecting the first matching flight")
        self.page.locator("div.flex > section.flex > div.flex").first.click()
        self.log_step("Flight selected")
