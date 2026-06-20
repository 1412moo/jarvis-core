"""Schemas and validation for the Hermes Manager Pilot v0.2 renderer."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


VERSION = "0.2"
SESSION_TYPE = "hermes_manager_session_state"

ALLOWED_NEXT_ACTIONS = frozenset(
    {
        "PROMPT_FOR_CODEX",
        "REVIEW_REQUEST",
        "COMMIT_REQUEST",
        "STATUS_SUMMARY",
        "BLOCKED_NEEDS_USER",
        "SKILL_CANDIDATE",
        "DAILY_RADAR_HANDOFF",
        "RESEARCH_COUNCIL_HANDOFF",
    }
)

FORBIDDEN_SECRET_FIELD_PARTS = (
    "apikey",
    "api_key",
    "credential",
    "password",
    "secret",
    "token",
)

FORBIDDEN_REASONING_FIELDS = frozenset(
    {
        "chain_of_thought",
        "hidden_chain_of_thought",
        "hidden_cot",
        "hidden_reasoning",
        "internal_reasoning",
        "private_notes",
        "private_reasoning",
        "reasoning_trace",
        "scratchpad",
    }
)


class ValidationError(ValueError):
    """Raised when session state violates the v0.2 local renderer contract."""


@dataclass(frozen=True)
class SessionState:
    """A normalized Hermes Manager Pilot session state."""

    repo: str
    branch: str
    head: str
    working_tree_status: str
    current_goal: str
    active_task: str
    blocked_by: str
    last_codex_prompt: str
    last_codex_result_summary: str
    validation_commands: tuple[str, ...]
    files_touched: tuple[str, ...]
    protected_paths: tuple[str, ...]
    commit_allowed: bool
    push_allowed: bool
    human_approval_required: bool
    human_approval_granted: bool
    next_action: str
    target_files: tuple[str, ...] = ()
    commit_message: str = ""
    session_type: str = SESSION_TYPE
    version: str = VERSION


def normalize_session_state(data: Mapping[str, Any]) -> SessionState:
    """Validate and normalize a local Hermes Manager Pilot session mapping."""

    if not isinstance(data, Mapping):
        raise ValidationError("session state must be a JSON object")
    _reject_forbidden_fields(data)

    session_type = _optional_text(data, "session_type") or SESSION_TYPE
    if session_type != SESSION_TYPE:
        raise ValidationError(f"session_type must be {SESSION_TYPE}")

    version = _optional_text(data, "version") or VERSION
    if version != VERSION:
        raise ValidationError(f"version must be {VERSION}")

    next_action = _required_text(data, "next_action")
    if next_action not in ALLOWED_NEXT_ACTIONS:
        raise ValidationError(f"next_action is invalid: {next_action}")

    validation_commands = _required_text_list(data, "validation_commands")
    files_touched = _required_text_list(data, "files_touched")
    protected_paths = _required_text_list(data, "protected_paths")
    target_files = _optional_text_list(data, "target_files")

    commit_allowed = _optional_bool(data, "commit_allowed", default=False)
    push_allowed = _optional_bool(data, "push_allowed", default=False)
    human_approval_required = _optional_bool(data, "human_approval_required", default=True)
    human_approval_granted = _optional_bool(data, "human_approval_granted", default=False)

    if push_allowed:
        raise ValidationError("push_allowed=true is not allowed in v0.2")
    if commit_allowed and not human_approval_required:
        raise ValidationError("commit_allowed=true requires human_approval_required=true")
    if human_approval_granted and not human_approval_required:
        raise ValidationError("human_approval_granted=true requires human_approval_required=true")
    if not protected_paths:
        raise ValidationError("protected_paths must include at least one protected path")

    protected_overlap = _protected_files_touched(files_touched, protected_paths)
    if protected_overlap:
        joined = ", ".join(protected_overlap)
        raise ValidationError(f"protected paths must not appear in files_touched: {joined}")

    return SessionState(
        repo=_required_text(data, "repo"),
        branch=_required_text(data, "branch"),
        head=_required_text(data, "head"),
        working_tree_status=_required_text(data, "working_tree_status"),
        current_goal=_required_text(data, "current_goal"),
        active_task=_required_text(data, "active_task"),
        blocked_by=_required_text(data, "blocked_by", allow_empty=True),
        last_codex_prompt=_required_text(data, "last_codex_prompt", allow_empty=True),
        last_codex_result_summary=_required_text(
            data,
            "last_codex_result_summary",
            allow_empty=True,
        ),
        validation_commands=validation_commands,
        files_touched=files_touched,
        protected_paths=protected_paths,
        commit_allowed=commit_allowed,
        push_allowed=push_allowed,
        human_approval_required=human_approval_required,
        human_approval_granted=human_approval_granted,
        next_action=next_action,
        target_files=target_files,
        commit_message=_optional_text(data, "commit_message"),
        session_type=session_type,
        version=version,
    )


def _required_text(data: Mapping[str, Any], field: str, allow_empty: bool = False) -> str:
    if field not in data:
        raise ValidationError(f"{field} is required")
    value = data[field]
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    normalized = _compact_text(value)
    if not allow_empty and not normalized:
        raise ValidationError(f"{field} must be a non-empty string")
    return normalized


def _optional_text(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string when provided")
    return _compact_text(value)


def _optional_bool(data: Mapping[str, Any], field: str, default: bool) -> bool:
    value = data.get(field, default)
    if not isinstance(value, bool):
        raise ValidationError(f"{field} must be a boolean")
    return value


def _required_text_list(data: Mapping[str, Any], field: str) -> tuple[str, ...]:
    if field not in data:
        raise ValidationError(f"{field} is required")
    return _text_list(data[field], field)


def _optional_text_list(data: Mapping[str, Any], field: str) -> tuple[str, ...]:
    if field not in data or data[field] is None:
        return ()
    return _text_list(data[field], field)


def _text_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list of strings")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{field}[{index}] must be a non-empty string")
        normalized.append(_compact_text(item))
    return tuple(normalized)


def _protected_files_touched(
    files_touched: tuple[str, ...],
    protected_paths: tuple[str, ...],
) -> tuple[str, ...]:
    protected = {_path_key(path) for path in protected_paths}
    return tuple(
        path
        for path in files_touched
        if _path_key(path) in protected
    )


def _path_key(path: str) -> str:
    return path.replace("\\", "/").strip().lower()


def _compact_text(value: str) -> str:
    return " ".join(value.strip().split())


def _reject_forbidden_fields(value: Any, path: str = "input") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            if _is_forbidden_secret_field(key_lower):
                raise ValidationError(f"{path}.{key_text} is not allowed; secrets must not be stored")
            if _reasoning_key(key_lower) in FORBIDDEN_REASONING_FIELDS:
                raise ValidationError(
                    f"{path}.{key_text} is not allowed; hidden reasoning must not be stored"
                )
            _reject_forbidden_fields(item, f"{path}.{key_text}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_fields(item, f"{path}[{index}]")


def _is_forbidden_secret_field(key_lower: str) -> bool:
    return any(field_part in key_lower for field_part in FORBIDDEN_SECRET_FIELD_PARTS)


def _reasoning_key(key_lower: str) -> str:
    return key_lower.replace("-", "_").replace(" ", "_")
