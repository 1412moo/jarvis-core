"""Deterministically validate Jarvis Multi-Agent SOP documents and agent policy."""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / ".codex" / "agents"
SOP_PATH = "docs/jarvis-multi-agent-sop-v0.1.md"
CLAUDE_REVIEWER_PATH = ".claude/agents/reviewer.md"
CODEX_REVIEWER_PATH = ".codex/agents/reviewer.toml"

# task-0135: the Claude and Codex Reviewer definitions carry the same role rules.
# Each clause must appear in both, on one line, so a raw mutation can remove it.
REVIEWER_ROLE_CLAUSES = (
    "Stay strict read-only: do not modify tracked or untracked files, stage, commit, or repair.",
    "Accept an exact candidate commit from Manager (the caller), verify that exact full hash exists",
    "Manager (the caller) must supply a full 40-character candidate commit hash.",
    "Never use `HEAD`, `@`, a branch name, a tag, a short hash, or the working tree as the review subject.",
    "limited to the file scope Manager (the caller) supplied",
    "Require the Owner's approval verbatim from Manager (the caller) under the marker line OWNER APPROVAL (verbatim).",
    "The marker line is exactly `=== OWNER APPROVAL (verbatim) ===`.",
    "return verdict BLOCKED with a blocking finding and review nothing",
    "Judge diff scope against the verbatim approval",
    "Compare the Manager summary against the verbatim approval condition by condition",
    "Use each form exactly as written.",
    "never join several patterns into one with regex alternation",
    "`<baseline>` is the full 40-character baseline commit hash Manager (the caller) supplied.",
    "If no full baseline hash was supplied, do not judge the cumulative change set",
    "Evidence paths may be read only through `git show <hash>:<path>` and `git grep` bound to the candidate hash",
    "Never read the working tree directly with any file-reading tool",
    "when Manager (the caller) supplied a full baseline hash, the baseline..candidate change set",
    "- `git diff --name-status <baseline> <hash>`",
    "- `git diff <baseline> <hash> -- <path>` — exactly one `<path>`, and it must be a file Manager (the caller) supplied as scope.",
    "- `git log --format=<format> <baseline>..<hash>`",
    "- `git show <hash>:<path>` — `<path>` must be a file Manager (the caller) supplied as scope or as an evidence path.",
    "supplied as scope or as an evidence path. Never run a repository-wide grep",
    "Never read, open, stage, quote, or describe the contents of `jarvis.bat` or any `.env` file.",
    "Never decide retry, repair, approval, release, push, or PR.",
    "When `verdict` is BLOCKED, `files_reviewed` is `[]`.",
    "`severity` is exactly one of `blocking`, `major`, `minor`.",
    "`verdict` follows `findings` mechanically",
    "Reviewer PASS는 QA PASS·승인·release 권한이 아니다",
    # task-0148: report fields that never change the verdict.
    "The approved contract is the Owner's verbatim approval plus the files Manager (the caller) supplied as scope or as evidence paths.",
    "`unverified` never changes `verdict`, and a PASS with `unverified` entries is a Reviewer-stage PASS only: every `unverified` entry goes to QA, and final acceptance is decided after QA.",
    "A non-empty `self_deviations` makes this review invalid",
    "`unverified` and `self_deviations` never change `verdict`.",
    "give every `unverified` entry `qa: <check name>` only if that one listed check alone verifies the entry, and `qa: none` otherwise. Never name a check that is not in the list.",
    # task-0177: optional reference commits, evidence for one scope path each.
    "- `git merge-base --is-ancestor <reference> <baseline>` — only for a valid reference line; see \"Reference commits (optional)\".",
    "- `git diff <reference> <hash> -- <path>` — exactly one `<path>`, and it must be the path paired with that `<reference>`.",
    "Manager (the caller) may supply reference commits under the marker line `=== REFERENCE COMMITS ===`",
    "Without that marker line, nothing in this section applies and no `<reference>` form may be run.",
    "and the same line `<reference> -- <path>`, with that exact hash and that exact path, appears verbatim in the section under `=== OWNER APPROVAL (verbatim) ===`.",
    "A hash and a path that appear only apart from each other in the approval do not make a valid reference line.",
    "Never accept `jarvis.bat`, a `.env` file, a directory, or a wildcard as a reference path.",
    "the reference is usable only when that command exits 0.",
    "or if no full baseline hash was supplied, STOP immediately: the verdict is BLOCKED with a blocking finding, and nothing is reviewed.",
    "A reference diff is evidence for its paired path only: the change set and the review subject stay as defined in Candidate binding",
    "A scope path with a valid reference is the only scope path that may be absent from the baseline..candidate change set.",
    "A reference never approves anything else: changes between `<reference>` and `<baseline>` to any other path are neither reviewed nor accepted",
    "`<reference>` is the full 40-character hash of one valid reference line.",
    "The report shows which scope paths were judged against a reference diff: each appears in `commands_run`",
    "candidate, approval or reference binding failure -> BLOCKED.",
)
# task-0177: the only Allowed commands lines that may name `<reference>` (Owner decision F2).
REVIEWER_REFERENCE_FORMS = (
    "git merge-base --is-ancestor <reference> <baseline>",
    "git diff <reference> <hash> -- <path>",
)
SOP_REFERENCE_CLAUSES = (
    "참조 diff는 그 파일의 검토 근거일 뿐이고, 변경 범위 판정과 검토 대상은 baseline..candidate 규칙 그대로다.",
    "참조 커밋과 baseline 사이의 다른 변경은 검토하지도 승인하지도 않는다.",
    "해시와 경로가 승인 원문의 서로 다른 곳에 따로 있는 것으로는 참조 커밋이 되지 않는다.",
)
CALLER_NAME = "Manager (the caller)"

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

MAP_PATH = "AGENTS.md"
TASK_MODEL_PATH = "docs/task-model.md"
TRANSITION_POLICY_PATH = "docs/execution-status-transition-policy.md"

# task-0147: each of these once claimed its own overall precedence; each now
# limits its list to its own area and defers to the AGENTS.md source map.
DELEGATION_CLAUSES = {
    "docs/ai-team-operating-model.md": (
        "영역 간 판정은 [`AGENTS.md`](../AGENTS.md)의 기준 지도를 따른다."
    ),
    "docs/chatgpt-handoff.md": (
        "Judging between areas follows the source map in `AGENTS.md` (기준 지도)."
    ),
    "docs/manager-reporting-workflow-v0.1.md": (
        "Judging between areas follows the source map in `AGENTS.md` (기준 지도)."
    ),
}

DOCUMENT_PATHS = (
    MAP_PATH,
    SOP_PATH,
    "docs/master-plan.md",
    TASK_MODEL_PATH,
    TRANSITION_POLICY_PATH,
    *DELEGATION_CLAUSES,
)

# task-0147: read only to compare the values the documents state with the code.
# They are not normative documents.
WORKER_PATH = "orchestrator/worker/claude_worker.py"
WRITER_PATH = "orchestrator/discord-intake/task_file_writer.py"
CODE_PATHS = (WORKER_PATH, WRITER_PATH)

MAP_AREAS = (
    "에이전트 행동 규칙",
    "현재 시스템 동작",
    "task 상태",
    "목표·milestone·approval state",
)
BEHAVIOR_AREA = "에이전트 행동 규칙"
# History sources that must never back the agent-behavior area.
NON_BEHAVIOR_SOURCES = (
    "docs/master-plan.md",
    "docs/chatgpt-handoff.md",
    "memory/tasks",
    "-design",
)
HISTORY_REQUIRED = ("memory/tasks/", "docs/chatgpt-handoff.md", "-design")
MAP_RULE_CLAUSES = (
    "### 판정 규칙",
    "`gate_safety_conflict`로 Owner에게 escalation한다(fail closed).",
    "Owner 승인은 그 승인을 받은 task의 범위 안에서만 효력이 있다.",
    "### Owner 승인의 효력과 승격",
    "옮기기 전에는 task 기록에만 있는 규칙을 현재 규칙으로 쓰지 않는다.",
)
# task-0148 decision 1: the conditions under which the Owner may accept minor findings.
SOP_ACCEPTANCE_CLAUSES = (
    "Owner의 minor finding 수용(수동 경로 한정).",
    "- blocking과 major는 수용할 수 없다.",
    "- 지적마다 Owner의 수용 원문을 task 기록에 남긴다.",
    "- 수용은 그 candidate에만 효력이 있고 candidate가 바뀌면 무효다.",
    "- QA는 그대로 전부 통과해야 하며 수용이 QA를 대신하지 않는다.",
    "- Manager는 finding을 수용할 수 없다.",
    "- §10 Worker 파이프라인에는 적용하지 않는다.",
)
# task-0151: accept_* are the `/go <id> accept` refusals, held to the same SOP 10.2 parity.
PIPELINE_REASON_PATTERN = re.compile(
    r"(?:resume_[a-z_]+|repair_no_[a-z_]+|reviewer_findings_not_repairable|reviewer_self_deviation|qa_unverified_owner_review"
    r"|accept_[a-z_]+)"
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
    (
        "global_source_of_truth_contradiction",
        re.compile(
            r"(?:is the source of truth for (?:all areas|every area|all rules)"
            r"|모든 영역의 기준(?:이다| 문서다))",
            re.IGNORECASE,
        ),
    ),
    (
        "findings_acceptance_rule_contradiction",
        re.compile(
            r"(?:Manager may accept Reviewer findings"
            r"|Manager가 (?:Reviewer )?finding을 수용(?:한다|할 수 있다)"
            r"|(?:blocking|major)(?:와|과|도)?[^.\n]{0,20}수용할 수 있다"
            r"|파이프라인[^.\n]{0,30}자동으로 수용)",
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
    sources[CLAUDE_REVIEWER_PATH] = _read_utf8(CLAUDE_REVIEWER_PATH, errors)
    for relative_path in CODE_PATHS:
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
    # task-0133 made the Manager quote the Owner's approval verbatim and pass it
    # to the Reviewer; task-0134 makes the Reviewer refuse to review without it.
    _require_all(
        errors,
        "owner_approval_verbatim",
        SOP_PATH,
        sop,
        (
            "Owner 승인 메시지의 포함·제외 조건을 task 기록에 요약 없이 원문 그대로",
            "Reviewer assignment에는 Manager 요약과 함께 Owner 승인 원문을 전달한다.",
            "Manager 요약과 Owner 승인 원문을 함께 받고, diff의 범위는 승인 원문을 기준으로",
        ),
    )
    _require_all(
        errors,
        "reviewer_approval_binding",
        "reviewer.toml",
        reviewer,
        (
            "Require the Owner's approval verbatim from Manager (the caller) under the marker line OWNER APPROVAL (verbatim).",
            "return verdict BLOCKED with a blocking finding and review nothing",
            "Judge diff scope against the verbatim approval",
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
        f"{path}\n{text}"
        for path, text in sorted(sources.items())
        if path not in CODE_PATHS
    )
    for code, pattern in CONTRADICTIONS:
        match = pattern.search(combined)
        if match is not None:
            _error(errors, code, f"contradictory clause {match.group(0)!r}")


def _validate_reviewer_parity(
    sources: dict[str, str],
    agents: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    claude_reviewer = sources.get(CLAUDE_REVIEWER_PATH, "")
    codex_reviewer = _instructions(agents, "reviewer.toml")
    for source_name, text in (
        (CLAUDE_REVIEWER_PATH, claude_reviewer),
        (CODEX_REVIEWER_PATH, codex_reviewer),
    ):
        _require_all(
            errors, "reviewer_role_parity", source_name, text, REVIEWER_ROLE_CLAUSES
        )
    # Both definitions name the caller only as "Manager (the caller)".
    for source_name, text in (
        (CLAUDE_REVIEWER_PATH, claude_reviewer),
        (CODEX_REVIEWER_PATH, sources.get(CODEX_REVIEWER_PATH, "")),
    ):
        match = re.search(r"\bcaller\b", text.replace(CALLER_NAME, ""), re.IGNORECASE)
        if match is not None:
            _error(
                errors,
                "reviewer_caller_name",
                f"{source_name} names the caller other than {CALLER_NAME!r}",
            )


def _validate_reviewer_reference_forms(
    sources: dict[str, str],
    agents: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    """task-0177: Allowed commands name `<reference>` only in the two approved forms."""

    for source_name, text in (
        (CLAUDE_REVIEWER_PATH, sources.get(CLAUDE_REVIEWER_PATH, "")),
        (CODEX_REVIEWER_PATH, _instructions(agents, "reviewer.toml")),
    ):
        allowed = _section(text, "## Allowed commands", r"^## ")
        forms = []
        for line in allowed.splitlines():
            if "<reference>" not in line:
                continue
            match = re.match(r"^- `([^`]*)`", line)
            forms.append(match.group(1) if match else line.strip())
        if sorted(forms) != sorted(REVIEWER_REFERENCE_FORMS):
            _error(
                errors,
                "reviewer_reference_forms",
                f"{source_name} Allowed commands name <reference> in {forms!r}, expected {list(REVIEWER_REFERENCE_FORMS)!r}",
            )


def _section(text: str, heading: str, end_pattern: str) -> str:
    """The text after `heading` up to the first line matching `end_pattern`."""

    start = text.find(heading)
    if start < 0:
        return ""
    body = text[start + len(heading):]
    end = re.search(end_pattern, body, re.MULTILINE)
    return body[: end.start()] if end else body


def _table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def _map_path_exists(token: str) -> bool:
    if "*" in token:
        return any(ROOT.glob(token))
    return (ROOT / token).is_file()


def _validate_source_map(sources: dict[str, str], errors: list[str]) -> None:
    """task-0147: the AGENTS.md source map names every area and only real files."""

    section = _section(sources.get(MAP_PATH, ""), "## 기준 지도", r"^## ")
    if not section:
        _error(errors, "source_map_missing", f"{MAP_PATH} has no '## 기준 지도' section")
        return
    table = _section(section, "### 영역별 기준", r"^### ")
    rows = {row[0]: row for row in _table_rows(table)[1:] if row}
    for area in MAP_AREAS:
        if area not in rows:
            _error(errors, "source_map_area", f"source map lacks the area {area!r}")
    for area, row in rows.items():
        for token in re.findall(r"`([^`]+)`", " ".join(row[1:])):
            if ("/" in token or token.endswith((".md", ".py", ".toml"))) and not _map_path_exists(token):
                _error(errors, "source_map_path", f"source map row {area!r} names a missing file {token!r}")
    behavior = " ".join(rows.get(BEHAVIOR_AREA, [])[1:])
    for fragment in NON_BEHAVIOR_SOURCES:
        if fragment in behavior:
            _error(errors, "source_map_behavior_source", f"agent-behavior row names history source {fragment!r}")
    history = _section(section, "### History로 취급하는 것", r"^### ")
    for fragment in HISTORY_REQUIRED:
        if fragment not in history:
            _error(errors, "source_map_history", f"history list lacks {fragment!r}")
    _require_all(errors, "source_map_rules", MAP_PATH, section, MAP_RULE_CLAUSES)
    for path, clause in DELEGATION_CLAUSES.items():
        _require_all(errors, "source_map_delegation", path, sources.get(path, ""), (clause,))


def _module_constant(tree: ast.Module, name: str) -> ast.expr | None:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return node.value
    return None


def _parse_code(sources: dict[str, str], path: str, errors: list[str]) -> ast.Module | None:
    try:
        return ast.parse(sources.get(path, ""))
    except SyntaxError as exc:
        _error(errors, "code_parse", f"{path} does not parse ({exc.msg})")
        return None


def _validate_pipeline_parity(sources: dict[str, str], errors: list[str]) -> None:
    """task-0147: SOP section 10 states the values the Worker pipeline really uses."""

    sop = sources.get(SOP_PATH, "")
    rules = _section(sop, "### 10.2 파이프라인 규칙", r"^## ")
    scope = _section(sop, "### 10.1 현재 실행 범위", r"^### ")
    tree = _parse_code(sources, WORKER_PATH, errors)
    if tree is None:
        return
    if not rules or not scope:
        _error(errors, "pipeline_section_missing", f"{SOP_PATH} lacks section 10.1 or 10.2")
        return

    budget_node = _module_constant(tree, "REPAIR_BUDGET_MAX")
    stated = re.search(r"파이프라인 상한은 (\d+)이다", rules)
    try:
        budget = ast.literal_eval(budget_node) if budget_node is not None else None
    except ValueError:
        budget = None
    if stated is None or budget is None or int(stated.group(1)) != budget:
        _error(errors, "pipeline_budget_parity", f"SOP states {stated and stated.group(1)!r}, code REPAIR_BUDGET_MAX is {budget!r}")

    code_reasons = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and PIPELINE_REASON_PATTERN.fullmatch(node.value)
    }
    doc_reasons = {
        token for token in re.findall(r"`([^`]+)`", rules) if PIPELINE_REASON_PATTERN.fullmatch(token)
    }
    if code_reasons != doc_reasons:
        _error(
            errors,
            "pipeline_reason_parity",
            f"only in code {sorted(code_reasons - doc_reasons)!r}, only in SOP {sorted(doc_reasons - code_reasons)!r}",
        )

    code_qa = {
        node.slice.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "qa"
        and isinstance(node.slice, ast.Constant)
    }
    qa_item = re.search(r"^8\. QA\.(.*?)^9\. ", rules, re.MULTILINE | re.DOTALL)
    doc_qa = set(re.findall(r"`([a-z_]+)`", qa_item.group(1))) - {"qa_failed"} if qa_item else set()
    if code_qa != doc_qa:
        _error(errors, "pipeline_qa_parity", f"code QA keys {sorted(code_qa)!r}, SOP {sorted(doc_qa)!r}")

    # Section 10.1 records scope values, not rules; they must still match the code.
    # task-0164: the work-kind values come from the WORK_KINDS registry, entry by entry, and
    # the table names each value with its kind as `value`(kind).
    kinds = _work_kinds(tree)
    if not kinds:
        _error(errors, "pipeline_scope_parity", f"{WORKER_PATH} has no readable WORK_KINDS entries")
    names = {kind.get("name") for kind in kinds}
    expected_pairs = {
        field: {(kind.get(field), kind.get("name")) for kind in kinds} for field in ("allowed_prefix", "test_script")
    }
    protected_node = _module_constant(tree, "PROTECTED_PATHS")
    if isinstance(protected_node, ast.Call) and protected_node.args:  # frozenset({...})
        protected_node = protected_node.args[0]
    protected_elements = protected_node.elts if isinstance(protected_node, (ast.Tuple, ast.Set)) else [protected_node]
    protected = {
        elt.value for elt in protected_elements if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    }
    unseen = {"WORK_KINDS", "allowed_prefix", "test_script", "PROTECTED_PATHS"}
    for row in _table_rows(scope)[1:]:
        cells = " ".join(row)
        value = row[1] if len(row) > 1 else ""
        if "`WORK_KINDS`" in cells:
            stated_names = set(re.findall(r"`([a-z_]+)`\(", value))
            if not names or stated_names != names:
                _error(errors, "pipeline_scope_parity", f"section 10.1 kinds {sorted(stated_names)!r}, code {sorted(names, key=str)!r}")
            unseen.discard("WORK_KINDS")
        for field, pairs in expected_pairs.items():
            if f"`{field}`" in cells:
                stated_pairs = set(re.findall(r"`([^`]+)`\(([a-z_]+)\)", value))
                if not pairs or stated_pairs != pairs:
                    _error(errors, "pipeline_scope_parity", f"section 10.1 {field} states {sorted(stated_pairs)!r}, code {sorted(pairs, key=str)!r}")
                unseen.discard(field)
        if "`PROTECTED_PATHS`" in cells:
            stated_protected = set(re.findall(r"`([^`]+)`", value))
            if not protected or stated_protected != protected:
                _error(errors, "pipeline_scope_parity", f"section 10.1 PROTECTED_PATHS states {sorted(stated_protected)!r}, code {sorted(protected)!r}")
            unseen.discard("PROTECTED_PATHS")
    for name in sorted(unseen):
        _error(errors, "pipeline_scope_parity", f"section 10.1 has no row for {name}")


def _work_kinds(tree: ast.Module) -> list[dict[str, str | None]]:
    """task-0164: each WorkKind(...) entry of WORK_KINDS as its literal keyword values."""

    node = _module_constant(tree, "WORK_KINDS")
    if not isinstance(node, (ast.Tuple, ast.List)):
        return []
    kinds = []
    for entry in node.elts:
        if not (isinstance(entry, ast.Call) and isinstance(entry.func, ast.Name) and entry.func.id == "WorkKind"):
            kinds.append({"name": None})
            continue
        values = {
            keyword.arg: keyword.value.value
            for keyword in entry.keywords
            if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str)
        }
        kinds.append({field: values.get(field) for field in ("name", "allowed_prefix", "test_script")})
    return kinds


def _validate_transition_contract(sources: dict[str, str], errors: list[str]) -> None:
    """task-0147: task-model 5-1 is exactly the writer's pairs; 5-2 uses only those."""

    tree = _parse_code(sources, WRITER_PATH, errors)
    if tree is None:
        return
    node = _module_constant(tree, "TASK_STATUS_TRANSITIONS")
    try:
        code_pairs = set(ast.literal_eval(node.args[0])) if isinstance(node, ast.Call) and node.args else set()
    except ValueError:
        code_pairs = set()
    model = sources.get(TASK_MODEL_PATH, "")
    contract = _section(model, "### 5-1) 허용 전이 계약", r"^### ")
    paths = _section(model, "### 5-2) 전이 발생 경로", r"^## ")
    doc_pairs = {
        (match.group(1), match.group(2))
        for match in re.finditer(r"^\|\s*`([A-Z_]+)`\s*\|\s*`([A-Z_]+)`", contract, re.MULTILINE)
    }
    if not code_pairs or doc_pairs != code_pairs:
        _error(
            errors,
            "transition_contract_parity",
            f"only in writer {sorted(code_pairs - doc_pairs)!r}, only in task-model {sorted(doc_pairs - code_pairs)!r}",
        )
    if re.search(r"(?<![\w`])/[a-z]+", contract):
        _error(errors, "transition_contract_command_name", "task-model 5-1 names a command; commands belong in 5-2")
    for match in re.finditer(r"`([A-Z_]+)` → `([A-Z_]+)`", paths):
        if (match.group(1), match.group(2)) not in doc_pairs:
            _error(errors, "transition_path_unknown", f"task-model 5-2 uses {match.group(0)!r}, not in 5-1")
    # task-0180: the status vocabulary in task-model 3 is exactly the writer's. ON_HOLD
    # (task-0098) and CLOSED each had to be added in several places; this keeps the
    # standard document from lagging the code.
    node = _module_constant(tree, "TASK_ALLOWED_STATUSES")
    try:
        code_statuses = set(ast.literal_eval(node.args[0])) if isinstance(node, ast.Call) and node.args else set()
    except ValueError:
        code_statuses = set()
    status_line = re.search(r"^- `status`: 현재 상태 \(`([A-Z_ |]+)`\)\r?$", _section(model, "## 3) 필수 필드", r"^## "), re.MULTILINE)
    doc_statuses = set(status_line.group(1).split(" | ")) if status_line else set()
    if not code_statuses or doc_statuses != code_statuses:
        _error(
            errors,
            "status_vocabulary_parity",
            f"only in writer {sorted(code_statuses - doc_statuses)!r}, only in task-model {sorted(doc_statuses - code_statuses)!r}",
        )


def _validate_sources(sources: dict[str, str]) -> list[str]:
    errors: list[str] = []
    agents = _parse_agents(sources, errors)
    _validate_role_boundaries(sources, agents, errors)
    _validate_reviewer_parity(sources, agents, errors)
    _validate_reviewer_reference_forms(sources, agents, errors)
    _validate_budget_and_candidate_rules(sources, agents, errors)
    _validate_escalation_gates(sources, agents, errors)
    _validate_master_plan(sources, errors)
    _validate_contradictions(sources, errors)
    _validate_source_map(sources, errors)
    _validate_pipeline_parity(sources, errors)
    _validate_transition_contract(sources, errors)
    _require_all(errors, "sop_findings_acceptance", SOP_PATH, sources.get(SOP_PATH, ""), SOP_ACCEPTANCE_CLAUSES)
    _require_all(errors, "sop_reference_commits", SOP_PATH, sources.get(SOP_PATH, ""), SOP_REFERENCE_CLAUSES)
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
        (
            "manager_verbatim_quote_removed",
            SOP_PATH,
            "Owner 승인 메시지의 포함·제외 조건을 task 기록에 요약 없이 원문 그대로",
            "Owner approval quote rule removed",
            "owner_approval_verbatim",
        ),
        (
            "manager_passes_approval_removed",
            SOP_PATH,
            "Reviewer assignment에는 Manager 요약과 함께 Owner 승인 원문을 전달한다.",
            "Reviewer approval handoff removed.",
            "owner_approval_verbatim",
        ),
        (
            "reviewer_judges_against_approval_removed",
            SOP_PATH,
            "Manager 요약과 Owner 승인 원문을 함께 받고, diff의 범위는 승인 원문을 기준으로",
            "Reviewer approval comparison removed",
            "owner_approval_verbatim",
        ),
        (
            "reviewer_requires_approval_removed",
            ".codex/agents/reviewer.toml",
            "Require the Owner's approval verbatim from Manager (the caller) under the marker line OWNER APPROVAL (verbatim).",
            "Approval requirement removed.",
            "reviewer_approval_binding",
        ),
        (
            "reviewer_blocks_without_approval_removed",
            ".codex/agents/reviewer.toml",
            "return verdict BLOCKED with a blocking finding and review nothing",
            "continue reviewing",
            "reviewer_approval_binding",
        ),
        (
            "reviewer_scope_against_approval_removed",
            ".codex/agents/reviewer.toml",
            "Judge diff scope against the verbatim approval",
            "Judge diff scope against the summary",
            "reviewer_approval_binding",
        ),
        # task-0147: source map, pipeline parity and transition contract.
        ("source_map_removed", MAP_PATH, "## 기준 지도", "## 지도 없음", "source_map_missing"),
        ("source_map_area_removed", MAP_PATH, "| 현재 시스템 동작 |", "| 기타 |", "source_map_area"),
        (
            "source_map_missing_file",
            MAP_PATH,
            "`docs/task-model.md` |",
            "`docs/missing-task-model.md` |",
            "source_map_path",
        ),
        (
            "source_map_behavior_from_handoff",
            MAP_PATH,
            "`.codex/agents/*.toml` |",
            "`.codex/agents/*.toml`, `docs/chatgpt-handoff.md` |",
            "source_map_behavior_source",
        ),
        (
            "source_map_history_handoff_removed",
            MAP_PATH,
            "- `docs/chatgpt-handoff.md` (특정 시점 스냅샷)",
            "- 스냅샷",
            "source_map_history",
        ),
        (
            "source_map_scope_rule_removed",
            MAP_PATH,
            "Owner 승인은 그 승인을 받은 task의 범위 안에서만 효력이 있다.",
            "Owner 승인은 계속 효력이 있다.",
            "source_map_rules",
        ),
        *(
            (f"delegation_removed_{index}", path, "기준 지도", "지도", "source_map_delegation")
            for index, path in enumerate(DELEGATION_CLAUSES, start=1)
        ),
        ("pipeline_budget_raised", SOP_PATH, "파이프라인 상한은 1이다", "파이프라인 상한은 2이다", "pipeline_budget_parity"),
        ("pipeline_reason_dropped_from_sop", SOP_PATH, "`resume_conflict`다", "충돌 거절이다", "pipeline_reason_parity"),
        ("pipeline_reason_renamed_in_code", WORKER_PATH, '"resume_conflict"', '"resume_clash"', "pipeline_reason_parity"),
        ("pipeline_qa_key_dropped", SOP_PATH, "`json_valid`,", "", "pipeline_qa_parity"),
        (
            "pipeline_scope_prefix_changed",
            SOP_PATH,
            "| `apps/studyroom/`(studyroom_content),",
            "| `apps/other/`(studyroom_content),",
            "pipeline_scope_parity",
        ),
        # task-0164: every registry kind must be stated, and only those.
        (
            "pipeline_kind_dropped_from_sop",
            SOP_PATH,
            "`daily_ai_radar`(Daily AI Radar 수정",
            "daily_ai_radar (Daily AI Radar 수정",
            "pipeline_scope_parity",
        ),
        (
            "pipeline_kind_renamed_in_code",
            WORKER_PATH,
            'name="daily_ai_radar",',
            'name="daily_ai_radar_v2",',
            "pipeline_scope_parity",
        ),
        (
            "pipeline_kind_prefix_changed_in_code",
            WORKER_PATH,
            'allowed_prefix="apps/daily-ai-radar/",',
            'allowed_prefix="apps/",',
            "pipeline_scope_parity",
        ),
        (
            "pipeline_kind_test_changed_in_sop",
            SOP_PATH,
            "`apps/daily-ai-radar/run_smoke_tests.py`(daily_ai_radar)",
            "`apps/daily-ai-radar/other_tests.py`(daily_ai_radar)",
            "pipeline_scope_parity",
        ),
        (
            "transition_added_to_contract",
            TASK_MODEL_PATH,
            "| `FAILED` | `TODO` |",
            "| `FAILED` | `TODO` |\n| `DONE` | `TODO` |",
            "transition_contract_parity",
        ),
        ("transition_removed_from_writer", WRITER_PATH, '("FAILED", "TODO"),', "", "transition_contract_parity"),
        (
            "transition_contract_names_command",
            TASK_MODEL_PATH,
            "| `TODO` | `DOING` |",
            "| `TODO` | `DOING` (/go) |",
            "transition_contract_command_name",
        ),
        (
            "transition_path_outside_contract",
            TASK_MODEL_PATH,
            "성공 `DOING` → `DONE`",
            "성공 `DOING` → `ARCHIVED`",
            "transition_path_unknown",
        ),
        (
            "status_dropped_from_task_model",
            TASK_MODEL_PATH,
            "| NEEDS_APPROVAL | CLOSED`)",
            "| NEEDS_APPROVAL`)",
            "status_vocabulary_parity",
        ),
        (
            "status_added_to_writer",
            WRITER_PATH,
            '"DONE", "CLOSED"}',
            '"DONE", "CLOSED", "ARCHIVED"}',
            "status_vocabulary_parity",
        ),
        ("sop_acceptance_major_clause_removed", SOP_PATH, "- blocking과 major는 수용할 수 없다.", "- 수용 제한 없음.", "sop_findings_acceptance"),
        ("sop_acceptance_pipeline_clause_removed", SOP_PATH, "- §10 Worker 파이프라인에는 적용하지 않는다.", "", "sop_findings_acceptance"),
        ("pipeline_self_deviation_dropped_from_sop", SOP_PATH, "`reviewer_self_deviation`으로", "재검토 실패로", "pipeline_reason_parity"),
        ("pipeline_unverified_review_dropped_from_sop", SOP_PATH, "`qa_unverified_owner_review`로", "Owner 확인 실패로", "pipeline_reason_parity"),
        ("pipeline_accept_reason_dropped_from_sop", SOP_PATH, "`accept_qa_failed`로", "QA 재실행 실패로", "pipeline_reason_parity"),
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
        (
            "handoff_claims_every_area",
            "docs/chatgpt-handoff.md",
            "This handoff is the source of truth for all areas.",
            "global_source_of_truth_contradiction",
        ),
        (
            "findings_acceptance_made_general",
            SOP_PATH,
            "Manager가 finding을 수용할 수 있다.",
            "findings_acceptance_rule_contradiction",
        ),
        (
            "findings_acceptance_major_allowed",
            SOP_PATH,
            "major도 Owner가 수용할 수 있다.",
            "findings_acceptance_rule_contradiction",
        ),
        (
            "findings_acceptance_pipeline_automatic",
            SOP_PATH,
            "파이프라인은 minor finding을 자동으로 수용한다.",
            "findings_acceptance_rule_contradiction",
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

    for path, prefix in (
        (CLAUDE_REVIEWER_PATH, "claude"),
        (CODEX_REVIEWER_PATH, "codex"),
    ):
        for index, clause in enumerate(REVIEWER_ROLE_CLAUSES, start=1):
            label = f"{prefix}_reviewer_clause_{index:02d}_removed"
            try:
                mutated = _replace_once(
                    sources, path, clause, "REMOVED_REVIEWER_CLAUSE"
                )
            except (KeyError, ValueError) as exc:
                failures.append(f"{label}: {exc}")
                continue
            checks.append((label, mutated, "reviewer_role_parity"))

    claude_caller = dict(sources)
    claude_caller[CLAUDE_REVIEWER_PATH] = (
        claude_caller.get(CLAUDE_REVIEWER_PATH, "") + "\nReport back to the caller.\n"
    )
    checks.append(
        ("claude_reviewer_bare_caller", claude_caller, "reviewer_caller_name")
    )
    try:
        codex_caller = _append_agent_instruction(
            sources, "reviewer.toml", "Report back to the caller."
        )
        checks.append(
            ("codex_reviewer_bare_caller", codex_caller, "reviewer_caller_name")
        )
    except (KeyError, ValueError) as exc:
        failures.append(f"codex_reviewer_bare_caller: {exc}")

    # task-0177: an unapproved or altered `<reference>` form, and the SOP limits.
    merge_base_line = f"- `{REVIEWER_REFERENCE_FORMS[0]}`"
    diff_line = f"- `{REVIEWER_REFERENCE_FORMS[1]}`"
    for path, prefix in (
        (CLAUDE_REVIEWER_PATH, "claude"),
        (CODEX_REVIEWER_PATH, "codex"),
    ):
        for label, old, new in (
            (
                f"{prefix}_reviewer_unapproved_reference_form",
                merge_base_line,
                "- `git log --format=<format> <reference>..<baseline> -- <path>`\n" + merge_base_line,
            ),
            (
                f"{prefix}_reviewer_reference_diff_without_path",
                diff_line,
                "- `git diff <reference> <hash>`",
            ),
        ):
            try:
                checks.append(
                    (label, _replace_once(sources, path, old, new), "reviewer_reference_forms")
                )
            except (KeyError, ValueError) as exc:
                failures.append(f"{label}: {exc}")
    for index, clause in enumerate(SOP_REFERENCE_CLAUSES, start=1):
        label = f"sop_reference_clause_{index:02d}_removed"
        try:
            checks.append(
                (
                    label,
                    _replace_once(sources, SOP_PATH, clause, "REMOVED_REFERENCE_CLAUSE"),
                    "sop_reference_commits",
                )
            )
        except (KeyError, ValueError) as exc:
            failures.append(f"{label}: {exc}")

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
