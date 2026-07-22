"""Bounded local change-evidence collection for Prompt Queue v0.1C-0A.

The collector reads one explicitly trusted local Git root and exact target
files. It does not persist evidence, execute a prompt, or grant approval.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

from .prompt_queue import ProjectCard, QueueItem
from .schemas import ValidationError


VERSION = "0.1C-0A"
EVIDENCE_TYPE = "hermes_local_change_evidence"

MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_FILE_BYTES = 16 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 64 * 1024
MAX_CANONICAL_BYTES = 64 * 1024
GIT_TIMEOUT_SECONDS = 10

_DIGEST_PREFIX = b"jarvis-core/hermes/local-change-evidence/v0.1C-0A\x00"
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
    root = _validated_trusted_root(trusted_repo_root, project.repo_path)
    _validate_target_scope(root, project, item)

    actual_top_level = _run_git_text(root, ("rev-parse", "--show-toplevel"))
    git_root = _resolve_directory(actual_top_level, "Git top-level")
    if not _same_path(root, git_root):
        raise ValidationError("trusted repo root does not match Git top-level")

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

    snapshot = {
        "evidence_type": EVIDENCE_TYPE,
        "version": VERSION,
        "project_id": project.project_id,
        "item_id": item.item_id,
        "repo_root": _portable_path(root),
        "branch": before.branch,
        "head": before.head,
        "status_scope_paths": list(status_paths),
        "scoped_git_status": list(before.status_lines),
        "targets": [
            {
                "path": target.path,
                "status": target.status,
                "kind": target.kind,
                "byte_size": target.byte_size,
                "content_sha256": target.content_sha256,
            }
            for target in first_targets
        ],
    }
    canonical_bytes = _canonical_json_bytes(snapshot)
    digest = hashlib.sha256(_DIGEST_PREFIX + canonical_bytes).hexdigest()
    return LocalChangeEvidence(
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
    for relative_path in item.target_files:
        _validate_relative_path(relative_path)
        if _path_is_protected(relative_path, project.protected_paths):
            raise ValidationError(f"target path is protected: {relative_path}")
        target_path = _validated_target_path(root, relative_path, allow_missing=True)
        if target_path.exists() and target_path.is_dir():
            raise ValidationError(f"target path must be a file: {relative_path}")
    for relative_path in project.expected_untracked:
        _validate_relative_path(relative_path)
        expected_path = _validated_target_path(root, relative_path, allow_missing=True)
        if expected_path.exists() and expected_path.is_dir():
            raise ValidationError(f"expected untracked path must be a file: {relative_path}")


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


def _validate_expected_project_state(project: ProjectCard, state: _RepositoryState) -> None:
    if state.branch != project.expected_branch:
        raise ValidationError("collected branch does not match expected branch")
    if state.head != project.expected_head:
        raise ValidationError("collected HEAD does not match expected HEAD")
    untracked = {_path_key(path) for code, path in state.status_entries if code == "??"}
    for expected_path in project.expected_untracked:
        if _path_key(expected_path) not in untracked:
            raise ValidationError(f"expected untracked path is missing: {expected_path}")


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
        completed = subprocess.run(
            command,
            cwd=root,
            env=_sanitized_git_environment(),
            check=False,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValidationError("read-only Git evidence command failed") from exc
    if len(completed.stdout) > MAX_GIT_OUTPUT_BYTES or len(completed.stderr) > MAX_GIT_OUTPUT_BYTES:
        raise ValidationError("Git evidence output exceeds limit")
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValidationError(f"read-only Git evidence command failed: {error[:240]}")
    return completed.stdout


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
