from pathlib import Path

from playwright.sync_api import Page

from utils.session_state import save_browser_state

from helpers.calendar_helper import (
    calendar_date_label,
    days_from_today,
    select_date_in_open_calendar,
)


class BasePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def log_step(self, message: str) -> None:
        print(f"[STAGE] [{type(self).__name__}] {message}")

    def save_current_state(self, file_name: str) -> Path:
        state_files = save_browser_state(self.page.context, file_name)
        self.log_step(f"Browser state saved to {state_files.storage_state}")
        return state_files.storage_state

    def wait_for_network(self) -> None:
        self.page.wait_for_load_state("networkidle")

    def wait_for_dom(self) -> None:
        self.page.wait_for_load_state("domcontentloaded")

    def select_calendar_date(self, days_ahead: int = 15):
        target_date = days_from_today(days_ahead)
        self.log_step(f"Selecting calendar date: {calendar_date_label(target_date)}")
        select_date_in_open_calendar(self.page, target_date)
        self.log_step(f"Calendar date selected: {calendar_date_label(target_date)}")
        return target_date
