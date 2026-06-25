"""Local browser shell for Jarvis Console v0.1."""

from __future__ import annotations

import argparse
import inspect
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlparse
import webbrowser


APP_ROOT = Path(__file__).resolve().parent
WEB_ROOT = APP_ROOT / "web"
REGISTRY_PATH = APP_ROOT / "skills.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8790
MAX_JSON_BODY_BYTES = 64_000
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

    assert suggest_skill("idea MVP validation")["recommended_skill"] == "research_council"
    assert suggest_skill("Codex commit review")["recommended_skill"] == "hermes_manager"
    assert suggest_skill("MCP Agent Skills new technology")["recommended_skill"] == "daily_ai_radar"
    assert suggest_skill("remember this repeated workflow as a skill")["recommended_skill"] == "memory_skills"
    assert suggest_skill("make this better somehow")["recommended_skill"] == "unknown"
    assert suggest_skill("\uc544\uc774\ub514\uc5b4 MVP \uac80\uc99d")["recommended_skill"] == "research_council"
    assert suggest_skill("Codex \ucee4\ubc0b \ub9ac\ubdf0")["recommended_skill"] == "hermes_manager"
    assert suggest_skill("MCP Agent Skills \uc0c8 \uae30\uc220")["recommended_skill"] == "daily_ai_radar"
    assert suggest_skill("\ubc18\ubcf5 \uc791\uc5c5 skill\ub85c \uae30\uc5b5")["recommended_skill"] == "memory_skills"

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

    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "Chat / Command" in html
    assert "Skills" in html
    assert "Hermes Manager" in html
    assert "Research Council" in html
    assert "Daily AI Radar" in html
    assert "Tasks / Reports" in html
    assert "Memory / Skills" in html
    assert "Settings" in html
    assert "skillGrid" in html
    assert "skillDetail" in html
    assert "Select a skill to inspect commands" in html
    assert "Safety mode: Jarvis only recommends. It does not run tools." in html
    assert "Local-only" in html
    assert "No automatic Codex / ChatGPT / Hermes invocation" in html
    assert "What do you want Jarvis to help with?" in html
    assert "jarvis.bat" in html

    app_js = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
    assert "fetch(" in app_js
    assert "/api/status" in app_js
    assert "/api/skill" in app_js
    assert "renderSkillCards" in app_js
    assert "renderSkillDetail" in app_js
    assert "action_guide" in app_js
    assert "What it does" in app_js
    assert "When to use" in app_js
    assert "Next action" in app_js
    assert "Commands" in app_js
    assert "selectedSkillId" in app_js
    assert "selected-skill" in app_js
    assert "navigator.clipboard.writeText" in app_js
    assert "copy-command" in app_js
    assert "Git Bash" in app_js
    assert "PowerShell" in app_js
    assert "http://" not in app_js
    assert "https://" not in app_js
    assert "cdn" not in app_js.lower()
    assert "child_process" not in app_js
    assert "exec(" not in app_js
    assert "spawn(" not in app_js

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
        "git" + " checkout",
        "git" + " reset",
        "git" + " clean",
        "git" + " rm",
        "git" + " stash",
        "invoke-" + "webrequest",
        "invoke-" + "restmethod",
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
