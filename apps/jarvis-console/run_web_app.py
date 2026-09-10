"""Local browser shell for Jarvis Console v0.1."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
import hashlib
import hmac
import inspect
import json
import os
import re
import secrets
import sys
import tempfile
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from subprocess import CalledProcessError, TimeoutExpired, run as run_process
from typing import Any
from urllib.parse import parse_qs, urlparse
import webbrowser

from owner_decision import owner_decision_to_dict
from owner_decision_data import OwnerDecisionDataError, build_owner_decision_from_snapshot
from recent_milestone_evidence import (
    RecentMilestoneEvidenceError,
    parse_recent_milestone_log,
    recent_milestone_evidence_to_dict,
)
# The deleted codex_review adapter used to be what put hermes-manager-pilot on
# sys.path; director and manager reporting import from it too, so the path
# setup belongs here rather than inside any one feature's module (task-0073).
HERMES_APP_ROOT = Path(__file__).resolve().parent.parent / "hermes-manager-pilot"
if str(HERMES_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_APP_ROOT))

from hermes_manager_pilot.director_reporting import (  # noqa: E402
    DirectorReportingError,
    build_director_report,
    director_report_projection,
)
from hermes_manager_pilot.manager_reporting_data import (  # noqa: E402
    ManagerReportingDataError,
    build_manager_report_from_checkpoint_sources,
    manager_report_projection,
)


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
WEB_ROOT = APP_ROOT / "web"
REGISTRY_PATH = APP_ROOT / "skills.json"
MASTER_PLAN_PATH = REPO_ROOT / "docs" / "master-plan.md"
DISCORD_INTAKE_ROOT = REPO_ROOT / "orchestrator" / "discord-intake"
if str(DISCORD_INTAKE_ROOT) not in sys.path:
    sys.path.insert(0, str(DISCORD_INTAKE_ROOT))

from task_file_writer import (  # noqa: E402
    TASK_ALLOWED_METADATA,
    TASK_ALLOWED_STATUSES,
    TASK_FILE_PATTERN,
    CompletionEvidenceWriteResult,
    TaskStatusTransitionResult,
    preview_task_file_write,
    record_task_completion_evidence,
    transition_task_file_status,
    write_task_file,
)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8790
MAX_JSON_BODY_BYTES = 64_000
MASTER_PLAN_MAX_BYTES = 128_000
MASTER_PLAN_VALUE_MAX_CHARS = 500
MASTER_PLAN_FIELDS = {
    "Last verified": "last_verified",
    "Verified implementation HEAD": "verified_implementation_head",
    "Branch": "branch",
    "Known protected untracked file": "known_protected_untracked_file",
    "Current goal": "current_goal",
    "Manager reporting milestone ID": "manager_reporting_milestone_id",
    "Manager reporting status": "manager_reporting_status",
    "Manager reporting next package ID": "manager_reporting_next_package_id",
    "Current workstream": "current_workstream",
    "Current milestone": "current_milestone",
    "Recommended next step": "recommended_next_step",
    "Next user-visible milestone": "next_user_visible_milestone",
    "Current reason": "current_reason",
    "Owner outcome": "owner_outcome",
    "Recent completed": "recent_completed",
    "Approval state": "approval_state",
    "Approval note": "approval_note",
    "Owner decision status": "owner_decision_status",
    "Owner decision recommendation": "owner_decision_recommended_workstream_id",
}
MASTER_PLAN_APPROVAL_STATES = frozenset({"none", "required", "blocked"})
MASTER_PLAN_MANAGER_REPORTING_STATUSES = frozenset(
    {"in_progress", "milestone_complete", "blocked"}
)
MASTER_PLAN_WORKSTREAM_COLUMNS = (
    "작업 축",
    "현재 상태",
    "사용자에게 보이는 기능",
    "다음 안전 단계",
)
MASTER_PLAN_MANAGER_PACKAGE_COLUMNS = (
    "Work package",
    "Result type",
    "Summary",
    "Commit",
)
MASTER_PLAN_MANAGER_RESULT_TYPES = frozenset(
    {"design", "implementation", "review", "commit", "blocked"}
)
MASTER_PLAN_MANAGER_PACKAGE_MAX_COUNT = 16
MASTER_PLAN_WORKSTREAMS = (
    ("hermes-manager", "Hermes Manager"),
    ("memory-skills", "Memory / Skills"),
    ("jarvis-console", "Jarvis Console"),
    ("research-council", "Research Council"),
    ("daily-ai-radar", "Daily AI Radar"),
    ("task-discord-dashboard", "Task / Discord / Dashboard"),
)
PROJECT_CONTROL_FORBIDDEN_ACTIONS = (
    "Jarvis Console does not invoke Codex, ChatGPT, or Hermes",
    "Jarvis Console does not stage, commit, push, or create PRs",
    "External API, LLM, or credential access",
    "Memory save, Voice Inbox auto-save, or saved-candidate actions",
)
PROJECT_CONTROL_VALIDATION_COMMANDS = (
    "git status --short",
    "git diff --check",
)
RECENT_MILESTONE_GIT_COMMAND = (
    "log",
    "-n",
    "5",
    "--format=%x1e%H%x1f%s",
    "--name-only",
)
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
TASK_VIEW_REQUIRED_FIELDS = (
    "id",
    "title",
    "status",
    "repo",
    "created_at",
    "updated_at",
    "summary",
)
TASK_VIEW_OPTIONAL_TEXT_FIELDS = frozenset(
    {
        "completion_evidence",
        "source_command",
        "execution_request",
        "execution_result",
        "execution_summary",
    }
)
TASK_VIEW_OPTIONAL_BOOLEAN_FIELDS = frozenset(
    {"execution_candidate", "executed", "success", "dry_run"}
)
TASK_VIEW_OPTIONAL_TIMESTAMP_FIELDS = frozenset({"execution_updated_at"})
TASK_VIEW_ALLOWED_FIELDS = frozenset(TASK_VIEW_REQUIRED_FIELDS).union(
    TASK_VIEW_OPTIONAL_TEXT_FIELDS,
    TASK_VIEW_OPTIONAL_BOOLEAN_FIELDS,
    TASK_VIEW_OPTIONAL_TIMESTAMP_FIELDS,
)
TASK_VIEW_METADATA_PATTERN = re.compile(
    r"^- (?P<field>[a-z][a-z0-9_]*): `(?P<value>[^`\r\n]*)`$"
)
TASK_VIEW_ID_PATTERN = re.compile(
    r"^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$"
)
TASK_VIEW_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M UTC"
TASK_VIEW_GROUPS = (
    ("metadata_review", "Needs metadata review"),
    ("needs_attention", "Needs attention"),
    ("in_progress", "In progress"),
    ("ready", "Ready"),
    ("completed", "Completed"),
)
TASK_VIEW_STATUS_RULES = {
    "NEEDS_APPROVAL": (
        "needs_attention",
        10,
        "Review the summary and make the required decision outside Jarvis Console.",
    ),
    "BLOCKED": (
        "needs_attention",
        20,
        "Review the summary and clear the blocker outside Jarvis Console.",
    ),
    # task-0098: ON_HOLD became the seventh official status by owner decision
    # (task-0041, 2026-08-28). The model, the template and task_file_writer all
    # took it; this table was written before that and did not, so a Task using
    # the documented vocabulary failed closed here as invalid_status. It waits
    # on an owner call like NEEDS_APPROVAL and BLOCKED do, and ranks after
    # BLOCKED because the pause is already deliberate.
    "ON_HOLD": (
        "needs_attention",
        25,
        "Review the summary and make the required decision outside Jarvis Console.",
    ),
    "FAILED": (
        "needs_attention",
        30,
        "Review the summary and decide the recovery outside Jarvis Console.",
    ),
    "DOING": (
        "in_progress",
        40,
        "Continue the work described in the summary outside Jarvis Console.",
    ),
    "TODO": (
        "ready",
        50,
        "Decide whether to start this task outside Jarvis Console.",
    ),
    "DONE": (
        "completed",
        60,
        "No next action is required.",
    ),
}
TASK_VIEW_REASON_CODES = frozenset(
    {
        "missing_field",
        "duplicate_field",
        "unsupported_field",
        "invalid_id",
        "id_path_mismatch",
        "invalid_status",
        "invalid_updated_at",
        "invalid_text",
        "field_too_long",
    }
)
HISTORY_MAX_COMMITS = 10
HISTORY_DIRECTORY_KEYS = ("docs", "jarvis_console", "hermes_examples", "daily_ai_radar_examples")
HISTORY_NAME_MARKERS = ("checkpoint", "summary", "report")
VOICE_INBOX_MAX_TRANSCRIPT_CHARS = 8000
VOICE_INBOX_TITLE_MAX_CHARS = 120
VOICE_INBOX_SUMMARY_MAX_CHARS = 280
CREATE_LOCAL_TASK_PRODUCT_NAME = "Create Local Task"
CREATE_LOCAL_TASK_PREVIEW_ENDPOINT = "/api/create-local-task/preview"
CREATE_LOCAL_TASK_CONFIRM_ENDPOINT = "/api/create-local-task/confirm"
CREATE_LOCAL_TASK_CONFIRMATION_LITERAL = "CREATE LOCAL TASK"
CREATE_LOCAL_TASK_STATUS = "TODO"
CREATE_LOCAL_TASK_REPO = "jarvis-core"
CREATE_LOCAL_TASK_STORAGE_ROOT = "memory/tasks"
CREATE_LOCAL_TASKS_DIR = REPO_ROOT / "memory" / "tasks"
CREATE_LOCAL_TASK_TOKEN_TTL_SECONDS = 10 * 60
CREATE_LOCAL_TASK_TOKEN_CAPACITY = 128
CREATE_LOCAL_TASK_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{24,128}$")
CREATE_LOCAL_TASK_ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/json; charset=utf-8",
}
CREATE_LOCAL_TASK_REQUIRED_HEADERS = (
    "host",
    "origin",
    "content-type",
    "content-length",
)
TASK_TRANSITION_PRODUCT_NAME = "Start / Complete Task"
TASK_TRANSITION_PREVIEW_ENDPOINT = "/api/task-transition/preview"
TASK_TRANSITION_CONFIRM_ENDPOINT = "/api/task-transition/confirm"
TASK_TRANSITION_ACTIONS = {
    "start": ("TODO", "DOING", "START TASK"),
    "complete": ("DOING", "DONE", "COMPLETE TASK"),
}
TASK_TRANSITION_COMPLETE_WARNING = (
    "Confirm Complete only if verification evidence is already recorded. "
    "Jarvis does not evaluate whether verification evidence exists or infer "
    "completion from task content or summary."
)
TASK_TRANSITION_NOTICE = (
    "This changes only status and updated_at. It does not execute the task."
)
TASK_TRANSITION_TOKEN_TTL_SECONDS = 10 * 60
TASK_TRANSITION_TOKEN_CAPACITY = 128
TASK_TRANSITION_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{24,128}$")
COMPLETION_EVIDENCE_PRODUCT_NAME = "Record Completion Evidence"
COMPLETION_EVIDENCE_PREVIEW_ENDPOINT = "/api/completion-evidence/preview"
COMPLETION_EVIDENCE_CONFIRM_ENDPOINT = "/api/completion-evidence/confirm"
COMPLETION_EVIDENCE_CONFIRMATION_LITERAL = "RECORD EVIDENCE"
COMPLETION_EVIDENCE_TOKEN_TTL_SECONDS = 10 * 60
COMPLETION_EVIDENCE_TOKEN_CAPACITY = 128
COMPLETION_EVIDENCE_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{24,128}$")
COMPLETION_EVIDENCE_NOTICE = (
    "This appends completion_evidence once and updates only updated_at. "
    "It does not validate the evidence, change status, complete, or execute the Task."
)
COMPLETION_EVIDENCE_RECOMMENDATION = (
    "Review the recorded evidence, then use Complete separately when the Task is ready."
)
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
# task-0126: historical evidence is verified by asking whether a recorded
# commit is part of this branch history, not by asking whether it is recent.
# This is the only allowlisted command that takes an argument, so its shape
# is fixed and the single variable is constrained to an abbreviated or full
# lowercase hash. Abbreviated values are allowed because
# verified_implementation_head has always accepted them.
ANCESTRY_GIT_COMMAND_PREFIX = ("merge-base", "--is-ancestor")
HISTORICAL_COMMIT_PATTERN = re.compile(r"[0-9a-f]{7,40}")
READ_ONLY_GIT_COMMANDS = {
    ("rev-parse", "--show-toplevel"),
    ("rev-parse", "--abbrev-ref", "HEAD"),
    ("rev-parse", "HEAD"),
    ("status", "--short"),
    ("status", "--short", "--untracked-files=all"),
    ("log", "--oneline", "-n", "10"),
    RECENT_MILESTONE_GIT_COMMAND,
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
            "Task discovery and basic details are read-only. Create Local Task creates one local TODO from Voice Inbox; Start / Complete changes only status and updated_at; Record Completion Evidence appends one evidence value and updates only updated_at for an eligible DOING Task. Every Task preview remains write-free. Every write requires Preview and explicit Confirm. Evidence is not validated, status stays DOING, and no flow executes or automatically completes Task work. Jarvis does not create approvals or reports, run skills, commit, push, or make external calls.",
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

    if args in READ_ONLY_GIT_COMMANDS:
        return
    if (
        len(args) == 4
        and tuple(args[:2]) == ANCESTRY_GIT_COMMAND_PREFIX
        and HISTORICAL_COMMIT_PATTERN.fullmatch(args[2])
        and args[3] == "HEAD"
    ):
        return
    raise RegistryError("git command is not allowed for read-only overview")


def run_read_only_git(
    args: tuple[str, ...],
    *,
    preserve_record_separators: bool = False,
) -> str:
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
        raise RegistryError(f"read-only Git command failed: {exc}") from exc
    if preserve_record_separators:
        return result.stdout.rstrip("\r\n")
    return result.stdout.rstrip("\r\n")


def commit_is_branch_ancestor(commit: str, *, _run: Any = run_process) -> bool:
    """Return whether one recorded commit is part of the current history.

    A commit that does not resolve and a commit that resolves but sits on
    another line of history both answer False, so recorded evidence that
    never existed is refused rather than merely reported as old. Only a
    broken Git invocation raises, matching run_read_only_git.
    """

    if not isinstance(commit, str) or not HISTORICAL_COMMIT_PATTERN.fullmatch(commit):
        return False
    args = (*ANCESTRY_GIT_COMMAND_PREFIX, commit, "HEAD")
    validate_read_only_git_args(args)
    try:
        result = _run(
            ["git", *args],
            cwd=REPO_ROOT,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (TimeoutExpired, OSError) as exc:
        raise RegistryError(f"read-only Git command failed: {exc}") from exc
    # 0 is an ancestor, 1 is a resolvable commit outside this history, and
    # 128 is a value Git cannot resolve at all. Every other code means the
    # question was not answered, so it fails closed instead of passing.
    if result.returncode == 0:
        return True
    if result.returncode in {1, 128}:
        return False
    raise RegistryError("read-only Git ancestry check failed")


def historical_commit_ancestry(commits: list[str]) -> dict[str, bool]:
    """Answer the ancestry question once per distinct recorded commit."""

    answers: dict[str, bool] = {}
    for commit in commits:
        if not isinstance(commit, str) or not commit or commit in answers:
            continue
        answers[commit] = commit_is_branch_ancestor(commit)
    return answers


def repo_status_payload() -> dict[str, Any]:
    """Return read-only repository status for the overview dashboard."""

    head = run_read_only_git(("rev-parse", "HEAD"))
    working_tree_status = run_read_only_git(("status", "--short", "--untracked-files=all"))
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


def recent_milestone_evidence_payload(repo: Mapping[str, Any]) -> dict[str, object]:
    """Collect bounded local Git metadata for the read-only owner dashboard."""

    observed_head = str(repo.get("head") or "")
    raw_log = run_read_only_git(
        RECENT_MILESTONE_GIT_COMMAND,
        preserve_record_separators=True,
    )
    try:
        evidence = parse_recent_milestone_log(raw_log, observed_head)
    except RecentMilestoneEvidenceError as exc:
        raise RegistryError(f"recent milestone evidence is unavailable: {exc}") from exc
    return recent_milestone_evidence_to_dict(evidence)


def reconcile_project_control_reporting_state(
    base_attention_reasons: list[str],
    manager_report: Mapping[str, Any],
    director_report: Mapping[str, Any],
) -> tuple[str, list[str]]:
    """Align the outer project card with canonical reporting state."""

    manager_status = str(manager_report.get("status") or "")
    director_status = str(director_report.get("status") or "")
    manager_owner_action = str(manager_report.get("owner_action") or "")
    director_owner_action = str(director_report.get("owner_action") or "")
    manager_owner_decision = str(manager_report.get("owner_decision") or "")
    director_owner_decision = str(director_report.get("owner_decision") or "")
    if manager_status != director_status:
        raise RegistryError("Manager and Director reporting status disagree")
    if manager_owner_action != director_owner_action:
        raise RegistryError("Manager and Director owner action disagree")
    if manager_owner_decision != director_owner_decision:
        raise RegistryError("Manager and Director owner decision disagree")
    if manager_owner_action == "decision_required":
        if not manager_owner_decision:
            raise RegistryError(
                "Manager and Director decision state requires a decision"
            )
    elif manager_owner_action == "none":
        if manager_owner_decision:
            raise RegistryError(
                "Manager and Director no-action state requires empty decisions"
            )
    else:
        raise RegistryError("Manager and Director owner action is invalid")

    source_conflicts = manager_report.get("source_conflicts")
    if not isinstance(source_conflicts, list) or not all(
        isinstance(item, str) and item for item in source_conflicts
    ):
        raise RegistryError("Manager Report source conflicts are invalid")
    if source_conflicts and (
        manager_status != "blocked"
        or manager_owner_action != "decision_required"
    ):
        raise RegistryError(
            "Manager Report source conflicts require blocked decision state"
        )

    visible_reasons = []
    for reason in (*base_attention_reasons, *source_conflicts):
        if reason not in visible_reasons:
            visible_reasons.append(reason)
    if manager_owner_action == "decision_required" and not visible_reasons:
        visible_reasons.append(manager_owner_decision)

    needs_attention = (
        bool(visible_reasons)
        or manager_status == "blocked"
        or manager_owner_action == "decision_required"
    )
    return ("attention" if needs_attention else "observed"), visible_reasons


def _parse_master_plan_table_row(line: str) -> list[str]:
    """Normalize one bounded four-cell master-plan table row."""

    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise RegistryError("master plan workstream table row is malformed")
    raw_cells = stripped[1:-1].split("|")
    if len(raw_cells) != len(MASTER_PLAN_WORKSTREAM_COLUMNS):
        raise RegistryError("master plan workstream table must have four columns")

    cells = []
    for raw_cell in raw_cells:
        if any(ord(character) < 32 or ord(character) == 127 for character in raw_cell):
            raise RegistryError("master plan workstream table contains a control character")
        normalized = raw_cell.strip().replace("`", "").replace("**", "")
        if not normalized or len(normalized) > MASTER_PLAN_VALUE_MAX_CHARS:
            raise RegistryError("master plan workstream table cell is empty or too long")
        cells.append(normalized)
    return cells


def _parse_master_plan_workstreams(text: str) -> list[dict[str, Any]]:
    """Read the fixed Jarvis-Core workstream table without inferring authority."""

    section_match = re.search(
        r"(?ms)^## 5\. 작업 축별 상태\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        text,
    )
    if section_match is None:
        raise RegistryError("master plan workstream section is missing")

    table_lines = [
        line.strip()
        for line in section_match.group("body").splitlines()
        if line.strip().startswith("|")
    ]
    expected_line_count = 2 + len(MASTER_PLAN_WORKSTREAMS)
    if len(table_lines) != expected_line_count:
        raise RegistryError("master plan workstream table has missing or extra rows")

    if tuple(_parse_master_plan_table_row(table_lines[0])) != MASTER_PLAN_WORKSTREAM_COLUMNS:
        raise RegistryError("master plan workstream table header is invalid")
    separator_cells = table_lines[1][1:-1].split("|")
    if len(separator_cells) != len(MASTER_PLAN_WORKSTREAM_COLUMNS) or any(
        re.fullmatch(r"\s*:?-{3,}:?\s*", cell) is None for cell in separator_cells
    ):
        raise RegistryError("master plan workstream table separator is invalid")

    workstreams = []
    seen_names = set()
    for (workstream_id, expected_name), line in zip(
        MASTER_PLAN_WORKSTREAMS,
        table_lines[2:],
        strict=True,
    ):
        display_name, status_summary, user_visible_capability, next_safe_step = (
            _parse_master_plan_table_row(line)
        )
        if display_name in seen_names:
            raise RegistryError(f"master plan workstream is duplicated: {display_name}")
        seen_names.add(display_name)
        if display_name != expected_name:
            raise RegistryError(
                "master plan workstream order or name is invalid: "
                f"expected {expected_name!r}"
            )
        workstreams.append(
            {
                "workstream_id": workstream_id,
                "display_name": display_name,
                "status_summary": status_summary,
                "user_visible_capability": user_visible_capability,
                "next_safe_step": next_safe_step,
                "read_only": True,
            }
        )
    return workstreams


def _parse_master_plan_manager_packages(text: str) -> list[dict[str, str]]:
    """Parse the bounded Manager Reporting package checkpoint table."""

    section_match = re.search(
        (
            r"(?ms)^### Manager Reporting Workflow v0\.1 package evidence\s*$"
            r"\n(?P<body>.*?)(?=^###?\s|\Z)"
        ),
        text,
    )
    if section_match is None:
        raise RegistryError("master plan Manager Reporting package section is missing")
    table_lines = [
        line.strip()
        for line in section_match.group("body").splitlines()
        if line.strip().startswith("|")
    ]
    if not 3 <= len(table_lines) <= 2 + MASTER_PLAN_MANAGER_PACKAGE_MAX_COUNT:
        raise RegistryError(
            "master plan Manager Reporting package table is empty or too large"
        )
    if (
        tuple(_parse_master_plan_table_row(table_lines[0]))
        != MASTER_PLAN_MANAGER_PACKAGE_COLUMNS
    ):
        raise RegistryError("master plan Manager Reporting package header is invalid")
    separator_cells = table_lines[1][1:-1].split("|")
    if len(separator_cells) != len(MASTER_PLAN_MANAGER_PACKAGE_COLUMNS) or any(
        re.fullmatch(r"\s*:?-{3,}:?\s*", cell) is None for cell in separator_cells
    ):
        raise RegistryError(
            "master plan Manager Reporting package separator is invalid"
        )

    packages = []
    seen_ids = set()
    for index, line in enumerate(table_lines[2:]):
        package_id, result_type, summary, commit_hash = (
            _parse_master_plan_table_row(line)
        )
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", package_id) is None:
            raise RegistryError(
                f"master plan Manager Reporting package ID is invalid at row {index}"
            )
        if package_id in seen_ids:
            raise RegistryError(
                f"master plan Manager Reporting package is duplicated: {package_id}"
            )
        seen_ids.add(package_id)
        if result_type not in MASTER_PLAN_MANAGER_RESULT_TYPES:
            raise RegistryError(
                f"master plan Manager Reporting result type is invalid: {result_type}"
            )
        if re.fullmatch(r"[0-9a-f]{40}", commit_hash) is None:
            raise RegistryError(
                f"master plan Manager Reporting commit is invalid: {package_id}"
            )
        packages.append(
            {
                "work_package_id": package_id,
                "result_type": result_type,
                "summary": summary,
                "commit_hash": commit_hash,
            }
        )
    return packages


def read_master_plan_snapshot(
    path: str | Path = MASTER_PLAN_PATH,
    allowed_root: str | Path = REPO_ROOT,
) -> dict[str, Any]:
    """Read bounded owner-facing fields from the trusted master plan."""

    source = Path(path)
    root = Path(allowed_root).resolve()
    try:
        resolved = source.resolve(strict=True)
    except OSError as exc:
        raise RegistryError(f"master plan is unavailable: {exc}") from exc
    if source.is_symlink() or not resolved.is_file() or not resolved.is_relative_to(root):
        raise RegistryError("master plan must be a regular file inside the trusted root")
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise RegistryError(f"master plan could not be read: {exc}") from exc
    if len(raw) > MASTER_PLAN_MAX_BYTES:
        raise RegistryError("master plan exceeds the read-only display limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RegistryError("master plan must be valid UTF-8") from exc

    section_match = re.search(
        r"(?ms)^## 2\. 현재 기준점\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        text,
    )
    if section_match is None:
        raise RegistryError("master plan current-baseline section is missing")

    values: dict[str, str] = {}
    for line in section_match.group("body").splitlines():
        if not line.startswith("- ") or ":" not in line:
            continue
        label, value = line[2:].split(":", 1)
        key = MASTER_PLAN_FIELDS.get(label.strip())
        if key is None:
            continue
        if key in values:
            raise RegistryError(f"master plan field is duplicated: {label.strip()}")
        normalized = value.strip().replace("`", "").replace("**", "")
        if not normalized or len(normalized) > MASTER_PLAN_VALUE_MAX_CHARS:
            raise RegistryError(f"master plan field is empty or too long: {label.strip()}")
        values[key] = normalized

    missing = sorted(set(MASTER_PLAN_FIELDS.values()) - set(values))
    if missing:
        raise RegistryError("master plan fields are missing: " + ", ".join(missing))
    if values["approval_state"] not in MASTER_PLAN_APPROVAL_STATES:
        raise RegistryError("master plan approval state is invalid")
    if (
        values["manager_reporting_status"]
        not in MASTER_PLAN_MANAGER_REPORTING_STATUSES
    ):
        raise RegistryError("master plan Manager Reporting status is invalid")
    for field in (
        "manager_reporting_milestone_id",
        "manager_reporting_next_package_id",
    ):
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", values[field]) is None:
            raise RegistryError(f"master plan field is not a normalized ID: {field}")
    values["workstreams"] = _parse_master_plan_workstreams(text)
    values["manager_reporting_work_packages"] = (
        _parse_master_plan_manager_packages(text)
    )
    values["source"] = resolved.relative_to(root).as_posix()
    return values


def project_control_payload(repo: Mapping[str, Any]) -> dict[str, Any]:
    """Build one write-free owner project card from master-plan and Git metadata."""

    snapshot = read_master_plan_snapshot()
    try:
        owner_decision = build_owner_decision_from_snapshot(snapshot)
    except OwnerDecisionDataError as exc:
        raise RegistryError(f"owner decision is unavailable: {exc}") from exc
    recent_milestone_evidence = recent_milestone_evidence_payload(repo)
    expected_branch = snapshot["branch"]
    live_branch = str(repo.get("branch") or "unknown")
    attention_reasons = []
    if live_branch != expected_branch:
        attention_reasons.append(
            f"Live branch {live_branch!r} does not match master-plan branch {expected_branch!r}."
        )
    if not recent_milestone_evidence["head_matches_latest_commit"]:
        attention_reasons.append(
            "Recent milestone evidence does not match the live repository HEAD."
        )
    if any(
        bool(commit.get("protected_path_present"))
        for commit in recent_milestone_evidence["commits"]
        if isinstance(commit, Mapping)
    ):
        attention_reasons.append(
            "A recent commit includes protected path jarvis.bat."
        )
    working_tree_status = str(repo.get("working_tree_status") or "clean")
    live_status_lines = (
        []
        if working_tree_status == "clean"
        else [line for line in working_tree_status.splitlines() if line]
    )
    manager_risks = [
        {
            "severity": "low",
            "category": "manual_handoff",
            "summary": (
                "Codex handoff remains explicit and copy-only; no automatic "
                "invocation or background worker exists."
            ),
        }
    ]
    manager_risks.extend(
        {
            "severity": "blocking",
            "category": "project_control_attention",
            "summary": reason,
        }
        for reason in attention_reasons
    )
    try:
        manager_report = build_manager_report_from_checkpoint_sources(
            master_plan_snapshot=snapshot,
            live_git_evidence={
                "branch": live_branch,
                "head": str(repo.get("head") or ""),
                "status": live_status_lines,
                "recent_commit_hashes": [
                    str(commit.get("hash") or "")
                    for commit in recent_milestone_evidence["commits"]
                    if isinstance(commit, Mapping)
                ],
                # task-0126: the display list above answers "what happened
                # recently". These answer "is this recorded commit real and
                # part of this branch", which is what historical evidence
                # actually claims and what stays true as history grows.
                "historical_commit_ancestry": historical_commit_ancestry(
                    [
                        snapshot["verified_implementation_head"],
                        *[
                            str(package.get("commit_hash") or "")
                            for package in snapshot[
                                "manager_reporting_work_packages"
                            ]
                            if isinstance(package, Mapping)
                        ],
                    ]
                ),
            },
            risks=manager_risks,
        )
    except ManagerReportingDataError as exc:
        raise RegistryError(f"Manager Report is unavailable: {exc}") from exc
    try:
        director_report = build_director_report(manager_report)
    except DirectorReportingError as exc:
        raise RegistryError(f"Director Report is unavailable: {exc}") from exc
    manager_report_payload = manager_report_projection(manager_report)
    director_report_payload = director_report_projection(director_report)
    project_status, visible_attention_reasons = (
        reconcile_project_control_reporting_state(
            attention_reasons,
            manager_report_payload,
            director_report_payload,
        )
    )
    return {
        "version": "project_control.v0.1F",
        "mode": "read-only",
        "source": snapshot["source"],
        "project_cards": [
            {
                "project_id": "jarvis-core",
                "display_name": "Jarvis-Core",
                "status": project_status,
                "branch": live_branch,
                "live_head": str(repo.get("head_short") or "unknown"),
                "verified_implementation_head": snapshot["verified_implementation_head"],
                "working_tree_status": str(repo.get("working_tree_status") or "unknown"),
                "last_verified": snapshot["last_verified"],
                "known_protected_untracked": [snapshot["known_protected_untracked_file"]],
                "current_goal": (
                    "Develop Jarvis-Core as a local-first, human-approved, "
                    "skill-based personal AI assistant."
                ),
                "current_workstream": snapshot["current_workstream"],
                "current_milestone": snapshot["current_milestone"],
                "recommended_next_step": snapshot["recommended_next_step"],
                "next_user_visible_milestone": snapshot["next_user_visible_milestone"],
                "owner_summary": {
                    "current_reason": snapshot["current_reason"],
                    "owner_outcome": snapshot["owner_outcome"],
                    "recent_completed": snapshot["recent_completed"],
                    "current_milestone": snapshot["current_milestone"],
                    "recommended_next_step": snapshot["recommended_next_step"],
                    "next_user_visible_milestone": snapshot["next_user_visible_milestone"],
                    "approval_state": snapshot["approval_state"],
                    "approval_note": snapshot["approval_note"],
                },
                "workstreams": snapshot["workstreams"],
                "director_report": director_report_payload,
                "manager_report": manager_report_payload,
                "owner_decision": owner_decision_to_dict(owner_decision),
                "recent_milestone_evidence": recent_milestone_evidence,
                "locked_capabilities": list(PROJECT_CONTROL_FORBIDDEN_ACTIONS),
                "validation_commands": list(PROJECT_CONTROL_VALIDATION_COMMANDS),
                "forbidden_actions": list(PROJECT_CONTROL_FORBIDDEN_ACTIONS),
                "attention_reasons": visible_attention_reasons,
            }
        ],
        "notes": [
            "The project card is reconstructed from tracked master-plan fields and fixed read-only Git commands.",
            "It does not create tasks, approvals, prompts, commits, runtime state, or cross-app calls.",
            "Project Control exposes one Jarvis-Core card and treats apps and capabilities as internal workstreams.",
            "The dormant multi-project registry primitive is not connected to this payload, HTTP, UI, or filesystem access.",
            "The Manager Report is a derived read-only view over tracked Master Plan checkpoints and bounded local Git evidence.",
            "The Director Report is a smaller read-only Owner summary derived only from the Manager Report.",
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


def truncate_overview_text(value: str, max_chars: int) -> str:
    """Return bounded display text for overview titles and summaries."""

    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


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


def discover_recent_items(
    directory_keys: tuple[str, ...],
    name_contains: str = "",
    item_types: set[str] | None = None,
    apply_caps: bool = True,
) -> list[dict[str, Any]]:
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
            item = overview_file_item(path, directory)
            # task-0109: a type filter has to run before the per-directory cap,
            # the way name_contains already does. Applied afterwards it let
            # non-matching files spend cap slots, so a directory holding more
            # than the cap could hide real matches - ten reports on disk showed
            # as eight. Nothing is read twice for this: overview_file_item is
            # already built for every candidate before the cap is applied.
            if item_types is not None and item["item_type"] not in item_types:
                continue
            directory_items.append(item)
        directory_items.sort(key=lambda item: (item["modified"], item["path"]), reverse=True)
        items.extend(
            directory_items[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY]
            if apply_caps
            else directory_items
        )
    # task-0107: the per-directory cap keeps each directory's newest, but the
    # combined list used to be returned in directory order. "Recent" was then
    # not recency-ordered across directories - a file 103 days newer sat below
    # older ones with both times on screen - and the total cap dropped whatever
    # came last rather than whatever was oldest. Worse, the early break could
    # skip a whole directory before its items were ever compared. Sort the
    # combined list before capping, the way project_task_view_items does.
    items.sort(key=lambda item: (item["modified"], item["path"]), reverse=True)
    return items[:OVERVIEW_MAX_TOTAL_ITEMS] if apply_caps else items


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
    # task-0107: same combined ordering rule as discover_recent_items.
    items.sort(key=lambda item: (item["modified"], item["path"]), reverse=True)
    return items[:OVERVIEW_MAX_TOTAL_ITEMS]


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


def invalid_task_view(
    reason_code: str,
    reason_field: str | None = None,
) -> dict[str, Any]:
    """Return one bounded fail-closed task projection without raw file content."""

    assert reason_code in TASK_VIEW_REASON_CODES
    payload: dict[str, Any] = {
        "parse_state": "invalid",
        "group_id": "metadata_review",
        "display_rank": 0,
        "next_action": (
            "Review this task file's metadata outside Jarvis Console."
        ),
        "reason_code": reason_code,
        "read_only": True,
    }
    if (
        reason_field
        and len(reason_field) <= 80
        and re.fullmatch(r"[a-z][a-z0-9_]*", reason_field)
    ):
        payload["reason_field"] = reason_field
    return payload


def normalize_task_view_text(value: str, *, allow_empty: bool) -> str | None:
    """Normalize safe one-line display text deterministically."""

    for character in value:
        if unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}:
            return None
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if not allow_empty and not normalized:
        return None
    return normalized


def parse_task_view_timestamp(value: str) -> datetime | None:
    """Parse one exact minute-resolution UTC task timestamp."""

    try:
        parsed = datetime.strptime(value, TASK_VIEW_TIMESTAMP_FORMAT)
    except ValueError:
        return None
    if parsed.strftime(TASK_VIEW_TIMESTAMP_FORMAT) != value:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def parse_task_view_text(file_name: str, text: str) -> dict[str, Any] | None:
    """Parse one matching Task Markdown file into a bounded read-only view."""

    if file_name == "task-template.md" or not TASK_FILE_PATTERN.fullmatch(file_name):
        return None

    metadata: dict[str, str] = {}
    metadata_line_indexes: dict[str, int] = {}
    # task-0096: metadata is the header block, not every line starting with
    # "- ". The old rule claimed every bullet anywhere in the file, so a task
    # record with an ordinary Markdown list in its body failed closed into
    # metadata review; 35 local Task records did at the time of this fix. It
    # also selected indented bullets that TASK_VIEW_METADATA_PATTERN can never
    # match, because that pattern is anchored at column 0.
    #
    # This is the same boundary task_file_writer._transition_metadata already
    # uses (task-0054). Only the boundary moves here: every field check below
    # is unchanged, and a malformed field inside the block still fails.
    in_header = False
    for line_index, line in enumerate(text.splitlines()):
        # An indented line continues the field above it, so it is neither a
        # metadata line nor a terminator.
        if line[:1].isspace():
            continue
        if not in_header:
            if not line.startswith("- "):
                # Title, HTML comments and blank lines sit above the block.
                continue
            in_header = True
        elif not line.startswith("- "):
            # The first column-0 line that is not a field closes the header
            # block. Everything after it is document body, not task metadata.
            break
        match = TASK_VIEW_METADATA_PATTERN.fullmatch(line)
        if match is None:
            field_match = re.match(r"^\s*- ([a-z][a-z0-9_]*):", line)
            return invalid_task_view(
                "invalid_text",
                field_match.group(1) if field_match else None,
            )
        field_name = match.group("field")
        if field_name not in TASK_VIEW_ALLOWED_FIELDS:
            return invalid_task_view("unsupported_field", field_name)
        if field_name in metadata:
            return invalid_task_view("duplicate_field", field_name)
        metadata[field_name] = match.group("value")
        metadata_line_indexes[field_name] = line_index

    for field_name in TASK_VIEW_REQUIRED_FIELDS:
        if field_name not in metadata:
            return invalid_task_view("missing_field", field_name)

    task_id = metadata["id"]
    if not TASK_VIEW_ID_PATTERN.fullmatch(task_id):
        return invalid_task_view("invalid_id", "id")
    if task_id != PurePosixPath(file_name).stem:
        return invalid_task_view("id_path_mismatch", "id")

    status = metadata["status"]
    status_rule = TASK_VIEW_STATUS_RULES.get(status)
    if status_rule is None:
        return invalid_task_view("invalid_status", "status")
    if (
        "completion_evidence" in metadata
        and metadata_line_indexes["completion_evidence"]
        != metadata_line_indexes["summary"] + 1
    ):
        return invalid_task_view("invalid_text", "completion_evidence")

    for field_name in ("created_at", "updated_at"):
        if parse_task_view_timestamp(metadata[field_name]) is None:
            return invalid_task_view("invalid_updated_at", field_name)

    text_limits = {
        "repo": 80,
        "title": 120,
        "summary": 500,
    }
    normalized_text: dict[str, str] = {}
    for field_name, max_chars in text_limits.items():
        raw_value = metadata[field_name]
        if len(raw_value) > max_chars:
            return invalid_task_view("field_too_long", field_name)
        normalized = normalize_task_view_text(raw_value, allow_empty=False)
        if normalized is None:
            return invalid_task_view("invalid_text", field_name)
        normalized_text[field_name] = normalized

    normalized_optional_text: dict[str, str] = {}
    for field_name in TASK_VIEW_OPTIONAL_TEXT_FIELDS:
        if field_name not in metadata:
            continue
        raw_value = metadata[field_name]
        if len(raw_value) > 500:
            return invalid_task_view("field_too_long", field_name)
        normalized = normalize_task_view_text(raw_value, allow_empty=False)
        if normalized is None:
            return invalid_task_view("invalid_text", field_name)
        normalized_optional_text[field_name] = normalized

    for field_name in TASK_VIEW_OPTIONAL_BOOLEAN_FIELDS:
        if field_name in metadata and metadata[field_name] not in {"true", "false"}:
            return invalid_task_view("invalid_text", field_name)

    for field_name in TASK_VIEW_OPTIONAL_TIMESTAMP_FIELDS:
        if (
            field_name in metadata
            and metadata[field_name]
            and parse_task_view_timestamp(metadata[field_name]) is None
        ):
            return invalid_task_view("invalid_updated_at", field_name)

    group_id, display_rank, next_action = status_rule
    return {
        "parse_state": "valid",
        "id": task_id,
        "title": normalized_text["title"],
        "status": status,
        "updated_at": metadata["updated_at"],
        "summary": normalized_text["summary"],
        "completion_evidence": normalized_optional_text.get(
            "completion_evidence"
        ),
        "has_completion_evidence": "completion_evidence" in metadata,
        "group_id": group_id,
        "display_rank": display_rank,
        "next_action": next_action,
        "read_only": True,
    }


def task_view_header_block_end(raw: bytes, truncated: bool) -> int | None:
    """Return the byte offset just past the header block, or None if unclosed.

    This is the task-0054 / task-0096 boundary applied to bytes: an indented
    line continues the field above it, the block opens at the first column-0
    "- " line, and the first column-0 line that is not one closes it. Working
    in bytes keeps every offset on a line terminator, and a line terminator is
    always a UTF-8 character boundary, so slicing here can never split a
    multi-byte sequence.
    """

    lines = raw.splitlines(keepends=True)
    if truncated and lines and not lines[-1].endswith((b"\n", b"\r")):
        # A bounded prefix can end mid-line. That fragment says nothing about
        # the field it belongs to, so it is not read as one.
        lines.pop()
    offset = 0
    started = False
    for line in lines:
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
    # A block running to the end of a whole file is closed by the file. One
    # running to the end of a truncated prefix may continue past it, and this
    # read cannot see that far.
    return None if truncated else offset


def read_task_view_text(path: Path) -> str:
    """Read one bounded Task header block as strict UTF-8 without writing state.

    task-0097: OVERVIEW_SNIPPET_BYTES bounds the read, not the file. The old
    rule raised on any file larger than the bound before the parser ever saw
    it, so a task record with a valid header and an ordinary long body failed
    closed into metadata review - 42 local records did at the time of this fix,
    which was every Task the Console displayed, and it also left Start /
    Complete / Record Completion Evidence with no valid Task to select. Only
    the header block is needed here and it sits at the front of the file, so
    the same bounded prefix is read and only that block reaches the parser.

    The bound itself is unchanged: at most OVERVIEW_SNIPPET_BYTES + 1 bytes are
    read, and a header block that does not close inside the prefix still fails
    closed, because nothing here can see whether it continued past the cut.
    """

    with path.open("rb") as file:
        raw = file.read(OVERVIEW_SNIPPET_BYTES + 1)
    truncated = len(raw) > OVERVIEW_SNIPPET_BYTES
    if truncated:
        raw = raw[:OVERVIEW_SNIPPET_BYTES]
    end = task_view_header_block_end(raw, truncated)
    if end is None:
        raise ValueError("task metadata header block exceeds bounded read")
    return raw[:end].decode("utf-8", errors="strict")


def task_view_sort_key(item: Mapping[str, Any]) -> tuple[int, float, str]:
    """Return the frozen display-order key for one projected Task item."""

    task_view = item["task_view"]
    updated_timestamp = 0.0
    if task_view["parse_state"] == "valid":
        parsed = parse_task_view_timestamp(task_view["updated_at"])
        assert parsed is not None
        updated_timestamp = parsed.timestamp()
    return (
        task_view["display_rank"],
        -updated_timestamp,
        item["path"],
    )


def project_task_view_items(
    discovered_items: list[dict[str, Any]],
    *,
    text_reader: Callable[[Path], str] = read_task_view_text,
) -> list[dict[str, Any]]:
    """Project only matching files after existing Recent Tasks selection."""

    projected: list[dict[str, Any]] = []
    for item in discovered_items:
        file_name = PurePosixPath(item["path"]).name
        if file_name == "task-template.md" or not TASK_FILE_PATTERN.fullmatch(
            file_name
        ):
            continue
        try:
            text = text_reader(REPO_ROOT / item["path"])
            task_view = parse_task_view_text(file_name, text)
        except (OSError, UnicodeError, ValueError):
            task_view = invalid_task_view("invalid_text")
        assert task_view is not None
        projected_item = dict(item)
        projected_item["task_view"] = task_view
        projected.append(projected_item)
    projected.sort(key=task_view_sort_key)
    return projected


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
    """Return Project Control discovery and bounded Task transition copy."""

    registry = load_registry()
    repo = repo_status_payload()
    # task-0114: the discovery caps rank by file mtime, and they used to run
    # before any Task status was known, so an old NEEDS_APPROVAL record simply
    # disappeared - six of them plus a DOING record were invisible at the time
    # of this fix while the view showed ten DONE Tasks and "Needs attention:
    # 0". The Task View now sees every candidate and applies its own cap to the
    # projection, so selection follows task_view_sort_key - the display order
    # this view already declares - instead of file recency. The displayed total
    # is unchanged at OVERVIEW_MAX_ITEMS_PER_DIRECTORY, and no status priority
    # is introduced here: project_task_view_items still owns Task semantics and
    # discovery still only supplies candidates.
    task_candidates = discover_recent_items(("memory_tasks",), apply_caps=False)
    # Recent Tasks keeps its own meaning - the newest files by mtime - so it
    # takes the capped prefix of the same candidate list rather than the
    # priority-ordered projection.
    discovered_tasks = task_candidates[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY]
    tasks = project_task_view_items(task_candidates)[
        :OVERVIEW_MAX_ITEMS_PER_DIRECTORY
    ]
    reports = discover_recent_items(
        ("reports", "research_examples", "daily_ai_radar_examples"),
        item_types={"report"},
    )
    checkpoints = discover_recent_items(("hermes_examples", "docs"), name_contains="checkpoint")
    docs_examples = discover_recent_items(
        ("docs", "research_examples", "daily_ai_radar_examples", "hermes_examples", "jarvis_console")
    )
    recent_groups = [
        recent_group(
            "tasks",
            "Recent Tasks",
            "No task index found yet.",
            discovered_tasks,
        ),
        recent_group("reports", "Recent Reports", "No generated reports found yet.", reports),
        recent_group("checkpoints", "Recent Checkpoints", "No checkpoint index found yet.", checkpoints),
        recent_group("docs_examples", "Recent Docs / Examples", "No docs or examples found yet.", docs_examples),
    ]
    return {
        "ok": True,
        "mode": "read-only",
        "repo": repo,
        "project_control": project_control_payload(repo),
        "skills": overview_skills_payload(registry["skills"]),
        "tasks": tasks,
        "reports": reports,
        "checkpoints": checkpoints,
        "docs_examples": docs_examples,
        "recent_groups": recent_groups,
        "notes": [
            "/api/overview discovery and basic details are read-only.",
            "Only explicit Start / Complete Preview + Confirm may update a selected valid Task's status and updated_at. Record Completion Evidence Preview + Confirm may append one completion_evidence value and update only updated_at for an eligible DOING Task; it does not validate evidence, change status, complete, or execute the Task.",
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


def route_keyword_matches(normalized_message: str, keyword: str) -> bool:
    """Match one route keyword, requiring token boundaries for ASCII terms.

    A plain substring test let short keywords fire inside unrelated words: "pr"
    inside "approval", "repo" inside "report", "idea" inside "ideal". Because a
    substring hit ties with an exact hit and ROUTING_PRIORITY then decides, the
    wrong skill could win over one whose keyword matched exactly. Korean has no
    word boundary to anchor on, so non-ASCII keywords keep substring matching.
    """

    if keyword.isascii():
        pattern = rf"(?<![0-9a-z]){re.escape(keyword)}(?![0-9a-z])"
        return re.search(pattern, normalized_message) is not None
    return keyword in normalized_message


def suggest_skill(message: str) -> dict[str, Any]:
    """Suggest one skill from registry keywords with deterministic matching."""

    normalized = normalize_message(message)
    if not normalized:
        return dict(UNKNOWN_SUGGESTION)

    candidates: list[tuple[int, int, dict[str, Any], list[str]]] = []
    for skill in registry_skills():
        keywords = [keyword.lower() for keyword in skill["route_keywords"]]
        hits = [
            keyword
            for keyword in keywords
            if route_keyword_matches(normalized, keyword)
        ]
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


@dataclass
class _CreateLocalTaskRecord:
    candidate: dict[str, str]
    expires_at: float
    receipt: dict[str, str] | None = None
    consumed_without_receipt: bool = False


@dataclass
class CreateLocalTaskRegistry:
    """One locked authority for Voice Create records."""

    def __init__(
        self,
        *,
        clock: Any = time.monotonic,
        token_factory: Any = lambda: secrets.token_urlsafe(32),
        ttl_seconds: int = CREATE_LOCAL_TASK_TOKEN_TTL_SECONDS,
        capacity: int = CREATE_LOCAL_TASK_TOKEN_CAPACITY,
        hmac_secret: bytes | None = None,
    ) -> None:
        self._clock = clock
        self._token_factory = token_factory
        self._ttl_seconds = ttl_seconds
        self._capacity = capacity
        self._records: dict[str, _CreateLocalTaskRecord] = {}
        self._hmac_secret = hmac_secret or secrets.token_bytes(32)
        self._lock = threading.Lock()

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(f"create-local-task:{token}".encode("utf-8")).hexdigest()

    def _purge_expired_locked(self, now: float) -> None:
        expired_records = [
            digest
            for digest, record in self._records.items()
            if record.expires_at <= now
        ]
        for digest in expired_records:
            del self._records[digest]

    def _capacity_used_locked(self) -> int:
        # Every record is standalone now that Evaluate Idea drafts are gone
        # (task-0075); this counted exactly the same set before.
        return len(self._records)

    def issue(self, candidate: dict[str, str]) -> tuple[int, dict[str, Any]]:
        now = float(self._clock())
        with self._lock:
            self._purge_expired_locked(now)
            if self._capacity_used_locked() >= self._capacity:
                return HTTPStatus.SERVICE_UNAVAILABLE, {
                    "ok": False,
                    "error": "create_local_task_temporarily_unavailable",
                }
            for _ in range(8):
                token = str(self._token_factory())
                if not CREATE_LOCAL_TASK_TOKEN_PATTERN.fullmatch(token):
                    continue
                digest = self._digest(token)
                if digest in self._records:
                    continue
                self._records[digest] = _CreateLocalTaskRecord(
                    candidate=dict(candidate),
                    expires_at=now + self._ttl_seconds,
                )
                return HTTPStatus.OK, {
                    "ok": True,
                    "token": token,
                    "expires_in_seconds": self._ttl_seconds,
                }
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "ok": False,
            "error": "create_local_task_temporarily_unavailable",
        }

    def confirm(
        self,
        *,
        token: str,
        confirmation: str,
        tasks_dir: Path,
    ) -> tuple[int, dict[str, Any]]:
        if confirmation != CREATE_LOCAL_TASK_CONFIRMATION_LITERAL:
            return HTTPStatus.BAD_REQUEST, {
                "ok": False,
                "error": "exact_confirmation_required",
            }
        if not CREATE_LOCAL_TASK_TOKEN_PATTERN.fullmatch(token):
            return HTTPStatus.NOT_FOUND, {
                "ok": False,
                "error": "invalid_or_expired_create_local_task_token",
            }

        now = float(self._clock())
        digest = self._digest(token)
        with self._lock:
            self._purge_expired_locked(now)
            record = self._records.get(digest)
            if record is None:
                return HTTPStatus.NOT_FOUND, {
                    "ok": False,
                    "error": "invalid_or_expired_create_local_task_token",
                }
            if record.receipt is not None:
                return HTTPStatus.OK, {
                    "ok": True,
                    "product_name": CREATE_LOCAL_TASK_PRODUCT_NAME,
                    "result_type": "already_created",
                    "receipt": dict(record.receipt),
                }
            if record.consumed_without_receipt:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "create_local_task_token_already_consumed",
                }

            record.consumed_without_receipt = True
            canonical_candidate = dict(record.candidate)
            try:
                write_result = write_task_file(
                    canonical_candidate,
                    tasks_dir=tasks_dir,
                )
            except OSError:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "create_local_task_storage_unavailable",
                }
            if write_result.result_type != "created" or not write_result.task_id:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": write_result.reason or "create_local_task_failed",
                }

            receipt = {
                "task_id": write_result.task_id,
                "title": record.candidate["title"],
                "status": CREATE_LOCAL_TASK_STATUS,
                "storage_location": (
                    f"{CREATE_LOCAL_TASK_STORAGE_ROOT}/{write_result.task_id}.md"
                ),
                "created_at": write_result.created_at or "",
                "next_recommended_action": (
                    "Review the new TODO task before any status change or execution."
                ),
            }
            record.receipt = receipt
            record.expires_at = now + self._ttl_seconds
            return HTTPStatus.OK, {
                "ok": True,
                "product_name": CREATE_LOCAL_TASK_PRODUCT_NAME,
                "result_type": "created",
                "receipt": dict(receipt),
            }


CREATE_LOCAL_TASK_REGISTRY = CreateLocalTaskRegistry()


def _create_local_task_transcript_error(transcript: str) -> str | None:
    for character in transcript:
        category = unicodedata.category(character)
        if category in {"Cc", "Cf", "Cs", "Zl", "Zp"} and character not in {
            "\r",
            "\n",
            "\t",
        }:
            return "unsafe_transcript_control_character"
    return None


def preview_create_local_task(
    payload: dict[str, Any],
    *,
    registry: CreateLocalTaskRegistry = CREATE_LOCAL_TASK_REGISTRY,
    tasks_dir: Path = CREATE_LOCAL_TASKS_DIR,
) -> tuple[int, dict[str, Any]]:
    """Create an exact, in-memory preview from the existing Voice candidate."""

    if set(payload) != {"transcript"}:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "create_local_task_preview_accepts_transcript_only",
        }
    transcript = payload.get("transcript")
    if not isinstance(transcript, str):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "transcript_must_be_string",
        }
    transcript_error = _create_local_task_transcript_error(transcript)
    if transcript_error:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": transcript_error}

    voice_status, voice_result = prepare_voice_inbox_task({"transcript": transcript})
    if voice_status != HTTPStatus.OK:
        return voice_status, voice_result
    task_candidate = voice_result["task_candidate"]
    canonical_candidate = {
        "title": task_candidate["title"],
        "status": CREATE_LOCAL_TASK_STATUS,
        "repo": CREATE_LOCAL_TASK_REPO,
        "summary": task_candidate["summary"],
        "source_command": "Voice Inbox",
    }
    try:
        provisional = preview_task_file_write(canonical_candidate, tasks_dir=tasks_dir)
    except OSError:
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "create_local_task_storage_unavailable",
        }
    if provisional.result_type != "would_create" or not provisional.task_id:
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": provisional.reason or "create_local_task_preview_failed",
        }

    issue_status, issued = registry.issue(canonical_candidate)
    if issue_status != HTTPStatus.OK:
        return issue_status, issued
    return HTTPStatus.OK, {
        "ok": True,
        "product_name": CREATE_LOCAL_TASK_PRODUCT_NAME,
        "token": issued["token"],
        "expires_in_seconds": issued["expires_in_seconds"],
        "confirmation_literal": CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
        "preview": {
            "title": canonical_candidate["title"],
            "summary": canonical_candidate["summary"],
            "status": CREATE_LOCAL_TASK_STATUS,
            "local_destination": (
                f"{CREATE_LOCAL_TASK_STORAGE_ROOT}/{provisional.task_id}.md"
            ),
        },
        "raw_transcript_saved": False,
        "destination_note": (
            "This destination is provisional. The receipt after Confirm is authoritative."
        ),
    }


def confirm_create_local_task(
    payload: dict[str, Any],
    *,
    registry: CreateLocalTaskRegistry = CREATE_LOCAL_TASK_REGISTRY,
    tasks_dir: Path = CREATE_LOCAL_TASKS_DIR,
) -> tuple[int, dict[str, Any]]:
    """Confirm one server-held candidate without accepting mutable task fields."""

    if set(payload) != {"token", "confirmation"}:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "create_local_task_confirm_accepts_token_and_confirmation_only",
        }
    token = payload.get("token")
    confirmation = payload.get("confirmation")
    if not isinstance(token, str) or not isinstance(confirmation, str):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_create_local_task_confirmation",
        }
    return registry.confirm(
        token=token,
        confirmation=confirmation,
        tasks_dir=tasks_dir,
    )


@dataclass
class _TaskTransitionRecord:
    task_id: str
    title: str
    storage_location: str
    action: str
    current_status: str
    target_status: str
    observed_updated_at: str
    planned_updated_at: str
    expected_digest: str
    confirmation_literal: str
    expires_at: float
    receipt: dict[str, Any] | None = None
    consumed_without_receipt: bool = False


class TaskTransitionRegistry:
    """Feature-local authority for one previewed Task status transition."""

    def __init__(
        self,
        *,
        clock: Any = time.monotonic,
        token_factory: Any = lambda: secrets.token_urlsafe(32),
        ttl_seconds: int = TASK_TRANSITION_TOKEN_TTL_SECONDS,
        capacity: int = TASK_TRANSITION_TOKEN_CAPACITY,
    ) -> None:
        self._clock = clock
        self._token_factory = token_factory
        self._ttl_seconds = ttl_seconds
        self._capacity = capacity
        self._records: dict[str, _TaskTransitionRecord] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(f"task-transition:{token}".encode("utf-8")).hexdigest()

    def _purge_expired_locked(self, now: float) -> None:
        for digest in [
            key
            for key, record in self._records.items()
            if record.expires_at <= now
        ]:
            del self._records[digest]

    def issue(self, record: _TaskTransitionRecord) -> tuple[int, dict[str, Any]]:
        now = float(self._clock())
        with self._lock:
            self._purge_expired_locked(now)
            if len(self._records) >= self._capacity:
                return HTTPStatus.SERVICE_UNAVAILABLE, {
                    "ok": False,
                    "error": "task_transition_temporarily_unavailable",
                }
            for _ in range(8):
                token = str(self._token_factory())
                if not TASK_TRANSITION_TOKEN_PATTERN.fullmatch(token):
                    continue
                digest = self._digest(token)
                if digest in self._records:
                    continue
                record.expires_at = now + self._ttl_seconds
                self._records[digest] = record
                return HTTPStatus.OK, {
                    "ok": True,
                    "token": token,
                    "expires_in_seconds": self._ttl_seconds,
                }
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "ok": False,
            "error": "task_transition_temporarily_unavailable",
        }

    def confirm(
        self,
        *,
        token: str,
        confirmation: str,
        tasks_dir: Path,
        writer: Any = transition_task_file_status,
    ) -> tuple[int, dict[str, Any]]:
        if not TASK_TRANSITION_TOKEN_PATTERN.fullmatch(token):
            return HTTPStatus.NOT_FOUND, {
                "ok": False,
                "error": "invalid_or_expired_task_transition_token",
            }
        now = float(self._clock())
        digest = self._digest(token)
        with self._lock:
            self._purge_expired_locked(now)
            record = self._records.get(digest)
            if record is None:
                return HTTPStatus.NOT_FOUND, {
                    "ok": False,
                    "error": "invalid_or_expired_task_transition_token",
                }
            if confirmation != record.confirmation_literal:
                return HTTPStatus.BAD_REQUEST, {
                    "ok": False,
                    "error": "exact_confirmation_required",
                }
            if record.receipt is not None:
                return HTTPStatus.OK, {
                    "ok": True,
                    "product_name": TASK_TRANSITION_PRODUCT_NAME,
                    "result_type": "already_updated",
                    "receipt": dict(record.receipt),
                }
            if record.consumed_without_receipt:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "task_transition_token_already_consumed",
                }

            record.consumed_without_receipt = True
            try:
                result = writer(
                    tasks_dir=tasks_dir,
                    task_id=record.task_id,
                    expected_digest=record.expected_digest,
                    current_status=record.current_status,
                    target_status=record.target_status,
                    planned_updated_at=record.planned_updated_at,
                )
            except OSError:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "task_transition_storage_unavailable",
                }
            if result.result_type == "stale":
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "task_changed_since_preview",
                }
            if result.result_type != "updated":
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": result.reason or "task_transition_failed",
                }

            receipt = {
                "task_id": record.task_id,
                "title": record.title,
                "previous_state": record.current_status,
                "transition": (
                    f"{record.current_status} \u2192 {record.target_status}"
                ),
                "current_state": record.target_status,
                "updated_at": record.planned_updated_at,
                "storage_location": record.storage_location,
                "no_execution": True,
            }
            record.receipt = receipt
            record.expires_at = now + self._ttl_seconds
            return HTTPStatus.OK, {
                "ok": True,
                "product_name": TASK_TRANSITION_PRODUCT_NAME,
                "result_type": "updated",
                "receipt": dict(receipt),
            }


TASK_TRANSITION_REGISTRY = TaskTransitionRegistry()


def selected_task_transition_items(
    tasks_dir: Path = CREATE_LOCAL_TASKS_DIR,
) -> list[dict[str, Any]]:
    """Return the same capped valid projection used by Actionable Task View."""

    if tasks_dir.resolve() == CREATE_LOCAL_TASKS_DIR.resolve():
        return overview_payload()["tasks"]
    directory = overview_directory_by_key()["memory_tasks"]
    discovered: list[dict[str, Any]] = []
    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return discovered
    for path in tasks_dir.rglob("*"):
        if not path.is_file() or not is_overview_candidate_path(path, tasks_dir):
            continue
        discovered.append(overview_file_item(path, directory))
    discovered.sort(
        key=lambda item: (item["modified"], item["path"]),
        reverse=True,
    )
    return project_task_view_items(
        discovered[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY]
    )


def preview_task_transition(
    payload: dict[str, Any],
    *,
    registry: TaskTransitionRegistry = TASK_TRANSITION_REGISTRY,
    tasks_dir: Path = CREATE_LOCAL_TASKS_DIR,
    utc_now: Any = lambda: datetime.now(timezone.utc).strftime(
        TASK_VIEW_TIMESTAMP_FORMAT
    ),
    _after_selection: Any = None,
) -> tuple[int, dict[str, Any]]:
    """Preview one status-only transition without writing the Task file."""

    if set(payload) != {"task_id", "action"}:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "task_transition_preview_accepts_task_id_and_action_only",
        }
    task_id = payload.get("task_id")
    action = payload.get("action")
    if not isinstance(task_id, str) or not isinstance(action, str):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_task_transition_preview",
        }
    transition = TASK_TRANSITION_ACTIONS.get(action)
    if transition is None:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_task_transition_action",
        }
    current_status, target_status, confirmation_literal = transition
    selected_item = next(
        (
            item
            for item in selected_task_transition_items(tasks_dir)
            if item["task_view"]["parse_state"] == "valid"
            and PurePosixPath(item["path"]).stem == task_id
        ),
        None,
    )
    if selected_item is None:
        return HTTPStatus.NOT_FOUND, {
            "ok": False,
            "error": "task_not_found_in_actionable_view",
        }
    task_path = (REPO_ROOT / selected_item["path"]).resolve()
    expected_path = (tasks_dir / f"{task_id}.md").resolve()
    if task_path != expected_path or task_path.parent != tasks_dir.resolve():
        return HTTPStatus.NOT_FOUND, {
            "ok": False,
            "error": "task_not_found_in_actionable_view",
        }
    if _after_selection is not None:
        _after_selection(task_path)
    try:
        raw = task_path.read_bytes()
    except OSError:
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "task_changed_since_preview",
        }
    try:
        snapshot_text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "task_changed_since_preview",
        }
    snapshot_view = parse_task_view_text(task_path.name, snapshot_text)
    if (
        snapshot_view is None
        or snapshot_view["parse_state"] != "valid"
        or snapshot_view["id"] != task_id
    ):
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "task_changed_since_preview",
        }
    snapshot_status = snapshot_view["status"]
    if snapshot_status != current_status:
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "task_status_transition_not_allowed",
        }
    planned_updated_at = str(utc_now())
    if parse_task_view_timestamp(planned_updated_at) is None:
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "invalid_planned_updated_at",
        }
    storage_location = selected_item["path"]
    record = _TaskTransitionRecord(
        task_id=task_id,
        title=snapshot_view["title"],
        storage_location=storage_location,
        action=action,
        current_status=snapshot_status,
        target_status=target_status,
        observed_updated_at=snapshot_view["updated_at"],
        planned_updated_at=planned_updated_at,
        expected_digest=hashlib.sha256(raw).hexdigest(),
        confirmation_literal=confirmation_literal,
        expires_at=0.0,
    )
    issue_status, issued = registry.issue(record)
    if issue_status != HTTPStatus.OK:
        return issue_status, issued
    return HTTPStatus.OK, {
        "ok": True,
        "product_name": TASK_TRANSITION_PRODUCT_NAME,
        "token": issued["token"],
        "expires_in_seconds": issued["expires_in_seconds"],
        "confirmation_literal": confirmation_literal,
        "preview": {
            "task_id": task_id,
            "title": snapshot_view["title"],
            "current_state": snapshot_status,
            "transition": f"{snapshot_status} \u2192 {target_status}",
            "proposed_state": target_status,
            "updated_at": planned_updated_at,
            "storage_location": storage_location,
            "no_execution": True,
            "notice": TASK_TRANSITION_NOTICE,
            "warning": (
                TASK_TRANSITION_COMPLETE_WARNING if action == "complete" else ""
            ),
        },
    }


def confirm_task_transition(
    payload: dict[str, Any],
    *,
    registry: TaskTransitionRegistry = TASK_TRANSITION_REGISTRY,
    tasks_dir: Path = CREATE_LOCAL_TASKS_DIR,
) -> tuple[int, dict[str, Any]]:
    """Confirm one server-held status-only Task transition."""

    if set(payload) != {"token", "confirmation"}:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "task_transition_confirm_accepts_token_and_confirmation_only",
        }
    token = payload.get("token")
    confirmation = payload.get("confirmation")
    if not isinstance(token, str) or not isinstance(confirmation, str):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_task_transition_confirmation",
        }
    return registry.confirm(
        token=token,
        confirmation=confirmation,
        tasks_dir=tasks_dir,
    )


def normalize_completion_evidence(value: Any) -> str | None:
    """Return one safe canonical evidence value or None."""

    if not isinstance(value, str):
        return None
    if "`" in value or "\x00" in value:
        return None
    if any(
        character in {"\r", "\n", "\u0085", "\u2028", "\u2029"}
        or unicodedata.category(character) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
        for character in value
    ):
        return None
    normalized = " ".join(unicodedata.normalize("NFC", value).strip().split())
    if not 1 <= len(normalized) <= 500:
        return None
    return normalized


@dataclass
class _CompletionEvidenceRecord:
    task_id: str
    title: str
    completion_evidence: str
    storage_location: str
    observed_updated_at: str
    planned_updated_at: str
    expected_digest: str
    expires_at: float
    receipt: dict[str, Any] | None = None
    consumed_without_receipt: bool = False


class CompletionEvidenceRegistry:
    """Feature-local authority for one append-once evidence preview."""

    def __init__(
        self,
        *,
        clock: Any = time.monotonic,
        token_factory: Any = lambda: secrets.token_urlsafe(32),
        ttl_seconds: int = COMPLETION_EVIDENCE_TOKEN_TTL_SECONDS,
        capacity: int = COMPLETION_EVIDENCE_TOKEN_CAPACITY,
    ) -> None:
        self._clock = clock
        self._token_factory = token_factory
        self._ttl_seconds = ttl_seconds
        self._capacity = capacity
        self._records: dict[str, _CompletionEvidenceRecord] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(
            f"completion-evidence:{token}".encode("utf-8")
        ).hexdigest()

    def _purge_expired_locked(self, now: float) -> None:
        for digest in [
            key
            for key, record in self._records.items()
            if record.expires_at <= now
        ]:
            del self._records[digest]

    def issue(
        self,
        record: _CompletionEvidenceRecord,
    ) -> tuple[int, dict[str, Any]]:
        now = float(self._clock())
        with self._lock:
            self._purge_expired_locked(now)
            if len(self._records) >= self._capacity:
                return HTTPStatus.SERVICE_UNAVAILABLE, {
                    "ok": False,
                    "error": "completion_evidence_temporarily_unavailable",
                }
            for _ in range(8):
                token = str(self._token_factory())
                if not COMPLETION_EVIDENCE_TOKEN_PATTERN.fullmatch(token):
                    continue
                digest = self._digest(token)
                if digest in self._records:
                    continue
                record.expires_at = now + self._ttl_seconds
                self._records[digest] = record
                return HTTPStatus.OK, {
                    "token": token,
                    "expires": self._ttl_seconds,
                }
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "ok": False,
            "error": "completion_evidence_temporarily_unavailable",
        }

    def confirm(
        self,
        *,
        token: str,
        confirmation: str,
        tasks_dir: Path,
        writer: Any = record_task_completion_evidence,
    ) -> tuple[int, dict[str, Any]]:
        if not COMPLETION_EVIDENCE_TOKEN_PATTERN.fullmatch(token):
            return HTTPStatus.NOT_FOUND, {
                "ok": False,
                "error": "completion_evidence_invalid_or_expired_token",
            }
        now = float(self._clock())
        digest = self._digest(token)
        with self._lock:
            self._purge_expired_locked(now)
            record = self._records.get(digest)
            if record is None:
                return HTTPStatus.NOT_FOUND, {
                    "ok": False,
                    "error": "completion_evidence_invalid_or_expired_token",
                }
            if confirmation != COMPLETION_EVIDENCE_CONFIRMATION_LITERAL:
                return HTTPStatus.BAD_REQUEST, {
                    "ok": False,
                    "error": "completion_evidence_exact_confirmation_required",
                }
            if record.receipt is not None:
                return HTTPStatus.OK, {
                    "ok": True,
                    "product_name": COMPLETION_EVIDENCE_PRODUCT_NAME,
                    "result_type": "already_recorded",
                    "receipt": dict(record.receipt),
                }
            if record.consumed_without_receipt:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_token_already_consumed",
                }
            record.consumed_without_receipt = True

            resolved_tasks_dir = tasks_dir.resolve()
            task_path = (tasks_dir / f"{record.task_id}.md").resolve()
            if (
                task_path.parent != resolved_tasks_dir
                or not TASK_FILE_PATTERN.fullmatch(task_path.name)
            ):
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_task_path_invalid",
                }
            try:
                raw = task_path.read_bytes()
                text = raw.decode("utf-8", errors="strict")
            except (OSError, UnicodeDecodeError):
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_storage_unavailable",
                }
            view = parse_task_view_text(task_path.name, text)
            if (
                view is None
                or view["parse_state"] != "valid"
                or view["id"] != record.task_id
            ):
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_task_changed_since_preview",
                }
            if view["status"] != "DOING":
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_task_not_doing",
                }
            if view["has_completion_evidence"]:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_already_exists",
                }
            if not hmac.compare_digest(
                hashlib.sha256(raw).hexdigest(),
                record.expected_digest,
            ):
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_task_changed_since_preview",
                }

            try:
                result = writer(
                    tasks_dir=tasks_dir,
                    task_id=record.task_id,
                    completion_evidence=record.completion_evidence,
                    expected_digest=record.expected_digest,
                    planned_updated_at=record.planned_updated_at,
                )
            except OSError:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_storage_unavailable",
                }
            if result.result_type == "stale":
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": "completion_evidence_task_changed_since_preview",
                }
            if result.result_type != "recorded":
                result_reason = result.reason or "record_failed"
                if not result_reason.startswith("completion_evidence_"):
                    result_reason = f"completion_evidence_{result_reason}"
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "error": result_reason,
                }

            receipt = {
                "task_id": record.task_id,
                "title": record.title,
                "current_status": "DOING",
                "completion_evidence": record.completion_evidence,
                "updated_at": record.planned_updated_at,
                "storage_location": record.storage_location,
                "evidence_validated": False,
                "status_changed": False,
                "no_execution": True,
                "recommendation": COMPLETION_EVIDENCE_RECOMMENDATION,
            }
            record.receipt = receipt
            record.expires_at = now + self._ttl_seconds
            return HTTPStatus.OK, {
                "ok": True,
                "product_name": COMPLETION_EVIDENCE_PRODUCT_NAME,
                "result_type": "recorded",
                "receipt": dict(receipt),
            }


COMPLETION_EVIDENCE_REGISTRY = CompletionEvidenceRegistry()


def preview_completion_evidence(
    payload: dict[str, Any],
    *,
    registry: CompletionEvidenceRegistry = COMPLETION_EVIDENCE_REGISTRY,
    tasks_dir: Path = CREATE_LOCAL_TASKS_DIR,
    utc_now: Any = lambda: datetime.now(timezone.utc).strftime(
        TASK_VIEW_TIMESTAMP_FORMAT
    ),
    _after_selection: Any = None,
) -> tuple[int, dict[str, Any]]:
    """Preview one append-once completion evidence write without mutation."""

    if set(payload) != {"task_id", "completion_evidence"}:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": (
                "completion_evidence_preview_accepts_task_id_and_"
                "completion_evidence_only"
            ),
        }
    task_id = payload.get("task_id")
    raw_evidence = payload.get("completion_evidence")
    if not isinstance(task_id, str) or not isinstance(raw_evidence, str):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "completion_evidence_invalid_preview",
        }
    completion_evidence = normalize_completion_evidence(raw_evidence)
    if completion_evidence is None:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "completion_evidence_invalid_value",
        }

    selected_item = next(
        (
            item
            for item in selected_task_transition_items(tasks_dir)
            if item["task_view"]["parse_state"] == "valid"
            and PurePosixPath(item["path"]).stem == task_id
        ),
        None,
    )
    if selected_item is None:
        return HTTPStatus.NOT_FOUND, {
            "ok": False,
            "error": "completion_evidence_task_not_found_in_actionable_view",
        }
    task_path = (REPO_ROOT / selected_item["path"]).resolve()
    expected_path = (tasks_dir / f"{task_id}.md").resolve()
    if task_path != expected_path or task_path.parent != tasks_dir.resolve():
        return HTTPStatus.NOT_FOUND, {
            "ok": False,
            "error": "completion_evidence_task_not_found_in_actionable_view",
        }
    if _after_selection is not None:
        _after_selection(task_path)
    try:
        raw = task_path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
    except (OSError, UnicodeDecodeError):
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "completion_evidence_task_changed_since_preview",
        }
    view = parse_task_view_text(task_path.name, text)
    if (
        view is None
        or view["parse_state"] != "valid"
        or view["id"] != task_id
    ):
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "completion_evidence_task_changed_since_preview",
        }
    if view["status"] != "DOING":
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "completion_evidence_task_not_doing",
        }
    if view["has_completion_evidence"]:
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "completion_evidence_already_exists",
        }
    planned_updated_at = str(utc_now())
    if parse_task_view_timestamp(planned_updated_at) is None:
        return HTTPStatus.CONFLICT, {
            "ok": False,
            "error": "completion_evidence_invalid_planned_updated_at",
        }

    record = _CompletionEvidenceRecord(
        task_id=task_id,
        title=view["title"],
        completion_evidence=completion_evidence,
        storage_location=selected_item["path"],
        observed_updated_at=view["updated_at"],
        planned_updated_at=planned_updated_at,
        expected_digest=hashlib.sha256(raw).hexdigest(),
        expires_at=0.0,
    )
    issue_status, issued = registry.issue(record)
    if issue_status != HTTPStatus.OK:
        return issue_status, issued
    return HTTPStatus.OK, {
        "ok": True,
        "product_name": COMPLETION_EVIDENCE_PRODUCT_NAME,
        "token": issued["token"],
        "expires": issued["expires"],
        "confirmation_literal": COMPLETION_EVIDENCE_CONFIRMATION_LITERAL,
        "preview": {
            "task_id": task_id,
            "title": view["title"],
            "current_status": "DOING",
            "existing_evidence": None,
            "proposed_evidence": completion_evidence,
            "observed_updated_at": view["updated_at"],
            "planned_updated_at": planned_updated_at,
            "storage_location": selected_item["path"],
            "evidence_validated": False,
            "status_changed": False,
            "no_execution": True,
            "notice": COMPLETION_EVIDENCE_NOTICE,
        },
    }


def confirm_completion_evidence(
    payload: dict[str, Any],
    *,
    registry: CompletionEvidenceRegistry = COMPLETION_EVIDENCE_REGISTRY,
    tasks_dir: Path = CREATE_LOCAL_TASKS_DIR,
) -> tuple[int, dict[str, Any]]:
    """Confirm one server-held completion evidence append."""

    if set(payload) != {"token", "confirmation"}:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": (
                "completion_evidence_confirm_accepts_token_and_confirmation_only"
            ),
        }
    token = payload.get("token")
    confirmation = payload.get("confirmation")
    if not isinstance(token, str) or not isinstance(confirmation, str):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "completion_evidence_invalid_confirmation",
        }
    return registry.confirm(
        token=token,
        confirmation=confirmation,
        tasks_dir=tasks_dir,
    )


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


class _DuplicateCreateLocalTaskJsonKey(ValueError):
    pass


def parse_create_local_task_json_body(raw_body: bytes) -> tuple[int, dict[str, Any]]:
    """Parse feature-local JSON while rejecting duplicate keys at every depth."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for key, value in pairs:
            if key in parsed:
                raise _DuplicateCreateLocalTaskJsonKey
            parsed[key] = value
        return parsed

    try:
        payload = json.loads(
            raw_body.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateCreateLocalTaskJsonKey,
    ):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_create_local_task_json",
        }
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "create_local_task_json_must_be_object",
        }
    return HTTPStatus.OK, payload


def validate_create_local_task_http_request(
    *,
    path: str,
    query: str,
    header_pairs: list[tuple[str, str]],
    bound_port: int,
) -> tuple[int, dict[str, Any]]:
    """Validate the exact write-capable local request before reading its body."""

    if path not in {
        CREATE_LOCAL_TASK_PREVIEW_ENDPOINT,
        CREATE_LOCAL_TASK_CONFIRM_ENDPOINT,
    } or query:
        return HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"}
    if len(header_pairs) > 32:
        return HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, {
            "ok": False,
            "error": "invalid_create_local_task_headers",
        }

    headers: dict[str, list[str]] = {}
    for raw_name, raw_value in header_pairs:
        name = str(raw_name).strip().lower()
        value = str(raw_value).strip()
        if not name or len(name) > 80 or len(value) > 1024:
            return HTTPStatus.BAD_REQUEST, {
                "ok": False,
                "error": "invalid_create_local_task_headers",
            }
        headers.setdefault(name, []).append(value)

    if headers.get("transfer-encoding"):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "transfer_encoding_not_allowed",
        }
    if any(len(headers.get(name, [])) != 1 for name in CREATE_LOCAL_TASK_REQUIRED_HEADERS):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_create_local_task_headers",
        }

    expected_authority = f"{DEFAULT_HOST}:{bound_port}"
    if headers["host"][0] != expected_authority:
        return HTTPStatus.FORBIDDEN, {
            "ok": False,
            "error": "create_local_task_origin_rejected",
        }
    if headers["origin"][0] != f"http://{expected_authority}":
        return HTTPStatus.FORBIDDEN, {
            "ok": False,
            "error": "create_local_task_origin_rejected",
        }
    if headers["content-type"][0].lower() not in CREATE_LOCAL_TASK_ALLOWED_CONTENT_TYPES:
        return HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {
            "ok": False,
            "error": "create_local_task_json_required",
        }

    content_length = headers["content-length"][0]
    if not re.fullmatch(r"0|[1-9][0-9]*", content_length):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_content_length",
        }
    body_length = int(content_length)
    if body_length <= 0 or body_length > MAX_JSON_BODY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {
            "ok": False,
            "error": "create_local_task_body_size_rejected",
        }
    return HTTPStatus.OK, {"ok": True, "body_length": body_length}


class _DuplicateTaskTransitionJsonKey(ValueError):
    pass


def parse_task_transition_json_body(raw_body: bytes) -> tuple[int, dict[str, Any]]:
    """Parse feature-local transition JSON and reject duplicate keys."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for key, value in pairs:
            if key in parsed:
                raise _DuplicateTaskTransitionJsonKey
            parsed[key] = value
        return parsed

    try:
        payload = json.loads(
            raw_body.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateTaskTransitionJsonKey,
    ):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_task_transition_json",
        }
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "task_transition_json_must_be_object",
        }
    return HTTPStatus.OK, payload


def validate_task_transition_http_request(
    *,
    path: str,
    query: str,
    header_pairs: list[tuple[str, str]],
    bound_port: int,
) -> tuple[int, dict[str, Any]]:
    """Validate one exact locally guarded task-transition request."""

    if path not in {
        TASK_TRANSITION_PREVIEW_ENDPOINT,
        TASK_TRANSITION_CONFIRM_ENDPOINT,
    } or query:
        return HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"}
    if len(header_pairs) > 32:
        return HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, {
            "ok": False,
            "error": "invalid_task_transition_headers",
        }
    headers: dict[str, list[str]] = {}
    for raw_name, raw_value in header_pairs:
        name = str(raw_name).strip().lower()
        value = str(raw_value).strip()
        if not name or len(name) > 80 or len(value) > 1024:
            return HTTPStatus.BAD_REQUEST, {
                "ok": False,
                "error": "invalid_task_transition_headers",
            }
        headers.setdefault(name, []).append(value)
    if headers.get("transfer-encoding"):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "transfer_encoding_not_allowed",
        }
    if any(
        len(headers.get(name, [])) != 1
        for name in CREATE_LOCAL_TASK_REQUIRED_HEADERS
    ):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_task_transition_headers",
        }
    expected_authority = f"{DEFAULT_HOST}:{bound_port}"
    if (
        headers["host"][0] != expected_authority
        or headers["origin"][0] != f"http://{expected_authority}"
    ):
        return HTTPStatus.FORBIDDEN, {
            "ok": False,
            "error": "task_transition_origin_rejected",
        }
    if (
        headers["content-type"][0].lower()
        not in CREATE_LOCAL_TASK_ALLOWED_CONTENT_TYPES
    ):
        return HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {
            "ok": False,
            "error": "task_transition_json_required",
        }
    content_length = headers["content-length"][0]
    if not re.fullmatch(r"0|[1-9][0-9]*", content_length):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "invalid_content_length",
        }
    body_length = int(content_length)
    if body_length <= 0 or body_length > MAX_JSON_BODY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {
            "ok": False,
            "error": "task_transition_body_size_rejected",
        }
    return HTTPStatus.OK, {"ok": True, "body_length": body_length}


class _DuplicateCompletionEvidenceJsonKey(ValueError):
    pass


def parse_completion_evidence_json_body(
    raw_body: bytes,
) -> tuple[int, dict[str, Any]]:
    """Parse feature-local evidence JSON and reject duplicate keys."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for key, value in pairs:
            if key in parsed:
                raise _DuplicateCompletionEvidenceJsonKey
            parsed[key] = value
        return parsed

    try:
        payload = json.loads(
            raw_body.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateCompletionEvidenceJsonKey,
    ):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "completion_evidence_invalid_json",
        }
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "completion_evidence_json_must_be_object",
        }
    return HTTPStatus.OK, payload


def validate_completion_evidence_http_request(
    *,
    path: str,
    query: str,
    header_pairs: list[tuple[str, str]],
    bound_port: int,
) -> tuple[int, dict[str, Any]]:
    """Validate one exact locally guarded completion-evidence request."""

    if path not in {
        COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
        COMPLETION_EVIDENCE_CONFIRM_ENDPOINT,
    } or query:
        return HTTPStatus.NOT_FOUND, {
            "ok": False,
            "error": "completion_evidence_not_found",
        }
    if len(header_pairs) > 32:
        return HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, {
            "ok": False,
            "error": "completion_evidence_headers_rejected",
        }
    headers: dict[str, list[str]] = {}
    for raw_name, raw_value in header_pairs:
        name = str(raw_name).strip().lower()
        value = str(raw_value).strip()
        if not name or len(name) > 80 or len(value) > 1024:
            return HTTPStatus.BAD_REQUEST, {
                "ok": False,
                "error": "completion_evidence_headers_rejected",
            }
        headers.setdefault(name, []).append(value)
    if headers.get("transfer-encoding"):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "completion_evidence_transfer_encoding_not_allowed",
        }
    if any(
        len(headers.get(name, [])) != 1
        for name in CREATE_LOCAL_TASK_REQUIRED_HEADERS
    ):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "completion_evidence_headers_rejected",
        }
    expected_authority = f"{DEFAULT_HOST}:{bound_port}"
    if (
        headers["host"][0] != expected_authority
        or headers["origin"][0] != f"http://{expected_authority}"
    ):
        return HTTPStatus.FORBIDDEN, {
            "ok": False,
            "error": "completion_evidence_origin_rejected",
        }
    if (
        headers["content-type"][0].lower()
        not in CREATE_LOCAL_TASK_ALLOWED_CONTENT_TYPES
    ):
        return HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {
            "ok": False,
            "error": "completion_evidence_json_required",
        }
    content_length = headers["content-length"][0]
    if not re.fullmatch(r"[1-9][0-9]*", content_length):
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "completion_evidence_invalid_content_length",
        }
    body_length = int(content_length)
    if body_length > MAX_JSON_BODY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {
            "ok": False,
            "error": "completion_evidence_body_size_rejected",
        }
    return HTTPStatus.OK, {"ok": True, "body_length": body_length}


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

        parsed = urlparse(self.path)
        path = parsed.path
        if path in {
            CREATE_LOCAL_TASK_PREVIEW_ENDPOINT,
            CREATE_LOCAL_TASK_CONFIRM_ENDPOINT,
        }:
            self._handle_create_local_task_post(parsed.path, parsed.query)
            return
        if path in {
            TASK_TRANSITION_PREVIEW_ENDPOINT,
            TASK_TRANSITION_CONFIRM_ENDPOINT,
        }:
            self._handle_task_transition_post(parsed.path, parsed.query)
            return
        if path in {
            COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
            COMPLETION_EVIDENCE_CONFIRM_ENDPOINT,
        }:
            self._handle_completion_evidence_post(parsed.path, parsed.query)
            return
        if path not in {
            "/api/suggest-skill",
            "/api/voice-inbox/prepare",
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

    def _handle_create_local_task_post(self, path: str, query: str) -> None:
        header_pairs = list(self.headers.raw_items())
        metadata_status, metadata = validate_create_local_task_http_request(
            path=path,
            query=query,
            header_pairs=header_pairs,
            bound_port=int(self.server.server_address[1]),
        )
        if metadata_status != HTTPStatus.OK:
            self._send_json(metadata_status, metadata)
            return

        raw_body = self.rfile.read(metadata["body_length"])
        if len(raw_body) != metadata["body_length"]:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "create_local_task_body_length_mismatch",
                },
            )
            return
        parse_status, payload = parse_create_local_task_json_body(raw_body)
        if parse_status != HTTPStatus.OK:
            self._send_json(parse_status, payload)
            return

        registry = getattr(
            self.server,
            "create_local_task_registry",
            CREATE_LOCAL_TASK_REGISTRY,
        )
        tasks_dir = getattr(
            self.server,
            "create_local_tasks_dir",
            CREATE_LOCAL_TASKS_DIR,
        )
        if path == CREATE_LOCAL_TASK_PREVIEW_ENDPOINT:
            response_status, response_payload = preview_create_local_task(
                payload,
                registry=registry,
                tasks_dir=tasks_dir,
            )
        else:
            response_status, response_payload = confirm_create_local_task(
                payload,
                registry=registry,
                tasks_dir=tasks_dir,
            )
        self._send_json(response_status, response_payload)

    def _handle_task_transition_post(self, path: str, query: str) -> None:
        metadata_status, metadata = validate_task_transition_http_request(
            path=path,
            query=query,
            header_pairs=list(self.headers.raw_items()),
            bound_port=int(self.server.server_address[1]),
        )
        if metadata_status != HTTPStatus.OK:
            self._send_json(metadata_status, metadata)
            return
        raw_body = self.rfile.read(metadata["body_length"])
        if len(raw_body) != metadata["body_length"]:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "task_transition_body_length_mismatch",
                },
            )
            return
        parse_status, payload = parse_task_transition_json_body(raw_body)
        if parse_status != HTTPStatus.OK:
            self._send_json(parse_status, payload)
            return
        registry = getattr(
            self.server,
            "task_transition_registry",
            TASK_TRANSITION_REGISTRY,
        )
        tasks_dir = getattr(
            self.server,
            "task_transition_tasks_dir",
            CREATE_LOCAL_TASKS_DIR,
        )
        if path == TASK_TRANSITION_PREVIEW_ENDPOINT:
            response_status, response_payload = preview_task_transition(
                payload,
                registry=registry,
                tasks_dir=tasks_dir,
                utc_now=getattr(
                    self.server,
                    "task_transition_utc_now",
                    lambda: datetime.now(timezone.utc).strftime(
                        TASK_VIEW_TIMESTAMP_FORMAT
                    ),
                ),
            )
        else:
            response_status, response_payload = confirm_task_transition(
                payload,
                registry=registry,
                tasks_dir=tasks_dir,
            )
        self._send_json(response_status, response_payload)

    def _handle_completion_evidence_post(self, path: str, query: str) -> None:
        metadata_status, metadata = validate_completion_evidence_http_request(
            path=path,
            query=query,
            header_pairs=list(self.headers.raw_items()),
            bound_port=int(self.server.server_address[1]),
        )
        if metadata_status != HTTPStatus.OK:
            self._send_json(metadata_status, metadata)
            return
        raw_body = self.rfile.read(metadata["body_length"])
        if len(raw_body) != metadata["body_length"]:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "completion_evidence_body_length_mismatch",
                },
            )
            return
        parse_status, payload = parse_completion_evidence_json_body(raw_body)
        if parse_status != HTTPStatus.OK:
            self._send_json(parse_status, payload)
            return
        registry = getattr(
            self.server,
            "completion_evidence_registry",
            COMPLETION_EVIDENCE_REGISTRY,
        )
        tasks_dir = getattr(
            self.server,
            "completion_evidence_tasks_dir",
            CREATE_LOCAL_TASKS_DIR,
        )
        if path == COMPLETION_EVIDENCE_PREVIEW_ENDPOINT:
            response_status, response_payload = preview_completion_evidence(
                payload,
                registry=registry,
                tasks_dir=tasks_dir,
                utc_now=getattr(
                    self.server,
                    "completion_evidence_utc_now",
                    lambda: datetime.now(timezone.utc).strftime(
                        TASK_VIEW_TIMESTAMP_FORMAT
                    ),
                ),
            )
        else:
            response_status, response_payload = confirm_completion_evidence(
                payload,
                registry=registry,
                tasks_dir=tasks_dir,
            )
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
    assert len(registry["skills"]) == 5
    assert len({skill["skill_id"] for skill in registry["skills"]}) == 5
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
    # task-0099: this filter runs inside discover_recent_items before anything
    # looks at TASK_FILE_PATTERN, so it covers memory/tasks too. Recent Tasks
    # renders a title and summary read from the file itself and that list is
    # not pattern-filtered, so a stray token.txt dropped there would otherwise
    # have its content shown. A Task record whose slug happens to carry one of
    # the words is excluded by the same rule; that over-exclusion is the
    # accepted cost, and /api/overview discloses it as "secrets-like file
    # names". The third case keeps the first two honest - the exclusion is
    # driven by the name, not by the directory.
    tasks_root = REPO_ROOT / "memory" / "tasks"
    assert is_overview_candidate_path(
        tasks_root / "task-0043-no-secrets-enforcement.md", tasks_root
    ) is False
    assert is_overview_candidate_path(
        tasks_root / "token.txt", tasks_root
    ) is False
    assert is_overview_candidate_path(
        tasks_root / "task-0500-ordinary-record.md", tasks_root
    ) is True

    assert suggest_skill("idea MVP validation")["recommended_skill"] == "research_council"
    assert suggest_skill("Codex commit review")["recommended_skill"] == "hermes_manager"
    assert suggest_skill("MCP Agent Skills new technology")["recommended_skill"] == "daily_ai_radar"
    assert suggest_skill("remember this repeated workflow as a skill")["recommended_skill"] == "unknown"
    assert suggest_skill("make this better somehow")["recommended_skill"] == "unknown"
    assert suggest_skill("\uc544\uc774\ub514\uc5b4 MVP \uac80\uc99d")["recommended_skill"] == "research_council"
    assert suggest_skill("\uc81c\uc870\uc7a5\ube44 \uc2dc\ubbac\ub808\uc774\uc158 \uc544\uc774\ub514\uc5b4 \uac80\uc99d\ud574\uc918")["recommended_skill"] == "research_council"
    assert suggest_skill("\ucc3d\uc5c5 \uc544\uc774\ub514\uc5b4 \uc0ac\uc5c5\uc131 \uac80\ud1a0\ud574\uc918")["recommended_skill"] == "research_council"
    assert suggest_skill("\uc2dc\ubbac\ub808\uc774\uc158 \uac8c\uc784 \ucd94\ucc9c\ud574\uc918")["recommended_skill"] == "unknown"
    assert suggest_skill("\uacc4\uc57d\uc11c \uac80\ud1a0 \uc571 \ucf54\ub4dc \uc218\uc815\ud574\uc918")["recommended_skill"] != "research_council"
    assert suggest_skill("Codex \ucee4\ubc0b \ub9ac\ubdf0")["recommended_skill"] == "hermes_manager"
    assert suggest_skill("MCP Agent Skills \uc0c8 \uae30\uc220")["recommended_skill"] == "daily_ai_radar"
    assert suggest_skill("\ubc18\ubcf5 \uc791\uc5c5 skill\ub85c \uae30\uc5b5")["recommended_skill"] == "tasks_reports"

    # task-0093: short keywords such as "pr", "repo", "idea" and "task" used to
    # fire as substrings of unrelated words, and a substring hit tied with an
    # exact hit so ROUTING_PRIORITY handed the query to the wrong skill.
    for routing_message, expected_skill in (
        ("git", "hermes_manager"),
        ("pr", "hermes_manager"),
        ("repo", "hermes_manager"),
        ("review", "hermes_manager"),
        ("리뷰", "hermes_manager"),
        ("repository", "hermes_manager"),
        ("report", "tasks_reports"),
        ("approval", "tasks_reports"),
        ("preview", "unknown"),
        ("prepare", "unknown"),
        ("process", "unknown"),
        ("progress", "unknown"),
        ("priority", "unknown"),
        ("print", "unknown"),
        ("ideal", "unknown"),
        ("multitask", "unknown"),
        ("reproduce", "unknown"),
    ):
        assert suggest_skill(routing_message)["recommended_skill"] == expected_skill

    # the Voice broad-hit filter keeps its own meaning on top of the new matching
    for voice_message, expected_voice_skill in (
        ("review", "unknown"),
        ("리뷰", "unknown"),
        ("git", "hermes_manager"),
        ("pr", "hermes_manager"),
        ("repo", "hermes_manager"),
        ("Codex 커밋 리뷰", "hermes_manager"),
    ):
        assert voice_suggest_skill(voice_message)["recommended_skill"] == expected_voice_skill

    # task-0096: the Task metadata block ends at the first column-0 line that is
    # not a field. An ordinary Markdown list in the document body is prose, not
    # metadata, and must not fail the record closed into metadata review.
    task_view_header = (
        "# task-0500-header-block-probe\n"
        "\n"
        "- id: `task-0500-header-block-probe`\n"
        "- title: `probe`\n"
        "- status: `DONE`\n"
        "- repo: `jarvis-core`\n"
        "- created_at: `2026-01-01 00:00 UTC`\n"
        "- updated_at: `2026-01-01 00:00 UTC`\n"
        "- summary: `probe summary`\n"
    )
    task_view_name = "task-0500-header-block-probe.md"
    for body, expected_state in (
        ("", "valid"),
        ("\n## Body\n\n- a prose bullet\n- another bullet\n", "valid"),
        # a body bullet that happens to satisfy the metadata grammar is still body
        ("\n## Body\n\n- valid: `true`\n", "valid"),
        ("\n## Body\n\n- status: `TODO`\n", "valid"),
        # an indented line continues the field above it
        ("  - 규칙: anything\n", "valid"),
    ):
        probe_view = parse_task_view_text(task_view_name, task_view_header + body)
        assert probe_view is not None
        assert probe_view["parse_state"] == expected_state
        if expected_state == "valid":
            assert probe_view["group_id"] != "metadata_review"

    for broken_header, expected_reason in (
        (task_view_header.replace("- repo: `jarvis-core`", "- repo: jarvis-core"), "invalid_text"),
        (task_view_header.replace("- repo: `jarvis-core`", "- bogus: `x`"), "unsupported_field"),
        (task_view_header + "- title: `dup`\n", "duplicate_field"),
        (task_view_header.replace("- repo: `jarvis-core`\n", ""), "missing_field"),
        (task_view_header.replace("- status: `DONE`", "- status: `WEIRD`"), "invalid_status"),
    ):
        broken_view = parse_task_view_text(task_view_name, broken_header)
        assert broken_view is not None
        assert broken_view["parse_state"] == "invalid"
        assert broken_view["reason_code"] == expected_reason
        assert broken_view["group_id"] == "metadata_review"

    # task-0097: OVERVIEW_SNIPPET_BYTES bounds the read, not the file. A record
    # whose header block is valid stays valid however far its body grows, and a
    # header block that does not close inside that prefix still fails closed.
    # These run through the real read_task_view_text on real files, because the
    # defect this replaced lived entirely in the reader: every projection test
    # in this repository injects a text_reader and steps straight over it.
    def probe_bounded_read(file_bytes: bytes) -> Any:
        with tempfile.TemporaryDirectory() as probe_dir:
            probe_path = Path(probe_dir) / task_view_name
            probe_path.write_bytes(file_bytes)
            try:
                probe_text = read_task_view_text(probe_path)
            except UnicodeDecodeError:
                return "invalid_utf8"
            except ValueError:
                return "fail_closed"
            assert len(probe_text.encode("utf-8")) <= OVERVIEW_SNIPPET_BYTES
            probe = parse_task_view_text(task_view_name, probe_text)
            assert probe is not None
            return probe

    header_bytes = task_view_header.encode("utf-8")
    assert len(header_bytes) < OVERVIEW_SNIPPET_BYTES
    # a body of ordinary column-0 Markdown bullets, the task-0096 shape, now
    # carried past the bound so the reader is exercised with it too
    bullet_body = b"\n## Body\n\n" + b"- an ordinary prose bullet\n" * 200
    assert len(header_bytes + bullet_body) > OVERVIEW_SNIPPET_BYTES
    NEWLINE = "\n"
    CONT_A = "  - 규칙: 위 필드의 연속이다"
    CONT_B = "  들여쓴 설명 줄도 마찬가지다"
    # an indented line continues the field above it, the shape this
    # repository's own task-template.md uses, and it must not close the
    # block early and strand the required fields below it
    continued_header = task_view_header.replace(
        "- status: `DONE`" + NEWLINE,
        ("- status: `DONE`" + NEWLINE + CONT_A + NEWLINE + CONT_B + NEWLINE),
    ).encode("utf-8")
    for probe_bytes, expected_state, expected_reason in (
        (header_bytes + b"\n## Body\n", "valid", None),
        (header_bytes + bullet_body, "valid", None),
        (continued_header + bullet_body, "valid", None),
        (
            task_view_header.replace(
                "- repo: `jarvis-core`", "- repo: jarvis-core"
            ).encode("utf-8") + bullet_body,
            "invalid",
            "invalid_text",
        ),
        (
            task_view_header.replace(
                "- repo: `jarvis-core`", "- bogus: `x`"
            ).encode("utf-8") + bullet_body,
            "invalid",
            "unsupported_field",
        ),
    ):
        bounded_view = probe_bounded_read(probe_bytes)
        assert not isinstance(bounded_view, str), bounded_view
        assert bounded_view["parse_state"] == expected_state
        if expected_reason is None:
            assert bounded_view["group_id"] != "metadata_review"
        else:
            assert bounded_view["reason_code"] == expected_reason
            assert bounded_view["group_id"] == "metadata_review"

    # the terminator line decides: reachable whole inside the prefix, or not
    terminator_line = b"## Body\n"
    for terminator_end in range(OVERVIEW_SNIPPET_BYTES - 3, OVERVIEW_SNIPPET_BYTES + 4):
        lead_length = terminator_end - len(header_bytes) - len(terminator_line) - 8
        assert lead_length >= 0
        sweep_bytes = (
            b"<!--" + b"p" * lead_length + b"-->\n"
            + header_bytes
            + terminator_line
            + b"tail padding\n" * 400
        )
        assert len(sweep_bytes) > OVERVIEW_SNIPPET_BYTES
        sweep_view = probe_bounded_read(sweep_bytes)
        if terminator_end <= OVERVIEW_SNIPPET_BYTES:
            assert not isinstance(sweep_view, str), terminator_end
            assert sweep_view["parse_state"] == "valid"
        else:
            assert sweep_view == "fail_closed", terminator_end

    # a multi-byte character split by the bound must never reach the decoder:
    # the header block closed long before it, so only that block is decoded
    multibyte_base = header_bytes + b"\n## Body\n"
    multibyte_bytes = (
        multibyte_base
        + b"x" * ((OVERVIEW_SNIPPET_BYTES - len(multibyte_base) - 1) % 3)
        + "가".encode("utf-8") * 2000
    )
    assert len(multibyte_bytes) > OVERVIEW_SNIPPET_BYTES
    try:
        multibyte_bytes[:OVERVIEW_SNIPPET_BYTES].decode("utf-8", errors="strict")
        raise AssertionError("multi-byte probe must straddle the bound")
    except UnicodeDecodeError:
        pass
    multibyte_view = probe_bounded_read(multibyte_bytes)
    assert not isinstance(multibyte_view, str), multibyte_view
    assert multibyte_view["parse_state"] == "valid"

    # a header block wider than the bound, and invalid UTF-8 inside one
    assert probe_bounded_read(
        header_bytes
        + b"- source_command: `" + b"x" * OVERVIEW_SNIPPET_BYTES + b"`\n"
        + b"\n## Body\n"
    ) == "fail_closed"
    assert probe_bounded_read(
        task_view_header.replace("- title: `probe`", "- title: `\udc80`").encode(
            "utf-8", errors="surrogateescape"
        )
        + b"\n## Body\n"
    ) == "invalid_utf8"

    with tempfile.TemporaryDirectory() as missing_dir:
        try:
            read_task_view_text(Path(missing_dir) / task_view_name)
            raise AssertionError("a missing Task file must not read as text")
        except OSError:
            pass

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
    assert voice_memory["task_candidate"]["suggested_skill"] == "tasks_reports"
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
    assert len(status["skills"]) == 5
    assert "jarvis.bat" in status["protected_paths"]
    assert status["safety"][0] == (
        "Task discovery and basic details are read-only. Create Local Task "
        "creates one local TODO from Voice Inbox; Start / Complete changes "
        "only status and updated_at; Record Completion Evidence appends one "
        "evidence value and updates only updated_at for an eligible DOING "
        "Task. Every Task preview remains write-free. Every write requires "
        "Preview and explicit Confirm. Evidence is not validated, status "
        "stays DOING, and no flow executes or automatically completes Task "
        "work. Jarvis does not create approvals or reports, run skills, "
        "commit, push, or make external calls."
    )
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
    assert overview["project_control"]["version"] == "project_control.v0.1F"
    assert overview["project_control"]["mode"] == "read-only"
    assert overview["project_control"]["source"] == "docs/master-plan.md"
    assert len(overview["project_control"]["project_cards"]) == 1
    owner_card = overview["project_control"]["project_cards"][0]
    assert owner_card["project_id"] == "jarvis-core"
    assert owner_card["branch"] == overview["repo"]["branch"]
    assert owner_card["live_head"] == overview["repo"]["head_short"]
    assert owner_card["known_protected_untracked"] == ["jarvis.bat"]
    assert owner_card["validation_commands"] == ["git status --short", "git diff --check"]
    assert owner_card["owner_summary"]["current_reason"]
    assert owner_card["owner_summary"]["owner_outcome"]
    assert owner_card["owner_summary"]["approval_state"] in MASTER_PLAN_APPROVAL_STATES
    assert [item["workstream_id"] for item in owner_card["workstreams"]] == [
        "hermes-manager",
        "memory-skills",
        "jarvis-console",
        "research-council",
        "daily-ai-radar",
        "task-discord-dashboard",
    ]
    assert all(item["read_only"] is True for item in owner_card["workstreams"])
    director_report_payload = owner_card["director_report"]
    assert director_report_payload["contract_type"] == "jarvis_director_report"
    assert director_report_payload["version"] == "0.1A"
    assert director_report_payload["source_contract_type"] == "hermes_manager_report"
    assert director_report_payload["derived_view"] is True
    assert director_report_payload["read_only"] is True
    assert (
        director_report_payload["authority_boundary"]
        == "derived_owner_summary_only"
    )
    assert director_report_payload["completed_packages"]
    assert "evidence_summary" not in director_report_payload
    manager_report_payload = owner_card["manager_report"]
    assert manager_report_payload["contract_type"] == "hermes_manager_report"
    assert manager_report_payload["version"] == "0.1A"
    assert manager_report_payload["source_of_truth"] == "master_plan"
    assert manager_report_payload["derived_view"] is True
    assert manager_report_payload["read_only"] is True
    assert manager_report_payload["authority_boundary"] == "derived_reporting_only"
    assert manager_report_payload["completed_work_packages"]
    assert (
        director_report_payload["status"]
        == manager_report_payload["status"]
    )
    assert (
        director_report_payload["owner_action"]
        == manager_report_payload["owner_action"]
    )
    assert (
        director_report_payload["owner_decision"]
        == manager_report_payload["owner_decision"]
    )
    current_snapshot = read_master_plan_snapshot()
    reporting_evidence = owner_card["recent_milestone_evidence"]
    available_hashes = {
        overview["repo"]["head"],
        *[commit["hash"] for commit in reporting_evidence["commits"]],
    }
    # task-0126: historical evidence is verified by branch ancestry, so the
    # expectation no longer depends on which commits happen to be recent.
    expected_missing_references = []
    verified_head = current_snapshot["verified_implementation_head"]
    if not commit_is_branch_ancestor(verified_head):
        expected_missing_references.append(
            "Verified implementation HEAD is absent from live Git evidence"
        )
    expected_missing_references.extend(
        (
            f"Checkpoint package {package['work_package_id']} commit is absent "
            "from Git evidence"
        )
        for package in current_snapshot["manager_reporting_work_packages"]
        if not commit_is_branch_ancestor(package["commit_hash"])
    )
    if expected_missing_references:
        assert manager_report_payload["source_conflicts"]
        assert manager_report_payload["status"] == "blocked"
        assert manager_report_payload["owner_action"] == "decision_required"
        assert manager_report_payload["owner_decision"]
        assert owner_card["status"] == "attention"
        assert all(
            conflict in manager_report_payload["source_conflicts"]
            for conflict in expected_missing_references
        )
        assert all(
            conflict in owner_card["attention_reasons"]
            for conflict in manager_report_payload["source_conflicts"]
        )
    elif current_snapshot["approval_state"] == "none":
        assert manager_report_payload["source_conflicts"] == []
        assert manager_report_payload["owner_action"] == "none"
        assert manager_report_payload["owner_decision"] == ""
        assert owner_card["status"] == "observed"
        assert owner_card["attention_reasons"] == []
    owner_decision_payload = owner_card["owner_decision"]
    assert owner_decision_payload["contract_type"] == "jarvis_owner_decision"
    assert owner_decision_payload["version"] == "0.1A"
    assert owner_decision_payload["status"] == "selection_required"
    assert owner_decision_payload["authority_boundary"] == "work_package_proposal_only"
    assert owner_decision_payload["recommended_workstream_id"] == read_master_plan_snapshot()[
        "owner_decision_recommended_workstream_id"
    ]
    assert owner_decision_payload["selected_workstream_id"] is None
    assert owner_decision_payload["read_only"] is True
    assert len(owner_decision_payload["candidates"]) == 6
    recent_evidence = owner_card["recent_milestone_evidence"]
    assert recent_evidence["contract_type"] == "jarvis_recent_milestone_evidence"
    assert recent_evidence["version"] == "0.1"
    assert recent_evidence["observed_head"] == overview["repo"]["head"]
    assert recent_evidence["head_matches_latest_commit"] is True
    assert 1 <= len(recent_evidence["commits"]) <= 5
    assert recent_evidence["commits"][0]["is_head"] is True
    assert all(commit["read_only"] is True for commit in recent_evidence["commits"])
    assert all(not commit["protected_path_present"] for commit in recent_evidence["commits"])
    assert owner_card["locked_capabilities"] == owner_card["forbidden_actions"]
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

    assert parse_json_body(b"{not json")[0] == HTTPStatus.BAD_REQUEST
    assert not (APP_ROOT / "state").exists()
    assert not (APP_ROOT / "examples" / "memory-skills-sample.json").exists()
    assert not (REPO_ROOT / ".jarvis-local").exists()
    assert not (REPO_ROOT / "memory" / "skills").exists()
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "Chat / Command" in html
    assert "Voice Inbox" in html
    assert "Skills" in html
    assert "Hermes Manager" in html
    assert "Project Control" in html
    assert "Owner-facing local project dashboard" in html
    assert "Research Council" in html
    assert "Daily AI Radar" in html
    assert "Project Control" in html
    assert "Checkpoints / History" in html
    assert "Settings" in html
    assert "skillGrid" in html
    assert "skillDetail" in html
    assert "Select a skill to inspect commands" in html
    assert (
        "Safety mode: Task discovery and basic details are read-only. Create "
        "Local Task creates one local TODO from Voice Inbox; Start / Complete "
        "changes only status and "
        "updated_at; Record Completion Evidence appends one evidence value and "
        "updates only updated_at for an eligible DOING Task. Every Task "
        "preview remains write-free. Every write requires Preview and "
        "explicit Confirm. Evidence is not validated, status stays DOING, and "
        "no flow executes or automatically completes Task work. Jarvis does not "
        "create approvals or reports, run skills, commit, push, or make external "
        "calls."
    ) in html
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
    assert "Refresh Project Control" in html
    assert "Refresh History" in html
    assert "Owner-facing local project dashboard" in html
    assert (
        "Task discovery and basic details are read-only. Create Local Task "
        "creates one local TODO from Voice Inbox; Start / Complete changes "
        "only status and updated_at; "
        "Record Completion Evidence appends one evidence value and updates only "
        "updated_at for an eligible DOING Task. Every Task "
        "preview remains write-free. Every write requires Preview and explicit "
        "Confirm. Evidence is not validated, status stays DOING, and no flow "
        "executes or automatically completes Task work. Jarvis Console does not "
        "create approvals or reports, run skills, commit, push, or make external "
        "calls."
    ) in html
    assert "does not create commits" in html

    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "fetch(" in app_js
    assert "/api/status" in app_js
    assert "/api/skill" in app_js
    assert "/api/overview" in app_js
    assert "renderProjectControl" in app_js
    assert "renderRecentMilestoneEvidence" in app_js
    assert "jarvis_recent_milestone_evidence" in app_js
    assert "최근 로컬 작업 증거" in app_js
    assert "HEAD verified" in app_js
    assert "작업 증거 요약" in app_js
    assert "현재 만드는 이유" in app_js
    assert "이 단계가 끝나면 사용자가 얻는 것" in app_js
    assert "Jarvis-Core 내부 workstream" in app_js
    assert "승인 필요 여부" in app_js
    assert "잠긴 기능" in app_js
    assert (
        "Project Control overview refreshed: read-only discovery with "
        "confirmed status transitions only."
    ) in app_js
    assert "/api/history" in app_js
    assert "/api/voice-inbox/prepare" in app_js
    assert "renderOverview" in app_js
    assert "renderHistory" in app_js
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
    assert not re.search(r"<button[^>]*>[^<]*Refresh Project Control", app_js)
    assert "overview-refresh" not in app_js
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
    for fallback_element_id in (
        "manualCopyFallback",
        "manualCopyFallbackText",
        "manualCopyFallbackClose",
    ):
        assert f'getElementById("{fallback_element_id}")' in app_js
        assert f'id="{fallback_element_id}"' in html
    assert "showManualCopyFallback(" in app_js
    assert "hideManualCopyFallback(" in app_js
    assert "readonly" in html
    assert "Copy Cleaned Task" in app_js
    assert "Copy As Jarvis Command" in app_js
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
