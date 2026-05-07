"""Minimal local smoke tests for Discord intake E2E dry-run pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from run_intake_demo import run_pipeline


def _run_case(name: str, command: str, expected_outcome: str, expected_exit_code: int) -> dict[str, object]:
    pipeline_result = run_pipeline(command, no_write=True)
    actual_outcome = str(pipeline_result.get("outcome"))
    actual_exit_code = int(pipeline_result.get("exit_code", 1))
    passed = actual_outcome == expected_outcome and actual_exit_code == expected_exit_code
    return {
        "name": name,
        "command": command,
        "expected_outcome": expected_outcome,
        "actual_outcome": actual_outcome,
        "expected_exit_code": expected_exit_code,
        "actual_exit_code": actual_exit_code,
        "passed": passed,
    }


def main() -> None:
    cases = [
        ("createable_task", "/task report-system-improvement", "would_create", 0),
        ("hold_non_ascii_title", "/task 보고 시스템 개선", "hold", 1),
        ("hold_risky_task", "/task production 삭제", "hold", 0),
        ("approve_parser_valid_but_draft_hold", "/approve task-0007 approve", "hold", 1),
        ("approve_parser_hold_invalid_target", "/approve wrong-target approve", "hold", 0),
        ("report_parser_valid_but_draft_hold", "/report today", "hold", 1),
        ("report_parser_hold_unrecognized_period", "/report monthly", "hold", 0),
        ("status_parser_valid_but_draft_hold", "/status task-0002", "hold", 1),
        ("status_parser_error_missing_target", "/status", "error", 1),
        ("invalid_command", "/hello something", "error", 1),
    ]

    results = [_run_case(*case) for case in cases]
    failed = [result for result in results if not result["passed"]]

    print("\n=== SMOKE TEST SUMMARY ===")
    print(json.dumps({"total": len(results), "failed": len(failed), "results": results}, ensure_ascii=False, indent=2))

    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
