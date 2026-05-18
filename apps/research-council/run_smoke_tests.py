"""Smoke tests for the deterministic Research Council v0.1 pipeline."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from research_council import (
    result_from_json,
    result_to_artifacts_dict,
    result_to_json,
    result_to_json_dict,
    run_research_council,
)
from research_council.claim_extractor import domain_profile_for
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
    domain_profile = domain_profile_for(input_data)

    payload = result_to_json_dict(result, domain_profile=domain_profile)
    loaded_payload = json.loads(result_to_json(result, domain_profile=domain_profile))
    _assert(loaded_payload == payload, "JSON payload must round-trip through json.loads")
    _assert(
        result_from_json(result_to_json(result, domain_profile=domain_profile)) == result,
        "JSON payload must rehydrate to the original result",
    )

    _assert(loaded_payload["result_type"] == "research_council_result", "JSON result_type missing")
    _assert(loaded_payload["version"] == "0.1", "JSON version missing")
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
    _assert(loaded_payload["domain_profile"]["id"], "JSON domain profile id must be preserved")
    _assert(
        loaded_payload["domain_profile"]["concept_label"],
        "JSON domain profile concept label must be preserved",
    )
    _assert(
        loaded_payload["domain_profile"]["blocker_order"],
        "JSON domain profile blocker order must be preserved",
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

    artifact_payload = result_to_artifacts_dict(
        result,
        domain_profile=domain_profile,
    )
    _assert(
        isinstance(artifact_payload["markdown_report"], str),
        "compact artifact JSON must expose markdown_report as text",
    )
    _assert(
        artifact_payload["markdown_report_artifact"]["artifact_type"] == "markdown",
        "compact artifact JSON must preserve markdown artifact metadata",
    )
    _assert(
        artifact_payload["domain_profile"]["id"],
        "compact artifact JSON must preserve domain profile fields",
    )
    _assert(
        artifact_payload["domain_profile"]["evidence_needs"],
        "compact artifact JSON must preserve domain evidence needs",
    )


def test_run_demo_json_output_support() -> None:
    artifacts_root = Path(__file__).parent / "artifacts"
    artifacts_root.mkdir(exist_ok=True)
    json_path = artifacts_root / "smoke-result.json"
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
        exported_payload["domain_profile"]["evidence_needs"],
        "run_demo JSON must preserve domain profile evidence needs",
    )
    exported_result = result_from_json(exported_json)
    _assert(
        exported_result.markdown_report.markdown == completed.stdout,
        "run_demo JSON markdown must match stdout markdown",
    )


def main() -> None:
    test_deterministic_pipeline_contract()
    test_json_export_contract()
    test_run_demo_json_output_support()
    print("Research Council smoke tests passed")


if __name__ == "__main__":
    main()
