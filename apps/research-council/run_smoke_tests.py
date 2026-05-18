"""Smoke tests for the Research Council v0.1 foundation pass."""

from __future__ import annotations

from research_council import ResearchCouncilInput, run_research_council


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_placeholder_pipeline_contract() -> None:
    result = run_research_council(
        ResearchCouncilInput(
            raw_idea="A local research helper might make vague ideas easier to validate.",
            goal="Check whether Research Council has a useful v0.1 shape.",
            provided_evidence=("The user requested the first schema and contract pass.",),
        )
    )

    _assert(result.result_type == "research_council_result", "unexpected result_type")
    _assert(result.version == "0.1", "unexpected version")
    _assert(len(result.claims) >= 1, "result must include claims")
    _assert(len(result.evidence_ledger) >= 1, "result must include evidence ledger")
    _assert(len(result.reviewer_critiques) >= 1, "result must include reviewer critiques")
    _assert(len(result.experiments) >= 1, "result must include experiments")
    _assert(result.recommendation.decision, "result must include recommendation")
    _assert(result.markdown_report.artifact_type == "markdown", "report must be markdown")
    _assert(result.markdown_report.markdown.startswith("# Research Council Report"), "report markdown missing title")
    _assert(any(entry.evidence_type == "missing" for entry in result.evidence_ledger), "missing evidence must be explicit")
    _assert(any(claim.source_label == "needs_evidence" for claim in result.claims), "claims must mark evidence needs")


def main() -> None:
    test_placeholder_pipeline_contract()
    print("Research Council smoke tests passed")


if __name__ == "__main__":
    main()
