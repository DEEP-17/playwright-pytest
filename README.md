# Travelfika Playwright tests (Python)

This project ports the TypeScript suite's page-object organization and flight,
hotel, and trip-planner flows to synchronous Playwright with pytest.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Install the browser with `python -m playwright install chromium`.
4. Copy `.env.example` to `.env` and set `BASE_URL`, `USER_EMAIL`, and
   `USER_PASSWORD`.
5. Run the unit checks with `pytest tests/test_calendar_helper.py
   tests/test_support.py`, or run the end-to-end suite with `pytest`.

The end-to-end tests authenticate before each flow. Authentication state files,
environment files, traces, and test reports are excluded from version control.

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
