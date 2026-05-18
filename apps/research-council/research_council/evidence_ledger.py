"""Evidence ledger construction for deterministic Research Council runs.

The stable v0.1 EvidenceEntry schema supports only ``provided`` and ``missing``
as evidence_type values. This module preserves that contract and records richer
local statuses in notes as ``status=<value>``:

- provided
- assumed
- missing
- needs_external_validation
"""

from __future__ import annotations

import re
from typing import Any

from .claim_extractor import (
    EVIDENCE_GAP_CATEGORIES,
    _coerce_input,
    domain_profile_for,
    evidence_request_for,
)
from .schemas import Claim, EvidenceEntry


EVIDENCE_STATUSES = frozenset(
    {"provided", "assumed", "missing", "needs_external_validation"}
)

_STATUS_BY_SOURCE_LABEL = {
    "user_provided": "provided",
    "extracted": "missing",
    "assumed": "assumed",
    "needs_evidence": "needs_external_validation",
}

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "before",
        "but",
        "by",
        "for",
        "from",
        "if",
        "in",
        "is",
        "it",
        "of",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)

_GENERIC_EXPECTATIONS_BY_CATEGORY = {
    "technical": "feasibility evidence with a measurable threshold and failure-mode result",
    "user_adoption": "target user, problem severity, current workaround, and adoption trigger",
    "prior_art": "existing alternatives, substitute comparison, and prior-art position",
    "safety_regulatory": "safety-sensitive uses, review boundaries, and stop conditions",
    "environmental": "measured environmental behavior and whether risk shifts elsewhere",
    "market": "buyer, budget owner, willingness-to-pay signal, and adoption barrier",
}

_PROFILE_EXPECTATIONS_BY_CATEGORY = {
    "ai_saas": {
        "technical": (
            "reliability requirement: output-quality rubric, source traceability, "
            "failure handling, privacy controls, and operational reliability threshold"
        ),
        "user_adoption": (
            "target user and buyer clarity, repeated workflow frequency, current "
            "workaround, switching cost, and repeat-use trigger"
        ),
        "prior_art": (
            "differentiation beyond a generic LLM wrapper, substitute map, and narrow "
            "workflow wedge"
        ),
        "safety_regulatory": (
            "trust boundary, legal-output limits, source-check behavior, and escalation "
            "to professional review"
        ),
        "market": (
            "buyer urgency, willingness to pay, pricing threshold, distribution path, "
            "switching trigger, and retention trigger"
        ),
    },
    "medical_device": {
        "technical": (
            "intended use, target population, measured performance threshold, reliability, "
            "and non-clinical validation evidence"
        ),
        "user_adoption": (
            "clinician, patient, and institution workflow fit without treating interest "
            "as clinical validation"
        ),
        "prior_art": (
            "clinical comparator, existing device or care-pathway alternative, and "
            "evidence boundary"
        ),
        "safety_regulatory": (
            "patient safety risk, clinical validation evidence, regulatory pathway, "
            "intended use, target population, and stop conditions"
        ),
        "market": "buyer, payer, reimbursement, procurement, and adoption trigger evidence",
        "environmental": _GENERIC_EXPECTATIONS_BY_CATEGORY["environmental"],
    },
    "marketplace": {
        "technical": (
            "matching efficiency, booking/listing workflow, quality-control mechanism, "
            "reputation-system behavior, and marketplace operations evidence"
        ),
        "user_adoption": (
            "supply-side acquisition, demand-side acquisition, liquidity threshold, local "
            "or niche density, cold-start strategy, matching frequency, and retention by side"
        ),
        "prior_art": (
            "comparison against existing marketplaces, direct off-platform alternatives, "
            "manual brokers, search/listing sites, and substitute channels"
        ),
        "market": (
            "transaction frequency, repeat transaction behavior, take-rate or monetization "
            "model, disintermediation risk, and durable liquidity evidence"
        ),
        "safety_regulatory": (
            "trust/safety risk, moderation burden, fraud or abuse cases, escrow or payment "
            "dispute boundaries, review abuse, and stop conditions"
        ),
    },
    "creator_tools": {
        "technical": (
            "content repurposing value, collaboration workflow, production workflow "
            "integration, import/export needs, and platform dependency constraints"
        ),
        "user_adoption": (
            "target creator segment, content production frequency, creator workflow pain, "
            "creator onboarding friction, creator retention trigger, and publishing cadence"
        ),
        "prior_art": (
            "comparison against generic AI/content tools, existing creator platforms, "
            "content calendars, community tools, editing workflows, and distribution "
            "channel substitutes"
        ),
        "market": (
            "monetization model, sponsorship or paid community path, audience growth or "
            "engagement loop, willingness to pay by creator segment, and churn risk"
        ),
        "safety_regulatory": (
            "platform policy dependency, audience data ownership, privacy, brand safety, "
            "sponsorship disclosure, fan/community moderation, and stop conditions"
        ),
    },
    "developer_tool": {
        "technical": (
            "setup complexity, integration burden, time-to-first-value, debugging or "
            "observability value, documentation clarity, and compatibility with the "
            "developer's existing stack"
        ),
        "user_adoption": (
            "target developer segment, existing workflow pain, current workaround, "
            "individual versus team adoption path, and repeat usage trigger"
        ),
        "prior_art": (
            "comparison against existing SDKs, APIs, CLIs, logs, monitoring tools, "
            "CI/CD workflows, GitHub integrations, and manual debugging habits"
        ),
        "market": (
            "switching cost from current tools, documentation/support burden, team "
            "rollout friction, and whether value survives beyond one setup session"
        ),
        "safety_regulatory": (
            "secrets handling, production data exposure, access scopes, log leakage, "
            "and operational-risk boundaries"
        ),
    },
    "enterprise_b2b": {
        "technical": (
            "enterprise integration requirements, workflow integration depth, deployment "
            "responsibility, rollout complexity, vendor reliability expectations, and "
            "compatibility with current systems"
        ),
        "user_adoption": (
            "stakeholder alignment, champion versus buyer distinction, department workflow, "
            "onboarding/training burden, and org-wide adoption risk"
        ),
        "prior_art": (
            "comparison against current enterprise systems, internal tools, manual processes, "
            "vendor alternatives, switching cost, and migration friction"
        ),
        "market": (
            "budget owner, procurement path, purchase process, ROI proof requirement, "
            "long sales cycle, and approval steps"
        ),
        "safety_regulatory": (
            "security/compliance requirements, SOC2 expectations, SSO, admin controls, "
            "audit logs, governance, data access, and IT approval"
        ),
    },
    "capsule_medical_environmental": {
        "technical": (
            "intended use, target population, data-capture quality, safe transit, "
            "retention behavior, and non-clinical validation evidence"
        ),
        "user_adoption": (
            "patient, clinician, payer, and screening-program workflow evidence compared "
            "with existing colorectal screening pathways"
        ),
        "prior_art": (
            "clinical comparator against colonoscopy, stool tests, capsule endoscopy, "
            "and biodegradable ingestible-device alternatives"
        ),
        "safety_regulatory": (
            "patient safety risk, ingestion and obstruction hazards, biocompatibility, "
            "clinical validation evidence, regulatory pathway, intended use, target "
            "population, and stop conditions"
        ),
        "environmental": (
            "degradation timing, byproducts, wastewater compatibility, and post-discharge "
            "risk evidence"
        ),
        "market": "payer, buyer, reimbursement, procurement, and screening adoption trigger evidence",
    },
}

_VALIDATION_EXPERIMENT_BY_PROFILE_CATEGORY = {
    "ai_saas": {
        "technical": (
            "Output-quality evaluation: score outputs against reliability, source "
            "traceability, failure handling, and operational reliability rubric."
        ),
        "user_adoption": (
            "Workflow interview: interview buyer/workflow owners about current workaround, "
            "repeated workflow, switching cost, and repeat-use trigger."
        ),
        "prior_art": (
            "Differentiation mapping: map generic AI wrapper, manual workflow, and "
            "software substitutes against the narrow wedge."
        ),
        "safety_regulatory": (
            "Trust and verification boundary check: separate allowed summaries from "
            "legal advice, unsupported citations, and professional-review triggers."
        ),
        "market": (
            "Workflow interview: run pricing or purchase-intent interviews with target "
            "buyers for willingness-to-pay evidence."
        ),
    },
    "medical_device": {
        "technical": (
            "Primary evidence gap closure check: define intended use, target population, "
            "performance threshold, and non-clinical validation evidence."
        ),
        "user_adoption": (
            "Decision usefulness readout: test clinician, patient, and institution workflow "
            "requirements without implying clinical validation."
        ),
        "prior_art": (
            "Primary evidence gap closure check: compare the concept with clinical "
            "comparators, existing devices, and care pathways."
        ),
        "safety_regulatory": (
            "Safety and misuse tabletop: define patient safety risk, regulatory pathway, "
            "clinical validation boundary, and stop conditions."
        ),
        "market": "Decision usefulness readout: identify payer, buyer, and procurement evidence.",
        "environmental": (
            "Primary evidence gap closure check: define environmental evidence needed "
            "before any disposal claim."
        ),
    },
    "marketplace": {
        "technical": (
            "Concierge matching test: manually match supply and demand, then record matching "
            "speed, booking/listing friction, quality-control failures, and completion rate."
        ),
        "user_adoption": (
            "Supply-side and demand-side interviews: validate acquisition channels, cold-start "
            "wedge, liquidity threshold, local or niche density, and retention by side."
        ),
        "prior_art": (
            "Existing marketplace and off-platform comparison: compare marketplace alternatives, "
            "manual brokers, listing sites, direct transactions, substitutes, and switching triggers."
        ),
        "market": (
            "Pricing/take-rate test: validate transaction frequency, repeat transactions, "
            "monetization, and disintermediation risk."
        ),
        "safety_regulatory": (
            "Trust/safety risk review: map moderation burden, escrow or dispute boundaries, "
            "fraud or abuse cases, review abuse, and stop conditions."
        ),
    },
    "creator_tools": {
        "technical": (
            "Content repurposing prototype: test one creator workflow for repurposing, "
            "collaboration handoffs, import/export needs, and platform constraints."
        ),
        "user_adoption": (
            "Creator workflow interview: interview creators about production cadence, "
            "workflow pain, onboarding friction, and retention trigger."
        ),
        "prior_art": (
            "Creator differentiation mapping: compare against generic AI/content tools, "
            "creator platforms, content calendars, community tools, editing workflows, "
            "and distribution channel substitutes."
        ),
        "market": (
            "Monetization willingness-to-pay interview: validate monetization path, "
            "audience growth loop, and WTP by creator segment."
        ),
        "safety_regulatory": (
            "Platform dependency risk review: map platform policy dependency, audience "
            "data ownership, disclosure, moderation, and audience lock-in risks."
        ),
    },
    "developer_tool": {
        "technical": (
            "Setup friction test: measure installation, configuration, permissions, "
            "integration burden, compatibility, and time-to-first-value in a real "
            "developer stack."
        ),
        "user_adoption": (
            "Developer workflow interview: interview target developers about current "
            "workflow pain, existing tools, switching cost, and repeat usage trigger."
        ),
        "prior_art": (
            "Existing tool comparison: compare against current SDK, CLI, logs, "
            "monitoring, CI/CD, GitHub, and manual debugging workflows."
        ),
        "market": (
            "Documentation comprehension test: ask developers to complete setup and "
            "integration from docs while recording support burden and team rollout friction."
        ),
        "safety_regulatory": (
            "Operational boundary check: define secrets, production data, access scopes, "
            "log exposure, and safe integration boundaries."
        ),
    },
    "enterprise_b2b": {
        "technical": (
            "Integration pilot: test one realistic enterprise integration path, deployment "
            "owner, workflow depth, reliability expectation, and rollout dependency."
        ),
        "user_adoption": (
            "Stakeholder mapping exercise: map champion, buyer, IT/security, procurement, "
            "department users, onboarding burden, and org-wide adoption risk."
        ),
        "prior_art": (
            "Switching-cost comparison: compare against current enterprise systems, internal "
            "tools, manual process, vendor alternatives, and migration friction."
        ),
        "market": (
            "Procurement interview: validate budget owner, buying process, approval steps, "
            "long sales cycle, and ROI proof requirement."
        ),
        "safety_regulatory": (
            "Security/compliance review mapping: define SOC2, SSO, audit logs, governance, "
            "data access, IT approval, and compliance blockers."
        ),
    },
    "capsule_medical_environmental": {
        "technical": (
            "Bench capsule sensing and transit mockup: test data capture, orientation, "
            "occlusion, transit, and safe-passage assumptions."
        ),
        "user_adoption": (
            "Care-pathway adoption check: compare patient, clinician, payer, and screening "
            "program requirements."
        ),
        "prior_art": (
            "Primary evidence gap closure check: compare against clinical comparators, "
            "capsule endoscopy, colorectal screening workflows, and biodegradable devices."
        ),
        "safety_regulatory": (
            "Non-clinical capsule safety boundary table: define intended use, target "
            "population, patient safety risk, regulatory pathway, and clinical validation "
            "boundary."
        ),
        "environmental": (
            "Wastewater degradation screen: measure degradation timing, byproducts, "
            "fragments, and wastewater compatibility."
        ),
        "market": "Care-pathway adoption check: identify payer, buyer, reimbursement, and adoption triggers.",
    },
}

_GENERIC_VALIDATION_EXPERIMENT_BY_CATEGORY = {
    "technical": "Primary evidence gap closure check: define the smallest feasible validation result.",
    "user_adoption": "Decision usefulness readout: test target user, problem severity, and adoption trigger.",
    "prior_art": "Primary evidence gap closure check: compare existing alternatives and substitutes.",
    "safety_regulatory": "Safety and misuse tabletop: define review boundaries and stop conditions.",
    "environmental": "Primary evidence gap closure check: define measurable environmental evidence.",
    "market": "Decision usefulness readout: identify buyer, budget owner, and willingness-to-pay evidence.",
}

_GENERIC_REASONING_TRACE_BY_CATEGORY = {
    "technical": (
        "Mechanism threshold unsupported",
        "Prototype evidence missing",
    ),
    "user_adoption": (
        "Target user unclear",
        "Problem severity unsupported",
        "Adoption evidence missing",
    ),
    "prior_art": (
        "Substitute comparison missing",
        "Prior-art position unsupported",
    ),
    "safety_regulatory": (
        "Safety boundary unclear",
        "Review condition unsupported",
    ),
    "environmental": (
        "Environmental measurement missing",
        "Lifecycle risk unresolved",
    ),
    "market": (
        "Buyer unclear",
        "Willingness-to-pay evidence missing",
    ),
}

_PROFILE_REASONING_TRACE_BY_CATEGORY = {
    "ai_saas": {
        "technical": (
            "Output reliability evidence missing",
            "Source traceability not demonstrated",
            "Failure handling unsupported",
        ),
        "user_adoption": (
            "No buyer/workflow owner identified",
            "No repeated workflow evidence detected",
            "Retention trigger unsupported",
            "Workflow interview required before medium confidence",
        ),
        "prior_art": (
            "Differentiation beyond generic AI wrapper unclear",
            "Narrow workflow wedge unsupported",
            "Substitute map missing",
        ),
        "safety_regulatory": (
            "Legal-output boundary unsupported",
            "Professional-review trigger not defined",
            "Unsupported citation risk unresolved",
        ),
        "market": (
            "No buyer identified",
            "Willingness-to-pay evidence missing",
            "Retention trigger unsupported",
        ),
    },
    "medical_device": {
        "technical": (
            "Intended use not bounded",
            "Performance threshold unsupported",
            "Non-clinical validation evidence missing",
        ),
        "user_adoption": (
            "Clinical workflow fit unsupported",
            "Patient and clinician adoption evidence missing",
        ),
        "prior_art": (
            "Clinical comparator missing",
            "Care-pathway alternative unclear",
        ),
        "safety_regulatory": (
            "Intended use not bounded",
            "Clinical validation evidence missing",
            "Regulatory pathway unclear",
            "Patient safety risk unresolved",
        ),
        "market": (
            "Payer or buyer unclear",
            "Reimbursement path unsupported",
        ),
        "environmental": (
            "Environmental disposal evidence missing",
            "Waste-path risk unresolved",
        ),
    },
    "marketplace": {
        "technical": (
            "Matching efficiency evidence missing",
            "Booking/listing workflow untested",
            "Quality-control mechanism unsupported",
            "Reputation system behavior unproven",
        ),
        "user_adoption": (
            "Liquidity threshold unsupported",
            "Cold-start strategy unclear",
            "Supply-side acquisition evidence missing",
            "Demand-side acquisition evidence missing",
            "Retention by side unsupported",
        ),
        "prior_art": (
            "Marketplace substitute map missing",
            "Direct off-platform alternative unclear",
            "Existing marketplace comparison unsupported",
        ),
        "market": (
            "Transaction frequency evidence missing",
            "Take-rate monetization unproven",
            "Disintermediation risk unresolved",
            "Repeat transaction behavior unsupported",
        ),
        "safety_regulatory": (
            "Trust/safety risk unresolved",
            "Moderation burden unknown",
            "Escrow or dispute boundary unclear",
            "Review or reputation abuse risk unsupported",
        ),
    },
    "creator_tools": {
        "technical": (
            "Content repurposing value unproven",
            "Collaboration workflow untested",
            "Platform dependency constraints unsupported",
        ),
        "user_adoption": (
            "Target creator segment unclear",
            "Content production frequency evidence missing",
            "Creator workflow pain unsupported",
            "Creator retention trigger unsupported",
            "Creator onboarding friction untested",
        ),
        "prior_art": (
            "Creator differentiation from generic AI/content tools unclear",
            "Creator platform substitute map missing",
            "Distribution channel alternative unclear",
        ),
        "market": (
            "Monetization model unproven",
            "Audience growth loop unsupported",
            "Fan/community engagement evidence missing",
            "Willingness to pay by creator segment missing",
            "Creator churn risk unresolved",
        ),
        "safety_regulatory": (
            "Platform policy dependency unresolved",
            "Audience data ownership unclear",
            "Fan/community moderation boundary unsupported",
            "Brand safety or sponsorship disclosure risk unresolved",
        ),
    },
    "developer_tool": {
        "technical": (
            "Setup complexity evidence missing",
            "Integration burden not measured",
            "Time-to-first-value unsupported",
            "Ecosystem compatibility not demonstrated",
            "Debugging or observability value unproven",
        ),
        "user_adoption": (
            "Target developer segment unclear",
            "Existing workflow pain unsupported",
            "Individual versus team adoption path unclear",
            "Repeat usage trigger unsupported",
        ),
        "prior_art": (
            "Existing developer tool comparison missing",
            "Switching cost from current tools unsupported",
            "Stack compatibility alternatives unclear",
        ),
        "market": (
            "Documentation burden unsupported",
            "Support burden unclear",
            "Team rollout friction untested",
        ),
        "safety_regulatory": (
            "Secrets and access-scope boundary unclear",
            "Production data or log exposure risk unresolved",
        ),
    },
    "enterprise_b2b": {
        "technical": (
            "Enterprise integration requirements unmeasured",
            "Workflow integration depth unsupported",
            "Deployment responsibility unclear",
            "Vendor reliability expectation unproven",
        ),
        "user_adoption": (
            "Stakeholder alignment unclear",
            "Champion versus buyer distinction missing",
            "Onboarding/training burden unknown",
            "Org-wide adoption risk unresolved",
        ),
        "prior_art": (
            "Switching cost from current systems unsupported",
            "Enterprise substitute map missing",
            "Migration friction unclear",
        ),
        "market": (
            "Budget owner unidentified",
            "Procurement path unclear",
            "ROI proof missing",
            "Long sales cycle risk unresolved",
        ),
        "safety_regulatory": (
            "Security/compliance requirements unknown",
            "SOC2 or security review path not mapped",
            "SSO, audit logs, governance, and IT approval unproven",
        ),
    },
    "capsule_medical_environmental": {
        "technical": (
            "Intended use not bounded",
            "Capsule sensing evidence missing",
            "Safe transit evidence missing",
        ),
        "user_adoption": (
            "Care-pathway workflow fit unsupported",
            "Patient and clinician adoption evidence missing",
        ),
        "prior_art": (
            "Clinical comparator missing",
            "Capsule-device alternative unclear",
        ),
        "safety_regulatory": (
            "Intended use not bounded",
            "Clinical validation evidence missing",
            "Regulatory pathway unclear",
            "Patient safety risk unresolved",
        ),
        "environmental": (
            "Degradation timing unsupported",
            "Wastewater byproduct risk unresolved",
        ),
        "market": (
            "Payer or buyer unclear",
            "Screening adoption trigger unsupported",
        ),
    },
}

_TRACE_SEVERITY_BY_CONFIDENCE_IMPACT = {
    "confidence_blocker": "high",
    "confidence_limiter": "medium",
    "confidence_supporting": "low",
}


def build_evidence_ledger(
    input_data: Any,
    claims: list[Claim] | tuple[Claim, ...],
    *,
    domain_profile: Any = None,
) -> list[EvidenceEntry]:
    """Build schema-compatible evidence entries for every claim.

    The ledger never invents citations. User-supplied text is labeled as local
    input or provided evidence, while unsupported truth claims are marked as
    missing, assumed, or needing external validation in the entry notes.
    """

    input_view = _coerce_input(input_data)
    domain_profile = _reasoning_profile_for(input_data, domain_profile)
    claim_list = list(claims)
    entries: list[EvidenceEntry] = []

    for claim in claim_list:
        status = _STATUS_BY_SOURCE_LABEL.get(claim.source_label, "missing")
        gap_category = _gap_category_for_claim(claim)
        required_evidence = _required_evidence_for_claim(
            domain_profile,
            claim,
            gap_category,
        )
        missing_evidence = _missing_evidence_for_claim(
            claim,
            status,
            gap_category,
            required_evidence,
        )
        validation_experiment = _validation_experiment_for_gap(
            domain_profile,
            gap_category,
        )
        confidence_impact = _confidence_impact_for_gap(
            domain_profile,
            claim,
            status,
            gap_category,
        )
        reasoning_trace = _reasoning_trace_for_entry(
            domain_profile,
            claim,
            status,
            gap_category,
            confidence_impact,
        )
        entries.append(
            _primary_entry_for_claim(
                sequence_number=len(entries) + 1,
                claim=claim,
                status=status,
                raw_idea=input_view.raw_idea,
                goal=input_view.goal,
                gap_category=gap_category,
                required_evidence=required_evidence,
                missing_evidence=missing_evidence,
                validation_experiment=validation_experiment,
                confidence_impact=confidence_impact,
                reasoning_trace=reasoning_trace,
                trace_category=_trace_category_for_entry(status, gap_category),
                trace_severity=_trace_severity_for_impact(confidence_impact),
            )
        )

    for evidence_text in input_view.provided_evidence:
        target_claim = _best_claim_for_evidence(evidence_text, claim_list)
        if target_claim is None:
            continue
        entries.append(
            EvidenceEntry(
                id=f"evidence-{len(entries) + 1:03d}",
                claim_id=target_claim.id,
                evidence_type="provided",
                summary=(
                    "User-provided local support: "
                    f"{_shorten(evidence_text)}"
                ),
                reference_label=f"provided_evidence:{len(entries) + 1:03d}",
                notes=(
                    "status=provided; source=user_supplied; support_scope=local_input_only; "
                    "this may clarify the submitted concept but is not external validation."
                ),
                required_evidence="User-provided local evidence tied to the closest claim.",
                missing_evidence="",
                validation_experiment="",
                confidence_impact="confidence_supporting",
                reasoning_trace=_provided_reasoning_trace(domain_profile),
                trace_category="local_support",
                trace_severity="low",
            )
        )

    return entries


def evidence_status(entry: EvidenceEntry) -> str:
    """Return the richer local evidence status recorded in an entry's notes."""

    match = re.search(r"\bstatus=([a-z_]+)\b", entry.notes)
    if match and match.group(1) in EVIDENCE_STATUSES:
        return match.group(1)
    return entry.evidence_type


def evidence_gap_category(entry: EvidenceEntry) -> str | None:
    """Return the deterministic evidence-gap category recorded in entry notes."""

    match = re.search(r"\bgap_category=([a-z_]+)\b", entry.notes)
    if match and match.group(1) in EVIDENCE_GAP_CATEGORIES:
        return match.group(1)
    return None


def evidence_confidence_impact(entry: EvidenceEntry) -> str:
    """Return the deterministic confidence impact for an evidence entry."""

    if entry.confidence_impact:
        return entry.confidence_impact
    match = re.search(r"\bconfidence_impact=([a-z_]+)\b", entry.notes)
    if match:
        return match.group(1)
    return "confidence_supporting" if entry.evidence_type == "provided" else "confidence_limiter"


def _primary_entry_for_claim(
    sequence_number: int,
    claim: Claim,
    status: str,
    raw_idea: str,
    goal: str,
    gap_category: str,
    required_evidence: str,
    missing_evidence: str,
    validation_experiment: str,
    confidence_impact: str,
    reasoning_trace: tuple[str, ...],
    trace_category: str,
    trace_severity: str,
) -> EvidenceEntry:
    if status == "provided":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="provided",
            summary=(
                "The user supplied the concept and goal being evaluated: "
                f"idea={_shorten(raw_idea)}; goal={_shorten(goal)}"
            ),
            reference_label="user_input",
            notes=(
                "status=provided; source=user_input; support_scope=concept_description_only; "
                "this does not validate feasibility, adoption, safety, environmental, "
                "prior-art, or market claims."
            ),
            required_evidence="User-provided concept and goal text.",
            missing_evidence="",
            validation_experiment="",
            confidence_impact="confidence_supporting",
            reasoning_trace=reasoning_trace,
            trace_category=trace_category,
            trace_severity=trace_severity,
        )

    if status == "assumed":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="missing",
            summary=(
                f"Assumption needs {gap_category.replace('_', ' ')} evidence: "
                f"{required_evidence} Validation experiment: {validation_experiment}. "
                f"Confidence impact: {confidence_impact}."
            ),
            notes=(
                f"status=assumed; gap_category={gap_category}; "
                f"missing_evidence={missing_evidence}; "
                f"validation_experiment={validation_experiment}; "
                f"confidence_impact={confidence_impact}"
            ),
            required_evidence=required_evidence,
            missing_evidence=missing_evidence,
            validation_experiment=validation_experiment,
            confidence_impact=confidence_impact,
            reasoning_trace=reasoning_trace,
            trace_category=trace_category,
            trace_severity=trace_severity,
        )

    if status == "needs_external_validation":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="missing",
            summary=(
                f"Needs {gap_category.replace('_', ' ')} evidence before support: "
                f"{required_evidence} Validation experiment: {validation_experiment}. "
                f"Confidence impact: {confidence_impact}."
            ),
            notes=(
                f"status=needs_external_validation; gap_category={gap_category}; "
                f"missing_evidence={missing_evidence}; "
                f"validation_experiment={validation_experiment}; "
                f"confidence_impact={confidence_impact}"
            ),
            required_evidence=required_evidence,
            missing_evidence=missing_evidence,
            validation_experiment=validation_experiment,
            confidence_impact=confidence_impact,
            reasoning_trace=reasoning_trace,
            trace_category=trace_category,
            trace_severity=trace_severity,
        )

    return EvidenceEntry(
        id=f"evidence-{sequence_number:03d}",
        claim_id=claim.id,
        evidence_type="missing",
        summary=(
            f"Missing {gap_category.replace('_', ' ')} evidence: {required_evidence} "
            f"Validation experiment: {validation_experiment}. "
            f"Confidence impact: {confidence_impact}."
        ),
        notes=(
            f"status=missing; gap_category={gap_category}; "
            f"missing_evidence={missing_evidence}; "
            f"validation_experiment={validation_experiment}; "
            f"confidence_impact={confidence_impact}"
        ),
        required_evidence=required_evidence,
        missing_evidence=missing_evidence,
        validation_experiment=validation_experiment,
        confidence_impact=confidence_impact,
        reasoning_trace=reasoning_trace,
        trace_category=trace_category,
        trace_severity=trace_severity,
    )


def _required_evidence_for_claim(
    domain_profile: Any,
    claim: Claim,
    gap_category: str,
) -> str:
    base_request = evidence_request_for(domain_profile, gap_category)
    expectation = _profile_expectation_for_gap(domain_profile, gap_category)
    if expectation and expectation.lower() not in base_request.lower():
        return f"{base_request} Profile expectation: {expectation}."
    return base_request


def _missing_evidence_for_claim(
    claim: Claim,
    status: str,
    gap_category: str,
    required_evidence: str,
) -> str:
    if status == "provided":
        return ""
    if status == "assumed":
        prefix = "Assumption is not yet supported by supplied evidence"
    elif status == "needs_external_validation":
        prefix = "External validation is required before support"
    else:
        prefix = "Missing support for the claim"
    return (
        f"{prefix}: {required_evidence} "
        f"Claim `{claim.id}` remains a {gap_category.replace('_', ' ')} evidence gap."
    )


def _profile_expectation_for_gap(domain_profile: Any, gap_category: str) -> str:
    profile_id = _profile_id(domain_profile)
    profile_expectations = _PROFILE_EXPECTATIONS_BY_CATEGORY.get(profile_id, {})
    if gap_category in profile_expectations:
        return profile_expectations[gap_category]
    return _GENERIC_EXPECTATIONS_BY_CATEGORY.get(gap_category, "")


def _validation_experiment_for_gap(domain_profile: Any, gap_category: str) -> str:
    profile_id = _profile_id(domain_profile)
    profile_experiments = _VALIDATION_EXPERIMENT_BY_PROFILE_CATEGORY.get(profile_id, {})
    if gap_category in profile_experiments:
        return profile_experiments[gap_category]
    return _GENERIC_VALIDATION_EXPERIMENT_BY_CATEGORY.get(
        gap_category,
        "Primary evidence gap closure check: define one falsifiable validation step.",
    )


def _confidence_impact_for_gap(
    domain_profile: Any,
    claim: Claim,
    status: str,
    gap_category: str,
) -> str:
    if status == "provided":
        return "confidence_supporting"
    profile_id = _profile_id(domain_profile)
    if profile_id in {"medical_device", "capsule_medical_environmental"} and gap_category in {
        "safety_regulatory",
        "technical",
    }:
        return "confidence_blocker"
    if status == "needs_external_validation":
        return "confidence_blocker"
    blocker_order = tuple(getattr(domain_profile, "blocker_order", ()))
    if gap_category in blocker_order[:2]:
        return "confidence_blocker"
    if claim.confidence == "low":
        return "confidence_limiter"
    return "confidence_limiter"


def _reasoning_trace_for_entry(
    domain_profile: Any,
    claim: Claim,
    status: str,
    gap_category: str,
    confidence_impact: str,
) -> tuple[str, ...]:
    if status == "provided":
        return _provided_reasoning_trace(domain_profile)

    trace: list[str] = []
    profile_id = _profile_id(domain_profile)
    profile_traces = _PROFILE_REASONING_TRACE_BY_CATEGORY.get(profile_id, {})
    trace.extend(profile_traces.get(gap_category, ()))
    trace.extend(_GENERIC_REASONING_TRACE_BY_CATEGORY.get(gap_category, ()))
    trace.append(_status_reasoning_trace(status))
    trace.append(_confidence_reasoning_trace(confidence_impact, gap_category))
    if claim.confidence == "low" and confidence_impact != "confidence_blocker":
        trace.append("Low claim confidence limits confidence upgrade")
    return _dedupe_trace(trace)


def _provided_reasoning_trace(domain_profile: Any) -> tuple[str, ...]:
    profile_id = _profile_id(domain_profile)
    if profile_id == "ai_saas":
        return (
            "Supporting evidence: local input frames the AI SaaS workflow",
            "Confidence supporting: local input does not validate buyer workflow",
        )
    if profile_id == "developer_tool":
        return (
            "Supporting evidence: local input frames the developer-tool workflow",
            "Confidence supporting: local input does not validate setup friction or integration burden",
        )
    if profile_id == "marketplace":
        return (
            "Supporting evidence: local input frames the marketplace structure",
            "Confidence supporting: local input does not validate liquidity, supply, demand, or trust/safety",
        )
    if profile_id == "creator_tools":
        return (
            "Supporting evidence: local input frames the creator-tool workflow",
            "Confidence supporting: local input does not validate creator retention, audience growth, or monetization",
        )
    if profile_id == "enterprise_b2b":
        return (
            "Supporting evidence: local input frames the enterprise B2B workflow",
            "Confidence supporting: local input does not validate procurement path or security/compliance requirements",
        )
    if profile_id in {"medical_device", "capsule_medical_environmental"}:
        return (
            "Supporting evidence: local input frames the medical-device concept",
            "Confidence supporting: local input does not validate patient safety",
        )
    return (
        "Supporting evidence: local input defines the concept",
        "Confidence supporting: local input does not validate external claims",
    )


def _status_reasoning_trace(status: str) -> str:
    if status == "assumed":
        return "Assumption requires evidence before confidence upgrade"
    if status == "needs_external_validation":
        return "External validation required before confidence upgrade"
    return "Missing evidence requires validation before confidence upgrade"


def _confidence_reasoning_trace(confidence_impact: str, gap_category: str) -> str:
    category = gap_category.replace("_", " ")
    if confidence_impact == "confidence_blocker":
        return f"Confidence blocker: unresolved {category} evidence blocks upgrade"
    if confidence_impact == "confidence_limiter":
        return f"Confidence limiter: unresolved {category} evidence caps confidence"
    return f"Confidence supporting: {category} evidence supports local framing"


def _trace_category_for_entry(status: str, gap_category: str) -> str:
    if status == "provided":
        return "local_support"
    return gap_category


def _trace_severity_for_impact(confidence_impact: str) -> str:
    return _TRACE_SEVERITY_BY_CONFIDENCE_IMPACT.get(confidence_impact, "medium")


def _dedupe_trace(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value)).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)
    return tuple(deduped)


def _gap_category_for_claim(claim: Claim) -> str:
    text = f"{claim.text} {claim.rationale}".lower()
    if _contains_any(
        text,
        (
            "prior-art position",
            "prior art position",
            "novelty and prior-art",
            "differentiated from",
            "patent-office",
            "manual patent search",
            "existing products",
            "substitutes",
            "existing developer tools",
            "existing tool comparison",
            "current tools",
            "ecosystem compatibility",
            "stack compatibility",
            "switching cost",
            "current enterprise systems",
            "internal tools",
            "vendor alternatives",
            "migration friction",
            "existing marketplaces",
            "manual brokers",
            "search/listing sites",
            "substitute channels",
            "generic ai/content tools",
            "generic content tools",
            "existing creator platforms",
            "creator platforms",
            "content calendars",
            "community tools",
            "editing workflows",
            "distribution channel substitutes",
        ),
    ):
        return "prior_art"
    if _contains_any(
        text, ("wastewater", "biodegradable", "degradation", "environment", "discharge")
    ):
        return "environmental"
    if _contains_any(
        text,
        (
            "procurement path",
            "roi proof",
            "long sales cycle",
            "purchase process",
            "budget timing",
        ),
    ):
        return "market"
    if _contains_any(
        text,
        (
            "safety",
            "regulatory",
            "medical-device",
            "ingestion",
            "obstruction",
            "biocompatibility",
            "sanitation",
            "diagnostic-quality",
            "clinical oversight",
            "human use",
            "approval",
            "legal interpretation",
            "patentability",
            "infringement",
            "freedom-to-operate",
            "legal strategy",
            "trust",
            "trust and safety",
            "trust/safety",
            "moderation",
            "escrow",
            "payment dispute",
            "fraud",
            "abuse",
            "review abuse",
            "reputation system",
            "verification boundaries",
            "professional-review",
            "hallucinated",
            "security/compliance",
            "compliance",
            "security review",
            "soc2",
            "sso",
            "audit logs",
            "governance",
            "data access",
            "it approval",
            "admin controls",
            "platform policy",
            "platform dependency",
            "audience data",
            "brand safety",
            "sponsorship disclosure",
            "fan/community moderation",
        ),
    ):
        return "safety_regulatory"
    if _contains_any(
        text,
        (
            "target developer segment",
            "developer adoption",
            "developer workflow",
            "workflow pain",
            "individual versus team adoption",
            "team adoption",
            "repeat usage trigger",
            "stakeholder alignment",
            "champion versus buyer",
            "department workflow",
            "onboarding/training burden",
            "onboarding and training burden",
            "org-wide adoption",
            "liquidity",
            "cold-start",
            "cold start",
            "chicken-and-egg",
            "supply-side acquisition",
            "demand-side acquisition",
            "local density",
            "niche density",
            "matching frequency",
            "retention by side",
            "target creator segment",
            "creator retention",
            "content production frequency",
            "creator workflow pain",
            "creator workflow",
            "publishing cadence",
            "audience growth loop",
            "fan/community engagement",
            "fan community",
            "creator onboarding",
            "creator churn",
        ),
    ):
        return "user_adoption"
    if _contains_any(
        text,
        (
            "technical",
            "feasibility",
            "implementation",
            "prototype",
            "sensing",
            "power",
            "manufacturing",
            "experimentable",
            "automation",
            "output reliability",
            "quality checks",
            "source traceability",
            "error labels",
            "rubric",
            "setup complexity",
            "integration burden",
            "integration cost",
            "integration prototype",
            "time-to-first-value",
            "time-to-first value",
            "sdk",
            "api",
            "debugging",
            "observability",
            "logs",
            "monitoring",
            "compatibility",
            "documentation",
            "enterprise integration requirements",
            "workflow integration depth",
            "deployment responsibility",
            "vendor reliability",
            "rollout complexity",
            "enterprise integration",
            "matching efficiency",
            "booking flow",
            "listing workflow",
            "listings",
            "booking/listing workflow",
            "quality-control",
            "quality control",
            "marketplace operations",
            "content repurposing",
            "collaboration workflow",
            "production workflow integration",
            "import/export",
        ),
    ):
        return "technical"
    if _contains_any(
        text,
        (
            "buyer",
            "payer",
            "willingness to pay",
            "pricing",
            "distribution",
            "channel access",
            "market includes",
            "commercial audience",
            "budget owner",
            "procurement path",
            "procurement",
            "roi proof",
            "long sales cycle",
            "approval steps",
            "budget timing",
            "purchase process",
            "transaction frequency",
            "take-rate",
            "take rate",
            "monetization",
            "disintermediation",
            "repeat transactions",
            "monetization model",
            "sponsorship",
            "paid community",
            "creator revenue",
            "creator segment",
            "creator-segment",
            "willingness to pay by creator",
        ),
    ):
        return "market"
    if _contains_any(
        text,
        (
            "user need",
            "adoption",
            "clinician",
            "patient adoption",
            "demand",
            "workflow fit",
            "avoidance",
            "founder workflow",
            "workflow integration",
            "repeat usage",
            "retention",
            "current-workaround",
            "solo developers",
            "time savings",
            "target developer",
            "developer segment",
            "developer workflow",
            "existing workflow pain",
            "team adoption",
            "stakeholder alignment",
            "champion",
            "buyer distinction",
            "onboarding",
            "training",
            "org-wide adoption",
            "department workflow",
            "supply-side",
            "demand-side",
            "supply and demand",
            "sellers",
            "providers",
            "customers",
            "marketplace liquidity",
            "cold-start",
            "cold start",
            "local density",
            "niche density",
            "retention by side",
            "creator retention",
            "content production frequency",
            "creator workflow",
            "audience growth",
            "fan engagement",
            "community engagement",
            "creator onboarding",
        ),
    ):
        return "user_adoption"
    if _contains_any(text, ("market", "commercial")):
        return "market"
    if _contains_any(
        text,
        ("prior-art", "patents", "comparison", "differentiated", "differentiation", "generic ai"),
    ):
        return "prior_art"
    if claim.source_label == "assumed":
        return "user_adoption"
    return "technical"


def _reasoning_profile_for(input_data: Any, domain_profile: Any) -> Any:
    if domain_profile is None:
        return domain_profile_for(input_data)
    if _profile_id(domain_profile) == "medical_device":
        legacy_profile = domain_profile_for(input_data)
        if legacy_profile.id == "capsule_medical_environmental":
            return legacy_profile
    return domain_profile


def _profile_id(profile: Any) -> str:
    return str(getattr(profile, "id", "") or "").strip().lower()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _best_claim_for_evidence(evidence_text: str, claims: list[Claim]) -> Claim | None:
    if not claims:
        return None

    evidence_tokens = _tokens(evidence_text)
    if not evidence_tokens:
        return claims[0]

    best_claim = claims[0]
    best_score = -1
    for claim in claims:
        claim_tokens = _tokens(f"{claim.text} {claim.rationale}")
        score = len(evidence_tokens & claim_tokens)
        if score > best_score:
            best_claim = claim
            best_score = score
    return best_claim


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[0-9A-Za-z\uAC00-\uD7A3]+", text.lower())
        if len(token) > 1 and token not in _STOPWORDS
    }


def _shorten(text: str, limit: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", str(text)).strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}..."
