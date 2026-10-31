from pathlib import Path

from playwright.sync_api import Browser

from utils.session_state import restore_session_storage, save_browser_state


def test_browser_state_round_trip_restores_cookies_and_all_web_storage(
    browser: Browser, tmp_path: Path
) -> None:
    url = "https://state.example.test"
    first_context = browser.new_context()
    first_page = first_context.new_page()
    first_page.route(
        "**/*",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="<html><body>state test</body></html>",
        ),
    )
    first_page.goto(url)
    first_page.evaluate(
        """() => {
            localStorage.setItem("local-key", "local-value");
            sessionStorage.setItem("session-key", "session-value");
            document.cookie = "cookie-key=cookie-value; path=/; secure";
        }"""
    )
    first_page.evaluate(
        """async () => {
            const database = await new Promise((resolve, reject) => {
                const request = indexedDB.open("state-test", 1);
                request.onupgradeneeded = () =>
                    request.result.createObjectStore("records");
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
            await new Promise((resolve, reject) => {
                const transaction = database.transaction("records", "readwrite");
                transaction.objectStore("records").put(
                    "indexed-value", "indexed-key"
                );
                transaction.oncomplete = resolve;
                transaction.onerror = () => reject(transaction.error);
            });
            database.close();
        }"""
    )
    state_files = save_browser_state(
        first_context, "round-trip-state.json", tmp_path
    )
    first_context.close()

    second_context = browser.new_context(
        storage_state=str(state_files.storage_state)
    )
    try:
        second_page = second_context.new_page()
        second_page.route(
            "**/*",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body="<html><body>state test</body></html>",
            ),
        )
        restore_session_storage(second_context, state_files.session_storage)
        second_page.goto(url)

        assert second_page.evaluate("() => localStorage.getItem('local-key')") == (
            "local-value"
        )
        assert second_page.evaluate(
            "() => sessionStorage.getItem('session-key')"
        ) == "session-value"
        assert second_page.evaluate("() => document.cookie") == (
            "cookie-key=cookie-value"
        )
        indexed_value = second_page.evaluate(
            """async () => {
                const database = await new Promise((resolve, reject) => {
                    const request = indexedDB.open("state-test", 1);
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                const value = await new Promise((resolve, reject) => {
                    const request = database
                        .transaction("records")
                        .objectStore("records")
                        .get("indexed-key");
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
                database.close();
                return value;
            }"""
        )
        assert indexed_value == "indexed-value"
    finally:
        second_context.close()
