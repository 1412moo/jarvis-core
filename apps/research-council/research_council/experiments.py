"""Deterministic minimum viable experiment proposals for Research Council.

This module creates local, cheap, decision-oriented experiment plans. It does
not perform web search, network calls, LLM calls, or citation generation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from textwrap import shorten

from .claim_extractor import domain_profile_for
from .schemas import Claim, EvidenceEntry, ExperimentPlan, ResearchCouncilInput, ReviewerCritique


@dataclass(frozen=True)
class _ExperimentDraft:
    title: str
    hypothesis: str
    claim_ids: tuple[str, ...]
    method: str
    metric: str
    minimum_sample: str
    estimated_time: str
    estimated_cost_level: str
    stop_criteria: str
    decision_impact: str
    risk: str


def propose_experiments(
    input_data: ResearchCouncilInput,
    claims: Sequence[Claim],
    evidence_entries: Sequence[EvidenceEntry],
    critiques: Sequence[ReviewerCritique],
) -> list[ExperimentPlan]:
    """Return deterministic, minimum viable experiment plans."""

    claim_list = tuple(claims)
    evidence_list = tuple(evidence_entries)
    critique_list = tuple(critiques)
    fallback_ids = _fallback_claim_ids(claim_list)
    domain_profile = domain_profile_for(input_data)

    if domain_profile.id == "capsule_medical_environmental":
        drafts = (
            _capsule_safety_boundary_experiment(input_data, claim_list, critique_list, fallback_ids),
            _capsule_sensing_bench_experiment(claim_list, critique_list, fallback_ids),
            _capsule_degradation_experiment(claim_list, critique_list, fallback_ids),
            _capsule_adoption_experiment(input_data, claim_list, critique_list, fallback_ids),
        )
        return [_to_experiment_plan(index, draft) for index, draft in enumerate(drafts, start=1)]

    drafts = (
        _usefulness_experiment(input_data, claim_list, evidence_list, critique_list, fallback_ids),
        _evidence_gap_experiment(claim_list, evidence_list, fallback_ids),
        _safety_tabletop_experiment(input_data, claim_list, critique_list, fallback_ids),
    )

    return [_to_experiment_plan(index, draft) for index, draft in enumerate(drafts, start=1)]


def _usefulness_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    evidence_entries: tuple[EvidenceEntry, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _select_claim_ids(
        claims,
        ("adopt", "market", "user", "useful", "value", "decision", "goal"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Decision usefulness readout",
        hypothesis=(
            "A target user can turn the structured claims, gaps, and critiques into a clearer "
            "next decision than they had from the raw idea alone."
        ),
        claim_ids=claim_ids,
        method=(
            "Run the idea through the local workflow or current structured notes, then ask one "
            "representative user to compare the raw idea with the resulting claims, gaps, critiques, "
            f"and experiments. Use the stated goal as the decision frame: {_short_goal(input_data)}."
        ),
        metric=(
            "The reviewer names at least one concrete decision that changed, became clearer, "
            "or was intentionally deferred because of an evidence gap."
        ),
        minimum_sample="One representative user or one realistic saved idea.",
        estimated_time="60-90 minutes",
        estimated_cost_level="free",
        stop_criteria=(
            "Stop if the reviewer cannot identify a decision impact after one complete pass."
        ),
        decision_impact=(
            "Continue only if the workflow produces a decision-relevant next action; otherwise "
            "revise the claim and critique format before integrating."
        ),
        risk=(
            "One readout can overfit to a friendly reviewer, so treat it as a usefulness screen, "
            "not market validation."
        ),
    )


def _evidence_gap_experiment(
    claims: tuple[Claim, ...],
    evidence_entries: tuple[EvidenceEntry, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    unsupported_ids = _unsupported_claim_ids(claims, evidence_entries)
    claim_ids = unsupported_ids[:3] if unsupported_ids else fallback_ids
    return _ExperimentDraft(
        title="Primary evidence gap closure check",
        hypothesis=(
            "The highest-risk unsupported claims can be converted into explicit evidence needs "
            "or dropped without blocking a cheap next step."
        ),
        claim_ids=claim_ids,
        method=(
            "List each missing or low-confidence claim, write the smallest acceptable evidence "
            "that would support it, and mark whether that evidence can be gathered locally without "
            "web search or network calls."
        ),
        metric=(
            "Every selected unsupported claim is either paired with a concrete evidence request, "
            "converted into an experiment, or removed from the decision."
        ),
        minimum_sample="Up to three unsupported claims from the current evidence ledger.",
        estimated_time="30-45 minutes",
        estimated_cost_level="free",
        stop_criteria=(
            "Stop if a required claim needs external evidence that is unavailable under the current constraints."
        ),
        decision_impact=(
            "Decide whether to proceed with only local validation, narrow the idea, or pause until "
            "external evidence collection is allowed."
        ),
        risk=(
            "The exercise improves evidence hygiene but does not create new external proof."
        ),
    )


def _safety_tabletop_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    safety_ids = _critique_claim_ids(critiques, "safety_regulatory")
    red_team_ids = _critique_claim_ids(critiques, "red_team")
    claim_ids = safety_ids or red_team_ids or _select_claim_ids(
        claims,
        ("safety", "regulatory", "privacy", "data", "risk", "legal", "health", "financial"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Safety and misuse tabletop",
        hypothesis=(
            "The idea can define clear local-use boundaries that prevent unsupported advice, "
            "sensitive-data leakage, and false confidence."
        ),
        claim_ids=claim_ids,
        method=(
            "Review the raw idea, goal, and critiques against three failure prompts: harmful advice, "
            "sensitive data exposure, and overconfident unsupported claims. Record one mitigation or "
            f"pause condition for each. Constraints considered: {_short_constraints(input_data)}."
        ),
        metric=(
            "All high-severity safety or red-team findings have an owner, mitigation, or explicit "
            "stop condition before broader use."
        ),
        minimum_sample="One 20-minute tabletop using the current idea and reviewer critiques.",
        estimated_time="20-30 minutes",
        estimated_cost_level="free",
        stop_criteria=(
            "Stop if any high-severity issue lacks a practical mitigation under the current scope."
        ),
        decision_impact=(
            "Proceed locally only if the boundary checklist is clear; otherwise narrow the use case "
            "or defer broader trials."
        ),
        risk=(
            "A tabletop can miss domain-specific obligations and should not be treated as legal, "
            "medical, or compliance advice."
        ),
    )


def _capsule_safety_boundary_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "safety_regulatory") or _select_claim_ids(
        claims,
        ("safety", "regulatory", "clinical", "patient", "ingested", "medical", "diagnostic"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Non-clinical capsule safety boundary table",
        hypothesis=(
            "The capsule concept can define safety blockers and stop conditions clearly enough "
            "to decide which non-clinical tests are permissible next."
        ),
        claim_ids=claim_ids,
        method=(
            "Create a table for ingestion, retention, obstruction, biocompatibility, sanitation, "
            "diagnostic false reassurance, data quality, discharge, and degradation-byproduct risks. "
            "For each row, record the minimum evidence required before moving beyond bench work. "
            f"Respect these constraints: {_short_constraints(input_data)}."
        ),
        metric=(
            "Every human-use or clinical-quality claim is either blocked, narrowed to bench-only "
            "language, or paired with a named expert-review requirement."
        ),
        minimum_sample="One structured hazard table covering the current capsule concept.",
        estimated_time="45-60 minutes",
        estimated_cost_level="free",
        stop_criteria=(
            "Stop if any ingestion, retention, diagnostic, or degradation risk lacks a bench-only "
            "test boundary."
        ),
        decision_impact=(
            "Decide whether the idea is safe to explore through non-clinical bench tests only, "
            "or whether it should pause until expert safety input is available."
        ),
        risk=(
            "A table is not medical, regulatory, or toxicology clearance; it only prevents premature scope expansion."
        ),
    )


def _capsule_sensing_bench_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "technical") or _select_claim_ids(
        claims,
        ("technical", "capsule", "sensor", "image", "data", "transit", "power", "inspection"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Bench capsule sensing and transit mockup",
        hypothesis=(
            "A capsule-sized non-ingestible mockup can collect interpretable observations while "
            "moving through a curved, wet, colon-like channel."
        ),
        claim_ids=claim_ids,
        method=(
            "Use an inert capsule-size shell or fixture in a simulated channel. Vary orientation, "
            "fluid, occlusion, and speed; record whether images or sensor readings remain readable "
            "and whether data capture assumptions are plausible. Do not use biological samples or people."
        ),
        metric=(
            "At least one sensing mode produces readable observations across the simulated path "
            "and records the failure cases that would make the concept impractical."
        ),
        minimum_sample="Three passes through one bench channel with different orientation or occlusion conditions.",
        estimated_time="2-4 hours",
        estimated_cost_level="low",
        stop_criteria=(
            "Stop if the mockup cannot produce interpretable readings under basic wet-channel conditions."
        ),
        decision_impact=(
            "Proceed to more detailed engineering only if bench sensing survives the simplest transit conditions."
        ),
        risk=(
            "A bench channel cannot prove clinical accuracy, safe ingestion, or full colon coverage."
        ),
    )


def _capsule_degradation_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _select_claim_ids(
        claims,
        (
            "environmental claim",
            "measured degradation",
            "wastewater compatibility",
            "sewage treatment",
            "byproducts",
        ),
        fallback_ids,
        limit=2,
    ) or _critique_claim_ids(critiques, "red_team")
    return _ExperimentDraft(
        title="Wastewater degradation screen",
        hypothesis=(
            "Candidate capsule materials can break down under simulated discharge conditions "
            "without obvious persistent fragments or residue."
        ),
        claim_ids=claim_ids,
        method=(
            "Expose material coupons or a nonfunctional shell to simulated wastewater conditions. "
            "Record visible breakdown, mass change if measurable, fragments, residue, and timing. "
            "Treat this as a screen, not environmental proof."
        ),
        metric=(
            "The test produces a timed degradation curve or a clear failure result for at least "
            "one candidate material."
        ),
        minimum_sample="One candidate material in three small containers or time checkpoints.",
        estimated_time="1-7 days",
        estimated_cost_level="low",
        stop_criteria=(
            "Stop if the material remains intact, leaves persistent fragments, or creates unknown residue."
        ),
        decision_impact=(
            "Decide whether the biodegradable claim deserves more materials work or should be removed from the concept."
        ),
        risk=(
            "A simple screen does not establish toxicology, wastewater treatment compatibility, or lifecycle impact."
        ),
    )


def _capsule_adoption_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("user", "adoption", "market", "patient", "clinician", "payer", "screening"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Care-pathway adoption check",
        hypothesis=(
            "The capsule concept changes a real screening decision for at least one stakeholder "
            "without relying on unsupported clinical claims."
        ),
        claim_ids=claim_ids,
        method=(
            "Show the concept as a hypothetical non-clinical storyboard to one patient-like user "
            "and one clinician, operator, or payer-like stakeholder. Ask what they would trust, "
            "reject, compare against, or need to see before considering it. Keep the goal in frame: "
            f"{_short_goal(input_data)}."
        ),
        metric=(
            "Each stakeholder names one decision requirement, refusal point, or competing pathway "
            "that would determine adoption."
        ),
        minimum_sample="Two structured interviews or readouts, separated by stakeholder type.",
        estimated_time="60-120 minutes",
        estimated_cost_level="free-to-low",
        stop_criteria=(
            "Stop if participants treat the idea as clinically proven or cannot identify a decision it would change."
        ),
        decision_impact=(
            "Decide whether adoption uncertainty is worth testing after safety and bench feasibility blockers."
        ),
        risk=(
            "Interview interest is not clinical validation, market proof, or reimbursement evidence."
        ),
    )


def _to_experiment_plan(index: int, draft: _ExperimentDraft) -> ExperimentPlan:
    return ExperimentPlan(
        id=f"experiment-{index:03d}",
        title=draft.title,
        hypothesis_claim_ids=draft.claim_ids,
        method=(
            f"Hypothesis: {draft.hypothesis} "
            f"Method: {draft.method} "
            f"Estimated time: {draft.estimated_time}. "
            f"Estimated cost level: {draft.estimated_cost_level}. "
            f"Stop criteria: {draft.stop_criteria} "
            f"Decision impact: {draft.decision_impact}"
        ),
        success_metric=f"Metric: {draft.metric}",
        minimum_sample=draft.minimum_sample,
        risk=draft.risk,
    )


def _fallback_claim_ids(claims: tuple[Claim, ...]) -> tuple[str, ...]:
    if claims:
        return (claims[0].id,)
    return ("input-idea",)


def _select_claim_ids(
    claims: tuple[Claim, ...],
    keywords: tuple[str, ...],
    fallback_ids: tuple[str, ...],
    *,
    limit: int,
) -> tuple[str, ...]:
    matches = tuple(
        claim.id for claim in claims if any(keyword in claim.text.lower() for keyword in keywords)
    )
    if matches:
        return matches[:limit]
    return fallback_ids[:limit] or ("input-idea",)


def _unsupported_claim_ids(
    claims: tuple[Claim, ...],
    evidence_entries: tuple[EvidenceEntry, ...],
) -> tuple[str, ...]:
    evidence_by_claim: dict[str, list[EvidenceEntry]] = {}
    for entry in evidence_entries:
        evidence_by_claim.setdefault(entry.claim_id, []).append(entry)

    unsupported: list[str] = []
    for claim in claims:
        entries = evidence_by_claim.get(claim.id, [])
        has_provided = any(entry.evidence_type == "provided" for entry in entries)
        has_missing = any(entry.evidence_type == "missing" for entry in entries)
        if claim.source_label == "needs_evidence" or claim.confidence == "low" or has_missing or not has_provided:
            unsupported.append(claim.id)
    return tuple(unsupported)


def _critique_claim_ids(critiques: tuple[ReviewerCritique, ...], reviewer_role: str) -> tuple[str, ...]:
    ids: list[str] = []
    for critique in critiques:
        if critique.reviewer_role == reviewer_role and critique.claim_id and critique.claim_id not in ids:
            ids.append(critique.claim_id)
    return tuple(ids)


def _short_goal(input_data: ResearchCouncilInput) -> str:
    value = _get_field(input_data, "goal") or "the user's stated goal"
    return shorten(value, width=120, placeholder="...")


def _short_constraints(input_data: ResearchCouncilInput) -> str:
    constraints = _get_sequence_field(input_data, "constraints")
    if not constraints:
        return "no extra constraints supplied"
    return shorten("; ".join(constraints), width=140, placeholder="...")


def _get_field(input_data: ResearchCouncilInput, field_name: str) -> str:
    if isinstance(input_data, dict):
        value = input_data.get(field_name, "")
    else:
        value = getattr(input_data, field_name, "")
    return str(value or "")


def _get_sequence_field(input_data: ResearchCouncilInput, field_name: str) -> tuple[str, ...]:
    if isinstance(input_data, dict):
        value = input_data.get(field_name, ())
    else:
        value = getattr(input_data, field_name, ())
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value if str(item).strip())
