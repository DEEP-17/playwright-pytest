from data.objects import HotelData

from pages.base.base_page import BasePage


class HotelGuestInfoPage(BasePage):
    def fill_info(self, data: HotelData, email: str) -> None:
        guest = data.guest
        self.page.get_by_role("textbox", name="Ex. John").fill(guest.first_name)
        self.page.get_by_role("textbox", name="Ex. Smith").fill(guest.last_name)
        self.page.get_by_role("textbox", name="Ex. 35").fill(guest.age)
        self.page.get_by_role("combobox").filter(
            has_text="Select your gender"
        ).click()
        self.page.get_by_role("option", name="Male", exact=True).click()
        contact = data.contact
        self.page.locator('input[name="adress"]').fill(contact.address)
        self.page.locator('input[name="zipcode"]').fill(contact.zip_code)
        self.page.locator('input[name="city"]').fill(contact.city)
        self.page.locator('input[name="email"]').fill(email)
        self.page.locator('input[name="phone"]').fill(contact.phone)
