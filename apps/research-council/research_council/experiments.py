"""Deterministic minimum viable experiment proposals for Research Council.

This module creates local, cheap, decision-oriented experiment plans. It does
not perform web search, network calls, LLM calls, or citation generation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from textwrap import shorten
from typing import Any

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
    *,
    domain_profile: Any = None,
) -> list[ExperimentPlan]:
    """Return deterministic, minimum viable experiment plans."""

    claim_list = tuple(claims)
    evidence_list = tuple(evidence_entries)
    critique_list = tuple(critiques)
    fallback_ids = _fallback_claim_ids(claim_list)
    domain_profile = _reasoning_profile_for(input_data, domain_profile)

    if domain_profile.id == "ai_saas":
        drafts = (
            _ai_saas_workflow_interview_experiment(input_data, claim_list, critique_list, fallback_ids),
            _ai_saas_output_quality_experiment(claim_list, critique_list, fallback_ids),
            _ai_saas_trust_boundary_experiment(input_data, claim_list, critique_list, fallback_ids),
            _ai_saas_differentiation_mapping_experiment(input_data, claim_list, critique_list, fallback_ids),
        )
        return [_to_experiment_plan(index, draft) for index, draft in enumerate(drafts, start=1)]

    if domain_profile.id == "developer_tool":
        drafts = (
            _developer_workflow_interview_experiment(input_data, claim_list, critique_list, fallback_ids),
            _developer_setup_friction_experiment(input_data, claim_list, critique_list, fallback_ids),
            _developer_integration_prototype_experiment(claim_list, critique_list, fallback_ids),
            _developer_docs_comprehension_experiment(claim_list, critique_list, fallback_ids),
            _developer_existing_tool_comparison_experiment(input_data, claim_list, critique_list, fallback_ids),
        )
        return [_to_experiment_plan(index, draft) for index, draft in enumerate(drafts, start=1)]

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
            "web search or network calls. Record whether the gap is a confidence limiter or "
            "confidence blocker before choosing the next step."
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


def _ai_saas_workflow_interview_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("founder workflow", "workflow integration", "repeat usage", "retention", "willingness"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Workflow interview",
        hypothesis=(
            "Solo founders have a frequent, painful patent-analysis workflow where a trusted "
            "automation tool could change the next decision."
        ),
        claim_ids=claim_ids,
        method=(
            "Interview target founders about their last invention-screening or prior-art search "
            "attempt. Capture current workaround, time spent, trigger event, trust blockers, "
            "integration needs, purchase-intent or willingness-to-pay threshold, and what would "
            "make them repeat the workflow. "
            f"Keep the decision goal in frame: {_short_goal(input_data)}."
        ),
        metric=(
            "At least three interviews identify the same painful workflow step, current substitute, "
            "and concrete repeat-use trigger."
        ),
        minimum_sample="3-5 solo founders or founder-like builders with recent invention-screening needs.",
        estimated_time="2-4 hours",
        estimated_cost_level="free-to-low",
        stop_criteria=(
            "Stop if participants describe patent analysis as rare, fully delegated, or not worth "
            "a paid workflow change."
        ),
        decision_impact=(
            "Decide whether adoption is strong enough to justify a prototype, or whether the "
            "target workflow, segment, or pricing logic must change."
        ),
        risk=(
            "Interview pain does not prove subscription retention or legal-output trust."
        ),
    )


def _ai_saas_output_quality_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "technical") or _select_claim_ids(
        claims,
        ("output reliability", "automation", "source traceability", "quality", "rubric"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Output-quality evaluation",
        hypothesis=(
            "A local prototype or manual concierge flow can produce useful patent-analysis outputs "
            "without unsupported claims, fake citations, or hidden uncertainty."
        ),
        claim_ids=claim_ids,
        method=(
            "Use only user-supplied invention briefs, saved prior-art notes, or offline reference "
            "snippets. Score each output for source traceability, claim-element coverage, uncertainty "
            "labels, missing-evidence flags, hallucinated citation risk, and actionability. If no "
            "local source material exists, stop at the rubric and request source material instead "
            "of inventing examples."
        ),
        metric=(
            "Every tested output links material statements to supplied inputs or marks them as "
            "missing evidence, with zero unsupported legal conclusions."
        ),
        minimum_sample="5 founder tasks or invention briefs with user-supplied offline reference material.",
        estimated_time="3-6 hours",
        estimated_cost_level="free-to-low",
        stop_criteria=(
            "Stop if outputs cannot separate source-backed summaries from uncertain analysis or "
            "if any legal conclusion appears without a verification boundary."
        ),
        decision_impact=(
            "Decide whether reliability deserves more product work before distribution or pricing tests."
        ),
        risk=(
            "A small local task set may miss production edge cases, search coverage gaps, and user data variation."
        ),
    )


def _ai_saas_trust_boundary_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "safety_regulatory") or _select_claim_ids(
        claims,
        ("legal interpretation", "trust", "verification", "professional-review", "patentability"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Trust and verification boundary check",
        hypothesis=(
            "The product can define boundaries that let founders use automation for triage "
            "without mistaking it for legal advice or verified prior-art coverage."
        ),
        claim_ids=claim_ids,
        method=(
            "Create an allowed/blocked output checklist for summaries, comparison tables, novelty "
            "signals, patentability language, infringement language, filing suggestions, and attorney "
            "review triggers. Red-team the current concept against hallucinated citations, hidden "
            "uncertainty, and overconfident legal interpretation. Constraints considered: "
            f"{_short_constraints(input_data)}."
        ),
        metric=(
            "Every high-risk output type is either blocked, downgraded to uncertainty language, "
            "or paired with a visible verification step and escalation trigger."
        ),
        minimum_sample="One boundary checklist applied to the current concept and two representative outputs.",
        estimated_time="60-90 minutes",
        estimated_cost_level="free",
        stop_criteria=(
            "Stop if the concept cannot prevent unverified legal advice, fake citations, or source-free claims."
        ),
        decision_impact=(
            "Proceed only if trust boundaries are explicit enough for a controlled prototype test."
        ),
        risk=(
            "A boundary checklist is not legal advice and does not validate compliance or patent accuracy."
        ),
    )


def _ai_saas_differentiation_mapping_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "red_team") or _select_claim_ids(
        claims,
        ("differentiated", "substitutes", "generic ai", "distribution", "manual patent search"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Differentiation mapping",
        hypothesis=(
            "The concept can identify a defensible wedge against competing workflow substitutes "
            "and a plausible distribution path for the chosen founder segment."
        ),
        claim_ids=claim_ids,
        method=(
            "Map the proposed workflow against manual patent search, patent-office databases, "
            "generic AI assistants, spreadsheets, attorney intake, and doing nothing. For each "
            "substitute, record the user's switching trigger, switching cost, integration path, "
            "trust advantage, pricing pressure, AI-wrapper risk, and distribution channel. "
            "Use the goal as the decision frame: "
            f"{_short_goal(input_data)}."
        ),
        metric=(
            "The map identifies one narrow differentiated workflow wedge, one reachable "
            "distribution path, and one substitute that should be treated as the main competitor."
        ),
        minimum_sample="One completed substitute map reviewed with at least one target founder.",
        estimated_time="60-120 minutes",
        estimated_cost_level="free",
        stop_criteria=(
            "Stop if the concept cannot name a differentiated narrow wedge beyond a generic AI wrapper."
        ),
        decision_impact=(
            "Decide whether the SaaS concept has a credible positioning path or should narrow to a "
            "more specific workflow."
        ),
        risk=(
            "A map clarifies strategy but does not create external market, patent, or competitive evidence."
        ),
    )


def _developer_workflow_interview_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("target developer", "developer workflow", "workflow pain", "repeat usage"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Developer workflow interview",
        hypothesis=(
            "A specific developer segment has recurring workflow pain that this tool can "
            "reduce without adding more process friction."
        ),
        claim_ids=claim_ids,
        method=(
            "Interview target developers about their current debugging, observability, "
            "local development, SDK, API, CLI, CI/CD, or GitHub workflow. Capture current "
            "tools, painful steps, switching cost, team versus individual adoption path, "
            "and repeat-use trigger. Keep the decision goal in frame: "
            f"{_short_goal(input_data)}."
        ),
        metric=(
            "At least three developers describe the same workflow pain, current workaround, "
            "and recurring trigger for using the tool."
        ),
        minimum_sample="3-5 developers in the target segment.",
        estimated_time="2-4 hours",
        estimated_cost_level="free-to-low",
        stop_criteria=(
            "Stop if developers see the problem as rare, already solved by existing tools, "
            "or not worth switching workflows."
        ),
        decision_impact=(
            "Decide whether the target segment and workflow are narrow enough for a setup "
            "or integration prototype."
        ),
        risk="Interview enthusiasm does not prove setup success or repeat usage.",
    )


def _developer_setup_friction_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "technical") or _select_claim_ids(
        claims,
        ("setup complexity", "integration burden", "time-to-first-value", "sdk", "cli"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Setup friction test",
        hypothesis=(
            "A target developer can install, configure, and reach first useful value "
            "without hidden setup or integration costs."
        ),
        claim_ids=claim_ids,
        method=(
            "Ask developers to follow only the current setup path and docs in their normal "
            "environment. Record installation steps, permissions, tokens, stack conflicts, "
            "error messages, time-to-first-value, and whether they can produce one useful "
            f"debugging or workflow result. Constraints considered: {_short_constraints(input_data)}."
        ),
        metric=(
            "Developers reach first useful output within the predefined time budget while "
            "recording no unresolved setup or compatibility blocker."
        ),
        minimum_sample="3 target developers using their normal local stack.",
        estimated_time="2-3 hours",
        estimated_cost_level="free-to-low",
        stop_criteria=(
            "Stop if setup needs handholding, unclear permissions, or unsupported stack assumptions."
        ),
        decision_impact=(
            "Decide whether integration friction is low enough to continue or the product "
            "must narrow to a simpler setup path."
        ),
        risk="A small setup sample may miss team security review and enterprise environments.",
    )


def _developer_integration_prototype_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "technical") or _select_claim_ids(
        claims,
        ("integration", "compatibility", "existing stack", "api", "observability"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Integration prototype",
        hypothesis=(
            "The tool can connect to one realistic developer stack without breaking existing "
            "SDK, API, CLI, logging, monitoring, or CI/CD workflows."
        ),
        claim_ids=claim_ids,
        method=(
            "Build the smallest local integration against one representative stack. Record "
            "required code changes, config, permissions, runtime assumptions, logs or traces "
            "produced, and every incompatibility with existing tools."
        ),
        metric=(
            "The prototype produces one useful debugging or observability result with a bounded "
            "setup diff and no unresolved compatibility blocker."
        ),
        minimum_sample="One representative project or local developer stack.",
        estimated_time="3-6 hours",
        estimated_cost_level="free-to-low",
        stop_criteria=(
            "Stop if integration requires broad rewrites, unsupported permissions, or fragile "
            "toolchain assumptions."
        ),
        decision_impact=(
            "Decide whether the first supported stack is credible or whether ecosystem scope "
            "must narrow."
        ),
        risk="One stack does not prove broad ecosystem compatibility.",
    )


def _developer_docs_comprehension_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("documentation", "support burden", "time-to-value", "team rollout"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Documentation comprehension test",
        hypothesis=(
            "Developers can understand setup, integration, error handling, and next steps "
            "from concise docs without support handholding."
        ),
        claim_ids=claim_ids,
        method=(
            "Give developers the current docs or readme and ask them to explain the setup "
            "path, integration assumptions, error recovery, and when they would use the tool "
            "again. Record unclear terms, missing examples, and support questions."
        ),
        metric=(
            "Developers can complete or accurately explain setup and first value with no "
            "critical documentation gaps."
        ),
        minimum_sample="3 developers reading the docs without live coaching.",
        estimated_time="60-90 minutes",
        estimated_cost_level="free",
        stop_criteria="Stop if docs hide prerequisites, permissions, or integration assumptions.",
        decision_impact=(
            "Decide whether documentation is good enough for self-serve adoption or must be "
            "rewritten before broader testing."
        ),
        risk="Docs comprehension does not prove production reliability or team approval.",
    )


def _developer_existing_tool_comparison_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "red_team") or _select_claim_ids(
        claims,
        ("existing tools", "switching cost", "ecosystem compatibility", "current tools"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Existing tool comparison",
        hypothesis=(
            "The tool has a clear reason to be used alongside or instead of existing developer "
            "tools in the target workflow."
        ),
        claim_ids=claim_ids,
        method=(
            "Compare the proposed workflow against current IDE, CLI, SDK, API, logging, "
            "monitoring, CI/CD, GitHub, and manual debugging alternatives. For each substitute, "
            "record switching cost, compatibility risk, documentation burden, and repeat-use "
            f"trigger. Use the goal as the decision frame: {_short_goal(input_data)}."
        ),
        metric=(
            "The comparison identifies one existing-tool gap, one compatibility boundary, "
            "and one repeat-use trigger that justify continued work."
        ),
        minimum_sample="One substitute map reviewed with at least one target developer.",
        estimated_time="60-120 minutes",
        estimated_cost_level="free",
        stop_criteria="Stop if existing tools already solve the workflow with lower friction.",
        decision_impact=(
            "Decide whether the product should continue, narrow to a specific integration, "
            "or stop because switching cost is too high."
        ),
        risk="A comparison map clarifies positioning but does not prove adoption.",
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


def _reasoning_profile_for(input_data: ResearchCouncilInput, domain_profile: Any) -> Any:
    if domain_profile is None:
        return domain_profile_for(input_data)
    if getattr(domain_profile, "id", "") == "medical_device":
        legacy_profile = domain_profile_for(input_data)
        if legacy_profile.id == "capsule_medical_environmental":
            return legacy_profile
    return domain_profile
