import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext

from utils.config import PROJECT_ROOT


@dataclass(frozen=True)
class BrowserStateFiles:
    storage_state: Path
    session_storage: Path


def state_files(
    file_name: str, directory: Path | None = None
) -> BrowserStateFiles:
    if Path(file_name).name != file_name or not file_name.endswith(".json"):
        raise ValueError("Browser-state file names must be simple .json names.")
    state_directory = directory or PROJECT_ROOT / ".auth"
    state_directory.mkdir(parents=True, exist_ok=True)
    storage_state = state_directory / file_name
    session_storage = storage_state.with_name(
        f"{storage_state.stem}.session-storage.json"
    )
    return BrowserStateFiles(storage_state, session_storage)


def save_browser_state(
    context: BrowserContext, file_name: str, directory: Path | None = None
) -> BrowserStateFiles:
    files = state_files(file_name, directory)
    context.storage_state(path=str(files.storage_state), indexed_db=True)

    session_storage: dict[str, dict[str, str]] = {}
    for page in context.pages:
        if page.is_closed() or not page.url.startswith(("http://", "https://")):
            continue
        origin = page.evaluate("() => location.origin")
        values = page.evaluate(
            "() => Object.fromEntries("
            "Array.from({ length: sessionStorage.length }, (_, index) => "
            "[sessionStorage.key(index), sessionStorage.getItem("
            "sessionStorage.key(index))]))"
        )
        if isinstance(origin, str) and isinstance(values, dict):
            session_storage[origin] = values

    files.session_storage.write_text(
        json.dumps(session_storage, indent=2), encoding="utf-8"
    )
    return files


def restore_session_storage(context: BrowserContext, session_storage_file: Path) -> None:
    with session_storage_file.open(encoding="utf-8") as session_file:
        session_storage: Any = json.load(session_file)
    if not isinstance(session_storage, dict):
        raise ValueError(
            f"Session storage must be a JSON object: {session_storage_file}"
        )
    if not all(
        isinstance(origin, str)
        and isinstance(values, dict)
        and all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in values.items()
        )
        for origin, values in session_storage.items()
    ):
        raise ValueError(
            f"Session storage contains invalid origin data: {session_storage_file}"
        )

    context.add_init_script(
        script=_session_storage_restore_script(session_storage)
    )


def _session_storage_restore_script(
    session_origins: dict[str, object]
) -> str:
    serialized = json.dumps(session_origins)
    return (
        "(() => {"
        f"const state = {serialized};"
        "const sessionState = state[location.origin];"
        "if (sessionState) {"
        "for (const [key, value] of Object.entries(sessionState)) "
        "sessionStorage.setItem(key, value);"
        "}"
        "})();"
    )
