"""Route-free Project Control registry normalization primitives.

This module validates in-memory declarations only. It does not read files or
repositories, run Git, persist state, expose routes, or grant action authority.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
import re
import unicodedata
from typing import Any


REGISTRY_TYPE = "jarvis_project_control"
REGISTRY_VERSION = "0.1B"

MAX_PROJECTS = 16
MAX_LIST_ITEMS = 64
MAX_AUTHORITY_IDS = 128
MAX_DISPLAY_NAME_CHARS = 120
MAX_PATH_CHARS = 512

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
_WINDOWS_FORBIDDEN_PATH_CHARS = frozenset('<>:"|?*')
_WINDOWS_RESERVED_PATH_STEMS = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)
_REGISTRY_FIELDS = frozenset({"registry_type", "version", "projects"})
_PROJECT_FIELDS = frozenset(
    {
        "project_id",
        "display_name",
        "trusted_root_key",
        "master_plan_path",
        "expected_branch",
        "protected_paths",
        "expected_untracked",
        "validation_command_ids",
    }
)


class ProjectRegistryError(ValueError):
    """Raised when a declared project registry fails closed."""


@dataclass(frozen=True)
class DeclaredProjectCard:
    project_id: str
    display_name: str
    trusted_root_key: str
    master_plan_path: str
    expected_branch: str
    protected_paths: tuple[str, ...]
    expected_untracked: tuple[str, ...]
    validation_command_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProjectRegistry:
    projects: tuple[DeclaredProjectCard, ...]
    registry_type: str = REGISTRY_TYPE
    version: str = REGISTRY_VERSION


@dataclass(frozen=True)
class ProjectRegistryDecision:
    registry: ProjectRegistry | None
    blocking_reasons: tuple[str, ...]

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocking_reasons)


def normalize_project_registry(
    data: Mapping[str, Any],
    *,
    trusted_root_keys: Collection[str],
    validation_command_ids: Collection[str],
) -> ProjectRegistry:
    """Normalize one portable project registry without performing I/O."""

    if not isinstance(data, Mapping):
        raise ProjectRegistryError("project registry must be an object")
    _reject_unknown_fields(data, _REGISTRY_FIELDS, "project registry")

    registry_type = _required_text(data, "registry_type", "project registry")
    if registry_type != REGISTRY_TYPE:
        raise ProjectRegistryError(f"registry_type must be {REGISTRY_TYPE}")
    version = _required_text(data, "version", "project registry")
    if version != REGISTRY_VERSION:
        raise ProjectRegistryError(f"version must be {REGISTRY_VERSION}")

    allowed_roots = _authority_ids(trusted_root_keys, "trusted_root_keys")
    allowed_commands = _authority_ids(validation_command_ids, "validation_command_ids")
    values = data.get("projects")
    if not isinstance(values, list):
        raise ProjectRegistryError("projects must be a list")
    if not values or len(values) > MAX_PROJECTS:
        raise ProjectRegistryError(f"projects must contain between 1 and {MAX_PROJECTS} items")

    projects = tuple(
        _normalize_project(value, index, allowed_roots, allowed_commands)
        for index, value in enumerate(values)
    )
    _reject_duplicates(
        (project.project_id for project in projects),
        "project_id",
        case_insensitive=False,
    )
    return ProjectRegistry(
        projects=projects,
        registry_type=registry_type,
        version=version,
    )


def evaluate_project_registry(
    data: Mapping[str, Any],
    *,
    trusted_root_keys: Collection[str],
    validation_command_ids: Collection[str],
) -> ProjectRegistryDecision:
    """Return a bounded fail-closed decision instead of raising to a caller."""

    try:
        registry = normalize_project_registry(
            data,
            trusted_root_keys=trusted_root_keys,
            validation_command_ids=validation_command_ids,
        )
    except ProjectRegistryError as exc:
        return ProjectRegistryDecision(registry=None, blocking_reasons=(str(exc),))
    return ProjectRegistryDecision(registry=registry, blocking_reasons=())


def _normalize_project(
    value: Any,
    index: int,
    allowed_roots: frozenset[str],
    allowed_commands: frozenset[str],
) -> DeclaredProjectCard:
    path = f"projects[{index}]"
    if not isinstance(value, Mapping):
        raise ProjectRegistryError(f"{path} must be an object")
    _reject_unknown_fields(value, _PROJECT_FIELDS, path)

    project_id = _required_id(value, "project_id", path)
    trusted_root_key = _required_id(value, "trusted_root_key", path)
    if trusted_root_key not in allowed_roots:
        raise ProjectRegistryError(f"{path}.trusted_root_key is not server-trusted")

    command_ids = _id_list(value, "validation_command_ids", path)
    if not command_ids:
        raise ProjectRegistryError(f"{path}.validation_command_ids must not be empty")
    unknown_commands = [command for command in command_ids if command not in allowed_commands]
    if unknown_commands:
        raise ProjectRegistryError(
            f"{path}.validation_command_ids contains an unknown command ID: "
            f"{unknown_commands[0]}"
        )

    return DeclaredProjectCard(
        project_id=project_id,
        display_name=_display_name(value, "display_name", path),
        trusted_root_key=trusted_root_key,
        master_plan_path=_required_master_plan_path(value, "master_plan_path", path),
        expected_branch=_required_branch(value, "expected_branch", path),
        protected_paths=_path_list(value, "protected_paths", path),
        expected_untracked=_path_list(value, "expected_untracked", path),
        validation_command_ids=command_ids,
    )


def _authority_ids(values: Collection[str], field: str) -> frozenset[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Collection):
        raise ProjectRegistryError(f"{field} must be a collection of IDs")
    if len(values) > MAX_AUTHORITY_IDS:
        raise ProjectRegistryError(f"{field} exceeds the authority ID limit")
    normalized = list(values)
    if any(not isinstance(value, str) or not _ID_PATTERN.fullmatch(value) for value in normalized):
        raise ProjectRegistryError(f"{field} contains an invalid ID")
    if not normalized:
        raise ProjectRegistryError(f"{field} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ProjectRegistryError(f"{field} contains duplicate IDs")
    return frozenset(normalized)


def _required_text(data: Mapping[str, Any], field: str, path: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProjectRegistryError(f"{path}.{field} must be non-empty trimmed text")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ProjectRegistryError(f"{path}.{field} contains a control character")
    return value


def _required_id(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _required_text(data, field, path)
    if not _ID_PATTERN.fullmatch(value):
        raise ProjectRegistryError(f"{path}.{field} must be a normalized lowercase ID")
    return value


def _display_name(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _required_text(data, field, path)
    if len(value) > MAX_DISPLAY_NAME_CHARS:
        raise ProjectRegistryError(f"{path}.{field} is too long")
    return value


def _required_branch(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _required_text(data, field, path)
    forbidden = ("..", "//", "@{", "\\", "~", "^", ":", "?", "*", "[")
    if (
        not _BRANCH_PATTERN.fullmatch(value)
        or value.endswith(("/", ".", ".lock"))
        or any(marker in value for marker in forbidden)
    ):
        raise ProjectRegistryError(f"{path}.{field} must be a bounded branch name")
    return value


def _required_relative_path(data: Mapping[str, Any], field: str, path: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_CHARS:
        raise ProjectRegistryError(f"{path}.{field} must be a bounded relative path")
    if value != value.strip() or "\\" in value or "\x00" in value:
        raise ProjectRegistryError(f"{path}.{field} must use normalized POSIX syntax")
    if value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise ProjectRegistryError(f"{path}.{field} must be repo-relative")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ProjectRegistryError(f"{path}.{field} contains an unsafe path component")
    if any(
        any(char in _WINDOWS_FORBIDDEN_PATH_CHARS for char in part)
        or part.endswith((".", " "))
        or part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_PATH_STEMS
        for part in parts
    ):
        raise ProjectRegistryError(f"{path}.{field} contains a non-portable path component")
    if any(any(unicodedata.category(char).startswith("C") for char in part) for part in parts):
        raise ProjectRegistryError(f"{path}.{field} contains a control character")
    return value


def _required_master_plan_path(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _required_relative_path(data, field, path)
    if not value.lower().endswith(".md") or any(part.startswith(".") for part in value.split("/")):
        raise ProjectRegistryError(f"{path}.{field} must reference a non-hidden Markdown file")
    return value


def _path_list(data: Mapping[str, Any], field: str, path: str) -> tuple[str, ...]:
    values = data.get(field)
    if not isinstance(values, list) or len(values) > MAX_LIST_ITEMS:
        raise ProjectRegistryError(f"{path}.{field} must be a bounded list")
    normalized = tuple(
        _required_relative_path({field: value}, field, path) for value in values
    )
    _reject_duplicates(normalized, f"{path}.{field}", case_insensitive=True)
    return normalized


def _id_list(data: Mapping[str, Any], field: str, path: str) -> tuple[str, ...]:
    values = data.get(field)
    if not isinstance(values, list) or len(values) > MAX_LIST_ITEMS:
        raise ProjectRegistryError(f"{path}.{field} must be a bounded list")
    normalized = tuple(_required_id({field: value}, field, path) for value in values)
    _reject_duplicates(normalized, f"{path}.{field}", case_insensitive=False)
    return normalized


def _reject_unknown_fields(
    data: Mapping[str, Any],
    allowed: frozenset[str],
    path: str,
) -> None:
    unknown = sorted(str(key) for key in data if key not in allowed)
    if unknown:
        raise ProjectRegistryError(f"{path} contains unknown fields: {', '.join(unknown)}")


def _reject_duplicates(
    values: Iterable[str],
    field: str,
    *,
    case_insensitive: bool,
) -> None:
    seen: set[str] = set()
    for value in values:
        key = value.casefold() if case_insensitive else value
        if key in seen:
            raise ProjectRegistryError(f"{field} contains duplicate values")
        seen.add(key)
