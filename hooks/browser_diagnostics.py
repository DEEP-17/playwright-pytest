import logging
import os
import re
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

import pytest
from playwright.sync_api import ConsoleMessage, Page, Request, Response

BROWSER_DIAGNOSTICS: pytest.StashKey[list[str]] = pytest.StashKey()


class _DiagnosticStash(Protocol):
    def setdefault(
        self, key: pytest.StashKey[list[str]], default: list[str], /
    ) -> list[str]: ...


class _StashNode(Protocol):
    stash: _DiagnosticStash


def _safe_url(url: str) -> str:
    parsed = urlsplit(url)
    safe_authority = parsed.netloc.rsplit("@", 1)[-1]
    safe_url = urlunsplit(
        (parsed.scheme, safe_authority, parsed.path, "", "")
    )
    for variable in ("USER_EMAIL", "USER_PASSWORD"):
        secret = os.environ.get(variable)
        if secret:
            safe_url = safe_url.replace(secret, "[REDACTED]")
    return re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[REDACTED_EMAIL]",
        safe_url,
        flags=re.IGNORECASE,
    )


def _safe_message(message: str) -> str:
    message = re.sub(
        r"https?://[^\s\"'<>]+",
        lambda match: _safe_url(match.group(0)),
        message,
    )
    for variable in ("USER_EMAIL", "USER_PASSWORD"):
        secret = os.environ.get(variable)
        if secret:
            message = message.replace(secret, "[REDACTED]")

    message = re.sub(
        r"(?i)(password|token|secret|authorization|cookie)(\s*[=:]\s*)"
        r"(['\"]?)[^,\s;'\"}]+",
        r"\1\2[REDACTED]",
        message,
    )
    message = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[REDACTED_EMAIL]",
        message,
        flags=re.IGNORECASE,
    )
    return message


def attach_browser_diagnostics(
    page: Page, node: _StashNode
) -> None:
    events = node.stash.setdefault(BROWSER_DIAGNOSTICS, [])
    attached_pages: set[int] = set()

    def record(level: int, message: str) -> None:
        safe_message = _safe_message(message)
        events.append(safe_message)
        logging.getLogger("playwright.browser").log(level, safe_message)

    def attach(target: Page) -> None:
        if id(target) in attached_pages:
            return
        attached_pages.add(id(target))

        def on_console(message: ConsoleMessage) -> None:
            levels = {"error": logging.ERROR, "warning": logging.WARNING}
            level = levels.get(message.type, logging.INFO)
            location = message.location
            source = _safe_url(location["url"]) if location.get("url") else ""
            record(
                level,
                f"[console:{message.type}] {source} {_safe_message(message.text)}",
            )

        def on_page_error(error: Exception) -> None:
            record(logging.ERROR, f"[pageerror] {_safe_message(str(error))}")

        def on_request(request: Request) -> None:
            record(
                logging.DEBUG,
                f"[request] {request.method} {_safe_url(request.url)}",
            )

        def on_request_failed(request: Request) -> None:
            failure = request.failure or "unknown failure"
            record(
                logging.ERROR,
                f"[requestfailed] {request.method} {_safe_url(request.url)} "
                f"({_safe_message(failure)})",
            )

        def on_response(response: Response) -> None:
            level = logging.ERROR if response.status >= 400 else logging.DEBUG
            label = "http-error" if response.status >= 400 else "response"
            record(
                level,
                f"[{label}] {response.status} {response.request.method} "
                f"{_safe_url(response.url)}",
            )

        target.on("console", on_console)
        target.on("pageerror", on_page_error)
        target.on("request", on_request)
        target.on("requestfailed", on_request_failed)
        target.on("response", on_response)
        target.on("popup", attach)

    attach(page)
