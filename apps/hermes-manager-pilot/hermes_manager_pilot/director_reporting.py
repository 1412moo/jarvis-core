"""Transport-neutral Director Report derived from a Manager Report.

This module validates caller-supplied objects only. It does not read a
repository, persist state, start a process, call a service, or grant authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import re
from typing import Any

from .manager_reporting import (
    MANAGER_CONTRACT_TYPE,
    MANAGER_STATUSES,
    OWNER_ACTIONS,
    RESULT_TYPES,
    RISK_SEVERITIES,
    ManagerReport,
    ManagerReportingError,
    manager_report_to_dict,
)


CONTRACT_TYPE = "jarvis_director_report"
VERSION = "0.1A"
AUTHORITY_BOUNDARY = "derived_owner_summary_only"

MAX_JSON_BYTES = 64 * 1024
MAX_TEXT_CHARS = 4000
MAX_LIST_ITEMS = 64

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_HASH_PATTERN = re.compile(r"^[0-9a-f]{40}$")

_COMPLETED_PACKAGE_FIELDS = frozenset(
    {"work_package_id", "result_type", "summary", "commit_hash"}
)
_RISK_FIELDS = frozenset({"severity", "summary"})
_RECOMMENDATION_FIELDS = frozenset(
    {"work_package_id", "summary", "user_value"}
)
_DIRECTOR_FIELDS = frozenset(
    {
        "contract_type",
        "version",
        "source_contract_type",
        "derived_view",
        "authority_boundary",
        "milestone_id",
        "milestone_summary",
        "status",
        "owner_outcome",
        "completed_packages",
        "risk_summary",
        "owner_action",
        "owner_decision",
        "next_recommendation",
    }
)


class DirectorReportingError(ValueError):
    """Raised when Director Report data fails closed."""


@dataclass(frozen=True, slots=True)
class DirectorCompletedPackage:
    work_package_id: str
    result_type: str
    summary: str
    commit_hash: str


@dataclass(frozen=True, slots=True)
class DirectorRisk:
    severity: str
    summary: str


@dataclass(frozen=True, slots=True)
class DirectorRecommendation:
    work_package_id: str
    summary: str
    user_value: str


@dataclass(frozen=True, slots=True)
class DirectorReport:
    contract_type: str
    version: str
    source_contract_type: str
    derived_view: bool
    authority_boundary: str
    milestone_id: str
    milestone_summary: str
    status: str
    owner_outcome: str
    completed_packages: tuple[DirectorCompletedPackage, ...]
    risk_summary: tuple[DirectorRisk, ...]
    owner_action: str
    owner_decision: str
    next_recommendation: DirectorRecommendation | None


def build_director_report(manager_report: ManagerReport) -> DirectorReport:
    """Derive the bounded Owner summary from one canonical Manager Report."""

    try:
        manager = manager_report_to_dict(manager_report)
    except ManagerReportingError as exc:
        raise DirectorReportingError(
            f"source Manager Report is invalid: {exc}"
        ) from exc

    risks: list[dict[str, str]] = [
        {
            "severity": str(item["severity"]),
            "summary": str(item["summary"]),
        }
        for item in manager["risks"]
    ]
    known_risks = {
        (item["severity"], item["summary"].casefold()) for item in risks
    }
    for conflict in manager["source_conflicts"]:
        identity = ("blocking", str(conflict).casefold())
        if identity not in known_risks:
            risks.append({"severity": "blocking", "summary": str(conflict)})
            known_risks.add(identity)

    payload = {
        "contract_type": CONTRACT_TYPE,
        "version": VERSION,
        "source_contract_type": MANAGER_CONTRACT_TYPE,
        "derived_view": True,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "milestone_id": manager["milestone_id"],
        "milestone_summary": manager["milestone_meaning"],
        "status": manager["status"],
        "owner_outcome": manager["user_outcome"],
        "completed_packages": [
            {
                "work_package_id": item["work_package_id"],
                "result_type": item["result_type"],
                "summary": item["summary"],
                "commit_hash": item["commit_hash"],
            }
            for item in manager["completed_work_packages"]
        ],
        "risk_summary": risks,
        "owner_action": manager["owner_action"],
        "owner_decision": manager["owner_decision"],
        "next_recommendation": manager["next_recommendation"],
    }
    return normalize_director_report(payload)


def normalize_director_report(data: Mapping[str, Any]) -> DirectorReport:
    """Validate and canonically normalize one Director Report mapping."""

    mapping = _mapping(data, "director report")
    _reject_unknown_fields(mapping, _DIRECTOR_FIELDS, "director report")
    contract_type = _required_text(mapping, "contract_type", "director report")
    if contract_type != CONTRACT_TYPE:
        raise DirectorReportingError(
            f"director report.contract_type must be {CONTRACT_TYPE}"
        )
    version = _required_text(mapping, "version", "director report")
    if version != VERSION:
        raise DirectorReportingError(f"director report.version must be {VERSION}")
    source_contract_type = _required_text(
        mapping,
        "source_contract_type",
        "director report",
    )
    if source_contract_type != MANAGER_CONTRACT_TYPE:
        raise DirectorReportingError(
            "director report.source_contract_type must be "
            f"{MANAGER_CONTRACT_TYPE}"
        )
    derived_view = _required_bool(mapping, "derived_view", "director report")
    if derived_view is not True:
        raise DirectorReportingError("director report.derived_view must be true")
    authority_boundary = _required_text(
        mapping,
        "authority_boundary",
        "director report",
    )
    if authority_boundary != AUTHORITY_BOUNDARY:
        raise DirectorReportingError(
            "director report.authority_boundary must be "
            f"{AUTHORITY_BOUNDARY}"
        )

    milestone_id = _required_id(mapping, "milestone_id", "director report")
    milestone_summary = _required_text(
        mapping,
        "milestone_summary",
        "director report",
    )
    status = _required_id(mapping, "status", "director report")
    if status not in MANAGER_STATUSES:
        raise DirectorReportingError("director report.status is not supported")
    owner_outcome = _required_text(
        mapping,
        "owner_outcome",
        "director report",
    )
    completed_packages = _normalize_completed_packages(
        mapping.get("completed_packages"),
        "director report.completed_packages",
    )
    risk_summary = _normalize_risks(
        mapping.get("risk_summary"),
        "director report.risk_summary",
    )
    owner_action = _required_id(mapping, "owner_action", "director report")
    if owner_action not in OWNER_ACTIONS:
        raise DirectorReportingError(
            "director report.owner_action is not supported"
        )
    owner_decision = _optional_text(
        mapping,
        "owner_decision",
        "director report",
    )
    next_recommendation = _normalize_recommendation(
        mapping.get("next_recommendation"),
        "director report.next_recommendation",
    )

    if owner_action == "none" and owner_decision:
        raise DirectorReportingError(
            "director report.owner_decision must be empty when owner_action is none"
        )
    if owner_action == "decision_required" and not owner_decision:
        raise DirectorReportingError(
            "director report.owner_decision is required when owner action is required"
        )
    if status == "blocked" and owner_action != "decision_required":
        raise DirectorReportingError(
            "blocked Director Report requires an owner decision"
        )
    if any(risk.severity == "blocking" for risk in risk_summary):
        if status != "blocked" or owner_action != "decision_required":
            raise DirectorReportingError(
                "blocking Director risk requires blocked status and owner decision"
            )

    return DirectorReport(
        contract_type=contract_type,
        version=version,
        source_contract_type=source_contract_type,
        derived_view=derived_view,
        authority_boundary=authority_boundary,
        milestone_id=milestone_id,
        milestone_summary=milestone_summary,
        status=status,
        owner_outcome=owner_outcome,
        completed_packages=completed_packages,
        risk_summary=risk_summary,
        owner_action=owner_action,
        owner_decision=owner_decision,
        next_recommendation=next_recommendation,
    )


def director_report_to_dict(report: DirectorReport) -> dict[str, Any]:
    """Return a detached canonical mapping for one Director Report."""

    report = _validate_director_report(report)
    return _director_report_mapping(report)


def director_report_projection(report: DirectorReport) -> dict[str, Any]:
    """Return a detached read-only presentation mapping."""

    projected = director_report_to_dict(report)
    projected["read_only"] = True
    return projected


def serialize_director_report(report: DirectorReport) -> str:
    text = json.dumps(
        director_report_to_dict(report),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise DirectorReportingError("Director Report exceeds the output limit")
    return text + "\n"


def parse_director_report_json(text: str) -> DirectorReport:
    if not isinstance(text, str):
        raise DirectorReportingError("Director Report JSON must be text")
    try:
        encoded = text.encode("utf-8")
    except UnicodeError as exc:
        raise DirectorReportingError(
            "Director Report JSON must be valid UTF-8"
        ) from exc
    if not encoded:
        raise DirectorReportingError("Director Report JSON must not be empty")
    if len(encoded) > MAX_JSON_BYTES:
        raise DirectorReportingError("Director Report JSON exceeds the input limit")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_finite_json,
        )
    except DirectorReportingError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise DirectorReportingError("Director Report JSON is malformed") from exc
    return normalize_director_report(_mapping(value, "Director Report"))


def _normalize_completed_packages(
    value: Any,
    path: str,
) -> tuple[DirectorCompletedPackage, ...]:
    items = _mapping_sequence(value, path)
    packages: list[DirectorCompletedPackage] = []
    identities: set[str] = set()
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        _reject_unknown_fields(item, _COMPLETED_PACKAGE_FIELDS, item_path)
        work_package_id = _required_id(item, "work_package_id", item_path)
        if work_package_id in identities:
            raise DirectorReportingError(
                f"{path} contains duplicate work_package_id"
            )
        identities.add(work_package_id)
        result_type = _required_id(item, "result_type", item_path)
        if result_type not in RESULT_TYPES:
            raise DirectorReportingError(f"{item_path}.result_type is not supported")
        packages.append(
            DirectorCompletedPackage(
                work_package_id=work_package_id,
                result_type=result_type,
                summary=_required_text(item, "summary", item_path),
                commit_hash=_optional_hash(item, "commit_hash", item_path),
            )
        )
    return tuple(packages)


def _normalize_risks(value: Any, path: str) -> tuple[DirectorRisk, ...]:
    items = _mapping_sequence(value, path)
    risks: list[DirectorRisk] = []
    identities: set[tuple[str, str]] = set()
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        _reject_unknown_fields(item, _RISK_FIELDS, item_path)
        severity = _required_id(item, "severity", item_path)
        if severity not in RISK_SEVERITIES:
            raise DirectorReportingError(f"{item_path}.severity is not supported")
        summary = _required_text(item, "summary", item_path)
        identity = (severity, summary.casefold())
        if identity in identities:
            raise DirectorReportingError(f"{path} contains a duplicate risk")
        identities.add(identity)
        risks.append(DirectorRisk(severity=severity, summary=summary))
    return tuple(risks)


def _normalize_recommendation(
    value: Any,
    path: str,
) -> DirectorRecommendation | None:
    if value is None:
        return None
    item = _mapping(value, path)
    _reject_unknown_fields(item, _RECOMMENDATION_FIELDS, path)
    return DirectorRecommendation(
        work_package_id=_required_id(item, "work_package_id", path),
        summary=_required_text(item, "summary", path),
        user_value=_required_text(item, "user_value", path),
    )


def _validate_director_report(report: DirectorReport) -> DirectorReport:
    if not isinstance(report, DirectorReport):
        raise DirectorReportingError(
            "Director Report serializer requires a DirectorReport"
        )
    normalized = normalize_director_report(_director_report_mapping(report))
    if normalized != report:
        raise DirectorReportingError("Director Report instance is not canonical")
    return report


def _director_report_mapping(report: DirectorReport) -> dict[str, Any]:
    if any(
        not isinstance(item, DirectorCompletedPackage)
        for item in report.completed_packages
    ):
        raise DirectorReportingError(
            "Director Report completed_packages are not canonical"
        )
    if any(not isinstance(item, DirectorRisk) for item in report.risk_summary):
        raise DirectorReportingError(
            "Director Report risk_summary is not canonical"
        )
    if report.next_recommendation is not None and not isinstance(
        report.next_recommendation,
        DirectorRecommendation,
    ):
        raise DirectorReportingError(
            "Director Report next_recommendation is not canonical"
        )
    return {
        "contract_type": report.contract_type,
        "version": report.version,
        "source_contract_type": report.source_contract_type,
        "derived_view": report.derived_view,
        "authority_boundary": report.authority_boundary,
        "milestone_id": report.milestone_id,
        "milestone_summary": report.milestone_summary,
        "status": report.status,
        "owner_outcome": report.owner_outcome,
        "completed_packages": [
            {
                "work_package_id": item.work_package_id,
                "result_type": item.result_type,
                "summary": item.summary,
                "commit_hash": item.commit_hash,
            }
            for item in report.completed_packages
        ],
        "risk_summary": [
            {"severity": item.severity, "summary": item.summary}
            for item in report.risk_summary
        ],
        "owner_action": report.owner_action,
        "owner_decision": report.owner_decision,
        "next_recommendation": (
            None
            if report.next_recommendation is None
            else {
                "work_package_id": report.next_recommendation.work_package_id,
                "summary": report.next_recommendation.summary,
                "user_value": report.next_recommendation.user_value,
            }
        ),
    }


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DirectorReportingError(f"{path} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise DirectorReportingError(f"{path} contains a non-text field name")
    return value


def _mapping_sequence(value: Any, path: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, (list, tuple)):
        raise DirectorReportingError(f"{path} must be a list")
    if len(value) > MAX_LIST_ITEMS:
        raise DirectorReportingError(f"{path} contains too many items")
    return tuple(
        _mapping(item, f"{path}[{index}]") for index, item in enumerate(value)
    )


def _required_text(
    data: Mapping[str, Any],
    field: str,
    path: str,
) -> str:
    if field not in data:
        raise DirectorReportingError(f"{path}.{field} is required")
    value = data[field]
    if not isinstance(value, str):
        raise DirectorReportingError(f"{path}.{field} must be text")
    if not value or value != value.strip():
        raise DirectorReportingError(
            f"{path}.{field} must be non-empty trimmed text"
        )
    if len(value) > MAX_TEXT_CHARS:
        raise DirectorReportingError(f"{path}.{field} is too long")
    if _contains_control(value):
        raise DirectorReportingError(
            f"{path}.{field} contains a control character"
        )
    return value


def _optional_text(
    data: Mapping[str, Any],
    field: str,
    path: str,
) -> str:
    if field not in data:
        raise DirectorReportingError(f"{path}.{field} is required")
    value = data[field]
    if not isinstance(value, str):
        raise DirectorReportingError(f"{path}.{field} must be text")
    if value and value != value.strip():
        raise DirectorReportingError(f"{path}.{field} must be trimmed text")
    if len(value) > MAX_TEXT_CHARS:
        raise DirectorReportingError(f"{path}.{field} is too long")
    if _contains_control(value):
        raise DirectorReportingError(
            f"{path}.{field} contains a control character"
        )
    return value


def _required_id(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _required_text(data, field, path)
    if _ID_PATTERN.fullmatch(value) is None:
        raise DirectorReportingError(f"{path}.{field} must be a normalized ID")
    return value


def _required_bool(data: Mapping[str, Any], field: str, path: str) -> bool:
    if field not in data or not isinstance(data[field], bool):
        raise DirectorReportingError(f"{path}.{field} must be a boolean")
    return data[field]


def _optional_hash(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _optional_text(data, field, path)
    if value and _HASH_PATTERN.fullmatch(value) is None:
        raise DirectorReportingError(
            f"{path}.{field} must be an empty or full lowercase Git hash"
        )
    return value


def _reject_unknown_fields(
    data: Mapping[str, Any],
    allowed: frozenset[str],
    path: str,
) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise DirectorReportingError(
            f"{path} contains unknown fields: {', '.join(unknown)}"
        )


def _contains_control(value: str) -> bool:
    return any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DirectorReportingError(
                f"Director Report JSON contains duplicate key: {key}"
            )
        result[key] = value
    return result


def _reject_non_finite_json(value: str) -> Any:
    raise DirectorReportingError(
        f"Director Report JSON contains non-finite number: {value}"
    )
