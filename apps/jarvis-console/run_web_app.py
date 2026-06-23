"""Local browser shell for Jarvis Console v0.1."""

from __future__ import annotations

import argparse
import inspect
import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import webbrowser


APP_ROOT = Path(__file__).resolve().parent
WEB_ROOT = APP_ROOT / "web"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8790
MAX_JSON_BODY_BYTES = 64_000
PROTECTED_PATHS = ("jarvis.bat",)


@dataclass(frozen=True)
class SkillInfo:
    skill_id: str
    display_name: str
    status: str
    purpose: str
    safe_next_action: str
    commands: tuple[str, ...]
    route_keywords: tuple[str, ...]


SKILLS: tuple[SkillInfo, ...] = (
    SkillInfo(
        skill_id="hermes_manager",
        display_name="Hermes Manager",
        status="available",
        purpose="Manage Codex/ChatGPT workflow prompts, reviews, commit prompts, and checkpoints.",
        safe_next_action="Open Hermes Manager separately, then copy/paste prompts manually.",
        commands=(
            "Git Bash: python -B apps/hermes-manager-pilot/run_web_app.py",
            "PowerShell: python -B apps\\hermes-manager-pilot\\run_web_app.py",
        ),
        route_keywords=(
            "codex",
            "commit",
            "review",
            "readme",
            "repo",
            "repository",
            "git",
            "pull request",
            "pr",
            "task prompt",
            "commit prompt",
            "hermes manager",
            "workflow manager",
            "\ucee4\ubc0b",
            "\ub9ac\ubdf0",
            "\uc791\uc5c5\uad00\ub9ac",
            "\uc800\uc7a5\uc18c",
        ),
    ),
    SkillInfo(
        skill_id="research_council",
        display_name="Research Council",
        status="available",
        purpose="Evaluate ideas, MVP assumptions, evidence gaps, risks, and experiment plans.",
        safe_next_action="Run the Research Council local launcher or prepare a bounded research input.",
        commands=(
            "Git Bash: python -B apps/research-council/run_local_app.py",
            "PowerShell: python -B apps\\research-council\\run_local_app.py",
        ),
        route_keywords=(
            "idea",
            "mvp",
            "validate",
            "validation",
            "experiment",
            "evidence",
            "risk",
            "business",
            "startup",
            "assumption",
            "research council",
            "\uc544\uc774\ub514\uc5b4",
            "\uac80\uc99d",
            "\uc2e4\ud5d8",
            "\uc99d\uac70",
            "\ub9ac\uc2a4\ud06c",
            "\uc0ac\uc5c5",
            "\uac00\uc124",
        ),
    ),
    SkillInfo(
        skill_id="daily_ai_radar",
        display_name="Daily AI Radar",
        status="available",
        purpose="Scout curated AI, agent, framework, protocol, and platform technology candidates.",
        safe_next_action="Prepare curated source metadata and run the Daily AI Radar renderer manually.",
        commands=(
            "Git Bash: python -B apps/daily-ai-radar/run_demo.py --input apps/daily-ai-radar/examples/sample-input.json",
            "PowerShell: python -B apps\\daily-ai-radar\\run_demo.py --input apps\\daily-ai-radar\\examples\\sample-input.json",
        ),
        route_keywords=(
            "ai technology",
            "new technology",
            "new tech",
            "mcp",
            "a2a",
            "hermes",
            "agent skills",
            "agent skill",
            "langgraph",
            "openai agents",
            "anthropic",
            "framework",
            "platform",
            "daily radar",
            "daily ai radar",
            "technology scout",
            "\uae30\uc220",
            "\uc0c8 \uae30\uc220",
            "\ub3d9\ud5a5",
            "\uc5d0\uc774\uc804\ud2b8",
            "\ud504\ub808\uc784\uc6cc\ud06c",
        ),
    ),
    SkillInfo(
        skill_id="memory_skills",
        display_name="Memory / Skills",
        status="planned",
        purpose="Track repeated workflow candidates, approved skills, and Jarvis operating rules.",
        safe_next_action="Capture the workflow as a proposal only; do not install or update a skill automatically.",
        commands=(),
        route_keywords=(
            "memory",
            "skill",
            "skills",
            "repeated task",
            "routine",
            "operating rule",
            "personal context",
            "\uae30\uc5b5",
            "\ubc18\ubcf5",
            "\uc2a4\ud0ac",
            "\uc6b4\uc601 \uaddc\uce59",
        ),
    ),
)

UNKNOWN_SUGGESTION = {
    "recommended_skill": "unknown",
    "display_name": "Manual choice needed",
    "reason": "No deterministic keyword rule matched the message.",
    "suggested_next_action": "Choose a skill manually from the sidebar and keep the approval boundary visible.",
    "commands": [],
}

STATIC_ROUTES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/web/index.html": ("index.html", "text/html; charset=utf-8"),
    "/web/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/web/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


def skill_payload(skill: SkillInfo) -> dict[str, Any]:
    """Return public metadata for a skill card or API response."""

    return {
        "skill_id": skill.skill_id,
        "display_name": skill.display_name,
        "status": skill.status,
        "purpose": skill.purpose,
        "safe_next_action": skill.safe_next_action,
        "commands": list(skill.commands),
        "does_not_auto_run": True,
    }


def status_payload() -> dict[str, Any]:
    """Return deterministic local console status metadata."""

    return {
        "ok": True,
        "console": "jarvis-console",
        "version": "0.1",
        "mode": "local-only",
        "host": DEFAULT_HOST,
        "default_port": DEFAULT_PORT,
        "protected_paths": list(PROTECTED_PATHS),
        "safety": [
            "Safety mode: Jarvis only recommends. It does not run tools.",
            "Local-only",
            "No automatic Codex / ChatGPT / Hermes invocation",
            "No commit or push",
            "No external network/API/LLM calls",
            "Human approval required before implementation",
        ],
        "skills": [skill_payload(skill) for skill in SKILLS],
    }


def normalize_message(message: str) -> str:
    """Normalize user text for deterministic keyword matching."""

    return " ".join(str(message).strip().lower().split())


def suggest_skill(message: str) -> dict[str, Any]:
    """Suggest one skill with deterministic keyword matching only."""

    normalized = normalize_message(message)
    if not normalized:
        return dict(UNKNOWN_SUGGESTION)

    best_skill: SkillInfo | None = None
    best_hits: list[str] = []
    for skill in SKILLS:
        hits = [keyword for keyword in skill.route_keywords if keyword in normalized]
        if len(hits) > len(best_hits):
            best_skill = skill
            best_hits = hits

    if best_skill is None or not best_hits:
        return dict(UNKNOWN_SUGGESTION)

    return {
        "recommended_skill": best_skill.skill_id,
        "display_name": best_skill.display_name,
        "reason": f"Matched deterministic keyword(s): {', '.join(best_hits[:5])}.",
        "suggested_next_action": best_skill.safe_next_action,
        "commands": list(best_skill.commands),
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


def handle_get_api(path: str) -> tuple[int, dict[str, Any]]:
    """Handle read-only GET API routes."""

    if path == "/api/status":
        return HTTPStatus.OK, status_payload()
    return HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"}


def handle_post_api(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Handle POST API routes without running external tools."""

    if path == "/api/suggest-skill":
        suggestion = suggest_skill(str(payload.get("message", "")))
        return HTTPStatus.OK, {"ok": True, **suggestion}
    return HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"}


class JarvisConsoleHandler(BaseHTTPRequestHandler):
    """Small local-only request handler for Jarvis Console."""

    server_version = "JarvisConsole/0.1"

    def do_GET(self) -> None:
        if not self._client_is_local():
            self._send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "local_clients_only"})
            return

        path = urlparse(self.path).path
        if path.startswith("/api/"):
            status, payload = handle_get_api(path)
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
        if path != "/api/suggest-skill":
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

    assert suggest_skill("idea MVP validation")["recommended_skill"] == "research_council"
    assert suggest_skill("Codex commit review")["recommended_skill"] == "hermes_manager"
    assert suggest_skill("MCP Agent Skills new technology")["recommended_skill"] == "daily_ai_radar"
    assert suggest_skill("remember this repeated workflow as a skill")["recommended_skill"] == "memory_skills"
    assert suggest_skill("make this better somehow")["recommended_skill"] == "unknown"
    assert suggest_skill("\uac04\ub2e8\ud55c \uc544\uc774\ub514\uc5b4 MVP \uac80\uc99d\ud574\uc918")["recommended_skill"] == "research_council"
    assert suggest_skill("Codex \ucee4\ubc0b \ub9ac\ubdf0 \ub3c4\uc640\uc918")["recommended_skill"] == "hermes_manager"
    assert suggest_skill("MCP Agent Skills \uc0c8 \uae30\uc220 \ucc3e\uc544\ubd10")["recommended_skill"] == "daily_ai_radar"
    assert suggest_skill("\ubc18\ubcf5 \uc791\uc5c5 skill\ub85c \uae30\uc5b5\ud574\uc918")["recommended_skill"] == "memory_skills"

    status = status_payload()
    skill_ids = {skill["skill_id"] for skill in status["skills"]}
    assert {"research_council", "daily_ai_radar", "hermes_manager"}.issubset(skill_ids)
    assert "jarvis.bat" in status["protected_paths"]
    hermes_commands = suggest_skill("Codex commit review")["commands"]
    assert any(command.startswith("Git Bash:") for command in hermes_commands)
    assert any("apps/hermes-manager-pilot/run_web_app.py" in command for command in hermes_commands)
    assert any(command.startswith("PowerShell:") for command in hermes_commands)

    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "Chat / Command" in html
    assert "Skills" in html
    assert "Hermes Manager" in html
    assert "Research Council" in html
    assert "Daily AI Radar" in html
    assert "Tasks / Reports" in html
    assert "Memory / Skills" in html
    assert "Settings" in html
    assert "Safety mode: Jarvis only recommends. It does not run tools." in html
    assert "Local-only" in html
    assert "No automatic Codex / ChatGPT / Hermes invocation" in html
    assert "What do you want Jarvis to help with?" in html
    assert "jarvis.bat" in html

    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "fetch(" in app_js
    assert "http://" not in app_js
    assert "https://" not in app_js
    assert "cdn" not in app_js.lower()

    styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
    assert "http://" not in styles
    assert "https://" not in styles

    assert handle_get_api("/api/missing")[0] == HTTPStatus.NOT_FOUND
    assert handle_post_api("/api/missing", {})[0] == HTTPStatus.NOT_FOUND
    assert parse_json_body(b"{not json")[0] == HTTPStatus.BAD_REQUEST

    source = Path(__file__).read_text(encoding="utf-8")
    forbidden_source_patterns = (
        "shell" + "=True",
        "sub" + "process",
        "os." + "system",
        "git" + " add",
        "git" + " commit",
        "git" + " push",
        "git" + " reset",
        "git" + " clean",
        "git" + " rm",
        "git" + " stash",
    )
    assert all(pattern not in source for pattern in forbidden_source_patterns)
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
