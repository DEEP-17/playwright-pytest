from __future__ import annotations

import argparse
import html
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


_CATEGORY_LABELS = {
    "flight-scenarios": "Flights",
    "hotel-scenarios": "Hotels",
    "public-attractions": "Attractions",
    "saved-trip": "Saved trips",
}


@dataclass(frozen=True)
class TestResult:
    category: str
    node_id: str
    status: str
    duration: float
    detail: str = ""


def _category_for_report(report_path: Path) -> str:
    for parent in report_path.parents:
        if parent.name.startswith("pytest-report-"):
            category_id = parent.name.removeprefix("pytest-report-")
            return _CATEGORY_LABELS.get(category_id, category_id.replace("-", " "))
    return "Uncategorized"


def read_test_results(reports_dir: Path) -> list[TestResult]:
    results: list[TestResult] = []
    for report_path in sorted(reports_dir.rglob("junit-*.xml")):
        root = ET.parse(report_path).getroot()
        category = _category_for_report(report_path)
        for case in root.iter("testcase"):
            node_id = f"{case.get('classname', '')}::{case.get('name', '')}"
            duration = float(case.get("time", "0"))
            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")
            result = failure if failure is not None else error
            if result is not None:
                status = "FAILED" if failure is not None else "ERROR"
                detail = " ".join(
                    part
                    for part in (result.get("message", ""), result.text or "")
                    if part
                )
            elif skipped is not None:
                status = "SKIPPED"
                detail = " ".join(
                    part
                    for part in (skipped.get("message", ""), skipped.text or "")
                    if part
                )
            else:
                status = "PASSED"
                detail = ""
            results.append(
                TestResult(
                    category=category,
                    node_id=node_id,
                    status=status,
                    duration=duration,
                    detail=detail,
                )
            )
    return sorted(results, key=lambda result: (result.category, result.node_id))


def validation_errors(
    results: list[TestResult], expected_count: int
) -> list[str]:
    errors: list[str] = []
    if len(results) != expected_count:
        errors.append(
            f"Expected {expected_count} workbook test results; found {len(results)}."
        )

    node_ids = [result.node_id for result in results]
    duplicates = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
    if duplicates:
        errors.append("Duplicate test results: " + ", ".join(duplicates))

    not_passed = [
        f"{result.node_id} ({result.status})"
        for result in results
        if result.status != "PASSED"
    ]
    if not_passed:
        errors.append("Workbook tests did not pass: " + ", ".join(not_passed))
    return errors


def render_html(results: list[TestResult], expected_count: int) -> str:
    passed = sum(result.status == "PASSED" for result in results)
    rows = []
    for result in results:
        detail = (
            f"<details><summary>Details</summary><pre>"
            f"{html.escape(result.detail)}</pre></details>"
            if result.detail
            else ""
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(result.category)}</td>"
            f"<td><code>{html.escape(result.node_id)}</code>{detail}</td>"
            f"<td class=\"{result.status.lower()}\">{result.status}</td>"
            f"<td>{result.duration:.2f}s</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Workbook UI test summary</title>
  <style>
    body {{ font: 15px system-ui, sans-serif; margin: 2rem auto; max-width: 1200px; padding: 0 1rem; color: #172033; }}
    h1 {{ margin-bottom: .3rem; }}
    .summary {{ color: #475569; margin-bottom: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #dbe2ea; padding: .65rem; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; position: sticky; top: 0; }}
    code {{ overflow-wrap: anywhere; }}
    .passed {{ color: #137333; font-weight: 700; }}
    .failed, .error {{ color: #b42318; font-weight: 700; }}
    .skipped {{ color: #9a6700; font-weight: 700; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <h1>Workbook UI test results</h1>
  <p class="summary">{passed}/{expected_count} expected cases passed; {len(results)} results collected.</p>
  <table>
    <thead><tr><th>Category</th><th>Test case</th><th>Result</th><th>Duration</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</body>
</html>
"""


def render_markdown(results: list[TestResult], expected_count: int) -> str:
    passed = sum(result.status == "PASSED" for result in results)
    lines = [
        f"## Workbook UI tests: {passed}/{expected_count} passed",
        "",
        "| Category | Test case | Result | Duration |",
        "|---|---|---:|---:|",
    ]
    lines.extend(
        f"| {result.category} | `{result.node_id}` | **{result.status}** "
        f"| {result.duration:.2f}s |"
        for result in results
    )
    if len(results) != expected_count:
        lines.extend(("", f"Collected {len(results)} of {expected_count} expected results."))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the combined CI test report.")
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=23)
    args = parser.parse_args()

    results = read_test_results(args.reports_dir)
    args.html.parent.mkdir(parents=True, exist_ok=True)
    args.html.write_text(
        render_html(results, args.expected_count), encoding="utf-8"
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(
        render_markdown(results, args.expected_count), encoding="utf-8"
    )

    errors = validation_errors(results, args.expected_count)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated all {args.expected_count} workbook test results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
