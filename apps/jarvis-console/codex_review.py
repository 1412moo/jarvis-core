"""Write-free Jarvis Console adapter for one fresh Hermes review session."""

from __future__ import annotations

from dataclasses import replace
from http import HTTPStatus
from pathlib import Path
import sys
from typing import Any, Mapping


APP_ROOT = Path(__file__).resolve().parent
HERMES_APP_ROOT = APP_ROOT.parent / "hermes-manager-pilot"
if str(HERMES_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_APP_ROOT))

from hermes_manager_pilot.approval_binding import (  # noqa: E402
    build_scope_approval_binding,
    digest_matches,
)
from hermes_manager_pilot.change_evidence import (  # noqa: E402
    build_fresh_review_handoff_decision,
    build_review_session_from_fresh_preview,
    collect_review_evidence_bundle,
    evaluate_review_evidence_in_queue,
)
from hermes_manager_pilot.prompt_queue import (  # noqa: E402
    ProjectCard,
    PromptQueueState,
    QueueItem,
    normalize_prompt_queue,
)
from hermes_manager_pilot.schemas import SessionState, ValidationError  # noqa: E402


CODEX_REVIEW_PREVIEW_ENDPOINT = "/api/codex-review/preview"
CODEX_REVIEW_MODE = "read-only"
CODEX_REVIEW_ERROR = "invalid_codex_review_handoff"
CODEX_REVIEW_BLOCKED_ERROR = "codex_review_blocked"
CODEX_REVIEW_NOTES = (
    "This review was rebuilt from fresh bounded local evidence.",
    "No queue, evidence, session, prompt, or approval was persisted.",
    "No prompt was rendered or executed, and no commit or push was authorized.",
)


def build_codex_review_preview(
    payload: Mapping[str, Any],
    trusted_repo_root: str | Path,
) -> tuple[int, dict[str, Any]]:
    """Build one bounded read-only payload from an approved Hermes queue snapshot."""

    try:
        queue, item, project = _normalize_request(payload)
        _validate_pre_collection_review(project, item)
    except ValidationError as exc:
        return _validation_error(str(exc))

    try:
        bundle = collect_review_evidence_bundle(trusted_repo_root, project, item)
        observation = evaluate_review_evidence_in_queue(queue, item.item_id, bundle)
    except ValidationError as exc:
        return _blocked_error((f"review evidence blocked: {exc}",))

    if observation.evaluation.is_blocked:
        return _blocked_error(observation.evaluation.blocking_reasons)

    try:
        decision = build_fresh_review_handoff_decision(
            trusted_repo_root,
            observation,
        )
    except ValidationError as exc:
        return _blocked_error((f"fresh review validation blocked: {exc}",))
    if decision.is_blocked or decision.preview is None:
        return _blocked_error(
            decision.blocking_reasons or ("fresh review preview is unavailable",)
        )

    try:
        session = build_review_session_from_fresh_preview(decision.preview)
    except ValidationError as exc:
        return _blocked_error((f"review session validation blocked: {exc}",))

    return HTTPStatus.OK, _presentation_payload(project, item, session)


def _normalize_request(
    payload: Mapping[str, Any],
) -> tuple[PromptQueueState, QueueItem, ProjectCard]:
    if not isinstance(payload, Mapping):
        raise ValidationError("request must be a JSON object")
    if set(payload) != {"queue", "item_id"}:
        raise ValidationError("request fields must be exactly queue and item_id")
    queue_data = payload.get("queue")
    if not isinstance(queue_data, Mapping):
        raise ValidationError("queue must be a JSON object")
    item_id = payload.get("item_id")
    if not isinstance(item_id, str) or not item_id or item_id != item_id.strip():
        raise ValidationError("item_id must be a non-empty normalized string")

    queue = normalize_prompt_queue(queue_data)
    items = tuple(candidate for candidate in queue.items if candidate.item_id == item_id)
    if len(items) != 1:
        raise ValidationError("selected review item was not found")
    item = items[0]
    projects = tuple(
        candidate for candidate in queue.projects if candidate.project_id == item.project_id
    )
    if len(projects) != 1:
        raise ValidationError("selected review project was not found")
    return queue, item, projects[0]


def _validate_pre_collection_review(project: ProjectCard, item: QueueItem) -> None:
    if item.result_type != "review":
        raise ValidationError("selected item must have result_type=review")
    if not item.target_files:
        raise ValidationError("selected review item requires target files")
    if item.change_evidence_digest:
        raise ValidationError("selected review item must not replace existing evidence")
    if item.review_passed or item.review_approval_digest:
        raise ValidationError("selected review item must be unreviewed")
    if item.commit_approved or item.commit_approval_digest or item.commit_message:
        raise ValidationError("selected review item contains commit-stage metadata")
    if not item.scope_approved:
        raise ValidationError("selected review item requires prior scope approval")

    implementation_item = replace(item, result_type="implementation")
    expected_scope = build_scope_approval_binding(project, implementation_item)
    if not digest_matches(expected_scope, item.scope_approval_digest):
        raise ValidationError("selected review item scope approval is stale")


def _presentation_payload(
    project: ProjectCard,
    item: QueueItem,
    session: SessionState,
) -> dict[str, Any]:
    return {
        "ok": True,
        "mode": CODEX_REVIEW_MODE,
        "write_free": True,
        "no_persistence": True,
        "project": {
            "project_id": project.project_id,
            "display_name": project.display_name,
            "repo_name": Path(project.repo_path).name,
            "branch": session.branch,
            "head": session.head,
        },
        "review": {
            "item_id": item.item_id,
            "current_goal": session.current_goal,
            "current_task": session.active_task,
            "working_tree_status": session.working_tree_status,
            "files_touched": list(session.files_touched),
            "target_files": list(session.target_files),
            "validation_commands": list(session.validation_commands),
            "last_prompt_summary": session.last_codex_prompt,
            "last_result_summary": session.last_codex_result_summary,
            "next_action": session.next_action,
        },
        "safety": {
            "fresh_local_evidence": True,
            "read_only": True,
            "human_approval_required": session.human_approval_required,
            "human_approval_granted": session.human_approval_granted,
            "commit_allowed": session.commit_allowed,
            "push_allowed": session.push_allowed,
            "prompt_rendered": False,
            "command_executed": False,
            "external_call": False,
        },
        "notes": list(CODEX_REVIEW_NOTES),
    }


def _validation_error(detail: str) -> tuple[int, dict[str, Any]]:
    return HTTPStatus.BAD_REQUEST, {
        "ok": False,
        "mode": CODEX_REVIEW_MODE,
        "write_free": True,
        "no_persistence": True,
        "error": CODEX_REVIEW_ERROR,
        "detail": detail,
        "review": None,
    }


def _blocked_error(reasons: tuple[str, ...]) -> tuple[int, dict[str, Any]]:
    return HTTPStatus.CONFLICT, {
        "ok": False,
        "mode": CODEX_REVIEW_MODE,
        "write_free": True,
        "no_persistence": True,
        "error": CODEX_REVIEW_BLOCKED_ERROR,
        "blocking_reasons": list(reasons),
        "review": None,
    }
