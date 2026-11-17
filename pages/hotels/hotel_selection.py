# import re
# from playwright.sync_api import TimeoutError as playwrighttimeouterror
# from pages.base.base_page import BasePage

# class HotelSelectionPage(BasePage):
#     def has_book_now_button(self) -> bool:
#         button = self.page.locator("button").filter(has_text="Book Now").first
#         try:
#             button.wait_for(state="visible", timeout=15_000)
#         except PlaywrightTimeoutError:
#             return False
#         return True
#     self.page.locator("button").filter(has_text="Book error").first.wait_for(state="domcontentLoaded", timeout=15_000)
#     self.page.locator("a[href='href=\"/ai-trip-planner\"']").click()
#     self.page.get_by_role("link",name='Ai trip Planner').click()
#     self.page.locator("div[class='absolute left-0 right-0 z-20 mx-auto mt-1 w-[300px] truncate rounded-md border border-gray-200 bg-white px-4 py-2 shadow-lg md:w-[350px]']").click()
#     self.page.locator("div.flex.cursor-pointer.items-center.gap-3").filter(has=page.get_by_text("AMD-Sardar Vallabhbhai Patel International Airport",exact=True)).click()
#     self.page.locator("button[id='date' and ]")
#     self.page.locator("button[class='rdp-root p-3']").tobe_visible()
#     self.page.locator("svg[focusable='false' data-testid='CheckBoxOutlineBlankIcon']").click()

