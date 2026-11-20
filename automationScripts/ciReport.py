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
_KNOWN_ISSUE_NODE_IDS = {
    "testCases.endToEndTests.testFlight::testE9SelectedFarePersistsToTripSummary"
}
_KNOWN_ISSUE_MARKER = "KNOWN_ISSUE:E9_INVALID_REPRICE_TOTAL"

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

def _base_node_id(node_id: str) -> str:
    return node_id.split("[", 1)[0]


def _is_expected_e9_skip(result: TestResult) -> bool:
    return (
        result.status == "SKIPPED"
        and _base_node_id(result.node_id) in _KNOWN_ISSUE_NODE_IDS
        and _KNOWN_ISSUE_MARKER in result.detail
    )


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
                detail = " ".join(
                    part
                    for part in (skipped.get("message", ""), skipped.text or "")
                    if part
                )
                is_known_issue = (
                    _base_node_id(node_id) in _KNOWN_ISSUE_NODE_IDS
                    and _KNOWN_ISSUE_MARKER in detail
                    and detail.startswith("XFAIL:")
                )
                status = "KNOWN ISSUE" if is_known_issue else "SKIPPED"
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
        if result.status not in {"PASSED", "KNOWN ISSUE"}
        and not _is_expected_e9_skip(result)
    ]
    if not_passed:
        errors.append("Workbook tests did not pass: " + ", ".join(not_passed))
    return errors


def _chart_segment(
    count: int, total: int, label: str, outcome: str
) -> str:
    if not count or not total:
        return ""
    width = count / total * 100
    return (
        f'<span class="chart-segment chart-{outcome}" '
        f'style="width:{width:.2f}%" title="{label}: {count}"></span>'
    )


def render_html(results: list[TestResult], expected_count: int) -> str:
    passed = sum(result.status == "PASSED" for result in results)
    failed = sum(result.status in {"FAILED", "ERROR"} for result in results)
    known_issues = sum(result.status == "KNOWN ISSUE" for result in results)
    skipped = sum(result.status == "SKIPPED" for result in results)
    expected_skips = sum(_is_expected_e9_skip(result) for result in results)
    total_duration = sum(result.duration for result in results)
    pass_rate = round(passed / len(results) * 100) if results else 0
    complete_without_blocking_results = (
        len(results) == expected_count and failed == 0 and skipped == expected_skips
    )
    run_status = "Review results"
    if complete_without_blocking_results:
        if known_issues and expected_skips:
            run_status = "Passed with known issue and expected skip"
        elif known_issues:
            run_status = "Passed with known issue"
        elif expected_skips:
            run_status = "Passed with expected skip"
        else:
            run_status = "All checks passed"
    run_state_class = (
        "review"
        if not complete_without_blocking_results
        else "known-issue"
        if known_issues or expected_skips
        else ""
    )
    exceptional_summaries = []
    if known_issues:
        exceptional_summaries.append(
            f"{known_issues} known issue{'s' if known_issues != 1 else ''}"
        )
    if expected_skips:
        exceptional_summaries.append(
            f"{expected_skips} expected skip{'s' if expected_skips != 1 else ''}"
        )
    outcome_summary = (
        " · " + " · ".join(exceptional_summaries) if exceptional_summaries else ""
    )
    categories: dict[str, list[TestResult]] = {}
    for result in results:
        categories.setdefault(result.category, []).append(result)

    outcome_counts = (
        ("Passed", passed, "passed"),
        ("Failed / errors", failed, "failed"),
        ("Known issues", known_issues, "known-issue"),
        ("Skipped", skipped, "skipped"),
    )
    outcome_segments = "".join(
        _chart_segment(count, len(results), label, style)
        for label, count, style in outcome_counts
    )
    outcome_legend = "".join(
        f'<li><span class="legend-dot chart-{style}"></span>'
        f"{label}: <strong>{count}</strong></li>"
        for label, count, style in outcome_counts
    )
    category_chart_rows = []
    for category, cases in sorted(categories.items()):
        category_passed = sum(case.status == "PASSED" for case in cases)
        category_failed = sum(case.status in {"FAILED", "ERROR"} for case in cases)
        category_known_issues = sum(case.status == "KNOWN ISSUE" for case in cases)
        category_skipped = sum(case.status == "SKIPPED" for case in cases)
        category_segments = "".join(
            _chart_segment(count, len(cases), label, style)
            for label, count, style in (
                ("Passed", category_passed, "passed"),
                ("Failed / errors", category_failed, "failed"),
                ("Known issues", category_known_issues, "known-issue"),
                ("Skipped", category_skipped, "skipped"),
            )
        )
        category_chart_rows.append(
            '<div class="suite-chart__row">'
            f'<div class="suite-chart__labels"><span>{html.escape(category)}</span>'
            f"<strong>{category_passed}/{len(cases)} passed</strong></div>"
            f'<div class="chart-stack" role="img" '
            f'aria-label="{category_passed} passed, {category_failed} failed, '
            f'{category_known_issues} known issues, {category_skipped} skipped">'
            f"{category_segments}</div></div>"
        )
    empty_chart = (
        '<p class="chart-empty">No test outcomes to chart.</p>' if not results else ""
    )

    rows = []
    for result in results:
        status_key = result.status.lower().replace(" ", "-")
        detail = (
            f'<details class="result-detail"><summary>View failure details</summary><pre>'
            f"{html.escape(result.detail)}</pre></details>"
            if result.detail
            else ""
        )
        search_text = html.escape(
            f"{result.category} {result.node_id} {result.status} {result.detail}",
            quote=True,
        )
        rows.append(
            f'<tr data-status="{status_key}" '
            f'data-category="{html.escape(result.category, quote=True)}" '
            f'data-search="{search_text}">'
            f"<td>{html.escape(result.category)}</td>"
            f"<td><code>{html.escape(result.node_id)}</code>{detail}</td>"
            f'<td><span class="status-badge {status_key}">{result.status}</span></td>'
            f"<td>{result.duration:.2f}s</td>"
            "</tr>"
        )
    category_cards = "".join(
        (
            '<article class="category-card">'
            f"<h3>{html.escape(category)}</h3>"
            f"<p>{sum(case.status == 'PASSED' for case in cases)}"
            f"/{len(cases)} passed · "
            f"{sum(case.status == 'KNOWN ISSUE' for case in cases)} known issues</p>"
            f'<span class="category-failures">'
            f"{sum(case.status in {'FAILED', 'ERROR'} for case in cases)} failures"
            "</span></article>"
        )
        for category, cases in sorted(categories.items())
    )
    empty_state = (
        '<tr class="empty-state"><td colspan="4">'
        "No test results were collected for this run.</td></tr>"
        if not rows
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Playwright UI test report</title>
  <style>
    :root {{ color-scheme: light; --ink:#17243b; --muted:#64748b; --line:#e2e8f0; --navy:#10243f; --blue:#2874d0; --green:#16835d; --red:#c43d4b; --amber:#a56a13; --page:#f3f6fb; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--page); color:var(--ink); font:14px/1.55 Inter,"Segoe UI",Arial,sans-serif; }}
    .hero {{ padding:2.2rem max(1.25rem,calc((100% - 1180px)/2)); background:linear-gradient(120deg,#10243f,#174f84); color:#fff; }}
    .eyebrow {{ color:#9fd1ff; font-size:.72rem; font-weight:800; letter-spacing:.13em; }}
    h1 {{ margin:.2rem 0; font-size:clamp(1.7rem,4vw,2.5rem); letter-spacing:-.04em; }}
    .hero p {{ margin:.3rem 0 0; color:#d5e6f8; }}
    main {{ width:min(1180px,calc(100% - 2.5rem)); margin:1.5rem auto 3rem; }}
    .run-state {{ display:inline-flex; margin-top:1rem; padding:.4rem .8rem; border-radius:999px; background:#e5f6ef; color:#116b4d; font-size:.8rem; font-weight:750; }}
    .run-state.review {{ background:#fff0ef; color:#a92836; }}
    .run-state.known-issue {{ background:#fff6df; color:#8a5b0d; }}
    .metrics {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.8rem; margin-bottom:1.2rem; }}
    .metric,.category-card,.panel {{ border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:0 8px 24px rgb(23 36 59 / 5%); }}
    .metric {{ padding:1rem; }} .metric span,.metric strong {{ display:block; }}
    .metric span {{ color:var(--muted); font-size:.78rem; }} .metric strong {{ margin-top:.15rem; font-size:1.6rem; letter-spacing:-.04em; }}
    .metric.passed strong {{ color:var(--green); }} .metric.failed strong {{ color:var(--red); }} .metric.known-issue strong,.metric.skipped strong {{ color:var(--amber); }}
    .progress-card {{ padding:1rem 1.1rem; margin-bottom:1.2rem; border:1px solid #dce5f0; border-radius:14px; background:linear-gradient(145deg,#fff,#f5f9ff); }}
    .progress-labels {{ display:flex; justify-content:space-between; color:var(--muted); font-size:.82rem; }}
    .progress-track {{ height:.55rem; margin-top:.55rem; overflow:hidden; border-radius:999px; background:#e7edf5; }}
    .progress-track span {{ display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg,#27a879,#48c79b); }}
    .section-heading {{ margin:1.6rem 0 .75rem; font-size:1.1rem; }}
    .categories {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:.75rem; margin-bottom:1.3rem; }}
    .category-card {{ padding:.9rem 1rem; }} .category-card h3 {{ margin:0; font-size:.95rem; }}
    .category-card p {{ margin:.25rem 0; color:var(--green); font-weight:750; }}
    .category-failures {{ color:var(--muted); font-size:.76rem; }}
    .chart-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; margin-bottom:1.3rem; }}
    .chart-card {{ min-width:0; padding:1rem 1.1rem; }} .chart-card h2 {{ margin:0 0 .9rem; font-size:.98rem; }}
    .chart-stack {{ display:flex; width:100%; height:.75rem; overflow:hidden; border-radius:999px; background:#e8eef5; }}
    .chart-stack--large {{ height:1rem; }}
    .chart-segment {{ display:block; height:100%; min-width:2px; }}
    .chart-passed {{ background:#27a879; }} .chart-failed {{ background:#d64a57; }} .chart-known-issue {{ background:#b7791f; }} .chart-skipped {{ background:#e3a32b; }}
    .chart-legend {{ display:flex; flex-wrap:wrap; gap:.55rem 1rem; margin:.8rem 0 0; padding:0; list-style:none; color:var(--muted); font-size:.76rem; }}
    .chart-legend li {{ display:flex; align-items:center; gap:.35rem; }} .chart-legend strong {{ color:var(--ink); }}
    .legend-dot {{ width:.58rem; height:.58rem; border-radius:50%; }}
    .suite-chart {{ display:grid; gap:.75rem; }} .suite-chart__row {{ display:grid; gap:.35rem; }}
    .suite-chart__labels {{ display:flex; justify-content:space-between; gap:.5rem; color:var(--muted); font-size:.76rem; }}
    .suite-chart__labels strong {{ color:var(--ink); }} .chart-empty {{ color:var(--muted); font-size:.8rem; }}
    .panel {{ overflow:hidden; }}
    .toolbar {{ display:flex; flex-wrap:wrap; gap:.7rem; padding:1rem; border-bottom:1px solid var(--line); }}
    .toolbar input,.toolbar select {{ min-height:2.5rem; padding:.45rem .7rem; border:1px solid #cbd5e1; border-radius:8px; background:#fff; color:var(--ink); font:inherit; }}
    .toolbar input {{ flex:1 1 270px; }} .toolbar select {{ min-width:155px; }}
    .result-count {{ align-self:center; margin-left:auto; color:var(--muted); font-size:.8rem; }}
    .table-wrap {{ overflow-x:auto; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ padding:.75rem .85rem; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ position:sticky; top:0; background:#eaf1fa; color:#29415e; font-size:.74rem; letter-spacing:.04em; text-transform:uppercase; }}
    tbody tr:hover {{ background:#f7faff; }} code {{ overflow-wrap:anywhere; font-size:.82rem; }}
    .status-badge {{ display:inline-block; padding:.2rem .55rem; border-radius:999px; font-size:.72rem; font-weight:800; }}
    .status-badge.passed {{ background:#e5f6ef; color:var(--green); }} .status-badge.failed,.status-badge.error {{ background:#fff0ef; color:var(--red); }} .status-badge.known-issue,.status-badge.skipped {{ background:#fff6df; color:var(--amber); }}
    .result-detail {{ margin-top:.45rem; color:var(--red); font-size:.78rem; }} .result-detail pre {{ max-width:60rem; overflow:auto; padding:.8rem; border-radius:8px; background:#101b2c; color:#e5edf7; white-space:pre-wrap; overflow-wrap:anywhere; }}
    .empty-state td {{ padding:2rem; color:var(--muted); text-align:center; }}
    footer {{ margin-top:1rem; color:var(--muted); font-size:.75rem; text-align:right; }}
    @media(max-width:760px) {{ .metrics {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} main {{ width:calc(100% - 1.25rem); }} }}
  </style>
</head>
<body>
  <header class="hero">
    <span class="eyebrow">PLAYWRIGHT · PYTEST · CI QUALITY GATE</span>
    <h1>UI test report</h1>
    <p>{passed}/{expected_count} expected cases passed{outcome_summary} · {len(results)} results collected · {total_duration:.1f}s combined test time</p>
    <span class="run-state {run_state_class}">{run_status}</span>
  </header>
  <main>
    <section class="metrics" aria-label="Test outcome summary">
      <article class="metric"><span>Total results</span><strong>{len(results)} / {expected_count}</strong></article>
      <article class="metric passed"><span>Passed</span><strong>{passed}</strong></article>
      <article class="metric known-issue"><span>Known issues</span><strong>{known_issues}</strong></article>
      <article class="metric failed"><span>Failed / errors</span><strong>{failed}</strong></article>
      <article class="metric skipped"><span>Skipped</span><strong>{skipped}</strong></article>
      <article class="metric"><span>Combined duration</span><strong>{total_duration:.1f}s</strong></article>
    </section>
    <section class="progress-card" aria-label="Pass rate">
      <div class="progress-labels"><span>Pass rate</span><strong>{pass_rate}%</strong></div>
      <div class="progress-track"><span style="width:{pass_rate}%"></span></div>
    </section>
    <h2 class="section-heading">Visual test summary</h2>
    <section class="chart-grid" aria-label="Test charts">
      <article class="chart-card">
        <h2>Outcome distribution</h2>
        <div class="chart-stack chart-stack--large" role="img"
             aria-label="{passed} passed, {failed} failed or errored, {known_issues} known issues, {skipped} skipped">{outcome_segments}</div>
        <ul class="chart-legend">{outcome_legend}</ul>{empty_chart}
      </article>
      <article class="chart-card">
        <h2>Pass rate by test area</h2>
        <div class="suite-chart">{"".join(category_chart_rows)}</div>{empty_chart}
      </article>
    </section>
    <h2 class="section-heading">Results by test area</h2>
    <section class="categories" aria-label="Results by category">{category_cards}</section>
    <h2 class="section-heading">Test case details</h2>
    <section class="panel">
      <div class="toolbar">
        <input id="report-search" type="search" aria-label="Search test results" placeholder="Search test cases, categories, or failure details">
        <select id="status-filter" aria-label="Filter by result">
          <option value="">All results</option><option value="failed">Failed</option>
          <option value="error">Errors</option><option value="skipped">Skipped</option>
          <option value="known-issue">Known issue</option>
          <option value="passed">Passed</option>
        </select>
        <span class="result-count" id="result-count" aria-live="polite"></span>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th scope="col">Category</th><th scope="col">Test case</th><th scope="col">Result</th><th scope="col">Duration</th></tr></thead>
          <tbody id="results-body">{''.join(rows)}{empty_state}</tbody>
        </table>
      </div>
    </section>
    <footer>Generated by pytest CI reporting · Failure details are expanded per test case.</footer>
  </main>
  <script>
    const searchInput = document.getElementById("report-search");
    const statusFilter = document.getElementById("status-filter");
    const resultRows = Array.from(document.querySelectorAll("#results-body tr[data-status]"));
    const resultCount = document.getElementById("result-count");
    function filterResults() {{
      const query = searchInput.value.trim().toLowerCase();
      const status = statusFilter.value;
      let visible = 0;
      for (const row of resultRows) {{
        const matches = (!query || row.dataset.search.toLowerCase().includes(query))
          && (!status || row.dataset.status === status);
        row.hidden = !matches;
        if (matches) visible += 1;
      }}
      resultCount.textContent = `Showing ${{visible}} of ${{resultRows.length}} results`;
    }}
    searchInput.addEventListener("input", filterResults);
    statusFilter.addEventListener("change", filterResults);
    filterResults();
  </script>
</body>
</html>
"""

def render_markdown(results: list[TestResult], expected_count: int) -> str:
    passed = sum(result.status == "PASSED" for result in results)
    known_issues = sum(result.status == "KNOWN ISSUE" for result in results)
    skipped = sum(result.status == "SKIPPED" for result in results)
    summaries = []
    if known_issues:
        summaries.append(
            f"{known_issues} known issue{'s' if known_issues != 1 else ''}"
        )
    if skipped:
        summaries.append(f"{skipped} skipped")
    outcome_summary = " · " + " · ".join(summaries) if summaries else ""
    lines = [
        f"## Workbook UI tests: {passed}/{expected_count} passed{outcome_summary}",
        "",
        "| Category | Test case | Result | Duration | Details |",
        "|---|---|---:|---:|---|",
    ]
    for result in results:
        detail = (
            html.escape(result.detail, quote=False)
            .replace("|", "&#124;")
            .replace("\r\n", "\n")
            .replace("\n", "<br>")
        )
        lines.append(
            f"| {result.category} | `{result.node_id}` | **{result.status}** "
            f"| {result.duration:.2f}s | {detail} |"
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
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Validate only the cases present in the reports, for targeted PR runs.",
    )
    args = parser.parse_args()
    results = read_test_results(args.reports_dir)
    expected_count = len(results) if args.allow_partial else args.expected_count
    args.html.parent.mkdir(parents=True, exist_ok=True)
    args.html.write_text(
        render_html(results, expected_count), encoding="utf-8"
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(
        render_markdown(results, expected_count), encoding="utf-8"
    )
    errors = validation_errors(results, expected_count)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    known_issues = sum(result.status == "KNOWN ISSUE" for result in results)
    expected_skips = sum(_is_expected_e9_skip(result) for result in results)
    print(
        f"Validated {expected_count} test results "
        f"({known_issues} known issue{'s' if known_issues != 1 else ''}, "
        f"{expected_skips} expected skip{'s' if expected_skips != 1 else ''})."
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
