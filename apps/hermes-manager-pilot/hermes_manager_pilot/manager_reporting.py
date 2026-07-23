"""Transport-neutral Worker and Manager reporting contracts.

The contracts in this module normalize caller-supplied data only. They do not
read repositories, persist state, start processes, call external services, or
grant approval or execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
import re
from typing import Any


WORKER_CONTRACT_TYPE = "hermes_worker_report"
MANAGER_CONTRACT_TYPE = "hermes_manager_report"
VERSION = "0.1A"
SOURCE_OF_TRUTH = "master_plan"

RESULT_TYPES = frozenset({"design", "implementation", "review", "commit", "blocked"})
VALIDATION_STATUSES = frozenset({"passed", "failed", "skipped"})
QA_LEVELS = (
    "unit_deterministic",
    "cli_output",
    "file_inspection",
    "static_ui",
    "browser",
    "manual_interactive",
)
CLEANUP_STATUSES = frozenset({"not_required", "confirmed", "failed"})
MANAGER_STATUSES = frozenset({"in_progress", "milestone_complete", "blocked"})
OWNER_ACTIONS = frozenset({"none", "decision_required"})
RISK_SEVERITIES = frozenset({"low", "medium", "high", "blocking"})

MAX_JSON_BYTES = 128 * 1024
MAX_TEXT_CHARS = 2000
MAX_SUMMARY_CHARS = 4000
MAX_LIST_ITEMS = 128
MAX_VALIDATIONS = 64
MAX_RISKS = 32
MAX_PATH_CHARS = 512
MAX_STATUS_CHARS = 1024

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_HASH_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_WINDOWS_DRIVE = re.compile(r"^[a-zA-Z]:")

_WORK_PACKAGE_FIELDS = frozenset(
    {"work_package_id", "milestone_id", "summary"}
)
_VALIDATION_FIELDS = frozenset({"name", "status", "evidence"})
_QA_FIELDS = frozenset(
    {"level", "reason", "server_started", "cleanup_status"}
)
_SAFETY_FIELDS = frozenset(
    {
        "protected_paths_untouched",
        "external_calls_made",
        "push_or_pr_created",
        "destructive_change_made",
        "clipboard_output_only",
        "unexpected_repository_changes",
    }
)
_WORKER_FIELDS = frozenset(
    {
        "contract_type",
        "version",
        "work_package",
        "result_type",
        "changed_files",
        "validation_results",
        "qa_strategy",
        "self_review_findings",
        "commit_hash",
        "commit_subject",
        "final_git_status",
        "blockers",
        "safety_boundary",
    }
)
_COMPLETED_PACKAGE_FIELDS = frozenset(
    {"work_package_id", "result_type", "summary", "commit_hash"}
)
_RISK_FIELDS = frozenset({"severity", "category", "summary"})
_RECOMMENDATION_FIELDS = frozenset(
    {"work_package_id", "summary", "user_value"}
)
_MANAGER_FIELDS = frozenset(
    {
        "contract_type",
        "version",
        "source_of_truth",
        "derived_view",
        "current_goal",
        "milestone_id",
        "milestone_meaning",
        "user_outcome",
        "completed_work_packages",
        "current_position",
        "status",
        "evidence_summary",
        "source_conflicts",
        "risks",
        "next_recommendation",
        "owner_action",
        "owner_decision",
    }
)


class ManagerReportingError(ValueError):
    """Raised when reporting data fails closed."""


@dataclass(frozen=True, slots=True)
class WorkPackageReference:
    work_package_id: str
    milestone_id: str
    summary: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    name: str
    status: str
    evidence: str


@dataclass(frozen=True, slots=True)
class QAStrategy:
    level: str
    reason: str
    server_started: bool
    cleanup_status: str


@dataclass(frozen=True, slots=True)
class SafetyBoundary:
    protected_paths_untouched: bool
    external_calls_made: bool
    push_or_pr_created: bool
    destructive_change_made: bool
    clipboard_output_only: bool
    unexpected_repository_changes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkerReport:
    contract_type: str
    version: str
    work_package: WorkPackageReference
    result_type: str
    changed_files: tuple[str, ...]
    validation_results: tuple[ValidationResult, ...]
    qa_strategy: QAStrategy
    self_review_findings: tuple[str, ...]
    commit_hash: str
    commit_subject: str
    final_git_status: tuple[str, ...]
    blockers: tuple[str, ...]
    safety_boundary: SafetyBoundary


@dataclass(frozen=True, slots=True)
class CompletedWorkPackage:
    work_package_id: str
    result_type: str
    summary: str
    commit_hash: str


@dataclass(frozen=True, slots=True)
class ManagerRisk:
    severity: str
    category: str
    summary: str


@dataclass(frozen=True, slots=True)
class NextRecommendation:
    work_package_id: str
    summary: str
    user_value: str


@dataclass(frozen=True, slots=True)
class ManagerReport:
    contract_type: str
    version: str
    source_of_truth: str
    derived_view: bool
    current_goal: str
    milestone_id: str
    milestone_meaning: str
    user_outcome: str
    completed_work_packages: tuple[CompletedWorkPackage, ...]
    current_position: str
    status: str
    evidence_summary: tuple[str, ...]
    source_conflicts: tuple[str, ...]
    risks: tuple[ManagerRisk, ...]
    next_recommendation: NextRecommendation | None
    owner_action: str
    owner_decision: str


def normalize_worker_report(data: Mapping[str, Any]) -> WorkerReport:
    """Validate and canonically normalize one Worker Report mapping."""

    mapping = _mapping(data, "worker report")
    _reject_unknown_fields(mapping, _WORKER_FIELDS, "worker report")
    contract_type = _required_text(mapping, "contract_type", "worker report")
    if contract_type != WORKER_CONTRACT_TYPE:
        raise ManagerReportingError(
            f"worker report.contract_type must be {WORKER_CONTRACT_TYPE}"
        )
    version = _required_text(mapping, "version", "worker report")
    if version != VERSION:
        raise ManagerReportingError(f"worker report.version must be {VERSION}")

    work_package = _normalize_work_package(
        mapping.get("work_package"),
        "worker report.work_package",
    )
    result_type = _required_id(mapping, "result_type", "worker report")
    if result_type not in RESULT_TYPES:
        raise ManagerReportingError("worker report.result_type is not supported")

    changed_files = _path_list(
        mapping.get("changed_files"),
        "worker report.changed_files",
    )
    validation_results = _normalize_validations(
        mapping.get("validation_results"),
        "worker report.validation_results",
    )
    qa_strategy = _normalize_qa_strategy(
        mapping.get("qa_strategy"),
        "worker report.qa_strategy",
    )
    self_review_findings = _text_list(
        mapping.get("self_review_findings"),
        "worker report.self_review_findings",
        maximum=MAX_LIST_ITEMS,
    )
    commit_hash = _optional_hash(mapping, "commit_hash", "worker report")
    commit_subject = _optional_text(
        mapping,
        "commit_subject",
        "worker report",
        maximum=MAX_TEXT_CHARS,
    )
    if bool(commit_hash) != bool(commit_subject):
        raise ManagerReportingError(
            "worker report commit_hash and commit_subject must be supplied together"
        )
    final_git_status = _status_list(
        mapping.get("final_git_status"),
        "worker report.final_git_status",
    )
    blockers = _text_list(
        mapping.get("blockers"),
        "worker report.blockers",
        maximum=MAX_LIST_ITEMS,
    )
    safety_boundary = _normalize_safety_boundary(
        mapping.get("safety_boundary"),
        "worker report.safety_boundary",
    )

    if result_type == "blocked" and not blockers:
        raise ManagerReportingError("blocked Worker Report requires a blocker")
    if result_type != "blocked" and blockers:
        raise ManagerReportingError(
            "non-blocked Worker Report must not contain blockers"
        )
    failed_validations = tuple(
        result.name for result in validation_results if result.status == "failed"
    )
    if result_type != "blocked" and failed_validations:
        raise ManagerReportingError(
            "non-blocked Worker Report contains failed validation"
        )
    safety_violations = _worker_safety_violations(qa_strategy, safety_boundary)
    if result_type != "blocked" and safety_violations:
        raise ManagerReportingError(
            "non-blocked Worker Report violates its safety boundary: "
            + ", ".join(safety_violations)
        )

    return WorkerReport(
        contract_type=contract_type,
        version=version,
        work_package=work_package,
        result_type=result_type,
        changed_files=changed_files,
        validation_results=validation_results,
        qa_strategy=qa_strategy,
        self_review_findings=self_review_findings,
        commit_hash=commit_hash,
        commit_subject=commit_subject,
        final_git_status=final_git_status,
        blockers=blockers,
        safety_boundary=safety_boundary,
    )


def normalize_manager_report(data: Mapping[str, Any]) -> ManagerReport:
    """Validate and canonically normalize one Manager Report mapping."""

    mapping = _mapping(data, "manager report")
    _reject_unknown_fields(mapping, _MANAGER_FIELDS, "manager report")
    contract_type = _required_text(mapping, "contract_type", "manager report")
    if contract_type != MANAGER_CONTRACT_TYPE:
        raise ManagerReportingError(
            f"manager report.contract_type must be {MANAGER_CONTRACT_TYPE}"
        )
    version = _required_text(mapping, "version", "manager report")
    if version != VERSION:
        raise ManagerReportingError(f"manager report.version must be {VERSION}")
    source_of_truth = _required_id(mapping, "source_of_truth", "manager report")
    if source_of_truth != SOURCE_OF_TRUTH:
        raise ManagerReportingError(
            f"manager report.source_of_truth must be {SOURCE_OF_TRUTH}"
        )
    derived_view = _required_bool(mapping, "derived_view", "manager report")
    if derived_view is not True:
        raise ManagerReportingError("manager report.derived_view must be true")

    current_goal = _required_text(
        mapping,
        "current_goal",
        "manager report",
        maximum=MAX_SUMMARY_CHARS,
    )
    milestone_id = _required_id(mapping, "milestone_id", "manager report")
    milestone_meaning = _required_text(
        mapping,
        "milestone_meaning",
        "manager report",
        maximum=MAX_SUMMARY_CHARS,
    )
    user_outcome = _required_text(
        mapping,
        "user_outcome",
        "manager report",
        maximum=MAX_SUMMARY_CHARS,
    )
    completed_work_packages = _normalize_completed_packages(
        mapping.get("completed_work_packages"),
        "manager report.completed_work_packages",
    )
    current_position = _required_text(
        mapping,
        "current_position",
        "manager report",
        maximum=MAX_SUMMARY_CHARS,
    )
    status = _required_id(mapping, "status", "manager report")
    if status not in MANAGER_STATUSES:
        raise ManagerReportingError("manager report.status is not supported")
    evidence_summary = _text_list(
        mapping.get("evidence_summary"),
        "manager report.evidence_summary",
        maximum=MAX_LIST_ITEMS,
        require_nonempty=True,
    )
    source_conflicts = _text_list(
        mapping.get("source_conflicts"),
        "manager report.source_conflicts",
        maximum=MAX_LIST_ITEMS,
    )
    risks = _normalize_risks(mapping.get("risks"), "manager report.risks")
    next_recommendation = _normalize_optional_recommendation(
        mapping.get("next_recommendation"),
        "manager report.next_recommendation",
    )
    owner_action = _required_id(mapping, "owner_action", "manager report")
    if owner_action not in OWNER_ACTIONS:
        raise ManagerReportingError("manager report.owner_action is not supported")
    owner_decision = _optional_text(
        mapping,
        "owner_decision",
        "manager report",
        maximum=MAX_SUMMARY_CHARS,
    )

    if owner_action == "none" and owner_decision:
        raise ManagerReportingError(
            "manager report.owner_decision must be empty when owner_action is none"
        )
    if owner_action == "decision_required" and not owner_decision:
        raise ManagerReportingError(
            "manager report.owner_decision is required when owner action is required"
        )
    blocking_risks = tuple(risk for risk in risks if risk.severity == "blocking")
    if source_conflicts or blocking_risks:
        if status != "blocked" or owner_action != "decision_required":
            raise ManagerReportingError(
                "source conflicts and blocking risks require blocked status and owner decision"
            )
    if status == "blocked" and owner_action != "decision_required":
        raise ManagerReportingError(
            "blocked Manager Report requires an owner decision"
        )

    return ManagerReport(
        contract_type=contract_type,
        version=version,
        source_of_truth=source_of_truth,
        derived_view=derived_view,
        current_goal=current_goal,
        milestone_id=milestone_id,
        milestone_meaning=milestone_meaning,
        user_outcome=user_outcome,
        completed_work_packages=completed_work_packages,
        current_position=current_position,
        status=status,
        evidence_summary=evidence_summary,
        source_conflicts=source_conflicts,
        risks=risks,
        next_recommendation=next_recommendation,
        owner_action=owner_action,
        owner_decision=owner_decision,
    )


def parse_worker_report_json(text: str) -> WorkerReport:
    return normalize_worker_report(_parse_json_object(text, "Worker Report"))


def parse_manager_report_json(text: str) -> ManagerReport:
    return normalize_manager_report(_parse_json_object(text, "Manager Report"))


def worker_report_to_dict(report: WorkerReport) -> dict[str, Any]:
    """Return a detached canonical mapping for a normalized Worker Report."""

    report = _validate_worker_report_instance(report)
    return _worker_report_mapping(report)


def manager_report_to_dict(report: ManagerReport) -> dict[str, Any]:
    """Return a detached canonical mapping for a normalized Manager Report."""

    report = _validate_manager_report_instance(report)
    return _manager_report_mapping(report)


def serialize_worker_report(report: WorkerReport) -> str:
    return _serialize(worker_report_to_dict(report), "Worker Report")


def serialize_manager_report(report: ManagerReport) -> str:
    return _serialize(manager_report_to_dict(report), "Manager Report")


def render_worker_report_markdown(report: WorkerReport) -> str:
    """Render a deterministic detailed report for Hermes Manager."""

    report = _validate_worker_report_instance(report)
    lines = [
        "# Worker Report",
        "",
        f"- Result type: `{_md(report.result_type)}`",
        f"- Work package: `{_md(report.work_package.work_package_id)}`",
        f"- Milestone: `{_md(report.work_package.milestone_id)}`",
        f"- Summary: {_md(report.work_package.summary)}",
        "",
        "## Changed Files",
        "",
        *_markdown_items(report.changed_files, "none"),
        "",
        "## Validation",
        "",
    ]
    if report.validation_results:
        lines.extend(
            f"- `{_md(result.status)}` {_md(result.name)} — {_md(result.evidence)}"
            for result in report.validation_results
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## QA Strategy",
            "",
            f"- Level: `{_md(report.qa_strategy.level)}`",
            f"- Reason: {_md(report.qa_strategy.reason)}",
            f"- Server started: {_yes_no(report.qa_strategy.server_started)}",
            f"- Cleanup: `{_md(report.qa_strategy.cleanup_status)}`",
            "",
            "## Self-review Findings",
            "",
            *_markdown_items(report.self_review_findings, "none"),
            "",
            "## Commit",
            "",
            f"- Hash: `{_md(report.commit_hash or 'none')}`",
            f"- Subject: {_md(report.commit_subject or 'none')}",
            "",
            "## Final Git Status",
            "",
            *_markdown_items(report.final_git_status, "clean"),
            "",
            "## Blockers",
            "",
            *_markdown_items(report.blockers, "none"),
            "",
            "## Safety Boundary",
            "",
            f"- Protected paths untouched: {_yes_no(report.safety_boundary.protected_paths_untouched)}",
            f"- External calls made: {_yes_no(report.safety_boundary.external_calls_made)}",
            f"- Push or PR created: {_yes_no(report.safety_boundary.push_or_pr_created)}",
            f"- Destructive change made: {_yes_no(report.safety_boundary.destructive_change_made)}",
            f"- Clipboard output-only: {_yes_no(report.safety_boundary.clipboard_output_only)}",
            "- Unexpected repository changes:",
            *_markdown_items(
                report.safety_boundary.unexpected_repository_changes,
                "none",
                indent="  ",
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def render_manager_report_markdown(report: ManagerReport) -> str:
    """Render a deterministic Owner-facing milestone report."""

    report = _validate_manager_report_instance(report)
    lines = [
        "# Manager Report",
        "",
        f"- Current goal: {_md(report.current_goal)}",
        f"- Milestone: `{_md(report.milestone_id)}`",
        f"- Status: `{_md(report.status)}`",
        f"- Source of truth: `{_md(report.source_of_truth)}`",
        "",
        "## Milestone Meaning",
        "",
        _md(report.milestone_meaning),
        "",
        "## User Outcome",
        "",
        _md(report.user_outcome),
        "",
        "## Completed Work Packages",
        "",
    ]
    if report.completed_work_packages:
        lines.extend(
            "- "
            f"`{_md(package.work_package_id)}` — {_md(package.summary)} "
            f"(`{_md(package.result_type)}`, `{_md(package.commit_hash or 'no commit')}`)"
            for package in report.completed_work_packages
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Current Position",
            "",
            _md(report.current_position),
            "",
            "## Evidence",
            "",
            *_markdown_items(report.evidence_summary, "none"),
            "",
            "## Source Conflicts",
            "",
            *_markdown_items(report.source_conflicts, "none"),
            "",
            "## Risks",
            "",
        ]
    )
    if report.risks:
        lines.extend(
            f"- `{_md(risk.severity)}` {_md(risk.category)} — {_md(risk.summary)}"
            for risk in report.risks
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Next Recommendation", ""])
    if report.next_recommendation is None:
        lines.append("- none")
    else:
        lines.extend(
            [
                f"- Work package: `{_md(report.next_recommendation.work_package_id)}`",
                f"- Summary: {_md(report.next_recommendation.summary)}",
                f"- User value: {_md(report.next_recommendation.user_value)}",
            ]
        )
    lines.extend(
        [
            "",
            "## Owner Action",
            "",
            f"Owner action: {_md(report.owner_action)}",
        ]
    )
    if report.owner_decision:
        lines.append(f"Decision needed: {_md(report.owner_decision)}")
    return "\n".join(lines) + "\n"


def _normalize_work_package(value: Any, path: str) -> WorkPackageReference:
    data = _mapping(value, path)
    _reject_unknown_fields(data, _WORK_PACKAGE_FIELDS, path)
    return WorkPackageReference(
        work_package_id=_required_id(data, "work_package_id", path),
        milestone_id=_required_id(data, "milestone_id", path),
        summary=_required_text(data, "summary", path, maximum=MAX_SUMMARY_CHARS),
    )


def _normalize_validations(value: Any, path: str) -> tuple[ValidationResult, ...]:
    values = _mapping_sequence(value, path, maximum=MAX_VALIDATIONS)
    results: list[ValidationResult] = []
    names: list[str] = []
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        _reject_unknown_fields(item, _VALIDATION_FIELDS, item_path)
        name = _required_text(item, "name", item_path)
        status = _required_id(item, "status", item_path)
        if status not in VALIDATION_STATUSES:
            raise ManagerReportingError(f"{item_path}.status is not supported")
        evidence = _required_text(
            item,
            "evidence",
            item_path,
            maximum=MAX_SUMMARY_CHARS,
        )
        names.append(name.casefold())
        results.append(ValidationResult(name=name, status=status, evidence=evidence))
    _reject_duplicates(names, f"{path}.name")
    return tuple(results)


def _normalize_qa_strategy(value: Any, path: str) -> QAStrategy:
    data = _mapping(value, path)
    _reject_unknown_fields(data, _QA_FIELDS, path)
    level = _required_id(data, "level", path)
    if level not in QA_LEVELS:
        raise ManagerReportingError(f"{path}.level is not supported")
    reason = _required_text(data, "reason", path, maximum=MAX_SUMMARY_CHARS)
    server_started = _required_bool(data, "server_started", path)
    cleanup_status = _required_id(data, "cleanup_status", path)
    if cleanup_status not in CLEANUP_STATUSES:
        raise ManagerReportingError(f"{path}.cleanup_status is not supported")
    if server_started and cleanup_status == "not_required":
        raise ManagerReportingError(
            f"{path}.cleanup_status must record server cleanup"
        )
    if not server_started and cleanup_status != "not_required":
        raise ManagerReportingError(
            f"{path}.cleanup_status must be not_required when no server started"
        )
    return QAStrategy(
        level=level,
        reason=reason,
        server_started=server_started,
        cleanup_status=cleanup_status,
    )


def _normalize_safety_boundary(value: Any, path: str) -> SafetyBoundary:
    data = _mapping(value, path)
    _reject_unknown_fields(data, _SAFETY_FIELDS, path)
    return SafetyBoundary(
        protected_paths_untouched=_required_bool(
            data,
            "protected_paths_untouched",
            path,
        ),
        external_calls_made=_required_bool(data, "external_calls_made", path),
        push_or_pr_created=_required_bool(data, "push_or_pr_created", path),
        destructive_change_made=_required_bool(
            data,
            "destructive_change_made",
            path,
        ),
        clipboard_output_only=_required_bool(data, "clipboard_output_only", path),
        unexpected_repository_changes=_path_list(
            data.get("unexpected_repository_changes"),
            f"{path}.unexpected_repository_changes",
        ),
    )


def _normalize_completed_packages(
    value: Any,
    path: str,
) -> tuple[CompletedWorkPackage, ...]:
    values = _mapping_sequence(value, path, maximum=MAX_LIST_ITEMS)
    packages: list[CompletedWorkPackage] = []
    ids: list[str] = []
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        _reject_unknown_fields(item, _COMPLETED_PACKAGE_FIELDS, item_path)
        package_id = _required_id(item, "work_package_id", item_path)
        result_type = _required_id(item, "result_type", item_path)
        if result_type not in RESULT_TYPES:
            raise ManagerReportingError(f"{item_path}.result_type is not supported")
        commit_hash = _optional_hash(item, "commit_hash", item_path)
        ids.append(package_id)
        packages.append(
            CompletedWorkPackage(
                work_package_id=package_id,
                result_type=result_type,
                summary=_required_text(
                    item,
                    "summary",
                    item_path,
                    maximum=MAX_SUMMARY_CHARS,
                ),
                commit_hash=commit_hash,
            )
        )
    _reject_duplicates(ids, f"{path}.work_package_id")
    return tuple(packages)


def _normalize_risks(value: Any, path: str) -> tuple[ManagerRisk, ...]:
    values = _mapping_sequence(value, path, maximum=MAX_RISKS)
    risks: list[ManagerRisk] = []
    identities: list[str] = []
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        _reject_unknown_fields(item, _RISK_FIELDS, item_path)
        severity = _required_id(item, "severity", item_path)
        if severity not in RISK_SEVERITIES:
            raise ManagerReportingError(f"{item_path}.severity is not supported")
        category = _required_id(item, "category", item_path)
        summary = _required_text(
            item,
            "summary",
            item_path,
            maximum=MAX_SUMMARY_CHARS,
        )
        identities.append(f"{severity}:{category}:{summary.casefold()}")
        risks.append(
            ManagerRisk(
                severity=severity,
                category=category,
                summary=summary,
            )
        )
    _reject_duplicates(identities, path)
    return tuple(risks)


def _normalize_optional_recommendation(
    value: Any,
    path: str,
) -> NextRecommendation | None:
    if value is None:
        return None
    data = _mapping(value, path)
    _reject_unknown_fields(data, _RECOMMENDATION_FIELDS, path)
    return NextRecommendation(
        work_package_id=_required_id(data, "work_package_id", path),
        summary=_required_text(
            data,
            "summary",
            path,
            maximum=MAX_SUMMARY_CHARS,
        ),
        user_value=_required_text(
            data,
            "user_value",
            path,
            maximum=MAX_SUMMARY_CHARS,
        ),
    )


def _validate_worker_report_instance(report: WorkerReport) -> WorkerReport:
    if not isinstance(report, WorkerReport):
        raise ManagerReportingError("Worker Report renderer requires a WorkerReport")
    normalized = normalize_worker_report(_worker_report_mapping(report))
    if normalized != report:
        raise ManagerReportingError("Worker Report instance is not canonical")
    return report


def _validate_manager_report_instance(report: ManagerReport) -> ManagerReport:
    if not isinstance(report, ManagerReport):
        raise ManagerReportingError("Manager Report renderer requires a ManagerReport")
    normalized = normalize_manager_report(_manager_report_mapping(report))
    if normalized != report:
        raise ManagerReportingError("Manager Report instance is not canonical")
    return report


def _worker_report_mapping(report: WorkerReport) -> dict[str, Any]:
    if not isinstance(report.work_package, WorkPackageReference):
        raise ManagerReportingError("Worker Report work_package is not canonical")
    if not isinstance(report.qa_strategy, QAStrategy):
        raise ManagerReportingError("Worker Report qa_strategy is not canonical")
    if not isinstance(report.safety_boundary, SafetyBoundary):
        raise ManagerReportingError("Worker Report safety_boundary is not canonical")
    if any(not isinstance(item, ValidationResult) for item in report.validation_results):
        raise ManagerReportingError("Worker Report validation_results are not canonical")
    return {
        "contract_type": report.contract_type,
        "version": report.version,
        "work_package": {
            "work_package_id": report.work_package.work_package_id,
            "milestone_id": report.work_package.milestone_id,
            "summary": report.work_package.summary,
        },
        "result_type": report.result_type,
        "changed_files": list(report.changed_files),
        "validation_results": [
            {
                "name": result.name,
                "status": result.status,
                "evidence": result.evidence,
            }
            for result in report.validation_results
        ],
        "qa_strategy": {
            "level": report.qa_strategy.level,
            "reason": report.qa_strategy.reason,
            "server_started": report.qa_strategy.server_started,
            "cleanup_status": report.qa_strategy.cleanup_status,
        },
        "self_review_findings": list(report.self_review_findings),
        "commit_hash": report.commit_hash,
        "commit_subject": report.commit_subject,
        "final_git_status": list(report.final_git_status),
        "blockers": list(report.blockers),
        "safety_boundary": {
            "protected_paths_untouched": report.safety_boundary.protected_paths_untouched,
            "external_calls_made": report.safety_boundary.external_calls_made,
            "push_or_pr_created": report.safety_boundary.push_or_pr_created,
            "destructive_change_made": report.safety_boundary.destructive_change_made,
            "clipboard_output_only": report.safety_boundary.clipboard_output_only,
            "unexpected_repository_changes": list(
                report.safety_boundary.unexpected_repository_changes
            ),
        },
    }


def _manager_report_mapping(report: ManagerReport) -> dict[str, Any]:
    if any(
        not isinstance(item, CompletedWorkPackage)
        for item in report.completed_work_packages
    ):
        raise ManagerReportingError(
            "Manager Report completed_work_packages are not canonical"
        )
    if any(not isinstance(item, ManagerRisk) for item in report.risks):
        raise ManagerReportingError("Manager Report risks are not canonical")
    if report.next_recommendation is not None and not isinstance(
        report.next_recommendation,
        NextRecommendation,
    ):
        raise ManagerReportingError(
            "Manager Report next_recommendation is not canonical"
        )
    recommendation = (
        None
        if report.next_recommendation is None
        else {
            "work_package_id": report.next_recommendation.work_package_id,
            "summary": report.next_recommendation.summary,
            "user_value": report.next_recommendation.user_value,
        }
    )
    return {
        "contract_type": report.contract_type,
        "version": report.version,
        "source_of_truth": report.source_of_truth,
        "derived_view": report.derived_view,
        "current_goal": report.current_goal,
        "milestone_id": report.milestone_id,
        "milestone_meaning": report.milestone_meaning,
        "user_outcome": report.user_outcome,
        "completed_work_packages": [
            {
                "work_package_id": package.work_package_id,
                "result_type": package.result_type,
                "summary": package.summary,
                "commit_hash": package.commit_hash,
            }
            for package in report.completed_work_packages
        ],
        "current_position": report.current_position,
        "status": report.status,
        "evidence_summary": list(report.evidence_summary),
        "source_conflicts": list(report.source_conflicts),
        "risks": [
            {
                "severity": risk.severity,
                "category": risk.category,
                "summary": risk.summary,
            }
            for risk in report.risks
        ],
        "next_recommendation": recommendation,
        "owner_action": report.owner_action,
        "owner_decision": report.owner_decision,
    }


def _worker_safety_violations(
    qa_strategy: QAStrategy,
    safety: SafetyBoundary,
) -> tuple[str, ...]:
    violations: list[str] = []
    if not safety.protected_paths_untouched:
        violations.append("protected_paths")
    if safety.external_calls_made:
        violations.append("external_calls")
    if safety.push_or_pr_created:
        violations.append("push_or_pr")
    if safety.destructive_change_made:
        violations.append("destructive_change")
    if not safety.clipboard_output_only:
        violations.append("clipboard_state")
    if safety.unexpected_repository_changes:
        violations.append("unexpected_repository_changes")
    if qa_strategy.cleanup_status == "failed":
        violations.append("process_cleanup")
    return tuple(violations)


def _parse_json_object(text: str, label: str) -> Mapping[str, Any]:
    if not isinstance(text, str):
        raise ManagerReportingError(f"{label} JSON must be text")
    try:
        encoded = text.encode("utf-8")
    except UnicodeError as exc:
        raise ManagerReportingError(f"{label} JSON must be valid UTF-8") from exc
    if not encoded:
        raise ManagerReportingError(f"{label} JSON must not be empty")
    if len(encoded) > MAX_JSON_BYTES:
        raise ManagerReportingError(f"{label} JSON exceeds the input limit")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_finite_json,
        )
    except ManagerReportingError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ManagerReportingError(f"{label} JSON is malformed") from exc
    return _mapping(value, label)


def _serialize(value: Mapping[str, Any], label: str) -> str:
    text = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise ManagerReportingError(f"{label} exceeds the output limit")
    return text + "\n"


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ManagerReportingError(f"{path} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ManagerReportingError(f"{path} contains a non-text field name")
    return value


def _mapping_sequence(
    value: Any,
    path: str,
    *,
    maximum: int,
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, (list, tuple)):
        raise ManagerReportingError(f"{path} must be a list")
    if len(value) > maximum:
        raise ManagerReportingError(f"{path} contains too many items")
    return tuple(_mapping(item, f"{path}[{index}]") for index, item in enumerate(value))


def _required_text(
    data: Mapping[str, Any],
    field: str,
    path: str,
    *,
    maximum: int = MAX_TEXT_CHARS,
) -> str:
    if field not in data:
        raise ManagerReportingError(f"{path}.{field} is required")
    value = data[field]
    if not isinstance(value, str):
        raise ManagerReportingError(f"{path}.{field} must be text")
    if not value or value != value.strip():
        raise ManagerReportingError(f"{path}.{field} must be non-empty trimmed text")
    if len(value) > maximum:
        raise ManagerReportingError(f"{path}.{field} is too long")
    if _contains_control(value):
        raise ManagerReportingError(f"{path}.{field} contains a control character")
    return value


def _optional_text(
    data: Mapping[str, Any],
    field: str,
    path: str,
    *,
    maximum: int,
) -> str:
    if field not in data:
        raise ManagerReportingError(f"{path}.{field} is required")
    value = data[field]
    if not isinstance(value, str):
        raise ManagerReportingError(f"{path}.{field} must be text")
    if value and value != value.strip():
        raise ManagerReportingError(f"{path}.{field} must be trimmed text")
    if len(value) > maximum:
        raise ManagerReportingError(f"{path}.{field} is too long")
    if _contains_control(value):
        raise ManagerReportingError(f"{path}.{field} contains a control character")
    return value


def _required_id(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _required_text(data, field, path)
    if not _ID_PATTERN.fullmatch(value):
        raise ManagerReportingError(
            f"{path}.{field} must be a normalized lowercase ID"
        )
    return value


def _required_bool(data: Mapping[str, Any], field: str, path: str) -> bool:
    if field not in data or not isinstance(data[field], bool):
        raise ManagerReportingError(f"{path}.{field} must be a boolean")
    return data[field]


def _optional_hash(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _optional_text(data, field, path, maximum=40)
    if value and not _HASH_PATTERN.fullmatch(value):
        raise ManagerReportingError(
            f"{path}.{field} must be empty or a full lowercase Git hash"
        )
    return value


def _text_list(
    value: Any,
    path: str,
    *,
    maximum: int,
    require_nonempty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ManagerReportingError(f"{path} must be a list")
    if len(value) > maximum:
        raise ManagerReportingError(f"{path} contains too many items")
    if require_nonempty and not value:
        raise ManagerReportingError(f"{path} must not be empty")
    normalized: list[str] = []
    identities: list[str] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if not isinstance(item, str):
            raise ManagerReportingError(f"{item_path} must be text")
        if not item or item != item.strip():
            raise ManagerReportingError(f"{item_path} must be non-empty trimmed text")
        if len(item) > MAX_SUMMARY_CHARS:
            raise ManagerReportingError(f"{item_path} is too long")
        if _contains_control(item):
            raise ManagerReportingError(f"{item_path} contains a control character")
        normalized.append(item)
        identities.append(item.casefold())
    _reject_duplicates(identities, path)
    return tuple(normalized)


def _path_list(value: Any, path: str) -> tuple[str, ...]:
    values = _text_list(value, path, maximum=MAX_LIST_ITEMS)
    normalized = tuple(_relative_path(item, f"{path}[{index}]") for index, item in enumerate(values))
    _reject_duplicates((item.casefold() for item in normalized), path)
    return normalized


def _status_list(value: Any, path: str) -> tuple[str, ...]:
    values = _text_list(value, path, maximum=MAX_LIST_ITEMS)
    for index, item in enumerate(values):
        if len(item) > MAX_STATUS_CHARS:
            raise ManagerReportingError(f"{path}[{index}] is too long")
        if len(item) < 4 or item[2] != " ":
            raise ManagerReportingError(
                f"{path}[{index}] must be a git status --short line"
            )
    return values


def _relative_path(value: str, path: str) -> str:
    if len(value) > MAX_PATH_CHARS:
        raise ManagerReportingError(f"{path} is too long")
    normalized = value.replace("\\", "/")
    if (
        normalized.startswith("/")
        or _WINDOWS_DRIVE.match(normalized)
        or "\x00" in normalized
    ):
        raise ManagerReportingError(f"{path} must be repository-relative")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ManagerReportingError(f"{path} contains an unsafe path segment")
    return "/".join(parts)


def _reject_unknown_fields(
    data: Mapping[str, Any],
    allowed: frozenset[str],
    path: str,
) -> None:
    unknown = sorted(set(data) - allowed)
    missing = sorted(allowed - set(data))
    if unknown:
        raise ManagerReportingError(
            f"{path} contains unknown fields: {', '.join(unknown)}"
        )
    if missing:
        raise ManagerReportingError(
            f"{path} is missing fields: {', '.join(missing)}"
        )


def _reject_duplicates(values: Any, path: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ManagerReportingError(f"{path} contains duplicate values")
        seen.add(value)


def _contains_control(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManagerReportingError(
                f"report JSON contains duplicate key: {key}"
            )
        result[key] = value
    return result


def _reject_non_finite_json(value: str) -> Any:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ManagerReportingError(
            f"report JSON contains non-finite value: {value}"
        )
    return parsed


def _markdown_items(
    values: tuple[str, ...],
    empty: str,
    *,
    indent: str = "",
) -> list[str]:
    if not values:
        return [f"{indent}- {empty}"]
    return [f"{indent}- `{_md(value)}`" for value in values]


def _md(value: str) -> str:
    return value.replace("\\", "\\\\").replace("`", "\\`").replace("<", "&lt;")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
