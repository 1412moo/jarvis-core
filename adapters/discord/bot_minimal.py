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
from datetime import datetime
import json
import os
import re
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
INTAKE_DIR = REPO_ROOT / "orchestrator" / "discord-intake"
if str(INTAKE_DIR) not in sys.path:
    sys.path.insert(0, str(INTAKE_DIR))

from intake_parser import parse_intake
from task_draft_builder import build_task_draft
from task_file_writer import write_task_file

TASK_ID_PATTERN = re.compile(r"^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
TASK_META_LINE_PATTERN = re.compile(r"^- ([a-z_]+): `(.*)`$")
TASK_STATUS_REQUIRED_FIELDS = ("id", "title", "status", "updated_at", "summary")
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
# Task intake + status/report metadata helpers
# ---------------------------------------------------------------------------
def _run_task_pipeline(command_text: str) -> dict[str, Any]:
    parser_result = parse_intake(command_text).to_dict()
    if parser_result.get("error_reason"):
        return _error_payload(str(parser_result.get("error_reason")))

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

    task_id = parts[1].strip()
    if not task_id:
        return _error_payload("empty_task_id")
    if not TASK_ID_PATTERN.fullmatch(task_id):
        return _error_payload("invalid_task_id_format")

    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return {"result_type": "not_found", "task_id": task_id}

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
        return _error_payload(f"task_file_missing_fields:{','.join(missing_fields)}")

    return {"result_type": "status", **metadata}


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
    today_ymd = datetime.utcnow().strftime("%Y-%m-%d")
    parsed_tasks: list[dict[str, str]] = []
    for task_file in sorted(tasks_dir.glob("*.md")):
        metadata = _read_task_metadata(task_file)
        if metadata is None:
            continue
        updated_date = metadata["updated_at"].split(" ", 1)[0]
        if updated_date == today_ymd:
            parsed_tasks.append(metadata)

    return _build_report_payload(parsed_tasks)


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

    return not reasons, reasons


def _apply_task_status_transition(task_id: str, transition_from: str, transition_to: str) -> tuple[bool, str]:
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
        lines[updated_line_index] = f"- updated_at: `{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}`"

    new_text = "\n".join(lines)
    if has_trailing_newline:
        new_text += "\n"
    try:
        task_file.write_text(new_text, encoding="utf-8")
    except OSError:
        return False, "write_failed"
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

    if not apply_ready:
        return _approve_writer_result_fail(task_id=task_id, reason="apply_not_ready", kind="hold")

    applied, reason = _apply_task_status_transition(task_id, transition_from, transition_to)
    if not applied:
        reason_kind = "hold" if reason in ("task_not_found", "status_mismatch") else "error"
        return _approve_writer_result_fail(task_id=task_id, reason=reason, kind=reason_kind)

    return {
        "result_type": "approve_file_write_result",
        "task_id": task_id,
        "applied": True,
        "error": False,
        "reason": "",
        "applied_transition": {"from": transition_from, "to": transition_to},
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

    parse_result = {"result_type": "approve_parse", "task_id": task_id, "decision": decision}
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
    if content.startswith("/task"):
        return _run_task_pipeline(content)
    if content.startswith("/status"):
        return _run_status_lookup(content)
    if content.startswith("/approve"):
        return _run_approve_parse(content)
    if content == "/report today":
        return _run_report_today(content)
    if content.startswith("/report"):
        return _run_report(content)
    return _error_payload("unsupported_command")


def _format_reply(pipeline_result: dict[str, Any]) -> str:
    result_type = pipeline_result.get("result_type")
    if result_type == "success":
        return (
            "✅ task 생성 완료\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- file: `{pipeline_result.get('file_name')}`"
        )
    if result_type == "hold":
        return f"⏸️ hold\n- reason: `{pipeline_result.get('reason')}`"
    if result_type == "status":
        return (
            "📄 task 정보\n"
            f"- id: `{pipeline_result.get('id')}`\n"
            f"- title: `{pipeline_result.get('title')}`\n"
            f"- status: `{pipeline_result.get('status')}`\n"
            f"- updated_at: `{pipeline_result.get('updated_at')}`\n"
            f"- summary: `{pipeline_result.get('summary')}`"
        )
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
        applied_transition = pipeline_result.get("applied_transition") or {}
        return (
            "🧾 approve file write result 생성 완료\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- applied: `{pipeline_result.get('applied')}`\n"
            f"- applied_transition: `{applied_transition.get('from')} -> {applied_transition.get('to')}`\n"
            f"- kind: `{pipeline_result.get('kind')}`\n"
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
            recent_lines.append(f"{index}. {task.get('id')} — {task.get('status')} — {task.get('updated_at')}")
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
    parser = argparse.ArgumentParser(description="Minimal Discord /task,/status,/report,/approve bot")
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

    original_repo_root = REPO_ROOT
    with tempfile.TemporaryDirectory(prefix="jarvis-self-check-") as temp_dir:
        temp_repo = Path(temp_dir)
        tasks_dir = temp_repo / "memory" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        def _write_task(task_id: str, status: str, updated_at: str) -> Path:
            task_file = tasks_dir / f"{task_id}.md"
            task_file.write_text(
                "\n".join(
                    [
                        f"# {task_id}",
                        "",
                        f"- id: `{task_id}`",
                        "- title: `self-check`",
                        f"- status: `{status}`",
                        "- repo: `jarvis-core`",
                        "- created_at: `2026-04-01 00:00 UTC`",
                        f"- updated_at: `{updated_at}`",
                        "- summary: `self-check summary`",
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
            _write_task(task_id_success, "NEEDS_APPROVAL", old_updated_at)
            before_status = _run_status_lookup(f"/status {task_id_success}")
            approve_result = _run_approve_parse(f"/approve {task_id_success} approve")
            after_status = _run_status_lookup(f"/status {task_id_success}")
            status_changed = before_status.get("status") == "NEEDS_APPROVAL" and after_status.get("status") == "DOING"
            updated_at_changed = before_status.get("updated_at") == old_updated_at and after_status.get("updated_at") != old_updated_at
            approve_result_ok = (
                approve_result.get("result_type") == "approve_file_write_result"
                and approve_result.get("applied") is True
                and approve_result.get("error") is False
                and approve_result.get("reason") == ""
            )
            _record("approve_applied_payload", approve_result_ok, f"result={approve_result}")
            _record("status_reader_writer_consistency", status_changed, f"before={before_status} after={after_status}")
            _record("updated_at_reader_writer_consistency", updated_at_changed, f"before={before_status} after={after_status}")

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
        finally:
            globals()["REPO_ROOT"] = original_repo_root

    failed = [check for check in checks if not check["ok"]]
    if failed:
        return {"result_type": "self_check_suite", "ok": False, "total": len(checks), "failed": failed, "checks": checks}
    return {"result_type": "self_check_suite", "ok": True, "total": len(checks), "checks": checks}


def _validate_required_env() -> tuple[bool, str | None]:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        return False, "missing_env:DISCORD_BOT_TOKEN"
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
            return

        if not content.startswith("/task") and not content.startswith("/status") and not content.startswith("/report") and not content.startswith("/approve"):
            await message.reply(
                "이 봇은 현재 `/task <내용>`, `/status <task-id>`, `/report`, `/report today`, `/approve <task-id> approve|reject`만 지원합니다."
            )
            return

        result = _run_command(content)
        await message.reply(_format_reply(result))

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
