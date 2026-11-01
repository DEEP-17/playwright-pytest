import pytest
from playwright.sync_api import Browser

from hooks.browser_diagnostics import (
    BROWSER_DIAGNOSTICS,
    _safe_message,
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
    assert "token=private" not in message


def test_ui_click_fill_and_selection_are_logged(
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
    assert all("[request]" not in event and "[response]" not in event for event in diagnostics)
