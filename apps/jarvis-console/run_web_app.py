"""Local browser shell for Jarvis Console v0.1."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from subprocess import CalledProcessError, TimeoutExpired, run as run_process
from typing import Any
from urllib.parse import parse_qs, urlparse
import webbrowser


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
    ("리뷰", "review"),
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
)
VOICE_HERMES_BROAD_HITS = {"git", "pr", "repo", "review", "리뷰"}
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
    return cleaned.strip()


def voice_suggest_skill(cleaned_transcript: str) -> dict[str, Any]:
    """Reuse skill routing with a conservative filter for voice-review ambiguity."""

    suggestion = suggest_skill(cleaned_transcript)
    if suggestion.get("recommended_skill") != "hermes_manager":
        return suggestion

    normalized = normalize_message(cleaned_transcript)
    matched_keywords = {normalize_message(keyword) for keyword in suggestion.get("matched_keywords", [])}
    has_hermes_context = any(voice_has_context_term(normalized, term) for term in VOICE_HERMES_CONTEXT_TERMS)
    broad_hits_only = matched_keywords and matched_keywords.issubset(VOICE_HERMES_BROAD_HITS)
    if broad_hits_only and not has_hermes_context:
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
        if path not in {"/api/suggest-skill", "/api/voice-inbox/prepare"}:
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
    assert clean_voice_transcript("고깃집 리뷰 정리해줘") == "고깃집 review 정리해줘"
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
    assert "고git" not in voice_restaurant["cleaned_transcript"]
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

    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "Chat / Command" in html
    assert "Voice Inbox" in html
    assert "Skills" in html
    assert "Hermes Manager" in html
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
    assert "Read-only operations dashboard" in html
    assert "does not create tasks" in html
    assert "does not create commits" in html

    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "fetch(" in app_js
    assert "/api/status" in app_js
    assert "/api/skill" in app_js
    assert "/api/overview" in app_js
    assert "/api/history" in app_js
    assert "/api/voice-inbox/prepare" in app_js
    assert "renderOverview" in app_js
    assert "renderHistory" in app_js
    assert "renderRecentCommits" in app_js
    assert "renderVoiceCandidate" in app_js
    assert "prepareVoiceCandidate" in app_js
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
    assert "navigator.clipboard.writeText" in app_js
    assert "copy-command" in app_js
    assert "copy-text" in app_js
    assert "Copy Cleaned Task" in app_js
    assert "Copy As Jarvis Command" in app_js
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
    assert "suggestion-action-panel" in styles
    assert "suggestion-actions" in styles
    assert "handoff-hint" in styles
    assert "overview-card" in styles
    assert "overview-list" in styles
    assert "overview-badge" in styles
    assert "normalized-overview-item" in styles
    assert "secondary-action" in styles
    assert "http://" not in styles
    assert "https://" not in styles

    assert handle_get_api("/api/missing")[0] == HTTPStatus.NOT_FOUND
    assert handle_post_api("/api/missing", {})[0] == HTTPStatus.NOT_FOUND
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
