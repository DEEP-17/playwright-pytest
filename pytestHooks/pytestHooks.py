import json
import logging
import os
import re
import shutil
import warnings
from collections.abc import Generator
from pathlib import Path
import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from sharedUtilities.structuredLogging import (
    FailureOnlyLogFilter,
    JsonLogFormatter,
    log_test_failure,
)
from pytestHooks.browserDiagnostics import (
    BROWSER_DIAGNOSTICS,
    log_failure_diagnostics,
)

_UI_LOG_LEVEL = 25


def pytest_configure(config: pytest.Config) -> None:
    logging.addLevelName(_UI_LOG_LEVEL, "UI")
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")
    cli_handler = getattr(logging_plugin, "log_cli_handler", None)
    formatter = getattr(cli_handler, "formatter", None)
    if formatter is not None and hasattr(formatter, "add_color_level"):
        formatter.add_color_level("UI", "cyan", bold=True)


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
    state_directory = Path(session.config.rootpath) / ".authenticationState"
    if state_directory.is_symlink():
        raise pytest.UsageError(
            "Refusing to clean an authentication-state symbolic link."
        )
    if state_directory.exists():
        shutil.rmtree(state_directory)

    logging_plugin = session.config.pluginmanager.get_plugin("logging-plugin")
    file_handler = getattr(logging_plugin, "log_file_handler", None)
    if file_handler is None:
        raise pytest.UsageError(
            "Pytest file logging is unavailable; structured test logs "
            "cannot be configured."
        )
    file_handler.setFormatter(JsonLogFormatter())
    file_handler.addFilter(FailureOnlyLogFilter())
    _prepare_output_directories(session.config)
    evidence_path = (
        Path(session.config.rootpath)
        / "testResults"
        / "session-state-evidence.json"
    )
    if evidence_path.exists():
        evidence_path.unlink()


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    root = Path(session.config.rootpath)
    state_directory = root / ".authenticationState"
    if state_directory.is_symlink():
        raise pytest.UsageError(
            "Refusing to clean an authentication-state symbolic link."
        )

    evidence: dict[str, bool | int] = {
        "storageStateCreated": (
            state_directory / "authenticated-state.json"
        ).is_file(),
        "sessionStorageCreated": (
            state_directory / "authenticated-state.session-storage.json"
        ).is_file(),
    }
    if state_directory.exists():
        shutil.rmtree(state_directory)
    evidence["stateDirectoryCleaned"] = not state_directory.exists()
    evidence["pytestExitStatus"] = exitstatus
    evidence_path = root / "testResults" / "session-state-evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )

    logging_plugin = session.config.pluginmanager.get_plugin("logging-plugin")
    file_handler = getattr(logging_plugin, "log_file_handler", None)
    if file_handler is not None:
        file_handler.flush()
        log_path = Path(file_handler.baseFilename)
        file_handler.close()
        if log_path.is_file() and log_path.stat().st_size == 0:
            log_path.unlink()

def pytest_runtest_setup(item: pytest.Item) -> None:
    _prepare_output_directories(item.config)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, None, None]:
    outcome = yield
    report = outcome.get_result()
    if not report.failed:
        report.sections[:] = [
            (name, content)
            for name, content in report.sections
            if not name.startswith("Captured log")
        ]
    if report.failed:
        diagnostics = item.stash.get(BROWSER_DIAGNOSTICS, [])
        captured_logs = "\n".join(
            f"{section_name}\n{content}"
            for section_name, content in report.sections
            if section_name.startswith("Captured log")
        )
        log_test_failure(
            item.nodeid,
            report.when,
            str(report.longrepr),
            captured_logs,
            diagnostics,
        )
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