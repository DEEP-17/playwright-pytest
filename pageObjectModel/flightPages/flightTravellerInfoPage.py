from playwright.sync_api import Page
from testData.testDataObjects import FlightData
from pageObjectModel.basePage.basePage import BasePage


class FlightTravellerInfoPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.first_passenger_field = page.locator('input[name="firstName1"]')
        self.all_first_name_fields = page.locator('input[name^="firstName"]')
        self.address_field = page.locator('input[name="adress"]')
        self.zip_code_field = page.locator('input[name="zipcode"]')
        self.city_field = page.locator('input[name="city"]')
        self.email_field = page.locator('input[name="email"]')
        self.phone_field = page.locator('input[name="phone"]')
        self.male_gender_option = page.get_by_role("option", name="Male", exact=True)

    # Per-passenger indexed locators (returned as needed by index)
    def first_name_field(self, index: int):
        return self.page.locator(f'input[name="firstName{index}"]')

    def middle_name_field(self, index: int):
        return self.page.locator(f'input[name="middleName{index}"]')

    def last_name_field(self, index: int):
        return self.page.locator(f'input[name="lastName{index}"]')

    def dob_field(self, index: int):
        return self.page.locator(f'input[name="DOB{index}"]')

    # --- Actions ---
    def fill_info(self, data: FlightData, email: str) -> None:
        self.first_passenger_field.wait_for(state="visible")
        passenger_count = self.all_first_name_fields.count()
        for index in range(1, passenger_count + 1):
            first_name = self.first_name_field(index)
            if not first_name.is_visible():
                break
            passenger = data.passenger
            first_name.fill(passenger.first_name)
            self.middle_name_field(index).fill(passenger.middle_name)
            self.last_name_field(index).fill(passenger.last_name)
            self.dob_field(index).fill(passenger.date_of_birth)
            self.page.get_by_role("combobox").nth(index * 2 - 1).click()
            self.male_gender_option.click()
        contact = data.contact
        self.address_field.fill(contact.address)
        self.zip_code_field.fill(contact.zip_code)
        self.city_field.fill(contact.city)
        self.email_field.fill(email)
        self.phone_field.fill(contact.phone)
