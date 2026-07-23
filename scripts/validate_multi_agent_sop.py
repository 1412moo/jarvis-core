"""Deterministically validate Jarvis Multi-Agent SOP v0.1 documents and agents."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".codex" / "agents"

AGENT_SPECS: dict[str, dict[str, Any]] = {
    "manager.toml": {
        "name": "Manager",
        "sandbox_mode": "read-only",
        "required": (
            "WORKER_ORCHESTRATION_OWNER=Manager",
            "Do not modify tracked files",
            "retry_budget=1",
            "repair_budget=1",
            "repair_count=0",
            "exact candidate commit",
            "invalidate all prior Reviewer and QA evidence",
            "Nested spawning is not assumed",
        ),
    },
    "implementer.toml": {
        "name": "Implementer",
        "sandbox_mode": "workspace-write",
        "required": (
            "sole source writer",
            "TRACKED_SOURCE_WRITE=Implementer",
            "exact assigned file scope",
            "candidate local commit",
            "Never use `git add .` or `git add -A`",
            "jarvis.bat",
        ),
    },
    "reviewer.toml": {
        "name": "Reviewer",
        "sandbox_mode": "read-only",
        "required": (
            "strict read-only",
            "exact candidate commit",
            "actionable findings",
            "prior result is invalid",
            "Never orchestrate Workers",
        ),
    },
    "qa.toml": {
        "name": "QA",
        "sandbox_mode": "workspace-write",
        "required": (
            "exact candidate commit",
            "Do not modify tracked source",
            "lightest sufficient QA",
            "do not start a server or browser",
            "prove the owned PID and target listeners are absent",
            "prior result is invalid",
        ),
    },
    "docs.toml": {
        "name": "Docs",
        "sandbox_mode": "workspace-write",
        "required": (
            "only after QA",
            "docs_status=not_required",
            "exact documentation paths",
            "invalidates all prior Reviewer and QA evidence",
            "fresh Reviewer -> QA",
        ),
    },
}

DOCUMENT_MARKERS: dict[str, tuple[str, ...]] = {
    "AGENTS.md": (
        "## 기본 개발 조직: Jarvis Multi-Agent SOP v0.1",
        "Manager만 Worker orchestration 책임을 갖는다",
        "retry_budget=1",
        "repair_budget=1",
        "repair_count=0",
        "candidate commit이",
        "Reviewer와 QA 결과는 전부 무효",
        "budget과 무관한 즉시",
        "Manager의 확정된 assignment plan을 기계적으로 실행",
    ),
    "docs/jarvis-multi-agent-sop-v0.1.md": (
        "# Jarvis Multi-Agent SOP v0.1",
        "Director (primary Codex task)",
        "Worker orchestration의 유일한 논리적 책임자",
        "retry_budget=1",
        "retry_count=0",
        "repair_budget=1",
        "repair_count=0",
        "candidate commit 변경 시 기존 Reviewer/QA 결과는 전부 무효",
        "Budget과 무관한 즉시 escalation",
        "nested spawning을",
        "가정하거나 가장하지 않는다",
        "실제 Implementer candidate",
    ),
    "docs/master-plan.md": (
        "Jarvis Multi-Agent SOP v0.1B",
        "7d4394eed584bc11ee25062a671952b2e4c38b31",
        "Reviewer가 실제 P2 finding 1건",
        "repair 1회",
        "fresh Reviewer와 QA",
        "Director Dashboard v0.1B",
        "실제 기능 work package 1~2개",
        "Hermes 자동 runtime",
    ),
}


def _read_text(relative_path: str, errors: list[str]) -> str:
    path = ROOT / relative_path
    try:
        raw = path.read_bytes()
    except OSError as exc:
        errors.append(f"{relative_path}: unreadable ({exc.__class__.__name__})")
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{relative_path}: not valid UTF-8")
        return ""


def _validate_agents(errors: list[str]) -> None:
    names: list[str] = []
    orchestration_owners: list[str] = []
    source_writers: list[str] = []
    expected_files = sorted(AGENT_SPECS)
    try:
        actual_files = sorted(
            path.name
            for path in AGENT_DIR.iterdir()
            if path.is_file() and path.suffix == ".toml"
        )
    except OSError as exc:
        errors.append(f".codex/agents: unreadable ({exc.__class__.__name__})")
        actual_files = []
    if actual_files != expected_files:
        errors.append(
            f".codex/agents: expected TOML files {expected_files!r}, "
            f"got {actual_files!r}"
        )

    for filename, spec in sorted(AGENT_SPECS.items()):
        relative_path = f".codex/agents/{filename}"
        text = _read_text(relative_path, errors)
        if not text:
            continue
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            errors.append(f"{relative_path}: invalid TOML")
            continue

        for key in ("name", "description", "developer_instructions", "sandbox_mode"):
            value = data.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{relative_path}: {key} must be non-empty text")

        name = data.get("name")
        if isinstance(name, str):
            names.append(name)
            if name != spec["name"]:
                errors.append(
                    f"{relative_path}: name must be {spec['name']!r}, got {name!r}"
                )

        sandbox_mode = data.get("sandbox_mode")
        if sandbox_mode != spec["sandbox_mode"]:
            errors.append(
                f"{relative_path}: sandbox_mode must be "
                f"{spec['sandbox_mode']!r}, got {sandbox_mode!r}"
            )

        instructions = data.get("developer_instructions")
        if not isinstance(instructions, str):
            continue
        for marker in spec["required"]:
            if marker not in instructions:
                errors.append(f"{relative_path}: missing marker {marker!r}")
        if "WORKER_ORCHESTRATION_OWNER=" in instructions:
            orchestration_owners.append(filename)
        if "TRACKED_SOURCE_WRITE=" in instructions:
            source_writers.append(filename)

    if len(names) == len(AGENT_SPECS) and len(set(names)) != len(names):
        errors.append("agent names must be unique")
    if orchestration_owners != ["manager.toml"]:
        errors.append(
            "only manager.toml may own Worker orchestration; got "
            + repr(orchestration_owners)
        )
    if source_writers != ["implementer.toml"]:
        errors.append(
            "only implementer.toml may own tracked source writes; got "
            + repr(source_writers)
        )


def _validate_documents(errors: list[str]) -> None:
    for relative_path, markers in sorted(DOCUMENT_MARKERS.items()):
        text = _read_text(relative_path, errors)
        if not text:
            continue
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative_path}: missing marker {marker!r}")


def main() -> int:
    errors: list[str] = []
    _validate_agents(errors)
    _validate_documents(errors)

    print("Jarvis Multi-Agent SOP validation")
    print(f"agents={len(AGENT_SPECS)}")
    print(f"documents={len(DOCUMENT_MARKERS)}")
    if errors:
        print("status=FAIL")
        for error in sorted(set(errors)):
            print(f"ERROR {error}")
        return 1
    print("status=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
