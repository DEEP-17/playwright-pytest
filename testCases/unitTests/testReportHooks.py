from types import SimpleNamespace

import pytest

from pytestHooks import pytestHooks


def testPytestHtmlReportUsesProjectTitleAndSuiteColumn() -> None:
    report = SimpleNamespace(title="")
    cells = ["<th>Result</th>", "<th>Test</th>"]
    row_cells = ["<td>Passed</td>", "<td>test</td>"]
    test_report = SimpleNamespace(
        nodeid="testCases/endToEndTests/testHotel.py::testBooking"
    )

    pytestHooks.pytest_html_report_title(report)
    pytestHooks.pytest_html_results_table_header(cells)
    pytestHooks.pytest_html_results_table_row(test_report, row_cells)

    assert report.title == "Playwright Test Results"
    assert cells[1] == "<th>Suite</th>"
    assert row_cells[1] == "<td>End-to-end</td>"


def testPytestHtmlSummaryShowsRunOutcomeAndTotals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pytestHooks,
        "_REPORT_RESULTS",
        {
            "testCases/endToEndTests/testTrip.py::testPassed": {
                "status": "passed",
                "duration": 1.0,
            },
            "testCases/endToEndTests/testTrip.py::testFailed": {
                "status": "failed",
                "duration": 2.0,
            },
            "testCases/unitTests/testSupport.py::testSkipped": {
                "status": "skipped",
                "duration": 0.1,
            },
        },
    )
    monkeypatch.setattr(pytestHooks, "_REPORT_STARTED_AT", 0.0)
    prefix: list[str] = []

    pytestHooks.pytest_html_results_summary(prefix, [], [], SimpleNamespace())

    assert len(prefix) == 1
    assert "Review failures" in prefix[0]
    assert "Total tests</span><strong>3" in prefix[0]
    assert "Passed</span><strong>1" in prefix[0]
    assert "Failed / errors</span><strong>1" in prefix[0]
    assert "Skipped / xfailed</span><strong>1" in prefix[0]
    assert "Outcome distribution" in prefix[0]
    assert "Results by suite" in prefix[0]
    assert "1 passed, 1 failed or errored, 1 skipped" in prefix[0]


def testPytestHtmlSummaryDoesNotTreatEmptyRunAsSuccess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pytestHooks, "_REPORT_RESULTS", {})
    monkeypatch.setattr(pytestHooks, "_REPORT_STARTED_AT", 0.0)
    prefix: list[str] = []

    pytestHooks.pytest_html_results_summary(prefix, [], [], SimpleNamespace())

    assert "No tests collected" in prefix[0]
    assert "All checks passed" not in prefix[0]
