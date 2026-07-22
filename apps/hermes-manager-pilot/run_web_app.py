"""Local browser UI for Hermes Manager Pilot v0.5."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import inspect
import json
from pathlib import Path
import secrets
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
import webbrowser

from hermes_manager_pilot.prompt_renderer import render_mode
from hermes_manager_pilot.review_handoff import (
    HANDOFF_ENDPOINT,
    build_copy_only_review_handoff,
    render_copy_only_review_handoff,
)
from hermes_manager_pilot.review_lifecycle import (
    ReviewLifecycleError,
    ReviewLifecycleService,
    delete_preview_to_dict,
    recovery_inspection_to_dict,
    save_preview_to_dict,
)
from hermes_manager_pilot.review_record import review_record_to_dict
from hermes_manager_pilot.schemas import ValidationError, normalize_session_state


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent.parent
WEB_ROOT = APP_ROOT / "web"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
SESSION_TYPE = "hermes_manager_session_state"
SESSION_VERSION = "0.2"
LOCAL_SESSION_ENDPOINT = "/api/local-session"
LOCAL_SESSION_HEADER = "X-Hermes-Local-Session"
NEEDS_USER_CONFIRMATION = "NEEDS_USER_CONFIRMATION: confirm target files before rendering a task prompt"
WIZARD_STEPS = (
    "Describe Task",
    "Confirm Scope",
    "Copy Task Prompt",
    "Paste Codex Result",
    "Copy Review Prompt",
    "Approve Commit",
    "Copy Commit Prompt",
    "Checkpoint",
)
WIZARD_TRANSITIONS = {
    "initial": 1,
    "prepare-session": 2,
    "continue-to-task-prompt": 3,
    "copy-task-prompt": 4,
    "paste-result": 5,
    "copy-review-prompt": 6,
    "approve-commit": 7,
    "copy-commit-prompt": 8,
    "checkpoint": 8,
}

ALLOWED_READ_ONLY_GIT_ARGS = frozenset(
    {
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("rev-parse", "HEAD"),
        ("status", "--short"),
    }
)

DEFAULT_VALIDATION_COMMANDS = (
    "python -B -m py_compile apps\\hermes-manager-pilot\\run_web_app.py apps\\hermes-manager-pilot\\run_local_app.py apps\\hermes-manager-pilot\\run_demo.py apps\\hermes-manager-pilot\\run_smoke_tests.py apps\\hermes-manager-pilot\\hermes_manager_pilot\\schemas.py apps\\hermes-manager-pilot\\hermes_manager_pilot\\pipeline.py apps\\hermes-manager-pilot\\hermes_manager_pilot\\prompt_renderer.py",
    "python -B apps\\hermes-manager-pilot\\run_web_app.py --self-test",
    "python -B apps\\hermes-manager-pilot\\run_local_app.py --self-test",
    "python -B apps\\hermes-manager-pilot\\run_smoke_tests.py",
    "python -B apps\\research-council\\run_smoke_tests.py",
    "python -B apps\\daily-ai-radar\\run_smoke_tests.py",
    "git diff --check",
)

STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/web/index.html": ("index.html", "text/html; charset=utf-8"),
    "/web/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/web/styles.css": ("styles.css", "text/css; charset=utf-8"),
}

API_ROUTES = {
    "/api/prepare",
    "/api/render",
    "/api/git-status",
    HANDOFF_ENDPOINT,
    "/api/validate-session",
    "/api/reviews/list",
    "/api/reviews/save-preview",
    "/api/reviews/save-confirm",
    "/api/reviews/reopen",
    "/api/reviews/recovery",
    "/api/reviews/delete-preview",
    "/api/reviews/delete-confirm",
}

REVIEW_LIFECYCLE_ROUTES = frozenset(
    route for route in API_ROUTES if route.startswith("/api/reviews/")
)
LOCAL_SESSION_ID = secrets.token_urlsafe(32)


def default_session_state(repo: str | None = None) -> dict[str, Any]:
    """Return a conservative in-memory session state for the browser UI."""

    repo_path = repo or str(REPO_ROOT)
    return {
        "session_type": SESSION_TYPE,
        "version": SESSION_VERSION,
        "repo": repo_path,
        "branch": "main",
        "head": "unknown",
        "working_tree_status": "Manual entry. Use Load Git Status for a read-only refresh.",
        "current_goal": "Complete a bounded Codex task from Browser Guided UI.",
        "active_task": "Describe the next Codex task here.",
        "blocked_by": "",
        "last_codex_prompt": "",
        "last_codex_result_summary": "",
        "validation_commands": list(DEFAULT_VALIDATION_COMMANDS),
        "files_touched": ["apps/hermes-manager-pilot/"],
        "target_files": ["apps/hermes-manager-pilot/"],
        "protected_paths": ["jarvis.bat"],
        "commit_allowed": False,
        "push_allowed": False,
        "human_approval_required": True,
        "human_approval_granted": False,
        "next_action": "PROMPT_FOR_CODEX",
        "commit_message": "hermes-manager-pilot: update browser guided UI",
    }


def prepare_session(task: str, repo: str | None = None) -> dict[str, Any]:
    """Prepare deterministic session metadata from a single task sentence."""

    normalized_task = " ".join(str(task).strip().split())
    if not normalized_task:
        raise ValidationError("task is required")

    target_files = infer_target_files(normalized_task)
    session = default_session_state(repo)
    session.update(
        {
            "current_goal": "Complete a bounded Codex task from Browser Guided UI.",
            "active_task": normalized_task,
            "files_touched": list(target_files),
            "target_files": list(target_files),
            "commit_message": infer_commit_message(normalized_task, target_files),
            "commit_allowed": False,
            "human_approval_granted": False,
            "push_allowed": False,
            "next_action": "PROMPT_FOR_CODEX",
        }
    )
    normalize_session_state(session)
    return session


def infer_target_files(task: str) -> tuple[str, ...]:
    """Infer a conservative target file list from deterministic keyword rules."""

    lower_task = task.lower()
    explicit_paths = extract_explicit_paths(task)
    if explicit_paths:
        return tuple(explicit_paths)

    if any(keyword in lower_task for keyword in ("hermes", "manager", "gui")) and "readme" in lower_task:
        return ("apps/hermes-manager-pilot/README.md",)
    if "daily ai radar" in lower_task or "daily-ai-radar" in lower_task:
        return ("apps/daily-ai-radar/README.md",)
    if "research council" in lower_task or "research-council" in lower_task:
        return ("apps/research-council/",)
    return (NEEDS_USER_CONFIRMATION,)


def extract_explicit_paths(task: str) -> tuple[str, ...]:
    """Extract simple repo-relative paths from a task sentence."""

    prefixes = ("apps/", "tests/", "docs/", "scripts/", ".github/")
    results: list[str] = []
    for raw_token in task.replace("\\", "/").split():
        token = raw_token.strip("`'\".,;:()[]{}<>")
        if token.startswith(prefixes) and token not in results and "jarvis.bat" not in token.lower():
            results.append(token)
    return tuple(results)


def infer_commit_message(task: str, target_files: tuple[str, ...]) -> str:
    """Return a safe deterministic commit message suggestion."""

    lower_task = task.lower()
    if any(path.startswith("apps/hermes-manager-pilot/") for path in target_files):
        if "readme" in lower_task:
            return "hermes-manager-pilot: update browser guided docs"
        return "hermes-manager-pilot: update browser guided UI"
    if any(path.startswith("apps/daily-ai-radar/") for path in target_files):
        return "daily-ai-radar: update documentation"
    if any(path.startswith("apps/research-council/") for path in target_files):
        return "research-council: update documentation"
    return "jarvis-core: update requested task"


def needs_confirmation(session: dict[str, Any]) -> bool:
    """Return true when the prepared target files still need user confirmation."""

    return any(str(path).startswith("NEEDS_USER_CONFIRMATION") for path in session.get("target_files", []))


def render_artifact(mode: str, session_data: dict[str, Any]) -> str:
    """Validate and render a deterministic Markdown artifact."""

    session = dict(session_data)
    session["push_allowed"] = False
    if mode == "implementation-prompt" and needs_confirmation(session):
        raise ValidationError("target files need confirmation before rendering a task prompt")
    if mode == "implementation-prompt":
        session["next_action"] = "PROMPT_FOR_CODEX"
    elif mode == "review-prompt":
        session["next_action"] = "REVIEW_REQUEST"
    elif mode == "commit-prompt":
        session["next_action"] = "COMMIT_REQUEST"
    elif mode == "checkpoint-summary":
        session["next_action"] = "STATUS_SUMMARY"
    normalized = normalize_session_state(session)
    return render_mode(normalized, mode)


def load_git_status(repo_path: str | Path) -> dict[str, str]:
    """Read repo state with read-only git commands."""

    repo_text = str(repo_path).strip()
    if not repo_text:
        raise ValidationError("repo path is required")
    repo = Path(repo_text)
    _run_read_only_git(repo, ("rev-parse", "--show-toplevel"))
    branch = _run_read_only_git(repo, ("rev-parse", "--abbrev-ref", "HEAD"))
    head = _run_read_only_git(repo, ("rev-parse", "HEAD"))
    status = _run_read_only_git(repo, ("status", "--short"))
    return {
        "branch": branch or "unknown",
        "head": head or "unknown",
        "working_tree_status": status or "clean",
    }


def load_current_review_git_snapshot() -> dict[str, Any]:
    """Return fresh trusted Git metadata in the Review Record contract shape."""

    git_state = load_git_status(REPO_ROOT)
    status_text = git_state["working_tree_status"]
    return {
        "branch": git_state["branch"],
        "head": git_state["head"],
        "status": [] if status_text == "clean" else status_text.splitlines(),
    }


REVIEW_LIFECYCLE = ReviewLifecycleService(
    trusted_repo_root=REPO_ROOT,
    git_snapshot_loader=load_current_review_git_snapshot,
)


def prepare_copy_only_review_handoff(
    session_data: dict[str, Any],
    *,
    scope_confirmed: bool,
    trusted_repo_root: str | Path = REPO_ROOT,
) -> tuple[dict[str, Any], str]:
    """Build a human-copyable review envelope from fresh read-only Git state."""

    git_state = load_git_status(trusted_repo_root)
    handoff = build_copy_only_review_handoff(
        session_data,
        git_state,
        trusted_repo_root=trusted_repo_root,
        scope_confirmed=scope_confirmed,
    )
    return handoff, render_copy_only_review_handoff(handoff)


def _run_read_only_git(repo: Path, args: tuple[str, ...]) -> str:
    if args not in ALLOWED_READ_ONLY_GIT_ARGS:
        raise ValidationError(f"git command is not allowed: git {' '.join(args)}")
    completed = subprocess.run(
        ("git", *args),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ValidationError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return _normalize_read_only_git_output(args, completed.stdout)


def _normalize_read_only_git_output(args: tuple[str, ...], output: str) -> str:
    """Preserve porcelain status columns while trimming command line endings."""

    if args == ("status", "--short"):
        return output.rstrip("\r\n")
    return output.strip()


def parse_json_body(raw_body: bytes) -> tuple[int, dict[str, Any]]:
    """Parse request JSON and return status plus payload or safe error."""

    try:
        value = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "malformed_json"}
    if not isinstance(value, dict):
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "json_body_must_be_object"}
    return HTTPStatus.OK, value


def handle_api_request(
    path: str,
    payload: dict[str, Any],
    *,
    lifecycle: ReviewLifecycleService | None = None,
    local_session_id: str = "",
) -> tuple[int, dict[str, Any]]:
    """Handle API routes without touching external services."""

    try:
        if path == "/api/prepare":
            session = prepare_session(str(payload.get("task", "")), str(payload.get("repo") or REPO_ROOT))
            return HTTPStatus.OK, {
                "ok": True,
                "session": session,
                "needs_confirmation": needs_confirmation(session),
                "next_step": wizard_step_after_action("prepare-session"),
                "message": "Prepared session. Confirm target files before copying a task prompt.",
            }
        if path == "/api/render":
            mode = str(payload.get("mode", ""))
            session = payload.get("session")
            if not isinstance(session, dict):
                raise ValidationError("session must be an object")
            artifact = render_artifact(mode, session)
            return HTTPStatus.OK, {
                "ok": True,
                "artifact": artifact,
                "next_step": next_step_for_mode(mode, session),
                "message": next_message_for_mode(mode, session),
            }
        if path == "/api/git-status":
            git_state = load_git_status(str(payload.get("repo") or REPO_ROOT))
            return HTTPStatus.OK, {"ok": True, "git_status": git_state}
        if path == HANDOFF_ENDPOINT:
            if set(payload) != {"session", "scope_confirmed"}:
                raise ValidationError(
                    "review handoff fields must be exactly session and scope_confirmed"
                )
            session = payload.get("session")
            if not isinstance(session, dict):
                raise ValidationError("session must be an object")
            handoff, artifact = prepare_copy_only_review_handoff(
                session,
                scope_confirmed=payload.get("scope_confirmed") is True,
                trusted_repo_root=REPO_ROOT,
            )
            return HTTPStatus.OK, {
                "ok": True,
                "artifact": artifact,
                "item_id": handoff["item_id"],
                "copy_only": True,
                "no_persistence": True,
                "message": (
                    "Jarvis review handoff prepared. Paste it once into Codex Review."
                ),
            }
        if path == "/api/validate-session":
            session = payload.get("session")
            if not isinstance(session, dict):
                raise ValidationError("session must be an object")
            normalized = normalize_session_state({**session, "push_allowed": False})
            return HTTPStatus.OK, {"ok": True, "session": asdict(normalized)}
        service = REVIEW_LIFECYCLE if lifecycle is None else lifecycle
        if path == "/api/reviews/list":
            _require_exact_fields(payload, set(), "review_list")
            return HTTPStatus.OK, {"ok": True, "listing": service.list_saved()}
        if path == "/api/reviews/save-preview":
            _require_exact_fields(
                payload,
                {
                    "session",
                    "result_summary",
                    "scope_confirmed",
                    "privacy_acknowledged",
                    "retention_acknowledged",
                },
                "review_save_preview",
            )
            session = payload.get("session")
            if not isinstance(session, dict):
                raise ReviewLifecycleError("review_session_invalid")
            preview = service.prepare_save(
                session,
                payload.get("result_summary"),
                scope_confirmed=payload.get("scope_confirmed") is True,
                privacy_acknowledged=payload.get("privacy_acknowledged") is True,
                retention_acknowledged=payload.get("retention_acknowledged") is True,
                session_id=local_session_id,
            )
            return HTTPStatus.OK, {"ok": True, "preview": save_preview_to_dict(preview)}
        if path == "/api/reviews/save-confirm":
            _require_exact_fields(payload, {"confirmation_token"}, "review_save_confirm")
            receipt = service.confirm_save(
                payload.get("confirmation_token"),
                session_id=local_session_id,
            )
            return HTTPStatus.OK, {"ok": True, "receipt": receipt}
        if path == "/api/reviews/reopen":
            _require_exact_fields(payload, {"review_id"}, "review_reopen")
            record = service.reopen(payload.get("review_id"))
            return HTTPStatus.OK, {"ok": True, "record": review_record_to_dict(record)}
        if path == "/api/reviews/recovery":
            _require_exact_fields(payload, {"review_id"}, "review_recovery")
            inspection = service.inspect_recovery(payload.get("review_id"))
            return HTTPStatus.OK, {
                "ok": True,
                "inspection": recovery_inspection_to_dict(inspection),
            }
        if path == "/api/reviews/delete-preview":
            _require_exact_fields(payload, {"review_id"}, "review_delete_preview")
            preview = service.prepare_delete(
                payload.get("review_id"),
                session_id=local_session_id,
            )
            return HTTPStatus.OK, {"ok": True, "preview": delete_preview_to_dict(preview)}
        if path == "/api/reviews/delete-confirm":
            _require_exact_fields(
                payload,
                {"confirmation_token", "confirmation_text"},
                "review_delete_confirm",
            )
            receipt = service.confirm_delete(
                payload.get("confirmation_token"),
                payload.get("confirmation_text"),
                session_id=local_session_id,
            )
            return HTTPStatus.OK, {"ok": True, "receipt": receipt}
    except ValidationError as exc:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)}
    except ReviewLifecycleError as exc:
        status = _review_lifecycle_error_status(exc.code)
        response: dict[str, Any] = {"ok": False, "error": exc.code}
        if exc.review_id is not None:
            response["review_id"] = exc.review_id
        return status, response
    return HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"}


def _require_exact_fields(
    payload: dict[str, Any],
    expected: set[str],
    operation: str,
) -> None:
    if set(payload) != expected:
        raise ReviewLifecycleError(f"{operation}_fields_invalid")


def _review_lifecycle_error_status(code: str) -> int:
    if code == "review_record_not_found":
        return HTTPStatus.NOT_FOUND
    if code in {
        "review_record_exists",
        "review_save_outcome_uncertain",
        "review_save_snapshot_stale",
        "review_delete_target_changed",
        "review_record_delete_outcome_uncertain",
        "review_store_recovery_required",
        "review_record_corrupt",
    }:
        return HTTPStatus.CONFLICT
    if code.startswith("review_store_") or code.endswith("_failed"):
        return HTTPStatus.SERVICE_UNAVAILABLE
    return HTTPStatus.BAD_REQUEST


def local_host_header_is_valid(value: str, port: int) -> bool:
    """Accept only the loopback names served by this exact local port."""

    if not isinstance(value, str) or not isinstance(port, int):
        return False
    normalized = value.strip().lower()
    return normalized in {f"127.0.0.1:{port}", f"localhost:{port}"}


def next_step_for_mode(mode: str, session: dict[str, Any]) -> int:
    """Return the wizard step after rendering an artifact."""

    if mode == "implementation-prompt":
        return wizard_step_after_action("copy-task-prompt")
    if mode == "review-prompt":
        return wizard_step_after_action("copy-review-prompt")
    if mode == "commit-prompt":
        return wizard_step_after_action("copy-commit-prompt") if session.get("human_approval_granted") else 7
    if mode == "checkpoint-summary":
        return wizard_step_after_action("checkpoint")
    return wizard_step_after_action("initial")


def wizard_step_after_action(action: str) -> int:
    """Return the browser wizard step after a named action."""

    return WIZARD_TRANSITIONS.get(action, WIZARD_TRANSITIONS["initial"])


def next_message_for_mode(mode: str, session: dict[str, Any]) -> str:
    """Return deterministic next-action copy for the UI."""

    if mode == "implementation-prompt":
        return "Paste this prompt into Codex. After Codex responds, copy the result and come back here."
    if mode == "review-prompt":
        return "Paste the review prompt into Codex. If review passes, continue to approval."
    if mode == "commit-prompt" and session.get("human_approval_granted"):
        return "Paste this commit prompt into Codex. This UI never commits or pushes."
    if mode == "commit-prompt":
        return "Commit is not approved. This prompt tells Codex not to commit."
    if mode == "checkpoint-summary":
        return "Checkpoint summary created."
    return "Ready."


class HermesWebHandler(BaseHTTPRequestHandler):
    """Small local-only request handler for the browser UI."""

    server_version = "HermesManagerPilotWeb/0.5"

    def do_GET(self) -> None:
        if not self._client_is_local():
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "local_clients_only"})
            return
        if not self._host_is_local():
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "local_host_required"})
            return
        if self.path == LOCAL_SESSION_ENDPOINT:
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "local_session_id": LOCAL_SESSION_ID,
                    "expires": "server_restart",
                },
            )
            return
        if self.path not in STATIC_ROUTES:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return
        filename, content_type = STATIC_ROUTES[self.path]
        path = WEB_ROOT / filename
        try:
            content = path.read_bytes()
        except OSError:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if not self._client_is_local():
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "local_clients_only"})
            return
        if not self._host_is_local():
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "local_host_required"})
            return
        if self.path not in API_ROUTES:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return
        if self.path in REVIEW_LIFECYCLE_ROUTES:
            if not self.headers.get("Content-Type", "").lower().startswith(
                "application/json"
            ):
                self._send_json(
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                    {"ok": False, "error": "application_json_required"},
                )
                return
            if self.headers.get("Origin", "") != f"http://{self.headers.get('Host', '')}":
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"ok": False, "error": "same_origin_required"},
                )
                return
            if self.headers.get(LOCAL_SESSION_HEADER, "") != LOCAL_SESSION_ID:
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"ok": False, "error": "local_session_invalid"},
                )
                return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_content_length"})
            return
        if length > 1_000_000:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "request_too_large"})
            return
        status, payload = parse_json_body(self.rfile.read(length))
        if status != HTTPStatus.OK:
            self._send_json(status, payload)
            return
        response_status, response = handle_api_request(
            self.path,
            payload,
            local_session_id=(
                LOCAL_SESSION_ID if self.path in REVIEW_LIFECYCLE_ROUTES else ""
            ),
        )
        self._send_json(response_status, response)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _client_is_local(self) -> bool:
        return self.client_address[0] in {"127.0.0.1", "localhost"}

    def _host_is_local(self) -> bool:
        return local_host_header_is_valid(
            self.headers.get("Host", ""),
            int(self.server.server_port),
        )

    def _send_security_headers(self) -> None:
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(content)


def run_server(port: int, open_browser: bool) -> None:
    """Run the local browser UI server on 127.0.0.1 only."""

    server = ThreadingHTTPServer((DEFAULT_HOST, port), HermesWebHandler)
    url = f"http://{DEFAULT_HOST}:{port}/"
    print(f"Hermes Manager Pilot Browser Guided UI: {url}")
    print("Local-only. Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Hermes Manager Pilot Browser Guided UI.")
    finally:
        server.server_close()


def run_self_test() -> None:
    """Run browser UI helper tests without opening a server."""

    assert DEFAULT_HOST == "127.0.0.1", "server must bind to 127.0.0.1"
    assert local_host_header_is_valid("127.0.0.1:8787", 8787)
    assert local_host_header_is_valid("localhost:8787", 8787)
    assert not local_host_header_is_valid("attacker.example:8787", 8787)
    assert not local_host_header_is_valid("127.0.0.1:9999", 8787)
    assert ALLOWED_READ_ONLY_GIT_ARGS == {
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("rev-parse", "HEAD"),
        ("status", "--short"),
    }, "git allowlist must stay read-only"
    assert _normalize_read_only_git_output(
        ("status", "--short"),
        " M apps/hermes-manager-pilot/run_web_app.py\r\n?? jarvis.bat\r\n",
    ).startswith(" M "), "git status parser must preserve the first porcelain column"
    assert _normalize_read_only_git_output(
        ("rev-parse", "HEAD"),
        "  abc123\r\n",
    ) == "abc123", "non-status Git output must remain compact"
    assert wizard_step_after_action("initial") == 1
    assert len(WIZARD_STEPS) == 8
    assert WIZARD_STEPS[1] == "Confirm Scope"
    assert wizard_step_after_action("prepare-session") == 2
    assert wizard_step_after_action("continue-to-task-prompt") == 3
    assert wizard_step_after_action("copy-task-prompt") == 4
    assert wizard_step_after_action("paste-result") == 5
    assert wizard_step_after_action("copy-review-prompt") == 6
    assert wizard_step_after_action("approve-commit") == 7
    assert wizard_step_after_action("copy-commit-prompt") == 8

    hermes = prepare_session("README에 Hermes GUI 사용법을 초보자도 이해하기 쉽게 추가해줘.")
    assert hermes["target_files"] == ["apps/hermes-manager-pilot/README.md"]
    daily = prepare_session("Daily AI Radar 설명을 보강해줘.")
    assert daily["target_files"] == ["apps/daily-ai-radar/README.md"]
    ambiguous = prepare_session("다음 작업을 더 좋게 만들어줘.")
    assert ambiguous["target_files"] == [NEEDS_USER_CONFIRMATION]
    assert needs_confirmation(ambiguous)
    prepare_status, prepare_payload = handle_api_request(
        "/api/prepare",
        {"task": "Update the Hermes Manager GUI README.", "repo": str(REPO_ROOT)},
    )
    assert prepare_status == HTTPStatus.OK
    assert prepare_payload["next_step"] == 2
    assert prepare_payload["needs_confirmation"] is False

    implementation = render_artifact("implementation-prompt", hermes)
    assert "# Codex Implementation Prompt" in implementation
    review_session = {**hermes, "last_codex_result_summary": "Implemented README update."}
    review = render_artifact("review-prompt", review_session)
    assert "# Codex Review Prompt" in review
    commit_refusal = render_artifact("commit-prompt", hermes)
    assert "Do not commit." in commit_refusal
    approved = {
        **hermes,
        "commit_allowed": True,
        "human_approval_granted": True,
        "commit_message": "hermes-manager-pilot: add browser guided UI",
    }
    commit_prompt = render_artifact("commit-prompt", approved)
    assert "Run `git status --short`." in commit_prompt
    assert "hermes-manager-pilot: add browser guided UI" in commit_prompt
    assert approved["push_allowed"] is False
    assert "jarvis.bat" in approved["protected_paths"]

    blocked_status, blocked = handle_api_request(
        "/api/render",
        {"mode": "implementation-prompt", "session": ambiguous},
    )
    assert blocked_status == HTTPStatus.BAD_REQUEST
    assert blocked["ok"] is False
    assert handle_api_request("/api/unknown", {})[0] == HTTPStatus.NOT_FOUND
    assert parse_json_body(b"{not json")[0] == HTTPStatus.BAD_REQUEST
    assert "shell=True" not in inspect.getsource(_run_read_only_git)

    index_html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "What do you want Codex to do?" in index_html
    assert "Jarvis Console Memory / Skills candidate prompt" in index_html
    assert "Manual review only" in index_html
    assert "nothing runs until you choose the next step" in index_html
    assert "Describe Task" in index_html
    assert "Confirm Scope" in index_html
    assert "Confirm Scope and Continue" in index_html
    assert "Save Review Object and Continue" in index_html
    assert "Clipboard is output only." in index_html
    assert "Copy Jarvis Review Handoff" in index_html
    assert "Generated Output" in index_html
    assert "does not call Codex" in index_html
    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "fetch(" in app_js
    assert "function continueToTaskPrompt()" in app_js
    assert "updateStep(data.next_step || 2)" in app_js
    assert "Target files need confirmation before Step 3." in app_js
    assert HANDOFF_ENDPOINT in app_js
    assert "scopeConfirmed" in app_js
    assert "function copyJarvisReviewHandoff()" in app_js
    assert "function reviewMatchesSession()" in app_js
    assert "state.review = Object.freeze" in app_js
    assert "navigator.clipboard.readText" not in app_js
    print("Hermes Manager Pilot browser UI self-test passed")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Hermes Manager Pilot local browser UI.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Local port to bind on 127.0.0.1.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    parser.add_argument("--self-test", action="store_true", help="Run helper tests without opening the server.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.self_test:
        run_self_test()
        return
    run_server(args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
