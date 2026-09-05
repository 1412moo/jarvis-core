"""Audit Hash Chain package for Jarvis-Core (task-0044)."""

from audit_entry import (
    CONTRACT_TYPE,
    VERSION,
    DOMAIN_PREFIX,
    AuditChainError,
    AuditEntry,
    canonical_json,
    compute_entry_hash,
    create_audit_entry,
    generate_entry_id,
    parse_audit_entry_json,
    audit_entry_to_dict,
)
from audit_store import (
    AuditStorePaths,
    append_audit_entry,
    read_chain_head,
    resolve_audit_chain_paths,
)
from audit_verifier import verify_audit_chain

__all__ = [
    "CONTRACT_TYPE",
    "VERSION",
    "DOMAIN_PREFIX",
    "AuditChainError",
    "AuditEntry",
    "AuditStorePaths",
    "append_audit_entry",
    "canonical_json",
    "compute_entry_hash",
    "create_audit_entry",
    "generate_entry_id",
    "parse_audit_entry_json",
    "audit_entry_to_dict",
    "read_chain_head",
    "resolve_audit_chain_paths",
    "verify_audit_chain",
]
