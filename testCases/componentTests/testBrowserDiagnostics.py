import logging
from unittest.mock import Mock, call

import pytest
from playwright.sync_api import Browser
from pytestHooks.browserDiagnostics import (
    BROWSER_DIAGNOSTICS,
    _safe_message,
    attach_browser_diagnostics,
    log_failure_diagnostics,
)

def testDiagnosticsRedactCredentialsAndQueryStrings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USER_EMAIL", "qa@example.test")
    monkeypatch.setenv("USER_PASSWORD", "test-password")

    message = _safe_message(
        "login qa@example.test password=test-password "
        "https://user:pass@example.test/path?token=private"
    )
    assert "qa@example.test" not in message
    assert "test-password" not in message
    assert "token=private" not in message

def testUiClickFillAndSelectionAreCapturedWithoutLiveLogs(
    browser: Browser,
    request: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = browser.new_page()
    try:
        attach_browser_diagnostics(page, request.node)
        page.route(
            "**/*",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body=(
                    '<label for="origin">Departing from?</label>'
                    '<input id="origin" type="text">'
                    '<label for="cabin">Cabin</label>'
                    '<select id="cabin">'
                    '<option value="economy">Economy</option>'
                    '<option value="business">Business class</option>'
                    '</select>'
                    '<button type="button">Search</button>'
                ),
            ),
        )
        with caplog.at_level(logging.INFO, logger="playwright.ui"):
            page.goto("https://diagnostics.example.test/")
            page.get_by_role("textbox", name="Departing from?").fill("Toronto")
            page.get_by_role("combobox", name="Cabin").select_option("business")
            page.get_by_role("button", name="Search").click()
    finally:
        page.close()
    diagnostics = request.node.stash[BROWSER_DIAGNOSTICS]
    assert any(
        "[ui] Filled textbox 'Departing from?'" in event
        for event in diagnostics
    )
    assert any(
        "[ui] Selected dropdown 'Cabin: Business class'" in event
        for event in diagnostics
    )
    assert any(
        "[ui] Clicked button 'Search'" in event
        for event in diagnostics
    )
    assert not [
        record for record in caplog.records if record.name == "playwright.ui"
    ]
    assert all("[request]" not in event and "[response]" not in event for event in diagnostics)

def testFailureDiagnosticsReplayUiAndBrowserLogsWithDistinctLevels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure_logger = logging.getLogger("pytest.failure")
    ui_logger = logging.getLogger("playwright.ui")
    browser_logger = logging.getLogger("playwright.browser")
    failure_error = Mock()
    ui_log = Mock()
    browser_warning = Mock()
    browser_error = Mock()
    monkeypatch.setattr(failure_logger, "error", failure_error)
    monkeypatch.setattr(ui_logger, "log", ui_log)
    monkeypatch.setattr(browser_logger, "warning", browser_warning)
    monkeypatch.setattr(browser_logger, "error", browser_error)

    diagnostics = [
        "[ui] Clicked button 'Search'",
        "[console:warning] A browser warning.",
        "[console:error] A browser error.",
        "[pageerror] An uncaught page error.",
    ]
    log_failure_diagnostics(
        "testCases.endToEndTests.testFlight::testSearch", diagnostics
    )

    failure_error.assert_called_once_with(
        "Browser and UI diagnostics for failed test %s:",
        "testCases.endToEndTests.testFlight::testSearch",
    )
    ui_log.assert_called_once_with(
        logging.getLevelName("UI"), diagnostics[0]
    )
    browser_warning.assert_called_once_with(diagnostics[1])
    browser_error.assert_has_calls([call(diagnostics[2]), call(diagnostics[3])])

def testBrowserWarningsAndErrorsAreQuietButRetainedInDiagnostics(
    browser: Browser,
    request: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = browser.new_page()
    try:
        attach_browser_diagnostics(page, request.node)
        with caplog.at_level(logging.INFO):
            with page.expect_event("pageerror", timeout=5_000):
                page.evaluate(
                    """() => {
                        console.warn(
                            "Mixed Content: The page was loaded over HTTPS, but requested "
                            + "an insecure element. This request was automatically upgraded "
                            + "to HTTPS."
                        );
                        console.warn("An unrelated browser warning.");
                        console.error("An application console error.");
                        setTimeout(
                            () => { throw new Error("An uncaught page error."); },
                            0
                        );
                    }"""
                )
    finally:
        page.close()
    diagnostics = request.node.stash[BROWSER_DIAGNOSTICS]
    assert not any("Mixed Content:" in event for event in diagnostics)
    assert any("An unrelated browser warning." in event for event in diagnostics)
    assert any("An application console error." in event for event in diagnostics)
    assert any("An uncaught page error." in event for event in diagnostics)
    assert "An unrelated browser warning." not in caplog.text
    assert "An application console error." not in caplog.text
    assert "An uncaught page error." not in caplog.text