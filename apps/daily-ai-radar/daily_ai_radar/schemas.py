"""Schemas and validation for the Daily AI Radar v0.2 renderer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any


RESULT_TYPE = "daily_ai_radar_result"
VERSION = "0.2"
INPUT_TYPE = "daily_ai_radar_curated_metadata"
DEFAULT_RADAR_DATE = "2026-06-18"

ALLOWED_AREAS = frozenset(
    {
        "agent_skills",
        "memory",
        "orchestration",
        "mcp",
        "a2a",
        "hermes",
        "langgraph",
        "openai_agents",
        "anthropic",
        "evaluation",
        "security",
        "unknown",
    }
)
ALLOWED_RECOMMENDATIONS = frozenset(
    {
        "DO_NOW",
        "WATCH",
        "IGNORE",
        "NEEDS_RESEARCH_COUNCIL",
        "NEEDS_HUMAN_REVIEW",
    }
)
ALLOWED_EVIDENCE_LEVELS = frozenset(
    {
        "unverified_claim",
        "manual_summary",
        "documented_release",
        "local_demo_observed",
        "research_discussion",
        "unknown",
    }
)
REQUIRED_ITEM_FIELDS = (
    "item_id",
    "observed_date",
    "source_name",
    "source_type",
    "source_url_or_ref",
    "title",
    "summary",
    "claimed_capability",
    "area",
    "evidence_level",
    "notes",
)
SCORE_FIELDS = (
    "relevance_to_jarvis",
    "implementation_effort",
    "risk",
    "urgency",
    "maturity",
)
FORBIDDEN_RAW_CONTENT_FIELDS = frozenset(
    {
        "article_body",
        "body",
        "content",
        "document_body",
        "full_content",
        "full_source_body",
        "full_source_text",
        "full_text",
        "raw_body",
        "raw_content",
        "raw_source",
        "source_body",
        "source_full_text",
        "source_text",
        "transcript",
    }
)

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_AREA_DEFAULT_SCORES: dict[str, dict[str, int]] = {
    "agent_skills": {
        "relevance_to_jarvis": 5,
        "implementation_effort": 1,
        "risk": 2,
        "urgency": 4,
        "maturity": 3,
    },
    "memory": {
        "relevance_to_jarvis": 4,
        "implementation_effort": 3,
        "risk": 4,
        "urgency": 3,
        "maturity": 2,
    },
    "orchestration": {
        "relevance_to_jarvis": 4,
        "implementation_effort": 4,
        "risk": 4,
        "urgency": 3,
        "maturity": 2,
    },
    "mcp": {
        "relevance_to_jarvis": 4,
        "implementation_effort": 3,
        "risk": 5,
        "urgency": 4,
        "maturity": 2,
    },
    "a2a": {
        "relevance_to_jarvis": 3,
        "implementation_effort": 4,
        "risk": 4,
        "urgency": 2,
        "maturity": 1,
    },
    "hermes": {
        "relevance_to_jarvis": 5,
        "implementation_effort": 4,
        "risk": 5,
        "urgency": 3,
        "maturity": 1,
    },
    "langgraph": {
        "relevance_to_jarvis": 3,
        "implementation_effort": 4,
        "risk": 3,
        "urgency": 2,
        "maturity": 3,
    },
    "openai_agents": {
        "relevance_to_jarvis": 4,
        "implementation_effort": 3,
        "risk": 3,
        "urgency": 3,
        "maturity": 3,
    },
    "anthropic": {
        "relevance_to_jarvis": 2,
        "implementation_effort": 2,
        "risk": 4,
        "urgency": 2,
        "maturity": 2,
    },
    "evaluation": {
        "relevance_to_jarvis": 4,
        "implementation_effort": 2,
        "risk": 2,
        "urgency": 3,
        "maturity": 3,
    },
    "security": {
        "relevance_to_jarvis": 4,
        "implementation_effort": 3,
        "risk": 5,
        "urgency": 4,
        "maturity": 3,
    },
    "unknown": {
        "relevance_to_jarvis": 2,
        "implementation_effort": 3,
        "risk": 3,
        "urgency": 1,
        "maturity": 1,
    },
}

_SELF_IMPROVEMENT_TERMS = (
    "self-improvement",
    "self improvement",
    "self-modification",
    "self modification",
    "recursive",
    "autonomous",
    "autonomy",
    "skill learning",
    "agent loop",
    "improve itself",
)

_RECOMMENDATION_SAFETY_RANK = {
    "IGNORE": 0,
    "WATCH": 1,
    "DO_NOW": 1,
    "NEEDS_RESEARCH_COUNCIL": 2,
    "NEEDS_HUMAN_REVIEW": 3,
}


class ValidationError(ValueError):
    """Raised when curated radar metadata violates the v0.2 contract."""


@dataclass(frozen=True)
class RadarItem:
    """A normalized Daily AI Radar item."""

    item_id: str
    observed_date: str
    source_name: str
    source_type: str
    source_url_or_ref: str
    title: str
    summary: str
    claimed_capability: str
    area: str
    evidence_level: str
    notes: str
    relevance_to_jarvis: int
    implementation_effort: int
    risk: int
    urgency: int
    maturity: int
    recommendation: str
    recommendation_source: str
    human_approval_required: bool
    research_council_handoff_recommended: bool


@dataclass(frozen=True)
class DailyAIRadarInput:
    """A normalized curated metadata input."""

    radar_date: str
    input_type: str
    items: tuple[RadarItem, ...]
    operator: str = ""
    notes: str = ""


@dataclass(frozen=True)
class DailyAIRadarResult:
    """Deterministic renderer result metadata plus normalized items."""

    radar_date: str
    items: tuple[RadarItem, ...]
    reviewed_items_count: int
    candidate_count: int
    human_approval_required_count: int
    recommended_next_action: str
    unknowns: tuple[str, ...]
    operator: str = ""
    notes: str = ""
    result_type: str = RESULT_TYPE
    version: str = VERSION


def normalize_input(data: Mapping[str, Any], radar_date_override: str | None = None) -> DailyAIRadarInput:
    """Validate and normalize a curated radar input mapping."""

    if not isinstance(data, Mapping):
        raise ValidationError("input must be a JSON object")
    _reject_forbidden_raw_content_fields(data)

    input_type = _optional_text(data, "input_type") or INPUT_TYPE
    if input_type != INPUT_TYPE:
        raise ValidationError(f"input_type must be {INPUT_TYPE}")

    radar_date = _normalize_radar_date(data, radar_date_override)
    operator = _optional_text(data, "operator")
    notes = _optional_text(data, "notes")
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise ValidationError("items must be a list")

    items = tuple(
        sorted(
            (_normalize_item(raw_item, index) for index, raw_item in enumerate(raw_items)),
            key=lambda item: item.item_id,
        )
    )
    return DailyAIRadarInput(
        radar_date=radar_date,
        input_type=input_type,
        operator=operator,
        notes=notes,
        items=items,
    )


def build_result(input_data: DailyAIRadarInput) -> DailyAIRadarResult:
    """Build deterministic result-level metadata from normalized input."""

    candidate_count = sum(1 for item in input_data.items if item.recommendation != "IGNORE")
    human_approval_count = sum(1 for item in input_data.items if item.human_approval_required)
    return DailyAIRadarResult(
        radar_date=input_data.radar_date,
        operator=input_data.operator,
        notes=input_data.notes,
        items=input_data.items,
        reviewed_items_count=len(input_data.items),
        candidate_count=candidate_count,
        human_approval_required_count=human_approval_count,
        recommended_next_action=_recommended_next_action(input_data.items),
        unknowns=_build_unknowns(input_data.items),
    )


def _normalize_radar_date(data: Mapping[str, Any], radar_date_override: str | None) -> str:
    if radar_date_override is not None and radar_date_override.strip():
        radar_date = radar_date_override.strip()
    else:
        radar_date = _optional_text(data, "radar_date") or DEFAULT_RADAR_DATE
    _validate_date("radar_date", radar_date)
    return radar_date


def _normalize_item(raw_item: Any, index: int) -> RadarItem:
    if not isinstance(raw_item, Mapping):
        raise ValidationError(f"items[{index}] must be an object")
    _reject_forbidden_raw_content_fields(raw_item, path=f"items[{index}]")

    values = {field: _required_text(raw_item, field, index) for field in REQUIRED_ITEM_FIELDS}
    _validate_date(f"items[{index}].observed_date", values["observed_date"])
    if values["area"] not in ALLOWED_AREAS:
        raise ValidationError(f"items[{index}].area is invalid: {values['area']}")
    if values["evidence_level"] not in ALLOWED_EVIDENCE_LEVELS:
        raise ValidationError(
            f"items[{index}].evidence_level is invalid: {values['evidence_level']}"
        )

    default_scores = _default_scores(values["area"], values["evidence_level"])
    scores = {
        field: _normalize_score(raw_item, field, default_scores[field], index)
        for field in SCORE_FIELDS
    }
    recommendation, recommendation_source = _normalize_recommendation(raw_item, values, scores, index)
    human_approval_required = _requires_human_approval(values, scores, recommendation)
    research_council_handoff_recommended = recommendation == "NEEDS_RESEARCH_COUNCIL"

    return RadarItem(
        **values,
        **scores,
        recommendation=recommendation,
        recommendation_source=recommendation_source,
        human_approval_required=human_approval_required,
        research_council_handoff_recommended=research_council_handoff_recommended,
    )


def _required_text(raw_item: Mapping[str, Any], field: str, index: int) -> str:
    value = raw_item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"items[{index}].{field} must be a non-empty string")
    return _compact_text(value)


def _optional_text(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string when provided")
    return _compact_text(value)


def _normalize_score(
    raw_item: Mapping[str, Any],
    field: str,
    default_value: int,
    index: int,
) -> int:
    if field not in raw_item or raw_item[field] is None:
        return default_value
    value = raw_item[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"items[{index}].{field} must be an integer from 1 to 5")
    if value < 1 or value > 5:
        raise ValidationError(f"items[{index}].{field} must be between 1 and 5")
    return value


def _normalize_recommendation(
    raw_item: Mapping[str, Any],
    values: Mapping[str, str],
    scores: Mapping[str, int],
    index: int,
) -> tuple[str, str]:
    raw_recommendation = raw_item.get("recommendation")
    if raw_recommendation is not None:
        if not isinstance(raw_recommendation, str) or not raw_recommendation.strip():
            raise ValidationError(f"items[{index}].recommendation must be a non-empty string")
        recommendation = raw_recommendation.strip()
        if recommendation not in ALLOWED_RECOMMENDATIONS:
            raise ValidationError(
                f"items[{index}].recommendation is invalid: {recommendation}"
            )
        safety_gate = _safety_gate_recommendation(values, scores)
        if safety_gate and _is_less_conservative(recommendation, safety_gate):
            return safety_gate, "safety_override"
        return recommendation, "explicit"
    return _recommend(values, scores), "computed"


def _recommend(values: Mapping[str, str], scores: Mapping[str, int]) -> str:
    area = values["area"]
    relevance = scores["relevance_to_jarvis"]
    risk = scores["risk"]
    maturity = scores["maturity"]

    safety_gate = _safety_gate_recommendation(values, scores)
    if safety_gate:
        return safety_gate
    if relevance <= 2:
        return "IGNORE"
    if relevance >= 4 and maturity >= 3 and risk <= 3:
        return "DO_NOW"
    if relevance >= 3:
        return "WATCH"
    return "IGNORE"


def _safety_gate_recommendation(
    values: Mapping[str, str],
    scores: Mapping[str, int],
) -> str | None:
    area = values["area"]
    relevance = scores["relevance_to_jarvis"]
    risk = scores["risk"]
    if area in {"security", "mcp"} and risk >= 3:
        return "NEEDS_HUMAN_REVIEW"
    if _is_self_improvement_related(values) and risk >= 3:
        return "NEEDS_RESEARCH_COUNCIL"
    if risk >= 4 and relevance >= 4:
        return "NEEDS_HUMAN_REVIEW"
    return None


def _is_less_conservative(recommendation: str, safety_gate: str) -> bool:
    return _RECOMMENDATION_SAFETY_RANK[recommendation] < _RECOMMENDATION_SAFETY_RANK[safety_gate]


def _requires_human_approval(
    values: Mapping[str, str],
    scores: Mapping[str, int],
    recommendation: str,
) -> bool:
    if recommendation == "IGNORE":
        return False
    if recommendation in {"NEEDS_HUMAN_REVIEW", "NEEDS_RESEARCH_COUNCIL"}:
        return True
    if scores["risk"] >= 4:
        return True
    if values["area"] in {"mcp", "a2a", "hermes", "openai_agents", "security"}:
        return True
    return False


def _default_scores(area: str, evidence_level: str) -> dict[str, int]:
    scores = dict(_AREA_DEFAULT_SCORES[area])
    if evidence_level == "unverified_claim":
        scores["maturity"] = min(scores["maturity"], 1)
        scores["risk"] = min(5, max(scores["risk"], 3))
    elif evidence_level == "local_demo_observed":
        scores["maturity"] = min(5, max(scores["maturity"], 4))
    elif evidence_level == "documented_release":
        scores["maturity"] = min(5, max(scores["maturity"], 3))
    elif evidence_level == "unknown":
        scores["maturity"] = min(scores["maturity"], 1)
    return scores


def _recommended_next_action(items: Sequence[RadarItem]) -> str:
    if any(item.recommendation == "NEEDS_HUMAN_REVIEW" for item in items):
        return "Review high-risk candidates with a human before implementation planning."
    if any(item.recommendation == "NEEDS_RESEARCH_COUNCIL" for item in items):
        return "Send Research Council candidates for evidence and experiment review."
    if any(item.recommendation == "DO_NOW" for item in items):
        return "Proceed only with documentation or review actions for DO_NOW candidates."
    if any(item.recommendation == "WATCH" for item in items):
        return "Keep watch items visible for later review."
    return "No Jarvis action is recommended from this curated metadata."


def _build_unknowns(items: Sequence[RadarItem]) -> tuple[str, ...]:
    unknowns = [
        "Whether manually supplied metadata represents a current real-world release, discussion, or fixture is outside this renderer.",
        "Whether candidates have enough evidence for adoption requires separate review.",
    ]
    if any(item.risk >= 4 for item in items):
        unknowns.append(
            "Security, permission, autonomy, or orchestration risk requires human approval before implementation."
        )
    if any(item.research_council_handoff_recommended for item in items):
        unknowns.append(
            "Research Council handoff recommendations are descriptive and are not invoked automatically."
        )
    return tuple(unknowns)


def _is_self_improvement_related(values: Mapping[str, str]) -> bool:
    if values["area"] == "hermes":
        return True
    searchable = " ".join(
        values[field]
        for field in ("title", "summary", "claimed_capability", "notes")
    ).lower()
    return any(term in searchable for term in _SELF_IMPROVEMENT_TERMS)


def _validate_date(field_name: str, value: str) -> None:
    if not _DATE_PATTERN.fullmatch(value):
        raise ValidationError(f"{field_name} must use YYYY-MM-DD")


def _compact_text(value: str) -> str:
    return " ".join(value.strip().split())


def _reject_forbidden_raw_content_fields(value: Any, path: str = "input") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in FORBIDDEN_RAW_CONTENT_FIELDS:
                raise ValidationError(f"{path}.{key_text} is not allowed; store source metadata only")
            _reject_forbidden_raw_content_fields(item, f"{path}.{key_text}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_forbidden_raw_content_fields(item, f"{path}[{index}]")
