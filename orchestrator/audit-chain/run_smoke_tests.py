"""Smoke tests for task-0044 audit hash chain implementation.

Verifies:
1. Canonical JSON encoding & domain-separated hashing
2. Kind-specific schema validation & secret rejection
3. External storage path policy (rejection of in-repo or relative paths)
4. Genesis entry (seq=1, prev_hash=None) and subsequent chaining
5. Integrity verification (seq continuity, hash matching, prev_hash chaining)
6. Tamper & corruption detection (bit flips, deleted lines, reordered lines)
7. Fail-closed write protection on corrupted chain
8. Helper functions (record_owner_approval, record_execution_result)
9. CLI verify-chain and status commands
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

# Ensure orchestrator packages can be imported
APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import audit-chain components
# Note: folder has a hyphen, so import via importlib or sys.path
import importlib.util

audit_chain_dir = REPO_ROOT / "orchestrator" / "audit-chain"
sys.path.insert(0, str(audit_chain_dir))

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
    validate_payload,
)
from audit_store import (
    AuditStorePaths,
    append_audit_entry,
    read_chain_head,
    record_execution_result,
    record_owner_approval,
    resolve_audit_chain_paths,
)
from audit_verifier import verify_audit_chain


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_error(fn: Any, expected_code: str, expected_detail: str | None = None) -> None:
    """Assert the call fails with `expected_code`.

    Owner decision Q5-B split the error surface: `code` is a fixed vocabulary term
    carrying no value, and the offending value lives in `detail`. Pass
    `expected_detail` to assert the value landed in the right layer.
    """
    try:
        fn()
    except AuditChainError as exc:
        _assert(
            expected_code in str(exc.code),
            f"Expected error code containing '{expected_code}', got '{exc.code}'",
        )
        # A code must never carry the value; that is what `detail` is for.
        _assert(
            ":" not in str(exc.code),
            f"Error code must be value-free (Q5-B), got '{exc.code}'",
        )
        if expected_detail is not None:
            _assert(
                exc.detail == expected_detail,
                f"Expected detail '{expected_detail}', got '{exc.detail}'",
            )
    else:
        raise AssertionError(f"Expected AuditChainError with code '{expected_code}' but none was raised")


def test_canonical_json_and_hashing() -> None:
    """Test deterministic canonical JSON and domain-separated hashing."""
    data = {"b": 2, "a": 1, "nested": {"z": True, "y": "hello"}}
    serialized = canonical_json(data)
    _assert(serialized == '{"a":1,"b":2,"nested":{"y":"hello","z":true}}', f"Unexpected canonical output: {serialized}")

    # Float must be rejected
    _assert_error(lambda: canonical_json({"val": 1.5}), "floats_not_allowed")

    # Domain prefix applied to hash
    entry_dict = {
        "contract_type": CONTRACT_TYPE,
        "version": VERSION,
        "seq": 1,
        "entry_id": "audit_0123456789abcdef01234567",
        "kind": "owner_approval",
        "ts": "2026-09-03T12:00:00Z",
        "actor": "owner",
        "task_id": "task-0044-audit-hash-chain",
        "payload": {
            "command": "/approve task-0044-audit-hash-chain approve",
            "decision": "approve",
            "transition": {"from": "TODO", "to": "DOING"},
            "applied": True,
            "reason": "",
        },
        "prev_hash": None,
    }
    h1 = compute_entry_hash(entry_dict)
    h2 = compute_entry_hash(entry_dict)
    _assert(h1 == h2, "Hash must be deterministic")
    _assert(len(h1) == 64, "Hash must be 64 hex characters")


def test_schema_and_payload_validation() -> None:
    """Test kind-specific payloads and secret rejection."""
    # Valid owner approval
    valid_approval = {
        "command": "/approve task-0044-test approve",
        "decision": "approve",
        "transition": {"from": "TODO", "to": "DOING"},
        "applied": True,
        "reason": "",
    }
    validated = validate_payload("owner_approval", valid_approval)
    _assert(validated["decision"] == "approve", "Validation failed on valid payload")

    # Rejection of unknown / missing fields
    _assert_error(
        lambda: validate_payload("owner_approval", {"command": "/approve", "decision": "approve"}),
        "invalid_owner_approval_payload_keys",
    )

    # Rejection of secrets / user IDs
    with_user_id = dict(valid_approval, user_id="12345678")
    _assert_error(
        lambda: validate_payload("owner_approval", with_user_id),
        "forbidden_key_in_payload",
        expected_detail="user_id",
    )
    with_discord_id = dict(valid_approval, discord_user_id="12345678")
    _assert_error(
        lambda: validate_payload("owner_approval", with_discord_id),
        "forbidden_key_in_payload",
        expected_detail="discord_user_id",
    )

    # Actor-kind mismatch
    _assert_error(
        lambda: create_audit_entry(
            seq=1,
            kind="owner_approval",
            actor="orchestrator",  # owner_approval requires actor: owner
            task_id="task-0001-bootstrap",
            payload=valid_approval,
            prev_hash=None,
        ),
        "actor_kind_mismatch",
    )


def test_path_policy_and_isolation() -> None:
    """Test 3-tier path policy and rejection of in-repo paths."""
    # Reject in-repo path
    in_repo_dir = REPO_ROOT / "some_internal_dir"
    _assert_error(
        lambda: resolve_audit_chain_paths(
            env={"JARVIS_LOCAL_STATE_DIR": str(in_repo_dir)},
            repo_root=REPO_ROOT,
        ),
        "local_state_dir_inside_repo",
    )

    # Reject relative path override
    _assert_error(
        lambda: resolve_audit_chain_paths(
            env={"JARVIS_LOCAL_STATE_DIR": "relative/path"},
            repo_root=REPO_ROOT,
        ),
        "local_state_dir_must_be_absolute",
    )

    # Resolve safe external path
    with tempfile.TemporaryDirectory(prefix="jarvis-audit-smoke-") as temp_state:
        paths = resolve_audit_chain_paths(
            env={"JARVIS_LOCAL_STATE_DIR": temp_state},
            repo_root=REPO_ROOT,
        )
        _assert(paths.source == "env_override", "Expected env_override source")
        _assert(paths.chain_file.name == "chain.jsonl", "File name must be chain.jsonl")
        _assert(paths.chain_file.parent.name == "v1", "Subpath must include v1")


def test_chaining_and_append_lifecycle() -> None:
    """Test genesis entry, sequential chaining, and verify-chain."""
    with tempfile.TemporaryDirectory(prefix="jarvis-audit-smoke-") as temp_state:
        paths = resolve_audit_chain_paths(
            env={"JARVIS_LOCAL_STATE_DIR": temp_state},
            repo_root=REPO_ROOT,
        )

        # 1. Genesis entry (seq=1, prev_hash=None)
        genesis = append_audit_entry(
            kind="owner_approval",
            task_id="task-0001-bootstrap",
            payload={
                "command": "/approve task-0001-bootstrap approve",
                "decision": "approve",
                "transition": {"from": "TODO", "to": "DOING"},
                "applied": True,
                "reason": "",
            },
            paths=paths,
        )
        _assert(genesis.seq == 1, "Genesis seq must be 1")
        _assert(genesis.prev_hash is None, "Genesis prev_hash must be None")
        _assert(genesis.actor == "owner", "Actor must be owner")

        # Verify after genesis
        res1 = verify_audit_chain(paths.chain_file)
        _assert(res1["valid"] is True, f"Chain verify failed: {res1}")
        _assert(res1["length"] == 1, f"Expected length 1, got {res1['length']}")
        _assert(res1["head_hash"] == genesis.hash, "Head hash mismatch")

        # 2. Second entry (execution_result)
        second = record_execution_result(
            task_id="task-0001-bootstrap",
            source="approve_file_write_result",
            execution_status_transition_applied=True,
            execution_status_transition_reason="",
            result_kind="success",
            paths=paths,
        )
        _assert(second.seq == 2, "Second seq must be 2")
        _assert(second.prev_hash == genesis.hash, "Second prev_hash must match genesis hash")
        _assert(second.actor == "orchestrator", "Actor must be orchestrator")

        # 3. Third entry (owner rejection)
        third = record_owner_approval(
            task_id="task-0002-sample",
            command="/approve task-0002-sample reject",
            decision="reject",
            transition_from="TODO",
            transition_to="TODO",
            applied=False,
            reason="rejected_by_owner",
            paths=paths,
        )
        _assert(third.seq == 3, "Third seq must be 3")
        _assert(third.prev_hash == second.hash, "Third prev_hash must match second hash")

        # Verify 3 entries
        res3 = verify_audit_chain(paths.chain_file)
        _assert(res3["valid"] is True, f"Chain verify failed: {res3}")
        _assert(res3["length"] == 3, f"Expected length 3, got {res3['length']}")
        _assert(res3["head_hash"] == third.hash, "Head hash mismatch")


def test_tamper_and_corruption_detection() -> None:
    """Test cryptographic tamper detection on modified files."""
    with tempfile.TemporaryDirectory(prefix="jarvis-audit-smoke-") as temp_state:
        paths = resolve_audit_chain_paths(
            env={"JARVIS_LOCAL_STATE_DIR": temp_state},
            repo_root=REPO_ROOT,
        )

        e1 = record_owner_approval(
            task_id="task-0001-bootstrap",
            command="/approve task-0001-bootstrap approve",
            decision="approve",
            transition_from="TODO",
            transition_to="DOING",
            applied=True,
            paths=paths,
        )
        e2 = record_execution_result(
            task_id="task-0001-bootstrap",
            source="approve_file_write_result",
            execution_status_transition_applied=True,
            result_kind="success",
            paths=paths,
        )
        e3 = record_owner_approval(
            task_id="task-0002-sample",
            command="/approve task-0002-sample approve",
            decision="approve",
            transition_from="TODO",
            transition_to="DOING",
            applied=True,
            paths=paths,
        )

        original_lines = paths.chain_file.read_text(encoding="utf-8").splitlines(keepends=True)

        # 1. Single byte tampering in payload
        tampered_lines = list(original_lines)
        tampered_lines[1] = tampered_lines[1].replace('"success"', '"failure"')
        paths.chain_file.write_text("".join(tampered_lines), encoding="utf-8")
        res_tamper = verify_audit_chain(paths.chain_file)
        _assert(res_tamper["valid"] is False, "Tampered payload was not detected")
        _assert(res_tamper["reason"] == "hash_mismatch", f"Unexpected reason: {res_tamper}")
        _assert(res_tamper["first_bad_seq"] == 2, f"Unexpected bad seq: {res_tamper}")

        # 2. Deleting middle line (broken sequence)
        deleted_lines = [original_lines[0], original_lines[2]]
        paths.chain_file.write_text("".join(deleted_lines), encoding="utf-8")
        res_delete = verify_audit_chain(paths.chain_file)
        _assert(res_delete["valid"] is False, "Deleted line was not detected")
        _assert(res_delete["reason"] == "seq_not_contiguous", f"Unexpected reason: {res_delete}")
        _assert(res_delete["first_bad_seq"] == 3, f"Unexpected bad seq: {res_delete}")

        # 3. Reordering lines
        reordered_lines = [original_lines[1], original_lines[0], original_lines[2]]
        paths.chain_file.write_text("".join(reordered_lines), encoding="utf-8")
        res_reorder = verify_audit_chain(paths.chain_file)
        _assert(res_reorder["valid"] is False, "Reordered lines were not detected")
        _assert(res_reorder["first_bad_seq"] == 2, f"Unexpected bad seq: {res_reorder}")

        # 4. Fail-closed: cannot append to corrupted chain
        _assert_error(
            lambda: record_owner_approval(
                task_id="task-0003-sample",
                command="/approve task-0003-sample approve",
                decision="approve",
                transition_from="TODO",
                transition_to="DOING",
                applied=True,
                paths=paths,
            ),
            "audit_chain_corrupt",
        )


def test_cli_interface() -> None:
    """Test CLI verify-chain and status execution via subprocess."""
    with tempfile.TemporaryDirectory(prefix="jarvis-audit-smoke-") as temp_state:
        paths = resolve_audit_chain_paths(
            env={"JARVIS_LOCAL_STATE_DIR": temp_state},
            repo_root=REPO_ROOT,
        )

        record_owner_approval(
            task_id="task-0001-bootstrap",
            command="/approve task-0001-bootstrap approve",
            decision="approve",
            transition_from="TODO",
            transition_to="DOING",
            applied=True,
            paths=paths,
        )

        cli_script = audit_chain_dir / "cli.py"

        # Verify CLI verify-chain
        cmd_verify = [
            sys.executable,
            "-B",
            str(cli_script),
            "verify-chain",
            "--chain-file",
            str(paths.chain_file),
        ]
        cp_verify = subprocess.run(cmd_verify, capture_output=True, text=True, check=False)
        _assert(cp_verify.returncode == 0, f"CLI verify-chain failed: {cp_verify.stderr}")
        parsed_verify = json.loads(cp_verify.stdout)
        _assert(parsed_verify["valid"] is True, "CLI reported invalid chain")
        _assert(parsed_verify["length"] == 1, "CLI length mismatch")

        # Verify CLI status
        cmd_status = [
            sys.executable,
            "-B",
            str(cli_script),
            "status",
            "--chain-file",
            str(paths.chain_file),
        ]
        cp_status = subprocess.run(cmd_status, capture_output=True, text=True, check=False)
        _assert(cp_status.returncode == 0, f"CLI status failed: {cp_status.stderr}")
        parsed_status = json.loads(cp_status.stdout)
        _assert(parsed_status["valid"] is True, "CLI status reported invalid")
        _assert(parsed_status["exists"] is True, "CLI status reported non-existing")


def main() -> int:
    tests = [
        test_canonical_json_and_hashing,
        test_schema_and_payload_validation,
        test_path_policy_and_isolation,
        test_chaining_and_append_lifecycle,
        test_tamper_and_corruption_detection,
        test_cli_interface,
    ]
    print("Running task-0044 audit hash chain smoke tests...")
    for test in tests:
        test()
        print(f"  ok   {test.__name__}")
    print(f"\n{len(tests)} passed, 0 failed")
    print("Audit Hash Chain smoke tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
