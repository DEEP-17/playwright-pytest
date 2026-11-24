import json
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

import pytest

from automationScripts.openAllureReport import create_server
from automationScripts.validateAllureReport import validate_report

def testAllureViewerServesReportDataOverHttpWithoutAccessLogs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "index.html").write_text("<html>Allure</html>", encoding="utf-8")
    widgets = tmp_path / "widgets"
    widgets.mkdir()
    summary = {"statistic": {"total": 53, "passed": 53}}
    (widgets / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    server = create_server(tmp_path)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/widgets/summary.json"
        ) as response:
            assert response.status == 200
            assert json.load(response) == summary
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    assert capsys.readouterr().err == ""


def testAllureReportValidationChecksDataCountAndLocalhostRoutes(
        tmp_path: Path,
) -> None:
        for relative_path in (
            "data/test-cases",
            "widgets",
        ):
            (tmp_path / relative_path).mkdir(parents=True, exist_ok=True)
        for relative_path in (
            "index.html",
            "app.js",
            "styles.css",
            "data/suites.json",
            "data/behaviors.json",
            "widgets/suites.json",
            "widgets/behaviors.json",
            "data/test-cases/test-one.json",
        ):
            (tmp_path / relative_path).write_text("{}", encoding="utf-8")
        (tmp_path / "widgets/summary.json").write_text(
            json.dumps({"statistic": {"total": 1}}), encoding="utf-8"
        )

        assert validate_report(tmp_path) == 1


def testAllureReportValidationRejectsEmptyOrIncompleteReports(
        tmp_path: Path,
) -> None:
        with pytest.raises(FileNotFoundError, match="missing required files"):
            validate_report(tmp_path)