"""Minimal local task file writer from task draft object.

Scope (MVP):
- accept task draft object
- scan existing task files under memory/tasks
- allocate next task number and slug
- create one markdown task file from template-compatible format

Out of scope:
- Discord/GitHub integration
- DB/network calls
- status automation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Callable, TextIO
import hashlib
import hmac
import json
import os
import re
import secrets
import unicodedata

TASK_FILE_PATTERN = re.compile(r"^task-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
DEFAULT_TASKS_DIR = Path("memory/tasks")
DEFAULT_STATUS = "TODO"
FALLBACK_SLUG = "task"
MAX_TASK_NUMBER = 9999
MAX_TITLE_CHARS = 120
MAX_REPO_CHARS = 80
MAX_SUMMARY_CHARS = 500
MAX_COMPLETION_EVIDENCE_CHARS = 500
MAX_SOURCE_COMMAND_CHARS = 80
TASK_STATUS_TRANSITIONS = frozenset(
    {
        ("TODO", "DOING"),
        ("DOING", "DONE"),
        # task-0052. The approval path in adapters/discord/bot_minimal.py performs
        # these four today through a writer with no fsync, no atomic replace and no
        # expected_digest check. Listing them is purely additive - no existing
        # constraint is removed - and keeps this set a superset of that path, which
        # is what bot_minimal._validate_approve_transition_contract_sync() asserts.
        # Only the two NEEDS_APPROVAL pairs actually route through this writer today
        # (task-0052 section 10.3): the rest run after execution metadata has been
        # written, which this module's metadata validator rejects by design.
        ("NEEDS_APPROVAL", "DOING"),
        ("NEEDS_APPROVAL", "FAILED"),
        ("DOING", "FAILED"),
        ("FAILED", "TODO"),
    }
)
TASK_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M UTC"
TASK_METADATA_PATTERN = re.compile(
    r"^- (?P<field>[a-z][a-z0-9_]*): `(?P<value>[^`\r\n]*)`$"
)
TASK_REQUIRED_METADATA = frozenset(
    {"id", "title", "status", "repo", "created_at", "updated_at", "summary"}
)
TASK_OPTIONAL_TEXT_METADATA = frozenset(
    {
        "completion_evidence",
        "source_command",
        "execution_request",
        "execution_result",
        "execution_summary",
    }
)
TASK_OPTIONAL_BOOLEAN_METADATA = frozenset(
    {
        "execution_candidate",
        "executed",
        "success",
        "dry_run",
    }
)
TASK_OPTIONAL_TIMESTAMP_METADATA = frozenset({"execution_updated_at"})
TASK_ALLOWED_METADATA = TASK_REQUIRED_METADATA.union(
    TASK_OPTIONAL_TEXT_METADATA,
    TASK_OPTIONAL_BOOLEAN_METADATA,
    TASK_OPTIONAL_TIMESTAMP_METADATA,
)
TASK_ALLOWED_STATUSES = frozenset(
    {"NEEDS_APPROVAL", "BLOCKED", "ON_HOLD", "FAILED", "DOING", "TODO", "DONE"}
)


@dataclass
class TaskFileWriteResult:
    result_type: str  # "created" | "would_create" | "hold" | "error"
    file_path: str | None = None
    task_id: str | None = None
    summary: str | None = None
    reason: str | None = None
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": self.result_type,
            "file_path": self.file_path,
            "task_id": self.task_id,
            "summary": self.summary,
            "reason": self.reason,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TaskStatusTransitionResult:
    result_type: str
    reason: str | None = None
    task_id: str | None = None
    previous_status: str | None = None
    current_status: str | None = None
    updated_at: str | None = None
    file_path: str | None = None


@dataclass(frozen=True)
class CompletionEvidenceWriteResult:
    result_type: str
    reason: str | None = None
    task_id: str | None = None
    title: str | None = None
    current_status: str | None = None
    completion_evidence: str | None = None
    updated_at: str | None = None
    file_path: str | None = None


def _normalize_spaces(text: str) -> str:
    return " ".join(str(text).strip().split())


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _slugify(title: str) -> str:
    lowered = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    slug = slug.strip("-")
    return slug or FALLBACK_SLUG


def _metadata_text_error(
    field_name: str,
    value: Any,
    *,
    max_chars: int,
    required: bool = True,
) -> str | None:
    if not isinstance(value, str):
        return f"invalid_field_type:{field_name}"
    if required and not value.strip():
        return f"missing_required_field:{field_name}"
    if not value and not required:
        return None
    if "\r" in value or "\n" in value:
        return f"unsafe_metadata_newline:{field_name}"
    if "`" in value:
        return f"unsafe_markdown_delimiter:{field_name}"
    if any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for character in value
    ):
        return f"unsafe_control_character:{field_name}"
    if len(_normalize_spaces(value)) > max_chars:
        return f"field_too_long:{field_name}"
    return None


def _existing_task_numbers(tasks_dir: Path) -> list[int]:
    numbers: list[int] = []
    for path in tasks_dir.iterdir():
        if not path.is_file():
            continue
        matched = TASK_FILE_PATTERN.match(path.name)
        if not matched:
            continue
        numbers.append(int(matched.group(1)))
    return sorted(numbers)


def _render_task_markdown(
    task_id: str,
    title: str,
    repo: str,
    summary: str,
    created_at: str,
    updated_at: str,
    source_command: str | None,
) -> str:
    lines = [
        f"# {task_id}",
        "",
        f"- id: `{task_id}`",
        f"- title: `{title}`",
        f"- status: `{DEFAULT_STATUS}`",
        f"- repo: `{repo}`",
        f"- created_at: `{created_at}`",
        f"- updated_at: `{updated_at}`",
        f"- summary: `{summary}`",
    ]
    if source_command:
        lines.append(f"- source_command: `{source_command}`")
    lines.append("")
    return "\n".join(lines)


def _open_attempt_temp_file(path: Path) -> TextIO:
    return path.open("x", encoding="utf-8", newline="\n")


def _publish_attempt_temp_file(temp_path: Path, target_path: Path) -> None:
    os.link(temp_path, target_path)


def _clean_attempt_temp_file(temp_path: Path) -> None:
    try:
        temp_path.unlink(missing_ok=True)
    except OSError:
        # The final task path is never removed here. A locked temporary file may
        # remain for manual cleanup, but it cannot be parsed as a task file.
        pass


def _write_failure_atomic(
    *,
    target_path: Path,
    content: str,
    open_temp_file: Callable[[Path], TextIO],
    publish_temp_file: Callable[[Path, Path], None],
    temp_token_factory: Callable[[], str],
) -> tuple[str, str | None]:
    """Write, sync, close, then atomically publish without overwriting."""

    temp_path: Path | None = None
    temp_file: TextIO | None = None
    for _ in range(8):
        token = str(temp_token_factory())
        if not re.fullmatch(r"[a-f0-9]{16,64}", token):
            continue
        candidate_path = target_path.parent / f".{target_path.name}.{token}.tmp"
        try:
            temp_file = open_temp_file(candidate_path)
        except FileExistsError:
            continue
        except OSError:
            return "error", "task_file_temp_create_failed"
        temp_path = candidate_path
        break

    if temp_path is None or temp_file is None:
        return "error", "task_file_temp_allocation_failed"

    try:
        try:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        finally:
            temp_file.close()
    except (OSError, UnicodeError):
        _clean_attempt_temp_file(temp_path)
        return "error", "task_file_write_failed"

    try:
        publish_temp_file(temp_path, target_path)
    except FileExistsError:
        _clean_attempt_temp_file(temp_path)
        return "collision", None
    except OSError:
        _clean_attempt_temp_file(temp_path)
        return "error", "task_file_publish_failed"

    _clean_attempt_temp_file(temp_path)
    return "created", None


def _validate_draft(task_draft: dict[str, Any]) -> tuple[bool, str | None]:
    for field_name, max_chars, required in (
        ("title", MAX_TITLE_CHARS, True),
        ("repo", MAX_REPO_CHARS, True),
        ("summary", MAX_SUMMARY_CHARS, True),
        ("source_command", MAX_SOURCE_COMMAND_CHARS, False),
    ):
        error = _metadata_text_error(
            field_name,
            task_draft.get(field_name, ""),
            max_chars=max_chars,
            required=required,
        )
        if error:
            return False, error

    title = _normalize_spaces(task_draft.get("title", ""))
    repo = _normalize_spaces(task_draft.get("repo", ""))
    summary = _normalize_spaces(task_draft.get("summary", ""))
    status = _normalize_spaces(task_draft.get("status", ""))

    if not isinstance(task_draft.get("status", ""), str):
        return False, "invalid_field_type:status"
    if status and status != DEFAULT_STATUS:
        return False, "invalid_status_for_creation:only_TODO_allowed"

    return True, None


def write_task_file(
    task_draft: dict[str, Any],
    tasks_dir: Path = DEFAULT_TASKS_DIR,
    *,
    _open_temp_file: Callable[[Path], TextIO] = _open_attempt_temp_file,
    _publish_temp_file: Callable[[Path, Path], None] = _publish_attempt_temp_file,
    _temp_token_factory: Callable[[], str] = lambda: secrets.token_hex(8),
) -> TaskFileWriteResult:
    """Create one task markdown file from task draft object.

    The function never overwrites an existing file.
    """
    is_valid, reason = _validate_draft(task_draft)
    if not is_valid:
        return TaskFileWriteResult(result_type="hold", reason=reason)

    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return TaskFileWriteResult(result_type="error", reason="tasks_dir_not_found")

    title = _normalize_spaces(task_draft["title"])
    repo = _normalize_spaces(task_draft["repo"])
    summary = _normalize_spaces(task_draft["summary"])
    source_command = _normalize_spaces(task_draft.get("source_command", "")) or None

    slug = _slugify(title)
    existing_numbers = _existing_task_numbers(tasks_dir)
    next_number = (max(existing_numbers) + 1) if existing_numbers else 1
    if next_number > MAX_TASK_NUMBER:
        return TaskFileWriteResult(result_type="error", reason="task_number_limit_reached")

    # Safe retry for rare filename conflicts (concurrent write, manual file creation, etc.)
    max_retries = 10
    for _ in range(max_retries):
        if next_number > MAX_TASK_NUMBER:
            return TaskFileWriteResult(result_type="error", reason="task_number_limit_reached")
        task_id = f"task-{next_number:04d}-{slug}"
        file_name = f"{task_id}.md"
        target_path = tasks_dir / file_name

        if target_path.exists():
            next_number += 1
            continue

        now_utc = _utc_now()
        content = _render_task_markdown(
            task_id=task_id,
            title=title,
            repo=repo,
            summary=summary,
            created_at=now_utc,
            updated_at=now_utc,
            source_command=source_command,
        )

        publish_result, publish_reason = _write_failure_atomic(
            target_path=target_path,
            content=content,
            open_temp_file=_open_temp_file,
            publish_temp_file=_publish_temp_file,
            temp_token_factory=_temp_token_factory,
        )
        if publish_result == "collision":
            next_number += 1
            continue
        if publish_result != "created":
            return TaskFileWriteResult(result_type="error", reason=publish_reason)

        return TaskFileWriteResult(
            result_type="created",
            file_path=str(target_path),
            task_id=task_id,
            summary="task file created",
            created_at=now_utc,
        )

    return TaskFileWriteResult(result_type="error", reason="failed_to_allocate_task_number")


def preview_task_file_write(
    task_draft: dict[str, Any], tasks_dir: Path = DEFAULT_TASKS_DIR
) -> TaskFileWriteResult:
    """Preview task file creation result without creating a file."""
    is_valid, reason = _validate_draft(task_draft)
    if not is_valid:
        return TaskFileWriteResult(result_type="hold", reason=reason)

    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return TaskFileWriteResult(result_type="error", reason="tasks_dir_not_found")

    title = _normalize_spaces(task_draft["title"])
    slug = _slugify(title)
    existing_numbers = _existing_task_numbers(tasks_dir)
    next_number = (max(existing_numbers) + 1) if existing_numbers else 1
    if next_number > MAX_TASK_NUMBER:
        return TaskFileWriteResult(result_type="error", reason="task_number_limit_reached")

    # Same allocation policy as write_task_file, but no write side effect.
    max_retries = 10
    for _ in range(max_retries):
        if next_number > MAX_TASK_NUMBER:
            return TaskFileWriteResult(result_type="error", reason="task_number_limit_reached")
        task_id = f"task-{next_number:04d}-{slug}"
        file_name = f"{task_id}.md"
        target_path = tasks_dir / file_name
        if target_path.exists():
            next_number += 1
            continue
        return TaskFileWriteResult(
            result_type="would_create",
            file_path=str(target_path),
            task_id=task_id,
            summary="task file would be created (dry-run)",
        )

    return TaskFileWriteResult(result_type="error", reason="failed_to_allocate_task_number")


def _transition_timestamp_is_valid(value: str) -> bool:
    try:
        parsed = datetime.strptime(value, TASK_TIMESTAMP_FORMAT)
    except ValueError:
        return False
    return parsed.strftime(TASK_TIMESTAMP_FORMAT) == value


def _transition_text_is_valid(
    value: str,
    *,
    max_chars: int,
    allow_empty: bool,
) -> tuple[bool, str | None]:
    if len(value) > max_chars:
        return False, "task_file_field_too_long"
    if any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for character in value
    ):
        return False, "task_file_invalid_text"
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if not allow_empty and not normalized:
        return False, "task_file_invalid_text"
    return True, None


def _transition_metadata(
    raw: bytes,
    file_name: str,
) -> tuple[dict[str, str] | None, str | None]:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None, "task_file_invalid_utf8"
    metadata: dict[str, str] = {}
    metadata_line_indexes: dict[str, int] = {}
    # task-0054: metadata is the header block, not "every line starting with -".
    #
    # The previous rule tested line.lstrip().startswith("- "), so it claimed every
    # bullet anywhere in the file - a prose list in the body, and the indented
    # "- 규칙:" note this repository's own task-template.md puts under each field.
    # That rejected the documented template and most real task records, which only
    # surfaced once task-0052 routed approvals through this writer.
    #
    # Only the boundary moves here. Every field inside the block is validated
    # exactly as before: vocabulary, types, lengths, allow_empty and the control
    # character rules below are untouched, and a malformed field inside the block
    # still fails.
    in_header = False
    for line_index, line in enumerate(text.splitlines()):
        # An indented line continues the field above it, so it is neither a metadata
        # line nor a terminator.
        if line[:1].isspace():
            continue
        if not in_header:
            if not line.startswith("- "):
                # Title, HTML comments and blank lines sit above the block.
                continue
            in_header = True
        elif not line.startswith("- "):
            # The first column-0 line that is not a field closes the header block.
            # Everything after it is document body and is not task metadata.
            break
        matched = TASK_METADATA_PATTERN.fullmatch(line)
        if matched is None:
            return None, "task_file_invalid_metadata"
        field_name = matched.group("field")
        if field_name not in TASK_ALLOWED_METADATA:
            return None, "task_file_unsupported_metadata"
        if field_name in metadata:
            return None, "task_file_duplicate_metadata"
        metadata[field_name] = matched.group("value")
        metadata_line_indexes[field_name] = line_index
    if not TASK_REQUIRED_METADATA.issubset(metadata):
        return None, "task_file_missing_metadata"
    task_id = metadata["id"]
    if not TASK_FILE_PATTERN.fullmatch(f"{task_id}.md"):
        return None, "task_file_invalid_id"
    if f"{task_id}.md" != file_name:
        return None, "task_id_path_mismatch"
    if metadata["status"] not in TASK_ALLOWED_STATUSES:
        return None, "task_file_invalid_status"
    if (
        "completion_evidence" in metadata
        and metadata_line_indexes["completion_evidence"]
        != metadata_line_indexes["summary"] + 1
    ):
        return None, "task_file_invalid_completion_evidence_metadata"
    for field_name in ("created_at", "updated_at"):
        if not _transition_timestamp_is_valid(metadata[field_name]):
            return None, "task_file_invalid_updated_at"
    for field_name, max_chars in (
        ("repo", MAX_REPO_CHARS),
        ("title", MAX_TITLE_CHARS),
        ("summary", MAX_SUMMARY_CHARS),
    ):
        valid, reason = _transition_text_is_valid(
            metadata[field_name],
            max_chars=max_chars,
            allow_empty=False,
        )
        if not valid:
            return None, reason
    for field_name in TASK_OPTIONAL_TEXT_METADATA:
        if field_name not in metadata:
            continue
        valid, reason = _transition_text_is_valid(
            metadata[field_name],
            max_chars=500,
            allow_empty=False,
        )
        if not valid:
            return None, reason
    for field_name in TASK_OPTIONAL_BOOLEAN_METADATA:
        if field_name in metadata and metadata[field_name] not in {"true", "false"}:
            return None, "task_file_invalid_text"
    if (
        "execution_updated_at" in metadata
        and metadata["execution_updated_at"]
        and not _transition_timestamp_is_valid(metadata["execution_updated_at"])
    ):
        return None, "task_file_invalid_updated_at"
    return metadata, None


def _open_transition_temp_file(path: Path) -> BinaryIO:
    return path.open("xb")


def _replace_transition_file(temp_path: Path, target_path: Path) -> None:
    os.replace(temp_path, target_path)


def _atomically_replace_task_file(
    *,
    target_path: Path,
    updated: bytes,
    expected_digest: str,
    temp_suffix: str,
    open_temp_file: Callable[[Path], BinaryIO],
    replace_file: Callable[[Path, Path], None],
    fsync_file: Callable[[int], None],
    temp_token_factory: Callable[[], str],
    before_final_check: Callable[[Path], None] | None = None,
) -> tuple[bool, str | None]:
    """Write `updated` over `target_path` atomically, or leave the file untouched.

    task-0055: extracted from transition_task_file_status() and
    record_task_completion_evidence(), which carried the same 78 and 91 line tail at
    73% similarity - the differences were the temp suffix, the result type and the
    reason prefix. A third copy was about to appear for the execution-result writer,
    and three copies of a durability primitive drift; the drifting copy is the one
    nobody notices.

    Returns (True, None) on success, or (False, key) where key is one of
    "temp_create_failed", "temp_allocation_failed", "write_failed", "flush_failed",
    "fsync_failed", "close_failed", "replace_failed" or "stale". Callers add their
    own prefix, so their reason codes are unchanged.

    One behaviour is deliberately levelled up rather than preserved twice over:
    record_task_completion_evidence() checked for a short write and
    transition_task_file_status() did not. The helper keeps the check, so the
    transition path gains it. That is a strengthening, not a regression, and it is
    called out here rather than buried.
    """

    temp_path: Path | None = None
    temp_file: BinaryIO | None = None
    for _ in range(8):
        token = str(temp_token_factory())
        if not re.fullmatch(r"[a-f0-9]{16,64}", token):
            continue
        candidate_path = target_path.parent / f".{target_path.name}.{token}.{temp_suffix}.tmp"
        try:
            temp_file = open_temp_file(candidate_path)
        except FileExistsError:
            continue
        except OSError:
            return False, "temp_create_failed"
        temp_path = candidate_path
        break
    if temp_path is None or temp_file is None:
        return False, "temp_allocation_failed"

    failure_reason: str | None = None
    try:
        try:
            written = temp_file.write(updated)
            if written != len(updated):
                failure_reason = "write_failed"
        except (OSError, UnicodeError):
            failure_reason = "write_failed"
        if failure_reason is None:
            try:
                temp_file.flush()
            except OSError:
                failure_reason = "flush_failed"
        if failure_reason is None:
            try:
                fsync_file(temp_file.fileno())
            except OSError:
                failure_reason = "fsync_failed"
        try:
            temp_file.close()
        except OSError:
            failure_reason = failure_reason or "close_failed"
        if failure_reason is not None:
            return False, failure_reason

        if before_final_check is not None:
            before_final_check(target_path)
        # The digest is compared once more here, immediately before the replace, so a
        # file changed since the caller read it is never overwritten.
        try:
            final_original = target_path.read_bytes()
        except OSError:
            return False, "stale"
        if not hmac.compare_digest(
            hashlib.sha256(final_original).hexdigest(),
            expected_digest,
        ):
            return False, "stale"
        try:
            replace_file(temp_path, target_path)
        except OSError:
            return False, "replace_failed"
        temp_path = None
    finally:
        try:
            if temp_file is not None and not temp_file.closed:
                temp_file.close()
        except OSError:
            pass
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    return True, None


def transition_task_file_status(
    *,
    tasks_dir: Path,
    task_id: str,
    expected_digest: str,
    current_status: str,
    target_status: str,
    planned_updated_at: str,
    _open_temp_file: Callable[[Path], BinaryIO] = _open_transition_temp_file,
    _replace_file: Callable[[Path, Path], None] = _replace_transition_file,
    _fsync_file: Callable[[int], None] = os.fsync,
    _temp_token_factory: Callable[[], str] = lambda: secrets.token_hex(8),
    _before_final_check: Callable[[Path], None] | None = None,
) -> TaskStatusTransitionResult:
    """Atomically replace only status and updated_at for one direct-child Task."""

    if not TASK_FILE_PATTERN.fullmatch(f"{task_id}.md"):
        return TaskStatusTransitionResult("hold", "invalid_task_id")
    if (current_status, target_status) not in TASK_STATUS_TRANSITIONS:
        return TaskStatusTransitionResult("hold", "invalid_task_transition")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_digest):
        return TaskStatusTransitionResult("hold", "invalid_expected_digest")
    try:
        parsed_time = datetime.strptime(planned_updated_at, TASK_TIMESTAMP_FORMAT)
    except ValueError:
        return TaskStatusTransitionResult("hold", "invalid_planned_updated_at")
    if parsed_time.strftime(TASK_TIMESTAMP_FORMAT) != planned_updated_at:
        return TaskStatusTransitionResult("hold", "invalid_planned_updated_at")
    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return TaskStatusTransitionResult("error", "tasks_dir_not_found")

    resolved_tasks_dir = tasks_dir.resolve()
    target_path = (tasks_dir / f"{task_id}.md").resolve()
    if target_path.parent != resolved_tasks_dir:
        return TaskStatusTransitionResult("hold", "task_path_not_direct_child")

    try:
        original = target_path.read_bytes()
    except OSError:
        return TaskStatusTransitionResult("stale", "task_changed_since_preview")
    if not hmac.compare_digest(hashlib.sha256(original).hexdigest(), expected_digest):
        return TaskStatusTransitionResult("stale", "task_changed_since_preview")

    metadata, metadata_error = _transition_metadata(original, target_path.name)
    if metadata is None:
        return TaskStatusTransitionResult("hold", metadata_error)
    if metadata["id"] != task_id:
        return TaskStatusTransitionResult("hold", "task_id_path_mismatch")
    if metadata["status"] != current_status:
        return TaskStatusTransitionResult("stale", "task_changed_since_preview")

    status_pattern = re.compile(
        rb"(?m)^- status: `[^`\r\n]*`(?=\r?$)"
    )
    updated_pattern = re.compile(
        rb"(?m)^- updated_at: `[^`\r\n]*`(?=\r?$)"
    )
    if len(status_pattern.findall(original)) != 1:
        return TaskStatusTransitionResult("hold", "task_file_invalid_status_metadata")
    if len(updated_pattern.findall(original)) != 1:
        return TaskStatusTransitionResult("hold", "task_file_invalid_updated_at_metadata")
    updated = status_pattern.sub(
        f"- status: `{target_status}`".encode("ascii"),
        original,
        count=1,
    )
    updated = updated_pattern.sub(
        f"- updated_at: `{planned_updated_at}`".encode("ascii"),
        updated,
        count=1,
    )

    ok, failure = _atomically_replace_task_file(
        target_path=target_path,
        updated=updated,
        expected_digest=expected_digest,
        temp_suffix="transition",
        open_temp_file=_open_temp_file,
        replace_file=_replace_file,
        fsync_file=_fsync_file,
        temp_token_factory=_temp_token_factory,
        before_final_check=_before_final_check,
    )
    if not ok:
        if failure == "stale":
            return TaskStatusTransitionResult("stale", "task_changed_since_preview")
        return TaskStatusTransitionResult("error", f"task_transition_{failure}")

    return TaskStatusTransitionResult(
        "updated",
        task_id=task_id,
        previous_status=current_status,
        current_status=target_status,
        updated_at=planned_updated_at,
        file_path=str(target_path),
    )


@dataclass(frozen=True)
class TaskExecutionResultWriteResult:
    result_type: str
    reason: str | None = None
    task_id: str | None = None
    previous_status: str | None = None
    current_status: str | None = None
    updated_at: str | None = None
    file_path: str | None = None


TASK_EXECUTION_METADATA_FIELDS = (
    "execution_candidate",
    "execution_request",
    "execution_result",
    "executed",
    "success",
    "dry_run",
    "execution_updated_at",
    "execution_summary",
)


def _execution_field_line_pattern(field_name: str) -> re.Pattern[bytes]:
    return re.compile(
        rb"(?m)^- " + re.escape(field_name.encode("ascii")) + rb": `[^`\r\n]*`(?=\r?$)"
    )


def _execution_header_block_end(raw: bytes) -> int:
    """Byte offset just past the metadata header block.

    Mirrors _transition_metadata()'s boundary from task-0054: indented lines
    continue the field above them, the block opens at the first column-0 field and
    closes at the first column-0 line that is not one. Execution fields belong
    inside it, because outside it they are invisible to the validator while still
    visible to /status - the asymmetry task-0053 closed.
    """

    offset = 0
    started = False
    end = len(raw)
    for line in raw.splitlines(keepends=True):
        stripped = line.rstrip(b"\r\n")
        if stripped[:1].isspace():
            offset += len(line)
            continue
        if not started:
            if not stripped.startswith(b"- "):
                offset += len(line)
                continue
            started = True
        elif not stripped.startswith(b"- "):
            return offset
        offset += len(line)
        end = offset
    return end


def record_task_execution_result(
    *,
    tasks_dir: Path,
    task_id: str,
    expected_digest: str,
    execution_fields: Mapping[str, str],
    planned_updated_at: str,
    current_status: str | None = None,
    target_status: str | None = None,
    _open_temp_file: Callable[[Path], BinaryIO] = _open_transition_temp_file,
    _replace_file: Callable[[Path, Path], None] = _replace_transition_file,
    _fsync_file: Callable[[int], None] = os.fsync,
    _temp_token_factory: Callable[[], str] = lambda: secrets.token_hex(8),
    _before_final_check: Callable[[Path], None] | None = None,
) -> TaskExecutionResultWriteResult:
    """Write the execution metadata and, optionally, the resulting status in one replace.

    task-0055 (U2). These used to be two writes: a bare write_text() for the metadata
    and a durable transition after it. Interrupted between them, the file kept a
    finished execution beside an unfinished task - measured as execution_status
    "success" while the task still read DOING, a combination a completed flow cannot
    produce and which nothing detects, because the file validates fine.

    target_status is optional on purpose. An execution that never ran - a target that
    is not whitelisted, say - writes its metadata and performs no transition, and
    that pairing (execution_status "not_executed" with the task still DOING) is
    correct rather than broken. Forcing a transition here would break the ordinary
    case in order to fix the rare one.

    The whole file is validated before the write, and the execution values are
    validated too, because unlike a status enum they arrive from subprocess output.
    Nothing about the canonical rules is relaxed to let them through.
    """

    if not TASK_FILE_PATTERN.fullmatch(f"{task_id}.md"):
        return TaskExecutionResultWriteResult("hold", "invalid_task_id")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_digest):
        return TaskExecutionResultWriteResult("hold", "invalid_expected_digest")
    if (target_status is None) != (current_status is None):
        return TaskExecutionResultWriteResult("hold", "invalid_transition_pair")
    if target_status is not None and (current_status, target_status) not in TASK_STATUS_TRANSITIONS:
        return TaskExecutionResultWriteResult("hold", "invalid_task_transition")
    try:
        parsed_time = datetime.strptime(planned_updated_at, TASK_TIMESTAMP_FORMAT)
    except ValueError:
        return TaskExecutionResultWriteResult("hold", "invalid_planned_updated_at")
    if parsed_time.strftime(TASK_TIMESTAMP_FORMAT) != planned_updated_at:
        return TaskExecutionResultWriteResult("hold", "invalid_planned_updated_at")
    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return TaskExecutionResultWriteResult("error", "tasks_dir_not_found")

    resolved_tasks_dir = tasks_dir.resolve()
    target_path = (tasks_dir / f"{task_id}.md").resolve()
    if target_path.parent != resolved_tasks_dir:
        return TaskExecutionResultWriteResult("hold", "task_path_not_direct_child")

    unknown = [name for name in execution_fields if name not in TASK_EXECUTION_METADATA_FIELDS]
    if unknown:
        return TaskExecutionResultWriteResult("hold", "unsupported_execution_field")

    try:
        original = target_path.read_bytes()
    except OSError:
        return TaskExecutionResultWriteResult("stale", "task_changed_since_preview")
    if not hmac.compare_digest(hashlib.sha256(original).hexdigest(), expected_digest):
        return TaskExecutionResultWriteResult("stale", "task_changed_since_preview")

    metadata, metadata_error = _transition_metadata(original, target_path.name)
    if metadata is None:
        return TaskExecutionResultWriteResult("hold", metadata_error)
    if metadata["id"] != task_id:
        return TaskExecutionResultWriteResult("hold", "task_id_path_mismatch")
    if current_status is not None and metadata["status"] != current_status:
        return TaskExecutionResultWriteResult("stale", "task_changed_since_preview")

    # Validate the values before writing them. transition_task_file_status can skip
    # this because a status enum and a timestamp are already checked by the time it
    # runs; an execution summary is whatever the subprocess printed.
    for field_name, value in execution_fields.items():
        if field_name in TASK_OPTIONAL_BOOLEAN_METADATA:
            if value not in {"true", "false"}:
                return TaskExecutionResultWriteResult("hold", "task_file_invalid_text")
            continue
        if field_name in TASK_OPTIONAL_TIMESTAMP_METADATA:
            if not _transition_timestamp_is_valid(value):
                return TaskExecutionResultWriteResult("hold", "task_file_invalid_updated_at")
            continue
        valid, reason = _transition_text_is_valid(value, max_chars=500, allow_empty=False)
        if not valid:
            return TaskExecutionResultWriteResult("hold", reason)

    updated = original
    insertions: list[bytes] = []
    for field_name in TASK_EXECUTION_METADATA_FIELDS:
        if field_name not in execution_fields:
            continue
        line = f"- {field_name}: `{execution_fields[field_name]}`".encode("utf-8")
        pattern = _execution_field_line_pattern(field_name)
        matches = pattern.findall(updated)
        if len(matches) > 1:
            return TaskExecutionResultWriteResult("hold", "task_file_duplicate_metadata")
        if matches:
            # Replace wherever it already sits, including below the body in a file
            # written before task-0053 moved the insertion point. Inserting a second
            # copy in the header would make the file fail validation outright.
            updated = pattern.sub(line, updated, count=1)
        else:
            insertions.append(line)

    if insertions:
        eol = b"\r\n" if b"\r\n" in original else b"\n"
        block = b"".join(insertion + eol for insertion in insertions)
        end = _execution_header_block_end(updated)
        updated = updated[:end] + block + updated[end:]

    if target_status is not None:
        status_pattern = re.compile(rb"(?m)^- status: `[^`\r\n]*`(?=\r?$)")
        if len(status_pattern.findall(updated)) != 1:
            return TaskExecutionResultWriteResult("hold", "task_file_invalid_status_metadata")
        updated = status_pattern.sub(
            f"- status: `{target_status}`".encode("ascii"), updated, count=1
        )

    updated_pattern = re.compile(rb"(?m)^- updated_at: `[^`\r\n]*`(?=\r?$)")
    if len(updated_pattern.findall(updated)) != 1:
        return TaskExecutionResultWriteResult("hold", "task_file_invalid_updated_at_metadata")
    updated = updated_pattern.sub(
        f"- updated_at: `{planned_updated_at}`".encode("ascii"), updated, count=1
    )

    # The result must satisfy the same validator the original did - the write is
    # atomic, so a file that would not validate must never reach disk.
    result_metadata, result_error = _transition_metadata(updated, target_path.name)
    if result_metadata is None:
        return TaskExecutionResultWriteResult("hold", result_error)

    ok, failure = _atomically_replace_task_file(
        target_path=target_path,
        updated=updated,
        expected_digest=expected_digest,
        temp_suffix="execution",
        open_temp_file=_open_temp_file,
        replace_file=_replace_file,
        fsync_file=_fsync_file,
        temp_token_factory=_temp_token_factory,
        before_final_check=_before_final_check,
    )
    if not ok:
        if failure == "stale":
            return TaskExecutionResultWriteResult("stale", "task_changed_since_preview")
        return TaskExecutionResultWriteResult("error", f"task_execution_{failure}")

    return TaskExecutionResultWriteResult(
        "recorded",
        task_id=task_id,
        previous_status=current_status or metadata["status"],
        current_status=target_status or metadata["status"],
        updated_at=planned_updated_at,
        file_path=str(target_path),
    )


def _completion_evidence_is_valid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value or len(value) > MAX_COMPLETION_EVIDENCE_CHARS:
        return False
    if "`" in value or "\x00" in value:
        return False
    if any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for character in value
    ):
        return False
    return value == " ".join(unicodedata.normalize("NFC", value).strip().split())


def record_task_completion_evidence(
    *,
    tasks_dir: Path,
    task_id: str,
    completion_evidence: str,
    expected_digest: str,
    planned_updated_at: str,
    _open_temp_file: Callable[[Path], BinaryIO] = _open_transition_temp_file,
    _replace_file: Callable[[Path, Path], None] = _replace_transition_file,
    _fsync_file: Callable[[int], None] = os.fsync,
    _temp_token_factory: Callable[[], str] = lambda: secrets.token_hex(8),
    _before_final_check: Callable[[Path], None] | None = None,
) -> CompletionEvidenceWriteResult:
    """Append evidence once and update only updated_at for one DOING Task."""

    if not TASK_FILE_PATTERN.fullmatch(f"{task_id}.md"):
        return CompletionEvidenceWriteResult("hold", "invalid_task_id")
    if not _completion_evidence_is_valid(completion_evidence):
        return CompletionEvidenceWriteResult("hold", "invalid_completion_evidence")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_digest):
        return CompletionEvidenceWriteResult("hold", "invalid_expected_digest")
    try:
        parsed_time = datetime.strptime(planned_updated_at, TASK_TIMESTAMP_FORMAT)
    except ValueError:
        return CompletionEvidenceWriteResult("hold", "invalid_planned_updated_at")
    if parsed_time.strftime(TASK_TIMESTAMP_FORMAT) != planned_updated_at:
        return CompletionEvidenceWriteResult("hold", "invalid_planned_updated_at")
    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return CompletionEvidenceWriteResult("error", "tasks_dir_not_found")

    resolved_tasks_dir = tasks_dir.resolve()
    target_path = (tasks_dir / f"{task_id}.md").resolve()
    if target_path.parent != resolved_tasks_dir:
        return CompletionEvidenceWriteResult("hold", "task_path_not_direct_child")

    try:
        original = target_path.read_bytes()
    except OSError:
        return CompletionEvidenceWriteResult("stale", "task_changed_since_preview")
    if not hmac.compare_digest(hashlib.sha256(original).hexdigest(), expected_digest):
        return CompletionEvidenceWriteResult("stale", "task_changed_since_preview")

    metadata, metadata_error = _transition_metadata(original, target_path.name)
    if metadata is None:
        return CompletionEvidenceWriteResult("hold", metadata_error)
    if metadata["id"] != task_id:
        return CompletionEvidenceWriteResult("hold", "task_id_path_mismatch")
    if metadata["status"] != "DOING":
        return CompletionEvidenceWriteResult("hold", "task_not_doing")
    if "completion_evidence" in metadata:
        return CompletionEvidenceWriteResult("hold", "completion_evidence_already_exists")

    summary_pattern = re.compile(
        rb"(?m)^- summary: `[^`\r\n]*`(?P<eol>\r?\n|$)"
    )
    updated_pattern = re.compile(
        rb"(?m)^- updated_at: `[^`\r\n]*`(?=\r?$)"
    )
    summary_matches = list(summary_pattern.finditer(original))
    if len(summary_matches) != 1:
        return CompletionEvidenceWriteResult(
            "hold", "task_file_invalid_summary_metadata"
        )
    if len(updated_pattern.findall(original)) != 1:
        return CompletionEvidenceWriteResult(
            "hold", "task_file_invalid_updated_at_metadata"
        )

    summary_match = summary_matches[0]
    existing_line_ending = summary_match.group("eol")
    evidence_bytes = (
        f"- completion_evidence: `{completion_evidence}`".encode("utf-8")
    )
    evidence_line = (
        evidence_bytes + existing_line_ending
        if existing_line_ending
        else b"\n" + evidence_bytes
    )
    updated = (
        original[: summary_match.end()]
        + evidence_line
        + original[summary_match.end() :]
    )
    updated = updated_pattern.sub(
        f"- updated_at: `{planned_updated_at}`".encode("ascii"),
        updated,
        count=1,
    )

    ok, failure = _atomically_replace_task_file(
        target_path=target_path,
        updated=updated,
        expected_digest=expected_digest,
        temp_suffix="evidence",
        open_temp_file=_open_temp_file,
        replace_file=_replace_file,
        fsync_file=_fsync_file,
        temp_token_factory=_temp_token_factory,
        before_final_check=_before_final_check,
    )
    if not ok:
        if failure == "stale":
            return CompletionEvidenceWriteResult("stale", "task_changed_since_preview")
        return CompletionEvidenceWriteResult("error", f"completion_evidence_{failure}")

    return CompletionEvidenceWriteResult(
        "recorded",
        task_id=task_id,
        title=metadata["title"],
        current_status="DOING",
        completion_evidence=completion_evidence,
        updated_at=planned_updated_at,
        file_path=str(target_path),
    )


def main() -> None:
    # Local runnable examples (1 invalid input included)
    samples = [
        {
            "title": "보고 시스템 개선",
            "status": "TODO",
            "repo": "jarvis-core",
            "summary": "보고 체계 문서 구조를 개선하는 task 파일을 생성한다.",
            "source_command": "/task 보고 시스템 개선",
        },
        {
            "title": "parser output 검증 규칙 보강",
            "status": "TODO",
            "repo": "jarvis-core",
            "summary": "파서 결과의 누락/형식 오류 검증 규칙을 명확히 한다.",
            "source_command": "/task parser output 검증 규칙 보강",
        },
        {
            "title": "   ",
            "status": "TODO",
            "repo": "jarvis-core",
            "summary": "잘못된 입력 예시",
        },
    ]

    for draft in samples:
        result = write_task_file(draft)
        print(json.dumps({"input": draft, "output": result.to_dict()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
