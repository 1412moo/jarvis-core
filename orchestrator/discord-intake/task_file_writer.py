"""Minimal local task file writer from task draft object.

Scope (MVP):
- accept task draft object
- scan existing task files under memory/tasks
- allocate next task number and slug
- create one markdown task file from template-compatible format

Out of scope:
- Discord/GitHub integration
- DB/network calls
- status automation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import re

TASK_FILE_PATTERN = re.compile(r"^task-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
DEFAULT_TASKS_DIR = Path("memory/tasks")
DEFAULT_STATUS = "TODO"


@dataclass
class TaskFileWriteResult:
    result_type: str  # "created" | "hold" | "error"
    file_path: str | None = None
    task_id: str | None = None
    summary: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_type": self.result_type,
            "file_path": self.file_path,
            "task_id": self.task_id,
            "summary": self.summary,
            "reason": self.reason,
        }


def _normalize_spaces(text: str) -> str:
    return " ".join(str(text).strip().split())


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _slugify(title: str) -> str:
    lowered = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    slug = slug.strip("-")
    return slug


def _existing_task_numbers(tasks_dir: Path) -> list[int]:
    numbers: list[int] = []
    for path in tasks_dir.iterdir():
        if not path.is_file():
            continue
        matched = TASK_FILE_PATTERN.match(path.name)
        if not matched:
            continue
        numbers.append(int(matched.group(1)))
    return sorted(numbers)


def _render_task_markdown(
    task_id: str,
    title: str,
    repo: str,
    summary: str,
    created_at: str,
    updated_at: str,
    source_command: str | None,
) -> str:
    lines = [
        f"# {task_id}",
        "",
        f"- id: `{task_id}`",
        f"- title: `{title}`",
        f"- status: `{DEFAULT_STATUS}`",
        f"- repo: `{repo}`",
        f"- created_at: `{created_at}`",
        f"- updated_at: `{updated_at}`",
        f"- summary: `{summary}`",
    ]
    if source_command:
        lines.append(f"- source_command: `{source_command}`")
    lines.append("")
    return "\n".join(lines)


def _validate_draft(task_draft: dict[str, Any]) -> tuple[bool, str | None]:
    title = _normalize_spaces(task_draft.get("title", ""))
    repo = _normalize_spaces(task_draft.get("repo", ""))
    summary = _normalize_spaces(task_draft.get("summary", ""))
    status = _normalize_spaces(task_draft.get("status", ""))

    if not title:
        return False, "missing_required_field:title"
    if not repo:
        return False, "missing_required_field:repo"
    if not summary:
        return False, "missing_required_field:summary"
    if status and status != DEFAULT_STATUS:
        return False, "invalid_status_for_creation:only_TODO_allowed"

    slug = _slugify(title)
    if not slug:
        return False, "invalid_title_for_slug"

    return True, None


def write_task_file(task_draft: dict[str, Any], tasks_dir: Path = DEFAULT_TASKS_DIR) -> TaskFileWriteResult:
    """Create one task markdown file from task draft object.

    The function never overwrites an existing file.
    """
    is_valid, reason = _validate_draft(task_draft)
    if not is_valid:
        return TaskFileWriteResult(result_type="hold", reason=reason)

    if not tasks_dir.exists() or not tasks_dir.is_dir():
        return TaskFileWriteResult(result_type="error", reason="tasks_dir_not_found")

    title = _normalize_spaces(task_draft["title"])
    repo = _normalize_spaces(task_draft["repo"])
    summary = _normalize_spaces(task_draft["summary"])
    source_command = _normalize_spaces(task_draft.get("source_command", "")) or None

    slug = _slugify(title)
    existing_numbers = _existing_task_numbers(tasks_dir)
    next_number = (max(existing_numbers) + 1) if existing_numbers else 1

    # Safe retry for rare filename conflicts (concurrent write, manual file creation, etc.)
    max_retries = 10
    for _ in range(max_retries):
        task_id = f"task-{next_number:04d}-{slug}"
        file_name = f"{task_id}.md"
        target_path = tasks_dir / file_name

        if target_path.exists():
            next_number += 1
            continue

        now_utc = _utc_now()
        content = _render_task_markdown(
            task_id=task_id,
            title=title,
            repo=repo,
            summary=summary,
            created_at=now_utc,
            updated_at=now_utc,
            source_command=source_command,
        )

        try:
            with target_path.open("x", encoding="utf-8") as fp:
                fp.write(content)
        except FileExistsError:
            next_number += 1
            continue

        return TaskFileWriteResult(
            result_type="created",
            file_path=str(target_path),
            task_id=task_id,
            summary="task file created",
        )

    return TaskFileWriteResult(result_type="error", reason="failed_to_allocate_task_number")


def main() -> None:
    # Local runnable examples (1 invalid input included)
    samples = [
        {
            "title": "보고 시스템 개선",
            "status": "TODO",
            "repo": "jarvis-core",
            "summary": "보고 체계 문서 구조를 개선하는 task 파일을 생성한다.",
            "source_command": "/task 보고 시스템 개선",
        },
        {
            "title": "parser output 검증 규칙 보강",
            "status": "TODO",
            "repo": "jarvis-core",
            "summary": "파서 결과의 누락/형식 오류 검증 규칙을 명확히 한다.",
            "source_command": "/task parser output 검증 규칙 보강",
        },
        {
            "title": "   ",
            "status": "TODO",
            "repo": "jarvis-core",
            "summary": "잘못된 입력 예시",
        },
    ]

    for draft in samples:
        result = write_task_file(draft)
        print(json.dumps({"input": draft, "output": result.to_dict()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
