"""Deterministically validate Jarvis Multi-Agent SOP documents and agent policy."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".codex" / "agents"
SOP_PATH = "docs/jarvis-multi-agent-sop-v0.1.md"

AGENT_SPECS: dict[str, dict[str, Any]] = {
    "manager.toml": {
        "name": "Manager",
        "sandbox_mode": "read-only",
    },
    "implementer.toml": {
        "name": "Implementer",
        "sandbox_mode": "workspace-write",
    },
    "reviewer.toml": {
        "name": "Reviewer",
        "sandbox_mode": "read-only",
    },
    "qa.toml": {
        "name": "QA",
        "sandbox_mode": "workspace-write",
    },
    "docs.toml": {
        "name": "Docs",
        "sandbox_mode": "workspace-write",
    },
}

DOCUMENT_PATHS = (
    "AGENTS.md",
    SOP_PATH,
    "docs/master-plan.md",
)

MANAGER_GATES = {
    "gate_scope_permission": "scope or permission expansion",
    "gate_jarvis": "jarvis.bat",
    "gate_external": "external API/LLM or credential use",
    "gate_destructive": "destructive action",
    "gate_push_pr": "push/PR",
    "gate_safety_conflict": "safety-contract conflict",
    "gate_unexpected_repo": "unexpected repository state",
}

SOP_GATES = {
    "gate_scope_permission": "승인된 scope 또는 권한 확대",
    "gate_jarvis": "`jarvis.bat` 접근·수정·stage·commit 필요",
    "gate_external": "외부 API/LLM, credential 또는 secret 필요",
    "gate_destructive": "destructive action이나 복구하기 어려운 변경 필요",
    "gate_push_pr": "push 또는 PR 필요",
    "gate_safety_conflict": "기존 안전 계약과 승인된 요구의 충돌",
    "gate_unexpected_repo": (
        "baseline 이후 예상하지 못한 저장소 변경, branch/HEAD drift 또는 "
        "file ownership 충돌"
    ),
}

CONTRADICTIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "director_worker_control_contradiction",
        re.compile(
            r"(?:Director (?:owns|controls|manages|orchestrates|decides) Worker"
            r"|Director decides Worker assignment"
            r"|Director가 Worker 생성·배정·순서·retry·repair를 결정한다)",
            re.IGNORECASE,
        ),
    ),
    (
        "retry_source_change_contradiction",
        re.compile(
            r"(?:Retry means a source-changing correction"
            r"|Retry는 source-changing correction이다)",
            re.IGNORECASE,
        ),
    ),
    (
        "stale_evidence_reuse_contradiction",
        re.compile(
            r"(?:Prior Reviewer and QA evidence remains valid after a candidate change"
            r"|candidate 변경 후 기존 Reviewer/QA evidence를 재사용한다)",
            re.IGNORECASE,
        ),
    ),
    (
        "reviewer_write_contradiction",
        re.compile(
            r"(?:Reviewer may modify tracked source"
            r"|Reviewer가 tracked source를 수정할 수 있다)",
            re.IGNORECASE,
        ),
    ),
    (
        "qa_write_contradiction",
        re.compile(
            r"(?:QA may modify tracked source"
            r"|QA가 tracked source를 수정할 수 있다)",
            re.IGNORECASE,
        ),
    ),
)


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _error(errors: list[str], code: str, detail: str) -> None:
    errors.append(f"[{code}] {detail}")


def _require_all(
    errors: list[str],
    code: str,
    source_name: str,
    text: str,
    clauses: tuple[str, ...],
) -> None:
    normalized = _normalize(text)
    for clause in clauses:
        if _normalize(clause) not in normalized:
            _error(errors, code, f"{source_name} missing clause {clause!r}")


def _read_utf8(relative_path: str, errors: list[str]) -> str:
    path = ROOT / relative_path
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _error(
            errors,
            "source_read",
            f"{relative_path} unreadable ({exc.__class__.__name__})",
        )
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        _error(errors, "source_encoding", f"{relative_path} is not valid UTF-8")
        return ""


def _load_sources(errors: list[str]) -> dict[str, str]:
    sources = {
        relative_path: _read_utf8(relative_path, errors)
        for relative_path in DOCUMENT_PATHS
    }
    try:
        agent_paths = sorted(
            path
            for path in AGENT_DIR.iterdir()
            if path.is_file() and path.suffix == ".toml"
        )
    except OSError as exc:
        _error(
            errors,
            "agent_file_set",
            f".codex/agents unreadable ({exc.__class__.__name__})",
        )
        agent_paths = []
    for path in agent_paths:
        relative_path = f".codex/agents/{path.name}"
        sources[relative_path] = _read_utf8(relative_path, errors)
    return sources


def _parse_agents(
    sources: dict[str, str], errors: list[str]
) -> dict[str, dict[str, Any]]:
    expected_paths = sorted(f".codex/agents/{name}" for name in AGENT_SPECS)
    actual_paths = sorted(
        path
        for path in sources
        if path.startswith(".codex/agents/") and path.endswith(".toml")
    )
    if actual_paths != expected_paths:
        _error(
            errors,
            "agent_file_set",
            f"expected {expected_paths!r}, got {actual_paths!r}",
        )

    parsed: dict[str, dict[str, Any]] = {}
    names: list[str] = []
    for filename, spec in sorted(AGENT_SPECS.items()):
        relative_path = f".codex/agents/{filename}"
        text = sources.get(relative_path)
        if not text:
            _error(errors, "agent_schema", f"{relative_path} is missing or empty")
            continue
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            _error(errors, "agent_schema", f"{relative_path} is invalid TOML")
            continue

        for key in ("name", "description", "developer_instructions", "sandbox_mode"):
            value = data.get(key)
            if not isinstance(value, str) or not value.strip():
                _error(
                    errors,
                    "agent_schema",
                    f"{relative_path} {key} must be non-empty text",
                )

        name = data.get("name")
        if isinstance(name, str):
            names.append(name)
            if name != spec["name"]:
                _error(
                    errors,
                    "agent_schema",
                    f"{relative_path} name must be {spec['name']!r}, got {name!r}",
                )

        sandbox_mode = data.get("sandbox_mode")
        if sandbox_mode != spec["sandbox_mode"]:
            _error(
                errors,
                "agent_schema",
                f"{relative_path} sandbox_mode must be "
                f"{spec['sandbox_mode']!r}, got {sandbox_mode!r}",
            )
        parsed[filename] = data

    if len(names) == len(AGENT_SPECS) and len(set(names)) != len(names):
        _error(errors, "agent_schema", "agent names must be unique")
    return parsed


def _instructions(
    agents: dict[str, dict[str, Any]], filename: str
) -> str:
    value = agents.get(filename, {}).get("developer_instructions")
    return value if isinstance(value, str) else ""


def _validate_role_boundaries(
    sources: dict[str, str],
    agents: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    agents_doc = sources.get("AGENTS.md", "")
    sop = sources.get(SOP_PATH, "")
    manager = _instructions(agents, "manager.toml")
    implementer = _instructions(agents, "implementer.toml")
    reviewer = _instructions(agents, "reviewer.toml")
    qa = _instructions(agents, "qa.toml")
    docs = _instructions(agents, "docs.toml")

    _require_all(
        errors,
        "director_no_worker_control",
        "AGENTS.md",
        agents_doc,
        (
            "Director는 Owner와 소통하는 primary Codex task다.",
            "Worker의 assignment, 순서, retry 또는 repair를 직접 결정하지 않는다.",
        ),
    )
    _require_all(
        errors,
        "director_no_worker_control",
        SOP_PATH,
        sop,
        (
            "Director (primary Codex task)",
            "Worker를 직접 운영하거나 assignment, 순서, retry, repair를 판단하지 않는다.",
        ),
    )
    _require_all(
        errors,
        "manager_orchestration_owner",
        "AGENTS.md",
        agents_doc,
        ("Manager만 Worker orchestration 책임을 갖는다.",),
    )
    _require_all(
        errors,
        "manager_orchestration_owner",
        SOP_PATH,
        sop,
        ("Worker orchestration의 유일한 논리적 책임자다.",),
    )
    _require_all(
        errors,
        "manager_orchestration_owner",
        "manager.toml",
        manager,
        (
            "WORKER_ORCHESTRATION_OWNER=Manager",
            "only logical owner of Worker spawning, assignment, order, retry, "
            "repair, and evidence reconciliation",
            "Do not modify tracked files",
        ),
    )

    ownership_markers = [
        filename
        for filename in AGENT_SPECS
        if "WORKER_ORCHESTRATION_OWNER=" in _instructions(agents, filename)
    ]
    if ownership_markers != ["manager.toml"]:
        _error(
            errors,
            "manager_orchestration_owner",
            f"orchestration owner markers found in {ownership_markers!r}",
        )

    _require_all(
        errors,
        "fallback_decision_boundary",
        "AGENTS.md",
        agents_doc,
        (
            "Director가 Manager의 확정된 assignment plan을 기계적으로 실행할 수 있다.",
            "orchestration 판단 책임은 Manager에 남는다.",
        ),
    )
    _require_all(
        errors,
        "fallback_decision_boundary",
        SOP_PATH,
        sop,
        (
            "Director가 Manager의 확정된 assignment plan에 따라 Worker task를 "
            "기계적으로 생성할 수 있다.",
            "Worker 선택·순서, repair·retry와 pass/fail 판단은 계속 Manager가 소유한다.",
            "nested spawning을 지원한다고 가정하거나 가장하지 않는다.",
        ),
    )
    _require_all(
        errors,
        "fallback_decision_boundary",
        "manager.toml",
        manager,
        (
            "Nested spawning is not assumed.",
            "produce an exact assignment plan for the primary Director to execute "
            "mechanically",
            "Retain all orchestration decisions and pass/fail judgment",
        ),
    )

    _require_all(
        errors,
        "implementer_sole_writer",
        "implementer.toml",
        implementer,
        (
            "sole source writer",
            "TRACKED_SOURCE_WRITE=Implementer",
            "exact assigned file scope",
            "candidate local commit",
        ),
    )
    source_write_markers = [
        filename
        for filename in AGENT_SPECS
        if "TRACKED_SOURCE_WRITE=" in _instructions(agents, filename)
    ]
    if source_write_markers != ["implementer.toml"]:
        _error(
            errors,
            "implementer_sole_writer",
            f"source write markers found in {source_write_markers!r}",
        )
    _require_all(
        errors,
        "implementer_sole_writer",
        SOP_PATH,
        sop,
        (
            "한 assignment에서 유일한 source writer다.",
            "병렬 source writer는 허용하지 않는다.",
        ),
    )

    _require_all(
        errors,
        "reviewer_read_only",
        "reviewer.toml",
        reviewer,
        (
            "strict read-only",
            "do not modify tracked or untracked files, stage, commit, or repair",
            "exact candidate commit",
            "actionable findings",
        ),
    )
    _require_all(
        errors,
        "qa_no_tracked_write",
        "qa.toml",
        qa,
        (
            "exact candidate commit",
            "Do not modify tracked source, stage, commit, or repair",
            "lightest sufficient QA",
            "prove the owned PID and target listeners are absent",
        ),
    )
    _require_all(
        errors,
        "docs_sequencing",
        "docs.toml",
        docs,
        (
            "Run sequentially only after QA",
            "docs_status=not_required",
            "exact documentation paths",
        ),
    )
    _require_all(
        errors,
        "docs_sequencing",
        SOP_PATH,
        sop,
        (
            "QA 뒤에 순차 실행하거나 `not_required`와 이유를 기록한다.",
        ),
    )


def _validate_budget_and_candidate_rules(
    sources: dict[str, str],
    agents: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    agents_doc = sources.get("AGENTS.md", "")
    sop = sources.get(SOP_PATH, "")
    manager = _instructions(agents, "manager.toml")
    docs = _instructions(agents, "docs.toml")

    _require_all(
        errors,
        "budget_defaults",
        "AGENTS.md",
        agents_doc,
        ("retry_budget=1", "repair_budget=1", "repair_count=0"),
    )
    _require_all(
        errors,
        "budget_defaults",
        SOP_PATH,
        sop,
        (
            "retry_budget=1",
            "retry_count=0",
            "repair_budget=1",
            "repair_count=0",
        ),
    )
    _require_all(
        errors,
        "budget_defaults",
        "manager.toml",
        manager,
        (
            "retry_budget=1",
            "retry_count=0",
            "repair_budget=1",
            "repair_count=0",
        ),
    )

    _require_all(
        errors,
        "retry_definition",
        SOP_PATH,
        sop,
        (
            "Retry는 source 변경이 없는 test 재실행, 일시적 환경 복구 또는 "
            "동일 candidate의 evidence 재수집이다.",
        ),
    )
    _require_all(
        errors,
        "retry_definition",
        "manager.toml",
        manager,
        ("Retry means a no-source-change rerun or environment recovery.",),
    )
    _require_all(
        errors,
        "repair_definition",
        SOP_PATH,
        sop,
        (
            "Repair는 Reviewer finding 또는 QA 실패를 해결하기 위해 tracked source를 "
            "바꾸는 correction이다.",
        ),
    )
    _require_all(
        errors,
        "repair_definition",
        "manager.toml",
        manager,
        ("Repair means a source-changing correction",),
    )
    _require_all(
        errors,
        "repair_increment",
        SOP_PATH,
        sop,
        ("source-changing repair마다 `repair_count += 1`이다.",),
    )
    _require_all(
        errors,
        "repair_increment",
        "manager.toml",
        manager,
        ("each source-changing repair increments repair_count",),
    )

    _require_all(
        errors,
        "candidate_invalidation",
        "AGENTS.md",
        agents_doc,
        (
            "candidate commit이 바뀌면 이전 Reviewer와 QA 결과는 전부 무효",
        ),
    )
    _require_all(
        errors,
        "candidate_invalidation",
        SOP_PATH,
        sop,
        (
            "candidate commit 변경 시 기존 Reviewer/QA 결과는 전부 무효",
        ),
    )
    _require_all(
        errors,
        "candidate_invalidation",
        "manager.toml",
        manager,
        ("invalidate all prior Reviewer and QA evidence",),
    )
    _require_all(
        errors,
        "candidate_invalidation",
        "docs.toml",
        docs,
        ("invalidates all prior Reviewer and QA evidence",),
    )
    _require_all(
        errors,
        "fresh_review_qa",
        "AGENTS.md",
        agents_doc,
        ("새 commit에 Reviewer → QA를 다시 실행한다.",),
    )
    _require_all(
        errors,
        "fresh_review_qa",
        SOP_PATH,
        sop,
        ("새 candidate는 반드시 fresh Reviewer → fresh QA 순서를 다시 통과한다.",),
    )
    _require_all(
        errors,
        "fresh_review_qa",
        "manager.toml",
        manager,
        ("require fresh Reviewer -> QA",),
    )
    _require_all(
        errors,
        "fresh_review_qa",
        "docs.toml",
        docs,
        ("require fresh Reviewer -> QA",),
    )

    _require_all(
        errors,
        "budget_exhaustion_escalation",
        SOP_PATH,
        sop,
        (
            "다음 retry/repair가 필요한 시점에 count가 budget과 같으면 budget이 "
            "소진된 것이므로 실행하지 않고 Manager → Director로 escalation한다.",
        ),
    )
    _require_all(
        errors,
        "budget_exhaustion_escalation",
        "manager.toml",
        manager,
        (
            "If another attempt is needed after a budget is exhausted, escalate "
            "to Director",
        ),
    )
    _require_all(
        errors,
        "owner_budget_authority",
        SOP_PATH,
        sop,
        ("budget 증액은 Owner만 결정할 수 있다.",),
    )
    _require_all(
        errors,
        "owner_budget_authority",
        "manager.toml",
        manager,
        ("only Owner may increase a budget",),
    )


def _validate_escalation_gates(
    sources: dict[str, str],
    agents: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    sop = sources.get(SOP_PATH, "")
    manager = _instructions(agents, "manager.toml")
    for code, clause in SOP_GATES.items():
        _require_all(errors, code, SOP_PATH, sop, (clause,))
    for code, clause in MANAGER_GATES.items():
        _require_all(errors, code, "manager.toml", manager, (clause,))


def _validate_master_plan(sources: dict[str, str], errors: list[str]) -> None:
    master_plan = sources.get("docs/master-plan.md", "")
    _require_all(
        errors,
        "master_plan_promotion",
        "docs/master-plan.md",
        master_plan,
        (
            "Jarvis Multi-Agent SOP v0.1B",
            "7d4394eed584bc11ee25062a671952b2e4c38b31",
            "Reviewer가 실제 P2 finding 1건",
            "repair 1회",
            "fresh Reviewer와 QA",
            "Director Dashboard v0.1B",
            "실제 기능 work package 1~2개",
            "Hermes 자동 runtime",
        ),
    )


def _validate_contradictions(
    sources: dict[str, str], errors: list[str]
) -> None:
    combined = "\n".join(
        f"{path}\n{text}" for path, text in sorted(sources.items())
    )
    for code, pattern in CONTRADICTIONS:
        match = pattern.search(combined)
        if match is not None:
            _error(errors, code, f"contradictory clause {match.group(0)!r}")


def _validate_sources(sources: dict[str, str]) -> list[str]:
    errors: list[str] = []
    agents = _parse_agents(sources, errors)
    _validate_role_boundaries(sources, agents, errors)
    _validate_budget_and_candidate_rules(sources, agents, errors)
    _validate_escalation_gates(sources, agents, errors)
    _validate_master_plan(sources, errors)
    _validate_contradictions(sources, errors)
    return sorted(set(errors))


def _exit_code(errors: list[str]) -> int:
    return 1 if errors else 0


def _replace_once(
    sources: dict[str, str],
    path: str,
    old: str,
    new: str,
) -> dict[str, str]:
    mutated = dict(sources)
    text = mutated[path]
    if old not in text:
        raise ValueError(f"mutation fixture missing in {path}: {old!r}")
    mutated[path] = text.replace(old, new, 1)
    return mutated


def _append_agent_instruction(
    sources: dict[str, str], filename: str, clause: str
) -> dict[str, str]:
    path = f".codex/agents/{filename}"
    mutated = dict(sources)
    text = mutated[path]
    marker = text.rfind('"""')
    if marker < 0:
        raise ValueError(f"developer_instructions terminator missing in {path}")
    mutated[path] = text[:marker] + clause + "\n" + text[marker:]
    return mutated


def _assert_mutation_fails(
    label: str,
    mutated: dict[str, str],
    expected_code: str,
    failures: list[str],
) -> None:
    errors = _validate_sources(mutated)
    has_expected_error = any(
        error.startswith(f"[{expected_code}]") for error in errors
    )
    if _exit_code(errors) != 1 or not has_expected_error:
        failures.append(
            f"{label}: expected nonzero [{expected_code}], got {errors!r}"
        )


def _run_negative_mutation_checks(
    sources: dict[str, str],
) -> tuple[int, list[str]]:
    checks: list[tuple[str, dict[str, str], str]] = []
    failures: list[str] = []

    director_agent = dict(sources)
    director_agent[".codex/agents/director.toml"] = (
        'name = "Director"\n'
        'description = "Forbidden custom Director role."\n'
        'sandbox_mode = "read-only"\n'
        'developer_instructions = "Director."\n'
    )
    checks.append(("no_custom_director_agent", director_agent, "agent_file_set"))

    cases = (
        (
            "director_no_worker_rule_removed",
            SOP_PATH,
            "Worker를 직접 운영하거나 assignment, 순서, retry, repair를 판단하지 않는다.",
            "Director boundary removed.",
            "director_no_worker_control",
        ),
        (
            "manager_owner_removed",
            ".codex/agents/manager.toml",
            "WORKER_ORCHESTRATION_OWNER=Manager",
            "WORKER_ORCHESTRATION_OWNER=Removed",
            "manager_orchestration_owner",
        ),
        (
            "fallback_decision_removed",
            SOP_PATH,
            "pass/fail 판단은 계속 Manager가 소유한다.",
            "pass/fail boundary removed.",
            "fallback_decision_boundary",
        ),
        (
            "implementer_writer_removed",
            ".codex/agents/implementer.toml",
            "TRACKED_SOURCE_WRITE=Implementer",
            "TRACKED_SOURCE_WRITE=Removed",
            "implementer_sole_writer",
        ),
        (
            "reviewer_read_only_removed",
            ".codex/agents/reviewer.toml",
            "Stay strict read-only",
            "Read-only boundary removed",
            "reviewer_read_only",
        ),
        (
            "qa_write_boundary_removed",
            ".codex/agents/qa.toml",
            "Do not modify tracked source, stage, commit, or repair",
            "Tracked-source boundary removed",
            "qa_no_tracked_write",
        ),
        (
            "docs_sequence_removed",
            ".codex/agents/docs.toml",
            "Run sequentially only after QA",
            "Docs sequence removed",
            "docs_sequencing",
        ),
        (
            "retry_definition_removed",
            SOP_PATH,
            "Retry는 source 변경이 없는",
            "Retry definition removed:",
            "retry_definition",
        ),
        (
            "repair_definition_removed",
            SOP_PATH,
            "Repair는 Reviewer finding 또는 QA 실패를 해결하기 위해 tracked source를",
            "Repair definition removed:",
            "repair_definition",
        ),
        (
            "repair_increment_removed",
            SOP_PATH,
            "source-changing repair마다 `repair_count += 1`이다.",
            "Repair count increment removed.",
            "repair_increment",
        ),
        (
            "budget_default_removed",
            ".codex/agents/manager.toml",
            "repair_count=0",
            "repair_count=unset",
            "budget_defaults",
        ),
        (
            "candidate_invalidation_removed",
            SOP_PATH,
            "candidate commit 변경 시 기존 Reviewer/QA 결과는 전부 무효",
            "candidate evidence invalidation removed",
            "candidate_invalidation",
        ),
        (
            "fresh_review_qa_removed",
            SOP_PATH,
            "새 candidate는 반드시 fresh Reviewer → fresh QA 순서를 다시 통과한다.",
            "Fresh review and QA requirement removed.",
            "fresh_review_qa",
        ),
        (
            "budget_escalation_removed",
            SOP_PATH,
            "Manager → Director로 escalation한다.",
            "Budget exhaustion escalation removed.",
            "budget_exhaustion_escalation",
        ),
        (
            "owner_budget_authority_removed",
            SOP_PATH,
            "budget 증액은 Owner만 결정할 수 있다.",
            "Budget authority removed.",
            "owner_budget_authority",
        ),
    )
    for label, path, old, new, expected_code in cases:
        try:
            mutated = _replace_once(sources, path, old, new)
        except (KeyError, ValueError) as exc:
            failures.append(f"{label}: {exc}")
            continue
        checks.append((label, mutated, expected_code))

    for code, clause in SOP_GATES.items():
        label = f"{code}_removed"
        try:
            mutated = _replace_once(
                sources,
                SOP_PATH,
                clause,
                f"REMOVED_{code}",
            )
        except (KeyError, ValueError) as exc:
            failures.append(f"{label}: {exc}")
            continue
        checks.append((label, mutated, code))

    contradiction_cases = (
        (
            "director_worker_control_granted",
            SOP_PATH,
            "Director owns Worker spawning, assignment, order, retry, repair, "
            "and evidence reconciliation.",
            "director_worker_control_contradiction",
        ),
        (
            "retry_redefined_as_source_change",
            SOP_PATH,
            "Retry means a source-changing correction.",
            "retry_source_change_contradiction",
        ),
        (
            "stale_evidence_reuse_allowed",
            SOP_PATH,
            "Prior Reviewer and QA evidence remains valid after a candidate change.",
            "stale_evidence_reuse_contradiction",
        ),
    )
    for label, path, clause, expected_code in contradiction_cases:
        mutated = dict(sources)
        mutated[path] = mutated[path] + "\n" + clause + "\n"
        checks.append((label, mutated, expected_code))

    try:
        reviewer_write = _append_agent_instruction(
            sources,
            "reviewer.toml",
            "Reviewer may modify tracked source.",
        )
        checks.append(
            (
                "reviewer_tracked_write_granted",
                reviewer_write,
                "reviewer_write_contradiction",
            )
        )
        qa_write = _append_agent_instruction(
            sources,
            "qa.toml",
            "QA may modify tracked source.",
        )
        checks.append(
            (
                "qa_tracked_write_granted",
                qa_write,
                "qa_write_contradiction",
            )
        )
    except (KeyError, ValueError) as exc:
        failures.append(f"write_contradiction_fixture: {exc}")

    for label, mutated, expected_code in checks:
        _assert_mutation_fails(
            label,
            mutated,
            expected_code,
            failures,
        )
    return len(checks), sorted(failures)


def main() -> int:
    load_errors: list[str] = []
    sources = _load_sources(load_errors)
    errors = sorted(set(load_errors + _validate_sources(sources)))
    negative_check_count = 0
    negative_failure_count = 0
    if not errors:
        negative_check_count, negative_failures = _run_negative_mutation_checks(
            sources
        )
        negative_failure_count = len(negative_failures)
        for failure in negative_failures:
            _error(errors, "negative_self_test", failure)
        errors = sorted(set(errors))

    print("Jarvis Multi-Agent SOP validation")
    print(f"agents={len(AGENT_SPECS)}")
    print(f"documents={len(DOCUMENT_PATHS)}")
    print(f"negative_checks={negative_check_count}")
    print(f"negative_failures={negative_failure_count}")
    if errors:
        print("status=FAIL")
        for error in errors:
            print(f"ERROR {error}")
        return _exit_code(errors)
    print("status=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
