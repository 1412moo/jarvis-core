"""Provider-agnostic Intent Schema for the Discord NL intent layer (Phase 2A).

Defines the structured shape an LLM-derived intent must take before any
dispatch/execution decision is made. Pure Python, no I/O, no network, no LLM
call. This module never executes anything and never trusts raw LLM output
without validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

# Executable: intent_dispatcher.dispatch() may turn these into an existing
# Jarvis-Core command string.
EXECUTABLE_INTENTS = frozenset(
    {
        "report_today",
        "status",
        "create_task",
        "approve_task",
        "search_tasks",
    }
)

# Recognized but never turned into an executable command.
NON_EXECUTABLE_INTENTS = frozenset(
    {
        "continue_task",
        "report_yesterday",
        "research_request",
        "unsupported",
    }
)

SUPPORTED_INTENTS = EXECUTABLE_INTENTS | NON_EXECUTABLE_INTENTS

# Mirrors TASK_ID_PATTERN in adapters/discord/bot_minimal.py (same regex,
# same meaning). Not imported directly: that module imports this package via
# intent_router, so importing back would create a circular import (same
# reasoning already documented in intent_router.py for _TASK_ID_TOKEN_PATTERN).
TASK_ID_PATTERN = re.compile(r"^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")

# New, conservative bound. No existing project-wide argument/title length
# limit was found in intake_parser.py or task_draft_builder.py to reuse.
MAX_ARGUMENT_LENGTH = 200


@dataclass(frozen=True)
class IntentResult:
    """One validated, immutable LLM-derived intent. Never executed directly.

    Constructing an instance validates every field; malformed input raises
    ValueError rather than producing a half-valid object.
    """

    intent: str
    arguments: dict[str, str]
    confidence: float
    clarification_needed: bool
    clarification_question: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.intent, str) or not self.intent:
            raise ValueError("intent must be a non-empty string")
        if not isinstance(self.arguments, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in self.arguments.items()
        ):
            raise ValueError("arguments must be a dict[str, str]")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise ValueError("confidence must be a number")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError("confidence must be within [0.0, 1.0]")
        if not isinstance(self.clarification_needed, bool):
            raise ValueError("clarification_needed must be a bool")
        if self.clarification_question is not None and not isinstance(self.clarification_question, str):
            raise ValueError("clarification_question must be a string or None")
        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "arguments", dict(self.arguments))


def parse_intent_result(raw: Any) -> IntentResult | None:
    """Parse an untrusted raw dict (e.g. from an LLM) into an IntentResult.

    Returns None for any structurally malformed input instead of raising, so
    callers can fail closed without wrapping every call site in try/except.

    Does not check `intent` against SUPPORTED_INTENTS -- that allowlist check
    is intent_dispatcher.dispatch()'s job at execution time, per design.
    """

    if not isinstance(raw, dict):
        return None
    try:
        return IntentResult(
            intent=str(raw.get("intent", "")),
            arguments=dict(raw.get("arguments") or {}),
            confidence=float(raw.get("confidence", 0.0)),
            clarification_needed=bool(raw.get("clarification_needed", False)),
            clarification_question=(
                str(raw["clarification_question"]) if raw.get("clarification_question") is not None else None
            ),
        )
    except (TypeError, ValueError):
        return None


def validate_task_id(value: Any) -> str | None:
    """Return the task id if it matches the existing TASK_ID_PATTERN shape.

    Rejects anything else, including path-traversal-shaped strings, oversized
    input, or non-string values. Never trusts the caller-supplied shape.
    """

    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_ARGUMENT_LENGTH:
        return None
    if not TASK_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate


def validate_bounded_text(value: Any) -> str | None:
    """Return a stripped, non-empty, length-bounded text argument, else None."""

    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_ARGUMENT_LENGTH:
        return None
    return candidate


__all__ = [
    "EXECUTABLE_INTENTS",
    "NON_EXECUTABLE_INTENTS",
    "SUPPORTED_INTENTS",
    "TASK_ID_PATTERN",
    "MAX_ARGUMENT_LENGTH",
    "IntentResult",
    "parse_intent_result",
    "validate_task_id",
    "validate_bounded_text",
]
