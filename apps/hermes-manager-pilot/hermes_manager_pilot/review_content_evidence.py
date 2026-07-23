"""Bind bounded local content evidence to one Durable Review record.

This adapter performs read-only Git and file collection through the existing
change-evidence subsystem. It does not persist data, expose routes, execute
prompts, use the clipboard, or grant review, commit, push, or execution
authority.
"""

from __future__ import annotations

import hmac
from pathlib import Path
from typing import Any

from .change_evidence import (
    EVIDENCE_TYPE,
    MAX_TARGET_FILES,
    MAX_TOTAL_FILE_BYTES,
    VERSION as CHANGE_EVIDENCE_VERSION,
    collect_review_evidence_bundle,
)
from .prompt_queue import ProjectCard, QueueItem, REQUIRED_FORBIDDEN_ACTIONS
from .review_record import (
    CONTENT_EVIDENCE_BINDING_TYPE,
    CONTENT_EVIDENCE_BINDING_VERSION,
    CONTENT_EVIDENCE_COVERAGE,
    CONTENT_EVIDENCE_SOURCE_TYPE,
    CONTENT_EVIDENCE_SOURCE_VERSION,
    PROTECTED_UNTRACKED_PATH,
    ReviewContentEvidenceBinding,
    ReviewGitSnapshot,
    ReviewRecord,
    ReviewRecordError,
    evaluate_review_record_freshness,
    normalize_review_content_evidence_binding,
    normalize_review_git_snapshot,
    review_content_evidence_binding_to_dict,
    review_record_to_dict,
)
from .schemas import ValidationError


class ReviewContentEvidenceError(ValueError):
    """A fixed-category evidence failure without local path disclosure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def collect_review_content_evidence_binding(
    trusted_repo_root: str | Path,
    record: ReviewRecord,
    current_git_snapshot: ReviewGitSnapshot | dict[str, Any],
) -> ReviewContentEvidenceBinding:
    """Collect one stable binding for the exact Review target content."""

    try:
        normalized_record = _validated_record(record)
        current = (
            _validated_snapshot(current_git_snapshot)
            if isinstance(current_git_snapshot, ReviewGitSnapshot)
            else normalize_review_git_snapshot(
                current_git_snapshot,
                path="content evidence Git snapshot",
            )
        )
        freshness = evaluate_review_record_freshness(normalized_record, current)
        if not freshness.matches:
            raise ReviewContentEvidenceError(
                "review_content_evidence_snapshot_mismatch"
            )
        concrete_targets = materialize_review_content_targets(
            normalized_record.target_files,
            current.status,
        )
        project, item = _evidence_subject(
            trusted_repo_root,
            normalized_record,
            current,
            concrete_targets,
        )
        bundle = collect_review_evidence_bundle(
            trusted_repo_root,
            project,
            item,
        )
        collected = normalize_review_git_snapshot(
            {
                "branch": bundle.branch,
                "head": bundle.head,
                "status": list(bundle.whole_status_evidence.whole_git_status),
            },
            path="collected content evidence Git snapshot",
        )
        if collected != current:
            raise ReviewContentEvidenceError(
                "review_content_evidence_repository_changed"
            )
        evidence = bundle.target_evidence
        total_bytes = sum(target.byte_size for target in evidence.targets)
        if (
            CONTENT_EVIDENCE_SOURCE_TYPE != EVIDENCE_TYPE
            or CONTENT_EVIDENCE_SOURCE_VERSION != CHANGE_EVIDENCE_VERSION
            or evidence.evidence_type != EVIDENCE_TYPE
            or evidence.version != CHANGE_EVIDENCE_VERSION
            or len(evidence.targets) < 1
            or len(evidence.targets) > MAX_TARGET_FILES
            or total_bytes < 0
            or total_bytes > MAX_TOTAL_FILE_BYTES
        ):
            raise ReviewContentEvidenceError(
                "review_content_evidence_collection_invalid"
            )
        return normalize_review_content_evidence_binding(
            {
                "binding_type": CONTENT_EVIDENCE_BINDING_TYPE,
                "version": CONTENT_EVIDENCE_BINDING_VERSION,
                "source_evidence_type": CONTENT_EVIDENCE_SOURCE_TYPE,
                "source_evidence_version": CONTENT_EVIDENCE_SOURCE_VERSION,
                "coverage": CONTENT_EVIDENCE_COVERAGE,
                "manifest_target_count": len(evidence.targets),
                "manifest_total_bytes": total_bytes,
                "change_evidence_digest": evidence.change_evidence_digest,
            }
        )
    except ReviewContentEvidenceError:
        raise
    except (ReviewRecordError, ValidationError, OSError, RuntimeError, TypeError):
        raise ReviewContentEvidenceError(
            "review_content_evidence_collection_failed"
        ) from None


def materialize_review_content_targets(
    declared_targets: tuple[str, ...],
    git_status: tuple[str, ...],
) -> tuple[str, ...]:
    """Expand directory scopes to exact Git-visible changed descendants."""

    if not isinstance(declared_targets, tuple) or not isinstance(git_status, tuple):
        raise ReviewContentEvidenceError("review_content_evidence_scope_invalid")
    changed_paths = tuple(
        line[3:]
        for line in git_status
        if isinstance(line, str)
        and len(line) >= 4
        and line[2] == " "
        and line[3:].casefold() != PROTECTED_UNTRACKED_PATH.casefold()
    )
    concrete: dict[str, str] = {}
    for target in declared_targets:
        if not isinstance(target, str) or not target:
            raise ReviewContentEvidenceError(
                "review_content_evidence_scope_invalid"
            )
        if target.endswith("/"):
            prefix = target.casefold()
            for changed_path in changed_paths:
                if changed_path.casefold().startswith(prefix):
                    concrete.setdefault(changed_path.casefold(), changed_path)
        else:
            concrete.setdefault(target.casefold(), target)
    if not concrete:
        raise ReviewContentEvidenceError("review_content_evidence_target_empty")
    if len(concrete) > MAX_TARGET_FILES:
        raise ReviewContentEvidenceError(
            "review_content_evidence_target_limit_exceeded"
        )
    return tuple(concrete[key] for key in sorted(concrete))


def content_evidence_bindings_match(
    stored: ReviewContentEvidenceBinding,
    current: ReviewContentEvidenceBinding,
) -> bool:
    """Compare two strictly normalized bindings with constant-time digest check."""

    try:
        stored_value = review_content_evidence_binding_to_dict(stored)
        current_value = review_content_evidence_binding_to_dict(current)
    except ReviewRecordError:
        return False
    stored_digest = stored_value.pop("change_evidence_digest")
    current_digest = current_value.pop("change_evidence_digest")
    return stored_value == current_value and hmac.compare_digest(
        stored_digest,
        current_digest,
    )


def _evidence_subject(
    trusted_repo_root: str | Path,
    record: ReviewRecord,
    current: ReviewGitSnapshot,
    concrete_targets: tuple[str, ...],
) -> tuple[ProjectCard, QueueItem]:
    root = Path(trusted_repo_root).resolve(strict=False)
    project = ProjectCard(
        project_id=record.project_id,
        display_name="Jarvis-Core Durable Review",
        repo_path=str(root),
        expected_branch=current.branch,
        expected_head=current.head,
        protected_paths=(PROTECTED_UNTRACKED_PATH,),
        expected_untracked=(PROTECTED_UNTRACKED_PATH,),
        forbidden_actions=tuple(sorted(REQUIRED_FORBIDDEN_ACTIONS)),
        validation_commands=record.validation_commands,
    )
    item = QueueItem(
        item_id=f"review-content-{record.review_id}",
        project_id=record.project_id,
        current_goal=record.current_goal,
        current_task=record.active_task,
        result_type="review",
        target_files=concrete_targets,
        observed_branch=current.branch,
        observed_head=current.head,
        observed_git_status=current.status,
        scope_approved=False,
        review_passed=False,
        commit_approved=False,
        scope_approval_digest="",
        change_evidence_digest="",
        review_approval_digest="",
        commit_approval_digest="",
        commit_message="",
        last_prompt_summary=record.last_codex_prompt_summary,
        last_result_summary=record.result_summary,
    )
    return project, item


def _validated_record(record: ReviewRecord) -> ReviewRecord:
    value = review_record_to_dict(record)
    if value.get("project_id") != "jarvis-core":
        raise ReviewContentEvidenceError("review_content_evidence_record_invalid")
    return record


def _validated_snapshot(snapshot: ReviewGitSnapshot) -> ReviewGitSnapshot:
    return normalize_review_git_snapshot(
        {
            "branch": snapshot.branch,
            "head": snapshot.head,
            "status": list(snapshot.status),
        },
        path="content evidence Git snapshot",
    )
