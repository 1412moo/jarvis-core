"""Local browser shell for Jarvis Console v0.1."""

from __future__ import annotations

import argparse
import base64
from collections.abc import Mapping
import hashlib
import hmac
import inspect
import json
import math
import os
import re
import secrets
import stat
import threading
import time
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from subprocess import CalledProcessError, TimeoutExpired, run as run_process
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import parse_qs, urlparse
import webbrowser

from codex_review import CODEX_REVIEW_PREVIEW_ENDPOINT, build_codex_review_preview


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
WEB_ROOT = APP_ROOT / "web"
REGISTRY_PATH = APP_ROOT / "skills.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8790
MAX_JSON_BODY_BYTES = 64_000
OVERVIEW_ALLOWED_EXTENSIONS = {".json", ".md", ".txt"}
OVERVIEW_SOURCE_AREAS = {
    "docs",
    "research_council",
    "daily_ai_radar",
    "hermes_manager",
    "jarvis_console",
    "tasks",
    "reports",
    "checkpoints",
    "unknown",
}
OVERVIEW_ITEM_TYPES = {"task", "report", "checkpoint", "doc", "example", "config"}
OVERVIEW_MAX_ITEMS_PER_DIRECTORY = 10
OVERVIEW_MAX_TOTAL_ITEMS = 50
OVERVIEW_SNIPPET_BYTES = 4096
OVERVIEW_TITLE_MAX_CHARS = 140
OVERVIEW_SUMMARY_MAX_CHARS = 220
HISTORY_MAX_COMMITS = 10
HISTORY_DIRECTORY_KEYS = ("docs", "jarvis_console", "hermes_examples", "daily_ai_radar_examples")
HISTORY_NAME_MARKERS = ("checkpoint", "summary", "report")
VOICE_INBOX_MAX_TRANSCRIPT_CHARS = 8000
VOICE_INBOX_TITLE_MAX_CHARS = 120
VOICE_INBOX_SUMMARY_MAX_CHARS = 280
SECRET_LIKE_NAME_PARTS = ("secret", "token", "credential", "password", ".env")
VOICE_TERM_CORRECTIONS = (
    ("데일리 AI 레이더", "Daily AI Radar"),
    ("데일리 에이아이 레이더", "Daily AI Radar"),
    ("데일리 레이더", "Daily AI Radar"),
    ("Daily Radar", "Daily AI Radar"),
    ("리서치 카운슬러", "Research Council"),
    ("리서치 카운슬", "Research Council"),
    ("에이전트 스킬", "Agent Skills"),
    ("케어노트", "CareNote"),
    ("코덱스", "Codex"),
    ("자비스", "Jarvis"),
    ("헤르메스", "Hermes"),
    ("허미스", "Hermes"),
    ("엠씨피", "MCP"),
)
VOICE_TOKEN_CORRECTIONS = (
    ("커밋", "commit"),
    ("깃", "git"),
)
VOICE_DESTRUCTIVE_TERMS = ("commit", "push", "delete", "remove", "삭제", "지워", "커밋", "푸시")
VOICE_HERMES_CONTEXT_TERMS = (
    "codex",
    "commit",
    "readme",
    "repo",
    "repository",
    "git",
    "pull request",
    "task prompt",
    "commit prompt",
    "hermes",
    "workflow manager",
    "코덱스",
    "커밋",
    "저장소",
    "작업관리",
    "코드",
    "수정",
    "프롬프트",
    "작업 리뷰",
    "커밋 리뷰",
)
VOICE_HERMES_BROAD_HITS = {"git", "pr", "repo", "review", "리뷰"}
VOICE_REVIEW_CORRECTION_CONTEXT_TERMS = (
    "codex",
    "commit",
    "git",
    "repo",
    "pr",
    "readme",
    "prompt",
    "코덱스",
    "커밋",
    "프롬프트",
    "코드",
    "작업 리뷰",
    "커밋 리뷰",
)
READ_ONLY_GIT_COMMANDS = {
    ("rev-parse", "--show-toplevel"),
    ("rev-parse", "--abbrev-ref", "HEAD"),
    ("rev-parse", "HEAD"),
    ("status", "--short"),
    ("log", "--oneline", "-n", "10"),
}
OVERVIEW_DIRECTORIES = (
    {"key": "memory_tasks", "label": "Memory Tasks", "path": "memory/tasks"},
    {"key": "reports", "label": "Reports", "path": "reports"},
    {"key": "research_examples", "label": "Research Council Examples", "path": "apps/research-council/examples"},
    {"key": "daily_ai_radar_examples", "label": "Daily AI Radar Examples", "path": "apps/daily-ai-radar/examples"},
    {"key": "hermes_examples", "label": "Hermes Manager Examples", "path": "apps/hermes-manager-pilot/examples"},
    {"key": "docs", "label": "Docs", "path": "docs"},
    {"key": "jarvis_console", "label": "Jarvis Console", "path": "apps/jarvis-console"},
)
CORE_SKILL_RECENT_ITEM_KEYS = {
    "research_council": ("research_examples",),
    "daily_ai_radar": ("daily_ai_radar_examples",),
    "hermes_manager": ("hermes_examples",),
}
ALLOWED_STATUSES = {"available", "planned", "experimental"}
ALLOWED_CATEGORIES = {"validation", "scouting", "workflow", "memory", "system"}
REQUIRED_SKILL_FIELDS = {
    "skill_id",
    "display_name",
    "status",
    "category",
    "purpose",
    "short_description",
    "safe_next_action",
    "when_to_use",
    "primary_next_action_label",
    "primary_next_action_description",
    "action_guide",
    "commands",
    "local_url",
    "app_path",
    "docs",
    "tests",
    "examples",
    "tags",
    "route_keywords",
    "safety_notes",
    "non_goals",
}
REQUIRED_COMMAND_FIELDS = {"git_bash", "powershell"}
ROUTING_PRIORITY = {
    "hermes_manager": 0,
    "research_council": 1,
    "daily_ai_radar": 2,
    "memory_skills": 3,
    "tasks_reports": 4,
    "settings": 5,
}
FORBIDDEN_COMMAND_PATTERNS = (
    "git" + " add",
    "git" + " commit",
    "git" + " push",
    "git" + " checkout",
    "git" + " reset",
    "git" + " clean",
    "git" + " rm",
    "git" + " stash",
    "cu" + "rl",
    "w" + "get",
    "invoke-" + "webrequest",
    "invoke-" + "restmethod",
    "start-" + "bitstransfer",
    "bits" + "admin",
)


class RegistryError(ValueError):
    """Raised when the read-only skill registry is malformed."""


UNKNOWN_SUGGESTION = {
    "recommended_skill": "unknown",
    "display_name": "Manual choice needed",
    "reason": "No deterministic keyword rule matched the message.",
    "suggested_next_action": "Choose a skill manually from the sidebar and keep the approval boundary visible.",
    "commands": {"git_bash": "", "powershell": ""},
    "matched_keywords": [],
}
MEMORY_SKILLS_ALLOWED_ACTIONS = (
    "Review Candidate",
    "Preview Local Candidate",
    "Copy Candidate",
    "Copy Skill Draft Prompt",
    "Open Skill Details",
)
MEMORY_SKILLS_UNAVAILABLE_ACTIONS = (
    "State changes are not available from the UI.",
    "Local persistence is not available from the UI.",
    "Save actions are not available from the UI.",
    "Skill creation is not available from the UI.",
    "Tool or command launch is not available from the UI.",
)
MEMORY_PREVIEW_ENDPOINT = "/api/memory-skills/candidates/preview"
MEMORY_SAVE_ENDPOINT = "/api/memory-skills/candidates"
MEMORY_SAVE_SUCCESS_MESSAGE = (
    "Saved locally as a candidate. It is not an approved skill and will not run automatically."
)
MEMORY_PREVIEW_TITLE_MAX_CHARS = 120
MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS = 1000
MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS = 240
MEMORY_PREVIEW_MAX_TAGS = 8
MEMORY_PREVIEW_TAG_MAX_CHARS = 32
MEMORY_PREVIEW_MAX_SAFETY_NOTES = 8
MEMORY_PREVIEW_SAFETY_NOTE_MAX_CHARS = 160
MEMORY_PREVIEW_CANDIDATE_TYPES = {
    "repeated_workflow",
    "operating_rule",
    "skill_candidate",
    "prompt_pattern",
    "unknown",
}
MEMORY_PREVIEW_CONFIDENCE_VALUES = {"low", "medium", "high"}
MEMORY_PREVIEW_SOURCES = {"voice_inbox", "chat_command", "manual", "sample"}
MEMORY_PREVIEW_PRIVACY_WARNING = (
    "Preview only. Nothing has been saved. Review for sensitive information before any future local save."
)
MEMORY_SAVE_DRY_RUN_PHASE = "phase_2c_1_save_validation_dry_run"
MEMORY_SAVE_DRY_RUN_REQUIRED_SCOPE = "local_only"
MEMORY_SAVE_DRY_RUN_DISALLOWED_RAW_FIELDS = {"original_text", "raw_transcript", "full_transcript"}
MEMORY_SAVE_DRY_RUN_DISALLOWED_PATH_FIELDS = {
    "file_path",
    "path",
    "candidate_file",
    "storage_path",
    "repo_path",
}
MEMORY_SAVE_DRY_RUN_NOTE_MAX_CHARS = 240
MEMORY_CANDIDATE_STORAGE_VERSION = "memory_candidate_storage.v1"
MEMORY_CANDIDATE_JSON_MAX_BYTES = 32 * 1024
MEMORY_CANDIDATE_TEMP_CREATE_ATTEMPTS = 3
MEMORY_CANDIDATE_ID_PATTERN = re.compile(r"^mem_[a-f0-9]{12,32}$")
MEMORY_REQUEST_GUARD_STATUS = "internal_tests_only"
MEMORY_PREVIEW_TOKEN_SUBSYSTEM_STATUS = "internal_tests_only"
MEMORY_GUARDED_SAVE_COORDINATOR_STATUS = "internal_tests_only"
MEMORY_HTTP_METADATA_ADAPTER_STATUS = "internal_tests_only"
MEMORY_SESSION_COOKIE_NAME = "jarvis_session"
MEMORY_CSRF_HEADER_NAME = "X-Jarvis-CSRF"
MEMORY_HTTP_METADATA_HEADER_MAP = {
    "host": "host",
    "origin": "origin",
    "content-type": "content_type",
    "cookie": "cookie",
    MEMORY_CSRF_HEADER_NAME.lower(): "csrf",
    "content-length": "content_length",
}
MEMORY_HTTP_METADATA_REQUIRED_HEADERS = frozenset(MEMORY_HTTP_METADATA_HEADER_MAP)
MEMORY_HTTP_METADATA_MAX_HEADER_COUNT = 32
MEMORY_HTTP_METADATA_MAX_HEADER_NAME_CHARS = 64
MEMORY_HTTP_METADATA_MAX_HEADER_VALUE_CHARS = 4096
MEMORY_HTTP_HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
MEMORY_SESSION_IDLE_TTL_SECONDS = 30 * 60
MEMORY_SESSION_MAX_ENTRIES = 64
MEMORY_PREVIEW_TOKEN_TTL_SECONDS = 5 * 60
MEMORY_PREVIEW_TOKEN_MAX_ENTRIES = 128
MEMORY_PREVIEW_TOKEN_PER_SESSION_MAX_ENTRIES = 8
MEMORY_GUARDED_SAVE_CONFIRMATION = "save_local_candidate"
MEMORY_GUARDED_SAVE_ALLOWED_FIELDS = frozenset({"preview_token", "confirmation"})
MEMORY_SECRET_BYTES = 32
MEMORY_SECRET_CREATE_ATTEMPTS = 3
MEMORY_SECRET_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43,}$")
MEMORY_PREVIEW_DIGEST_PREFIX = b"jarvis-memory-preview-v1\0"
MEMORY_CANONICAL_PREVIEW_FIELDS = (
    "schema_version",
    "id",
    "title",
    "cleaned_text",
    "original_text_preview",
    "candidate_type",
    "suggested_skill_id",
    "confidence",
    "status",
    "source",
    "confirmation_required",
    "user_approved_at",
    "next_action",
    "safety_notes",
    "tags",
    "privacy_note",
    "redaction_status",
)
JARVIS_LOCAL_STATE_DIR_ENV = "JARVIS_LOCAL_STATE_DIR"
MEMORY_SKILLS_STATE_ROOT_NAME = "Jarvis-Core"
MEMORY_SKILLS_STATE_SEGMENTS = ("memory-skills", "candidates")
MEMORY_SKILLS_SAMPLE_CANDIDATES = (
    {
        "id": "mem_sample_weekly_research_candidates",
        "title": "매주 반복되는 리서치 후보 정리",
        "cleaned_text": "매주 새 리서치 후보를 모아 Research Council 검토 후보로 정리한다.",
        "candidate_type": "repeated_workflow",
        "suggested_skill_id": "memory_skills",
        "confidence": "medium",
        "status": "candidate",
        "source": "sample",
        "confirmation_required": True,
        "next_action": "Review this sample as a proposal; do not store or run it automatically.",
        "safety_notes": [
            "Read-only sample candidate.",
            "No local memory is written in Phase 1.",
        ],
        "tags": ["sample", "research", "proposal"],
        "read_only": True,
        "sample": True,
    },
    {
        "id": "mem_sample_codex_review_prompt_pattern",
        "title": "Codex 리뷰/커밋 프롬프트 패턴",
        "cleaned_text": "Codex 작업 후 리뷰와 커밋 프롬프트를 준비하는 반복 패턴을 후보로 정리한다.",
        "candidate_type": "prompt_pattern",
        "suggested_skill_id": "memory_skills",
        "confidence": "medium",
        "status": "candidate",
        "source": "sample",
        "confirmation_required": True,
        "next_action": "Copy the candidate or draft prompt for manual review only.",
        "safety_notes": [
            "Read-only sample candidate.",
            "No Codex or Hermes call is made from Memory / Skills.",
        ],
        "tags": ["sample", "codex", "prompt"],
        "read_only": True,
        "sample": True,
    },
    {
        "id": "mem_sample_daily_radar_review_routine",
        "title": "Daily AI Radar 후보 검토 루틴",
        "cleaned_text": "Daily AI Radar 결과에서 후보를 읽고 승인 전 검토 항목을 정리한다.",
        "candidate_type": "operating_rule",
        "suggested_skill_id": "memory_skills",
        "confidence": "low",
        "status": "candidate",
        "source": "sample",
        "confirmation_required": True,
        "next_action": "Use this as a read-only example of a future operating rule proposal.",
        "safety_notes": [
            "Read-only sample candidate.",
            "Radar recommendations remain candidates, not implementation approval.",
        ],
        "tags": ["sample", "radar", "review"],
        "read_only": True,
        "sample": True,
    },
)


def normalize_filesystem_path(path: Path) -> Path:
    """Resolve a path for policy checks without creating it."""

    return path.expanduser().resolve(strict=False)


def absolute_filesystem_path(path: Path) -> Path:
    """Return a lexical absolute path without resolving symlinks or reparse points."""

    return Path(os.path.abspath(os.fspath(path.expanduser())))


def filesystem_stat_is_reparse_point(path_stat: Any) -> bool:
    """Return whether an lstat result represents a symlink or Windows reparse point."""

    if stat.S_ISLNK(path_stat.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(getattr(path_stat, "st_file_attributes", 0) & reparse_flag)


def existing_path_chain_has_reparse_point(path: Path) -> bool:
    """Inspect existing lexical path components without following a detected reparse point."""

    current = absolute_filesystem_path(path)
    components = [current]
    while current.parent != current:
        current = current.parent
        components.append(current)
    for component in reversed(components):
        try:
            component_stat = os.lstat(component)
        except FileNotFoundError:
            continue
        if filesystem_stat_is_reparse_point(component_stat):
            return True
    return False


def is_path_inside_repo(path: Path, repo_root: Path = REPO_ROOT) -> bool:
    """Return whether a path is inside the repository, without requiring it to exist."""

    resolved_path = normalize_filesystem_path(path)
    resolved_repo = normalize_filesystem_path(repo_root)
    path_text = os.path.normcase(os.path.normpath(str(resolved_path)))
    repo_text = os.path.normcase(os.path.normpath(str(resolved_repo)))
    try:
        return os.path.commonpath([path_text, repo_text]) == repo_text
    except ValueError:
        return False


def default_jarvis_local_state_root(
    *,
    env: Any | None = None,
    home_dir: Path | str | None = None,
    is_windows: bool | None = None,
) -> tuple[Path, str]:
    """Return the default Jarvis local state root without creating it."""

    env_map = os.environ if env is None else env
    windows = (os.name == "nt") if is_windows is None else is_windows
    if windows:
        local_appdata = str(env_map.get("LOCALAPPDATA", "")).strip()
        if local_appdata:
            return Path(os.path.expandvars(local_appdata)) / MEMORY_SKILLS_STATE_ROOT_NAME, "default_windows_localappdata"
    home = Path.home() if home_dir is None else Path(home_dir)
    return home / ".jarvis-core", "default_home"


def resolve_memory_skills_state_paths(
    *,
    env: Any | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
) -> dict[str, Any]:
    """Calculate future Memory / Skills state paths without creating directories or files."""

    env_map = os.environ if env is None else env
    override = str(env_map.get(JARVIS_LOCAL_STATE_DIR_ENV, "")).strip()
    if override:
        state_root = Path(os.path.expandvars(override)).expanduser()
        source = "env_override"
        if not state_root.is_absolute():
            return {
                "ok": False,
                "error": "local_state_dir_must_be_absolute",
                "source": source,
                "state_root": state_root,
                "candidate_dir": state_root.joinpath(*MEMORY_SKILLS_STATE_SEGMENTS),
                "repo_root": normalize_filesystem_path(repo_root),
                "repo_internal": False,
                "will_create_directory": False,
                "will_write_files": False,
            }
    else:
        state_root, source = default_jarvis_local_state_root(env=env_map, home_dir=home_dir, is_windows=is_windows)

    state_root_policy_path = absolute_filesystem_path(state_root)
    candidate_dir_policy_path = state_root_policy_path.joinpath(*MEMORY_SKILLS_STATE_SEGMENTS)
    state_root = normalize_filesystem_path(state_root_policy_path)
    candidate_dir = normalize_filesystem_path(candidate_dir_policy_path)
    repo_internal = is_path_inside_repo(candidate_dir, repo_root)
    if repo_internal:
        return {
            "ok": False,
            "error": "local_state_dir_inside_repo",
            "source": source,
            "state_root": state_root,
            "candidate_dir": candidate_dir,
            "state_root_policy_path": state_root_policy_path,
            "candidate_dir_policy_path": candidate_dir_policy_path,
            "repo_root": normalize_filesystem_path(repo_root),
            "repo_internal": True,
            "will_create_directory": False,
            "will_write_files": False,
        }

    return {
        "ok": True,
        "error": "",
        "source": source,
        "state_root": state_root,
        "candidate_dir": candidate_dir,
        "state_root_policy_path": state_root_policy_path,
        "candidate_dir_policy_path": candidate_dir_policy_path,
        "repo_root": normalize_filesystem_path(repo_root),
        "repo_internal": False,
        "will_create_directory": False,
        "will_write_files": False,
    }

STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/web/index.html": ("index.html", "text/html; charset=utf-8"),
    "/web/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/web/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


def load_registry() -> dict[str, Any]:
    """Load and validate the read-only skill registry."""

    with REGISTRY_PATH.open("r", encoding="utf-8") as file:
        registry = json.load(file)
    validate_registry(registry)
    return registry


def validate_registry(registry: dict[str, Any]) -> None:
    """Validate registry shape and safety boundaries deterministically."""

    if not isinstance(registry, dict):
        raise RegistryError("registry must be an object")
    if registry.get("registry_type") != "jarvis_console_skill_registry":
        raise RegistryError("registry_type must be jarvis_console_skill_registry")
    if registry.get("read_only") is not True:
        raise RegistryError("registry read_only must be true")

    protected_paths = registry.get("protected_paths")
    if not isinstance(protected_paths, list) or "jarvis.bat" not in protected_paths:
        raise RegistryError("protected_paths must mention jarvis.bat")

    skills = registry.get("skills")
    if not isinstance(skills, list) or not skills:
        raise RegistryError("skills must be a non-empty list")

    seen_ids: set[str] = set()
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            raise RegistryError(f"skill #{index} must be an object")
        missing = REQUIRED_SKILL_FIELDS - set(skill)
        if missing:
            raise RegistryError(f"{skill.get('skill_id', index)} missing fields: {sorted(missing)}")

        skill_id = _required_text(skill, "skill_id")
        if skill_id in seen_ids:
            raise RegistryError(f"duplicate skill_id: {skill_id}")
        seen_ids.add(skill_id)

        _required_text(skill, "display_name")
        _required_text(skill, "purpose")
        _required_text(skill, "short_description")
        _required_text(skill, "safe_next_action")
        _required_text(skill, "when_to_use")
        _required_text(skill, "primary_next_action_label")
        _required_text(skill, "primary_next_action_description")

        if skill["status"] not in ALLOWED_STATUSES:
            raise RegistryError(f"{skill_id} invalid status: {skill['status']}")
        if skill["category"] not in ALLOWED_CATEGORIES:
            raise RegistryError(f"{skill_id} invalid category: {skill['category']}")

        commands = skill["commands"]
        if not isinstance(commands, dict):
            raise RegistryError(f"{skill_id} commands must be an object")
        missing_commands = REQUIRED_COMMAND_FIELDS - set(commands)
        if missing_commands:
            raise RegistryError(f"{skill_id} missing command fields: {sorted(missing_commands)}")
        for command_name in sorted(REQUIRED_COMMAND_FIELDS):
            command = commands.get(command_name)
            if not isinstance(command, str):
                raise RegistryError(f"{skill_id} command {command_name} must be text")
            validate_display_command(skill_id, command_name, command)

        local_url = skill.get("local_url")
        if not isinstance(local_url, str):
            raise RegistryError(f"{skill_id} local_url must be text")
        if local_url and not local_url.startswith("http://127.0.0.1"):
            raise RegistryError(f"{skill_id} local_url must be local-only")

        for field in (
            "tags",
            "route_keywords",
            "safety_notes",
            "non_goals",
            "docs",
            "tests",
            "examples",
            "action_guide",
        ):
            value = skill[field]
            if not isinstance(value, list):
                raise RegistryError(f"{skill_id} {field} must be a list")
            if field == "route_keywords" and not value:
                raise RegistryError(f"{skill_id} route_keywords must not be empty")
            if field == "action_guide" and not value:
                raise RegistryError(f"{skill_id} action_guide must not be empty")
            if not all(isinstance(item, str) for item in value):
                raise RegistryError(f"{skill_id} {field} entries must be text")
            if any(not item.strip() for item in value):
                raise RegistryError(f"{skill_id} {field} entries must not be empty")
            if field in {"docs", "examples"}:
                for path_value in value:
                    validate_registry_path(skill_id, field, path_value)
            if field == "tests":
                for test_command in value:
                    validate_display_command(skill_id, "test command", test_command)

        handoff_steps = skill.get("handoff_steps")
        if handoff_steps is not None:
            if not isinstance(handoff_steps, list) or len(handoff_steps) != 3:
                raise RegistryError(f"{skill_id} handoff_steps must be a three-item list")
            if not all(isinstance(item, str) for item in handoff_steps):
                raise RegistryError(f"{skill_id} handoff_steps entries must be text")
            if any(not item.strip() for item in handoff_steps):
                raise RegistryError(f"{skill_id} handoff_steps entries must not be empty")

        if skill["status"] == "available" and not (skill["docs"] or skill["tests"] or skill["safe_next_action"]):
            raise RegistryError(f"{skill_id} available skills need docs, tests, or safe_next_action")


def _required_text(skill: dict[str, Any], field: str) -> str:
    value = skill.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{skill.get('skill_id', '<unknown>')} {field} is required")
    return value


def validate_display_command(skill_id: str, command_name: str, command: str) -> None:
    """Validate a display-only command without executing it."""

    lowered = command.lower()
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if pattern in lowered:
            raise RegistryError(f"{skill_id} {command_name} contains forbidden command text")
    if "http://" in lowered or "https://" in lowered:
        raise RegistryError(f"{skill_id} {command_name} must not contain network URLs")


def validate_registry_path(skill_id: str, field: str, path_value: str) -> None:
    """Validate a metadata path as local, repo-relative display text."""

    if not path_value.strip():
        raise RegistryError(f"{skill_id} {field} entries must not be empty")
    lowered = path_value.lower()
    path = PurePosixPath(path_value)
    if (
        "http://" in lowered
        or "https://" in lowered
        or "\\" in path_value
        or ":" in path_value
        or path.is_absolute()
        or path_value.startswith("~")
        or ".." in path.parts
    ):
        raise RegistryError(f"{skill_id} {field} entries must be local repo-relative paths")


def registry_skills() -> list[dict[str, Any]]:
    """Return validated skill list from the registry."""

    return list(load_registry()["skills"])


def skill_detail(skill_id: str) -> dict[str, Any] | None:
    """Return one registry skill by id without mutating registry state."""

    for skill in registry_skills():
        if skill["skill_id"] == skill_id:
            return dict(skill)
    return None


def status_payload() -> dict[str, Any]:
    """Return deterministic local console status metadata."""

    registry = load_registry()
    return {
        "ok": True,
        "console": "jarvis-console",
        "version": "0.1",
        "mode": "local-only",
        "host": DEFAULT_HOST,
        "default_port": DEFAULT_PORT,
        "protected_paths": registry["protected_paths"],
        "registry_version": registry["registry_version"],
        "registry_read_only": registry["read_only"],
        "safety": [
            "Safety mode: Jarvis only recommends. It does not run tools.",
            "Local-only",
            "No automatic Codex / ChatGPT / Hermes invocation",
            "No commit or push",
            "No external network/API/LLM calls",
            "Human approval required before implementation",
        ],
        "skills": registry["skills"],
    }


def validate_read_only_git_args(args: tuple[str, ...]) -> None:
    """Allow only fixed read-only git commands for overview metadata."""

    if args not in READ_ONLY_GIT_COMMANDS:
        raise RegistryError("git command is not allowed for read-only overview")


def run_read_only_git(args: tuple[str, ...]) -> str:
    """Run a fixed read-only git command without shell expansion."""

    validate_read_only_git_args(args)
    try:
        result = run_process(
            ["git", *args],
            cwd=REPO_ROOT,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=True,
            timeout=5,
        )
    except (CalledProcessError, TimeoutExpired, OSError) as exc:
        raise RegistryError(f"read-only git status failed: {exc}") from exc
    return result.stdout.strip()


def repo_status_payload() -> dict[str, Any]:
    """Return read-only repository status for the overview dashboard."""

    head = run_read_only_git(("rev-parse", "HEAD"))
    working_tree_status = run_read_only_git(("status", "--short"))
    return {
        "root": run_read_only_git(("rev-parse", "--show-toplevel")),
        "branch": run_read_only_git(("rev-parse", "--abbrev-ref", "HEAD")),
        "head": head,
        "head_short": head[:7],
        "working_tree_status": working_tree_status or "clean",
        "protected_path_note": "jarvis.bat remains protected and must not be staged or modified by Jarvis Console.",
        "read_only_git_commands": [
            "git rev-parse --show-toplevel",
            "git rev-parse --abbrev-ref HEAD",
            "git rev-parse HEAD",
            "git status --short",
        ],
    }


def history_repo_payload() -> dict[str, Any]:
    """Return repository metadata for the read-only history view."""

    repo = repo_status_payload()
    return {
        "branch": repo["branch"],
        "head": repo["head"],
        "head_short": repo["head_short"],
        "working_tree_status": repo["working_tree_status"],
        "protected_path_note": repo["protected_path_note"],
    }


def overview_directory_by_key() -> dict[str, dict[str, str]]:
    return {item["key"]: item for item in OVERVIEW_DIRECTORIES}


def is_overview_candidate_path(path: Path, allowed_root: Path | None = None) -> bool:
    """Check path-only safety rules for overview file discovery."""

    try:
        resolved_path = path.resolve()
        relative = resolved_path.relative_to(REPO_ROOT)
    except ValueError:
        return False
    if allowed_root is not None:
        try:
            resolved_path.relative_to(allowed_root.resolve())
        except ValueError:
            return False
    if path.suffix.lower() not in OVERVIEW_ALLOWED_EXTENSIONS:
        return False
    lowered_name = path.name.lower()
    if any(part in lowered_name for part in SECRET_LIKE_NAME_PARTS):
        return False
    for part in relative.parts:
        if part == ".git" or part == "__pycache__" or part.startswith("."):
            return False
    return True


def read_overview_title(path: Path) -> str:
    """Read a small prefix and return a display-only title or first line."""

    title, _summary = read_overview_title_and_summary(path)
    return title


def truncate_overview_text(value: str, max_chars: int) -> str:
    """Return bounded display text for overview titles and summaries."""

    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def read_overview_title_and_summary(path: Path) -> tuple[str, str]:
    """Read a small prefix and return display-only title and summary text."""

    try:
        with path.open("rb") as file:
            raw = file.read(OVERVIEW_SNIPPET_BYTES)
    except OSError:
        return "", ""
    text = raw.decode("utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = ""
    if path.suffix.lower() == ".json" and lines and lines[0] in {"{", "["}:
        title = path.stem.replace("-", " ").replace("_", " ").title()
        summary = "JSON metadata file."
        return truncate_overview_text(title, OVERVIEW_TITLE_MAX_CHARS), summary
    for line in lines:
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break
    if not title and lines:
        title = lines[0]
    summary_candidates = [line.lstrip("#").strip() for line in lines if line.lstrip("#").strip() != title]
    summary = summary_candidates[0] if summary_candidates else ""
    return (
        truncate_overview_text(title, OVERVIEW_TITLE_MAX_CHARS),
        truncate_overview_text(summary, OVERVIEW_SUMMARY_MAX_CHARS),
    )


def infer_source_area(repo_path: str, directory: dict[str, str]) -> str:
    """Classify overview files by source area without reading beyond metadata."""

    directory_key = directory["key"]
    lowered_path = repo_path.lower()
    if directory_key == "memory_tasks":
        return "tasks"
    if directory_key == "reports":
        return "reports"
    if directory_key == "research_examples" or "research-council" in lowered_path:
        return "research_council"
    if directory_key == "daily_ai_radar_examples" or "daily-ai-radar" in lowered_path:
        return "daily_ai_radar"
    if directory_key == "hermes_examples" or "hermes-manager" in lowered_path:
        return "hermes_manager"
    if directory_key == "jarvis_console" or "jarvis-console" in lowered_path:
        return "jarvis_console"
    if directory_key == "docs":
        return "docs"
    return "unknown"


def infer_item_type(repo_path: str, directory: dict[str, str]) -> str:
    """Classify overview files as display metadata only."""

    directory_key = directory["key"]
    lowered_path = repo_path.lower()
    name = PurePosixPath(repo_path).name.lower()
    stem = PurePosixPath(repo_path).stem.lower()
    if directory_key == "memory_tasks":
        return "task"
    if "checkpoint" in stem:
        return "checkpoint"
    if directory_key == "reports":
        return "report"
    if name in {"skills.json"}:
        return "config"
    if "contracts/" in lowered_path:
        return "doc"
    if directory_key in {"research_examples", "daily_ai_radar_examples", "hermes_examples"}:
        if "report" in stem:
            return "report"
        return "example"
    if directory_key == "jarvis_console" and PurePosixPath(repo_path).suffix.lower() == ".json":
        return "config"
    if directory_key == "docs":
        return "doc"
    return "doc"


def overview_item_id(repo_path: str, source_area: str, item_type: str) -> str:
    """Return a deterministic display key for one overview item."""

    return f"{source_area}:{item_type}:{repo_path}"


def overview_source_area_label(source_area: str) -> str:
    labels = {
        "docs": "Docs",
        "research_council": "Research Council",
        "daily_ai_radar": "Daily AI Radar",
        "hermes_manager": "Hermes Manager",
        "jarvis_console": "Jarvis Console",
        "tasks": "Tasks",
        "reports": "Reports",
        "checkpoints": "Checkpoints",
        "unknown": "Unknown",
    }
    return labels.get(source_area, "Unknown")


def overview_file_item(path: Path, directory: dict[str, str]) -> dict[str, Any]:
    stat = path.stat()
    repo_path = path.relative_to(REPO_ROOT).as_posix()
    title, summary = read_overview_title_and_summary(path)
    source_area = infer_source_area(repo_path, directory)
    item_type = infer_item_type(repo_path, directory)
    return {
        "item_id": overview_item_id(repo_path, source_area, item_type),
        "name": path.name,
        "path": repo_path,
        "directory_key": directory["key"],
        "directory_label": directory["label"],
        "source_area": source_area,
        "source_area_label": overview_source_area_label(source_area),
        "item_type": item_type,
        "title": title,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "modified": stat.st_mtime,
        "modified_time": stat.st_mtime,
        "summary": summary,
        "read_only": True,
    }


def discover_recent_items(directory_keys: tuple[str, ...], name_contains: str = "") -> list[dict[str, Any]]:
    """Discover recent display-only file metadata from fixed safe directories."""

    directories = overview_directory_by_key()
    items: list[dict[str, Any]] = []
    for key in directory_keys:
        directory = directories[key]
        root = REPO_ROOT / directory["path"]
        if not root.exists() or not root.is_dir():
            continue
        directory_items: list[dict[str, Any]] = []
        for path in root.rglob("*"):
            if not path.is_file() or not is_overview_candidate_path(path, root):
                continue
            if name_contains and name_contains.lower() not in path.name.lower():
                continue
            directory_items.append(overview_file_item(path, directory))
        directory_items.sort(key=lambda item: (item["modified"], item["path"]), reverse=True)
        items.extend(directory_items[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY])
        if len(items) >= OVERVIEW_MAX_TOTAL_ITEMS:
            break
    return items[:OVERVIEW_MAX_TOTAL_ITEMS]


def is_history_candidate_name(path: Path) -> bool:
    """Return true for checkpoint/history display candidates by filename only."""

    lowered = path.name.lower()
    return any(marker in lowered for marker in HISTORY_NAME_MARKERS)


def discover_history_items() -> list[dict[str, Any]]:
    """Discover read-only checkpoint and history metadata from fixed safe directories."""

    directories = overview_directory_by_key()
    items: list[dict[str, Any]] = []
    for key in HISTORY_DIRECTORY_KEYS:
        directory = directories[key]
        root = REPO_ROOT / directory["path"]
        if not root.exists() or not root.is_dir():
            continue
        directory_items: list[dict[str, Any]] = []
        for path in root.rglob("*"):
            if not path.is_file() or not is_overview_candidate_path(path, root):
                continue
            if not is_history_candidate_name(path):
                continue
            directory_items.append(overview_file_item(path, directory))
        directory_items.sort(key=lambda item: (item["modified"], item["path"]), reverse=True)
        items.extend(directory_items[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY])
        if len(items) >= OVERVIEW_MAX_TOTAL_ITEMS:
            break
    return items[:OVERVIEW_MAX_TOTAL_ITEMS]


def filter_overview_items(items: list[dict[str, Any]], item_types: set[str] | None = None) -> list[dict[str, Any]]:
    """Filter already discovered read-only items without touching the filesystem."""

    if item_types is None:
        return list(items)
    return [item for item in items if item["item_type"] in item_types]


def recent_group(group_id: str, title: str, empty_text: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a grouped recent-item section for the overview dashboard."""

    return {
        "group_id": group_id,
        "title": title,
        "empty_text": empty_text,
        "items": items[:OVERVIEW_MAX_TOTAL_ITEMS],
        "read_only": True,
    }


def assert_overview_item_safety(item: dict[str, Any]) -> None:
    """Validate one normalized overview item without touching the filesystem."""

    repo_path = item["path"]
    pure_path = PurePosixPath(repo_path)
    assert item["read_only"] is True
    assert item["source_area"] in OVERVIEW_SOURCE_AREAS
    assert item["item_type"] in OVERVIEW_ITEM_TYPES
    assert item["item_id"] == overview_item_id(repo_path, item["source_area"], item["item_type"])
    assert repo_path
    assert len(item["title"]) <= OVERVIEW_TITLE_MAX_CHARS
    assert len(item["summary"]) <= OVERVIEW_SUMMARY_MAX_CHARS
    assert "\\" not in repo_path
    assert ":" not in repo_path
    assert ".." not in pure_path.parts
    assert not pure_path.is_absolute()
    assert Path(repo_path).suffix in OVERVIEW_ALLOWED_EXTENSIONS


def overview_skills_payload(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return core skill status cards with recent read-only artifacts."""

    payload = []
    for skill in skills:
        skill_id = skill["skill_id"]
        if skill_id not in CORE_SKILL_RECENT_ITEM_KEYS:
            continue
        payload.append(
            {
                "skill_id": skill_id,
                "display_name": skill["display_name"],
                "status": skill["status"],
                "safe_next_action": skill["safe_next_action"],
                "docs": skill["docs"],
                "examples": skill["examples"],
                "recent_items": discover_recent_items(CORE_SKILL_RECENT_ITEM_KEYS[skill_id])[:5],
            }
        )
    return payload


def overview_payload() -> dict[str, Any]:
    """Return the read-only Tasks / Reports dashboard payload."""

    registry = load_registry()
    tasks = discover_recent_items(("memory_tasks",))
    reports = filter_overview_items(
        discover_recent_items(("reports", "research_examples", "daily_ai_radar_examples")),
        {"report"},
    )
    checkpoints = discover_recent_items(("hermes_examples", "docs"), name_contains="checkpoint")
    docs_examples = discover_recent_items(
        ("docs", "research_examples", "daily_ai_radar_examples", "hermes_examples", "jarvis_console")
    )
    recent_groups = [
        recent_group("tasks", "Recent Tasks", "No task index found yet.", tasks),
        recent_group("reports", "Recent Reports", "No generated reports found yet.", reports),
        recent_group("checkpoints", "Recent Checkpoints", "No checkpoint index found yet.", checkpoints),
        recent_group("docs_examples", "Recent Docs / Examples", "No docs or examples found yet.", docs_examples),
    ]
    return {
        "ok": True,
        "mode": "read-only",
        "repo": repo_status_payload(),
        "skills": overview_skills_payload(registry["skills"]),
        "tasks": tasks,
        "reports": reports,
        "checkpoints": checkpoints,
        "docs_examples": docs_examples,
        "recent_groups": recent_groups,
        "notes": [
            "Read-only dashboard. Jarvis Console does not create or mutate tasks.",
            "Reports and checkpoints are discovered as existing local files only; none are generated here.",
            "Recent items are read-only metadata from allowlisted local paths.",
            "Jarvis Console does not run skills, call Codex/ChatGPT/Hermes, or commit/push.",
            "Protected path remains visible: jarvis.bat.",
        ],
        "discovery": {
            "safe_directories": [
                {"key": item["key"], "label": item["label"], "path": item["path"], "exists": (REPO_ROOT / item["path"]).is_dir()}
                for item in OVERVIEW_DIRECTORIES
            ],
            "allowed_extensions": sorted(OVERVIEW_ALLOWED_EXTENSIONS),
            "max_items_per_directory": OVERVIEW_MAX_ITEMS_PER_DIRECTORY,
            "max_total_items": OVERVIEW_MAX_TOTAL_ITEMS,
            "excluded": ["hidden files", ".git", "__pycache__", "secrets-like file names"],
        },
    }


def memory_skills_payload() -> dict[str, Any]:
    """Return the read-only Memory / Skills sample panel and preview boundary."""

    skill = skill_detail("memory_skills") or {}
    candidates = [dict(candidate) for candidate in MEMORY_SKILLS_SAMPLE_CANDIDATES]
    return {
        "ok": True,
        "mode": "read-only",
        "phase": "phase_2b_preview_only",
        "title": "Memory / Skills Phase 2B",
        "description": "Read-only sample inbox with preview-only candidate capture before any future local save.",
        "skill_id": "memory_skills",
        "display_name": skill.get("display_name", "Memory / Skills"),
        "read_only": True,
        "sample": True,
        "preview_only": True,
        "not_saved": True,
        "no_persistence": True,
        "runtime_write": False,
        "save_endpoint": False,
        "post_endpoints": "preview_only",
        "write_endpoints": False,
        "preview_endpoint": MEMORY_PREVIEW_ENDPOINT,
        "preview_endpoint_write_free": True,
        "approval_gated_save_api": False,
        "approval_gated_save_endpoint": False,
        "candidate_write_helper": "tests_only",
        "request_guard": MEMORY_REQUEST_GUARD_STATUS,
        "preview_token_subsystem": MEMORY_PREVIEW_TOKEN_SUBSYSTEM_STATUS,
        "guarded_save_coordinator": MEMORY_GUARDED_SAVE_COORDINATOR_STATUS,
        "http_metadata_adapter": MEMORY_HTTP_METADATA_ADAPTER_STATUS,
        "persisted_original_text_preview": False,
        "preview_token_issuance": False,
        "ui_save_action": False,
        "voice_inbox_auto_save": False,
        "candidates": candidates,
        "guidance": [
            "Treat these as sample candidates, not saved user memory.",
            "Voice Inbox can suggest Memory / Skills, but it does not save candidates automatically.",
            "Phase 2B previews the fields that would be saved later; it does not save them.",
            "Preview requests are write-free and return privacy warnings only.",
            "The approval-gated local save endpoint is not enabled while safety hardening is pending.",
            "The internal candidate write helper is exercised by tests only.",
            "The UI has no save action, saved list, or automatic Voice Inbox save.",
        ],
        "allowed_actions": list(MEMORY_SKILLS_ALLOWED_ACTIONS),
        "unavailable_actions": list(MEMORY_SKILLS_UNAVAILABLE_ACTIONS),
        "safety_boundary": [
            "No automatic memory save.",
            "No automatic skill creation.",
            "No automatic code modification.",
            "No runtime file write.",
            "No UI save action.",
            "No approval-gated save API endpoint.",
            "No external API, web, or LLM call.",
            "No microphone, STT, TTS, or recording.",
            "No Codex, ChatGPT, Hermes, Research Council, or Daily AI Radar automatic invocation.",
            "No git write operations.",
            "Protected path remains visible: jarvis.bat.",
        ],
    }


def assert_memory_candidate_safety(candidate: dict[str, Any]) -> None:
    """Validate a Memory / Skills sample candidate without filesystem access."""

    assert candidate["read_only"] is True
    assert candidate["sample"] is True
    assert candidate["confirmation_required"] is True
    assert candidate["status"] == "candidate"
    assert candidate["source"] == "sample"
    assert candidate["suggested_skill_id"] == "memory_skills"
    assert candidate["id"].startswith("mem_sample_")
    assert "/" not in candidate["id"]
    assert "\\" not in candidate["id"]
    assert "original_text" not in candidate


def memory_string_has_valid_unicode(value: str) -> bool:
    """Return whether a string is NUL-free and strictly UTF-8 encodable."""

    if "\x00" in value:
        return False
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return False
    return True


def memory_json_strings_have_valid_unicode(value: Any) -> bool:
    """Recursively validate every string key and value destined for candidate JSON."""

    if isinstance(value, str):
        return memory_string_has_valid_unicode(value)
    if isinstance(value, dict):
        return all(
            (not isinstance(key, str) or memory_string_has_valid_unicode(key))
            and memory_json_strings_have_valid_unicode(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(memory_json_strings_have_valid_unicode(item) for item in value)
    return True


def normalize_memory_preview_string(
    payload: dict[str, Any],
    field: str,
    max_chars: int,
    *,
    required: bool = False,
) -> tuple[int, str | None, str]:
    """Return a bounded preview string without writing it anywhere."""

    if field not in payload:
        if required:
            return HTTPStatus.BAD_REQUEST, f"missing_{field}", ""
        return HTTPStatus.OK, None, ""
    value = payload[field]
    if not isinstance(value, str):
        return HTTPStatus.BAD_REQUEST, f"{field}_must_be_string", ""
    if not memory_string_has_valid_unicode(value):
        return HTTPStatus.BAD_REQUEST, "invalid_unicode", ""
    text = re.sub(r"\s+", " ", value).strip()
    if required and not text:
        return HTTPStatus.BAD_REQUEST, f"empty_{field}", ""
    if len(text) > max_chars:
        return HTTPStatus.BAD_REQUEST, f"{field}_too_long", ""
    return HTTPStatus.OK, None, text


def normalize_memory_preview_list(
    payload: dict[str, Any],
    field: str,
    max_items: int,
    max_chars: int,
) -> tuple[int, str | None, list[str]]:
    """Return a bounded list for preview display only."""

    if field not in payload or payload[field] is None:
        return HTTPStatus.OK, None, []
    value = payload[field]
    if not isinstance(value, list):
        return HTTPStatus.BAD_REQUEST, f"{field}_must_be_list", []
    if len(value) > max_items:
        return HTTPStatus.BAD_REQUEST, f"too_many_{field}", []
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return HTTPStatus.BAD_REQUEST, f"{field}_items_must_be_string", []
        if not memory_string_has_valid_unicode(item):
            return HTTPStatus.BAD_REQUEST, "invalid_unicode", []
        text = re.sub(r"\s+", " ", item).strip()
        if not text:
            continue
        if len(text) > max_chars:
            return HTTPStatus.BAD_REQUEST, f"{field}_item_too_long", []
        normalized.append(text)
    return HTTPStatus.OK, None, normalized


def normalize_memory_preview_choice(
    payload: dict[str, Any],
    field: str,
    allowed: set[str],
    fallback: str,
) -> tuple[int, str | None, str]:
    """Normalize enum-like preview values with conservative fallback."""

    value = payload.get(field)
    if not isinstance(value, str):
        return HTTPStatus.OK, None, fallback
    if not memory_string_has_valid_unicode(value):
        return HTTPStatus.BAD_REQUEST, "invalid_unicode", fallback
    normalized = value.strip().lower()
    return HTTPStatus.OK, None, normalized if normalized in allowed else fallback


def memory_preview_title(title: str, cleaned_text: str) -> str:
    """Return a human-readable preview title without creating a stable stored ID."""

    if title:
        return title
    first_line = cleaned_text.splitlines()[0] if cleaned_text.splitlines() else cleaned_text
    return first_line[:MEMORY_PREVIEW_TITLE_MAX_CHARS].strip() or "Preview-only Memory / Skills candidate"


def prepare_memory_candidate_preview(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Build a write-free candidate preview for Phase 2B."""

    status, error, cleaned_text = normalize_memory_preview_string(
        payload,
        "cleaned_text",
        MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS,
        required=True,
    )
    if status != HTTPStatus.OK:
        return status, {"ok": False, "error": error}

    status, error, title = normalize_memory_preview_string(payload, "title", MEMORY_PREVIEW_TITLE_MAX_CHARS)
    if status != HTTPStatus.OK:
        return status, {"ok": False, "error": error}

    status, error, original_text_preview = normalize_memory_preview_string(
        payload,
        "original_text_preview",
        MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS,
    )
    if status != HTTPStatus.OK:
        return status, {"ok": False, "error": error}

    status, error, tags = normalize_memory_preview_list(
        payload,
        "tags",
        MEMORY_PREVIEW_MAX_TAGS,
        MEMORY_PREVIEW_TAG_MAX_CHARS,
    )
    if status != HTTPStatus.OK:
        return status, {"ok": False, "error": error}

    status, error, safety_notes = normalize_memory_preview_list(
        payload,
        "safety_notes",
        MEMORY_PREVIEW_MAX_SAFETY_NOTES,
        MEMORY_PREVIEW_SAFETY_NOTE_MAX_CHARS,
    )
    if status != HTTPStatus.OK:
        return status, {"ok": False, "error": error}

    status, error, candidate_type = normalize_memory_preview_choice(
        payload,
        "candidate_type",
        MEMORY_PREVIEW_CANDIDATE_TYPES,
        "unknown",
    )
    if status != HTTPStatus.OK:
        return status, {"ok": False, "error": error}
    status, error, confidence = normalize_memory_preview_choice(
        payload,
        "confidence",
        MEMORY_PREVIEW_CONFIDENCE_VALUES,
        "low",
    )
    if status != HTTPStatus.OK:
        return status, {"ok": False, "error": error}
    status, error, source = normalize_memory_preview_choice(payload, "source", MEMORY_PREVIEW_SOURCES, "manual")
    if status != HTTPStatus.OK:
        return status, {"ok": False, "error": error}
    candidate_preview = {
        "schema_version": "memory_candidate.v1",
        "id": "preview_only_not_persisted",
        "title": memory_preview_title(title, cleaned_text),
        "cleaned_text": cleaned_text,
        "original_text_preview": original_text_preview or cleaned_text[:MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS],
        "candidate_type": candidate_type,
        "suggested_skill_id": "memory_skills",
        "confidence": confidence,
        "status": "preview_only",
        "source": source,
        "confirmation_required": True,
        "user_approved_at": None,
        "next_action": "Review this preview. Nothing has been saved.",
        "safety_notes": safety_notes,
        "tags": tags,
        "privacy_note": "User-provided local candidate preview; avoid storing sensitive raw text.",
        "redaction_status": "preview_only",
    }
    return HTTPStatus.OK, {
        "ok": True,
        "preview_only": True,
        "not_saved": True,
        "read_only": True,
        "no_persistence": True,
        "runtime_write": False,
        "save_endpoint": False,
        "phase": "phase_2b_preview_only",
        "candidate_preview": candidate_preview,
        "privacy_warning": MEMORY_PREVIEW_PRIVACY_WARNING,
        "next_step": "Review this preview. Nothing has been saved.",
        "safety_notes": [
            "Preview endpoint is write-free.",
            "No candidate file, local state, repo write, or save endpoint is created.",
            "Voice Inbox does not save Memory / Skills candidates automatically.",
        ],
    }


def memory_save_dry_run_error(error: str) -> tuple[int, dict[str, Any]]:
    """Return a safe dry-run validation error without filesystem side effects."""

    return HTTPStatus.BAD_REQUEST, {
        "ok": False,
        "dry_run": True,
        "valid_for_local_save": False,
        "error": error,
        "will_write_files": False,
        "will_create_directory": False,
        "save_endpoint_enabled": False,
    }


def reject_memory_save_dry_run_disallowed_fields(payload: dict[str, Any]) -> str | None:
    """Reject raw transcript and user-controlled path fields before any future save."""

    if any(field in payload for field in MEMORY_SAVE_DRY_RUN_DISALLOWED_RAW_FIELDS):
        return "raw_transcript_not_allowed"
    if any(field in payload for field in MEMORY_SAVE_DRY_RUN_DISALLOWED_PATH_FIELDS):
        return "path_field_not_allowed"
    return None


def validate_memory_save_dry_run_choice(
    candidate: dict[str, Any],
    field: str,
    allowed: set[str],
    error: str,
) -> tuple[int, str | None, str]:
    """Validate an enum-like field for a dry-run save request."""

    value = candidate.get(field)
    if not isinstance(value, str):
        return HTTPStatus.BAD_REQUEST, error, ""
    if not memory_string_has_valid_unicode(value):
        return HTTPStatus.BAD_REQUEST, "invalid_unicode", ""
    normalized = value.strip().lower()
    if normalized not in allowed:
        return HTTPStatus.BAD_REQUEST, error, ""
    return HTTPStatus.OK, None, normalized


def validate_memory_skills_save_dry_run(payload: Any) -> tuple[int, dict[str, Any]]:
    """Validate a future local-save request candidate without enabling a save endpoint."""

    if not isinstance(payload, dict):
        return memory_save_dry_run_error("request_body_must_be_object")
    disallowed_error = reject_memory_save_dry_run_disallowed_fields(payload)
    if disallowed_error:
        return memory_save_dry_run_error(disallowed_error)
    if payload.get("explicit_confirmation") is not True:
        return memory_save_dry_run_error("explicit_confirmation_required")
    if payload.get("privacy_reviewed") is not True:
        return memory_save_dry_run_error("privacy_review_required")
    if payload.get("save_scope") != MEMORY_SAVE_DRY_RUN_REQUIRED_SCOPE:
        return memory_save_dry_run_error("invalid_save_scope")

    candidate = payload.get("candidate_preview")
    if candidate is None:
        return memory_save_dry_run_error("missing_candidate_preview")
    if not isinstance(candidate, dict):
        return memory_save_dry_run_error("candidate_preview_must_be_object")
    disallowed_error = reject_memory_save_dry_run_disallowed_fields(candidate)
    if disallowed_error:
        return memory_save_dry_run_error(disallowed_error)
    if not memory_json_strings_have_valid_unicode(candidate):
        return memory_save_dry_run_error("invalid_unicode")

    if candidate.get("schema_version") != "memory_candidate.v1":
        return memory_save_dry_run_error("invalid_schema_version")
    if candidate.get("id") != "preview_only_not_persisted":
        return memory_save_dry_run_error("invalid_candidate_id")
    if candidate.get("status") != "preview_only":
        return memory_save_dry_run_error("candidate_must_be_preview_only")
    if candidate.get("suggested_skill_id") != "memory_skills":
        return memory_save_dry_run_error("invalid_suggested_skill_id")
    if candidate.get("confirmation_required") is not True:
        return memory_save_dry_run_error("confirmation_required_expected")
    if candidate.get("user_approved_at") is not None:
        return memory_save_dry_run_error("candidate_already_approved")
    if candidate.get("redaction_status") != "preview_only":
        return memory_save_dry_run_error("invalid_redaction_status")

    status, error, title = normalize_memory_preview_string(
        candidate,
        "title",
        MEMORY_PREVIEW_TITLE_MAX_CHARS,
        required=True,
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_title")

    status, error, cleaned_text = normalize_memory_preview_string(
        candidate,
        "cleaned_text",
        MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS,
        required=True,
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_cleaned_text")

    status, error, original_text_preview = normalize_memory_preview_string(
        candidate,
        "original_text_preview",
        MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS,
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_original_text_preview")

    status, error, next_action = normalize_memory_preview_string(
        candidate,
        "next_action",
        MEMORY_SAVE_DRY_RUN_NOTE_MAX_CHARS,
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_next_action")

    status, error, privacy_note = normalize_memory_preview_string(
        candidate,
        "privacy_note",
        MEMORY_SAVE_DRY_RUN_NOTE_MAX_CHARS,
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_privacy_note")

    status, error, tags = normalize_memory_preview_list(
        candidate,
        "tags",
        MEMORY_PREVIEW_MAX_TAGS,
        MEMORY_PREVIEW_TAG_MAX_CHARS,
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_tags")

    status, error, safety_notes = normalize_memory_preview_list(
        candidate,
        "safety_notes",
        MEMORY_PREVIEW_MAX_SAFETY_NOTES,
        MEMORY_PREVIEW_SAFETY_NOTE_MAX_CHARS,
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_safety_notes")

    status, error, candidate_type = validate_memory_save_dry_run_choice(
        candidate,
        "candidate_type",
        MEMORY_PREVIEW_CANDIDATE_TYPES,
        "invalid_candidate_type",
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_candidate_type")

    status, error, confidence = validate_memory_save_dry_run_choice(
        candidate,
        "confidence",
        MEMORY_PREVIEW_CONFIDENCE_VALUES,
        "invalid_confidence",
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_confidence")

    status, error, source = validate_memory_save_dry_run_choice(
        candidate,
        "source",
        MEMORY_PREVIEW_SOURCES,
        "invalid_source",
    )
    if status != HTTPStatus.OK:
        return memory_save_dry_run_error(error or "invalid_source")

    normalized_candidate = {
        "schema_version": "memory_candidate.v1",
        "id": "preview_only_not_persisted",
        "title": title,
        "cleaned_text": cleaned_text,
        "original_text_preview": original_text_preview,
        "candidate_type": candidate_type,
        "suggested_skill_id": "memory_skills",
        "confidence": confidence,
        "status": "preview_only",
        "source": source,
        "confirmation_required": True,
        "user_approved_at": None,
        "next_action": next_action,
        "safety_notes": safety_notes,
        "tags": tags,
        "privacy_note": privacy_note,
        "redaction_status": "preview_only",
    }
    return HTTPStatus.OK, {
        "ok": True,
        "dry_run": True,
        "valid_for_local_save": True,
        "will_write_files": False,
        "will_create_directory": False,
        "save_endpoint_enabled": False,
        "phase": MEMORY_SAVE_DRY_RUN_PHASE,
        "candidate": normalized_candidate,
        "warnings": [
            "This is a validation dry-run. Nothing has been saved.",
            "No candidate file, local state, directory, or save endpoint was created.",
        ],
    }


def memory_internal_subsystem_error(status: HTTPStatus, error: str) -> tuple[int, dict[str, Any]]:
    """Return a fixed internal-helper error without echoing request or secret material."""

    return status, {"ok": False, "error": error}


def memory_secret_token(generator: Any | None = None) -> str:
    """Create a URL-safe token from at least 256 bits, with deterministic test injection."""

    raw = secrets.token_bytes(MEMORY_SECRET_BYTES) if generator is None else generator(MEMORY_SECRET_BYTES)
    if not isinstance(raw, (bytes, bytearray)) or len(raw) < MEMORY_SECRET_BYTES:
        raise ValueError("secret generator must return at least 256 bits")
    return base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode("ascii")


def memory_secret_token_is_valid(token: Any) -> bool:
    """Return whether a token has the bounded URL-safe shape produced by this module."""

    return isinstance(token, str) and len(token) <= 256 and MEMORY_SECRET_TOKEN_PATTERN.fullmatch(token) is not None


def memory_secret_token_digest(token: str) -> bytes:
    """Return a one-way digest so raw preview tokens are not registry keys."""

    return hashlib.sha256(token.encode("ascii")).digest()


class SessionRegistry:
    """Bounded process-local session registry for internal/tests-only request guards."""

    cookie_policy = {
        "name": MEMORY_SESSION_COOKIE_NAME,
        "http_only": True,
        "same_site": "Strict",
        "path": "/",
        "secure": False,
        "reason_secure_false": "loopback_http_only",
    }

    def __init__(
        self,
        *,
        max_entries: int = MEMORY_SESSION_MAX_ENTRIES,
        idle_ttl_seconds: float = MEMORY_SESSION_IDLE_TTL_SECONDS,
        clock: Any | None = None,
        token_generator: Any | None = None,
    ) -> None:
        if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries <= 0:
            raise ValueError("max_entries must be a positive integer")
        if not isinstance(idle_ttl_seconds, (int, float)) or isinstance(idle_ttl_seconds, bool):
            raise ValueError("idle_ttl_seconds must be numeric")
        if not math.isfinite(float(idle_ttl_seconds)) or idle_ttl_seconds <= 0:
            raise ValueError("idle_ttl_seconds must be finite and positive")
        self.max_entries = max_entries
        self.idle_ttl_seconds = float(idle_ttl_seconds)
        self._clock = time.monotonic if clock is None else clock
        self._token_generator = token_generator
        self._entries: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        now = float(self._clock())
        if not math.isfinite(now):
            raise ValueError("clock must return a finite value")
        return now

    def _purge_expired_locked(self, now: float) -> None:
        expired = [session_id for session_id, entry in self._entries.items() if now >= entry["expires_at_monotonic"]]
        for session_id in expired:
            self._entries.pop(session_id, None)

    def issue(self) -> tuple[int, dict[str, Any]]:
        """Issue one process-local session and server-verified CSRF token."""

        try:
            now = self._now()
            with self._lock:
                self._purge_expired_locked(now)
                if len(self._entries) >= self.max_entries:
                    return memory_internal_subsystem_error(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        "session_capacity_reached",
                    )
                session_id = ""
                for _ in range(MEMORY_SECRET_CREATE_ATTEMPTS):
                    candidate = memory_secret_token(self._token_generator)
                    if candidate not in self._entries:
                        session_id = candidate
                        break
                if not session_id:
                    return memory_internal_subsystem_error(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        "session_issue_failed",
                    )
                csrf_token = memory_secret_token(self._token_generator)
                self._entries[session_id] = {
                    "csrf_digest": memory_secret_token_digest(csrf_token),
                    "created_at_monotonic": now,
                    "last_seen_monotonic": now,
                    "expires_at_monotonic": now + self.idle_ttl_seconds,
                }
        except Exception:
            return memory_internal_subsystem_error(HTTPStatus.INTERNAL_SERVER_ERROR, "session_issue_failed")
        return HTTPStatus.OK, {
            "ok": True,
            "session_id": session_id,
            "csrf_token": csrf_token,
            "idle_ttl_seconds": self.idle_ttl_seconds,
            "cookie_policy": dict(self.cookie_policy),
        }

    def verify(self, session_id: Any, csrf_token: Any) -> tuple[int, dict[str, Any]]:
        """Verify and touch one session while unifying all credential failures."""

        if not memory_secret_token_is_valid(session_id) or not memory_secret_token_is_valid(csrf_token):
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "request_verification_failed")
        try:
            now = self._now()
            csrf_digest = memory_secret_token_digest(csrf_token)
            with self._lock:
                self._purge_expired_locked(now)
                entry = self._entries.get(session_id)
                if entry is None or not hmac.compare_digest(entry["csrf_digest"], csrf_digest):
                    return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "request_verification_failed")
                entry["last_seen_monotonic"] = now
                entry["expires_at_monotonic"] = now + self.idle_ttl_seconds
        except Exception:
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "request_verification_failed")
        return HTTPStatus.OK, {"ok": True, "session_id": session_id}

    def active_count(self) -> int:
        """Return the active bounded size for deterministic tests and future metadata."""

        try:
            now = self._now()
            with self._lock:
                self._purge_expired_locked(now)
                return len(self._entries)
        except Exception:
            return 0


def memory_http_metadata_error(status: HTTPStatus, error: str) -> tuple[int, dict[str, Any]]:
    """Return a bounded raw-header adapter error without echoing header values."""

    return status, {"ok": False, "error": error}


def adapt_memory_guarded_http_metadata(
    raw_headers: Any,
    *,
    max_body_bytes: int = MAX_JSON_BODY_BYTES,
    max_header_count: int = MEMORY_HTTP_METADATA_MAX_HEADER_COUNT,
) -> tuple[int, dict[str, Any]]:
    """Adapt duplicate-preserving raw header pairs for internal/tests-only guard use."""

    if (
        isinstance(raw_headers, (str, bytes, bytearray, Mapping))
        or not isinstance(max_body_bytes, int)
        or isinstance(max_body_bytes, bool)
        or max_body_bytes < 0
        or not isinstance(max_header_count, int)
        or isinstance(max_header_count, bool)
        or max_header_count <= 0
    ):
        return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")

    try:
        iterator = iter(raw_headers)
    except TypeError:
        return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")

    collected: dict[str, str] = {}
    seen_security_headers: set[str] = set()
    header_count = 0
    try:
        for item in iterator:
            header_count += 1
            if header_count > max_header_count:
                return memory_http_metadata_error(
                    HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE,
                    "request_headers_too_large",
                )
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
            raw_name, raw_value = item
            if not isinstance(raw_name, str) or not isinstance(raw_value, str):
                return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
            if (
                not raw_name
                or len(raw_name) > MEMORY_HTTP_METADATA_MAX_HEADER_NAME_CHARS
                or MEMORY_HTTP_HEADER_NAME_PATTERN.fullmatch(raw_name) is None
                or len(raw_value) > MEMORY_HTTP_METADATA_MAX_HEADER_VALUE_CHARS
                or raw_value != raw_value.strip()
                or any(ord(character) < 0x20 or ord(character) == 0x7F for character in raw_value)
            ):
                return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
            try:
                raw_name.encode("ascii", errors="strict")
                raw_value.encode("ascii", errors="strict")
            except UnicodeEncodeError:
                return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")

            name = raw_name.lower()
            if name == "transfer-encoding":
                return memory_http_metadata_error(
                    HTTPStatus.BAD_REQUEST,
                    "transfer_encoding_not_allowed",
                )
            metadata_key = MEMORY_HTTP_METADATA_HEADER_MAP.get(name)
            if metadata_key is None:
                continue
            if name in seen_security_headers:
                return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
            seen_security_headers.add(name)
            collected[metadata_key] = raw_value
    except Exception:
        return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")

    if seen_security_headers != MEMORY_HTTP_METADATA_REQUIRED_HEADERS:
        return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_request_metadata")

    raw_content_length = collected.pop("content_length")
    if re.fullmatch(r"(?:0|[1-9][0-9]*)", raw_content_length) is None:
        return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_content_length")
    try:
        content_length = int(raw_content_length)
    except ValueError:
        return memory_http_metadata_error(HTTPStatus.BAD_REQUEST, "invalid_content_length")
    if content_length > max_body_bytes:
        return memory_http_metadata_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request_too_large")

    return HTTPStatus.OK, {
        "ok": True,
        "request_metadata": collected,
        "content_length": content_length,
        "header_count": header_count,
    }


class LocalRequestGuard:
    """Validate synthetic guarded-request metadata; not connected to the HTTP handler."""

    def __init__(self, bound_host: str, bound_port: int, sessions: SessionRegistry) -> None:
        if bound_host != DEFAULT_HOST:
            raise ValueError("request guard requires the IPv4 loopback host")
        if not isinstance(bound_port, int) or isinstance(bound_port, bool) or not 1 <= bound_port <= 65535:
            raise ValueError("bound_port must be a valid TCP port")
        if not isinstance(sessions, SessionRegistry):
            raise TypeError("sessions must be a SessionRegistry")
        self.expected_host = f"{bound_host}:{bound_port}"
        self.expected_origin = f"http://{self.expected_host}"
        self.sessions = sessions

    @staticmethod
    def _single_metadata_value(metadata: dict[str, Any], key: str) -> str | None:
        value = metadata.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], str):
            return value[0]
        return None

    @staticmethod
    def _content_type_is_allowed(value: str) -> bool:
        parts = value.split(";")
        if parts[0].strip().lower() != "application/json":
            return False
        if len(parts) == 1:
            return True
        return len(parts) == 2 and parts[1].strip().lower() == "charset=utf-8"

    @staticmethod
    def _session_from_cookie(value: str) -> str | None:
        matches: list[str] = []
        for part in value.split(";"):
            item = part.strip()
            if not item or "=" not in item:
                return None
            name, cookie_value = item.split("=", 1)
            if name.strip() == MEMORY_SESSION_COOKIE_NAME:
                matches.append(cookie_value.strip())
        if len(matches) != 1 or not memory_secret_token_is_valid(matches[0]):
            return None
        return matches[0]

    def validate(self, metadata: Any) -> tuple[int, dict[str, Any]]:
        """Validate Host, Origin, JSON media type, session cookie, and CSRF header."""

        if not isinstance(metadata, dict):
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "invalid_host")
        host = self._single_metadata_value(metadata, "host")
        if host != self.expected_host:
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "invalid_host")
        origin = self._single_metadata_value(metadata, "origin")
        if origin != self.expected_origin:
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "invalid_origin")
        content_type = self._single_metadata_value(metadata, "content_type")
        if content_type is None or not self._content_type_is_allowed(content_type):
            return memory_internal_subsystem_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "unsupported_media_type")
        cookie = self._single_metadata_value(metadata, "cookie")
        csrf_token = self._single_metadata_value(metadata, "csrf")
        if cookie is None or csrf_token is None:
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "request_verification_failed")
        session_id = self._session_from_cookie(cookie)
        if session_id is None:
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "request_verification_failed")
        verify_status, verify_result = self.sessions.verify(session_id, csrf_token)
        if verify_status != HTTPStatus.OK:
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "request_verification_failed")
        return HTTPStatus.OK, {
            "ok": True,
            "guarded": True,
            "session_id": verify_result["session_id"],
        }


def canonicalize_memory_candidate_snapshot(candidate_preview: Any) -> tuple[int, dict[str, Any]]:
    """Return one validated, bounded canonical preview snapshot and its domain-separated digest."""

    validation_status, validation_result = validate_memory_skills_save_dry_run(
        {
            "candidate_preview": candidate_preview,
            "explicit_confirmation": True,
            "privacy_reviewed": True,
            "save_scope": MEMORY_SAVE_DRY_RUN_REQUIRED_SCOPE,
        }
    )
    if validation_status != HTTPStatus.OK:
        return memory_internal_subsystem_error(
            HTTPStatus.BAD_REQUEST,
            str(validation_result.get("error", "invalid_candidate_snapshot")),
        )
    normalized = validation_result["candidate"]
    snapshot = {field: normalized[field] for field in MEMORY_CANONICAL_PREVIEW_FIELDS}
    if not memory_json_strings_have_valid_unicode(snapshot):
        return memory_internal_subsystem_error(HTTPStatus.BAD_REQUEST, "invalid_unicode")
    try:
        canonical_bytes = json.dumps(
            snapshot,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return memory_internal_subsystem_error(HTTPStatus.BAD_REQUEST, "invalid_unicode")
    except (TypeError, ValueError):
        return memory_internal_subsystem_error(HTTPStatus.BAD_REQUEST, "invalid_candidate_snapshot")
    if len(canonical_bytes) > MEMORY_CANDIDATE_JSON_MAX_BYTES:
        return memory_internal_subsystem_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "candidate_json_too_large")
    candidate_digest = hashlib.sha256(MEMORY_PREVIEW_DIGEST_PREFIX + canonical_bytes).hexdigest()
    return HTTPStatus.OK, {
        "ok": True,
        "candidate_digest": candidate_digest,
        "canonical_snapshot": json.loads(canonical_bytes.decode("utf-8")),
        "canonical_bytes": canonical_bytes,
        "byte_size": len(canonical_bytes),
    }


class PreviewTokenRegistry:
    """Bounded process-local one-time preview tokens; internal/tests-only and route-free."""

    def __init__(
        self,
        *,
        max_entries: int = MEMORY_PREVIEW_TOKEN_MAX_ENTRIES,
        per_session_limit: int = MEMORY_PREVIEW_TOKEN_PER_SESSION_MAX_ENTRIES,
        ttl_seconds: float = MEMORY_PREVIEW_TOKEN_TTL_SECONDS,
        clock: Any | None = None,
        token_generator: Any | None = None,
    ) -> None:
        for name, value in (("max_entries", max_entries), ("per_session_limit", per_session_limit)):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if per_session_limit > max_entries:
            raise ValueError("per_session_limit cannot exceed max_entries")
        if not isinstance(ttl_seconds, (int, float)) or isinstance(ttl_seconds, bool):
            raise ValueError("ttl_seconds must be numeric")
        if not math.isfinite(float(ttl_seconds)) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be finite and positive")
        self.max_entries = max_entries
        self.per_session_limit = per_session_limit
        self.ttl_seconds = float(ttl_seconds)
        self._clock = time.monotonic if clock is None else clock
        self._token_generator = token_generator
        self._entries: dict[bytes, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        now = float(self._clock())
        if not math.isfinite(now):
            raise ValueError("clock must return a finite value")
        return now

    def _purge_expired_locked(self, now: float) -> None:
        expired = [digest for digest, entry in self._entries.items() if now >= entry["expires_at_monotonic"]]
        for digest in expired:
            self._entries.pop(digest, None)

    def issue(
        self,
        session_id: Any,
        candidate_preview: Any,
        *,
        privacy_reviewed: Any = False,
    ) -> tuple[int, dict[str, Any]]:
        """Issue one token bound to a validated server-stored canonical snapshot."""

        if not memory_secret_token_is_valid(session_id):
            return memory_internal_subsystem_error(HTTPStatus.FORBIDDEN, "request_verification_failed")
        if privacy_reviewed is not True:
            return memory_internal_subsystem_error(HTTPStatus.BAD_REQUEST, "privacy_review_required")
        snapshot_status, snapshot_result = canonicalize_memory_candidate_snapshot(candidate_preview)
        if snapshot_status != HTTPStatus.OK:
            return snapshot_status, snapshot_result
        candidate_digest = snapshot_result["candidate_digest"]
        canonical_bytes = snapshot_result["canonical_bytes"]
        try:
            now = self._now()
            with self._lock:
                self._purge_expired_locked(now)
                if any(
                    hmac.compare_digest(entry["session_id"], session_id)
                    and hmac.compare_digest(entry["candidate_digest"], candidate_digest)
                    for entry in self._entries.values()
                ):
                    return memory_internal_subsystem_error(HTTPStatus.CONFLICT, "preview_token_already_active")
                if len(self._entries) >= self.max_entries:
                    return memory_internal_subsystem_error(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        "preview_token_capacity_reached",
                    )
                session_count = sum(
                    1 for entry in self._entries.values() if hmac.compare_digest(entry["session_id"], session_id)
                )
                if session_count >= self.per_session_limit:
                    return memory_internal_subsystem_error(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        "preview_token_capacity_reached",
                    )
                raw_token = ""
                token_digest = b""
                for _ in range(MEMORY_SECRET_CREATE_ATTEMPTS):
                    candidate_token = memory_secret_token(self._token_generator)
                    candidate_token_digest = memory_secret_token_digest(candidate_token)
                    if candidate_token_digest not in self._entries:
                        raw_token = candidate_token
                        token_digest = candidate_token_digest
                        break
                if not raw_token:
                    return memory_internal_subsystem_error(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        "preview_token_issue_failed",
                    )
                self._entries[token_digest] = {
                    "token_digest": token_digest,
                    "session_id": session_id,
                    "candidate_digest": candidate_digest,
                    "canonical_snapshot": canonical_bytes,
                    "issued_at_monotonic": now,
                    "expires_at_monotonic": now + self.ttl_seconds,
                }
        except Exception:
            return memory_internal_subsystem_error(HTTPStatus.INTERNAL_SERVER_ERROR, "preview_token_issue_failed")
        return HTTPStatus.OK, {
            "ok": True,
            "preview_token": raw_token,
            "candidate_digest": candidate_digest,
            "expires_in_seconds": self.ttl_seconds,
        }

    def claim(self, session_id: Any, raw_token: Any) -> tuple[int, dict[str, Any]]:
        """Atomically pop one session-bound token and return its server-stored snapshot once."""

        if not memory_secret_token_is_valid(session_id) or not memory_secret_token_is_valid(raw_token):
            return memory_internal_subsystem_error(
                HTTPStatus.CONFLICT,
                "invalid_or_expired_preview_token",
            )
        try:
            now = self._now()
            token_digest = memory_secret_token_digest(raw_token)
            with self._lock:
                self._purge_expired_locked(now)
                entry = self._entries.get(token_digest)
                if entry is None or not hmac.compare_digest(entry["session_id"], session_id):
                    return memory_internal_subsystem_error(
                        HTTPStatus.CONFLICT,
                        "invalid_or_expired_preview_token",
                    )
                entry = self._entries.pop(token_digest)
            snapshot = json.loads(entry["canonical_snapshot"].decode("utf-8"))
        except Exception:
            return memory_internal_subsystem_error(
                HTTPStatus.CONFLICT,
                "invalid_or_expired_preview_token",
            )
        return HTTPStatus.OK, {
            "ok": True,
            "candidate_digest": entry["candidate_digest"],
            "canonical_snapshot": snapshot,
        }

    def active_count(self) -> int:
        """Return the active bounded token count after deterministic expiry cleanup."""

        try:
            now = self._now()
            with self._lock:
                self._purge_expired_locked(now)
                return len(self._entries)
        except Exception:
            return 0


def memory_candidate_write_error(status: HTTPStatus, error: str) -> tuple[int, dict[str, Any]]:
    """Return a safe candidate write helper error without exposing stack traces."""

    return status, {
        "ok": False,
        "saved": False,
        "error": error,
        "will_run_automatically": False,
        "skill_created": False,
        "registry_modified": False,
    }


def generate_memory_candidate_id(id_generator: Any | None = None) -> str:
    """Return a generated storage ID that is independent of user-provided text."""

    if id_generator is not None:
        return str(id_generator()).strip()
    return f"mem_{uuid.uuid4().hex[:12]}"


def is_safe_memory_candidate_id(candidate_id: str) -> bool:
    """Validate a candidate storage ID before it is used as a filename."""

    if not isinstance(candidate_id, str):
        return False
    if "/" in candidate_id or "\\" in candidate_id or ":" in candidate_id or ".." in candidate_id:
        return False
    return MEMORY_CANDIDATE_ID_PATTERN.fullmatch(candidate_id) is not None


def memory_candidate_timestamp(clock: Any | None = None) -> str:
    """Return a timestamp for explicit candidate writes, with deterministic tests via injection."""

    if clock is not None:
        value = clock()
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return str(value)
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def saved_memory_candidate_from_dry_run(candidate: dict[str, Any], candidate_id: str, timestamp: str) -> dict[str, Any]:
    """Build the persisted candidate object without source preview, raw transcript, or path fields."""

    return {
        "schema_version": "memory_candidate.v1",
        "storage_version": MEMORY_CANDIDATE_STORAGE_VERSION,
        "id": candidate_id,
        "title": candidate["title"],
        "cleaned_text": candidate["cleaned_text"],
        "candidate_type": candidate["candidate_type"],
        "suggested_skill_id": "memory_skills",
        "confidence": candidate["confidence"],
        "status": "saved",
        "source": candidate["source"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "confirmation_required": True,
        "user_approved_at": timestamp,
        "next_action": candidate.get("next_action", ""),
        "safety_notes": candidate.get("safety_notes", []),
        "tags": candidate.get("tags", []),
        "privacy_note": candidate.get("privacy_note", ""),
        "redaction_status": "user_confirmed",
    }


def cleanup_memory_candidate_temp_file(temp_file: Path) -> None:
    """Best-effort cleanup for a candidate temp file."""

    try:
        temp_file.unlink(missing_ok=True)
    except OSError:
        pass


def serialize_memory_candidate_json(
    stored_candidate: Any,
    *,
    max_bytes: int = MEMORY_CANDIDATE_JSON_MAX_BYTES,
) -> tuple[int, str, bytes]:
    """Serialize one candidate completely before any filesystem path is resolved or created."""

    if not memory_json_strings_have_valid_unicode(stored_candidate):
        return HTTPStatus.BAD_REQUEST, "invalid_unicode", b""
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        return HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed", b""
    try:
        serialized_text = json.dumps(
            stored_candidate,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        serialized_bytes = f"{serialized_text}\n".encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        return HTTPStatus.BAD_REQUEST, "invalid_unicode", b""
    except (TypeError, ValueError):
        return HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed", b""
    if len(serialized_bytes) > max_bytes:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "candidate_json_too_large", b""
    return HTTPStatus.OK, "", serialized_bytes


def validate_memory_candidate_directory_path(
    candidate_dir_policy_path: Path,
    *,
    repo_root: Path = REPO_ROOT,
    expected_candidate_dir: Path | None = None,
    require_exists: bool = False,
) -> tuple[int, str, Path]:
    """Apply best-effort repo and reparse checks to a lexical candidate directory path."""

    try:
        if existing_path_chain_has_reparse_point(candidate_dir_policy_path):
            return HTTPStatus.BAD_REQUEST, "candidate_path_not_safe", Path()
        candidate_dir = candidate_dir_policy_path.resolve(strict=require_exists)
        if require_exists and not candidate_dir.is_dir():
            return HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed", Path()
        if expected_candidate_dir is not None and candidate_dir != expected_candidate_dir:
            return HTTPStatus.BAD_REQUEST, "candidate_path_not_safe", Path()
        if is_path_inside_repo(candidate_dir, repo_root):
            return HTTPStatus.BAD_REQUEST, "local_state_dir_inside_repo", Path()
    except (OSError, RuntimeError):
        return HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed", Path()
    return HTTPStatus.OK, "", candidate_dir


def write_memory_skills_candidate(
    dry_run_result: Any,
    *,
    env: Any | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
    id_generator: Any | None = None,
    clock: Any | None = None,
    max_json_bytes: int = MEMORY_CANDIDATE_JSON_MAX_BYTES,
    linker: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    """Write one validated candidate JSON file; not connected to any API or UI route."""

    if not isinstance(dry_run_result, dict) or dry_run_result.get("dry_run") is not True:
        return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "valid_dry_run_result_required")
    if dry_run_result.get("valid_for_local_save") is not True:
        return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "dry_run_not_valid_for_local_save")
    if dry_run_result.get("save_endpoint_enabled") is not False:
        return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "save_endpoint_must_remain_disabled")
    if dry_run_result.get("will_write_files") is not False or dry_run_result.get("will_create_directory") is not False:
        return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "dry_run_must_not_include_writes")
    candidate = dry_run_result.get("candidate")
    if not isinstance(candidate, dict):
        return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "candidate_required")

    validation_body = {
        "candidate_preview": dict(candidate),
        "explicit_confirmation": True,
        "privacy_reviewed": True,
        "save_scope": MEMORY_SAVE_DRY_RUN_REQUIRED_SCOPE,
    }
    validation_status, validation_result = validate_memory_skills_save_dry_run(validation_body)
    if validation_status != HTTPStatus.OK:
        return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, validation_result.get("error", "invalid_candidate"))

    try:
        candidate_id = generate_memory_candidate_id(id_generator)
        if not memory_string_has_valid_unicode(candidate_id):
            return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "invalid_unicode")
        if not is_safe_memory_candidate_id(candidate_id):
            return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "invalid_candidate_id")
        timestamp = memory_candidate_timestamp(clock)
        stored_candidate = saved_memory_candidate_from_dry_run(
            validation_result["candidate"],
            candidate_id,
            timestamp,
        )
        serialization_status, serialization_error, serialized_candidate = serialize_memory_candidate_json(
            stored_candidate,
            max_bytes=max_json_bytes,
        )
    except Exception:
        return memory_candidate_write_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed")
    if serialization_status != HTTPStatus.OK:
        return memory_candidate_write_error(serialization_status, serialization_error)

    try:
        state_paths = resolve_memory_skills_state_paths(
            env=env,
            home_dir=home_dir,
            repo_root=repo_root,
            is_windows=is_windows,
        )
    except (OSError, RuntimeError):
        return memory_candidate_write_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed")
    if not state_paths.get("ok"):
        return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, state_paths.get("error", "invalid_state_path"))
    candidate_dir_policy_path = state_paths.get("candidate_dir_policy_path")
    if not isinstance(candidate_dir_policy_path, Path):
        return memory_candidate_write_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed")
    path_status, path_error, candidate_dir = validate_memory_candidate_directory_path(
        candidate_dir_policy_path,
        repo_root=repo_root,
    )
    if path_status != HTTPStatus.OK:
        return memory_candidate_write_error(path_status, path_error)

    candidate_file = candidate_dir / f"{candidate_id}.json"
    if candidate_file.parent != candidate_dir or is_path_inside_repo(candidate_dir, repo_root):
        return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "candidate_path_not_safe")
    if os.path.lexists(candidate_file):
        return memory_candidate_write_error(HTTPStatus.CONFLICT, "candidate_file_exists")

    temp_file: Path | None = None
    publish_link = os.link if linker is None else linker
    try:
        candidate_dir_policy_path.mkdir(parents=True, exist_ok=True)
        path_status, path_error, candidate_dir_after_mkdir = validate_memory_candidate_directory_path(
            candidate_dir_policy_path,
            repo_root=repo_root,
            expected_candidate_dir=candidate_dir,
            require_exists=True,
        )
        if path_status != HTTPStatus.OK:
            return memory_candidate_write_error(path_status, path_error)
        candidate_dir = candidate_dir_after_mkdir
        candidate_file = candidate_dir / f"{candidate_id}.json"
        if candidate_file.parent != candidate_dir or is_path_inside_repo(candidate_dir, repo_root):
            return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "candidate_path_not_safe")
        if os.path.lexists(candidate_file):
            return memory_candidate_write_error(HTTPStatus.CONFLICT, "candidate_file_exists")

        for _ in range(MEMORY_CANDIDATE_TEMP_CREATE_ATTEMPTS):
            temp_candidate = candidate_dir / f".{candidate_id}.{uuid.uuid4().hex}.tmp"
            if temp_candidate.parent != candidate_dir or is_path_inside_repo(candidate_dir, repo_root):
                return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "candidate_temp_path_not_safe")
            try:
                file = temp_candidate.open("xb")
            except FileExistsError:
                continue
            temp_file = temp_candidate
            with file:
                file.write(serialized_candidate)
                file.flush()
                os.fsync(file.fileno())
            break
        if temp_file is None:
            return memory_candidate_write_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed")

        path_status, path_error, candidate_dir_before_publish = validate_memory_candidate_directory_path(
            candidate_dir_policy_path,
            repo_root=repo_root,
            expected_candidate_dir=candidate_dir,
            require_exists=True,
        )
        if path_status != HTTPStatus.OK:
            return memory_candidate_write_error(path_status, path_error)
        if candidate_dir_before_publish != candidate_dir:
            return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "candidate_path_not_safe")
        candidate_file = candidate_dir / f"{candidate_id}.json"
        if candidate_file.parent != candidate_dir or is_path_inside_repo(candidate_dir, repo_root):
            return memory_candidate_write_error(HTTPStatus.BAD_REQUEST, "candidate_path_not_safe")
        if os.path.lexists(candidate_file):
            return memory_candidate_write_error(HTTPStatus.CONFLICT, "candidate_file_exists")
        try:
            publish_link(temp_file, candidate_file)
        except FileExistsError:
            return memory_candidate_write_error(HTTPStatus.CONFLICT, "candidate_file_exists")
        except OSError:
            return memory_candidate_write_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed")
    except OSError:
        return memory_candidate_write_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed")
    except Exception:
        return memory_candidate_write_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed")
    finally:
        if temp_file is not None:
            cleanup_memory_candidate_temp_file(temp_file)

    if not os.path.lexists(candidate_file):
        return memory_candidate_write_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_write_failed")

    return HTTPStatus.OK, {
        "ok": True,
        "saved": True,
        "status": "saved",
        "candidate_id": candidate_id,
        "candidate_file": str(candidate_file),
        "repo_safe": True,
        "will_run_automatically": False,
        "skill_created": False,
        "registry_modified": False,
        "schema_version": "memory_candidate.v1",
        "storage_version": MEMORY_CANDIDATE_STORAGE_VERSION,
    }


def memory_save_endpoint_error(status: HTTPStatus, error: str) -> tuple[int, dict[str, Any]]:
    """Return a safe approval-gated save endpoint error without path or stack details."""

    return status, {
        "ok": False,
        "saved": False,
        "error": error,
        "skill_created": False,
        "registry_modified": False,
        "will_run_automatically": False,
        "local_only": False,
    }


def save_memory_skills_candidate(
    payload: Any,
    *,
    env: Any | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
    id_generator: Any | None = None,
    clock: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    """Compose candidate validation and writing for internal tests only."""

    validation_status, validation_result = validate_memory_skills_save_dry_run(payload)
    if validation_status != HTTPStatus.OK:
        return memory_save_endpoint_error(
            validation_status,
            str(validation_result.get("error", "invalid_save_request")),
        )

    write_status, write_result = write_memory_skills_candidate(
        validation_result,
        env=env,
        home_dir=home_dir,
        repo_root=repo_root,
        is_windows=is_windows,
        id_generator=id_generator,
        clock=clock,
    )
    if write_status != HTTPStatus.OK:
        return memory_save_endpoint_error(write_status, str(write_result.get("error", "candidate_write_failed")))

    candidate = validation_result["candidate"]
    return HTTPStatus.OK, {
        "ok": True,
        "saved": True,
        "status": "saved",
        "candidate_id": write_result["candidate_id"],
        "title": candidate["title"],
        "message": MEMORY_SAVE_SUCCESS_MESSAGE,
        "skill_created": False,
        "registry_modified": False,
        "will_run_automatically": False,
        "local_only": True,
        "schema_version": write_result["schema_version"],
        "storage_version": write_result["storage_version"],
    }


def coordinate_guarded_memory_skills_save(
    request_guard: Any,
    preview_tokens: Any,
    request_metadata: Any,
    payload: Any,
    *,
    env: Any | None = None,
    home_dir: Path | str | None = None,
    repo_root: Path = REPO_ROOT,
    is_windows: bool | None = None,
    id_generator: Any | None = None,
    clock: Any | None = None,
    max_json_bytes: int = MEMORY_CANDIDATE_JSON_MAX_BYTES,
    linker: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    """Compose guarded one-claim candidate saving for internal/tests-only coverage."""

    if not isinstance(request_guard, LocalRequestGuard) or not isinstance(preview_tokens, PreviewTokenRegistry):
        return memory_save_endpoint_error(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "guarded_save_configuration_invalid",
        )

    guard_status, guard_result = request_guard.validate(request_metadata)
    if guard_status != HTTPStatus.OK:
        error = (
            "unsupported_media_type"
            if guard_status == HTTPStatus.UNSUPPORTED_MEDIA_TYPE
            else "request_verification_failed"
        )
        return memory_save_endpoint_error(guard_status, error)

    if not isinstance(payload, dict) or set(payload) != MEMORY_GUARDED_SAVE_ALLOWED_FIELDS:
        return memory_save_endpoint_error(HTTPStatus.BAD_REQUEST, "invalid_save_request")
    if payload.get("confirmation") != MEMORY_GUARDED_SAVE_CONFIRMATION:
        return memory_save_endpoint_error(HTTPStatus.BAD_REQUEST, "explicit_confirmation_required")

    claim_status, claim_result = preview_tokens.claim(
        guard_result["session_id"],
        payload.get("preview_token"),
    )
    if claim_status != HTTPStatus.OK:
        return memory_save_endpoint_error(
            HTTPStatus.CONFLICT,
            "invalid_or_expired_preview_token",
        )

    snapshot_status, snapshot_result = canonicalize_memory_candidate_snapshot(
        claim_result.get("canonical_snapshot")
    )
    claimed_digest = claim_result.get("candidate_digest")
    if (
        snapshot_status != HTTPStatus.OK
        or not isinstance(claimed_digest, str)
        or len(claimed_digest) != 64
        or any(character not in "0123456789abcdef" for character in claimed_digest)
        or not hmac.compare_digest(
            claimed_digest,
            str(snapshot_result.get("candidate_digest", "")),
        )
    ):
        return memory_save_endpoint_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_save_failed")

    validation_status, validation_result = validate_memory_skills_save_dry_run(
        {
            "candidate_preview": snapshot_result["canonical_snapshot"],
            "explicit_confirmation": True,
            "privacy_reviewed": True,
            "save_scope": MEMORY_SAVE_DRY_RUN_REQUIRED_SCOPE,
        }
    )
    if validation_status != HTTPStatus.OK:
        return memory_save_endpoint_error(HTTPStatus.INTERNAL_SERVER_ERROR, "candidate_save_failed")

    write_status, write_result = write_memory_skills_candidate(
        validation_result,
        env=env,
        home_dir=home_dir,
        repo_root=repo_root,
        is_windows=is_windows,
        id_generator=id_generator,
        clock=clock,
        max_json_bytes=max_json_bytes,
        linker=linker,
    )
    if write_status != HTTPStatus.OK:
        return memory_save_endpoint_error(
            write_status,
            str(write_result.get("error", "candidate_write_failed")),
        )

    candidate = validation_result["candidate"]
    return HTTPStatus.OK, {
        "ok": True,
        "saved": True,
        "status": "saved",
        "candidate_id": write_result["candidate_id"],
        "title": candidate["title"],
        "message": MEMORY_SAVE_SUCCESS_MESSAGE,
        "skill_created": False,
        "registry_modified": False,
        "will_run_automatically": False,
        "local_only": True,
        "original_text_preview_stored": False,
        "schema_version": write_result["schema_version"],
        "storage_version": write_result["storage_version"],
    }


def parse_recent_commits(raw_log: str) -> list[dict[str, Any]]:
    """Parse fixed git log output into display-only commit cards."""

    commits: list[dict[str, Any]] = []
    for line in raw_log.splitlines():
        text = line.strip()
        if not text:
            continue
        hash_value, _, subject = text.partition(" ")
        commits.append(
            {
                "item_id": f"commit:{hash_value}",
                "hash": hash_value,
                "subject": truncate_overview_text(subject or "(no subject)", OVERVIEW_TITLE_MAX_CHARS),
                "read_only": True,
            }
        )
        if len(commits) >= HISTORY_MAX_COMMITS:
            break
    return commits


def assert_history_commit_safety(commit: dict[str, Any]) -> None:
    """Validate one read-only commit card."""

    assert commit["read_only"] is True
    assert commit["item_id"] == f"commit:{commit['hash']}"
    assert commit["hash"]
    assert " " not in commit["hash"]
    assert "\\" not in commit["hash"]
    assert "/" not in commit["hash"]
    assert len(commit["subject"]) <= OVERVIEW_TITLE_MAX_CHARS


def history_payload() -> dict[str, Any]:
    """Return the read-only Checkpoint / History view payload."""

    history_items = discover_history_items()
    checkpoint_docs = [
        item
        for item in history_items
        if item["item_type"] == "checkpoint" or any(marker in item["name"].lower() for marker in ("checkpoint", "summary"))
    ]
    related_items = [item for item in history_items if item not in checkpoint_docs]
    recent_commits = parse_recent_commits(run_read_only_git(("log", "--oneline", "-n", "10")))
    return {
        "ok": True,
        "mode": "read-only",
        "repo": history_repo_payload(),
        "recent_commits": recent_commits,
        "checkpoint_docs": checkpoint_docs[:OVERVIEW_MAX_TOTAL_ITEMS],
        "related_items": related_items[:OVERVIEW_MAX_TOTAL_ITEMS],
        "notes": [
            "This view is read-only.",
            "It does not create commits or checkpoints.",
            "It does not push, tag, reset, checkout, merge, or rebase.",
            "Checkpoint and report files are displayed as metadata only.",
            "Protected path remains visible: jarvis.bat.",
        ],
        "discovery": {
            "safe_directories": [
                {
                    "key": overview_directory_by_key()[key]["key"],
                    "label": overview_directory_by_key()[key]["label"],
                    "path": overview_directory_by_key()[key]["path"],
                    "exists": (REPO_ROOT / overview_directory_by_key()[key]["path"]).is_dir(),
                }
                for key in HISTORY_DIRECTORY_KEYS
            ],
            "allowed_extensions": sorted(OVERVIEW_ALLOWED_EXTENSIONS),
            "name_markers": list(HISTORY_NAME_MARKERS),
            "max_commits": HISTORY_MAX_COMMITS,
            "max_items_per_directory": OVERVIEW_MAX_ITEMS_PER_DIRECTORY,
            "max_total_items": OVERVIEW_MAX_TOTAL_ITEMS,
            "excluded": ["hidden files", ".git", "__pycache__", "secrets-like file names"],
        },
    }


def normalize_message(message: str) -> str:
    """Normalize user text for deterministic keyword matching."""

    return " ".join(str(message).strip().lower().split())


def suggest_skill(message: str) -> dict[str, Any]:
    """Suggest one skill from registry keywords with deterministic matching."""

    normalized = normalize_message(message)
    if not normalized:
        return dict(UNKNOWN_SUGGESTION)

    candidates: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for skill in registry_skills():
        keywords = [keyword.lower() for keyword in skill["route_keywords"]]
        hits = [keyword for keyword in keywords if keyword in normalized]
        if hits:
            priority = ROUTING_PRIORITY.get(skill["skill_id"], 99)
            candidates.append((len(hits), -priority, skill, hits))

    if not candidates:
        return dict(UNKNOWN_SUGGESTION)

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    hit_count, _priority, skill, hits = candidates[0]
    return {
        "recommended_skill": skill["skill_id"],
        "display_name": skill["display_name"],
        "reason": f"Matched deterministic keyword(s): {', '.join(hits[:5])}.",
        "suggested_next_action": skill["safe_next_action"],
        "commands": skill["commands"],
        "matched_keywords": hits[:hit_count],
    }


def clean_voice_transcript(transcript: str) -> str:
    """Normalize a pasted voice transcript with deterministic local rules only."""

    cleaned = " ".join(transcript.replace("\r", "\n").split())
    for source, target in VOICE_TERM_CORRECTIONS:
        cleaned = cleaned.replace(source, target)
    for source, target in VOICE_TOKEN_CORRECTIONS:
        pattern = rf"(?<![0-9A-Za-z가-힣]){re.escape(source)}(?![0-9A-Za-z가-힣])"
        cleaned = re.sub(pattern, target, cleaned)
    if voice_has_development_review_context(cleaned):
        cleaned = re.sub(r"(?<![0-9A-Za-z가-힣])리뷰(?![0-9A-Za-z가-힣])", "review", cleaned)
    return cleaned.strip()


def voice_has_development_review_context(cleaned_transcript: str) -> bool:
    """Allow review correction only when the transcript is clearly development-related."""

    normalized = normalize_message(cleaned_transcript)
    if "리뷰" not in normalized:
        return False
    return any(voice_has_context_term(normalized, term) for term in VOICE_REVIEW_CORRECTION_CONTEXT_TERMS)


def voice_suggest_skill(cleaned_transcript: str) -> dict[str, Any]:
    """Reuse skill routing with a conservative filter for voice-review ambiguity."""

    suggestion = suggest_skill(cleaned_transcript)
    if suggestion.get("recommended_skill") != "hermes_manager":
        return suggestion

    normalized = normalize_message(cleaned_transcript)
    matched_keywords = {normalize_message(keyword) for keyword in suggestion.get("matched_keywords", [])}
    has_broad_hit_context = any(
        voice_has_context_term(normalized, term) for term in VOICE_REVIEW_CORRECTION_CONTEXT_TERMS
    )
    broad_hits_only = matched_keywords and matched_keywords.issubset(VOICE_HERMES_BROAD_HITS)
    if broad_hits_only and not has_broad_hit_context:
        return dict(UNKNOWN_SUGGESTION)
    return suggestion


def voice_has_context_term(normalized_transcript: str, term: str) -> bool:
    """Match short English routing terms as tokens to avoid preview/report overmatches."""

    if term.isascii():
        pattern = rf"(?<![0-9a-z]){re.escape(term)}(?![0-9a-z])"
        return re.search(pattern, normalized_transcript) is not None
    return term in normalized_transcript


def voice_candidate_title(cleaned_transcript: str) -> str:
    """Create a bounded display title from the first transcript sentence."""

    separators = ("。", ".", "?", "!", "\n")
    first_sentence = cleaned_transcript
    for separator in separators:
        if separator in first_sentence:
            first_sentence = first_sentence.split(separator, 1)[0]
    return truncate_overview_text(first_sentence, VOICE_INBOX_TITLE_MAX_CHARS)


def voice_candidate_summary(cleaned_transcript: str) -> str:
    """Create a bounded summary without external model calls."""

    return truncate_overview_text(cleaned_transcript, VOICE_INBOX_SUMMARY_MAX_CHARS)


def voice_confidence(suggestion: dict[str, Any], cleaned_transcript: str) -> str:
    """Return a deterministic confidence level for a voice task candidate."""

    skill_id = suggestion.get("recommended_skill", "unknown")
    if skill_id == "unknown":
        return "low"
    normalized = normalize_message(cleaned_transcript)
    skill = next((item for item in registry_skills() if item["skill_id"] == skill_id), None)
    display_name = normalize_message(skill["display_name"]) if skill else ""
    matched_keywords = [normalize_message(keyword) for keyword in suggestion.get("matched_keywords", [])]
    if display_name and display_name in normalized:
        return "high"
    if any(" " in keyword and keyword in normalized for keyword in matched_keywords):
        return "high"
    if len(matched_keywords) >= 2:
        return "medium"
    return "medium"


def voice_needs_confirmation(suggestion: dict[str, Any], cleaned_transcript: str) -> bool:
    """Voice Inbox always requires human confirmation before handoff."""

    _suggestion = suggestion
    _cleaned_transcript = cleaned_transcript
    return True


def voice_next_action(suggestion: dict[str, Any]) -> str:
    """Return the next manual handoff action for a candidate."""

    skill_id = suggestion.get("recommended_skill", "unknown")
    if skill_id == "unknown":
        return "Review the cleaned task, then choose a skill manually from the sidebar."
    display_name = suggestion.get("display_name") or skill_id
    return f"Review the candidate, then open {display_name} details or copy the handoff command."


def prepare_voice_inbox_task(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Prepare a read-only task candidate from a pasted transcript."""

    if "transcript" not in payload:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing_transcript"}
    transcript = payload["transcript"]
    if not isinstance(transcript, str):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "transcript_must_be_string"}
    if len(transcript) > VOICE_INBOX_MAX_TRANSCRIPT_CHARS:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "transcript_too_long"}
    raw_transcript = transcript.strip()
    if not raw_transcript:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "empty_transcript"}

    cleaned_transcript = clean_voice_transcript(raw_transcript)
    suggestion = voice_suggest_skill(cleaned_transcript)
    task_candidate = {
        "title": voice_candidate_title(cleaned_transcript),
        "summary": voice_candidate_summary(cleaned_transcript),
        "suggested_skill": suggestion["recommended_skill"],
        "confidence": voice_confidence(suggestion, cleaned_transcript),
        "needs_confirmation": voice_needs_confirmation(suggestion, cleaned_transcript),
        "reason": (
            f"{suggestion['reason']} "
            "Voice Inbox candidates require human confirmation before handoff."
        ),
        "matched_keywords": suggestion.get("matched_keywords", []),
        "next_action": voice_next_action(suggestion),
    }
    return HTTPStatus.OK, {
        "ok": True,
        "raw_transcript": raw_transcript,
        "cleaned_transcript": cleaned_transcript,
        "task_candidate": task_candidate,
        "suggested_skill": suggestion["recommended_skill"],
        "display_name": suggestion.get("display_name", "Manual choice needed"),
        "commands": suggestion.get("commands", {"git_bash": "", "powershell": ""}),
        "safety_notes": [
            "This is a task candidate, not an execution.",
            "Jarvis Console does not run Codex, ChatGPT, Hermes, git, or external tools.",
            "Voice Inbox v0.1 does not record audio, run STT, or call external APIs.",
        ],
    }


def parse_json_body(raw_body: bytes) -> tuple[int, dict[str, Any]]:
    """Parse request JSON and return a safe error for malformed input."""

    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "malformed_json"}
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "json_body_must_be_object"}
    return HTTPStatus.OK, payload


def handle_get_api(path: str, query: str = "") -> tuple[int, dict[str, Any]]:
    """Handle read-only GET API routes."""

    try:
        if path == "/api/status":
            return HTTPStatus.OK, status_payload()
        if path == "/api/overview":
            return HTTPStatus.OK, overview_payload()
        if path == "/api/history":
            return HTTPStatus.OK, history_payload()
        if path == "/api/memory-skills":
            return HTTPStatus.OK, memory_skills_payload()
        if path == "/api/skill":
            params = parse_qs(query)
            skill_id = (params.get("skill_id") or [""])[0].strip()
            if not skill_id:
                return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "missing_skill_id"}
            skill = skill_detail(skill_id)
            if skill is None:
                return HTTPStatus.NOT_FOUND, {"ok": False, "error": "unknown_skill"}
            return HTTPStatus.OK, {"ok": True, "skill": skill}
    except RegistryError as exc:
        return HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)}
    return HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"}


def handle_post_api(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Handle POST API routes without running external tools."""

    try:
        if path == "/api/suggest-skill":
            suggestion = suggest_skill(str(payload.get("message", "")))
            return HTTPStatus.OK, {"ok": True, **suggestion}
        if path == "/api/voice-inbox/prepare":
            return prepare_voice_inbox_task(payload)
        if path == CODEX_REVIEW_PREVIEW_ENDPOINT:
            return build_codex_review_preview(payload, REPO_ROOT)
        if path == MEMORY_PREVIEW_ENDPOINT:
            return prepare_memory_candidate_preview(payload)
    except RegistryError as exc:
        return HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)}
    return HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"}


class JarvisConsoleHandler(BaseHTTPRequestHandler):
    """Small local-only request handler for Jarvis Console."""

    server_version = "JarvisConsole/0.1"

    def do_GET(self) -> None:
        if not self._client_is_local():
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "local_clients_only"})
            return

        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            status, payload = handle_get_api(path, parsed.query)
            self._send_json(status, payload)
            return

        if path not in STATIC_ROUTES:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        filename, content_type = STATIC_ROUTES[path]
        file_path = WEB_ROOT / filename
        try:
            content = file_path.read_bytes()
        except OSError:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if not self._client_is_local():
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "local_clients_only"})
            return

        path = urlparse(self.path).path
        if path not in {
            "/api/suggest-skill",
            "/api/voice-inbox/prepare",
            CODEX_REVIEW_PREVIEW_ENDPOINT,
            MEMORY_PREVIEW_ENDPOINT,
        }:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_content_length"})
            return

        if length > MAX_JSON_BODY_BYTES:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "request_too_large"})
            return

        status, payload = parse_json_body(self.rfile.read(length))
        if status != HTTPStatus.OK:
            self._send_json(status, payload)
            return

        response_status, response_payload = handle_post_api(path, payload)
        self._send_json(response_status, response_payload)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _client_is_local(self) -> bool:
        return self.client_address[0] == "127.0.0.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


def run_server(port: int, open_browser: bool) -> None:
    """Run the local browser shell on 127.0.0.1 only."""

    server = ThreadingHTTPServer((DEFAULT_HOST, port), JarvisConsoleHandler)
    url = f"http://{DEFAULT_HOST}:{port}/"
    print(f"Jarvis Console v0.1: {url}")
    print("Local-only. Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Jarvis Console.")
    finally:
        server.server_close()


def run_memory_request_guard_token_self_tests() -> None:
    """Exercise Phase 2C-3b primitives without routes, sleeps, or filesystem writes."""

    class FakeClock:
        def __init__(self, value: float = 1000.0) -> None:
            self.value = value

        def __call__(self) -> float:
            return self.value

        def advance(self, seconds: float) -> None:
            self.value += seconds

    class DeterministicBytes:
        def __init__(self, namespace: str = "default") -> None:
            self.namespace = namespace
            self.counter = 0

        def __call__(self, size: int) -> bytes:
            self.counter += 1
            seed = hashlib.sha256(
                f"jarvis-test-secret-{self.namespace}-{self.counter}".encode("ascii")
            ).digest()
            return (seed * ((size + len(seed) - 1) // len(seed)))[:size]

    def candidate_variant(candidate: dict[str, Any], marker: str) -> dict[str, Any]:
        variant = dict(candidate)
        variant["cleaned_text"] = f'{candidate["cleaned_text"]} {marker}'
        variant["tags"] = list(candidate.get("tags", []))
        variant["safety_notes"] = list(candidate.get("safety_notes", []))
        return variant

    before_status = run_read_only_git(("status", "--short"))
    preview_status, preview_result = prepare_memory_candidate_preview(
        {
            "title": "Request guard token candidate",
            "cleaned_text": "Keep a deterministic candidate snapshot for explicit review.",
            "original_text_preview": "Deterministic preview only.",
            "candidate_type": "operating_rule",
            "confidence": "medium",
            "source": "manual",
            "tags": ["guard", "token"],
            "safety_notes": ["Tests only; no live token issuance."],
        }
    )
    assert preview_status == HTTPStatus.OK
    candidate = preview_result["candidate_preview"]

    session_clock = FakeClock()
    session_generator = DeterministicBytes("sessions")
    sessions = SessionRegistry(clock=session_clock, token_generator=session_generator)
    first_session_status, first_session = sessions.issue()
    second_session_status, second_session = sessions.issue()
    assert first_session_status == HTTPStatus.OK
    assert second_session_status == HTTPStatus.OK
    assert sessions.active_count() == 2
    assert memory_secret_token_is_valid(first_session["session_id"])
    assert memory_secret_token_is_valid(first_session["csrf_token"])
    assert first_session["session_id"] != second_session["session_id"]
    assert first_session["csrf_token"] not in repr(sessions._entries)
    assert first_session["cookie_policy"] == SessionRegistry.cookie_policy
    assert first_session["cookie_policy"]["http_only"] is True
    assert first_session["cookie_policy"]["same_site"] == "Strict"
    assert first_session["cookie_policy"]["path"] == "/"
    assert first_session["cookie_policy"]["secure"] is False

    guard = LocalRequestGuard(DEFAULT_HOST, DEFAULT_PORT, sessions)
    valid_request = {
        "host": f"{DEFAULT_HOST}:{DEFAULT_PORT}",
        "origin": f"http://{DEFAULT_HOST}:{DEFAULT_PORT}",
        "content_type": "application/json",
        "cookie": f'other_cookie=read_only; {MEMORY_SESSION_COOKIE_NAME}={first_session["session_id"]}',
        "csrf": first_session["csrf_token"],
    }

    def assert_guard_error(
        updates: dict[str, Any] | None,
        remove: str | None,
        expected_error: str,
        expected_status: HTTPStatus,
    ) -> None:
        metadata = dict(valid_request)
        if updates:
            metadata.update(updates)
        if remove:
            metadata.pop(remove, None)
        status, result = guard.validate(metadata)
        assert status == expected_status
        assert result == {"ok": False, "error": expected_error}
        rendered = str(result)
        assert first_session["session_id"] not in rendered
        assert first_session["csrf_token"] not in rendered

    for invalid_host in (
        f"{DEFAULT_HOST}:{DEFAULT_PORT + 1}",
        f"localhost:{DEFAULT_PORT}",
        f"{DEFAULT_HOST}:{DEFAULT_PORT},evil.example",
        f" {DEFAULT_HOST}:{DEFAULT_PORT}",
        f"{DEFAULT_HOST}.:{DEFAULT_PORT}",
        f"[::1]:{DEFAULT_PORT}",
    ):
        assert_guard_error({"host": invalid_host}, None, "invalid_host", HTTPStatus.FORBIDDEN)
    assert_guard_error(None, "host", "invalid_host", HTTPStatus.FORBIDDEN)
    assert_guard_error({"host": [valid_request["host"], valid_request["host"]]}, None, "invalid_host", HTTPStatus.FORBIDDEN)
    assert guard.validate(valid_request)[0] == HTTPStatus.OK

    for invalid_origin in (
        "null",
        f"https://{DEFAULT_HOST}:{DEFAULT_PORT}",
        f"http://localhost:{DEFAULT_PORT}",
        f"http://{DEFAULT_HOST}:{DEFAULT_PORT + 1}",
        f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/path",
        f"http://{DEFAULT_HOST}:{DEFAULT_PORT}?query=1",
        f"http://{DEFAULT_HOST}:{DEFAULT_PORT}#fragment",
        f"http://user@{DEFAULT_HOST}:{DEFAULT_PORT}",
        "https://evil.example",
    ):
        assert_guard_error({"origin": invalid_origin}, None, "invalid_origin", HTTPStatus.FORBIDDEN)
    assert_guard_error(None, "origin", "invalid_origin", HTTPStatus.FORBIDDEN)
    assert guard.validate({**valid_request, "origin": f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"})[0] == HTTPStatus.OK

    for invalid_content_type in (
        "text/plain",
        "application/x-www-form-urlencoded",
        "multipart/form-data; boundary=test",
        "application/json; charset=iso-8859-1",
        "application/json, text/plain",
    ):
        assert_guard_error(
            {"content_type": invalid_content_type},
            None,
            "unsupported_media_type",
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )
    assert_guard_error(None, "content_type", "unsupported_media_type", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
    assert_guard_error(
        {"content_type": ["application/json", "application/json"]},
        None,
        "unsupported_media_type",
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
    )
    assert guard.validate({**valid_request, "content_type": "application/json; charset=utf-8"})[0] == HTTPStatus.OK

    wrong_csrf = memory_secret_token(lambda size: b"x" * size)
    assert_guard_error({"csrf": wrong_csrf}, None, "request_verification_failed", HTTPStatus.FORBIDDEN)
    assert_guard_error(None, "csrf", "request_verification_failed", HTTPStatus.FORBIDDEN)
    assert_guard_error(None, "cookie", "request_verification_failed", HTTPStatus.FORBIDDEN)
    assert_guard_error(
        {"cookie": f'{MEMORY_SESSION_COOKIE_NAME}={first_session["session_id"]}', "csrf": second_session["csrf_token"]},
        None,
        "request_verification_failed",
        HTTPStatus.FORBIDDEN,
    )
    assert_guard_error(
        {
            "cookie": (
                f'{MEMORY_SESSION_COOKIE_NAME}={first_session["session_id"]}; '
                f'{MEMORY_SESSION_COOKIE_NAME}={second_session["session_id"]}'
            )
        },
        None,
        "request_verification_failed",
        HTTPStatus.FORBIDDEN,
    )
    valid_guard_status, valid_guard = guard.validate(valid_request)
    assert valid_guard_status == HTTPStatus.OK
    assert valid_guard == {"ok": True, "guarded": True, "session_id": first_session["session_id"]}

    expiring_clock = FakeClock()
    expiring_sessions = SessionRegistry(clock=expiring_clock, token_generator=DeterministicBytes())
    expiring_session_status, expiring_session = expiring_sessions.issue()
    assert expiring_session_status == HTTPStatus.OK
    expiring_guard = LocalRequestGuard(DEFAULT_HOST, DEFAULT_PORT, expiring_sessions)
    expiring_request = {
        **valid_request,
        "cookie": f'{MEMORY_SESSION_COOKIE_NAME}={expiring_session["session_id"]}',
        "csrf": expiring_session["csrf_token"],
    }
    expiring_clock.advance(MEMORY_SESSION_IDLE_TTL_SECONDS)
    expired_session_status, expired_session = expiring_guard.validate(expiring_request)
    assert expired_session_status == HTTPStatus.FORBIDDEN
    assert expired_session == {"ok": False, "error": "request_verification_failed"}
    assert expiring_sessions.active_count() == 0

    capacity_sessions = SessionRegistry(max_entries=1, clock=FakeClock(), token_generator=DeterministicBytes())
    assert capacity_sessions.issue()[0] == HTTPStatus.OK
    capacity_session_status, capacity_session = capacity_sessions.issue()
    assert capacity_session_status == HTTPStatus.SERVICE_UNAVAILABLE
    assert capacity_session == {"ok": False, "error": "session_capacity_reached"}
    restarted_sessions = SessionRegistry(clock=FakeClock(), token_generator=DeterministicBytes("restart-session"))
    assert restarted_sessions.verify(first_session["session_id"], first_session["csrf_token"]) == (
        HTTPStatus.FORBIDDEN,
        {"ok": False, "error": "request_verification_failed"},
    )

    canonical_status, canonical = canonicalize_memory_candidate_snapshot(candidate)
    assert canonical_status == HTTPStatus.OK
    changed_status, changed = canonicalize_memory_candidate_snapshot(candidate_variant(candidate, "x"))
    assert changed_status == HTTPStatus.OK
    assert canonical["candidate_digest"] != changed["candidate_digest"]
    assert canonical["candidate_digest"] == hashlib.sha256(
        MEMORY_PREVIEW_DIGEST_PREFIX + canonical["canonical_bytes"]
    ).hexdigest()
    assert canonical["canonical_bytes"] == json.dumps(
        canonical["canonical_snapshot"],
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    assert set(canonical["canonical_snapshot"]) == set(MEMORY_CANONICAL_PREVIEW_FIELDS)
    assert not (set(MEMORY_SAVE_DRY_RUN_DISALLOWED_RAW_FIELDS) & set(canonical["canonical_snapshot"]))
    assert not (set(MEMORY_SAVE_DRY_RUN_DISALLOWED_PATH_FIELDS) & set(canonical["canonical_snapshot"]))
    candidate_with_ignored_ui_field = dict(candidate)
    candidate_with_ignored_ui_field["ui_only_note"] = "C:\\private\\not-authority"
    ignored_status, ignored = canonicalize_memory_candidate_snapshot(candidate_with_ignored_ui_field)
    assert ignored_status == HTTPStatus.OK
    assert ignored["candidate_digest"] == canonical["candidate_digest"]
    assert "ui_only_note" not in ignored["canonical_snapshot"]
    for forbidden_field, expected_error in (
        ("raw_transcript", "raw_transcript_not_allowed"),
        ("storage_path", "path_field_not_allowed"),
    ):
        unsafe_candidate = dict(candidate)
        unsafe_candidate[forbidden_field] = "C:\\private\\sensitive"
        unsafe_status, unsafe_result = canonicalize_memory_candidate_snapshot(unsafe_candidate)
        assert unsafe_status == HTTPStatus.BAD_REQUEST
        assert unsafe_result == {"ok": False, "error": expected_error}
        assert "sensitive" not in str(unsafe_result)

    token_clock = FakeClock()
    token_registry = PreviewTokenRegistry(clock=token_clock, token_generator=DeterministicBytes("tokens"))
    missing_privacy_status, missing_privacy = token_registry.issue(first_session["session_id"], candidate)
    assert missing_privacy_status == HTTPStatus.BAD_REQUEST
    assert missing_privacy == {"ok": False, "error": "privacy_review_required"}
    false_privacy_status, false_privacy = token_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=False,
    )
    assert false_privacy_status == HTTPStatus.BAD_REQUEST
    assert false_privacy == {"ok": False, "error": "privacy_review_required"}
    assert token_registry.active_count() == 0
    issue_status, issued = token_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )
    assert issue_status == HTTPStatus.OK
    assert memory_secret_token_is_valid(issued["preview_token"])
    assert issued["candidate_digest"] == canonical["candidate_digest"]
    assert issued["expires_in_seconds"] == MEMORY_PREVIEW_TOKEN_TTL_SECONDS
    assert token_registry.active_count() == 1
    assert issued["preview_token"] not in repr(token_registry._entries)
    entry_key, entry = next(iter(token_registry._entries.items()))
    assert entry_key == memory_secret_token_digest(issued["preview_token"])
    assert entry["token_digest"] == entry_key
    assert set(entry) == {
        "token_digest",
        "session_id",
        "candidate_digest",
        "canonical_snapshot",
        "issued_at_monotonic",
        "expires_at_monotonic",
    }
    duplicate_status, duplicate = token_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )
    assert duplicate_status == HTTPStatus.CONFLICT
    assert duplicate == {"ok": False, "error": "preview_token_already_active"}
    assert token_registry.active_count() == 1
    wrong_session_status, wrong_session = token_registry.claim(
        second_session["session_id"],
        issued["preview_token"],
    )
    assert wrong_session_status == HTTPStatus.CONFLICT
    assert wrong_session == {"ok": False, "error": "invalid_or_expired_preview_token"}
    assert token_registry.active_count() == 1
    claim_status, claimed = token_registry.claim(first_session["session_id"], issued["preview_token"])
    assert claim_status == HTTPStatus.OK
    assert claimed["candidate_digest"] == canonical["candidate_digest"]
    assert claimed["canonical_snapshot"] == canonical["canonical_snapshot"]
    assert token_registry.active_count() == 0
    second_claim_status, second_claim = token_registry.claim(
        first_session["session_id"],
        issued["preview_token"],
    )
    assert second_claim_status == HTTPStatus.CONFLICT
    assert second_claim == {"ok": False, "error": "invalid_or_expired_preview_token"}
    for secret_text in (
        issued["preview_token"],
        first_session["session_id"],
        candidate["cleaned_text"],
        "C:\\private",
    ):
        assert secret_text not in str(second_claim)

    before_expiry_clock = FakeClock()
    before_expiry_registry = PreviewTokenRegistry(
        clock=before_expiry_clock,
        token_generator=DeterministicBytes(),
    )
    before_expiry_status, before_expiry_token = before_expiry_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )
    assert before_expiry_status == HTTPStatus.OK
    before_expiry_clock.advance(MEMORY_PREVIEW_TOKEN_TTL_SECONDS - 0.001)
    assert before_expiry_registry.claim(first_session["session_id"], before_expiry_token["preview_token"])[0] == HTTPStatus.OK

    boundary_clock = FakeClock()
    boundary_registry = PreviewTokenRegistry(clock=boundary_clock, token_generator=DeterministicBytes())
    boundary_status, boundary_token = boundary_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )
    assert boundary_status == HTTPStatus.OK
    boundary_clock.advance(MEMORY_PREVIEW_TOKEN_TTL_SECONDS)
    expired_token_status, expired_token = boundary_registry.claim(
        first_session["session_id"],
        boundary_token["preview_token"],
    )
    assert expired_token_status == HTTPStatus.CONFLICT
    assert expired_token == {"ok": False, "error": "invalid_or_expired_preview_token"}
    assert boundary_registry.active_count() == 0

    cleanup_clock = FakeClock()
    cleanup_registry = PreviewTokenRegistry(
        max_entries=1,
        per_session_limit=1,
        ttl_seconds=MEMORY_PREVIEW_TOKEN_TTL_SECONDS,
        clock=cleanup_clock,
        token_generator=DeterministicBytes("issue-cleanup"),
    )
    assert cleanup_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )[0] == HTTPStatus.OK
    cleanup_clock.advance(MEMORY_PREVIEW_TOKEN_TTL_SECONDS)
    assert cleanup_registry.issue(
        first_session["session_id"],
        candidate_variant(candidate, "after-expiry-cleanup"),
        privacy_reviewed=True,
    )[0] == HTTPStatus.OK
    assert cleanup_registry.active_count() == 1

    per_session_registry = PreviewTokenRegistry(
        max_entries=2,
        per_session_limit=1,
        clock=FakeClock(),
        token_generator=DeterministicBytes(),
    )
    assert per_session_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )[0] == HTTPStatus.OK
    per_session_status, per_session_error = per_session_registry.issue(
        first_session["session_id"],
        candidate_variant(candidate, "per-session"),
        privacy_reviewed=True,
    )
    assert per_session_status == HTTPStatus.SERVICE_UNAVAILABLE
    assert per_session_error == {"ok": False, "error": "preview_token_capacity_reached"}

    third_session_status, third_session = sessions.issue()
    assert third_session_status == HTTPStatus.OK
    global_registry = PreviewTokenRegistry(
        max_entries=2,
        per_session_limit=2,
        clock=FakeClock(),
        token_generator=DeterministicBytes(),
    )
    assert global_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )[0] == HTTPStatus.OK
    assert global_registry.issue(
        second_session["session_id"],
        candidate_variant(candidate, "global-2"),
        privacy_reviewed=True,
    )[0] == HTTPStatus.OK
    global_status, global_error = global_registry.issue(
        third_session["session_id"],
        candidate_variant(candidate, "global-3"),
        privacy_reviewed=True,
    )
    assert global_status == HTTPStatus.SERVICE_UNAVAILABLE
    assert global_error == {"ok": False, "error": "preview_token_capacity_reached"}
    assert global_registry.active_count() == 2

    original_registry = PreviewTokenRegistry(clock=FakeClock(), token_generator=DeterministicBytes())
    restart_issue_status, restart_issue = original_registry.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )
    assert restart_issue_status == HTTPStatus.OK
    restarted_registry = PreviewTokenRegistry(clock=FakeClock(), token_generator=DeterministicBytes())
    restart_claim_status, restart_claim = restarted_registry.claim(
        first_session["session_id"],
        restart_issue["preview_token"],
    )
    assert restart_claim_status == HTTPStatus.CONFLICT
    assert restart_claim == {"ok": False, "error": "invalid_or_expired_preview_token"}

    live_registry = PreviewTokenRegistry(clock=FakeClock(), token_generator=DeterministicBytes())
    live_count_before = live_registry.active_count()
    live_preview_status, live_preview = handle_post_api(
        MEMORY_PREVIEW_ENDPOINT,
        {"cleaned_text": "Live preview stays write-free and token-free."},
    )
    assert live_preview_status == HTTPStatus.OK
    assert "preview_token" not in live_preview
    assert "candidate_digest" not in live_preview
    assert live_registry.active_count() == live_count_before == 0
    assert handle_post_api(MEMORY_SAVE_ENDPOINT, {}) == (
        HTTPStatus.NOT_FOUND,
        {"ok": False, "error": "not_found"},
    )
    assert "LocalRequestGuard" not in inspect.getsource(JarvisConsoleHandler)
    assert "PreviewTokenRegistry" not in inspect.getsource(handle_post_api)
    assert "preview_token" not in str(prepare_voice_inbox_task({"transcript": "이 반복 작업을 기억해줘"}))
    assert not (APP_ROOT / "state").exists()
    assert not (REPO_ROOT / ".jarvis-local").exists()
    assert not (REPO_ROOT / "memory" / "skills").exists()
    after_status = run_read_only_git(("status", "--short"))
    assert before_status == after_status


def run_memory_http_metadata_adapter_self_tests() -> None:
    """Exercise duplicate-preserving raw metadata adaptation without HTTP routes."""

    class DeterministicBytes:
        def __init__(self) -> None:
            self.counter = 0

        def __call__(self, size: int) -> bytes:
            self.counter += 1
            seed = hashlib.sha256(f"jarvis-http-metadata-{self.counter}".encode("ascii")).digest()
            return (seed * ((size + len(seed) - 1) // len(seed)))[:size]

    before_status = run_read_only_git(("status", "--short"))
    sessions = SessionRegistry(clock=lambda: 100.0, token_generator=DeterministicBytes())
    session_status, session = sessions.issue()
    assert session_status == HTTPStatus.OK
    raw_headers = [
        ("hOsT", f"{DEFAULT_HOST}:{DEFAULT_PORT}"),
        ("Origin", f"http://{DEFAULT_HOST}:{DEFAULT_PORT}"),
        ("CONTENT-TYPE", "application/json; charset=utf-8"),
        ("Cookie", f'{MEMORY_SESSION_COOKIE_NAME}={session["session_id"]}'),
        (MEMORY_CSRF_HEADER_NAME, session["csrf_token"]),
        ("Content-Length", "123"),
        ("User-Agent", "Jarvis-Metadata-Self-Test"),
    ]

    valid_status, valid = adapt_memory_guarded_http_metadata(iter(raw_headers))
    assert valid_status == HTTPStatus.OK
    assert valid["ok"] is True
    assert valid["content_length"] == 123
    assert valid["header_count"] == len(raw_headers)
    assert valid["request_metadata"] == {
        "host": f"{DEFAULT_HOST}:{DEFAULT_PORT}",
        "origin": f"http://{DEFAULT_HOST}:{DEFAULT_PORT}",
        "content_type": "application/json; charset=utf-8",
        "cookie": f'{MEMORY_SESSION_COOKIE_NAME}={session["session_id"]}',
        "csrf": session["csrf_token"],
    }
    guard = LocalRequestGuard(DEFAULT_HOST, DEFAULT_PORT, sessions)
    assert guard.validate(valid["request_metadata"])[0] == HTTPStatus.OK

    def assert_adapter_error(
        headers: Any,
        expected_status: HTTPStatus,
        expected_error: str,
        **kwargs: Any,
    ) -> None:
        status, result = adapt_memory_guarded_http_metadata(headers, **kwargs)
        assert status == expected_status
        assert result == {"ok": False, "error": expected_error}
        rendered = str(result)
        assert session["session_id"] not in rendered
        assert session["csrf_token"] not in rendered

    security_header_names = tuple(MEMORY_HTTP_METADATA_REQUIRED_HEADERS)
    for security_header_name in security_header_names:
        matching = [item for item in raw_headers if item[0].lower() == security_header_name]
        assert len(matching) == 1
        assert_adapter_error(
            [*raw_headers, matching[0]],
            HTTPStatus.BAD_REQUEST,
            "invalid_request_metadata",
        )
        assert_adapter_error(
            [item for item in raw_headers if item[0].lower() != security_header_name],
            HTTPStatus.BAD_REQUEST,
            "invalid_request_metadata",
        )

    assert_adapter_error(dict(raw_headers), HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error("Host: value", HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error(None, HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error([*raw_headers, ("broken",)], HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error([*raw_headers, (123, "value")], HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error([*raw_headers, ("Bad Header", "value")], HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error([*raw_headers, ("X-Test", " leading")], HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error([*raw_headers, ("X-Test", "trailing ")], HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error([*raw_headers, ("X-Test", "line\r\nbreak")], HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error([*raw_headers, ("X-Test", "nul\x00value")], HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error([*raw_headers, ("X-Test", "한글")], HTTPStatus.BAD_REQUEST, "invalid_request_metadata")
    assert_adapter_error(
        [*raw_headers, ("X-Test", "x" * (MEMORY_HTTP_METADATA_MAX_HEADER_VALUE_CHARS + 1))],
        HTTPStatus.BAD_REQUEST,
        "invalid_request_metadata",
    )
    assert_adapter_error(
        [*raw_headers, ("X" * (MEMORY_HTTP_METADATA_MAX_HEADER_NAME_CHARS + 1), "value")],
        HTTPStatus.BAD_REQUEST,
        "invalid_request_metadata",
    )
    assert_adapter_error(
        [*raw_headers, ("Transfer-Encoding", "chunked")],
        HTTPStatus.BAD_REQUEST,
        "transfer_encoding_not_allowed",
    )

    def with_content_length(value: str) -> list[tuple[str, str]]:
        return [
            (name, value if name.lower() == "content-length" else header_value)
            for name, header_value in raw_headers
        ]

    for invalid_length in ("", "-1", "+1", "01", "1.0", "1,1"):
        assert_adapter_error(
            with_content_length(invalid_length),
            HTTPStatus.BAD_REQUEST,
            "invalid_content_length",
        )
    assert_adapter_error(
        with_content_length(str(MAX_JSON_BODY_BYTES + 1)),
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        "request_too_large",
    )
    assert adapt_memory_guarded_http_metadata(with_content_length("0"))[1]["content_length"] == 0
    assert adapt_memory_guarded_http_metadata(
        with_content_length(str(MAX_JSON_BODY_BYTES))
    )[1]["content_length"] == MAX_JSON_BODY_BYTES

    too_many_headers = [
        *raw_headers,
        *[(f"X-Bounded-{index}", "value") for index in range(MEMORY_HTTP_METADATA_MAX_HEADER_COUNT)],
    ]
    assert_adapter_error(
        too_many_headers,
        HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE,
        "request_headers_too_large",
    )
    assert_adapter_error(raw_headers, HTTPStatus.BAD_REQUEST, "invalid_request_metadata", max_header_count=0)
    assert_adapter_error(raw_headers, HTTPStatus.BAD_REQUEST, "invalid_request_metadata", max_body_bytes=-1)
    assert_adapter_error(
        with_content_length("1"),
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        "request_too_large",
        max_body_bytes=0,
    )

    assert "adapt_memory_guarded_http_metadata" not in inspect.getsource(handle_post_api)
    assert "adapt_memory_guarded_http_metadata" not in inspect.getsource(JarvisConsoleHandler)
    assert handle_post_api(MEMORY_SAVE_ENDPOINT, {}) == (
        HTTPStatus.NOT_FOUND,
        {"ok": False, "error": "not_found"},
    )
    assert not (APP_ROOT / "state").exists()
    assert not (REPO_ROOT / ".jarvis-local").exists()
    assert not (REPO_ROOT / "memory" / "skills").exists()
    after_status = run_read_only_git(("status", "--short"))
    assert before_status == after_status


def run_memory_guarded_save_coordinator_self_tests() -> None:
    """Verify the route-free one-claim coordinator only against temporary local state."""

    class DeterministicBytes:
        def __init__(self, namespace: str) -> None:
            self.namespace = namespace
            self.counter = 0

        def __call__(self, size: int) -> bytes:
            self.counter += 1
            seed = hashlib.sha256(
                f"jarvis-guarded-save-{self.namespace}-{self.counter}".encode("ascii")
            ).digest()
            return (seed * ((size + len(seed) - 1) // len(seed)))[:size]

    def session_metadata(session: dict[str, Any]) -> dict[str, str]:
        return {
            "host": f"{DEFAULT_HOST}:{DEFAULT_PORT}",
            "origin": f"http://{DEFAULT_HOST}:{DEFAULT_PORT}",
            "content_type": "application/json",
            "cookie": f'{MEMORY_SESSION_COOKIE_NAME}={session["session_id"]}',
            "csrf": session["csrf_token"],
        }

    def final_payload(token: str) -> dict[str, str]:
        return {
            "preview_token": token,
            "confirmation": MEMORY_GUARDED_SAVE_CONFIRMATION,
        }

    def candidate_variant(candidate: dict[str, Any], marker: str) -> dict[str, Any]:
        variant = dict(candidate)
        variant["cleaned_text"] = f'{candidate["cleaned_text"]} {marker}'
        variant["tags"] = list(candidate.get("tags", []))
        variant["safety_notes"] = list(candidate.get("safety_notes", []))
        return variant

    before_status = run_read_only_git(("status", "--short"))
    preview_status, preview = prepare_memory_candidate_preview(
        {
            "title": "Guarded save coordinator candidate",
            "cleaned_text": "Persist only the reviewed normalized candidate.",
            "original_text_preview": "Private source preview must not be stored.",
            "candidate_type": "operating_rule",
            "confidence": "medium",
            "source": "manual",
            "tags": ["guarded", "coordinator"],
            "safety_notes": ["Internal tests only; no live route."],
        }
    )
    assert preview_status == HTTPStatus.OK
    candidate = preview["candidate_preview"]

    sessions = SessionRegistry(clock=lambda: 100.0, token_generator=DeterministicBytes("sessions"))
    first_status, first_session = sessions.issue()
    second_status, second_session = sessions.issue()
    assert first_status == second_status == HTTPStatus.OK
    guard = LocalRequestGuard(DEFAULT_HOST, DEFAULT_PORT, sessions)
    first_metadata = session_metadata(first_session)
    second_metadata = session_metadata(second_session)

    tokens = PreviewTokenRegistry(clock=lambda: 200.0, token_generator=DeterministicBytes("tokens"))
    issue_status, issued = tokens.issue(
        first_session["session_id"],
        candidate,
        privacy_reviewed=True,
    )
    assert issue_status == HTTPStatus.OK
    token = issued["preview_token"]

    wrong_origin_status, wrong_origin = coordinate_guarded_memory_skills_save(
        guard,
        tokens,
        {**first_metadata, "origin": "https://evil.example"},
        final_payload(token),
    )
    assert wrong_origin_status == HTTPStatus.FORBIDDEN
    assert wrong_origin["error"] == "request_verification_failed"
    assert tokens.active_count() == 1

    invalid_body_status, invalid_body = coordinate_guarded_memory_skills_save(
        guard,
        tokens,
        first_metadata,
        {**final_payload(token), "candidate_preview": candidate},
    )
    assert invalid_body_status == HTTPStatus.BAD_REQUEST
    assert invalid_body["error"] == "invalid_save_request"
    assert tokens.active_count() == 1

    missing_confirmation_status, missing_confirmation = coordinate_guarded_memory_skills_save(
        guard,
        tokens,
        first_metadata,
        {"preview_token": token, "confirmation": True},
    )
    assert missing_confirmation_status == HTTPStatus.BAD_REQUEST
    assert missing_confirmation["error"] == "explicit_confirmation_required"
    assert tokens.active_count() == 1

    with TemporaryDirectory(prefix="jarvis-guarded-save-success-") as success_root_text:
        success_root = Path(success_root_text)
        save_status, saved = coordinate_guarded_memory_skills_save(
            guard,
            tokens,
            first_metadata,
            final_payload(token),
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(success_root)},
            id_generator=lambda: "mem_c0a400000001",
            clock=lambda: "2026-07-22T00:00:00Z",
        )
        assert save_status == HTTPStatus.OK
        assert saved["saved"] is True
        assert saved["candidate_id"] == "mem_c0a400000001"
        assert saved["original_text_preview_stored"] is False
        assert saved["skill_created"] is False
        assert saved["registry_modified"] is False
        assert saved["will_run_automatically"] is False
        assert "preview_token" not in saved
        assert "candidate_digest" not in saved
        assert "candidate_file" not in saved
        assert candidate["cleaned_text"] not in str(saved)
        assert candidate["original_text_preview"] not in str(saved)
        candidate_file = success_root / "memory-skills" / "candidates" / "mem_c0a400000001.json"
        stored = json.loads(candidate_file.read_text(encoding="utf-8"))
        assert stored["cleaned_text"] == candidate["cleaned_text"]
        assert "original_text_preview" not in stored
        assert "original_text" not in stored
        assert "raw_transcript" not in stored
        assert tokens.active_count() == 0

        replay_status, replay = coordinate_guarded_memory_skills_save(
            guard,
            tokens,
            first_metadata,
            final_payload(token),
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(success_root)},
            id_generator=lambda: "mem_c0a400000002",
            clock=lambda: "2026-07-22T00:00:01Z",
        )
        assert replay_status == HTTPStatus.CONFLICT
        assert replay["error"] == "invalid_or_expired_preview_token"
        assert len(list(candidate_file.parent.glob("*.json"))) == 1

    cross_session_tokens = PreviewTokenRegistry(
        clock=lambda: 300.0,
        token_generator=DeterministicBytes("cross-session"),
    )
    cross_status, cross_issued = cross_session_tokens.issue(
        first_session["session_id"],
        candidate_variant(candidate, "cross-session"),
        privacy_reviewed=True,
    )
    assert cross_status == HTTPStatus.OK
    cross_token = cross_issued["preview_token"]
    wrong_session_status, wrong_session = coordinate_guarded_memory_skills_save(
        guard,
        cross_session_tokens,
        second_metadata,
        final_payload(cross_token),
    )
    assert wrong_session_status == HTTPStatus.CONFLICT
    assert wrong_session["error"] == "invalid_or_expired_preview_token"
    assert cross_session_tokens.active_count() == 1

    with TemporaryDirectory(prefix="jarvis-guarded-save-cross-session-") as cross_root_text:
        cross_root = Path(cross_root_text)
        correct_session_status, correct_session = coordinate_guarded_memory_skills_save(
            guard,
            cross_session_tokens,
            first_metadata,
            final_payload(cross_token),
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(cross_root)},
            id_generator=lambda: "mem_c0a400000003",
            clock=lambda: "2026-07-22T00:00:02Z",
        )
        assert correct_session_status == HTTPStatus.OK
        assert correct_session["saved"] is True
        assert cross_session_tokens.active_count() == 0

    failure_tokens = PreviewTokenRegistry(
        clock=lambda: 400.0,
        token_generator=DeterministicBytes("failure"),
    )
    failure_issue_status, failure_issued = failure_tokens.issue(
        first_session["session_id"],
        candidate_variant(candidate, "writer-failure"),
        privacy_reviewed=True,
    )
    assert failure_issue_status == HTTPStatus.OK
    failure_token = failure_issued["preview_token"]
    with TemporaryDirectory(prefix="jarvis-guarded-save-failure-") as failure_root_text:
        failure_root = Path(failure_root_text)
        (failure_root / "memory-skills").write_text("blocking file", encoding="utf-8")
        failure_status, failure = coordinate_guarded_memory_skills_save(
            guard,
            failure_tokens,
            first_metadata,
            final_payload(failure_token),
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(failure_root)},
            id_generator=lambda: "mem_c0a400000004",
            clock=lambda: "2026-07-22T00:00:03Z",
        )
        assert failure_status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert failure["error"] == "candidate_write_failed"
        assert "candidate_file" not in failure
        assert str(failure_root) not in str(failure)
        assert failure_tokens.active_count() == 0

    with TemporaryDirectory(prefix="jarvis-guarded-save-dead-token-") as retry_root_text:
        retry_root = Path(retry_root_text)
        retry_status, retry = coordinate_guarded_memory_skills_save(
            guard,
            failure_tokens,
            first_metadata,
            final_payload(failure_token),
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(retry_root)},
            id_generator=lambda: "mem_c0a400000005",
            clock=lambda: "2026-07-22T00:00:04Z",
        )
        assert retry_status == HTTPStatus.CONFLICT
        assert retry["error"] == "invalid_or_expired_preview_token"
        assert not (retry_root / "memory-skills").exists()

    corrupt_tokens = PreviewTokenRegistry(
        clock=lambda: 500.0,
        token_generator=DeterministicBytes("corrupt"),
    )
    corrupt_issue_status, corrupt_issued = corrupt_tokens.issue(
        first_session["session_id"],
        candidate_variant(candidate, "corrupt-digest"),
        privacy_reviewed=True,
    )
    assert corrupt_issue_status == HTTPStatus.OK
    next(iter(corrupt_tokens._entries.values()))["candidate_digest"] = "0" * 64
    with TemporaryDirectory(prefix="jarvis-guarded-save-corrupt-") as corrupt_root_text:
        corrupt_root = Path(corrupt_root_text)
        corrupt_status, corrupt = coordinate_guarded_memory_skills_save(
            guard,
            corrupt_tokens,
            first_metadata,
            final_payload(corrupt_issued["preview_token"]),
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(corrupt_root)},
            id_generator=lambda: "mem_c0a400000006",
            clock=lambda: "2026-07-22T00:00:05Z",
        )
        assert corrupt_status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert corrupt["error"] == "candidate_save_failed"
        assert corrupt_tokens.active_count() == 0
        assert not (corrupt_root / "memory-skills").exists()

    assert handle_post_api(MEMORY_SAVE_ENDPOINT, {}) == (
        HTTPStatus.NOT_FOUND,
        {"ok": False, "error": "not_found"},
    )
    assert "coordinate_guarded_memory_skills_save" not in inspect.getsource(handle_post_api)
    assert "coordinate_guarded_memory_skills_save" not in inspect.getsource(JarvisConsoleHandler)
    assert "preview_token" not in str(prepare_voice_inbox_task({"transcript": "이 반복 작업을 기억해줘"}))
    assert not (APP_ROOT / "state").exists()
    assert not (REPO_ROOT / ".jarvis-local").exists()
    assert not (REPO_ROOT / "memory" / "skills").exists()
    after_status = run_read_only_git(("status", "--short"))
    assert before_status == after_status


def run_self_test() -> None:
    """Run deterministic helper checks without starting a long-lived server."""

    assert DEFAULT_HOST == "127.0.0.1", "server must bind to 127.0.0.1"
    assert DEFAULT_PORT == 8790, "default port must be 8790"

    registry = load_registry()
    assert registry["read_only"] is True
    assert "jarvis.bat" in registry["protected_paths"]
    assert len(registry["skills"]) == 6
    assert len({skill["skill_id"] for skill in registry["skills"]}) == 6
    for skill in registry["skills"]:
        assert REQUIRED_SKILL_FIELDS.issubset(skill)
        assert skill["status"] in ALLOWED_STATUSES
        assert skill["category"] in ALLOWED_CATEGORIES
        assert skill["when_to_use"]
        assert skill["primary_next_action_label"]
        assert skill["primary_next_action_description"]
        assert isinstance(skill["action_guide"], list) and skill["action_guide"]
        assert isinstance(skill["route_keywords"], list) and skill["route_keywords"]
        assert set(skill["commands"]).issuperset(REQUIRED_COMMAND_FIELDS)
        for command in skill["commands"].values():
            validate_display_command(skill["skill_id"], "self-test", command)
        for test_command in skill["tests"]:
            validate_display_command(skill["skill_id"], "self-test", test_command)
        if skill["status"] == "available":
            assert skill["docs"] or skill["tests"] or skill["safe_next_action"]
        if skill["local_url"]:
            assert skill["local_url"].startswith("http://127.0.0.1")

    bad_commands = (
        "git" + " add .",
        "git" + " commit -m test",
        "git" + " push",
        "git" + " checkout main",
        "git" + " reset --hard",
        "git" + " clean -fd",
        "git" + " rm file",
        "git" + " stash",
        "cu" + "rl https://example.com",
        "w" + "get https://example.com",
        "powershell Invoke-" + "WebRequest https://example.com",
        "powershell Invoke-" + "RestMethod https://example.com",
        "Start-" + "BitsTransfer https://example.com",
        "bits" + "admin https://example.com",
    )
    for command in bad_commands:
        try:
            validate_display_command("bad_skill", "self-test", command)
        except RegistryError:
            pass
        else:
            raise AssertionError(f"dangerous command was not rejected: {command}")

    bad_paths = (
        "",
        "https://example.com/doc",
        "http://example.com/doc",
        "C:/work/file.md",
        "/absolute/file.md",
        "../outside.md",
        "apps\\jarvis-console\\README.md",
        "~/secret.md",
    )
    for path_value in bad_paths:
        try:
            validate_registry_path("bad_skill", "docs", path_value)
        except RegistryError:
            pass
        else:
            raise AssertionError(f"unsafe registry path was not rejected: {path_value}")

    for args in READ_ONLY_GIT_COMMANDS:
        validate_read_only_git_args(args)
    bad_git_args = (
        ("add", "."),
        ("commit", "-m", "test"),
        ("push",),
        ("checkout", "main"),
        ("reset", "--hard"),
        ("clean", "-fd"),
        ("rm", "file"),
        ("stash",),
        ("tag", "v0.1"),
        ("merge", "main"),
        ("rebase", "main"),
    )
    for args in bad_git_args:
        try:
            validate_read_only_git_args(args)
        except RegistryError:
            pass
        else:
            raise AssertionError(f"unsafe git args were not rejected: {args}")

    assert is_overview_candidate_path(REPO_ROOT / "docs" / "sample.md") is True
    assert is_overview_candidate_path(REPO_ROOT / "docs" / "sample.json") is True
    assert is_overview_candidate_path(REPO_ROOT / "docs" / "sample.txt") is True
    assert is_overview_candidate_path(REPO_ROOT / "docs" / "sample.py") is False
    assert is_overview_candidate_path(REPO_ROOT / ".git" / "config.txt") is False
    assert is_overview_candidate_path(REPO_ROOT / "docs" / "__pycache__" / "sample.md") is False
    assert is_overview_candidate_path(REPO_ROOT / "docs" / ".hidden.md") is False
    assert is_overview_candidate_path(REPO_ROOT / "docs" / "secret-plan.md") is False
    assert is_overview_candidate_path(REPO_ROOT.parent / "outside.md") is False
    assert is_overview_candidate_path(REPO_ROOT / "docs" / "sample.md", REPO_ROOT / "reports") is False

    assert suggest_skill("idea MVP validation")["recommended_skill"] == "research_council"
    assert suggest_skill("Codex commit review")["recommended_skill"] == "hermes_manager"
    assert suggest_skill("MCP Agent Skills new technology")["recommended_skill"] == "daily_ai_radar"
    assert suggest_skill("remember this repeated workflow as a skill")["recommended_skill"] == "memory_skills"
    assert suggest_skill("make this better somehow")["recommended_skill"] == "unknown"
    assert suggest_skill("\uc544\uc774\ub514\uc5b4 MVP \uac80\uc99d")["recommended_skill"] == "research_council"
    assert suggest_skill("\uc81c\uc870\uc7a5\ube44 \uc2dc\ubbac\ub808\uc774\uc158 \uc544\uc774\ub514\uc5b4 \uac80\uc99d\ud574\uc918")["recommended_skill"] == "research_council"
    assert suggest_skill("\ucc3d\uc5c5 \uc544\uc774\ub514\uc5b4 \uc0ac\uc5c5\uc131 \uac80\ud1a0\ud574\uc918")["recommended_skill"] == "research_council"
    assert suggest_skill("\uc2dc\ubbac\ub808\uc774\uc158 \uac8c\uc784 \ucd94\ucc9c\ud574\uc918")["recommended_skill"] == "unknown"
    assert suggest_skill("\uacc4\uc57d\uc11c \uac80\ud1a0 \uc571 \ucf54\ub4dc \uc218\uc815\ud574\uc918")["recommended_skill"] != "research_council"
    assert suggest_skill("Codex \ucee4\ubc0b \ub9ac\ubdf0")["recommended_skill"] == "hermes_manager"
    assert suggest_skill("MCP Agent Skills \uc0c8 \uae30\uc220")["recommended_skill"] == "daily_ai_radar"
    assert suggest_skill("\ubc18\ubcf5 \uc791\uc5c5 skill\ub85c \uae30\uc5b5")["recommended_skill"] == "memory_skills"

    assert clean_voice_transcript("코덱스 케어노트 헤르메스") == "Codex CareNote Hermes"
    assert clean_voice_transcript("엠씨피 에이전트 스킬 데일리 레이더") == "MCP Agent Skills Daily AI Radar"
    assert clean_voice_transcript("고깃집 리뷰 정리해줘") == "고깃집 리뷰 정리해줘"
    assert clean_voice_transcript("영화 리뷰 정리해줘") == "영화 리뷰 정리해줘"
    assert clean_voice_transcript("영화 리뷰 수정해줘") == "영화 리뷰 수정해줘"
    assert clean_voice_transcript("프리뷰 화면 확인") == "프리뷰 화면 확인"
    voice_empty_code, voice_empty = handle_post_api("/api/voice-inbox/prepare", {"transcript": ""})
    assert voice_empty_code == HTTPStatus.BAD_REQUEST
    assert voice_empty["error"] == "empty_transcript"
    voice_missing_code, voice_missing = handle_post_api("/api/voice-inbox/prepare", {})
    assert voice_missing_code == HTTPStatus.BAD_REQUEST
    assert voice_missing["error"] == "missing_transcript"
    voice_type_code, voice_type = handle_post_api("/api/voice-inbox/prepare", {"transcript": 123})
    assert voice_type_code == HTTPStatus.BAD_REQUEST
    assert voice_type["error"] == "transcript_must_be_string"
    voice_long_code, voice_long = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "a" * (VOICE_INBOX_MAX_TRANSCRIPT_CHARS + 1)},
    )
    assert voice_long_code == HTTPStatus.BAD_REQUEST
    assert voice_long["error"] == "transcript_too_long"
    voice_research_code, voice_research = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "Jarvis, CareNote 복약 기록 UX 리스크를 Research Council로 검증해줘"},
    )
    assert voice_research_code == HTTPStatus.OK
    assert voice_research["task_candidate"]["suggested_skill"] == "research_council"
    assert voice_research["task_candidate"]["confidence"] == "high"
    assert voice_research["task_candidate"]["needs_confirmation"] is True
    assert "CareNote" in voice_research["cleaned_transcript"]
    assert "Research Council" in voice_research["cleaned_transcript"]
    voice_hermes_code, voice_hermes = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "코덱스한테 README 수정하고 커밋 리뷰 프롬프트 만들어줘"},
    )
    assert voice_hermes_code == HTTPStatus.OK
    assert voice_hermes["task_candidate"]["suggested_skill"] == "hermes_manager"
    assert "Codex" in voice_hermes["cleaned_transcript"]
    assert "commit" in voice_hermes["cleaned_transcript"]
    assert "review" in voice_hermes["cleaned_transcript"]
    voice_radar_code, voice_radar = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "MCP Agent Skills 새 기술 Daily Radar로 확인해줘"},
    )
    assert voice_radar_code == HTTPStatus.OK
    assert voice_radar["task_candidate"]["suggested_skill"] == "daily_ai_radar"
    assert "Daily AI Radar" in voice_radar["cleaned_transcript"]
    voice_memory_code, voice_memory = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "이 반복 작업 skill 후보로 기억해줘"},
    )
    assert voice_memory_code == HTTPStatus.OK
    assert voice_memory["task_candidate"]["suggested_skill"] == "memory_skills"
    assert voice_memory["task_candidate"]["needs_confirmation"] is True
    assert "saved" not in voice_memory
    voice_unknown_code, voice_unknown = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "오늘 뭐하지"},
    )
    assert voice_unknown_code == HTTPStatus.OK
    assert voice_unknown["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_unknown["task_candidate"]["confidence"] == "low"
    assert voice_unknown["task_candidate"]["needs_confirmation"] is True
    voice_restaurant_code, voice_restaurant = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "고깃집 리뷰 정리해줘"},
    )
    assert voice_restaurant_code == HTTPStatus.OK
    assert voice_restaurant["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_restaurant["cleaned_transcript"] == "고깃집 리뷰 정리해줘"
    assert "고git" not in voice_restaurant["cleaned_transcript"]
    voice_movie_code, voice_movie = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "영화 리뷰 정리해줘"},
    )
    assert voice_movie_code == HTTPStatus.OK
    assert voice_movie["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_movie["cleaned_transcript"] == "영화 리뷰 정리해줘"
    voice_movie_edit_code, voice_movie_edit = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "영화 리뷰 수정해줘"},
    )
    assert voice_movie_edit_code == HTTPStatus.OK
    assert voice_movie_edit["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_movie_edit["cleaned_transcript"] == "영화 리뷰 수정해줘"
    voice_preview_code, voice_preview = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "프리뷰 화면 확인"},
    )
    assert voice_preview_code == HTTPStatus.OK
    assert voice_preview["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_preview["cleaned_transcript"] == "프리뷰 화면 확인"
    voice_report_review_code, voice_report_review = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "report review draft"},
    )
    assert voice_report_review_code == HTTPStatus.OK
    assert voice_report_review["task_candidate"]["suggested_skill"] == "unknown"
    voice_daily_routine_code, voice_daily_routine = handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "데일리 루틴 정리"},
    )
    assert voice_daily_routine_code == HTTPStatus.OK
    assert voice_daily_routine["task_candidate"]["suggested_skill"] == "unknown"
    assert len(voice_research["task_candidate"]["title"]) <= VOICE_INBOX_TITLE_MAX_CHARS
    assert len(voice_research["task_candidate"]["summary"]) <= VOICE_INBOX_SUMMARY_MAX_CHARS
    assert "This is a task candidate, not an execution." in voice_research["safety_notes"]

    status = status_payload()
    skill_ids = {skill["skill_id"] for skill in status["skills"]}
    assert {"research_council", "daily_ai_radar", "hermes_manager"}.issubset(skill_ids)
    assert len(status["skills"]) == 6
    assert "jarvis.bat" in status["protected_paths"]
    assert all({"docs", "tests", "examples", "action_guide", "when_to_use"}.issubset(skill) for skill in status["skills"])
    hermes_commands = suggest_skill("Codex commit review")["commands"]
    assert "apps/hermes-manager-pilot/run_web_app.py" in hermes_commands["git_bash"]
    assert "apps\\hermes-manager-pilot\\run_web_app.py" in hermes_commands["powershell"]
    skill_code, skill_response = handle_get_api("/api/skill", "skill_id=research_council")
    assert skill_code == HTTPStatus.OK
    assert skill_response["skill"]["skill_id"] == "research_council"
    assert skill_response["skill"]["docs"]
    assert skill_response["skill"]["tests"]
    assert skill_response["skill"]["handoff_steps"][2] == "In the launcher, paste your idea, click Idea \uad6c\uccb4\ud654, then run the report."
    daily_code, daily_response = handle_get_api("/api/skill", "skill_id=daily_ai_radar")
    assert daily_code == HTTPStatus.OK
    assert daily_response["skill"]["handoff_steps"][2] == (
        "Read the generated radar report and review Executive Summary, Candidate Highlights, and Governance Notes."
    )
    assert "Radar recommendations are candidates, not implementation approval." in daily_response["skill"]["safety_notes"]
    for skill_id in ("research_council", "daily_ai_radar", "hermes_manager"):
        detail_code, detail_response = handle_get_api("/api/skill", f"skill_id={skill_id}")
        assert detail_code == HTTPStatus.OK
        detail = detail_response["skill"]
        assert detail["docs"] and detail["tests"]
        assert detail["action_guide"]
        assert detail["primary_next_action_label"]
        assert set(detail["commands"]).issuperset(REQUIRED_COMMAND_FIELDS)
    assert handle_get_api("/api/skill")[0] == HTTPStatus.BAD_REQUEST
    assert handle_get_api("/api/skill", "skill_id=missing")[0] == HTTPStatus.NOT_FOUND
    before_overview_status = run_read_only_git(("status", "--short"))
    overview_code, overview = handle_get_api("/api/overview")
    after_overview_status = run_read_only_git(("status", "--short"))
    assert before_overview_status == after_overview_status
    assert overview_code == HTTPStatus.OK
    assert overview["ok"] is True
    assert overview["mode"] == "read-only"
    assert overview["repo"]["head_short"]
    assert "jarvis.bat" in overview["repo"]["protected_path_note"]
    assert overview["repo"]["working_tree_status"]
    assert len(overview["tasks"]) <= OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["reports"]) <= OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["checkpoints"]) <= OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["docs_examples"]) <= OVERVIEW_MAX_TOTAL_ITEMS
    assert [group["group_id"] for group in overview["recent_groups"]] == [
        "tasks",
        "reports",
        "checkpoints",
        "docs_examples",
    ]
    assert [group["title"] for group in overview["recent_groups"]] == [
        "Recent Tasks",
        "Recent Reports",
        "Recent Checkpoints",
        "Recent Docs / Examples",
    ]
    assert all(group["read_only"] is True for group in overview["recent_groups"])
    assert overview["discovery"]["max_items_per_directory"] == OVERVIEW_MAX_ITEMS_PER_DIRECTORY
    assert overview["discovery"]["max_total_items"] == OVERVIEW_MAX_TOTAL_ITEMS
    assert overview["discovery"]["allowed_extensions"] == sorted(OVERVIEW_ALLOWED_EXTENSIONS)
    assert ".git" in overview["discovery"]["excluded"]
    assert "__pycache__" in overview["discovery"]["excluded"]
    assert any(item["skill_id"] == "daily_ai_radar" for item in overview["skills"])
    overview_items = [
        item
        for section in ("tasks", "reports", "checkpoints", "docs_examples")
        for item in overview[section]
    ]
    overview_items.extend(item for group in overview["recent_groups"] for item in group["items"])
    overview_items.extend(item for skill in overview["skills"] for item in skill["recent_items"])
    assert overview_items
    for item in overview_items:
        assert item["path"].split("/")[-1][0] != "."
        assert_overview_item_safety(item)
    assert any(item["source_area"] == "jarvis_console" for item in overview["checkpoints"] + overview["docs_examples"])
    assert any(item["item_type"] == "checkpoint" for item in overview["checkpoints"])
    assert all(item["item_type"] == "task" for item in overview["tasks"])
    assert all(item["item_type"] == "report" for item in overview["reports"])
    before_history_status = run_read_only_git(("status", "--short"))
    history_code, history = handle_get_api("/api/history")
    after_history_status = run_read_only_git(("status", "--short"))
    assert before_history_status == after_history_status
    assert history_code == HTTPStatus.OK
    assert history["ok"] is True
    assert history["mode"] == "read-only"
    assert history["repo"]["head_short"]
    assert "root" not in history["repo"]
    assert "jarvis.bat" in history["repo"]["protected_path_note"]
    assert history["recent_commits"]
    assert len(history["recent_commits"]) <= HISTORY_MAX_COMMITS
    for commit in history["recent_commits"]:
        assert_history_commit_safety(commit)
    history_items = history["checkpoint_docs"] + history["related_items"]
    assert history_items
    for item in history_items:
        assert_overview_item_safety(item)
        assert is_history_candidate_name(Path(item["path"]))
    assert any(item["path"] == "docs/jarvis-console-v0.1-checkpoint.md" for item in history["checkpoint_docs"])
    assert any(item["read_only"] is True for item in history["checkpoint_docs"])
    assert all("\\" not in item["path"] for item in history_items)
    assert history["discovery"]["max_commits"] == HISTORY_MAX_COMMITS
    assert history["discovery"]["allowed_extensions"] == sorted(OVERVIEW_ALLOWED_EXTENSIONS)
    assert [item["path"] for item in history["discovery"]["safe_directories"]] == [
        "docs",
        "apps/jarvis-console",
        "apps/hermes-manager-pilot/examples",
        "apps/daily-ai-radar/examples",
    ]
    assert ".git" in history["discovery"]["excluded"]
    assert "__pycache__" in history["discovery"]["excluded"]
    assert "This view is read-only." in history["notes"]
    assert "It does not create commits or checkpoints." in history["notes"]
    assert is_history_candidate_name(REPO_ROOT / "docs" / "jarvis-console-v0.1-checkpoint.md") is True
    assert is_history_candidate_name(REPO_ROOT / "docs" / "sample.md") is False

    before_memory_status = run_read_only_git(("status", "--short"))
    memory_code, memory = handle_get_api("/api/memory-skills")
    after_memory_status = run_read_only_git(("status", "--short"))
    assert before_memory_status == after_memory_status
    assert memory_code == HTTPStatus.OK
    assert memory["ok"] is True
    assert memory["mode"] == "read-only"
    assert memory["phase"] == "phase_2b_preview_only"
    assert memory["read_only"] is True
    assert memory["sample"] is True
    assert memory["preview_only"] is True
    assert memory["not_saved"] is True
    assert memory["no_persistence"] is True
    assert memory["runtime_write"] is False
    assert memory["save_endpoint"] is False
    assert memory["post_endpoints"] == "preview_only"
    assert memory["write_endpoints"] is False
    assert memory["preview_endpoint"] == MEMORY_PREVIEW_ENDPOINT
    assert memory["preview_endpoint_write_free"] is True
    assert memory["approval_gated_save_api"] is False
    assert memory["approval_gated_save_endpoint"] is False
    assert memory["candidate_write_helper"] == "tests_only"
    assert memory["request_guard"] == "internal_tests_only"
    assert memory["preview_token_subsystem"] == "internal_tests_only"
    assert memory["guarded_save_coordinator"] == "internal_tests_only"
    assert memory["http_metadata_adapter"] == "internal_tests_only"
    assert memory["persisted_original_text_preview"] is False
    assert memory["preview_token_issuance"] is False
    assert memory["ui_save_action"] is False
    assert memory["voice_inbox_auto_save"] is False
    assert len(memory["candidates"]) == len(MEMORY_SKILLS_SAMPLE_CANDIDATES)
    assert "Review Candidate" in memory["allowed_actions"]
    assert "Preview Local Candidate" in memory["allowed_actions"]
    assert "Copy Candidate" in memory["allowed_actions"]
    assert "Copy Skill Draft Prompt" in memory["allowed_actions"]
    assert "Open Skill Details" in memory["allowed_actions"]
    assert any("Voice Inbox" in item for item in memory["guidance"])
    assert any("No automatic memory save." == item for item in memory["safety_boundary"])
    assert any("No runtime file write." == item for item in memory["safety_boundary"])
    assert any("No UI save action." == item for item in memory["safety_boundary"])
    assert "No approval-gated save API endpoint." in memory["safety_boundary"]
    for candidate in memory["candidates"]:
        assert_memory_candidate_safety(candidate)

    run_memory_http_metadata_adapter_self_tests()
    run_memory_request_guard_token_self_tests()
    run_memory_guarded_save_coordinator_self_tests()

    with TemporaryDirectory(prefix="jarvis-localappdata-") as fake_local_appdata_text:
        fake_local_appdata = Path(fake_local_appdata_text)
        windows_default_state = resolve_memory_skills_state_paths(
            env={"LOCALAPPDATA": str(fake_local_appdata)},
            is_windows=True,
        )
        assert windows_default_state["ok"] is True
        assert windows_default_state["source"] == "default_windows_localappdata"
        assert windows_default_state["state_root"] == normalize_filesystem_path(fake_local_appdata / "Jarvis-Core")
        assert windows_default_state["candidate_dir"] == normalize_filesystem_path(
            fake_local_appdata / "Jarvis-Core" / "memory-skills" / "candidates"
        )
        assert windows_default_state["repo_internal"] is False
        assert windows_default_state["will_create_directory"] is False
        assert windows_default_state["will_write_files"] is False
        assert not windows_default_state["state_root"].exists()
        assert not windows_default_state["candidate_dir"].exists()

    with TemporaryDirectory(prefix="jarvis-home-") as fake_home_text:
        fake_home = Path(fake_home_text)
        home_default_state = resolve_memory_skills_state_paths(env={}, home_dir=fake_home, is_windows=False)
        assert home_default_state["ok"] is True
        assert home_default_state["source"] == "default_home"
        assert home_default_state["candidate_dir"] == normalize_filesystem_path(
            fake_home / ".jarvis-core" / "memory-skills" / "candidates"
        )
        assert not home_default_state["state_root"].exists()
        assert not home_default_state["candidate_dir"].exists()

    with TemporaryDirectory(prefix="jarvis-state-override-") as fake_override_root_text:
        fake_override_root = Path(fake_override_root_text)
        override_state = resolve_memory_skills_state_paths(env={JARVIS_LOCAL_STATE_DIR_ENV: str(fake_override_root)})
        assert override_state["ok"] is True
        assert override_state["source"] == "env_override"
        assert override_state["candidate_dir"] == normalize_filesystem_path(
            fake_override_root / "memory-skills" / "candidates"
        )
        assert not override_state["candidate_dir"].exists()
        assert not override_state["candidate_dir"].parent.exists()

    relative_override_state = resolve_memory_skills_state_paths(env={JARVIS_LOCAL_STATE_DIR_ENV: "relative-state"})
    assert relative_override_state["ok"] is False
    assert relative_override_state["error"] == "local_state_dir_must_be_absolute"

    repo_internal_state = resolve_memory_skills_state_paths(
        env={JARVIS_LOCAL_STATE_DIR_ENV: str(REPO_ROOT / ".jarvis-local")}
    )
    assert repo_internal_state["ok"] is False
    assert repo_internal_state["error"] == "local_state_dir_inside_repo"
    assert repo_internal_state["repo_internal"] is True
    assert is_path_inside_repo(REPO_ROOT / ".jarvis-local" / "memory-skills" / "candidates") is True
    traversal_like_state = resolve_memory_skills_state_paths(
        env={JARVIS_LOCAL_STATE_DIR_ENV: str(REPO_ROOT / "apps" / ".." / ".jarvis-local")}
    )
    assert traversal_like_state["ok"] is False
    assert traversal_like_state["error"] == "local_state_dir_inside_repo"
    fake_reparse_stat = type(
        "FakeReparseStat",
        (),
        {"st_mode": stat.S_IFDIR, "st_file_attributes": 0x0400},
    )()
    assert filesystem_stat_is_reparse_point(fake_reparse_stat) is True
    assert not APP_ROOT.joinpath("state").exists()
    assert not REPO_ROOT.joinpath(".jarvis-local").exists()

    preview_request = {
        "source": "voice_inbox",
        "title": "Repeated workflow preview",
        "cleaned_text": "이 반복 작업을 Memory / Skills 후보로 검토한다.",
        "original_text_preview": "이 반복 작업 skill 후보로 기억해줘",
        "candidate_type": "repeated_workflow",
        "confidence": "medium",
        "tags": ["voice_inbox", "preview"],
        "safety_notes": ["Preview only; no local memory is written."],
    }
    before_preview_status = run_read_only_git(("status", "--short"))
    preview_code, preview = handle_post_api(MEMORY_PREVIEW_ENDPOINT, preview_request)
    after_preview_status = run_read_only_git(("status", "--short"))
    assert before_preview_status == after_preview_status
    assert preview_code == HTTPStatus.OK
    assert preview["ok"] is True
    assert preview["preview_only"] is True
    assert preview["not_saved"] is True
    assert preview["read_only"] is True
    assert preview["no_persistence"] is True
    assert preview["runtime_write"] is False
    assert preview["save_endpoint"] is False
    assert preview["phase"] == "phase_2b_preview_only"
    assert preview["privacy_warning"]
    assert "Nothing has been saved" in preview["next_step"]
    candidate_preview = preview["candidate_preview"]
    assert candidate_preview["schema_version"] == "memory_candidate.v1"
    assert candidate_preview["id"] == "preview_only_not_persisted"
    assert candidate_preview["status"] == "preview_only"
    assert candidate_preview["suggested_skill_id"] == "memory_skills"
    assert candidate_preview["confirmation_required"] is True
    assert candidate_preview["user_approved_at"] is None
    assert candidate_preview["redaction_status"] == "preview_only"
    assert len(candidate_preview["original_text_preview"]) <= MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS
    assert "/" not in candidate_preview["id"]
    assert "\\" not in candidate_preview["id"]
    assert handle_post_api(MEMORY_PREVIEW_ENDPOINT, {})[0] == HTTPStatus.BAD_REQUEST
    assert handle_post_api(MEMORY_PREVIEW_ENDPOINT, {"cleaned_text": ""})[0] == HTTPStatus.BAD_REQUEST
    assert handle_post_api(MEMORY_PREVIEW_ENDPOINT, {"cleaned_text": "x" * (MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS + 1)})[0] == HTTPStatus.BAD_REQUEST
    assert handle_post_api(
        MEMORY_PREVIEW_ENDPOINT,
        {"cleaned_text": "../memory/tasks/secret", "candidate_type": "../../escape", "source": "C:\\temp"},
    )[1]["candidate_preview"]["id"] == "preview_only_not_persisted"
    assert handle_post_api(
        MEMORY_PREVIEW_ENDPOINT,
        {"cleaned_text": "valid", "original_text_preview": "x" * (MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS + 1)},
    )[0] == HTTPStatus.BAD_REQUEST
    invalid_preview_payloads = (
        {"cleaned_text": "\ud800"},
        {"cleaned_text": "valid", "title": "bad\udfff"},
        {"cleaned_text": "valid", "original_text_preview": "bad\ud800"},
        {"cleaned_text": "valid", "tags": ["bad\ud800"]},
        {"cleaned_text": "valid", "safety_notes": ["bad\udfff"]},
        {"cleaned_text": "valid", "candidate_type": "bad\ud800"},
        {"cleaned_text": "valid", "confidence": "bad\ud800"},
        {"cleaned_text": "valid", "source": "bad\ud800"},
        {"cleaned_text": "bad\x00text"},
    )
    for invalid_preview_payload in invalid_preview_payloads:
        invalid_unicode_code, invalid_unicode_preview = handle_post_api(
            MEMORY_PREVIEW_ENDPOINT,
            invalid_preview_payload,
        )
        assert invalid_unicode_code == HTTPStatus.BAD_REQUEST
        assert invalid_unicode_preview == {"ok": False, "error": "invalid_unicode"}

    valid_unicode_code, valid_unicode_preview = handle_post_api(
        MEMORY_PREVIEW_ENDPOINT,
        {
            "title": "정상 한글 😀 𐐷",
            "cleaned_text": "반복 작업을 안전하게 정리 😀 𐐷",
            "original_text_preview": "원문 미리보기 😀",
            "tags": ["한글", "emoji-😀"],
            "safety_notes": ["정상 Unicode만 저장 후보로 사용 😀"],
        },
    )
    assert valid_unicode_code == HTTPStatus.OK
    assert valid_unicode_preview["candidate_preview"]["title"] == "정상 한글 😀 𐐷"
    assert valid_unicode_preview["candidate_preview"]["cleaned_text"] == "반복 작업을 안전하게 정리 😀 𐐷"
    save_dry_run_request = {
        "candidate_preview": candidate_preview,
        "explicit_confirmation": True,
        "privacy_reviewed": True,
        "save_scope": "local_only",
    }
    save_dry_run_code, save_dry_run = validate_memory_skills_save_dry_run(save_dry_run_request)
    assert save_dry_run_code == HTTPStatus.OK
    assert save_dry_run["dry_run"] is True
    assert save_dry_run["valid_for_local_save"] is True
    assert save_dry_run["will_write_files"] is False
    assert save_dry_run["will_create_directory"] is False
    assert save_dry_run["save_endpoint_enabled"] is False
    assert save_dry_run["phase"] == MEMORY_SAVE_DRY_RUN_PHASE
    assert save_dry_run["candidate"]["status"] == "preview_only"
    assert save_dry_run["candidate"]["user_approved_at"] is None
    assert any("Nothing has been saved" in warning for warning in save_dry_run["warnings"])

    def assert_save_dry_run_rejected(body: Any, expected_error: str) -> None:
        rejected_code, rejected = validate_memory_skills_save_dry_run(body)
        assert rejected_code == HTTPStatus.BAD_REQUEST
        assert rejected["dry_run"] is True
        assert rejected["valid_for_local_save"] is False
        assert rejected["will_write_files"] is False
        assert rejected["will_create_directory"] is False
        assert rejected["save_endpoint_enabled"] is False
        assert rejected["error"] == expected_error

    def save_dry_run_body(
        *,
        body_updates: dict[str, Any] | None = None,
        candidate_updates: dict[str, Any] | None = None,
        remove_body_fields: tuple[str, ...] = (),
        remove_candidate_fields: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        body = dict(save_dry_run_request)
        body["candidate_preview"] = dict(candidate_preview)
        if body_updates:
            body.update(body_updates)
        if candidate_updates:
            body["candidate_preview"].update(candidate_updates)
        for field in remove_body_fields:
            body.pop(field, None)
        for field in remove_candidate_fields:
            body["candidate_preview"].pop(field, None)
        return body

    assert_save_dry_run_rejected([], "request_body_must_be_object")
    assert_save_dry_run_rejected(save_dry_run_body(remove_body_fields=("candidate_preview",)), "missing_candidate_preview")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"candidate_preview": []}), "candidate_preview_must_be_object")
    assert_save_dry_run_rejected(save_dry_run_body(remove_body_fields=("explicit_confirmation",)), "explicit_confirmation_required")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"explicit_confirmation": False}), "explicit_confirmation_required")
    assert_save_dry_run_rejected(save_dry_run_body(remove_body_fields=("privacy_reviewed",)), "privacy_review_required")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"privacy_reviewed": False}), "privacy_review_required")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"save_scope": "repo"}), "invalid_save_scope")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"status": "saved"}), "candidate_must_be_preview_only")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"suggested_skill_id": "hermes_manager"}), "invalid_suggested_skill_id")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"confirmation_required": False}), "confirmation_required_expected")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"user_approved_at": "2026-07-08"}), "candidate_already_approved")
    assert_save_dry_run_rejected(save_dry_run_body(remove_candidate_fields=("cleaned_text",)), "missing_cleaned_text")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"cleaned_text": ""}), "empty_cleaned_text")
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"cleaned_text": "x" * (MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS + 1)}),
        "cleaned_text_too_long",
    )
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"title": "x" * (MEMORY_PREVIEW_TITLE_MAX_CHARS + 1)}),
        "title_too_long",
    )
    assert_save_dry_run_rejected(
        save_dry_run_body(
            candidate_updates={"original_text_preview": "x" * (MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS + 1)}
        ),
        "original_text_preview_too_long",
    )
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"candidate_type": "../escape"}), "invalid_candidate_type")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"confidence": "certain"}), "invalid_confidence")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"source": "C:\\temp"}), "invalid_source")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"tags": "not-list"}), "tags_must_be_list")
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"tags": [f"tag{i}" for i in range(MEMORY_PREVIEW_MAX_TAGS + 1)]}),
        "too_many_tags",
    )
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"tags": ["x" * (MEMORY_PREVIEW_TAG_MAX_CHARS + 1)]}),
        "tags_item_too_long",
    )
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"safety_notes": "not-list"}), "safety_notes_must_be_list")
    assert_save_dry_run_rejected(
        save_dry_run_body(
            candidate_updates={"safety_notes": [f"note{i}" for i in range(MEMORY_PREVIEW_MAX_SAFETY_NOTES + 1)]}
        ),
        "too_many_safety_notes",
    )
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"safety_notes": ["x" * (MEMORY_PREVIEW_SAFETY_NOTE_MAX_CHARS + 1)]}),
        "safety_notes_item_too_long",
    )
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"raw_transcript": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"full_transcript": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"original_text": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"storage_path": "memory/skills/x.json"}), "path_field_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"repo_path": "memory/skills/x.json"}), "path_field_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"file_path": "memory/tasks/x.json"}), "path_field_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"candidate_file": "candidate.json"}), "path_field_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"id": "../memory/tasks/x"}), "invalid_candidate_id")
    for scalar_field in (
        "title",
        "cleaned_text",
        "original_text_preview",
        "next_action",
        "privacy_note",
        "candidate_type",
        "confidence",
        "source",
    ):
        assert_save_dry_run_rejected(
            save_dry_run_body(candidate_updates={scalar_field: "bad\ud800"}),
            "invalid_unicode",
        )
    for list_field in ("tags", "safety_notes"):
        assert_save_dry_run_rejected(
            save_dry_run_body(candidate_updates={list_field: ["bad\udfff"]}),
            "invalid_unicode",
        )
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"cleaned_text": "bad\x00text"}),
        "invalid_unicode",
    )

    serialized_code, serialized_error, serialized_candidate = serialize_memory_candidate_json(
        {"title": "정상 한글 😀 𐐷"},
        max_bytes=1024,
    )
    assert serialized_code == HTTPStatus.OK
    assert serialized_error == ""
    assert json.loads(serialized_candidate.decode("utf-8"))["title"] == "정상 한글 😀 𐐷"
    assert serialize_memory_candidate_json({"title": "bad\ud800"})[:2] == (
        HTTPStatus.BAD_REQUEST,
        "invalid_unicode",
    )
    assert serialize_memory_candidate_json({"title": "bad\x00text"})[:2] == (
        HTTPStatus.BAD_REQUEST,
        "invalid_unicode",
    )
    assert serialize_memory_candidate_json({"title": "too large"}, max_bytes=1)[:2] == (
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        "candidate_json_too_large",
    )

    def assert_save_endpoint_rejected(
        body: Any,
        expected_error: str,
        expected_status: HTTPStatus = HTTPStatus.BAD_REQUEST,
    ) -> None:
        rejected_code, rejected = save_memory_skills_candidate(body)
        assert rejected_code == expected_status
        assert rejected["ok"] is False
        assert rejected["saved"] is False
        assert rejected["error"] == expected_error
        assert rejected["skill_created"] is False
        assert rejected["registry_modified"] is False
        assert rejected["will_run_automatically"] is False
        assert "candidate_file" not in rejected

    assert_save_endpoint_rejected(save_dry_run_body(remove_body_fields=("explicit_confirmation",)), "explicit_confirmation_required")
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"explicit_confirmation": False}), "explicit_confirmation_required")
    assert_save_endpoint_rejected(save_dry_run_body(remove_body_fields=("privacy_reviewed",)), "privacy_review_required")
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"privacy_reviewed": False}), "privacy_review_required")
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"save_scope": "repo"}), "invalid_save_scope")
    assert_save_endpoint_rejected(save_dry_run_body(candidate_updates={"status": "saved"}), "candidate_must_be_preview_only")
    assert_save_endpoint_rejected(save_dry_run_body(candidate_updates={"user_approved_at": "2026-07-08"}), "candidate_already_approved")
    assert_save_endpoint_rejected(
        save_dry_run_body(candidate_updates={"cleaned_text": "x" * (MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS + 1)}),
        "cleaned_text_too_long",
    )
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"raw_transcript": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_endpoint_rejected(save_dry_run_body(candidate_updates={"original_text": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"storage_path": "memory/skills/x.json"}), "path_field_not_allowed")
    assert_save_endpoint_rejected(save_dry_run_body(candidate_updates={"candidate_file": "candidate.json"}), "path_field_not_allowed")

    endpoint_candidate_id = "mem_111111111111"
    endpoint_timestamp = "2026-07-08T00:00:00Z"
    with TemporaryDirectory(prefix="jarvis-candidate-endpoint-") as endpoint_root_text:
        endpoint_root = Path(endpoint_root_text)
        endpoint_code, endpoint_result = save_memory_skills_candidate(
            save_dry_run_request,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(endpoint_root)},
            id_generator=lambda: endpoint_candidate_id,
            clock=lambda: endpoint_timestamp,
        )
        assert endpoint_code == HTTPStatus.OK
        assert endpoint_result["ok"] is True
        assert endpoint_result["saved"] is True
        assert endpoint_result["status"] == "saved"
        assert endpoint_result["candidate_id"] == endpoint_candidate_id
        assert endpoint_result["title"] == candidate_preview["title"]
        assert endpoint_result["message"] == MEMORY_SAVE_SUCCESS_MESSAGE
        assert endpoint_result["skill_created"] is False
        assert endpoint_result["registry_modified"] is False
        assert endpoint_result["will_run_automatically"] is False
        assert endpoint_result["local_only"] is True
        assert "candidate_file" not in endpoint_result
        endpoint_candidate_dir = normalize_filesystem_path(endpoint_root / "memory-skills" / "candidates")
        endpoint_candidate_file = normalize_filesystem_path(endpoint_candidate_dir / f"{endpoint_candidate_id}.json")
        assert endpoint_candidate_file.exists()
        endpoint_stored_candidate = json.loads(endpoint_candidate_file.read_text(encoding="utf-8"))
        assert endpoint_stored_candidate["status"] == "saved"
        assert endpoint_stored_candidate["redaction_status"] == "user_confirmed"
        assert endpoint_stored_candidate["suggested_skill_id"] == "memory_skills"
        for forbidden_field in (
            "original_text_preview",
            "original_text",
            "raw_transcript",
            "full_transcript",
            "file_path",
            "path",
            "candidate_file",
            "storage_path",
            "repo_path",
        ):
            assert forbidden_field not in endpoint_stored_candidate
        before_endpoint_collision = endpoint_candidate_file.read_text(encoding="utf-8")
        endpoint_collision_code, endpoint_collision = save_memory_skills_candidate(
            save_dry_run_request,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(endpoint_root)},
            id_generator=lambda: endpoint_candidate_id,
            clock=lambda: endpoint_timestamp,
        )
        assert endpoint_collision_code == HTTPStatus.CONFLICT
        assert endpoint_collision["saved"] is False
        assert endpoint_collision["error"] == "candidate_file_exists"
        assert "candidate_file" not in endpoint_collision
        assert endpoint_candidate_file.read_text(encoding="utf-8") == before_endpoint_collision

    with TemporaryDirectory(prefix="jarvis-candidate-endpoint-invalid-") as invalid_endpoint_root_text:
        invalid_endpoint_root = Path(invalid_endpoint_root_text)
        invalid_endpoint_body = save_dry_run_body(remove_body_fields=("explicit_confirmation",))
        invalid_endpoint_code, invalid_endpoint = save_memory_skills_candidate(
            invalid_endpoint_body,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(invalid_endpoint_root)},
            id_generator=lambda: "mem_222222222222",
            clock=lambda: endpoint_timestamp,
        )
        assert invalid_endpoint_code == HTTPStatus.BAD_REQUEST
        assert invalid_endpoint["error"] == "explicit_confirmation_required"
        assert not (invalid_endpoint_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-candidate-endpoint-failure-") as endpoint_failure_root_text:
        endpoint_failure_root = Path(endpoint_failure_root_text)
        endpoint_blocking_path = endpoint_failure_root / "memory-skills"
        endpoint_blocking_path.write_text("not a directory", encoding="utf-8")
        endpoint_failure_code, endpoint_failure = save_memory_skills_candidate(
            save_dry_run_request,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(endpoint_failure_root)},
            id_generator=lambda: "mem_333333333333",
            clock=lambda: endpoint_timestamp,
        )
        assert endpoint_failure_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert endpoint_failure["saved"] is False
        assert endpoint_failure["error"] == "candidate_write_failed"
        assert "candidate_file" not in endpoint_failure
        assert endpoint_blocking_path.is_file()

    endpoint_repo_write_code, endpoint_repo_write = save_memory_skills_candidate(
        save_dry_run_request,
        env={JARVIS_LOCAL_STATE_DIR_ENV: str(REPO_ROOT / ".jarvis-local")},
        id_generator=lambda: "mem_444444444444",
        clock=lambda: endpoint_timestamp,
    )
    assert endpoint_repo_write_code == HTTPStatus.BAD_REQUEST
    assert endpoint_repo_write["error"] == "local_state_dir_inside_repo"
    assert not REPO_ROOT.joinpath(".jarvis-local").exists()

    valid_unicode_save_request = {
        "candidate_preview": valid_unicode_preview["candidate_preview"],
        "explicit_confirmation": True,
        "privacy_reviewed": True,
        "save_scope": "local_only",
    }
    valid_unicode_dry_run_code, valid_unicode_dry_run = validate_memory_skills_save_dry_run(
        valid_unicode_save_request
    )
    assert valid_unicode_dry_run_code == HTTPStatus.OK
    with TemporaryDirectory(prefix="jarvis-unicode-candidate-write-") as unicode_write_root_text:
        unicode_write_root = Path(unicode_write_root_text)
        unicode_write_code, unicode_write = write_memory_skills_candidate(
            valid_unicode_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(unicode_write_root)},
            id_generator=lambda: "mem_555555555555",
            clock=lambda: "2026-07-08T00:00:00Z",
        )
        assert unicode_write_code == HTTPStatus.OK
        unicode_candidate_file = unicode_write_root / "memory-skills" / "candidates" / "mem_555555555555.json"
        unicode_stored_candidate = json.loads(unicode_candidate_file.read_text(encoding="utf-8"))
        assert unicode_stored_candidate["title"] == "정상 한글 😀 𐐷"
        assert unicode_stored_candidate["cleaned_text"] == "반복 작업을 안전하게 정리 😀 𐐷"
        assert not list(unicode_candidate_file.parent.glob("*.tmp"))

    for invalid_stored_text in ("bad\ud800", "bad\x00text"):
        with TemporaryDirectory(prefix="jarvis-invalid-unicode-write-") as invalid_unicode_root_text:
            invalid_unicode_root = Path(invalid_unicode_root_text)
            invalid_unicode_dry_run = dict(save_dry_run)
            invalid_unicode_dry_run["candidate"] = dict(save_dry_run["candidate"])
            invalid_unicode_dry_run["candidate"]["cleaned_text"] = invalid_stored_text
            invalid_unicode_write_code, invalid_unicode_write = write_memory_skills_candidate(
                invalid_unicode_dry_run,
                env={JARVIS_LOCAL_STATE_DIR_ENV: str(invalid_unicode_root)},
                id_generator=lambda: "mem_666666666666",
                clock=lambda: "2026-07-08T00:00:00Z",
            )
            assert invalid_unicode_write_code == HTTPStatus.BAD_REQUEST
            assert invalid_unicode_write["error"] == "invalid_unicode"
            assert "candidate_file" not in invalid_unicode_write
            assert str(invalid_unicode_root) not in str(invalid_unicode_write)
            assert not (invalid_unicode_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-invalid-timestamp-write-") as invalid_timestamp_root_text:
        invalid_timestamp_root = Path(invalid_timestamp_root_text)
        invalid_timestamp_code, invalid_timestamp = write_memory_skills_candidate(
            save_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(invalid_timestamp_root)},
            id_generator=lambda: "mem_777777777777",
            clock=lambda: "bad\ud800",
        )
        assert invalid_timestamp_code == HTTPStatus.BAD_REQUEST
        assert invalid_timestamp["error"] == "invalid_unicode"
        assert not (invalid_timestamp_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-oversize-candidate-write-") as oversize_root_text:
        oversize_root = Path(oversize_root_text)
        oversize_code, oversize = write_memory_skills_candidate(
            save_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(oversize_root)},
            id_generator=lambda: "mem_888888888888",
            clock=lambda: "2026-07-08T00:00:00Z",
            max_json_bytes=1,
        )
        assert oversize_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        assert oversize["error"] == "candidate_json_too_large"
        assert "candidate_file" not in oversize
        assert not (oversize_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-reparse-candidate-write-") as reparse_root_text:
        reparse_root = Path(reparse_root_text)
        reparse_target = reparse_root / "target"
        reparse_target.mkdir()
        reparse_state_root = reparse_root / "state-link"
        try:
            reparse_state_root.symlink_to(reparse_target, target_is_directory=True)
        except (NotImplementedError, OSError):
            pass
        else:
            reparse_code, reparse_result = write_memory_skills_candidate(
                save_dry_run,
                env={JARVIS_LOCAL_STATE_DIR_ENV: str(reparse_state_root)},
                id_generator=lambda: "mem_999999999999",
                clock=lambda: "2026-07-08T00:00:00Z",
            )
            assert reparse_code == HTTPStatus.BAD_REQUEST
            assert reparse_result["error"] == "candidate_path_not_safe"
            assert "candidate_file" not in reparse_result
            assert not (reparse_target / "memory-skills").exists()

    fixed_candidate_id = "mem_0123456789ab"
    fixed_timestamp = "2026-07-08T00:00:00Z"
    with TemporaryDirectory(prefix="jarvis-candidate-write-") as write_root_text:
        write_root = Path(write_root_text)
        write_code, write_result = write_memory_skills_candidate(
            save_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(write_root)},
            id_generator=lambda: fixed_candidate_id,
            clock=lambda: fixed_timestamp,
        )
        assert write_code == HTTPStatus.OK
        assert write_result["saved"] is True
        assert write_result["status"] == "saved"
        assert write_result["candidate_id"] == fixed_candidate_id
        assert write_result["will_run_automatically"] is False
        assert write_result["skill_created"] is False
        assert write_result["registry_modified"] is False
        candidate_dir = normalize_filesystem_path(write_root / "memory-skills" / "candidates")
        candidate_file = normalize_filesystem_path(candidate_dir / f"{fixed_candidate_id}.json")
        assert Path(write_result["candidate_file"]) == candidate_file
        assert candidate_file.exists()
        assert not is_path_inside_repo(candidate_file)
        stored_candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
        assert stored_candidate["schema_version"] == "memory_candidate.v1"
        assert stored_candidate["storage_version"] == MEMORY_CANDIDATE_STORAGE_VERSION
        assert stored_candidate["id"] == fixed_candidate_id
        assert stored_candidate["status"] == "saved"
        assert stored_candidate["created_at"] == fixed_timestamp
        assert stored_candidate["updated_at"] == fixed_timestamp
        assert stored_candidate["user_approved_at"] == fixed_timestamp
        assert stored_candidate["redaction_status"] == "user_confirmed"
        assert stored_candidate["suggested_skill_id"] == "memory_skills"
        assert "original_text_preview" not in stored_candidate
        assert "original_text" not in stored_candidate
        assert "raw_transcript" not in stored_candidate
        assert "full_transcript" not in stored_candidate
        assert "file_path" not in stored_candidate
        assert "path" not in stored_candidate
        assert "candidate_file" not in stored_candidate
        assert "storage_path" not in stored_candidate
        assert "repo_path" not in stored_candidate
        assert not list(candidate_dir.glob(f".{fixed_candidate_id}.*.tmp"))
        before_collision_text = candidate_file.read_text(encoding="utf-8")
        collision_code, collision = write_memory_skills_candidate(
            save_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(write_root)},
            id_generator=lambda: fixed_candidate_id,
            clock=lambda: fixed_timestamp,
        )
        assert collision_code == HTTPStatus.CONFLICT
        assert collision["saved"] is False
        assert collision["error"] == "candidate_file_exists"
        assert candidate_file.read_text(encoding="utf-8") == before_collision_text
        assert not list(candidate_dir.glob(f".{fixed_candidate_id}.*.tmp"))
        invalid_id_code, invalid_id = write_memory_skills_candidate(
            save_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(write_root)},
            id_generator=lambda: "../memory/tasks/x",
            clock=lambda: fixed_timestamp,
        )
        assert invalid_id_code == HTTPStatus.BAD_REQUEST
        assert invalid_id["error"] == "invalid_candidate_id"
        assert len(list(candidate_dir.glob("*.json"))) == 1

    with TemporaryDirectory(prefix="jarvis-link-collision-write-") as link_collision_root_text:
        link_collision_root = Path(link_collision_root_text)
        link_collision_candidate = (
            link_collision_root / "memory-skills" / "candidates" / "mem_aaaaaaaaaaaa.json"
        )

        def collide_during_publish(_temp_file: Path, final_file: Path) -> None:
            final_file.write_bytes(b"existing candidate")
            raise FileExistsError

        link_collision_code, link_collision = write_memory_skills_candidate(
            save_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(link_collision_root)},
            id_generator=lambda: "mem_aaaaaaaaaaaa",
            clock=lambda: fixed_timestamp,
            linker=collide_during_publish,
        )
        assert link_collision_code == HTTPStatus.CONFLICT
        assert link_collision["error"] == "candidate_file_exists"
        assert "candidate_file" not in link_collision
        assert link_collision_candidate.read_bytes() == b"existing candidate"
        assert not list(link_collision_candidate.parent.glob("*.tmp"))

    with TemporaryDirectory(prefix="jarvis-link-failure-write-") as link_failure_root_text:
        link_failure_root = Path(link_failure_root_text)

        def fail_candidate_publish(_temp_file: Path, _final_file: Path) -> None:
            raise OSError("private filesystem detail")

        link_failure_code, link_failure = write_memory_skills_candidate(
            save_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(link_failure_root)},
            id_generator=lambda: "mem_bbbbbbbbbbbb",
            clock=lambda: fixed_timestamp,
            linker=fail_candidate_publish,
        )
        link_failure_candidate_dir = link_failure_root / "memory-skills" / "candidates"
        assert link_failure_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert link_failure["error"] == "candidate_write_failed"
        assert "candidate_file" not in link_failure
        assert "private filesystem detail" not in str(link_failure)
        assert str(link_failure_root) not in str(link_failure)
        assert not list(link_failure_candidate_dir.glob("*.tmp"))
        assert not list(link_failure_candidate_dir.glob("*.json"))

    with TemporaryDirectory(prefix="jarvis-invalid-candidate-write-") as invalid_write_root_text:
        invalid_write_root = Path(invalid_write_root_text)
        invalid_dry_run = dict(save_dry_run)
        invalid_dry_run["candidate"] = dict(save_dry_run["candidate"])
        invalid_dry_run["candidate"]["status"] = "saved"
        invalid_candidate_code, invalid_candidate = write_memory_skills_candidate(
            invalid_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(invalid_write_root)},
            id_generator=lambda: "mem_abcdefabcdef",
            clock=lambda: fixed_timestamp,
        )
        assert invalid_candidate_code == HTTPStatus.BAD_REQUEST
        assert invalid_candidate["error"] == "candidate_must_be_preview_only"
        assert not (invalid_write_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-candidate-write-failure-") as failure_root_text:
        failure_root = Path(failure_root_text)
        blocking_path = failure_root / "memory-skills"
        blocking_path.write_text("not a directory", encoding="utf-8")
        failure_code, failure = write_memory_skills_candidate(
            save_dry_run,
            env={JARVIS_LOCAL_STATE_DIR_ENV: str(failure_root)},
            id_generator=lambda: "mem_abcdefabcdef",
            clock=lambda: fixed_timestamp,
        )
        assert failure_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert failure["saved"] is False
        assert failure["error"] == "candidate_write_failed"
        assert blocking_path.is_file()

    repo_write_code, repo_write = write_memory_skills_candidate(
        save_dry_run,
        env={JARVIS_LOCAL_STATE_DIR_ENV: str(REPO_ROOT / ".jarvis-local")},
        id_generator=lambda: "mem_abcdefabcdef",
        clock=lambda: fixed_timestamp,
    )
    assert repo_write_code == HTTPStatus.BAD_REQUEST
    assert repo_write["error"] == "local_state_dir_inside_repo"
    assert not (REPO_ROOT / ".jarvis-local").exists()
    assert parse_json_body(b"{not json")[0] == HTTPStatus.BAD_REQUEST
    assert not (APP_ROOT / "state").exists()
    assert not (APP_ROOT / "examples" / "memory-skills-sample.json").exists()
    assert not (REPO_ROOT / ".jarvis-local").exists()
    assert not (REPO_ROOT / "memory" / "skills").exists()
    assert handle_post_api("/api/memory-skills", {})[0] == HTTPStatus.NOT_FOUND
    save_route_code, save_route = handle_post_api(MEMORY_SAVE_ENDPOINT, {})
    assert save_route_code == HTTPStatus.NOT_FOUND
    assert save_route == {"ok": False, "error": "not_found"}

    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "Chat / Command" in html
    assert "Voice Inbox" in html
    assert "Skills" in html
    assert "Hermes Manager" in html
    assert "Codex Review" in html
    assert "Load Read-Only Review" in html
    assert "Research Council" in html
    assert "Daily AI Radar" in html
    assert "Tasks / Reports" in html
    assert "Checkpoints / History" in html
    assert "Memory / Skills" in html
    assert "Settings" in html
    assert "skillGrid" in html
    assert "skillDetail" in html
    assert "Select a skill to inspect commands" in html
    assert "Safety mode: Jarvis only recommends. It does not run tools." in html
    assert "Local-only" in html
    assert "No automatic Codex / ChatGPT / Hermes invocation" in html
    assert "What do you want Jarvis to help with?" in html
    assert "Transcript / rough thought" in html
    assert "Prepare Task Candidate" in html
    assert "Paste From Clipboard" in html
    assert "Clear Transcript" in html
    assert "v0.1 does not record audio." in html
    assert "Jarvis will not run tools until you choose a handoff." in html
    assert "jarvis.bat" in html
    assert "Refresh Overview" in html
    assert "Refresh History" in html
    assert "Refresh Memory / Skills" in html
    assert "Read-only operations dashboard" in html
    assert "does not create tasks" in html
    assert "does not create commits" in html
    assert "preview-only: sample candidates" in html
    assert "no save endpoint" in html
    assert "no persistence" in html
    assert "no runtime write" in html

    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "fetch(" in app_js
    assert "/api/status" in app_js
    assert "/api/skill" in app_js
    assert "/api/overview" in app_js
    assert "/api/history" in app_js
    assert "/api/memory-skills" in app_js
    assert "/api/memory-skills/candidates/preview" in app_js
    assert "/api/codex-review/preview" in app_js
    assert "/api/voice-inbox/prepare" in app_js
    assert "renderCodexReview" in app_js
    assert "loadCodexReview" in app_js
    assert "renderOverview" in app_js
    assert "renderHistory" in app_js
    assert "renderMemorySkills" in app_js
    assert "loadMemorySkills" in app_js
    assert "memoryCandidateCards" in app_js
    assert "renderMemoryCandidatePreview" in app_js
    assert "previewMemoryCandidatePayload" in app_js
    assert "previewVoiceMemoryCandidate" in app_js
    assert "renderRecentCommits" in app_js
    assert "renderVoiceCandidate" in app_js
    assert "prepareVoiceCandidate" in app_js
    assert "jarvisCommandFromCleaned" in app_js
    assert "voiceUnknownGuidance" in app_js
    assert "renderRecentGroups" in app_js
    assert "normalizedOverviewItemsMarkup" in app_js
    assert "Read-only metadata" in app_js
    assert "overview-badge" in app_js
    assert "Open file" not in app_js
    assert "Edit file" not in app_js
    assert "Delete file" not in app_js
    assert "navigator.mediaDevices" not in app_js
    assert "getUserMedia" not in app_js
    assert "<audio" not in app_js
    assert "MediaRecorder" not in app_js
    assert "loadOverview" in app_js
    assert "loadHistory" in app_js
    assert "Refresh Overview" not in app_js
    assert "Refresh History" not in app_js
    assert "renderSkillCards" in app_js
    assert "renderSkillDetail" in app_js
    assert "action_guide" in app_js
    assert "What it does" in app_js
    assert "When to use" in app_js
    assert "Next action" in app_js
    assert "Commands" in app_js
    assert "selectedSkillId" in app_js
    assert "recommendedSkillId" in app_js
    assert "selected-skill" in app_js
    assert "handoffStepsForSkill" in app_js
    assert "copyNextActionForHandoff" in app_js
    assert "registeredSafetyNotes" in app_js
    assert "skill.safety_notes" in app_js
    assert "Suggested Skill Action Panel" in app_js
    assert "suggestion-action-panel" in app_js
    assert "Open Skill Details" in app_js
    assert "open-skill-details" in app_js
    assert "Open Local URL" in app_js
    assert "open-local-url" in app_js
    assert "Next handoff" in app_js
    assert "handoff-hint" in app_js
    assert "Copy Git Bash or PowerShell command." in app_js
    assert "Run it in your terminal." in app_js
    assert "Open the local URL after the server starts." in app_js
    assert "Follow the copied command output." in app_js
    assert "handoff_steps" in app_js
    assert "Run the command first if the page does not load." in app_js
    assert "data-copy-next-action" in app_js
    assert "Jarvis Console does not run it for you." in app_js
    assert "localOnlyUrl" in app_js
    assert "LOCAL_URL_PREFIX" in app_js
    assert "LOCAL_URL_PROTOCOL" in app_js
    assert "LOCAL_URL_HOSTNAME" in app_js
    assert "new URL(url)" in app_js
    assert "parsed.hostname === LOCAL_URL_HOSTNAME" in app_js
    assert "window.open" in app_js
    assert "noopener,noreferrer" in app_js
    assert "This only opens the URL. It does not start the server." in app_js
    assert "Opening a URL does not start the server." in app_js
    assert "Commands are copy-only." in app_js
    assert "Choose a skill manually from the sidebar." in app_js
    assert "No matching skill yet." in app_js
    assert "Idea validation -> Research Council" in app_js
    assert "Codex/repo work -> Hermes Manager" in app_js
    assert "navigator.clipboard.writeText" in app_js
    assert "copy-command" in app_js
    assert "copy-text" in app_js
    assert "Copy Cleaned Task" in app_js
    assert "Copy As Jarvis Command" in app_js
    assert "Open Memory / Skills" in app_js
    assert "Copy Candidate" in app_js
    assert "Copy Skill Draft Prompt" in app_js
    assert "Review Candidate" in app_js
    assert "Preview Local Candidate" in app_js
    assert "Preview only" in app_js
    assert "Not saved" in app_js
    assert "No persistence" in app_js
    assert "No runtime write" in app_js
    assert "No candidate preview prepared yet." in app_js
    assert "Nothing was saved." in app_js
    assert "Not available in Phase 2B" in app_js
    assert "save_endpoint" in app_js
    assert "does not save this candidate automatically" in app_js
    assert "No persistence, no runtime write, and no automatic skill creation." in app_js
    assert "Save Candidate" not in app_js
    assert "Confirm Local Save" not in app_js
    assert "Git Bash" in app_js
    assert "PowerShell" in app_js
    assert "Copy Git Bash" in app_js
    assert "Copy PowerShell" in app_js
    assert "aria-label" in app_js
    assert ">Run<" not in app_js
    assert ">Execute<" not in app_js
    assert ">Start<" not in app_js
    assert "http://" not in app_js
    assert "https://" not in app_js
    assert "cdn" not in app_js.lower()
    assert "child_process" not in app_js
    assert "exec(" not in app_js
    assert "spawn(" not in app_js

    styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
    assert "voice-inbox-layout" in styles
    assert "voice-candidate-card" in styles
    assert "voice-unknown-guidance" in styles
    assert "suggestion-action-panel" in styles
    assert "suggestion-actions" in styles
    assert "handoff-hint" in styles
    assert "overview-card" in styles
    assert "overview-list" in styles
    assert "overview-badge" in styles
    assert "normalized-overview-item" in styles
    assert "memory-candidate-card" in styles
    assert "memory-preview-card" in styles
    assert "codex-review-card" in styles
    assert "codex-review-safety-grid" in styles
    assert "secondary-action" in styles
    assert "http://" not in styles
    assert "https://" not in styles

    assert handle_get_api("/api/missing")[0] == HTTPStatus.NOT_FOUND
    assert handle_post_api("/api/missing", {})[0] == HTTPStatus.NOT_FOUND
    assert handle_post_api(CODEX_REVIEW_PREVIEW_ENDPOINT, {})[0] == HTTPStatus.BAD_REQUEST
    assert parse_json_body(b"{not json")[0] == HTTPStatus.BAD_REQUEST

    source = Path(__file__).read_text(encoding="utf-8")
    forbidden_source_patterns = (
        "shell" + "=True",
        "os." + "system",
        "git" + " add",
        "git" + " commit",
        "git" + " push",
        "git" + " checkout",
        "git" + " reset",
        "git" + " clean",
        "git" + " rm",
        "git" + " stash",
        "git" + " tag",
        "git" + " merge",
        "git" + " rebase",
        "invoke-" + "webrequest",
        "invoke-" + "restmethod",
    )
    assert all(pattern not in source for pattern in forbidden_source_patterns)
    assert ("shell" + "=True") not in source
    assert "READ_ONLY_GIT_COMMANDS" in source
    assert "run_read_only_git" in source
    assert inspect.getsource(run_server).count(DEFAULT_HOST) >= 1
    print("Jarvis Console browser shell self-test passed")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Jarvis Console local browser shell.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Local port to bind on 127.0.0.1.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    parser.add_argument("--self-test", action="store_true", help="Run self-tests without opening the server.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.self_test:
        run_self_test()
        return
    run_server(args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
