"""Deterministic placeholder pipeline for Research Council v0.1."""

from __future__ import annotations

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


def run_research_council(input: ResearchCouncilInput) -> ResearchCouncilResult:
    """Run the v0.1 placeholder Research Council workflow.

    This function is intentionally deterministic. It performs no web search, no
    network calls, and no LLM calls. Later passes can replace the placeholder
    internals while keeping this function shape stable.
    """

    input_summary = _build_input_summary(input)
    claims = _build_placeholder_claims(input)
    evidence_ledger = _build_placeholder_evidence(input, claims)
    reviewer_critiques = _build_placeholder_critiques()
    experiments = _build_placeholder_experiments()
    recommendation = Recommendation(
        decision="continue_with_minimum_experiment",
        summary="Continue only through a small local experiment before adding integrations.",
        next_step="Run one manual Research Council pass with a real idea and inspect whether the report produces useful next actions.",
        rationale="The current result exposes clear evidence gaps and can be validated without web search or app integrations.",
    )
    markdown_report = MarkdownReport(
        title="Research Council Report",
        markdown=_render_markdown_report(
            input_summary=input_summary,
            claims=claims,
            evidence_ledger=evidence_ledger,
            reviewer_critiques=reviewer_critiques,
            experiments=experiments,
            recommendation=recommendation,
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
        warnings=(
            "No web search, network calls, LLM calls, or external evidence collection were performed.",
            "Missing evidence is represented explicitly in the evidence ledger.",
        ),
    )


def _build_input_summary(input: ResearchCouncilInput) -> str:
    return f"Evaluate whether the idea can support the goal: {input.goal}"


def _build_placeholder_claims(input: ResearchCouncilInput) -> tuple[Claim, ...]:
    return (
        Claim(
            id="claim-001",
            text="The user's raw idea and goal define a research direction worth structuring.",
            source_label="user_provided",
            confidence="medium",
            rationale="The user supplied both an idea and a goal.",
        ),
        Claim(
            id="claim-002",
            text="The idea can be evaluated through a small local experiment before broader Jarvis integration.",
            source_label="extracted",
            confidence="low",
            rationale="The requested workflow can be checked through a local demo and report review.",
        ),
        Claim(
            id="claim-003",
            text="There is enough evidence to justify expanding Research Council beyond an isolated app module.",
            source_label="needs_evidence",
            confidence="low",
            rationale="No adoption, usefulness, or quality evidence has been collected in this foundation pass.",
        ),
    )


def _build_placeholder_evidence(
    input: ResearchCouncilInput, claims: tuple[Claim, ...]
) -> tuple[EvidenceEntry, ...]:
    first_evidence = (
        input.provided_evidence[0]
        if input.provided_evidence
        else "The user supplied a raw idea, goal, and requested Research Council workflow."
    )
    return (
        EvidenceEntry(
            id="evidence-001",
            claim_id=claims[0].id,
            evidence_type="provided",
            summary=first_evidence,
            reference_label="user_input",
            notes="This is user-provided context, not externally verified evidence.",
        ),
        EvidenceEntry(
            id="evidence-002",
            claim_id=claims[1].id,
            evidence_type="missing",
            summary="No real local trial has been run against a user idea yet.",
            notes="A manual smoke experiment can fill this gap.",
        ),
        EvidenceEntry(
            id="evidence-003",
            claim_id=claims[2].id,
            evidence_type="missing",
            summary="No external validation, adoption signal, or report quality review exists yet.",
            notes="Do not treat this claim as supported until evidence is collected.",
        ),
    )


def _build_placeholder_critiques() -> tuple[ReviewerCritique, ...]:
    return (
        ReviewerCritique(
            id="critique-001",
            reviewer_role="skeptic",
            claim_id="claim-003",
            finding="The expansion claim is unsupported because there is no usefulness or adoption evidence yet.",
            severity="high",
            suggested_action="Keep Research Council isolated until a local trial produces useful output.",
        ),
        ReviewerCritique(
            id="critique-002",
            reviewer_role="operator",
            claim_id=None,
            finding="The workflow should stay deterministic and local while the contract is stabilizing.",
            severity="medium",
            suggested_action="Use smoke tests and stdout Markdown before adding persistence or adapters.",
        ),
    )


def _build_placeholder_experiments() -> tuple[ExperimentPlan, ...]:
    return (
        ExperimentPlan(
            id="experiment-001",
            title="One-idea local report trial",
            hypothesis_claim_ids=("claim-001", "claim-002"),
            method="Run the local demo with one real user idea, then inspect whether the report identifies claims, gaps, critiques, and next actions.",
            success_metric="A human reviewer can name at least one useful next action from the Markdown report.",
            minimum_sample="One real idea and one manual review session.",
            risk="A single trial may validate formatting without proving repeated usefulness.",
        ),
    )


def _render_markdown_report(
    input_summary: str,
    claims: tuple[Claim, ...],
    evidence_ledger: tuple[EvidenceEntry, ...],
    reviewer_critiques: tuple[ReviewerCritique, ...],
    experiments: tuple[ExperimentPlan, ...],
    recommendation: Recommendation,
) -> str:
    lines: list[str] = [
        "# Research Council Report",
        "",
        "## Scope Notice",
        "",
        "No web search, network calls, LLM calls, or external evidence collection were performed. No citations are generated.",
        "",
        "## Input Summary",
        "",
        input_summary,
        "",
        "## Claims",
        "",
    ]
    for claim in claims:
        lines.append(f"- `{claim.id}` (`{claim.source_label}`, {claim.confidence}): {claim.text}")
        lines.append(f"  - Rationale: {claim.rationale}")

    lines.extend(["", "## Evidence Ledger", ""])
    for entry in evidence_ledger:
        reference = f", reference `{entry.reference_label}`" if entry.reference_label else ""
        lines.append(f"- `{entry.id}` for `{entry.claim_id}` (`{entry.evidence_type}`{reference}): {entry.summary}")
        if entry.notes:
            lines.append(f"  - Notes: {entry.notes}")

    lines.extend(["", "## Reviewer Critiques", ""])
    for critique in reviewer_critiques:
        claim_text = f" for `{critique.claim_id}`" if critique.claim_id else ""
        lines.append(f"- `{critique.id}` (`{critique.reviewer_role}`, {critique.severity}){claim_text}: {critique.finding}")
        lines.append(f"  - Suggested action: {critique.suggested_action}")

    lines.extend(["", "## Minimum Viable Experiments", ""])
    for experiment in experiments:
        joined_claims = ", ".join(f"`{claim_id}`" for claim_id in experiment.hypothesis_claim_ids)
        lines.append(f"- `{experiment.id}`: {experiment.title}")
        lines.append(f"  - Hypothesis claims: {joined_claims}")
        lines.append(f"  - Method: {experiment.method}")
        lines.append(f"  - Success metric: {experiment.success_metric}")
        lines.append(f"  - Minimum sample: {experiment.minimum_sample}")
        lines.append(f"  - Risk: {experiment.risk}")

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- Decision: `{recommendation.decision}`",
            f"- Summary: {recommendation.summary}",
            f"- Next step: {recommendation.next_step}",
            f"- Rationale: {recommendation.rationale}",
            "",
        ]
    )
    return "\n".join(lines)
