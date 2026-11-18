from pathlib import Path
from automationScripts.impactAnalysis import (
    ImpactReport,
    analyze_impact,
    github_lane_outputs,
    render_markdown,
)

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def testAnalyzesTransitivePageObjectDependencies(tmp_path: Path) -> None:
    _write(
        tmp_path / "testCases/endToEndTests/testHotel.py",
        "from pageObjectModel.hotelPages.hotelDetailPage import HotelDetailPage\n"
        "\ndef testHotelCheckout():\n    pass\n",
    )
    _write(
        tmp_path / "pageObjectModel/hotelPages/hotelDetailPage.py",
        "from pageObjectModel.basePage.basePage import BasePage\n",
    )
    _write(tmp_path / "pageObjectModel/basePage/basePage.py", "class BasePage: pass\n")
    _write(
        tmp_path / "testCases/unitTests/testSupport.py",
        "def testSettings():\n    pass\n",
    )
    report = analyze_impact(tmp_path, ["pageObjectModel/basePage/basePage.py"])
    assert report.scope == "targeted"
    assert report.impacted_tests == [
        "testCases.endToEndTests.testHotel::testHotelCheckout"
    ]
    assert "testSupport" not in render_markdown(report)

def testSharedFixtureChangeImpactsEveryTest(tmp_path: Path) -> None:
    _write(tmp_path / "testCases/endToEndTests/testHotel.py", "def testHotel(): pass\n")
    _write(tmp_path / "testCases/unitTests/testSupport.py", "def testSupport(): pass\n")
    _write(tmp_path / "pytestFixtures/appFixtures.py", "VALUE = 1\n")
    report = analyze_impact(tmp_path, ["pytestFixtures/appFixtures.py"])
    assert report.scope == "all"
    assert len(report.impacted_tests) == 2

def testDocumentationChangeHasNoTestImpact(tmp_path: Path) -> None:
    _write(tmp_path / "testCases/unitTests/testSupport.py", "def testSupport(): pass\n")
    _write(tmp_path / "README.md", "Project documentation\n")
    report = analyze_impact(tmp_path, ["README.md"])
    assert report.scope == "none"
    assert report.impacted_tests == []

def testGithubOutputsSelectImpactedTestLanes() -> None:
    report = ImpactReport(
        changed_files=[],
        impacted_tests=[
            "testCases.endToEndTests.testFlight::testE1",
            "testCases.endToEndTests.testTrip::testE12",
        ],
        scope="targeted",
    )
    assert github_lane_outputs(report) == {
        "flightTests": True,
        "hotelTests": False,
        "attractionsTests": False,
        "savedTripTests": True,
    }

def testCriticalFlowChangesSelectAllRelevantUiLanes() -> None:
    report = ImpactReport(
        changed_files=[],
        impacted_tests=[
            "testCases.endToEndTests.testCriticalFlows::testC8HotelRecovery"
        ],
        scope="targeted",
    )
    outputs = github_lane_outputs(report)
    assert outputs["flightTests"]
    assert outputs["hotelTests"]
    assert outputs["attractionsTests"]
    assert not outputs["savedTripTests"]