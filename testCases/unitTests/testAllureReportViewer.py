import json
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

from scripts.openAllureReport import create_server


def testAllureViewerServesReportDataOverHttp(tmp_path: Path) -> None:
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
