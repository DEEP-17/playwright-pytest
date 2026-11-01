import os
import re
import warnings
from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page


def pytest_runtest_setup(item: pytest.Item) -> None:
    config = item.config
    (Path(config.rootpath) / ".auth").mkdir(parents=True, exist_ok=True)
    html_path = getattr(config.option, "htmlpath", None)
    if html_path:
        report_path = Path(os.path.expandvars(html_path)).expanduser()
        if not report_path.is_absolute():
            report_path = Path(config.invocation_params.dir) / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, None, None]:
    outcome = yield
    report = outcome.get_result()
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
