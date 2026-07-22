"""Bounded local change-evidence collection and verification for v0.1C-0B.

The collector reads one explicitly trusted local Git root and exact target
files. It does not persist evidence, execute a prompt, or grant approval.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import threading
import time
from typing import Any

from .prompt_queue import ProjectCard, QueueItem
from .schemas import ValidationError


VERSION = "0.1C-0B"
EVIDENCE_TYPE = "hermes_local_change_evidence"
WHOLE_STATUS_VERSION = "0.1C-0C-1"
WHOLE_STATUS_EVIDENCE_TYPE = "hermes_whole_worktree_status_evidence"
WHOLE_STATUS_COVERAGE = "git-visible-whole-worktree"
REVIEW_BUNDLE_VERSION = "0.1C-0C-2"
REVIEW_BUNDLE_EVIDENCE_TYPE = "hermes_review_evidence_bundle"

MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_FILE_BYTES = 16 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 64 * 1024
MAX_CANONICAL_BYTES = 64 * 1024
GIT_TIMEOUT_SECONDS = 10
MAX_TARGET_FILES = 64
MAX_STATUS_ENTRIES = 128
MAX_EVIDENCE_TEXT_LENGTH = 4096

_DIGEST_PREFIX = b"jarvis-core/hermes/local-change-evidence/v0.1C-0B\x00"
_WHOLE_STATUS_DIGEST_PREFIX = (
    b"jarvis-core/hermes/whole-worktree-status-evidence/v0.1C-0C-1\x00"
)
_REVIEW_BUNDLE_DIGEST_PREFIX = (
    b"jarvis-core/hermes/review-evidence-bundle/v0.1C-0C-2\x00"
)
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_TRACKED_STATUS_CODES = frozenset(" MADRCU")
_GIT_BASE_ARGS = (
    "git",
    "--literal-pathspecs",
    "-c",
    "color.ui=false",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.hooksPath=NUL",
    "-c",
    "diff.external=",
    "-c",
    "status.renames=true",
)


@dataclass(frozen=True)
class TargetChangeEvidence:
    """One exact target's stable local state without its content."""

    path: str
    status: str
    kind: str
    byte_size: int
    content_sha256: str


@dataclass(frozen=True)
class LocalChangeEvidence:
    """A bounded local evidence manifest and domain-separated digest."""

    project_id: str
    item_id: str
    declared_repo_path: str
    repo_root: str
    branch: str
    head: str
    status_scope_paths: tuple[str, ...]
    scoped_git_status: tuple[str, ...]
    targets: tuple[TargetChangeEvidence, ...]
    change_evidence_digest: str
    canonical_bytes: bytes
    byte_size: int
    evidence_type: str = EVIDENCE_TYPE
    version: str = VERSION

    def snapshot(self) -> dict[str, Any]:
        """Return a new JSON-decoded copy of the canonical evidence manifest."""

        value = json.loads(self.canonical_bytes.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValidationError("change evidence snapshot must be an object")
        return value


@dataclass(frozen=True)
class WholeWorktreeStatusEvidence:
    """Bounded Git-visible status artifact that contains no file contents."""

    project_id: str
    item_id: str
    declared_repo_path: str
    repo_root: str
    branch: str
    head: str
    coverage: str
    whole_git_status: tuple[str, ...]
    status_evidence_digest: str
    canonical_bytes: bytes
    byte_size: int
    evidence_type: str = WHOLE_STATUS_EVIDENCE_TYPE
    version: str = WHOLE_STATUS_VERSION

    def snapshot(self) -> dict[str, Any]:
        """Return a new JSON-decoded copy of the canonical status manifest."""

        value = json.loads(self.canonical_bytes.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValidationError("whole-worktree status snapshot must be an object")
        return value


@dataclass(frozen=True)
class ReviewEvidenceBundle:
    """One bounded target/status bundle without queue or approval mutation."""

    project_id: str
    item_id: str
    declared_repo_path: str
    repo_root: str
    branch: str
    head: str
    target_evidence: LocalChangeEvidence
    whole_status_evidence: WholeWorktreeStatusEvidence
    bundle_digest: str
    canonical_bytes: bytes
    byte_size: int
    evidence_type: str = REVIEW_BUNDLE_EVIDENCE_TYPE
    version: str = REVIEW_BUNDLE_VERSION

    def snapshot(self) -> dict[str, Any]:
        """Return a new JSON-decoded copy of the canonical bundle manifest."""

        value = json.loads(self.canonical_bytes.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValidationError("review evidence bundle snapshot must be an object")
        return value


@dataclass(frozen=True)
class _RepositoryState:
    branch: str
    head: str
    status_entries: tuple[tuple[str, str], ...]

    @property
    def status_lines(self) -> tuple[str, ...]:
        return tuple(f"{code} {path}" for code, path in self.status_entries)


def collect_local_change_evidence(
    trusted_repo_root: str | Path,
    project: ProjectCard,
    item: QueueItem,
) -> LocalChangeEvidence:
    """Collect stable read-only evidence for exact review or commit targets."""

    _validate_project_item(project, item)
    root = _validated_git_root(trusted_repo_root, project)
    _validate_target_scope(root, project, item)

    status_paths = _status_scope_paths(item.target_files, project.expected_untracked)
    before = _collect_repository_state(root, status_paths)
    _validate_expected_project_state(project, before)
    _validate_status_entries(project, item, before.status_entries)

    first_targets = _collect_target_manifest(root, item.target_files, before.status_entries)
    middle = _collect_repository_state(root, status_paths)
    if middle != before:
        raise ValidationError("repository changed during evidence collection")

    second_targets = _collect_target_manifest(root, item.target_files, middle.status_entries)
    after = _collect_repository_state(root, status_paths)
    if after != before or second_targets != first_targets:
        raise ValidationError("repository changed during evidence collection")

    snapshot = _evidence_snapshot(
        project_id=project.project_id,
        item_id=item.item_id,
        declared_repo_path=_portable_declared_path(project.repo_path),
        repo_root=_portable_path(root),
        branch=before.branch,
        head=before.head,
        status_scope_paths=status_paths,
        scoped_git_status=before.status_lines,
        targets=first_targets,
    )
    canonical_bytes = _canonical_json_bytes(snapshot)
    digest = hashlib.sha256(_DIGEST_PREFIX + canonical_bytes).hexdigest()
    return LocalChangeEvidence(
        project_id=project.project_id,
        item_id=item.item_id,
        declared_repo_path=_portable_declared_path(project.repo_path),
        repo_root=_portable_path(root),
        branch=before.branch,
        head=before.head,
        status_scope_paths=status_paths,
        scoped_git_status=before.status_lines,
        targets=first_targets,
        change_evidence_digest=digest,
        canonical_bytes=canonical_bytes,
        byte_size=len(canonical_bytes),
    )


def collect_whole_worktree_status_evidence(
    trusted_repo_root: str | Path,
    project: ProjectCard,
    item: QueueItem,
) -> WholeWorktreeStatusEvidence:
    """Collect stable whole Git-visible status without returning file contents."""

    _validate_project_item(project, item)
    root = _validated_git_root(trusted_repo_root, project)
    _validate_declared_scope(project, item)

    before = _collect_whole_repository_state(root)
    _validate_expected_project_state(project, before)
    _validate_whole_status_entries(before.status_entries)
    after = _collect_whole_repository_state(root)
    if after != before:
        raise ValidationError("repository changed during whole-status collection")

    snapshot = _whole_status_snapshot(
        project_id=project.project_id,
        item_id=item.item_id,
        declared_repo_path=_portable_declared_path(project.repo_path),
        repo_root=_portable_path(root),
        branch=before.branch,
        head=before.head,
        coverage=WHOLE_STATUS_COVERAGE,
        whole_git_status=before.status_lines,
    )
    canonical_bytes = _canonical_json_bytes(snapshot)
    digest = hashlib.sha256(_WHOLE_STATUS_DIGEST_PREFIX + canonical_bytes).hexdigest()
    return WholeWorktreeStatusEvidence(
        project_id=project.project_id,
        item_id=item.item_id,
        declared_repo_path=_portable_declared_path(project.repo_path),
        repo_root=_portable_path(root),
        branch=before.branch,
        head=before.head,
        coverage=WHOLE_STATUS_COVERAGE,
        whole_git_status=before.status_lines,
        status_evidence_digest=digest,
        canonical_bytes=canonical_bytes,
        byte_size=len(canonical_bytes),
    )


def collect_review_evidence_bundle(
    trusted_repo_root: str | Path,
    project: ProjectCard,
    item: QueueItem,
) -> ReviewEvidenceBundle:
    """Bind target content and whole status from one repeated collection window."""

    _validate_project_item(project, item)
    before = collect_whole_worktree_status_evidence(trusted_repo_root, project, item)
    first_target = collect_local_change_evidence(trusted_repo_root, project, item)
    middle = collect_whole_worktree_status_evidence(trusted_repo_root, project, item)
    if middle != before:
        raise ValidationError("repository changed during review evidence collection")
    second_target = collect_local_change_evidence(trusted_repo_root, project, item)
    after = collect_whole_worktree_status_evidence(trusted_repo_root, project, item)
    if after != before or second_target != first_target:
        raise ValidationError("repository changed during review evidence collection")
    _validate_target_and_whole_status_consistency(first_target, before)

    snapshot = _review_bundle_snapshot(
        project_id=project.project_id,
        item_id=item.item_id,
        declared_repo_path=before.declared_repo_path,
        repo_root=before.repo_root,
        branch=before.branch,
        head=before.head,
        target_evidence=first_target,
        whole_status_evidence=before,
    )
    canonical_bytes = _canonical_json_bytes(snapshot)
    digest = hashlib.sha256(_REVIEW_BUNDLE_DIGEST_PREFIX + canonical_bytes).hexdigest()
    return ReviewEvidenceBundle(
        project_id=project.project_id,
        item_id=item.item_id,
        declared_repo_path=before.declared_repo_path,
        repo_root=before.repo_root,
        branch=before.branch,
        head=before.head,
        target_evidence=first_target,
        whole_status_evidence=before,
        bundle_digest=digest,
        canonical_bytes=canonical_bytes,
        byte_size=len(canonical_bytes),
    )


def verify_local_change_evidence(
    evidence: LocalChangeEvidence,
    project: ProjectCard,
    item: QueueItem,
) -> None:
    """Verify structural integrity without proving provenance or authority."""

    if not isinstance(evidence, LocalChangeEvidence):
        raise ValidationError("evidence must be LocalChangeEvidence")
    _validate_project_item(project, item)
    _validate_evidence_shape(evidence)

    if evidence.evidence_type != EVIDENCE_TYPE or evidence.version != VERSION:
        raise ValidationError("change evidence type or version is unsupported")
    if evidence.project_id != project.project_id:
        raise ValidationError("change evidence project does not match project card")
    if evidence.item_id != item.item_id:
        raise ValidationError("change evidence item does not match queue item")
    _validate_local_absolute_root(project.repo_path, "project repo_path")
    expected_declared_path = _portable_declared_path(project.repo_path)
    if evidence.declared_repo_path != expected_declared_path:
        raise ValidationError("change evidence declared repo path does not match project")
    if evidence.branch != project.expected_branch:
        raise ValidationError("change evidence branch does not match expected branch")
    if evidence.head != project.expected_head:
        raise ValidationError("change evidence HEAD does not match expected HEAD")

    _validate_declared_scope(project, item)
    expected_scope = _status_scope_paths(item.target_files, project.expected_untracked)
    if evidence.status_scope_paths != expected_scope:
        raise ValidationError("change evidence status scope does not match queue item")
    expected_targets = tuple(sorted(item.target_files, key=_path_key))
    evidence_target_paths = tuple(target.path for target in evidence.targets)
    if evidence_target_paths != expected_targets:
        raise ValidationError("change evidence targets do not match queue item")

    status_entries = _parse_evidence_status_lines(evidence.scoped_git_status)
    state = _RepositoryState(
        branch=evidence.branch,
        head=evidence.head,
        status_entries=status_entries,
    )
    _validate_expected_project_state(project, state)
    _validate_status_entries(project, item, status_entries)
    _validate_target_evidence(evidence.targets, status_entries)

    expected_snapshot = _evidence_snapshot(
        project_id=evidence.project_id,
        item_id=evidence.item_id,
        declared_repo_path=evidence.declared_repo_path,
        repo_root=evidence.repo_root,
        branch=evidence.branch,
        head=evidence.head,
        status_scope_paths=evidence.status_scope_paths,
        scoped_git_status=evidence.scoped_git_status,
        targets=evidence.targets,
    )
    expected_canonical = _canonical_json_bytes(expected_snapshot)
    if evidence.byte_size != len(expected_canonical):
        raise ValidationError("change evidence byte size is inconsistent")
    if not hmac.compare_digest(evidence.canonical_bytes, expected_canonical):
        raise ValidationError("change evidence canonical manifest is inconsistent")
    expected_digest = hashlib.sha256(_DIGEST_PREFIX + expected_canonical).hexdigest()
    if not hmac.compare_digest(evidence.change_evidence_digest, expected_digest):
        raise ValidationError("change evidence digest is inconsistent")


def verify_whole_worktree_status_evidence(
    evidence: WholeWorktreeStatusEvidence,
    project: ProjectCard,
    item: QueueItem,
) -> None:
    """Verify whole-status structure without proving provenance or authority."""

    if not isinstance(evidence, WholeWorktreeStatusEvidence):
        raise ValidationError("evidence must be WholeWorktreeStatusEvidence")
    _validate_project_item(project, item)
    _validate_whole_status_evidence_shape(evidence)

    if (
        evidence.evidence_type != WHOLE_STATUS_EVIDENCE_TYPE
        or evidence.version != WHOLE_STATUS_VERSION
        or evidence.coverage != WHOLE_STATUS_COVERAGE
    ):
        raise ValidationError("whole-worktree status evidence metadata is unsupported")
    if evidence.project_id != project.project_id:
        raise ValidationError("whole-worktree status project does not match project card")
    if evidence.item_id != item.item_id:
        raise ValidationError("whole-worktree status item does not match queue item")
    _validate_local_absolute_root(project.repo_path, "project repo_path")
    if evidence.declared_repo_path != _portable_declared_path(project.repo_path):
        raise ValidationError("whole-worktree declared repo path does not match project")
    if evidence.branch != project.expected_branch:
        raise ValidationError("whole-worktree status branch does not match expected branch")
    if evidence.head != project.expected_head:
        raise ValidationError("whole-worktree status HEAD does not match expected HEAD")

    _validate_declared_scope(project, item)
    entries = _parse_evidence_status_lines(evidence.whole_git_status)
    state = _RepositoryState(
        branch=evidence.branch,
        head=evidence.head,
        status_entries=entries,
    )
    _validate_expected_project_state(project, state)
    _validate_whole_status_entries(entries)

    expected_snapshot = _whole_status_snapshot(
        project_id=evidence.project_id,
        item_id=evidence.item_id,
        declared_repo_path=evidence.declared_repo_path,
        repo_root=evidence.repo_root,
        branch=evidence.branch,
        head=evidence.head,
        coverage=evidence.coverage,
        whole_git_status=evidence.whole_git_status,
    )
    expected_canonical = _canonical_json_bytes(expected_snapshot)
    if evidence.byte_size != len(expected_canonical):
        raise ValidationError("whole-worktree status byte size is inconsistent")
    if not hmac.compare_digest(evidence.canonical_bytes, expected_canonical):
        raise ValidationError("whole-worktree status canonical manifest is inconsistent")
    expected_digest = hashlib.sha256(
        _WHOLE_STATUS_DIGEST_PREFIX + expected_canonical
    ).hexdigest()
    if not hmac.compare_digest(evidence.status_evidence_digest, expected_digest):
        raise ValidationError("whole-worktree status digest is inconsistent")


def verify_review_evidence_bundle(
    bundle: ReviewEvidenceBundle,
    project: ProjectCard,
    item: QueueItem,
) -> None:
    """Verify composite consistency without proving provenance or approval."""

    if not isinstance(bundle, ReviewEvidenceBundle):
        raise ValidationError("bundle must be ReviewEvidenceBundle")
    _validate_project_item(project, item)
    _validate_review_bundle_shape(bundle)

    if (
        bundle.evidence_type != REVIEW_BUNDLE_EVIDENCE_TYPE
        or bundle.version != REVIEW_BUNDLE_VERSION
    ):
        raise ValidationError("review evidence bundle metadata is unsupported")
    if bundle.project_id != project.project_id:
        raise ValidationError("review evidence bundle project does not match project card")
    if bundle.item_id != item.item_id:
        raise ValidationError("review evidence bundle item does not match queue item")
    _validate_local_absolute_root(project.repo_path, "project repo_path")
    if bundle.declared_repo_path != _portable_declared_path(project.repo_path):
        raise ValidationError("review evidence declared repo path does not match project")
    if bundle.branch != project.expected_branch:
        raise ValidationError("review evidence branch does not match expected branch")
    if bundle.head != project.expected_head:
        raise ValidationError("review evidence HEAD does not match expected HEAD")

    verify_local_change_evidence(bundle.target_evidence, project, item)
    verify_whole_worktree_status_evidence(bundle.whole_status_evidence, project, item)
    _validate_bundle_metadata_consistency(bundle)
    _validate_target_and_whole_status_consistency(
        bundle.target_evidence,
        bundle.whole_status_evidence,
    )

    expected_snapshot = _review_bundle_snapshot(
        project_id=bundle.project_id,
        item_id=bundle.item_id,
        declared_repo_path=bundle.declared_repo_path,
        repo_root=bundle.repo_root,
        branch=bundle.branch,
        head=bundle.head,
        target_evidence=bundle.target_evidence,
        whole_status_evidence=bundle.whole_status_evidence,
    )
    expected_canonical = _canonical_json_bytes(expected_snapshot)
    if bundle.byte_size != len(expected_canonical):
        raise ValidationError("review evidence bundle byte size is inconsistent")
    if not hmac.compare_digest(bundle.canonical_bytes, expected_canonical):
        raise ValidationError("review evidence bundle canonical manifest is inconsistent")
    expected_digest = hashlib.sha256(
        _REVIEW_BUNDLE_DIGEST_PREFIX + expected_canonical
    ).hexdigest()
    if not hmac.compare_digest(bundle.bundle_digest, expected_digest):
        raise ValidationError("review evidence bundle digest is inconsistent")


def _validate_project_item(project: ProjectCard, item: QueueItem) -> None:
    if not isinstance(project, ProjectCard):
        raise ValidationError("project must be a normalized ProjectCard")
    if not isinstance(item, QueueItem):
        raise ValidationError("item must be a normalized QueueItem")
    if item.project_id != project.project_id:
        raise ValidationError("queue item does not belong to the supplied project")
    if item.result_type not in {"review", "commit"}:
        raise ValidationError("local change evidence requires result_type=review or commit")
    if not item.target_files:
        raise ValidationError("local change evidence requires target files")


def _validate_evidence_shape(evidence: LocalChangeEvidence) -> None:
    text_fields = (
        (evidence.project_id, "project_id"),
        (evidence.item_id, "item_id"),
        (evidence.declared_repo_path, "declared_repo_path"),
        (evidence.repo_root, "repo_root"),
        (evidence.branch, "branch"),
        (evidence.head, "head"),
        (evidence.change_evidence_digest, "change_evidence_digest"),
        (evidence.evidence_type, "evidence_type"),
        (evidence.version, "version"),
    )
    for value, label in text_fields:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > MAX_EVIDENCE_TEXT_LENGTH
            or any(ord(character) < 32 for character in value)
        ):
            raise ValidationError(f"change evidence {label} is malformed")
    if not _DIGEST_PATTERN.fullmatch(evidence.change_evidence_digest):
        raise ValidationError("change evidence digest is malformed")
    _validate_local_absolute_root(
        evidence.declared_repo_path,
        "change evidence declared_repo_path",
    )
    _validate_local_absolute_root(evidence.repo_root, "change evidence repo_root")
    if not isinstance(evidence.canonical_bytes, bytes):
        raise ValidationError("change evidence canonical manifest must be bytes")
    if len(evidence.canonical_bytes) > MAX_CANONICAL_BYTES:
        raise ValidationError("change evidence canonical manifest exceeds limit")
    if (
        not isinstance(evidence.byte_size, int)
        or isinstance(evidence.byte_size, bool)
        or evidence.byte_size < 1
        or evidence.byte_size > MAX_CANONICAL_BYTES
    ):
        raise ValidationError("change evidence byte size is malformed")
    if not isinstance(evidence.status_scope_paths, tuple) or not isinstance(
        evidence.scoped_git_status, tuple
    ):
        raise ValidationError("change evidence status fields must be tuples")
    if not isinstance(evidence.targets, tuple):
        raise ValidationError("change evidence targets must be a tuple")
    if not evidence.targets or len(evidence.targets) > MAX_TARGET_FILES:
        raise ValidationError("change evidence target count is invalid")
    if any(not isinstance(target, TargetChangeEvidence) for target in evidence.targets):
        raise ValidationError("change evidence target is malformed")
    if (
        len(evidence.status_scope_paths) > MAX_STATUS_ENTRIES
        or len(evidence.scoped_git_status) > MAX_STATUS_ENTRIES
    ):
        raise ValidationError("change evidence status count exceeds limit")
    for path in evidence.status_scope_paths:
        _validate_relative_path(path)
    if len({_path_key(path) for path in evidence.status_scope_paths}) != len(
        evidence.status_scope_paths
    ):
        raise ValidationError("change evidence status scope contains duplicate paths")


def _validate_whole_status_evidence_shape(
    evidence: WholeWorktreeStatusEvidence,
) -> None:
    text_fields = (
        (evidence.project_id, "project_id"),
        (evidence.item_id, "item_id"),
        (evidence.declared_repo_path, "declared_repo_path"),
        (evidence.repo_root, "repo_root"),
        (evidence.branch, "branch"),
        (evidence.head, "head"),
        (evidence.coverage, "coverage"),
        (evidence.status_evidence_digest, "status_evidence_digest"),
        (evidence.evidence_type, "evidence_type"),
        (evidence.version, "version"),
    )
    for value, label in text_fields:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > MAX_EVIDENCE_TEXT_LENGTH
            or any(ord(character) < 32 for character in value)
        ):
            raise ValidationError(f"whole-worktree status {label} is malformed")
    if not _DIGEST_PATTERN.fullmatch(evidence.status_evidence_digest):
        raise ValidationError("whole-worktree status digest is malformed")
    _validate_local_absolute_root(
        evidence.declared_repo_path,
        "whole-worktree declared_repo_path",
    )
    _validate_local_absolute_root(evidence.repo_root, "whole-worktree repo_root")
    if not isinstance(evidence.canonical_bytes, bytes):
        raise ValidationError("whole-worktree status canonical manifest must be bytes")
    if len(evidence.canonical_bytes) > MAX_CANONICAL_BYTES:
        raise ValidationError("whole-worktree status canonical manifest exceeds limit")
    if (
        not isinstance(evidence.byte_size, int)
        or isinstance(evidence.byte_size, bool)
        or evidence.byte_size < 1
        or evidence.byte_size > MAX_CANONICAL_BYTES
    ):
        raise ValidationError("whole-worktree status byte size is malformed")
    if not isinstance(evidence.whole_git_status, tuple):
        raise ValidationError("whole-worktree Git status must be a tuple")
    if len(evidence.whole_git_status) > MAX_STATUS_ENTRIES:
        raise ValidationError("whole-worktree Git status count exceeds limit")


def _validate_review_bundle_shape(bundle: ReviewEvidenceBundle) -> None:
    text_fields = (
        (bundle.project_id, "project_id"),
        (bundle.item_id, "item_id"),
        (bundle.declared_repo_path, "declared_repo_path"),
        (bundle.repo_root, "repo_root"),
        (bundle.branch, "branch"),
        (bundle.head, "head"),
        (bundle.bundle_digest, "bundle_digest"),
        (bundle.evidence_type, "evidence_type"),
        (bundle.version, "version"),
    )
    for value, label in text_fields:
        if (
            not isinstance(value, str)
            or not value
            or len(value) > MAX_EVIDENCE_TEXT_LENGTH
            or any(ord(character) < 32 for character in value)
        ):
            raise ValidationError(f"review evidence bundle {label} is malformed")
    if not _DIGEST_PATTERN.fullmatch(bundle.bundle_digest):
        raise ValidationError("review evidence bundle digest is malformed")
    _validate_local_absolute_root(
        bundle.declared_repo_path,
        "review evidence declared_repo_path",
    )
    _validate_local_absolute_root(bundle.repo_root, "review evidence repo_root")
    if not isinstance(bundle.target_evidence, LocalChangeEvidence):
        raise ValidationError("review bundle target evidence is malformed")
    if not isinstance(bundle.whole_status_evidence, WholeWorktreeStatusEvidence):
        raise ValidationError("review bundle whole-status evidence is malformed")
    if not isinstance(bundle.canonical_bytes, bytes):
        raise ValidationError("review evidence bundle canonical manifest must be bytes")
    if len(bundle.canonical_bytes) > MAX_CANONICAL_BYTES:
        raise ValidationError("review evidence bundle canonical manifest exceeds limit")
    if (
        not isinstance(bundle.byte_size, int)
        or isinstance(bundle.byte_size, bool)
        or bundle.byte_size < 1
        or bundle.byte_size > MAX_CANONICAL_BYTES
    ):
        raise ValidationError("review evidence bundle byte size is malformed")


def _validate_bundle_metadata_consistency(bundle: ReviewEvidenceBundle) -> None:
    target = bundle.target_evidence
    whole = bundle.whole_status_evidence
    expected = (
        bundle.project_id,
        bundle.item_id,
        bundle.declared_repo_path,
        bundle.repo_root,
        bundle.branch,
        bundle.head,
    )
    target_metadata = (
        target.project_id,
        target.item_id,
        target.declared_repo_path,
        target.repo_root,
        target.branch,
        target.head,
    )
    whole_metadata = (
        whole.project_id,
        whole.item_id,
        whole.declared_repo_path,
        whole.repo_root,
        whole.branch,
        whole.head,
    )
    if target_metadata != expected or whole_metadata != expected:
        raise ValidationError("review evidence bundle metadata is inconsistent")


def _validate_target_and_whole_status_consistency(
    target: LocalChangeEvidence,
    whole: WholeWorktreeStatusEvidence,
) -> None:
    scoped_entries = _parse_evidence_status_lines(target.scoped_git_status)
    whole_entries = _parse_evidence_status_lines(whole.whole_git_status)
    scoped_by_path = {_path_key(path): code for code, path in scoped_entries}
    whole_by_path = {_path_key(path): code for code, path in whole_entries}
    for path in target.status_scope_paths:
        path_key = _path_key(path)
        if scoped_by_path.get(path_key, "  ") != whole_by_path.get(path_key, "  "):
            raise ValidationError(f"target and whole status disagree: {path}")
    for target_entry in target.targets:
        if target_entry.status != whole_by_path.get(_path_key(target_entry.path), "  "):
            raise ValidationError(
                f"target evidence and whole status disagree: {target_entry.path}"
            )


def _parse_evidence_status_lines(lines: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    encoded: list[bytes] = []
    for line in lines:
        if not isinstance(line, str) or len(line) > MAX_EVIDENCE_TEXT_LENGTH:
            raise ValidationError("change evidence Git status line is malformed")
        try:
            encoded.append(line.encode("utf-8", errors="strict") + b"\x00")
        except UnicodeEncodeError as exc:
            raise ValidationError("change evidence Git status line is malformed") from exc
    entries = _parse_porcelain_status(b"".join(encoded))
    canonical_lines = tuple(f"{code} {path}" for code, path in entries)
    if lines != canonical_lines:
        raise ValidationError("change evidence Git status is not canonical")
    return entries


def _validate_target_evidence(
    targets: tuple[TargetChangeEvidence, ...],
    status_entries: tuple[tuple[str, str], ...],
) -> None:
    status_by_path = {_path_key(path): code for code, path in status_entries}
    total_bytes = 0
    seen_paths: set[str] = set()
    for target in targets:
        if not isinstance(target, TargetChangeEvidence):
            raise ValidationError("change evidence target is malformed")
        _validate_relative_path(target.path)
        path_key = _path_key(target.path)
        if path_key in seen_paths:
            raise ValidationError("change evidence contains duplicate targets")
        seen_paths.add(path_key)
        if target.status != status_by_path.get(path_key, "  "):
            raise ValidationError(f"change evidence target status is inconsistent: {target.path}")
        if (
            not isinstance(target.byte_size, int)
            or isinstance(target.byte_size, bool)
            or target.byte_size < 0
            or target.byte_size > MAX_FILE_BYTES
        ):
            raise ValidationError(f"change evidence target size is invalid: {target.path}")
        if not isinstance(target.content_sha256, str):
            raise ValidationError(f"change evidence target digest is invalid: {target.path}")
        if target.kind == "file":
            if not _DIGEST_PATTERN.fullmatch(target.content_sha256) or "D" in target.status:
                raise ValidationError(
                    f"change evidence file target is inconsistent: {target.path}"
                )
        elif target.kind == "deleted":
            if target.byte_size != 0 or target.content_sha256 or "D" not in target.status:
                raise ValidationError(
                    f"change evidence deletion target is inconsistent: {target.path}"
                )
        else:
            raise ValidationError(f"change evidence target kind is unsupported: {target.path}")
        total_bytes += target.byte_size
        if total_bytes > MAX_TOTAL_FILE_BYTES:
            raise ValidationError("total target file size exceeds evidence limit")


def _validated_trusted_root(
    trusted_repo_root: str | Path,
    declared_repo_path: str,
) -> Path:
    root_text = str(trusted_repo_root).strip()
    if not root_text:
        raise ValidationError("trusted repo root is required")
    if _is_network_or_device_path(root_text):
        raise ValidationError("trusted repo root must be a local absolute path")
    root_path = Path(root_text)
    if not root_path.is_absolute():
        raise ValidationError("trusted repo root must be absolute")
    root = _resolve_directory(root_path, "trusted repo root")

    declared_text = str(declared_repo_path).strip()
    if _is_network_or_device_path(declared_text):
        raise ValidationError("project repo_path must be a local absolute path")
    declared_path = Path(declared_text)
    if not declared_path.is_absolute():
        raise ValidationError("project repo_path must be absolute for evidence collection")
    declared_root = _resolve_directory(declared_path, "project repo_path")
    if not _same_path(root, declared_root):
        raise ValidationError("trusted repo root does not match project repo_path")
    return root


def _validated_git_root(trusted_repo_root: str | Path, project: ProjectCard) -> Path:
    root = _validated_trusted_root(trusted_repo_root, project.repo_path)
    actual_top_level = _run_git_text(root, ("rev-parse", "--show-toplevel"))
    git_root = _resolve_directory(actual_top_level, "Git top-level")
    if not _same_path(root, git_root):
        raise ValidationError("trusted repo root does not match Git top-level")
    return root


def _validate_local_absolute_root(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a local absolute path")
    try:
        path = Path(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be a local absolute path") from exc
    if _is_network_or_device_path(value) or not path.is_absolute():
        raise ValidationError(f"{label} must be a local absolute path")


def _resolve_directory(value: str | Path, label: str) -> Path:
    path = Path(value)
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValidationError(f"{label} is not a readable directory") from exc
    if not resolved.is_dir():
        raise ValidationError(f"{label} is not a readable directory")
    if _is_reparse_or_symlink(path):
        raise ValidationError(f"{label} must not be a symlink or reparse point")
    return resolved


def _validate_target_scope(root: Path, project: ProjectCard, item: QueueItem) -> None:
    _validate_declared_scope(project, item)
    for relative_path in item.target_files:
        target_path = _validated_target_path(root, relative_path, allow_missing=True)
        if target_path.exists() and target_path.is_dir():
            raise ValidationError(f"target path must be a file: {relative_path}")
    for relative_path in project.expected_untracked:
        expected_path = _validated_target_path(root, relative_path, allow_missing=True)
        if expected_path.exists() and expected_path.is_dir():
            raise ValidationError(f"expected untracked path must be a file: {relative_path}")


def _validate_declared_scope(project: ProjectCard, item: QueueItem) -> None:
    for relative_path in item.target_files:
        _validate_relative_path(relative_path)
        if _path_is_protected(relative_path, project.protected_paths):
            raise ValidationError(f"target path is protected: {relative_path}")
    for relative_path in project.expected_untracked:
        _validate_relative_path(relative_path)


def _validated_target_path(root: Path, relative_path: str, allow_missing: bool) -> Path:
    _validate_relative_path(relative_path)
    candidate = root.joinpath(*relative_path.replace("\\", "/").split("/"))
    current = root
    parts = relative_path.replace("\\", "/").split("/")
    for index, part in enumerate(parts):
        current = current / part
        if not os.path.lexists(current):
            if allow_missing:
                break
            raise ValidationError(f"target path does not exist: {relative_path}")
        if _is_reparse_or_symlink(current):
            raise ValidationError(f"target path crosses a symlink or reparse point: {relative_path}")
        if index < len(parts) - 1 and not current.is_dir():
            raise ValidationError(f"target parent is not a directory: {relative_path}")
    try:
        resolved_parent = candidate.parent.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValidationError(f"target parent is not a readable directory: {relative_path}") from exc
    if not _is_within(root, resolved_parent):
        raise ValidationError(f"target path escapes trusted repo root: {relative_path}")
    return candidate


def _collect_repository_state(
    root: Path,
    status_paths: tuple[str, ...],
) -> _RepositoryState:
    branch = _run_git_text(root, ("rev-parse", "--abbrev-ref", "HEAD"))
    head = _run_git_text(root, ("rev-parse", "HEAD"))
    status_bytes = _run_git_bytes(
        root,
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            *status_paths,
        ),
    )
    entries = _parse_porcelain_status(status_bytes)
    return _RepositoryState(branch=branch, head=head, status_entries=entries)


def _collect_whole_repository_state(root: Path) -> _RepositoryState:
    branch = _run_git_text(root, ("rev-parse", "--abbrev-ref", "HEAD"))
    head = _run_git_text(root, ("rev-parse", "HEAD"))
    status_bytes = _run_git_bytes(
        root,
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ),
    )
    entries = _parse_porcelain_status(status_bytes)
    return _RepositoryState(branch=branch, head=head, status_entries=entries)


def _validate_expected_project_state(project: ProjectCard, state: _RepositoryState) -> None:
    if state.branch != project.expected_branch:
        raise ValidationError("collected branch does not match expected branch")
    if state.head != project.expected_head:
        raise ValidationError("collected HEAD does not match expected HEAD")
    untracked = {_path_key(path) for code, path in state.status_entries if code == "??"}
    for expected_path in project.expected_untracked:
        if _path_key(expected_path) not in untracked:
            raise ValidationError(f"expected untracked path is missing: {expected_path}")


def _validate_whole_status_entries(entries: tuple[tuple[str, str], ...]) -> None:
    for code, path in entries:
        if code != "??" and code[0] != " ":
            raise ValidationError(f"staged changes are not allowed in whole status: {path}")
        if "U" in code or code in {"AA", "DD"}:
            raise ValidationError(f"conflicted changes are not allowed in whole status: {path}")
        if "R" in code or "C" in code:
            raise ValidationError(f"rename/copy changes are not allowed in whole status: {path}")


def _validate_status_entries(
    project: ProjectCard,
    item: QueueItem,
    entries: tuple[tuple[str, str], ...],
) -> None:
    targets = {_path_key(path) for path in item.target_files}
    expected_untracked = {_path_key(path) for path in project.expected_untracked}
    for code, path in entries:
        path_key = _path_key(path)
        if code != "??" and code[0] != " ":
            raise ValidationError(f"staged target changes are not allowed: {path}")
        if "U" in code or code in {"AA", "DD"}:
            raise ValidationError(f"conflicted target changes are not allowed: {path}")
        if "R" in code or "C" in code:
            raise ValidationError(f"renamed or copied target changes are not allowed: {path}")
        if _path_is_protected(path, project.protected_paths) and path_key not in expected_untracked:
            raise ValidationError(f"protected path appears in change evidence: {path}")
        if path_key not in targets and path_key not in expected_untracked:
            raise ValidationError(f"status path is outside evidence scope: {path}")
        if code == "??" and path_key not in targets and path_key not in expected_untracked:
            raise ValidationError(f"unexpected untracked path in evidence scope: {path}")


def _collect_target_manifest(
    root: Path,
    target_files: tuple[str, ...],
    status_entries: tuple[tuple[str, str], ...],
) -> tuple[TargetChangeEvidence, ...]:
    status_by_path = {_path_key(path): code for code, path in status_entries}
    targets: list[TargetChangeEvidence] = []
    total_bytes = 0
    for relative_path in sorted(target_files, key=_path_key):
        target_path = _validated_target_path(root, relative_path, allow_missing=True)
        status_code = status_by_path.get(_path_key(relative_path), "  ")
        if not target_path.exists():
            if "D" not in status_code:
                raise ValidationError(f"missing target is not a Git deletion: {relative_path}")
            targets.append(
                TargetChangeEvidence(
                    path=relative_path,
                    status=status_code,
                    kind="deleted",
                    byte_size=0,
                    content_sha256="",
                )
            )
            continue
        if target_path.is_dir():
            raise ValidationError(f"target path must be a file: {relative_path}")
        content_digest, byte_size = _hash_stable_file(target_path, relative_path)
        total_bytes += byte_size
        if total_bytes > MAX_TOTAL_FILE_BYTES:
            raise ValidationError("total target file size exceeds evidence limit")
        targets.append(
            TargetChangeEvidence(
                path=relative_path,
                status=status_code,
                kind="file",
                byte_size=byte_size,
                content_sha256=content_digest,
            )
        )
    return tuple(targets)


def _hash_stable_file(path: Path, relative_path: str) -> tuple[str, int]:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValidationError(f"target file is not readable: {relative_path}") from exc
    if not stat.S_ISREG(before.st_mode) or _stat_is_reparse(before):
        raise ValidationError(f"target path must be a regular non-reparse file: {relative_path}")
    if before.st_size > MAX_FILE_BYTES:
        raise ValidationError(f"target file exceeds evidence size limit: {relative_path}")

    digest = hashlib.sha256()
    byte_count = 0
    try:
        with path.open("rb") as source:
            opened = os.fstat(source.fileno())
            if not _same_file_stat(before, opened):
                raise ValidationError(f"target file changed before evidence read: {relative_path}")
            while True:
                chunk = source.read(64 * 1024)
                if not chunk:
                    break
                byte_count += len(chunk)
                if byte_count > MAX_FILE_BYTES:
                    raise ValidationError(f"target file exceeds evidence size limit: {relative_path}")
                digest.update(chunk)
            after = os.fstat(source.fileno())
    except ValidationError:
        raise
    except OSError as exc:
        raise ValidationError(f"target file is not readable: {relative_path}") from exc
    if byte_count != before.st_size or not _same_file_stat(opened, after):
        raise ValidationError(f"target file changed during evidence read: {relative_path}")
    return digest.hexdigest(), byte_count


def _parse_porcelain_status(raw: bytes) -> tuple[tuple[str, str], ...]:
    if not raw:
        return ()
    records = raw.split(b"\x00")
    if records[-1] != b"":
        raise ValidationError("Git status output is not NUL terminated")
    records.pop()
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4 or record[2:3] != b" ":
            raise ValidationError("Git status output is malformed")
        try:
            code = record[:2].decode("ascii", errors="strict")
            path = record[3:].decode("utf-8", errors="strict").replace("\\", "/")
        except UnicodeDecodeError as exc:
            raise ValidationError("Git status contains a non-UTF-8 path") from exc
        if code != "??" and (
            code == "  " or any(character not in _TRACKED_STATUS_CODES for character in code)
        ):
            raise ValidationError(f"unsupported Git status code: {code!r}")
        _validate_relative_path(path)
        if "R" in code or "C" in code:
            if index >= len(records):
                raise ValidationError("Git rename status is malformed")
            index += 1
        entries.append((code, path))
    entries.sort(key=lambda entry: (_path_key(entry[1]), entry[0]))
    if len(entries) > 128:
        raise ValidationError("Git status contains too many evidence entries")
    return tuple(entries)


def _run_git_text(root: Path, args: tuple[str, ...]) -> str:
    raw = _run_git_bytes(root, args)
    try:
        return raw.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise ValidationError("Git output is not valid UTF-8") from exc


def _run_git_bytes(root: Path, args: tuple[str, ...]) -> bytes:
    command = (*_GIT_BASE_ARGS, *args)
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=_sanitized_git_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as exc:
        raise ValidationError("read-only Git evidence command failed") from exc
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise ValidationError("read-only Git evidence command failed")

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    overflow = threading.Event()
    reader_errors: list[Exception] = []

    stdout_thread = threading.Thread(
        target=_read_bounded_pipe,
        args=(process.stdout, stdout_chunks, overflow, reader_errors),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_bounded_pipe,
        args=(process.stderr, stderr_chunks, overflow, reader_errors),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    deadline = time.monotonic() + GIT_TIMEOUT_SECONDS
    timed_out = False
    while process.poll() is None:
        if overflow.wait(timeout=0.01):
            _kill_process(process)
            break
        if time.monotonic() >= deadline:
            timed_out = True
            _kill_process(process)
            break
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        _kill_process(process)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired as exc:
            raise ValidationError("read-only Git evidence command failed to stop") from exc
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)

    if timed_out:
        raise ValidationError("read-only Git evidence command timed out")
    if overflow.is_set():
        raise ValidationError("Git evidence output exceeds limit")
    if stdout_thread.is_alive() or stderr_thread.is_alive() or reader_errors:
        raise ValidationError("read-only Git evidence command failed")

    stdout = b"".join(stdout_chunks)
    stderr = b"".join(stderr_chunks)
    if process.returncode != 0:
        error = stderr.decode("utf-8", errors="replace").strip()
        raise ValidationError(f"read-only Git evidence command failed: {error[:240]}")
    return stdout


def _read_bounded_pipe(
    pipe: Any,
    chunks: list[bytes],
    overflow: threading.Event,
    errors: list[Exception],
) -> None:
    total = 0
    try:
        while not overflow.is_set():
            remaining = MAX_GIT_OUTPUT_BYTES - total
            chunk = pipe.read(min(64 * 1024, remaining + 1))
            if not chunk:
                break
            if len(chunk) > remaining:
                overflow.set()
                return
            chunks.append(chunk)
            total += len(chunk)
    except Exception as exc:
        errors.append(exc)
    finally:
        try:
            pipe.close()
        except OSError:
            pass


def _kill_process(process: subprocess.Popen[bytes]) -> None:
    try:
        process.kill()
    except OSError:
        pass


def _sanitized_git_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _status_scope_paths(
    target_files: tuple[str, ...],
    expected_untracked: tuple[str, ...],
) -> tuple[str, ...]:
    unique = {_path_key(path): path for path in (*target_files, *expected_untracked)}
    return tuple(unique[key] for key in sorted(unique))


def _evidence_snapshot(
    *,
    project_id: str,
    item_id: str,
    declared_repo_path: str,
    repo_root: str,
    branch: str,
    head: str,
    status_scope_paths: tuple[str, ...],
    scoped_git_status: tuple[str, ...],
    targets: tuple[TargetChangeEvidence, ...],
) -> dict[str, Any]:
    return {
        "evidence_type": EVIDENCE_TYPE,
        "version": VERSION,
        "project_id": project_id,
        "item_id": item_id,
        "declared_repo_path": declared_repo_path,
        "repo_root": repo_root,
        "branch": branch,
        "head": head,
        "status_scope_paths": list(status_scope_paths),
        "scoped_git_status": list(scoped_git_status),
        "targets": [
            {
                "path": target.path,
                "status": target.status,
                "kind": target.kind,
                "byte_size": target.byte_size,
                "content_sha256": target.content_sha256,
            }
            for target in targets
        ],
    }


def _whole_status_snapshot(
    *,
    project_id: str,
    item_id: str,
    declared_repo_path: str,
    repo_root: str,
    branch: str,
    head: str,
    coverage: str,
    whole_git_status: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "evidence_type": WHOLE_STATUS_EVIDENCE_TYPE,
        "version": WHOLE_STATUS_VERSION,
        "project_id": project_id,
        "item_id": item_id,
        "declared_repo_path": declared_repo_path,
        "repo_root": repo_root,
        "branch": branch,
        "head": head,
        "coverage": coverage,
        "whole_git_status": list(whole_git_status),
    }


def _review_bundle_snapshot(
    *,
    project_id: str,
    item_id: str,
    declared_repo_path: str,
    repo_root: str,
    branch: str,
    head: str,
    target_evidence: LocalChangeEvidence,
    whole_status_evidence: WholeWorktreeStatusEvidence,
) -> dict[str, Any]:
    return {
        "evidence_type": REVIEW_BUNDLE_EVIDENCE_TYPE,
        "version": REVIEW_BUNDLE_VERSION,
        "project_id": project_id,
        "item_id": item_id,
        "declared_repo_path": declared_repo_path,
        "repo_root": repo_root,
        "branch": branch,
        "head": head,
        "target_evidence": {
            "evidence_type": target_evidence.evidence_type,
            "version": target_evidence.version,
            "digest": target_evidence.change_evidence_digest,
        },
        "whole_status_evidence": {
            "evidence_type": whole_status_evidence.evidence_type,
            "version": whole_status_evidence.version,
            "coverage": whole_status_evidence.coverage,
            "digest": whole_status_evidence.status_evidence_digest,
        },
    }


def _canonical_json_bytes(snapshot: dict[str, Any]) -> bytes:
    try:
        canonical = json.dumps(
            snapshot,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValidationError("change evidence snapshot is not canonicalizable") from exc
    if len(canonical) > MAX_CANONICAL_BYTES:
        raise ValidationError("change evidence snapshot exceeds limit")
    return canonical


def _validate_relative_path(value: str) -> None:
    if not isinstance(value, str):
        raise ValidationError("evidence path must be a string")
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    if (
        not normalized
        or normalized.startswith("/")
        or ":" in normalized
        or any(character in normalized for character in '*?<>|"')
        or any(ord(character) < 32 for character in normalized)
        or any(part in {"", ".", ".."} for part in parts)
        or any(part.casefold() == ".git" for part in parts)
        or any(part != part.rstrip(" .") for part in parts)
        or any(_is_windows_reserved_name(part) for part in parts)
    ):
        raise ValidationError(f"evidence path must be repository-relative: {value!r}")


def _same_file_stat(first: os.stat_result, second: os.stat_result) -> bool:
    return (
        first.st_dev,
        first.st_ino,
        first.st_size,
        first.st_mtime_ns,
        first.st_mode,
    ) == (
        second.st_dev,
        second.st_ino,
        second.st_size,
        second.st_mtime_ns,
        second.st_mode,
    )


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        info = path.stat(follow_symlinks=False)
    except OSError:
        return False
    return stat.S_ISLNK(info.st_mode) or _stat_is_reparse(info)


def _stat_is_reparse(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _path_key(value: str) -> str:
    return value.replace("\\", "/").casefold()


def _path_is_protected(value: str, protected_paths: tuple[str, ...]) -> bool:
    value_key = _path_key(value)
    return any(
        value_key == protected_key or value_key.startswith(protected_key.rstrip("/") + "/")
        for protected_key in (_path_key(path) for path in protected_paths)
    )


def _is_windows_reserved_name(part: str) -> bool:
    stem = part.split(".", 1)[0].casefold()
    return stem in {"con", "prn", "aux", "nul"} or (
        len(stem) == 4
        and stem[:3] in {"com", "lpt"}
        and stem[3] in "123456789"
    )


def _is_network_or_device_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return normalized.startswith("//")


def _portable_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _portable_declared_path(value: str) -> str:
    return _portable_path(Path(value))
