"""Deterministic Prompt Queue v0.1B-1 approval-binding primitives.

Bindings detect changes to declared approval inputs. They are not signatures,
tokens, proof of human identity, or authority to execute an action.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import re
from typing import Any

from .prompt_queue import ProjectCard, QueueItem
from .schemas import ValidationError


VERSION = "0.1B-1"
BINDING_TYPE = "hermes_prompt_queue_approval_binding"
SCOPE_PURPOSE = "scope"
REVIEW_PURPOSE = "review"
COMMIT_PURPOSE = "commit"

_MAX_CANONICAL_BYTES = 64 * 1024
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_DOMAIN_PREFIXES = {
    SCOPE_PURPOSE: b"jarvis-core/hermes/prompt-queue/approval/scope/v0.1B-1\x00",
    REVIEW_PURPOSE: b"jarvis-core/hermes/prompt-queue/approval/review/v0.1B-1\x00",
    COMMIT_PURPOSE: b"jarvis-core/hermes/prompt-queue/approval/commit/v0.1B-1\x00",
}
_PURPOSE_RESULT_TYPES = {
    SCOPE_PURPOSE: "implementation",
    REVIEW_PURPOSE: "review",
    COMMIT_PURPOSE: "commit",
}


@dataclass(frozen=True)
class ApprovalBinding:
    """One bounded canonical snapshot and its domain-separated digest."""

    purpose: str
    digest: str
    canonical_bytes: bytes
    byte_size: int
    binding_type: str = BINDING_TYPE
    version: str = VERSION

    def snapshot(self) -> dict[str, Any]:
        """Return a new JSON-decoded copy of the canonical snapshot."""

        value = json.loads(self.canonical_bytes.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValidationError("approval binding snapshot must be an object")
        return value


def build_scope_approval_binding(
    project: ProjectCard,
    item: QueueItem,
) -> ApprovalBinding:
    """Bind one approved implementation scope without granting authority."""

    _validate_pair(project, item)
    _require_result_type(item, SCOPE_PURPOSE)
    if not item.target_files:
        raise ValidationError("scope approval binding requires target files")
    return _build_binding(SCOPE_PURPOSE, _scope_snapshot(project, item))


def build_review_approval_binding(
    project: ProjectCard,
    item: QueueItem,
    *,
    scope_digest: str,
    change_evidence_digest: str,
) -> ApprovalBinding:
    """Bind review evidence to the exact previously approved scope."""

    _validate_pair(project, item)
    _require_result_type(item, REVIEW_PURPOSE)
    normalized_scope_digest = _required_digest(scope_digest, "scope_digest")
    normalized_evidence_digest = _required_digest(
        change_evidence_digest,
        "change_evidence_digest",
    )
    current_scope = _build_binding(SCOPE_PURPOSE, _scope_snapshot(project, item))
    if not digest_matches(current_scope, normalized_scope_digest):
        raise ValidationError("scope approval binding is stale")
    return _build_binding(
        REVIEW_PURPOSE,
        _review_snapshot(
            project,
            item,
            scope_digest=current_scope.digest,
            change_evidence_digest=normalized_evidence_digest,
        ),
    )


def build_commit_approval_binding(
    project: ProjectCard,
    item: QueueItem,
    *,
    scope_digest: str,
    review_digest: str,
    change_evidence_digest: str,
) -> ApprovalBinding:
    """Bind a commit message to the exact current scope and review evidence."""

    _validate_pair(project, item)
    _require_result_type(item, COMMIT_PURPOSE)
    if not item.commit_message:
        raise ValidationError("commit approval binding requires a commit message")
    normalized_scope_digest = _required_digest(scope_digest, "scope_digest")
    normalized_review_digest = _required_digest(review_digest, "review_digest")
    normalized_evidence_digest = _required_digest(
        change_evidence_digest,
        "change_evidence_digest",
    )

    current_scope = _build_binding(SCOPE_PURPOSE, _scope_snapshot(project, item))
    if not digest_matches(current_scope, normalized_scope_digest):
        raise ValidationError("scope approval binding is stale")
    current_review = _build_binding(
        REVIEW_PURPOSE,
        _review_snapshot(
            project,
            item,
            scope_digest=current_scope.digest,
            change_evidence_digest=normalized_evidence_digest,
        ),
    )
    if not digest_matches(current_review, normalized_review_digest):
        raise ValidationError("review approval binding is stale")

    return _build_binding(
        COMMIT_PURPOSE,
        _commit_snapshot(
            project,
            item,
            scope_digest=current_scope.digest,
            review_digest=current_review.digest,
            change_evidence_digest=normalized_evidence_digest,
        ),
    )


def digest_matches(binding: ApprovalBinding, supplied_digest: str) -> bool:
    """Compare a supplied lowercase SHA-256 digest without treating it as secret."""

    if not isinstance(supplied_digest, str) or not _DIGEST_PATTERN.fullmatch(supplied_digest):
        return False
    return hmac.compare_digest(binding.digest, supplied_digest)


def approval_binding_blocking_reasons(
    project: ProjectCard,
    item: QueueItem,
) -> tuple[str, ...]:
    """Return fail-closed v0.1B-2 binding reasons for one normalized item."""

    _validate_pair(project, item)
    reasons: list[str] = []
    binding_fields = (
        item.scope_approval_digest,
        item.change_evidence_digest,
        item.review_approval_digest,
        item.commit_approval_digest,
    )

    if item.result_type in {"design", "blocked"}:
        if item.scope_approved or item.review_passed or item.commit_approved or any(binding_fields):
            reasons.append(
                f"approval binding metadata is not allowed for result_type={item.result_type}"
            )
        return tuple(reasons)

    scope_binding_valid = False
    if not item.scope_approved:
        if item.scope_approval_digest:
            reasons.append("scope approval digest exists without scope approval")
    else:
        current_scope = _build_binding(SCOPE_PURPOSE, _scope_snapshot(project, item))
        scope_binding_valid = _append_binding_match_reason(
            reasons,
            current_scope,
            item.scope_approval_digest,
            "scope approval",
        )

    if item.result_type == "implementation":
        if item.change_evidence_digest:
            reasons.append("change evidence digest is not allowed for implementation")
        if item.review_passed or item.review_approval_digest:
            reasons.append("review approval metadata is not allowed for implementation")
        if item.commit_approved or item.commit_approval_digest:
            reasons.append("commit approval metadata is not allowed for implementation")
        return tuple(reasons)

    evidence_digest = _validated_digest_reason(
        reasons,
        item.change_evidence_digest,
        "change evidence",
    )
    current_review: ApprovalBinding | None = None
    if evidence_digest and scope_binding_valid:
        current_review = _build_binding(
            REVIEW_PURPOSE,
            _review_snapshot(
                project,
                item,
                scope_digest=item.scope_approval_digest,
                change_evidence_digest=evidence_digest,
            ),
        )

    review_binding_valid = False
    if not item.review_passed:
        if item.review_approval_digest:
            reasons.append("review approval digest exists without a passed review")
    else:
        review_digest = _validated_digest_reason(
            reasons,
            item.review_approval_digest,
            "review approval",
        )
        if current_review is not None and review_digest:
            review_binding_valid = digest_matches(current_review, review_digest)
            if not review_binding_valid:
                reasons.append("review approval binding is stale")

    if item.result_type == "review":
        if item.commit_approved or item.commit_approval_digest:
            reasons.append("commit approval metadata is not allowed for review")
        return tuple(reasons)

    if not item.commit_approved:
        if item.commit_approval_digest:
            reasons.append("commit approval digest exists without commit approval")
    else:
        commit_digest = _validated_digest_reason(
            reasons,
            item.commit_approval_digest,
            "commit approval",
        )
        if not item.commit_message:
            reasons.append("commit approval binding requires a commit message")
        elif evidence_digest and scope_binding_valid and review_binding_valid and commit_digest:
            current_commit = _build_binding(
                COMMIT_PURPOSE,
                _commit_snapshot(
                    project,
                    item,
                    scope_digest=item.scope_approval_digest,
                    review_digest=item.review_approval_digest,
                    change_evidence_digest=evidence_digest,
                ),
            )
            if not digest_matches(current_commit, commit_digest):
                reasons.append("commit approval binding is stale")
    return tuple(reasons)


def _validated_digest_reason(
    reasons: list[str],
    value: str,
    label: str,
) -> str:
    if not value:
        reasons.append(f"{label} digest is missing")
        return ""
    if not _DIGEST_PATTERN.fullmatch(value):
        reasons.append(f"{label} digest is malformed")
        return ""
    return value


def _append_binding_match_reason(
    reasons: list[str],
    binding: ApprovalBinding,
    supplied_digest: str,
    label: str,
) -> bool:
    normalized_digest = _validated_digest_reason(reasons, supplied_digest, label)
    if not normalized_digest:
        return False
    if not digest_matches(binding, normalized_digest):
        reasons.append(f"{label} binding is stale")
        return False
    return True


def _scope_snapshot(project: ProjectCard, item: QueueItem) -> dict[str, Any]:
    return {
        "binding_type": BINDING_TYPE,
        "version": VERSION,
        "purpose": SCOPE_PURPOSE,
        "result_type": _PURPOSE_RESULT_TYPES[SCOPE_PURPOSE],
        "project": {
            "project_id": project.project_id,
            "repo_path": project.repo_path,
            "expected_branch": project.expected_branch,
            "expected_head": project.expected_head,
            "protected_paths": _sorted_paths(project.protected_paths),
            "expected_untracked": _sorted_paths(project.expected_untracked),
            "forbidden_actions": sorted(project.forbidden_actions),
            "validation_commands": list(project.validation_commands),
        },
        "item": {
            "item_id": item.item_id,
            "current_goal": item.current_goal,
            "current_task": item.current_task,
            "target_files": _sorted_paths(item.target_files),
        },
    }


def _review_snapshot(
    project: ProjectCard,
    item: QueueItem,
    *,
    scope_digest: str,
    change_evidence_digest: str,
) -> dict[str, Any]:
    return {
        "binding_type": BINDING_TYPE,
        "version": VERSION,
        "purpose": REVIEW_PURPOSE,
        "result_type": _PURPOSE_RESULT_TYPES[REVIEW_PURPOSE],
        "project_id": project.project_id,
        "item_id": item.item_id,
        "scope_digest": scope_digest,
        "change_evidence_digest": change_evidence_digest,
        "observed_branch": item.observed_branch,
        "observed_head": item.observed_head,
        "observed_git_status": sorted(item.observed_git_status, key=str.casefold),
    }


def _commit_snapshot(
    project: ProjectCard,
    item: QueueItem,
    *,
    scope_digest: str,
    review_digest: str,
    change_evidence_digest: str,
) -> dict[str, Any]:
    return {
        "binding_type": BINDING_TYPE,
        "version": VERSION,
        "purpose": COMMIT_PURPOSE,
        "result_type": _PURPOSE_RESULT_TYPES[COMMIT_PURPOSE],
        "project_id": project.project_id,
        "item_id": item.item_id,
        "scope_digest": scope_digest,
        "review_digest": review_digest,
        "change_evidence_digest": change_evidence_digest,
        "observed_branch": item.observed_branch,
        "observed_head": item.observed_head,
        "observed_git_status": sorted(item.observed_git_status, key=str.casefold),
        "commit_message": item.commit_message,
    }


def _build_binding(purpose: str, snapshot: dict[str, Any]) -> ApprovalBinding:
    try:
        canonical_bytes = json.dumps(
            snapshot,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValidationError("approval binding snapshot is not canonicalizable") from exc
    if len(canonical_bytes) > _MAX_CANONICAL_BYTES:
        raise ValidationError("approval binding snapshot is too large")
    digest = hashlib.sha256(_DOMAIN_PREFIXES[purpose] + canonical_bytes).hexdigest()
    return ApprovalBinding(
        purpose=purpose,
        digest=digest,
        canonical_bytes=canonical_bytes,
        byte_size=len(canonical_bytes),
    )


def _validate_pair(project: ProjectCard, item: QueueItem) -> None:
    if not isinstance(project, ProjectCard):
        raise ValidationError("project must be a normalized ProjectCard")
    if not isinstance(item, QueueItem):
        raise ValidationError("item must be a normalized QueueItem")
    if item.project_id != project.project_id:
        raise ValidationError("queue item does not belong to the supplied project")


def _require_result_type(item: QueueItem, purpose: str) -> None:
    expected = _PURPOSE_RESULT_TYPES[purpose]
    if item.result_type != expected:
        raise ValidationError(
            f"{purpose} approval binding requires result_type={expected}"
        )


def _required_digest(value: str, field: str) -> str:
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise ValidationError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _sorted_paths(paths: tuple[str, ...]) -> list[str]:
    return sorted(paths, key=lambda value: value.replace("\\", "/").casefold())
