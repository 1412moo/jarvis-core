"""Transport-neutral Owner Decision v0.1A contract and pure renderers.

This module normalizes in-memory data only. It does not read files, persist
state, expose routes, call external services, or grant implementation authority.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
import re
import unicodedata
from typing import Any


CONTRACT_TYPE = "jarvis_owner_decision"
VERSION = "0.1A"
PROJECT_ID = "jarvis-core"
DECISION_KIND = "workstream_selection"
AUTHORITY_BOUNDARY = "work_package_proposal_only"

ALLOWED_WORKSTREAMS = (
    ("hermes-manager", "Hermes Manager"),
    ("memory-skills", "Memory / Skills"),
    ("jarvis-console", "Jarvis Console"),
    ("research-council", "Research Council"),
    ("daily-ai-radar", "Daily AI Radar"),
    ("task-discord-dashboard", "Task / Discord / Dashboard"),
)
ALLOWED_STATUSES = frozenset(
    {
        "selection_required",
        "selected_for_proposal",
        "selection_rejected",
        "superseded",
    }
)
STATUSES_WITH_SELECTION = frozenset(
    {
        "selected_for_proposal",
        "superseded",
    }
)
STATUSES_WITHOUT_SELECTION = ALLOWED_STATUSES - STATUSES_WITH_SELECTION

RESPONSE_TEMPLATE = """Owner Decision
Project: Jarvis-Core
Workstream: <one exact allowed workstream name>
Desired outcome: <one bounded plain-language user result>
Decision: select for work-package proposal"""

MAX_JSON_BYTES = 64 * 1024
MAX_TEXT_CHARS = 500
MAX_LOCKED_CAPABILITIES = 16
MAX_LOCKED_CAPABILITY_CHARS = 200

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_WORKSTREAM_NAMES = dict(ALLOWED_WORKSTREAMS)
_WORKSTREAM_ORDER = tuple(workstream_id for workstream_id, _ in ALLOWED_WORKSTREAMS)
_DECISION_FIELDS = frozenset(
    {
        "contract_type",
        "version",
        "project_id",
        "decision_kind",
        "status",
        "reason",
        "authority_boundary",
        "recommended_workstream_id",
        "candidates",
        "selected_workstream_id",
        "desired_outcome",
        "response_template",
        "read_only",
    }
)
_CANDIDATE_FIELDS = frozenset(
    {
        "workstream_id",
        "display_name",
        "current_capability",
        "next_user_outcome",
        "locked_capabilities",
    }
)
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]<>#|])")


class OwnerDecisionError(ValueError):
    """Raised when Owner Decision input fails closed."""


@dataclass(frozen=True, slots=True)
class OwnerDecisionCandidate:
    """One bounded Jarvis-Core workstream choice."""

    workstream_id: str
    display_name: str
    current_capability: str
    next_user_outcome: str
    locked_capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OwnerDecision:
    """One immutable, transport-neutral owner direction decision."""

    contract_type: str
    version: str
    project_id: str
    decision_kind: str
    status: str
    reason: str
    authority_boundary: str
    recommended_workstream_id: str
    candidates: tuple[OwnerDecisionCandidate, ...]
    selected_workstream_id: str | None
    desired_outcome: str | None
    response_template: str
    read_only: bool


def normalize_owner_decision(data: Mapping[str, Any]) -> OwnerDecision:
    """Validate and canonically normalize one Owner Decision mapping."""

    if not isinstance(data, Mapping):
        raise OwnerDecisionError("owner decision must be an object")
    _reject_unknown_fields(data, _DECISION_FIELDS, "owner decision")

    contract_type = _required_text(data, "contract_type", "owner decision")
    if contract_type != CONTRACT_TYPE:
        raise OwnerDecisionError(f"contract_type must be {CONTRACT_TYPE}")
    version = _required_text(data, "version", "owner decision")
    if version != VERSION:
        raise OwnerDecisionError(f"version must be {VERSION}")
    project_id = _required_id(data, "project_id", "owner decision")
    if project_id != PROJECT_ID:
        raise OwnerDecisionError(f"project_id must be {PROJECT_ID}")
    decision_kind = _required_id(data, "decision_kind", "owner decision")
    if decision_kind != DECISION_KIND:
        raise OwnerDecisionError(f"decision_kind must be {DECISION_KIND}")

    status = _required_id(data, "status", "owner decision")
    if status not in ALLOWED_STATUSES:
        raise OwnerDecisionError("owner decision.status is not supported")
    reason = _bounded_text(data, "reason", "owner decision", MAX_TEXT_CHARS)
    authority_boundary = _required_id(data, "authority_boundary", "owner decision")
    if authority_boundary != AUTHORITY_BOUNDARY:
        raise OwnerDecisionError(
            f"authority_boundary must be {AUTHORITY_BOUNDARY}"
        )

    candidates_value = data.get("candidates")
    if not isinstance(candidates_value, list):
        raise OwnerDecisionError("owner decision.candidates must be a list")
    if len(candidates_value) != len(ALLOWED_WORKSTREAMS):
        raise OwnerDecisionError(
            "owner decision.candidates must contain all six Jarvis-Core workstreams"
        )
    candidates_by_id: dict[str, OwnerDecisionCandidate] = {}
    for index, value in enumerate(candidates_value):
        candidate = _normalize_candidate(value, index)
        if candidate.workstream_id in candidates_by_id:
            raise OwnerDecisionError(
                "owner decision.candidates contains duplicate workstream IDs"
            )
        candidates_by_id[candidate.workstream_id] = candidate
    if set(candidates_by_id) != set(_WORKSTREAM_ORDER):
        raise OwnerDecisionError(
            "owner decision.candidates must contain the exact allowed workstreams"
        )
    candidates = tuple(candidates_by_id[item] for item in _WORKSTREAM_ORDER)

    recommended_workstream_id = _required_id(
        data,
        "recommended_workstream_id",
        "owner decision",
    )
    if recommended_workstream_id not in candidates_by_id:
        raise OwnerDecisionError(
            "owner decision.recommended_workstream_id must reference a candidate"
        )

    selected_workstream_id = _optional_id(
        data,
        "selected_workstream_id",
        "owner decision",
    )
    desired_outcome = _optional_text(
        data,
        "desired_outcome",
        "owner decision",
        MAX_TEXT_CHARS,
    )
    if status in STATUSES_WITH_SELECTION:
        if selected_workstream_id not in candidates_by_id or desired_outcome is None:
            raise OwnerDecisionError(
                "selected status requires a candidate workstream and desired outcome"
            )
    elif selected_workstream_id is not None or desired_outcome is not None:
        raise OwnerDecisionError(
            "unselected status must not contain a workstream or desired outcome"
        )

    response_template = data.get("response_template")
    if response_template != RESPONSE_TEMPLATE:
        raise OwnerDecisionError("owner decision.response_template is not the v0.1A template")
    if data.get("read_only") is not True:
        raise OwnerDecisionError("owner decision.read_only must be true")

    return OwnerDecision(
        contract_type=contract_type,
        version=version,
        project_id=project_id,
        decision_kind=decision_kind,
        status=status,
        reason=reason,
        authority_boundary=authority_boundary,
        recommended_workstream_id=recommended_workstream_id,
        candidates=candidates,
        selected_workstream_id=selected_workstream_id,
        desired_outcome=desired_outcome,
        response_template=response_template,
        read_only=True,
    )


def parse_owner_decision_json(text: str) -> OwnerDecision:
    """Parse bounded JSON with duplicate-key rejection, then normalize it."""

    if not isinstance(text, str):
        raise OwnerDecisionError("owner decision JSON must be text")
    try:
        byte_length = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise OwnerDecisionError("owner decision JSON must be valid UTF-8") from exc
    if not text.strip():
        raise OwnerDecisionError("owner decision JSON must not be empty")
    if byte_length > MAX_JSON_BYTES:
        raise OwnerDecisionError("owner decision JSON exceeds the input limit")

    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_finite_json,
        )
    except OwnerDecisionError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise OwnerDecisionError("owner decision JSON is malformed") from exc
    return normalize_owner_decision(value)


def owner_decision_to_dict(decision: OwnerDecision) -> dict[str, Any]:
    """Return a fresh transport mapping after revalidating the immutable object."""

    normalized = _validate_owner_decision_instance(decision)
    return _owner_decision_mapping(normalized)


def serialize_owner_decision(decision: OwnerDecision) -> str:
    """Return stable, compact, UTF-8-compatible canonical JSON."""

    serialized = json.dumps(
        owner_decision_to_dict(decision),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if len(serialized.encode("utf-8")) > MAX_JSON_BYTES:
        raise OwnerDecisionError("normalized owner decision exceeds the output limit")
    return serialized


def render_owner_decision_markdown(decision: OwnerDecision) -> str:
    """Render a deterministic, read-only Markdown view without mutating input."""

    normalized = _validate_owner_decision_instance(decision)
    candidates_by_id = {
        candidate.workstream_id: candidate for candidate in normalized.candidates
    }
    recommended = candidates_by_id[normalized.recommended_workstream_id]
    lines = [
        "# Owner Decision",
        "",
        f"- Project: {_escape_markdown(normalized.project_id)}",
        f"- Status: `{normalized.status}`",
        f"- Authority: `{normalized.authority_boundary}`",
        "- Mode: read-only",
        "",
        "## Why This Decision Is Needed",
        "",
        _escape_markdown(normalized.reason),
        "",
        "## Workstream Candidates",
        "",
    ]
    for index, candidate in enumerate(normalized.candidates, start=1):
        locked = (
            ", ".join(_escape_markdown(item) for item in candidate.locked_capabilities)
            if candidate.locked_capabilities
            else "None declared by this decision contract"
        )
        lines.extend(
            [
                f"### {index}. {_escape_markdown(candidate.display_name)}",
                "",
                f"- ID: `{candidate.workstream_id}`",
                f"- Current capability: {_escape_markdown(candidate.current_capability)}",
                f"- Next user outcome: {_escape_markdown(candidate.next_user_outcome)}",
                f"- Remains locked: {locked}",
                "",
            ]
        )
    lines.extend(
        [
            "## Recommendation",
            "",
            f"{_escape_markdown(recommended.display_name)} (`{recommended.workstream_id}`)",
            "",
            "This recommendation permits a bounded work-package proposal only.",
            "",
            "## Current Selection",
            "",
            "- Workstream: "
            + (
                f"`{normalized.selected_workstream_id}`"
                if normalized.selected_workstream_id is not None
                else "Not selected"
            ),
            "- Desired outcome: "
            + (
                _escape_markdown(normalized.desired_outcome)
                if normalized.desired_outcome is not None
                else "Not provided"
            ),
            "",
            "## Copy-only Response Template",
            "",
            "```text",
            normalized.response_template,
            "```",
            "",
            "No selection, implementation, save, execution, push, or PR authority is granted by this rendering.",
            "",
        ]
    )
    return "\n".join(lines)


def _normalize_candidate(value: Any, index: int) -> OwnerDecisionCandidate:
    path = f"owner decision.candidates[{index}]"
    if not isinstance(value, Mapping):
        raise OwnerDecisionError(f"{path} must be an object")
    _reject_unknown_fields(value, _CANDIDATE_FIELDS, path)
    workstream_id = _required_id(value, "workstream_id", path)
    expected_name = _WORKSTREAM_NAMES.get(workstream_id)
    if expected_name is None:
        raise OwnerDecisionError(f"{path}.workstream_id is not allowed")
    display_name = _bounded_text(value, "display_name", path, MAX_TEXT_CHARS)
    if display_name != expected_name:
        raise OwnerDecisionError(f"{path}.display_name does not match its workstream ID")
    return OwnerDecisionCandidate(
        workstream_id=workstream_id,
        display_name=display_name,
        current_capability=_bounded_text(
            value,
            "current_capability",
            path,
            MAX_TEXT_CHARS,
        ),
        next_user_outcome=_bounded_text(
            value,
            "next_user_outcome",
            path,
            MAX_TEXT_CHARS,
        ),
        locked_capabilities=_locked_capabilities(value, path),
    )


def _validate_owner_decision_instance(decision: OwnerDecision) -> OwnerDecision:
    if not isinstance(decision, OwnerDecision):
        raise OwnerDecisionError("renderer input must be an OwnerDecision")
    raw = _owner_decision_mapping(decision)
    normalized = normalize_owner_decision(raw)
    if normalized != decision:
        raise OwnerDecisionError("OwnerDecision instance is not canonically normalized")
    return normalized


def _owner_decision_mapping(decision: OwnerDecision) -> dict[str, Any]:
    if not isinstance(decision.candidates, tuple) or any(
        not isinstance(candidate, OwnerDecisionCandidate)
        for candidate in decision.candidates
    ):
        raise OwnerDecisionError("OwnerDecision candidates must be immutable contracts")
    return {
        "contract_type": decision.contract_type,
        "version": decision.version,
        "project_id": decision.project_id,
        "decision_kind": decision.decision_kind,
        "status": decision.status,
        "reason": decision.reason,
        "authority_boundary": decision.authority_boundary,
        "recommended_workstream_id": decision.recommended_workstream_id,
        "candidates": [
            {
                "workstream_id": candidate.workstream_id,
                "display_name": candidate.display_name,
                "current_capability": candidate.current_capability,
                "next_user_outcome": candidate.next_user_outcome,
                "locked_capabilities": list(candidate.locked_capabilities),
            }
            for candidate in decision.candidates
        ],
        "selected_workstream_id": decision.selected_workstream_id,
        "desired_outcome": decision.desired_outcome,
        "response_template": decision.response_template,
        "read_only": decision.read_only,
    }


def _locked_capabilities(data: Mapping[str, Any], path: str) -> tuple[str, ...]:
    values = data.get("locked_capabilities")
    if not isinstance(values, list) or len(values) > MAX_LOCKED_CAPABILITIES:
        raise OwnerDecisionError(f"{path}.locked_capabilities must be a bounded list")
    normalized = tuple(
        _bounded_text(
            {"value": value},
            "value",
            f"{path}.locked_capabilities[{index}]",
            MAX_LOCKED_CAPABILITY_CHARS,
        )
        for index, value in enumerate(values)
    )
    _reject_duplicates(normalized, f"{path}.locked_capabilities")
    return tuple(sorted(normalized, key=lambda item: (item.casefold(), item)))


def _required_text(data: Mapping[str, Any], field: str, path: str) -> str:
    return _bounded_text(data, field, path, MAX_TEXT_CHARS)


def _bounded_text(
    data: Mapping[str, Any],
    field: str,
    path: str,
    maximum: int,
) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise OwnerDecisionError(f"{path}.{field} must be non-empty trimmed text")
    if len(value) > maximum:
        raise OwnerDecisionError(f"{path}.{field} is too long")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise OwnerDecisionError(f"{path}.{field} contains a control character")
    return value


def _optional_text(
    data: Mapping[str, Any],
    field: str,
    path: str,
    maximum: int,
) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    return _bounded_text(data, field, path, maximum)


def _required_id(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _required_text(data, field, path)
    if not _ID_PATTERN.fullmatch(value):
        raise OwnerDecisionError(f"{path}.{field} must be a normalized lowercase ID")
    return value


def _optional_id(data: Mapping[str, Any], field: str, path: str) -> str | None:
    if data.get(field) is None:
        return None
    return _required_id(data, field, path)


def _reject_unknown_fields(
    data: Mapping[str, Any],
    allowed: frozenset[str],
    path: str,
) -> None:
    non_text = [key for key in data if not isinstance(key, str)]
    if non_text:
        raise OwnerDecisionError(f"{path} contains a non-text field name")
    unknown = sorted(key for key in data if key not in allowed)
    if unknown:
        raise OwnerDecisionError(f"{path} contains unknown fields: {', '.join(unknown)}")


def _reject_duplicates(values: Iterable[str], path: str) -> None:
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            raise OwnerDecisionError(f"{path} contains duplicate values")
        seen.add(key)


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise OwnerDecisionError(f"owner decision JSON contains duplicate key: {key}")
        value[key] = item
    return value


def _reject_non_finite_json(value: str) -> Any:
    raise OwnerDecisionError(f"owner decision JSON contains non-finite value: {value}")


def _escape_markdown(value: str) -> str:
    return _MARKDOWN_SPECIAL.sub(r"\\\1", value)
