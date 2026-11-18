import os
import re
import warnings
from collections.abc import Generator
from pathlib import Path
import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from hooks.browser_diagnostics import BROWSER_DIAGNOSTICS

def _skip_reason(node_id: str, selectors: list[str]) -> str | None:
    matching = []
    for selector in selectors:
        if re.fullmatch(r"[ec]\d+", selector, re.IGNORECASE):
            matches = re.search(
                rf"test{re.escape(selector)}(?!\d)", node_id, re.IGNORECASE
            )
        else:
            matches = re.search(re.escape(selector), node_id, re.IGNORECASE)
        if matches:
            matching.append(selector)
    if not matching:
        return None
    return "Skipped by --skip-case: " + ", ".join(matching)

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--skip-case",
        action="append",
        default=[],
        metavar="ID_OR_NODE",
        help=(
            "Skip matching case IDs (for example C8) or node ID text; "
            "may be repeated or comma-separated."
        ),
    )

def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    selectors = [
        selector.strip()
        for value in config.getoption("skip_case")
        for selector in value.split(",")
        if selector.strip()
    ]
    for item in items:
        reason = _skip_reason(item.nodeid, selectors)
        if reason:
            item.add_marker(pytest.mark.skip(reason=reason))

def _prepare_output_directories(config: pytest.Config) -> None:
    (Path(config.rootpath) / "test-results").mkdir(parents=True, exist_ok=True)
    (Path(config.rootpath) / ".auth").mkdir(parents=True, exist_ok=True)
    html_path = getattr(config.option, "htmlpath", None)
    if html_path:
        report_path = Path(os.path.expandvars(html_path)).expanduser()
        if not report_path.is_absolute():
            report_path = Path(config.invocation_params.dir) / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)

def pytest_sessionstart(session: pytest.Session) -> None:
    _prepare_output_directories(session.config)

def pytest_runtest_setup(item: pytest.Item) -> None:
    _prepare_output_directories(item.config)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, None, None]:
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        diagnostics = item.stash.get(BROWSER_DIAGNOSTICS, [])
        if diagnostics:
            item.add_report_section(
                "call", "browser diagnostics", "\n".join(diagnostics)
            )
    if report.when != "call" or not report.failed:
        return
    page = item.funcargs.get("page")
    if not isinstance(page, Page) or page.is_closed():
        return
    safe_node_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.nodeid).strip("_")
    screenshot_path = item.config.rootpath / "test-results" / "screenshots"
    screenshot_path.mkdir(parents=True, exist_ok=True)
    screenshot = screenshot_path / f"{safe_node_id}.png"
    try:
        page.screenshot(path=str(screenshot), full_page=True)
    except (OSError, PlaywrightError) as error:
        warnings.warn(
            pytest.PytestWarning(
                f"Could not capture failure screenshot for {item.nodeid}: {error}"
            ),
            stacklevel=2,
        )
        return
    item.add_report_section("call", "failure screenshot", str(screenshot))