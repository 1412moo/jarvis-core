"""Minimal local smoke tests for the Discord NL intent layer.

Phase 1 (rule-based resolve_intent) and Phase 2A (provider-agnostic
IntentResult/dispatch/llm_provider stub) tests live in this single file so
"the existing suite still passes" is one command, per repo convention.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import intent_router
from intent_router import resolve_intent
from intent_schema import IntentResult
from intent_dispatcher import (
    CONTINUE_TASK_CLARIFICATION,
    MISSING_QUERY_CLARIFICATION,
    MISSING_TASK_ID_CLARIFICATION,
    MISSING_TITLE_CLARIFICATION,
    REPORT_YESTERDAY_CLARIFICATION,
    RESEARCH_COUNCIL_NOT_APPROVED_REPLY,
    dispatch,
)
from llm_provider import call_llm_for_intent

REPO_ROOT = THIS_DIR.parent.parent
BOT_MINIMAL_PATH = REPO_ROOT / "adapters" / "discord" / "bot_minimal.py"
PHASE_2A_SOURCE_PATHS = (
    THIS_DIR / "intent_schema.py",
    THIS_DIR / "intent_dispatcher.py",
    THIS_DIR / "llm_provider.py",
)


# ---------------------------------------------------------------------------
# Phase 1 (unchanged): rule-based mapping + defensive/structural guards
# ---------------------------------------------------------------------------
def _run_mapping_case(name: str, text: str, expected: str | None) -> dict[str, object]:
    actual = resolve_intent(text)
    passed = actual == expected
    return {
        "name": name,
        "text": text,
        "expected": expected,
        "actual": actual,
        "passed": passed,
    }


def _run_bot_minimal_hook_case() -> dict[str, object]:
    """Structural regression guard, updated for the Phase 2A fallback hook.

    Invariant unchanged from Phase 1: resolve_intent() is called exactly
    once in bot_minimal.py, only inside the non-slash branch of on_message.
    Phase 2A adds one more invariant: resolve_llm_fallback() is called
    exactly once, only inside that same branch, and strictly after
    `if resolved_command is None:` -- i.e. only on a rule miss, never on a
    rule match.
    """

    source = BOT_MINIMAL_PATH.read_text(encoding="utf-8")

    non_slash_start_match = re.search(r'if not content\.startswith\("/"\):\n', source)
    slash_allowlist_start_match = re.search(r"\n        if \(\n            not content\.startswith", source)
    non_slash_start = non_slash_start_match.start() if non_slash_start_match else -1
    non_slash_end = slash_allowlist_start_match.start() if slash_allowlist_start_match else -1
    non_slash_branch = source[non_slash_start:non_slash_end] if 0 <= non_slash_start < non_slash_end else ""

    resolve_intent_call_sites = [m.start() for m in re.finditer(r"resolve_intent\(", source)]
    fallback_call_sites = [m.start() for m in re.finditer(r"resolve_llm_fallback\(", source)]
    resolve_intent_in_branch = sum(1 for pos in resolve_intent_call_sites if non_slash_start <= pos < non_slash_end)
    fallback_in_branch = sum(1 for pos in fallback_call_sites if non_slash_start <= pos < non_slash_end)

    rule_miss_gate_pattern = re.compile(
        r"if resolved_command is None:\s*fallback_outcome = resolve_llm_fallback\(content\)"
    )
    fallback_only_after_rule_miss = rule_miss_gate_pattern.search(non_slash_branch) is not None

    passed = (
        len(resolve_intent_call_sites) == 1
        and resolve_intent_in_branch == 1
        and len(fallback_call_sites) == 1
        and fallback_in_branch == 1
        and fallback_only_after_rule_miss
    )
    return {
        "name": "bot_minimal_hook_is_single_non_slash_gate",
        "resolve_intent_call_site_count": len(resolve_intent_call_sites),
        "resolve_intent_in_non_slash_branch": resolve_intent_in_branch,
        "resolve_llm_fallback_call_site_count": len(fallback_call_sites),
        "resolve_llm_fallback_in_non_slash_branch": fallback_in_branch,
        "fallback_only_after_rule_miss": fallback_only_after_rule_miss,
        "passed": passed,
    }


def _run_slash_input_defensive_case() -> dict[str, object]:
    actual = resolve_intent("/report today")
    passed = actual is None
    return {
        "name": "resolve_intent_rejects_slash_prefixed_input",
        "text": "/report today",
        "expected": None,
        "actual": actual,
        "passed": passed,
    }


# ---------------------------------------------------------------------------
# Phase 2A: schema
# ---------------------------------------------------------------------------
def _run_schema_valid_case() -> dict[str, object]:
    try:
        result = IntentResult(
            intent="status",
            arguments={"task_id": "task-0029-research-council-live-augmentation"},
            confidence=0.9,
            clarification_needed=False,
            clarification_question=None,
        )
        passed = (
            result.intent == "status"
            and result.arguments == {"task_id": "task-0029-research-council-live-augmentation"}
            and result.confidence == 0.9
            and result.clarification_needed is False
            and result.clarification_question is None
        )
    except ValueError:
        passed = False
    return {"name": "schema_valid_intent_result", "passed": passed}


def _run_schema_rejects_case(name: str, overrides: dict[str, object]) -> dict[str, object]:
    base: dict[str, object] = {
        "intent": "status",
        "arguments": {},
        "confidence": 0.9,
        "clarification_needed": False,
        "clarification_question": None,
    }
    base.update(overrides)
    try:
        IntentResult(**base)
        passed = False
    except (ValueError, TypeError):
        passed = True
    return {"name": name, "passed": passed}


# ---------------------------------------------------------------------------
# Phase 2A: dispatcher
# ---------------------------------------------------------------------------
def _make_intent_result(**overrides: object) -> IntentResult:
    base: dict[str, object] = {
        "intent": "report_today",
        "arguments": {},
        "confidence": 0.9,
        "clarification_needed": False,
        "clarification_question": None,
    }
    base.update(overrides)
    return IntentResult(**base)  # type: ignore[arg-type]


def _run_dispatch_case(
    name: str,
    intent_result: IntentResult,
    *,
    expected_command: str | None = None,
    expected_reply: str | None = None,
    expect_ignored: bool = False,
) -> dict[str, object]:
    outcome = dispatch(intent_result)
    if expect_ignored:
        passed = outcome.command is None and outcome.reply is None
    elif expected_command is not None:
        passed = outcome.command == expected_command
    elif expected_reply is not None:
        passed = outcome.reply == expected_reply
    else:
        passed = False
    return {
        "name": name,
        "command": outcome.command,
        "reply": outcome.reply,
        "passed": passed,
    }


# ---------------------------------------------------------------------------
# Phase 2A: security
# ---------------------------------------------------------------------------
def _run_injected_command_ignored_case() -> dict[str, object]:
    """An extra `arguments["command"]` from an untrusted LLM must never be
    read or executed -- dispatch() only ever reads the exact keys each intent
    branch expects (e.g. task_id, title, action, query)."""

    intent_result = _make_intent_result(
        intent="status",
        arguments={
            "task_id": "not-a-real-id",
            "command": "/approve task-0029-research-council-live-augmentation approve",
        },
    )
    outcome = dispatch(intent_result)
    passed = outcome.command is None and outcome.reply == MISSING_TASK_ID_CLARIFICATION
    return {"name": "security_injected_command_argument_ignored", "outcome": str(outcome), "passed": passed}


def _run_path_traversal_rejected_case() -> dict[str, object]:
    intent_result = _make_intent_result(
        intent="approve_task",
        arguments={"task_id": "../../etc/passwd", "action": "approve"},
    )
    outcome = dispatch(intent_result)
    passed = outcome.command is None
    return {"name": "security_task_id_path_traversal_rejected", "outcome": str(outcome), "passed": passed}


def _run_shell_metacharacter_case() -> dict[str, object]:
    """A title containing shell metacharacters must be embedded as literal
    text in the fixed /task template, never interpreted -- there is no
    subprocess/shell anywhere between dispatch() and the resulting string."""

    title = "hello; rm -rf / && echo pwned"
    intent_result = _make_intent_result(intent="create_task", arguments={"title": title})
    outcome = dispatch(intent_result)
    passed = outcome.command == f"/task {title}"
    return {"name": "security_shell_metacharacters_stay_literal", "command": outcome.command, "passed": passed}


def _run_no_eval_exec_case() -> dict[str, object]:
    offenders = []
    for path in PHASE_2A_SOURCE_PATHS:
        source = path.read_text(encoding="utf-8")
        if re.search(r"\beval\s*\(", source) or re.search(r"\bexec\s*\(", source):
            offenders.append(str(path))
    return {"name": "security_no_eval_or_exec", "offenders": offenders, "passed": not offenders}


def _run_no_subprocess_case() -> dict[str, object]:
    """Scoped to the new Phase 2A files only. bot_minimal.py legitimately
    uses subprocess for its separate, pre-existing whitelisted /run and
    /retry feature -- out of scope for this Phase 2A check."""

    subprocess_usage_pattern = re.compile(r"\bimport subprocess\b|\bsubprocess\.")
    offenders = []
    for path in PHASE_2A_SOURCE_PATHS:
        source = path.read_text(encoding="utf-8")
        if subprocess_usage_pattern.search(source):
            offenders.append(str(path))
    return {"name": "security_no_subprocess_in_phase_2a_files", "offenders": offenders, "passed": not offenders}


# ---------------------------------------------------------------------------
# Phase 2A: provider stub
# ---------------------------------------------------------------------------
def _run_provider_stub_case() -> dict[str, object]:
    samples = ["오늘 뭐 해야 해?", "이 아이디어 조사해줘", ""]
    results = [call_llm_for_intent(sample) for sample in samples]
    passed = all(result is None for result in results)
    return {"name": "llm_provider_stub_always_none", "results": results, "passed": passed}


# ---------------------------------------------------------------------------
# Phase 2A: router regression (rule priority preserved, no LLM call on match)
# ---------------------------------------------------------------------------
def _run_rule_match_skips_llm_case() -> dict[str, object]:
    call_count = {"n": 0}
    original = intent_router.call_llm_for_intent

    def _counting_stub(text: str):
        call_count["n"] += 1
        return None

    intent_router.call_llm_for_intent = _counting_stub
    try:
        rule_matched_text = "오늘 할 일 정리해줘"
        rule_result = intent_router.resolve_intent(rule_matched_text)
        # Mirror bot_minimal.py::on_message's exact order: the fallback is
        # only ever invoked when the rule result is None.
        if rule_result is None:
            intent_router.resolve_llm_fallback(rule_matched_text)
        count_after_rule_match = call_count["n"]

        rule_missed_text = "강아지 관련 작업 어떻게 됐어?"
        rule_result_2 = intent_router.resolve_intent(rule_missed_text)
        if rule_result_2 is None:
            intent_router.resolve_llm_fallback(rule_missed_text)
        count_after_rule_miss = call_count["n"]
    finally:
        intent_router.call_llm_for_intent = original

    passed = (
        rule_result == "/report today"
        and count_after_rule_match == 0
        and rule_result_2 is None
        and count_after_rule_miss == 1
    )
    return {
        "name": "rule_match_never_calls_llm_provider",
        "count_after_rule_match": count_after_rule_match,
        "count_after_rule_miss": count_after_rule_miss,
        "passed": passed,
    }


def main() -> None:
    mapping_cases = [
        ("report_today_ko", "오늘 할 일 정리해줘", "/report today"),
        ("status_task_0029", "task-0029 상태 알려줘", "/status task-0029"),
        ("status_task_0028_progress", "task-0028 진행 상황 알려줘", "/status task-0028"),
        ("unsupported_topic_search", "강아지 관련 작업 어떻게 됐어?", None),
        ("unsupported_research_request", "이 아이디어 조사해줘", None),
        ("unsupported_vague_progress", "지난번 작업 어디까지 했어?", None),
        ("empty_input", "", None),
    ]

    results = [_run_mapping_case(*case) for case in mapping_cases]
    results.append(_run_slash_input_defensive_case())
    results.append(_run_bot_minimal_hook_case())

    # Schema
    results.append(_run_schema_valid_case())
    results.append(_run_schema_rejects_case("schema_confidence_below_zero", {"confidence": -0.1}))
    results.append(_run_schema_rejects_case("schema_confidence_above_one", {"confidence": 1.1}))
    results.append(_run_schema_rejects_case("schema_invalid_arguments_type", {"arguments": ["not", "a", "dict"]}))
    results.append(
        _run_schema_rejects_case("schema_invalid_clarification_question_type", {"clarification_question": 12345})
    )

    # Dispatcher
    results.append(
        _run_dispatch_case(
            "dispatch_report_today",
            _make_intent_result(intent="report_today"),
            expected_command="/report today",
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_status_valid_task_id",
            _make_intent_result(
                intent="status",
                arguments={"task_id": "task-0029-research-council-live-augmentation"},
            ),
            expected_command="/status task-0029-research-council-live-augmentation",
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_status_invalid_task_id_not_executed",
            _make_intent_result(intent="status", arguments={"task_id": "../../something"}),
            expected_reply=MISSING_TASK_ID_CLARIFICATION,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_create_task_valid_title",
            _make_intent_result(intent="create_task", arguments={"title": "새로운 task 제목"}),
            expected_command="/task 새로운 task 제목",
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_create_task_empty_title_not_executed",
            _make_intent_result(intent="create_task", arguments={"title": ""}),
            expected_reply=MISSING_TITLE_CLARIFICATION,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_create_task_oversized_title_not_executed",
            _make_intent_result(intent="create_task", arguments={"title": "x" * 500}),
            expected_reply=MISSING_TITLE_CLARIFICATION,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_approve_task_valid",
            _make_intent_result(
                intent="approve_task",
                arguments={"task_id": "task-0029-research-council-live-augmentation", "action": "approve"},
            ),
            expected_command="/approve task-0029-research-council-live-augmentation approve",
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_unknown_intent_not_executed",
            _make_intent_result(intent="totally_unknown_intent"),
            expect_ignored=True,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_research_request_not_approved_reply",
            _make_intent_result(intent="research_request"),
            expected_reply=RESEARCH_COUNCIL_NOT_APPROVED_REPLY,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_continue_task_without_task_id_clarification",
            _make_intent_result(intent="continue_task"),
            expected_reply=CONTINUE_TASK_CLARIFICATION,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_report_yesterday_clarification",
            _make_intent_result(intent="report_yesterday"),
            expected_reply=REPORT_YESTERDAY_CLARIFICATION,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_search_tasks_missing_query_clarification",
            _make_intent_result(intent="search_tasks", arguments={"query": ""}),
            expected_reply=MISSING_QUERY_CLARIFICATION,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_low_confidence_status_not_executed",
            _make_intent_result(
                intent="status",
                arguments={"task_id": "task-0029-research-council-live-augmentation"},
                confidence=0.3,
            ),
            expect_ignored=True,
        )
    )
    results.append(
        _run_dispatch_case(
            "dispatch_clarification_needed_flag_overrides",
            _make_intent_result(
                intent="status",
                arguments={"task_id": "task-0029-research-council-live-augmentation"},
                clarification_needed=True,
                clarification_question="정확히 어떤 task인가요?",
            ),
            expected_reply="정확히 어떤 task인가요?",
        )
    )

    # Security
    results.append(_run_injected_command_ignored_case())
    results.append(_run_path_traversal_rejected_case())
    results.append(_run_shell_metacharacter_case())
    results.append(_run_no_eval_exec_case())
    results.append(_run_no_subprocess_case())

    # Provider stub
    results.append(_run_provider_stub_case())

    # Router regression
    results.append(_run_rule_match_skips_llm_case())

    failed = [result for result in results if not result["passed"]]

    print("\n=== DISCORD NL INTENT SMOKE TEST SUMMARY ===")
    print(json.dumps({"total": len(results), "failed": len(failed), "results": results}, ensure_ascii=False, indent=2))

    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
