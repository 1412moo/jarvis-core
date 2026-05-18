"""Deterministic Research Council v0.1 pipeline."""

from __future__ import annotations

from collections.abc import Sequence

from .claim_extractor import extract_claims
from .evidence_ledger import build_evidence_ledger, evidence_status
from .experiments import propose_experiments
from .report_renderer import render_markdown_report
from .reviewers import run_reviewers
from .schemas import (
    Claim,
    EvidenceEntry,
    ExperimentPlan,
    MarkdownReport,
    Recommendation,
    ResearchCouncilInput,
    ResearchCouncilResult,
    ReviewerCritique,
)


_STANDARD_WARNINGS = (
    "No web search, network calls, LLM calls, or external evidence collection were performed.",
    "No citations are generated; user-provided evidence is local input only.",
    "Missing evidence is represented explicitly in the evidence ledger.",
)


def run_research_council(input: ResearchCouncilInput) -> ResearchCouncilResult:
    """Run the deterministic v0.1 Research Council workflow.

    The pipeline is intentionally local and standard-library only. It wires the
    completed isolated modules together without web search, network calls, LLM
    calls, or citation generation.
    """

    input_summary = _build_input_summary(input)
    claims = tuple(extract_claims(input))
    evidence_ledger = tuple(build_evidence_ledger(input, claims))
    _validate_evidence_coverage(claims, evidence_ledger)

    reviewer_critiques = tuple(run_reviewers(input, claims, evidence_ledger))
    experiments = tuple(propose_experiments(input, claims, evidence_ledger, reviewer_critiques))
    recommendation = _create_recommendation(
        claims=claims,
        evidence_ledger=evidence_ledger,
        reviewer_critiques=reviewer_critiques,
        experiments=experiments,
    )
    warnings = _build_warnings(evidence_ledger)
    markdown_report = MarkdownReport(
        title="Research Council Report",
        markdown=render_markdown_report(
            {
                "title": "Research Council Report",
                "input_data": input.to_dict(),
                "input_summary": input_summary,
                "claims": claims,
                "evidence_ledger": evidence_ledger,
                "reviewer_critiques": reviewer_critiques,
                "experiments": experiments,
                "recommendation": recommendation,
                "warnings": warnings,
            }
        ),
    )

    return ResearchCouncilResult(
        input_summary=input_summary,
        claims=claims,
        evidence_ledger=evidence_ledger,
        reviewer_critiques=reviewer_critiques,
        experiments=experiments,
        recommendation=recommendation,
        markdown_report=markdown_report,
        warnings=warnings,
    )


def _build_input_summary(input: ResearchCouncilInput) -> str:
    return f"Evaluate whether the idea can support the goal: {input.goal}"


def _validate_evidence_coverage(
    claims: Sequence[Claim], evidence_ledger: Sequence[EvidenceEntry]
) -> None:
    covered_claim_ids = {entry.claim_id for entry in evidence_ledger}
    missing_claim_ids = [claim.id for claim in claims if claim.id not in covered_claim_ids]
    if missing_claim_ids:
        joined_ids = ", ".join(missing_claim_ids)
        raise ValueError(f"evidence ledger missing coverage for: {joined_ids}")


def _create_recommendation(
    *,
    claims: Sequence[Claim],
    evidence_ledger: Sequence[EvidenceEntry],
    reviewer_critiques: Sequence[ReviewerCritique],
    experiments: Sequence[ExperimentPlan],
) -> Recommendation:
    missing_entries = _entries_with_status(
        evidence_ledger, {"assumed", "missing", "needs_external_validation"}
    )
    externally_unvalidated_entries = _entries_with_status(
        evidence_ledger, {"needs_external_validation"}
    )
    provided_claim_ids = {
        entry.claim_id for entry in evidence_ledger if entry.evidence_type == "provided"
    }
    high_severity_roles = sorted(
        {
            critique.reviewer_role
            for critique in reviewer_critiques
            if critique.severity == "high"
        }
    )
    first_experiment = _select_next_experiment(
        experiments=experiments,
        high_severity_roles=high_severity_roles,
        has_missing_entries=bool(missing_entries),
    )

    if missing_entries:
        decision = "continue_with_minimum_experiments"
        if "safety_regulatory" in high_severity_roles or externally_unvalidated_entries:
            decision = "pause_broad_use_run_minimum_experiments"

        summary = (
            f"Proceed only with constrained minimum experiments: "
            f"{len(missing_entries)} of {len(evidence_ledger)} evidence entries are "
            "missing, assumed, or require external validation."
        )
        next_step = (
            f"Run `{first_experiment.id}` ({first_experiment.title}) before expanding scope."
            if first_experiment
            else "Create one minimum experiment that targets the largest explicit evidence gap."
        )
        rationale_parts = [
            f"{len(claims)} claims were extracted, with provided evidence touching "
            f"{len(provided_claim_ids)} claim(s).",
            "The ledger keeps unsupported claims visible instead of treating them as proven.",
        ]
        if high_severity_roles:
            rationale_parts.append(
                "High-severity critiques were raised by: "
                f"{', '.join(high_severity_roles)}."
            )
        return Recommendation(
            decision=decision,
            summary=summary,
            next_step=next_step,
            rationale=" ".join(rationale_parts),
        )

    if high_severity_roles:
        return Recommendation(
            decision="resolve_high_severity_critiques",
            summary=(
                "Evidence entries are present, but high-severity reviewer concerns "
                "must be resolved before broader use."
            ),
            next_step=(
                f"Address the {high_severity_roles[0]} critique and rerun the local pipeline."
            ),
            rationale=(
                "Reviewer severity is part of the deterministic evidence-aware decision; "
                "a complete ledger alone is not enough to proceed."
            ),
        )

    return Recommendation(
        decision="continue_with_controlled_next_step",
        summary="The local pass found no explicit missing evidence entries or high-severity critiques.",
        next_step=(
            f"Run `{first_experiment.id}` ({first_experiment.title}) as a controlled next step."
            if first_experiment
            else "Run one controlled local validation step."
        ),
        rationale=(
            "All claims have ledger coverage and reviewer risk is below high severity in this "
            "deterministic local pass."
        ),
    )


def _entries_with_status(
    evidence_ledger: Sequence[EvidenceEntry], statuses: set[str]
) -> tuple[EvidenceEntry, ...]:
    return tuple(entry for entry in evidence_ledger if evidence_status(entry) in statuses)


def _select_next_experiment(
    *,
    experiments: Sequence[ExperimentPlan],
    high_severity_roles: Sequence[str],
    has_missing_entries: bool,
) -> ExperimentPlan | None:
    if not experiments:
        return None

    preferred_title_fragments: list[str] = []
    if "safety_regulatory" in high_severity_roles:
        preferred_title_fragments.append("safety")
    if has_missing_entries:
        preferred_title_fragments.append("evidence gap")

    for fragment in preferred_title_fragments:
        for experiment in experiments:
            if fragment in experiment.title.lower():
                return experiment
    return experiments[0]


def _build_warnings(evidence_ledger: Sequence[EvidenceEntry]) -> tuple[str, ...]:
    warnings: list[str] = list(_STANDARD_WARNINGS)
    if any(entry.evidence_type == "missing" for entry in evidence_ledger):
        warnings.append(
            "At least one claim has explicit missing evidence; do not treat the report as validated research."
        )
    return tuple(warnings)


__all__ = ["run_research_council"]
