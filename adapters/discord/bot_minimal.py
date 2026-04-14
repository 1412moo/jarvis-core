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


def _build_retro_today_payload(report_today_result: dict[str, Any]) -> dict[str, Any]:
    counts = report_today_result.get("counts") or {}
    total = int(report_today_result.get("total") or 0)
    today_ymd = datetime.utcnow().strftime("%Y-%m-%d")

    failed_count = int(counts.get("FAILED", 0))
    doing_count = int(counts.get("DOING", 0))
    done_count = int(counts.get("DONE", 0))
    needs_approval_count = int(counts.get("NEEDS_APPROVAL", 0))

    highlights: list[str] = []
    if total == 0:
        highlights.append("오늘 반영된 작업이 없거나 기준에 맞는 변경이 없음")
    else:
        if done_count > 0:
            highlights.append(f"DONE 상태 작업 {done_count}건이 오늘 반영됨")
        if doing_count > 0:
            highlights.append(f"DOING 상태 작업 {doing_count}건이 진행 중으로 확인됨")
        if failed_count > 0:
            highlights.append(f"FAILED 상태 작업 {failed_count}건이 확인됨")
        if not highlights:
            highlights.append("오늘 작업 상태 집계가 완료됨")
    highlights = highlights[:3]

    risks: list[str] = []
    if failed_count > 0:
        risks.append("실패 원인 재검토 필요")
    if needs_approval_count > 0:
        risks.append("승인 대기 항목 존재")
    if total == 0:
        risks.append("회고 대상 부족")

    recommended_next_steps: list[str] = []
    if total == 0:
        recommended_next_steps.append("오늘 반영된 작업이 있는지 입력/상태 기록을 점검한다")
    else:
        recommended_next_steps.append("회고 highlights를 기준으로 다음 우선순위를 정리한다")
    if failed_count > 0:
        recommended_next_steps.append("FAILED 항목별 원인과 재시도 조건을 문서화한다")
    if needs_approval_count > 0:
        recommended_next_steps.append("승인 대기 항목의 승인 요청 조건을 확인한다")

    if not recommended_next_steps:
        recommended_next_steps.append("내일 작업 시작 전 오늘 요약을 참고해 계획을 갱신한다")
    recommended_next_steps = recommended_next_steps[:3]

    return {
        "result_type": "retro_today_result",
        "date": today_ymd,
        "total": total,
        "counts": counts,
        "highlights": highlights,
        "risks": risks,
        "recommended_next_steps": recommended_next_steps,
    }


def _run_retro_today(command_text: str) -> dict[str, Any]:
    parts = command_text.strip().split()
    if len(parts) != 2 or parts[0] != "/retro" or parts[1] != "today":
        return _error_payload("usage:/retro today")

    report_today_result = _run_report_today("/report today")
    return _build_retro_today_payload(report_today_result)


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

    status = metadata["status"]
    return {
        "result_type": "review_task_result",
        "task_id": metadata["id"],
        "title": metadata["title"],
        "status": status,
        "updated_at": metadata["updated_at"],
        "summary": metadata["summary"],
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


def _build_execution_candidate(task_id: str) -> dict[str, Any] | None:
    task_file = REPO_ROOT / "memory" / "tasks" / f"{task_id}.md"
    if not task_file.exists() or not task_file.is_file():
        return None

    metadata = _read_task_metadata(task_file)
    if metadata is None:
        return None

    title_summary = f"{metadata.get('title', '')} {metadata.get('summary', '')}".lower()
    if any(keyword in title_summary for keyword in ("script", "run", "demo")):
        return {
            "result_type": "execution_candidate",
            "task_id": task_id,
            "execution_type": "script",
            "action": "plan_script_execution",
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
        "requested_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "source": "approve_file_write_result",
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

    execution_candidate = _build_execution_candidate(task_id)
    execution_request = None
    execution_result_dry_run = None
    if isinstance(execution_candidate, dict):
        execution_request = _build_execution_request(execution_candidate)
        execution_result_dry_run = _build_execution_result_dry_run(execution_request)
    return {
        "result_type": "approve_file_write_result",
        "task_id": task_id,
        "applied": True,
        "error": False,
        "reason": "",
        "applied_transition": {"from": transition_from, "to": transition_to},
        "execution_candidate": execution_candidate,
        "execution_request": execution_request,
        "execution_result_dry_run": execution_result_dry_run,
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
    if content.startswith("/approve"):
        return _run_approve_parse(content)
    if content == "/report today":
        return _run_report_today(content)
    if content.startswith("/report"):
        return _run_report(content)
    return _error_payload("unsupported_command")


def _format_reply(pipeline_result: dict[str, Any]) -> str:
    result_type = pipeline_result.get("result_type")
    if result_type == "retro_today_result":
        counts = pipeline_result.get("counts") or {}
        highlights = pipeline_result.get("highlights") or []
        risks = pipeline_result.get("risks") or []
        next_steps = pipeline_result.get("recommended_next_steps") or []
        highlights_text = "\n".join(f"- {item}" for item in highlights) if highlights else "- (없음)"
        risks_text = "\n".join(f"- {item}" for item in risks) if risks else "- (없음)"
        next_steps_text = "\n".join(f"- {item}" for item in next_steps) if next_steps else "- (없음)"
        return (
            "🪞 retro today 결과\n"
            f"- date: `{pipeline_result.get('date')}`\n"
            f"- total: {pipeline_result.get('total', 0)}\n"
            f"- DONE: {counts.get('DONE', 0)}\n"
            f"- DOING: {counts.get('DOING', 0)}\n"
            f"- FAILED: {counts.get('FAILED', 0)}\n"
            f"- NEEDS_APPROVAL: {counts.get('NEEDS_APPROVAL', 0)}\n\n"
            f"highlights:\n{highlights_text}\n\n"
            f"risks:\n{risks_text}\n\n"
            f"recommended_next_steps:\n{next_steps_text}"
        )
    if result_type == "review_task_result":
        recommended = pipeline_result.get("recommended_next_steps") or []
        related_files = pipeline_result.get("related_files") or []
        recommended_text = "\n".join(f"- {item}" for item in recommended) if recommended else "- (없음)"
        related_text = "\n".join(f"- {path}" for path in related_files) if related_files else "- (없음)"
        return (
            "🧪 review task 결과\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- title: `{pipeline_result.get('title')}`\n"
            f"- status: `{pipeline_result.get('status')}`\n"
            f"- updated_at: `{pipeline_result.get('updated_at')}`\n"
            f"- summary: `{pipeline_result.get('summary')}`\n"
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
        if pipeline_result.get("applied") is True:
            applied_transition = pipeline_result.get("applied_transition") or {}
            execution_candidate = pipeline_result.get("execution_candidate")
            execution_result_dry_run = pipeline_result.get("execution_result_dry_run")
            execution_line = ""
            if isinstance(execution_candidate, dict):
                execution_line = (
                    f"\n🚀 execution candidate 생성됨\n"
                    f"- execution_type: `{execution_candidate.get('execution_type')}`\n"
                    f"- action: `{execution_candidate.get('action')}`"
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
            return (
                "🧾 approve file write result 생성 완료\n"
                f"- task_id: `{pipeline_result.get('task_id')}`\n"
                f"- applied: `{pipeline_result.get('applied')}`\n"
                f"- applied_transition: `{applied_transition.get('from')} -> {applied_transition.get('to')}`"
                f"{execution_line}"
                f"{dry_run_line}"
            )
        return (
            "🧾 approve file write result 생성 완료\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- applied: `{pipeline_result.get('applied')}`\n"
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
    parser = argparse.ArgumentParser(
        description="Minimal Discord /plan,/task,/status,/review-task,/report,/retro today,/approve bot"
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

    original_repo_root = REPO_ROOT
    with tempfile.TemporaryDirectory(prefix="jarvis-self-check-") as temp_dir:
        temp_repo = Path(temp_dir)
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
            status_changed = before_status.get("status") == "NEEDS_APPROVAL" and after_status.get("status") == "DOING"
            updated_at_changed = before_status.get("updated_at") == old_updated_at and after_status.get("updated_at") != old_updated_at
            approve_result_ok = (
                approve_result.get("result_type") == "approve_file_write_result"
                and approve_result.get("applied") is True
                and approve_result.get("error") is False
                and approve_result.get("reason") == ""
            )
            _record("approve_applied_payload", approve_result_ok, f"result={approve_result}")
            execution_candidate_ok = (
                isinstance(approve_result.get("execution_candidate"), dict)
                and approve_result["execution_candidate"].get("result_type") == "execution_candidate"
                and approve_result["execution_candidate"].get("execution_type") == "script"
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
            )
            _record("execution_candidate_not_created", no_candidate_ok, f"result={no_candidate_result}")
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

        if (
            not content.startswith("/plan")
            and not content.startswith("/task")
            and not content.startswith("/status")
            and not content.startswith("/review-task")
            and not content.startswith("/retro")
            and not content.startswith("/report")
            and not content.startswith("/approve")
        ):
            await message.reply(
                "이 봇은 현재 `/plan <request>`, `/task <내용>`, `/status <task-id>`, `/review-task <task-id>`, `/report`, `/report today`, `/retro today`, `/approve <task-id> approve|reject`만 지원합니다."
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
