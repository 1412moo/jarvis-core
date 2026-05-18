"""JSON export helpers for Research Council results.

The helpers in this module only serialize already-built deterministic artifacts.
They do not perform web search, network calls, LLM calls, citation lookup, or any
other evidence collection.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import MISSING, fields, is_dataclass
import json
from pathlib import Path
import re
from typing import Any

from .domain_profiles import get_profile
from .schemas import (
    Claim,
    EvidenceEntry,
    ExperimentPlan,
    MarkdownReport,
    Recommendation,
    ResearchCouncilResult,
    ReviewerCritique,
)


def result_to_json_dict(
    result: ResearchCouncilResult,
    *,
    profile: Any | None = None,
    domain_profile: Any | None = None,
) -> dict[str, Any]:
    """Return a deterministic, schema-aligned JSON-ready result dictionary."""

    profile_metadata = _profile_metadata(profile or getattr(result, "profile", None))
    payload = {
        "result_type": result.result_type,
        "version": result.version,
        "profile": profile_metadata,
        "input_summary": result.input_summary,
        "claims": [_to_jsonable(claim) for claim in result.claims],
        "evidence_ledger": [_to_jsonable(entry) for entry in result.evidence_ledger],
        "reviewer_critiques": [
            _to_jsonable(critique) for critique in result.reviewer_critiques
        ],
        "experiments": [_to_jsonable(experiment) for experiment in result.experiments],
        "recommendation": _to_jsonable(result.recommendation),
        "quality_signals": _build_quality_signals(result, profile_metadata),
        "markdown_report": _to_jsonable(result.markdown_report),
        "warnings": list(result.warnings),
    }
    if domain_profile is not None:
        payload["domain_profile"] = _to_jsonable(domain_profile)
    return payload


def result_to_artifacts_dict(
    result: ResearchCouncilResult,
    *,
    profile: Any | None = None,
    domain_profile: Any | None = None,
) -> dict[str, Any]:
    """Return a compact artifact bundle with Markdown as plain text.

    This keeps the user-facing artifact names prominent while preserving the
    Markdown artifact metadata separately. Profile-selection metadata is exposed
    under ``profile``. If a caller supplies a legacy domain profile, all of its
    dataclass fields are carried through unchanged under ``domain_profile``.
    """

    payload = result_to_json_dict(
        result,
        profile=profile,
        domain_profile=domain_profile,
    )
    markdown_report = payload["markdown_report"]
    payload["markdown_report"] = markdown_report["markdown"]
    payload["markdown_report_artifact"] = {
        "title": markdown_report["title"],
        "artifact_type": markdown_report["artifact_type"],
    }
    return payload


def result_to_json(
    result: ResearchCouncilResult,
    *,
    profile: Any | None = None,
    domain_profile: Any | None = None,
    indent: int = 2,
) -> str:
    """Serialize a ResearchCouncilResult to deterministic JSON text."""

    return json.dumps(
        result_to_json_dict(
            result,
            profile=profile,
            domain_profile=domain_profile,
        ),
        ensure_ascii=False,
        indent=indent,
    ) + "\n"


def artifacts_to_json(
    result: ResearchCouncilResult,
    *,
    profile: Any | None = None,
    domain_profile: Any | None = None,
    indent: int = 2,
) -> str:
    """Serialize compact Research Council artifacts to deterministic JSON text."""

    return json.dumps(
        result_to_artifacts_dict(
            result,
            profile=profile,
            domain_profile=domain_profile,
        ),
        ensure_ascii=False,
        indent=indent,
    ) + "\n"


def write_result_json(
    result: ResearchCouncilResult,
    output_path: str | Path,
    *,
    profile: Any | None = None,
    domain_profile: Any | None = None,
    indent: int = 2,
) -> Path:
    """Write a ResearchCouncilResult JSON artifact and return the path."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        result_to_json(
            result,
            profile=profile,
            domain_profile=domain_profile,
            indent=indent,
        ),
        encoding="utf-8",
    )
    return path


def result_from_json(text: str) -> ResearchCouncilResult:
    """Load a ResearchCouncilResult from JSON text produced by these helpers."""

    payload = json.loads(text)
    if not isinstance(payload, Mapping):
        raise ValueError("Research Council JSON must contain an object")
    return result_from_json_dict(payload)


def result_from_json_dict(payload: Mapping[str, Any]) -> ResearchCouncilResult:
    """Rehydrate and validate a ResearchCouncilResult from a JSON dictionary."""

    markdown_report = _coerce_markdown_report(payload)
    return ResearchCouncilResult(
        input_summary=_require_string(payload, "input_summary"),
        claims=tuple(_coerce_items(payload, "claims", Claim)),
        evidence_ledger=tuple(_coerce_items(payload, "evidence_ledger", EvidenceEntry)),
        reviewer_critiques=tuple(
            _coerce_items(payload, "reviewer_critiques", ReviewerCritique)
        ),
        experiments=tuple(_coerce_items(payload, "experiments", ExperimentPlan)),
        recommendation=_coerce_dataclass(
            _require_mapping(payload, "recommendation"), Recommendation
        ),
        markdown_report=markdown_report,
        profile=_coerce_profile(payload.get("profile", {})),
        warnings=tuple(str(warning) for warning in payload.get("warnings", ())),
        result_type=str(payload.get("result_type", "research_council_result")),
        version=str(payload.get("version", "0.1")),
    )


def _coerce_markdown_report(payload: Mapping[str, Any]) -> MarkdownReport:
    value = payload.get("markdown_report")
    if isinstance(value, Mapping):
        return _coerce_dataclass(value, MarkdownReport)
    if isinstance(value, str):
        artifact = payload.get("markdown_report_artifact")
        artifact_mapping = artifact if isinstance(artifact, Mapping) else {}
        return MarkdownReport(
            title=str(artifact_mapping.get("title", "Research Council Report")),
            markdown=value,
            artifact_type=str(artifact_mapping.get("artifact_type", "markdown")),
        )
    raise ValueError("markdown_report must be a MarkdownReport object or markdown string")


def _coerce_items(
    payload: Mapping[str, Any],
    field_name: str,
    item_type: type[Any],
) -> tuple[Any, ...]:
    raw_items = payload.get(field_name)
    if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
        raise ValueError(f"{field_name} must be a list")
    return tuple(_coerce_dataclass(item, item_type) for item in raw_items)


def _coerce_dataclass(value: Any, item_type: type[Any]) -> Any:
    if isinstance(value, item_type):
        return value
    if not isinstance(value, Mapping):
        raise ValueError(f"{item_type.__name__} must be an object")
    field_names = {field.name for field in fields(item_type)}
    kwargs = {name: value[name] for name in field_names if name in value}
    missing_names = {
        field.name
        for field in fields(item_type)
        if field.default is MISSING
        and field.default_factory is MISSING
        and field.name not in kwargs
    }
    if missing_names:
        joined = ", ".join(sorted(missing_names))
        raise ValueError(f"{item_type.__name__} missing required fields: {joined}")
    return item_type(**kwargs)


def _require_mapping(payload: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    value = payload.get(field_name)
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _coerce_profile(value: Any) -> Mapping[str, Any] | None:
    if value in (None, {}):
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("profile must be an object")
    return value


def _profile_metadata(value: Any) -> dict[str, Any]:
    if value in (None, {}):
        return {}
    if isinstance(value, Mapping):
        return _profile_metadata_from_mapping(value)
    selected_profile = getattr(value, "selected_profile", None) or getattr(value, "profile", None)
    if selected_profile is not None:
        return {
            "profile_id": str(getattr(selected_profile, "id", "")),
            "selected_by": str(getattr(value, "selected_by", "")),
            "matched_keywords": _to_jsonable(getattr(value, "matched_keywords", {})),
            "score_by_profile": _to_jsonable(getattr(value, "score_by_profile", {})),
            "reasoning_policy": _reasoning_policy_from_profile(selected_profile),
        }
    return _profile_metadata_from_mapping(_to_jsonable(value))


def _profile_metadata_from_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    if "profile_id" not in value and "selected_profile" in value:
        selected_profile = value.get("selected_profile")
        selected_profile_id = (
            selected_profile.get("id", "")
            if isinstance(selected_profile, Mapping)
            else getattr(selected_profile, "id", "")
        )
        reasoning_policy = value.get("reasoning_policy") or _reasoning_policy_from_profile(
            selected_profile
        )
        return {
            "profile_id": str(selected_profile_id),
            "selected_by": str(value.get("selected_by", "")),
            "matched_keywords": _to_jsonable(value.get("matched_keywords", {})),
            "score_by_profile": _to_jsonable(value.get("score_by_profile", {})),
            "reasoning_policy": _to_jsonable(reasoning_policy),
        }
    return {
        "profile_id": str(value.get("profile_id", "")),
        "selected_by": str(value.get("selected_by", "")),
        "matched_keywords": _to_jsonable(value.get("matched_keywords", {})),
        "score_by_profile": _to_jsonable(value.get("score_by_profile", {})),
        "reasoning_policy": _to_jsonable(value.get("reasoning_policy", {})),
    }


def _build_quality_signals(
    result: ResearchCouncilResult,
    profile_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    profile = _profile_from_metadata(profile_metadata)
    result_text = _normalized_result_text(result)
    return {
        "profile_adherence": _profile_adherence_signal(profile, result_text),
        "evidence_coverage": _evidence_coverage_signal(result),
        "risk_specificity": _risk_specificity_signal(profile, result_text),
        "next_step_actionability": _next_step_actionability_signal(result),
        "caveat_appropriateness": _caveat_appropriateness_signal(
            profile_metadata,
            result_text,
            result.warnings,
        ),
    }


def _profile_adherence_signal(profile: Any, result_text: str) -> dict[str, Any]:
    terms = _policy_terms(
        profile,
        (
            "council_lenses",
            "reasoning_priorities",
            "evidence_expectations",
            "output_guidance",
        ),
    )
    matched_terms = _matched_terms(result_text, terms)
    score = min(4, len(matched_terms))
    status = "strong" if score >= 4 else "partial" if score >= 2 else "weak"
    return _quality_signal(
        status=status,
        score=score,
        matched_terms=matched_terms,
        rationale=(
            "Deterministic check for profile policy terms appearing in claims, "
            "evidence gaps, critiques, experiments, recommendation, or caveats."
        ),
    )


def _evidence_coverage_signal(result: ResearchCouncilResult) -> dict[str, Any]:
    claim_ids = {claim.id for claim in result.claims}
    covered_claim_ids = {entry.claim_id for entry in result.evidence_ledger}
    missing_entries = [
        entry for entry in result.evidence_ledger if entry.evidence_type == "missing"
    ]
    has_gap_categories = any("gap_category=" in entry.notes for entry in missing_entries)
    all_claims_covered = bool(claim_ids) and claim_ids <= covered_claim_ids
    score = int(all_claims_covered) + int(bool(missing_entries)) + int(has_gap_categories)
    status = "strong" if score == 3 else "partial" if score >= 1 else "weak"
    return _quality_signal(
        status=status,
        score=score,
        matched_terms=(
            "all_claims_covered" if all_claims_covered else "claims_missing_coverage",
            "explicit_missing_evidence" if missing_entries else "no_missing_entries",
            "gap_categories_present" if has_gap_categories else "gap_categories_missing",
        ),
        rationale=(
            "Deterministic check that every claim has ledger coverage and unsupported "
            "claims remain explicit as categorized missing evidence."
        ),
        details={
            "claim_count": len(claim_ids),
            "covered_claim_count": len(claim_ids & covered_claim_ids),
            "missing_evidence_count": len(missing_entries),
        },
    )


def _risk_specificity_signal(profile: Any, result_text: str) -> dict[str, Any]:
    terms = _policy_terms(profile, ("risk_factors", "decision_heuristics"))
    if not terms:
        terms = (
            "feasibility",
            "safety",
            "adoption",
            "prior art",
            "market",
            "regulatory",
        )
    matched_terms = _matched_terms(result_text, terms)
    score = min(4, len(matched_terms))
    status = "strong" if score >= 3 else "partial" if score >= 1 else "weak"
    return _quality_signal(
        status=status,
        score=score,
        matched_terms=matched_terms,
        rationale="Deterministic check that risk language is profile-specific, not generic.",
    )


def _next_step_actionability_signal(result: ResearchCouncilResult) -> dict[str, Any]:
    raw_next_step = str(result.recommendation.next_step or "").lower()
    next_step = _normalize_text(result.recommendation.next_step)
    experiment_ids = tuple(experiment.id for experiment in result.experiments)
    selected_experiment_ids = tuple(
        experiment_id for experiment_id in experiment_ids if experiment_id in raw_next_step
    )
    action_terms = _matched_terms(
        next_step,
        ("run", "create", "capture", "score", "map", "write", "address"),
    )
    score = (
        int(bool(next_step))
        + int(bool(selected_experiment_ids))
        + int(bool(action_terms))
        + int(any(term in next_step for term in ("threshold", "rubric", "trigger", "boundary")))
    )
    status = "strong" if score >= 3 else "partial" if score >= 1 else "weak"
    return _quality_signal(
        status=status,
        score=score,
        matched_terms=selected_experiment_ids + action_terms,
        rationale=(
            "Deterministic check that the recommendation names an experiment or concrete "
            "action with decision-relevant detail."
        ),
    )


def _caveat_appropriateness_signal(
    profile_metadata: Mapping[str, Any],
    result_text: str,
    warnings: Sequence[str],
) -> dict[str, Any]:
    profile_id = str(profile_metadata.get("profile_id", ""))
    warning_text = _normalize_text(" ".join(warnings))
    expected_terms = _expected_caveat_terms(profile_id)
    matched_terms = _matched_terms(f"{warning_text} {result_text}", expected_terms)
    has_standard_warning = "no web search" in warning_text and "no citations" in warning_text
    score = min(4, len(matched_terms) + int(has_standard_warning))
    status = "strong" if score >= 3 else "partial" if score >= 1 else "weak"
    return _quality_signal(
        status=status,
        score=score,
        matched_terms=(
            ("standard_local_only_caveat",) if has_standard_warning else ()
        )
        + matched_terms,
        rationale=(
            "Deterministic check that local-only caveats and domain-specific caveats "
            "match the selected profile."
        ),
    )


def _quality_signal(
    *,
    status: str,
    score: int,
    matched_terms: Sequence[str],
    rationale: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "score": score,
        "matched_terms": list(matched_terms),
        "rationale": rationale,
    }
    if details:
        payload["details"] = _to_jsonable(details)
    return payload


def _profile_from_metadata(profile_metadata: Mapping[str, Any]) -> Any | None:
    profile_id = str(profile_metadata.get("profile_id", "")).strip()
    if not profile_id:
        return None
    try:
        return get_profile(profile_id)
    except ValueError:
        return None


def _policy_terms(profile: Any, field_names: Sequence[str]) -> tuple[str, ...]:
    if profile is None:
        return ()
    terms: list[str] = []
    for field_name in field_names:
        for value in getattr(profile, field_name, ()):
            terms.extend(_term_fragments(str(value)))
    return _dedupe(terms)


def _reasoning_policy_from_profile(profile: Any) -> dict[str, Any]:
    field_names = (
        "council_lenses",
        "reasoning_priorities",
        "risk_factors",
        "evidence_expectations",
        "decision_heuristics",
        "output_guidance",
        "confidence_policy",
        "caveat_policy",
        "next_step_policy",
    )
    return {
        field_name: _to_jsonable(
            profile.get(field_name, ()) if isinstance(profile, Mapping) else getattr(profile, field_name, ())
        )
        for field_name in field_names
    }


def _expected_caveat_terms(profile_id: str) -> tuple[str, ...]:
    if profile_id == "medical_device":
        return (
            "patient safety",
            "clinical validation",
            "clinical efficacy",
            "diagnostic performance",
            "regulatory clearance",
            "human testing",
        )
    if profile_id == "ai_saas":
        return (
            "buyer workflow",
            "repeat usage",
            "differentiation",
            "ai wrapper",
            "operational reliability",
            "willingness to pay",
            "legal advice",
        )
    if profile_id == "developer_tool":
        return (
            "developer workflow",
            "setup complexity",
            "integration cost",
            "ecosystem compatibility",
            "observability",
            "documentation burden",
            "switching cost",
            "time to value",
            "repeat usage",
        )
    if profile_id == "enterprise_b2b":
        return (
            "procurement path",
            "budget owner",
            "security compliance",
            "stakeholder alignment",
            "integration burden",
            "rollout complexity",
            "onboarding",
            "training",
            "switching cost",
            "long sales cycle",
            "roi proof",
            "vendor trust",
        )
    return ("local only", "missing evidence", "no citations")


def _normalized_result_text(result: ResearchCouncilResult) -> str:
    parts: list[str] = [result.input_summary]
    parts.extend(claim.text for claim in result.claims)
    parts.extend(claim.rationale for claim in result.claims)
    parts.extend(entry.summary for entry in result.evidence_ledger)
    parts.extend(entry.notes for entry in result.evidence_ledger)
    parts.extend(critique.finding for critique in result.reviewer_critiques)
    parts.extend(critique.suggested_action for critique in result.reviewer_critiques)
    parts.extend(experiment.title for experiment in result.experiments)
    parts.extend(experiment.method for experiment in result.experiments)
    parts.extend(experiment.risk for experiment in result.experiments)
    parts.extend(
        (
            result.recommendation.decision,
            result.recommendation.summary,
            result.recommendation.next_step,
            result.recommendation.rationale,
        )
    )
    parts.extend(result.warnings)
    return _normalize_text(" ".join(parts))


def _matched_terms(text: str, terms: Sequence[str]) -> tuple[str, ...]:
    normalized_text = _normalize_text(text)
    matches: list[str] = []
    for term in terms:
        normalized_term = _normalize_text(term)
        if normalized_term and normalized_term in normalized_text:
            matches.append(normalized_term)
    return _dedupe(matches)


def _term_fragments(value: str) -> tuple[str, ...]:
    normalized = _normalize_text(value)
    if not normalized:
        return ()
    fragments = [normalized]
    fragments.extend(
        part.strip()
        for part in re.split(r"\bbefore\b|\band\b|,|;|:", normalized)
        if len(part.strip()) >= 4
    )
    if normalized.endswith(" risk"):
        fragments.append(normalized[: -len(" risk")])
    return tuple(fragments)


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            deduped.append(value)
    return tuple(deduped)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted(_to_jsonable(item) for item in value)
    return value


to_json_dict = result_to_json_dict
to_json = result_to_json
from_json_dict = result_from_json_dict
from_json = result_from_json


__all__ = [
    "artifacts_to_json",
    "from_json",
    "from_json_dict",
    "result_from_json",
    "result_from_json_dict",
    "result_to_artifacts_dict",
    "result_to_json",
    "result_to_json_dict",
    "to_json",
    "to_json_dict",
    "write_result_json",
]
