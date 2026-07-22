"""Deterministic copy-only handoff from Hermes to Jarvis Codex Review."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .approval_binding import build_scope_approval_binding
from .prompt_queue import (
    REQUIRED_FORBIDDEN_ACTIONS,
    PromptQueueState,
    normalize_prompt_queue,
)
from .review_record import (
    ReviewGitSnapshot,
    ReviewRecord,
    evaluate_review_record_freshness,
    normalize_review_git_snapshot,
    review_record_to_dict,
)
from .schemas import SessionState, ValidationError, normalize_session_state


HANDOFF_ENDPOINT = "/api/review-handoff"
PROTECTED_UNTRACKED_PATH = "jarvis.bat"
PROJECT_ID = "jarvis-core"
PROJECT_NAME = "Jarvis Core"
_SUMMARY_LIMIT = 1200


def build_copy_only_review_handoff(
    session_data: Mapping[str, Any],
    git_state: Mapping[str, Any],
    *,
    trusted_repo_root: str | Path,
    scope_confirmed: bool,
) -> dict[str, Any]:
    """Return one Jarvis-compatible queue envelope without persistence or execution."""

    if scope_confirmed is not True:
        raise ValidationError("scope must be explicitly confirmed before review handoff")
    session = normalize_session_state(session_data)
    root = Path(trusted_repo_root).resolve()
    _validate_session_for_handoff(session, root)

    branch = _required_git_text(git_state, "branch")
    head = _required_git_text(git_state, "head")
    status_lines = _status_lines(_required_git_status(git_state))
    if f"?? {PROTECTED_UNTRACKED_PATH}" not in status_lines:
        raise ValidationError(f"{PROTECTED_UNTRACKED_PATH} must remain untracked")

    protected_by_key = {
        _path_key(path): path for path in session.protected_paths
    }
    protected_by_key[_path_key(PROTECTED_UNTRACKED_PATH)] = PROTECTED_UNTRACKED_PATH
    protected_paths = tuple(sorted(protected_by_key.values(), key=str.casefold))
    target_keys = {_path_key(path) for path in session.target_files}
    protected_overlap = tuple(
        path for path in protected_paths if _path_key(path) in target_keys
    )
    if protected_overlap:
        raise ValidationError(
            "protected paths must not appear in review targets: "
            + ", ".join(protected_overlap)
        )

    item_id = _item_id(session, branch, head)
    queue_payload: dict[str, Any] = {
        "queue_type": "hermes_prompt_queue",
        "version": "0.1B-2",
        "projects": [
            {
                "project_id": PROJECT_ID,
                "display_name": PROJECT_NAME,
                "repo_path": str(root),
                "expected_branch": branch,
                "expected_head": head,
                "protected_paths": list(protected_paths),
                "expected_untracked": [PROTECTED_UNTRACKED_PATH],
                "forbidden_actions": sorted(REQUIRED_FORBIDDEN_ACTIONS),
                "validation_commands": list(session.validation_commands),
            }
        ],
        "items": [
            {
                "item_id": item_id,
                "project_id": PROJECT_ID,
                "current_goal": session.current_goal,
                "current_task": session.active_task,
                "result_type": "review",
                "target_files": list(session.target_files),
                "observed_branch": branch,
                "observed_head": head,
                "observed_git_status": list(status_lines),
                "scope_approved": False,
                "review_passed": False,
                "commit_approved": False,
                "scope_approval_digest": "",
                "change_evidence_digest": "",
                "review_approval_digest": "",
                "commit_approval_digest": "",
                "commit_message": "",
                "last_prompt_summary": _bounded_summary(
                    session.last_codex_prompt
                    or f"Implementation requested: {session.active_task}"
                ),
                "last_result_summary": _bounded_summary(
                    session.last_codex_result_summary
                ),
            }
        ],
    }

    initial_queue = normalize_prompt_queue(queue_payload)
    scope_binding = build_scope_approval_binding(
        initial_queue.projects[0],
        replace(initial_queue.items[0], result_type="implementation"),
    )
    queue_payload["items"][0]["scope_approved"] = True
    queue_payload["items"][0]["scope_approval_digest"] = scope_binding.digest
    queue = normalize_prompt_queue(queue_payload)
    return _envelope(queue, item_id)


def build_copy_only_review_handoff_from_record(
    record: ReviewRecord,
    current_git_snapshot: ReviewGitSnapshot | Mapping[str, Any],
    *,
    trusted_repo_root: str | Path,
    scope_confirmed: bool,
) -> dict[str, Any]:
    """Regenerate one copy-only handoff from an exact, still-fresh Review record.

    This adapter is pure: the caller supplies both the immutable stored record
    and freshly collected Git metadata. It neither reads Git nor writes state.
    """

    if scope_confirmed is not True:
        raise ValidationError(
            "stored Review target scope must be explicitly reconfirmed"
        )
    record_data = review_record_to_dict(record)
    current = (
        current_git_snapshot
        if isinstance(current_git_snapshot, ReviewGitSnapshot)
        else normalize_review_git_snapshot(
            current_git_snapshot,
            path="current reopen-to-handoff git snapshot",
        )
    )
    freshness = evaluate_review_record_freshness(record, current)
    if not freshness.matches:
        raise ValidationError(
            "stored Review is stale: " + "; ".join(freshness.blocking_reasons)
        )

    working_tree_status = "\n".join(current.status) or "clean"
    session_data = {
        "repo": str(Path(trusted_repo_root).resolve()),
        "branch": current.branch,
        "head": current.head,
        "working_tree_status": working_tree_status,
        "current_goal": record_data["current_goal"],
        "active_task": record_data["active_task"],
        "blocked_by": "",
        "last_codex_prompt": record_data["last_codex_prompt_summary"],
        "last_codex_result_summary": record_data["result_summary"],
        "validation_commands": record_data["validation_commands"],
        "files_touched": record_data["target_files"],
        "target_files": record_data["target_files"],
        "protected_paths": [PROTECTED_UNTRACKED_PATH],
        "commit_allowed": False,
        "push_allowed": False,
        "human_approval_required": True,
        "human_approval_granted": False,
        "next_action": "REVIEW_REQUEST",
        "commit_message": "",
    }
    return build_copy_only_review_handoff(
        session_data,
        {
            "branch": current.branch,
            "head": current.head,
            "working_tree_status": working_tree_status,
        },
        trusted_repo_root=trusted_repo_root,
        scope_confirmed=scope_confirmed,
    )


def render_copy_only_review_handoff(handoff: Mapping[str, Any]) -> str:
    """Render one stable, human-copyable JSON envelope."""

    if set(handoff) != {"queue", "item_id"}:
        raise ValidationError("review handoff fields must be exactly queue and item_id")
    return json.dumps(handoff, ensure_ascii=False, indent=2, sort_keys=True)


def _validate_session_for_handoff(session: SessionState, root: Path) -> None:
    if _resolved_path_key(session.repo) != _resolved_path_key(root):
        raise ValidationError("session repository does not match the trusted repository")
    if session.blocked_by:
        raise ValidationError("blocked session cannot create a review handoff")
    if not session.target_files:
        raise ValidationError("review handoff requires explicit target files")
    if any(path.startswith("NEEDS_USER_CONFIRMATION") for path in session.target_files):
        raise ValidationError("target files still need user confirmation")
    if not session.last_codex_result_summary.strip():
        raise ValidationError("Codex result is required before review handoff")
    if session.commit_allowed or session.human_approval_granted:
        raise ValidationError("review handoff must not contain commit approval")
    if session.push_allowed:
        raise ValidationError("review handoff must not allow push")
    if PROTECTED_UNTRACKED_PATH.casefold() not in {
        path.casefold() for path in session.protected_paths
    }:
        raise ValidationError(f"protected paths must include {PROTECTED_UNTRACKED_PATH}")


def _required_git_text(git_state: Mapping[str, Any], field: str) -> str:
    if not isinstance(git_state, Mapping):
        raise ValidationError("git state must be an object")
    value = git_state.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"git state {field} must be a non-empty string")
    return value.strip()


def _required_git_status(git_state: Mapping[str, Any]) -> str:
    """Return bounded caller status text without losing porcelain columns."""

    if not isinstance(git_state, Mapping):
        raise ValidationError("git state must be an object")
    value = git_state.get("working_tree_status")
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            "git state working_tree_status must be a non-empty string"
        )
    return value.rstrip("\r\n")


def _status_lines(status: str) -> tuple[str, ...]:
    if status == "clean":
        return ()
    return tuple(line.rstrip() for line in status.splitlines() if line.strip())


def _item_id(session: SessionState, branch: str, head: str) -> str:
    identity = {
        "active_task": session.active_task,
        "branch": branch,
        "current_goal": session.current_goal,
        "head": head,
        "target_files": sorted(session.target_files, key=str.casefold),
    }
    canonical = json.dumps(
        identity,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"review-{hashlib.sha256(canonical).hexdigest()[:12]}"


def _bounded_summary(value: str) -> str:
    compact = " ".join(value.strip().split())
    if len(compact) <= _SUMMARY_LIMIT:
        return compact
    return compact[: _SUMMARY_LIMIT - 3].rstrip() + "..."


def _envelope(queue: PromptQueueState, item_id: str) -> dict[str, Any]:
    queue_data = json.loads(json.dumps(asdict(queue), ensure_ascii=False))
    return {"queue": queue_data, "item_id": item_id}


def _resolved_path_key(value: str | Path) -> str:
    return os.path.normcase(str(Path(value).resolve()))


def _path_key(value: str) -> str:
    return value.replace("\\", "/").casefold()
