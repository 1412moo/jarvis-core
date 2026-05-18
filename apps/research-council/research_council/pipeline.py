"""Deterministic Research Council v0.1 pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .claim_extractor import extract_claims
from .domain_profiles import DomainProfile, DomainProfileSelection, resolve_domain_profile
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
    "technical": (
        "output-quality",
        "reliability",
        "quality",
        "bench",
        "technical",
        "sensing",
        "prototype",
        "mockup",
    ),
    "environmental": ("degradation", "wastewater", "environment"),
    "user_adoption": (
        "workflow interview",
        "adoption",
        "care-pathway",
        "interview",
        "usefulness",
    ),
    "market": ("workflow interview", "differentiation", "adoption", "market", "payer", "buyer"),
    "prior_art": ("differentiation", "prior", "evidence gap", "comparison", "map"),
}

_AI_SAAS_CATEGORY_BONUS = {
    "user_adoption": 18,
    "technical": 16,
    "safety_regulatory": 14,
    "prior_art": 12,
    "market": 10,
}

_AI_SAAS_PRIORITY_TERMS = {
    "user_adoption": (
        "workflow",
        "founder",
        "adoption",
        "integration",
        "retention",
        "repeat usage",
    ),
    "technical": ("reliability", "quality", "traceability", "hallucination", "automation"),
    "safety_regulatory": ("trust", "verification", "legal", "patentability", "citation"),
    "prior_art": ("differentiation", "substitute", "prior-art", "generic ai"),
    "market": ("willingness to pay", "pricing", "distribution", "subscription"),
}


@dataclass(frozen=True)
class _DecisionBlocker:
    category: str
    claim_id: str
    status: str
    impact_score: int
    summary: str


def run_research_council(
    input: ResearchCouncilInput,
    profile: str | None = None,
) -> ResearchCouncilResult:
    """Run the deterministic v0.1 Research Council workflow.

    The pipeline is intentionally local and standard-library only. It wires the
    completed isolated modules together without web search, network calls, LLM
    calls, or citation generation.
    """

    profile_selection = resolve_domain_profile(input, explicit_profile_id=profile)
    profile_metadata = _profile_metadata(profile_selection)
    input_summary = _build_input_summary(input)
    claims = tuple(extract_claims(input, domain_profile=profile_selection.profile))
    evidence_ledger = tuple(
        build_evidence_ledger(input, claims, domain_profile=profile_selection.profile)
    )
    _validate_evidence_coverage(claims, evidence_ledger)

    reviewer_critiques = tuple(
        run_reviewers(
            input,
            claims,
            evidence_ledger,
            domain_profile=profile_selection.profile,
        )
    )
    experiments = tuple(
        propose_experiments(
            input,
            claims,
            evidence_ledger,
            reviewer_critiques,
            domain_profile=profile_selection.profile,
        )
    )
    recommendation = _create_recommendation(
        evidence_ledger=evidence_ledger,
        reviewer_critiques=reviewer_critiques,
        experiments=experiments,
        domain_profile=profile_selection.profile,
    )
    warnings = _build_warnings(evidence_ledger, profile_selection.profile)
    markdown_report = MarkdownReport(
        title="Research Council Report",
        markdown=render_markdown_report(
            {
                "title": "Research Council Report",
                "input_data": input.to_dict(),
                "input_summary": input_summary,
                "profile": profile_metadata,
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
        profile=profile_metadata,
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
    evidence_ledger: Sequence[EvidenceEntry],
    reviewer_critiques: Sequence[ReviewerCritique],
    experiments: Sequence[ExperimentPlan],
    domain_profile: DomainProfile,
) -> Recommendation:
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

        if domain_profile.id == "ai_saas":
            if primary_blocker.category == "safety_regulatory":
                decision = "pause_broad_use_resolve_trust_boundary"
            elif primary_blocker.category == "technical":
                decision = "continue_with_output_quality_experiment"
            elif primary_blocker.category == "user_adoption":
                decision = "continue_with_workflow_adoption_experiment"
            summary = (
                f"Primary AI SaaS blocker: {primary_blocker.category.replace('_', ' ')} "
                f"evidence for `{primary_blocker.claim_id}`. Treat the submitted description "
                "as concept input, not proof of founder adoption, output reliability, workflow "
                "integration, trust, narrow-wedge differentiation, retention, or willingness to pay."
            )
        else:
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
        next_step_policy_note = _next_step_policy_note(domain_profile, primary_blocker)
        if next_step_policy_note:
            next_step = f"{next_step} {next_step_policy_note}"
        rationale_parts = [
            "Blockers ranked by decision impact: "
            f"{_format_blocker_ranking(blockers)}.",
            (
                "User-provided evidence establishes what the concept says; actual support still "
                "requires the missing evidence named in the ledger."
            ),
        ]
        if domain_profile.id == "ai_saas":
            rationale_parts.append(
                "AI SaaS weighting gives extra priority to user adoption, reliability, "
                "workflow integration, trust, buyer urgency, AI-wrapper risk, and "
                "differentiation because these determine whether an AI tooling concept "
                "becomes a repeatable paid workflow."
            )
        confidence_note = _confidence_policy_note(domain_profile)
        if confidence_note:
            rationale_parts.append(confidence_note)
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
        confidence_note = _confidence_policy_note(domain_profile)
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
                + (f" {confidence_note}" if confidence_note else "")
            ),
        )

    confidence_note = _confidence_policy_note(domain_profile)
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
            + (f" {confidence_note}" if confidence_note else "")
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
        impact_score += _profile_priority_bonus(domain_profile, category, entry.summary)
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


def _profile_priority_bonus(
    domain_profile: DomainProfile, category: str, summary: str
) -> int:
    bonus = 0
    if domain_profile.id == "ai_saas":
        bonus += _AI_SAAS_CATEGORY_BONUS.get(category, 0)
    lowered = summary.lower()
    terms = _AI_SAAS_PRIORITY_TERMS.get(category, ())
    if any(term in lowered for term in terms):
        bonus += 6
    profile_terms = _profile_policy_terms(
        domain_profile,
        "reasoning_priorities",
        "risk_factors",
        "decision_heuristics",
    )
    if any(term in lowered for term in profile_terms):
        bonus += 4
    return bonus


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


def _build_warnings(
    evidence_ledger: Sequence[EvidenceEntry],
    domain_profile: DomainProfile,
) -> tuple[str, ...]:
    warnings: list[str] = list(_STANDARD_WARNINGS)
    if any(entry.evidence_type == "missing" for entry in evidence_ledger):
        warnings.append(
            "At least one claim has explicit missing evidence; do not treat the report as validated research."
        )
    warnings.extend(_profile_caveats(domain_profile))
    return tuple(warnings)


def _profile_metadata(selection: DomainProfileSelection) -> dict[str, object]:
    return {
        "profile_id": selection.profile.id,
        "selected_by": selection.selected_by,
        "matched_keywords": {
            profile_id: tuple(keywords)
            for profile_id, keywords in selection.matched_keywords.items()
        },
        "score_by_profile": dict(selection.score_by_profile),
        "reasoning_policy": _profile_policy_metadata(selection.profile),
    }


def _profile_policy_metadata(domain_profile: DomainProfile) -> dict[str, tuple[str, ...]]:
    return {
        "council_lenses": tuple(domain_profile.council_lenses),
        "reasoning_priorities": tuple(domain_profile.reasoning_priorities),
        "risk_factors": tuple(domain_profile.risk_factors),
        "evidence_expectations": tuple(domain_profile.evidence_expectations),
        "decision_heuristics": tuple(domain_profile.decision_heuristics),
        "output_guidance": tuple(domain_profile.output_guidance),
        "confidence_policy": tuple(domain_profile.confidence_policy),
        "caveat_policy": tuple(domain_profile.caveat_policy),
        "next_step_policy": tuple(domain_profile.next_step_policy),
    }


def _profile_policy_terms(
    domain_profile: DomainProfile,
    *field_names: str,
) -> tuple[str, ...]:
    terms: list[str] = []
    for field_name in field_names:
        for value in getattr(domain_profile, field_name, ()):
            normalized = str(value).lower().strip()
            if normalized:
                terms.append(normalized)
    return tuple(terms)


def _confidence_policy_note(domain_profile: DomainProfile) -> str:
    if not domain_profile.confidence_policy:
        return ""
    return "Profile confidence policy: " + " ".join(domain_profile.confidence_policy[:2])


def _next_step_policy_note(
    domain_profile: DomainProfile,
    primary_blocker: _DecisionBlocker | None,
) -> str:
    category = primary_blocker.category if primary_blocker else ""
    if domain_profile.id == "ai_saas":
        if category in {"user_adoption", "market"}:
            return (
                "Capture buyer/workflow owner, current substitute, switching cost, "
                "repeat-use trigger, and willingness-to-pay threshold."
            )
        if category == "technical":
            return (
                "Use a fixed rubric for output quality, source traceability, failure "
                "handling, and operational reliability."
            )
        if category == "prior_art":
            return (
                "Map the narrow wedge against generic AI, manual workflow, and existing "
                "software substitutes."
            )
        if category == "safety_regulatory":
            return (
                "Keep legal-output boundaries, uncertainty labels, and professional-review "
                "triggers visible."
            )
    if domain_profile.id == "medical_device":
        return (
            "Keep the next step non-clinical and preserve patient-safety, clinical-validation, "
            "and regulatory boundaries."
        )
    if domain_profile.next_step_policy:
        return domain_profile.next_step_policy[0]
    return ""


def _profile_caveats(domain_profile: DomainProfile) -> tuple[str, ...]:
    if domain_profile.id == "medical_device":
        return (
            "Medical-device profile caveat: this deterministic pass does not establish patient safety, clinical efficacy, diagnostic performance, or regulatory clearance.",
        )
    if domain_profile.id == "ai_saas":
        return (
            "AI SaaS profile caveat: buyer/workflow urgency, repeat usage, differentiation, AI-wrapper risk, operational reliability, and willingness to pay remain unvalidated without targeted evidence.",
        )
    if domain_profile.caveat_policy:
        return tuple(f"Profile caveat policy: {caveat}" for caveat in domain_profile.caveat_policy)
    return ()


__all__ = ["run_research_council"]
