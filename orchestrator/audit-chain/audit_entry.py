"""Audit entry schema, canonical JSON serialization, and domain-separated hashing.

Implements task-0044 audit hash chain entry contracts and invariants:
- Contract: "jarvis_audit_entry", version: "0.1A"
- Domain separation: sha256(b"jarvis-core/audit-chain/v0.1A\\0" + canonical_bytes(entry_without_hash))
- Canonical JSON: compact, deterministic, sort_keys=True, allow_nan=False, no floats
- Kind schemas: owner_approval, execution_result
- No owner user ID or secrets allowed in payload
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import secrets
from typing import Any, Mapping

CONTRACT_TYPE = "jarvis_audit_entry"
VERSION = "0.1A"
DOMAIN_PREFIX = b"jarvis-core/audit-chain/v0.1A\0"
MAX_JSON_BYTES = 64 * 1024

UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ENTRY_ID_PATTERN = re.compile(r"^audit_[0-9a-f]{24}$")
HEX_64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TASK_ID_PATTERN = re.compile(r"^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")

ALLOWED_KINDS = frozenset({"owner_approval", "execution_result"})
ALLOWED_ACTORS = frozenset({"owner", "orchestrator"})
KIND_ACTOR_MAP = {
    "owner_approval": "owner",
    "execution_result": "orchestrator",
}
ALLOWED_STATUSES = frozenset(
    {"NEEDS_APPROVAL", "BLOCKED", "ON_HOLD", "FAILED", "DOING", "TODO", "DONE"}
)
ALLOWED_EXECUTION_SOURCES = frozenset({"approve_file_write_result", "run", "retry"})
ALLOWED_RESULT_KINDS = frozenset({"dry_run", "success", "failure"})

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "user_id",
        "author_id",
        "discord_user_id",
        "owner_id",
        "token",
        "secret",
        "api_key",
        "password",
        "credential",
    }
)


class AuditChainError(Exception):
    """Raised when an audit chain contract or invariant is violated.

    Owner decision Q5-B (design section 10): the error surface has two layers.
    ``code`` is a fixed, value-free vocabulary term and is the only thing that
    may reach a caller-facing ``reason``. ``detail`` carries the investigation
    information - the offending value, a path, a hash pair, an OS error - and
    stays internal. ``str(exc)`` renders the code alone on purpose, so no
    detail can leak through an incidental string conversion.
    """

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """One immutable, domain-hash-chained audit log entry."""

    contract_type: str
    version: str
    seq: int
    entry_id: str
    kind: str
    ts: str
    actor: str
    task_id: str
    payload: dict[str, Any]
    prev_hash: str | None
    hash: str


def generate_entry_id() -> str:
    """Return a fresh cryptographically random entry_id matching audit_<24hex>."""
    return f"audit_{secrets.token_hex(12)}"


def _validate_canonical_value(value: Any, path: str = "root") -> None:
    """Ensure data contains only canonicalizable types: int, str, bool, None, list, dict."""
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str):
            # Check for lone surrogates
            try:
                value.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise AuditChainError("surrogate_not_allowed", detail=path) from exc
        return
    if isinstance(value, float):
        raise AuditChainError("floats_not_allowed", detail=path)
    if isinstance(value, int):
        return
    if isinstance(value, (list, tuple)):
        for idx, item in enumerate(value):
            _validate_canonical_value(item, f"{path}[{idx}]")
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise AuditChainError("dict_key_must_be_str", detail=path)
            _validate_canonical_value(v, f"{path}.{k}")
        return
    raise AuditChainError(
        "unsupported_type", detail=f"{path}:{type(value).__name__}"
    )


def canonical_json(data: Any) -> str:
    """Return stable, compact, UTF-8 canonical JSON without floats."""
    _validate_canonical_value(data)
    serialized = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    encoded = serialized.encode("utf-8")
    if len(encoded) > MAX_JSON_BYTES:
        raise AuditChainError("audit_entry_exceeds_max_bytes")
    return serialized


def compute_entry_hash(entry_dict: Mapping[str, Any]) -> str:
    """Compute sha256(DOMAIN_PREFIX + canonical_bytes(entry_without_hash))."""
    entry_without_hash = {k: v for k, v in entry_dict.items() if k != "hash"}
    canonical_bytes = canonical_json(entry_without_hash).encode("utf-8")
    return hashlib.sha256(DOMAIN_PREFIX + canonical_bytes).hexdigest()


def _validate_owner_approval_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    # Owner decision Q5-B / defect 3: the forbidden-key guard runs FIRST. While the
    # key-set equality check ran ahead of it, it always won - any payload carrying a
    # forbidden key necessarily fails exact-key-set equality - so this guard was
    # unreachable and the rejection echoed the offending key names back out.
    for forbidden in FORBIDDEN_PAYLOAD_KEYS:
        if forbidden in payload:
            raise AuditChainError("forbidden_key_in_payload", detail=forbidden)

    expected_keys = {"command", "decision", "transition", "applied", "reason"}
    actual_keys = set(payload.keys())
    if actual_keys != expected_keys:
        raise AuditChainError(
            "invalid_owner_approval_payload_keys", detail=",".join(sorted(actual_keys))
        )

    command = payload["command"]
    if not isinstance(command, str) or not command.strip() or len(command) > 200:
        raise AuditChainError("invalid_payload_command")

    decision = payload["decision"]
    if decision not in ("approve", "reject"):
        raise AuditChainError("invalid_payload_decision")

    transition = payload["transition"]
    if not isinstance(transition, dict):
        raise AuditChainError("invalid_payload_transition")
    if set(transition.keys()) != {"from", "to"}:
        raise AuditChainError("invalid_payload_transition_keys")

    from_status = transition["from"]
    to_status = transition["to"]
    if from_status not in ALLOWED_STATUSES or to_status not in ALLOWED_STATUSES:
        raise AuditChainError("invalid_payload_transition_status")

    applied = payload["applied"]
    if not isinstance(applied, bool):
        raise AuditChainError("invalid_payload_applied")

    reason = payload["reason"]
    if not isinstance(reason, str) or len(reason) > 200:
        raise AuditChainError("invalid_payload_reason")

    return {
        "command": command.strip(),
        "decision": decision,
        "transition": {"from": from_status, "to": to_status},
        "applied": applied,
        "reason": reason.strip(),
    }


def _validate_execution_result_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    # Owner decision Q5-B / defect 3: the forbidden-key guard runs FIRST. While the
    # key-set equality check ran ahead of it, it always won - any payload carrying a
    # forbidden key necessarily fails exact-key-set equality - so this guard was
    # unreachable and the rejection echoed the offending key names back out.
    for forbidden in FORBIDDEN_PAYLOAD_KEYS:
        if forbidden in payload:
            raise AuditChainError("forbidden_key_in_payload", detail=forbidden)

    expected_keys = {
        "source",
        "execution_status_transition_applied",
        "execution_status_transition_reason",
        "result_kind",
    }
    actual_keys = set(payload.keys())
    if actual_keys != expected_keys:
        raise AuditChainError(
            "invalid_execution_result_payload_keys", detail=",".join(sorted(actual_keys))
        )

    source = payload["source"]
    if source not in ALLOWED_EXECUTION_SOURCES:
        raise AuditChainError("invalid_payload_source", detail=str(source))

    applied = payload["execution_status_transition_applied"]
    if not isinstance(applied, bool):
        raise AuditChainError("invalid_payload_execution_status_transition_applied")

    reason = payload["execution_status_transition_reason"]
    if not isinstance(reason, str) or len(reason) > 200:
        raise AuditChainError("invalid_payload_execution_status_transition_reason")

    result_kind = payload["result_kind"]
    if result_kind not in ALLOWED_RESULT_KINDS:
        raise AuditChainError("invalid_payload_result_kind", detail=str(result_kind))

    return {
        "source": source,
        "execution_status_transition_applied": applied,
        "execution_status_transition_reason": reason.strip(),
        "result_kind": result_kind,
    }


def validate_payload(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize kind-specific payload with strict schemas."""
    if not isinstance(payload, dict):
        raise AuditChainError("payload_must_be_dict")
    if kind == "owner_approval":
        return _validate_owner_approval_payload(payload)
    if kind == "execution_result":
        return _validate_execution_result_payload(payload)
    raise AuditChainError("unsupported_kind", detail=str(kind))


def create_audit_entry(
    *,
    seq: int,
    kind: str,
    task_id: str,
    payload: Mapping[str, Any],
    prev_hash: str | None,
    actor: str | None = None,
    ts: str | None = None,
    entry_id: str | None = None,
) -> AuditEntry:
    """Create a validated AuditEntry and compute its domain hash."""
    if not isinstance(seq, int) or seq < 1:
        raise AuditChainError("invalid_seq", detail=str(seq))

    if kind not in ALLOWED_KINDS:
        raise AuditChainError("invalid_kind", detail=str(kind))

    expected_actor = KIND_ACTOR_MAP[kind]
    actual_actor = expected_actor if actor is None else actor
    if actual_actor != expected_actor:
        raise AuditChainError(
            "actor_kind_mismatch",
            detail=f"expected_{expected_actor}_got_{actual_actor}",
        )

    if not isinstance(task_id, str) or not TASK_ID_PATTERN.fullmatch(task_id):
        raise AuditChainError("invalid_task_id", detail=str(task_id))

    validated_payload = validate_payload(kind, payload)

    if seq == 1:
        if prev_hash is not None:
            raise AuditChainError("genesis_prev_hash_must_be_null")
    else:
        if not isinstance(prev_hash, str) or not HEX_64_PATTERN.fullmatch(prev_hash):
            raise AuditChainError("non_genesis_prev_hash_must_be_64hex")

    actual_entry_id = generate_entry_id() if entry_id is None else entry_id
    if not isinstance(actual_entry_id, str) or not ENTRY_ID_PATTERN.fullmatch(actual_entry_id):
        raise AuditChainError("invalid_entry_id", detail=str(actual_entry_id))

    if ts is None:
        actual_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        if not isinstance(ts, str) or not UTC_TIMESTAMP_PATTERN.fullmatch(ts):
            raise AuditChainError("invalid_ts", detail=str(ts))
        actual_ts = ts

    entry_dict = {
        "contract_type": CONTRACT_TYPE,
        "version": VERSION,
        "seq": seq,
        "entry_id": actual_entry_id,
        "kind": kind,
        "ts": actual_ts,
        "actor": actual_actor,
        "task_id": task_id,
        "payload": validated_payload,
        "prev_hash": prev_hash,
    }

    computed_hash = compute_entry_hash(entry_dict)

    return AuditEntry(
        contract_type=CONTRACT_TYPE,
        version=VERSION,
        seq=seq,
        entry_id=actual_entry_id,
        kind=kind,
        ts=actual_ts,
        actor=actual_actor,
        task_id=task_id,
        payload=validated_payload,
        prev_hash=prev_hash,
        hash=computed_hash,
    )


def audit_entry_to_dict(entry: AuditEntry) -> dict[str, Any]:
    """Convert an AuditEntry dataclass to a plain dictionary."""
    return {
        "contract_type": entry.contract_type,
        "version": entry.version,
        "seq": entry.seq,
        "entry_id": entry.entry_id,
        "kind": entry.kind,
        "ts": entry.ts,
        "actor": entry.actor,
        "task_id": entry.task_id,
        "payload": entry.payload,
        "prev_hash": entry.prev_hash,
        "hash": entry.hash,
    }


def parse_audit_entry_json(text: str) -> AuditEntry:
    """Parse one canonical JSON audit line and verify its contract and hash."""
    if not isinstance(text, str):
        raise AuditChainError("entry_text_must_be_str")

    try:
        raw = json.loads(text)
    except Exception as exc:
        raise AuditChainError("json_parse_failed", detail=str(exc)) from exc

    if not isinstance(raw, dict):
        raise AuditChainError("audit_entry_must_be_json_object")

    required_keys = {
        "contract_type",
        "version",
        "seq",
        "entry_id",
        "kind",
        "ts",
        "actor",
        "task_id",
        "payload",
        "prev_hash",
        "hash",
    }
    if set(raw.keys()) != required_keys:
        raise AuditChainError("audit_entry_keys_mismatch")

    if raw["contract_type"] != CONTRACT_TYPE:
        raise AuditChainError("contract_type_mismatch")
    if raw["version"] != VERSION:
        raise AuditChainError("version_mismatch")

    seq = raw["seq"]
    if not isinstance(seq, int) or seq < 1:
        raise AuditChainError("invalid_seq", detail=str(seq))

    entry_id = raw["entry_id"]
    if not isinstance(entry_id, str) or not ENTRY_ID_PATTERN.fullmatch(entry_id):
        raise AuditChainError("invalid_entry_id", detail=str(entry_id))

    kind = raw["kind"]
    if kind not in ALLOWED_KINDS:
        raise AuditChainError("invalid_kind", detail=str(kind))

    actor = raw["actor"]
    if actor != KIND_ACTOR_MAP[kind]:
        raise AuditChainError("actor_kind_mismatch")

    task_id = raw["task_id"]
    if not isinstance(task_id, str) or not TASK_ID_PATTERN.fullmatch(task_id):
        raise AuditChainError("invalid_task_id", detail=str(task_id))

    ts = raw["ts"]
    if not isinstance(ts, str) or not UTC_TIMESTAMP_PATTERN.fullmatch(ts):
        raise AuditChainError("invalid_ts", detail=str(ts))

    prev_hash = raw["prev_hash"]
    if seq == 1:
        if prev_hash is not None:
            raise AuditChainError("genesis_prev_hash_must_be_null")
    else:
        if not isinstance(prev_hash, str) or not HEX_64_PATTERN.fullmatch(prev_hash):
            raise AuditChainError("non_genesis_prev_hash_must_be_64hex")

    given_hash = raw["hash"]
    if not isinstance(given_hash, str) or not HEX_64_PATTERN.fullmatch(given_hash):
        raise AuditChainError("invalid_hash_format")

    validated_payload = validate_payload(kind, raw["payload"])

    computed_hash = compute_entry_hash(raw)
    if computed_hash != given_hash:
        raise AuditChainError(
            "hash_mismatch", detail=f"expected_{computed_hash}_got_{given_hash}"
        )

    return AuditEntry(
        contract_type=CONTRACT_TYPE,
        version=VERSION,
        seq=seq,
        entry_id=entry_id,
        kind=kind,
        ts=ts,
        actor=actor,
        task_id=task_id,
        payload=validated_payload,
        prev_hash=prev_hash,
        hash=given_hash,
    )
