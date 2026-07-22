"""Transport-neutral Durable Review Record v0.1A core contract.

This module normalizes in-memory data only. It does not read a repository,
persist state, expose routes, use the clipboard, call external services, or
grant review, commit, push, or execution authority.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from typing import Any
import uuid


CONTRACT_TYPE = "hermes_review_record"
VERSION = "0.1A"
PROJECT_ID = "jarvis-core"
AUTHORITY_BOUNDARY = "review_input_only"
PROTECTED_UNTRACKED_PATH = "jarvis.bat"

MAX_JSON_BYTES = 64 * 1024
MAX_TEXT_CHARS = 1000
MAX_SUMMARY_CHARS = 1200
MAX_COMMAND_CHARS = 1000
MAX_PATH_CHARS = 512
MAX_TARGET_FILES = 64
MAX_VALIDATION_COMMANDS = 32
MAX_STATUS_LINES = 128

_REVIEW_ID_PATTERN = re.compile(r"^review_[0-9a-f]{24}$")
_GIT_HEAD_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_TRACKED_STATUS_CODES = frozenset(" MADRCU")

_GIT_SNAPSHOT_FIELDS = frozenset({"branch", "head", "status"})
_CANDIDATE_FIELDS = frozenset(
    {
        "project_id",
        "git_snapshot",
        "current_goal",
        "active_task",
        "target_files",
        "validation_commands",
        "last_codex_prompt_summary",
        "result_summary",
        "privacy_reviewed",
    }
)
_RECORD_FIELDS = _CANDIDATE_FIELDS | frozenset(
    {
        "contract_type",
        "version",
        "review_id",
        "created_at",
        "authority_boundary",
        "read_only",
        "review_passed",
        "commit_approved",
        "push_allowed",
    }
)


class ReviewRecordError(ValueError):
    """Raised when Review Record input fails closed."""


@dataclass(frozen=True, slots=True)
class ReviewGitSnapshot:
    """One caller-supplied, bounded Git snapshot with no filesystem authority."""

    branch: str
    head: str
    status: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewRecordCandidate:
    """One normalized result proposed for a future durable Review record."""

    project_id: str
    git_snapshot: ReviewGitSnapshot
    current_goal: str
    active_task: str
    target_files: tuple[str, ...]
    validation_commands: tuple[str, ...]
    last_codex_prompt_summary: str
    result_summary: str
    privacy_reviewed: bool


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """One immutable Review input snapshot without approval authority."""

    contract_type: str
    version: str
    review_id: str
    created_at: str
    authority_boundary: str
    project_id: str
    git_snapshot: ReviewGitSnapshot
    current_goal: str
    active_task: str
    target_files: tuple[str, ...]
    validation_commands: tuple[str, ...]
    last_codex_prompt_summary: str
    result_summary: str
    privacy_reviewed: bool
    read_only: bool
    review_passed: bool
    commit_approved: bool
    push_allowed: bool


@dataclass(frozen=True, slots=True)
class ReviewRecordFreshness:
    """A pure blocked-or-matching decision for one current Git snapshot."""

    matches: bool
    blocking_reasons: tuple[str, ...]


def normalize_review_git_snapshot(
    data: Mapping[str, Any],
    *,
    path: str = "review git snapshot",
) -> ReviewGitSnapshot:
    """Validate and canonically normalize caller-supplied Git metadata."""

    if not isinstance(data, Mapping):
        raise ReviewRecordError(f"{path} must be an object")
    _reject_unknown_fields(data, _GIT_SNAPSHOT_FIELDS, path)

    branch = _bounded_text(data, "branch", path, 255)
    if (
        not _BRANCH_PATTERN.fullmatch(branch)
        or branch.endswith(("/", "."))
        or "//" in branch
        or ".." in branch
        or "@{" in branch
    ):
        raise ReviewRecordError(f"{path}.branch is not a safe branch name")

    head = _bounded_text(data, "head", path, 64)
    if not _GIT_HEAD_PATTERN.fullmatch(head):
        raise ReviewRecordError(f"{path}.head must be a full lowercase Git object ID")

    status_value = data.get("status")
    if not isinstance(status_value, list):
        raise ReviewRecordError(f"{path}.status must be a list of git status --short lines")
    if len(status_value) > MAX_STATUS_LINES:
        raise ReviewRecordError(f"{path}.status contains too many lines")
    normalized_status = tuple(
        _normalize_status_line(value, f"{path}.status[{index}]")
        for index, value in enumerate(status_value)
    )
    _reject_duplicates(normalized_status, f"{path}.status")
    _reject_duplicates(
        tuple(_status_path(line) for line in normalized_status),
        f"{path}.status paths",
        paths=True,
    )

    return ReviewGitSnapshot(
        branch=branch,
        head=head,
        status=tuple(sorted(normalized_status, key=lambda item: (item.casefold(), item))),
    )


def normalize_review_record_candidate(data: Mapping[str, Any]) -> ReviewRecordCandidate:
    """Validate and canonically normalize one future Review record candidate."""

    if not isinstance(data, Mapping):
        raise ReviewRecordError("review record candidate must be an object")
    path = "review record candidate"
    _reject_unknown_fields(data, _CANDIDATE_FIELDS, path)

    project_id = _bounded_text(data, "project_id", path, 64)
    if project_id != PROJECT_ID:
        raise ReviewRecordError(f"{path}.project_id must be {PROJECT_ID}")
    snapshot = normalize_review_git_snapshot(data.get("git_snapshot"), path=f"{path}.git_snapshot")

    target_files = _path_list(
        data,
        "target_files",
        path,
        maximum=MAX_TARGET_FILES,
    )
    if not target_files:
        raise ReviewRecordError(f"{path}.target_files must not be empty")
    if _path_key(PROTECTED_UNTRACKED_PATH) in {_path_key(value) for value in target_files}:
        raise ReviewRecordError(f"{PROTECTED_UNTRACKED_PATH} must not be a Review target")

    validation_commands = _text_list(
        data,
        "validation_commands",
        path,
        maximum=MAX_VALIDATION_COMMANDS,
        item_maximum=MAX_COMMAND_CHARS,
        sort_values=False,
    )
    if not validation_commands:
        raise ReviewRecordError(f"{path}.validation_commands must not be empty")

    if data.get("privacy_reviewed") is not True:
        raise ReviewRecordError(f"{path}.privacy_reviewed must be true")

    _validate_candidate_status(snapshot, target_files)

    return ReviewRecordCandidate(
        project_id=project_id,
        git_snapshot=snapshot,
        current_goal=_bounded_text(data, "current_goal", path, MAX_TEXT_CHARS),
        active_task=_bounded_text(data, "active_task", path, MAX_TEXT_CHARS),
        target_files=target_files,
        validation_commands=validation_commands,
        last_codex_prompt_summary=_optional_bounded_text(
            data,
            "last_codex_prompt_summary",
            path,
            MAX_SUMMARY_CHARS,
        ),
        result_summary=_bounded_text(data, "result_summary", path, MAX_SUMMARY_CHARS),
        privacy_reviewed=True,
    )


def create_review_record(
    candidate: ReviewRecordCandidate,
    *,
    id_generator: Callable[[], str] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> ReviewRecord:
    """Create one immutable record without filesystem or transport side effects."""

    normalized_candidate = _validate_candidate_instance(candidate)
    review_id = (
        f"review_{uuid.uuid4().hex[:24]}"
        if id_generator is None
        else str(id_generator()).strip()
    )
    if not _REVIEW_ID_PATTERN.fullmatch(review_id):
        raise ReviewRecordError("generated review_id is invalid")

    timestamp = datetime.now(timezone.utc) if clock is None else clock()
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        raise ReviewRecordError("Review record clock must return a timezone-aware datetime")
    created_at = timestamp.astimezone(timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    return normalize_review_record(
        {
            "contract_type": CONTRACT_TYPE,
            "version": VERSION,
            "review_id": review_id,
            "created_at": created_at,
            "authority_boundary": AUTHORITY_BOUNDARY,
            **_candidate_mapping(normalized_candidate),
            "read_only": True,
            "review_passed": False,
            "commit_approved": False,
            "push_allowed": False,
        }
    )


def normalize_review_record(data: Mapping[str, Any]) -> ReviewRecord:
    """Validate and canonically normalize one complete Review record."""

    if not isinstance(data, Mapping):
        raise ReviewRecordError("review record must be an object")
    path = "review record"
    _reject_unknown_fields(data, _RECORD_FIELDS, path)

    if data.get("contract_type") != CONTRACT_TYPE:
        raise ReviewRecordError(f"{path}.contract_type must be {CONTRACT_TYPE}")
    if data.get("version") != VERSION:
        raise ReviewRecordError(f"{path}.version must be {VERSION}")
    review_id = data.get("review_id")
    if not isinstance(review_id, str) or not _REVIEW_ID_PATTERN.fullmatch(review_id):
        raise ReviewRecordError(f"{path}.review_id is invalid")
    created_at = _canonical_utc_timestamp(data.get("created_at"), f"{path}.created_at")
    if data.get("authority_boundary") != AUTHORITY_BOUNDARY:
        raise ReviewRecordError(
            f"{path}.authority_boundary must be {AUTHORITY_BOUNDARY}"
        )
    if data.get("read_only") is not True:
        raise ReviewRecordError(f"{path}.read_only must be true")
    for field in ("review_passed", "commit_approved", "push_allowed"):
        if data.get(field) is not False:
            raise ReviewRecordError(f"{path}.{field} must be false")

    candidate = normalize_review_record_candidate(
        {field: data.get(field) for field in _CANDIDATE_FIELDS}
    )
    return ReviewRecord(
        contract_type=CONTRACT_TYPE,
        version=VERSION,
        review_id=review_id,
        created_at=created_at,
        authority_boundary=AUTHORITY_BOUNDARY,
        project_id=candidate.project_id,
        git_snapshot=candidate.git_snapshot,
        current_goal=candidate.current_goal,
        active_task=candidate.active_task,
        target_files=candidate.target_files,
        validation_commands=candidate.validation_commands,
        last_codex_prompt_summary=candidate.last_codex_prompt_summary,
        result_summary=candidate.result_summary,
        privacy_reviewed=True,
        read_only=True,
        review_passed=False,
        commit_approved=False,
        push_allowed=False,
    )


def parse_review_record_json(text: str) -> ReviewRecord:
    """Parse bounded JSON with duplicate-key rejection, then normalize it."""

    if not isinstance(text, str):
        raise ReviewRecordError("review record JSON must be text")
    try:
        byte_length = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ReviewRecordError("review record JSON must be valid UTF-8") from exc
    if not text.strip():
        raise ReviewRecordError("review record JSON must not be empty")
    if byte_length > MAX_JSON_BYTES:
        raise ReviewRecordError("review record JSON exceeds the input limit")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_finite_json,
        )
    except ReviewRecordError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ReviewRecordError("review record JSON is malformed") from exc
    return normalize_review_record(value)


def review_record_to_dict(record: ReviewRecord) -> dict[str, Any]:
    """Return a fresh transport mapping after revalidating the immutable record."""

    normalized = _validate_record_instance(record)
    return _record_mapping(normalized)


def serialize_review_record(record: ReviewRecord) -> str:
    """Return stable, compact, UTF-8-compatible canonical JSON."""

    serialized = json.dumps(
        review_record_to_dict(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if len(serialized.encode("utf-8")) > MAX_JSON_BYTES:
        raise ReviewRecordError("normalized Review record exceeds the output limit")
    return serialized


def review_record_digest(record: ReviewRecord) -> str:
    """Return the stable SHA-256 digest of one canonical Review record."""

    return hashlib.sha256(serialize_review_record(record).encode("utf-8")).hexdigest()


def evaluate_review_record_freshness(
    record: ReviewRecord,
    current_git_snapshot: ReviewGitSnapshot | Mapping[str, Any],
) -> ReviewRecordFreshness:
    """Compare fresh caller-supplied Git metadata with one captured record."""

    normalized_record = _validate_record_instance(record)
    current = (
        _validate_snapshot_instance(current_git_snapshot)
        if isinstance(current_git_snapshot, ReviewGitSnapshot)
        else normalize_review_git_snapshot(current_git_snapshot, path="current git snapshot")
    )
    reasons: list[str] = []
    if current.branch != normalized_record.git_snapshot.branch:
        reasons.append("current branch differs from the captured Review branch")
    if current.head != normalized_record.git_snapshot.head:
        reasons.append("current HEAD differs from the captured Review HEAD")
    if current.status != normalized_record.git_snapshot.status:
        reasons.append("current working tree differs from the captured Review snapshot")
    if f"?? {PROTECTED_UNTRACKED_PATH}" not in current.status:
        reasons.append(f"{PROTECTED_UNTRACKED_PATH} is not protected and untracked")
    if _has_staged_change(current.status):
        reasons.append("current working tree contains staged changes")
    if _status_paths_outside_targets(current.status, normalized_record.target_files):
        reasons.append("current working tree contains changes outside the Review target scope")
    return ReviewRecordFreshness(matches=not reasons, blocking_reasons=tuple(reasons))


def _validate_candidate_status(
    snapshot: ReviewGitSnapshot,
    target_files: tuple[str, ...],
) -> None:
    if f"?? {PROTECTED_UNTRACKED_PATH}" not in snapshot.status:
        raise ReviewRecordError(f"{PROTECTED_UNTRACKED_PATH} must remain untracked")
    if _has_staged_change(snapshot.status):
        raise ReviewRecordError("Review record candidate must not contain staged changes")
    outside_targets = _status_paths_outside_targets(snapshot.status, target_files)
    if outside_targets:
        raise ReviewRecordError(
            "Review record candidate contains changes outside target_files: "
            + ", ".join(outside_targets)
        )
    changed_paths = tuple(
        path
        for line in snapshot.status
        if (path := _status_path(line)).casefold() != PROTECTED_UNTRACKED_PATH.casefold()
    )
    if not changed_paths:
        raise ReviewRecordError("Review record candidate requires at least one target change")


def _has_staged_change(status: tuple[str, ...]) -> bool:
    return any(line[:2] != "??" and line[0] != " " for line in status)


def _status_paths_outside_targets(
    status: tuple[str, ...],
    target_files: tuple[str, ...],
) -> tuple[str, ...]:
    outside: list[str] = []
    for line in status:
        path = _status_path(line)
        if path.casefold() == PROTECTED_UNTRACKED_PATH.casefold():
            continue
        if not any(_target_covers_path(target, path) for target in target_files):
            outside.append(path)
    return tuple(outside)


def _target_covers_path(target: str, changed_path: str) -> bool:
    target_key = _path_key(target)
    changed_key = _path_key(changed_path)
    return changed_key == target_key or (
        target.endswith("/") and changed_key.startswith(target_key)
    )


def _normalize_status_line(value: Any, path: str) -> str:
    if not isinstance(value, str) or value != value.rstrip() or len(value) > MAX_PATH_CHARS + 3:
        raise ReviewRecordError(f"{path} must be one bounded git status --short line")
    if len(value) < 4 or value[2] != " ":
        raise ReviewRecordError(f"{path} is malformed")
    code = value[:2]
    if code != "??" and (
        code == "  " or any(character not in _TRACKED_STATUS_CODES for character in code)
    ):
        raise ReviewRecordError(f"{path} has an unsupported status code")
    raw_path = value[3:]
    if not raw_path or raw_path.startswith('"') or " -> " in raw_path:
        raise ReviewRecordError(f"{path} has unsupported path syntax")
    normalized_path = _relative_path(raw_path, path)
    return f"{code} {normalized_path}"


def _status_path(line: str) -> str:
    return line[3:]


def _path_list(
    data: Mapping[str, Any],
    field: str,
    path: str,
    *,
    maximum: int,
) -> tuple[str, ...]:
    values = data.get(field)
    if not isinstance(values, list) or len(values) > maximum:
        raise ReviewRecordError(f"{path}.{field} must be a bounded list")
    normalized = tuple(
        _relative_path(
            value,
            f"{path}.{field}[{index}]",
            allow_directory=True,
        )
        for index, value in enumerate(values)
    )
    _reject_duplicates(normalized, f"{path}.{field}", paths=True)
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


def _relative_path(value: Any, path: str, *, allow_directory: bool = False) -> str:
    if not isinstance(value, str):
        raise ReviewRecordError(f"{path} must be a repository-relative path")
    normalized = value.replace("\\", "/").strip()
    directory_target = normalized.endswith("/")
    path_without_suffix = normalized[:-1] if directory_target else normalized
    if (
        not normalized
        or len(normalized) > MAX_PATH_CHARS
        or normalized.startswith("/")
        or _WINDOWS_DRIVE.match(normalized)
        or (directory_target and not allow_directory)
        or any(part in {"", ".", ".."} for part in path_without_suffix.split("/"))
        or any(unicodedata.category(character).startswith("C") for character in normalized)
    ):
        raise ReviewRecordError(f"{path} must be a safe repository-relative path")
    return normalized


def _text_list(
    data: Mapping[str, Any],
    field: str,
    path: str,
    *,
    maximum: int,
    item_maximum: int,
    sort_values: bool,
) -> tuple[str, ...]:
    values = data.get(field)
    if not isinstance(values, list) or len(values) > maximum:
        raise ReviewRecordError(f"{path}.{field} must be a bounded list")
    normalized = tuple(
        _normalized_text(value, f"{path}.{field}[{index}]", item_maximum)
        for index, value in enumerate(values)
    )
    _reject_duplicates(normalized, f"{path}.{field}")
    return (
        tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))
        if sort_values
        else normalized
    )


def _bounded_text(
    data: Mapping[str, Any],
    field: str,
    path: str,
    maximum: int,
) -> str:
    if field not in data:
        raise ReviewRecordError(f"{path}.{field} is required")
    return _normalized_text(data[field], f"{path}.{field}", maximum)


def _optional_bounded_text(
    data: Mapping[str, Any],
    field: str,
    path: str,
    maximum: int,
) -> str:
    value = data.get(field, "")
    if value == "":
        return ""
    return _normalized_text(value, f"{path}.{field}", maximum)


def _normalized_text(value: Any, path: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ReviewRecordError(f"{path} must be text")
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ReviewRecordError(f"{path} must be non-empty text")
    if len(normalized) > maximum:
        raise ReviewRecordError(f"{path} is too long")
    if any(unicodedata.category(character).startswith("C") for character in normalized):
        raise ReviewRecordError(f"{path} contains a control character")
    return normalized


def _canonical_utc_timestamp(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _UTC_TIMESTAMP_PATTERN.fullmatch(value):
        raise ReviewRecordError(f"{path} must be a canonical UTC timestamp")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise ReviewRecordError(f"{path} must be a valid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ReviewRecordError(f"{path} must be a canonical UTC timestamp")
    return value


def _validate_candidate_instance(candidate: ReviewRecordCandidate) -> ReviewRecordCandidate:
    if not isinstance(candidate, ReviewRecordCandidate):
        raise ReviewRecordError("candidate must be a ReviewRecordCandidate")
    normalized = normalize_review_record_candidate(_candidate_mapping(candidate))
    if normalized != candidate:
        raise ReviewRecordError("ReviewRecordCandidate is not canonically normalized")
    return normalized


def _validate_snapshot_instance(snapshot: ReviewGitSnapshot) -> ReviewGitSnapshot:
    if not isinstance(snapshot, ReviewGitSnapshot):
        raise ReviewRecordError("snapshot must be a ReviewGitSnapshot")
    normalized = normalize_review_git_snapshot(_snapshot_mapping(snapshot))
    if normalized != snapshot:
        raise ReviewRecordError("ReviewGitSnapshot is not canonically normalized")
    return normalized


def _validate_record_instance(record: ReviewRecord) -> ReviewRecord:
    if not isinstance(record, ReviewRecord):
        raise ReviewRecordError("record must be a ReviewRecord")
    normalized = normalize_review_record(_record_mapping(record))
    if normalized != record:
        raise ReviewRecordError("ReviewRecord is not canonically normalized")
    return normalized


def _snapshot_mapping(snapshot: ReviewGitSnapshot) -> dict[str, Any]:
    if not isinstance(snapshot, ReviewGitSnapshot):
        raise ReviewRecordError("ReviewGitSnapshot must be an immutable contract")
    if not isinstance(snapshot.status, tuple):
        raise ReviewRecordError("ReviewGitSnapshot status must be immutable")
    return {
        "branch": snapshot.branch,
        "head": snapshot.head,
        "status": list(snapshot.status),
    }


def _candidate_mapping(candidate: ReviewRecordCandidate) -> dict[str, Any]:
    if not isinstance(candidate.target_files, tuple) or not isinstance(
        candidate.validation_commands, tuple
    ):
        raise ReviewRecordError("ReviewRecordCandidate lists must be immutable")
    return {
        "project_id": candidate.project_id,
        "git_snapshot": _snapshot_mapping(candidate.git_snapshot),
        "current_goal": candidate.current_goal,
        "active_task": candidate.active_task,
        "target_files": list(candidate.target_files),
        "validation_commands": list(candidate.validation_commands),
        "last_codex_prompt_summary": candidate.last_codex_prompt_summary,
        "result_summary": candidate.result_summary,
        "privacy_reviewed": candidate.privacy_reviewed,
    }


def _record_mapping(record: ReviewRecord) -> dict[str, Any]:
    candidate = ReviewRecordCandidate(
        project_id=record.project_id,
        git_snapshot=record.git_snapshot,
        current_goal=record.current_goal,
        active_task=record.active_task,
        target_files=record.target_files,
        validation_commands=record.validation_commands,
        last_codex_prompt_summary=record.last_codex_prompt_summary,
        result_summary=record.result_summary,
        privacy_reviewed=record.privacy_reviewed,
    )
    return {
        "contract_type": record.contract_type,
        "version": record.version,
        "review_id": record.review_id,
        "created_at": record.created_at,
        "authority_boundary": record.authority_boundary,
        **_candidate_mapping(candidate),
        "read_only": record.read_only,
        "review_passed": record.review_passed,
        "commit_approved": record.commit_approved,
        "push_allowed": record.push_allowed,
    }


def _reject_unknown_fields(
    data: Mapping[str, Any],
    allowed: frozenset[str],
    path: str,
) -> None:
    non_text = [key for key in data if not isinstance(key, str)]
    if non_text:
        raise ReviewRecordError(f"{path} contains a non-text field name")
    unknown = sorted(key for key in data if key not in allowed)
    if unknown:
        raise ReviewRecordError(f"{path} contains unknown fields: {', '.join(unknown)}")


def _reject_duplicates(
    values: Iterable[str],
    path: str,
    *,
    paths: bool = False,
) -> None:
    seen: set[str] = set()
    for value in values:
        key = _path_key(value) if paths else value.casefold()
        if key in seen:
            raise ReviewRecordError(f"{path} contains duplicate values")
        seen.add(key)


def _path_key(value: str) -> str:
    return value.replace("\\", "/").strip().casefold()


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReviewRecordError(f"review record JSON contains duplicate key: {key}")
        value[key] = item
    return value


def _reject_non_finite_json(value: str) -> Any:
    raise ReviewRecordError(f"review record JSON contains non-finite value: {value}")
