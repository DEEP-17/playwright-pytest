from __future__ import annotations

import argparse
import json
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from automationScripts.openAllureReport import create_server

_REQUIRED_REPORT_FILES = (
    "index.html",
    "app.js",
    "styles.css",
    "data/suites.json",
    "data/behaviors.json",
    "widgets/summary.json",
    "widgets/suites.json",
    "widgets/behaviors.json",
)


def validate_report(report_directory: Path) -> int:
    report_directory = report_directory.resolve()
    missing_files = [
        name
        for name in _REQUIRED_REPORT_FILES
        if not (report_directory / name).is_file()
    ]
    if missing_files:
        raise FileNotFoundError(
            "Allure report is missing required files: "
            + ", ".join(missing_files)
        )

    summary = json.loads(
        (report_directory / "widgets" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    total = summary.get("statistic", {}).get("total")
    if not isinstance(total, int) or total <= 0:
        raise ValueError("Allure report contains no test results.")

    test_case_directory = report_directory / "data" / "test-cases"
    test_case_files = sorted(test_case_directory.glob("*.json"))
    if len(test_case_files) != total:
        raise ValueError(
            "Allure report summary lists "
            f"{total} tests, but {len(test_case_files)} test-case data files "
            "were generated."
        )

    report_paths = list(_REQUIRED_REPORT_FILES)
    report_paths.extend(
        path.relative_to(report_directory).as_posix()
        for path in test_case_files
    )

    server = create_server(report_directory)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for relative_path in report_paths:
            url_path = quote(relative_path, safe="/")
            try:
                with urlopen(
                    f"http://127.0.0.1:{server.server_port}/{url_path}",
                    timeout=10,
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(
                            f"Allure report URL returned HTTP "
                            f"{response.status}: /{relative_path}"
                        )
                    response.read()
            except (HTTPError, URLError) as error:
                raise RuntimeError(
                    f"Allure report URL is unavailable: /{relative_path}"
                ) from error
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    return total


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate generated Allure report data and HTTP routes."
    )
    parser.add_argument("report_directory", type=Path)
    args = parser.parse_args()
    total = validate_report(args.report_directory)
    print(
        f"Validated Allure report: {total} test cases and "
        "all required localhost report URLs returned HTTP 200."
    )


if __name__ == "__main__":
    main()
