"""Deterministic dispatcher for Phase 2A LLM-derived intents.

Turns a validated IntentResult into one of the existing Jarvis-Core command
strings, a clarification/info reply, or nothing. This module never executes
anything itself: it only builds a command string for the caller to hand to
the existing, unmodified `_run_command()` in adapters/discord/bot_minimal.py,
or a plain-text reply for a non-executable / under-specified intent.

Security boundary: every argument is revalidated here regardless of what an
untrusted LLM claims. Only intents in EXECUTABLE_INTENTS/NON_EXECUTABLE_INTENTS
are recognized; anything else is rejected. There is no eval, no exec, no
subprocess, and no network call anywhere in this module. Command strings are
built only from a fixed per-intent template with validated arguments
substituted in -- never from raw LLM text directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from intent_schema import IntentResult, validate_bounded_text, validate_task_id

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
TASKS_DIR = REPO_ROOT / "memory" / "tasks"

# Mirrors the metadata parsing used by _read_task_metadata in
# adapters/discord/bot_minimal.py. Not imported directly: that module imports
# this package via intent_router, so importing back would create a circular
# import (same reasoning already documented in intent_router.py).
_TASK_META_LINE_PATTERN = re.compile(r"^- ([a-z_]+): `(.*)`$")
_TASK_STATUS_REQUIRED_FIELDS = ("id", "title", "status", "updated_at", "summary")

_APPROVE_DECISIONS = frozenset({"approve", "reject"})

# New, conservative default. No existing project-wide LLM-confidence
# threshold was found to reuse; this only gates EXECUTABLE_INTENTS command
# construction, never the read-only or clarification/info reply paths.
_MIN_EXECUTION_CONFIDENCE = 0.7

_MAX_SEARCH_RESULTS = 5

RESEARCH_COUNCIL_NOT_APPROVED_REPLY = "Research Council 연동은 아직 승인되지 않았습니다."
CONTINUE_TASK_CLARIFICATION = "어떤 task를 계속 진행할지 task ID를 알려주세요."
REPORT_YESTERDAY_CLARIFICATION = (
    "어제 기록만 따로 조회하는 기능은 아직 지원하지 않습니다. task ID 또는 오늘 기준으로 다시 물어봐 주세요."
)
MISSING_TASK_ID_CLARIFICATION = "어떤 task를 말씀하시는지 정확한 task ID를 알려주세요."
MISSING_TITLE_CLARIFICATION = "어떤 내용으로 task를 만들지 조금 더 자세히 말씀해주세요."
MISSING_QUERY_CLARIFICATION = "무엇을 찾아야 할지 조금 더 자세히 말씀해주세요."
MISSING_APPROVE_DECISION_CLARIFICATION = "승인할지 반려할지, 그리고 정확한 task ID를 알려주세요."
NO_SEARCH_MATCH_REPLY_TEMPLATE = "'{query}' 관련 task를 찾지 못했습니다."


@dataclass(frozen=True)
class DispatchOutcome:
    """Result of dispatch(). At most one of `command`/`reply` is set.

    Both None means: ignore, same as Phase 1's existing silent-ignore
    behavior for unmatched/unsupported text.
    """

    command: str | None = None
    reply: str | None = None


_IGNORE = DispatchOutcome()


def _read_task_metadata_minimal(task_file: Path) -> dict[str, str] | None:
    metadata: dict[str, str] = {}
    try:
        text = task_file.read_text(encoding="utf-8")
    except OSError:
        return None
    for raw_line in text.splitlines():
        matched = _TASK_META_LINE_PATTERN.match(raw_line.strip())
        if not matched:
            continue
        key, value = matched.groups()
        if key in _TASK_STATUS_REQUIRED_FIELDS:
            metadata[key] = value.strip()
    if not all(metadata.get(field) for field in _TASK_STATUS_REQUIRED_FIELDS):
        return None
    return metadata


def _search_tasks(query: str) -> str:
    """Read-only keyword search over memory/tasks/*.md title+summary.

    Mirrors the existing file-scan pattern used by _run_report in
    adapters/discord/bot_minimal.py (glob memory/tasks/*.md, parse `- key:
    `value`` lines). No arbitrary path input is accepted: `query` is a
    plain search string, never a filesystem path, and TASKS_DIR is fixed.
    """

    normalized_query = query.strip().lower()
    if not TASKS_DIR.exists() or not TASKS_DIR.is_dir():
        return NO_SEARCH_MATCH_REPLY_TEMPLATE.format(query=query)

    matches: list[dict[str, str]] = []
    for task_file in sorted(TASKS_DIR.glob("*.md")):
        metadata = _read_task_metadata_minimal(task_file)
        if metadata is None:
            continue
        haystack = f"{metadata.get('title', '')} {metadata.get('summary', '')}".lower()
        if normalized_query in haystack:
            matches.append(metadata)
        if len(matches) >= _MAX_SEARCH_RESULTS:
            break

    if not matches:
        return NO_SEARCH_MATCH_REPLY_TEMPLATE.format(query=query)

    lines = [
        f"{index}. {item['id']} — {item['title']} — {item['status']} — {item['updated_at']}"
        for index, item in enumerate(matches, start=1)
    ]
    return "검색 결과:\n" + "\n".join(lines)


def dispatch(result: IntentResult) -> DispatchOutcome:
    """Turn a validated IntentResult into a command, a reply, or nothing.

    Never raises on well-formed IntentResult input. Every branch either
    builds a command from a fixed template with revalidated arguments, or
    returns a fixed/derived reply string -- never raw LLM text as a command.
    """

    if not isinstance(result, IntentResult):
        return _IGNORE

    if result.clarification_needed:
        question = result.clarification_question
        if isinstance(question, str) and question.strip():
            return DispatchOutcome(reply=question.strip())
        return _IGNORE

    intent = result.intent

    if intent == "report_today":
        if result.confidence < _MIN_EXECUTION_CONFIDENCE:
            return _IGNORE
        return DispatchOutcome(command="/report today")

    if intent == "status":
        task_id = validate_task_id(result.arguments.get("task_id"))
        if task_id is None:
            return DispatchOutcome(reply=MISSING_TASK_ID_CLARIFICATION)
        if result.confidence < _MIN_EXECUTION_CONFIDENCE:
            return _IGNORE
        return DispatchOutcome(command=f"/status {task_id}")

    if intent == "create_task":
        title = validate_bounded_text(result.arguments.get("title"))
        if title is None:
            return DispatchOutcome(reply=MISSING_TITLE_CLARIFICATION)
        if result.confidence < _MIN_EXECUTION_CONFIDENCE:
            return _IGNORE
        return DispatchOutcome(command=f"/task {title}")

    if intent == "approve_task":
        task_id = validate_task_id(result.arguments.get("task_id"))
        decision = result.arguments.get("action")
        decision = decision.strip().lower() if isinstance(decision, str) else None
        if task_id is None or decision not in _APPROVE_DECISIONS:
            return DispatchOutcome(reply=MISSING_APPROVE_DECISION_CLARIFICATION)
        if result.confidence < _MIN_EXECUTION_CONFIDENCE:
            return _IGNORE
        return DispatchOutcome(command=f"/approve {task_id} {decision}")

    if intent == "search_tasks":
        query = validate_bounded_text(result.arguments.get("query"))
        if query is None:
            return DispatchOutcome(reply=MISSING_QUERY_CLARIFICATION)
        return DispatchOutcome(reply=_search_tasks(query))

    if intent == "continue_task":
        # Even with a syntactically valid task_id, Phase 2A does not wire an
        # execution path for continue_task -- inventing one here would be a
        # new execution route, which this phase explicitly does not add.
        return DispatchOutcome(reply=CONTINUE_TASK_CLARIFICATION)

    if intent == "report_yesterday":
        return DispatchOutcome(reply=REPORT_YESTERDAY_CLARIFICATION)

    if intent == "research_request":
        return DispatchOutcome(reply=RESEARCH_COUNCIL_NOT_APPROVED_REPLY)

    # "unsupported", or any intent string not explicitly handled above
    # (including anything outside SUPPORTED_INTENTS) is rejected here.
    return _IGNORE


__all__ = ["DispatchOutcome", "dispatch"]
