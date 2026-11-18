import logging
from unittest.mock import Mock
import pytest
from pageObjectModel.basePage.basePage import BasePage

def testBasePageLogsStepsThroughPythonLogging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = BasePage(Mock())
    with caplog.at_level(logging.INFO, logger="pageObjectModel.basePage.basePage"):
        page.log_step("Opening flight search")
    assert "[BasePage] Opening flight search" in caplog.text
