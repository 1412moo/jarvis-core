"""Audit chain integrity verifier.

Implements task-0044 section 8 verification checks:
1. seq is 1-indexed and contiguous without gaps or repeats
2. Each entry hash matches fresh recomputation
3. Each prev_hash matches previous entry hash (genesis must be null)
4. Strict fail-closed return shape (Owner decision Q5-B):
   - Success: {"valid": True, "length": N, "head_hash": "<64hex>"}
   - Failure: {"valid": False, "reason": "<fixed code>", "first_bad_seq": N,
               "detail": "<investigation string>" | None}

``reason`` is drawn from the fixed AuditChainError vocabulary and never carries
a value. Everything a person needs in order to investigate - the offending
sequence number, a hash pair, an OS error - goes in ``detail``, which callers
may log locally but must not surface as the reason.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from audit_entry import (
    AuditChainError,
    audit_entry_to_dict,
    compute_entry_hash,
    parse_audit_entry_json,
)


def _invalid(reason: str, first_bad_seq: int, detail: str | None = None) -> dict[str, Any]:
    """Build the one failure shape, so every exit point matches design section 8."""
    return {
        "valid": False,
        "reason": reason,
        "first_bad_seq": first_bad_seq,
        "detail": detail,
    }


def verify_audit_chain(chain_path: Path | str) -> dict[str, Any]:
    """Verify the cryptographic integrity of one audit hash chain file."""
    path = Path(chain_path)
    if not path.exists():
        return {"valid": True, "length": 0, "head_hash": None}

    try:
        size = path.stat().st_size
    except OSError as exc:
        return _invalid("chain_file_stat_failed", 0, str(exc))

    if size == 0:
        return {"valid": True, "length": 0, "head_hash": None}

    expected_seq = 1
    expected_prev_hash: str | None = None
    last_valid_hash: str | None = None

    try:
        with path.open("r", encoding="utf-8", errors="strict") as stream:
            for raw_line in stream:
                # Ensure each line ends with a standard newline
                if not raw_line.endswith("\n"):
                    return _invalid("missing_trailing_newline", expected_seq)

                line = raw_line.rstrip("\r\n")
                if not line:
                    return _invalid("unexpected_blank_line", expected_seq)

                try:
                    entry = parse_audit_entry_json(line)
                except AuditChainError as exc:
                    # Owner decision Q5-B / defect 4: surface the parser's own stable
                    # code as the reason rather than wrapping it. parse_audit_entry_json
                    # already recomputes the hash, so a tampered entry is caught here -
                    # and it must still report "hash_mismatch", the code design section 8
                    # fixes, not a wrapped variant no caller can match on.
                    return _invalid(exc.code, expected_seq, exc.detail)
                except Exception as exc:  # noqa: BLE001 - fail closed on anything unexpected
                    return _invalid("entry_syntax_error", expected_seq, str(exc))

                # 1. seq contiguous check
                if entry.seq != expected_seq:
                    return _invalid("seq_not_contiguous", entry.seq, f"expected_{expected_seq}")

                # 2. prev_hash check
                if entry.prev_hash != expected_prev_hash:
                    return _invalid("prev_hash_mismatch", entry.seq)

                # 3. hash recomputation check. parse_audit_entry_json already performed
                # this, so reaching a mismatch here means the two disagree - keep it as
                # a fail-closed backstop rather than trusting one of them.
                recomputed_hash = compute_entry_hash(audit_entry_to_dict(entry))
                if recomputed_hash != entry.hash:
                    return _invalid("hash_mismatch", entry.seq, "recomputed_hash_differs")

                expected_seq += 1
                expected_prev_hash = entry.hash
                last_valid_hash = entry.hash

    except UnicodeDecodeError as exc:
        return _invalid("unicode_decode_error", expected_seq, str(exc))
    except OSError as exc:
        return _invalid("chain_file_read_error", expected_seq, str(exc))

    return {
        "valid": True,
        "length": expected_seq - 1,
        "head_hash": last_valid_hash,
    }
