"""Minimal task draft builder from intake parser output.

Scope (MVP):
- accept parser output dict/ParseResult-compatible payload
- build task draft object only for /task
- return hold result for hold/error/non-task commands

Out of scope:
- writing files
- network calls
- Discord/GitHub integration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json


NON_TASK_DRAFT_REASON = "non_task_command_not_supported_for_draft"


@dataclass
class DraftBuildResult:
    result_type: str  # "task_draft" | "hold"
    task_draft: dict[str, Any] | None = None
    hold: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": self.result_type,
            "task_draft": self.task_draft,
            "hold": self.hold,
        }


def _normalize_spaces(text: str) -> str:
    return " ".join(text.strip().split())


def _extract_repo(normalized_payload: dict[str, Any]) -> str:
    repo_hint = normalized_payload.get("repo_hint")
    if isinstance(repo_hint, str) and repo_hint.strip():
        return repo_hint.strip()
    return "jarvis-core"


def _build_summary(request: str) -> str:
    normalized_request = _normalize_spaces(request)
    return (
        f"요청 사항({normalized_request})을 작업 초안으로 정리한다. "
        "이번 단계는 draft object 생성 규칙 정의까지만 포함한다."
    )


def _hold(reason: str, source_command: str | None) -> DraftBuildResult:
    return DraftBuildResult(
        result_type="hold",
        hold={
            "result_type": "hold",
            "reason": reason,
            "source_command": source_command,
        },
    )


def build_task_draft(parse_result: dict[str, Any]) -> DraftBuildResult:
    """Build a task draft object (or hold) from intake parser output."""
    command_name = parse_result.get("command_name")
    required_args_present = bool(parse_result.get("required_args_present"))
    normalized_payload = parse_result.get("normalized_payload") or {}
    hold_reason = parse_result.get("hold_reason")
    error_reason = parse_result.get("error_reason")

    if error_reason:
        return _hold(f"error_input:{error_reason}", command_name)

    if hold_reason:
        return _hold(f"hold_input:{hold_reason}", command_name)

    if command_name != "/task":
        return _hold(NON_TASK_DRAFT_REASON, command_name)

    if not required_args_present:
        return _hold("error_input:missing_required_args", command_name)

    request = _normalize_spaces(str(normalized_payload.get("request", "")))
    if not request:
        return _hold("error_input:missing_required_arg:request", command_name)

    task_draft = {
        "title": request,
        "status": "TODO",
        "repo": _extract_repo(normalized_payload),
        "summary": _build_summary(request),
        "source_command": command_name,
    }
    return DraftBuildResult(result_type="task_draft", task_draft=task_draft)


def main() -> None:
    # Local runnable examples without external dependencies.
    samples = [
        {
            "command_name": "/task",
            "required_args_present": True,
            "normalized_payload": {"request": "보고 시스템 개선", "repo_hint": None},
            "hold_reason": None,
            "error_reason": None,
        },
        {
            "command_name": "/task",
            "required_args_present": True,
            "normalized_payload": {"request": "production 삭제", "repo_hint": None},
            "hold_reason": "needs_approval:risky_keyword_detected",
            "error_reason": None,
        },
        {
            "command_name": "/status",
            "required_args_present": True,
            "normalized_payload": {"target": "task-0002"},
            "hold_reason": None,
            "error_reason": None,
        },
    ]

    for sample in samples:
        built = build_task_draft(sample)
        print(json.dumps({"input": sample, "output": built.to_dict()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
