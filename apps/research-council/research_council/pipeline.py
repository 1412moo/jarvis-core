"""Deterministic Research Council v0.1 pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .claim_extractor import DomainProfile, domain_profile_for, extract_claims
from .evidence_ledger import build_evidence_ledger, evidence_gap_category, evidence_status
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

_ROLE_TO_BLOCKER_CATEGORY = {
    "technical": "technical",
    "market": "user_adoption",
    "safety_regulatory": "safety_regulatory",
    "red_team": "prior_art",
}

_EXPERIMENT_FRAGMENTS_BY_CATEGORY = {
    "safety_regulatory": ("safety", "hazard", "boundary"),
    "technical": ("bench", "technical", "sensing", "prototype", "mockup"),
    "environmental": ("degradation", "wastewater", "environment"),
    "user_adoption": ("adoption", "care-pathway", "interview", "usefulness"),
    "market": ("adoption", "market", "payer", "buyer"),
    "prior_art": ("prior", "evidence gap", "comparison", "map"),
}


@dataclass(frozen=True)
class _DecisionBlocker:
    category: str
    claim_id: str
    status: str
    impact_score: int
    summary: str


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
        input_data=input,
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
    input_data: ResearchCouncilInput,
    claims: Sequence[Claim],
    evidence_ledger: Sequence[EvidenceEntry],
    reviewer_critiques: Sequence[ReviewerCritique],
    experiments: Sequence[ExperimentPlan],
) -> Recommendation:
    domain_profile = domain_profile_for(input_data)
    blockers = _rank_decision_blockers(
        evidence_ledger=evidence_ledger,
        reviewer_critiques=reviewer_critiques,
        domain_profile=domain_profile,
    )
    high_severity_roles = sorted(
        {
            critique.reviewer_role
            for critique in reviewer_critiques
            if critique.severity == "high"
        }
    )
    primary_blocker = blockers[0] if blockers else None
    first_experiment = _select_next_experiment(experiments, primary_blocker)

    if primary_blocker:
        decision = "continue_with_primary_blocker_experiment"
        if primary_blocker.category == "safety_regulatory":
            decision = "pause_broad_use_resolve_safety_blocker"

        summary = (
            f"Primary blocker: {primary_blocker.category.replace('_', ' ')} evidence for "
            f"`{primary_blocker.claim_id}`. Treat the submitted description as concept input, "
            "not proof of feasibility, safety, adoption, environmental performance, or market demand."
        )
        next_step = (
            f"Run `{first_experiment.id}` ({first_experiment.title}) as the primary next experiment."
            if first_experiment
            else (
                "Create one minimum experiment that targets the highest-impact explicit "
                f"{primary_blocker.category.replace('_', ' ')} blocker."
            )
        )
        rationale_parts = [
            "Blockers ranked by decision impact: "
            f"{_format_blocker_ranking(blockers)}.",
            (
                "User-provided evidence establishes what the concept says; actual support still "
                "requires the missing evidence named in the ledger."
            ),
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


def _rank_decision_blockers(
    *,
    evidence_ledger: Sequence[EvidenceEntry],
    reviewer_critiques: Sequence[ReviewerCritique],
    domain_profile: DomainProfile,
) -> tuple[_DecisionBlocker, ...]:
    high_severity_claim_ids = {
        critique.claim_id for critique in reviewer_critiques if critique.severity == "high" and critique.claim_id
    }
    high_severity_categories = {
        _ROLE_TO_BLOCKER_CATEGORY.get(critique.reviewer_role, critique.reviewer_role)
        for critique in reviewer_critiques
        if critique.severity == "high"
    }
    category_rank = {
        category: len(domain_profile.blocker_order) - index
        for index, category in enumerate(domain_profile.blocker_order)
    }

    blockers: list[_DecisionBlocker] = []
    seen: set[tuple[str, str]] = set()
    for entry in evidence_ledger:
        status = evidence_status(entry)
        if status not in {"assumed", "missing", "needs_external_validation"}:
            continue
        category = evidence_gap_category(entry) or "technical"
        key = (category, entry.claim_id)
        if key in seen:
            continue
        seen.add(key)
        impact_score = category_rank.get(category, 0) * 10
        if status == "needs_external_validation":
            impact_score += 6
        if entry.claim_id in high_severity_claim_ids:
            impact_score += 14
        if category in high_severity_categories:
            impact_score += 10
        blockers.append(
            _DecisionBlocker(
                category=category,
                claim_id=entry.claim_id,
                status=status,
                impact_score=impact_score,
                summary=entry.summary,
            )
        )

    return tuple(
        sorted(
            blockers,
            key=lambda blocker: (
                -blocker.impact_score,
                domain_profile.blocker_order.index(blocker.category)
                if blocker.category in domain_profile.blocker_order
                else len(domain_profile.blocker_order),
                blocker.claim_id,
            ),
        )
    )


def _format_blocker_ranking(blockers: Sequence[_DecisionBlocker], *, limit: int = 4) -> str:
    if not blockers:
        return "none"
    return "; ".join(
        f"{blocker.category} on {blocker.claim_id}"
        for blocker in blockers[:limit]
    )


def _select_next_experiment(
    experiments: Sequence[ExperimentPlan],
    primary_blocker: _DecisionBlocker | None,
) -> ExperimentPlan | None:
    if not experiments:
        return None

    preferred_title_fragments = (
        _EXPERIMENT_FRAGMENTS_BY_CATEGORY.get(primary_blocker.category, ())
        if primary_blocker
        else ()
    )
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
