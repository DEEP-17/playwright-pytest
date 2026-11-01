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
5. Run the unit checks with `pytest tests/test_calendar_helper.py
   tests/test_support.py`, or run the end-to-end suite with `pytest`.

The end-to-end tests authenticate before each flow. Authentication state files,
environment files, traces, and test reports are excluded from version control.
The workbook's 23 non-network test executions are mapped to pytest cases
`E1-E14` (only IDs present in the workbook) and `C5-C22`; C7 runs once for
flights and once for hotels. The C14 slow-network scenario is deliberately
excluded from CI and was not run. Locator-based critical flows are implemented
in `tests/test_critical_flows.py` and can be selected with `pytest -m critical`.

## Browser session state and test data

Authenticated UI tests sign in once per pytest run, save browser state under the
ignored `.auth` directory, and restore it into each test context. Saved stage
states include cookies, local storage, IndexedDB, and session storage; they
contain authentication data and must not be committed. Flow page objects save
state at login, search, selection, and checkout milestones.

`data/objects.py` defines immutable typed test-data objects, and
`data/factory.py` builds them from `data/test_data.json` with support for nested
per-test overrides. Page objects consume these objects instead of unvalidated
dictionary keys.

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

Every pytest command streams verbose test output and DEBUG-level logs to the
Actions console and saves DEBUG-level Python logs as `test-results/pytest.log`.
Browser interaction logs show clicks, filled field labels, and selected
options, for example `[ui] Clicked button 'Search'`; raw network request logs
are disabled. Console warnings/errors and uncaught page errors remain visible.
Diagnostic text redacts query strings and known credential values. The final
report job combines the four
workbook JUnit reports into a 23-row `23-test-summary.html` and publishes the
same case-by-case results in the GitHub Actions job summary. It fails
validation if a result is missing, duplicated, skipped, or not passed.
The HTML/Markdown summary is also uploaded as `pytest-23-case-summary`.

Each authenticated lane creates its own `.auth` state locally on its
runner and verifies both storage-state files were written. These files contain
credentials and are deliberately not uploaded or shared between jobs. CI
artifacts contain pytest and JUnit reports, debug logs, browser failure media,
and a non-sensitive state-creation evidence manifest. The saved-trip flow
deletes an existing saved trip before creating one, so its automatic CI run
uses the configured test account. CI uploads per-job reports and a combined
bundle named `complete-pytest-reports`; the bundle includes the summary, logs,
session-state evidence, and failure screenshots, videos, and traces.
Pytest writes a self-contained HTML report to `test-results/report.html`;
failed browser tests also retain screenshots, videos, and traces.

## Page-object layout

- `pages/base`: shared navigation, state saving, waits, and calendar selection
- `pages/common`: home/login pages
- `pages/flights`, `pages/hotels`, `pages/trips`: domain-specific page objects
- `helpers`: reusable calendar interactions and date formatting
- `utils`: environment settings and shared test-data loading
- `fixtures`: page-object and authentication fixtures
- `hooks`: additional failure screenshots saved under `test-results/screenshots`
- `conftest.py`: registers the project fixtures and pytest hooks
- `data/test_data.json`: input data used by the corresponding end-to-end flows
