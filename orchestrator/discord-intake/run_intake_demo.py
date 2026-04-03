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
from task_file_writer import write_task_file


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_demo(command_text: str) -> int:
    _print_header("INPUT")
    print(command_text)

    parser_result = parse_intake(command_text).to_dict()
    _print_header("PARSER RESULT")
    _print_json(parser_result)

    if parser_result.get("error_reason"):
        _print_header("PIPELINE STOPPED")
        print("parser 단계 error로 중단되었습니다.")
        return 1

    if parser_result.get("hold_reason"):
        _print_header("PIPELINE STOPPED")
        print("parser 단계 hold로 중단되었습니다.")
        return 0

    draft_result = build_task_draft(parser_result).to_dict()
    _print_header("DRAFT RESULT")
    _print_json(draft_result)

    if draft_result.get("result_type") != "task_draft":
        _print_header("PIPELINE STOPPED")
        print("draft 단계 hold/error로 file writer를 실행하지 않았습니다.")
        return 1

    task_draft = draft_result.get("task_draft") or {}
    file_result = write_task_file(task_draft).to_dict()
    _print_header("FILE RESULT")
    _print_json(file_result)

    if file_result.get("result_type") != "created":
        _print_header("FILE WRITE FAILED")
        reason = file_result.get("reason") or "unknown_reason"
        print(f"task_file_writer 실패 원인: {reason}")
        return 1

    _print_header("DONE")
    print("end-to-end demo completed")
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 orchestrator/discord-intake/run_intake_demo.py '<slash command>'")
        print("Example: python3 orchestrator/discord-intake/run_intake_demo.py '/task report-system-improvement'")
        raise SystemExit(2)

    command_text = " ".join(sys.argv[1:]).strip()
    raise SystemExit(run_demo(command_text))


if __name__ == "__main__":
    main()
