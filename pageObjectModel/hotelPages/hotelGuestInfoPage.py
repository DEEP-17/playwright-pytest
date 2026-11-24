from playwright.sync_api import Page
from testData.testDataObjects import HotelData
from pageObjectModel.basePage.basePage import BasePage


class HotelGuestInfoPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # --- Locators ---
        self.first_name_field = page.get_by_role("textbox", name="Ex. John")
        self.last_name_field = page.get_by_role("textbox", name="Ex. Smith")
        self.age_field = page.get_by_role("textbox", name="Ex. 35")
        self.gender_dropdown = page.get_by_role("combobox").filter(
            has_text="Select your gender"
        )
        self.male_gender_option = page.get_by_role("option", name="Male", exact=True)
        self.address_field = page.locator('input[name="adress"]')
        self.zip_code_field = page.locator('input[name="zipcode"]')
        self.city_field = page.locator('input[name="city"]')
        self.email_field = page.locator('input[name="email"]')
        self.phone_field = page.locator('input[name="phone"]')

    # --- Actions ---
    def fill_info(self, data: HotelData, email: str) -> None:
        guest = data.guest
        self.first_name_field.fill(guest.first_name)
        self.last_name_field.fill(guest.last_name)
        self.age_field.fill(guest.age)
        self.gender_dropdown.click()
        self.male_gender_option.click()
        contact = data.contact
        self.address_field.fill(contact.address)
        self.zip_code_field.fill(contact.zip_code)
        self.city_field.fill(contact.city)
        self.email_field.fill(email)
        self.phone_field.fill(contact.phone)
