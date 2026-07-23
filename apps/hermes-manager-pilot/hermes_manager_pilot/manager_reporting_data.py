"""Pure adapters from existing Hermes evidence into reporting contracts.

Callers retain all I/O authority. This module accepts normalized existing
objects and bounded mappings, cross-checks their identities, and returns the
transport-neutral contracts from :mod:`manager_reporting`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .manager_reporting import (
    MANAGER_CONTRACT_TYPE,
    SOURCE_OF_TRUTH,
    VERSION,
    WORKER_CONTRACT_TYPE,
    ManagerReport,
    ManagerReportingError,
    WorkerReport,
    manager_report_to_dict,
    normalize_manager_report,
    normalize_worker_report,
    worker_report_to_dict,
)
from .prompt_queue import (
    PromptQueueState,
    QueueEvaluation,
    QueueItem,
    evaluate_queue_item,
)
from .review_record import ReviewRecord, review_record_to_dict
from .schemas import SessionState


PROJECT_ID = "jarvis-core"
PROTECTED_UNTRACKED_PATH = "jarvis.bat"
MASTER_PLAN_SOURCE = "docs/master-plan.md"

_MASTER_PLAN_FIELDS = frozenset(
    {
        "source",
        "current_goal",
        "manager_reporting_milestone_id",
        "manager_reporting_status",
        "current_reason",
        "owner_outcome",
        "current_milestone",
        "recommended_next_step",
        "approval_state",
        "approval_note",
        "branch",
        "verified_implementation_head",
        "known_protected_untracked_file",
    }
)
_LIVE_GIT_FIELDS = frozenset({"branch", "head", "status", "recent_commit_hashes"})
_EXECUTION_SAFETY_FIELDS = frozenset(
    {
        "external_calls_made",
        "push_or_pr_created",
        "destructive_change_made",
        "clipboard_output_only",
    }
)
_QA_FIELDS = frozenset({"level", "reason", "server_started", "cleanup_status"})
_VALIDATION_FIELDS = frozenset({"name", "status", "evidence"})
_RISK_FIELDS = frozenset({"severity", "category", "summary"})
_RECOMMENDATION_FIELDS = frozenset(
    {"work_package_id", "summary", "user_value"}
)
_CHECKPOINT_PACKAGE_FIELDS = frozenset(
    {"work_package_id", "result_type", "summary", "commit_hash"}
)
_CHECKPOINT_SNAPSHOT_FIELDS = _MASTER_PLAN_FIELDS | frozenset(
    {
        "manager_reporting_work_packages",
        "manager_reporting_next_package_id",
        "next_user_visible_milestone",
    }
)


class ManagerReportingDataError(ValueError):
    """Raised when existing evidence sources disagree or are incomplete."""


def build_worker_report_from_sources(
    *,
    work_package_id: str,
    milestone_id: str,
    session: SessionState,
    queue: PromptQueueState,
    item_id: str,
    validation_results: Sequence[Mapping[str, Any]],
    qa_strategy: Mapping[str, Any],
    self_review_findings: Sequence[str],
    commit_hash: str,
    commit_subject: str,
    final_git_status: Sequence[str],
    execution_safety: Mapping[str, Any],
    review_record: ReviewRecord | None = None,
) -> WorkerReport:
    """Cross-check existing sources and derive one detailed Worker Report."""

    if not isinstance(session, SessionState):
        raise ManagerReportingDataError("session must be a normalized SessionState")
    if not isinstance(queue, PromptQueueState):
        raise ManagerReportingDataError("queue must be a normalized PromptQueueState")
    if review_record is not None and not isinstance(review_record, ReviewRecord):
        raise ManagerReportingDataError(
            "review_record must be a normalized ReviewRecord"
        )
    item = _find_item(queue, item_id)
    project = _find_project(queue, item.project_id)
    evaluation = evaluate_queue_item(queue, item.item_id)
    conflicts = _worker_source_conflicts(
        session=session,
        item=item,
        evaluation=evaluation,
        project=project,
        review_record=review_record,
    )
    if conflicts:
        raise ManagerReportingDataError(
            "Worker evidence sources conflict: " + "; ".join(conflicts)
        )

    qa = _exact_mapping(qa_strategy, _QA_FIELDS, "qa_strategy")
    safety = _exact_mapping(
        execution_safety,
        _EXECUTION_SAFETY_FIELDS,
        "execution_safety",
    )
    validation_items = [
        dict(_exact_mapping(item, _VALIDATION_FIELDS, f"validation_results[{index}]"))
        for index, item in enumerate(validation_results)
    ]
    final_status = tuple(_bounded_text_list(final_git_status, "final_git_status"))
    unexpected = _unexpected_final_changes(
        final_status,
        item.target_files,
        project.expected_untracked,
        commit_created=bool(commit_hash),
    )
    protected_paths_untouched = not _protected_path_changed(
        final_status,
        project.protected_paths,
        project.expected_untracked,
    )
    blockers = list(evaluation.blocking_reasons)
    result_type = "blocked" if blockers else item.result_type

    payload = {
        "contract_type": WORKER_CONTRACT_TYPE,
        "version": VERSION,
        "work_package": {
            "work_package_id": work_package_id,
            "milestone_id": milestone_id,
            "summary": item.current_task,
        },
        "result_type": result_type,
        "changed_files": list(evaluation.observed_changed_files),
        "validation_results": validation_items,
        "qa_strategy": dict(qa),
        "self_review_findings": list(self_review_findings),
        "commit_hash": commit_hash,
        "commit_subject": commit_subject,
        "final_git_status": list(final_status),
        "blockers": blockers,
        "safety_boundary": {
            "protected_paths_untouched": protected_paths_untouched,
            "external_calls_made": safety["external_calls_made"],
            "push_or_pr_created": safety["push_or_pr_created"],
            "destructive_change_made": safety["destructive_change_made"],
            "clipboard_output_only": safety["clipboard_output_only"],
            "unexpected_repository_changes": list(unexpected),
        },
    }
    try:
        return normalize_worker_report(payload)
    except ManagerReportingError as exc:
        raise ManagerReportingDataError(
            f"derived Worker Report is invalid: {exc}"
        ) from exc


def build_manager_report_from_sources(
    *,
    master_plan_snapshot: Mapping[str, Any],
    worker_reports: Sequence[WorkerReport],
    live_git_evidence: Mapping[str, Any],
    risks: Sequence[Mapping[str, Any]],
    next_recommendation: Mapping[str, Any] | None,
) -> ManagerReport:
    """Derive one Owner-facing report and fail closed on source conflicts."""

    snapshot = _required_fields(
        master_plan_snapshot,
        _MASTER_PLAN_FIELDS,
        "master_plan_snapshot",
    )
    live_git = _exact_mapping(
        live_git_evidence,
        _LIVE_GIT_FIELDS,
        "live_git_evidence",
    )
    normalized_workers = tuple(
        _validated_worker_report(report, index)
        for index, report in enumerate(worker_reports)
    )
    normalized_risks = [
        dict(_exact_mapping(risk, _RISK_FIELDS, f"risks[{index}]"))
        for index, risk in enumerate(risks)
    ]
    recommendation = (
        None
        if next_recommendation is None
        else dict(
            _exact_mapping(
                next_recommendation,
                _RECOMMENDATION_FIELDS,
                "next_recommendation",
            )
        )
    )
    conflicts = _manager_source_conflicts(snapshot, normalized_workers, live_git)
    blocking_risk = any(risk["severity"] == "blocking" for risk in normalized_risks)

    if conflicts or blocking_risk:
        status = "blocked"
        owner_action = "decision_required"
        if conflicts:
            owner_decision = (
                "Resolve reporting source conflicts before continuing: "
                + "; ".join(conflicts)
            )
        else:
            owner_decision = (
                "Resolve the blocking Manager Report risk before continuing."
            )
        recommendation = None
    else:
        status = _required_text(snapshot, "manager_reporting_status", "master plan")
        approval_state = _required_text(snapshot, "approval_state", "master plan")
        if approval_state == "none":
            owner_action = "none"
            owner_decision = ""
        elif approval_state in {"required", "blocked"}:
            owner_action = "decision_required"
            owner_decision = _required_text(
                snapshot,
                "approval_note",
                "master plan",
            )
        else:
            raise ManagerReportingDataError(
                "master plan approval_state is not supported"
            )

    completed = []
    for report in normalized_workers:
        completed.append(
            {
                "work_package_id": report.work_package.work_package_id,
                "result_type": report.result_type,
                "summary": report.work_package.summary,
                "commit_hash": report.commit_hash,
            }
        )
    validation_count = sum(
        len(report.validation_results) for report in normalized_workers
    )
    commit_count = sum(bool(report.commit_hash) for report in normalized_workers)
    evidence_summary = [
        (
            f"{len(normalized_workers)} Worker Report contract(s) passed "
            "cross-source identity checks."
        ),
        (
            f"{validation_count} bounded validation result(s) and "
            f"{commit_count} local commit reference(s) were reviewed."
        ),
        (
            "Caller-supplied live Git evidence was compared with the Master Plan "
            "branch, protected status, verified HEAD, and package commits."
        ),
    ]
    payload = {
        "contract_type": MANAGER_CONTRACT_TYPE,
        "version": VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "derived_view": True,
        "current_goal": _required_text(snapshot, "current_goal", "master plan"),
        "milestone_id": _required_text(
            snapshot,
            "manager_reporting_milestone_id",
            "master plan",
        ),
        "milestone_meaning": _required_text(
            snapshot,
            "current_reason",
            "master plan",
        ),
        "user_outcome": _required_text(
            snapshot,
            "owner_outcome",
            "master plan",
        ),
        "completed_work_packages": completed,
        "current_position": _required_text(
            snapshot,
            "current_milestone",
            "master plan",
        ),
        "status": status,
        "evidence_summary": evidence_summary,
        "source_conflicts": list(conflicts),
        "risks": normalized_risks,
        "next_recommendation": recommendation,
        "owner_action": owner_action,
        "owner_decision": owner_decision,
    }
    try:
        return normalize_manager_report(payload)
    except ManagerReportingError as exc:
        raise ManagerReportingDataError(
            f"derived Manager Report is invalid: {exc}"
        ) from exc


def manager_report_projection(report: ManagerReport) -> dict[str, Any]:
    """Return a detached read-only presentation mapping."""

    projected = manager_report_to_dict(report)
    projected["read_only"] = True
    projected["authority_boundary"] = "derived_reporting_only"
    return projected


def build_manager_report_from_checkpoint_sources(
    *,
    master_plan_snapshot: Mapping[str, Any],
    live_git_evidence: Mapping[str, Any],
    risks: Sequence[Mapping[str, Any]],
) -> ManagerReport:
    """Build the restart-safe Owner view from tracked checkpoint and Git facts.

    Historical Worker Reports are intentionally not persisted. The Master Plan
    records only bounded completed-package summaries and commit hashes after
    Manager review; current Git evidence verifies those references.
    """

    snapshot = _required_fields(
        master_plan_snapshot,
        _CHECKPOINT_SNAPSHOT_FIELDS,
        "master_plan_snapshot",
    )
    live_git = _exact_mapping(
        live_git_evidence,
        _LIVE_GIT_FIELDS,
        "live_git_evidence",
    )
    packages_value = snapshot["manager_reporting_work_packages"]
    if not isinstance(packages_value, (list, tuple)):
        raise ManagerReportingDataError(
            "master_plan_snapshot.manager_reporting_work_packages must be a list"
        )
    if not packages_value or len(packages_value) > 16:
        raise ManagerReportingDataError(
            "master_plan_snapshot.manager_reporting_work_packages is empty or too large"
        )
    packages: list[dict[str, Any]] = []
    package_ids: set[str] = set()
    for index, value in enumerate(packages_value):
        item = dict(
            _exact_mapping(
                value,
                _CHECKPOINT_PACKAGE_FIELDS,
                f"manager_reporting_work_packages[{index}]",
            )
        )
        package_id = _required_text(
            item,
            "work_package_id",
            f"manager_reporting_work_packages[{index}]",
        )
        if package_id in package_ids:
            raise ManagerReportingDataError(
                "manager_reporting_work_packages contains duplicate package IDs"
            )
        package_ids.add(package_id)
        packages.append(item)

    normalized_risks = [
        dict(_exact_mapping(risk, _RISK_FIELDS, f"risks[{index}]"))
        for index, risk in enumerate(risks)
    ]
    conflicts = list(_checkpoint_source_conflicts(snapshot, packages, live_git))
    blocking_risk = any(risk["severity"] == "blocking" for risk in normalized_risks)
    if blocking_risk:
        conflicts.append("Project Control has a blocking Manager Report risk")

    if conflicts:
        status = "blocked"
        owner_action = "decision_required"
        owner_decision = (
            "Resolve reporting source conflicts before continuing: "
            + "; ".join(_deduplicate(conflicts))
        )
        recommendation = None
    else:
        status = _required_text(snapshot, "manager_reporting_status", "master plan")
        approval_state = _required_text(snapshot, "approval_state", "master plan")
        if approval_state == "none":
            owner_action = "none"
            owner_decision = ""
        elif approval_state in {"required", "blocked"}:
            owner_action = "decision_required"
            owner_decision = _required_text(
                snapshot,
                "approval_note",
                "master plan",
            )
        else:
            raise ManagerReportingDataError(
                "master plan approval_state is not supported"
            )
        if status == "milestone_complete":
            recommendation = None
        else:
            recommendation = {
                "work_package_id": _required_text(
                    snapshot,
                    "manager_reporting_next_package_id",
                    "master plan",
                ),
                "summary": _required_text(
                    snapshot,
                    "recommended_next_step",
                    "master plan",
                ),
                "user_value": _required_text(
                    snapshot,
                    "next_user_visible_milestone",
                    "master plan",
                ),
            }

    live_head = _required_hash(live_git, "head", "live Git")
    payload = {
        "contract_type": MANAGER_CONTRACT_TYPE,
        "version": VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "derived_view": True,
        "current_goal": _required_text(snapshot, "current_goal", "master plan"),
        "milestone_id": _required_text(
            snapshot,
            "manager_reporting_milestone_id",
            "master plan",
        ),
        "milestone_meaning": _required_text(
            snapshot,
            "current_reason",
            "master plan",
        ),
        "user_outcome": _required_text(
            snapshot,
            "owner_outcome",
            "master plan",
        ),
        "completed_work_packages": packages,
        "current_position": _required_text(
            snapshot,
            "current_milestone",
            "master plan",
        ),
        "status": status,
        "evidence_summary": [
            (
                f"{len(packages)} reviewed package checkpoint(s) were read from "
                "the tracked Master Plan."
            ),
            (
                "Every checkpoint commit was found in bounded recent local Git "
                "evidence."
            ),
            (
                f"Live branch and protected status were checked at HEAD "
                f"{live_head[:7]}."
            ),
        ],
        "source_conflicts": list(_deduplicate(conflicts)),
        "risks": normalized_risks,
        "next_recommendation": recommendation,
        "owner_action": owner_action,
        "owner_decision": owner_decision,
    }
    try:
        return normalize_manager_report(payload)
    except ManagerReportingError as exc:
        raise ManagerReportingDataError(
            f"derived checkpoint Manager Report is invalid: {exc}"
        ) from exc


def _worker_source_conflicts(
    *,
    session: SessionState,
    item: QueueItem,
    evaluation: QueueEvaluation,
    project: Any,
    review_record: ReviewRecord | None,
) -> tuple[str, ...]:
    conflicts: list[str] = []
    if item.project_id != PROJECT_ID:
        conflicts.append("Prompt Queue project is not jarvis-core")
    if session.repo != project.repo_path:
        conflicts.append("Session repository differs from Prompt Queue")
    if session.current_goal != item.current_goal:
        conflicts.append("Session goal differs from Prompt Queue")
    if session.active_task != item.current_task:
        conflicts.append("Session task differs from Prompt Queue")
    if _canonical_paths(session.target_files) != _canonical_paths(item.target_files):
        conflicts.append("Session target scope differs from Prompt Queue")
    if session.branch != item.observed_branch or session.branch != project.expected_branch:
        conflicts.append("Session branch differs from Prompt Queue")
    if session.head != item.observed_head or session.head != project.expected_head:
        conflicts.append("Session HEAD differs from Prompt Queue")
    if tuple(session.validation_commands) != tuple(project.validation_commands):
        conflicts.append("Session validation commands differ from Prompt Queue")
    if PROTECTED_UNTRACKED_PATH.casefold() not in {
        path.casefold() for path in session.protected_paths
    }:
        conflicts.append("Session protected paths omit jarvis.bat")
    if _canonical_paths(session.files_touched) != _canonical_paths(
        evaluation.observed_changed_files
    ):
        conflicts.append("Session changed files differ from queue evaluation")

    if review_record is not None:
        record = review_record_to_dict(review_record)
        if record["project_id"] != item.project_id:
            conflicts.append("Review Record project differs from Prompt Queue")
        if record["current_goal"] != item.current_goal:
            conflicts.append("Review Record goal differs from Prompt Queue")
        if record["active_task"] != item.current_task:
            conflicts.append("Review Record task differs from Prompt Queue")
        if _canonical_paths(record["target_files"]) != _canonical_paths(
            item.target_files
        ):
            conflicts.append("Review Record target scope differs from Prompt Queue")
        snapshot = record["git_snapshot"]
        if snapshot["branch"] != item.observed_branch:
            conflicts.append("Review Record branch differs from Prompt Queue")
        if snapshot["head"] != item.observed_head:
            conflicts.append("Review Record HEAD differs from Prompt Queue")
        if tuple(snapshot["status"]) != tuple(sorted(item.observed_git_status, key=str.casefold)):
            conflicts.append("Review Record Git status differs from Prompt Queue")
        if tuple(record["validation_commands"]) != tuple(project.validation_commands):
            conflicts.append(
                "Review Record validation commands differ from Prompt Queue"
            )
    return tuple(_deduplicate(conflicts))


def _manager_source_conflicts(
    snapshot: Mapping[str, Any],
    worker_reports: tuple[WorkerReport, ...],
    live_git: Mapping[str, Any],
) -> tuple[str, ...]:
    conflicts: list[str] = []
    if _required_text(snapshot, "source", "master plan") != MASTER_PLAN_SOURCE:
        conflicts.append("Master Plan source path is not docs/master-plan.md")
    if (
        _required_text(snapshot, "known_protected_untracked_file", "master plan")
        != PROTECTED_UNTRACKED_PATH
    ):
        conflicts.append("Master Plan protected path is not jarvis.bat")
    snapshot_branch = _required_text(snapshot, "branch", "master plan")
    live_branch = _required_text(live_git, "branch", "live Git")
    if snapshot_branch != live_branch:
        conflicts.append("Live Git branch differs from Master Plan")
    live_head = _required_hash(live_git, "head", "live Git")
    recent_hashes = tuple(
        _bounded_text_list(live_git["recent_commit_hashes"], "recent_commit_hashes")
    )
    for index, value in enumerate(recent_hashes):
        if not _is_full_hash(value):
            raise ManagerReportingDataError(
                f"recent_commit_hashes[{index}] must be a full lowercase Git hash"
            )
    verified_head = _required_text(
        snapshot,
        "verified_implementation_head",
        "master plan",
    )
    if not any(commit.startswith(verified_head) for commit in (live_head, *recent_hashes)):
        conflicts.append("Verified implementation HEAD is absent from live Git evidence")

    live_status = _bounded_git_status_list(live_git["status"], "live Git status")
    if f"?? {PROTECTED_UNTRACKED_PATH}" not in live_status:
        conflicts.append("Live Git status is missing protected untracked jarvis.bat")
    if _protected_path_changed(
        live_status,
        (PROTECTED_UNTRACKED_PATH,),
        (PROTECTED_UNTRACKED_PATH,),
    ):
        conflicts.append("Protected jarvis.bat has tracked changes")

    milestone_id = _required_text(
        snapshot,
        "manager_reporting_milestone_id",
        "master plan",
    )
    recent_set = set(recent_hashes) | {live_head}
    for report in worker_reports:
        if report.work_package.milestone_id != milestone_id:
            conflicts.append(
                f"Worker Report {report.work_package.work_package_id} has another milestone"
            )
        if report.result_type == "blocked":
            conflicts.append(
                f"Worker Report {report.work_package.work_package_id} is blocked"
            )
        if any(result.status != "passed" for result in report.validation_results):
            conflicts.append(
                f"Worker Report {report.work_package.work_package_id} has unverified validation"
            )
        if report.self_review_findings:
            conflicts.append(
                f"Worker Report {report.work_package.work_package_id} has review findings"
            )
        if not report.commit_hash:
            conflicts.append(
                f"Worker Report {report.work_package.work_package_id} has no local commit"
            )
        elif report.commit_hash not in recent_set:
            conflicts.append(
                f"Worker Report {report.work_package.work_package_id} commit is absent from Git evidence"
            )
    return tuple(_deduplicate(conflicts))


def _checkpoint_source_conflicts(
    snapshot: Mapping[str, Any],
    packages: Sequence[Mapping[str, Any]],
    live_git: Mapping[str, Any],
) -> tuple[str, ...]:
    conflicts = list(_manager_source_conflicts(snapshot, (), live_git))
    milestone_id = _required_text(
        snapshot,
        "manager_reporting_milestone_id",
        "master plan",
    )
    recent_hashes = tuple(
        _bounded_text_list(live_git["recent_commit_hashes"], "recent_commit_hashes")
    )
    live_head = _required_hash(live_git, "head", "live Git")
    recent_set = set(recent_hashes) | {live_head}
    for index, package in enumerate(packages):
        package_id = _required_text(
            package,
            "work_package_id",
            f"manager_reporting_work_packages[{index}]",
        )
        if not package_id.startswith(milestone_id):
            conflicts.append(
                f"Checkpoint package {package_id} is outside the current milestone"
            )
        result_type = _required_text(
            package,
            "result_type",
            f"manager_reporting_work_packages[{index}]",
        )
        if result_type == "blocked":
            conflicts.append(f"Checkpoint package {package_id} is blocked")
        commit_hash = _required_hash(
            package,
            "commit_hash",
            f"manager_reporting_work_packages[{index}]",
        )
        if commit_hash not in recent_set:
            conflicts.append(
                f"Checkpoint package {package_id} commit is absent from Git evidence"
            )
    return tuple(_deduplicate(conflicts))


def _validated_worker_report(report: WorkerReport, index: int) -> WorkerReport:
    if not isinstance(report, WorkerReport):
        raise ManagerReportingDataError(
            f"worker_reports[{index}] must be a normalized WorkerReport"
        )
    try:
        mapping = worker_report_to_dict(report)
        return normalize_worker_report(mapping)
    except ManagerReportingError as exc:
        raise ManagerReportingDataError(
            f"worker_reports[{index}] is invalid: {exc}"
        ) from exc


def _find_item(queue: PromptQueueState, item_id: str) -> QueueItem:
    matches = tuple(item for item in queue.items if item.item_id == item_id)
    if len(matches) != 1:
        raise ManagerReportingDataError("item_id must select exactly one queue item")
    return matches[0]


def _find_project(queue: PromptQueueState, project_id: str) -> Any:
    matches = tuple(project for project in queue.projects if project.project_id == project_id)
    if len(matches) != 1:
        raise ManagerReportingDataError(
            "queue item must select exactly one project"
        )
    return matches[0]


def _required_fields(
    data: Mapping[str, Any],
    required: frozenset[str],
    path: str,
) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise ManagerReportingDataError(f"{path} must be an object")
    missing = sorted(required - set(data))
    if missing:
        raise ManagerReportingDataError(
            f"{path} is missing fields: {', '.join(missing)}"
        )
    return data


def _exact_mapping(
    data: Mapping[str, Any],
    fields: frozenset[str],
    path: str,
) -> Mapping[str, Any]:
    mapping = _required_fields(data, fields, path)
    unknown = sorted(set(mapping) - fields)
    if unknown:
        raise ManagerReportingDataError(
            f"{path} contains unknown fields: {', '.join(unknown)}"
        )
    return mapping


def _required_text(data: Mapping[str, Any], field: str, path: str) -> str:
    if field not in data:
        raise ManagerReportingDataError(f"{path}.{field} is required")
    value = data[field]
    if not isinstance(value, str) or not value or value != value.strip():
        raise ManagerReportingDataError(
            f"{path}.{field} must be non-empty trimmed text"
        )
    if len(value) > 4000 or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise ManagerReportingDataError(f"{path}.{field} is invalid")
    return value


def _required_hash(data: Mapping[str, Any], field: str, path: str) -> str:
    value = _required_text(data, field, path)
    if not _is_full_hash(value):
        raise ManagerReportingDataError(
            f"{path}.{field} must be a full lowercase Git hash"
        )
    return value


def _is_full_hash(value: str) -> bool:
    return len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def _bounded_text_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ManagerReportingDataError(f"{path} must be a list")
    if len(value) > 128:
        raise ManagerReportingDataError(f"{path} contains too many items")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item or item != item.strip():
            raise ManagerReportingDataError(
                f"{path}[{index}] must be non-empty trimmed text"
            )
        if len(item) > 4000 or any(
            ord(character) < 32 or ord(character) == 127 for character in item
        ):
            raise ManagerReportingDataError(f"{path}[{index}] is invalid")
        key = item.casefold()
        if key in seen:
            raise ManagerReportingDataError(f"{path} contains duplicate values")
        seen.add(key)
        normalized.append(item)
    return tuple(normalized)


def _bounded_git_status_list(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ManagerReportingDataError(f"{path} must be a list")
    if len(value) > 128:
        raise ManagerReportingDataError(f"{path} contains too many items")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise ManagerReportingDataError(
                f"{path}[{index}] must be a Git status line"
            )
        if len(item) > 4000 or any(
            ord(character) < 32 or ord(character) == 127 for character in item
        ):
            raise ManagerReportingDataError(f"{path}[{index}] is invalid")
        _parse_status_line(item)
        key = item.casefold()
        if key in seen:
            raise ManagerReportingDataError(f"{path} contains duplicate values")
        seen.add(key)
        normalized.append(item)
    return tuple(normalized)


def _unexpected_final_changes(
    status: tuple[str, ...],
    targets: tuple[str, ...],
    expected_untracked: tuple[str, ...],
    *,
    commit_created: bool,
) -> tuple[str, ...]:
    expected_keys = {path.casefold() for path in expected_untracked}
    unexpected: list[str] = []
    for line in status:
        code, path = _parse_status_line(line)
        if code == "??" and path.casefold() in expected_keys:
            continue
        if not _path_is_targeted(path, targets) or commit_created:
            unexpected.append(path)
    return tuple(sorted(set(unexpected), key=str.casefold))


def _protected_path_changed(
    status: tuple[str, ...],
    protected_paths: tuple[str, ...],
    expected_untracked: tuple[str, ...],
) -> bool:
    protected = {path.casefold() for path in protected_paths}
    expected = {path.casefold() for path in expected_untracked}
    for line in status:
        code, path = _parse_status_line(line)
        key = path.casefold()
        if key in protected and not (code == "??" and key in expected):
            return True
    return False


def _parse_status_line(line: str) -> tuple[str, str]:
    if not isinstance(line, str) or len(line) < 4 or line[2] != " ":
        raise ManagerReportingDataError("Git status line is malformed")
    code = line[:2]
    path = line[3:].replace("\\", "/")
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    if (
        not path
        or path.startswith("/")
        or ":" in path.split("/", 1)[0]
        or any(part in {"", ".", ".."} for part in path.split("/"))
    ):
        raise ManagerReportingDataError("Git status path is unsafe")
    return code, path


def _path_is_targeted(path: str, targets: tuple[str, ...]) -> bool:
    key = path.casefold()
    for target in targets:
        target_key = target.replace("\\", "/").rstrip("/").casefold()
        if key == target_key or key.startswith(target_key + "/"):
            return True
    return False


def _canonical_paths(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted((value.replace("\\", "/") for value in values), key=str.casefold))


def _deduplicate(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)
