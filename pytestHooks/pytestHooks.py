import json
import html
import logging
import os
import re
import shutil
import time
import warnings
from collections.abc import Generator
from pathlib import Path
from typing import Protocol
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
_REPORT_RESULTS: dict[str, dict[str, float | str]] = {}
_REPORT_STARTED_AT = 0.0


class _HtmlReport(Protocol):
    title: str


def pytest_configure(config: pytest.Config) -> None:
    logging.addLevelName(_UI_LOG_LEVEL, "UI")
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")
    cli_handler = getattr(logging_plugin, "log_cli_handler", None)
    formatter = getattr(cli_handler, "formatter", None)
    if formatter is not None and hasattr(formatter, "add_color_level"):
        formatter.add_color_level("UI", "cyan", bold=True)


def pytest_html_report_title(report: _HtmlReport) -> None:
    report.title = "Playwright Test Results"


def pytest_html_results_table_header(cells: list[str]) -> None:
    cells.insert(1, "<th>Suite</th>")


def pytest_html_results_table_row(
    report: pytest.TestReport, cells: list[str]
) -> None:
    suite = _suite_for_nodeid(report.nodeid)
    cells.insert(1, f"<td>{html.escape(suite)}</td>")


def _suite_for_nodeid(nodeid: str) -> str:
    test_path = nodeid.split("::", 1)[0].replace("\\", "/")
    path_parts = test_path.split("/")
    suite = "Other"
    if "unitTests" in path_parts:
        suite = "Unit tests"
    elif "endToEndTests" in path_parts:
        suite = "End-to-end"
    return suite


def _chart_segment(count: int, total: int, label: str, outcome: str) -> str:
    if not count or not total:
        return ""
    width = count / total * 100
    return (
        f'<span class="chart-segment chart-{outcome}" '
        f'style="width:{width:.2f}%" title="{label}: {count}"></span>'
    )


def _report_charts(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    outcomes = (
        ("Passed", counts["passed"], "passed"),
        (
            "Failed / errors",
            counts["failed"] + counts["error"] + counts["xpassed"],
            "failed",
        ),
        ("Skipped / xfailed", counts["skipped"] + counts["xfailed"], "skipped"),
    )
    segments = "".join(
        _chart_segment(count, total, label, style)
        for label, count, style in outcomes
    )
    legend = "".join(
        f'<li><span class="legend-dot chart-{style}"></span>'
        f"{label}: <strong>{count}</strong></li>"
        for label, count, style in outcomes
    )
    suite_counts: dict[str, dict[str, int]] = {}
    for nodeid, result in _REPORT_RESULTS.items():
        suite = _suite_for_nodeid(nodeid)
        suite_counts.setdefault(suite, {}).setdefault(str(result["status"]), 0)
        suite_counts[suite][str(result["status"])] += 1

    suite_rows = []
    for suite, statuses in sorted(suite_counts.items()):
        passed = statuses.get("passed", 0)
        failed = statuses.get("failed", 0) + statuses.get("error", 0)
        failed += statuses.get("xpassed", 0)
        skipped = statuses.get("skipped", 0) + statuses.get("xfailed", 0)
        suite_total = passed + failed + skipped
        suite_segments = "".join(
            _chart_segment(count, suite_total, label, style)
            for label, count, style in (
                ("Passed", passed, "passed"),
                ("Failed / errors", failed, "failed"),
                ("Skipped / xfailed", skipped, "skipped"),
            )
        )
        suite_rows.append(
            '<div class="suite-chart__row">'
            f'<div class="suite-chart__labels"><span>{html.escape(suite)}</span>'
            f"<strong>{passed}/{suite_total} passed</strong></div>"
            f'<div class="chart-stack" role="img" '
            f'aria-label="{passed} passed, {failed} failed, {skipped} skipped">'
            f"{suite_segments}</div></div>"
        )

    no_results = (
        '<p class="chart-empty">No test outcomes to chart.</p>' if not total else ""
    )
    return (
        '<section class="report-charts" aria-label="Test charts">'
        '<article class="report-chart-card"><h3>Outcome distribution</h3>'
        f'<div class="chart-stack chart-stack--large" role="img" '
        f'aria-label="{counts["passed"]} passed, '
        f'{outcomes[1][1]} failed or errored, {outcomes[2][1]} skipped">'
        f"{segments}</div><ul class=\"chart-legend\">{legend}</ul>{no_results}"
        "</article>"
        '<article class="report-chart-card"><h3>Results by suite</h3>'
        f'<div class="suite-chart">{"".join(suite_rows)}</div>'
        "</article></section>"
    )


def _report_dashboard_html(duration: float) -> str:
    counts = {
        "passed": 0,
        "failed": 0,
        "error": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }
    for result in _REPORT_RESULTS.values():
        status = str(result["status"])
        if status in counts:
            counts[status] += 1

    total = sum(counts.values())
    failures = counts["failed"] + counts["error"] + counts["xpassed"]
    skipped = counts["skipped"] + counts["xfailed"]
    pass_rate = round(counts["passed"] / total * 100) if total else 0
    if failures:
        run_status = "Review failures"
        status_class = "needs-attention"
    elif total:
        run_status = "All checks passed"
        status_class = "run-passed"
    else:
        run_status = "No tests collected"
        status_class = "run-empty"
    duration_label = (
        f"{int(duration // 60)}m {int(duration % 60):02d}s"
        if duration >= 60
        else f"{duration:.1f}s"
    )
    return (
        '<section class="report-dashboard">'
        '<div class="report-dashboard__heading">'
        '<div><span class="report-eyebrow">AUTOMATION RUN</span>'
        '<h2>Execution overview</h2>'
        '<p>Browser checks, test outcomes, and run health at a glance.</p></div>'
        f'<span class="run-status {status_class}">{run_status}</span>'
        "</div>"
        '<div class="report-metrics">'
        f'<div class="report-metric"><span>Total tests</span><strong>{total}</strong></div>'
        f'<div class="report-metric metric-passed"><span>Passed</span><strong>{counts["passed"]}</strong></div>'
        f'<div class="report-metric metric-failed"><span>Failed / errors</span><strong>{failures}</strong></div>'
        f'<div class="report-metric metric-skipped"><span>Skipped / xfailed</span><strong>{skipped}</strong></div>'
        f'<div class="report-metric"><span>Run duration</span><strong>{duration_label}</strong></div>'
        "</div>"
        '<div class="report-progress">'
        '<div class="report-progress__labels">'
        f"<span>Pass rate</span><strong>{pass_rate}%</strong></div>"
        '<div class="report-progress__track">'
        f'<span style="width:{pass_rate}%"></span></div></div>'
        f"{_report_charts(counts)}"
        "</section>"
    )


def pytest_html_results_summary(
    prefix: list[str],
    summary: list[str],
    postfix: list[str],
    session: pytest.Session,
) -> None:
    del summary, postfix, session
    duration = time.perf_counter() - _REPORT_STARTED_AT
    prefix.insert(0, _report_dashboard_html(duration))


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
    global _REPORT_STARTED_AT
    _REPORT_RESULTS.clear()
    _REPORT_STARTED_AT = time.perf_counter()
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
    if report.failed:
        status = "failed" if report.when == "call" else "error"
    elif report.skipped:
        status = "xfailed" if hasattr(report, "wasxfail") else "skipped"
    elif hasattr(report, "wasxfail"):
        status = "xpassed"
    else:
        status = "passed"
    result = _REPORT_RESULTS.setdefault(
        report.nodeid, {"status": status, "duration": 0.0}
    )
    result["duration"] = float(result["duration"]) + report.duration
    priority = {
        "passed": 0,
        "xfailed": 1,
        "skipped": 1,
        "xpassed": 2,
        "failed": 3,
        "error": 3,
    }
    if priority[status] >= priority[str(result["status"])]:
        result["status"] = status
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