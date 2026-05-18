"""Smoke tests for the deterministic Research Council v0.1 pipeline."""

from __future__ import annotations

from research_council import run_research_council
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


def main() -> None:
    test_deterministic_pipeline_contract()
    print("Research Council smoke tests passed")


if __name__ == "__main__":
    main()
