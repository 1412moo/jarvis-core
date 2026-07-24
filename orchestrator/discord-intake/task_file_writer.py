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
TASK_STATUS_TRANSITIONS = frozenset({("TODO", "DOING"), ("DOING", "DONE")})
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
    {"NEEDS_APPROVAL", "BLOCKED", "FAILED", "DOING", "TODO", "DONE"}
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
    for line_index, line in enumerate(text.splitlines()):
        if not line.lstrip().startswith("- "):
            continue
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

    temp_path: Path | None = None
    temp_file: BinaryIO | None = None
    for _ in range(8):
        token = str(_temp_token_factory())
        if not re.fullmatch(r"[a-f0-9]{16,64}", token):
            continue
        candidate_path = target_path.parent / f".{target_path.name}.{token}.transition.tmp"
        try:
            temp_file = _open_temp_file(candidate_path)
        except FileExistsError:
            continue
        except OSError:
            return TaskStatusTransitionResult("error", "task_transition_temp_create_failed")
        temp_path = candidate_path
        break
    if temp_path is None or temp_file is None:
        return TaskStatusTransitionResult("error", "task_transition_temp_allocation_failed")

    failure_reason: str | None = None
    try:
        try:
            temp_file.write(updated)
        except (OSError, UnicodeError):
            failure_reason = "task_transition_write_failed"
        if failure_reason is None:
            try:
                temp_file.flush()
            except OSError:
                failure_reason = "task_transition_flush_failed"
        if failure_reason is None:
            try:
                _fsync_file(temp_file.fileno())
            except OSError:
                failure_reason = "task_transition_fsync_failed"
        try:
            temp_file.close()
        except OSError:
            failure_reason = failure_reason or "task_transition_close_failed"
        if failure_reason is not None:
            return TaskStatusTransitionResult("error", failure_reason)

        if _before_final_check is not None:
            _before_final_check(target_path)
        try:
            final_original = target_path.read_bytes()
        except OSError:
            return TaskStatusTransitionResult("stale", "task_changed_since_preview")
        if not hmac.compare_digest(
            hashlib.sha256(final_original).hexdigest(),
            expected_digest,
        ):
            return TaskStatusTransitionResult("stale", "task_changed_since_preview")
        try:
            _replace_file(temp_path, target_path)
        except OSError:
            return TaskStatusTransitionResult("error", "task_transition_replace_failed")
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

    return TaskStatusTransitionResult(
        "updated",
        task_id=task_id,
        previous_status=current_status,
        current_status=target_status,
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

    temp_path: Path | None = None
    temp_file: BinaryIO | None = None
    for _ in range(8):
        token = str(_temp_token_factory())
        if not re.fullmatch(r"[a-f0-9]{16,64}", token):
            continue
        candidate_path = target_path.parent / f".{target_path.name}.{token}.evidence.tmp"
        try:
            temp_file = _open_temp_file(candidate_path)
        except FileExistsError:
            continue
        except OSError:
            return CompletionEvidenceWriteResult(
                "error", "completion_evidence_temp_create_failed"
            )
        temp_path = candidate_path
        break
    if temp_path is None or temp_file is None:
        return CompletionEvidenceWriteResult(
            "error", "completion_evidence_temp_allocation_failed"
        )

    failure_reason: str | None = None
    try:
        try:
            written = temp_file.write(updated)
            if written != len(updated):
                failure_reason = "completion_evidence_write_failed"
        except (OSError, UnicodeError):
            failure_reason = "completion_evidence_write_failed"
        if failure_reason is None:
            try:
                temp_file.flush()
            except OSError:
                failure_reason = "completion_evidence_flush_failed"
        if failure_reason is None:
            try:
                _fsync_file(temp_file.fileno())
            except OSError:
                failure_reason = "completion_evidence_fsync_failed"
        try:
            temp_file.close()
        except OSError:
            failure_reason = failure_reason or "completion_evidence_close_failed"
        if failure_reason is not None:
            return CompletionEvidenceWriteResult("error", failure_reason)

        if _before_final_check is not None:
            _before_final_check(target_path)
        try:
            final_original = target_path.read_bytes()
        except OSError:
            return CompletionEvidenceWriteResult(
                "stale", "task_changed_since_preview"
            )
        if not hmac.compare_digest(
            hashlib.sha256(final_original).hexdigest(),
            expected_digest,
        ):
            return CompletionEvidenceWriteResult(
                "stale", "task_changed_since_preview"
            )
        try:
            _replace_file(temp_path, target_path)
        except OSError:
            return CompletionEvidenceWriteResult(
                "error", "completion_evidence_replace_failed"
            )
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
