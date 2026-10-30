import re
import warnings
from collections.abc import Generator

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page


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
