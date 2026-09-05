"""Command-line interface for the audit hash chain.

Usage:
  python -B orchestrator/audit-chain/cli.py verify-chain [--chain-file <path>]
  python -B orchestrator/audit-chain/cli.py status [--chain-file <path>]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# This directory name contains a hyphen, so it can never be a Python package.
# Entrypoints put their own directory on sys.path and use absolute imports, the
# same convention orchestrator/discord-intake and discord-nl-intent follow.
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from audit_store import resolve_audit_chain_paths
from audit_verifier import verify_audit_chain


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit hash chain inspection CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify-chain", help="Verify cryptographic integrity of the chain.")
    verify_parser.add_argument(
        "--chain-file",
        type=str,
        default="",
        help="Optional explicit path to the audit chain file.",
    )

    status_parser = subparsers.add_parser("status", help="Show audit chain location and current head.")
    status_parser.add_argument(
        "--chain-file",
        type=str,
        default="",
        help="Optional explicit path to the audit chain file.",
    )

    args = parser.parse_args(argv)

    if args.chain_file:
        chain_path = Path(args.chain_file).resolve()
    else:
        paths = resolve_audit_chain_paths()
        chain_path = paths.chain_file

    if args.command == "verify-chain":
        result = verify_audit_chain(chain_path)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        print(output)
        return 0 if result.get("valid") else 1

    if args.command == "status":
        result = verify_audit_chain(chain_path)
        # Owner decision Q6: the chain has no length cap, because it cannot be
        # truncated and a fail-closed cap would let a full audit log block approvals.
        # Growth is made observable here instead, so the Owner can act on a number
        # rather than discover the size by accident.
        exists = chain_path.exists()
        try:
            size_bytes = chain_path.stat().st_size if exists else 0
        except OSError:
            size_bytes = None
        status_info = {
            "chain_file": str(chain_path),
            "exists": exists,
            "valid": result.get("valid", False),
            "length": result.get("length", 0),
            "size_bytes": size_bytes,
            "head_hash": result.get("head_hash"),
            "retention": "manual_delete_only",
        }
        print(json.dumps(status_info, ensure_ascii=False, indent=2))
        return 0 if result.get("valid") else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
