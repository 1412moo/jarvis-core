"""Deterministic domain profiles for Research Council.

This module is a data-layer foundation only. It does not call LLMs, perform
network work, mutate pipeline behavior, or change report output.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any, Literal


SelectionReason = Literal["explicit", "deterministic_score", "fallback"]
WeightedKeyword = tuple[str, int]


@dataclass(frozen=True)
class ClaimLens:
    """A deterministic lens for claim extraction and review planning."""

    id: str
    label: str
    focus: str
    keywords: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty("ClaimLens.id", self.id)
        _require_non_empty("ClaimLens.label", self.label)
        _require_non_empty("ClaimLens.focus", self.focus)
        object.__setattr__(self, "keywords", _tuple_of_strings(self.keywords))


@dataclass(frozen=True)
class EvidenceNeed:
    """A deterministic evidence requirement for a domain profile."""

    category: str
    request: str
    rationale: str = ""

    def __post_init__(self) -> None:
        _require_non_empty("EvidenceNeed.category", self.category)
        _require_non_empty("EvidenceNeed.request", self.request)
        object.__setattr__(self, "rationale", _clean_text(self.rationale))


@dataclass(frozen=True)
class ReviewerLens:
    """A reviewer perspective that should be emphasized for a domain."""

    role: str
    focus: str
    escalation_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty("ReviewerLens.role", self.role)
        _require_non_empty("ReviewerLens.focus", self.focus)
        object.__setattr__(
            self,
            "escalation_terms",
            _tuple_of_strings(self.escalation_terms),
        )


@dataclass(frozen=True)
class ExperimentTemplate:
    """A reusable minimum-viable experiment template for a profile."""

    id: str
    title: str
    method: str
    success_metric: str
    minimum_sample: str
    risk: str

    def __post_init__(self) -> None:
        _require_non_empty("ExperimentTemplate.id", self.id)
        _require_non_empty("ExperimentTemplate.title", self.title)
        _require_non_empty("ExperimentTemplate.method", self.method)
        _require_non_empty("ExperimentTemplate.success_metric", self.success_metric)
        _require_non_empty("ExperimentTemplate.minimum_sample", self.minimum_sample)
        _require_non_empty("ExperimentTemplate.risk", self.risk)


@dataclass(frozen=True)
class DomainProfile:
    """A first-class deterministic profile for a Research Council domain."""

    id: str
    label: str
    concept_label: str
    summary: str
    claim_lenses: tuple[ClaimLens, ...]
    evidence_needs: tuple[EvidenceNeed, ...]
    reviewer_lenses: tuple[ReviewerLens, ...]
    experiment_templates: tuple[ExperimentTemplate, ...]
    selection_keywords: tuple[WeightedKeyword, ...]
    blocker_order: tuple[str, ...]
    council_lenses: tuple[str, ...] = ()
    reasoning_priorities: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    evidence_expectations: tuple[str, ...] = ()
    decision_heuristics: tuple[str, ...] = ()
    output_guidance: tuple[str, ...] = ()
    confidence_policy: tuple[str, ...] = ()
    caveat_policy: tuple[str, ...] = ()
    next_step_policy: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty("DomainProfile.id", self.id)
        _require_non_empty("DomainProfile.label", self.label)
        _require_non_empty("DomainProfile.concept_label", self.concept_label)
        _require_non_empty("DomainProfile.summary", self.summary)
        if _canonical_identifier(self.id) != self.id:
            raise ValueError("DomainProfile.id must be a canonical snake_case identifier")
        object.__setattr__(self, "claim_lenses", tuple(self.claim_lenses))
        object.__setattr__(self, "evidence_needs", tuple(self.evidence_needs))
        object.__setattr__(self, "reviewer_lenses", tuple(self.reviewer_lenses))
        object.__setattr__(
            self,
            "experiment_templates",
            tuple(self.experiment_templates),
        )
        object.__setattr__(
            self,
            "selection_keywords",
            _normalize_weighted_keywords(self.selection_keywords),
        )
        object.__setattr__(self, "blocker_order", _tuple_of_strings(self.blocker_order))
        object.__setattr__(
            self,
            "council_lenses",
            _tuple_of_strings(self.council_lenses)
            or tuple(lens.id for lens in self.claim_lenses),
        )
        object.__setattr__(
            self,
            "reasoning_priorities",
            _tuple_of_strings(self.reasoning_priorities),
        )
        object.__setattr__(self, "risk_factors", _tuple_of_strings(self.risk_factors))
        object.__setattr__(
            self,
            "evidence_expectations",
            _tuple_of_strings(self.evidence_expectations),
        )
        object.__setattr__(
            self,
            "decision_heuristics",
            _tuple_of_strings(self.decision_heuristics),
        )
        object.__setattr__(
            self,
            "output_guidance",
            _tuple_of_strings(self.output_guidance),
        )
        object.__setattr__(
            self,
            "confidence_policy",
            _tuple_of_strings(self.confidence_policy),
        )
        object.__setattr__(
            self,
            "caveat_policy",
            _tuple_of_strings(self.caveat_policy),
        )
        object.__setattr__(
            self,
            "next_step_policy",
            _tuple_of_strings(self.next_step_policy),
        )
        if not self.claim_lenses:
            raise ValueError("DomainProfile.claim_lenses must not be empty")
        if not self.evidence_needs:
            raise ValueError("DomainProfile.evidence_needs must not be empty")
        if not self.reviewer_lenses:
            raise ValueError("DomainProfile.reviewer_lenses must not be empty")
        if not self.experiment_templates:
            raise ValueError("DomainProfile.experiment_templates must not be empty")
        if not self.blocker_order:
            raise ValueError("DomainProfile.blocker_order must not be empty")


@dataclass(frozen=True)
class DomainProfileSelection:
    """A deterministic domain profile selection and its explanation."""

    selected_profile: DomainProfile
    score_by_profile: dict[str, int]
    matched_keywords: dict[str, tuple[str, ...]]
    selected_by: SelectionReason

    @property
    def profile(self) -> DomainProfile:
        """Alias for callers that prefer a shorter selected profile field."""

        return self.selected_profile


def _normalize_scoring_text(value: Any) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _canonical_identifier(value: Any) -> str:
    cleaned = _clean_text(value).lower()
    cleaned = re.sub(r"[-\s]+", "_", cleaned)
    cleaned = re.sub(r"[^a-z0-9_]+", "", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def _normalize_weighted_keywords(
    values: tuple[WeightedKeyword, ...],
) -> tuple[WeightedKeyword, ...]:
    normalized: list[WeightedKeyword] = []
    seen: set[str] = set()
    for keyword, weight in values:
        cleaned_keyword = _normalize_scoring_text(keyword)
        if not cleaned_keyword or cleaned_keyword in seen:
            continue
        if int(weight) <= 0:
            raise ValueError("selection keyword weights must be positive")
        seen.add(cleaned_keyword)
        normalized.append((cleaned_keyword, int(weight)))
    return tuple(normalized)


def _tuple_of_strings(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    return tuple(_clean_text(value) for value in values if _clean_text(value))


def _is_sequence_input(input_data: Any) -> bool:
    return isinstance(input_data, Sequence) and not isinstance(
        input_data, (str, bytes, bytearray)
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _require_non_empty(field_name: str, value: str) -> None:
    if not _clean_text(value):
        raise ValueError(f"{field_name} must be non-empty")


ALIASES: dict[str, str] = {
    "enterprise": "enterprise_b2b",
    "software": "ai_saas",
    "hardware": "hardware_device",
    "capsule_medical_environmental": "medical_device",
}

_PROFILE_ORDER: tuple[str, ...] = (
    "general",
    "medical_device",
    "ai_saas",
    "enterprise_b2b",
    "developer_tool",
    "consumer_app",
    "hardware_device",
    "materials_science",
)

_SAFETY_TIE_BREAKER: tuple[str, ...] = (
    "medical_device",
    "materials_science",
    "hardware_device",
    "enterprise_b2b",
    "developer_tool",
    "ai_saas",
    "consumer_app",
    "general",
)

_GENERIC_CLAIM_LENSES: tuple[ClaimLens, ...] = (
    ClaimLens(
        id="mechanism",
        label="Mechanism",
        focus="What must be true about the mechanism for the concept to work.",
    ),
    ClaimLens(
        id="user_need",
        label="User need",
        focus="Who has the problem, how painful it is, and what they do today.",
    ),
    ClaimLens(
        id="differentiation",
        label="Differentiation",
        focus="How the concept differs from substitutes, prior art, or current workflows.",
    ),
)

_GENERIC_EVIDENCE_NEEDS: tuple[EvidenceNeed, ...] = (
    EvidenceNeed(
        category="technical",
        request=(
            "Define the mechanism, prototype path, measurable threshold, and one "
            "failure-mode test."
        ),
    ),
    EvidenceNeed(
        category="user_adoption",
        request=(
            "Identify the target user, current workaround, switching trigger, and "
            "direct demand signal."
        ),
    ),
    EvidenceNeed(
        category="prior_art",
        request=(
            "Compare the concept against substitutes, patents, products, published "
            "work, or user-supplied offline references."
        ),
    ),
    EvidenceNeed(
        category="safety_regulatory",
        request=(
            "List safety-sensitive uses, review boundaries, approval assumptions, "
            "and stop conditions."
        ),
    ),
    EvidenceNeed(
        category="market",
        request=(
            "Name the buyer, competing alternative, adoption barrier, and "
            "willingness-to-pay signal."
        ),
    ),
)

_GENERIC_REVIEWER_LENSES: tuple[ReviewerLens, ...] = (
    ReviewerLens(
        role="technical",
        focus="Challenge mechanism, feasibility, and measurable performance claims.",
    ),
    ReviewerLens(
        role="market",
        focus="Challenge audience definition, buying path, and adoption assumptions.",
    ),
    ReviewerLens(
        role="safety_regulatory",
        focus="Challenge harm, compliance, privacy, and misuse assumptions.",
    ),
    ReviewerLens(
        role="red_team",
        focus="Look for the fastest way the concept could be wrong or misleading.",
    ),
)

_GENERIC_EXPERIMENT_TEMPLATES: tuple[ExperimentTemplate, ...] = (
    ExperimentTemplate(
        id="paper-prototype-test",
        title="Paper prototype test",
        method="Turn the concept into a simple task flow and test it with target users.",
        success_metric="Users can explain the value and identify a real next use.",
        minimum_sample="5 target users or buyers",
        risk="May validate interest without validating feasibility.",
    ),
    ExperimentTemplate(
        id="single-risk-spike",
        title="Single-risk spike",
        method="Isolate the riskiest assumption and build the smallest observable test.",
        success_metric="The test produces a pass/fail result tied to a decision threshold.",
        minimum_sample="1 focused prototype or analysis artifact",
        risk="May miss cross-domain risks outside the isolated assumption.",
    ),
)

_PROFILES: tuple[DomainProfile, ...] = (
    DomainProfile(
        id="general",
        label="General",
        concept_label="submitted concept",
        summary="A domain-neutral profile for concepts without strong deterministic signals.",
        claim_lenses=_GENERIC_CLAIM_LENSES,
        evidence_needs=_GENERIC_EVIDENCE_NEEDS,
        reviewer_lenses=_GENERIC_REVIEWER_LENSES,
        experiment_templates=_GENERIC_EXPERIMENT_TEMPLATES,
        selection_keywords=(),
        blocker_order=(
            "technical",
            "user_adoption",
            "prior_art",
            "safety_regulatory",
            "market",
        ),
    ),
    DomainProfile(
        id="medical_device",
        label="Medical device",
        concept_label="medical device concept",
        summary=(
            "A profile for patient-facing, clinical, diagnostic, ingestible, implantable, "
            "or regulated health device concepts."
        ),
        claim_lenses=(
            ClaimLens(
                id="clinical_use",
                label="Clinical use",
                focus="The care pathway, patient population, and clinical use boundary.",
                keywords=("clinical", "patient", "diagnostic", "screening"),
            ),
            ClaimLens(
                id="device_safety",
                label="Device safety",
                focus="Patient harm, biocompatibility, retention, sanitation, and oversight.",
                keywords=("safety", "biocompatibility", "ingestible", "implant"),
            ),
            ClaimLens(
                id="performance_quality",
                label="Performance quality",
                focus="The measured signal quality needed before any human-use claim.",
                keywords=("sensitivity", "specificity", "data quality", "diagnosis"),
            ),
        ),
        evidence_needs=(
            EvidenceNeed(
                category="safety_regulatory",
                request=(
                    "Identify patient safety risks, clinical oversight, data-quality "
                    "requirements, privacy issues, and regulatory approval boundaries."
                ),
            ),
            EvidenceNeed(
                category="technical",
                request=(
                    "Demonstrate the device mechanism, reliability, performance threshold, "
                    "and safe-use failure modes in a non-clinical prototype."
                ),
            ),
            EvidenceNeed(
                category="user_adoption",
                request=(
                    "Check clinician, patient, and institution workflow fit before "
                    "assuming adoption."
                ),
            ),
            EvidenceNeed(
                category="prior_art",
                request=(
                    "Compare against existing devices, care pathways, clinical substitutes, "
                    "and user-supplied offline references."
                ),
            ),
            EvidenceNeed(
                category="market",
                request="Identify buyer, payer, reimbursement, procurement, and adoption triggers.",
            ),
        ),
        reviewer_lenses=(
            ReviewerLens(
                role="safety_regulatory",
                focus="Prioritize patient harm, clinical claims, approval boundaries, and stop rules.",
                escalation_terms=("patient", "clinical", "diagnostic", "implant", "ingestible"),
            ),
            ReviewerLens(
                role="technical",
                focus="Stress-test device mechanism, measurement quality, reliability, and failure modes.",
            ),
            ReviewerLens(
                role="market",
                focus="Challenge payer, clinician workflow, reimbursement, and procurement assumptions.",
            ),
            ReviewerLens(
                role="red_team",
                focus="Look for unsafe shortcuts, invalid clinical inference, and unproven health claims.",
            ),
        ),
        experiment_templates=(
            ExperimentTemplate(
                id="non-clinical-bench-test",
                title="Non-clinical bench test",
                method=(
                    "Build a non-human prototype or fixture that measures the core signal, "
                    "failure modes, and operating constraints."
                ),
                success_metric="Prototype meets the predefined threshold without unsafe failure modes.",
                minimum_sample="3 bench runs across expected and adverse conditions",
                risk="Bench results do not establish clinical safety or efficacy.",
            ),
            ExperimentTemplate(
                id="workflow-risk-interview",
                title="Workflow risk interview",
                method="Interview clinicians or operators about workflow, trust, and adoption blockers.",
                success_metric="A repeatable adoption blocker and testable workflow requirement emerge.",
                minimum_sample="5 relevant clinicians, operators, or buyers",
                risk="Interviews may not represent clinical outcome or approval risk.",
            ),
        ),
        selection_keywords=(
            ("medical device", 8),
            ("clinical", 6),
            ("diagnostic", 6),
            ("diagnosis", 5),
            ("screening", 5),
            ("patient", 5),
            ("implant", 6),
            ("implantable", 6),
            ("ingestible", 7),
            ("swallowable", 7),
            ("capsule", 4),
            ("colon", 5),
            ("colorectal", 6),
            ("biocompatibility", 5),
            ("regulatory", 4),
            ("fda", 5),
            ("safety", 3),
        ),
        blocker_order=(
            "safety_regulatory",
            "technical",
            "user_adoption",
            "prior_art",
            "market",
        ),
        council_lenses=(
            "clinical_use",
            "device_safety",
            "performance_quality",
            "regulatory_path",
        ),
        reasoning_priorities=(
            "patient safety before adoption or market upside",
            "clinical validation before diagnostic or human-use claims",
            "regulatory boundary before broad use",
            "non-clinical prototype evidence before confidence upgrades",
        ),
        risk_factors=(
            "patient harm",
            "clinical false reassurance",
            "diagnostic-quality failure",
            "biocompatibility or retention risk",
            "regulatory approval uncertainty",
        ),
        evidence_expectations=(
            "non-clinical safety evidence",
            "measured reliability and performance thresholds",
            "clinical workflow and oversight evidence",
            "regulatory classification and approval-boundary evidence",
        ),
        decision_heuristics=(
            "pause broad use when safety_regulatory evidence is missing",
            "treat clinician or patient interest as adoption signal only, not validation",
            "do not treat bench evidence as clinical safety or efficacy",
        ),
        output_guidance=(
            "use conservative medical-device language",
            "separate concept plausibility from clinical validation",
            "name patient-safety and regulatory caveats explicitly",
        ),
        confidence_policy=(
            "confidence remains conservative until safety, clinical validation, and regulatory boundaries are evidenced",
            "human-use, diagnostic, or efficacy claims stay low confidence in a local-only pass",
        ),
        caveat_policy=(
            "include patient safety caveats",
            "include regulatory awareness",
            "include clinical validation limits",
        ),
        next_step_policy=(
            "prefer non-clinical safety boundary work before adoption or market tests",
            "never recommend human testing from the deterministic local pass",
        ),
    ),
    DomainProfile(
        id="ai_saas",
        label="AI SaaS",
        concept_label="AI SaaS concept",
        summary=(
            "A profile for software, AI assistant, automation, workflow, dashboard, API, "
            "and subscription product concepts."
        ),
        claim_lenses=(
            ClaimLens(
                id="workflow_value",
                label="Workflow value",
                focus="The job-to-be-done, workflow owner, and time or quality improvement.",
                keywords=("workflow", "assistant", "automation", "dashboard"),
            ),
            ClaimLens(
                id="model_quality",
                label="Model quality",
                focus="Data inputs, quality rubric, failure handling, and reliability.",
                keywords=("ai", "model", "llm", "quality"),
            ),
            ClaimLens(
                id="go_to_market",
                label="Go-to-market",
                focus="Buyer, budget, switching cost, packaging, and subscription logic.",
                keywords=("saas", "subscription", "b2b", "buyer"),
            ),
            ClaimLens(
                id="defensible_wedge",
                label="Defensible wedge",
                focus="Narrow workflow wedge, differentiation risk, and AI-wrapper substitution risk.",
                keywords=("differentiation", "wrapper", "substitute", "retention"),
            ),
        ),
        evidence_needs=(
            EvidenceNeed(
                category="user_adoption",
                request=(
                    "Show that the target workflow is painful, frequent, integrated into "
                    "the buyer's current process, and owned by someone with urgency and "
                    "authority to change tools."
                ),
            ),
            EvidenceNeed(
                category="technical",
                request=(
                    "Define data inputs, deterministic quality checks, failure handling, "
                    "privacy, security, uptime expectations, and operational reliability."
                ),
            ),
            EvidenceNeed(
                category="prior_art",
                request=(
                    "Compare against existing software, AI assistants, manual workflows, "
                    "generic AI wrappers, and user-supplied offline references."
                ),
            ),
            EvidenceNeed(
                category="market",
                request=(
                    "Identify buyer urgency, pricing logic, willingness to pay, distribution "
                    "channel, switching trigger, switching cost, and retention trigger."
                ),
            ),
            EvidenceNeed(
                category="safety_regulatory",
                request=(
                    "Identify sensitive data, regulated decisions, legal boundaries, and "
                    "review points before deployment."
                ),
            ),
        ),
        reviewer_lenses=(
            ReviewerLens(
                role="technical",
                focus="Challenge model quality, data access, deterministic checks, and reliability.",
            ),
            ReviewerLens(
                role="market",
                focus="Challenge buyer urgency, willingness to pay, and distribution assumptions.",
            ),
            ReviewerLens(
                role="safety_regulatory",
                focus="Review privacy, security, regulated decisions, and misleading automation.",
                escalation_terms=("legal", "health", "finance", "personal data", "patent"),
            ),
            ReviewerLens(
                role="red_team",
                focus="Find brittle prompts, hallucination risk, data leakage, and weak differentiation.",
            ),
        ),
        experiment_templates=(
            ExperimentTemplate(
                id="task-rubric-prototype",
                title="Task rubric prototype",
                method=(
                    "Run representative tasks through a local prototype and grade outputs "
                    "with a fixed rubric."
                ),
                success_metric="The prototype beats the current workaround on the chosen rubric.",
                minimum_sample="10 representative tasks",
                risk="A local task set may not represent production data or edge cases.",
            ),
            ExperimentTemplate(
                id="workflow-demand-test",
                title="Workflow demand test",
                method="Test a clickable flow or concierge version with target users.",
                success_metric="Users commit to a next trial, payment conversation, or data upload.",
                minimum_sample="5 target users or buyers",
                risk="Interest may not survive integration, compliance, or switching costs.",
            ),
        ),
        selection_keywords=(
            ("artificial intelligence", 6),
            ("machine learning", 5),
            ("ai", 5),
            ("llm", 5),
            ("saas", 6),
            ("software", 5),
            ("assistant", 4),
            ("automation", 4),
            ("workflow", 3),
            ("dashboard", 3),
            ("api", 3),
            ("patent", 3),
            ("document", 2),
            ("b2b", 3),
            ("subscription", 3),
        ),
        blocker_order=(
            "user_adoption",
            "technical",
            "safety_regulatory",
            "market",
            "prior_art",
        ),
        council_lenses=(
            "workflow_value",
            "model_quality",
            "go_to_market",
            "defensible_wedge",
        ),
        reasoning_priorities=(
            "buyer/workflow urgency before generic product scope",
            "repeat usage and retention before broad SaaS confidence",
            "narrow wedge before platform expansion",
            "operational reliability before automation trust",
            "willingness to pay before market optimism",
        ),
        risk_factors=(
            "workflow integration risk",
            "buyer urgency risk",
            "switching cost risk",
            "differentiation risk",
            "AI wrapper risk",
            "retention risk",
            "operational reliability risk",
            "willingness to pay risk",
        ),
        evidence_expectations=(
            "buyer and workflow-owner interviews",
            "current workaround and switching-trigger evidence",
            "repeat usage or retention signal",
            "output-quality rubric and reliability thresholds",
            "substitute map against generic AI and manual workflows",
            "willingness-to-pay or pricing threshold evidence",
        ),
        decision_heuristics=(
            "penalize concepts that only describe a generic AI wrapper",
            "treat one-time report value as insufficient for SaaS retention",
            "prefer a narrow workflow wedge when differentiation is weak",
            "do not upgrade confidence without buyer urgency and repeat-use evidence",
        ),
        output_guidance=(
            "surface buyer/workflow, repeat usage, narrow wedge, GTM risk, and adoption risk",
            "name AI-wrapper and differentiation risk when prior-art evidence is missing",
            "keep legal, data, and reliability boundaries visible",
        ),
        confidence_policy=(
            "confidence is capped until workflow frequency, buyer urgency, reliability, differentiation, and willingness to pay are evidenced",
            "high confidence requires repeated-use evidence, not just user interest",
        ),
        caveat_policy=(
            "include adoption and GTM caveats",
            "include AI-wrapper differentiation caveats",
            "include reliability and legal-boundary caveats",
        ),
        next_step_policy=(
            "prioritize workflow interviews when buyer/workflow evidence is weak",
            "prioritize output-quality evaluation when reliability evidence is weak",
            "prioritize differentiation mapping when AI-wrapper risk is unresolved",
        ),
    ),
    DomainProfile(
        id="enterprise_b2b",
        label="Enterprise B2B",
        concept_label="enterprise B2B concept",
        summary=(
            "A profile for enterprise workflow platforms, internal tools, procurement, "
            "security/compliance review, rollout, and multi-stakeholder B2B adoption."
        ),
        claim_lenses=(
            ClaimLens(
                id="procurement_path",
                label="Procurement path",
                focus="Budget owner clarity, procurement friction, long sales cycle, and ROI proof.",
                keywords=("procurement", "budget owner", "roi", "long sales cycle"),
            ),
            ClaimLens(
                id="stakeholder_alignment",
                label="Stakeholder alignment",
                focus="Champion versus buyer distinction, department workflow, and org-wide adoption risk.",
                keywords=("stakeholder", "champion", "buyer", "department workflow"),
            ),
            ClaimLens(
                id="security_compliance",
                label="Security and compliance",
                focus="Security review, compliance requirements, SOC2, SSO, audit logs, governance, and IT approval.",
                keywords=("security review", "compliance", "soc2", "sso", "audit logs"),
            ),
            ClaimLens(
                id="rollout_integration",
                label="Rollout and integration",
                focus="Integration burden, workflow integration depth, training, onboarding, and rollout complexity.",
                keywords=("enterprise integration", "multi-team rollout", "onboarding", "training"),
            ),
        ),
        evidence_needs=(
            EvidenceNeed(
                category="market",
                request=(
                    "Identify the budget owner, procurement path, purchase process, "
                    "ROI proof requirement, long-sales-cycle risk, and whether the "
                    "economic buyer differs from the product champion."
                ),
            ),
            EvidenceNeed(
                category="user_adoption",
                request=(
                    "Map stakeholder alignment, champion versus buyer distinction, "
                    "department workflow, onboarding/training burden, and org-wide "
                    "adoption risk."
                ),
            ),
            EvidenceNeed(
                category="safety_regulatory",
                request=(
                    "Define security/compliance requirements, SOC2 expectations, "
                    "SSO/admin needs, audit logs, governance, data access, and IT "
                    "approval boundaries before rollout."
                ),
            ),
            EvidenceNeed(
                category="technical",
                request=(
                    "Measure integration burden, workflow integration depth, deployment "
                    "responsibility, vendor reliability expectations, and rollout complexity."
                ),
            ),
            EvidenceNeed(
                category="prior_art",
                request=(
                    "Compare against current enterprise systems, internal tools, manual "
                    "processes, vendor alternatives, switching cost, and migration friction."
                ),
            ),
        ),
        reviewer_lenses=(
            ReviewerLens(
                role="technical",
                focus="Challenge integration burden, workflow integration depth, deployment responsibility, rollout complexity, and vendor reliability.",
            ),
            ReviewerLens(
                role="market",
                focus="Challenge procurement friction, budget owner clarity, stakeholder alignment, ROI proof, and long sales cycle.",
            ),
            ReviewerLens(
                role="safety_regulatory",
                focus="Review compliance, SOC2, security review, SSO, audit logs, governance, data access, and IT approval.",
                escalation_terms=("compliance", "security review", "soc2", "sso", "audit logs", "governance"),
            ),
            ReviewerLens(
                role="red_team",
                focus="Look for champion-only enthusiasm, stalled procurement, rollout drag, training cost, and vendor-trust gaps.",
            ),
        ),
        experiment_templates=(
            ExperimentTemplate(
                id="procurement-interview",
                title="Procurement interview",
                method=(
                    "Interview the likely budget owner, procurement stakeholder, and "
                    "product champion about purchase process, approval steps, ROI proof, "
                    "security review, and long-sales-cycle risk."
                ),
                success_metric="The buying path, owner, blockers, and required proof are explicit.",
                minimum_sample="3 stakeholders across champion, buyer, and procurement roles",
                risk="Interviews clarify process but do not guarantee approval or budget timing.",
            ),
            ExperimentTemplate(
                id="security-compliance-review-mapping",
                title="Security/compliance review mapping",
                method=(
                    "Map SOC2, SSO, audit logs, data-access, governance, IT approval, "
                    "and security-review requirements before any enterprise rollout."
                ),
                success_metric="Security and compliance blockers are named with owner, evidence, and stop condition.",
                minimum_sample="One checklist reviewed with a security, IT, or compliance stakeholder",
                risk="A checklist does not replace formal security or legal review.",
            ),
        ),
        selection_keywords=(
            ("enterprise b2b", 10),
            ("enterprise", 9),
            ("procurement", 9),
            ("security review", 9),
            ("enterprise integration", 9),
            ("multi team rollout", 9),
            ("compliance", 8),
            ("soc2", 8),
            ("soc 2", 8),
            ("sso", 8),
            ("audit logs", 8),
            ("it approval", 8),
            ("budget owner", 8),
            ("stakeholder alignment", 8),
            ("internal tool", 7),
            ("admin dashboard", 7),
            ("governance", 7),
            ("department workflow", 7),
            ("roi", 7),
            ("long sales cycle", 7),
            ("onboarding", 6),
            ("vendor trust", 6),
            ("champion", 5),
            ("rollout", 5),
            ("training", 5),
        ),
        blocker_order=(
            "market",
            "safety_regulatory",
            "user_adoption",
            "technical",
            "prior_art",
        ),
        council_lenses=(
            "procurement_path",
            "stakeholder_alignment",
            "security_compliance",
            "rollout_integration",
        ),
        reasoning_priorities=(
            "procurement path and budget owner before enterprise confidence",
            "security/compliance requirements before rollout optimism",
            "stakeholder alignment before champion enthusiasm",
            "integration and onboarding burden before org-wide adoption claims",
            "ROI proof before long-sales-cycle investment",
        ),
        risk_factors=(
            "procurement friction",
            "unclear budget owner",
            "stakeholder alignment risk",
            "security/compliance review risk",
            "enterprise integration burden",
            "rollout complexity",
            "training and onboarding cost",
            "switching cost from current systems",
            "long sales cycle risk",
            "ROI proof gap",
            "champion versus buyer mismatch",
            "org-wide adoption risk",
            "vendor trust and reliability risk",
        ),
        evidence_expectations=(
            "budget owner and procurement path evidence",
            "security/compliance, SOC2, SSO, audit-log, and governance requirements",
            "stakeholder map separating champion, buyer, IT, security, and end users",
            "integration requirements and deployment responsibility evidence",
            "rollout, training, and onboarding burden evidence",
            "ROI proof and long-sales-cycle evidence",
            "switching-cost and migration-friction evidence",
        ),
        decision_heuristics=(
            "do not upgrade confidence without procurement and security/compliance evidence",
            "treat champion interest as weak until budget owner and buyer are identified",
            "penalize enterprise claims that omit rollout, training, and integration burden",
            "prefer ROI validation before broad platform buildout",
        ),
        output_guidance=(
            "surface procurement, budget owner, stakeholder alignment, ROI, and long-sales-cycle risk",
            "name security/compliance, SSO, audit-log, governance, and IT-approval gaps explicitly",
            "separate champion enthusiasm from buyer approval and org-wide adoption",
            "keep rollout, onboarding, training, integration, switching cost, and vendor reliability visible",
        ),
        confidence_policy=(
            "confidence is capped until procurement path, security/compliance requirements, integration burden, rollout plan, and ROI proof are evidenced",
            "high confidence requires identified budget owner, security review path, and stakeholder alignment",
        ),
        caveat_policy=(
            "include procurement and long-sales-cycle caveats",
            "include security/compliance and IT-approval caveats",
            "include rollout, onboarding, training, switching-cost, and stakeholder-alignment caveats",
        ),
        next_step_policy=(
            "prioritize procurement interviews when budget owner or buying path is unclear",
            "prioritize security/compliance review mapping when enterprise controls are unknown",
            "prioritize rollout simulation or integration pilot when adoption depends on workflow depth",
        ),
    ),
    DomainProfile(
        id="developer_tool",
        label="Developer tool",
        concept_label="developer tool concept",
        summary=(
            "A profile for SDKs, APIs, CLIs, debugging, observability, local "
            "development, CI/CD, and developer workflow tools."
        ),
        claim_lenses=(
            ClaimLens(
                id="developer_workflow",
                label="Developer workflow",
                focus="The target developer segment, existing workflow pain, and workflow fit.",
                keywords=("developer workflow", "debugging", "local development"),
            ),
            ClaimLens(
                id="setup_integration",
                label="Setup and integration",
                focus="Setup complexity, integration cost, ecosystem compatibility, and time-to-value.",
                keywords=("sdk", "api", "cli", "integration", "setup"),
            ),
            ClaimLens(
                id="debug_observability",
                label="Debuggability and observability",
                focus="Logs, monitoring, observability, debugging value, and failure visibility.",
                keywords=("logs", "monitoring", "observability", "debugging"),
            ),
            ClaimLens(
                id="adoption_path",
                label="Adoption path",
                focus="Individual developer adoption, team rollout, documentation burden, and repeat usage.",
                keywords=("documentation", "team", "repeat usage", "switching cost"),
            ),
        ),
        evidence_needs=(
            EvidenceNeed(
                category="user_adoption",
                request=(
                    "Identify the target developer segment, existing workflow pain, "
                    "current workaround, repeat usage trigger, and whether adoption "
                    "starts with an individual developer or a team process."
                ),
            ),
            EvidenceNeed(
                category="technical",
                request=(
                    "Measure setup complexity, integration burden, time-to-first-value, "
                    "debugging or observability value, and compatibility with the "
                    "developer's existing stack."
                ),
            ),
            EvidenceNeed(
                category="prior_art",
                request=(
                    "Compare against existing developer tools, SDKs, CLIs, logs, "
                    "monitoring systems, CI/CD workflows, and current manual debugging habits."
                ),
            ),
            EvidenceNeed(
                category="market",
                request=(
                    "Clarify switching cost from current tools, team rollout friction, "
                    "documentation/support burden, and whether the value survives beyond "
                    "one setup session."
                ),
            ),
            EvidenceNeed(
                category="safety_regulatory",
                request=(
                    "Identify secrets, production data, access scopes, log exposure, "
                    "and operational-risk boundaries before integration."
                ),
            ),
        ),
        reviewer_lenses=(
            ReviewerLens(
                role="technical",
                focus="Challenge setup complexity, integration cost, compatibility, observability value, and time-to-value.",
            ),
            ReviewerLens(
                role="market",
                focus="Challenge developer workflow pain, repeat usage, switching cost, and individual versus team adoption.",
            ),
            ReviewerLens(
                role="safety_regulatory",
                focus="Review secrets, production data, permissions, logs, and operational blast radius.",
                escalation_terms=("secrets", "production", "logs", "access token", "credential"),
            ),
            ReviewerLens(
                role="red_team",
                focus="Look for tool sprawl, unclear workflow fit, brittle integrations, and documentation gaps.",
            ),
        ),
        experiment_templates=(
            ExperimentTemplate(
                id="setup-friction-test",
                title="Setup friction test",
                method=(
                    "Ask target developers to install or configure the smallest useful "
                    "version and record every setup, permission, and integration blocker."
                ),
                success_metric="Developers reach first useful output within the target time budget.",
                minimum_sample="3 target developers using their normal stack",
                risk="A small setup test may miss enterprise, security, or team rollout constraints.",
            ),
            ExperimentTemplate(
                id="developer-workflow-interview",
                title="Developer workflow interview",
                method=(
                    "Interview developers about their current debugging, observability, "
                    "or local development workflow, existing tools, switching costs, "
                    "and repeat-use triggers."
                ),
                success_metric="Repeated workflow pain and a concrete adoption trigger are observed.",
                minimum_sample="5 developers in the target segment",
                risk="Interview pain may not translate into integration or team adoption.",
            ),
        ),
        selection_keywords=(
            ("developer tool", 10),
            ("developer workflow", 9),
            ("devtool", 9),
            ("sdk", 8),
            ("cli", 8),
            ("debugging", 8),
            ("observability", 8),
            ("local development", 8),
            ("ci cd", 8),
            ("github integration", 7),
            ("developer", 5),
            ("developers", 5),
            ("api", 5),
            ("logs", 5),
            ("logging", 5),
            ("monitoring", 5),
            ("integration", 5),
            ("setup", 5),
            ("documentation", 4),
            ("command line", 4),
        ),
        blocker_order=(
            "user_adoption",
            "technical",
            "prior_art",
            "market",
            "safety_regulatory",
        ),
        council_lenses=(
            "developer_workflow",
            "setup_integration",
            "debug_observability",
            "adoption_path",
        ),
        reasoning_priorities=(
            "developer workflow fit before broad tooling claims",
            "setup complexity and time-to-value before adoption confidence",
            "ecosystem compatibility before integration optimism",
            "debugging and observability value before feature breadth",
            "repeat usage before one-time setup excitement",
        ),
        risk_factors=(
            "developer experience friction",
            "setup complexity risk",
            "integration cost risk",
            "ecosystem compatibility risk",
            "debugging value risk",
            "documentation burden",
            "switching cost from existing tools",
            "team adoption friction",
            "time-to-value risk",
            "repeat usage risk",
        ),
        evidence_expectations=(
            "target developer segment and workflow pain evidence",
            "setup friction and time-to-first-value evidence",
            "integration prototype against an existing stack",
            "compatibility evidence for SDK, API, CLI, CI/CD, or GitHub workflows",
            "existing tool comparison and switching-cost evidence",
            "documentation comprehension and support-burden evidence",
            "repeat usage trigger or workflow-fit evidence",
        ),
        decision_heuristics=(
            "do not upgrade confidence without setup and integration evidence",
            "treat developer interest as weak until time-to-value is observed",
            "prefer compatibility tests before broad ecosystem claims",
            "penalize tools that add workflow steps without debugging or observability value",
        ),
        output_guidance=(
            "surface DX friction, setup complexity, integration cost, compatibility, and time-to-value",
            "separate individual developer adoption from team rollout",
            "name documentation, support, switching cost, and repeat usage gaps explicitly",
        ),
        confidence_policy=(
            "confidence is capped until setup friction, integration burden, ecosystem compatibility, and repeat usage are evidenced",
            "high confidence requires observed time-to-value in a real developer workflow",
        ),
        caveat_policy=(
            "include developer-workflow and setup-friction caveats",
            "include integration and ecosystem compatibility caveats",
            "include documentation, support, and team-adoption caveats",
        ),
        next_step_policy=(
            "prioritize setup friction tests when integration evidence is weak",
            "prioritize developer workflow interviews when segment pain is unclear",
            "prioritize documentation comprehension tests when time-to-value depends on docs",
        ),
    ),
    DomainProfile(
        id="consumer_app",
        label="Consumer app",
        concept_label="consumer app concept",
        summary=(
            "A profile for mobile, consumer, creator, social, habit, wellness, and "
            "personal productivity app concepts."
        ),
        claim_lenses=(
            ClaimLens(
                id="consumer_problem",
                label="Consumer problem",
                focus="The personal pain, frequency, motivation, and substitute behavior.",
                keywords=("consumer", "habit", "wellness", "personal"),
            ),
            ClaimLens(
                id="retention_loop",
                label="Retention loop",
                focus="The reason users return after novelty fades.",
                keywords=("retention", "daily", "habit", "social"),
            ),
            ClaimLens(
                id="distribution",
                label="Distribution",
                focus="The acquisition channel and reason the app can be discovered.",
                keywords=("mobile app", "ios", "android", "creator"),
            ),
        ),
        evidence_needs=(
            EvidenceNeed(
                category="user_adoption",
                request=(
                    "Show that target consumers have a frequent problem, a current workaround, "
                    "and a reason to return after first use."
                ),
            ),
            EvidenceNeed(
                category="market",
                request=(
                    "Identify acquisition channel, monetization path, competing apps, and "
                    "retention signal."
                ),
            ),
            EvidenceNeed(
                category="technical",
                request="Define the minimum product loop, data needs, privacy boundaries, and reliability.",
            ),
            EvidenceNeed(
                category="prior_art",
                request="Compare against app-store substitutes and offline behavior alternatives.",
            ),
            EvidenceNeed(
                category="safety_regulatory",
                request="Identify privacy, minors, health, financial, and content-moderation risks.",
            ),
        ),
        reviewer_lenses=(
            ReviewerLens(
                role="market",
                focus="Challenge retention, monetization, acquisition, and substitute behavior.",
            ),
            ReviewerLens(
                role="technical",
                focus="Challenge product loop, data handling, scalability, and reliability.",
            ),
            ReviewerLens(
                role="safety_regulatory",
                focus="Review privacy, minors, health claims, content, and consumer protection.",
                escalation_terms=("minor", "health", "finance", "location", "personal data"),
            ),
            ReviewerLens(
                role="red_team",
                focus="Look for novelty-only engagement, weak retention, and harmful incentives.",
            ),
        ),
        experiment_templates=(
            ExperimentTemplate(
                id="retention-loop-test",
                title="Retention loop test",
                method="Run a lightweight prototype that asks users to complete the core loop repeatedly.",
                success_metric="Users return unprompted or opt into a repeated-use test.",
                minimum_sample="10 target consumers over 7 days",
                risk="Short tests can overstate durable retention.",
            ),
            ExperimentTemplate(
                id="landing-demand-test",
                title="Landing demand test",
                method="Present the app promise and capture a concrete signup or waitlist action.",
                success_metric="A predefined share of target users take the next action.",
                minimum_sample="50 qualified visitors",
                risk="Signup intent may not convert to retained use.",
            ),
        ),
        selection_keywords=(
            ("consumer", 6),
            ("mobile app", 6),
            ("app", 1),
            ("ios", 4),
            ("android", 4),
            ("habit", 4),
            ("wellness", 3),
            ("personal", 3),
            ("social", 3),
            ("community", 3),
            ("creator", 3),
            ("users", 2),
            ("retention", 4),
        ),
        blocker_order=(
            "user_adoption",
            "market",
            "technical",
            "safety_regulatory",
            "prior_art",
        ),
    ),
    DomainProfile(
        id="hardware_device",
        label="Hardware device",
        concept_label="hardware device concept",
        summary=(
            "A profile for physical devices, sensors, firmware, electronics, robotics, "
            "manufacturing, and field-use concepts."
        ),
        claim_lenses=(
            ClaimLens(
                id="physical_mechanism",
                label="Physical mechanism",
                focus="Components, power, enclosure, sensing, actuation, and operating conditions.",
                keywords=("hardware", "sensor", "firmware", "electronics"),
            ),
            ClaimLens(
                id="manufacturing_path",
                label="Manufacturing path",
                focus="Prototype, bill of materials, manufacturability, supply, and maintenance.",
                keywords=("prototype", "manufacturing", "battery", "mechanical"),
            ),
            ClaimLens(
                id="field_safety",
                label="Field safety",
                focus="Physical safety, reliability, misuse, and environmental exposure.",
                keywords=("device", "field", "safety", "reliability"),
            ),
        ),
        evidence_needs=(
            EvidenceNeed(
                category="technical",
                request=(
                    "Define components, prototype path, power budget, reliability threshold, "
                    "and failure-mode tests."
                ),
            ),
            EvidenceNeed(
                category="safety_regulatory",
                request="Identify physical safety, misuse, certification, and field-operation boundaries.",
            ),
            EvidenceNeed(
                category="market",
                request="Identify buyer, deployment setting, competing equipment, and service burden.",
            ),
            EvidenceNeed(
                category="user_adoption",
                request="Check operator workflow, maintenance burden, installation friction, and training.",
            ),
            EvidenceNeed(
                category="prior_art",
                request="Compare against existing hardware, sensors, robotics, and manual alternatives.",
            ),
        ),
        reviewer_lenses=(
            ReviewerLens(
                role="technical",
                focus="Challenge physics, component availability, reliability, power, and manufacturing.",
            ),
            ReviewerLens(
                role="safety_regulatory",
                focus="Review physical harm, certification, misuse, and field conditions.",
                escalation_terms=("battery", "safety", "field", "certification", "robot"),
            ),
            ReviewerLens(
                role="market",
                focus="Challenge buyer, installation, service cost, and replacement alternatives.",
            ),
            ReviewerLens(
                role="red_team",
                focus="Look for hidden manufacturing cost, fragile prototypes, and unsafe operation.",
            ),
        ),
        experiment_templates=(
            ExperimentTemplate(
                id="bench-prototype-test",
                title="Bench prototype test",
                method="Build a small prototype or fixture for the core physical mechanism.",
                success_metric="The prototype meets its threshold across repeat trials.",
                minimum_sample="5 bench trials",
                risk="Bench performance may not survive field conditions or manufacturing scale.",
            ),
            ExperimentTemplate(
                id="operator-workflow-test",
                title="Operator workflow test",
                method="Observe target operators using a mock device in the intended workflow.",
                success_metric="Operators complete the task and identify fewer blockers than expected.",
                minimum_sample="5 target operators",
                risk="Mock workflows may understate installation and maintenance burden.",
            ),
        ),
        selection_keywords=(
            ("hardware", 6),
            ("device", 4),
            ("sensor", 5),
            ("prototype", 3),
            ("firmware", 5),
            ("embedded", 5),
            ("robot", 5),
            ("robotic", 5),
            ("manufacturing", 4),
            ("battery", 4),
            ("electronics", 5),
            ("iot", 4),
            ("mechanical", 4),
            ("actuator", 4),
        ),
        blocker_order=(
            "technical",
            "safety_regulatory",
            "market",
            "user_adoption",
            "prior_art",
        ),
    ),
    DomainProfile(
        id="materials_science",
        label="Materials science",
        concept_label="materials science concept",
        summary=(
            "A profile for materials, polymers, coatings, composites, degradation, corrosion, "
            "thermal behavior, and measured material properties."
        ),
        claim_lenses=(
            ClaimLens(
                id="material_property",
                label="Material property",
                focus="The property, test condition, baseline, and measurement method.",
                keywords=("polymer", "composite", "coating", "alloy"),
            ),
            ClaimLens(
                id="degradation_path",
                label="Degradation path",
                focus="How the material changes over time and what residues or byproducts remain.",
                keywords=("degradation", "degradable", "corrosion", "residue"),
            ),
            ClaimLens(
                id="use_environment",
                label="Use environment",
                focus="The operating environment, exposure, stress, and lifecycle boundary.",
                keywords=("thermal", "wastewater", "uv", "mechanical properties"),
            ),
        ),
        evidence_needs=(
            EvidenceNeed(
                category="technical",
                request=(
                    "Define material composition, test method, baseline, operating environment, "
                    "and measured property threshold."
                ),
            ),
            EvidenceNeed(
                category="environmental",
                request=(
                    "Measure degradation timing, byproducts, residues, disposal pathway, and "
                    "whether risk shifts elsewhere."
                ),
            ),
            EvidenceNeed(
                category="prior_art",
                request="Compare against known materials, coatings, composites, and published references.",
            ),
            EvidenceNeed(
                category="safety_regulatory",
                request="Identify toxicity, exposure, contamination, handling, and disposal hazards.",
            ),
            EvidenceNeed(
                category="market",
                request="Identify application owner, substitute material, performance tradeoff, and cost.",
            ),
        ),
        reviewer_lenses=(
            ReviewerLens(
                role="technical",
                focus="Challenge test method, baseline, repeatability, and property claims.",
            ),
            ReviewerLens(
                role="safety_regulatory",
                focus="Review toxicity, exposure, contamination, disposal, and material handling.",
                escalation_terms=("toxicity", "implant", "patient", "bio", "wastewater"),
            ),
            ReviewerLens(
                role="market",
                focus="Challenge target application, cost, substitute materials, and adoption threshold.",
            ),
            ReviewerLens(
                role="red_team",
                focus="Look for cherry-picked conditions, unmeasured byproducts, and lifecycle shifts.",
            ),
        ),
        experiment_templates=(
            ExperimentTemplate(
                id="bench-material-characterization",
                title="Bench material characterization",
                method="Run a controlled material test against a baseline and repeated conditions.",
                success_metric="The material meets the threshold with repeatable measurements.",
                minimum_sample="3 material samples per condition",
                risk="Bench conditions may not represent real exposure or lifecycle behavior.",
            ),
            ExperimentTemplate(
                id="degradation-path-test",
                title="Degradation path test",
                method="Expose samples to the expected environment and measure breakdown and residue.",
                success_metric="Breakdown timing and residues stay within predefined limits.",
                minimum_sample="3 samples across expected exposure conditions",
                risk="Short tests may miss long-term byproducts or disposal pathway effects.",
            ),
        ),
        selection_keywords=(
            ("materials science", 7),
            ("materials", 6),
            ("material", 5),
            ("polymer", 6),
            ("composite", 5),
            ("coating", 5),
            ("alloy", 5),
            ("degradation", 6),
            ("degradable", 5),
            ("biodegradable", 5),
            ("corrosion", 5),
            ("thermal", 4),
            ("mechanical properties", 5),
            ("microstructure", 6),
            ("residue", 4),
            ("wastewater", 4),
            ("uv", 3),
        ),
        blocker_order=(
            "technical",
            "safety_regulatory",
            "environmental",
            "prior_art",
            "market",
        ),
    ),
)

_PROFILE_REGISTRY: dict[str, DomainProfile] = {profile.id: profile for profile in _PROFILES}
_TIE_BREAKER_RANK: dict[str, int] = {
    profile_id: index for index, profile_id in enumerate(_SAFETY_TIE_BREAKER)
}


def get_profile(profile_id: str) -> DomainProfile:
    """Return a domain profile by canonical id or alias."""

    canonical_id = _canonical_profile_id(profile_id)
    try:
        return _PROFILE_REGISTRY[canonical_id]
    except KeyError as exc:
        known = ", ".join(sorted(_PROFILE_REGISTRY))
        aliases = ", ".join(f"{alias}->{target}" for alias, target in sorted(ALIASES.items()))
        raise ValueError(
            f"unknown domain profile: {profile_id!r}. Known profiles: {known}. "
            f"Aliases: {aliases}."
        ) from exc


def list_profiles() -> tuple[DomainProfile, ...]:
    """Return the deterministic profile registry contents in stable order."""

    return tuple(_PROFILE_REGISTRY[profile_id] for profile_id in _PROFILE_ORDER)


def resolve_domain_profile(
    input_data: Any,
    explicit_profile_id: str | None = None,
) -> DomainProfileSelection:
    """Select a domain profile deterministically from explicit id or input text."""

    if explicit_profile_id is not None and str(explicit_profile_id).strip():
        return DomainProfileSelection(
            selected_profile=get_profile(explicit_profile_id),
            score_by_profile=_empty_score_by_profile(),
            matched_keywords=_empty_matched_keywords(),
            selected_by="explicit",
        )

    scoring_text = _scoring_text_for(input_data)
    score_by_profile, matched_keywords = _score_profiles(scoring_text)
    highest_score = max(score_by_profile.values(), default=0)
    if highest_score <= 0:
        return DomainProfileSelection(
            selected_profile=get_profile("general"),
            score_by_profile=score_by_profile,
            matched_keywords=matched_keywords,
            selected_by="fallback",
        )

    candidates = tuple(
        profile_id
        for profile_id in _PROFILE_ORDER
        if score_by_profile.get(profile_id, 0) == highest_score
    )
    selected_id = min(candidates, key=lambda profile_id: _TIE_BREAKER_RANK[profile_id])
    return DomainProfileSelection(
        selected_profile=get_profile(selected_id),
        score_by_profile=score_by_profile,
        matched_keywords=matched_keywords,
        selected_by="deterministic_score",
    )


def _score_profiles(scoring_text: str) -> tuple[dict[str, int], dict[str, tuple[str, ...]]]:
    score_by_profile: dict[str, int] = {}
    matched_keywords: dict[str, tuple[str, ...]] = {}
    for profile in list_profiles():
        score = 0
        matches: list[str] = []
        for keyword, weight in profile.selection_keywords:
            if _keyword_matches(
                scoring_text,
                keyword,
                ignore_negated=profile.id in {"developer_tool", "enterprise_b2b"},
            ):
                score += weight
                matches.append(keyword)
        score_by_profile[profile.id] = score
        matched_keywords[profile.id] = tuple(matches)
    return score_by_profile, matched_keywords


def _scoring_text_for(input_data: Any) -> str:
    if isinstance(input_data, str):
        return _normalize_scoring_text(input_data)

    if isinstance(input_data, Mapping):
        raw_idea = _first_mapping_value(input_data, "raw_idea", "idea", "raw", "description")
        goal = _first_mapping_value(input_data, "goal", "objective", "outcome")
        context = _first_mapping_value(input_data, "context", "background")
        constraints = _tuple_of_strings(input_data.get("constraints"))
        return _normalize_scoring_text(" ".join(_flatten_parts(raw_idea, goal, context, constraints)))

    if _is_sequence_input(input_data):
        values = list(input_data)
        raw_idea = values[0] if values else ""
        goal = values[1] if len(values) > 1 else ""
        context = values[2] if len(values) > 2 else ""
        constraints = _tuple_of_strings(values[3] if len(values) > 3 else ())
        return _normalize_scoring_text(" ".join(_flatten_parts(raw_idea, goal, context, constraints)))

    raw_idea = getattr(input_data, "raw_idea", "")
    goal = getattr(input_data, "goal", "")
    context = getattr(input_data, "context", "")
    constraints = _tuple_of_strings(getattr(input_data, "constraints", ()))
    return _normalize_scoring_text(" ".join(_flatten_parts(raw_idea, goal, context, constraints)))


def _first_mapping_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return ""


def _flatten_parts(*parts: Any) -> tuple[str, ...]:
    flattened: list[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, str):
            cleaned = _clean_text(part)
            if cleaned:
                flattened.append(cleaned)
            continue
        if isinstance(part, Sequence) and not isinstance(part, (bytes, bytearray)):
            flattened.extend(_flatten_parts(*part))
            continue
        cleaned = _clean_text(part)
        if cleaned:
            flattened.append(cleaned)
    return tuple(flattened)


_NEGATED_SELECTION_KEYWORD_WINDOW = 8
_NEGATION_MARKERS = frozenset(("no", "not", "without", "non"))


def _keyword_matches(
    scoring_text: str,
    keyword: str,
    *,
    ignore_negated: bool = False,
) -> bool:
    normalized_keyword = _normalize_scoring_text(keyword)
    if not normalized_keyword:
        return False
    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(normalized_keyword).replace(r"\ ", r"\s+")
        + r"(?![a-z0-9])"
    )
    matches = tuple(re.finditer(pattern, scoring_text))
    if not matches:
        return False
    if not ignore_negated:
        return True
    return any(not _keyword_match_is_negated(scoring_text, match.start()) for match in matches)


def _keyword_match_is_negated(scoring_text: str, match_start: int) -> bool:
    prefix_tokens = scoring_text[:match_start].split()
    if not prefix_tokens:
        return False
    window = prefix_tokens[-_NEGATED_SELECTION_KEYWORD_WINDOW:]
    return any(token in _NEGATION_MARKERS for token in window)


def _canonical_profile_id(profile_id: str) -> str:
    canonical_id = _canonical_identifier(profile_id)
    return ALIASES.get(canonical_id, canonical_id)


def _empty_score_by_profile() -> dict[str, int]:
    return {profile_id: 0 for profile_id in _PROFILE_ORDER}


def _empty_matched_keywords() -> dict[str, tuple[str, ...]]:
    return {profile_id: () for profile_id in _PROFILE_ORDER}


__all__ = [
    "ALIASES",
    "ClaimLens",
    "DomainProfile",
    "DomainProfileSelection",
    "EvidenceNeed",
    "ExperimentTemplate",
    "ReviewerLens",
    "get_profile",
    "list_profiles",
    "resolve_domain_profile",
]
