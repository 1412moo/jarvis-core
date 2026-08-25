"""Rule-based natural-language to existing-command translator (Phase 1, no LLM).

Scope:
- Pure function, no I/O, no network call, no LLM/API call.
- Converts free-form Korean text into one of the exact command strings that
  `adapters/discord/bot_minimal.py::_run_command` already understands.
- Ambiguous or unrecognized input returns None rather than guessing.

Out of scope:
- Any command execution, file read/write, or Discord API access.
- Fuzzy task search (e.g. matching a task by topic keyword instead of an
  explicit task-id) is intentionally not handled in Phase 1.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from intent_dispatcher import DispatchOutcome, dispatch
from intent_schema import parse_intent_result
from llm_provider import call_llm_for_intent

# Mirrors the task-id token shape enforced by TASK_ID_PATTERN in
# adapters/discord/bot_minimal.py. Not imported directly: that module imports
# this one, so importing back would create a circular import.
_TASK_ID_TOKEN_PATTERN = re.compile(r"task-\d{4}(?:-[a-z0-9]+)*")

_REPORT_TODAY_PATTERN = re.compile(r"오늘.*(할\s*일|정리)")
_STATUS_PATTERN = re.compile(r"상태|진행\s*상황|어떻게")

_Rule = tuple["re.Pattern[str]", Callable[[str, "re.Match[str]"], "str | None"]]


def _build_report_today_command(_text: str, _match: "re.Match[str]") -> str | None:
    return "/report today"


def _build_status_command(text: str, _match: "re.Match[str]") -> str | None:
    task_id_match = _TASK_ID_TOKEN_PATTERN.search(text)
    if task_id_match is None:
        return None
    return f"/status {task_id_match.group(0)}"


_RULES: tuple[_Rule, ...] = (
    (_REPORT_TODAY_PATTERN, _build_report_today_command),
    (_STATUS_PATTERN, _build_status_command),
)


def resolve_intent(text: str) -> str | None:
    """Translate free-form text into an existing command string, or None.

    Slash-prefixed input is never expected here (the caller only forwards
    non-slash text) and is rejected defensively if it ever arrives, so a
    resolved command can never bypass the caller's own slash-command routing.
    """

    if not isinstance(text, str):
        return None
    stripped = text.strip()
    if not stripped or stripped.startswith("/"):
        return None

    for pattern, build in _RULES:
        match = pattern.search(stripped)
        if match is None:
            continue
        command = build(stripped, match)
        if command is not None:
            return command
    return None


def resolve_llm_fallback(text: str) -> DispatchOutcome:
    """Phase 2A fallback path -- only call this after resolve_intent(text)
    returned None (a rule miss). This function never re-tries rule matching
    itself; it is the caller's responsibility (bot_minimal.py::on_message) to
    try resolve_intent() first and only fall back here on a miss, so rule
    priority and "no LLM call on a rule match" are guaranteed by call order,
    not by anything inside this function.

    Calls the LLM provider boundary at most once. Any failure, malformed
    response, or unsupported/low-confidence/invalid-argument result degrades
    to an empty DispatchOutcome (ignore) -- the same behavior Phase 1 already
    has for unmatched text.
    """

    raw = call_llm_for_intent(text)
    if raw is None:
        return DispatchOutcome()

    intent_result = parse_intent_result(raw)
    if intent_result is None:
        return DispatchOutcome()

    return dispatch(intent_result)


__all__ = ["resolve_intent", "resolve_llm_fallback"]
