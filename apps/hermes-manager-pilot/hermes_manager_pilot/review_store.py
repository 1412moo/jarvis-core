"""Route-free Durable Review Record v0.1B-1 local store primitives.

The store is append-only and local. This module exposes no HTTP/UI integration,
does not read Git, performs no automatic deletion or migration, and grants no
review, commit, push, or execution authority.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import threading
from typing import Any
import uuid

from .review_record import (
    MAX_JSON_BYTES,
    ReviewRecord,
    ReviewRecordError,
    parse_review_record_json,
    review_record_digest,
    serialize_review_record,
)


JARVIS_LOCAL_STATE_DIR_ENV = "JARVIS_LOCAL_STATE_DIR"
WINDOWS_STATE_ROOT_NAME = "Jarvis-Core"
REVIEW_STORE_SEGMENTS = ("hermes-manager", "reviews", "v1")
RETENTION_POLICY = "manual_delete_only"
MAX_RECORDS = 256
MAX_DIRECTORY_ENTRIES = 512
MAX_STORED_BYTES = MAX_JSON_BYTES + 1
TEMP_CREATE_ATTEMPTS = 8

REPO_ROOT = Path(__file__).resolve().parents[3]

_REVIEW_ID_PATTERN = re.compile(r"^review_[0-9a-f]{24}$")
_RECORD_FILE_PATTERN = re.compile(r"^(review_[0-9a-f]{24})\.json$")
_TEMP_FILE_PATTERN = re.compile(
    r"^\.review_[0-9a-f]{24}\.[0-9a-f]{32}\.tmp$"
)
_TEMP_TOKEN_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_STORE_LOCK = threading.RLock()


class ReviewStoreError(ValueError):
    """A fixed-category local Review store failure without path disclosure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ReviewStorePaths:
    """Validated policy and normalized paths for the Hermes Review store."""

    source: str
    state_root_policy_path: Path
    review_dir_policy_path: Path
    state_root: Path
    review_dir: Path


@dataclass(frozen=True, slots=True)
class ReviewStoreWriteResult:
    """A path-free receipt for one append-only Review record write."""

    stored: bool
    review_id: str
    created_at: str
    retention_policy: str


@dataclass(frozen=True, slots=True)
class ReviewStoreDeleteResult:
    """A path-free receipt for one exact Review record deletion."""

    deleted: bool
    review_id: str
    previous_created_at: str
    retention_policy: str


@dataclass(frozen=True, slots=True)
class ReviewRecordSummary:
    """Bounded metadata for read-only Review record listing."""

    review_id: str
    record_version: str
    created_at: str
    active_task: str
    branch: str
    head: str
    target_count: int
    content_evidence_available: bool


@dataclass(frozen=True, slots=True)
class ReviewStoreListing:
    """One deterministic, bounded list without result text or file paths."""

    records: tuple[ReviewRecordSummary, ...]
    count: int
    capacity: int
    retention_policy: str


def resolve_review_store_paths(
    *,
    env: Mapping[str, Any] | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
) -> ReviewStorePaths:
    """Resolve the Review store path without creating files or directories."""

    env_map: Mapping[str, Any] = os.environ if env is None else env
    windows = (os.name == "nt") if is_windows is None else is_windows
    override = str(env_map.get(JARVIS_LOCAL_STATE_DIR_ENV, "")).strip()
    if override:
        state_root_policy_path = Path(os.path.expandvars(override)).expanduser()
        source = "env_override"
        if not state_root_policy_path.is_absolute():
            raise ReviewStoreError("local_state_dir_must_be_absolute")
    elif windows and str(env_map.get("LOCALAPPDATA", "")).strip():
        local_appdata = os.path.expandvars(str(env_map["LOCALAPPDATA"]).strip())
        state_root_policy_path = Path(local_appdata) / WINDOWS_STATE_ROOT_NAME
        source = "default_windows_localappdata"
    else:
        home = Path.home() if home_dir is None else Path(home_dir)
        state_root_policy_path = home / ".jarvis-core"
        source = "default_home"

    state_root_policy_path = _absolute_lexical_path(state_root_policy_path)
    review_dir_policy_path = state_root_policy_path.joinpath(*REVIEW_STORE_SEGMENTS)
    try:
        state_root = state_root_policy_path.resolve(strict=False)
        review_dir = review_dir_policy_path.resolve(strict=False)
        normalized_repo_root = Path(repo_root).resolve(strict=False)
    except (OSError, RuntimeError):
        raise ReviewStoreError("review_store_path_not_safe") from None
    if _is_path_inside(review_dir, normalized_repo_root):
        raise ReviewStoreError("local_state_dir_inside_repo")
    return ReviewStorePaths(
        source=source,
        state_root_policy_path=state_root_policy_path,
        review_dir_policy_path=review_dir_policy_path,
        state_root=state_root,
        review_dir=review_dir,
    )


def write_review_record(
    record: ReviewRecord,
    *,
    env: Mapping[str, Any] | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
    publisher: Callable[[Path, Path], Any] | None = None,
    temp_token_generator: Callable[[], str] | None = None,
) -> ReviewStoreWriteResult:
    """Append one canonical Review record with no overwrite or automatic delete."""

    serialized = _serialized_record_bytes(record)
    review_id = record.review_id
    paths = resolve_review_store_paths(
        env=env,
        home_dir=home_dir,
        repo_root=repo_root,
        is_windows=is_windows,
    )
    publish = os.link if publisher is None else publisher
    token_generator = (
        (lambda: uuid.uuid4().hex)
        if temp_token_generator is None
        else temp_token_generator
    )

    with _STORE_LOCK:
        review_dir = _prepare_store_directory(paths, repo_root=repo_root)
        record_files = _scan_store_directory(review_dir)
        final_file = _record_file(review_dir, review_id)
        if os.path.lexists(final_file):
            raise ReviewStoreError("review_record_exists")
        _validate_existing_records(record_files)
        if len(record_files) >= MAX_RECORDS:
            raise ReviewStoreError("review_store_capacity_reached")

        temp_file: Path | None = None
        published = False
        try:
            for _ in range(TEMP_CREATE_ATTEMPTS):
                token = str(token_generator()).strip()
                if not _TEMP_TOKEN_PATTERN.fullmatch(token):
                    raise ReviewStoreError("review_record_write_failed")
                candidate = review_dir / f".{review_id}.{token}.tmp"
                if candidate.parent != review_dir:
                    raise ReviewStoreError("review_store_path_not_safe")
                try:
                    stream = _open_exclusive_private_file(candidate)
                except FileExistsError:
                    continue
                except OSError:
                    raise ReviewStoreError("review_record_write_failed") from None
                temp_file = candidate
                try:
                    with stream:
                        stream.write(serialized)
                        stream.flush()
                        os.fsync(stream.fileno())
                except OSError:
                    raise ReviewStoreError("review_record_write_failed") from None
                break
            if temp_file is None:
                raise ReviewStoreError("review_record_write_failed")

            _validate_existing_store_directory(
                paths,
                repo_root=repo_root,
                expected_review_dir=review_dir,
            )
            if os.path.lexists(final_file):
                raise ReviewStoreError("review_record_exists")
            try:
                publish(temp_file, final_file)
            except FileExistsError:
                raise ReviewStoreError("review_record_exists") from None
            except OSError:
                raise ReviewStoreError("review_record_write_failed") from None
            published = True
        finally:
            if temp_file is not None:
                _cleanup_own_temp_file(temp_file)

        if not published:
            raise ReviewStoreError("review_record_write_failed")
        try:
            stored = _read_record_file(final_file, expected_review_id=review_id)
        except ReviewStoreError:
            raise ReviewStoreError("review_record_write_outcome_uncertain") from None
        if stored != record:
            raise ReviewStoreError("review_record_write_outcome_uncertain")
        return ReviewStoreWriteResult(
            stored=True,
            review_id=stored.review_id,
            created_at=stored.created_at,
            retention_policy=RETENTION_POLICY,
        )


def read_review_record(
    review_id: str,
    *,
    env: Mapping[str, Any] | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
) -> ReviewRecord:
    """Read exactly one canonical Review record by safe generated ID."""

    safe_id = _safe_review_id(review_id)
    paths = resolve_review_store_paths(
        env=env,
        home_dir=home_dir,
        repo_root=repo_root,
        is_windows=is_windows,
    )
    with _STORE_LOCK:
        review_dir = _require_store_directory(paths, repo_root=repo_root)
        return _read_record_file(
            _record_file(review_dir, safe_id),
            expected_review_id=safe_id,
        )


def delete_review_record(
    review_id: str,
    expected_digest: str,
    *,
    env: Mapping[str, Any] | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
) -> ReviewStoreDeleteResult:
    """Delete exactly one unchanged canonical record; never delete corrupt data."""

    safe_id = _safe_review_id(review_id)
    if not isinstance(expected_digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", expected_digest
    ):
        raise ReviewStoreError("review_record_digest_invalid")
    paths = resolve_review_store_paths(
        env=env,
        home_dir=home_dir,
        repo_root=repo_root,
        is_windows=is_windows,
    )
    with _STORE_LOCK:
        review_dir = _require_store_directory(paths, repo_root=repo_root)
        record_file = _record_file(review_dir, safe_id)
        try:
            before = os.lstat(record_file)
        except FileNotFoundError:
            raise ReviewStoreError("review_record_not_found") from None
        except OSError:
            raise ReviewStoreError("review_record_read_failed") from None
        record = _read_record_file(record_file, expected_review_id=safe_id)
        if review_record_digest(record) != expected_digest:
            raise ReviewStoreError("review_delete_target_changed")
        try:
            after_read = os.lstat(record_file)
        except FileNotFoundError:
            raise ReviewStoreError("review_delete_target_changed") from None
        except OSError:
            raise ReviewStoreError("review_record_read_failed") from None
        if not _same_file_snapshot(before, after_read):
            raise ReviewStoreError("review_delete_target_changed")
        try:
            record_file.unlink()
        except FileNotFoundError:
            raise ReviewStoreError("review_delete_target_changed") from None
        except OSError:
            raise ReviewStoreError("review_record_delete_failed") from None
        if os.path.lexists(record_file):
            raise ReviewStoreError("review_record_delete_outcome_uncertain")
        _sync_directory_best_effort(review_dir)
        return ReviewStoreDeleteResult(
            deleted=True,
            review_id=record.review_id,
            previous_created_at=record.created_at,
            retention_policy=RETENTION_POLICY,
        )


def list_review_records(
    *,
    env: Mapping[str, Any] | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
) -> ReviewStoreListing:
    """Return deterministic metadata only; never return Review result text or paths."""

    paths = resolve_review_store_paths(
        env=env,
        home_dir=home_dir,
        repo_root=repo_root,
        is_windows=is_windows,
    )
    with _STORE_LOCK:
        if not os.path.lexists(paths.review_dir_policy_path):
            _validate_path_chain(paths.review_dir_policy_path)
            return ReviewStoreListing(
                records=(),
                count=0,
                capacity=MAX_RECORDS,
                retention_policy=RETENTION_POLICY,
            )
        review_dir = _require_store_directory(paths, repo_root=repo_root)
        record_files = _scan_store_directory(review_dir)
        if len(record_files) > MAX_RECORDS:
            raise ReviewStoreError("review_store_capacity_exceeded")
        records = tuple(
            _read_record_file(path, expected_review_id=_review_id_from_filename(path.name))
            for path in record_files
        )
        summaries = tuple(
            ReviewRecordSummary(
                review_id=record.review_id,
                record_version=record.version,
                created_at=record.created_at,
                active_task=record.active_task,
                branch=record.git_snapshot.branch,
                head=record.git_snapshot.head,
                target_count=len(record.target_files),
                content_evidence_available=record.content_evidence_binding is not None,
            )
            for record in sorted(
                records,
                key=lambda value: (value.created_at, value.review_id),
                reverse=True,
            )
        )
        return ReviewStoreListing(
            records=summaries,
            count=len(summaries),
            capacity=MAX_RECORDS,
            retention_policy=RETENTION_POLICY,
        )


def _prepare_store_directory(paths: ReviewStorePaths, *, repo_root: Path) -> Path:
    _validate_path_chain(paths.review_dir_policy_path)
    existed = os.path.lexists(paths.review_dir_policy_path)
    try:
        paths.review_dir_policy_path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not existed:
            os.chmod(paths.review_dir_policy_path, 0o700)
    except OSError:
        raise ReviewStoreError("review_store_unavailable") from None
    return _validate_existing_store_directory(paths, repo_root=repo_root)


def _require_store_directory(paths: ReviewStorePaths, *, repo_root: Path) -> Path:
    if not os.path.lexists(paths.review_dir_policy_path):
        _validate_path_chain(paths.review_dir_policy_path)
        raise ReviewStoreError("review_record_not_found")
    return _validate_existing_store_directory(paths, repo_root=repo_root)


def _validate_existing_store_directory(
    paths: ReviewStorePaths,
    *,
    repo_root: Path,
    expected_review_dir: Path | None = None,
) -> Path:
    _validate_path_chain(paths.review_dir_policy_path)
    try:
        review_dir = paths.review_dir_policy_path.resolve(strict=True)
        normalized_repo_root = Path(repo_root).resolve(strict=False)
        path_stat = os.lstat(paths.review_dir_policy_path)
    except (OSError, RuntimeError):
        raise ReviewStoreError("review_store_unavailable") from None
    if _stat_is_reparse_point(path_stat) or not stat.S_ISDIR(path_stat.st_mode):
        raise ReviewStoreError("review_store_path_not_safe")
    if review_dir != paths.review_dir or _is_path_inside(review_dir, normalized_repo_root):
        raise ReviewStoreError("review_store_path_not_safe")
    if expected_review_dir is not None and review_dir != expected_review_dir:
        raise ReviewStoreError("review_store_path_not_safe")
    return review_dir


def _scan_store_directory(review_dir: Path) -> tuple[Path, ...]:
    try:
        entries = list(os.scandir(review_dir))
    except OSError:
        raise ReviewStoreError("review_store_unavailable") from None
    if len(entries) > MAX_DIRECTORY_ENTRIES:
        raise ReviewStoreError("review_store_too_many_entries")
    records: list[Path] = []
    for entry in entries:
        name = entry.name
        if _TEMP_FILE_PATTERN.fullmatch(name):
            raise ReviewStoreError("review_store_recovery_required")
        if not _RECORD_FILE_PATTERN.fullmatch(name):
            raise ReviewStoreError("review_store_unexpected_entry")
        try:
            entry_stat = os.lstat(entry.path)
        except OSError:
            raise ReviewStoreError("review_store_unavailable") from None
        if _stat_is_reparse_point(entry_stat) or not stat.S_ISREG(entry_stat.st_mode):
            raise ReviewStoreError("review_store_path_not_safe")
        records.append(Path(entry.path))
    return tuple(sorted(records, key=lambda path: path.name))


def _validate_existing_records(record_files: tuple[Path, ...]) -> None:
    for path in record_files:
        _read_record_file(path, expected_review_id=_review_id_from_filename(path.name))


def _read_record_file(path: Path, *, expected_review_id: str) -> ReviewRecord:
    if path.name != f"{expected_review_id}.json" or path.parent == path:
        raise ReviewStoreError("review_store_path_not_safe")
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        raise ReviewStoreError("review_record_not_found") from None
    except OSError:
        raise ReviewStoreError("review_record_read_failed") from None
    if _stat_is_reparse_point(before) or not stat.S_ISREG(before.st_mode):
        raise ReviewStoreError("review_store_path_not_safe")
    if before.st_size <= 0 or before.st_size > MAX_STORED_BYTES:
        raise ReviewStoreError("review_record_corrupt")
    try:
        with _open_read_only_no_follow(path) as stream:
            raw = stream.read(MAX_STORED_BYTES + 1)
            during = os.fstat(stream.fileno())
        after = os.lstat(path)
    except OSError:
        raise ReviewStoreError("review_record_read_failed") from None
    if len(raw) > MAX_STORED_BYTES or not _same_file_snapshot(before, during, after):
        raise ReviewStoreError("review_record_corrupt")
    try:
        text = raw.decode("utf-8", errors="strict")
        record = parse_review_record_json(text)
        canonical = f"{serialize_review_record(record)}\n".encode("utf-8")
    except (UnicodeDecodeError, ReviewRecordError):
        raise ReviewStoreError("review_record_corrupt") from None
    if raw != canonical or record.review_id != expected_review_id:
        raise ReviewStoreError("review_record_corrupt")
    return record


def _serialized_record_bytes(record: ReviewRecord) -> bytes:
    try:
        serialized = f"{serialize_review_record(record)}\n".encode(
            "utf-8",
            errors="strict",
        )
    except (ReviewRecordError, UnicodeEncodeError):
        raise ReviewStoreError("review_record_invalid") from None
    if len(serialized) > MAX_STORED_BYTES:
        raise ReviewStoreError("review_record_invalid")
    return serialized


def _safe_review_id(value: str) -> str:
    if not isinstance(value, str) or not _REVIEW_ID_PATTERN.fullmatch(value):
        raise ReviewStoreError("review_id_invalid")
    return value


def _review_id_from_filename(name: str) -> str:
    match = _RECORD_FILE_PATTERN.fullmatch(name)
    if match is None:
        raise ReviewStoreError("review_store_unexpected_entry")
    return match.group(1)


def _record_file(review_dir: Path, review_id: str) -> Path:
    safe_id = _safe_review_id(review_id)
    path = review_dir / f"{safe_id}.json"
    if path.parent != review_dir:
        raise ReviewStoreError("review_store_path_not_safe")
    return path


def _validate_path_chain(path: Path) -> None:
    if _existing_path_chain_has_reparse_point(path):
        raise ReviewStoreError("review_store_path_not_safe")


def _existing_path_chain_has_reparse_point(path: Path) -> bool:
    current = _absolute_lexical_path(path)
    components = [current]
    while current.parent != current:
        current = current.parent
        components.append(current)
    for component in reversed(components):
        try:
            component_stat = os.lstat(component)
        except FileNotFoundError:
            continue
        except OSError:
            raise ReviewStoreError("review_store_unavailable") from None
        if _stat_is_reparse_point(component_stat):
            return True
    return False


def _stat_is_reparse_point(path_stat: os.stat_result) -> bool:
    if stat.S_ISLNK(path_stat.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(getattr(path_stat, "st_file_attributes", 0) & reparse_flag)


def _same_file_snapshot(
    before: os.stat_result,
    during: os.stat_result,
    after: os.stat_result | None = None,
) -> bool:
    fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns")
    snapshots = (before, during) if after is None else (before, during, after)
    return all(
        len({getattr(snapshot, field, None) for snapshot in snapshots}) == 1
        for field in fields
    )


def _sync_directory_best_effort(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _open_exclusive_private_file(path: Path) -> Any:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        return os.fdopen(descriptor, "wb")
    except Exception:
        os.close(descriptor)
        raise


def _open_read_only_no_follow(path: Path) -> Any:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        return os.fdopen(descriptor, "rb")
    except Exception:
        os.close(descriptor)
        raise


def _cleanup_own_temp_file(path: Path) -> None:
    if not _TEMP_FILE_PATTERN.fullmatch(path.name):
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _absolute_lexical_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _is_path_inside(path: Path, root: Path) -> bool:
    path_text = os.path.normcase(os.path.normpath(str(path)))
    root_text = os.path.normcase(os.path.normpath(str(root)))
    try:
        return os.path.commonpath([path_text, root_text]) == root_text
    except ValueError:
        return False
