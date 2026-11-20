from __future__ import annotations

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_skipped_tests(reports_dir: Path, output_dir: Path) -> int:
    junit_path = output_dir / "junit-skipped-tests.xml"
    markdown_path = output_dir / "skipped-tests.md"
    for output_path in (junit_path, markdown_path):
        if output_path.exists():
            output_path.unlink()

    skipped_cases = []
    for report_path in sorted(reports_dir.rglob("junit-*.xml")):
        root = ET.parse(report_path).getroot()
        skipped_cases.extend(
            copy.deepcopy(case)
            for case in root.iter("testcase")
            if case.find("skipped") is not None
        )

    if not skipped_cases:
        print("No skipped test cases found.")
        return 0

    total_time = sum(float(case.get("time", "0")) for case in skipped_cases)
    suite = ET.Element(
        "testsuite",
        {
            "name": "Skipped pytest cases",
            "tests": str(len(skipped_cases)),
            "errors": "0",
            "failures": "0",
            "skipped": str(len(skipped_cases)),
            "time": f"{total_time:.3f}",
        },
    )
    for case in skipped_cases:
        suite.append(case)

    output_dir.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(
        junit_path, encoding="utf-8", xml_declaration=True
    )

    lines = [
        "# Skipped pytest cases",
        "",
        f"Found {len(skipped_cases)} skipped test case(s).",
        "",
        "| Test case | Skip details |",
        "|---|---|",
    ]
    for case in skipped_cases:
        skipped = case.find("skipped")
        if skipped is None:
            continue
        node_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        detail = " ".join(
            part
            for part in (skipped.get("message", ""), skipped.text or "")
            if part
        )
        detail = detail.replace("|", "&#124;").replace("\r\n", "\n").replace(
            "\n", "<br>"
        )
        lines.append(f"| `{node_id}` | {detail} |")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(skipped_cases)} skipped test case(s) to {output_dir}.")
    return len(skipped_cases)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract skipped pytest cases into a standalone artifact."
    )
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    extract_skipped_tests(args.reports_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
