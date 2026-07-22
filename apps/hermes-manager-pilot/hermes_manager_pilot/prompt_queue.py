"""In-memory Prompt Queue v0.1B-2 schema and safety evaluation.

This module does not read repositories, persist state, call external services, or
execute prompts.  Callers must supply observed local Git evidence explicitly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Any

from .schemas import SessionState, ValidationError, normalize_session_state


VERSION = "0.1B-2"
QUEUE_TYPE = "hermes_prompt_queue"

ALLOWED_RESULT_TYPES = frozenset(
    {"design", "implementation", "review", "commit", "blocked"}
)
REQUIRED_FORBIDDEN_ACTIONS = frozenset(
    {"auto_commit", "push", "create_pr", "external_api", "api_key_creation"}
)
RESULT_NEXT_ACTIONS = {
    "design": "STATUS_SUMMARY",
    "implementation": "PROMPT_FOR_CODEX",
    "review": "REVIEW_REQUEST",
    "commit": "COMMIT_REQUEST",
    "blocked": "BLOCKED_NEEDS_USER",
}
RESULT_RENDER_MODES = {
    "design": "checkpoint-summary",
    "implementation": "implementation-prompt",
    "review": "review-prompt",
    "commit": "commit-prompt",
    "blocked": "checkpoint-summary",
}

_MAX_PROJECTS = 32
_MAX_ITEMS = 256
_MAX_LIST_ITEMS = 128
_MAX_TEXT_LENGTH = 4096
_TRACKED_STATUS_CODES = frozenset(" MADRCU")
_WINDOWS_DRIVE = re.compile(r"^[a-zA-Z]:")

_QUEUE_FIELDS = frozenset({"queue_type", "version", "projects", "items"})
_PROJECT_FIELDS = frozenset(
    {
        "project_id",
        "display_name",
        "repo_path",
        "expected_branch",
        "expected_head",
        "protected_paths",
        "expected_untracked",
        "forbidden_actions",
        "validation_commands",
    }
)
_ITEM_FIELDS = frozenset(
    {
        "item_id",
        "project_id",
        "current_goal",
        "current_task",
        "result_type",
        "target_files",
        "observed_branch",
        "observed_head",
        "observed_git_status",
        "scope_approved",
        "review_passed",
        "commit_approved",
        "scope_approval_digest",
        "change_evidence_digest",
        "review_approval_digest",
        "commit_approval_digest",
        "commit_message",
        "last_prompt_summary",
        "last_result_summary",
    }
)


@dataclass(frozen=True)
class ProjectCard:
    """A declared project boundary; repo_path is metadata, not I/O authority."""

    project_id: str
    display_name: str
    repo_path: str
    expected_branch: str
    expected_head: str
    protected_paths: tuple[str, ...]
    expected_untracked: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    validation_commands: tuple[str, ...]


@dataclass(frozen=True)
class QueueItem:
    """One requested Prompt Queue transition with supplied Git observations."""

    item_id: str
    project_id: str
    current_goal: str
    current_task: str
    result_type: str
    target_files: tuple[str, ...]
    observed_branch: str
    observed_head: str
    observed_git_status: tuple[str, ...]
    scope_approved: bool
    review_passed: bool
    commit_approved: bool
    scope_approval_digest: str
    change_evidence_digest: str
    review_approval_digest: str
    commit_approval_digest: str
    commit_message: str
    last_prompt_summary: str
    last_result_summary: str


@dataclass(frozen=True)
class PromptQueueState:
    """A normalized, in-memory-only Prompt Queue snapshot."""

    projects: tuple[ProjectCard, ...]
    items: tuple[QueueItem, ...]
    queue_type: str = QUEUE_TYPE
    version: str = VERSION


@dataclass(frozen=True)
class QueueEvaluation:
    """Deterministic safety decision for one queue item."""

    item_id: str
    result_type: str
    next_action: str
    render_mode: str
    blocking_reasons: tuple[str, ...]
    observed_changed_files: tuple[str, ...]

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocking_reasons)


@dataclass(frozen=True)
class _StatusEntry:
    code: str
    path: str

    @property
    def is_untracked(self) -> bool:
        return self.code == "??"

    @property
    def is_staged(self) -> bool:
        return not self.is_untracked and self.code[0] != " "


def normalize_prompt_queue(data: Mapping[str, Any]) -> PromptQueueState:
    """Validate and normalize a Prompt Queue v0.1A mapping without side effects."""

    if not isinstance(data, Mapping):
        raise ValidationError("prompt queue must be a JSON object")
    _reject_unknown_fields(data, _QUEUE_FIELDS, "prompt queue")

    queue_type = _optional_text(data, "queue_type") or QUEUE_TYPE
    if queue_type != QUEUE_TYPE:
        raise ValidationError(f"queue_type must be {QUEUE_TYPE}")
    version = _optional_text(data, "version") or VERSION
    if version != VERSION:
        raise ValidationError(f"version must be {VERSION}")

    project_values = _mapping_list(data, "projects", _MAX_PROJECTS)
    item_values = _mapping_list(data, "items", _MAX_ITEMS)
    if not project_values:
        raise ValidationError("projects must include at least one project card")

    projects = tuple(_normalize_project(value, index) for index, value in enumerate(project_values))
    _reject_duplicate_values((project.project_id for project in projects), "project_id")
    project_ids = {project.project_id for project in projects}

    items = tuple(_normalize_item(value, index) for index, value in enumerate(item_values))
    _reject_duplicate_values((item.item_id for item in items), "item_id")
    for item in items:
        if item.project_id not in project_ids:
            raise ValidationError(
                f"item {item.item_id} references unknown project_id: {item.project_id}"
            )

    return PromptQueueState(
        projects=projects,
        items=items,
        queue_type=queue_type,
        version=version,
    )


def evaluate_queue_item(queue: PromptQueueState, item_id: str) -> QueueEvaluation:
    """Return a conservative local safety decision for one normalized item."""

    item = _find_item(queue, item_id)
    project = _find_project(queue, item.project_id)
    reasons: list[str] = []
    status_entries: list[_StatusEntry] = []

    if item.observed_branch != project.expected_branch:
        reasons.append(
            f"observed branch {item.observed_branch!r} does not match expected branch "
            f"{project.expected_branch!r}"
        )
    if item.observed_head != project.expected_head:
        reasons.append(
            f"observed HEAD {item.observed_head!r} does not match expected HEAD "
            f"{project.expected_head!r}"
        )

    for line in item.observed_git_status:
        try:
            status_entries.append(_parse_status_line(line))
        except ValidationError as exc:
            reasons.append(str(exc))

    observed_untracked = {entry.path for entry in status_entries if entry.is_untracked}
    expected_untracked = set(project.expected_untracked)
    for path in sorted(expected_untracked - observed_untracked):
        reasons.append(f"expected untracked path is missing: {path}")

    protected_keys = {_path_key(path) for path in project.protected_paths}
    for path in item.target_files:
        protected_overlap = tuple(
            protected
            for protected in project.protected_paths
            if _path_is_targeted(protected, (path,))
        )
        if protected_overlap:
            reasons.append(f"target file is protected: {path}")

    changed_files: list[str] = []
    for entry in status_entries:
        if entry.is_untracked:
            if entry.path in expected_untracked:
                continue
            changed_files.append(entry.path)
            path_key = _path_key(entry.path)
            if path_key in protected_keys:
                reasons.append(f"protected path is unexpectedly untracked: {entry.path}")
            elif not _path_is_targeted(entry.path, item.target_files):
                reasons.append(f"unexpected untracked path: {entry.path}")
            continue
        changed_files.append(entry.path)
        path_key = _path_key(entry.path)
        if path_key in protected_keys:
            reasons.append(f"protected path has tracked changes: {entry.path}")
        elif not _path_is_targeted(entry.path, item.target_files):
            reasons.append(f"tracked change is outside target files: {entry.path}")
        if entry.is_staged:
            reasons.append(f"staged change exists before an approved commit step: {entry.path}")

    missing_forbidden = REQUIRED_FORBIDDEN_ACTIONS - set(project.forbidden_actions)
    if missing_forbidden:
        reasons.append(
            "project card is missing forbidden actions: " + ", ".join(sorted(missing_forbidden))
        )

    if item.result_type in {"implementation", "review", "commit"} and not item.scope_approved:
        reasons.append("scope approval is required")
    if item.result_type in {"implementation", "review", "commit"} and not item.target_files:
        reasons.append("an explicit target file scope is required")
    if item.result_type in {"review", "commit"} and not changed_files:
        reasons.append("review and commit steps require observed target changes")
    if item.commit_approved and not item.review_passed:
        reasons.append("commit approval requires a passed review")
    if item.result_type == "commit":
        if not item.review_passed:
            reasons.append("commit step requires a passed review")
        if not item.commit_approved:
            reasons.append("commit step requires explicit commit approval")
        if not item.commit_message:
            reasons.append("commit step requires an approved commit message")
    elif item.commit_approved:
        reasons.append("commit approval is only valid for a commit item")
    if item.result_type == "blocked":
        reasons.append("queue item is explicitly marked blocked")

    try:
        from .approval_binding import approval_binding_blocking_reasons

        reasons.extend(approval_binding_blocking_reasons(project, item))
    except ValidationError as exc:
        reasons.append(f"approval binding validation failed: {exc}")

    blocking_reasons = _deduplicate(reasons)
    if blocking_reasons:
        result_type = "blocked"
        next_action = "BLOCKED_NEEDS_USER"
        render_mode = "checkpoint-summary"
    else:
        result_type = item.result_type
        next_action = RESULT_NEXT_ACTIONS[result_type]
        render_mode = RESULT_RENDER_MODES[result_type]

    return QueueEvaluation(
        item_id=item.item_id,
        result_type=result_type,
        next_action=next_action,
        render_mode=render_mode,
        blocking_reasons=blocking_reasons,
        observed_changed_files=tuple(changed_files),
    )


def build_hermes_session(queue: PromptQueueState, item_id: str) -> SessionState:
    """Map an evaluated item to the existing renderer contract without executing it."""

    item = _find_item(queue, item_id)
    project = _find_project(queue, item.project_id)
    evaluation = evaluate_queue_item(queue, item_id)
    protected_keys = {_path_key(path) for path in project.protected_paths}
    safe_changed_files = tuple(
        path
        for path in evaluation.observed_changed_files
        if _path_key(path) not in protected_keys
    )
    safe_target_files = tuple(
        path for path in item.target_files if _path_key(path) not in protected_keys
    )

    return normalize_session_state(
        {
            "repo": project.repo_path,
            "branch": project.expected_branch,
            "head": project.expected_head,
            "working_tree_status": _working_tree_summary(item.observed_git_status),
            "current_goal": item.current_goal,
            "active_task": item.current_task,
            "blocked_by": "; ".join(evaluation.blocking_reasons),
            "last_codex_prompt": item.last_prompt_summary,
            "last_codex_result_summary": item.last_result_summary,
            "validation_commands": list(project.validation_commands),
            "files_touched": list(safe_changed_files),
            "protected_paths": list(project.protected_paths),
            "commit_allowed": evaluation.result_type == "commit",
            "push_allowed": False,
            "human_approval_required": True,
            "human_approval_granted": (
                evaluation.result_type == "commit" and item.commit_approved
            ),
            "next_action": evaluation.next_action,
            "target_files": list(safe_target_files),
            "commit_message": item.commit_message if evaluation.result_type == "commit" else "",
        }
    )


def _normalize_project(data: Mapping[str, Any], index: int) -> ProjectCard:
    path = f"projects[{index}]"
    _reject_unknown_fields(data, _PROJECT_FIELDS, path)
    protected_paths = _path_list(data, "protected_paths", path)
    expected_untracked = _path_list(data, "expected_untracked", path)
    forbidden_actions = _text_list(data, "forbidden_actions", path)
    validation_commands = _text_list(data, "validation_commands", path)
    if not protected_paths:
        raise ValidationError(f"{path}.protected_paths must include at least one path")
    if not validation_commands:
        raise ValidationError(f"{path}.validation_commands must include at least one command")
    _reject_duplicates(protected_paths, f"{path}.protected_paths")
    _reject_duplicates(expected_untracked, f"{path}.expected_untracked")
    _reject_duplicates(forbidden_actions, f"{path}.forbidden_actions")
    return ProjectCard(
        project_id=_required_text(data, "project_id", path),
        display_name=_required_text(data, "display_name", path),
        repo_path=_required_text(data, "repo_path", path),
        expected_branch=_required_text(data, "expected_branch", path),
        expected_head=_required_text(data, "expected_head", path),
        protected_paths=protected_paths,
        expected_untracked=expected_untracked,
        forbidden_actions=forbidden_actions,
        validation_commands=validation_commands,
    )


def _normalize_item(data: Mapping[str, Any], index: int) -> QueueItem:
    path = f"items[{index}]"
    _reject_unknown_fields(data, _ITEM_FIELDS, path)
    result_type = _required_text(data, "result_type", path).lower()
    if result_type not in ALLOWED_RESULT_TYPES:
        raise ValidationError(f"{path}.result_type is invalid: {result_type}")
    target_files = _path_list(data, "target_files", path, allow_directory=True)
    _reject_duplicates(target_files, f"{path}.target_files")
    return QueueItem(
        item_id=_required_text(data, "item_id", path),
        project_id=_required_text(data, "project_id", path),
        current_goal=_required_text(data, "current_goal", path),
        current_task=_required_text(data, "current_task", path),
        result_type=result_type,
        target_files=target_files,
        observed_branch=_required_text(data, "observed_branch", path),
        observed_head=_required_text(data, "observed_head", path),
        observed_git_status=_text_list(data, "observed_git_status", path),
        scope_approved=_bool(data, "scope_approved", path, default=False),
        review_passed=_bool(data, "review_passed", path, default=False),
        commit_approved=_bool(data, "commit_approved", path, default=False),
        scope_approval_digest=_optional_text(data, "scope_approval_digest", path),
        change_evidence_digest=_optional_text(data, "change_evidence_digest", path),
        review_approval_digest=_optional_text(data, "review_approval_digest", path),
        commit_approval_digest=_optional_text(data, "commit_approval_digest", path),
        commit_message=_optional_text(data, "commit_message", path),
        last_prompt_summary=_optional_text(data, "last_prompt_summary", path),
        last_result_summary=_optional_text(data, "last_result_summary", path),
    )


def _mapping_list(data: Mapping[str, Any], field: str, limit: int) -> list[Mapping[str, Any]]:
    value = data.get(field)
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list of objects")
    if len(value) > limit:
        raise ValidationError(f"{field} must contain at most {limit} items")
    normalized: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValidationError(f"{field}[{index}] must be an object")
        normalized.append(item)
    return normalized


def _required_text(data: Mapping[str, Any], field: str, path: str) -> str:
    if field not in data:
        raise ValidationError(f"{path}.{field} is required")
    value = data[field]
    if not isinstance(value, str):
        raise ValidationError(f"{path}.{field} must be a string")
    normalized = _compact_text(value)
    if not normalized:
        raise ValidationError(f"{path}.{field} must be a non-empty string")
    if len(normalized) > _MAX_TEXT_LENGTH:
        raise ValidationError(f"{path}.{field} is too long")
    return normalized


def _optional_text(data: Mapping[str, Any], field: str, path: str = "prompt queue") -> str:
    value = data.get(field, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{path}.{field} must be a string when provided")
    normalized = _compact_text(value)
    if len(normalized) > _MAX_TEXT_LENGTH:
        raise ValidationError(f"{path}.{field} is too long")
    return normalized


def _bool(data: Mapping[str, Any], field: str, path: str, default: bool) -> bool:
    value = data.get(field, default)
    if not isinstance(value, bool):
        raise ValidationError(f"{path}.{field} must be a boolean")
    return value


def _text_list(data: Mapping[str, Any], field: str, path: str) -> tuple[str, ...]:
    value = data.get(field)
    if not isinstance(value, list):
        raise ValidationError(f"{path}.{field} must be a list of strings")
    if len(value) > _MAX_LIST_ITEMS:
        raise ValidationError(f"{path}.{field} must contain at most {_MAX_LIST_ITEMS} items")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValidationError(f"{path}.{field}[{index}] must be a string")
        text = item.rstrip() if field == "observed_git_status" else _compact_text(item)
        if not text.strip():
            raise ValidationError(f"{path}.{field}[{index}] must be non-empty")
        if len(text) > _MAX_TEXT_LENGTH:
            raise ValidationError(f"{path}.{field}[{index}] is too long")
        normalized.append(text)
    return tuple(normalized)


def _path_list(
    data: Mapping[str, Any],
    field: str,
    path: str,
    *,
    allow_directory: bool = False,
) -> tuple[str, ...]:
    values = _text_list(data, field, path)
    return tuple(
        _relative_path(
            value,
            f"{path}.{field}",
            allow_directory=allow_directory,
        )
        for value in values
    )


def _relative_path(
    value: str,
    field: str,
    *,
    allow_directory: bool = False,
) -> str:
    normalized = value.replace("\\", "/").strip()
    is_directory = allow_directory and normalized.endswith("/")
    candidate = normalized[:-1] if is_directory else normalized
    if (
        not candidate
        or candidate.startswith("/")
        or _WINDOWS_DRIVE.match(candidate)
        or any(part in {"", ".", ".."} for part in candidate.split("/"))
    ):
        raise ValidationError(f"{field} must contain repository-relative paths")
    return f"{candidate}/" if is_directory else candidate


def _path_is_targeted(path: str, targets: tuple[str, ...]) -> bool:
    """Match one canonical file path against exact-file or trailing-slash scope."""

    path_key = _path_key(path)
    return any(
        path_key == target_key
        or (target_key.endswith("/") and path_key.startswith(target_key))
        for target_key in (_path_key(target) for target in targets)
    )


def _parse_status_line(line: str) -> _StatusEntry:
    if len(line) < 4 or line[2] != " ":
        raise ValidationError(f"malformed git status --short line: {line!r}")
    code = line[:2]
    path_text = line[3:].strip()
    if code != "??" and (
        any(character not in _TRACKED_STATUS_CODES for character in code)
        or code == "  "
    ):
        raise ValidationError(f"unsupported git status code {code!r}: {line!r}")
    if not path_text or path_text.startswith('"') or " -> " in path_text:
        raise ValidationError(f"unsupported git status path syntax: {line!r}")
    try:
        path = _relative_path(path_text, "observed_git_status")
    except ValidationError:
        raise ValidationError(f"unsafe git status path: {line!r}") from None
    return _StatusEntry(code=code, path=path)


def _reject_unknown_fields(
    data: Mapping[str, Any], allowed: frozenset[str], path: str
) -> None:
    unknown = sorted(str(key) for key in data if key not in allowed)
    if unknown:
        raise ValidationError(f"{path} contains unknown fields: {', '.join(unknown)}")


def _reject_duplicate_values(values: Any, field: str) -> None:
    normalized = list(values)
    if len(normalized) != len(set(normalized)):
        raise ValidationError(f"{field} values must be unique")


def _reject_duplicates(values: tuple[str, ...], field: str) -> None:
    keys = tuple(_path_key(value) for value in values)
    if len(keys) != len(set(keys)):
        raise ValidationError(f"{field} values must be unique")


def _find_item(queue: PromptQueueState, item_id: str) -> QueueItem:
    for item in queue.items:
        if item.item_id == item_id:
            return item
    raise ValidationError(f"unknown queue item: {item_id}")


def _find_project(queue: PromptQueueState, project_id: str) -> ProjectCard:
    for project in queue.projects:
        if project.project_id == project_id:
            return project
    raise ValidationError(f"unknown project: {project_id}")


def _working_tree_summary(lines: tuple[str, ...]) -> str:
    return "clean" if not lines else "; ".join(lines)


def _deduplicate(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _path_key(path: str) -> str:
    return path.replace("\\", "/").strip().lower()


def _compact_text(value: str) -> str:
    return " ".join(value.strip().split())
