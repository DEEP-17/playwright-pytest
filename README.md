# Travelfika Playwright tests (Python)

This project ports the TypeScript suite's page-object organization and flight,
hotel, and trip-planner flows to synchronous Playwright with pytest.

## Setup

1. Create and activate a virtual environment with `python -m venv .venv` and
   `.venv\Scripts\Activate.ps1` on Windows.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Install the browser with `python -m playwright install chromium`.
4. Copy `.env.example` to `.env` and set `BASE_URL`, `USER_EMAIL`, and
   `USER_PASSWORD`.
5. Run the unit checks with `pytest testCases/unitTests`, or run the 23
   workbook end-to-end cases with `pytest`.

The end-to-end tests authenticate before each flow. Authentication state files,
environment files, traces, and test reports are excluded from version control.
The workbook's 23 non-network test executions are mapped to pytest cases
`E1-E14` (only IDs present in the workbook) and `C5-C22`; C7 runs once for
flights and once for hotels. The C14 slow-network scenario is deliberately
excluded from CI and was not run. Locator-based critical flows are implemented
in `testCases/endToEndTests/testCriticalFlows.py` and can be selected with
`pytest -m critical`. Test files and functions use camelCase; pytest discovery
is configured for the `test*.py` and `test*` naming patterns. Default discovery
is limited to `testCases/endToEndTests`; unit tests remain explicitly runnable
and are still included in the CI preflight.

Use `pytest --skip-case C8` to skip a case by workbook ID, or pass a node-id
fragment such as `pytest --skip-case HotelGuestAge`. Add a reason with
`pytest --skip-case "C8=waiting for QA data"`; repeat the option to provide
separate reasons for multiple cases. Skipped reasons are recorded in JUnit and
Allure results and shown in the combined CI reports for follow-up. Skips do not
apply unless explicitly requested.

## Browser session state and test data

Authenticated UI tests sign in once per pytest run, save browser state under the
ignored `.authenticationState` directory, and restore it into each test
context. Saved stage states include cookies, local storage, IndexedDB, and
session storage; they contain authentication data and must not be committed.
Flow page objects save state at login, search, selection, and checkout
milestones.

`testData/testDataObjects.py` defines immutable typed test-data objects.
`testData/testDataFactory.py` builds them from `testData/testData.json`, and
`testData/testDataLoader.py` provides the shared loader. The factory supports
nested per-test overrides. Page objects consume typed objects instead of
unvalidated dictionary keys.

GitHub Actions runs unit and browser session-state checks together in one
preflight job, then branches into three separate, named Flight, Hotel, and
Attractions jobs (not a matrix). Each category job depends on preflight and has
its own selector, report, logs, and artifact. The category jobs run in parallel.
Every flight
listing and checkout scenario runs sequentially in its lane to avoid concurrent
search, repricing, and seat requests against the same QA itinerary. C15 also
checks browser back/forward recovery for both flight and hotel results. A
failure in one case does not stop later cases in its lane or other lanes. The
E12-E14 saved-trip scenarios run afterward because E14 deletes and creates
account-level saved-trip data. The final report job collects evidence from
every lane. Every suite runs on pushes,
pull requests, manual dispatch, and the daily 02:00 UTC schedule; missing
`BASE_URL`, `USER_EMAIL`, or `USER_PASSWORD` is reported as a test error
rather than silently skipping the job. Configure those repository secrets to
run the authenticated suites.

Page-object steps use Python's `logging` library. Pytest streams configured logs
to the console; `testResults/pytest.log` contains only failed-test records,
including captured logs, browser/UI diagnostics, exception details, and test
context as one JSON object per line. A successful run removes the empty log
file. CI can override console levels to stream DEBUG output. Browser/UI
diagnostics are captured per test and replayed to the console only when that
test fails. UI
interactions use a separate cyan, bold `UI` log level; browser warnings and
errors use pytest's severity colors. Diagnostics are also attached to the
failed test's JUnit/HTML report. Network request logs are not captured. UI
messages identify actions and labels, never typed field values. Diagnostic text
redacts query strings and known credential values. The final report job
combines JUnit reports from the executed lanes and
publishes case-by-case results in the GitHub Actions job summary. Push runs
validate all 23 workbook cases; pull requests run the impacted UI lanes and
validate the selected results. The report fails if a result is duplicated,
skipped, or not passed, except that E9's skip is non-blocking when the site's
repricing response produces a nonnumeric total. E9 remains visible as skipped
and is not counted as passed. Once the fare is numeric again, E9 must pass
normally.
The HTML/Markdown summary is also uploaded as `pytest-23-case-summary`.

Each authenticated lane creates its own `.authenticationState` directory on its
runner and verifies that both storage-state files were written. Pytest clears
stale state before a run and deletes every stage-state file when the session
ends; CI also deletes the local log and performs unconditional session-state
cleanup after uploading artifacts. These files contain credentials and are
never uploaded or shared between jobs. CI
artifacts contain pytest and JUnit reports, failure-only logs, browser failure
media, and a non-sensitive state-creation/cleanup evidence manifest. Successful
runs do not retain a `pytest.log` file. The saved-trip flow
deletes an existing saved trip before creating one, so its automatic CI run
uses the configured test account. CI uploads per-job reports and a combined
bundle named `complete-pytest-reports`; the bundle includes the summary, logs,
session-state evidence, and failure screenshots, videos, and traces.
The workflow also runs Codacy's static-analysis action as an independent
quality check. Codacy exports a SARIF report as the `codacy-sarif-report`
artifact and publishes findings to GitHub code scanning when repository
permissions allow it. Workflow permissions default to read-only, newer runs
cancel superseded runs on the same branch or pull request, and external actions
are pinned to commit SHAs. Dependabot checks GitHub Actions dependencies weekly.
Pytest writes a styled, self-contained HTML report to `testResults/report.html`
with run totals, pass rate, suite labels, failure diagnostics, and environment
metadata. It includes outcome and per-suite charts. Allure results are written
to `testResults/allureResults`; failed browser tests also retain screenshots,
videos, and traces. CI combines the Allure results and
uploads the generated HTML report as the `allure-report` artifact.
After downloading and extracting that artifact, double-click `OPEN_REPORT.bat`
in the extracted report folder. This serves the report on localhost and opens
it in your browser; do not open `index.html` directly, because browser
`file://` restrictions block the report data and make the page appear empty or
return 404 for report JSON. If that happens, close the `index.html` tab and run
`OPEN_REPORT.bat`. The workflow validates the report's test-data files and
localhost routes before publishing the artifact. Python 3 must be installed.
The combined CI test-case summary is available as the interactive
`pytest-23-case-summary` artifact, with category totals, outcome and per-area
charts, search, status filters, and expandable failure detail. To generate the
Allure HTML report locally, install Allure CLI with Java 17 and run
`allure generate testResults/allureResults --clean -o testResults/allureReport`.

Pull requests run a dependency-based impact analysis. It lists changed files
and affected pytest cases in the PR workflow summary, selects affected UI
lanes, and uploads JSON/Markdown reports as the
`pull-request-impact-analysis` artifact. If impact analysis fails, all UI lanes
run as a safe fallback. Shared configuration, fixtures, data, helper, and
hook changes conservatively impact the full test suite.

## Project layout

- `testCases/unitTests`: unit and local support checks
- `testCases/endToEndTests`: browser-driven flight, hotel, trip, and critical flows
- `pageObjectModel/basePage`: shared navigation, state saving, waits, and calendar
  selection
- `pageObjectModel/commonPages`: home/login pages and shared calendar facade
- `pageObjectModel/flightPages`, `pageObjectModel/hotelPages`,
  `pageObjectModel/tripPages`: domain-specific page objects
- `testHelpers`: reusable calendar interactions and date formatting
- `sharedUtilities`: environment settings and browser session-state helpers
- `pytestFixtures`: page-object and authentication fixtures
- `pytestHooks`: skip tracking and failure diagnostics
- `automationScripts`: CI summaries, PR impact analysis, and Allure report viewer
- `conftest.py`: registers the project fixtures and pytest hooks
- `testData`: typed data objects, factory, loader, and JSON input
- `testCases/endToEndTests` and `testCases/unitTests`: browser and local test suites
