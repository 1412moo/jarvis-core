"""Local end-to-end demo runner for Discord intake pipeline.

Flow:
1) intake_parser.parse_intake
2) task_draft_builder.build_task_draft
3) task_file_writer.write_task_file

Scope:
- local CLI only
- no Discord API, no network calls
- side effect only: task file creation via task_file_writer
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from intake_parser import parse_intake
from task_draft_builder import build_task_draft
from task_file_writer import preview_task_file_write, write_task_file


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_pipeline(command_text: str, no_write: bool = False) -> dict:
    _print_header("INPUT")
    print(command_text)

    parser_result = parse_intake(command_text).to_dict()
    _print_header("PARSER RESULT")
    _print_json(parser_result)

    if parser_result.get("error_reason"):
        _print_header("PIPELINE STOPPED")
        print("parser 단계 error로 중단되었습니다.")
        if no_write:
            print("DRY_RUN_OUTCOME: error")
        return {"exit_code": 1, "outcome": "error"}

    if parser_result.get("hold_reason"):
        _print_header("PIPELINE STOPPED")
        print("parser 단계 hold로 중단되었습니다.")
        if no_write:
            print("DRY_RUN_OUTCOME: hold")
        return {"exit_code": 0, "outcome": "hold"}

    draft_result = build_task_draft(parser_result).to_dict()
    _print_header("DRAFT RESULT")
    _print_json(draft_result)

    if draft_result.get("result_type") != "task_draft":
        _print_header("PIPELINE STOPPED")
        print("draft 단계 hold/error로 file writer를 실행하지 않았습니다.")
        if no_write:
            print("DRY_RUN_OUTCOME: hold")
        return {"exit_code": 1, "outcome": "hold"}

    task_draft = draft_result.get("task_draft") or {}
    if no_write:
        file_result = preview_task_file_write(task_draft).to_dict()
    else:
        file_result = write_task_file(task_draft).to_dict()

    _print_header("FILE RESULT")
    _print_json(file_result)

    if file_result.get("result_type") not in {"created", "would_create"}:
        _print_header("FILE WRITE BLOCKED/FAILED")
        reason = file_result.get("reason") or "unknown_reason"
        print(f"task_file_writer 실패 원인: {reason}")
        if no_write:
            outcome = "hold" if file_result.get("result_type") == "hold" else "error"
            print(f"DRY_RUN_OUTCOME: {outcome}")
            return {"exit_code": 1, "outcome": outcome}
        return {"exit_code": 1, "outcome": "error"}

    _print_header("DONE")
    if no_write:
        print("end-to-end demo completed (dry-run, no file created)")
        print("DRY_RUN_OUTCOME: would_create")
        return {"exit_code": 0, "outcome": "would_create"}

    print("end-to-end demo completed")
    return {"exit_code": 0, "outcome": "created"}


def run_demo(command_text: str, no_write: bool = False) -> int:
    return int(run_pipeline(command_text, no_write=no_write)["exit_code"])


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 orchestrator/discord-intake/run_intake_demo.py [--no-write] '<slash command>'")
        print("Example: python3 orchestrator/discord-intake/run_intake_demo.py '/task report-system-improvement'")
        print("Example: python3 orchestrator/discord-intake/run_intake_demo.py --no-write '/task report-system-improvement'")
        raise SystemExit(2)

    args = sys.argv[1:]
    no_write = False
    if "--no-write" in args:
        no_write = True
        args = [arg for arg in args if arg != "--no-write"]

    command_text = " ".join(args).strip()
    if not command_text:
        print("error: slash command input is required")
        raise SystemExit(2)
    raise SystemExit(run_demo(command_text, no_write=no_write))


if __name__ == "__main__":
    main()
