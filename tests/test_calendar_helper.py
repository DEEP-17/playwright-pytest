from datetime import date

import pytest

from helpers.calendar_helper import calendar_date_label, days_from_today, ordinal


@pytest.mark.all
@pytest.mark.parametrize(
    ("day", "expected"),
    [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (12, "12th"), (13, "13th"), (21, "21st"), (22, "22nd"), (23, "23rd"), (31, "31st")],
)
def test_ordinal(day: int, expected: str) -> None:
    assert ordinal(day) == expected


@pytest.mark.all
def test_days_from_today_and_calendar_label() -> None:
    target = days_from_today(1, date(2026, 10, 26))

    assert (target.year, target.month, target.day, target.hour) == (2026, 10, 27, 12)
    assert calendar_date_label(target) == "Tuesday, October 27th, 2026"
