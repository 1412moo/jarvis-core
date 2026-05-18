"""Stable v0.1 schemas for the Research Council app.

These dataclasses are intentionally small and standard-library only. They define
the app contract without integrating with Jarvis adapters, task memory, or global
report flows.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal


CLAIM_SOURCE_LABELS = frozenset({"user_provided", "extracted", "assumed", "needs_evidence"})
EVIDENCE_TYPES = frozenset({"provided", "missing"})
SEVERITY_LEVELS = frozenset({"low", "medium", "high"})
CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})
EVIDENCE_CONFIDENCE_IMPACTS = frozenset(
    {"confidence_supporting", "confidence_limiter", "confidence_blocker"}
)

ClaimSourceLabel = Literal["user_provided", "extracted", "assumed", "needs_evidence"]
EvidenceType = Literal["provided", "missing"]
SeverityLevel = Literal["low", "medium", "high"]
ConfidenceLevel = Literal["low", "medium", "high"]


def _tuple_of_strings(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(str(value).strip() for value in values if str(value).strip())


def _require_non_empty(field_name: str, value: str) -> None:
    if not str(value).strip():
        raise ValueError(f"{field_name} must be non-empty")


@dataclass(frozen=True)
class ResearchCouncilInput:
    """Input for a local Research Council run."""

    raw_idea: str
    goal: str
    context: str | None = None
    constraints: tuple[str, ...] = ()
    provided_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty("raw_idea", self.raw_idea)
        _require_non_empty("goal", self.goal)
        object.__setattr__(self, "raw_idea", self.raw_idea.strip())
        object.__setattr__(self, "goal", self.goal.strip())
        object.__setattr__(self, "context", self.context.strip() if self.context else None)
        object.__setattr__(self, "constraints", _tuple_of_strings(self.constraints))
        object.__setattr__(self, "provided_evidence", _tuple_of_strings(self.provided_evidence))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Claim:
    """A structured research claim."""

    id: str
    text: str
    source_label: ClaimSourceLabel
    confidence: ConfidenceLevel
    rationale: str

    def __post_init__(self) -> None:
        _require_non_empty("id", self.id)
        _require_non_empty("text", self.text)
        _require_non_empty("rationale", self.rationale)
        if self.source_label not in CLAIM_SOURCE_LABELS:
            raise ValueError(f"invalid claim source_label: {self.source_label}")
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"invalid claim confidence: {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceEntry:
    """A ledger entry describing provided or missing evidence for a claim."""

    id: str
    claim_id: str
    evidence_type: EvidenceType
    summary: str
    reference_label: str | None = None
    notes: str = ""
    required_evidence: str = ""
    missing_evidence: str = ""
    validation_experiment: str = ""
    confidence_impact: str = ""
    reasoning_trace: tuple[str, ...] = ()
    trace_category: str = ""
    trace_severity: str = ""

    def __post_init__(self) -> None:
        _require_non_empty("id", self.id)
        _require_non_empty("claim_id", self.claim_id)
        _require_non_empty("summary", self.summary)
        if self.evidence_type not in EVIDENCE_TYPES:
            raise ValueError(f"invalid evidence_type: {self.evidence_type}")
        if self.evidence_type == "missing" and self.reference_label:
            raise ValueError("missing evidence entries must not include a reference_label")
        object.__setattr__(self, "required_evidence", str(self.required_evidence or "").strip())
        object.__setattr__(self, "missing_evidence", str(self.missing_evidence or "").strip())
        object.__setattr__(
            self,
            "validation_experiment",
            str(self.validation_experiment or "").strip(),
        )
        object.__setattr__(self, "confidence_impact", str(self.confidence_impact or "").strip())
        if (
            self.confidence_impact
            and self.confidence_impact not in EVIDENCE_CONFIDENCE_IMPACTS
        ):
            raise ValueError(f"invalid evidence confidence_impact: {self.confidence_impact}")
        object.__setattr__(self, "reasoning_trace", _tuple_of_strings(self.reasoning_trace))
        object.__setattr__(self, "trace_category", str(self.trace_category or "").strip())
        object.__setattr__(self, "trace_severity", str(self.trace_severity or "").strip())
        if self.trace_severity and self.trace_severity not in SEVERITY_LEVELS:
            raise ValueError(f"invalid evidence trace_severity: {self.trace_severity}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewerCritique:
    """Deterministic reviewer feedback for a claim or full result."""

    id: str
    reviewer_role: str
    claim_id: str | None
    finding: str
    severity: SeverityLevel
    suggested_action: str

    def __post_init__(self) -> None:
        _require_non_empty("id", self.id)
        _require_non_empty("reviewer_role", self.reviewer_role)
        _require_non_empty("finding", self.finding)
        _require_non_empty("suggested_action", self.suggested_action)
        if self.severity not in SEVERITY_LEVELS:
            raise ValueError(f"invalid critique severity: {self.severity}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExperimentPlan:
    """A minimum viable experiment proposal."""

    id: str
    title: str
    hypothesis_claim_ids: tuple[str, ...]
    method: str
    success_metric: str
    minimum_sample: str
    risk: str

    def __post_init__(self) -> None:
        _require_non_empty("id", self.id)
        _require_non_empty("title", self.title)
        _require_non_empty("method", self.method)
        _require_non_empty("success_metric", self.success_metric)
        _require_non_empty("minimum_sample", self.minimum_sample)
        _require_non_empty("risk", self.risk)
        object.__setattr__(self, "hypothesis_claim_ids", _tuple_of_strings(self.hypothesis_claim_ids))
        if not self.hypothesis_claim_ids:
            raise ValueError("hypothesis_claim_ids must include at least one claim id")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Recommendation:
    """The recommended next action after the v0.1 research pass."""

    decision: str
    summary: str
    next_step: str
    rationale: str

    def __post_init__(self) -> None:
        _require_non_empty("decision", self.decision)
        _require_non_empty("summary", self.summary)
        _require_non_empty("next_step", self.next_step)
        _require_non_empty("rationale", self.rationale)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarkdownReport:
    """Markdown report artifact returned by the pipeline."""

    title: str
    markdown: str
    artifact_type: str = "markdown"

    def __post_init__(self) -> None:
        _require_non_empty("title", self.title)
        _require_non_empty("markdown", self.markdown)
        if self.artifact_type != "markdown":
            raise ValueError("artifact_type must be markdown")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchCouncilResult:
    """Complete Research Council v0.1 pipeline result."""

    input_summary: str
    claims: tuple[Claim, ...]
    evidence_ledger: tuple[EvidenceEntry, ...]
    reviewer_critiques: tuple[ReviewerCritique, ...]
    experiments: tuple[ExperimentPlan, ...]
    recommendation: Recommendation
    markdown_report: MarkdownReport
    warnings: tuple[str, ...] = ()
    profile: dict[str, Any] | None = None
    optional_llm_augments: dict[str, Any] | None = None
    result_type: str = "research_council_result"
    version: str = "0.1"

    def __post_init__(self) -> None:
        _require_non_empty("input_summary", self.input_summary)
        if self.result_type != "research_council_result":
            raise ValueError("result_type must be research_council_result")
        if self.version != "0.1":
            raise ValueError("version must be 0.1")
        object.__setattr__(self, "claims", tuple(self.claims))
        object.__setattr__(self, "evidence_ledger", tuple(self.evidence_ledger))
        object.__setattr__(self, "reviewer_critiques", tuple(self.reviewer_critiques))
        object.__setattr__(self, "experiments", tuple(self.experiments))
        object.__setattr__(self, "profile", _normalize_profile_metadata(self.profile))
        object.__setattr__(
            self,
            "optional_llm_augments",
            _normalize_optional_llm_augments(self.optional_llm_augments),
        )
        object.__setattr__(self, "warnings", _tuple_of_strings(self.warnings))
        if not self.claims:
            raise ValueError("claims must include at least one item")
        if not self.evidence_ledger:
            raise ValueError("evidence_ledger must include at least one item")
        if not self.reviewer_critiques:
            raise ValueError("reviewer_critiques must include at least one item")
        if not self.experiments:
            raise ValueError("experiments must include at least one item")
        self._validate_evidence_claim_links()

    def _validate_evidence_claim_links(self) -> None:
        claim_ids = {claim.id for claim in self.claims}
        for entry in self.evidence_ledger:
            if entry.claim_id not in claim_ids:
                raise ValueError(f"evidence entry references unknown claim: {entry.claim_id}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_profile_metadata(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("profile must be an object")
    if not value:
        return {}

    profile_id = str(value.get("profile_id", "")).strip()
    selected_by = str(value.get("selected_by", "")).strip()
    matched_keywords = value.get("matched_keywords", {})
    score_by_profile = value.get("score_by_profile", {})
    reasoning_policy = value.get("reasoning_policy", {})
    if not profile_id:
        raise ValueError("profile.profile_id must be non-empty")
    if not selected_by:
        raise ValueError("profile.selected_by must be non-empty")
    if not isinstance(matched_keywords, Mapping):
        raise ValueError("profile.matched_keywords must be an object")
    if not isinstance(score_by_profile, Mapping):
        raise ValueError("profile.score_by_profile must be an object")
    if not isinstance(reasoning_policy, Mapping):
        raise ValueError("profile.reasoning_policy must be an object")

    return {
        "profile_id": profile_id,
        "selected_by": selected_by,
        "matched_keywords": {
            str(profile_key): _tuple_of_strings(_coerce_keyword_sequence(keywords))
            for profile_key, keywords in matched_keywords.items()
        },
        "score_by_profile": {
            str(profile_key): int(score)
            for profile_key, score in score_by_profile.items()
        },
        "reasoning_policy": {
            str(policy_key): _tuple_of_strings(_coerce_keyword_sequence(policy_values))
            for policy_key, policy_values in reasoning_policy.items()
        },
    }


def _normalize_optional_llm_augments(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value in (None, {}):
        return _off_llm_augments()
    if not isinstance(value, Mapping):
        raise ValueError("optional_llm_augments must be an object")

    mode = str(value.get("mode", "off")).strip() or "off"
    enabled = bool(value.get("enabled", mode != "off"))
    source = str(value.get("source", "")).strip()
    profile_id = str(value.get("profile_id", "")).strip()
    validated_augments = value.get("validated_augments", {})
    rejected_augments_summary = value.get("rejected_augments_summary", ())
    allowed_scopes = value.get("allowed_scopes", ())

    if not isinstance(validated_augments, Mapping):
        raise ValueError("optional_llm_augments.validated_augments must be an object")
    if isinstance(rejected_augments_summary, (str, bytes)) or not isinstance(
        rejected_augments_summary, (tuple, list)
    ):
        raise ValueError(
            "optional_llm_augments.rejected_augments_summary must be a list"
        )

    return {
        "mode": mode,
        "enabled": enabled,
        "source": source,
        "profile_id": profile_id,
        "validated_augments": {
            str(category): _normalize_metadata_items(items)
            for category, items in validated_augments.items()
        },
        "rejected_augments_summary": _normalize_metadata_items(rejected_augments_summary),
        "accepted_count": int(value.get("accepted_count", 0)),
        "filtered_count": int(value.get("filtered_count", 0)),
        "rejected_count": int(value.get("rejected_count", 0)),
        "deterministic_source_of_truth": bool(
            value.get("deterministic_source_of_truth", True)
        ),
        "allowed_scopes": _tuple_of_strings(_coerce_keyword_sequence(allowed_scopes)),
    }


def _off_llm_augments() -> dict[str, Any]:
    return {
        "mode": "off",
        "enabled": False,
        "source": "deterministic_fake_advisor",
        "profile_id": "",
        "validated_augments": {},
        "rejected_augments_summary": (),
        "accepted_count": 0,
        "filtered_count": 0,
        "rejected_count": 0,
        "deterministic_source_of_truth": True,
        "allowed_scopes": (),
    }


def _normalize_metadata_items(value: Any) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        value = (value,)
    if isinstance(value, (str, bytes)) or not isinstance(value, (tuple, list)):
        raise ValueError("optional LLM augmentation metadata items must be a list")
    normalized_items: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("optional LLM augmentation metadata item must be an object")
        normalized_items.append({str(key): _normalize_metadata_value(item_value) for key, item_value in item.items()})
    return tuple(normalized_items)


def _normalize_metadata_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_metadata_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(_normalize_metadata_value(item) for item in value)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _coerce_keyword_sequence(value: Any) -> tuple[str, ...] | list[str] | None:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)
