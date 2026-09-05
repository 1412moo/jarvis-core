"""Audit hash chain storage, atomic append with fsync, and external path policy.

Implements task-0044 storage contracts:
- Path policy: outside repository, 3-tier precedence (JARVIS_LOCAL_STATE_DIR -> %LOCALAPPDATA%/Jarvis-Core -> ~/.jarvis-core)
- Subpath: audit/v1/chain.jsonl
- Retention: manual_delete_only, no length cap (Owner decision Q6). The chain
  cannot be truncated, so a fail-closed cap would let a full audit log block
  approvals; ``cli.py status`` reports length and byte size instead.
- Fire-and-forget forbidden: append failures fail synchronously; fsync enforced
- Concurrency: cross-platform file locking for race-free appends
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import stat
import sys
import time
from typing import Any, Callable, Iterator, Mapping

from audit_entry import (
    AuditChainError,
    AuditEntry,
    audit_entry_to_dict,
    canonical_json,
    create_audit_entry,
    parse_audit_entry_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_STORE_SEGMENTS = ("audit", "v1")
CHAIN_FILE_NAME = "chain.jsonl"
LOCK_FILE_NAME = ".chain.lock"
WINDOWS_STATE_ROOT_NAME = "Jarvis-Core"
JARVIS_LOCAL_STATE_DIR_ENV = "JARVIS_LOCAL_STATE_DIR"
LOCK_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class AuditStorePaths:
    """Resolved, validated audit storage filesystem locations."""

    source: str
    state_root: Path
    audit_dir: Path
    chain_file: Path
    lock_file: Path


def _is_path_inside(target: Path, ancestor: Path) -> bool:
    """Return True when target is equal to or inside ancestor."""
    try:
        target.relative_to(ancestor)
        return True
    except ValueError:
        return False


def resolve_audit_chain_paths(
    *,
    env: Mapping[str, Any] | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
) -> AuditStorePaths:
    """Resolve the Audit store path outside the repository with fail-closed safety."""
    env_map: Mapping[str, Any] = os.environ if env is None else env
    windows = (os.name == "nt") if is_windows is None else is_windows

    override = str(env_map.get(JARVIS_LOCAL_STATE_DIR_ENV, "")).strip()
    if override:
        state_root_path = Path(os.path.expandvars(override)).expanduser()
        source = "env_override"
        if not state_root_path.is_absolute():
            raise AuditChainError("local_state_dir_must_be_absolute")
    elif windows and str(env_map.get("LOCALAPPDATA", "")).strip():
        local_appdata = os.path.expandvars(str(env_map["LOCALAPPDATA"]).strip())
        state_root_path = Path(local_appdata) / WINDOWS_STATE_ROOT_NAME
        source = "default_windows_localappdata"
    else:
        home = Path.home() if home_dir is None else Path(home_dir)
        state_root_path = home / ".jarvis-core"
        source = "default_home"

    try:
        normalized_state_root = state_root_path.resolve(strict=False)
        audit_dir = normalized_state_root.joinpath(*AUDIT_STORE_SEGMENTS).resolve(strict=False)
        normalized_repo_root = Path(repo_root).resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise AuditChainError("audit_store_path_not_safe") from exc

    if _is_path_inside(audit_dir, normalized_repo_root) or _is_path_inside(normalized_state_root, normalized_repo_root):
        raise AuditChainError("local_state_dir_inside_repo")

    chain_file = audit_dir / CHAIN_FILE_NAME
    lock_file = audit_dir / LOCK_FILE_NAME

    return AuditStorePaths(
        source=source,
        state_root=normalized_state_root,
        audit_dir=audit_dir,
        chain_file=chain_file,
        lock_file=lock_file,
    )


@contextmanager
def _acquire_store_lock(lock_path: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    """Acquire a cooperative, cross-platform file lock for audit appending."""
    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout

    lock_fd = None
    try:
        lock_fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o600)
        acquired = False

        if os.name == "nt":
            import msvcrt
            while time.monotonic() < deadline:
                try:
                    msvcrt.locking(lock_fd, msvcrt.LK_NBLCK, 1)
                    acquired = True
                    break
                except (OSError, PermissionError):
                    time.sleep(0.05)
        else:
            import fcntl
            while time.monotonic() < deadline:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except (OSError, BlockingIOError):
                    time.sleep(0.05)

        if not acquired:
            raise AuditChainError("audit_store_lock_timeout")

        yield

    finally:
        if lock_fd is not None:
            try:
                if os.name == "nt":
                    import msvcrt
                    try:
                        msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                else:
                    import fcntl
                    try:
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
            finally:
                os.close(lock_fd)


def read_chain_head(chain_file: Path) -> tuple[int, str | None]:
    """Read the current chain length and head hash. Fail closed if corrupt."""
    if not chain_file.exists():
        return 0, None

    try:
        size = chain_file.stat().st_size
    except OSError as exc:
        raise AuditChainError("chain_file_stat_failed", detail=str(exc)) from exc

    if size == 0:
        return 0, None

    last_seq = 0
    last_hash: str | None = None

    try:
        with chain_file.open("r", encoding="utf-8", errors="strict") as stream:
            for line_no, line in enumerate(stream, start=1):
                stripped = line.rstrip("\r\n")
                if not stripped:
                    raise AuditChainError(
                        "audit_chain_corrupt_empty_line", detail=f"line_{line_no}"
                    )
                entry = parse_audit_entry_json(stripped)
                if entry.seq != last_seq + 1:
                    raise AuditChainError(
                        "audit_chain_corrupt_seq_broken", detail=f"seq_{entry.seq}"
                    )
                if entry.prev_hash != last_hash:
                    raise AuditChainError(
                        "audit_chain_corrupt_prev_hash_mismatch", detail=f"seq_{entry.seq}"
                    )
                last_seq = entry.seq
                last_hash = entry.hash
    except UnicodeDecodeError as exc:
        raise AuditChainError(
            "audit_chain_corrupt_unicode_decode", detail=str(exc)
        ) from exc

    return last_seq, last_hash


def append_audit_entry(
    *,
    kind: str,
    task_id: str,
    payload: Mapping[str, Any],
    actor: str | None = None,
    ts: str | None = None,
    entry_id: str | None = None,
    paths: AuditStorePaths | None = None,
    repo_root: Path = REPO_ROOT,
    env: Mapping[str, Any] | None = None,
) -> AuditEntry:
    """Atomically append one validated AuditEntry with fsync. Never fire-and-forget."""
    resolved_paths = (
        paths
        if paths is not None
        else resolve_audit_chain_paths(repo_root=repo_root, env=env)
    )

    resolved_paths.audit_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    with _acquire_store_lock(resolved_paths.lock_file):
        last_seq, last_hash = read_chain_head(resolved_paths.chain_file)
        next_seq = last_seq + 1
        prev_hash = last_hash

        entry = create_audit_entry(
            seq=next_seq,
            kind=kind,
            task_id=task_id,
            payload=payload,
            prev_hash=prev_hash,
            actor=actor,
            ts=ts,
            entry_id=entry_id,
        )

        canonical_line = canonical_json(audit_entry_to_dict(entry)) + "\n"
        canonical_bytes = canonical_line.encode("utf-8")

        # Open in append mode, write, flush and fsync
        try:
            fd = os.open(
                str(resolved_paths.chain_file),
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o600,
            )
            try:
                written = os.write(fd, canonical_bytes)
                if written != len(canonical_bytes):
                    raise AuditChainError("incomplete_write_to_chain_file")
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError as exc:
            raise AuditChainError("append_audit_entry_io_failed", detail=str(exc)) from exc

    return entry


def record_owner_approval(
    *,
    task_id: str,
    command: str,
    decision: str,
    transition_from: str,
    transition_to: str,
    applied: bool,
    reason: str = "",
    paths: AuditStorePaths | None = None,
    repo_root: Path = REPO_ROOT,
    env: Mapping[str, Any] | None = None,
) -> AuditEntry:
    """Helper to record an owner_approval entry to the audit hash chain."""
    payload = {
        "command": command,
        "decision": decision,
        "transition": {"from": transition_from, "to": transition_to},
        "applied": applied,
        "reason": reason,
    }
    return append_audit_entry(
        kind="owner_approval",
        task_id=task_id,
        payload=payload,
        paths=paths,
        repo_root=repo_root,
        env=env,
    )


def record_execution_result(
    *,
    task_id: str,
    source: str,
    execution_status_transition_applied: bool,
    execution_status_transition_reason: str = "",
    result_kind: str = "success",
    paths: AuditStorePaths | None = None,
    repo_root: Path = REPO_ROOT,
    env: Mapping[str, Any] | None = None,
) -> AuditEntry:
    """Helper to record an execution_result entry to the audit hash chain."""
    payload = {
        "source": source,
        "execution_status_transition_applied": execution_status_transition_applied,
        "execution_status_transition_reason": execution_status_transition_reason,
        "result_kind": result_kind,
    }
    return append_audit_entry(
        kind="execution_result",
        task_id=task_id,
        payload=payload,
        paths=paths,
        repo_root=repo_root,
        env=env,
    )
