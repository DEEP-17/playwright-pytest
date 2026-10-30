import calendar
import re
from datetime import date, datetime, time, timedelta

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

MONTHS = tuple(calendar.month_name[1:])


def ordinal(day: int) -> str:
    if 11 <= day % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def days_from_today(days: int, today: date | None = None) -> datetime:
    base_date = today or date.today()
    target = base_date + timedelta(days=days)
    return datetime.combine(target, time(hour=12))


def calendar_date_label(target: date | datetime) -> str:
    return (
        f"{target.strftime('%A')}, {MONTHS[target.month - 1]} "
        f"{ordinal(target.day)}, {target.year}"
    )


def select_date_in_open_calendar(
    page: Page, target_date: date | datetime, maximum_month_changes: int = 24
) -> None:
    full_label = calendar_date_label(target_date)
    label_without_year = full_label.rsplit(" ", 1)[0]
    date_name = re.compile(
        rf"^{re.escape(label_without_year)}(?: {target_date.year})?$"
    )

    for attempt in range(maximum_month_changes + 1):
        date_buttons = page.get_by_role("button", name=date_name)
        for index in range(date_buttons.count()):
            date_button = date_buttons.nth(index)
            if date_button.is_visible() and date_button.is_enabled():
                date_button.click()
                return

        if attempt == maximum_month_changes:
            break

        navigation_name = (
            "Go to the Next Month"
            if (
                target_date.date() if isinstance(target_date, datetime) else target_date
            ) >= datetime.now().date()
            else "Go to the Previous Month"
        )
        navigation_button = page.get_by_role("button", name=navigation_name)
        try:
            navigation_button.wait_for(state="visible", timeout=2_000)
        except PlaywrightTimeoutError as error:
            raise RuntimeError(
                f"Could not find {full_label} or the calendar navigation button."
            ) from error
        navigation_button.click()

    raise RuntimeError(
        f"Could not select {full_label} after {maximum_month_changes} month changes."
    )
