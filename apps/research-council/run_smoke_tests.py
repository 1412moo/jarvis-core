"""Smoke tests for the deterministic Research Council v0.1 pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from research_council import (
    ALLOWED_AUGMENTATION_CATEGORIES,
    LLMAdvisorConfig,
    LLMAugmentationMode,
    ResearchCouncilInput,
    get_profile,
    list_profiles,
    result_from_json,
    result_to_artifacts_dict,
    result_to_json,
    result_to_json_dict,
    resolve_domain_profile,
    run_research_council,
)
from research_council.evaluation import (
    build_benchmark_analytics,
    evaluate_golden_cases,
    format_benchmark_analytics,
    format_regression_summary,
)
from research_council.benchmark_snapshot import (
    benchmark_snapshot_from_json_dict,
    benchmark_snapshot_to_json_dict,
    compare_benchmark_snapshots,
    export_benchmark_snapshot,
    load_benchmark_snapshot,
    snapshot_to_json,
    validate_benchmark_pack_metadata,
)
from research_council.benchmark_history import (
    append_benchmark_history,
    benchmark_history_entry_from_json_dict,
    benchmark_history_entry_to_json_dict,
    build_benchmark_diff_view,
    build_benchmark_diff_view_from_history,
    categorize_benchmark_drift,
    classify_benchmark_governance_severity,
    compare_latest_to_previous,
    format_benchmark_diff_view,
    format_benchmark_governance_summary,
    format_benchmark_trend_summary,
    history_to_json,
    load_benchmark_history,
)
from research_council.mutation_tests import (
    build_mutation_cases,
    build_template_mutation_cases,
    format_mutation_summary,
    run_mutation_tests,
)
from research_council.scenario_templates import (
    CATEGORY_ORDER,
    PROFILE_ORDER,
    build_scenario_summary,
    format_scenario_summary,
    generate_scenarios,
    scenarios_to_json,
)
from run_demo import build_sample_input


REQUIRED_REVIEWER_ROLES = {
    "technical",
    "market",
    "safety_regulatory",
    "red_team",
}

REQUIRED_GAP_CATEGORIES = {
    "technical",
    "user_adoption",
    "prior_art",
    "safety_regulatory",
    "environmental",
    "market",
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _combined_reasoning_trace(entries: list[dict[str, object]]) -> str:
    trace_parts: list[str] = []
    for entry in entries:
        traces = entry.get("reasoning_trace", ())
        if isinstance(traces, list):
            trace_parts.extend(str(trace) for trace in traces)
    return " ".join(trace_parts).lower()


def _assert_scenario_template_coverage(coverage: dict[str, object]) -> None:
    _assert(
        coverage.get("coverage_type") == "generated_metadata",
        "scenario template coverage must be labeled as generated metadata",
    )
    _assert(
        coverage.get("total_scenarios") == 42,
        "scenario template coverage must record generated scenario count",
    )
    _assert(
        coverage.get("categories_count") == 6,
        "scenario template coverage must record category count",
    )
    _assert(
        coverage.get("profiles_count") == 7,
        "scenario template coverage must record profile count",
    )
    _assert(
        coverage.get("template_mutation_subset_count") == 6,
        "scenario template coverage must record lightweight mutation subset count",
    )
    _assert(
        set(coverage.get("categories_covered", ())) == set(CATEGORY_ORDER),
        "scenario template coverage must record covered categories",
    )
    _assert(
        tuple(coverage.get("profiles_covered", ())) == PROFILE_ORDER,
        "scenario template coverage must record covered profiles",
    )
    serialized = json.dumps(coverage, sort_keys=True)
    for forbidden_text in (
        "C:",
        "jarvis-core",
        "raw_idea",
        "goal",
        "input_data",
        "scenario_id",
    ):
        _assert(
            forbidden_text not in serialized,
            f"scenario template coverage must not store raw scenario data: {forbidden_text}",
        )


def _assert_benchmark_pack_metadata(metadata: dict[str, object]) -> None:
    violations = validate_benchmark_pack_metadata(metadata)
    _assert(
        not violations,
        "benchmark pack metadata must match the frozen contract: "
        + ", ".join(violations),
    )
    serialized = json.dumps(metadata, sort_keys=True)
    for forbidden_text in (
        "C:",
        "jarvis-core",
        "raw_idea",
        "goal",
        "input_data",
        "scenario_id",
    ):
        _assert(
            forbidden_text not in serialized,
            f"benchmark pack metadata must not store raw benchmark data: {forbidden_text}",
        )


def test_deterministic_pipeline_contract() -> None:
    result = run_research_council(build_sample_input())

    _assert(result.result_type == "research_council_result", "unexpected result_type")
    _assert(result.version == "0.1", "unexpected version")
    _assert(result.profile["profile_id"] == "medical_device", "sample profile must resolve")
    _assert(
        result.profile["selected_by"] == "deterministic_score",
        "sample profile must be selected by deterministic scoring",
    )
    _assert(result.claims, "claims must exist")
    _assert(result.evidence_ledger, "evidence ledger must exist")
    _assert(result.experiments, "experiments must exist")
    _assert(result.recommendation.decision, "recommendation must include a decision")
    _assert(result.recommendation.summary, "recommendation must include a summary")
    _assert(
        result.recommendation.next_step.count("experiment-") == 1,
        "recommendation must select one primary next experiment",
    )
    _assert(
        "concept input" in result.recommendation.summary,
        "recommendation must distinguish concept description from proof",
    )
    _assert(result.markdown_report.artifact_type == "markdown", "report must be markdown")
    _assert(result.markdown_report.markdown.strip(), "markdown report must exist")

    claim_ids = {claim.id for claim in result.claims}
    covered_claim_ids = {entry.claim_id for entry in result.evidence_ledger}
    _assert(claim_ids <= covered_claim_ids, "every claim must have evidence coverage")

    reviewer_roles = {critique.reviewer_role for critique in result.reviewer_critiques}
    _assert(
        REQUIRED_REVIEWER_ROLES <= reviewer_roles,
        "reviewer critiques must include technical, market, safety_regulatory, and red_team",
    )

    missing_entries = [
        entry for entry in result.evidence_ledger if entry.evidence_type == "missing"
    ]
    _assert(missing_entries, "missing evidence must be represented explicitly")
    _assert(
        any(claim.source_label == "needs_evidence" for claim in result.claims),
        "claims must mark evidence needs",
    )
    for category in REQUIRED_GAP_CATEGORIES:
        _assert(
            any(f"gap_category={category}" in entry.notes for entry in result.evidence_ledger),
            f"evidence gaps must include category {category}",
        )

    markdown = result.markdown_report.markdown
    _assert(markdown.startswith("# Research Council Report"), "report markdown missing title")
    _assert("## Structured Claims" in markdown, "markdown report missing structured claims")
    _assert("## Evidence Ledger" in markdown, "markdown report missing evidence ledger")
    _assert("## Reviewer Critiques" in markdown, "markdown report missing critiques")
    _assert("## Minimum Viable Experiments" in markdown, "markdown report missing experiments")
    _assert("## Recommendation" in markdown, "markdown report missing recommendation")
    _assert("Missing evidence entries" in markdown, "markdown report must show evidence gaps")
    _assert(
        "Local determinism spike" not in markdown,
        "developer QA experiments must not appear in the user-facing report",
    )
    _assert("primary next experiment" in markdown, "report must identify a primary next experiment")
    _assert("capsule" in markdown.lower(), "capsule sample must be reflected in the report")
    _assert("colon" in markdown.lower(), "colon screening sample must be reflected in the report")


def test_json_export_contract() -> None:
    input_data = build_sample_input()
    result = run_research_council(input_data)

    payload = result_to_json_dict(result)
    loaded_payload = json.loads(result_to_json(result))
    _assert(loaded_payload == payload, "JSON payload must round-trip through json.loads")
    _assert(
        result_from_json(result_to_json(result)) == result,
        "JSON payload must rehydrate to the original result",
    )

    _assert(loaded_payload["result_type"] == "research_council_result", "JSON result_type missing")
    _assert(loaded_payload["version"] == "0.1", "JSON version missing")
    _assert(
        loaded_payload["profile"]["profile_id"] == "medical_device",
        "JSON profile id must be preserved",
    )
    _assert(
        loaded_payload["profile"]["selected_by"] == "deterministic_score",
        "JSON profile selected_by must be preserved",
    )
    _assert(
        "capsule" in loaded_payload["profile"]["matched_keywords"]["medical_device"],
        "JSON profile matched keywords must be preserved",
    )
    _assert(
        loaded_payload["profile"]["score_by_profile"]["medical_device"] > 0,
        "JSON profile scores must be preserved",
    )
    _assert(
        "reasoning_policy" in loaded_payload["profile"],
        "JSON profile metadata must include deterministic reasoning policy",
    )
    quality_signals = loaded_payload.get("quality_signals")
    _assert(isinstance(quality_signals, dict), "JSON quality_signals must be an object")
    for signal_name in (
        "profile_adherence",
        "evidence_coverage",
        "risk_specificity",
        "next_step_actionability",
        "caveat_appropriateness",
    ):
        _assert(signal_name in quality_signals, f"quality_signals missing {signal_name}")
        _assert(
            quality_signals[signal_name]["status"] in {"strong", "partial", "weak"},
            f"quality signal {signal_name} must expose deterministic status",
        )
    _assert(
        quality_signals["evidence_coverage"]["status"] == "strong",
        "quality_signals must report deterministic evidence coverage",
    )
    _assert(
        "patient safety" in quality_signals["caveat_appropriateness"]["matched_terms"],
        "medical quality signals must preserve patient-safety caveat matching",
    )
    _assert(isinstance(loaded_payload["claims"], list), "JSON claims must be a list")
    _assert(
        isinstance(loaded_payload["evidence_ledger"], list),
        "JSON evidence ledger must be a list",
    )
    _assert(
        isinstance(loaded_payload["reviewer_critiques"], list),
        "JSON reviewer critiques must be a list",
    )
    _assert(isinstance(loaded_payload["experiments"], list), "JSON experiments must be a list")
    _assert(
        isinstance(loaded_payload["recommendation"], dict),
        "JSON recommendation must be an object",
    )
    _assert(
        loaded_payload["markdown_report"]["artifact_type"] == "markdown",
        "JSON markdown artifact metadata must be preserved",
    )
    _assert(
        loaded_payload["markdown_report"]["markdown"] == result.markdown_report.markdown,
        "JSON markdown report content must be unchanged",
    )
    missing_entries = [
        entry for entry in loaded_payload["evidence_ledger"] if entry["evidence_type"] == "missing"
    ]
    _assert(missing_entries, "JSON must preserve explicit missing evidence")
    for entry in missing_entries:
        for field_name in (
            "required_evidence",
            "missing_evidence",
            "validation_experiment",
            "confidence_impact",
        ):
            _assert(
                field_name in entry,
                f"JSON missing evidence must include {field_name}",
            )
            _assert(entry[field_name], f"JSON missing evidence {field_name} must be non-empty")
        _assert(
            entry["confidence_impact"]
            in {"confidence_supporting", "confidence_limiter", "confidence_blocker"},
            "JSON evidence confidence impact must use deterministic labels",
        )
    _assert(
        all(entry["reference_label"] is None for entry in missing_entries),
        "JSON missing evidence must not gain reference labels",
    )
    for category in REQUIRED_GAP_CATEGORIES:
        _assert(
            any(f"gap_category={category}" in entry["notes"] for entry in missing_entries),
            f"JSON evidence gaps must include category {category}",
        )

    artifact_payload = result_to_artifacts_dict(result)
    _assert(
        isinstance(artifact_payload["markdown_report"], str),
        "compact artifact JSON must expose markdown_report as text",
    )
    _assert(
        artifact_payload["markdown_report_artifact"]["artifact_type"] == "markdown",
        "compact artifact JSON must preserve markdown artifact metadata",
    )
    _assert(
        artifact_payload["profile"]["profile_id"] == "medical_device",
        "compact artifact JSON must preserve profile id",
    )
    _assert(
        artifact_payload["profile"]["selected_by"] == "deterministic_score",
        "compact artifact JSON must preserve profile selected_by",
    )


def test_optional_llm_augmentation_sandbox() -> None:
    input_data = ResearchCouncilInput(
        raw_idea="AI SaaS patent analysis assistant for solo founders",
        goal="Evaluate buyer workflow, willingness to pay, retention, and differentiation.",
        context="Focus on repeated workflow, generic LLM wrapper risk, and purchase intent.",
    )
    off_result = run_research_council(input_data)
    off_payload = result_to_json_dict(off_result)
    off_augments = off_payload["optional_llm_augments"]
    _assert(off_augments["mode"] == "off", "LLM augmentation must default to off")
    _assert(not off_augments["enabled"], "OFF augmentation must be disabled")
    _assert(off_augments["accepted_count"] == 0, "OFF augmentation must accept nothing")

    safe_result = run_research_council(
        input_data,
        llm_advisor_config=LLMAdvisorConfig(mode=LLMAugmentationMode.TEST_SAFE),
    )
    safe_payload = result_to_json_dict(safe_result)
    safe_augments = safe_payload["optional_llm_augments"]
    _assert(
        safe_result.claims == off_result.claims
        and safe_result.evidence_ledger == off_result.evidence_ledger
        and safe_result.reviewer_critiques == off_result.reviewer_critiques
        and safe_result.experiments == off_result.experiments
        and safe_result.recommendation == off_result.recommendation,
        "LLM augmentation must not overwrite deterministic pipeline outputs",
    )
    _assert(safe_augments["mode"] == "test_safe", "TEST_SAFE mode must be reported")
    _assert(safe_augments["accepted_count"] > 0, "TEST_SAFE must accept safe augments")
    _assert(safe_augments["filtered_count"] == 0, "TEST_SAFE should not filter safe augments")
    _assert(safe_augments["rejected_count"] == 0, "TEST_SAFE should not reject safe augments")
    _assert(
        set(safe_augments["validated_augments"]) <= ALLOWED_AUGMENTATION_CATEGORIES,
        "LLM augments must stay inside allowed additive scopes",
    )
    accepted_text = " ".join(
        item["text"]
        for items in safe_augments["validated_augments"].values()
        for item in items
    ).lower()
    _assert(
        "high confidence" not in accepted_text and "replace" not in accepted_text,
        "accepted augments must not escalate confidence or replace deterministic output",
    )

    noisy_result = run_research_council(
        input_data,
        llm_advisor_config=LLMAdvisorConfig(mode=LLMAugmentationMode.TEST_NOISY),
    )
    noisy_payload = result_to_json_dict(noisy_result)
    noisy_augments = noisy_payload["optional_llm_augments"]
    noisy_reasons = {
        item["rejection_reason"]
        for item in noisy_augments["rejected_augments_summary"]
    }
    _assert(noisy_augments["accepted_count"] > 0, "TEST_NOISY keeps valid safe augments")
    _assert(noisy_augments["filtered_count"] > 0, "TEST_NOISY must filter duplicates")
    _assert(noisy_augments["rejected_count"] > 0, "TEST_NOISY must reject unsafe augments")
    for expected_reason in (
        "duplicate reasoning",
        "raw input echo",
        "unsupported confidence escalation",
        "unsupported augmentation scope",
    ):
        _assert(
            expected_reason in noisy_reasons,
            f"TEST_NOISY missing rejection/filter path: {expected_reason}",
        )
    _assert(
        any(reason.startswith("profile contamination") for reason in noisy_reasons),
        "TEST_NOISY must reject profile contamination",
    )
    _assert(
        all(
            "text" not in item or not item["text"]
            for item in noisy_augments["rejected_augments_summary"]
        ),
        "rejected augment summaries must not expose rejected raw text",
    )
    _assert(
        noisy_result.recommendation == off_result.recommendation,
        "TEST_NOISY must not replace the deterministic recommendation",
    )

    medical_noisy = run_research_council(
        build_sample_input(),
        llm_advisor_config=LLMAdvisorConfig(mode=LLMAugmentationMode.TEST_NOISY),
    )
    medical_reasons = {
        item["rejection_reason"]
        for item in result_to_json_dict(medical_noisy)["optional_llm_augments"][
            "rejected_augments_summary"
        ]
    }
    _assert(
        "unsafe medical claim" in medical_reasons,
        "medical TEST_NOISY must reject unsafe medical claims",
    )

    safe_summary = evaluate_golden_cases(llm_advisor_config=LLMAugmentationMode.TEST_SAFE)
    _assert(safe_summary.passed, format_regression_summary(safe_summary))
    safe_analytics = build_benchmark_analytics(safe_summary)
    _assert(
        safe_analytics.augmentation_accepted > 0,
        "TEST_SAFE analytics must count accepted augmentation candidates",
    )
    _assert(
        safe_analytics.failed_invariants == 0
        and safe_analytics.consistency_failures == 0,
        "TEST_SAFE analytics must preserve passing invariants and consistency",
    )
    noisy_summary = evaluate_golden_cases(llm_advisor_config=LLMAugmentationMode.TEST_NOISY)
    _assert(noisy_summary.passed, format_regression_summary(noisy_summary))
    noisy_analytics = build_benchmark_analytics(noisy_summary)
    _assert(
        noisy_analytics.augmentation_accepted > 0
        and noisy_analytics.augmentation_filtered > 0
        and noisy_analytics.augmentation_rejected > 0,
        "TEST_NOISY analytics must count accepted, filtered, and rejected paths",
    )


def test_run_demo_json_output_support() -> None:
    artifacts_root = Path(__file__).parent / "artifacts"
    artifacts_root.mkdir(exist_ok=True)
    json_path = artifacts_root / f"smoke-result-{os.getpid()}.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_demo.py")),
            "--json-output",
            str(json_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        completed.returncode == 0,
        f"run_demo --json-output failed: {completed.stderr.strip()}",
    )
    _assert(
        completed.stdout.startswith("# Research Council Report"),
        "run_demo markdown stdout must remain unchanged",
    )
    _assert(json_path.exists(), "run_demo --json-output must create a JSON file")
    exported_json = json_path.read_text(encoding="utf-8")
    exported_payload = json.loads(exported_json)
    _assert(
        exported_payload["profile"]["profile_id"] == "medical_device",
        "run_demo JSON must preserve selected profile id",
    )
    _assert(
        exported_payload["profile"]["selected_by"] == "deterministic_score",
        "run_demo JSON must preserve profile selection reason",
    )
    exported_result = result_from_json(exported_json)
    _assert(
        exported_result.markdown_report.markdown == completed.stdout,
        "run_demo JSON markdown must match stdout markdown",
    )


def test_run_demo_custom_cli_input_support() -> None:
    artifacts_root = Path(__file__).parent / "artifacts"
    artifacts_root.mkdir(exist_ok=True)
    json_path = artifacts_root / f"smoke-custom-result-{os.getpid()}.json"
    markdown_path = artifacts_root / f"smoke-custom-result-{os.getpid()}.md"

    idea = "AI patent analysis assistant for solo founders"
    goal = "Evaluate differentiation and market viability"
    context = "Focus on a bootstrap SaaS concept before any external research is allowed."
    constraints = (
        "No web search, network calls, LLM calls, or fake citations.",
        "Keep prior-art uncertainty explicit.",
    )
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).with_name("run_demo.py")),
        "--idea",
        idea,
        "--goal",
        goal,
        "--context",
        context,
        "--json-output",
        str(json_path),
        "--output",
        str(markdown_path),
    ]
    for constraint in constraints:
        command.extend(["--constraints", constraint])

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        completed.returncode == 0,
        f"run_demo custom CLI input failed: {completed.stderr.strip()}",
    )
    _assert(
        completed.stdout.startswith("# Research Council Report"),
        "custom run_demo markdown stdout must start with the report title",
    )
    _assert(idea in completed.stdout, "custom idea must be reflected in stdout")
    _assert(goal in completed.stdout, "custom goal must be reflected in stdout")
    _assert(context in completed.stdout, "custom context must be reflected in stdout")
    for constraint in constraints:
        _assert(constraint in completed.stdout, "custom constraints must be reflected in stdout")
    _assert(
        "swallowable biodegradable capsule" not in completed.stdout.lower(),
        "custom CLI input must not use the capsule fixture",
    )

    _assert(json_path.exists(), "run_demo custom --json-output must create a JSON file")
    _assert(markdown_path.exists(), "run_demo custom --output must create a Markdown file")
    _assert(
        markdown_path.read_text(encoding="utf-8") == completed.stdout,
        "custom run_demo Markdown output file must match stdout markdown",
    )
    exported_json = json_path.read_text(encoding="utf-8")
    exported_payload = json.loads(exported_json)
    _assert(
        exported_payload["profile"]["profile_id"] == "ai_saas",
        "custom AI assistant input should use the deterministic ai_saas profile",
    )
    _assert(
        exported_payload["profile"]["selected_by"] == "deterministic_score",
        "custom AI assistant profile should be selected by deterministic scoring",
    )
    exported_result = result_from_json(exported_json)
    _assert(
        exported_result.markdown_report.markdown == completed.stdout,
        "custom run_demo JSON markdown must match stdout markdown",
    )


def test_run_demo_explicit_profile_support() -> None:
    artifacts_root = Path(__file__).parent / "artifacts"
    artifacts_root.mkdir(exist_ok=True)
    json_path = artifacts_root / f"smoke-explicit-profile-{os.getpid()}.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_demo.py")),
            "--profile",
            "ai_saas",
            "--json-output",
            str(json_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        completed.returncode == 0,
        f"run_demo explicit --profile failed: {completed.stderr.strip()}",
    )
    _assert(
        "Selected profile: `ai_saas` (explicit)" in completed.stdout,
        "explicit profile must be reflected concisely in Markdown",
    )
    exported_payload = json.loads(json_path.read_text(encoding="utf-8"))
    _assert(
        exported_payload["profile"]["profile_id"] == "ai_saas",
        "explicit --profile must win over deterministic scoring",
    )
    _assert(
        exported_payload["profile"]["selected_by"] == "explicit",
        "explicit --profile must preserve selected_by",
    )


def test_ai_saas_profile_reasoning() -> None:
    result = run_research_council(
        ResearchCouncilInput(
            raw_idea="Automated patent analysis tool for solo software founders",
            goal="Evaluate marketability and differentiation potential.",
            context=(
                "Assess as an AI SaaS workflow concept before web research, external "
                "patent search, or LLM calls are allowed."
            ),
            constraints=(
                "No web search, network calls, LLM calls, or fake citations.",
                "Keep legal interpretation risk explicit.",
            ),
        ),
        profile="ai_saas",
    )

    markdown = result.markdown_report.markdown.lower()
    claim_text = " ".join(claim.text.lower() for claim in result.claims)
    evidence_text = " ".join(entry.summary.lower() for entry in result.evidence_ledger)
    critique_text = " ".join(
        f"{critique.finding} {critique.suggested_action}".lower()
        for critique in result.reviewer_critiques
    )
    experiment_titles = {experiment.title for experiment in result.experiments}
    recommendation_text = (
        f"{result.recommendation.summary} {result.recommendation.rationale}".lower()
    )

    _assert(result.profile["profile_id"] == "ai_saas", "AI SaaS profile must be active")
    for expected in (
        "founder workflow",
        "automation",
        "prior-art",
        "generic ai wrapper",
        "narrow wedge",
        "output reliability",
        "hallucinated",
        "verification boundaries",
        "buyer/workflow integration",
        "retention",
        "willingness to pay",
        "distribution",
    ):
        _assert(expected in claim_text, f"AI SaaS claims must mention {expected}")

    for expected in (
        "current prior-art search workflow",
        "ai wrapper risk",
        "hallucination checks",
        "competing workflow substitute",
        "professional review",
    ):
        _assert(expected in evidence_text, f"AI SaaS evidence gaps must mention {expected}")

    for expected in (
        "ai patent-analysis tool",
        "repeatable output quality",
        "founder workflow",
        "hallucinates citations",
        "ai-wrapper risk",
        "generic-ai substitution",
    ):
        _assert(expected in critique_text, f"AI SaaS critiques must mention {expected}")

    _assert(
        {
            "Workflow interview",
            "Output-quality evaluation",
            "Trust and verification boundary check",
            "Differentiation mapping",
        }
        <= experiment_titles,
        "AI SaaS experiments must include workflow, quality, trust, and differentiation checks",
    )
    for expected in (
        "user adoption",
        "reliability",
        "workflow integration",
        "trust",
        "buyer urgency",
        "ai-wrapper risk",
        "differentiation",
    ):
        _assert(
            expected in recommendation_text,
            f"AI SaaS recommendation must weight {expected}",
        )
    _assert(
        "generic ai" in markdown and "legal advice" in markdown,
        "AI SaaS Markdown must expose substitutes and legal-output boundaries",
    )


def test_ai_saas_policy_regression_signals() -> None:
    input_data = ResearchCouncilInput(
        raw_idea=(
            "AI SaaS workflow assistant that wraps an LLM to generate patent analysis "
            "reports for solo founders"
        ),
        goal="Evaluate buyer urgency, narrow wedge, differentiation, and GTM risk.",
        context="Focus on repeat usage, switching cost, and workflow integration.",
    )
    selection = resolve_domain_profile(input_data)
    _assert(
        selection.selected_profile.id == "ai_saas",
        "AI SaaS workflow input must select ai_saas deterministically",
    )

    result = run_research_council(input_data)
    combined_text = " ".join(
        (
            result.recommendation.summary,
            result.recommendation.rationale,
            " ".join(result.warnings),
            " ".join(critique.finding for critique in result.reviewer_critiques),
            " ".join(experiment.method for experiment in result.experiments),
        )
    ).lower()
    _assert(
        "ai-wrapper risk" in combined_text,
        "AI SaaS output must warn about AI-wrapper differentiation risk",
    )
    _assert(
        "buyer/workflow" in combined_text or "buyer workflow" in combined_text,
        "AI SaaS output must preserve buyer/workflow reasoning",
    )
    _assert(
        "narrow wedge" in combined_text or "narrow-wedge" in combined_text,
        "AI SaaS output must preserve narrow-wedge reasoning",
    )
    _assert(
        "switching cost" in combined_text,
        "AI SaaS output must preserve switching-cost reasoning",
    )

    payload = result_to_json_dict(result)
    _assert(
        payload["quality_signals"]["risk_specificity"]["status"] in {"strong", "partial"},
        "AI SaaS quality signals must detect profile-specific risk language",
    )


def test_medical_device_policy_regression_preserves_conservative_behavior() -> None:
    result = run_research_council(build_sample_input())
    combined_text = " ".join(
        (
            " ".join(result.warnings),
            result.recommendation.summary,
            result.recommendation.rationale,
            result.recommendation.next_step,
            " ".join(critique.finding for critique in result.reviewer_critiques),
        )
    ).lower()

    _assert(result.profile["profile_id"] == "medical_device", "sample must remain medical_device")
    _assert(
        result.recommendation.decision == "pause_broad_use_resolve_safety_blocker",
        "medical_device must keep conservative safety-first decision",
    )
    for expected in ("patient safety", "regulatory", "clinical", "validation"):
        _assert(
            expected in combined_text,
            f"medical_device output must preserve {expected} language",
        )
    _assert(
        "non-clinical" in combined_text,
        "medical_device next step must remain non-clinical",
    )
    _assert(
        "profile confidence policy" in combined_text and "conservative" in combined_text,
        "medical_device must preserve conservative confidence behavior",
    )
    _assert(
        any(
            critique.reviewer_role == "safety_regulatory" and critique.severity == "high"
            for critique in result.reviewer_critiques
        ),
        "medical_device safety reviewer must remain high severity",
    )
    _assert(
        "ai-wrapper risk" not in combined_text,
        "AI SaaS policy language must not leak into medical_device regression output",
    )


def test_ai_saas_evidence_gap_engine_links_experiments() -> None:
    result = run_research_council(
        ResearchCouncilInput(
            raw_idea="AI SaaS patent analysis assistant for solo founders",
            goal="Evaluate buyer workflow, willingness to pay, retention, and differentiation.",
            context="Focus on repeated workflow, generic LLM wrapper risk, and purchase intent.",
        )
    )
    payload = result_to_json_dict(result)
    missing_entries = [
        entry for entry in payload["evidence_ledger"] if entry["evidence_type"] == "missing"
    ]
    evidence_text = " ".join(
        f"{entry['required_evidence']} {entry['missing_evidence']} {entry['validation_experiment']}"
        for entry in missing_entries
    ).lower()
    experiment_titles = {experiment.title for experiment in result.experiments}

    for expected in (
        "buyer",
        "workflow",
        "willingness to pay",
        "differentiation",
        "generic llm wrapper",
        "retention trigger",
        "reliability",
    ):
        _assert(expected in evidence_text, f"AI SaaS evidence gaps must include {expected}")

    _assert(
        any(
            "Workflow interview" in entry["validation_experiment"]
            and "willingness-to-pay" in entry["validation_experiment"]
            for entry in missing_entries
        ),
        "AI SaaS willingness-to-pay gap must map to a workflow/pricing validation experiment",
    )
    for entry in missing_entries:
        experiment_title = entry["validation_experiment"].split(":", 1)[0]
        _assert(
            experiment_title in experiment_titles,
            f"missing evidence must map to an existing experiment title: {experiment_title}",
        )


def test_medical_device_evidence_gap_engine_preserves_conservative_confidence() -> None:
    result = run_research_council(build_sample_input())
    payload = result_to_json_dict(result)
    missing_entries = [
        entry for entry in payload["evidence_ledger"] if entry["evidence_type"] == "missing"
    ]
    evidence_text = " ".join(
        f"{entry['required_evidence']} {entry['missing_evidence']} {entry['validation_experiment']}"
        for entry in missing_entries
    ).lower()

    for expected in (
        "patient safety risk",
        "regulatory pathway",
        "clinical validation",
        "intended use",
        "target population",
    ):
        _assert(
            expected in evidence_text,
            f"medical_device evidence gaps must include {expected}",
        )

    safety_entries = [
        entry
        for entry in missing_entries
        if "gap_category=safety_regulatory" in entry["notes"]
    ]
    _assert(safety_entries, "medical_device must keep safety/regulatory evidence gaps")
    _assert(
        all(entry["confidence_impact"] == "confidence_blocker" for entry in safety_entries),
        "medical_device safety/regulatory gaps must remain confidence blockers",
    )
    _assert(
        any("Non-clinical capsule safety boundary table" in entry["validation_experiment"] for entry in safety_entries),
        "medical_device safety gaps must map to the non-clinical safety validation experiment",
    )


def test_ai_saas_reasoning_trace_explainability() -> None:
    result = run_research_council(
        ResearchCouncilInput(
            raw_idea="AI SaaS patent analysis assistant for solo founders",
            goal="Evaluate buyer workflow, willingness to pay, retention, and differentiation.",
            context="Focus on repeated workflow, generic LLM wrapper risk, and purchase intent.",
        )
    )
    payload = result_to_json_dict(result)
    entries = payload["evidence_ledger"]
    trace_text = _combined_reasoning_trace(entries)

    _assert(result.profile["profile_id"] == "ai_saas", "AI SaaS profile must be active")
    for expected in (
        "no buyer",
        "workflow",
        "differentiation beyond generic ai wrapper unclear",
        "retention trigger unsupported",
    ):
        _assert(
            expected in trace_text,
            f"AI SaaS reasoning trace must include {expected}",
        )
    _assert(
        "reasoning_trace" in entries[0],
        "JSON evidence entries must expose additive reasoning_trace",
    )
    _assert(
        "trace_category" in entries[0] and "trace_severity" in entries[0],
        "JSON evidence entries must expose additive trace metadata",
    )
    _assert(
        "quality_signals" in payload,
        "explainability metadata must preserve existing quality_signals",
    )


def test_medical_device_reasoning_trace_explainability() -> None:
    result = run_research_council(build_sample_input())
    payload = result_to_json_dict(result)
    missing_entries = [
        entry for entry in payload["evidence_ledger"] if entry["evidence_type"] == "missing"
    ]
    trace_text = _combined_reasoning_trace(missing_entries)

    _assert(result.profile["profile_id"] == "medical_device", "sample must remain medical_device")
    for expected in (
        "patient safety risk unresolved",
        "regulatory pathway unclear",
        "clinical validation evidence missing",
        "intended use not bounded",
    ):
        _assert(
            expected in trace_text,
            f"medical_device reasoning trace must include {expected}",
        )

    safety_entries = [
        entry
        for entry in missing_entries
        if entry["trace_category"] == "safety_regulatory"
    ]
    _assert(safety_entries, "medical_device trace must preserve safety/regulatory category")
    _assert(
        all(entry["trace_severity"] == "high" for entry in safety_entries),
        "medical_device safety/regulatory trace must preserve high severity",
    )


def test_confidence_trace_linkage_and_json_additive_fields() -> None:
    result = run_research_council(build_sample_input())
    payload = result_to_json_dict(result)
    entries = payload["evidence_ledger"]
    blocker_entries = [
        entry for entry in entries if entry["confidence_impact"] == "confidence_blocker"
    ]
    supporting_entries = [
        entry for entry in entries if entry["confidence_impact"] == "confidence_supporting"
    ]
    limiter_entries = [
        entry for entry in entries if entry["confidence_impact"] == "confidence_limiter"
    ]

    _assert(blocker_entries, "fixture must include confidence_blocker entries")
    _assert(supporting_entries, "fixture must include confidence_supporting entries")

    for entry in entries:
        traces = entry.get("reasoning_trace")
        _assert(isinstance(traces, list), "JSON reasoning_trace must be a list")
        _assert(bool(traces), "JSON reasoning_trace must be non-empty")
        _assert(entry.get("trace_category"), "JSON trace_category must be non-empty")
        _assert(
            entry.get("trace_severity") in {"low", "medium", "high"},
            "JSON trace_severity must use deterministic severity labels",
        )

    for entry in blocker_entries:
        trace_text = " ".join(entry["reasoning_trace"]).lower()
        _assert(
            "confidence blocker" in trace_text,
            "confidence_blocker entries must contain blocker rationale",
        )
    for entry in supporting_entries:
        trace_text = " ".join(entry["reasoning_trace"]).lower()
        _assert(
            "supporting" in trace_text,
            "confidence_supporting entries must contain supporting rationale",
        )
    for entry in limiter_entries:
        trace_text = " ".join(entry["reasoning_trace"]).lower()
        _assert(
            "confidence limiter" in trace_text or "limits confidence" in trace_text,
            "confidence_limiter entries must contain limiter rationale",
        )


def test_golden_case_evaluation_harness() -> None:
    summary = evaluate_golden_cases()
    case_ids = {evaluation.case_id for evaluation in summary.evaluations}
    analytics = build_benchmark_analytics(summary)
    _assert(summary.case_count >= 22, "golden case harness must load the committed cases")
    _assert(summary.invariant_count >= 20, "golden case harness must evaluate invariants")
    _assert(summary.profile_coverage_count >= 7, "golden case harness must cover selected profiles")
    _assert(summary.hard_case_count >= 7, "golden case harness must include hard cases")
    _assert(
        summary.realistic_case_count >= 7,
        "golden case harness must include realistic benchmark cases",
    )
    _assert(
        summary.overlap_case_count >= 6,
        "golden case harness must include realistic overlap stress cases",
    )
    _assert(
        summary.augmentation_stress_count >= 2,
        "golden case harness must include augmentation stress cases",
    )
    for expected_case_id in (
        "ai_saas/hard_false_marketplace_enterprise_noise",
        "ai_saas/real_workflow_assistant_pitch",
        "ai_saas/weak_ai_wrapper",
        "ai_saas/workflow_ai_assistant",
        "creator_tools/creator_content_studio",
        "creator_tools/hard_marketplace_noise_creator_workflow",
        "creator_tools/real_creator_growth_pitch",
        "developer_tool/cli_debugging_tool",
        "developer_tool/hard_observability_not_generic_saas",
        "developer_tool/real_devtool_readme",
        "enterprise_b2b/enterprise_workflow_platform",
        "enterprise_b2b/hard_buzzword_procurement_gap",
        "enterprise_b2b/real_enterprise_ops_pitch",
        "generic/hard_vague_profile_ambiguity",
        "generic/real_vague_business_pitch",
        "generic/vague_consumer_idea",
        "marketplace/hard_creator_community_marketplace_overlap",
        "marketplace/local_service_marketplace",
        "marketplace/real_local_services_pitch",
        "medical_device/diagnostic_tool",
        "medical_device/hard_optimistic_validation_claim",
        "medical_device/real_remote_monitoring_pitch",
    ):
        _assert(
            expected_case_id in case_ids,
            f"golden case harness missing {expected_case_id}",
        )
    _assert(summary.passed, format_regression_summary(summary))
    _assert(analytics.total_cases == summary.case_count, "analytics case count must match summary")
    _assert(
        analytics.total_invariants == summary.invariant_count,
        "analytics invariant count must match summary",
    )
    _assert(analytics.failed_invariants == 0, "passing suite must have zero failed invariants")
    _assert(
        analytics.consistency_checks == summary.consistency_check_count,
        "analytics consistency check count must match summary",
    )
    _assert(
        analytics.consistency_failures == 0,
        "passing suite must have zero consistency failures",
    )
    _assert(
        analytics.hard_cases == summary.hard_case_count,
        "analytics hard case count must match fixture tags",
    )
    _assert(
        analytics.realistic_cases == summary.realistic_case_count,
        "analytics realistic case count must match fixture tags",
    )
    _assert(
        analytics.overlap_cases == summary.overlap_case_count,
        "analytics overlap case count must match fixture tags",
    )
    _assert(
        analytics.augmentation_accepted == 0
        and analytics.augmentation_filtered == 0
        and analytics.augmentation_rejected == 0,
        "OFF mode analytics must keep augmentation counts at zero",
    )
    for profile_id in (
        "ai_saas",
        "creator_tools",
        "developer_tool",
        "enterprise_b2b",
        "general",
        "marketplace",
        "medical_device",
    ):
        _assert(
            profile_id in analytics.profiles_covered,
            f"analytics profile coverage missing {profile_id}",
        )
    formatted_analytics = format_benchmark_analytics(analytics)
    _assert(
        "Benchmark analytics:" in formatted_analytics,
        "analytics formatter must identify benchmark analytics output",
    )
    _assert(
        "failed_invariants=0" in formatted_analytics,
        "analytics formatter must expose failed invariant count",
    )
    _assert(
        "realistic_cases=" in formatted_analytics
        and "overlap_cases=" in formatted_analytics,
        "analytics formatter must expose realistic benchmark counts",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_golden_cases.py")),
            "--show-analytics",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        completed.returncode == 0,
        f"run_golden_cases --show-analytics failed: {completed.stderr.strip()}",
    )
    _assert(
        "Golden cases passed:" in completed.stdout
        and "Benchmark analytics:" in completed.stdout,
        "run_golden_cases --show-analytics must print summary and analytics",
    )


def test_benchmark_snapshot_export_contract() -> None:
    summary = evaluate_golden_cases()
    analytics = build_benchmark_analytics(summary)
    artifacts_root = Path(__file__).parent / "artifacts"
    artifacts_root.mkdir(exist_ok=True)
    snapshot_path = artifacts_root / f"benchmark-snapshot-{os.getpid()}.json"

    snapshot = export_benchmark_snapshot(
        summary,
        snapshot_path,
        augmentation_mode=LLMAugmentationMode.OFF.value,
    )
    _assert(snapshot_path.exists(), "benchmark snapshot export must create a JSON file")
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    loaded = load_benchmark_snapshot(snapshot_path)
    _assert(loaded == snapshot, "benchmark snapshot must load back to the exported object")
    _assert(
        benchmark_snapshot_to_json_dict(loaded) == payload,
        "benchmark snapshot JSON structure must round-trip deterministically",
    )
    _assert(
        benchmark_snapshot_from_json_dict(payload) == loaded,
        "benchmark snapshot mapping loader must round-trip",
    )

    _assert(payload["total_cases"] == summary.case_count, "snapshot case count mismatch")
    _assert(
        payload["total_invariants"] == summary.invariant_count,
        "snapshot invariant count mismatch",
    )
    _assert(
        payload["failed_invariants"] == 0,
        "passing snapshot must record zero failed invariants",
    )
    _assert(
        payload["consistency_failures"] == 0,
        "passing snapshot must record zero consistency failures",
    )
    _assert(
        payload["hard_cases"] == summary.hard_case_count,
        "snapshot hard case count must match summary",
    )
    _assert(
        payload["realistic_cases"] == summary.realistic_case_count,
        "snapshot realistic case count must match summary",
    )
    _assert(
        payload["overlap_cases"] == summary.overlap_case_count,
        "snapshot overlap case count must match summary",
    )
    _assert(
        payload["version_info"]["fixture_count"] == summary.case_count,
        "snapshot fixture count must match evaluated cases",
    )
    _assert(
        payload["run_metadata"]["augmentation_mode"] == "off",
        "snapshot must record augmentation mode",
    )
    _assert(
        payload["augmentation_counts"] == {"accepted": 0, "filtered": 0, "rejected": 0},
        "OFF snapshot must record zero augmentation counts",
    )
    _assert_scenario_template_coverage(payload["scenario_template_coverage"])
    _assert_benchmark_pack_metadata(payload["benchmark_pack_metadata"])
    _assert(
        payload["cases_by_profile"] == dict(analytics.cases_by_profile),
        "snapshot cases_by_profile must match analytics",
    )
    _assert(
        payload["confidence_impact_distribution"]
        == dict(analytics.confidence_impact_distribution),
        "snapshot confidence impact distribution must match analytics",
    )
    _assert(
        payload["evidence_gap_distribution"] == dict(analytics.evidence_gaps_by_profile),
        "snapshot evidence gap distribution must match analytics",
    )
    snapshot_text = snapshot_path.read_text(encoding="utf-8")
    _assert(
        "C:" not in snapshot_text and "jarvis-core" not in snapshot_text,
        "benchmark snapshot must not leak local filesystem paths",
    )
    _assert(
        snapshot.version_info.benchmark_hash,
        "benchmark snapshot must include a deterministic benchmark hash",
    )
    old_snapshot_payload = dict(payload)
    old_snapshot_payload.pop("scenario_template_coverage", None)
    old_snapshot_payload.pop("benchmark_pack_metadata", None)
    old_snapshot = benchmark_snapshot_from_json_dict(old_snapshot_payload)
    old_snapshot_coverage = benchmark_snapshot_to_json_dict(old_snapshot)[
        "scenario_template_coverage"
    ]
    old_snapshot_pack_metadata = benchmark_snapshot_to_json_dict(old_snapshot)[
        "benchmark_pack_metadata"
    ]
    _assert(
        old_snapshot_coverage["coverage_type"] == ""
        and old_snapshot_coverage["total_scenarios"] == 0,
        "old snapshots without scenario template coverage must load tolerantly",
    )
    _assert(
        old_snapshot_pack_metadata["pack_id"] == ""
        and old_snapshot_pack_metadata["golden_case_count"] == 0,
        "old snapshots without benchmark pack metadata must load tolerantly",
    )
    _assert(
        validate_benchmark_pack_metadata(old_snapshot_pack_metadata),
        "old snapshots without benchmark pack metadata must fail frozen contract validation",
    )

    same_diff = compare_benchmark_snapshots(loaded, loaded)
    _assert(
        same_diff.total_cases_delta == 0
        and same_diff.total_invariants_delta == 0
        and same_diff.failed_invariants_delta == 0
        and same_diff.consistency_failures_delta == 0
        and same_diff.augmentation_rejected_delta == 0
        and not same_diff.profiles_added
        and not same_diff.profiles_removed
        and not same_diff.benchmark_hash_changed,
        "identical benchmark snapshots must compare with zero deltas",
    )

    changed_payload = dict(payload)
    changed_payload["total_invariants"] = int(payload["total_invariants"]) + 2
    changed_payload["consistency_failures"] = int(payload["consistency_failures"]) + 1
    changed_payload["augmentation_counts"] = dict(payload["augmentation_counts"])
    changed_payload["augmentation_counts"]["rejected"] += 3
    changed_payload["version_info"] = dict(payload["version_info"])
    changed_payload["version_info"]["benchmark_hash"] = "changed"
    changed_snapshot = benchmark_snapshot_from_json_dict(changed_payload)
    changed_diff = compare_benchmark_snapshots(loaded, changed_snapshot)
    _assert(
        changed_diff.total_invariants_delta == 2
        and changed_diff.consistency_failures_delta == 1
        and changed_diff.augmentation_rejected_delta == 3
        and changed_diff.benchmark_hash_changed,
        "benchmark snapshot comparison must report compact deltas",
    )

    cli_snapshot_path = artifacts_root / f"benchmark-cli-snapshot-{os.getpid()}.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_golden_cases.py")),
            "--export-snapshot",
            str(cli_snapshot_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        completed.returncode == 0,
        f"run_golden_cases --export-snapshot failed: {completed.stderr.strip()}",
    )
    _assert(
        cli_snapshot_path.exists(),
        "run_golden_cases --export-snapshot must create a snapshot file",
    )
    _assert(
        "Golden cases passed:" in completed.stdout
        and "Benchmark snapshot exported:" in completed.stdout,
        "run_golden_cases --export-snapshot must preserve summary output and report export",
    )


def test_benchmark_history_contract() -> None:
    summary = evaluate_golden_cases()
    artifacts_root = Path(__file__).parent / "artifacts"
    artifacts_root.mkdir(exist_ok=True)
    snapshot_path = artifacts_root / f"benchmark-history-snapshot-{os.getpid()}.json"
    history_path = artifacts_root / f"benchmark-history-{os.getpid()}.json"

    snapshot = export_benchmark_snapshot(summary, snapshot_path)
    history = append_benchmark_history(snapshot, history_path)
    _assert(history_path.exists(), "benchmark history append must create a JSON file")
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    loaded_history = load_benchmark_history(history_path)
    _assert(loaded_history == history, "benchmark history must load back unchanged")
    _assert(
        payload["history_schema_version"] == 1,
        "benchmark history must expose a schema version",
    )
    _assert(
        json.loads(history_to_json(loaded_history)) == payload,
        "benchmark history JSON must round-trip deterministically",
    )
    _assert(
        benchmark_history_entry_from_json_dict(
            benchmark_history_entry_to_json_dict(loaded_history[0])
        )
        == loaded_history[0],
        "benchmark history entry mapping must round-trip",
    )
    _assert_scenario_template_coverage(payload["entries"][0]["scenario_template_coverage"])
    _assert_benchmark_pack_metadata(payload["entries"][0]["benchmark_pack_metadata"])
    _assert(
        loaded_history[0].scenario_template_coverage
        == snapshot.scenario_template_coverage,
        "benchmark history must preserve scenario template coverage metadata",
    )
    _assert(
        loaded_history[0].benchmark_pack_metadata == snapshot.benchmark_pack_metadata,
        "benchmark history must preserve benchmark pack metadata",
    )
    old_history_entry_payload = benchmark_history_entry_to_json_dict(loaded_history[0])
    old_history_entry_payload.pop("benchmark_pack_metadata", None)
    old_history_entry = benchmark_history_entry_from_json_dict(old_history_entry_payload)
    _assert(
        old_history_entry.benchmark_pack_metadata["pack_id"] == ""
        and old_history_entry.benchmark_pack_metadata["golden_case_count"] == 0,
        "old history entries without benchmark pack metadata must load tolerantly",
    )
    _assert(
        validate_benchmark_pack_metadata(old_history_entry.benchmark_pack_metadata),
        "old history entries without benchmark pack metadata must fail frozen contract validation",
    )

    first_trend = compare_latest_to_previous(loaded_history)
    _assert(first_trend.entries == 1, "single-entry history must report one entry")
    _assert(
        not first_trend.changed and first_trend.regression_count == 0,
        "single-entry history must not report change or regressions",
    )

    repeated_history = append_benchmark_history(snapshot, history_path)
    repeated_trend = compare_latest_to_previous(repeated_history)
    _assert(
        repeated_trend.entries == 2
        and not repeated_trend.changed
        and repeated_trend.regression_count == 0,
        "repeated identical snapshots must compare cleanly",
    )
    _assert(
        not repeated_trend.scenario_template_coverage_changed
        and not repeated_trend.scenario_template_coverage_delta,
        "repeated identical snapshots must keep scenario template telemetry stable",
    )
    _assert(
        not repeated_trend.benchmark_pack_metadata_changed
        and not repeated_trend.benchmark_pack_metadata_delta,
        "repeated identical snapshots must keep benchmark pack metadata stable",
    )

    changed_payload = json.loads(json.dumps(benchmark_snapshot_to_json_dict(snapshot)))
    changed_payload["failed_invariants"] += 1
    changed_payload["consistency_failures"] += 1
    changed_payload["hard_cases"] -= 1
    changed_payload["realistic_cases"] -= 1
    changed_payload["augmentation_counts"]["rejected"] += 2
    changed_payload["version_info"]["benchmark_hash"] = "changed"
    changed_payload["profiles_covered"] = changed_payload["profiles_covered"][:-1]
    changed_payload["case_ids"] = changed_payload["case_ids"][:-1]
    first_case_id = sorted(changed_payload["selected_profiles_by_case"])[0]
    current_profile = changed_payload["selected_profiles_by_case"][first_case_id]
    changed_payload["selected_profiles_by_case"][first_case_id] = (
        "general" if current_profile != "general" else "ai_saas"
    )
    changed_payload["confidence_impact_distribution"]["confidence_blocker"] += 1
    changed_payload["evidence_gap_distribution"]["ai_saas"] += 2
    changed_snapshot = benchmark_snapshot_from_json_dict(changed_payload)
    changed_history = append_benchmark_history(changed_snapshot, history_path)
    changed_trend = compare_latest_to_previous(changed_history)
    _assert(changed_trend.changed, "changed benchmark hash must mark trend as changed")
    _assert(
        changed_trend.failed_invariants_delta == 1
        and changed_trend.consistency_failures_delta == 1
        and changed_trend.hard_cases_delta == -1
        and changed_trend.realistic_cases_delta == -1
        and changed_trend.augmentation_rejected_delta == 2,
        "benchmark trend must report core regression deltas",
    )
    _assert(
        changed_trend.profiles_removed
        and changed_trend.case_ids_removed
        and changed_trend.selected_profile_changes,
        "benchmark trend must report coverage and selected-profile changes",
    )
    _assert(
        changed_trend.confidence_impact_delta["confidence_blocker"] == 1
        and changed_trend.evidence_gap_delta["ai_saas"] == 2,
        "benchmark trend must report distribution deltas",
    )
    _assert(
        not changed_trend.scenario_template_coverage_changed
        and not changed_trend.scenario_template_coverage_delta,
        "unchanged scenario template metadata must not create trend noise",
    )
    _assert(
        not changed_trend.benchmark_pack_metadata_changed
        and not changed_trend.benchmark_pack_metadata_delta,
        "unchanged benchmark pack metadata must not create trend noise",
    )
    for expected_signal in (
        "failed_invariants increased",
        "consistency_failures increased",
        "profiles_covered decreased",
        "hard_cases decreased",
        "realistic_cases decreased",
        "benchmark_hash changed",
    ):
        _assert(
            expected_signal in changed_trend.regressions,
            f"benchmark trend missing regression signal: {expected_signal}",
        )

    trend_text = format_benchmark_trend_summary(changed_trend)
    history_text = history_path.read_text(encoding="utf-8")
    _assert(
        "Benchmark history updated:" in trend_text and "regressions=" in trend_text,
        "benchmark trend formatter must be concise and labeled",
    )
    _assert(
        "C:" not in trend_text
        and "jarvis-core" not in trend_text
        and "C:" not in history_text
        and "jarvis-core" not in history_text,
        "benchmark history must not leak local filesystem paths",
    )

    cli_history_path = artifacts_root / f"benchmark-history-cli-{os.getpid()}.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_benchmark_history.py")),
            "--snapshot",
            str(snapshot_path),
            "--history",
            str(cli_history_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        completed.returncode == 0,
        f"run_benchmark_history.py failed: {completed.stderr.strip()}",
    )
    _assert(cli_history_path.exists(), "benchmark history CLI must create history JSON")
    _assert(
        "Benchmark history updated:" in completed.stdout,
        "benchmark history CLI must print a concise trend summary",
    )
    _assert(
        "C:" not in completed.stdout and "jarvis-core" not in completed.stdout,
        "benchmark history CLI output must not leak local filesystem paths",
    )


def test_benchmark_diff_viewer_contract() -> None:
    summary = evaluate_golden_cases()
    artifacts_root = Path(__file__).parent / "artifacts"
    artifacts_root.mkdir(exist_ok=True)
    before_path = artifacts_root / f"benchmark-diff-before-{os.getpid()}.json"
    after_path = artifacts_root / f"benchmark-diff-after-{os.getpid()}.json"
    history_path = artifacts_root / f"benchmark-diff-history-{os.getpid()}.json"

    before_snapshot = export_benchmark_snapshot(summary, before_path)
    same_view = build_benchmark_diff_view(before_snapshot, before_snapshot)
    same_diff_text = format_benchmark_diff_view(same_view)
    same_governance_summary = format_benchmark_governance_summary(same_view)
    _assert(
        not categorize_benchmark_drift(same_view),
        "identical benchmark diffs must not report drift categories",
    )
    _assert(
        same_governance_summary
        == (
            "Benchmark governance: "
            "status=stable categories=none regressions=0 severity=stable"
        ),
        "stable benchmark diffs must report a compact stable governance summary",
    )
    _assert(
        classify_benchmark_governance_severity(same_view) == "stable",
        "identical benchmark diffs must classify as stable severity",
    )
    _assert(
        "- drift_categories: none" in same_diff_text,
        "benchmark diff formatter must report empty drift categories",
    )

    hash_only_payload = json.loads(json.dumps(benchmark_snapshot_to_json_dict(before_snapshot)))
    hash_only_payload["version_info"]["benchmark_hash"] = "changed"
    hash_only_view = build_benchmark_diff_view(
        before_snapshot,
        benchmark_snapshot_from_json_dict(hash_only_payload),
    )
    _assert(
        hash_only_view.benchmark_hash_changed
        and "regression" not in categorize_benchmark_drift(hash_only_view),
        "benchmark hash changes alone must not be categorized as regression",
    )
    _assert(
        format_benchmark_governance_summary(hash_only_view)
        == (
            "Benchmark governance: "
            "status=stable categories=none regressions=0 severity=info"
        ),
        "benchmark hash changes alone must not count as governance regressions",
    )
    _assert(
        classify_benchmark_governance_severity(hash_only_view) == "info",
        "benchmark hash changes alone must classify as info severity",
    )

    changed_payload = json.loads(json.dumps(benchmark_snapshot_to_json_dict(before_snapshot)))
    changed_payload["failed_invariants"] += 1
    changed_payload["consistency_failures"] += 1
    changed_payload["hard_cases"] -= 1
    changed_payload["realistic_cases"] -= 1
    changed_payload["augmentation_counts"]["accepted"] += 1
    changed_payload["augmentation_counts"]["filtered"] += 2
    changed_payload["augmentation_counts"]["rejected"] += 3
    changed_payload["version_info"]["benchmark_hash"] = "changed"
    changed_payload["profiles_covered"] = changed_payload["profiles_covered"][:-1]
    changed_payload["case_ids"] = changed_payload["case_ids"][:-1]
    first_case_id = sorted(changed_payload["selected_profiles_by_case"])[0]
    current_profile = changed_payload["selected_profiles_by_case"][first_case_id]
    changed_payload["selected_profiles_by_case"][first_case_id] = (
        "general" if current_profile != "general" else "ai_saas"
    )
    changed_payload["cases_by_profile"]["ai_saas"] += 1
    changed_payload["evidence_gap_distribution"]["ai_saas"] += 2
    changed_payload["confidence_impact_distribution"]["confidence_blocker"] += 1
    after_snapshot = benchmark_snapshot_from_json_dict(changed_payload)
    after_path.write_text(snapshot_to_json(after_snapshot), encoding="utf-8")

    diff_view = build_benchmark_diff_view(before_snapshot, after_snapshot)
    diff_text = format_benchmark_diff_view(diff_view)
    governance_summary = format_benchmark_governance_summary(diff_view)
    drift_categories = categorize_benchmark_drift(diff_view)
    _assert(diff_view.changed, "benchmark diff view must report hash changes")
    _assert(
        drift_categories == ("regression", "composition_change"),
        "benchmark drift categories must classify regressions and composition changes",
    )
    _assert(
        governance_summary
        == (
            "Benchmark governance: "
            "status=warning "
            "categories=regression,composition_change "
            "regressions=5 severity=critical"
        ),
        "warning benchmark diffs must report compact regression governance",
    )
    _assert(
        classify_benchmark_governance_severity(diff_view) == "critical",
        "regression benchmark drift must classify as critical severity",
    )
    _assert(
        diff_view.regression_count >= 5,
        "benchmark diff view must surface regression signals",
    )
    _assert(
        diff_view.failed_invariants_delta == 1
        and diff_view.consistency_failures_delta == 1
        and diff_view.hard_cases_delta == -1
        and diff_view.realistic_cases_delta == -1
        and diff_view.augmentation_accepted_delta == 1
        and diff_view.augmentation_filtered_delta == 2
        and diff_view.augmentation_rejected_delta == 3,
        "benchmark diff view must report core deltas",
    )
    _assert(
        diff_view.profiles_removed
        and diff_view.case_ids_removed
        and diff_view.selected_profile_changes,
        "benchmark diff view must report coverage and selected-profile changes",
    )
    _assert(
        any(
            profile.profile_id == "ai_saas"
            and profile.case_count_delta == 1
            and profile.evidence_gap_delta == 2
            for profile in diff_view.profile_diffs
        ),
        "benchmark diff view must report per-profile case and evidence-gap deltas",
    )
    _assert(
        diff_view.confidence_impact_delta["confidence_blocker"] == 1,
        "benchmark diff view must report confidence impact deltas",
    )
    for expected_fragment in (
        "Benchmark diff:",
        "- cases:",
        "- augmentation:",
        "- scenario_templates:",
        "- benchmark_pack:",
        "- drift_categories:",
        "- profiles:",
        "- benchmark_hash_changed:",
        "- regression_signals:",
    ):
        _assert(
            expected_fragment in diff_text,
            f"benchmark diff formatter missing {expected_fragment}",
        )
    _assert(
        "C:" not in diff_text and "jarvis-core" not in diff_text,
        "benchmark diff formatter must not leak local paths",
    )
    _assert(
        "scenario_templates: changed=false, scenarios=+0, categories=+0, profiles=+0, subset=+0"
        in diff_text,
        "benchmark diff formatter must include concise scenario template telemetry",
    )
    _assert(
        "benchmark_pack: changed=false, golden=+0, mutation=+0, templates=+0, profiles=+0"
        in diff_text,
        "benchmark diff formatter must include concise benchmark pack metadata",
    )
    _assert(
        "drift_categories: regression,composition_change" in diff_text,
        "benchmark diff formatter must include concise drift categories",
    )

    scenario_changed_payload = json.loads(
        json.dumps(benchmark_snapshot_to_json_dict(before_snapshot))
    )
    scenario_changed_payload["scenario_template_coverage"]["total_scenarios"] += 1
    scenario_changed_view = build_benchmark_diff_view(
        before_snapshot,
        benchmark_snapshot_from_json_dict(scenario_changed_payload),
    )
    _assert(
        categorize_benchmark_drift(scenario_changed_view) == ("composition_change",),
        "scenario template count changes must be categorized as composition changes",
    )
    _assert(
        format_benchmark_governance_summary(scenario_changed_view)
        == (
            "Benchmark governance: "
            "status=warning categories=composition_change regressions=0 severity=warning"
        ),
        "composition-only benchmark drift must report warning severity",
    )
    _assert(
        classify_benchmark_governance_severity(scenario_changed_view) == "warning",
        "composition-only benchmark drift must classify as warning severity",
    )

    pack_changed_payload = json.loads(
        json.dumps(benchmark_snapshot_to_json_dict(before_snapshot))
    )
    pack_changed_payload["benchmark_pack_metadata"]["profile_count"] += 1
    pack_changed_view = build_benchmark_diff_view(
        before_snapshot,
        benchmark_snapshot_from_json_dict(pack_changed_payload),
    )
    _assert(
        categorize_benchmark_drift(pack_changed_view)
        == ("composition_change", "contract_mismatch"),
        "invalid benchmark pack changes must report composition and contract mismatch",
    )
    _assert(
        classify_benchmark_governance_severity(pack_changed_view) == "critical",
        "contract mismatch benchmark drift must classify as critical severity",
    )

    warning_payload = json.loads(json.dumps(changed_payload))
    warning_payload["benchmark_pack_metadata"]["profile_count"] += 1
    warning_view = build_benchmark_diff_view(
        before_snapshot,
        benchmark_snapshot_from_json_dict(warning_payload),
    )
    _assert(
        format_benchmark_governance_summary(warning_view)
        == (
            "Benchmark governance: "
            "status=warning "
            "categories=regression,composition_change,contract_mismatch "
            "regressions=5 severity=critical"
        ),
        "governance summary must include regression, composition, and contract categories",
    )

    old_pack_payload = json.loads(json.dumps(benchmark_snapshot_to_json_dict(before_snapshot)))
    old_pack_payload.pop("benchmark_pack_metadata", None)
    old_pack_view = build_benchmark_diff_view(
        before_snapshot,
        benchmark_snapshot_from_json_dict(old_pack_payload),
    )
    _assert(
        "contract_mismatch" in categorize_benchmark_drift(old_pack_view),
        "missing benchmark pack metadata must be categorized as contract mismatch",
    )

    history = append_benchmark_history(before_snapshot, history_path)
    history = append_benchmark_history(after_snapshot, history_path)
    history_view = build_benchmark_diff_view_from_history(history)
    _assert(
        history_view == diff_view,
        "history diff view must compare the latest entry to the previous entry",
    )

    before_after_cli = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_benchmark_diff.py")),
            "--before",
            str(before_path),
            "--after",
            str(after_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        before_after_cli.returncode == 0,
        f"run_benchmark_diff --before/--after failed: {before_after_cli.stderr.strip()}",
    )
    _assert(
        "Benchmark diff:" in before_after_cli.stdout
        and "regressions=" in before_after_cli.stdout,
        "run_benchmark_diff --before/--after must print concise diff output",
    )
    before_after_lines = before_after_cli.stdout.strip().splitlines()
    _assert(
        before_after_lines
        and before_after_lines[0].startswith("Benchmark governance:"),
        "run_benchmark_diff --before/--after must print governance summary first",
    )
    _assert(
        "Benchmark diff:" in before_after_cli.stdout
        and "- drift_categories:" in before_after_cli.stdout,
        "run_benchmark_diff --before/--after must preserve detailed diff output",
    )
    _assert(
        "C:" not in before_after_cli.stdout
        and "jarvis-core" not in before_after_cli.stdout
        and "raw_idea" not in before_after_cli.stdout
        and "goal" not in before_after_cli.stdout
        and "input_data" not in before_after_cli.stdout
        and "scenario_id" not in before_after_cli.stdout,
        "benchmark diff CLI output must not leak local paths",
    )

    history_cli = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_benchmark_diff.py")),
            "--history",
            str(history_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        history_cli.returncode == 0,
        f"run_benchmark_diff --history failed: {history_cli.stderr.strip()}",
    )
    _assert(
        "Benchmark diff:" in history_cli.stdout
        and "regressions=" in history_cli.stdout,
        "run_benchmark_diff --history must print concise diff output",
    )
    history_lines = history_cli.stdout.strip().splitlines()
    _assert(
        history_lines and history_lines[0].startswith("Benchmark governance:"),
        "run_benchmark_diff --history must print governance summary first",
    )
    _assert(
        "Benchmark diff:" in history_cli.stdout
        and "- drift_categories:" in history_cli.stdout,
        "run_benchmark_diff --history must preserve detailed diff output",
    )
    _assert(
        "C:" not in history_cli.stdout
        and "jarvis-core" not in history_cli.stdout
        and "raw_idea" not in history_cli.stdout
        and "goal" not in history_cli.stdout
        and "input_data" not in history_cli.stdout
        and "scenario_id" not in history_cli.stdout,
        "benchmark diff history output must not leak local paths",
    )


def test_mutation_test_runner_contract() -> None:
    cases = build_mutation_cases()
    summary = run_mutation_tests(cases)
    summary_text = format_mutation_summary(summary)
    _assert(summary.passed, summary_text)
    _assert(summary.total_cases >= 15, "mutation suite must cover fixed edge cases")
    _assert(
        set(summary.categories_covered)
        >= {
            "negation",
            "weak_keyword",
            "structural_anchor",
            "contamination",
            "unsafe_confidence",
        },
        "mutation suite must cover the required robustness categories",
    )
    _assert(
        summary.profile_drift_failures == 0,
        "passing mutation suite must record zero profile drift failures",
    )
    _assert(
        summary.contamination_failures == 0,
        "passing mutation suite must record zero contamination failures",
    )
    _assert(
        summary.unsafe_acceptance_failures == 0,
        "passing mutation suite must record zero unsafe acceptance failures",
    )
    _assert(
        "C:" not in summary_text and "jarvis-core" not in summary_text,
        "mutation summary must not leak local filesystem paths",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_mutation_tests.py")),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        completed.returncode == 0,
        f"run_mutation_tests.py failed: {completed.stderr.strip()}",
    )
    _assert(
        "Mutation tests passed:" in completed.stdout,
        "run_mutation_tests.py must print a concise pass summary",
    )
    _assert(
        "C:" not in completed.stdout and "jarvis-core" not in completed.stdout,
        "mutation runner output must not leak local filesystem paths",
    )


def test_scenario_template_generation_contract() -> None:
    scenarios = generate_scenarios()
    repeated_scenarios = generate_scenarios()
    summary = build_scenario_summary(scenarios)
    summary_text = format_scenario_summary(summary)
    serialized = scenarios_to_json(summary)
    payload = json.loads(serialized)

    _assert(scenarios == repeated_scenarios, "scenario generation must be deterministic")
    _assert(summary.total_scenarios == 42, "scenario templates must generate fixed coverage")
    _assert(
        summary.categories_covered == tuple(sorted(CATEGORY_ORDER)),
        "scenario templates must cover all required categories",
    )
    _assert(
        summary.profiles_covered == PROFILE_ORDER,
        "scenario templates must cover benchmark profile ids",
    )
    _assert(
        set(summary.cases_by_category.values()) == {len(PROFILE_ORDER)},
        "each scenario template category must cover all profiles",
    )
    _assert(
        set(summary.cases_by_profile.values()) == {len(CATEGORY_ORDER)},
        "each profile must receive one scenario per template category",
    )
    _assert(
        summary_text.startswith("Scenario templates generated:")
        and "42 scenarios" in summary_text
        and "6 categories" in summary_text
        and "7 profiles" in summary_text,
        "scenario template summary must stay concise",
    )
    _assert(
        payload["total_scenarios"] == summary.total_scenarios
        and len(payload["scenarios"]) == summary.total_scenarios,
        "scenario template JSON must preserve scenario count",
    )
    _assert(
        payload == json.loads(scenarios_to_json(summary)),
        "scenario template JSON serialization must be stable",
    )
    for forbidden_text in ("C:", "jarvis-core", "timestamp", "uuid", "current time"):
        _assert(
            forbidden_text not in serialized and forbidden_text not in summary_text,
            f"scenario templates must not leak nondeterministic metadata: {forbidden_text}",
        )

    negation_summary = build_scenario_summary(generate_scenarios(category="negation_template"))
    _assert(
        negation_summary.total_scenarios == len(PROFILE_ORDER),
        "scenario category filtering must keep deterministic profile coverage",
    )

    template_cases = build_template_mutation_cases()
    template_summary = run_mutation_tests(template_cases)
    template_summary_text = format_mutation_summary(template_summary)
    _assert(template_summary.passed, template_summary_text)
    _assert(
        template_summary.total_cases == 6,
        "scenario-template mutation subset must stay lightweight",
    )
    _assert(
        set(template_summary.categories_covered)
        >= {
            "negation_template",
            "weak_keyword_template",
            "contamination_template",
            "structural_anchor_template",
            "confidence_escalation_template",
            "ambiguity_template",
        },
        "scenario-template subset must convert generated scenarios into mutation checks",
    )

    text_cli = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_scenario_templates.py")),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        text_cli.returncode == 0,
        f"run_scenario_templates.py failed: {text_cli.stderr.strip()}",
    )
    _assert(
        len(text_cli.stdout.strip().splitlines()) == 1
        and "Scenario templates generated:" in text_cli.stdout
        and "42 scenarios" in text_cli.stdout,
        "run_scenario_templates.py must print the concise scenario summary by default",
    )

    json_cli = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_scenario_templates.py")),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        json_cli.returncode == 0,
        f"run_scenario_templates.py --json failed: {json_cli.stderr.strip()}",
    )
    _assert(
        json.loads(json_cli.stdout)["total_scenarios"] == summary.total_scenarios,
        "run_scenario_templates.py --json must emit parseable deterministic JSON",
    )
    _assert(
        "C:" not in json_cli.stdout and "jarvis-core" not in json_cli.stdout,
        "scenario template JSON output must not leak local filesystem paths",
    )

    category_cli = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_scenario_templates.py")),
            "--category",
            "weak_keyword_template",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(
        category_cli.returncode == 0,
        f"run_scenario_templates.py --category failed: {category_cli.stderr.strip()}",
    )
    _assert(
        "7 scenarios" in category_cli.stdout
        and "1 category" in category_cli.stdout
        and "7 profiles" in category_cli.stdout,
        "scenario template category filter must report bounded generated coverage",
    )


def test_run_demo_unknown_profile_fails_clearly() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("run_demo.py")),
            "--profile",
            "unknown_profile",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    _assert(completed.returncode != 0, "unknown explicit profile must fail")
    _assert(
        "unknown domain profile" in completed.stderr,
        "unknown explicit profile must explain the error",
    )
    _assert(
        "Traceback" not in completed.stderr,
        "unknown explicit profile must fail without a traceback",
    )


def test_domain_profile_selection_foundation() -> None:
    profile_ids = tuple(profile.id for profile in list_profiles())
    _assert(
        profile_ids
        == (
            "general",
            "medical_device",
            "ai_saas",
            "creator_tools",
            "marketplace",
            "enterprise_b2b",
            "developer_tool",
            "consumer_app",
            "hardware_device",
            "materials_science",
        ),
        "domain profile registry must expose the initial profiles in deterministic order",
    )
    _assert(
        get_profile("software").id == "ai_saas",
        "software alias must resolve to ai_saas",
    )
    _assert(
        get_profile("creator").id == "creator_tools",
        "creator alias must resolve to creator_tools",
    )
    _assert(
        get_profile("hardware").id == "hardware_device",
        "hardware alias must resolve to hardware_device",
    )
    _assert(
        get_profile("capsule_medical_environmental").id == "medical_device",
        "legacy capsule alias must resolve to medical_device",
    )

    medical_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "Swallowable capsule medical device for colon screening with "
                "biocompatibility constraints"
            ),
            "goal": "Evaluate patient safety and diagnostic feasibility.",
            "context": "Clinical workflow and regulatory risk are central.",
        }
    )
    _assert(
        medical_selection.selected_profile.id == "medical_device",
        "medical capsule idea must select medical_device",
    )
    _assert(
        medical_selection.selected_by == "deterministic_score",
        "medical capsule selection must be score-based",
    )
    _assert(
        "capsule" in medical_selection.matched_keywords["medical_device"],
        "medical capsule selection must explain matched keywords",
    )

    ai_selection = resolve_domain_profile(
        {
            "raw_idea": "AI SaaS patent analysis assistant for solo founders",
            "goal": "Evaluate differentiation and market viability.",
            "context": "Bootstrap software workflow before external research.",
        }
    )
    _assert(
        ai_selection.selected_profile.id == "ai_saas",
        "AI SaaS / patent assistant idea must select ai_saas",
    )

    creator_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "Creator content studio for newsletter creators and YouTubers with "
                "content production workflow, fan community prompts, audience growth, "
                "content repurposing, sponsorship monetization, platform dependency, "
                "and creator retention tracking"
            ),
            "goal": (
                "Evaluate creator workflow fit, audience growth loop, monetization, "
                "distribution channel dependency, and willingness to pay by creator segment."
            ),
            "context": "Creator workflow and audience lock-in should dominate generic SaaS framing.",
        }
    )
    _assert(
        creator_selection.selected_profile.id == "creator_tools",
        "creator workflow / audience / monetization input must select creator_tools",
    )

    enterprise_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "Enterprise workflow platform for compliance automation with procurement, "
                "security review, SSO, audit logs, and multi-team rollout"
            ),
            "goal": "Evaluate stakeholder alignment, ROI proof, and rollout risk.",
            "context": "Budget owner, IT approval, and department workflow matter.",
        }
    )
    _assert(
        enterprise_selection.selected_profile.id == "enterprise_b2b",
        "enterprise procurement / security / rollout input must select enterprise_b2b",
    )

    marketplace_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "Local service marketplace connecting providers and customers with listings, "
                "booking, reviews, escrow, liquidity, local density, take rate, and trust and safety moderation"
            ),
            "goal": "Evaluate supply and demand acquisition, cold start, matching, and transaction frequency.",
            "context": "Marketplace structure should dominate generic SaaS or enterprise software framing.",
        }
    )
    _assert(
        marketplace_selection.selected_profile.id == "marketplace",
        "marketplace liquidity / supply-demand / transaction input must select marketplace",
    )

    weak_marketplace_keyword_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "Booking and reviews management app for small service businesses with "
                "transaction history."
            ),
            "goal": "Evaluate SaaS workflow value and retention.",
            "context": "This is SaaS software for service operations, not a two-sided marketplace.",
        }
    )
    _assert(
        weak_marketplace_keyword_selection.selected_profile.id != "marketplace",
        "weak booking / reviews / transaction wording alone must not select marketplace",
    )

    structural_marketplace_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "Two-sided marketplace matching local service providers and customers "
                "with liquidity and trust-and-safety challenges."
            ),
            "goal": "Evaluate supply and demand, cold start, local density, and transaction frequency.",
            "context": "Marketplace structure should dominate generic software framing.",
        }
    )
    _assert(
        structural_marketplace_selection.selected_profile.id == "marketplace",
        "structural two-sided marketplace anchor must select marketplace",
    )

    negated_enterprise_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "AI SaaS for legal intake automation. No enterprise rollout, compliance, "
                "or security workflow is planned."
            ),
            "goal": "Evaluate buyer workflow, retention, and willingness to pay.",
            "context": "This is business software for legal intake teams.",
        }
    )
    _assert(
        negated_enterprise_selection.selected_profile.id == "ai_saas",
        "AI SaaS with negated enterprise keywords must remain ai_saas",
    )
    _assert(
        not negated_enterprise_selection.matched_keywords["enterprise_b2b"],
        "negated enterprise / compliance / security wording must not score enterprise_b2b",
    )

    negated_developer_keyword_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "AI SaaS for legal intake automation. No SDK, CLI, logs, "
                "observability, or local development workflow is planned."
            ),
            "goal": "Evaluate buyer workflow, retention, and willingness to pay.",
            "context": "This is business software for legal intake teams.",
        }
    )
    _assert(
        negated_developer_keyword_selection.selected_profile.id == "ai_saas",
        "AI SaaS with negated developer keywords must remain ai_saas",
    )
    _assert(
        not negated_developer_keyword_selection.matched_keywords["developer_tool"],
        "negated SDK / CLI / logs wording must not score developer_tool",
    )

    negated_marketplace_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "AI SaaS for legal intake automation. No marketplace, sellers, buyers, "
                "listings, or transaction workflow is planned."
            ),
            "goal": "Evaluate buyer workflow, retention, and willingness to pay.",
            "context": "This is business software for legal intake teams.",
        }
    )
    _assert(
        negated_marketplace_selection.selected_profile.id == "ai_saas",
        "AI SaaS with negated marketplace keywords must remain ai_saas",
    )
    _assert(
        not negated_marketplace_selection.matched_keywords["marketplace"],
        "negated marketplace / sellers / buyers / listings / transaction wording must not score marketplace",
    )

    negated_creator_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "AI SaaS for marketing operations. No creator platform, no fan community, "
                "and no monetization workflow is planned."
            ),
            "goal": "Evaluate buyer workflow, retention, and willingness to pay.",
            "context": "This is business software for content marketing teams.",
        }
    )
    _assert(
        negated_creator_selection.selected_profile.id == "ai_saas",
        "negated creator keywords must not override AI SaaS selection",
    )
    _assert(
        not negated_creator_selection.matched_keywords["creator_tools"],
        "negated creator / fan community / monetization wording must not score creator_tools",
    )

    long_negated_creator_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "AI SaaS for marketing operations. No creator platform, fan community, "
                "content calendar, distribution channel, platform dependency, or "
                "monetization workflow is planned."
            ),
            "goal": "Evaluate buyer workflow, retention, and willingness to pay.",
            "context": "This is business software for content marketing teams.",
        }
    )
    _assert(
        long_negated_creator_selection.selected_profile.id == "ai_saas",
        "long negated creator keyword list must not override AI SaaS selection",
    )
    _assert(
        not long_negated_creator_selection.matched_keywords["creator_tools"],
        "long negated creator keyword list must not score creator_tools",
    )

    weak_creator_keyword_selection = resolve_domain_profile(
        {
            "raw_idea": "Content marketing calendar for internal brand campaigns and blog approvals.",
            "goal": "Evaluate marketing workflow value and campaign operations.",
            "context": "No creator workflow, fan community, or creator monetization path is planned.",
        }
    )
    _assert(
        weak_creator_keyword_selection.selected_profile.id != "creator_tools",
        "weak generic content / marketing wording alone must not select creator_tools",
    )

    developer_tool_selection = resolve_domain_profile(
        {
            "raw_idea": (
                "AI developer tool CLI debugging SDK with observability logs, "
                "GitHub integration, CI/CD monitoring, and local development workflow"
            ),
            "goal": "Evaluate setup complexity, integration cost, and repeat usage.",
            "context": "Developer workflow fit should dominate generic AI SaaS positioning.",
        }
    )
    _assert(
        developer_tool_selection.selected_profile.id == "developer_tool",
        "developer workflow / SDK / CLI / observability input must select developer_tool",
    )

    consumer_selection = resolve_domain_profile(
        {
            "raw_idea": "Consumer mobile app for daily habit tracking and social accountability",
            "goal": "Evaluate retention and willingness to pay.",
            "constraints": ("Privacy-sensitive consumer data must be handled carefully.",),
        }
    )
    _assert(
        consumer_selection.selected_profile.id == "consumer_app",
        "consumer app idea must select consumer_app",
    )

    hardware_selection = resolve_domain_profile(
        {
            "raw_idea": "Sensor hardware device with embedded firmware and battery constraints",
            "goal": "Evaluate prototype feasibility and manufacturing risk.",
        }
    )
    _assert(
        hardware_selection.selected_profile.id == "hardware_device",
        "hardware device idea must select hardware_device",
    )

    materials_selection = resolve_domain_profile(
        {
            "raw_idea": "Biodegradable polymer coating with UV degradation and residue testing",
            "goal": "Evaluate material performance and disposal risk.",
        }
    )
    _assert(
        materials_selection.selected_profile.id == "materials_science",
        "materials / degradation idea must select materials_science",
    )

    medical_materials_selection = resolve_domain_profile(
        {
            "raw_idea": "Biodegradable implant material for patient safety testing",
            "goal": "Evaluate clinical safety and material degradation.",
        }
    )
    _assert(
        medical_materials_selection.selected_profile.id == "medical_device",
        "medical safety terms must dominate materials terms when selecting profiles",
    )

    fallback_selection = resolve_domain_profile(
        {
            "raw_idea": "A taxonomy for organizing private reading notes",
            "goal": "Evaluate clarity.",
        }
    )
    _assert(
        fallback_selection.selected_profile.id == "general",
        "unmatched ideas must fall back to general",
    )
    _assert(
        fallback_selection.selected_by == "fallback",
        "unmatched ideas must report fallback selection",
    )

    explicit_selection = resolve_domain_profile(
        {"raw_idea": "A hardware sensor concept", "goal": "Evaluate risk."},
        explicit_profile_id="software",
    )
    _assert(
        explicit_selection.selected_profile.id == "ai_saas",
        "explicit aliases must win over deterministic scoring",
    )
    _assert(
        explicit_selection.selected_by == "explicit",
        "explicit profile selection must report explicit selection",
    )

    try:
        resolve_domain_profile(
            {"raw_idea": "A concept", "goal": "Evaluate risk."},
            explicit_profile_id="unknown_profile",
        )
    except ValueError as exc:
        _assert(
            "unknown domain profile" in str(exc),
            "unknown explicit profile must raise a clear ValueError",
        )
    else:
        raise AssertionError("unknown explicit profile must raise ValueError")


def main() -> None:
    test_deterministic_pipeline_contract()
    test_json_export_contract()
    test_optional_llm_augmentation_sandbox()
    test_run_demo_json_output_support()
    test_run_demo_custom_cli_input_support()
    test_run_demo_explicit_profile_support()
    test_ai_saas_profile_reasoning()
    test_ai_saas_policy_regression_signals()
    test_medical_device_policy_regression_preserves_conservative_behavior()
    test_ai_saas_evidence_gap_engine_links_experiments()
    test_medical_device_evidence_gap_engine_preserves_conservative_confidence()
    test_ai_saas_reasoning_trace_explainability()
    test_medical_device_reasoning_trace_explainability()
    test_confidence_trace_linkage_and_json_additive_fields()
    test_golden_case_evaluation_harness()
    test_benchmark_snapshot_export_contract()
    test_benchmark_history_contract()
    test_benchmark_diff_viewer_contract()
    test_mutation_test_runner_contract()
    test_scenario_template_generation_contract()
    test_run_demo_unknown_profile_fails_clearly()
    test_domain_profile_selection_foundation()
    print("Research Council smoke tests passed")


if __name__ == "__main__":
    main()
