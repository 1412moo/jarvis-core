"""Smoke tests for the deterministic Research Council v0.1 pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from research_council import (
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
    test_run_demo_unknown_profile_fails_clearly()
    test_domain_profile_selection_foundation()
    print("Research Council smoke tests passed")


if __name__ == "__main__":
    main()
