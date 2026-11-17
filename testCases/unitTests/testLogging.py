import logging
from unittest.mock import Mock

import pytest

from pages.base.base_page import BasePage


def testBasePageLogsStepsThroughPythonLogging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = BasePage(Mock())

    with caplog.at_level(logging.INFO, logger="pages.base.base_page"):
        page.log_step("Opening flight search")

    assert "[BasePage] Opening flight search" in caplog.text
