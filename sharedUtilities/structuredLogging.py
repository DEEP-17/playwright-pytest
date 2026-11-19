from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


def safe_log_message(message: str) -> str:
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
    return re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[REDACTED_EMAIL]",
        message,
        flags=re.IGNORECASE,
    )


def _safe_url(url: str) -> str:
    parsed = urlsplit(url)
    safe_authority = parsed.netloc.rsplit("@", 1)[-1]
    safe_url = urlunsplit((parsed.scheme, safe_authority, parsed.path, "", ""))
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


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": safe_log_message(record.getMessage()),
        }
        for field in (
            "event",
            "test_node_id",
            "test_phase",
            "captured_logs",
            "browser_diagnostics",
        ):
            value = getattr(record, field, None)
            if value is not None:
                if field == "event":
                    entry[field] = value
                elif isinstance(value, list):
                    entry[field] = [
                        safe_log_message(str(item)) for item in value
                    ]
                else:
                    entry[field] = safe_log_message(str(value))

        exception_text = getattr(record, "exception_text", None)
        if exception_text:
            entry["exception"] = safe_log_message(str(exception_text))
        elif record.exc_info:
            entry["exception"] = safe_log_message(
                self.formatException(record.exc_info)
            )
        return json.dumps(entry, ensure_ascii=False, default=str)


class FailureOnlyLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return (
            record.name == "pytest.failure"
            and getattr(record, "event", None) == "test_failure"
        )


def log_test_failure(
    node_id: str,
    phase: str,
    exception_text: str,
    captured_logs: str,
    browser_diagnostics: list[str],
) -> None:
    logging.getLogger("pytest.failure").error(
        "Test failed",
        extra={
            "event": "test_failure",
            "test_node_id": node_id,
            "test_phase": phase,
            "exception_text": exception_text,
            "captured_logs": captured_logs,
            "browser_diagnostics": browser_diagnostics,
        },
    )
