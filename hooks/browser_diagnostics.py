import json
import logging
import os
import re
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

import pytest
from playwright.sync_api import ConsoleMessage, Page

BROWSER_DIAGNOSTICS: pytest.StashKey[list[str]] = pytest.StashKey()


class _DiagnosticStash(Protocol):
    def setdefault(
        self, key: pytest.StashKey[list[str]], default: list[str], /
    ) -> list[str]: ...


class _StashNode(Protocol):
    stash: _DiagnosticStash


_UI_INTERACTION_SCRIPT = r"""
(() => {
  if (window.__pytestUiLogInstalled) return;
  window.__pytestUiLogInstalled = true;

  const fieldValues = new WeakMap();
  const normalize = (value) => (value || "").replace(/\s+/g, " ").trim().slice(0, 100);
  const labelFor = (element) => {
    const ariaLabel = element.getAttribute("aria-label");
    if (ariaLabel) return normalize(ariaLabel);
    if (element.labels && element.labels.length) {
      const label = Array.from(element.labels).map((item) => item.innerText).join(" ");
      if (label) return normalize(label);
    }
    return normalize(
      element.getAttribute("placeholder") ||
      element.getAttribute("title") ||
      element.innerText ||
      element.textContent
    );
  };
  const emit = (action, target, labelOverride) => {
    const label = normalize(labelOverride || labelFor(target));
    const role = target.getAttribute("role");
    const tag = target.tagName.toLowerCase();
    const type = (target.getAttribute("type") || "").toLowerCase();
    let control = role || (
      tag === "button" ? "button" :
      tag === "a" ? "link" :
      tag === "select" ? "dropdown" :
      tag === "textarea" ? "textbox" :
      tag === "input" && type === "checkbox" ? "checkbox" :
      tag === "input" && type === "radio" ? "radio" :
      tag === "input" ? "textbox" : "control"
    );
    if (!label) return;
    console.debug("__PYTEST_UI__" + JSON.stringify({ action, control, label }));
  };

  document.addEventListener("focusin", (event) => {
    const target = event.target;
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
      fieldValues.set(target, target.value);
    }
  }, true);

  document.addEventListener("focusout", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return;
    const previous = fieldValues.get(target);
    if (previous !== undefined && previous !== target.value) {
      const sensitive = target.type === "password" ||
        /password|token|secret|email/i.test(
          [target.name, target.id, target.getAttribute("autocomplete")].join(" ")
        );
      emit("Filled", target, labelFor(target) || (sensitive ? "sensitive field" : "field"));
    }
    fieldValues.set(target, target.value);
  }, true);

  document.addEventListener("change", (event) => {
    const target = event.target;
    if (target instanceof HTMLSelectElement) {
      const selected = Array.from(target.selectedOptions).map((option) => option.innerText).join(", ");
      emit("Selected", target, `${labelFor(target)}: ${selected}`);
    } else if (target instanceof HTMLInputElement &&
      (target.type === "checkbox" || target.type === "radio")) {
      emit(target.checked ? "Selected" : "Cleared", target);
    }
  }, true);

  document.addEventListener("click", (event) => {
    const target = event.target.closest(
      'button, a, [role="button"], [role="tab"], [role="menuitem"], [role="option"], ' +
      '[role="radio"], [role="checkbox"], input[type="checkbox"], input[type="radio"], ' +
      'select, label, [tabindex], [onclick]'
    );
    if (target) emit("Clicked", target);
  }, true);
})();
"""


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
            if message.text.startswith("__PYTEST_UI__"):
                try:
                    interaction = json.loads(
                        message.text.removeprefix("__PYTEST_UI__")
                    )
                except json.JSONDecodeError:
                    record(logging.WARNING, "[ui] Could not decode interaction log")
                    return
                record(
                    logging.INFO,
                    f"[ui] {interaction['action']} {interaction['control']} "
                    f"'{interaction['label']}'",
                )
                return
            if message.type not in {"error", "warning"}:
                return
            levels = {"error": logging.ERROR, "warning": logging.WARNING}
            level = levels.get(message.type, logging.INFO)
            record(
                level,
                f"[console:{message.type}] {_safe_message(message.text)}",
            )

        def on_page_error(error: Exception) -> None:
            record(logging.ERROR, f"[pageerror] {_safe_message(str(error))}")

        target.on("console", on_console)
        target.on("pageerror", on_page_error)
        target.on("popup", attach)
        target.add_init_script(_UI_INTERACTION_SCRIPT)
        if target.url != "about:blank":
            target.evaluate(_UI_INTERACTION_SCRIPT)

    attach(page)
