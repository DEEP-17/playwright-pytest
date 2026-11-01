from pathlib import Path

from scripts.ci_report import (
    read_test_results,
    render_html,
    validation_errors,
)


def test_ci_report_reads_and_groups_junit_results(tmp_path: Path) -> None:
    report_dir = tmp_path / "pytest-report-flight-scenarios"
    report_dir.mkdir()
    (report_dir / "junit-flight-scenarios.xml").write_text(
        """<testsuites><testsuite>
<testcase classname="tests.test_flight" name="test_search" time="1.25" />
<testcase classname="tests.test_flight" name="test_checkout" time="0.50">
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
    assert "Workbook UI test results" in report
    assert "&lt;unexpected&gt;" in report


def test_ci_report_flags_skipped_and_duplicate_results(tmp_path: Path) -> None:
    report_dir = tmp_path / "pytest-report-hotel-scenarios"
    report_dir.mkdir()
    (report_dir / "junit-hotel-scenarios.xml").write_text(
        """<testsuite>
<testcase classname="tests.test_hotel" name="test_search" time="1.0">
  <skipped message="not selected" />
</testcase>
<testcase classname="tests.test_hotel" name="test_search" time="1.0" />
</testsuite>""",
        encoding="utf-8",
    )

    results = read_test_results(tmp_path)
    errors = validation_errors(results, expected_count=2)

    assert any("Duplicate test results" in error for error in errors)
    assert any("SKIPPED" in error for error in errors)


def test_ci_report_accepts_exact_23_case_lane_breakdown(tmp_path: Path) -> None:
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
            f'<testcase classname="tests.{lane}" name="test_case_{index}" time="1.0" />'
            for index in range(count)
        )
        (report_dir / f"junit-{lane}.xml").write_text(
            f"<testsuite>{cases}</testsuite>", encoding="utf-8"
        )

    results = read_test_results(tmp_path)

    assert len(results) == 23
    assert validation_errors(results, expected_count=23) == []
    assert render_html(results, expected_count=23).count("<tr>") == 24
