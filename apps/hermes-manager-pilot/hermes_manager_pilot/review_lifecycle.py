"""Local-only Durable Review Save/Reopen/Delete lifecycle v0.1C.

The service binds short-lived, single-use confirmations to one browser session
and one immutable Review record. It does not expose HTTP routes itself, call
external services, run commands, grant review/commit/push authority, or perform
automatic cleanup.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Any

from .review_record import (
    PROJECT_ID,
    ReviewRecord,
    ReviewRecordError,
    create_review_record,
    evaluate_review_record_freshness,
    normalize_review_git_snapshot,
    normalize_review_record_candidate,
    review_record_digest,
    review_record_to_dict,
)
from .review_store import (
    RETENTION_POLICY,
    ReviewStoreError,
    delete_review_record,
    list_review_records,
    read_review_record,
    write_review_record,
)
from .schemas import ValidationError, normalize_session_state


VERSION = "0.1C"
CONFIRMATION_TTL_SECONDS = 5 * 60
MAX_PENDING_CONFIRMATIONS = 64
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class ReviewLifecycleError(ValueError):
    """A fixed-category lifecycle failure with an optional safe Review ID."""

    def __init__(self, code: str, *, review_id: str | None = None) -> None:
        self.code = code
        self.review_id = review_id
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ReviewSavePreview:
    """One exact write-free Review save preview."""

    version: str
    confirmation_token: str
    expires_in_seconds: int
    record_digest: str
    retention_policy: str
    local_only: bool
    encrypted: bool
    cloud_synced: bool
    record: ReviewRecord


@dataclass(frozen=True, slots=True)
class ReviewDeletePreview:
    """One exact write-free deletion preview without result text."""

    version: str
    confirmation_token: str
    expires_in_seconds: int
    record_digest: str
    confirmation_text: str
    review_id: str
    created_at: str
    active_task: str
    branch: str
    head: str
    target_count: int


@dataclass(frozen=True, slots=True)
class ReviewRecoveryInspection:
    """Read-only exact-ID recovery state; never repairs or deletes data."""

    version: str
    review_id: str
    status: str
    blocking_reason: str
    record: ReviewRecord | None


@dataclass(frozen=True, slots=True)
class _PendingConfirmation:
    operation: str
    session_id: str
    expires_at: float
    record_digest: str
    record: ReviewRecord


class ReviewLifecycleService:
    """Coordinate one local Review lifecycle with no background activity."""

    def __init__(
        self,
        *,
        trusted_repo_root: Path | str,
        git_snapshot_loader: Callable[[], Mapping[str, Any]],
        store_kwargs: Mapping[str, Any] | None = None,
        record_id_generator: Callable[[], str] | None = None,
        record_clock: Callable[[], datetime] | None = None,
        token_generator: Callable[[], str] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self._trusted_repo_root = Path(trusted_repo_root).resolve(strict=False)
        self._git_snapshot_loader = git_snapshot_loader
        self._store_kwargs = dict(store_kwargs or {})
        self._record_id_generator = record_id_generator
        self._record_clock = record_clock
        self._token_generator = token_generator or (lambda: secrets.token_urlsafe(32))
        self._monotonic_clock = monotonic_clock or time.monotonic
        self._pending: dict[str, _PendingConfirmation] = {}
        self._lock = threading.RLock()

    def prepare_save(
        self,
        session_data: Mapping[str, Any],
        result_summary: str,
        *,
        scope_confirmed: bool,
        privacy_acknowledged: bool,
        retention_acknowledged: bool,
        session_id: str,
    ) -> ReviewSavePreview:
        """Create a write-free preview and one Save-only confirmation token."""

        self._require_session_id(session_id)
        if scope_confirmed is not True:
            raise ReviewLifecycleError("review_scope_not_confirmed")
        if privacy_acknowledged is not True:
            raise ReviewLifecycleError("review_privacy_not_acknowledged")
        if retention_acknowledged is not True:
            raise ReviewLifecycleError("review_retention_not_acknowledged")
        try:
            session = normalize_session_state({**session_data, "push_allowed": False})
        except (TypeError, ValidationError):
            raise ReviewLifecycleError("review_session_invalid") from None
        if not self._same_path(session.repo, self._trusted_repo_root):
            raise ReviewLifecycleError("review_repository_not_trusted")
        try:
            snapshot = normalize_review_git_snapshot(
                self._git_snapshot_loader(),
                path="current review git snapshot",
            )
            candidate = normalize_review_record_candidate(
                {
                    "project_id": PROJECT_ID,
                    "git_snapshot": {
                        "branch": snapshot.branch,
                        "head": snapshot.head,
                        "status": list(snapshot.status),
                    },
                    "current_goal": session.current_goal,
                    "active_task": session.active_task,
                    "target_files": list(session.target_files),
                    "validation_commands": list(session.validation_commands),
                    "last_codex_prompt_summary": session.last_codex_prompt,
                    "result_summary": result_summary,
                    "privacy_reviewed": True,
                }
            )
            record = create_review_record(
                candidate,
                id_generator=self._record_id_generator,
                clock=self._record_clock,
            )
        except (ReviewRecordError, TypeError):
            raise ReviewLifecycleError("review_save_candidate_invalid") from None
        digest = review_record_digest(record)
        token = self._issue_confirmation("save", session_id, record, digest)
        return ReviewSavePreview(
            version=VERSION,
            confirmation_token=token,
            expires_in_seconds=CONFIRMATION_TTL_SECONDS,
            record_digest=digest,
            retention_policy=RETENTION_POLICY,
            local_only=True,
            encrypted=False,
            cloud_synced=False,
            record=record,
        )

    def confirm_save(self, confirmation_token: str, *, session_id: str) -> dict[str, Any]:
        """Write the exact previewed record if its Git snapshot is still current."""

        pending = self._claim_confirmation("save", confirmation_token, session_id)
        try:
            current = normalize_review_git_snapshot(
                self._git_snapshot_loader(),
                path="current review git snapshot",
            )
            freshness = evaluate_review_record_freshness(pending.record, current)
        except ReviewRecordError:
            raise ReviewLifecycleError("review_save_snapshot_invalid") from None
        if not freshness.matches:
            raise ReviewLifecycleError("review_save_snapshot_stale")
        try:
            receipt = write_review_record(pending.record, **self._store_kwargs)
        except ReviewStoreError as exc:
            if exc.code in {
                "review_record_write_failed",
                "review_record_write_outcome_uncertain",
                "review_record_exists",
            }:
                raise ReviewLifecycleError(
                    "review_save_outcome_uncertain",
                    review_id=pending.record.review_id,
                ) from None
            raise ReviewLifecycleError(exc.code) from None
        return {
            "version": VERSION,
            "stored": receipt.stored,
            "review_id": receipt.review_id,
            "created_at": receipt.created_at,
            "retention_policy": receipt.retention_policy,
        }

    def list_saved(self) -> dict[str, Any]:
        """Return the existing bounded, result-free Review listing."""

        try:
            listing = list_review_records(**self._store_kwargs)
        except ReviewStoreError as exc:
            raise ReviewLifecycleError(exc.code) from None
        return {
            "version": VERSION,
            "records": [asdict(record) for record in listing.records],
            "count": listing.count,
            "capacity": listing.capacity,
            "retention_policy": listing.retention_policy,
        }

    def reopen(self, review_id: str) -> ReviewRecord:
        """Read one immutable record without changing workflow authority."""

        try:
            return read_review_record(review_id, **self._store_kwargs)
        except ReviewStoreError as exc:
            raise ReviewLifecycleError(exc.code) from None

    def inspect_recovery(self, review_id: str) -> ReviewRecoveryInspection:
        """Inspect one exact ID without retrying, repairing, or deleting it."""

        try:
            record = read_review_record(review_id, **self._store_kwargs)
        except ReviewStoreError as exc:
            if exc.code == "review_id_invalid":
                raise ReviewLifecycleError(exc.code) from None
            if exc.code == "review_record_not_found":
                return ReviewRecoveryInspection(VERSION, review_id, "absent", "", None)
            if exc.code == "review_record_corrupt":
                return ReviewRecoveryInspection(
                    VERSION,
                    review_id,
                    "present_corrupt",
                    "manual_recovery_required",
                    None,
                )
            return ReviewRecoveryInspection(
                VERSION,
                review_id,
                "store_unavailable",
                exc.code,
                None,
            )
        return ReviewRecoveryInspection(VERSION, review_id, "present_valid", "", record)

    def prepare_delete(self, review_id: str, *, session_id: str) -> ReviewDeletePreview:
        """Create a result-free exact-ID deletion preview and Delete-only token."""

        self._require_session_id(session_id)
        record = self.reopen(review_id)
        digest = review_record_digest(record)
        token = self._issue_confirmation("delete", session_id, record, digest)
        return ReviewDeletePreview(
            version=VERSION,
            confirmation_token=token,
            expires_in_seconds=CONFIRMATION_TTL_SECONDS,
            record_digest=digest,
            confirmation_text=f"DELETE {record.review_id}",
            review_id=record.review_id,
            created_at=record.created_at,
            active_task=record.active_task,
            branch=record.git_snapshot.branch,
            head=record.git_snapshot.head,
            target_count=len(record.target_files),
        )

    def confirm_delete(
        self,
        confirmation_token: str,
        confirmation_text: str,
        *,
        session_id: str,
    ) -> dict[str, Any]:
        """Delete the one unchanged record bound to an exact human confirmation."""

        pending = self._claim_confirmation("delete", confirmation_token, session_id)
        if confirmation_text != f"DELETE {pending.record.review_id}":
            raise ReviewLifecycleError("review_delete_confirmation_mismatch")
        try:
            receipt = delete_review_record(
                pending.record.review_id,
                pending.record_digest,
                **self._store_kwargs,
            )
        except ReviewStoreError as exc:
            raise ReviewLifecycleError(exc.code) from None
        return {
            "version": VERSION,
            "operation": "exact_delete",
            "deleted": receipt.deleted,
            "review_id": receipt.review_id,
            "previous_created_at": receipt.previous_created_at,
            "retention_policy": receipt.retention_policy,
        }

    def _issue_confirmation(
        self,
        operation: str,
        session_id: str,
        record: ReviewRecord,
        digest: str,
    ) -> str:
        with self._lock:
            now = self._monotonic_clock()
            self._purge_expired(now)
            if len(self._pending) >= MAX_PENDING_CONFIRMATIONS:
                raise ReviewLifecycleError("review_confirmation_capacity_reached")
            for _ in range(8):
                token = str(self._token_generator()).strip()
                if not _TOKEN_PATTERN.fullmatch(token):
                    raise ReviewLifecycleError("review_confirmation_generation_failed")
                if token not in self._pending:
                    self._pending[token] = _PendingConfirmation(
                        operation=operation,
                        session_id=session_id,
                        expires_at=now + CONFIRMATION_TTL_SECONDS,
                        record_digest=digest,
                        record=record,
                    )
                    return token
            raise ReviewLifecycleError("review_confirmation_generation_failed")

    def _claim_confirmation(
        self,
        operation: str,
        confirmation_token: str,
        session_id: str,
    ) -> _PendingConfirmation:
        self._require_session_id(session_id)
        if not isinstance(confirmation_token, str) or not _TOKEN_PATTERN.fullmatch(
            confirmation_token
        ):
            raise ReviewLifecycleError("review_confirmation_invalid")
        with self._lock:
            now = self._monotonic_clock()
            pending = self._pending.pop(confirmation_token, None)
            self._purge_expired(now)
        if pending is None or pending.expires_at < now:
            raise ReviewLifecycleError("review_confirmation_expired_or_unknown")
        if pending.operation != operation or pending.session_id != session_id:
            raise ReviewLifecycleError("review_confirmation_scope_mismatch")
        return pending

    def _purge_expired(self, now: float) -> None:
        for token in tuple(self._pending):
            if self._pending[token].expires_at < now:
                del self._pending[token]

    @staticmethod
    def _require_session_id(session_id: str) -> None:
        if not isinstance(session_id, str) or not _TOKEN_PATTERN.fullmatch(session_id):
            raise ReviewLifecycleError("local_session_invalid")

    @staticmethod
    def _same_path(value: str, expected: Path) -> bool:
        try:
            actual = Path(value).resolve(strict=False)
        except (OSError, RuntimeError, TypeError):
            return False
        return os.path.normcase(str(actual)) == os.path.normcase(str(expected))


def save_preview_to_dict(preview: ReviewSavePreview) -> dict[str, Any]:
    """Return a fresh transport mapping for one Save preview."""

    return {
        "version": preview.version,
        "confirmation_token": preview.confirmation_token,
        "expires_in_seconds": preview.expires_in_seconds,
        "record_digest": preview.record_digest,
        "retention_policy": preview.retention_policy,
        "local_only": preview.local_only,
        "encrypted": preview.encrypted,
        "cloud_synced": preview.cloud_synced,
        "record": review_record_to_dict(preview.record),
    }


def delete_preview_to_dict(preview: ReviewDeletePreview) -> dict[str, Any]:
    """Return a fresh result-free transport mapping for one Delete preview."""

    return asdict(preview)


def recovery_inspection_to_dict(inspection: ReviewRecoveryInspection) -> dict[str, Any]:
    """Return a fresh path-free transport mapping for one recovery inspection."""

    return {
        "version": inspection.version,
        "review_id": inspection.review_id,
        "status": inspection.status,
        "blocking_reason": inspection.blocking_reason,
        "record": (
            None if inspection.record is None else review_record_to_dict(inspection.record)
        ),
    }
