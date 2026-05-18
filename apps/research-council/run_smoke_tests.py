"""Smoke tests for the deterministic Research Council v0.1 pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from research_council import (
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
    test_run_demo_unknown_profile_fails_clearly()
    test_domain_profile_selection_foundation()
    print("Research Council smoke tests passed")


if __name__ == "__main__":
    main()
