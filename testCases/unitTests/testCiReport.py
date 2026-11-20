from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

from automationScripts.ciReport import (
    main,
    read_test_results,
    render_html,
    render_markdown,
    validation_errors,
)
from automationScripts.extractSkippedTests import extract_skipped_tests

def testCiReportReadsAndGroupsJunitResults(tmp_path: Path) -> None:
    report_dir = tmp_path / "pytest-report-flight-scenarios"
    report_dir.mkdir()
    (report_dir / "junit-flight-scenarios.xml").write_text(
        """<testsuites><testsuite>
<testcase classname="testCases.endToEndTests.testFlight" name="testSearch" time="1.25" />
<testcase classname="testCases.endToEndTests.testFlight" name="testCheckout" time="0.50">
  <failure message="assertion failed">&lt;unexpected&gt;</failure>
</testcase>
</testsuite></testsuites>""",
        encoding="utf-8",
    )
    results = read_test_results(tmp_path)
    assert [result.category for result in results] == ["Flights", "Flights"]
    assert [result.status for result in results] == ["FAILED", "PASSED"]
    assert "Expected 23 workbook test results; found 2." in validation_errors(
        results, expected_count=23
    )
    report = render_html(results, expected_count=23)
    assert "UI test report" in report
    assert "Outcome distribution" in report
    assert "Pass rate by test area" in report
    assert 'id="report-search"' in report
    assert 'id="status-filter"' in report
    assert "&lt;unexpected&gt;" in report

def testCiReportFlagsSkippedAndDuplicateResults(tmp_path: Path) -> None:
    report_dir = tmp_path / "pytest-report-hotel-scenarios"
    report_dir.mkdir()
    (report_dir / "junit-hotel-scenarios.xml").write_text(
        """<testsuite>
<testcase classname="testCases.endToEndTests.testHotel" name="testSearch" time="1.0">
  <skipped message="KNOWN_ISSUE:E9_INVALID_REPRICE_TOTAL: waiting for QA | test data" />
</testcase>
<testcase classname="testCases.endToEndTests.testHotel" name="testSearch" time="1.0" />
</testsuite>""",
        encoding="utf-8",
    )
    results = read_test_results(tmp_path)
    errors = validation_errors(results, expected_count=2)
    assert any("Duplicate test results" in error for error in errors)
    assert any("SKIPPED" in error for error in errors)
    assert "waiting for QA &#124; test data" in render_markdown(results, 2)

def testCiReportAllowsOnlyExpectedE9Skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_dir = tmp_path / "pytest-report-flight-scenarios"
    report_dir.mkdir()
    passed_cases = "".join(
        f'<testcase classname="testCases.endToEndTests.testFlight" '
        f'name="testFlight{index}" time="1.0" />'
        for index in range(22)
    )
    (report_dir / "junit-flight-scenarios.xml").write_text(
        f"""<testsuite>
{passed_cases}
<testcase classname="testCases.endToEndTests.testFlight"
 name="testE9SelectedFarePersistsToTripSummary[chromium]" time="1.0">
  <skipped message="Skipped: KNOWN_ISSUE:E9_INVALID_REPRICE_TOTAL: fare was NaN" />
</testcase>
</testsuite>""",
        encoding="utf-8",
    )
    results = read_test_results(tmp_path)
    assert [result.status for result in results].count("PASSED") == 22
    assert [result.status for result in results].count("SKIPPED") == 1
    assert validation_errors(results, expected_count=23) == []
    html_path = tmp_path / "summary.html"
    markdown_path = tmp_path / "summary.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ciReport.py",
            "--reports-dir",
            str(tmp_path),
            "--html",
            str(html_path),
            "--markdown",
            str(markdown_path),
            "--expected-count",
            "23",
        ],
    )
    assert main() == 0
    html_report = html_path.read_text(encoding="utf-8")
    markdown_report = markdown_path.read_text(encoding="utf-8")
    assert "Passed with expected skip" in html_report
    assert 'class="status-badge skipped">SKIPPED</span>' in html_report
    assert "22/23 passed · 1 skipped" in markdown_report
    assert "KNOWN_ISSUE:E9_INVALID_REPRICE_TOTAL" in markdown_report


def testExtractSkippedTestsCreatesDedicatedReports(tmp_path: Path) -> None:
    reports_dir = tmp_path / "testReports"
    report_dir = reports_dir / "pytest-report-flight-scenarios"
    report_dir.mkdir(parents=True)
    (report_dir / "junit-flight-scenarios.xml").write_text(
        """<testsuite>
<testcase classname="testCases.endToEndTests.testFlight" name="testPassed" time="1.0" />
<testcase classname="testCases.endToEndTests.testFlight" name="testE9" time="2.0">
  <skipped message="KNOWN_ISSUE:E9_INVALID_REPRICE_TOTAL: fare was NaN">
    testFlight.py:209
  </skipped>
</testcase>
</testsuite>""",
        encoding="utf-8",
    )
    output_dir = tmp_path / "skipped-test-artifact"

    assert extract_skipped_tests(reports_dir, output_dir) == 1

    junit_root = ET.parse(output_dir / "junit-skipped-tests.xml").getroot()
    cases = list(junit_root.iter("testcase"))
    assert len(cases) == 1
    assert cases[0].get("name") == "testE9"
    assert cases[0].find("skipped") is not None
    markdown = (output_dir / "skipped-tests.md").read_text(encoding="utf-8")
    assert "testE9" in markdown
    assert "KNOWN_ISSUE:E9_INVALID_REPRICE_TOTAL" in markdown
    assert "testFlight.py:209" in markdown
    results = read_test_results(reports_dir)
    assert len(results) == 2
    assert sum(result.node_id.endswith("::testE9") for result in results) == 1


def testExtractSkippedTestsRemovesStaleArtifactWhenNoSkips(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "testReports"
    report_dir = reports_dir / "pytest-report-flight-scenarios"
    report_dir.mkdir(parents=True)
    (report_dir / "junit-flight-scenarios.xml").write_text(
        '<testsuite><testcase name="testPassed" time="1.0" /></testsuite>',
        encoding="utf-8",
    )
    output_dir = tmp_path / "skipped-test-artifact"
    output_dir.mkdir()
    junit_path = output_dir / "junit-skipped-tests.xml"
    markdown_path = output_dir / "skipped-tests.md"
    junit_path.write_text("stale", encoding="utf-8")
    markdown_path.write_text("stale", encoding="utf-8")

    assert extract_skipped_tests(reports_dir, output_dir) == 0
    assert not junit_path.exists()
    assert not markdown_path.exists()


def testCiReportAcceptsExact23CaseLaneBreakdown(tmp_path: Path) -> None:
    lane_counts = {
        "flight-scenarios": 13,
        "hotel-scenarios": 5,
        "public-attractions": 2,
        "saved-trip": 3,
    }
    for lane, count in lane_counts.items():
        report_dir = tmp_path / f"pytest-report-{lane}"
        report_dir.mkdir()
        cases = "".join(
            f'<testcase classname="testCases.endToEndTests.{lane}" name="testCase{index}" time="1.0" />'
            for index in range(count)
        )
        (report_dir / f"junit-{lane}.xml").write_text(
            f"<testsuite>{cases}</testsuite>", encoding="utf-8"
        )
    preflight_dir = tmp_path / "pytest-report-preflight"
    preflight_dir.mkdir()
    (preflight_dir / "preflight-results.xml").write_text(
        '<testsuite><testcase classname="testCases.unitTests.testSupport" '
        'name="testSupport" time="0.1" /></testsuite>',
        encoding="utf-8",
    )
    results = read_test_results(tmp_path)
    assert len(results) == 23
    assert validation_errors(results, expected_count=23) == []
    report = render_html(results, expected_count=23)
    assert report.count('data-status="passed"') == 23
    assert (
        'aria-label="23 passed, 0 failed or errored, 0 known issues, 0 skipped"'
        in report
    )

def testCiReportAllowsTargetedPartialResults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_dir = tmp_path / "pytest-report-flight-scenarios"
    report_dir.mkdir()
    (report_dir / "junit-flight-scenarios.xml").write_text(
        '<testsuite><testcase classname="testCases.endToEndTests.testFlight" '
        'name="testSearch" time="1.0" /></testsuite>',
        encoding="utf-8",
    )
    html_path = tmp_path / "summary.html"
    markdown_path = tmp_path / "summary.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ciReport.py",
            "--reports-dir",
            str(tmp_path),
            "--html",
            str(html_path),
            "--markdown",
            str(markdown_path),
            "--allow-partial",
        ],
    )

    assert main() == 0
    assert "1/1 passed" in markdown_path.read_text(encoding="utf-8")