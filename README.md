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
Locator-based critical flows are implemented in `tests/test_critical_flows.py`
and can be selected with `pytest -m critical`. Network-throttling scenarios are
excluded from this UI-only set.

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

GitHub Actions runs the unit tests first, then fans out to separate session
state, public UI, flight UI, hotel UI, and authenticated critical-flow jobs.
Each UI job creates its own `.venv`; authenticated jobs are skipped unless the
repository secrets `BASE_URL`, `USER_EMAIL`, and `USER_PASSWORD` are set. The
public UI job requires `BASE_URL` but does not require login credentials.
The workflow runs on pushes, pull requests, manual dispatch, and daily at 02:00
UTC. The saved-trip flow is opt-in because it removes an existing saved trip;
run it manually with the `run_saved_trip_flow` workflow input.

## Page-object layout

- `pages/base`: shared navigation, state saving, waits, and calendar selection
- `pages/common`: home/login pages
- `pages/flights`, `pages/hotels`, `pages/trips`: domain-specific page objects
- `helpers`: reusable calendar interactions and date formatting
- `utils`: environment settings and shared test-data loading
- `fixtures`: page-object and authentication fixtures
- `hooks`: failure screenshots saved under `test-results/screenshots`
- `conftest.py`: registers the project fixtures and pytest hooks
- `data/test_data.json`: input data used by the corresponding end-to-end flows
