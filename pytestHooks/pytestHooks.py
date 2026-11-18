import os
import re
import warnings
from collections.abc import Generator
from pathlib import Path
import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from pytestHooks.browserDiagnostics import (
    BROWSER_DIAGNOSTICS,
    log_failure_diagnostics,
)

def _skip_reason(node_id: str, selectors: list[str]) -> str | None:
    matching = []
    for selection in selectors:
        selector, _, requested_reason = selection.partition("=")
        selector = selector.strip()
        requested_reason = requested_reason.strip()
        if re.fullmatch(r"[ec]\d+", selector, re.IGNORECASE):
            matches = re.search(
                rf"test{re.escape(selector)}(?!\d)", node_id, re.IGNORECASE
            )
        else:
            matches = re.search(re.escape(selector), node_id, re.IGNORECASE)
        if matches:
            matching.append(
                f"{selector} ({requested_reason})"
                if requested_reason
                else selector
            )
    if not matching:
        return None
    return "Skipped by --skip-case: " + ", ".join(matching)

def _skip_selectors(values: list[str]) -> list[str]:
    selectors = []
    for value in values:
        value = value.strip()
        if not value:
            continue
        if "=" in value:
            selectors.append(value)
        else:
            selectors.extend(
                selector.strip()
                for selector in value.split(",")
                if selector.strip()
            )
    return selectors

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--skip-case",
        action="append",
        default=[],
        metavar="ID_OR_NODE[=REASON]",
        help=(
            "Skip matching case IDs (for example C8) or node ID text, optionally "
            "with a reason such as C8=blocked by QA. Repeat the option for "
            "separate reasons; comma-separated selectors are supported without "
            "reasons."
        ),
    )

def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    selectors = _skip_selectors(config.getoption("skip_case"))
    for item in items:
        reason = _skip_reason(item.nodeid, selectors)
        if reason:
            item.add_marker(pytest.mark.skip(reason=reason))

def _prepare_output_directories(config: pytest.Config) -> None:
    (Path(config.rootpath) / "testResults").mkdir(parents=True, exist_ok=True)
    (Path(config.rootpath) / ".authenticationState").mkdir(parents=True, exist_ok=True)
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
    if report.failed:
        diagnostics = item.stash.get(BROWSER_DIAGNOSTICS, [])
        if diagnostics:
            item.add_report_section(
                report.when, "browser and UI diagnostics", "\n".join(diagnostics)
            )
            log_failure_diagnostics(item.nodeid, diagnostics)
    if report.when != "call" or not report.failed:
        return
    page = item.funcargs.get("page")
    if not isinstance(page, Page) or page.is_closed():
        return
    safe_node_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.nodeid).strip("_")
    screenshot_path = item.config.rootpath / "testResults" / "screenshots"
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