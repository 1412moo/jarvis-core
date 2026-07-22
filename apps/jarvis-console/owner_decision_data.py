"""Pure read-only data adapter for the Owner Decision v0.1A contract.

The caller supplies an already bounded master-plan snapshot. This module does
not read files, expose routes, persist state, or perform any action.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from owner_decision import (
    ALLOWED_WORKSTREAMS,
    AUTHORITY_BOUNDARY,
    CONTRACT_TYPE,
    DECISION_KIND,
    PROJECT_ID,
    RESPONSE_TEMPLATE,
    VERSION,
    OwnerDecision,
    OwnerDecisionError,
    normalize_owner_decision,
)


OWNER_DECISION_OUTCOMES = {
    "hermes-manager": "Reduce manual prompt and review handoff friction through one bounded real-use improvement.",
    "memory-skills": "Review one complete guarded-memory vertical slice while all live save surfaces stay locked.",
    "jarvis-console": "Read the same Owner Decision object in the CLI and existing single-repo Owner Dashboard.",
    "research-council": "Improve one local idea and risk report from concrete real-use feedback.",
    "daily-ai-radar": "Improve one local scouting workflow without enabling external source collection.",
    "task-discord-dashboard": "Improve one bounded owner task workflow without unattended or remote execution.",
}
OWNER_DECISION_LOCKS = {
    "hermes-manager": (
        "Automatic Codex or ChatGPT invocation",
        "Automatic stage, commit, push, or pull request",
    ),
    "memory-skills": (
        "Live candidate save",
        "Saved candidates dashboard",
        "UI Save or Confirm",
        "Voice Inbox auto-save",
    ),
    "jarvis-console": (
        "Approval or execution action",
        "New route or persistence",
        "Second repository connection",
    ),
    "research-council": (
        "External research call",
        "Report treated as approval or verified proof",
    ),
    "daily-ai-radar": (
        "External source collection",
        "Recommendation treated as implementation approval",
    ),
    "task-discord-dashboard": (
        "Mobile or remote execution",
        "Unattended execution",
    ),
}


class OwnerDecisionDataError(ValueError):
    """Raised when bounded source data cannot produce a safe decision object."""


def build_owner_decision_from_snapshot(snapshot: Mapping[str, Any]) -> OwnerDecision:
    """Adapt one bounded master-plan snapshot into the v0.1A core contract."""

    if not isinstance(snapshot, Mapping):
        raise OwnerDecisionDataError("owner decision snapshot must be an object")
    workstreams_value = snapshot.get("workstreams")
    if not isinstance(workstreams_value, list):
        raise OwnerDecisionDataError("owner decision snapshot workstreams must be a list")

    workstreams_by_id: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(workstreams_value):
        if not isinstance(value, Mapping):
            raise OwnerDecisionDataError(
                f"owner decision snapshot workstreams[{index}] must be an object"
            )
        workstream_id = value.get("workstream_id")
        if not isinstance(workstream_id, str):
            raise OwnerDecisionDataError(
                f"owner decision snapshot workstreams[{index}].workstream_id is invalid"
            )
        if workstream_id in workstreams_by_id:
            raise OwnerDecisionDataError(
                "owner decision snapshot contains duplicate workstream IDs"
            )
        workstreams_by_id[workstream_id] = value

    expected_ids = tuple(workstream_id for workstream_id, _ in ALLOWED_WORKSTREAMS)
    if set(workstreams_by_id) != set(expected_ids):
        raise OwnerDecisionDataError(
            "owner decision snapshot must contain the exact allowed workstreams"
        )

    candidates = []
    for workstream_id, expected_name in ALLOWED_WORKSTREAMS:
        item = workstreams_by_id[workstream_id]
        display_name = _required_text(item, "display_name", workstream_id)
        if display_name != expected_name:
            raise OwnerDecisionDataError(
                f"owner decision snapshot display name does not match {workstream_id}"
            )
        candidates.append(
            {
                "workstream_id": workstream_id,
                "display_name": display_name,
                "current_capability": _required_text(
                    item,
                    "user_visible_capability",
                    workstream_id,
                ),
                "next_user_outcome": OWNER_DECISION_OUTCOMES[workstream_id],
                "locked_capabilities": list(OWNER_DECISION_LOCKS[workstream_id]),
            }
        )

    raw = {
        "contract_type": CONTRACT_TYPE,
        "version": VERSION,
        "project_id": PROJECT_ID,
        "decision_kind": DECISION_KIND,
        "status": _required_text(snapshot, "owner_decision_status", "snapshot"),
        "reason": _required_text(snapshot, "current_reason", "snapshot"),
        "authority_boundary": AUTHORITY_BOUNDARY,
        "recommended_workstream_id": _required_text(
            snapshot,
            "owner_decision_recommended_workstream_id",
            "snapshot",
        ),
        "candidates": candidates,
        "selected_workstream_id": None,
        "desired_outcome": None,
        "response_template": RESPONSE_TEMPLATE,
        "read_only": True,
    }
    try:
        return normalize_owner_decision(raw)
    except OwnerDecisionError as exc:
        raise OwnerDecisionDataError(f"owner decision snapshot is blocked: {exc}") from exc


def _required_text(data: Mapping[str, Any], field: str, path: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise OwnerDecisionDataError(f"owner decision {path}.{field} must be trimmed text")
    return value
