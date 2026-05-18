"""Deterministic minimum viable experiment proposals for Research Council.

This module creates local, cheap, decision-oriented experiment plans. It does
not perform web search, network calls, LLM calls, or citation generation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from textwrap import shorten

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

    drafts = (
        _usefulness_experiment(input_data, claim_list, evidence_list, critique_list, fallback_ids),
        _evidence_gap_experiment(claim_list, evidence_list, fallback_ids),
        _technical_spike_experiment(claim_list, critique_list, fallback_ids),
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
        title="Manual usefulness readout",
        hypothesis=(
            "A target user can turn the Research Council output into a clearer next decision "
            "than they had from the raw idea alone."
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
        title="Evidence gap closure check",
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


def _technical_spike_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _select_claim_ids(
        claims,
        ("technical", "workflow", "module", "pipeline", "local", "experiment", "integrat"),
        _critique_claim_ids(critiques, "technical") or fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Local determinism spike",
        hypothesis=(
            "The reviewer and experiment logic can produce stable, schema-valid outputs for "
            "representative ideas without hidden dependencies."
        ),
        claim_ids=claim_ids,
        method=(
            "Run the local modules twice with the same input, claims, and evidence ledger. Compare "
            "reviewer roles, critique IDs, experiment IDs, and claim links for exact stability."
        ),
        metric=(
            "Both runs return the same four reviewer roles and at least four schema-valid "
            "experiment plans with non-empty linked claim IDs."
        ),
        minimum_sample="Two repeated runs against one sample idea, then one run against a second idea.",
        estimated_time="30 minutes",
        estimated_cost_level="free",
        stop_criteria=(
            "Stop if outputs are nondeterministic, schema-invalid, or require manual cleanup."
        ),
        decision_impact=(
            "If stable, the modules are ready for later pipeline wiring; if not, keep them isolated "
            "and simplify the heuristics."
        ),
        risk=(
            "Passing a local spike does not prove the later integrated pipeline will handle every input shape."
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
