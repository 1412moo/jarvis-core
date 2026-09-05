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



def _metadata_boundary_cases() -> list[dict[str, object]]:
    """task-0054: the metadata header boundary, with counter-examples.

    The boundary moved; no field-level rule did. So these assert both directions -
    a body bullet must be ignored, and a malformed field inside the header must
    still fail exactly as it did before.
    """

    from task_file_writer import _transition_metadata

    header_lines = [
        "# task-0001-boundary",
        "",
        "- id: `task-0001-boundary`",
        "- title: `boundary check`",
        "- status: `TODO`",
        "- repo: `jarvis-core`",
        "- created_at: `2026-01-01 00:00 UTC`",
        "- updated_at: `2026-01-01 00:00 UTC`",
        "- summary: `boundary check summary`",
    ]
    header = "\n".join(header_lines)
    tab = chr(9)

    cases: list[tuple[str, str, object]] = [
        ("header_only", header + "\n", None),
        (
            "body_top_level_bullet_ignored",
            header + "\n\n## 본문\n\n- 본문 최상위 bullet\n- 또 하나의 bullet\n",
            None,
        ),
        (
            "body_nested_bullet_ignored",
            header + "\n\n## 본문\n\n- 최상위\n  - 중첩 bullet\n    - 더 깊은 중첩\n",
            None,
        ),
        (
            "body_bullet_without_heading_ignored",
            header + "\n\n- 빈 줄 뒤에 오는 본문 bullet\n",
            None,
        ),
        (
            "indented_note_under_field_ignored",
            "\n".join(
                [
                    "# task-0001-boundary",
                    "",
                    "- id: `task-0001-boundary`",
                    "  - 규칙: 이 줄은 필드 설명이지 metadata 가 아니다.",
                    "- title: `boundary check`",
                    "  - 규칙: 설명 줄.",
                    "- status: `TODO`",
                    "- repo: `jarvis-core`",
                    "- created_at: `2026-01-01 00:00 UTC`",
                    "- updated_at: `2026-01-01 00:00 UTC`",
                    "- summary: `boundary check summary`",
                    "",
                ]
            ),
            None,
        ),
        # --- counter-examples: inside the header nothing was relaxed -------------
        (
            "malformed_field_inside_header_still_fails",
            "\n".join(
                [
                    "# task-0001-boundary",
                    "",
                    "- id: `task-0001-boundary`",
                    "- title: 백틱이 없는 잘못된 줄",
                    "- status: `TODO`",
                    "- repo: `jarvis-core`",
                    "- created_at: `2026-01-01 00:00 UTC`",
                    "- updated_at: `2026-01-01 00:00 UTC`",
                    "- summary: `boundary check summary`",
                    "",
                ]
            ),
            "task_file_invalid_metadata",
        ),
        (
            "unsupported_field_inside_header_still_fails",
            header + "\n- mode: `real`\n",
            "task_file_unsupported_metadata",
        ),
        (
            "too_long_summary_inside_header_still_fails",
            header.replace(
                "- summary: `boundary check summary`",
                "- summary: `" + ("x" * 501) + "`",
            )
            + "\n",
            "task_file_field_too_long",
        ),
        (
            "duplicate_field_inside_header_still_fails",
            header + "\n- status: `DOING`\n",
            "task_file_duplicate_metadata",
        ),
        (
            "missing_required_field_still_fails",
            "\n".join(line for line in header_lines if not line.startswith("- summary:")) + "\n",
            "task_file_missing_metadata",
        ),
        (
            "control_character_inside_header_still_fails",
            header.replace(
                "- summary: `boundary check summary`",
                "- summary: `tab" + tab + "here`",
            )
            + "\n",
            "task_file_invalid_text",
        ),
        (
            "empty_optional_text_inside_header_still_fails",
            header + "\n- execution_summary: ``\n",
            "task_file_invalid_text",
        ),
    ]

    results: list[dict[str, object]] = []
    for name, text, expected in cases:
        metadata, error = _transition_metadata(text.encode("utf-8"), "task-0001-boundary.md")
        actual = None if metadata is not None else error
        results.append(
            {
                "name": "metadata_boundary:" + name,
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )
    return results


def _repository_task_validation_cases() -> list[dict[str, object]]:
    """task-0054: validate the real records under memory/tasks, not a fixture.

    task-0052's regression hid behind minimal fixtures with no document body, so
    this checks the files the approval path actually writes to. Records whose
    summary quotes a path or hash in backticks stay failing on purpose - that is a
    content contract violation left to a separate decision, not a boundary bug.
    """

    from pathlib import Path

    from task_file_writer import _transition_metadata

    # These records quote a path or a commit hash inside their summary, and the
    # value delimiter is the backtick, so the value cannot contain one. That is a
    # content contract violation, not a boundary bug, and task-0054 deliberately
    # leaves it to a separate decision (design document section 3.2). Listing them
    # explicitly keeps this a real contract test: any OTHER record that starts
    # failing - including a newly written one - fails this suite.
    KNOWN_BACKTICK_IN_SUMMARY = {
        "task-0037-gemini-cli-local-dev-environment.md",
        "task-0039-buzz-integration-phase1-architecture-borrow.md",
        "task-0041-task-model-append-only-event-log.md",
        "task-0043-no-secrets-enforcement.md",
        "task-0045-acp-feasibility-research.md",
        "task-0048-buzz-bridge-phase2-slice1.md",
        "task-0049-buzz-bridge-p2-2-p2-3-completion.md",
        "task-0050-buzz-bridge-p2-4-p2-5-p2-6-completion.md",
    }

    # task-template.md is a template, not a task: its id, timestamps and filename are
    # placeholders (task-####-slug, YYYY-MM-DD), so it can never satisfy the id,
    # path and timestamp checks. task-0054 fixed the reason that mattered - its
    # indented "- 규칙:" notes are no longer read as metadata - which the dedicated
    # boundary case above pins. Making the placeholders themselves valid would mean
    # either rewriting the template or weakening those checks; neither is in scope.
    TEMPLATE_WITH_PLACEHOLDERS = {"task-template.md"}

    tasks_dir = Path(__file__).resolve().parents[2] / "memory" / "tasks"
    results: list[dict[str, object]] = []
    for path in sorted(tasks_dir.glob("task-*.md")):
        if path.name in TEMPLATE_WITH_PLACEHOLDERS:
            continue
        metadata, error = _transition_metadata(path.read_bytes(), path.name)
        expected_known_failure = path.name in KNOWN_BACKTICK_IN_SUMMARY
        results.append(
            {
                "name": "repo_task_validation:" + path.name,
                "error": error,
                "passed": (metadata is not None) != expected_known_failure
                if metadata is None or not expected_known_failure
                else False,
            }
        )
    return results


def main() -> None:
    cases = [
        ("createable_task", "/task report-system-improvement", "would_create", 0),
        ("task_parser_error_missing_request", "/task", "error", 1),
        ("createable_korean_title", "/task 보고 시스템 개선", "would_create", 0),
        ("hold_risky_task", "/task production 삭제", "hold", 0),
        ("approve_parser_valid_but_draft_hold", "/approve task-0007-sample approve", "hold", 1),
        ("approve_parser_hold_invalid_target", "/approve wrong-target approve", "hold", 0),
        ("report_parser_valid_but_draft_hold", "/report today", "hold", 1),
        ("report_parser_hold_unrecognized_period", "/report monthly", "hold", 0),
        ("status_parser_valid_but_draft_hold", "/status task-0002", "hold", 1),
        ("status_parser_error_missing_target", "/status", "error", 1),
        ("invalid_command", "/hello something", "error", 1),
    ]

    results = [_run_case(*case) for case in cases]
    results.extend(_metadata_boundary_cases())
    results.extend(_repository_task_validation_cases())
    failed = [result for result in results if not result["passed"]]

    print("\n=== SMOKE TEST SUMMARY ===")
    print(json.dumps({"total": len(results), "failed": len(failed), "results": results}, ensure_ascii=False, indent=2))

    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
