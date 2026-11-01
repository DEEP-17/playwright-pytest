import pytest
from playwright.sync_api import Browser

from hooks.browser_diagnostics import (
    BROWSER_DIAGNOSTICS,
    _safe_message,
    _safe_url,
    attach_browser_diagnostics,
)


def test_diagnostics_redact_credentials_and_query_strings(
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
    assert "user:pass" not in message
    assert "token=private" not in message
    assert _safe_url("https://example.test/path?token=private") == (
        "https://example.test/path"
    )


def test_browser_console_events_are_recorded(
    browser: Browser, request: pytest.FixtureRequest
) -> None:
    page = browser.new_page()
    try:
        attach_browser_diagnostics(page, request.node)
        page.route(
            "**/*",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body="<html><body>diagnostics</body></html>",
            ),
        )
        page.goto("https://diagnostics.example.test/status?token=private")
        page.evaluate("console.info('captured diagnostic event')")
    finally:
        page.close()

    diagnostics = request.node.stash[BROWSER_DIAGNOSTICS]
    assert any("captured diagnostic event" in event for event in diagnostics)
    assert any(
        "[request] GET https://diagnostics.example.test/status" in event
        for event in diagnostics
    )
    assert any(
        "[response] 200 GET https://diagnostics.example.test/status" in event
        for event in diagnostics
    )
    assert all("token=private" not in event for event in diagnostics)
