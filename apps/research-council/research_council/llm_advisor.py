"""Optional LLM augmentation sandbox for Research Council.

This module intentionally does not call an LLM. It provides a deterministic
future integration path where LLM-like suggestions can be generated, validated,
filtered, and merged only as bounded additive metadata after the deterministic
pipeline has produced the source-of-truth result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
import re
from typing import Any


ALLOWED_AUGMENTATION_CATEGORIES = frozenset(
    {
        "additional_risks",
        "additional_questions",
        "additional_experiments",
        "alternative_positioning",
        "optional_caveats",
    }
)


class LLMAugmentationMode(str, Enum):
    """Deterministic-safe augmentation modes."""

    OFF = "off"
    TEST_SAFE = "test_safe"
    TEST_NOISY = "test_noisy"


@dataclass(frozen=True)
class LLMAdvisorConfig:
    """Configuration for the optional augmentation sandbox."""

    mode: LLMAugmentationMode | str = LLMAugmentationMode.OFF
    source: str = "deterministic_fake_advisor"

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _coerce_mode(self.mode))
        source = str(self.source or "").strip() or "deterministic_fake_advisor"
        object.__setattr__(self, "source", source)

    @classmethod
    def from_value(cls, value: "LLMAdvisorConfig | LLMAugmentationMode | str | None") -> "LLMAdvisorConfig":
        if isinstance(value, LLMAdvisorConfig):
            return value
        if value is None:
            return cls()
        return cls(mode=value)


@dataclass(frozen=True)
class LLMInsightBundle:
    """Legacy optional advisory notes that cannot replace deterministic artifacts."""

    observations: tuple[str, ...] = ()
    follow_up_questions: tuple[str, ...] = ()
    evidence_requests: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    confidence_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", _tuple_of_strings(self.observations))
        object.__setattr__(
            self,
            "follow_up_questions",
            _tuple_of_strings(self.follow_up_questions),
        )
        object.__setattr__(
            self,
            "evidence_requests",
            _tuple_of_strings(self.evidence_requests),
        )
        object.__setattr__(self, "risk_flags", _tuple_of_strings(self.risk_flags))
        object.__setattr__(self, "caveats", _tuple_of_strings(self.caveats))
        object.__setattr__(
            self,
            "confidence_notes",
            _tuple_of_strings(self.confidence_notes),
        )


@dataclass(frozen=True)
class LLMAugmentationCandidate:
    """One LLM-like candidate before deterministic validation."""

    category: str
    text: str
    source: str = "deterministic_fake_advisor"

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", str(self.category or "").strip())
        object.__setattr__(self, "text", str(self.text or "").strip())
        object.__setattr__(self, "source", str(self.source or "").strip())


@dataclass(frozen=True)
class ValidatedLLMSuggestion:
    """One validated, filtered, or rejected augmentation candidate."""

    id: str
    category: str
    text: str
    source: str
    validation_result: str
    rejection_reason: str = ""
    profile_id: str = ""
    profile_consistency: str = "checked"

    @property
    def accepted(self) -> bool:
        return self.validation_result == "accepted"

    def accepted_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "validation_result": self.validation_result,
            "profile_id": self.profile_id,
            "profile_consistency": self.profile_consistency,
        }

    def summary_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "source": self.source,
            "validation_result": self.validation_result,
            "rejection_reason": self.rejection_reason,
            "profile_id": self.profile_id,
            "profile_consistency": self.profile_consistency,
        }


@dataclass(frozen=True)
class LLMAugmentationResult:
    """Validated augmentation bundle merged additively into result metadata."""

    mode: LLMAugmentationMode
    source: str
    profile_id: str
    suggestions: tuple[ValidatedLLMSuggestion, ...] = ()

    @property
    def enabled(self) -> bool:
        return self.mode != LLMAugmentationMode.OFF

    @property
    def accepted_count(self) -> int:
        return sum(1 for suggestion in self.suggestions if suggestion.validation_result == "accepted")

    @property
    def filtered_count(self) -> int:
        return sum(1 for suggestion in self.suggestions if suggestion.validation_result == "filtered")

    @property
    def rejected_count(self) -> int:
        return sum(1 for suggestion in self.suggestions if suggestion.validation_result == "rejected")

    def to_metadata(self) -> dict[str, Any]:
        validated_augments: dict[str, list[dict[str, Any]]] = {
            category: [] for category in sorted(ALLOWED_AUGMENTATION_CATEGORIES)
        }
        rejected_augments_summary: list[dict[str, Any]] = []
        for suggestion in self.suggestions:
            if suggestion.accepted:
                validated_augments.setdefault(suggestion.category, []).append(
                    suggestion.accepted_payload()
                )
            else:
                rejected_augments_summary.append(suggestion.summary_payload())

        return {
            "mode": self.mode.value,
            "enabled": self.enabled,
            "source": self.source,
            "profile_id": self.profile_id,
            "validated_augments": validated_augments,
            "rejected_augments_summary": rejected_augments_summary,
            "accepted_count": self.accepted_count,
            "filtered_count": self.filtered_count,
            "rejected_count": self.rejected_count,
            "deterministic_source_of_truth": True,
            "allowed_scopes": sorted(ALLOWED_AUGMENTATION_CATEGORIES),
        }

    @classmethod
    def off(cls, *, source: str = "deterministic_fake_advisor", profile_id: str = "") -> "LLMAugmentationResult":
        return cls(
            mode=LLMAugmentationMode.OFF,
            source=source,
            profile_id=profile_id,
            suggestions=(),
        )


class LLMResearchAdvisor:
    """Future optional collaborator interface.

    Implementations must consume a completed deterministic result and return an
    advisory bundle. They must not mutate claims, evidence, critiques,
    experiments, recommendation, warnings, profile metadata, or quality signals.
    """

    def advise(
        self,
        deterministic_result: Any,
        *,
        domain_profile: Any = None,
    ) -> LLMInsightBundle:
        raise NotImplementedError(
            "LLMResearchAdvisor is an optional future extension and is not wired "
            "into the deterministic Research Council pipeline."
        )


def build_llm_augmentation(
    deterministic_result: Any,
    *,
    input_data: Any,
    domain_profile: Any,
    config: LLMAdvisorConfig | LLMAugmentationMode | str | None = None,
) -> LLMAugmentationResult:
    """Generate and validate deterministic fake LLM-style suggestions."""

    advisor_config = LLMAdvisorConfig.from_value(config)
    profile_id = str(getattr(domain_profile, "id", "") or _profile_id_from_result(deterministic_result))
    if advisor_config.mode == LLMAugmentationMode.OFF:
        return LLMAugmentationResult.off(
            source=advisor_config.source,
            profile_id=profile_id,
        )

    candidates = _fake_advisor_candidates(
        deterministic_result,
        input_data=input_data,
        domain_profile=domain_profile,
        config=advisor_config,
    )
    return validate_llm_suggestions(
        candidates,
        deterministic_result=deterministic_result,
        input_data=input_data,
        domain_profile=domain_profile,
        config=advisor_config,
    )


def validate_llm_suggestions(
    candidates: Sequence[LLMAugmentationCandidate],
    *,
    deterministic_result: Any,
    input_data: Any,
    domain_profile: Any,
    config: LLMAdvisorConfig | LLMAugmentationMode | str | None = None,
) -> LLMAugmentationResult:
    """Validate LLM-like candidates with deterministic safety checks."""

    advisor_config = LLMAdvisorConfig.from_value(config)
    profile_id = str(getattr(domain_profile, "id", "") or _profile_id_from_result(deterministic_result))
    deterministic_text = _deterministic_result_text(deterministic_result)
    seen_accepted: set[str] = set()
    suggestions: list[ValidatedLLMSuggestion] = []
    for index, candidate in enumerate(candidates, start=1):
        validation_result, reason = _validate_candidate(
            candidate,
            deterministic_text=deterministic_text,
            input_data=input_data,
            profile_id=profile_id,
            seen_accepted=seen_accepted,
        )
        if validation_result == "accepted":
            seen_accepted.add(_normalize_text(candidate.text))
        suggestions.append(
            ValidatedLLMSuggestion(
                id=f"llm-augment-{index:03d}",
                category=candidate.category,
                text=candidate.text if validation_result == "accepted" else "",
                source=candidate.source or advisor_config.source,
                validation_result=validation_result,
                rejection_reason=reason,
                profile_id=profile_id,
            )
        )

    return LLMAugmentationResult(
        mode=advisor_config.mode,
        source=advisor_config.source,
        profile_id=profile_id,
        suggestions=tuple(suggestions),
    )


def merge_validated_llm_suggestions(
    deterministic_result: Any,
    augmentation_result: LLMAugmentationResult,
) -> Any:
    """Merge only validated augmentation metadata without overwriting core outputs."""

    return replace(
        deterministic_result,
        optional_llm_augments=augmentation_result.to_metadata(),
    )


def validate_llm_insight_bundle(bundle: LLMInsightBundle) -> tuple[str, ...]:
    """Return deterministic validation issues for a legacy optional LLM bundle."""

    issues: list[str] = []
    combined_text = " ".join(_all_bundle_text(bundle)).lower()
    blocked_phrases = (
        "replace deterministic",
        "override deterministic",
        "source of truth",
        "validated by the llm",
    )
    for phrase in blocked_phrases:
        if phrase in combined_text:
            issues.append(
                f"LLM advisory bundle must not claim deterministic replacement: {phrase}"
            )
    return tuple(issues)


def _fake_advisor_candidates(
    deterministic_result: Any,
    *,
    input_data: Any,
    domain_profile: Any,
    config: LLMAdvisorConfig,
) -> tuple[LLMAugmentationCandidate, ...]:
    profile_id = str(getattr(domain_profile, "id", "") or _profile_id_from_result(deterministic_result))
    candidates = list(_safe_profile_candidates(profile_id, config.source))
    if config.mode == LLMAugmentationMode.TEST_NOISY:
        candidates.extend(
            _noisy_candidates(
                deterministic_result,
                input_data=input_data,
                profile_id=profile_id,
                source=config.source,
            )
        )
    return tuple(candidates)


def _safe_profile_candidates(profile_id: str, source: str) -> tuple[LLMAugmentationCandidate, ...]:
    by_profile: Mapping[str, tuple[tuple[str, str], ...]] = {
        "ai_saas": (
            ("additional_risks", "Additional risk: buyer workflow ownership, retention trigger, reliability expectation, and differentiation may still be weaker than the deterministic evidence gaps suggest."),
            ("additional_questions", "Which buyer owns the workflow, what current substitute is painful, and what retention trigger would make repeat use observable?"),
            ("additional_experiments", "Run a bounded workflow reliability review that scores output quality, repeat usage, and buyer willingness to pay without changing the deterministic recommendation."),
            ("alternative_positioning", "Position narrowly around a repeat buyer workflow before broad AI automation claims."),
            ("optional_caveats", "Keep AI-wrapper differentiation and operational reliability caveats visible until external evidence is supplied."),
        ),
        "developer_tool": (
            ("additional_risks", "Additional risk: developer workflow fit may fail if setup complexity, integration burden, compatibility, and time-to-value are not measured in a real stack."),
            ("additional_questions", "Which developer segment has the repeated workflow pain, and what integration step blocks time-to-value today?"),
            ("additional_experiments", "Run a local setup walkthrough that records installation steps, compatibility issues, integration burden, and repeat-use trigger."),
            ("alternative_positioning", "Position around one high-friction developer workflow rather than a broad developer productivity claim."),
            ("optional_caveats", "Keep setup, compatibility, documentation, and integration caveats separate from the deterministic recommendation."),
        ),
        "enterprise_b2b": (
            ("additional_risks", "Additional risk: procurement path, stakeholder alignment, budget owner clarity, rollout, security/compliance, and ROI proof may block adoption."),
            ("additional_questions", "Who is the budget owner, which stakeholders approve rollout, and what security/compliance evidence is required before procurement?"),
            ("additional_experiments", "Run a stakeholder procurement map that records approval steps, rollout blockers, ROI threshold, and compliance review needs."),
            ("alternative_positioning", "Position as a controlled rollout wedge with explicit budget owner and security/compliance evidence needs."),
            ("optional_caveats", "Keep procurement, rollout, ROI, and compliance caveats additive and separate from final confidence."),
        ),
        "marketplace": (
            ("additional_risks", "Additional risk: liquidity, supply-side acquisition, demand-side acquisition, cold-start path, trust/safety, and transaction frequency may remain unproven."),
            ("additional_questions", "What constrained wedge can prove supply and demand density before expanding the marketplace?"),
            ("additional_experiments", "Run a concierge matching test that records liquidity threshold, cold-start sequence, trust/safety issues, and repeat transaction frequency."),
            ("alternative_positioning", "Position around a narrow marketplace wedge where both supply and demand can be observed."),
            ("optional_caveats", "Keep liquidity, cold-start, trust/safety, and disintermediation caveats separate from deterministic scoring."),
        ),
        "creator_tools": (
            ("additional_risks", "Additional risk: creator retention, content production frequency, audience growth, monetization, and platform dependency may remain unproven."),
            ("additional_questions", "Which creator segment has a repeated production workflow, audience growth loop, and creator-segment willingness to pay?"),
            ("additional_experiments", "Run a creator diary study that records content production cadence, fan/community engagement, monetization path, and platform dependency."),
            ("alternative_positioning", "Position around one creator workflow with a measurable retention trigger before broad creator platform claims."),
            ("optional_caveats", "Keep platform dependency, audience lock-in, churn, and monetization caveats additive and bounded."),
        ),
        "medical_device": (
            ("additional_risks", "Additional risk: intended use, patient safety boundary, clinical validation plan, and regulatory pathway remain unresolved until external evidence exists."),
            ("additional_questions", "What non-clinical validation step can clarify intended use, patient-safety boundary, and regulatory assumptions without claiming efficacy?"),
            ("additional_experiments", "Run a non-clinical safety boundary review that maps intended use, validation evidence needed, and regulatory pathway uncertainty."),
            ("alternative_positioning", "Position as an early evidence-gathering concept with conservative confidence and explicit clinical boundaries."),
            ("optional_caveats", "Keep patient safety, clinical validation, regulatory pathway, and conservative confidence caveats visible."),
        ),
        "general": (
            ("additional_risks", "Additional risk: target user, problem severity, alternatives, and adoption evidence may remain too vague for a strong decision."),
            ("additional_questions", "Which target user has the severe problem, what alternative do they use today, and what adoption evidence would change the decision?"),
            ("additional_experiments", "Run a target-user interview that compares problem severity, alternatives, and adoption trigger."),
            ("alternative_positioning", "Position around one target user and one severe problem before widening the concept."),
            ("optional_caveats", "Keep missing evidence and local-only caveats additive to the deterministic output."),
        ),
    }
    rows = by_profile.get(profile_id, by_profile["general"])
    return tuple(
        LLMAugmentationCandidate(category=category, text=text, source=source)
        for category, text in rows
    )


def _noisy_candidates(
    deterministic_result: Any,
    *,
    input_data: Any,
    profile_id: str,
    source: str,
) -> tuple[LLMAugmentationCandidate, ...]:
    recommendation = getattr(deterministic_result, "recommendation", None)
    duplicate_text = str(getattr(recommendation, "summary", "") or "")
    if profile_id == "medical_device":
        contamination_text = (
            "This is safe for patients, clinically validated, regulatory cleared, "
            "and ready for high confidence."
        )
    elif profile_id == "marketplace":
        contamination_text = (
            "Position around procurement path, enterprise B2B blocker, and "
            "security/compliance requirements instead of marketplace liquidity."
        )
    else:
        contamination_text = (
            "Position around liquidity threshold, marketplace blocker, and "
            "supply-side acquisition instead of the selected profile."
        )
    raw_idea = str(getattr(input_data, "raw_idea", "") or "")
    return (
        LLMAugmentationCandidate("additional_risks", duplicate_text, source),
        LLMAugmentationCandidate(
            "additional_questions",
            f"Can the team restate the raw idea exactly: {raw_idea}",
            source,
        ),
        LLMAugmentationCandidate(
            "optional_caveats",
            "Raise confidence to high because the concept is proven.",
            source,
        ),
        LLMAugmentationCandidate("alternative_positioning", contamination_text, source),
        LLMAugmentationCandidate(
            "final_recommendation",
            "Replace the deterministic recommendation with the advisor recommendation.",
            source,
        ),
    )


def _validate_candidate(
    candidate: LLMAugmentationCandidate,
    *,
    deterministic_text: str,
    input_data: Any,
    profile_id: str,
    seen_accepted: set[str],
) -> tuple[str, str]:
    text = candidate.text.strip()
    normalized_text = _normalize_text(text)
    if candidate.category not in ALLOWED_AUGMENTATION_CATEGORIES:
        return "rejected", "unsupported augmentation scope"
    if _is_empty_or_noisy(normalized_text):
        return "filtered", "empty or noisy suggestion"
    if _contains_hidden_reasoning_request(normalized_text):
        return "rejected", "hidden reasoning request"
    if _contains_raw_input_echo(normalized_text, input_data):
        return "rejected", "raw input echo"
    if profile_id == "medical_device" and _contains_medical_unsafe_claim(normalized_text):
        return "rejected", "unsafe medical claim"
    if _contains_confidence_escalation(normalized_text):
        return "rejected", "unsupported confidence escalation"
    contamination = _profile_contamination_reason(profile_id, normalized_text)
    if contamination:
        return "rejected", contamination
    if _is_duplicate_reasoning(normalized_text, deterministic_text, seen_accepted):
        return "filtered", "duplicate reasoning"
    return "accepted", ""


def _is_empty_or_noisy(normalized_text: str) -> bool:
    if len(normalized_text) < 16:
        return True
    if normalized_text in {"n a", "none", "unknown", "todo"}:
        return True
    return len(set(normalized_text.replace(" ", ""))) < 4


def _contains_hidden_reasoning_request(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in (
            "chain of thought",
            "hidden reasoning",
            "scratchpad",
            "private reasoning",
            "step by step reasoning",
        )
    )


def _contains_confidence_escalation(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in (
            "high confidence",
            "raise confidence",
            "increase confidence",
            "upgrade confidence",
            "override confidence",
            "concept is proven",
            "safe to proceed",
            "replace deterministic",
            "advisor recommendation",
        )
    )


def _contains_medical_unsafe_claim(normalized_text: str) -> bool:
    return any(
        phrase in normalized_text
        for phrase in (
            "safe for patients",
            "clinically validated",
            "regulatory cleared",
            "regulatory clearance achieved",
            "diagnostic accuracy is proven",
            "no clinical validation needed",
            "ready for clinical use",
        )
    )


def _profile_contamination_reason(profile_id: str, normalized_text: str) -> str:
    forbidden_terms = _FORBIDDEN_PROFILE_TERMS.get(profile_id, ())
    matched = [term for term in forbidden_terms if _normalize_text(term) in normalized_text]
    if matched:
        return "profile contamination: " + ", ".join(matched[:3])
    return ""


def _is_duplicate_reasoning(
    normalized_text: str,
    deterministic_text: str,
    seen_accepted: set[str],
) -> bool:
    if normalized_text in seen_accepted:
        return True
    return len(normalized_text) >= 40 and normalized_text in deterministic_text


def _contains_raw_input_echo(normalized_text: str, input_data: Any) -> bool:
    raw_parts = (
        getattr(input_data, "raw_idea", ""),
        getattr(input_data, "goal", ""),
        getattr(input_data, "context", ""),
    )
    for raw_part in raw_parts:
        normalized_part = _normalize_text(raw_part)
        if not normalized_part:
            continue
        if len(normalized_part) >= 24 and normalized_part in normalized_text:
            return True
        tokens = normalized_part.split()
        if len(tokens) >= 7:
            for index in range(0, len(tokens) - 6):
                if " ".join(tokens[index : index + 7]) in normalized_text:
                    return True
    return False


def _deterministic_result_text(result: Any) -> str:
    parts: list[str] = [str(getattr(result, "input_summary", "") or "")]
    parts.extend(str(getattr(claim, "text", "") or "") for claim in getattr(result, "claims", ()))
    parts.extend(str(getattr(claim, "rationale", "") or "") for claim in getattr(result, "claims", ()))
    for entry in getattr(result, "evidence_ledger", ()):
        parts.extend(
            (
                str(getattr(entry, "summary", "") or ""),
                str(getattr(entry, "notes", "") or ""),
                str(getattr(entry, "required_evidence", "") or ""),
                str(getattr(entry, "missing_evidence", "") or ""),
                " ".join(str(item) for item in getattr(entry, "reasoning_trace", ()) or ()),
            )
        )
    parts.extend(str(getattr(critique, "finding", "") or "") for critique in getattr(result, "reviewer_critiques", ()))
    parts.extend(str(getattr(experiment, "title", "") or "") for experiment in getattr(result, "experiments", ()))
    recommendation = getattr(result, "recommendation", None)
    if recommendation is not None:
        parts.extend(
            (
                str(getattr(recommendation, "decision", "") or ""),
                str(getattr(recommendation, "summary", "") or ""),
                str(getattr(recommendation, "next_step", "") or ""),
                str(getattr(recommendation, "rationale", "") or ""),
            )
        )
    parts.extend(str(warning) for warning in getattr(result, "warnings", ()) or ())
    return _normalize_text(" ".join(parts))


def _profile_id_from_result(result: Any) -> str:
    profile = getattr(result, "profile", {}) or {}
    if isinstance(profile, Mapping):
        return str(profile.get("profile_id", "") or "")
    return ""


def _coerce_mode(value: LLMAugmentationMode | str) -> LLMAugmentationMode:
    if isinstance(value, LLMAugmentationMode):
        return value
    normalized = str(value or "").strip().lower().replace("-", "_")
    for mode in LLMAugmentationMode:
        if mode.value == normalized:
            return mode
    allowed = ", ".join(mode.value for mode in LLMAugmentationMode)
    raise ValueError(f"invalid LLM augmentation mode: {value!r}; expected one of {allowed}")


def _all_bundle_text(bundle: LLMInsightBundle) -> tuple[str, ...]:
    return (
        bundle.observations
        + bundle.follow_up_questions
        + bundle.evidence_requests
        + bundle.risk_flags
        + bundle.caveats
        + bundle.confidence_notes
    )


def _tuple_of_strings(values: Sequence[str] | str | None) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    return tuple(str(value).strip() for value in values if str(value).strip())


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_FORBIDDEN_PROFILE_TERMS: Mapping[str, tuple[str, ...]] = {
    "ai_saas": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "liquidity threshold",
        "marketplace blocker",
        "procurement path",
        "enterprise B2B blocker",
        "developer-tool blocker",
        "creator-tools blocker",
    ),
    "developer_tool": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "procurement path",
        "enterprise B2B blocker",
        "liquidity threshold",
        "marketplace blocker",
        "creator-tools blocker",
    ),
    "enterprise_b2b": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "liquidity threshold",
        "marketplace blocker",
        "developer-tool blocker",
        "creator-tools blocker",
    ),
    "marketplace": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "procurement path",
        "security/compliance requirements",
        "enterprise B2B blocker",
        "developer-tool blocker",
        "buyer/workflow integration",
        "generic ai wrapper",
        "creator-tools blocker",
    ),
    "creator_tools": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "liquidity threshold",
        "marketplace blocker",
        "supply-side acquisition",
        "demand-side acquisition",
        "procurement path",
        "security/compliance requirements",
        "enterprise B2B blocker",
        "developer-tool blocker",
        "buyer/workflow integration",
        "generic ai wrapper",
    ),
    "medical_device": (
        "buyer/workflow integration",
        "generic ai wrapper",
        "liquidity threshold",
        "marketplace blocker",
        "developer-tool blocker",
        "enterprise B2B blocker",
        "procurement path",
        "creator-tools blocker",
    ),
    "general": (
        "marketplace blocker",
        "enterprise B2B blocker",
        "developer-tool blocker",
        "creator-tools blocker",
        "patient safety risk unresolved",
        "clinical validation evidence missing",
        "regulatory pathway unclear",
    ),
}


__all__ = [
    "ALLOWED_AUGMENTATION_CATEGORIES",
    "LLMAdvisorConfig",
    "LLMAugmentationCandidate",
    "LLMAugmentationMode",
    "LLMAugmentationResult",
    "LLMInsightBundle",
    "LLMResearchAdvisor",
    "ValidatedLLMSuggestion",
    "build_llm_augmentation",
    "merge_validated_llm_suggestions",
    "validate_llm_insight_bundle",
    "validate_llm_suggestions",
]
