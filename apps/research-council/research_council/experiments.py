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

    if domain_profile.id == "creator_tools":
        drafts = (
            _creator_workflow_interview_experiment(input_data, claim_list, critique_list, fallback_ids),
            _creator_content_production_diary_experiment(claim_list, critique_list, fallback_ids),
            _creator_audience_growth_loop_experiment(claim_list, critique_list, fallback_ids),
            _creator_onboarding_experiment(claim_list, critique_list, fallback_ids),
            _creator_monetization_wtp_experiment(input_data, claim_list, critique_list, fallback_ids),
            _creator_content_repurposing_experiment(claim_list, critique_list, fallback_ids),
            _creator_platform_dependency_review_experiment(claim_list, critique_list, fallback_ids),
        )
        return [_to_experiment_plan(index, draft) for index, draft in enumerate(drafts, start=1)]

    if domain_profile.id == "marketplace":
        drafts = (
            _marketplace_supply_interview_experiment(input_data, claim_list, critique_list, fallback_ids),
            _marketplace_demand_interview_experiment(input_data, claim_list, critique_list, fallback_ids),
            _marketplace_concierge_matching_experiment(claim_list, critique_list, fallback_ids),
            _marketplace_liquidity_threshold_experiment(input_data, claim_list, critique_list, fallback_ids),
            _marketplace_trust_safety_review_experiment(claim_list, critique_list, fallback_ids),
            _marketplace_pricing_take_rate_experiment(claim_list, critique_list, fallback_ids),
            _marketplace_repeat_transaction_cohort_experiment(claim_list, critique_list, fallback_ids),
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

    if domain_profile.id == "enterprise_b2b":
        drafts = (
            _enterprise_procurement_interview_experiment(input_data, claim_list, critique_list, fallback_ids),
            _enterprise_security_compliance_mapping_experiment(claim_list, critique_list, fallback_ids),
            _enterprise_stakeholder_mapping_experiment(claim_list, critique_list, fallback_ids),
            _enterprise_rollout_simulation_experiment(input_data, claim_list, critique_list, fallback_ids),
            _enterprise_roi_validation_experiment(input_data, claim_list, critique_list, fallback_ids),
            _enterprise_integration_pilot_experiment(claim_list, critique_list, fallback_ids),
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


def _creator_workflow_interview_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("creator retention", "creator workflow", "content production frequency", "workflow pain"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Creator workflow interview",
        hypothesis=(
            "Creators in one segment have a frequent production workflow pain and a clear "
            "retention trigger for a dedicated creator tool."
        ),
        claim_ids=claim_ids,
        method=(
            "Interview creators about their last publishing cycle, production cadence, "
            "current workaround, audience growth loop, fan/community engagement, monetization "
            "path, onboarding friction, and what would make them keep using the tool. "
            f"Keep the decision goal in frame: {_short_goal(input_data)}."
        ),
        metric=(
            "At least three creators name the same repeated workflow pain, production frequency, "
            "and retention trigger."
        ),
        minimum_sample="3-5 creators in one creator segment.",
        estimated_time="2-4 hours",
        estimated_cost_level="free-to-low",
        stop_criteria=(
            "Stop if creators describe the workflow as rare, already solved, or not tied to "
            "audience growth, engagement, or revenue."
        ),
        decision_impact=(
            "Decide whether creator workflow fit and retention are strong enough for a prototype."
        ),
        risk="Interview interest does not prove creator retention or creator-segment WTP.",
    )


def _creator_content_production_diary_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("content production frequency", "publishing cycles", "production cadence"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Content production diary study",
        hypothesis=(
            "A creator's real production cycle exposes repeated steps where the tool can save "
            "time, improve output reuse, or increase publishing consistency."
        ),
        claim_ids=claim_ids,
        method=(
            "Ask creators to log one production cycle: idea capture, drafting, editing, "
            "content repurposing, collaboration, publishing, distribution channel, audience "
            "feedback, and follow-up work."
        ),
        metric=(
            "The diary shows a repeated production bottleneck with a measurable time, quality, "
            "or cadence improvement opportunity."
        ),
        minimum_sample="3 creators over one week or one publishing cycle.",
        estimated_time="1 week",
        estimated_cost_level="free-to-low",
        stop_criteria="Stop if production is too infrequent or idiosyncratic to support retention.",
        decision_impact=(
            "Decide whether content production frequency can support a repeat-use creator workflow."
        ),
        risk="Diary studies can find workflow pain without proving audience growth or revenue.",
    )


def _creator_audience_growth_loop_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("audience growth", "fan/community engagement", "fan community", "engagement loop"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Audience growth loop test",
        hypothesis=(
            "The creator tool can improve one audience growth or fan/community engagement loop "
            "without relying only on more content volume."
        ),
        claim_ids=claim_ids,
        method=(
            "Define one loop from content idea to distribution, audience response, fan/community "
            "engagement, learning, and next content decision. Run the tool manually or as a "
            "prototype through one cycle."
        ),
        metric=(
            "The loop produces a visible audience insight, engagement action, or next content "
            "decision that the creator would repeat."
        ),
        minimum_sample="One creator segment and one publishing channel.",
        estimated_time="2-5 hours",
        estimated_cost_level="free-to-low",
        stop_criteria="Stop if the tool cannot affect audience growth, fan engagement, or the next content decision.",
        decision_impact="Decide whether audience growth logic is real enough for product work.",
        risk="A single loop test may not predict durable audience growth.",
    )


def _creator_onboarding_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _select_claim_ids(
        claims,
        ("creator onboarding", "workflow fit", "creator workflow", "onboarding friction"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Creator onboarding test",
        hypothesis=(
            "Creators can reach first useful value quickly enough that onboarding friction does "
            "not block retention."
        ),
        claim_ids=claim_ids,
        method=(
            "Ask creators to connect or simulate their current content workflow, import an "
            "existing content asset, choose a distribution channel, and complete one useful output."
        ),
        metric="Creators reach first useful output without unclear setup, channel, or workflow steps.",
        minimum_sample="3 creators in one segment.",
        estimated_time="2-3 hours",
        estimated_cost_level="free-to-low",
        stop_criteria="Stop if creators cannot reach value without heavy handholding.",
        decision_impact="Decide whether onboarding must be narrowed before testing retention.",
        risk="Fast onboarding does not prove repeated use or monetization.",
    )


def _creator_monetization_wtp_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _select_claim_ids(
        claims,
        ("monetization", "willingness to pay", "creator segment", "sponsorship", "paid community"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Monetization willingness-to-pay interview",
        hypothesis=(
            "A specific creator segment can connect the tool to revenue, sponsorship, paid "
            "community, or another monetization path strongly enough to pay."
        ),
        claim_ids=claim_ids,
        method=(
            "Interview creators about current revenue model, audience size, sponsor or paid "
            "community workflow, pricing threshold, churn risk, and purchase trigger. "
            f"Use the goal as the decision frame: {_short_goal(input_data)}."
        ),
        metric=(
            "Creators name a monetization path, a pricing threshold, and the proof needed "
            "before paying."
        ),
        minimum_sample="3-5 creators with an active monetization path.",
        estimated_time="2-4 hours",
        estimated_cost_level="free-to-low",
        stop_criteria="Stop if the segment cannot connect the workflow to revenue or savings.",
        decision_impact="Decide whether creator-segment WTP is strong enough to continue.",
        risk="Stated willingness to pay can overstate actual conversion.",
    )


def _creator_content_repurposing_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "technical") or _select_claim_ids(
        claims,
        ("content repurposing", "collaboration workflow", "production workflow"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Content repurposing prototype",
        hypothesis=(
            "A small prototype or concierge flow can repurpose one content asset into useful "
            "channel-specific outputs with less creator effort."
        ),
        claim_ids=claim_ids,
        method=(
            "Use one creator-owned content asset and produce channel-specific variants, "
            "collaboration notes, distribution metadata, and reuse prompts. Record manual edits, "
            "creator approval, and channel constraints."
        ),
        metric=(
            "The creator accepts at least one repurposed output and names why it saves time or "
            "improves distribution."
        ),
        minimum_sample="3 content assets from one creator segment.",
        estimated_time="2-5 hours",
        estimated_cost_level="free-to-low",
        stop_criteria="Stop if outputs require as much effort as the current workflow.",
        decision_impact="Decide whether repurposing value deserves deeper product work.",
        risk="A prototype can overfit to one creator's style or channel.",
    )


def _creator_platform_dependency_review_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "safety_regulatory") or _select_claim_ids(
        claims,
        ("platform dependency", "distribution channel dependency", "audience lock-in", "audience data"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Platform dependency risk review",
        hypothesis=(
            "The creator tool can identify platform dependency, audience lock-in, data access, "
            "policy, and distribution risks before creators rely on it."
        ),
        claim_ids=claim_ids,
        method=(
            "Map each distribution channel, account dependency, audience data access, policy "
            "risk, export path, moderation concern, sponsorship disclosure need, and lock-in "
            "mitigation."
        ),
        metric="Every dependency has an owner, failure mode, mitigation, or explicit stop condition.",
        minimum_sample="One platform dependency map for the target creator workflow.",
        estimated_time="60-90 minutes",
        estimated_cost_level="free",
        stop_criteria="Stop if the product depends on an unbounded channel or inaccessible audience data.",
        decision_impact=(
            "Decide whether platform dependency is acceptable or the workflow must narrow."
        ),
        risk="A dependency review does not guarantee platform policy stability.",
    )


def _marketplace_supply_interview_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("supply-side acquisition", "seller", "provider", "liquidity"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Supply-side interview",
        hypothesis=(
            "A specific supply-side segment has enough pain, incentive, and trust in the "
            "marketplace to join before demand-side liquidity is fully proven."
        ),
        claim_ids=claim_ids,
        method=(
            "Interview likely sellers or providers using the submitted marketplace wedge "
            f"and goal `{_short_goal(input_data)}`. Record current channels, onboarding "
            "friction, quality-control concerns, and willingness to accept marketplace rules."
        ),
        metric="At least 3 supply-side participants state a concrete join trigger and current alternative.",
        minimum_sample="5 likely sellers or providers in one niche or locality",
        estimated_time="1 day",
        estimated_cost_level="low",
        stop_criteria="Stop if supply-side participants cannot name a repeated acquisition channel or join trigger.",
        decision_impact="Validates whether the supply side can be seeded without assuming instant liquidity.",
        risk="Interview interest does not prove marketplace liquidity or completed transactions.",
    )


def _marketplace_demand_interview_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("demand-side acquisition", "buyer", "customer", "matching frequency"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Demand-side interview",
        hypothesis=(
            "A specific demand-side segment has a frequent enough search or booking problem "
            "to try the marketplace instead of current alternatives."
        ),
        claim_ids=claim_ids,
        method=(
            "Interview likely buyers or customers about the last matching or booking attempt, "
            "current substitutes, trust blockers, expected response time, and repeat-use trigger."
        ),
        metric="At least 3 demand-side participants describe a recent transaction attempt and a switching trigger.",
        minimum_sample="5 likely buyers or customers in the same niche or locality",
        estimated_time="1 day",
        estimated_cost_level="low",
        stop_criteria="Stop if demand-side pain is infrequent or not tied to a transaction moment.",
        decision_impact="Validates whether demand can pull liquidity rather than only expressing casual interest.",
        risk="Demand interviews can overstate willingness to transact when supply is absent.",
    )


def _marketplace_concierge_matching_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "technical") or _select_claim_ids(
        claims,
        ("matching efficiency", "listings", "booking", "quality control"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Concierge matching test",
        hypothesis=(
            "Manual matching can produce reliable transactions with visible quality-control "
            "and trust boundaries before automated marketplace buildout."
        ),
        claim_ids=claim_ids,
        method=(
            "Manually match a small batch of supply and demand participants, tracking match "
            "time, response rate, booking friction, quality issues, and completion outcome."
        ),
        metric="At least 3 attempted matches produce a clear completion, refusal, or quality-control reason.",
        minimum_sample="5 attempted matches in one focused marketplace wedge",
        estimated_time="2 days",
        estimated_cost_level="low",
        stop_criteria="Stop if matching requires too much manual intervention or trust repair.",
        decision_impact="Tests matching efficiency and workflow fit without adding marketplace automation.",
        risk="Concierge matching may hide automation, operations, and moderation cost.",
    )


def _marketplace_liquidity_threshold_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("liquidity", "cold-start", "cold start", "local density"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Liquidity threshold test",
        hypothesis=(
            "The marketplace can name the minimum supply, demand, geography or niche density, "
            "and cold-start sequence needed for useful matches."
        ),
        claim_ids=claim_ids,
        method=(
            "Define one constrained density wedge from the submitted concept and estimate the "
            "minimum supply count, demand count, match frequency, and cold-start sequence."
        ),
        metric="The team can state a falsifiable liquidity threshold and first-side acquisition target.",
        minimum_sample="One tightly defined locality or niche with supply and demand estimates",
        estimated_time="0.5 day",
        estimated_cost_level="low",
        stop_criteria="Stop if the concept cannot constrain geography, niche, or first-side seeding.",
        decision_impact="Prevents broad marketplace buildout before liquidity and density assumptions are bounded.",
        risk="A threshold estimate still needs observed acquisition and transaction evidence.",
    )


def _marketplace_trust_safety_review_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "safety_regulatory") or _select_claim_ids(
        claims,
        ("trust and safety", "moderation", "escrow", "reputation", "fraud"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Trust/safety risk review",
        hypothesis=(
            "The marketplace can define moderation, reputation, escrow or dispute, fraud, "
            "and abuse boundaries before increasing transaction volume."
        ),
        claim_ids=claim_ids,
        method=(
            "List likely bad interactions across both sides, then mark prevention, detection, "
            "moderation owner, dispute path, and stop condition for each risk."
        ),
        metric="Every high-risk interaction has an owner, prevention check, and stop condition.",
        minimum_sample="One risk table covering both marketplace sides",
        estimated_time="0.5 day",
        estimated_cost_level="low",
        stop_criteria="Stop if trust/safety or moderation ownership cannot be named.",
        decision_impact="Keeps growth claims bounded by trust, quality, moderation, and dispute risk.",
        risk="A tabletop review does not prove real-world safety or moderation performance.",
    )


def _marketplace_pricing_take_rate_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("take-rate", "take rate", "monetization", "transaction frequency"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Pricing/take-rate test",
        hypothesis=(
            "A realistic take rate can be charged without pushing either side to transact "
            "off-platform or reducing transaction frequency."
        ),
        claim_ids=claim_ids,
        method=(
            "Present a simple transaction scenario with marketplace fee, escrow or payment "
            "rules, and value delivered; record fee acceptance and off-platform intent."
        ),
        metric="At least 3 participants accept the fee logic without preferring direct transaction.",
        minimum_sample="5 likely supply-side or demand-side participants",
        estimated_time="1 day",
        estimated_cost_level="low",
        stop_criteria="Stop if participants reject the fee or intend to bypass the marketplace.",
        decision_impact="Validates monetization and disintermediation risk before take-rate optimism.",
        risk="Stated fee acceptance may not survive real transaction context.",
    )


def _marketplace_repeat_transaction_cohort_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("repeat transactions", "transaction frequency", "retention by side", "repeat"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Repeat transaction cohort check",
        hypothesis=(
            "Both sides have a repeat transaction trigger strong enough to support retention, "
            "liquidity, and durable marketplace value."
        ),
        claim_ids=claim_ids,
        method=(
            "Track a small cohort's expected repeat transaction moments, side-specific "
            "retention trigger, and reason they would return to the marketplace."
        ),
        metric="Both sides can name a credible repeat-use trigger and next transaction condition.",
        minimum_sample="3 supply-side and 3 demand-side participants",
        estimated_time="1 day",
        estimated_cost_level="low",
        stop_criteria="Stop if one side is mostly one-time or has no reason to return.",
        decision_impact="Tests retention asymmetry before interpreting first transactions as durable liquidity.",
        risk="Cohort expectations need follow-up behavioral evidence.",
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


def _enterprise_procurement_interview_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("procurement", "budget owner", "roi proof", "long sales cycle"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Procurement interview",
        hypothesis=(
            "The enterprise buying path has a named budget owner, procurement process, "
            "approval sequence, and ROI proof requirement."
        ),
        claim_ids=claim_ids,
        method=(
            "Interview the likely product champion, economic buyer, and procurement or finance "
            "stakeholder. Record budget owner, approval steps, long-sales-cycle risk, required "
            f"ROI proof, security review dependency, and stop conditions. Keep the goal in frame: "
            f"{_short_goal(input_data)}."
        ),
        metric=(
            "The interview notes identify the buyer, budget owner, approval path, required ROI "
            "proof, and one procurement blocker."
        ),
        minimum_sample="3 stakeholders across champion, buyer, and procurement roles.",
        estimated_time="2-4 hours",
        estimated_cost_level="free-to-low",
        stop_criteria="Stop if no budget owner or procurement path can be identified.",
        decision_impact=(
            "Decide whether the opportunity has a credible buying path or should narrow to "
            "a different department, buyer, or workflow."
        ),
        risk="Procurement interviews do not prove budget approval or contract timing.",
    )


def _enterprise_security_compliance_mapping_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "safety_regulatory") or _select_claim_ids(
        claims,
        ("security/compliance", "soc2", "security review", "sso", "audit logs"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Security/compliance review mapping",
        hypothesis=(
            "The enterprise deployment can name security, compliance, SSO, audit-log, "
            "governance, data-access, and IT-approval requirements before rollout."
        ),
        claim_ids=claim_ids,
        method=(
            "Create a security/compliance map for SOC2 expectations, SSO, admin controls, "
            "audit logs, governance, data access, IT approval, and vendor-risk evidence. "
            "For each item, record owner, required evidence, unresolved blocker, and stop condition."
        ),
        metric=(
            "Every security or compliance requirement has an owner, required evidence, and "
            "clear pass/block status."
        ),
        minimum_sample="One checklist reviewed with an IT, security, or compliance stakeholder.",
        estimated_time="60-120 minutes",
        estimated_cost_level="free",
        stop_criteria="Stop if required controls or approval owners cannot be named.",
        decision_impact=(
            "Decide whether enterprise deployment can proceed to a narrow pilot or must pause "
            "for security/compliance scoping."
        ),
        risk="A review map is not a formal compliance audit or security certification.",
    )


def _enterprise_stakeholder_mapping_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("stakeholder alignment", "champion", "buyer", "department workflow"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Stakeholder mapping exercise",
        hypothesis=(
            "The champion, buyer, IT/security reviewer, procurement owner, admin, and end "
            "users can be mapped with distinct incentives and blockers."
        ),
        claim_ids=claim_ids,
        method=(
            "Map each enterprise stakeholder, decision right, approval concern, workflow impact, "
            "training need, and adoption blocker. Mark whether the champion can influence the "
            "budget owner and whether end users have a repeat workflow."
        ),
        metric=(
            "The map names champion, buyer, procurement, IT/security, admin, and user roles "
            "with one blocker and one required proof point each."
        ),
        minimum_sample="One stakeholder map reviewed with the champion or workflow owner.",
        estimated_time="60-90 minutes",
        estimated_cost_level="free",
        stop_criteria="Stop if the champion cannot name the buyer or approval path.",
        decision_impact=(
            "Decide whether stakeholder alignment is strong enough for procurement or pilot work."
        ),
        risk="A stakeholder map may miss hidden approvers or political blockers.",
    )


def _enterprise_rollout_simulation_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("rollout complexity", "onboarding", "training", "org-wide adoption"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Rollout simulation",
        hypothesis=(
            "A department can roll out the workflow without hidden onboarding, training, "
            "admin, support, or change-management burden."
        ),
        claim_ids=claim_ids,
        method=(
            "Simulate the first department rollout. List admin setup, onboarding steps, training "
            "materials, user permissions, support owner, migration tasks, and failure points. "
            f"Constraints considered: {_short_constraints(input_data)}."
        ),
        metric=(
            "The rollout plan names owner, user group, onboarding path, training burden, "
            "support responsibility, and one stop condition."
        ),
        minimum_sample="One department rollout walkthrough with the champion and one end user.",
        estimated_time="90-120 minutes",
        estimated_cost_level="free",
        stop_criteria="Stop if rollout depends on unclear owners, unbounded training, or unsupported admin work.",
        decision_impact=(
            "Decide whether org-wide adoption risk is acceptable for a controlled pilot."
        ),
        risk="A simulation does not prove full enterprise adoption or production readiness.",
    )


def _enterprise_roi_validation_experiment(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "market") or _select_claim_ids(
        claims,
        ("roi proof", "budget owner", "procurement", "long sales cycle"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="ROI validation interview",
        hypothesis=(
            "The enterprise buyer can state the ROI threshold, measurement window, and proof "
            "needed to justify procurement."
        ),
        claim_ids=claim_ids,
        method=(
            "Interview the budget owner or buyer about measurable ROI, current cost baseline, "
            "budget timing, approval threshold, acceptable pilot proof, and what would stop a "
            f"purchase. Use the goal as the decision frame: {_short_goal(input_data)}."
        ),
        metric=(
            "The buyer names a measurable ROI metric, baseline, proof threshold, and budget timing."
        ),
        minimum_sample="1-3 budget owners or economic buyers.",
        estimated_time="60-120 minutes",
        estimated_cost_level="free-to-low",
        stop_criteria="Stop if ROI cannot be measured or tied to a budget owner.",
        decision_impact=(
            "Decide whether the enterprise case has enough economic proof to continue."
        ),
        risk="A stated ROI threshold does not guarantee procurement approval.",
    )


def _enterprise_integration_pilot_experiment(
    claims: tuple[Claim, ...],
    critiques: tuple[ReviewerCritique, ...],
    fallback_ids: tuple[str, ...],
) -> _ExperimentDraft:
    claim_ids = _critique_claim_ids(critiques, "technical") or _select_claim_ids(
        claims,
        ("enterprise integration", "workflow integration depth", "deployment responsibility"),
        fallback_ids,
        limit=2,
    )
    return _ExperimentDraft(
        title="Integration pilot",
        hypothesis=(
            "The product can fit one enterprise workflow with bounded integration work, "
            "deployment responsibility, and reliability expectations."
        ),
        claim_ids=claim_ids,
        method=(
            "Pilot the smallest non-production integration path. Record systems touched, "
            "data handoffs, admin permissions, deployment owner, reliability expectation, "
            "rollback path, and workflow depth needed for value."
        ),
        metric=(
            "The pilot defines integration scope, owner, reliability threshold, rollback path, "
            "and one workflow outcome without unresolved deployment blockers."
        ),
        minimum_sample="One representative enterprise workflow or system handoff.",
        estimated_time="3-6 hours",
        estimated_cost_level="free-to-low",
        stop_criteria="Stop if value depends on broad system access, unclear ownership, or unsupported reliability.",
        decision_impact=(
            "Decide whether integration depth is realistic enough for an enterprise pilot."
        ),
        risk="A narrow pilot does not prove full enterprise deployment or procurement readiness.",
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
