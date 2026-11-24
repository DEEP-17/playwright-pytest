import json
import logging
from unittest.mock import Mock
import pytest
from pageObjectModel.basePage.basePage import BasePage
from sharedUtilities.structuredLogging import (
    FailureOnlyLogFilter,
    JsonLogFormatter,
    log_test_failure,
)

def testBasePageLogsStepsThroughPythonLogging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = BasePage(Mock())
    with caplog.at_level(logging.INFO, logger="pageObjectModel.basePage.basePage"):
        page.log_step("Opening flight search")
    assert "[BasePage] Opening flight search" in caplog.text


def testPytestFileLogHandlerUsesJsonFormatter(
    pytestconfig: pytest.Config,
) -> None:
    logging_plugin = pytestconfig.pluginmanager.get_plugin("logging-plugin")
    file_handler = getattr(logging_plugin, "log_file_handler", None)
    assert file_handler is not None
    assert isinstance(file_handler.formatter, JsonLogFormatter)
    assert any(
        isinstance(handler_filter, FailureOnlyLogFilter)
        for handler_filter in file_handler.filters
    )


def testFailureLogIncludesStructuredContextAndRedactedException(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USER_PASSWORD", "qa-secret")
    logger = logging.getLogger("pytest.failure")
    log_error = Mock()
    monkeypatch.setattr(logger, "error", log_error)

    log_test_failure(
        "testCases.endToEndTests.testFlight::testE1FlightBookingFlow",
        "call",
        "AssertionError: password=qa-secret\nExpected booking confirmation",
        "Captured log call\npassword=qa-secret\nBooking was not confirmed",
        ["[ui] Clicked button 'Book flight'"],
    )

    message, = log_error.call_args.args
    fields = log_error.call_args.kwargs["extra"]
    record = logging.LogRecord(
        logger.name, logging.ERROR, __file__, 1, message, (), None
    )
    for name, value in fields.items():
        setattr(record, name, value)
    entry = json.loads(JsonLogFormatter().format(record))

    assert entry["event"] == "test_failure"
    assert entry["test_node_id"].endswith("testE1FlightBookingFlow")
    assert entry["test_phase"] == "call"
    assert "Expected booking confirmation" in entry["exception"]
    assert "qa-secret" not in entry["exception"]
    assert "password=[REDACTED]" in entry["exception"]
    assert "Booking was not confirmed" in entry["captured_logs"]
    assert "qa-secret" not in entry["captured_logs"]
    assert "Book flight" in entry["browser_diagnostics"][0]
