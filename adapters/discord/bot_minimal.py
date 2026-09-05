"""Minimal Discord bot adapter for jarvis-core intake pipeline.

Scope (this step):
- Accept text commands: /task <내용>, /status <task-id>, /report
- Reuse existing intake pipeline:
  intake_parser -> task_draft_builder -> task_file_writer
- Read existing task markdown for status lookup

Out of scope:
- GitHub execution/report automation/DB/web UI
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import discord
except ModuleNotFoundError:
    discord = None  # type: ignore[assignment]


THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
CODEBASE_ROOT = THIS_DIR.parent.parent
INTAKE_DIR = REPO_ROOT / "orchestrator" / "discord-intake"
if str(INTAKE_DIR) not in sys.path:
    sys.path.insert(0, str(INTAKE_DIR))

NL_INTENT_DIR = REPO_ROOT / "orchestrator" / "discord-nl-intent"
if str(NL_INTENT_DIR) not in sys.path:
    sys.path.insert(0, str(NL_INTENT_DIR))

# task-0052. The directory name has a hyphen, so it can never be a Python package -
# absolute imports off sys.path, the same convention the two directories above use.
AUDIT_CHAIN_DIR = REPO_ROOT / "orchestrator" / "audit-chain"
if str(AUDIT_CHAIN_DIR) not in sys.path:
    sys.path.insert(0, str(AUDIT_CHAIN_DIR))

from intake_parser import parse_intake
from task_draft_builder import build_task_draft
from task_file_writer import (
    TASK_STATUS_TRANSITIONS,
    transition_task_file_status,
    write_task_file,
)
from intent_router import resolve_intent, resolve_llm_fallback
from audit_entry import AuditChainError
from audit_store import (
    record_execution_result,
    record_owner_approval,
    resolve_audit_chain_paths,
)
from audit_verifier import verify_audit_chain

TASK_ID_PATTERN = re.compile(r"^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
TASK_META_LINE_PATTERN = re.compile(r"^- ([a-z_]+): `(.*)`$")
TASK_STATUS_REQUIRED_FIELDS = ("id", "title", "status", "updated_at", "summary")
TASK_EXECUTION_REVIEW_FIELDS = (
    "execution_candidate",
    "execution_request",
    "execution_result",
    "executed",
    "success",
    "dry_run",
    "error",
    "mode",
    "reason",
    "message",
    "execution_status",
    "execution_updated_at",
    "execution_summary",
)
TASK_EXECUTION_STATUS_FIELDS = (
    "execution_candidate",
    "execution_request",
    "execution_result",
    "executed",
    "success",
    "dry_run",
    "error",
    "mode",
    "reason",
    "message",
    "execution_status",
    "execution_updated_at",
    "execution_summary",
)
RETRY_ALLOWED_STATUSES = frozenset({"FAILED", "DOING"})
RUN_ALLOWED_STATUSES = frozenset({"DOING"})
REPORT_STATUS_ORDER = ("TODO", "DOING", "BLOCKED", "DONE", "FAILED", "NEEDS_APPROVAL")
ALLOWED_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "TODO": ("DOING",),
    "DOING": ("DONE",),
    "FAILED": ("TODO",),
    "NEEDS_APPROVAL": ("DOING", "FAILED"),
}
CONTRACT_APPROVE_STATES = frozenset({"NEEDS_APPROVAL", "DOING", "FAILED"})
CONTRACT_APPROVE_TRANSITIONS = frozenset(
    {
        ("NEEDS_APPROVAL", "DOING"),
        ("NEEDS_APPROVAL", "FAILED"),
    }
)
PLAN_ALWAYS_FILES = ("docs/codex-workflow.md",)
REVIEW_ALWAYS_FILES = ("docs/codex-workflow.md",)
PLAN_KEYWORD_FILE_MAP: dict[str, tuple[str, ...]] = {
    "approve": ("docs/approve-file-writer-contract.md", "adapters/discord/bot_minimal.py"),
    "task": ("docs/command-to-task.md", "adapters/discord/bot_minimal.py"),
    "status": ("docs/status-report-contract.md", "docs/status-report-flow.md", "adapters/discord/bot_minimal.py"),
    "report": ("docs/status-report-contract.md", "docs/status-report-flow.md", "adapters/discord/bot_minimal.py"),
    "intake": ("docs/discord-command-intake.md", "orchestrator/discord-intake/intake_parser.py"),
    "parser": ("orchestrator/discord-intake/intake_parser.py", "docs/discord-command-intake.md"),
}
REVIEW_KEYWORD_FILE_MAP: dict[str, tuple[str, ...]] = {
    "approve": ("docs/approve-file-writer-contract.md", "adapters/discord/bot_minimal.py"),
    "status": ("docs/status-report-contract.md", "docs/status-report-flow.md", "adapters/discord/bot_minimal.py"),
    "report": ("docs/status-report-contract.md", "docs/status-report-flow.md", "adapters/discord/bot_minimal.py"),
    "task": ("docs/command-to-task.md", "adapters/discord/bot_minimal.py"),
    "intake": ("docs/discord-command-intake.md", "orchestrator/discord-intake/intake_parser.py"),
    "parser": ("orchestrator/discord-intake/intake_parser.py", "docs/discord-command-intake.md"),
}
PLAN_DIRECTIONAL_KEYWORDS = ("architecture", "workflow", "north-star", "long-term", "execution")
EXECUTION_SCRIPT_WHITELIST: dict[tuple[str, str], tuple[str, ...]] = {
    (
        "plan_script_execution",
        "discord_intake_smoke_tests",
    ): ("python", "orchestrator/discord-intake/run_smoke_tests.py"),
}
EXECUTION_TIMEOUT_SECONDS = 10
EXECUTION_OUTPUT_MAX_CHARS = 220

# Commands that change task state or reach _run_execution_flow() (which spawns
# a whitelisted subprocess). Only an Owner may run these. Read-only commands
# (/status, /report, /help, /plan, /review-task, /retro) stay open to everyone
# and are deliberately absent from this set.
PRIVILEGED_COMMANDS = frozenset({"/approve", "/run", "/retry", "/task"})
# Name of the env var holding the Owner allowlist. The NAME is safe to log;
# the VALUE never is (see _load_owner_ids).
OWNER_IDS_ENV = "JARVIS_OWNER_DISCORD_USER_IDS"

# Outbound-only Buzz notification publisher (P2-5). Deliberately a separate
# constant from EXECUTION_SCRIPT_WHITELIST: publishing a notification is not
# task execution and must never become reachable from /run or /retry.
NOTIFICATION_PUBLISHER_COMMAND = ("node", "orchestrator/buzz-bridge/publish_notification.js")
# A cold publish is connect + NIP-42 auth + channel lookup + publish, each
# with its own 10s relay timeout, plus channel creation on first use.
NOTIFICATION_PUBLISH_TIMEOUT_SECONDS = 60


# ---------------------------------------------------------------------------
# Common / shared helpers
# ---------------------------------------------------------------------------
def _load_env_file(env_path: Path) -> None:
    """Very small .env loader to avoid extra dependencies."""
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _error_payload(reason: str) -> dict[str, Any]:
    return {"result_type": "error", "reason": reason}


# ---------------------------------------------------------------------------
# Owner authorization (P2-4)
#
# The approval boundary lives in exactly one place: the single gate in
# on_message() just before _run_command(). The approval pipeline itself
# (_run_approve_parse and everything under it) is deliberately left unchanged
# and unaware of identity -- adding a second gate inside it would create two
# boundaries that can drift apart.
# ---------------------------------------------------------------------------
def _load_owner_ids() -> frozenset[str]:
    """Parse the Owner allowlist from the environment. Never logs its value.

    Missing, empty, or fully malformed configuration yields an EMPTY set, and
    every caller treats an empty set as "deny every privileged command" -- an
    unset variable must never read as "allow everyone".
    """

    raw = os.getenv(OWNER_IDS_ENV, "")
    # Discord user IDs are numeric snowflakes. A non-numeric entry is a typo,
    # not an identity: dropping it here means a malformed allowlist fails
    # closed at startup instead of silently matching nobody at runtime.
    return frozenset(part.strip() for part in raw.split(",") if part.strip().isdigit())


def _command_name(command_text: str) -> str:
    parts = command_text.strip().split()
    return parts[0] if parts else ""


def _is_privileged_command(command_text: str) -> bool:
    name = _command_name(command_text)
    if name in PRIVILEGED_COMMANDS:
        return True
    # _run_command() routes with str.startswith(), so a first token that merely
    # STARTS WITH a privileged name (e.g. "/approvex") still reaches that
    # handler. Classify those as privileged too rather than relying on each
    # handler's own exact-name recheck to catch them.
    return any(name.startswith(privileged) for privileged in PRIVILEGED_COMMANDS)


def _authorize_command(command_text: str, author_id: str) -> tuple[bool, str | None]:
    """Decide whether `author_id` may run `command_text`.

    Returns (True, None) to allow, (False, "unauthorized") to deny. Any
    unexpected error denies -- there is no path through this function that
    falls back to allow. The denial reason is deliberately generic: it never
    reveals who the Owner is, or whether an allowlist is configured at all.
    """

    try:
        if not _is_privileged_command(command_text):
            return True, None
        owner_ids = _load_owner_ids()
        if not owner_ids:
            return False, "unauthorized"
        if not isinstance(author_id, str):
            # Exact string identity only. An int id (discord.py's native type)
            # must be converted by the caller, never coerced here, so that
            # 123 can never be mistaken for "123".
            return False, "unauthorized"
        if author_id not in owner_ids:
            return False, "unauthorized"
        return True, None
    except Exception:  # noqa: BLE001 - fail closed on any unexpected error
        return False, "unauthorized"


# ---------------------------------------------------------------------------
# Buzz task-status notification (P2-5, outbound only)
#
# Jarvis owns the approval decision; Buzz is a notification surface and
# nothing else. Everything below runs AFTER the approval is already
# committed to disk and already reported to the Owner, so it can only ever
# report a fact - it can never influence, delay, or reverse one. A failure
# here is a failed notification, never a failed approval.
# ---------------------------------------------------------------------------
def _notification_payload_for_result(result: dict[str, Any]) -> dict[str, Any] | None:
    """Return the payload to publish, or None when nothing may be published.

    Only a CONFIRMED approve/reject qualifies: the one result shape that
    means a task file was actually transitioned. Usage errors, holds,
    applied=False, and every non-approve command return None.
    """

    if not isinstance(result, dict):
        return None
    if result.get("result_type") != "approve_file_write_result":
        return None
    if result.get("applied") is not True:
        return None

    applied_transition = result.get("applied_transition")
    if not isinstance(applied_transition, dict):
        return None
    transition_from = applied_transition.get("from")
    transition_to = applied_transition.get("to")
    task_id = result.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        return None
    if not isinstance(transition_from, str) or not isinstance(transition_to, str):
        return None
    if not transition_from or not transition_to:
        return None

    # Status transition FACT only. The decision verb (approve/reject) stays
    # on the Jarvis side of the boundary; Buzz is told what changed, never
    # what it means or what to do about it.
    return {
        "task_id": task_id,
        "from": transition_from,
        "to": transition_to,
        "execution_status_transition_applied": bool(result.get("execution_status_transition_applied")),
        "ts": _utc_now_minutes(),
    }


def _utc_now_minutes() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _run_notification_publisher(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the outbound publisher. Returns a structured outcome, never raises.

    Mirrors the repo's existing python->node subprocess pattern: fixed
    argument list (no shell), explicit utf-8, bounded timeout, check=False,
    and every exception mapped to a structured result. This is deliberately
    NOT routed through EXECUTION_SCRIPT_WHITELIST - notification is not task
    execution, and must not become reachable from /run or /retry.
    """

    try:
        completed = subprocess.run(
            list(NOTIFICATION_PUBLISHER_COMMAND),
            cwd=str(CODEBASE_ROOT),
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=NOTIFICATION_PUBLISH_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "notification_publish_timeout"}
    except OSError:
        return {"ok": False, "reason": "notification_publisher_start_failed"}

    if completed.returncode != 0:
        detail = _summarize_execution_output(completed.stdout or "", completed.stderr or "")
        return {"ok": False, "reason": f"notification_publish_failed:exit_code:{completed.returncode}", "detail": detail}
    return {"ok": True, "reason": "", "detail": _summarize_execution_output(completed.stdout or "", "")}


def _publish_approval_notification(result: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort publish. Returns None when nothing was eligible.

    Never mutates `result`, never raises, and its return value is never fed
    back into the approval result. The caller may use it only to tell the
    Owner that the NOTIFICATION failed - never that the approval did.
    """

    try:
        payload = _notification_payload_for_result(result)
        if payload is None:
            return None
        return _run_notification_publisher(payload)
    except Exception as exc:  # noqa: BLE001 - a notification must never escalate
        return {"ok": False, "reason": "notification_unexpected_error", "detail": type(exc).__name__}


# ---------------------------------------------------------------------------
# Audit hash chain (task-0052)
#
# Read this next to _publish_approval_notification() above: the two look alike and
# are opposites. A notification is best-effort and its failure must never look like
# a failed approval (P2-2/P2-5). An audit append is the reverse - task-0044 section
# 6.1 forbids fire-and-forget, so its failure DOES fail the approval.
#
# Ordering is decision 1 (ii-b): the transition is applied first, the append second,
# and a failed append is NOT rolled back. The approval then answers as a failure
# with the task left in DOING and no record - a visible, stuck state that cannot be
# retried (status_mismatch blocks it), which is what prevents a double execution.
#
# This adds no second identity boundary. The approval pipeline stays unaware of who
# the caller is, exactly as the P2-4 note above requires, and the payload schema
# rejects owner identity outright (FORBIDDEN_PAYLOAD_KEYS).
# ---------------------------------------------------------------------------
AUDIT_APPEND_FAILED = "audit_append_failed"


def _record_audit_event(record_fn: Any, **fields: Any) -> str | None:
    """Append one audit entry. Returns None on success, a stable code on failure.

    Decision 7: only the stable code leaves this function. The detail - paths,
    hashes, OS errors - goes to stderr for local diagnosis and never into a reply.
    """

    try:
        record_fn(**fields)
        return None
    except AuditChainError as exc:
        print(f"[audit] append failed: {exc.code} detail={exc.detail}", file=sys.stderr)
        return exc.code
    except Exception as exc:  # noqa: BLE001 - an audit failure must never crash the bot
        print(f"[audit] append failed: unexpected {type(exc).__name__}", file=sys.stderr)
        return AUDIT_APPEND_FAILED


def _audit_owner_approval(
    *,
    command: str,
    decision: str,
    transition_from: str,
    transition_to: str,
    applied: bool,
    reason: str,
) -> str | None:
    """Record one /approve decision, applied or refused (decision 3)."""

    return _record_audit_event(
        record_owner_approval,
        task_id=_audit_task_id(command),
        command=command,
        decision=decision,
        transition_from=transition_from,
        transition_to=transition_to,
        applied=applied,
        reason=reason,
    )


def _audit_task_id(command: str) -> str:
    parts = command.strip().split()
    return parts[1].strip().lower() if len(parts) > 1 else ""


def _audit_execution_result(
    *,
    task_id: str,
    source: str,
    execution_result: dict[str, Any] | None,
    applied: bool,
    reason: str,
) -> str | None:
    """Record one execution outcome (decision 4).

    result_kind stays on the existing {success, failure} values and the finer
    distinction rides the existing reason vocabulary - "policy refused it" already
    arrives as execution_not_executed. No new vocabulary is invented here.
    """

    executed = bool((execution_result or {}).get("executed", False))
    succeeded = bool((execution_result or {}).get("success", False))
    return _record_audit_event(
        record_execution_result,
        task_id=task_id,
        source=source,
        execution_status_transition_applied=applied,
        # Strip any value the reason carries: task-0044 decision 5 keeps codes free
        # of values, and the payload is a record, not a diagnostic channel.
        execution_status_transition_reason=str(reason or "").split(":", 1)[0],
        result_kind="success" if (executed and succeeded) else "failure",
    )


# ---------------------------------------------------------------------------
# Task intake + status/report metadata helpers
# ---------------------------------------------------------------------------
def _run_task_pipeline(command_text: str) -> dict[str, Any]:
    parser_result = parse_intake(command_text).to_dict()
    if parser_result.get("error_reason"):
        error_reason = str(parser_result.get("error_reason"))
        if error_reason == "missing_required_arg:request":
            return _error_payload("usage:/task <request>")
        return _error_payload(error_reason)

    if parser_result.get("hold_reason"):
        return {"result_type": "hold", "reason": str(parser_result.get("hold_reason"))}

    draft_result = build_task_draft(parser_result).to_dict()
    if draft_result.get("result_type") != "task_draft":
        hold = draft_result.get("hold") or {}
        return {"result_type": "hold", "reason": str(hold.get("reason") or "draft_not_created")}

    task_draft = draft_result.get("task_draft") or {}
    file_result = write_task_file(task_draft).to_dict()

    if file_result.get("result_type") == "created":
        file_path = str(file_result.get("file_path") or "")
        return {
            "result_type": "success",
            "task_id": str(file_result.get("task_id") or ""),
            "file_name": Path(file_path).name,
            "file_path": file_path,
        }

    if file_result.get("result_type") == "hold":
        return {"result_type": "hold", "reason": str(file_result.get("reason") or "unknown_hold")}

    return _error_payload(str(file_result.get("reason") or "task_file_writer_failed"))


def _run_status_lookup(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 2:
        return _error_payload("usage:/status <task-id>")

    task_id = parts[1].strip().lower()
    if not task_id:
        return _error_payload("usage:/status <task-id>")
    if not TASK_ID_PATTERN.fullmatch(task_id):
        return _error_payload("invalid_task_id_format")

    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return {"result_type": "not_found", "task_id": task_id}

    try:
        metadata = _read_task_metadata(task_file)
        if metadata is None:
            return _error_payload("task_file_missing_fields:id,title,status,updated_at,summary")
        execution_metadata = _read_execution_status_metadata(task_file)
    except OSError:
        return _error_payload("task_file_read_failed")

    payload: dict[str, Any] = {
        "result_type": "status",
        "id": metadata["id"],
        "title": metadata["title"],
        "status": metadata["status"],
        "updated_at": metadata["updated_at"],
        "summary": metadata["summary"],
    }
    for key in TASK_EXECUTION_STATUS_FIELDS:
        value = execution_metadata.get(key)
        if value:
            payload[key] = value
    return payload


def _read_task_metadata(task_file: Path) -> dict[str, str] | None:
    metadata: dict[str, str] = {}
    for raw_line in task_file.read_text(encoding="utf-8").splitlines():
        matched = TASK_META_LINE_PATTERN.match(raw_line.strip())
        if not matched:
            continue
        key, value = matched.groups()
        if key in TASK_STATUS_REQUIRED_FIELDS:
            metadata[key] = value.strip()

    missing_fields = [field for field in TASK_STATUS_REQUIRED_FIELDS if not metadata.get(field)]
    if missing_fields:
        return None
    if not TASK_ID_PATTERN.fullmatch(metadata["id"]):
        return None

    return metadata


def _read_execution_review_metadata(task_file: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for raw_line in task_file.read_text(encoding="utf-8").splitlines():
        matched = TASK_META_LINE_PATTERN.match(raw_line.strip())
        if not matched:
            continue
        key, value = matched.groups()
        if key in TASK_EXECUTION_REVIEW_FIELDS:
            metadata[key] = value.strip()
    return metadata


def _read_execution_status_metadata(task_file: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for raw_line in task_file.read_text(encoding="utf-8").splitlines():
        matched = TASK_META_LINE_PATTERN.match(raw_line.strip())
        if not matched:
            continue
        key, value = matched.groups()
        if key in TASK_EXECUTION_STATUS_FIELDS:
            metadata[key] = value.strip()
    return metadata


def _build_report_payload(parsed_tasks: list[dict[str, str]]) -> dict[str, Any]:
    if not parsed_tasks:
        return {"result_type": "report_empty", "total": 0, "counts": {status: 0 for status in REPORT_STATUS_ORDER}, "recent": []}

    counts = {status: 0 for status in REPORT_STATUS_ORDER}
    for task in parsed_tasks:
        task_status = task["status"]
        if task_status in counts:
            counts[task_status] += 1

    def _sort_key(task: dict[str, str]) -> tuple[int, str]:
        updated_at = task["updated_at"]
        try:
            parsed = datetime.strptime(updated_at, "%Y-%m-%d %H:%M UTC")
            return int(parsed.timestamp()), updated_at
        except ValueError:
            return 0, updated_at

    recent = sorted(parsed_tasks, key=_sort_key, reverse=True)[:5]
    return {"result_type": "report", "total": len(parsed_tasks), "counts": counts, "recent": recent}


def _empty_report_payload() -> dict[str, Any]:
    return {"result_type": "report_empty", "total": 0, "counts": {status: 0 for status in REPORT_STATUS_ORDER}, "recent": []}


def _run_report(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 1:
        return _error_payload("usage:/report")

    tasks_dir = REPO_ROOT / "memory" / "tasks"
    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return _empty_report_payload()

    parsed_tasks: list[dict[str, str]] = []
    for task_file in sorted(tasks_dir.glob("*.md")):
        metadata = _read_task_metadata(task_file)
        if metadata is None:
            continue
        parsed_tasks.append(metadata)

    return _build_report_payload(parsed_tasks)


def _run_report_today(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 2 or parts[0] != "/report" or parts[1] != "today":
        return _error_payload("usage:/report today")

    tasks_dir = REPO_ROOT / "memory" / "tasks"
    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return _empty_report_payload()

    # NOTE: `/report today` uses UTC date 기준 (task `updated_at` 포맷과 동일).
    today_ymd = datetime.now(UTC).strftime("%Y-%m-%d")
    parsed_tasks: list[dict[str, str]] = []
    for task_file in sorted(tasks_dir.glob("*.md")):
        metadata = _read_task_metadata(task_file)
        if metadata is None:
            continue
        updated_date = metadata["updated_at"].split(" ", 1)[0]
        if updated_date == today_ymd:
            parsed_tasks.append(metadata)

    return _build_report_payload(parsed_tasks)


def _run_retro_today(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 2 or parts[0] != "/retro" or parts[1] != "today":
        return _error_payload("usage:/retro today")

    tasks_dir = REPO_ROOT / "memory" / "tasks"
    today_ymd = datetime.now(UTC).strftime("%Y-%m-%d")
    counts = {status: 0 for status in REPORT_STATUS_ORDER}
    total = 0
    completed_titles: list[str] = []
    follow_up_titles: list[str] = []

    if tasks_dir.exists() and tasks_dir.is_dir():
        for task_file in sorted(tasks_dir.glob("*.md")):
            metadata = _read_task_metadata(task_file)
            if metadata is None:
                continue
            updated_date = metadata["updated_at"].split(" ", 1)[0]
            if updated_date != today_ymd:
                continue

            total += 1
            task_status = metadata["status"]
            if task_status in counts:
                counts[task_status] += 1
            title = metadata["title"]
            if task_status == "DONE":
                completed_titles.append(title)
            if task_status in {"FAILED", "BLOCKED"}:
                follow_up_titles.append(title)

    blocked_or_failed = counts["FAILED"] + counts["BLOCKED"]
    if total == 0:
        summary_line = "no task updates found today"
    elif blocked_or_failed > 0:
        summary_line = "today had blocked/failed items that may need follow-up"
    else:
        summary_line = f"today moved forward on {total} tasks"

    return {
        "result_type": "retro_today",
        "total": total,
        "counts": counts,
        "completed_titles": completed_titles,
        "follow_up_titles": follow_up_titles,
        "summary_line": summary_line,
    }


def _run_help(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 1 or parts[0] != "/help":
        return _error_payload("usage:/help")

    return {
        "result_type": "help",
        "lines": [
            "/task <request> - task 생성",
            "/plan <request> - 작업 계획 초안 생성",
            "/review-task <task-id> - task 상세 검토",
            "/approve <task-id> approve|reject - 승인/반려",
            "/run <task-id> - DOING task 실행",
            "/retry <task-id> - FAILED/DOING task 재실행",
            "/status <task-id> - 단건 상태 확인",
            "/report - 전체 task 집계",
            "/report today - 오늘 업데이트 task 집계",
            "/retro today - 오늘 회고 요약",
        ],
    }


def _run_plan_draft(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split(maxsplit=1)
    if len(parts) != 2 or not parts[1].strip():
        return _error_payload("usage:/plan <request>")

    request = parts[1].strip()
    lowered_request = request.lower()
    files_to_check: list[str] = list(PLAN_ALWAYS_FILES)

    for keyword, mapped_files in PLAN_KEYWORD_FILE_MAP.items():
        if keyword in lowered_request:
            for path in mapped_files:
                if path not in files_to_check:
                    files_to_check.append(path)

    if any(keyword in lowered_request for keyword in PLAN_DIRECTIONAL_KEYWORDS):
        if "docs/project-north-star.md" not in files_to_check:
            files_to_check.append("docs/project-north-star.md")

    return {
        "result_type": "plan_draft",
        "goal": request,
        "files_to_check": files_to_check,
        "scope_summary": "Discord /plan 최소 버전에서 계획 초안 생성까지만 수행",
        "out_of_scope": [
            "파일 저장/승인/실행 레이어 확장 금지",
            "memory/tasks 반영 금지",
            "기존 /task /status /report /approve 동작 변경 금지",
        ],
        "codex_prompt": f"다음 요청의 최소 계획 초안을 작성하라: {request}. codex-workflow 규칙을 준수하고 범위 밖 확장을 금지하라.",
    }


def _build_review_notes(status: str) -> str:
    if status == "TODO":
        return "아직 구현 전 또는 계획 단계일 수 있음"
    if status == "DOING":
        return "진행 중 작업으로 보임"
    if status == "DONE":
        return "완료 상태로 보임"
    if status == "FAILED":
        return "실패 원인/재시도 계획 점검 필요"
    if status == "NEEDS_APPROVAL":
        return "승인 대기 상태로 보임"
    if status == "BLOCKED":
        return "차단 원인과 해소 조건 점검 필요"
    return "상태 정보 점검 필요"


def _build_recommended_next_steps(status: str) -> list[str]:
    if status == "TODO":
        return ["요구사항과 범위를 다시 확인한다", "작업 착수 조건을 정리한다"]
    if status == "DOING":
        return ["진행 중 산출물을 점검한다", "남은 작업을 우선순위로 정리한다"]
    if status == "DONE":
        return ["검증 근거와 결과를 최종 점검한다"]
    if status == "FAILED":
        return ["실패 원인을 명시한다", "재시도 조건과 계획을 정리한다"]
    if status == "NEEDS_APPROVAL":
        return ["승인 요청 항목과 사유를 점검한다", "승인 후 즉시 수행할 다음 작업을 정리한다"]
    if status == "BLOCKED":
        return ["차단 원인을 summary에 명확히 기록한다", "의존 주체와 재시도 조건을 확인한다"]
    return ["task 메타데이터를 점검한다"]


def _build_related_files(metadata: dict[str, str]) -> list[str]:
    related_files: list[str] = list(REVIEW_ALWAYS_FILES)
    searchable_text = f"{metadata.get('id', '')} {metadata.get('title', '')} {metadata.get('summary', '')}".lower()
    for keyword, mapped_files in REVIEW_KEYWORD_FILE_MAP.items():
        if keyword in searchable_text:
            for path in mapped_files:
                if path not in related_files:
                    related_files.append(path)
    return related_files


def _run_review_task(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 2:
        return _error_payload("usage:/review-task <task-id>")

    task_id = parts[1].strip()
    if not task_id:
        return _error_payload("usage:/review-task <task-id>")
    if not TASK_ID_PATTERN.fullmatch(task_id):
        return _error_payload("invalid_task_id_format")

    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return {"result_type": "not_found", "task_id": task_id}

    metadata = _read_task_metadata(task_file)
    if metadata is None:
        return _error_payload("task_file_missing_fields:id,title,status,updated_at,summary")
    execution_metadata = _read_execution_review_metadata(task_file)

    status = metadata["status"]
    return {
        "result_type": "review_task_result",
        "task_id": metadata["id"],
        "title": metadata["title"],
        "status": status,
        "updated_at": metadata["updated_at"],
        "summary": metadata["summary"],
        "execution_status": execution_metadata.get("execution_status", ""),
        "execution_updated_at": execution_metadata.get("execution_updated_at", ""),
        "execution_summary": execution_metadata.get("execution_summary", ""),
        "review_notes": _build_review_notes(status),
        "recommended_next_steps": _build_recommended_next_steps(status),
        "related_files": _build_related_files(metadata),
    }


# ---------------------------------------------------------------------------
# Approve transition helpers
# ---------------------------------------------------------------------------
def _build_approve_draft(parse_result: dict[str, Any]) -> dict[str, Any]:
    if parse_result.get("result_type") != "approve_parse":
        return _error_payload("approve_parse_required")

    decision = str(parse_result.get("decision") or "")
    task_id = str(parse_result.get("task_id") or "")
    if decision == "approve":
        transition_to = "DOING"
    elif decision == "reject":
        transition_to = "FAILED"
    else:
        return _error_payload("usage:/approve <task-id> approve|reject")

    return {
        "result_type": "approve_draft",
        "draft_type": "approve_status_transition_draft",
        "task_id": task_id,
        # task-0052: owner_approval requires both of these, and decision 5-b needs
        # `decision` to keep a rejection out of the execution flow. One wiring, two
        # uses - which is why 5-b is cheap to include here.
        "command": str(parse_result.get("command") or ""),
        "decision": decision,
        "proposed_transition": {"from": "NEEDS_APPROVAL", "to": transition_to},
        "apply_ready": True,
        "hold_reason": None,
    }


def _build_approve_writer_input(approve_draft: dict[str, Any]) -> dict[str, Any]:
    if approve_draft.get("result_type") != "approve_draft":
        return _error_payload("approve_draft_required")

    return {
        "result_type": "approve_writer_input",
        "draft_type": str(approve_draft.get("draft_type") or ""),
        "task_id": str(approve_draft.get("task_id") or ""),
        "command": str(approve_draft.get("command") or ""),
        "decision": str(approve_draft.get("decision") or ""),
        "proposed_transition": approve_draft.get("proposed_transition") or {},
        "apply_ready": bool(approve_draft.get("apply_ready", False)),
        "hold_reason": approve_draft.get("hold_reason"),
    }


def _approve_writer_result_fail(*, task_id: str, reason: str, kind: str) -> dict[str, Any]:
    return {
        "result_type": "approve_file_write_result",
        "task_id": task_id,
        "applied": False,
        "error": kind == "error",
        "reason": reason,
        "kind": kind,
    }


def _allowed_transition_targets(transition_from: str) -> tuple[str, ...]:
    return ALLOWED_STATUS_TRANSITIONS.get(transition_from, ())


def _is_allowed_status_transition(transition_from: str, transition_to: str) -> bool:
    return transition_to in _allowed_transition_targets(transition_from)


def _validate_status_transition(transition_from: str, transition_to: str) -> tuple[bool, str]:
    if not _is_allowed_status_transition(transition_from, transition_to):
        return False, "invalid_transition"
    return True, ""


def _validate_approve_transition(transition_from: str, transition_to: str) -> tuple[bool, str]:
    return _validate_status_transition(transition_from, transition_to)


def _validate_approve_transition_contract_sync() -> tuple[bool, list[str]]:
    reasons: list[str] = []

    code_approve_transitions = frozenset(
        ("NEEDS_APPROVAL", target)
        for target in _allowed_transition_targets("NEEDS_APPROVAL")
    )
    code_approve_states = frozenset({"NEEDS_APPROVAL", *(target for _, target in code_approve_transitions)})

    if code_approve_states != CONTRACT_APPROVE_STATES:
        reasons.append("approve_contract_state_set_mismatch")
    if code_approve_transitions != CONTRACT_APPROVE_TRANSITIONS:
        reasons.append("approve_contract_transition_set_mismatch")
    if not _is_allowed_status_transition("NEEDS_APPROVAL", "DOING") or not _is_allowed_status_transition(
        "NEEDS_APPROVAL", "FAILED"
    ):
        reasons.append("approve_contract_required_transition_missing")

    # task-0052. Until now this check compared only this module's own tables, so
    # task_file_writer's transition set could drift from what this path performs
    # and nobody would notice until a transition was refused at runtime - which is
    # exactly how the missing FAILED->TODO pair was found. Assert the writer's set
    # stays a superset of every transition this module can perform.
    local_transitions = frozenset(
        (source, target)
        for source, targets in ALLOWED_STATUS_TRANSITIONS.items()
        for target in targets
    )
    if not local_transitions.issubset(TASK_STATUS_TRANSITIONS):
        reasons.append("approve_contract_writer_transition_missing")

    return not reasons, reasons


# task-0052 decision 2, narrowed by section 10.3. Only these two transitions go
# through task_file_writer's durable writer. The rest run *after*
# _write_execution_review_metadata() has added execution fields that the writer's
# metadata validator rejects by design, and that validator is deliberately not
# being loosened - so those transitions keep the inline path below. This split is
# a known residual risk, recorded in the design document rather than hidden here.
DURABLE_STATUS_TRANSITIONS = frozenset(
    {("NEEDS_APPROVAL", "DOING"), ("NEEDS_APPROVAL", "FAILED")}
)


def _apply_task_status_transition(task_id: str, transition_from: str, transition_to: str) -> tuple[bool, str]:
    """Apply one task status transition, durably where that is possible.

    The (bool, reason) contract and its vocabulary are unchanged, so no caller has
    to know about the split: "task_not_found", "status_mismatch" and "write_failed"
    mean exactly what they meant before.
    """

    if (transition_from, transition_to) in DURABLE_STATUS_TRANSITIONS:
        return _apply_task_status_transition_durable(task_id, transition_from, transition_to)
    return _apply_task_status_transition_inline(task_id, transition_from, transition_to)


def _apply_task_status_transition_durable(task_id: str, transition_from: str, transition_to: str) -> tuple[bool, str]:
    """Approval transition via task_file_writer.transition_task_file_status().

    This is the transition the audit chain is laid over, so it is the one that has
    to be atomic: fsync, os.replace and an expected_digest concurrency check, none
    of which the inline path has. A chain over a write that can tear cannot tell
    corruption from tampering (task-0044 section 6.3).
    """

    tasks_dir = REPO_ROOT / "memory" / "tasks"
    task_file = tasks_dir / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return False, "task_not_found"

    try:
        original = task_file.read_bytes()
    except OSError:
        return False, "write_failed"

    # Pre-check the current status so the familiar "status_mismatch" still fires for
    # the ordinary case; a "stale" result from the writer then means a genuine
    # concurrent modification between our read and its write.
    current_status = ""
    for line in original.decode("utf-8", errors="replace").splitlines():
        matched = TASK_META_LINE_PATTERN.match(line.strip())
        if matched and matched.group(1) == "status":
            current_status = matched.group(2).strip()
    if current_status != transition_from:
        return False, "status_mismatch"

    result = transition_task_file_status(
        tasks_dir=tasks_dir,
        task_id=task_id,
        expected_digest=hashlib.sha256(original).hexdigest(),
        current_status=transition_from,
        target_status=transition_to,
        planned_updated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )

    if result.result_type == "updated":
        return True, ""
    if result.result_type == "stale":
        # Reuse the existing code rather than invent vocabulary (decision 4). The
        # writer's own reason is investigation detail and stays out of the return.
        return False, "status_mismatch"
    return False, "write_failed"


def _apply_task_status_transition_inline(task_id: str, transition_from: str, transition_to: str) -> tuple[bool, str]:
    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return False, "task_not_found"

    task_text = task_file.read_text(encoding="utf-8")
    has_trailing_newline = task_text.endswith("\n")
    lines = task_text.splitlines()
    status_line_index: int | None = None
    current_status = ""
    for idx, line in enumerate(lines):
        matched = TASK_META_LINE_PATTERN.match(line.strip())
        if not matched:
            continue
        key, value = matched.groups()
        if key == "status":
            status_line_index = idx
            current_status = value.strip()

    if status_line_index is None:
        return False, "write_failed"
    if current_status != transition_from:
        return False, "status_mismatch"

    lines[status_line_index] = f"- status: `{transition_to}`"
    updated_line_index: int | None = None
    for idx, line in enumerate(lines):
        matched = TASK_META_LINE_PATTERN.match(line.strip())
        if not matched:
            continue
        key, _ = matched.groups()
        if key == "updated_at":
            updated_line_index = idx
    if updated_line_index is not None:
        lines[updated_line_index] = f"- updated_at: `{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}`"

    new_text = "\n".join(lines)
    if has_trailing_newline:
        new_text += "\n"
    try:
        task_file.write_text(new_text, encoding="utf-8")
    except OSError:
        return False, "write_failed"
    return True, ""


def _metadata_json(value: dict[str, Any] | None) -> str:
    if not isinstance(value, dict):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _metadata_bool(value: bool) -> str:
    return "true" if value else "false"


def _write_execution_review_metadata(
    task_id: str,
    execution_result: dict[str, Any],
    execution_candidate: dict[str, Any] | None = None,
    execution_request: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return False, "task_not_found"

    executed = bool(execution_result.get("executed", False))
    success = bool(execution_result.get("success", False))
    reason = str(execution_result.get("error_reason") or "")
    message = str(execution_result.get("output_summary") or "")
    if executed and success:
        execution_status = "success"
    elif executed and not success:
        execution_status = "failed"
    else:
        execution_status = "not_executed"

    execution_summary = message or reason
    execution_updated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    values_by_key = {
        "execution_candidate": _metadata_json(execution_candidate),
        "execution_request": _metadata_json(execution_request),
        "execution_result": _metadata_json(execution_result),
        "executed": _metadata_bool(executed),
        "success": _metadata_bool(success),
        "dry_run": "false",
        "error": reason,
        "mode": "real",
        "reason": reason,
        "message": message,
        "execution_status": execution_status,
        "execution_updated_at": execution_updated_at,
        "execution_summary": execution_summary,
    }

    task_text = task_file.read_text(encoding="utf-8")
    has_trailing_newline = task_text.endswith("\n")
    lines = task_text.splitlines()
    existing_indexes: dict[str, int] = {}
    for idx, line in enumerate(lines):
        matched = TASK_META_LINE_PATTERN.match(line.strip())
        if not matched:
            continue
        key, _ = matched.groups()
        if key in TASK_EXECUTION_REVIEW_FIELDS:
            existing_indexes[key] = idx

    for key in TASK_EXECUTION_REVIEW_FIELDS:
        new_line = f"- {key}: `{values_by_key[key]}`"
        if key in existing_indexes:
            lines[existing_indexes[key]] = new_line
        else:
            lines.append(new_line)

    new_text = "\n".join(lines)
    if has_trailing_newline:
        new_text += "\n"
    try:
        task_file.write_text(new_text, encoding="utf-8")
    except OSError:
        return False, "write_failed"
    return True, ""


def _build_execution_candidate(task_id: str) -> dict[str, Any] | None:
    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return None

    metadata = _read_task_metadata(task_file)
    if metadata is None:
        return None

    title_summary = f"{metadata.get('title', '')} {metadata.get('summary', '')}".lower()
    if any(keyword in title_summary for keyword in ("script", "run", "demo")):
        script_target = "unknown_script_target"
        if any(keyword in title_summary for keyword in ("smoke", "demo")):
            script_target = "discord_intake_smoke_tests"
        return {
            "result_type": "execution_candidate",
            "task_id": task_id,
            "execution_type": "script",
            "action": "plan_script_execution",
            "target": script_target,
            "reason": "summary_or_title_contains_script_run_demo",
        }
    if "test" in title_summary or "검증" in f"{metadata.get('title', '')} {metadata.get('summary', '')}":
        return {
            "result_type": "execution_candidate",
            "task_id": task_id,
            "execution_type": "test",
            "action": "plan_test_execution",
            "reason": "summary_or_title_contains_test_or_검증",
        }
    return None


def _build_execution_request(execution_candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "result_type": "execution_request",
        "task_id": str(execution_candidate.get("task_id") or ""),
        "execution_type": str(execution_candidate.get("execution_type") or ""),
        "action": str(execution_candidate.get("action") or ""),
        "target": str(execution_candidate.get("target") or ""),
        "requested_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "approve_file_write_result",
    }


def _run_execution_flow(task_id: str, source: str) -> dict[str, Any]:
    execution_candidate = _build_execution_candidate(task_id)
    execution_request = None
    execution_result_dry_run = None
    execution_result = None
    execution_status_transition_applied = False
    execution_status_transition_reason = "execution_result_missing"
    if isinstance(execution_candidate, dict):
        execution_request = _build_execution_request(execution_candidate)
        execution_request["source"] = source
        execution_result_dry_run = _build_execution_result_dry_run(execution_request)
        execution_result = _build_execution_result_real(execution_request)
        _write_execution_review_metadata(task_id, execution_result, execution_candidate, execution_request)
        execution_status_transition_applied, execution_status_transition_reason = _apply_execution_result_status_transition(
            task_id, execution_result
        )
    # task-0052 E2. One hook, inside the flow - NOT at the three call sites. /approve,
    # /run and /retry all pass through here, and a fourth caller added later is covered
    # automatically; per-call-site hooks would let that fourth one slip out of the audit
    # silently, which is the same shape of gap that lets /run and /retry bypass /approve.
    #
    # Unlike the approval hook, a failure here cannot fail the work: the subprocess has
    # already run and nothing can un-run it (design section 9.1). So it is reported
    # loudly and carried out to the caller instead of being swallowed.
    audit_error = _audit_execution_result(
        task_id=task_id,
        source=source,
        execution_result=execution_result,
        applied=execution_status_transition_applied,
        reason=execution_status_transition_reason,
    )

    return {
        "execution_candidate": execution_candidate,
        "execution_request": execution_request,
        "execution_result_dry_run": execution_result_dry_run,
        "execution_result": execution_result,
        "execution_status_transition_applied": execution_status_transition_applied,
        "execution_status_transition_reason": execution_status_transition_reason,
        "audit_error": audit_error,
    }


def _run_retry(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 2:
        return _error_payload("usage:/retry <task-id>")
    if parts[0] != "/retry":
        return _error_payload("usage:/retry <task-id>")

    task_id = parts[1].strip().lower()
    if not task_id:
        return _error_payload("usage:/retry <task-id>")
    if not TASK_ID_PATTERN.fullmatch(task_id):
        return _error_payload("usage:/retry <task-id>")

    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return {"result_type": "not_found", "task_id": task_id}

    try:
        metadata = _read_task_metadata(task_file)
    except OSError:
        return _error_payload("task_file_read_failed")
    if metadata is None:
        return _error_payload("task_file_missing_fields:id,title,status,updated_at,summary")

    status = metadata.get("status") or ""
    if status not in RETRY_ALLOWED_STATUSES:
        return {
            "result_type": "retry_not_allowed",
            "task_id": task_id,
            "status": status,
            "reason": "retry_allowed_only_for:FAILED,DOING",
        }

    if _build_execution_candidate(task_id) is None:
        return {
            "result_type": "error",
            "reason": "retry_execution_candidate_missing",
            "task_id": task_id,
        }

    if status == "FAILED":
        todo_applied, todo_reason = _apply_task_status_transition(task_id, "FAILED", "TODO")
        if not todo_applied:
            return _error_payload(f"retry_status_prep_failed:{todo_reason}")
        doing_applied, doing_reason = _apply_task_status_transition(task_id, "TODO", "DOING")
        if not doing_applied:
            return _error_payload(f"retry_status_prep_failed:{doing_reason}")

    execution_flow = _run_execution_flow(task_id, "retry")
    execution_result = execution_flow.get("execution_result")
    return {
        "result_type": "retry_result",
        "task_id": task_id,
        "retried": True,
        "execution_result": execution_result,
        "execution_status_transition_applied": execution_flow.get("execution_status_transition_applied"),
        "execution_status_transition_reason": execution_flow.get("execution_status_transition_reason"),
        "audit_error": execution_flow.get("audit_error"),
    }


def _run_run(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 2:
        return _error_payload("usage:/run <task-id>")
    if parts[0] != "/run":
        return _error_payload("usage:/run <task-id>")

    task_id = parts[1].strip().lower()
    if not task_id:
        return _error_payload("usage:/run <task-id>")
    if not TASK_ID_PATTERN.fullmatch(task_id):
        return _error_payload("usage:/run <task-id>")

    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return {"result_type": "not_found", "task_id": task_id}

    try:
        metadata = _read_task_metadata(task_file)
    except OSError:
        return _error_payload("task_file_read_failed")
    if metadata is None:
        return _error_payload("task_file_missing_fields:id,title,status,updated_at,summary")

    status = metadata.get("status") or ""
    if status not in RUN_ALLOWED_STATUSES:
        return {
            "result_type": "run_not_allowed",
            "task_id": task_id,
            "status": status,
            "reason": "run_allowed_only_for:DOING",
        }

    if _build_execution_candidate(task_id) is None:
        return {
            "result_type": "error",
            "reason": "run_execution_candidate_missing",
            "task_id": task_id,
        }

    execution_flow = _run_execution_flow(task_id, "run")
    execution_result = execution_flow.get("execution_result")
    return {
        "result_type": "run_result",
        "task_id": task_id,
        "run_attempted": True,
        "execution_result": execution_result,
        "execution_status_transition_applied": execution_flow.get("execution_status_transition_applied"),
        "execution_status_transition_reason": execution_flow.get("execution_status_transition_reason"),
        "audit_error": execution_flow.get("audit_error"),
    }


def _build_execution_result_dry_run(execution_request: dict[str, Any]) -> dict[str, Any]:
    execution_type = str(execution_request.get("execution_type") or "")
    output_summary = "dry-run: execution planned"
    if execution_type == "script":
        output_summary = "dry-run: script execution planned"
    elif execution_type == "test":
        output_summary = "dry-run: test execution planned"

    return {
        "result_type": "execution_result",
        "task_id": str(execution_request.get("task_id") or ""),
        "execution_type": execution_type,
        "action": str(execution_request.get("action") or ""),
        "executed": False,
        "success": False,
        "output_summary": output_summary,
        "error_reason": "dry_run_not_executed",
    }


def _summarize_execution_output(stdout: str, stderr: str) -> str:
    merged = []
    if stdout.strip():
        merged.append(f"stdout={stdout.strip()}")
    if stderr.strip():
        merged.append(f"stderr={stderr.strip()}")
    if not merged:
        return "no_output"
    normalized = " | ".join(merged).replace("\n", " ").replace("\r", " ")
    if len(normalized) <= EXECUTION_OUTPUT_MAX_CHARS:
        return normalized
    return f"{normalized[:EXECUTION_OUTPUT_MAX_CHARS]}..."


def _build_execution_result_real(execution_request: dict[str, Any]) -> dict[str, Any]:
    task_id = str(execution_request.get("task_id") or "")
    execution_type = str(execution_request.get("execution_type") or "")
    action = str(execution_request.get("action") or "")
    target = str(execution_request.get("target") or "")
    base_payload = {
        "result_type": "execution_result",
        "task_id": task_id,
        "execution_type": execution_type,
        "action": action,
    }

    if execution_type != "script":
        return {
            **base_payload,
            "executed": False,
            "success": False,
            "output_summary": "",
            "error_reason": "execution_type_not_allowed",
        }

    command = EXECUTION_SCRIPT_WHITELIST.get((action, target))
    if command is None:
        return {
            **base_payload,
            "executed": False,
            "success": False,
            "output_summary": "",
            "error_reason": "script_action_target_not_whitelisted",
        }

    try:
        completed = subprocess.run(
            list(command),
            cwd=str(CODEBASE_ROOT),
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        summary = _summarize_execution_output(exc.stdout or "", exc.stderr or "")
        return {
            **base_payload,
            "executed": True,
            "success": False,
            "output_summary": summary,
            "error_reason": "execution_timeout",
        }
    except OSError:
        return {
            **base_payload,
            "executed": False,
            "success": False,
            "output_summary": "",
            "error_reason": "execution_start_failed",
        }

    success = completed.returncode == 0
    return {
        **base_payload,
        "executed": True,
        "success": success,
        "output_summary": _summarize_execution_output(completed.stdout, completed.stderr),
        "error_reason": "" if success else f"execution_failed:exit_code:{completed.returncode}",
    }


def _apply_execution_result_status_transition(task_id: str, execution_result: dict[str, Any] | None) -> tuple[bool, str]:
    if not isinstance(execution_result, dict):
        return False, "execution_result_missing"

    executed = execution_result.get("executed")
    success = execution_result.get("success")
    if not isinstance(executed, bool):
        return False, "execution_executed_not_boolean"
    if not executed:
        return False, "execution_not_executed"
    if not isinstance(success, bool):
        return False, "execution_success_not_boolean"

    transition_to = "DONE" if success else "FAILED"
    applied, reason = _apply_task_status_transition(task_id, "DOING", transition_to)
    if not applied:
        return False, f"transition_not_applied:{reason}"
    return True, ""


def _build_approve_writer_result(approve_writer_input: dict[str, Any]) -> dict[str, Any]:
    task_id = str(approve_writer_input.get("task_id") or "")
    proposed_transition = approve_writer_input.get("proposed_transition")
    apply_ready = bool(approve_writer_input.get("apply_ready", False))
    contract_ok, contract_reasons = _validate_approve_transition_contract_sync()
    if not contract_ok:
        return _approve_writer_result_fail(
            task_id=task_id,
            reason=f"approve_contract_mismatch:{','.join(contract_reasons)}",
            kind="error",
        )

    if approve_writer_input.get("result_type") != "approve_writer_input":
        return _approve_writer_result_fail(
            task_id=task_id,
            reason="invalid_writer_input",
            kind="error",
        )

    draft_type = str(approve_writer_input.get("draft_type") or "")
    if draft_type != "approve_status_transition_draft":
        return _approve_writer_result_fail(
            task_id=task_id,
            reason="invalid_writer_input",
            kind="error",
        )

    if not task_id:
        return _approve_writer_result_fail(
            task_id=task_id,
            reason="invalid_writer_input",
            kind="error",
        )

    if not isinstance(proposed_transition, dict):
        return _approve_writer_result_fail(
            task_id=task_id,
            reason="invalid_writer_input",
            kind="error",
        )

    transition_from = str(proposed_transition.get("from") or "")
    transition_to = str(proposed_transition.get("to") or "")
    if not transition_from or not transition_to:
        return _approve_writer_result_fail(
            task_id=task_id,
            reason="invalid_writer_input",
            kind="error",
        )

    transition_ok, transition_reason = _validate_approve_transition(transition_from, transition_to)
    if not transition_ok:
        return _approve_writer_result_fail(
            task_id=task_id,
            reason=transition_reason,
            kind="error",
        )

    command = str(approve_writer_input.get("command") or "")
    decision = str(approve_writer_input.get("decision") or "")

    if not apply_ready:
        # Decision 3: a refused attempt is evidence too. The transition pair is
        # already valid here, so the payload can be built.
        audit_error = _audit_owner_approval(
            command=command,
            decision=decision,
            transition_from=transition_from,
            transition_to=transition_to,
            applied=False,
            reason="apply_not_ready",
        )
        result = _approve_writer_result_fail(task_id=task_id, reason="apply_not_ready", kind="hold")
        result["audit_error"] = audit_error
        return result

    # Decision 1 (ii-b): transition first, audit second, and no rollback.
    applied, reason = _apply_task_status_transition(task_id, transition_from, transition_to)
    audit_error = _audit_owner_approval(
        command=command,
        decision=decision,
        transition_from=transition_from,
        transition_to=transition_to,
        applied=applied,
        reason=reason,
    )

    if not applied:
        reason_kind = "hold" if reason in ("task_not_found", "status_mismatch") else "error"
        result = _approve_writer_result_fail(task_id=task_id, reason=reason, kind=reason_kind)
        result["audit_error"] = audit_error
        return result

    if audit_error is not None:
        # The file already moved and is deliberately not rolled back, so say exactly
        # that instead of reporting a clean failure the Owner would misread. This is
        # the stuck state section 10.1 describes; recovery is a manual edit.
        result = _approve_writer_result_fail(task_id=task_id, reason=audit_error, kind="error")
        result["audit_error"] = audit_error
        result["applied_transition"] = {"from": transition_from, "to": transition_to}
        result["transition_applied_without_audit"] = True
        return result

    if decision == "reject":
        # Decision 5-b. A rejection must not reach _run_execution_flow(): it used to,
        # and a whitelisted target would then run a subprocess for a task the Owner
        # had just refused, after which the DOING-based transition failed silently as
        # status_mismatch. This is a semantics fix, separate from the audit wiring.
        return {
            "result_type": "approve_file_write_result",
            "task_id": task_id,
            "applied": True,
            "error": False,
            "reason": "",
            "applied_transition": {"from": transition_from, "to": transition_to},
            "execution_candidate": None,
            "execution_request": None,
            "execution_result_dry_run": None,
            "execution_result": None,
            "execution_status_transition_applied": False,
            "execution_status_transition_reason": "execution_skipped_on_reject",
            "audit_error": None,
        }

    execution_flow = _run_execution_flow(task_id, "approve_file_write_result")
    return {
        "result_type": "approve_file_write_result",
        "task_id": task_id,
        "applied": True,
        "error": False,
        "reason": "",
        "applied_transition": {"from": transition_from, "to": transition_to},
        "execution_candidate": execution_flow.get("execution_candidate"),
        "execution_request": execution_flow.get("execution_request"),
        "execution_result_dry_run": execution_flow.get("execution_result_dry_run"),
        "execution_result": execution_flow.get("execution_result"),
        "execution_status_transition_applied": execution_flow.get("execution_status_transition_applied"),
        "execution_status_transition_reason": execution_flow.get("execution_status_transition_reason"),
        "audit_error": execution_flow.get("audit_error"),
    }


def _run_approve_parse(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 3:
        return _error_payload("usage:/approve <task-id> approve|reject")
    if parts[0] != "/approve":
        return _error_payload("usage:/approve <task-id> approve|reject")

    task_id = parts[1].strip()
    decision = parts[2].strip()
    if not task_id:
        return _error_payload("usage:/approve <task-id> approve|reject")
    if decision not in ("approve", "reject"):
        return _error_payload("usage:/approve <task-id> approve|reject")

    parse_result = {
        "result_type": "approve_parse",
        "task_id": task_id,
        "decision": decision,
        "command": command_text.strip(),
    }
    approve_draft = _build_approve_draft(parse_result)
    if approve_draft.get("result_type") != "approve_draft":
        return approve_draft

    approve_writer_input = _build_approve_writer_input(approve_draft)
    if approve_writer_input.get("result_type") != "approve_writer_input":
        return approve_writer_input

    return _build_approve_writer_result(approve_writer_input)


# ---------------------------------------------------------------------------
# Command routing / reply formatting
# ---------------------------------------------------------------------------
def _run_command(command_text: str) -> dict[str, Any]:
    content = command_text.strip()
    if content.startswith("/help"):
        return _run_help(content)
    if content.startswith("/review-task"):
        return _run_review_task(content)
    if content.startswith("/retro"):
        return _run_retro_today(content)
    if content.startswith("/plan"):
        return _run_plan_draft(content)
    if content.startswith("/task"):
        return _run_task_pipeline(content)
    if content.startswith("/status"):
        return _run_status_lookup(content)
    if content.startswith("/retry"):
        return _run_retry(content)
    if content.startswith("/run"):
        return _run_run(content)
    if content.startswith("/approve"):
        return _run_approve_parse(content)
    if content == "/report today" or content.startswith("/report today "):
        return _run_report_today(content)
    if content.startswith("/report"):
        return _run_report(content)
    return _error_payload("unsupported_command")


def _format_reply(pipeline_result: dict[str, Any]) -> str:
    result_type = pipeline_result.get("result_type")
    if result_type == "help":
        lines = pipeline_result.get("lines") or []
        body = "\n".join(f"- {line}" for line in lines) if lines else "- (없음)"
        return f"📘 help\n{body}"
    if result_type == "retro_today":
        counts = pipeline_result.get("counts") or {}
        completed = pipeline_result.get("completed_titles") or []
        follow_up = pipeline_result.get("follow_up_titles") or []
        completed_text = "\n".join(f"- {item}" for item in completed) if completed else "- (없음)"
        follow_up_text = "\n".join(f"- {item}" for item in follow_up) if follow_up else "- (없음)"
        return (
            "📋 retro today\n"
            f"- total: {pipeline_result.get('total', 0)}\n\n"
            "status summary:\n"
            f"- TODO: {counts.get('TODO', 0)}\n"
            f"- DOING: {counts.get('DOING', 0)}\n"
            f"- BLOCKED: {counts.get('BLOCKED', 0)}\n"
            f"- DONE: {counts.get('DONE', 0)}\n"
            f"- FAILED: {counts.get('FAILED', 0)}\n"
            f"- NEEDS_APPROVAL: {counts.get('NEEDS_APPROVAL', 0)}\n\n"
            f"completed today:\n{completed_text}\n\n"
            f"needs follow-up:\n{follow_up_text}\n\n"
            "summary:\n"
            f"- {pipeline_result.get('summary_line', '')}"
        )
    if result_type == "review_task_result":
        recommended = pipeline_result.get("recommended_next_steps") or []
        related_files = pipeline_result.get("related_files") or []
        execution_status = str(pipeline_result.get("execution_status") or "")
        execution_updated_at = str(pipeline_result.get("execution_updated_at") or "")
        execution_summary = str(pipeline_result.get("execution_summary") or "")
        recommended_text = "\n".join(f"- {item}" for item in recommended) if recommended else "- (없음)"
        related_text = "\n".join(f"- {path}" for path in related_files) if related_files else "- (없음)"
        return (
            "🧪 review task 결과\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- title: `{pipeline_result.get('title')}`\n"
            f"- status: `{pipeline_result.get('status')}`\n"
            f"- updated_at: `{pipeline_result.get('updated_at')}`\n"
            f"- summary: `{pipeline_result.get('summary')}`\n"
            f"- execution_status: `{execution_status or '(없음)'}`\n"
            f"- execution_updated_at: `{execution_updated_at or '(없음)'}`\n"
            f"- execution_summary: `{execution_summary or '(없음)'}`\n"
            f"- review_notes: `{pipeline_result.get('review_notes')}`\n\n"
            f"recommended_next_steps:\n{recommended_text}\n\n"
            f"related_files:\n{related_text}"
        )
    if result_type == "plan_draft":
        files_to_check = pipeline_result.get("files_to_check") or []
        out_of_scope = pipeline_result.get("out_of_scope") or []
        files_text = "\n".join(f"- {path}" for path in files_to_check) if files_to_check else "- (없음)"
        out_scope_text = "\n".join(f"- {item}" for item in out_of_scope) if out_of_scope else "- (없음)"
        return (
            "🧭 plan draft 생성 완료\n"
            f"- goal: `{pipeline_result.get('goal')}`\n"
            f"- scope_summary: `{pipeline_result.get('scope_summary')}`\n"
            f"- codex_prompt: `{pipeline_result.get('codex_prompt')}`\n\n"
            f"files_to_check:\n{files_text}\n\n"
            f"out_of_scope:\n{out_scope_text}"
        )
    if result_type == "success":
        return (
            "✅ task 생성 완료\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- file: `{pipeline_result.get('file_name')}`"
        )
    if result_type == "hold":
        return f"⏸️ hold\n- reason: `{pipeline_result.get('reason')}`"
    if result_type == "status":
        execution_lines: list[str] = []
        for key in ("executed", "success", "dry_run", "mode", "reason", "error", "message"):
            if key in pipeline_result and str(pipeline_result.get(key)).strip():
                execution_lines.append(f"- {key}: `{pipeline_result.get(key)}`")
        if "execution_status" in pipeline_result and str(pipeline_result.get("execution_status")).strip():
            execution_lines.append(f"- execution_status: `{pipeline_result.get('execution_status')}`")
        if "execution_updated_at" in pipeline_result and str(pipeline_result.get("execution_updated_at")).strip():
            execution_lines.append(f"- execution_updated_at: `{pipeline_result.get('execution_updated_at')}`")
        if "execution_summary" in pipeline_result and str(pipeline_result.get("execution_summary")).strip():
            execution_lines.append(f"- execution_summary: `{pipeline_result.get('execution_summary')}`")
        execution_text = "\n".join(execution_lines)
        reply = (
            "📄 task 정보\n"
            f"- id: `{pipeline_result.get('id')}`\n"
            f"- title: `{pipeline_result.get('title')}`\n"
            f"- status: `{pipeline_result.get('status')}`\n"
            f"- note: `{_build_review_notes(str(pipeline_result.get('status') or ''))}`\n"
            f"- updated_at: `{pipeline_result.get('updated_at')}`\n"
            f"\nsummary:\n`{pipeline_result.get('summary')}`"
        )
        if execution_text:
            reply += f"\n\nexecution:\n{execution_text}"
        return reply
    if result_type == "not_found":
        return f"⚠️ not found: `{pipeline_result.get('task_id')}`"
    if result_type == "approve_draft":
        proposed_transition = pipeline_result.get("proposed_transition") or {}
        return (
            "🧾 approve draft 생성 완료\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- draft_type: `{pipeline_result.get('draft_type')}`\n"
            f"- proposed_transition: `{proposed_transition.get('from')} -> {proposed_transition.get('to')}`\n"
            f"- apply_ready: `{pipeline_result.get('apply_ready')}`"
        )
    if result_type == "approve_writer_input":
        proposed_transition = pipeline_result.get("proposed_transition") or {}
        return (
            "🧾 approve writer input 생성 완료\n"
            f"- draft_type: `{pipeline_result.get('draft_type')}`\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- proposed_transition: `{proposed_transition.get('from')} -> {proposed_transition.get('to')}`\n"
            f"- apply_ready: `{pipeline_result.get('apply_ready')}`"
        )
    if result_type == "approve_file_write_result":
        if pipeline_result.get("applied") is True:
            applied_transition = pipeline_result.get("applied_transition") or {}
            execution_candidate = pipeline_result.get("execution_candidate")
            execution_result_dry_run = pipeline_result.get("execution_result_dry_run")
            execution_result = pipeline_result.get("execution_result")
            execution_status_transition_applied = pipeline_result.get("execution_status_transition_applied")
            execution_status_transition_reason = pipeline_result.get("execution_status_transition_reason")
            execution_line = ""
            if isinstance(execution_candidate, dict):
                execution_line = (
                    f"\n🚀 execution candidate 생성됨\n"
                    f"- execution_type: `{execution_candidate.get('execution_type')}`\n"
                    f"- action: `{execution_candidate.get('action')}`\n"
                    f"- target: `{execution_candidate.get('target')}`"
                )
            dry_run_line = ""
            if isinstance(execution_result_dry_run, dict):
                dry_run_line = (
                    f"\n🧪 dry-run execution result\n"
                    f"- executed: `{execution_result_dry_run.get('executed')}`\n"
                    f"- success: `{execution_result_dry_run.get('success')}`\n"
                    f"- output_summary: `{execution_result_dry_run.get('output_summary')}`\n"
                    f"- error_reason: `{execution_result_dry_run.get('error_reason')}`"
                )
            execution_result_line = ""
            if isinstance(execution_result, dict):
                execution_result_line = (
                    f"\n⚙️ execution result\n"
                    f"- executed: `{execution_result.get('executed')}`\n"
                    f"- success: `{execution_result.get('success')}`\n"
                    f"- output_summary: `{execution_result.get('output_summary')}`\n"
                    f"- error_reason: `{execution_result.get('error_reason')}`"
                )
            return (
                "🧾 approve file write result 생성 완료\n"
                f"- task_id: `{pipeline_result.get('task_id')}`\n"
                f"- applied: `{pipeline_result.get('applied')}`\n"
                f"- applied_transition: `{applied_transition.get('from')} -> {applied_transition.get('to')}`\n"
                f"- execution_status_transition_applied: `{execution_status_transition_applied}`\n"
                f"- execution_status_transition_reason: `{execution_status_transition_reason}`"
                f"{execution_line}"
                f"{dry_run_line}"
                f"{execution_result_line}"
            )
        return (
            "🧾 approve file write result 생성 완료\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- applied: `{pipeline_result.get('applied')}`\n"
            f"- kind: `{pipeline_result.get('kind')}`\n"
            f"- reason: `{pipeline_result.get('reason')}`"
        )
    if result_type == "retry_result":
        execution_result = pipeline_result.get("execution_result") or {}
        return (
            "🔁 retry result\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- retried: `{pipeline_result.get('retried')}`\n"
            f"- executed: `{execution_result.get('executed')}`\n"
            f"- success: `{execution_result.get('success')}`\n"
            f"- dry_run: `False`\n"
            f"- mode: `real`\n"
            f"- reason: `{execution_result.get('error_reason')}`\n"
            f"- message: `{execution_result.get('output_summary')}`\n"
            f"- execution_status_transition_applied: `{pipeline_result.get('execution_status_transition_applied')}`\n"
            f"- execution_status_transition_reason: `{pipeline_result.get('execution_status_transition_reason')}`"
        )
    if result_type == "retry_not_allowed":
        return (
            "⚠️ retry not allowed\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- status: `{pipeline_result.get('status')}`\n"
            f"- reason: `{pipeline_result.get('reason')}`"
        )
    if result_type == "run_result":
        execution_result = pipeline_result.get("execution_result") or {}
        return (
            "▶️ run result\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- run_attempted: `{pipeline_result.get('run_attempted')}`\n"
            f"- executed: `{execution_result.get('executed')}`\n"
            f"- success: `{execution_result.get('success')}`\n"
            f"- dry_run: `False`\n"
            f"- mode: `real`\n"
            f"- reason: `{execution_result.get('error_reason')}`\n"
            f"- message: `{execution_result.get('output_summary')}`\n"
            f"- execution_status_transition_applied: `{pipeline_result.get('execution_status_transition_applied')}`\n"
            f"- execution_status_transition_reason: `{pipeline_result.get('execution_status_transition_reason')}`"
        )
    if result_type == "run_not_allowed":
        return (
            "⚠️ run not allowed\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- status: `{pipeline_result.get('status')}`\n"
            f"- reason: `{pipeline_result.get('reason')}`"
        )
    if result_type == "report_empty":
        counts = pipeline_result.get("counts") or {}
        return (
            "📊 task report\n"
            "- total: 0\n"
            f"- TODO: {counts.get('TODO', 0)}\n"
            f"- DOING: {counts.get('DOING', 0)}\n"
            f"- BLOCKED: {counts.get('BLOCKED', 0)}\n"
            f"- DONE: {counts.get('DONE', 0)}\n"
            f"- FAILED: {counts.get('FAILED', 0)}\n"
            f"- NEEDS_APPROVAL: {counts.get('NEEDS_APPROVAL', 0)}\n\n"
            "최근 업데이트:\n"
            "(없음)"
        )
    if result_type == "report":
        counts = pipeline_result.get("counts") or {}
        recent = pipeline_result.get("recent") or []
        recent_lines: list[str] = []
        for index, task in enumerate(recent, start=1):
            recent_lines.append(f"{index}. {task.get('id')} — {task.get('title')} — {task.get('status')} — {task.get('updated_at')}")
        recent_text = "\n".join(recent_lines) if recent_lines else "(없음)"
        return (
            "📊 task report\n"
            f"- total: {pipeline_result.get('total', 0)}\n"
            f"- TODO: {counts.get('TODO', 0)}\n"
            f"- DOING: {counts.get('DOING', 0)}\n"
            f"- BLOCKED: {counts.get('BLOCKED', 0)}\n"
            f"- DONE: {counts.get('DONE', 0)}\n"
            f"- FAILED: {counts.get('FAILED', 0)}\n"
            f"- NEEDS_APPROVAL: {counts.get('NEEDS_APPROVAL', 0)}\n\n"
            f"최근 업데이트:\n{recent_text}"
        )
    return f"❌ error: `{pipeline_result.get('reason')}`"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal Discord /plan,/task,/status,/review-task,/report,/retro today,/approve,/run bot"
    )
    parser.add_argument(
        "--env-file",
        default=str(THIS_DIR / ".env"),
        help="Optional .env file path (default: adapters/discord/.env)",
    )
    parser.add_argument(
        "--self-check",
        help="Run local command check without Discord connection. Example: --self-check '/status task-0001-bootstrap'",
    )
    parser.add_argument(
        "--self-check-suite",
        action="store_true",
        help="Run minimal regression self-check suite for approve/status core behavior.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Self-check helpers
# ---------------------------------------------------------------------------
def _run_self_check_suite() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def _record(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    # --- P2-4 Owner authorization boundary -------------------------------
    # These cases need no repo/task fixtures, so they run before the temp repo
    # block. The env var is restored afterwards no matter what happens.
    owner_env_original = os.environ.get(OWNER_IDS_ENV)

    def _set_owner_env(value: str | None) -> None:
        if value is None:
            os.environ.pop(OWNER_IDS_ENV, None)
        else:
            os.environ[OWNER_IDS_ENV] = value

    try:
        owner_id = "111111111111111111"
        other_id = "222222222222222222"
        _set_owner_env(f"  {owner_id} , {other_id} ,, ")

        allowed, reason = _authorize_command("/approve task-0001-self-check approve", owner_id)
        _record("owner_id_allows_privileged", allowed and reason is None, f"reason={reason}")

        denied, reason = _authorize_command("/approve task-0001-self-check approve", "999999999999999999")
        _record(
            "non_owner_denies_privileged",
            (not denied) and reason == "unauthorized",
            f"reason={reason}",
        )

        readonly_results = {
            command: _authorize_command(command, "999999999999999999")
            for command in ("/status task-0001-self-check", "/report", "/report today", "/help", "/plan x", "/review-task task-0001-self-check", "/retro today")
        }
        _record(
            "non_owner_allows_readonly",
            all(ok and why is None for ok, why in readonly_results.values()),
            f"results={ {k: v[0] for k, v in readonly_results.items()} }",
        )

        empty_config_results = {}
        for empty_value in (None, "", "   ", ",,,", "not-a-snowflake"):
            _set_owner_env(empty_value)
            empty_config_results[repr(empty_value)] = {
                command: _authorize_command(command, owner_id)[0]
                for command in ("/approve task-0001-x approve", "/run task-0001-x", "/retry task-0001-x", "/task something")
            }
        _record(
            "empty_owner_config_denies_all",
            all(not allowed for per_value in empty_config_results.values() for allowed in per_value.values()),
            f"results={empty_config_results}",
        )

        _set_owner_env(owner_id)
        exact_cases = {
            "prefix_of_owner": _authorize_command("/approve task-0001-x approve", owner_id[:-1])[0],
            "owner_is_prefix_of": _authorize_command("/approve task-0001-x approve", owner_id + "9")[0],
            "int_instead_of_str": _authorize_command("/approve task-0001-x approve", int(owner_id))[0],  # type: ignore[arg-type]
            "whitespace_padded": _authorize_command("/approve task-0001-x approve", f" {owner_id} ")[0],
            "exact_match": _authorize_command("/approve task-0001-x approve", owner_id)[0],
        }
        _record(
            "owner_id_comparison_is_exact_string",
            exact_cases == {
                "prefix_of_owner": False,
                "owner_is_prefix_of": False,
                "int_instead_of_str": False,
                "whitespace_padded": False,
                "exact_match": True,
            },
            f"cases={exact_cases}",
        )

        token_original = os.environ.get("DISCORD_BOT_TOKEN")
        try:
            os.environ["DISCORD_BOT_TOKEN"] = "self-check-placeholder"
            _set_owner_env(None)
            missing_ok, missing_reason = _validate_required_env()
            _set_owner_env("   ")
            blank_ok, blank_reason = _validate_required_env()
            _set_owner_env(owner_id)
            present_ok, present_reason = _validate_required_env()
        finally:
            if token_original is None:
                os.environ.pop("DISCORD_BOT_TOKEN", None)
            else:
                os.environ["DISCORD_BOT_TOKEN"] = token_original
        _record(
            "missing_owner_env_fails_startup",
            (not missing_ok)
            and missing_reason == f"missing_env:{OWNER_IDS_ENV}"
            and (not blank_ok)
            and blank_reason == f"missing_env:{OWNER_IDS_ENV}"
            and present_ok
            and present_reason is None,
            f"missing={missing_reason} blank={blank_reason} present={present_reason}",
        )

        # The NL branch rewrites `content` into this exact shape before the
        # gate runs (see intent_dispatcher.dispatch's approve_task branch), so
        # gating that string is gating the NL path. This deliberately does not
        # invoke the NL resolver helpers here: orchestrator/discord-nl-intent/
        # run_smoke_tests.py asserts each of them has exactly one call site in
        # this file, and a second one would break that structural contract.
        _set_owner_env(owner_id)
        nl_synthesized = "/approve task-0029-research-council-live-augmentation approve"
        nl_denied, nl_reason = _authorize_command(nl_synthesized, "999999999999999999")
        nl_allowed, _ = _authorize_command(nl_synthesized, owner_id)
        _record(
            "nl_resolved_approve_is_also_gated",
            (not nl_denied) and nl_reason == "unauthorized" and nl_allowed,
            f"reason={nl_reason}",
        )

        run_command_calls = {"n": 0}
        original_run_command = globals()["_run_command"]

        def _counting_run_command(command_text: str) -> dict[str, Any]:
            run_command_calls["n"] += 1
            return original_run_command(command_text)

        globals()["_run_command"] = _counting_run_command
        try:
            # Mirror on_message()'s exact order: authorize, and only call
            # _run_command() when the gate allowed the command.
            for blocked in ("/approve task-0001-x approve", "/run task-0001-x", "/retry task-0001-x", "/task something"):
                gate_ok, _ = _authorize_command(blocked, "999999999999999999")
                if gate_ok:
                    _run_command(blocked)
        finally:
            globals()["_run_command"] = original_run_command
        _record(
            "denied_command_never_reaches_run_command",
            run_command_calls["n"] == 0,
            f"run_command_calls={run_command_calls['n']}",
        )

        privileged_denials = {
            command: _authorize_command(command, "999999999999999999")
            for command in (
                "/approve task-0001-x approve",
                "/run task-0001-x",
                "/retry task-0001-x",
                "/task 새 작업 하나",
            )
        }
        _record(
            "non_owner_denied_for_every_privileged_command",
            all((not ok) and why == "unauthorized" for ok, why in privileged_denials.values()),
            f"results={ {k: v[0] for k, v in privileged_denials.items()} }",
        )

        prefix_bypass = {
            command: _authorize_command(command, "999999999999999999")[0]
            for command in ("/approvex task-0001-x approve", "/taskfoo bar", "/runx task-0001-x", "/retryx task-0001-x")
        }
        _record(
            "privileged_prefix_bypass_is_denied",
            not any(prefix_bypass.values()),
            f"results={prefix_bypass}",
        )
    finally:
        _set_owner_env(owner_env_original)

    # --- P2-5 outbound notification boundary -----------------------------
    # Pure-function checks: no relay, no subprocess, no Discord. The real
    # publisher is stubbed where a failure needs to be observed.
    def _applied_approve_result(transition_to: str = "DOING") -> dict[str, Any]:
        return {
            "result_type": "approve_file_write_result",
            "task_id": "task-0001-self-check",
            "applied": True,
            "error": False,
            "reason": "",
            "applied_transition": {"from": "NEEDS_APPROVAL", "to": transition_to},
            "execution_status_transition_applied": True,
            "execution_status_transition_reason": "",
        }

    approve_payload = _notification_payload_for_result(_applied_approve_result("DOING"))
    reject_payload = _notification_payload_for_result(_applied_approve_result("FAILED"))
    _record(
        "notify_only_on_applied_approve",
        isinstance(approve_payload, dict)
        and approve_payload.get("task_id") == "task-0001-self-check"
        and approve_payload.get("from") == "NEEDS_APPROVAL"
        and approve_payload.get("to") == "DOING"
        and isinstance(reject_payload, dict)
        and reject_payload.get("to") == "FAILED",
        f"approve={approve_payload} reject={reject_payload}",
    )

    not_publishable = {
        "usage_error": _error_payload("usage:/approve <task-id> approve|reject"),
        "hold": _approve_writer_result_fail(task_id="task-0001-x", reason="apply_not_ready", kind="hold"),
        "error": _approve_writer_result_fail(task_id="task-0001-x", reason="task_file_write_failed", kind="error"),
        "applied_false": {**_applied_approve_result(), "applied": False},
        "missing_transition": {k: v for k, v in _applied_approve_result().items() if k != "applied_transition"},
        "blank_transition": {**_applied_approve_result(), "applied_transition": {"from": "", "to": ""}},
    }
    _record(
        "notify_skips_error_hold_and_not_applied",
        all(_notification_payload_for_result(r) is None for r in not_publishable.values()),
        f"results={ {k: _notification_payload_for_result(v) for k, v in not_publishable.items()} }",
    )

    non_approve_results = {
        "run": {"result_type": "run_result", "task_id": "task-0001-x", "run_attempted": True},
        "retry": {"result_type": "retry_result", "task_id": "task-0001-x", "retried": True},
        "task": {"result_type": "success", "task_id": "task-0001-x", "file_name": "task-0001-x.md"},
        "status": {"result_type": "status", "id": "task-0001-x", "status": "DOING"},
        "report": {"result_type": "report", "total": 1},
        "help": {"result_type": "help", "lines": []},
        "not_a_dict": "approve_file_write_result",
    }
    _record(
        "notify_skips_non_approve_results",
        all(_notification_payload_for_result(r) is None for r in non_approve_results.values()),
        f"results={ {k: _notification_payload_for_result(v) for k, v in non_approve_results.items()} }",
    )

    payload_keys = set(approve_payload or {})
    serialized_payload = json.dumps(approve_payload, ensure_ascii=False).lower()
    _record(
        "notify_payload_has_no_p_or_run_tag",
        payload_keys == {"task_id", "from", "to", "execution_status_transition_applied", "ts"}
        and not any(k in payload_keys for k in ("p", "tags", "jarvis_run", "jarvis-run"))
        and "jarvis-run" not in serialized_payload
        and "jarvis_run" not in serialized_payload,
        f"keys={sorted(payload_keys)}",
    )

    _record(
        "notify_payload_carries_transition_not_instruction",
        approve_payload is not None
        and approve_payload.get("from") == "NEEDS_APPROVAL"
        and approve_payload.get("to") in ("DOING", "FAILED")
        and not any(word in serialized_payload for word in ("approve", "reject", "grant", "deny")),
        f"payload={approve_payload}",
    )

    original_publisher = globals()["_run_notification_publisher"]

    def _failing_publisher(_payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "reason": "notification_publish_failed:exit_code:1", "detail": "stub"}

    def _raising_publisher(_payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("stub publisher blew up")

    approve_result_obj = _applied_approve_result()
    before_snapshot = json.dumps(approve_result_obj, sort_keys=True, ensure_ascii=False)
    globals()["_run_notification_publisher"] = _failing_publisher
    try:
        failure_outcome = _publish_approval_notification(approve_result_obj)
        globals()["_run_notification_publisher"] = _raising_publisher
        raised_outcome = _publish_approval_notification(approve_result_obj)
    finally:
        globals()["_run_notification_publisher"] = original_publisher
    after_snapshot = json.dumps(approve_result_obj, sort_keys=True, ensure_ascii=False)

    _record(
        "notify_failure_never_mutates_approve_result",
        before_snapshot == after_snapshot
        and approve_result_obj.get("applied") is True
        and approve_result_obj.get("error") is False
        and "notification" not in after_snapshot.lower(),
        f"mutated={before_snapshot != after_snapshot}",
    )

    _record(
        "notify_failure_is_reported_separately",
        isinstance(failure_outcome, dict)
        and failure_outcome.get("ok") is False
        and str(failure_outcome.get("reason", "")).startswith("notification_publish_failed")
        and isinstance(raised_outcome, dict)
        and raised_outcome.get("ok") is False
        and raised_outcome.get("reason") == "notification_unexpected_error"
        and _publish_approval_notification({"result_type": "status"}) is None,
        f"failure={failure_outcome} raised={raised_outcome}",
    )

    _record(
        "notify_uses_dedicated_constant_not_execution_whitelist",
        NOTIFICATION_PUBLISHER_COMMAND == ("node", "orchestrator/buzz-bridge/publish_notification.js")
        and all(NOTIFICATION_PUBLISHER_COMMAND != command for command in EXECUTION_SCRIPT_WHITELIST.values())
        and not any("publish_notification" in str(command) for command in EXECUTION_SCRIPT_WHITELIST.values())
        and len(EXECUTION_SCRIPT_WHITELIST) == 1
        and ("plan_script_execution", "discord_intake_smoke_tests") in EXECUTION_SCRIPT_WHITELIST,
        f"whitelist={dict(EXECUTION_SCRIPT_WHITELIST)}",
    )

    original_repo_root = REPO_ROOT
    # task-0052. The approval and execution paths now append to the audit chain, and
    # the chain resolves its own location from the environment - so without this the
    # self-check would write test entries into the Owner's real, append-only chain,
    # which cannot be undone. Point it at throwaway state for the duration.
    original_state_dir = os.environ.get("JARVIS_LOCAL_STATE_DIR")
    with tempfile.TemporaryDirectory(prefix="jarvis-self-check-") as temp_dir:
        temp_repo = Path(temp_dir)
        os.environ["JARVIS_LOCAL_STATE_DIR"] = str(temp_repo / "audit-state")
        tasks_dir = temp_repo / "memory" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        def _write_task(
            task_id: str,
            status: str,
            updated_at: str,
            title: str = "self-check",
            summary: str = "self-check summary",
        ) -> Path:
            task_file = tasks_dir / f"{task_id}.md"
            task_file.write_text(
                "\n".join(
                    [
                        f"# {task_id}",
                        "",
                        f"- id: `{task_id}`",
                        f"- title: `{title}`",
                        f"- status: `{status}`",
                        "- repo: `jarvis-core`",
                        "- created_at: `2026-04-01 00:00 UTC`",
                        f"- updated_at: `{updated_at}`",
                        f"- summary: `{summary}`",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            return task_file

        globals()["REPO_ROOT"] = temp_repo
        try:
            transition_ok, transition_reason = _validate_status_transition("NEEDS_APPROVAL", "DOING")
            _record("allowed_transition", transition_ok and transition_reason == "", f"reason={transition_reason}")

            invalid_ok, invalid_reason = _validate_status_transition("DOING", "FAILED")
            _record(
                "invalid_transition",
                (not invalid_ok) and invalid_reason == "invalid_transition",
                f"reason={invalid_reason}",
            )

            old_updated_at = "2026-04-01 00:00 UTC"
            task_id_success = "task-0001-self-check"
            _write_task(task_id_success, "NEEDS_APPROVAL", old_updated_at, title="run demo", summary="self-check summary")
            before_status = _run_status_lookup(f"/status {task_id_success}")
            approve_result = _run_approve_parse(f"/approve {task_id_success} approve")
            after_status = _run_status_lookup(f"/status {task_id_success}")
            status_changed = before_status.get("status") == "NEEDS_APPROVAL" and after_status.get("status") == "DONE"
            updated_at_changed = before_status.get("updated_at") == old_updated_at and after_status.get("updated_at") != old_updated_at
            approve_result_ok = (
                approve_result.get("result_type") == "approve_file_write_result"
                and approve_result.get("applied") is True
                and approve_result.get("error") is False
                and approve_result.get("reason") == ""
            )
            _record("approve_applied_payload", approve_result_ok, f"result={approve_result}")
            execution_status_transition_success_ok = (
                approve_result.get("execution_status_transition_applied") is True
                and approve_result.get("execution_status_transition_reason") == ""
            )
            _record("execution_status_transition_success", execution_status_transition_success_ok, f"result={approve_result}")
            execution_candidate_ok = (
                isinstance(approve_result.get("execution_candidate"), dict)
                and approve_result["execution_candidate"].get("result_type") == "execution_candidate"
                and approve_result["execution_candidate"].get("execution_type") == "script"
                and approve_result["execution_candidate"].get("target") == "discord_intake_smoke_tests"
            )
            _record("execution_candidate_created", execution_candidate_ok, f"result={approve_result}")
            execution_result_script_ok = (
                isinstance(approve_result.get("execution_result_dry_run"), dict)
                and approve_result["execution_result_dry_run"].get("result_type") == "execution_result"
                and approve_result["execution_result_dry_run"].get("execution_type") == "script"
                and approve_result["execution_result_dry_run"].get("executed") is False
                and approve_result["execution_result_dry_run"].get("output_summary") == "dry-run: script execution planned"
            )
            _record("execution_result_dry_run_script", execution_result_script_ok, f"result={approve_result}")
            execution_result_real_whitelist_ok = (
                isinstance(approve_result.get("execution_result"), dict)
                and approve_result["execution_result"].get("result_type") == "execution_result"
                and approve_result["execution_result"].get("execution_type") == "script"
                and approve_result["execution_result"].get("executed") is True
                and approve_result["execution_result"].get("success") is True
            )
            _record("execution_result_real_whitelist_allowed", execution_result_real_whitelist_ok, f"result={approve_result}")
            review_task_after_approve = _run_review_task(f"/review-task {task_id_success}")
            review_execution_metadata_ok = (
                review_task_after_approve.get("result_type") == "review_task_result"
                and review_task_after_approve.get("execution_status") == "success"
                and str(review_task_after_approve.get("execution_summary") or "") != ""
            )
            _record("review_task_execution_metadata_visible", review_execution_metadata_ok, f"result={review_task_after_approve}")
            _record("status_reader_writer_consistency", status_changed, f"before={before_status} after={after_status}")
            _record("updated_at_reader_writer_consistency", updated_at_changed, f"before={before_status} after={after_status}")

            task_id_test_candidate = "task-0004-self-check"
            _write_task(task_id_test_candidate, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="test 검증", summary="테스트 실행")
            test_candidate_result = _run_approve_parse(f"/approve {task_id_test_candidate} approve")
            execution_result_test_ok = (
                isinstance(test_candidate_result.get("execution_result_dry_run"), dict)
                and test_candidate_result["execution_result_dry_run"].get("result_type") == "execution_result"
                and test_candidate_result["execution_result_dry_run"].get("execution_type") == "test"
                and test_candidate_result["execution_result_dry_run"].get("executed") is False
                and test_candidate_result["execution_result_dry_run"].get("output_summary") == "dry-run: test execution planned"
            )
            _record("execution_result_dry_run_test", execution_result_test_ok, f"result={test_candidate_result}")

            task_id_reject = "task-0005-self-check"
            _write_task(task_id_reject, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="run script", summary="승인 후 실행")
            reject_result = _run_approve_parse(f"/approve {task_id_reject} approve")
            execution_result_reject_ok = (
                isinstance(reject_result.get("execution_result"), dict)
                and reject_result["execution_result"].get("result_type") == "execution_result"
                and reject_result["execution_result"].get("executed") is False
                and reject_result["execution_result"].get("success") is False
                and reject_result["execution_result"].get("error_reason") == "script_action_target_not_whitelisted"
            )
            _record("execution_result_real_whitelist_rejected", execution_result_reject_ok, f"result={reject_result}")
            reject_status_after = _run_status_lookup(f"/status {task_id_reject}")
            execution_status_transition_reject_ok = (
                reject_result.get("execution_status_transition_applied") is False
                and reject_result.get("execution_status_transition_reason") == "execution_not_executed"
                and reject_status_after.get("status") == "DOING"
            )
            _record("execution_status_transition_not_executed", execution_status_transition_reject_ok, f"result={reject_result}")

            task_id_fail = "task-0006-self-check"
            _write_task(task_id_fail, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            original_build_execution_result_real = _build_execution_result_real
            try:
                globals()["_build_execution_result_real"] = lambda execution_request: {
                    "result_type": "execution_result",
                    "task_id": str(execution_request.get("task_id") or ""),
                    "execution_type": str(execution_request.get("execution_type") or ""),
                    "action": str(execution_request.get("action") or ""),
                    "executed": True,
                    "success": False,
                    "output_summary": "forced_failure",
                    "error_reason": "execution_failed:exit_code:1",
                }
                fail_result = _run_approve_parse(f"/approve {task_id_fail} approve")
            finally:
                globals()["_build_execution_result_real"] = original_build_execution_result_real
            fail_status_after = _run_status_lookup(f"/status {task_id_fail}")
            execution_status_transition_failure_ok = (
                fail_result.get("result_type") == "approve_file_write_result"
                and fail_result.get("applied") is True
                and fail_result.get("execution_status_transition_applied") is True
                and fail_result.get("execution_status_transition_reason") == ""
                and fail_status_after.get("status") == "FAILED"
            )
            _record("execution_status_transition_failed", execution_status_transition_failure_ok, f"result={fail_result}")

            task_id_transition_fail = "task-0007-self-check"
            _write_task(task_id_transition_fail, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            original_apply_task_status_transition = _apply_task_status_transition
            try:
                def _patched_apply_status_transition(task_id: str, transition_from: str, transition_to: str) -> tuple[bool, str]:
                    if transition_from == "DOING":
                        return False, "write_failed"
                    return original_apply_task_status_transition(task_id, transition_from, transition_to)

                globals()["_apply_task_status_transition"] = _patched_apply_status_transition
                transition_fail_result = _run_approve_parse(f"/approve {task_id_transition_fail} approve")
            finally:
                globals()["_apply_task_status_transition"] = original_apply_task_status_transition
            transition_fail_status_after = _run_status_lookup(f"/status {task_id_transition_fail}")
            execution_status_transition_failure_non_blocking_ok = (
                transition_fail_result.get("result_type") == "approve_file_write_result"
                and transition_fail_result.get("applied") is True
                and transition_fail_result.get("execution_status_transition_applied") is False
                and transition_fail_result.get("execution_status_transition_reason") == "transition_not_applied:write_failed"
                and transition_fail_status_after.get("status") == "DOING"
            )
            _record(
                "execution_status_transition_failure_non_blocking",
                execution_status_transition_failure_non_blocking_ok,
                f"result={transition_fail_result}",
            )

            task_id_mismatch = "task-0002-self-check"
            _write_task(task_id_mismatch, "DOING", "2026-04-01 00:00 UTC")
            mismatch_result = _run_approve_parse(f"/approve {task_id_mismatch} approve")
            mismatch_ok = (
                mismatch_result.get("result_type") == "approve_file_write_result"
                and mismatch_result.get("applied") is False
                and mismatch_result.get("error") is False
                and mismatch_result.get("reason") == "status_mismatch"
            )
            _record("status_mismatch", mismatch_ok, f"result={mismatch_result}")

            not_found_result = _run_approve_parse("/approve task-9999-self-check approve")
            not_found_ok = (
                not_found_result.get("result_type") == "approve_file_write_result"
                and not_found_result.get("applied") is False
                and not_found_result.get("error") is False
                and not_found_result.get("reason") == "task_not_found"
            )
            _record("task_not_found", not_found_ok, f"result={not_found_result}")

            task_id_no_candidate = "task-0003-self-check"
            _write_task(task_id_no_candidate, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="문서 정리", summary="범위 확인")
            no_candidate_result = _run_approve_parse(f"/approve {task_id_no_candidate} approve")
            no_candidate_ok = (
                no_candidate_result.get("result_type") == "approve_file_write_result"
                and no_candidate_result.get("applied") is True
                and no_candidate_result.get("execution_candidate") is None
                and no_candidate_result.get("execution_result_dry_run") is None
                and no_candidate_result.get("execution_result") is None
            )
            _record("execution_candidate_not_created", no_candidate_ok, f"result={no_candidate_result}")

            status_usage_error = _run_status_lookup("/status")
            status_usage_error_ok = (
                status_usage_error.get("result_type") == "error"
                and status_usage_error.get("reason") == "usage:/status <task-id>"
            )
            _record("status_usage_error", status_usage_error_ok, f"result={status_usage_error}")

            status_not_found = _run_status_lookup("/status task-9998-self-check")
            status_not_found_ok = status_not_found.get("result_type") == "not_found"
            _record("status_not_found", status_not_found_ok, f"result={status_not_found}")

            status_execution_visible = _run_status_lookup(f"/status {task_id_success}")
            status_execution_visible_ok = (
                status_execution_visible.get("result_type") == "status"
                and status_execution_visible.get("id") == task_id_success
                and status_execution_visible.get("execution_status") == "success"
                and str(status_execution_visible.get("execution_summary") or "") != ""
            )
            _record("status_execution_metadata_visible", status_execution_visible_ok, f"result={status_execution_visible}")

            status_dry_run_only = _run_status_lookup(f"/status {task_id_reject}")
            status_dry_run_only_ok = (
                status_dry_run_only.get("result_type") == "status"
                and status_dry_run_only.get("id") == task_id_reject
                and status_dry_run_only.get("execution_status") == "not_executed"
            )
            _record("status_dry_run_only_safe", status_dry_run_only_ok, f"result={status_dry_run_only}")

            retry_usage_error = _run_retry("/retry")
            retry_usage_error_ok = (
                retry_usage_error.get("result_type") == "error"
                and retry_usage_error.get("reason") == "usage:/retry <task-id>"
            )
            _record("retry_usage_error", retry_usage_error_ok, f"result={retry_usage_error}")

            retry_not_found = _run_retry("/retry task-9997-self-check")
            retry_not_found_ok = retry_not_found.get("result_type") == "not_found"
            _record("retry_not_found", retry_not_found_ok, f"result={retry_not_found}")

            task_id_retry_not_allowed = "task-0008-self-check"
            _write_task(task_id_retry_not_allowed, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            retry_not_allowed_result = _run_retry(f"/retry {task_id_retry_not_allowed}")
            retry_not_allowed_ok = (
                retry_not_allowed_result.get("result_type") == "retry_not_allowed"
                and retry_not_allowed_result.get("status") == "NEEDS_APPROVAL"
            )
            _record("retry_not_allowed_status", retry_not_allowed_ok, f"result={retry_not_allowed_result}")

            task_id_retry_success = "task-0009-self-check"
            _write_task(task_id_retry_success, "FAILED", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            retry_success_result = _run_retry(f"/retry {task_id_retry_success}")
            retry_success_status = _run_status_lookup(f"/status {task_id_retry_success}")
            retry_success_ok = (
                retry_success_result.get("result_type") == "retry_result"
                and retry_success_result.get("execution_status_transition_applied") is True
                and retry_success_result.get("execution_status_transition_reason") == ""
                and retry_success_status.get("status") == "DONE"
            )
            _record("retry_failed_to_done_on_success", retry_success_ok, f"result={retry_success_result} status={retry_success_status}")
            retry_success_metadata_ok = (
                retry_success_status.get("execution_status") == "success"
                and retry_success_status.get("executed") == "true"
                and retry_success_status.get("success") == "true"
                and retry_success_status.get("dry_run") == "false"
                and retry_success_status.get("mode") == "real"
                and '"source":"retry"' in str(retry_success_status.get("execution_request") or "")
                and str(retry_success_status.get("execution_result") or "") != ""
                and str(retry_success_status.get("execution_summary") or "") != ""
            )
            _record("retry_execution_metadata_persisted", retry_success_metadata_ok, f"status={retry_success_status}")

            task_id_retry_fail = "task-0010-self-check"
            _write_task(task_id_retry_fail, "DOING", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            original_build_execution_result_real = _build_execution_result_real
            try:
                globals()["_build_execution_result_real"] = lambda execution_request: {
                    "result_type": "execution_result",
                    "task_id": str(execution_request.get("task_id") or ""),
                    "execution_type": str(execution_request.get("execution_type") or ""),
                    "action": str(execution_request.get("action") or ""),
                    "executed": True,
                    "success": False,
                    "output_summary": "forced_retry_failure",
                    "error_reason": "execution_failed:exit_code:1",
                }
                retry_fail_result = _run_retry(f"/retry {task_id_retry_fail}")
            finally:
                globals()["_build_execution_result_real"] = original_build_execution_result_real
            retry_fail_status = _run_status_lookup(f"/status {task_id_retry_fail}")
            retry_fail_ok = (
                retry_fail_result.get("result_type") == "retry_result"
                and retry_fail_result.get("execution_status_transition_applied") is True
                and retry_fail_status.get("status") == "FAILED"
            )
            _record("retry_failed_on_execution_failure", retry_fail_ok, f"result={retry_fail_result} status={retry_fail_status}")

            task_id_retry_not_executed = "task-0011-self-check"
            _write_task(task_id_retry_not_executed, "DOING", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            original_build_execution_result_real = _build_execution_result_real
            try:
                globals()["_build_execution_result_real"] = lambda execution_request: {
                    "result_type": "execution_result",
                    "task_id": str(execution_request.get("task_id") or ""),
                    "execution_type": str(execution_request.get("execution_type") or ""),
                    "action": str(execution_request.get("action") or ""),
                    "executed": False,
                    "success": False,
                    "output_summary": "",
                    "error_reason": "script_action_target_not_whitelisted",
                }
                retry_not_executed_result = _run_retry(f"/retry {task_id_retry_not_executed}")
            finally:
                globals()["_build_execution_result_real"] = original_build_execution_result_real
            retry_not_executed_status = _run_status_lookup(f"/status {task_id_retry_not_executed}")
            retry_not_executed_ok = (
                retry_not_executed_result.get("result_type") == "retry_result"
                and retry_not_executed_result.get("execution_status_transition_applied") is False
                and retry_not_executed_result.get("execution_status_transition_reason") == "execution_not_executed"
                and retry_not_executed_status.get("status") == "DOING"
            )
            _record(
                "retry_status_unchanged_when_not_executed",
                retry_not_executed_ok,
                f"result={retry_not_executed_result} status={retry_not_executed_status}",
            )

            run_usage_error = _run_run("/run")
            run_usage_error_ok = (
                run_usage_error.get("result_type") == "error"
                and run_usage_error.get("reason") == "usage:/run <task-id>"
            )
            _record("run_usage_error", run_usage_error_ok, f"result={run_usage_error}")

            run_not_found = _run_run("/run task-9996-self-check")
            run_not_found_ok = run_not_found.get("result_type") == "not_found"
            _record("run_not_found", run_not_found_ok, f"result={run_not_found}")

            task_id_run_not_allowed = "task-0012-self-check"
            _write_task(task_id_run_not_allowed, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            run_not_allowed_result = _run_run(f"/run {task_id_run_not_allowed}")
            run_not_allowed_ok = (
                run_not_allowed_result.get("result_type") == "run_not_allowed"
                and run_not_allowed_result.get("status") == "NEEDS_APPROVAL"
            )
            _record("run_not_allowed_status", run_not_allowed_ok, f"result={run_not_allowed_result}")

            task_id_run_success = "task-0013-self-check"
            _write_task(task_id_run_success, "DOING", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            run_success_result = _run_run(f"/run {task_id_run_success}")
            run_success_status = _run_status_lookup(f"/status {task_id_run_success}")
            run_success_ok = (
                run_success_result.get("result_type") == "run_result"
                and run_success_result.get("execution_status_transition_applied") is True
                and run_success_result.get("execution_status_transition_reason") == ""
                and run_success_status.get("status") == "DONE"
            )
            _record("run_doing_to_done_on_success", run_success_ok, f"result={run_success_result} status={run_success_status}")
            run_success_metadata_ok = (
                run_success_status.get("execution_status") == "success"
                and run_success_status.get("executed") == "true"
                and run_success_status.get("success") == "true"
                and run_success_status.get("dry_run") == "false"
                and run_success_status.get("mode") == "real"
                and '"source":"run"' in str(run_success_status.get("execution_request") or "")
                and str(run_success_status.get("execution_candidate") or "") != ""
                and str(run_success_status.get("execution_result") or "") != ""
                and str(run_success_status.get("execution_summary") or "") != ""
            )
            _record("run_execution_metadata_persisted", run_success_metadata_ok, f"status={run_success_status}")

            task_id_run_fail = "task-0014-self-check"
            _write_task(task_id_run_fail, "DOING", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            original_build_execution_result_real = _build_execution_result_real
            try:
                globals()["_build_execution_result_real"] = lambda execution_request: {
                    "result_type": "execution_result",
                    "task_id": str(execution_request.get("task_id") or ""),
                    "execution_type": str(execution_request.get("execution_type") or ""),
                    "action": str(execution_request.get("action") or ""),
                    "executed": True,
                    "success": False,
                    "output_summary": "forced_run_failure",
                    "error_reason": "execution_failed:exit_code:1",
                }
                run_fail_result = _run_run(f"/run {task_id_run_fail}")
            finally:
                globals()["_build_execution_result_real"] = original_build_execution_result_real
            run_fail_status = _run_status_lookup(f"/status {task_id_run_fail}")
            run_fail_ok = (
                run_fail_result.get("result_type") == "run_result"
                and run_fail_result.get("execution_status_transition_applied") is True
                and run_fail_status.get("status") == "FAILED"
            )
            _record("run_doing_to_failed_on_execution_failure", run_fail_ok, f"result={run_fail_result} status={run_fail_status}")
            status_execution_error_reply = _format_reply(run_fail_status)
            status_execution_error_visible_ok = (
                run_fail_status.get("execution_status") == "failed"
                and run_fail_status.get("error") == "execution_failed:exit_code:1"
                and run_fail_status.get("message") == "forced_run_failure"
                and "- error: `execution_failed:exit_code:1`" in status_execution_error_reply
                and "- message: `forced_run_failure`" in status_execution_error_reply
            )
            _record(
                "status_execution_error_metadata_visible",
                status_execution_error_visible_ok,
                f"status={run_fail_status} reply={status_execution_error_reply}",
            )

            task_id_run_not_executed = "task-0015-self-check"
            _write_task(task_id_run_not_executed, "DOING", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            original_build_execution_result_real = _build_execution_result_real
            try:
                globals()["_build_execution_result_real"] = lambda execution_request: {
                    "result_type": "execution_result",
                    "task_id": str(execution_request.get("task_id") or ""),
                    "execution_type": str(execution_request.get("execution_type") or ""),
                    "action": str(execution_request.get("action") or ""),
                    "executed": False,
                    "success": False,
                    "output_summary": "",
                    "error_reason": "script_action_target_not_whitelisted",
                }
                run_not_executed_result = _run_run(f"/run {task_id_run_not_executed}")
            finally:
                globals()["_build_execution_result_real"] = original_build_execution_result_real
            run_not_executed_status = _run_status_lookup(f"/status {task_id_run_not_executed}")
            run_not_executed_ok = (
                run_not_executed_result.get("result_type") == "run_result"
                and run_not_executed_result.get("execution_status_transition_applied") is False
                and run_not_executed_result.get("execution_status_transition_reason") == "execution_not_executed"
                and run_not_executed_status.get("status") == "DOING"
            )
            _record(
                "run_status_unchanged_when_not_executed",
                run_not_executed_ok,
                f"result={run_not_executed_result} status={run_not_executed_status}",
            )

            help_result = _run_help("/help")
            help_ok = (
                help_result.get("result_type") == "help"
                and any(str(line).startswith("/approve <task-id> approve|reject - 승인/반려") for line in (help_result.get("lines") or []))
                and any(str(line).startswith("/run <task-id> - DOING task 실행") for line in (help_result.get("lines") or []))
                and any(str(line).startswith("/retry <task-id> - FAILED/DOING task 재실행") for line in (help_result.get("lines") or []))
                and any(str(line).startswith("/status <task-id> - 단건 상태 확인") for line in (help_result.get("lines") or []))
            )
            _record("help_command", help_ok, f"result={help_result}")

            help_usage_error = _run_help("/help extra")
            help_usage_error_ok = (
                help_usage_error.get("result_type") == "error"
                and help_usage_error.get("reason") == "usage:/help"
            )
            _record("help_usage_error", help_usage_error_ok, f"result={help_usage_error}")

            today_ymd = datetime.now(UTC).strftime("%Y-%m-%d")
            _write_task("task-0101-retro-done", "DONE", f"{today_ymd} 10:00 UTC", title="retro done item")
            _write_task("task-0102-retro-blocked", "BLOCKED", f"{today_ymd} 11:00 UTC", title="retro blocked item")
            retro_today_result = _run_retro_today("/retro today")
            retro_today_ok = (
                retro_today_result.get("result_type") == "retro_today"
                and int(retro_today_result.get("total") or 0) >= 2
                and int((retro_today_result.get("counts") or {}).get("DONE") or 0) >= 1
                and int((retro_today_result.get("counts") or {}).get("BLOCKED") or 0) >= 1
                and "retro done item" in (retro_today_result.get("completed_titles") or [])
                and "retro blocked item" in (retro_today_result.get("follow_up_titles") or [])
            )
            _record("retro_today_command", retro_today_ok, f"result={retro_today_result}")

            retro_usage_error = _run_retro_today("/retro")
            retro_usage_error_ok = (
                retro_usage_error.get("result_type") == "error"
                and retro_usage_error.get("reason") == "usage:/retro today"
            )
            _record("retro_usage_error", retro_usage_error_ok, f"result={retro_usage_error}")

            retro_usage_extra_error = _run_retro_today("/retro today extra")
            retro_usage_extra_error_ok = (
                retro_usage_extra_error.get("result_type") == "error"
                and retro_usage_extra_error.get("reason") == "usage:/retro today"
            )
            _record("retro_usage_extra_error", retro_usage_extra_error_ok, f"result={retro_usage_extra_error}")

            status_invalid_task_id = _run_status_lookup("/status task-0002")
            status_invalid_task_id_ok = (
                status_invalid_task_id.get("result_type") == "error"
                and status_invalid_task_id.get("reason") == "invalid_task_id_format"
            )
            _record("status_invalid_task_id_format", status_invalid_task_id_ok, f"result={status_invalid_task_id}")

            report_today_extra_error = _run_command("/report today extra")
            report_today_extra_error_ok = (
                report_today_extra_error.get("result_type") == "error"
                and report_today_extra_error.get("reason") == "usage:/report today"
            )
            _record("report_today_extra_usage", report_today_extra_error_ok, f"result={report_today_extra_error}")

            _write_task("task-0110-report-visible", "DONE", "2099-01-01 00:00 UTC", title="report visible item")
            report_result = _run_command("/report")
            report_reply = _format_reply(report_result)
            report_recent_title_visible_ok = (
                report_result.get("result_type") == "report"
                and "task-0110-report-visible" in report_reply
                and "report visible item" in report_reply
            )
            _record("report_recent_title_visible", report_recent_title_visible_ok, f"reply={report_reply}")

            # --- task-0052 audit chain integration -----------------------------
            # The chain is isolated to throwaway state for this whole block, so
            # these append to a temp chain and never touch the Owner's real one.
            audit_paths = resolve_audit_chain_paths()

            def _chain_entries() -> list[dict[str, Any]]:
                if not audit_paths.chain_file.exists():
                    return []
                return [
                    json.loads(line)
                    for line in audit_paths.chain_file.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]

            task_id_audit = "task-0020-self-check"
            _write_task(task_id_audit, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            audit_before = len(_chain_entries())
            audit_approve = _run_approve_parse(f"/approve {task_id_audit} approve")
            audit_entries = _chain_entries()
            approval_entry = next(
                (e for e in audit_entries if e["kind"] == "owner_approval" and e["task_id"] == task_id_audit),
                None,
            )
            execution_entry = next(
                (e for e in audit_entries if e["kind"] == "execution_result" and e["task_id"] == task_id_audit),
                None,
            )
            _record(
                "audit_owner_approval_recorded",
                approval_entry is not None
                and approval_entry["payload"]["decision"] == "approve"
                and approval_entry["payload"]["applied"] is True
                and audit_approve.get("audit_error") is None,
                f"entry={approval_entry} audit_error={audit_approve.get('audit_error')}",
            )
            _record(
                "audit_execution_result_recorded",
                execution_entry is not None and execution_entry["payload"]["source"] == "approve_file_write_result",
                f"entry={execution_entry}",
            )
            # The approval pipeline stays unaware of identity (P2-4) and the schema
            # refuses it outright - assert the recorded payload really has none.
            _record(
                "audit_payload_has_no_owner_identity",
                approval_entry is not None
                and not ({"user_id", "author_id", "discord_user_id", "owner_id"} & set(approval_entry["payload"])),
                f"payload_keys={sorted(approval_entry['payload']) if approval_entry else None}",
            )
            chain_state = verify_audit_chain(audit_paths.chain_file)
            _record(
                "audit_chain_verifies_after_approval",
                chain_state.get("valid") is True and chain_state.get("length", 0) > audit_before,
                f"chain={chain_state}",
            )

            # --- decision 5-b: a rejection must not reach the execution flow ----
            task_id_no_exec = "task-0021-self-check"
            _write_task(task_id_no_exec, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="run demo", summary="self-check summary")
            reject_exec = _run_approve_parse(f"/approve {task_id_no_exec} reject")
            reject_status = _run_status_lookup(f"/status {task_id_no_exec}")
            reject_entries = [e for e in _chain_entries() if e["task_id"] == task_id_no_exec]
            _record(
                "reject_skips_execution_flow",
                reject_exec.get("applied") is True
                and reject_exec.get("execution_result") is None
                and reject_exec.get("execution_candidate") is None
                and reject_exec.get("execution_status_transition_reason") == "execution_skipped_on_reject"
                and reject_status.get("status") == "FAILED",
                f"result={reject_exec} status={reject_status}",
            )
            # The title matches the whitelisted target, so before this fix the
            # rejection ran the subprocess and left execution metadata behind.
            _record(
                "reject_leaves_no_execution_metadata",
                str(reject_status.get("execution_status") or "") == ""
                and str(reject_status.get("execution_result") or "") == "",
                f"status={reject_status}",
            )
            _record(
                "reject_records_no_execution_audit_entry",
                len(reject_entries) == 1 and reject_entries[0]["kind"] == "owner_approval",
                f"entries={[e['kind'] for e in reject_entries]}",
            )

            # --- decision 1: an append failure fails the approval, without rollback
            task_id_audit_fail = "task-0022-self-check"
            _write_task(task_id_audit_fail, "NEEDS_APPROVAL", "2026-04-01 00:00 UTC", title="plain task", summary="self-check summary")
            original_record_owner_approval = globals()["record_owner_approval"]

            def _failing_record(**_fields: Any) -> None:
                raise AuditChainError("audit_store_lock_timeout", detail="C:/secret/path/chain.jsonl")

            globals()["record_owner_approval"] = _failing_record
            try:
                audit_fail_result = _run_approve_parse(f"/approve {task_id_audit_fail} approve")
            finally:
                globals()["record_owner_approval"] = original_record_owner_approval
            audit_fail_status = _run_status_lookup(f"/status {task_id_audit_fail}")
            _record(
                "audit_failure_refuses_approval",
                audit_fail_result.get("applied") is False
                and audit_fail_result.get("error") is True
                and audit_fail_result.get("reason") == "audit_store_lock_timeout"
                and audit_fail_result.get("transition_applied_without_audit") is True,
                f"result={audit_fail_result}",
            )
            # Decision 1 (ii-b): the transition is NOT rolled back, and the task is
            # left visibly stuck rather than quietly reported as fine.
            _record(
                "audit_failure_does_not_roll_back",
                audit_fail_status.get("status") == "DOING",
                f"status={audit_fail_status}",
            )
            # Decision 7: the reply carries the stable code only - the detail that
            # accompanied the error (a path, here) must not travel with it.
            _record(
                "audit_failure_reason_carries_no_detail",
                ":" not in str(audit_fail_result.get("reason") or "")
                and "secret" not in str(audit_fail_result.get("reason") or ""),
                f"reason={audit_fail_result.get('reason')}",
            )
            # And the stuck task cannot be silently retried into a second execution.
            audit_retry_result = _run_approve_parse(f"/approve {task_id_audit_fail} approve")
            _record(
                "audit_failure_retry_blocked",
                audit_retry_result.get("applied") is False
                and audit_retry_result.get("reason") == "status_mismatch",
                f"result={audit_retry_result}",
            )

            # --- decision 3: refused attempts are recorded too -------------------
            missing_before = len([e for e in _chain_entries() if e["task_id"] == "task-0023-self-check"])
            missing_result = _run_approve_parse("/approve task-0023-self-check approve")
            missing_entries = [e for e in _chain_entries() if e["task_id"] == "task-0023-self-check"]
            _record(
                "failed_approval_attempt_recorded",
                missing_before == 0
                and missing_result.get("applied") is False
                and len(missing_entries) == 1
                and missing_entries[0]["payload"]["applied"] is False
                and missing_entries[0]["payload"]["reason"] == "task_not_found",
                f"result={missing_result} entries={missing_entries}",
            )

            # --- decision 2: approval transitions go through the durable writer --
            _record(
                "approval_transition_is_durable",
                DURABLE_STATUS_TRANSITIONS == frozenset(
                    {("NEEDS_APPROVAL", "DOING"), ("NEEDS_APPROVAL", "FAILED")}
                )
                and DURABLE_STATUS_TRANSITIONS.issubset(TASK_STATUS_TRANSITIONS),
                f"durable={sorted(DURABLE_STATUS_TRANSITIONS)}",
            )
            # The drift between the two modules' transition tables is what hid the
            # missing FAILED->TODO pair, so assert the guard actually catches it.
            original_writer_transitions = globals()["TASK_STATUS_TRANSITIONS"]
            globals()["TASK_STATUS_TRANSITIONS"] = frozenset({("TODO", "DOING")})
            try:
                drift_ok, drift_reasons = _validate_approve_transition_contract_sync()
            finally:
                globals()["TASK_STATUS_TRANSITIONS"] = original_writer_transitions
            _record(
                "writer_transition_drift_detected",
                drift_ok is False and "approve_contract_writer_transition_missing" in drift_reasons,
                f"reasons={drift_reasons}",
            )
        finally:
            globals()["REPO_ROOT"] = original_repo_root
            if original_state_dir is None:
                os.environ.pop("JARVIS_LOCAL_STATE_DIR", None)
            else:
                os.environ["JARVIS_LOCAL_STATE_DIR"] = original_state_dir

    failed = [check for check in checks if not check["ok"]]
    if failed:
        return {"result_type": "self_check_suite", "ok": False, "total": len(checks), "failed": failed, "checks": checks}
    return {"result_type": "self_check_suite", "ok": True, "total": len(checks), "checks": checks}


def _validate_required_env() -> tuple[bool, str | None]:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        return False, "missing_env:DISCORD_BOT_TOKEN"
    # Refuse to start rather than run with no approval boundary. Only the env
    # var NAME appears in the reason - never any configured id.
    if not _load_owner_ids():
        return False, f"missing_env:{OWNER_IDS_ENV}"
    return True, None


# ---------------------------------------------------------------------------
# Discord runtime / CLI entrypoint
# ---------------------------------------------------------------------------
async def _start_discord_bot() -> None:
    if discord is None:
        raise RuntimeError("missing_dependency:discord.py")

    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        print(f"[discord] connected as {client.user}")

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

        content = (message.content or "").strip()
        if not content.startswith("/"):
            resolved_command = resolve_intent(content)
            if resolved_command is None:
                fallback_outcome = resolve_llm_fallback(content)
                if fallback_outcome.command is not None:
                    resolved_command = fallback_outcome.command
                elif fallback_outcome.reply is not None:
                    await message.reply(fallback_outcome.reply)
                    return
                else:
                    return
            content = resolved_command

        if (
            not content.startswith("/help")
            and not content.startswith("/plan")
            and not content.startswith("/task")
            and not content.startswith("/status")
            and not content.startswith("/retry")
            and not content.startswith("/run")
            and not content.startswith("/review-task")
            and not content.startswith("/retro")
            and not content.startswith("/report")
            and not content.startswith("/approve")
        ):
            await message.reply(
                "이 봇은 현재 `/help`, `/plan <request>`, `/task <내용>`, `/status <task-id>`, `/retry <task-id>`, `/run <task-id>`, `/review-task <task-id>`, `/report`, `/report today`, `/retro today`, `/approve <task-id> approve|reject`만 지원합니다."
            )
            return

        # Single authorization gate for the whole adapter. It sits here, after
        # the natural-language branch has already rewritten `content` into a
        # concrete command, so an NL-synthesized "/approve ..." is gated by the
        # exact same check as a typed one.
        authorized, denial_reason = _authorize_command(content, str(message.author.id))
        if not authorized:
            await message.reply(_format_reply(_error_payload(denial_reason or "unauthorized")))
            return

        result = _run_command(content)
        # The approval result is authoritative and reaches the Owner FIRST.
        # Nothing below can change it, delay it, or make it look failed.
        await message.reply(_format_reply(result))

        # Best-effort outbound notification. Runs off the event loop so a
        # slow relay cannot stall this handler, and its outcome is reported
        # separately - never folded back into `result`.
        publication = await asyncio.to_thread(_publish_approval_notification, result)
        if publication is not None and not publication.get("ok"):
            print(f"[notify] task-status notification failed: {publication.get('reason')} {publication.get('detail', '')}")
            await message.reply(
                "ℹ️ 승인 처리는 정상 완료되었습니다. 위 결과가 확정된 상태입니다.\n"
                f"다만 Buzz 알림 발행에는 실패했습니다 (`{publication.get('reason')}`). 승인 결과에는 영향이 없습니다."
            )

    token = os.environ["DISCORD_BOT_TOKEN"].strip()
    try:
        await client.start(token)
    except Exception as exc:  # noqa: BLE001 - entrypoint level reporting only
        raise RuntimeError(f"discord_connection_failed:{exc}") from exc


def main() -> None:
    args = _parse_args()
    _load_env_file(Path(args.env_file))

    if args.self_check_suite:
        print(json.dumps(_run_self_check_suite(), ensure_ascii=False, indent=2))
        return

    if args.self_check:
        command_text = args.self_check.strip()
        if not command_text:
            print(json.dumps(_error_payload("empty_input"), ensure_ascii=False))
            raise SystemExit(2)
        print(json.dumps(_run_command(command_text), ensure_ascii=False, indent=2))
        return

    is_valid, reason = _validate_required_env()
    if not is_valid:
        print(json.dumps(_error_payload(str(reason)), ensure_ascii=False))
        raise SystemExit(2)

    try:
        asyncio.run(_start_discord_bot())
    except RuntimeError as exc:
        print(json.dumps(_error_payload(str(exc)), ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
