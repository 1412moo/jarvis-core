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
from typing import Any

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
        return {
            "profile_id": str(selected_profile_id),
            "selected_by": str(value.get("selected_by", "")),
            "matched_keywords": _to_jsonable(value.get("matched_keywords", {})),
            "score_by_profile": _to_jsonable(value.get("score_by_profile", {})),
        }
    return {
        "profile_id": str(value.get("profile_id", "")),
        "selected_by": str(value.get("selected_by", "")),
        "matched_keywords": _to_jsonable(value.get("matched_keywords", {})),
        "score_by_profile": _to_jsonable(value.get("score_by_profile", {})),
    }


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
