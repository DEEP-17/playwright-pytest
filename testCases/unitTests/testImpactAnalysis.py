from pathlib import Path

from scripts.impactAnalysis import analyze_impact, render_markdown


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def testAnalyzesTransitivePageObjectDependencies(tmp_path: Path) -> None:
    _write(
        tmp_path / "testCases/e2eTests/testHotel.py",
        "from pages.hotels.hotel_detail_page import HotelDetailPage\n"
        "\ndef testHotelCheckout():\n    pass\n",
    )
    _write(
        tmp_path / "pages/hotels/hotel_detail_page.py",
        "from pages.base.base_page import BasePage\n",
    )
    _write(tmp_path / "pages/base/base_page.py", "class BasePage: pass\n")
    _write(
        tmp_path / "testCases/unitTests/testSupport.py",
        "def testSettings():\n    pass\n",
    )

    report = analyze_impact(tmp_path, ["pages/base/base_page.py"])

    assert report.scope == "targeted"
    assert report.impacted_tests == [
        "testCases.e2eTests.testHotel::testHotelCheckout"
    ]
    assert "testSupport" not in render_markdown(report)


def testSharedFixtureChangeImpactsEveryTest(tmp_path: Path) -> None:
    _write(tmp_path / "testCases/e2eTests/testHotel.py", "def testHotel(): pass\n")
    _write(tmp_path / "testCases/unitTests/testSupport.py", "def testSupport(): pass\n")
    _write(tmp_path / "fixtures/app_fixtures.py", "VALUE = 1\n")

    report = analyze_impact(tmp_path, ["fixtures/app_fixtures.py"])

    assert report.scope == "all"
    assert len(report.impacted_tests) == 2


def testDocumentationChangeHasNoTestImpact(tmp_path: Path) -> None:
    _write(tmp_path / "testCases/unitTests/testSupport.py", "def testSupport(): pass\n")
    _write(tmp_path / "README.md", "Project documentation\n")

    report = analyze_impact(tmp_path, ["README.md"])

    assert report.scope == "none"
    assert report.impacted_tests == []
