"""Smoke tests for Jarvis Console v0.1."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
from http.client import HTTPConnection
from io import StringIO
import inspect
import json
from http import HTTPStatus
from pathlib import Path
import socket
import subprocess
import shutil
from tempfile import TemporaryDirectory
import threading
from typing import Any

import run_web_app
import codex_review
import render_owner_decision
from owner_decision import (
    AUTHORITY_BOUNDARY,
    CONTRACT_TYPE,
    MAX_JSON_BYTES,
    PROJECT_ID,
    RESPONSE_TEMPLATE,
    VERSION as OWNER_DECISION_VERSION,
    OwnerDecisionError,
    normalize_owner_decision,
    owner_decision_to_dict,
    parse_owner_decision_json,
    render_owner_decision_markdown,
    serialize_owner_decision,
)
from owner_decision_data import (
    OWNER_DECISION_LOCKS,
    OwnerDecisionDataError,
    build_owner_decision_from_snapshot,
)
from project_control_registry import (
    MAX_PROJECTS,
    REGISTRY_TYPE,
    REGISTRY_VERSION,
    ProjectRegistryError,
    evaluate_project_registry,
    normalize_project_registry,
)
from recent_milestone_evidence import (
    CONTRACT_TYPE as RECENT_MILESTONE_CONTRACT_TYPE,
    MAX_COMMITS as RECENT_MILESTONE_MAX_COMMITS,
    MAX_FILES_PER_COMMIT,
    MAX_RAW_LOG_BYTES,
    RECORD_SEPARATOR,
    FIELD_SEPARATOR,
    VERSION as RECENT_MILESTONE_VERSION,
    RecentMilestoneEvidenceError,
    parse_recent_milestone_log,
    recent_milestone_evidence_to_dict,
    serialize_recent_milestone_evidence,
)
from hermes_manager_pilot.approval_binding import build_scope_approval_binding
from hermes_manager_pilot.director_reporting import (
    AUTHORITY_BOUNDARY as DIRECTOR_AUTHORITY_BOUNDARY,
    CONTRACT_TYPE as DIRECTOR_CONTRACT_TYPE,
    VERSION as DIRECTOR_VERSION,
    normalize_director_report,
)
from hermes_manager_pilot.manager_reporting import (
    MANAGER_CONTRACT_TYPE,
    VERSION as MANAGER_REPORTING_VERSION,
    normalize_manager_report,
)
from hermes_manager_pilot.prompt_queue import (
    REQUIRED_FORBIDDEN_ACTIONS,
    normalize_prompt_queue,
)
from hermes_manager_pilot.schemas import ValidationError


def _test_tasks_reports_registry_copy() -> None:
    baseline_commit = "064f82bf4806198a4e904e58b85c3c87a2ca8123"
    registry_path = Path(run_web_app.REGISTRY_PATH)
    relative_registry_path = registry_path.relative_to(
        run_web_app.REPO_ROOT
    ).as_posix()
    baseline_result = subprocess.run(
        ("git", "show", f"{baseline_commit}:{relative_registry_path}"),
        cwd=run_web_app.REPO_ROOT,
        check=False,
        capture_output=True,
    )
    assert baseline_result.returncode == 0, baseline_result.stderr.decode(
        "utf-8",
        errors="replace",
    )
    baseline_raw = baseline_result.stdout
    current_raw = registry_path.read_bytes()
    baseline_registry = json.loads(baseline_raw.decode("utf-8"))
    current_registry = json.loads(current_raw.decode("utf-8"))

    baseline_index = next(
        index
        for index, skill in enumerate(baseline_registry["skills"])
        if skill["skill_id"] == "tasks_reports"
    )
    current_index = next(
        index
        for index, skill in enumerate(current_registry["skills"])
        if skill["skill_id"] == "tasks_reports"
    )
    assert current_index == baseline_index
    baseline_research_index = next(
        index
        for index, skill in enumerate(baseline_registry["skills"])
        if skill["skill_id"] == "research_council"
    )
    current_research_index = next(
        index
        for index, skill in enumerate(current_registry["skills"])
        if skill["skill_id"] == "research_council"
    )
    assert current_research_index == baseline_research_index

    replacements = (
        (
            "Review the refined input.",
            (
                "In Jarvis Console, review a successful Evaluate Idea "
                "recommendation before using Preview as Local Task."
            ),
            (
                "skills",
                current_research_index,
                "action_guide",
                4,
            ),
        ),
        (
            "Run the report.",
            (
                "Review the local TODO preview, then explicitly Confirm Create "
                "Local Task if the handoff is correct."
            ),
            (
                "skills",
                current_research_index,
                "action_guide",
                5,
            ),
        ),
        (
            "Jarvis Console does not run Research Council automatically.",
            (
                "Jarvis Console does not run Research Council automatically; "
                "Evaluate Idea and Preview as Local Task are write-free, and "
                "only explicit Confirm Create Local Task writes one local TODO."
            ),
            (
                "skills",
                current_research_index,
                "safety_notes",
                1,
            ),
        ),
        (
            "Treat this as a future surface; v0.1 does not mutate tasks or reports.",
            (
                "Review bounded local Task details; all Task writes require "
                "Preview and explicit Confirm."
            ),
            ("skills", current_index, "primary_next_action_description"),
        ),
        (
            "Do not mutate tasks in v0.1.",
            (
                "Only after Preview and explicit Confirm may Start / Complete "
                "change status and updated_at for TODO → DOING or DOING → DONE."
            ),
            ("skills", current_index, "action_guide", 1),
        ),
        (
            "Use this as a future placeholder.",
            (
                "Record Completion Evidence may append one evidence value and "
                "update only updated_at for an eligible DOING Task after "
                "Preview and explicit Confirm; it does not validate evidence, "
                "change status, complete, or execute the Task."
            ),
            ("skills", current_index, "action_guide", 2),
        ),
        (
            "v0.1 does not mutate tasks or write reports from this console.",
            (
                "No general Task content editing, Task work execution, AI "
                "judgment, automatic execution, or generic status editing."
            ),
            ("skills", current_index, "safety_notes", 0),
        ),
        (
            "No task mutation.",
            "No Task work execution or report persistence from this console.",
            ("skills", current_index, "non_goals", 0),
        ),
    )

    def string_values(
        value: Any,
        path: tuple[Any, ...] = (),
    ) -> dict[tuple[Any, ...], str]:
        if isinstance(value, str):
            return {path: value}
        collected: dict[tuple[Any, ...], str] = {}
        if isinstance(value, list):
            for index, item in enumerate(value):
                collected.update(string_values(item, (*path, index)))
        elif isinstance(value, dict):
            for key, item in value.items():
                collected.update(string_values(item, (*path, key)))
        return collected

    baseline_strings = string_values(baseline_registry)
    current_strings = string_values(current_registry)
    assert baseline_strings.keys() == current_strings.keys()
    approved_paths = {path for _old, _new, path in replacements}
    for path, baseline_value in baseline_strings.items():
        if path not in approved_paths:
            assert current_strings[path].encode("utf-8") == baseline_value.encode(
                "utf-8"
            )
    for obsolete, replacement, path in replacements:
        assert baseline_strings[path] == obsolete
        assert current_strings[path] == replacement
        assert obsolete.encode("utf-8") not in current_raw
        assert current_raw.count(replacement.encode("utf-8")) == 1

    restored_raw = current_raw
    for obsolete, replacement, _path in replacements:
        restored_raw = restored_raw.replace(
            replacement.encode("utf-8"),
            obsolete.encode("utf-8"),
        )
    assert restored_raw == baseline_raw

    tasks_reports = current_registry["skills"][current_index]
    assert tasks_reports["status"] == "planned"
    assert "all Task writes require" in tasks_reports[
        "primary_next_action_description"
    ]
    transition_copy = tasks_reports["action_guide"][1]
    assert "Preview and explicit Confirm" in transition_copy
    assert "TODO → DOING" in transition_copy
    assert "DOING → DONE" in transition_copy
    assert "status and updated_at" in transition_copy
    evidence_copy = tasks_reports["action_guide"][2]
    for exact_evidence_boundary in (
        "Record Completion Evidence",
        "append one evidence value",
        "update only updated_at",
        "eligible DOING Task",
        "Preview and explicit Confirm",
        "does not validate evidence",
        "change status",
        "complete",
        "execute the Task",
    ):
        assert exact_evidence_boundary in evidence_copy
    prohibition_copy = tasks_reports["safety_notes"][0]
    for exact_prohibition in (
        "No general Task content editing",
        "Task work execution",
        "AI judgment",
        "automatic execution",
        "generic status editing",
    ):
        assert exact_prohibition in prohibition_copy
    assert tasks_reports["non_goals"] == [
        "No Task work execution or report persistence from this console.",
        "No report persistence from this console.",
    ]


def _run_fixture_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"fixture git command failed: git {' '.join(args)}: {completed.stderr}"
        )
    return completed.stdout.strip()


def _create_codex_review_fixture(temp_dir: str) -> tuple[Path, dict[str, Any], str]:
    repo = Path(temp_dir).resolve()
    _run_fixture_git(repo, "init", "-b", "main")
    _run_fixture_git(repo, "config", "user.email", "jarvis-console@example.invalid")
    _run_fixture_git(repo, "config", "user.name", "Jarvis Console Smoke")
    _run_fixture_git(repo, "config", "core.autocrlf", "false")
    source_dir = repo / "src"
    source_dir.mkdir()
    target = source_dir / "review.txt"
    target.write_text("baseline\n", encoding="utf-8")
    _run_fixture_git(repo, "add", "src/review.txt")
    _run_fixture_git(repo, "commit", "-m", "baseline")
    head = _run_fixture_git(repo, "rev-parse", "HEAD")
    target.write_text("changed Codex work\n", encoding="utf-8")
    (repo / "jarvis.bat").write_text("protected boundary\n", encoding="utf-8")

    queue_data: dict[str, Any] = {
        "queue_type": "hermes_prompt_queue",
        "version": "0.1B-2",
        "projects": [
            {
                "project_id": "jarvis-review-fixture",
                "display_name": "Jarvis Review Fixture",
                "repo_path": str(repo),
                "expected_branch": "main",
                "expected_head": head,
                "protected_paths": ["jarvis.bat"],
                "expected_untracked": ["jarvis.bat"],
                "forbidden_actions": sorted(REQUIRED_FORBIDDEN_ACTIONS),
                "validation_commands": ["git diff --check"],
            }
        ],
        "items": [
            {
                "item_id": "review-001",
                "project_id": "jarvis-review-fixture",
                "current_goal": "Show one safe Codex work package.",
                "current_task": "Review the bounded local change without action.",
                "result_type": "review",
                "target_files": ["src/review.txt"],
                "observed_branch": "main",
                "observed_head": head,
                "observed_git_status": [],
                "scope_approved": False,
                "review_passed": False,
                "commit_approved": False,
                "scope_approval_digest": "",
                "change_evidence_digest": "",
                "review_approval_digest": "",
                "commit_approval_digest": "",
                "commit_message": "",
                "last_prompt_summary": "Implement the approved read-only slice.",
                "last_result_summary": "Local implementation is ready for review.",
            }
        ],
    }
    normalized = normalize_prompt_queue(queue_data)
    scope_binding = build_scope_approval_binding(
        normalized.projects[0],
        replace(normalized.items[0], result_type="implementation"),
    )
    queue_data["items"][0]["scope_approved"] = True
    queue_data["items"][0]["scope_approval_digest"] = scope_binding.digest
    return repo, {"queue": queue_data, "item_id": "review-001"}, head


def _test_codex_review_vertical_slice() -> None:
    with TemporaryDirectory(prefix="jarvis-codex-review-") as temp_dir:
        repo, payload, head = _create_codex_review_fixture(temp_dir)
        first_status, first = codex_review.build_codex_review_preview(payload, repo)
        second_status, second = codex_review.build_codex_review_preview(payload, repo)
        assert first_status == HTTPStatus.OK
        assert second_status == HTTPStatus.OK
        assert first == second
        assert first["ok"] is True
        assert first["mode"] == "read-only"
        assert first["write_free"] is True
        assert first["no_persistence"] is True
        assert first["project"] == {
            "project_id": "jarvis-review-fixture",
            "display_name": "Jarvis Review Fixture",
            "repo_name": repo.name,
            "branch": "main",
            "head": head,
        }
        assert first["review"]["item_id"] == "review-001"
        assert first["review"]["files_touched"] == ["src/review.txt"]
        assert first["review"]["target_files"] == ["src/review.txt"]
        assert first["review"]["validation_commands"] == ["git diff --check"]
        assert first["review"]["next_action"] == "REVIEW_REQUEST"
        assert first["safety"] == {
            "fresh_local_evidence": True,
            "read_only": True,
            "human_approval_required": True,
            "human_approval_granted": False,
            "commit_allowed": False,
            "push_allowed": False,
            "prompt_rendered": False,
            "command_executed": False,
            "external_call": False,
        }
        serialized = json.dumps(first, ensure_ascii=False, sort_keys=True)
        assert "changed Codex work" not in serialized
        assert str(repo) not in serialized
        assert "scope_approval_digest" not in serialized
        assert "change_evidence_digest" not in serialized
        assert "commit_message" not in serialized

        original_collect = codex_review.collect_review_evidence_bundle

        def forbidden_collect(*args: object, **kwargs: object) -> object:
            raise AssertionError("invalid handoff must fail before repository reads")

        codex_review.collect_review_evidence_bundle = forbidden_collect
        try:
            invalid_status, invalid = codex_review.build_codex_review_preview({}, repo)
            assert invalid_status == HTTPStatus.BAD_REQUEST
            assert invalid["error"] == "invalid_codex_review_handoff"
            assert invalid["review"] is None

            stale_payload = json.loads(json.dumps(payload))
            stale_payload["queue"]["items"][0]["current_task"] = "tampered task"
            stale_status, stale = codex_review.build_codex_review_preview(
                stale_payload,
                repo,
            )
            assert stale_status == HTTPStatus.BAD_REQUEST
            assert stale["detail"] == "selected review item scope approval is stale"
            assert stale["review"] is None
        finally:
            codex_review.collect_review_evidence_bundle = original_collect

        (repo / "outside.txt").write_text("outside approved scope\n", encoding="utf-8")
        blocked_status, blocked = codex_review.build_codex_review_preview(payload, repo)
        assert blocked_status == HTTPStatus.CONFLICT
        assert blocked["error"] == "codex_review_blocked"
        assert blocked["review"] is None
        assert any("outside.txt" in reason for reason in blocked["blocking_reasons"])
        (repo / "outside.txt").unlink()

        _run_fixture_git(repo, "add", "src/review.txt")
        staged_status, staged = codex_review.build_codex_review_preview(payload, repo)
        assert staged_status == HTTPStatus.CONFLICT
        assert staged["review"] is None
        assert any("staged" in reason for reason in staged["blocking_reasons"])

    captured_roots: list[Path] = []
    original_builder = run_web_app.build_codex_review_preview

    def recording_builder(
        payload: object,
        trusted_repo_root: str | Path,
    ) -> tuple[int, dict[str, object]]:
        captured_roots.append(Path(trusted_repo_root))
        return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "fixture"}

    run_web_app.build_codex_review_preview = recording_builder
    try:
        route_status, route_payload = run_web_app.handle_post_api(
            run_web_app.CODEX_REVIEW_PREVIEW_ENDPOINT,
            {},
        )
    finally:
        run_web_app.build_codex_review_preview = original_builder
    assert route_status == HTTPStatus.BAD_REQUEST
    assert route_payload == {"ok": False, "error": "fixture"}
    assert captured_roots == [run_web_app.REPO_ROOT]

    adapter_source = Path(codex_review.__file__).read_text(encoding="utf-8")
    forbidden_adapter_patterns = (
        ".write_text(",
        ".write_bytes(",
        ".mkdir(",
        ".unlink(",
        "subprocess",
        "requests",
        "urlopen",
        "render_prompt",
        "execute_command",
    )
    assert all(pattern not in adapter_source for pattern in forbidden_adapter_patterns)


def _test_evaluate_idea_vertical_slice() -> None:
    expected_keys = {
        "ok",
        "product_name",
        "executive_summary",
        "evidence_gaps",
        "key_critiques_risks",
        "minimum_experiments",
        "recommendation",
        "write_free",
        "local_only",
        "external_calls",
    }
    optional_payload = {
        "idea": "  A local workflow assistant for small clinic intake teams.  ",
        "goal": "  Decide whether a manual pilot is justified.  ",
        "context": "  Teams currently duplicate intake notes across two tools.  ",
        "provided_evidence": [
            "  Three staff interviews identified duplicate entry.  ",
            "A timed walkthrough took twelve minutes.",
        ],
    }
    watched_roots = (
        run_web_app.REPO_ROOT / "memory" / "tasks",
        run_web_app.REPO_ROOT / "reports",
    )

    def artifact_snapshot() -> tuple[tuple[str, int, int], ...]:
        snapshot: list[tuple[str, int, int]] = []
        for root in watched_roots:
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                stat_result = path.stat()
                snapshot.append(
                    (
                        path.relative_to(run_web_app.REPO_ROOT).as_posix(),
                        stat_result.st_size,
                        stat_result.st_mtime_ns,
                    )
                )
        return tuple(snapshot)

    before_artifacts = artifact_snapshot()
    first_status, first = run_web_app.evaluate_idea(optional_payload)
    second_status, second = run_web_app.evaluate_idea(optional_payload)
    assert first_status == HTTPStatus.OK
    assert second_status == HTTPStatus.OK
    assert first == second
    assert set(first) == expected_keys
    assert first["product_name"] == "Evaluate Idea"
    assert first["write_free"] is True
    assert first["local_only"] is True
    assert first["external_calls"] is False
    assert first["executive_summary"]
    assert len(first["executive_summary"]) <= 1_200
    assert 0 < len(first["evidence_gaps"]) <= run_web_app.EVALUATE_IDEA_MAX_GAPS
    assert (
        0
        < len(first["key_critiques_risks"])
        <= run_web_app.EVALUATE_IDEA_MAX_CRITIQUES
    )
    assert (
        0
        < len(first["minimum_experiments"])
        <= run_web_app.EVALUATE_IDEA_MAX_EXPERIMENTS
    )
    assert set(first["recommendation"]) == {
        "decision",
        "summary",
        "rationale",
        "next_step",
    }
    assert all(first["recommendation"].values())
    for gap in first["evidence_gaps"]:
        assert set(gap) == {
            "summary",
            "missing_evidence",
            "required_evidence",
            "validation_experiment",
            "confidence_impact",
        }
        assert len(gap["summary"]) <= 600
        assert len(gap["missing_evidence"]) <= 600
        assert len(gap["required_evidence"]) <= 600
        assert len(gap["validation_experiment"]) <= 800
        assert len(gap["confidence_impact"]) <= 80
    for critique in first["key_critiques_risks"]:
        assert set(critique) == {
            "reviewer_role",
            "finding",
            "severity",
            "suggested_action",
        }
        assert critique["severity"] in {"low", "medium", "high"}
        assert len(critique["finding"]) <= 800
        assert len(critique["suggested_action"]) <= 800
    for experiment in first["minimum_experiments"]:
        assert set(experiment) == {
            "title",
            "method",
            "success_metric",
            "minimum_sample",
            "risk",
        }
        assert all(experiment.values())
        assert len(experiment["title"]) <= 200
        assert len(experiment["method"]) <= 1_200
        assert len(experiment["success_metric"]) <= 600
        assert len(experiment["minimum_sample"]) <= 300
        assert len(experiment["risk"]) <= 600
    assert "markdown_report" not in first
    assert "optional_llm_augments" not in first
    assert "file_path" not in first
    assert "task_id" not in first
    assert artifact_snapshot() == before_artifacts

    minimal_status, minimal = run_web_app.evaluate_idea(
        {
            "idea": "A neighborhood tool-lending directory.",
            "goal": "Decide the smallest demand test.",
        }
    )
    assert minimal_status == HTTPStatus.OK
    assert set(minimal) == expected_keys

    known_input = run_web_app.ResearchCouncilInput(
        raw_idea="CLI tool that groups repeated local test failures.",
        goal="Decide whether to build a two-day prototype.",
        context="Developer tool with no external data source.",
        provided_evidence=("Two developers repeated the same diagnosis steps.",),
    )
    known_first = run_web_app.result_to_json_dict(
        run_web_app.run_research_council(
            known_input,
            llm_advisor_config=run_web_app.LLMAugmentationMode.OFF,
        )
    )
    known_second = run_web_app.result_to_json_dict(
        run_web_app.run_research_council(
            known_input,
            llm_advisor_config=run_web_app.LLMAugmentationMode.OFF,
        )
    )
    assert known_first == known_second
    assert known_first["optional_llm_augments"]["mode"] == "off"

    invalid_cases = (
        ({}, "evaluate_idea_requires_idea_and_goal"),
        ({"idea": "idea", "goal": " "}, "evaluate_idea_requires_idea_and_goal"),
        ({"idea": 7, "goal": "goal"}, "evaluate_idea_fields_must_be_strings"),
        (
            {"idea": "idea", "goal": "goal", "context": []},
            "evaluate_idea_fields_must_be_strings",
        ),
        (
            {"idea": "idea", "goal": "goal", "provided_evidence": "evidence"},
            "provided_evidence_must_be_a_list",
        ),
        (
            {
                "idea": "idea",
                "goal": "goal",
                "provided_evidence": ["entry"] * 9,
            },
            "too_many_provided_evidence_entries",
        ),
        (
            {
                "idea": "idea",
                "goal": "goal",
                "provided_evidence": [7],
            },
            "provided_evidence_entries_must_be_strings",
        ),
        (
            {
                "idea": "idea",
                "goal": "goal",
                "provided_evidence": [" "],
            },
            "provided_evidence_entries_must_be_nonempty",
        ),
        (
            {"idea": "idea", "goal": "goal", "path": "reports/result.md"},
            "evaluate_idea_unknown_fields",
        ),
        (
            {"idea": "x" * 2_001, "goal": "goal"},
            "idea_too_long",
        ),
        (
            {"idea": "idea\ud800", "goal": "goal"},
            "invalid_unicode",
        ),
        (
            {"idea": "idea", "goal": "goal\x00"},
            "invalid_unicode",
        ),
        (
            {"idea": "idea", "goal": "goal", "context": "context\ud800"},
            "invalid_unicode",
        ),
        (
            {
                "idea": "idea",
                "goal": "goal",
                "provided_evidence": ["evidence\x00"],
            },
            "invalid_unicode",
        ),
    )
    for invalid_payload, expected_error in invalid_cases:
        invalid_status, invalid = run_web_app.evaluate_idea(invalid_payload)
        assert invalid_status == HTTPStatus.BAD_REQUEST
        assert invalid == {"ok": False, "error": expected_error}
    assert artifact_snapshot() == before_artifacts

    html = Path(run_web_app.WEB_ROOT, "index.html").read_text(encoding="utf-8")
    app_js = Path(run_web_app.WEB_ROOT, "app.js").read_text(encoding="utf-8")
    styles = Path(run_web_app.WEB_ROOT, "styles.css").read_text(encoding="utf-8")
    assert html.count("Evaluate Idea") >= 3
    for heading in (
        "Executive summary",
        "Evidence gaps",
        "Key critiques / risks",
        "Minimum experiments",
        "Recommendation",
    ):
        assert heading in app_js
    assert "/api/evaluate-idea" in app_js
    assert "renderSkillDetails(\"research_council\", \"research\")" not in app_js
    assert "evaluate-idea-layout" in styles

    server = run_web_app.ThreadingHTTPServer(
        (run_web_app.DEFAULT_HOST, 0),
        run_web_app.JarvisConsoleHandler,
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    port = int(server.server_address[1])

    def post_evaluate_idea(
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        connection = HTTPConnection(run_web_app.DEFAULT_HOST, port, timeout=10)
        body = json.dumps(payload, ensure_ascii=True).encode("ascii")
        connection.request(
            "POST",
            run_web_app.EVALUATE_IDEA_ENDPOINT,
            body=body,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response_payload = json.loads(response.read().decode("utf-8"))
        response_status = response.status
        connection.close()
        return response_status, response_payload

    try:
        response_status, response_payload = post_evaluate_idea(optional_payload)
        assert response_status == HTTPStatus.OK
        assert response_payload == first

        surrogate_status, surrogate_response = post_evaluate_idea(
            {
                "idea": "HTTP surrogate \ud800",
                "goal": "Reject invalid Unicode.",
            }
        )
        assert surrogate_status == HTTPStatus.BAD_REQUEST
        assert surrogate_response == {"ok": False, "error": "invalid_unicode"}

        nul_status, nul_response = post_evaluate_idea(
            {
                "idea": "HTTP NUL evidence",
                "goal": "Reject invalid Unicode.",
                "provided_evidence": ["invalid\x00evidence"],
            }
        )
        assert nul_status == HTTPStatus.BAD_REQUEST
        assert nul_response == {"ok": False, "error": "invalid_unicode"}
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
    assert not server_thread.is_alive()
    assert artifact_snapshot() == before_artifacts


def _test_evaluate_idea_create_task_vertical_slice() -> None:
    class FakeClock:
        def __init__(self) -> None:
            self.value = 1_000.0

        def __call__(self) -> float:
            return self.value

        def advance(self, seconds: float) -> None:
            self.value += seconds

    class TokenFactory:
        def __init__(self, prefix: str = "evaluate-task-token") -> None:
            self.prefix = prefix
            self.counter = 0

        def __call__(self) -> str:
            self.counter += 1
            return f"{self.prefix}-{self.counter:08d}"

    class PreviewResult:
        def __init__(
            self,
            result_type: str,
            task_id: str | None = None,
        ) -> None:
            self.result_type = result_type
            self.task_id = task_id

    production_dir = run_web_app.REPO_ROOT / "memory" / "tasks"

    def production_snapshot() -> dict[str, str]:
        return {
            path.relative_to(production_dir).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(production_dir.rglob("*"))
            if path.is_file()
        }

    before_production = production_snapshot()
    optional_payload = {
        "idea": "A local workflow assistant for small clinic intake teams.",
        "goal": "Decide whether a manual pilot is justified.",
        "context": "Teams currently duplicate intake notes across two tools.",
        "provided_evidence": [
            "Three staff interviews identified duplicate entry.",
            "A timed walkthrough took twelve minutes.",
        ],
    }
    evaluation_status, evaluation = run_web_app.evaluate_idea(optional_payload)
    assert evaluation_status == HTTPStatus.OK
    actual_next_step = evaluation["recommendation"]["next_step"]
    assert "`experiment-001`" in actual_next_step
    assert run_web_app.normalize_evaluate_idea_task_seed(
        "  cafe\u0301\t`inner`\nword  "
    ) == ("caf\u00e9 inner word", None)
    assert run_web_app.normalize_evaluate_idea_task_seed(" \u2028 a\u00a0b ") == (
        "a b",
        None,
    )
    assert run_web_app.normalize_evaluate_idea_task_seed("`` \t") == (
        None,
        "evaluate_idea_create_task_next_step_empty",
    )
    for unsafe in ("bad\u200bvalue", "bad\x00value", "bad\ud800value"):
        assert run_web_app.normalize_evaluate_idea_task_seed(unsafe) == (
            None,
            "evaluate_idea_create_task_next_step_unsafe",
        )

    with TemporaryDirectory(prefix="jarvis-evaluate-task-") as temp_dir:
        tasks_dir = Path(temp_dir) / "memory" / "tasks"
        tasks_dir.mkdir(parents=True)
        clock = FakeClock()
        registry = run_web_app.CreateLocalTaskRegistry(
            clock=clock,
            token_factory=TokenFactory(),
            ttl_seconds=60,
            capacity=8,
        )

        preview_status, preview = (
            run_web_app.preview_evaluate_idea_create_task(
                optional_payload,
                registry=registry,
                tasks_dir=tasks_dir,
            )
        )
        assert preview_status == HTTPStatus.OK
        assert set(preview) == {
            "ok",
            "product_name",
            "result_type",
            "source",
            "token",
            "expires_in_seconds",
            "confirmation_literal",
            "evaluation",
            "candidate",
            "destination",
            "warning",
        }
        assert preview["product_name"] == "Create Local Task"
        assert preview["result_type"] == "preview"
        assert preview["source"] == "evaluate_idea"
        assert preview["confirmation_literal"] == "CREATE LOCAL TASK"
        assert preview["evaluation"] == {
            "decision": evaluation["recommendation"]["decision"],
            "next_step": actual_next_step,
        }
        assert "`" in preview["evaluation"]["next_step"]
        assert preview["candidate"] == {
            "title": (
                "Run experiment-001 (Workflow interview) as the primary next "
                "experiment"
            ),
            "summary": run_web_app.voice_candidate_summary(
                actual_next_step.replace("`", "")
            ),
            "status": "TODO",
            "repo": "jarvis-core",
            "source_command": "Evaluate Idea",
        }
        assert "`" not in preview["candidate"]["title"]
        assert "`" not in preview["candidate"]["summary"]
        assert preview["destination"] == {
            "storage_location": (
                "memory/tasks/task-0001-run-experiment-001-workflow-"
                "interview-as-the-primary-next-experiment.md"
            ),
            "provisional": True,
            "receipt_authoritative": True,
        }
        assert preview["warning"] == (
            "Evaluate Idea is decision support, not implementation approval. "
            "This preview creates nothing. Only explicit Confirm Create Local "
            "Task writes one local TODO Task."
        )
        assert not list(tasks_dir.iterdir())

        confirm_status, confirmed = run_web_app.confirm_create_local_task(
            {
                "token": preview["token"],
                "confirmation": preview["confirmation_literal"],
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert confirm_status == HTTPStatus.OK
        assert confirmed["result_type"] == "created"
        receipt = confirmed["receipt"]
        assert receipt["status"] == "TODO"
        assert receipt["storage_location"] == (
            preview["destination"]["storage_location"]
        )
        created_path = tasks_dir / Path(receipt["storage_location"]).name
        created_text = created_path.read_text(encoding="utf-8")
        assert "- status: `TODO`" in created_text
        assert "- source_command: `Evaluate Idea`" in created_text
        assert "completion_evidence" not in created_text
        assert "- execution_" not in created_text

        replay_status, replay = run_web_app.confirm_create_local_task(
            {
                "token": preview["token"],
                "confirmation": preview["confirmation_literal"],
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert replay_status == HTTPStatus.OK
        assert replay["result_type"] == "already_created"
        assert replay["receipt"] == receipt
        assert len(list(tasks_dir.glob("task-*.md"))) == 1

        race_status, race_preview = (
            run_web_app.preview_evaluate_idea_create_task(
                {
                    "idea": "Race-safe local task.",
                    "goal": "Decide the next bounded experiment.",
                },
                registry=registry,
                tasks_dir=tasks_dir,
                evaluator=lambda _payload: (
                    HTTPStatus.OK,
                    {
                        "recommendation": {
                            "decision": "continue_with_primary_blocker_experiment",
                            "next_step": "Run the allocation race experiment.",
                        }
                    },
                ),
            )
        )
        assert race_status == HTTPStatus.OK
        provisional_location = race_preview["destination"]["storage_location"]
        (tasks_dir / "task-0002-allocation-race.md").write_text(
            "fixture\n",
            encoding="utf-8",
        )
        race_confirm_status, race_confirmed = (
            run_web_app.confirm_create_local_task(
                {
                    "token": race_preview["token"],
                    "confirmation": "CREATE LOCAL TASK",
                },
                registry=registry,
                tasks_dir=tasks_dir,
            )
        )
        assert race_confirm_status == HTTPStatus.OK
        assert race_confirmed["receipt"]["storage_location"] != (
            provisional_location
        )
        assert race_confirmed["receipt"]["storage_location"].startswith(
            "memory/tasks/"
        )

        expired_status, expired_preview = (
            run_web_app.preview_evaluate_idea_create_task(
                {
                    "idea": "Expiry-safe local task.",
                    "goal": "Decide the next bounded experiment.",
                },
                registry=registry,
                tasks_dir=tasks_dir,
                evaluator=lambda _payload: (
                    HTTPStatus.OK,
                    {
                        "recommendation": {
                            "decision": "continue",
                            "next_step": "Run the expiry experiment.",
                        }
                    },
                ),
            )
        )
        assert expired_status == HTTPStatus.OK
        clock.advance(61)
        expired_confirm_status, expired_confirm = (
            run_web_app.confirm_create_local_task(
                {
                    "token": expired_preview["token"],
                    "confirmation": "CREATE LOCAL TASK",
                },
                registry=registry,
                tasks_dir=tasks_dir,
            )
        )
        assert expired_confirm_status == HTTPStatus.NOT_FOUND
        assert expired_confirm["error"] == (
            "invalid_or_expired_create_local_task_token"
        )

        captured_payloads: list[dict[str, Any]] = []

        def capture_defaults(
            payload: dict[str, Any],
        ) -> tuple[int, dict[str, Any]]:
            captured_payloads.append(payload)
            return HTTPStatus.OK, {
                "recommendation": {
                    "decision": "continue",
                    "next_step": "Run the defaults experiment.",
                }
            }

        defaults_status, defaults_preview = (
            run_web_app.preview_evaluate_idea_create_task(
                {"idea": "idea", "goal": "goal"},
                registry=registry,
                tasks_dir=tasks_dir,
                evaluator=capture_defaults,
            )
        )
        assert defaults_status == HTTPStatus.OK
        assert captured_payloads == [
            {
                "idea": "idea",
                "goal": "goal",
                "context": "",
                "provided_evidence": [],
            }
        ]
        assert list(captured_payloads[0]) == [
            "idea",
            "goal",
            "context",
            "provided_evidence",
        ]
        assert defaults_preview["candidate"]["source_command"] == "Evaluate Idea"

        long_status, long_preview = (
            run_web_app.preview_evaluate_idea_create_task(
                {"idea": "long", "goal": "truncate"},
                registry=registry,
                tasks_dir=tasks_dir,
                evaluator=lambda _payload: (
                    HTTPStatus.OK,
                    {
                        "recommendation": {
                            "decision": "continue",
                            "next_step": "x" * 1_000,
                        }
                    },
                ),
            )
        )
        assert long_status == HTTPStatus.OK
        assert len(long_preview["candidate"]["title"]) == 120
        assert len(long_preview["candidate"]["summary"]) == 280

        pause_status, pause_preview = (
            run_web_app.preview_evaluate_idea_create_task(
                {"idea": "pause", "goal": "remediate"},
                registry=registry,
                tasks_dir=tasks_dir,
                evaluator=lambda _payload: (
                    HTTPStatus.OK,
                    {
                        "recommendation": {
                            "decision": "pause_broad_use_resolve_safety_blocker",
                            "next_step": "Resolve the safety blocker first.",
                        }
                    },
                ),
            )
        )
        assert pause_status == HTTPStatus.OK
        assert pause_preview["evaluation"] == {
            "decision": "pause_broad_use_resolve_safety_blocker",
            "next_step": "Resolve the safety blocker first.",
        }
        assert pause_preview["candidate"]["status"] == "TODO"

        invalid_cases = (
            ({}, "requires_idea_and_goal"),
            (
                {"idea": "idea", "goal": " ", "context": "", "provided_evidence": []},
                "requires_idea_and_goal",
            ),
            (
                {"idea": 7, "goal": "goal"},
                "fields_must_be_strings",
            ),
            (
                {"idea": "idea", "goal": "goal", "context": []},
                "fields_must_be_strings",
            ),
            (
                {"idea": "idea", "goal": "goal", "provided_evidence": "x"},
                "provided_evidence_must_be_a_list",
            ),
            (
                {
                    "idea": "idea",
                    "goal": "goal",
                    "provided_evidence": ["x"] * 9,
                },
                "too_many_provided_evidence_entries",
            ),
            (
                {
                    "idea": "idea",
                    "goal": "goal",
                    "provided_evidence": [7],
                },
                "provided_evidence_entries_must_be_strings",
            ),
            (
                {
                    "idea": "idea",
                    "goal": "goal",
                    "provided_evidence": [" "],
                },
                "provided_evidence_entries_must_be_nonempty",
            ),
            (
                {
                    "idea": "idea",
                    "goal": "goal",
                    "provided_evidence": ["x" * 501],
                },
                "provided_evidence_entry_too_long",
            ),
            (
                {"idea": "x" * 2_001, "goal": "goal"},
                "idea_too_long",
            ),
            (
                {"idea": "idea", "goal": "x" * 501},
                "goal_too_long",
            ),
            (
                {"idea": "idea", "goal": "goal", "context": "x" * 2_001},
                "context_too_long",
            ),
            (
                {"idea": "idea\ud800", "goal": "goal"},
                "invalid_unicode",
            ),
            (
                {
                    "idea": "idea",
                    "goal": "goal",
                    "title": "client-controlled",
                },
                "unknown_fields",
            ),
        )
        for invalid_payload, suffix in invalid_cases:
            invalid_status, invalid = (
                run_web_app.preview_evaluate_idea_create_task(
                    invalid_payload,
                    registry=registry,
                    tasks_dir=tasks_dir,
                )
            )
            assert invalid_status == HTTPStatus.BAD_REQUEST
            assert invalid["error"] == (
                f"evaluate_idea_create_task_{suffix}"
            )

        business_cases = (
            (
                lambda _payload: (HTTPStatus.OK, {}),
                "evaluate_idea_create_task_recommendation_unavailable",
            ),
            (
                lambda _payload: (
                    HTTPStatus.OK,
                    {"recommendation": {"decision": "continue"}},
                ),
                "evaluate_idea_create_task_next_step_unavailable",
            ),
            (
                lambda _payload: (
                    HTTPStatus.OK,
                    {
                        "recommendation": {
                            "decision": "continue",
                            "next_step": 7,
                        }
                    },
                ),
                "evaluate_idea_create_task_next_step_nonstring",
            ),
            (
                lambda _payload: (
                    HTTPStatus.OK,
                    {
                        "recommendation": {
                            "decision": "continue",
                            "next_step": "bad\u200bvalue",
                        }
                    },
                ),
                "evaluate_idea_create_task_next_step_unsafe",
            ),
            (
                lambda _payload: (
                    HTTPStatus.OK,
                    {
                        "recommendation": {
                            "decision": "continue",
                            "next_step": " `` \t",
                        }
                    },
                ),
                "evaluate_idea_create_task_next_step_empty",
            ),
        )
        for evaluator, expected_error in business_cases:
            status, result = run_web_app.preview_evaluate_idea_create_task(
                {"idea": "idea", "goal": "goal"},
                registry=registry,
                tasks_dir=tasks_dir,
                evaluator=evaluator,
            )
            assert status == HTTPStatus.CONFLICT
            assert result["error"] == expected_error

        unexpected_status, unexpected = (
            run_web_app.preview_evaluate_idea_create_task(
                {"idea": "idea", "goal": "goal"},
                registry=registry,
                tasks_dir=tasks_dir,
                evaluator=lambda _payload: (
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False},
                ),
            )
        )
        assert unexpected_status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert unexpected["error"] == (
            "evaluate_idea_create_task_preview_failed"
        )

        def raise_evaluator(_payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
            raise RuntimeError("injected evaluator failure")

        raised_status, raised = run_web_app.preview_evaluate_idea_create_task(
            {"idea": "idea", "goal": "goal"},
            registry=registry,
            tasks_dir=tasks_dir,
            evaluator=raise_evaluator,
        )
        assert raised_status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert raised["error"] == "evaluate_idea_create_task_preview_failed"

        def raise_storage(
            _candidate: dict[str, str],
            *,
            tasks_dir: Path,
        ) -> Any:
            raise OSError("injected storage failure")

        storage_status, storage = run_web_app.preview_evaluate_idea_create_task(
            {"idea": "idea", "goal": "goal"},
            registry=registry,
            tasks_dir=tasks_dir,
            evaluator=capture_defaults,
            candidate_previewer=raise_storage,
        )
        assert storage_status == HTTPStatus.CONFLICT
        assert storage["error"] == (
            "evaluate_idea_create_task_storage_unavailable"
        )
        candidate_status, candidate_error = (
            run_web_app.preview_evaluate_idea_create_task(
                {"idea": "idea", "goal": "goal"},
                registry=registry,
                tasks_dir=tasks_dir,
                evaluator=capture_defaults,
                candidate_previewer=lambda _candidate, *, tasks_dir: (
                    PreviewResult("hold")
                ),
            )
        )
        assert candidate_status == HTTPStatus.CONFLICT
        assert candidate_error["error"] == (
            "evaluate_idea_create_task_candidate_preview_failed"
        )
        unavailable_status, unavailable = (
            run_web_app.preview_evaluate_idea_create_task(
                {"idea": "idea", "goal": "goal"},
                registry=run_web_app.CreateLocalTaskRegistry(capacity=0),
                tasks_dir=tasks_dir,
                evaluator=capture_defaults,
            )
        )
        assert unavailable_status == HTTPStatus.SERVICE_UNAVAILABLE
        assert unavailable["error"] == (
            "evaluate_idea_create_task_temporarily_unavailable"
        )

        valid_headers = [
            ("Host", "127.0.0.1:43210"),
            ("Origin", "http://127.0.0.1:43210"),
            ("Content-Type", "application/json"),
            ("Content-Length", "2"),
        ]
        assert run_web_app.validate_evaluate_idea_create_task_http_request(
            path=run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT,
            query="",
            header_pairs=valid_headers,
            bound_port=43210,
        ) == (HTTPStatus.OK, {"ok": True, "body_length": 2})
        guard_cases = (
            (
                [*valid_headers, ("Host", "127.0.0.1:43210")],
                HTTPStatus.BAD_REQUEST,
                "evaluate_idea_create_task_headers_rejected",
            ),
            (
                [pair for pair in valid_headers if pair[0] != "Origin"],
                HTTPStatus.BAD_REQUEST,
                "evaluate_idea_create_task_headers_rejected",
            ),
            (
                [*valid_headers, ("Transfer-Encoding", "chunked")],
                HTTPStatus.BAD_REQUEST,
                "evaluate_idea_create_task_transfer_encoding_not_allowed",
            ),
            (
                [
                    (name, "http://127.0.0.1:1")
                    if name == "Origin"
                    else (name, value)
                    for name, value in valid_headers
                ],
                HTTPStatus.FORBIDDEN,
                "evaluate_idea_create_task_origin_rejected",
            ),
            (
                [
                    (name, "text/plain")
                    if name == "Content-Type"
                    else (name, value)
                    for name, value in valid_headers
                ],
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "evaluate_idea_create_task_json_required",
            ),
            (
                [
                    (name, "0")
                    if name == "Content-Length"
                    else (name, value)
                    for name, value in valid_headers
                ],
                HTTPStatus.BAD_REQUEST,
                "evaluate_idea_create_task_invalid_content_length",
            ),
        )
        for headers, expected_status, expected_error in guard_cases:
            status, result = (
                run_web_app.validate_evaluate_idea_create_task_http_request(
                    path=run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT,
                    query="",
                    header_pairs=headers,
                    bound_port=43210,
                )
            )
            assert status == expected_status
            assert result["error"] == expected_error
        large_status, large = (
            run_web_app.validate_evaluate_idea_create_task_http_request(
                path=run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT,
                query="",
                header_pairs=[
                    (name, str(run_web_app.MAX_JSON_BODY_BYTES + 1))
                    if name == "Content-Length"
                    else (name, value)
                    for name, value in valid_headers
                ],
                bound_port=43210,
            )
        )
        assert large_status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        assert large["error"] == (
            "evaluate_idea_create_task_body_size_rejected"
        )
        too_many_status, too_many = (
            run_web_app.validate_evaluate_idea_create_task_http_request(
                path=run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT,
                query="",
                header_pairs=[
                    *valid_headers,
                    *[(f"X-Test-{index}", "x") for index in range(29)],
                ],
                bound_port=43210,
            )
        )
        assert too_many_status == HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE
        assert too_many["error"] == (
            "evaluate_idea_create_task_headers_rejected"
        )
        for path, query in (
            (run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT, "x=1"),
            ("/api/evaluate-idea/create-task-preview/other", ""),
        ):
            not_found_status, not_found = (
                run_web_app.validate_evaluate_idea_create_task_http_request(
                    path=path,
                    query=query,
                    header_pairs=valid_headers,
                    bound_port=43210,
                )
            )
            assert not_found_status == HTTPStatus.NOT_FOUND
            assert not_found["error"] == (
                "evaluate_idea_create_task_not_found"
            )

        parse_cases = (
            (
                b"\xff",
                "evaluate_idea_create_task_invalid_json",
            ),
            (
                b"{",
                "evaluate_idea_create_task_invalid_json",
            ),
            (
                b'{"idea":"one","idea":"two"}',
                "evaluate_idea_create_task_duplicate_json_key",
            ),
            (
                b"[]",
                "evaluate_idea_create_task_json_must_be_object",
            ),
        )
        for raw_body, expected_error in parse_cases:
            parse_status, parsed = (
                run_web_app.parse_evaluate_idea_create_task_json_body(raw_body)
            )
            assert parse_status == HTTPStatus.BAD_REQUEST
            assert parsed["error"] == expected_error
        assert run_web_app.handle_post_api(
            run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT,
            optional_payload,
        ) == (HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

        http_registry = run_web_app.CreateLocalTaskRegistry(
            token_factory=TokenFactory("evaluate-http-token"),
            capacity=8,
        )
        server = run_web_app.ThreadingHTTPServer(
            (run_web_app.DEFAULT_HOST, 0),
            run_web_app.JarvisConsoleHandler,
        )
        server.create_local_task_registry = http_registry
        server.create_local_tasks_dir = tasks_dir
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        port = int(server.server_address[1])

        def post_json(
            path: str,
            payload: dict[str, Any],
        ) -> tuple[int, dict[str, Any]]:
            connection = HTTPConnection(run_web_app.DEFAULT_HOST, port, timeout=10)
            body = json.dumps(payload, ensure_ascii=True).encode("ascii")
            connection.request(
                "POST",
                path,
                body=body,
                headers={
                    "Origin": f"http://{run_web_app.DEFAULT_HOST}:{port}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            response_payload = json.loads(response.read().decode("utf-8"))
            response_status = response.status
            connection.close()
            return response_status, response_payload

        try:
            http_status, http_preview = post_json(
                run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT,
                optional_payload,
            )
            assert http_status == HTTPStatus.OK
            assert http_preview["source"] == "evaluate_idea"
            query_status, query_result = post_json(
                f"{run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT}?x=1",
                optional_payload,
            )
            assert query_status == HTTPStatus.NOT_FOUND
            assert query_result["error"] == (
                "evaluate_idea_create_task_not_found"
            )
            unknown_status, unknown = post_json(
                "/api/completely-unknown",
                {},
            )
            assert unknown_status == HTTPStatus.NOT_FOUND
            assert unknown["error"] == "not_found"

            truncated_body = json.dumps(optional_payload).encode("utf-8")
            declared_length = len(truncated_body) + 7
            raw_request = (
                f"POST {run_web_app.EVALUATE_IDEA_CREATE_TASK_PREVIEW_ENDPOINT} "
                "HTTP/1.1\r\n"
                f"Host: {run_web_app.DEFAULT_HOST}:{port}\r\n"
                f"Origin: http://{run_web_app.DEFAULT_HOST}:{port}\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {declared_length}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode("ascii") + truncated_body
            with socket.create_connection(
                (run_web_app.DEFAULT_HOST, port),
                timeout=5,
            ) as truncated_socket:
                truncated_socket.sendall(raw_request)
                truncated_socket.shutdown(socket.SHUT_WR)
                response_chunks: list[bytes] = []
                while True:
                    chunk = truncated_socket.recv(4096)
                    if not chunk:
                        break
                    response_chunks.append(chunk)
            raw_response = b"".join(response_chunks)
            assert b" 400 " in raw_response.split(b"\r\n", 1)[0]
            assert (
                b"evaluate_idea_create_task_body_length_mismatch"
                in raw_response
            )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
        assert not server_thread.is_alive()

    assert production_snapshot() == before_production


def _test_evaluate_idea_create_task_client_state_machine() -> None:
    app_js = Path(run_web_app.WEB_ROOT, "app.js").read_text(encoding="utf-8")
    block_start = app_js.index("function evaluateIdeaList(")
    block_end = app_js.index("function copyCommandLabel(", block_start)
    feature_source = app_js[block_start:block_end]
    isolated_source = app_js[
        app_js.index("function canonicalEvaluateIdeaPayload(", block_start):
        block_end
    ]
    for voice_authority in (
        "createLocalTaskToken",
        "createLocalTaskConfirmation",
        "createLocalTaskBusy",
        "lastVoiceCandidateData",
    ):
        assert voice_authority not in isolated_source
    assert ">Preview as Local Task<" in feature_source
    assert '"/api/evaluate-idea/create-task-preview"' in feature_source
    assert '"/api/create-local-task/confirm"' in feature_source

    harness = f"""
function escapeHtml(value) {{
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}}
function field(value = "") {{
  return {{ value, disabled: false }};
}}
const evaluateIdeaInput = field("Initial idea");
const evaluateIdeaGoal = field("Choose a bounded next experiment");
const evaluateIdeaContext = field("Initial context");
const evaluateIdeaEvidence = field("Evidence one\\nEvidence two");
const evaluateIdeaButton = {{ disabled: false, textContent: "" }};
const statusText = {{ textContent: "" }};
const nextActionText = {{ textContent: "" }};
const previewButton = {{ disabled: false, textContent: "" }};
const confirmButton = {{ disabled: false, textContent: "" }};
const resultTarget = {{
  innerHTML: "",
  querySelector(selector) {{
    if (
      selector === ".evaluate-create-local-task-receipt"
      && this.innerHTML.includes("evaluate-create-local-task-receipt")
    ) {{
      return {{}};
    }}
    return null;
  }},
}};
const researchDetails = {{
  _innerHTML: "",
  get innerHTML() {{
    return this._innerHTML;
  }},
  set innerHTML(value) {{
    this._innerHTML = value;
    if (value.includes("evaluate-create-local-task-result")) {{
      resultTarget.innerHTML = "No Evaluate-to-Task preview yet.";
    }}
  }},
  querySelector(selector) {{
    if (
      selector === ".evaluate-create-local-task-result"
      && this._innerHTML.includes("evaluate-create-local-task-result")
    ) {{
      return resultTarget;
    }}
    if (
      selector === ".preview-evaluate-local-task"
      && this._innerHTML.includes("preview-evaluate-local-task")
    ) {{
      return previewButton;
    }}
    if (
      selector === ".confirm-evaluate-local-task"
      && resultTarget.innerHTML.includes("confirm-evaluate-local-task")
    ) {{
      return confirmButton;
    }}
    return null;
  }},
}};
let lastVoiceCandidateData = {{ id: "voice-candidate" }};
let createLocalTaskToken = "voice-token";
let createLocalTaskConfirmation = "VOICE CONFIRM";
let createLocalTaskBusy = true;
let evaluateIdeaBusy = false;
let evaluateIdeaRevision = 0;
let evaluateSuccessfulBinding = null;
let evaluateTaskPreviewBusy = false;
let evaluateTaskToken = "";
let evaluateTaskConfirmation = "";
let evaluateTaskTokenBinding = null;
let evaluateTaskConfirmPending = false;
let evaluateTaskConfirmInFlight = false;
let evaluateTaskConfirmRetryReady = false;
const HTTP_STATUS_OK = 200;
const fetchCalls = [];
const fetchQueue = [];
async function fetch(url, options) {{
  fetchCalls.push({{ url, options }});
  if (!fetchQueue.length) {{
    throw new Error(`No queued response for ${{url}}`);
  }}
  return await fetchQueue.shift();
}}
function response(status, data) {{
  return {{
    status,
    ok: status >= 200 && status < 300,
    async json() {{
      return data;
    }},
  }};
}}
function deferred() {{
  let resolve;
  let reject;
  const promise = new Promise((resolveValue, rejectValue) => {{
    resolve = resolveValue;
    reject = rejectValue;
  }});
  return {{ promise, resolve, reject }};
}}
function evaluationData(nextStep = "Run the bounded workflow experiment.") {{
  return {{
    ok: true,
    executive_summary: "Local evaluation.",
    evidence_gaps: [],
    key_critiques_risks: [],
    minimum_experiments: [],
    recommendation: {{
      decision: "continue",
      summary: "Continue.",
      rationale: "Evidence supports one bounded test.",
      next_step: nextStep,
    }},
    write_free: true,
    local_only: true,
    external_calls: false,
  }};
}}
function previewData(token) {{
  return {{
    ok: true,
    product_name: "Create Local Task",
    result_type: "preview",
    source: "evaluate_idea",
    token,
    expires_in_seconds: 60,
    confirmation_literal: "CREATE LOCAL TASK",
    evaluation: {{
      decision: "continue",
      next_step: "Run the bounded workflow experiment.",
    }},
    candidate: {{
      title: "Run the bounded workflow experiment",
      summary: "Run the bounded workflow experiment.",
      status: "TODO",
      repo: "jarvis-core",
      source_command: "Evaluate Idea",
    }},
    destination: {{
      storage_location: "memory/tasks/task-0001-run-the-bounded-workflow-experiment.md",
      provisional: true,
      receipt_authoritative: true,
    }},
    warning: "Preview creates nothing.",
  }};
}}
function receiptData(resultType = "created") {{
  return {{
    ok: true,
    product_name: "Create Local Task",
    result_type: resultType,
    receipt: {{
      task_id: "task-0001-run-the-bounded-workflow-experiment",
      title: "Run the bounded workflow experiment",
      status: "TODO",
      storage_location: "memory/tasks/task-0001-run-the-bounded-workflow-experiment.md",
      created_at: "2026-07-27 00:00 UTC",
      next_recommended_action: "Review the new TODO task.",
    }},
  }};
}}
{feature_source}
(async () => {{
  const canonical = canonicalEvaluateIdeaPayload();
  if (
    JSON.stringify(Object.keys(canonical))
    !== JSON.stringify(["idea", "goal", "context", "provided_evidence"])
  ) {{
    throw new Error("canonical Evaluate payload order changed");
  }}

  const staleEvaluate = deferred();
  fetchQueue.push(staleEvaluate.promise);
  const staleEvaluateRequest = evaluateIdea();
  await Promise.resolve();
  evaluateIdeaInput.value = "Mutated while Evaluate was in flight";
  onEvaluateIdeaInputMutation();
  staleEvaluate.resolve(response(200, evaluationData()));
  await staleEvaluateRequest;
  if (evaluateSuccessfulBinding !== null) {{
    throw new Error("late Evaluate response retained authority");
  }}

  fetchQueue.push(response(200, evaluationData()));
  await evaluateIdea();
  if (!evaluateIdeaBindingMatches(evaluateSuccessfulBinding)) {{
    throw new Error("successful Evaluate did not bind current inputs");
  }}
  const successfulEvaluateCall = fetchCalls.at(-1);
  const successfulBody = JSON.parse(successfulEvaluateCall.options.body);
  if (
    successfulEvaluateCall.url !== "/api/evaluate-idea"
    || JSON.stringify(Object.keys(successfulBody))
      !== JSON.stringify(["idea", "goal", "context", "provided_evidence"])
  ) {{
    throw new Error("Evaluate request did not use the fixed canonical payload");
  }}

  const stalePreview = deferred();
  fetchQueue.push(stalePreview.promise);
  const stalePreviewRequest = previewEvaluateIdeaAsTask();
  await Promise.resolve();
  evaluateIdeaContext.value = "Mutated while Preview was in flight";
  onEvaluateIdeaInputMutation();
  stalePreview.resolve(response(200, previewData("stale-token-00000001")));
  await stalePreviewRequest;
  if (evaluateTaskToken || evaluateSuccessfulBinding !== null) {{
    throw new Error("late Preview response retained authority");
  }}

  fetchQueue.push(response(200, evaluationData()));
  await evaluateIdea();
  const boundPayloadJson = evaluateSuccessfulBinding.payloadJson;
  fetchQueue.push(response(200, previewData("evaluate-token-00000001")));
  await previewEvaluateIdeaAsTask();
  const successfulPreviewCall = fetchCalls.at(-1);
  if (
    successfulPreviewCall.url !== "/api/evaluate-idea/create-task-preview"
    || successfulPreviewCall.options.body !== boundPayloadJson
    || evaluateTaskToken !== "evaluate-token-00000001"
  ) {{
    throw new Error("Preview was not bound to the exact successful Evaluate tuple");
  }}
  if (
    createLocalTaskToken !== "voice-token"
    || createLocalTaskConfirmation !== "VOICE CONFIRM"
    || createLocalTaskBusy !== true
    || lastVoiceCandidateData.id !== "voice-candidate"
  ) {{
    throw new Error("Evaluate handoff mutated Voice authority");
  }}

  fetchQueue.push(Promise.reject(new Error("lost confirm response")));
  await confirmEvaluateIdeaTask();
  const firstConfirmCall = fetchCalls.at(-1);
  const firstConfirmBody = firstConfirmCall.options.body;
  if (
    !evaluateTaskConfirmPending
    || !evaluateTaskConfirmRetryReady
    || evaluateTaskToken !== "evaluate-token-00000001"
    || !evaluateIdeaInput.disabled
    || firstConfirmCall.url !== "/api/create-local-task/confirm"
  ) {{
    throw new Error("lost Confirm did not retain locked retry authority");
  }}
  const lockedCallCount = fetchCalls.length;
  const lockedRevision = evaluateIdeaRevision;
  onEvaluateIdeaInputMutation();
  await evaluateIdea();
  await previewEvaluateIdeaAsTask();
  if (
    fetchCalls.length !== lockedCallCount
    || evaluateIdeaRevision !== lockedRevision
  ) {{
    throw new Error("Confirm-pending lock allowed a new evaluation or handoff");
  }}

  fetchQueue.push(response(200, receiptData("already_created")));
  await confirmEvaluateIdeaTask();
  const retryConfirmCall = fetchCalls.at(-1);
  const receiptCount = (
    resultTarget.innerHTML.match(/evaluate-create-local-task-receipt/g) || []
  ).length;
  if (
    retryConfirmCall.options.body !== firstConfirmBody
    || receiptCount !== 1
    || evaluateTaskToken
    || evaluateTaskConfirmPending
    || evaluateIdeaInput.disabled
  ) {{
    throw new Error(`Retry Confirm did not reconcile one receipt and unlock: ${{
      JSON.stringify({{
        sameBody: retryConfirmCall.options.body === firstConfirmBody,
        receiptCount,
        evaluateTaskToken,
        evaluateTaskConfirmPending,
        inputDisabled: evaluateIdeaInput.disabled,
      }})
    }}`);
  }}

  fetchQueue.push(response(200, evaluationData()));
  await evaluateIdea();
  fetchQueue.push(response(200, previewData("evaluate-token-00000002")));
  await previewEvaluateIdeaAsTask();
  fetchQueue.push(response(409, {{ ok: false, error: "terminal conflict" }}));
  await confirmEvaluateIdeaTask();
  if (
    evaluateTaskToken
    || evaluateTaskConfirmPending
    || evaluateIdeaInput.disabled
    || !resultTarget.innerHTML.includes("terminal conflict")
  ) {{
    throw new Error("terminal 4xx did not clear authority and unlock");
  }}
  if (
    createLocalTaskToken !== "voice-token"
    || createLocalTaskConfirmation !== "VOICE CONFIRM"
    || createLocalTaskBusy !== true
    || lastVoiceCandidateData.id !== "voice-candidate"
  ) {{
    throw new Error("Voice authority changed after confirm paths");
  }}
}})().catch((error) => {{
  console.error(error.stack || error);
  process.exitCode = 1;
}});
"""
    completed = subprocess.run(
        ("node", "-"),
        cwd=Path(__file__).resolve().parent,
        input=harness,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, (
        "Evaluate-to-Task client state harness failed: "
        f"{completed.stdout}\n{completed.stderr}"
    )


def _test_create_local_task_vertical_slice() -> None:
    class FakeClock:
        def __init__(self) -> None:
            self.value = 1000.0

        def __call__(self) -> float:
            return self.value

        def advance(self, seconds: float) -> None:
            self.value += seconds

    class TokenFactory:
        def __init__(self) -> None:
            self.counter = 0

        def __call__(self) -> str:
            self.counter += 1
            return f"create-local-task-token-{self.counter:08d}"

    class FailingTextFile:
        def __init__(self, path: Path, stage: str) -> None:
            self._file = path.open("x", encoding="utf-8", newline="\n")
            self._stage = stage

        def write(self, content: str) -> int:
            if self._stage == "write":
                raise OSError("injected write failure")
            return self._file.write(content)

        def flush(self) -> None:
            if self._stage == "flush":
                raise OSError("injected flush failure")
            self._file.flush()

        def fileno(self) -> int:
            return self._file.fileno()

        def close(self) -> None:
            self._file.close()
            if self._stage == "close":
                raise OSError("injected close failure")

    html = Path(run_web_app.WEB_ROOT, "index.html").read_text(encoding="utf-8")
    assert (
        "Safety mode: Task discovery and basic details are read-only. Create "
        "Local Task creates one local TODO from Voice Inbox or a reviewed "
        "Evaluate Idea recommendation; Start / Complete changes only status and "
        "updated_at; Record Completion Evidence appends one evidence value and "
        "updates only updated_at for an eligible DOING Task. Evaluate Idea and "
        "every Task preview remain write-free. Every write requires Preview and "
        "explicit Confirm. Evidence is not validated, status stays DOING, and "
        "no flow executes or automatically completes Task work. Jarvis does not "
        "create approvals or reports, run skills, commit, push, or make external "
        "calls."
        in html
    )
    assert run_web_app.handle_post_api(
        run_web_app.CREATE_LOCAL_TASK_PREVIEW_ENDPOINT,
        {"transcript": "must use guarded handler"},
    )[0] == HTTPStatus.NOT_FOUND
    assert run_web_app.handle_post_api(
        run_web_app.CREATE_LOCAL_TASK_CONFIRM_ENDPOINT,
        {"token": "must-use-guarded-handler", "confirmation": "CREATE LOCAL TASK"},
    )[0] == HTTPStatus.NOT_FOUND

    with TemporaryDirectory(prefix="jarvis-create-local-task-") as temp_dir:
        tasks_dir = Path(temp_dir) / "memory" / "tasks"
        tasks_dir.mkdir(parents=True)
        clock = FakeClock()
        registry = run_web_app.CreateLocalTaskRegistry(
            clock=clock,
            token_factory=TokenFactory(),
            ttl_seconds=60,
            capacity=8,
        )

        preview_status, preview = run_web_app.preview_create_local_task(
            {"transcript": "오늘 장보기 목록 정리해줘\n우유와 계란을 확인해줘"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert preview_status == HTTPStatus.OK
        assert preview["product_name"] == "Create Local Task"
        assert preview["preview"] == {
            "title": "오늘 장보기 목록 정리해줘 우유와 계란을 확인해줘",
            "summary": "오늘 장보기 목록 정리해줘 우유와 계란을 확인해줘",
            "status": "TODO",
            "local_destination": "memory/tasks/task-0001-task.md",
        }
        assert preview["raw_transcript_saved"] is False
        assert not list(tasks_dir.iterdir())

        token = preview["token"]
        wrong_literal_status, wrong_literal = run_web_app.confirm_create_local_task(
            {"token": token, "confirmation": "confirm"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert wrong_literal_status == HTTPStatus.BAD_REQUEST
        assert wrong_literal["error"] == "exact_confirmation_required"
        assert not list(tasks_dir.iterdir())

        clock.advance(59)
        confirm_status, confirmed = run_web_app.confirm_create_local_task(
            {
                "token": token,
                "confirmation": run_web_app.CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert confirm_status == HTTPStatus.OK
        assert confirmed["result_type"] == "created"
        receipt = confirmed["receipt"]
        assert set(receipt) == {
            "task_id",
            "title",
            "status",
            "storage_location",
            "created_at",
            "next_recommended_action",
        }
        assert receipt["task_id"] == "task-0001-task"
        assert receipt["title"] == preview["preview"]["title"]
        assert receipt["status"] == "TODO"
        assert receipt["storage_location"] == "memory/tasks/task-0001-task.md"
        assert receipt["created_at"]
        assert receipt["next_recommended_action"]
        task_path = tasks_dir / "task-0001-task.md"
        assert task_path.is_file()
        task_text = task_path.read_text(encoding="utf-8")
        assert f"- title: `{receipt['title']}`" in task_text
        assert "- status: `TODO`" in task_text
        assert "\n우유와" not in task_text

        # Keep an idempotent receipt available for a bounded window after a
        # late confirmation, even once the original preview TTL has elapsed.
        clock.advance(2)
        duplicate_status, duplicate = run_web_app.confirm_create_local_task(
            {
                "token": token,
                "confirmation": run_web_app.CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert duplicate_status == HTTPStatus.OK
        assert duplicate["result_type"] == "already_created"
        assert duplicate["receipt"] == receipt
        assert len(list(tasks_dir.glob("task-*.md"))) == 1

        collision_status, collision_preview = run_web_app.preview_create_local_task(
            {"transcript": "내일 일정 정리"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert collision_status == HTTPStatus.OK
        assert collision_preview["preview"]["local_destination"] == (
            "memory/tasks/task-0002-task.md"
        )
        collision_confirm_status, collision_confirmed = (
            run_web_app.confirm_create_local_task(
                {
                    "token": collision_preview["token"],
                    "confirmation": run_web_app.CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
                },
                registry=registry,
                tasks_dir=tasks_dir,
            )
        )
        assert collision_confirm_status == HTTPStatus.OK
        assert collision_confirmed["receipt"]["task_id"] == "task-0002-task"

        expired_status, expired_preview = run_web_app.preview_create_local_task(
            {"transcript": "만료 확인 작업"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert expired_status == HTTPStatus.OK
        clock.advance(61)
        expired_confirm_status, expired_confirm = run_web_app.confirm_create_local_task(
            {
                "token": expired_preview["token"],
                "confirmation": run_web_app.CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert expired_confirm_status == HTTPStatus.NOT_FOUND
        assert expired_confirm["error"] == "invalid_or_expired_create_local_task_token"

        unknown_status, unknown = run_web_app.confirm_create_local_task(
            {
                "token": "unknown-create-local-task-token",
                "confirmation": run_web_app.CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert unknown_status == HTTPStatus.NOT_FOUND
        assert unknown["error"] == "invalid_or_expired_create_local_task_token"

        unsafe_status, unsafe = run_web_app.preview_create_local_task(
            {"transcript": "제목에 ` 구분자 넣기"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert unsafe_status == HTTPStatus.CONFLICT
        assert unsafe["error"] == "unsafe_markdown_delimiter:title"
        extra_status, extra = run_web_app.preview_create_local_task(
            {"transcript": "정상", "status": "DONE"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert extra_status == HTTPStatus.BAD_REQUEST
        assert extra["error"] == "create_local_task_preview_accepts_transcript_only"
        mutable_confirm_status, mutable_confirm = run_web_app.confirm_create_local_task(
            {
                "token": token,
                "confirmation": run_web_app.CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
                "title": "tampered",
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert mutable_confirm_status == HTTPStatus.BAD_REQUEST
        assert (
            mutable_confirm["error"]
            == "create_local_task_confirm_accepts_token_and_confirmation_only"
        )

        writer_draft = {
            "title": "safe-title",
            "status": "TODO",
            "repo": "jarvis-core",
            "summary": "unsafe\nsummary",
            "source_command": "Voice Inbox",
        }
        writer_result = run_web_app.preview_task_file_write(
            writer_draft,
            tasks_dir=tasks_dir,
        )
        assert writer_result.result_type == "hold"
        assert writer_result.reason == "unsafe_metadata_newline:summary"

        safe_writer_draft = {
            "title": "failure atomic task",
            "status": "TODO",
            "repo": "jarvis-core",
            "summary": "No partial final task may survive an I/O failure.",
            "source_command": "Voice Inbox",
        }
        for failure_stage in ("write", "flush", "close", "publish"):
            failure_dir = tasks_dir / f"failure-{failure_stage}"
            failure_dir.mkdir()

            def injected_open(
                path: Path,
                stage: str = failure_stage,
            ) -> FailingTextFile:
                return FailingTextFile(path, stage)

            def injected_publish(_temp_path: Path, _target_path: Path) -> None:
                raise OSError("injected publish failure")

            failure_kwargs: dict[str, Any] = {
                "_temp_token_factory": lambda: "f" * 16,
            }
            if failure_stage == "publish":
                failure_kwargs["_publish_temp_file"] = injected_publish
            else:
                failure_kwargs["_open_temp_file"] = injected_open
            failed_write = run_web_app.write_task_file(
                safe_writer_draft,
                tasks_dir=failure_dir,
                **failure_kwargs,
            )
            assert failed_write.result_type == "error"
            assert not list(failure_dir.glob("task-*.md"))
            assert not list(failure_dir.iterdir())

            recovery = run_web_app.write_task_file(
                safe_writer_draft,
                tasks_dir=failure_dir,
            )
            assert recovery.result_type == "created"
            assert recovery.task_id == "task-0001-failure-atomic-task"
            assert len(list(failure_dir.glob("task-*.md"))) == 1

    with TemporaryDirectory(prefix="jarvis-create-local-task-limit-") as limit_dir:
        tasks_dir = Path(limit_dir)
        (tasks_dir / "task-9999-limit.md").write_text("fixture\n", encoding="utf-8")
        limit_result = run_web_app.preview_task_file_write(
            {
                "title": "next-task",
                "status": "TODO",
                "repo": "jarvis-core",
                "summary": "Must fail beyond the four-digit task ID boundary.",
                "source_command": "Voice Inbox",
            },
            tasks_dir=tasks_dir,
        )
        assert limit_result.result_type == "error"
        assert limit_result.reason == "task_number_limit_reached"

    valid_headers = [
        ("Host", "127.0.0.1:43210"),
        ("Origin", "http://127.0.0.1:43210"),
        ("Content-Type", "application/json"),
        ("Content-Length", "2"),
    ]
    metadata_status, metadata = run_web_app.validate_create_local_task_http_request(
        path=run_web_app.CREATE_LOCAL_TASK_PREVIEW_ENDPOINT,
        query="",
        header_pairs=valid_headers,
        bound_port=43210,
    )
    assert metadata_status == HTTPStatus.OK
    assert metadata["body_length"] == 2
    duplicate_header_status, _ = run_web_app.validate_create_local_task_http_request(
        path=run_web_app.CREATE_LOCAL_TASK_PREVIEW_ENDPOINT,
        query="",
        header_pairs=[*valid_headers, ("Host", "127.0.0.1:43210")],
        bound_port=43210,
    )
    assert duplicate_header_status == HTTPStatus.BAD_REQUEST
    transfer_status, _ = run_web_app.validate_create_local_task_http_request(
        path=run_web_app.CREATE_LOCAL_TASK_PREVIEW_ENDPOINT,
        query="",
        header_pairs=[*valid_headers, ("Transfer-Encoding", "chunked")],
        bound_port=43210,
    )
    assert transfer_status == HTTPStatus.BAD_REQUEST
    query_status, _ = run_web_app.validate_create_local_task_http_request(
        path=run_web_app.CREATE_LOCAL_TASK_PREVIEW_ENDPOINT,
        query="unexpected=1",
        header_pairs=valid_headers,
        bound_port=43210,
    )
    assert query_status == HTTPStatus.NOT_FOUND
    assert run_web_app.parse_create_local_task_json_body(
        b'{"transcript":"one","transcript":"two"}'
    )[0] == HTTPStatus.BAD_REQUEST

    with TemporaryDirectory(prefix="jarvis-create-local-task-http-") as http_dir:
        tasks_dir = Path(http_dir) / "tasks"
        tasks_dir.mkdir()
        registry = run_web_app.CreateLocalTaskRegistry(
            token_factory=TokenFactory(),
            ttl_seconds=60,
            capacity=8,
        )
        server = run_web_app.ThreadingHTTPServer(
            (run_web_app.DEFAULT_HOST, 0),
            run_web_app.JarvisConsoleHandler,
        )
        server.create_local_task_registry = registry
        server.create_local_tasks_dir = tasks_dir
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        port = int(server.server_address[1])

        def post_json(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
            connection = HTTPConnection(run_web_app.DEFAULT_HOST, port, timeout=5)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            connection.request(
                "POST",
                path,
                body=body,
                headers={
                    "Origin": f"http://{run_web_app.DEFAULT_HOST}:{port}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            response_payload = json.loads(response.read().decode("utf-8"))
            status = response.status
            connection.close()
            return status, response_payload

        try:
            truncated_body = b'{"transcript":"truncated request"}'
            declared_length = len(truncated_body) + 7
            raw_request = (
                f"POST {run_web_app.CREATE_LOCAL_TASK_PREVIEW_ENDPOINT} HTTP/1.1\r\n"
                f"Host: {run_web_app.DEFAULT_HOST}:{port}\r\n"
                f"Origin: http://{run_web_app.DEFAULT_HOST}:{port}\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {declared_length}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode("ascii") + truncated_body
            with socket.create_connection(
                (run_web_app.DEFAULT_HOST, port),
                timeout=5,
            ) as truncated_socket:
                truncated_socket.sendall(raw_request)
                truncated_socket.shutdown(socket.SHUT_WR)
                response_chunks: list[bytes] = []
                while True:
                    chunk = truncated_socket.recv(4096)
                    if not chunk:
                        break
                    response_chunks.append(chunk)
            truncated_response = b"".join(response_chunks)
            assert b" 400 " in truncated_response.split(b"\r\n", 1)[0]
            assert b"create_local_task_body_length_mismatch" in truncated_response
            assert not list(tasks_dir.iterdir())

            route_preview_status, route_preview = post_json(
                run_web_app.CREATE_LOCAL_TASK_PREVIEW_ENDPOINT,
                {"transcript": "HTTP 경로 작업 생성"},
            )
            assert route_preview_status == HTTPStatus.OK
            route_confirm_status, route_confirm = post_json(
                run_web_app.CREATE_LOCAL_TASK_CONFIRM_ENDPOINT,
                {
                    "token": route_preview["token"],
                    "confirmation": run_web_app.CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
                },
            )
            assert route_confirm_status == HTTPStatus.OK
            assert route_confirm["receipt"]["status"] == "TODO"
            route_duplicate_status, route_duplicate = post_json(
                run_web_app.CREATE_LOCAL_TASK_CONFIRM_ENDPOINT,
                {
                    "token": route_preview["token"],
                    "confirmation": run_web_app.CREATE_LOCAL_TASK_CONFIRMATION_LITERAL,
                },
            )
            assert route_duplicate_status == HTTPStatus.OK
            assert route_duplicate["result_type"] == "already_created"
            assert len(list(tasks_dir.glob("task-*.md"))) == 1
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
        assert not server_thread.is_alive()


def _test_project_control_snapshot() -> None:
    with TemporaryDirectory(prefix="jarvis-project-control-") as temp_dir:
        root = Path(temp_dir)
        docs = root / "docs"
        docs.mkdir()
        plan = docs / "master-plan.md"
        baseline = """# Fixture Master Plan

## 2. 현재 기준점

- Last verified: 2026-07-22
- Verified implementation HEAD: `0123456789abcdef`
- Branch: `main`
- Known protected untracked file: `jarvis.bat`
- Current goal: Develop Jarvis-Core as a local-first human-approved assistant
- Manager reporting milestone ID: `manager-reporting-v0.1`
- Manager reporting status: `in_progress`
- Manager reporting next package ID: `manager-reporting-v0.1c`
- Current workstream: Prompt Queue / Project Control Panel
- Current milestone: Read-only owner project card
- Recommended next step: Verify the local vertical slice
- Next user-visible milestone: One trusted project card in Jarvis Console
- Current reason: Make internal progress understandable without reading every document
- Owner outcome: See current status and the next decision in one place
- Recent completed: Project Control v0.1D design
- Approval state: none
- Approval note: No approval is needed for the bounded read-only slice
- Owner decision status: selection_required
- Owner decision recommendation: hermes-manager

### Manager Reporting Workflow v0.1 package evidence

| Work package | Result type | Summary | Commit |
| --- | --- | --- | --- |
| manager-reporting-v0.1a | implementation | Reporting contracts completed | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |

## 3. Later

## 5. 작업 축별 상태

| 작업 축 | 현재 상태 | 사용자에게 보이는 기능 | 다음 안전 단계 |
| --- | --- | --- | --- |
| Hermes Manager | copy-only handoff verified | prompt drafting | repeated local use |
| Memory / Skills | keep locked | write-free preview | remain locked |
| Jarvis Console | v0.1D design complete | owner project card | implement read-only slice |
| Research Council | local report app | idea and risk review | usage feedback |
| Daily AI Radar | curated local scout | local radar report | keep manual sources |
| Task / Discord / Dashboard | workflow foundation | task dashboard | bounded maintenance |
"""
        plan.write_text(baseline, encoding="utf-8")
        first = run_web_app.read_master_plan_snapshot(plan, root)
        second = run_web_app.read_master_plan_snapshot(plan, root)
        assert first == second
        assert first == {
            "last_verified": "2026-07-22",
            "verified_implementation_head": "0123456789abcdef",
            "branch": "main",
            "known_protected_untracked_file": "jarvis.bat",
            "current_goal": "Develop Jarvis-Core as a local-first human-approved assistant",
            "manager_reporting_milestone_id": "manager-reporting-v0.1",
            "manager_reporting_status": "in_progress",
            "manager_reporting_next_package_id": "manager-reporting-v0.1c",
            "current_workstream": "Prompt Queue / Project Control Panel",
            "current_milestone": "Read-only owner project card",
            "recommended_next_step": "Verify the local vertical slice",
            "next_user_visible_milestone": "One trusted project card in Jarvis Console",
            "current_reason": "Make internal progress understandable without reading every document",
            "owner_outcome": "See current status and the next decision in one place",
            "recent_completed": "Project Control v0.1D design",
            "approval_state": "none",
            "approval_note": "No approval is needed for the bounded read-only slice",
            "owner_decision_status": "selection_required",
            "owner_decision_recommended_workstream_id": "hermes-manager",
            "manager_reporting_work_packages": [
                {
                    "work_package_id": "manager-reporting-v0.1a",
                    "result_type": "implementation",
                    "summary": "Reporting contracts completed",
                    "commit_hash": "a" * 40,
                }
            ],
            "workstreams": [
                {
                    "workstream_id": "hermes-manager",
                    "display_name": "Hermes Manager",
                    "status_summary": "copy-only handoff verified",
                    "user_visible_capability": "prompt drafting",
                    "next_safe_step": "repeated local use",
                    "read_only": True,
                },
                {
                    "workstream_id": "memory-skills",
                    "display_name": "Memory / Skills",
                    "status_summary": "keep locked",
                    "user_visible_capability": "write-free preview",
                    "next_safe_step": "remain locked",
                    "read_only": True,
                },
                {
                    "workstream_id": "jarvis-console",
                    "display_name": "Jarvis Console",
                    "status_summary": "v0.1D design complete",
                    "user_visible_capability": "owner project card",
                    "next_safe_step": "implement read-only slice",
                    "read_only": True,
                },
                {
                    "workstream_id": "research-council",
                    "display_name": "Research Council",
                    "status_summary": "local report app",
                    "user_visible_capability": "idea and risk review",
                    "next_safe_step": "usage feedback",
                    "read_only": True,
                },
                {
                    "workstream_id": "daily-ai-radar",
                    "display_name": "Daily AI Radar",
                    "status_summary": "curated local scout",
                    "user_visible_capability": "local radar report",
                    "next_safe_step": "keep manual sources",
                    "read_only": True,
                },
                {
                    "workstream_id": "task-discord-dashboard",
                    "display_name": "Task / Discord / Dashboard",
                    "status_summary": "workflow foundation",
                    "user_visible_capability": "task dashboard",
                    "next_safe_step": "bounded maintenance",
                    "read_only": True,
                },
            ],
            "source": "docs/master-plan.md",
        }

        owner_decision = build_owner_decision_from_snapshot(first)
        assert owner_decision.contract_type == CONTRACT_TYPE
        assert owner_decision.version == OWNER_DECISION_VERSION
        assert owner_decision.status == "selection_required"
        assert owner_decision.recommended_workstream_id == "hermes-manager"
        assert owner_decision.selected_workstream_id is None
        assert len(owner_decision.candidates) == 6
        assert owner_decision.candidates[1].locked_capabilities == tuple(
            sorted(
                OWNER_DECISION_LOCKS["memory-skills"],
                key=lambda item: (item.casefold(), item),
            )
        )
        assert "owner project card" in owner_decision.candidates[2].current_capability
        first_serialized = serialize_owner_decision(owner_decision)
        assert first_serialized == serialize_owner_decision(
            build_owner_decision_from_snapshot(first)
        )

        def assert_decision_data_rejected(payload: object, message: str) -> None:
            try:
                build_owner_decision_from_snapshot(payload)  # type: ignore[arg-type]
            except OwnerDecisionDataError as exc:
                assert message in str(exc), str(exc)
            else:
                raise AssertionError(f"owner decision data should fail closed: {message}")

        assert_decision_data_rejected([], "must be an object")
        missing_workstreams = dict(first)
        missing_workstreams.pop("workstreams")
        assert_decision_data_rejected(missing_workstreams, "workstreams must be a list")
        incomplete_workstreams = dict(first)
        incomplete_workstreams["workstreams"] = first["workstreams"][:-1]
        assert_decision_data_rejected(incomplete_workstreams, "exact allowed workstreams")
        duplicate_workstreams = json.loads(json.dumps(first))
        duplicate_workstreams["workstreams"][1]["workstream_id"] = "hermes-manager"
        assert_decision_data_rejected(duplicate_workstreams, "duplicate workstream IDs")
        mismatched_display = json.loads(json.dumps(first))
        mismatched_display["workstreams"][0]["display_name"] = "Hermes"
        assert_decision_data_rejected(mismatched_display, "display name does not match")
        selected_without_selection_data = dict(first)
        selected_without_selection_data["owner_decision_status"] = "selected_for_proposal"
        assert_decision_data_rejected(selected_without_selection_data, "selected status requires")
        unknown_recommendation = dict(first)
        unknown_recommendation["owner_decision_recommended_workstream_id"] = "unknown"
        assert_decision_data_rejected(unknown_recommendation, "reference a candidate")

        adapter_source = Path(__file__).with_name("owner_decision_data.py").read_text(
            encoding="utf-8"
        )
        forbidden_adapter_patterns = (
            "pathlib",
            "subprocess",
            "requests",
            "urlopen",
            "http.server",
            "open(",
            ".read_text(",
            ".read_bytes(",
            ".write_text(",
            ".write_bytes(",
            "run_web_app",
        )
        assert all(pattern not in adapter_source for pattern in forbidden_adapter_patterns)

        duplicate = baseline.replace(
            "- Last verified: 2026-07-22",
            "- Last verified: 2026-07-22\n- Last verified: 2026-07-23",
        )
        plan.write_text(duplicate, encoding="utf-8")
        try:
            run_web_app.read_master_plan_snapshot(plan, root)
        except run_web_app.RegistryError as exc:
            assert "duplicated" in str(exc)
        else:
            raise AssertionError("duplicate master-plan fields must be rejected")

        plan.write_text(baseline.replace("- Branch: `main`\n", ""), encoding="utf-8")
        try:
            run_web_app.read_master_plan_snapshot(plan, root)
        except run_web_app.RegistryError as exc:
            assert "missing" in str(exc)
        else:
            raise AssertionError("missing master-plan fields must be rejected")

        invalid_cases = (
            (
                baseline.replace("- Approval state: none", "- Approval state: maybe"),
                "approval state",
            ),
            (
                baseline.replace(
                    "- Manager reporting status: `in_progress`",
                    "- Manager reporting status: `complete-ish`",
                ),
                "Manager Reporting status",
            ),
            (
                baseline.replace(
                    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "short-hash",
                    1,
                ),
                "Manager Reporting commit",
            ),
            (
                baseline.split(
                    "### Manager Reporting Workflow v0.1 package evidence",
                    1,
                )[0]
                + "\n## 3. Later\n"
                + baseline.split("## 3. Later\n", 1)[1],
                "Manager Reporting package section",
            ),
            (
                baseline.split("## 5. 작업 축별 상태", 1)[0],
                "workstream section",
            ),
            (
                baseline.replace("| Hermes Manager |", "| Unknown Workstream |", 1),
                "order or name",
            ),
            (
                baseline.replace("| Daily AI Radar |", "| Research Council |", 1),
                "duplicated",
            ),
            (
                baseline.replace("| Memory / Skills | keep locked |", "| Memory / Skills |  |", 1),
                "empty or too long",
            ),
            (
                baseline.replace("copy-only handoff verified", "x" * 501, 1),
                "empty or too long",
            ),
            (
                baseline.replace("copy-only handoff verified", "copy-only\x01handoff", 1),
                "control character",
            ),
            (
                baseline.replace(
                    "| Task / Discord / Dashboard | workflow foundation | task dashboard | bounded maintenance |\n",
                    "",
                    1,
                ),
                "missing or extra rows",
            ),
            (
                baseline.replace("| 작업 축 | 현재 상태 |", "| Project | 현재 상태 |", 1),
                "header",
            ),
        )
        for invalid_source, expected_error in invalid_cases:
            plan.write_text(invalid_source, encoding="utf-8")
            try:
                run_web_app.read_master_plan_snapshot(plan, root)
            except run_web_app.RegistryError as exc:
                assert expected_error in str(exc)
            else:
                raise AssertionError(f"invalid master plan must be rejected: {expected_error}")

        plan.write_bytes(b"x" * (run_web_app.MASTER_PLAN_MAX_BYTES + 1))
        try:
            run_web_app.read_master_plan_snapshot(plan, root)
        except run_web_app.RegistryError as exc:
            assert "exceeds" in str(exc)
        else:
            raise AssertionError("oversized master plans must be rejected")


def _test_project_control_reporting_state_invariants() -> None:
    no_conflict_manager = {
        "status": "in_progress",
        "owner_action": "none",
        "owner_decision": "",
        "source_conflicts": [],
    }
    no_conflict_director = {
        "status": "in_progress",
        "owner_action": "none",
        "owner_decision": "",
    }
    assert run_web_app.reconcile_project_control_reporting_state(
        [],
        no_conflict_manager,
        no_conflict_director,
    ) == ("observed", [])

    conflicts = [
        "Verified implementation HEAD is absent from live Git evidence",
        "Checkpoint package commit is absent from Git evidence",
    ]
    blocked_manager = {
        "status": "blocked",
        "owner_action": "decision_required",
        "owner_decision": "Resolve reporting source conflicts before continuing.",
        "source_conflicts": conflicts,
    }
    blocked_director = {
        "status": "blocked",
        "owner_action": "decision_required",
        "owner_decision": "Resolve reporting source conflicts before continuing.",
    }
    status, reasons = run_web_app.reconcile_project_control_reporting_state(
        ["Live branch differs from the Master Plan."],
        blocked_manager,
        blocked_director,
    )
    assert status == "attention"
    assert reasons == [
        "Live branch differs from the Master Plan.",
        *conflicts,
    ]

    approval_manager = {
        "status": "in_progress",
        "owner_action": "decision_required",
        "owner_decision": "Owner approval is required.",
        "source_conflicts": [],
    }
    approval_director = {
        "status": "in_progress",
        "owner_action": "decision_required",
        "owner_decision": "Owner approval is required.",
    }
    assert run_web_app.reconcile_project_control_reporting_state(
        [],
        approval_manager,
        approval_director,
    ) == ("attention", ["Owner approval is required."])

    try:
        run_web_app.reconcile_project_control_reporting_state(
            [],
            blocked_manager,
            no_conflict_director,
        )
    except run_web_app.RegistryError as exc:
        assert "status disagree" in str(exc)
    else:
        raise AssertionError("reporting status disagreement must fail closed")

    mismatched_decision_director = dict(blocked_director)
    mismatched_decision_director["owner_decision"] = "Another decision."
    try:
        run_web_app.reconcile_project_control_reporting_state(
            [],
            blocked_manager,
            mismatched_decision_director,
        )
    except run_web_app.RegistryError as exc:
        assert "decision disagree" in str(exc)
    else:
        raise AssertionError("reporting decision disagreement must fail closed")

    empty_decision_manager = dict(blocked_manager)
    empty_decision_manager["owner_decision"] = ""
    empty_decision_director = dict(blocked_director)
    empty_decision_director["owner_decision"] = ""
    try:
        run_web_app.reconcile_project_control_reporting_state(
            [],
            empty_decision_manager,
            empty_decision_director,
        )
    except run_web_app.RegistryError as exc:
        assert "requires a decision" in str(exc)
    else:
        raise AssertionError("empty required reporting decision must fail closed")

    unexpected_decision_manager = dict(no_conflict_manager)
    unexpected_decision_manager["owner_decision"] = "Unexpected."
    unexpected_decision_director = dict(no_conflict_director)
    unexpected_decision_director["owner_decision"] = "Unexpected."
    try:
        run_web_app.reconcile_project_control_reporting_state(
            [],
            unexpected_decision_manager,
            unexpected_decision_director,
        )
    except run_web_app.RegistryError as exc:
        assert "requires empty decisions" in str(exc)
    else:
        raise AssertionError("no-action reporting decision must be empty")


def _project_registry_fixture() -> dict[str, Any]:
    return {
        "registry_type": REGISTRY_TYPE,
        "version": REGISTRY_VERSION,
        "projects": [
            {
                "project_id": "jarvis-core",
                "display_name": "Jarvis-Core",
                "trusted_root_key": "jarvis_core",
                "master_plan_path": "docs/master-plan.md",
                "expected_branch": "main",
                "protected_paths": ["jarvis.bat"],
                "expected_untracked": ["jarvis.bat"],
                "validation_command_ids": ["git_status_short", "git_diff_check"],
            },
            {
                "project_id": "care-note",
                "display_name": "CareNote",
                "trusted_root_key": "care_note",
                "master_plan_path": "docs/project-plan.md",
                "expected_branch": "feature/project-control-v1",
                "protected_paths": [],
                "expected_untracked": [],
                "validation_command_ids": ["git_status_short"],
            },
        ],
    }


def _test_read_only_git_preserves_porcelain_status() -> None:
    outputs = iter(
        (
            " M file\n",
            "?? file\n",
            " M file\r\n?? file\r\n",
            "",
            " M file\r\n",
            " M file\n",
        )
    )

    class FixtureResult:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fixture_run_process(*args: Any, **kwargs: Any) -> FixtureResult:
        return FixtureResult(next(outputs))

    original_run_process = run_web_app.run_process
    run_web_app.run_process = fixture_run_process
    try:
        assert run_web_app.run_read_only_git(("status", "--short")) == " M file"
        assert run_web_app.run_read_only_git(("status", "--short")) == "?? file"
        assert (
            run_web_app.run_read_only_git(("status", "--short"))
            == " M file\r\n?? file"
        )
        assert run_web_app.run_read_only_git(("status", "--short")) == ""
        assert run_web_app.run_read_only_git(("status", "--short")) == " M file"
        assert run_web_app.run_read_only_git(("status", "--short")) == " M file"
    finally:
        run_web_app.run_process = original_run_process


def _owner_decision_fixture() -> dict[str, Any]:
    return {
        "contract_type": CONTRACT_TYPE,
        "version": OWNER_DECISION_VERSION,
        "project_id": PROJECT_ID,
        "decision_kind": "workstream_selection",
        "status": "selection_required",
        "reason": (
            "Choose the next Jarvis-Core workstream without treating the choice "
            "as implementation authority."
        ),
        "authority_boundary": AUTHORITY_BOUNDARY,
        "recommended_workstream_id": "jarvis-console",
        "candidates": [
            {
                "workstream_id": "hermes-manager",
                "display_name": "Hermes Manager",
                "current_capability": "Copy-only prompt and review handoff",
                "next_user_outcome": "Reduce manual coordination friction",
                "locked_capabilities": [
                    "Automatic Codex or ChatGPT invocation",
                    "Push or pull request",
                ],
            },
            {
                "workstream_id": "memory-skills",
                "display_name": "Memory / Skills",
                "current_capability": "Write-free candidate preview",
                "next_user_outcome": "Review one bounded memory safety slice",
                "locked_capabilities": [
                    "Live candidate save",
                    "UI Save or Confirm",
                    "Voice Inbox auto-save",
                ],
            },
            {
                "workstream_id": "jarvis-console",
                "display_name": "Jarvis Console",
                "current_capability": "Single-repo read-only Owner Dashboard",
                "next_user_outcome": "Read one shared decision contract across renderers",
                "locked_capabilities": [
                    "Approval or execution action",
                    "Second repository connection",
                ],
            },
            {
                "workstream_id": "research-council",
                "display_name": "Research Council",
                "current_capability": "Deterministic local idea and risk report",
                "next_user_outcome": "Improve one real-use report workflow",
                "locked_capabilities": ["External research calls"],
            },
            {
                "workstream_id": "daily-ai-radar",
                "display_name": "Daily AI Radar",
                "current_capability": "Manually curated local radar report",
                "next_user_outcome": "Improve one local scouting workflow",
                "locked_capabilities": ["External source collection"],
            },
            {
                "workstream_id": "task-discord-dashboard",
                "display_name": "Task / Discord / Dashboard",
                "current_capability": "Task workflow and read-only dashboard",
                "next_user_outcome": "Improve one bounded owner task workflow",
                "locked_capabilities": [
                    "Remote execution",
                    "Unattended execution",
                ],
            },
        ],
        "selected_workstream_id": None,
        "desired_outcome": None,
        "response_template": RESPONSE_TEMPLATE,
        "read_only": True,
    }


def _test_owner_decision_contract() -> None:
    fixture = _owner_decision_fixture()
    first = normalize_owner_decision(fixture)
    second = normalize_owner_decision(fixture)
    assert first == second
    assert isinstance(first.candidates, tuple)
    assert all(isinstance(candidate.locked_capabilities, tuple) for candidate in first.candidates)
    assert [candidate.workstream_id for candidate in first.candidates] == [
        "hermes-manager",
        "memory-skills",
        "jarvis-console",
        "research-council",
        "daily-ai-radar",
        "task-discord-dashboard",
    ]
    try:
        first.status = "selected_for_proposal"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("OwnerDecision must be immutable")
    try:
        first.candidates[0].display_name = "Changed"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("OwnerDecisionCandidate must be immutable")

    canonical = serialize_owner_decision(first)
    assert canonical == serialize_owner_decision(second)
    assert parse_owner_decision_json(canonical) == first
    assert owner_decision_to_dict(first) == json.loads(canonical)
    assert " " not in canonical[: canonical.index('"authority_boundary"')]

    reordered = json.loads(json.dumps(fixture))
    reordered["candidates"].reverse()
    for candidate in reordered["candidates"]:
        candidate["locked_capabilities"].reverse()
    assert serialize_owner_decision(normalize_owner_decision(reordered)) == canonical

    before_render = serialize_owner_decision(first)
    markdown = render_owner_decision_markdown(first)
    assert markdown.startswith("# Owner Decision\n")
    assert "## Workstream Candidates" in markdown
    assert "### 3. Jarvis Console" in markdown
    assert RESPONSE_TEMPLATE in markdown
    assert "bounded work-package proposal only" in markdown
    assert "`work_package_proposal_only`" in markdown
    assert markdown.endswith("\n")
    assert serialize_owner_decision(first) == before_render

    escaped_fixture = json.loads(json.dumps(fixture))
    escaped_fixture["candidates"][0]["current_capability"] = (
        "Draft *prompts* without <script> execution"
    )
    escaped = render_owner_decision_markdown(
        normalize_owner_decision(escaped_fixture)
    )
    assert r"\*prompts\*" in escaped
    assert r"\<script\>" in escaped

    selected_fixture = json.loads(json.dumps(fixture))
    selected_fixture.update(
        {
            "status": "selected_for_proposal",
            "selected_workstream_id": "jarvis-console",
            "desired_outcome": "Show one transport-neutral read-only decision",
        }
    )
    selected = normalize_owner_decision(selected_fixture)
    assert selected.selected_workstream_id == "jarvis-console"
    assert "Show one transport-neutral" in render_owner_decision_markdown(selected)

    superseded_fixture = json.loads(json.dumps(selected_fixture))
    superseded_fixture["status"] = "superseded"
    assert normalize_owner_decision(superseded_fixture).status == "superseded"
    rejected_fixture = json.loads(json.dumps(fixture))
    rejected_fixture["status"] = "selection_rejected"
    assert normalize_owner_decision(rejected_fixture).status == "selection_rejected"

    def assert_rejected(payload: object, message: str) -> None:
        try:
            normalize_owner_decision(payload)  # type: ignore[arg-type]
        except OwnerDecisionError as exc:
            assert message in str(exc), str(exc)
        else:
            raise AssertionError(f"Owner Decision input should fail closed: {message}")

    assert_rejected([], "must be an object")
    assert_rejected({**fixture, "unknown": True}, "unknown fields")
    assert_rejected({**fixture, "contract_type": "other"}, "contract_type must be")
    assert_rejected({**fixture, "version": "0.1B"}, "version must be")
    assert_rejected({**fixture, "project_id": "other"}, "project_id must be")
    assert_rejected({**fixture, "decision_kind": "implementation"}, "decision_kind must be")
    assert_rejected({**fixture, "status": "approved"}, "status is not supported")
    assert_rejected({**fixture, "reason": "Unsafe\nreason"}, "control character")
    assert_rejected({**fixture, "reason": "x" * 501}, "too long")
    assert_rejected({**fixture, "authority_boundary": "execute"}, "authority_boundary must be")
    assert_rejected({**fixture, "recommended_workstream_id": "unknown"}, "reference a candidate")
    assert_rejected({**fixture, "read_only": False}, "read_only must be true")
    assert_rejected({**fixture, "response_template": "Approve"}, "not the v0.1A template")
    assert_rejected({**fixture, "candidates": fixture["candidates"][:-1]}, "all six")

    duplicate_candidate = json.loads(json.dumps(fixture))
    duplicate_candidate["candidates"][1] = json.loads(
        json.dumps(duplicate_candidate["candidates"][0])
    )
    assert_rejected(duplicate_candidate, "duplicate workstream IDs")
    unknown_candidate = json.loads(json.dumps(fixture))
    unknown_candidate["candidates"][0]["workstream_id"] = "unknown"
    assert_rejected(unknown_candidate, "is not allowed")
    mismatched_name = json.loads(json.dumps(fixture))
    mismatched_name["candidates"][0]["display_name"] = "Memory / Skills"
    assert_rejected(mismatched_name, "does not match")
    unknown_candidate_field = json.loads(json.dumps(fixture))
    unknown_candidate_field["candidates"][0]["route"] = "/api/decision"
    assert_rejected(unknown_candidate_field, "unknown fields")
    duplicate_locks = json.loads(json.dumps(fixture))
    duplicate_locks["candidates"][0]["locked_capabilities"] = ["Push", "push"]
    assert_rejected(duplicate_locks, "duplicate values")

    unselected_with_choice = json.loads(json.dumps(fixture))
    unselected_with_choice["selected_workstream_id"] = "jarvis-console"
    unselected_with_choice["desired_outcome"] = "Unexpected implied selection"
    assert_rejected(unselected_with_choice, "unselected status")
    selected_without_choice = json.loads(json.dumps(fixture))
    selected_without_choice["status"] = "selected_for_proposal"
    assert_rejected(selected_without_choice, "selected status requires")
    selected_unknown = json.loads(json.dumps(selected_fixture))
    selected_unknown["selected_workstream_id"] = "unknown"
    assert_rejected(selected_unknown, "selected status requires")

    noncanonical = replace(first, candidates=tuple(reversed(first.candidates)))
    try:
        serialize_owner_decision(noncanonical)
    except OwnerDecisionError as exc:
        assert "not canonically normalized" in str(exc)
    else:
        raise AssertionError("noncanonical contract instance must fail closed")

    duplicate_json = canonical.replace(
        '"version":"0.1A"',
        '"version":"0.1A","version":"0.1A"',
        1,
    )
    try:
        parse_owner_decision_json(duplicate_json)
    except OwnerDecisionError as exc:
        assert "duplicate key" in str(exc)
    else:
        raise AssertionError("duplicate JSON keys must fail closed")
    try:
        parse_owner_decision_json(canonical.replace('"read_only":true', '"read_only":NaN'))
    except OwnerDecisionError as exc:
        assert "non-finite" in str(exc)
    else:
        raise AssertionError("non-finite JSON values must fail closed")
    try:
        parse_owner_decision_json("x" * (MAX_JSON_BYTES + 1))
    except OwnerDecisionError as exc:
        assert "exceeds the input limit" in str(exc)
    else:
        raise AssertionError("oversized JSON must fail closed")

    markdown_stdout = StringIO()
    markdown_stderr = StringIO()
    assert render_owner_decision.run_cli(
        ["--format", "markdown"],
        stdin=StringIO(canonical),
        stdout=markdown_stdout,
        stderr=markdown_stderr,
    ) == 0
    assert markdown_stdout.getvalue() == markdown
    assert markdown_stderr.getvalue() == ""

    json_stdout = StringIO()
    json_stderr = StringIO()
    assert render_owner_decision.run_cli(
        ["--format", "json"],
        stdin=StringIO(canonical),
        stdout=json_stdout,
        stderr=json_stderr,
    ) == 0
    assert json_stdout.getvalue() == canonical + "\n"
    assert json_stderr.getvalue() == ""

    invalid_stdout = StringIO()
    invalid_stderr = StringIO()
    assert render_owner_decision.run_cli(
        [],
        stdin=StringIO("{}"),
        stdout=invalid_stdout,
        stderr=invalid_stderr,
    ) == 2
    assert invalid_stdout.getvalue() == ""
    assert invalid_stderr.getvalue().startswith("Owner Decision error:")

    module_source = Path(__file__).with_name("owner_decision.py").read_text(encoding="utf-8")
    cli_source = Path(__file__).with_name("render_owner_decision.py").read_text(encoding="utf-8")
    forbidden_core_patterns = (
        "pathlib",
        "subprocess",
        "requests",
        "urlopen",
        "http.server",
        "open(",
        ".read_text(",
        ".read_bytes(",
        ".write_text(",
        ".write_bytes(",
        "socket",
    )
    forbidden_cli_patterns = forbidden_core_patterns + ("run_web_app",)
    assert all(pattern not in module_source for pattern in forbidden_core_patterns)
    assert all(pattern not in cli_source for pattern in forbidden_cli_patterns)


def _test_project_control_registry_primitives() -> None:
    roots = {"jarvis_core", "care_note"}
    commands = {"git_status_short", "git_diff_check"}
    fixture = _project_registry_fixture()
    first = normalize_project_registry(
        fixture,
        trusted_root_keys=roots,
        validation_command_ids=commands,
    )
    second = normalize_project_registry(
        fixture,
        trusted_root_keys=roots,
        validation_command_ids=commands,
    )
    assert first == second
    assert [project.project_id for project in first.projects] == ["jarvis-core", "care-note"]
    assert first.projects[0].protected_paths == ("jarvis.bat",)
    assert first.projects[1].expected_branch == "feature/project-control-v1"
    assert "repo_path" not in json.dumps(fixture, ensure_ascii=False, sort_keys=True)
    accepted = evaluate_project_registry(
        fixture,
        trusted_root_keys=roots,
        validation_command_ids=commands,
    )
    assert accepted.is_blocked is False
    assert accepted.registry == first
    assert accepted.blocking_reasons == ()

    def assert_rejected(payload: object, message: str) -> None:
        decision = evaluate_project_registry(
            payload,  # type: ignore[arg-type]
            trusted_root_keys=roots,
            validation_command_ids=commands,
        )
        assert decision.is_blocked is True
        assert decision.registry is None
        assert len(decision.blocking_reasons) == 1
        assert message in decision.blocking_reasons[0]

    assert_rejected([], "must be an object")
    unknown_envelope = json.loads(json.dumps(fixture))
    unknown_envelope["repo_path"] = "C:/work/other"
    assert_rejected(unknown_envelope, "unknown fields")
    wrong_version = json.loads(json.dumps(fixture))
    wrong_version["version"] = "0.1C"
    assert_rejected(wrong_version, "version must be")
    assert_rejected({**fixture, "projects": []}, "between 1 and")
    assert_rejected(
        {**fixture, "projects": [fixture["projects"][0]] * (MAX_PROJECTS + 1)},
        "between 1 and",
    )

    invalid_cases = (
        ("project_id", "Jarvis-Core", "normalized lowercase ID"),
        ("trusted_root_key", "unknown_root", "not server-trusted"),
        ("master_plan_path", "../master-plan.md", "unsafe path component"),
        ("master_plan_path", "C:/work/master-plan.md", "repo-relative"),
        ("master_plan_path", "docs\\master-plan.md", "normalized POSIX"),
        ("master_plan_path", "docs/plan:stream.md", "non-portable path component"),
        ("master_plan_path", "docs/plan?.md", "non-portable path component"),
        ("master_plan_path", "docs/NUL.md", "non-portable path component"),
        ("master_plan_path", "docs/plan./master.md", "non-portable path component"),
        ("master_plan_path", ".private/master-plan.md", "non-hidden Markdown"),
        ("master_plan_path", "docs/master-plan.txt", "non-hidden Markdown"),
        ("expected_branch", "feature//unsafe", "bounded branch name"),
        ("display_name", "Unsafe\nName", "control character"),
    )
    for field, value, message in invalid_cases:
        payload = json.loads(json.dumps(fixture))
        payload["projects"][0][field] = value
        assert_rejected(payload, message)

    duplicate_projects = json.loads(json.dumps(fixture))
    duplicate_projects["projects"][1]["project_id"] = "jarvis-core"
    assert_rejected(duplicate_projects, "project_id contains duplicate")
    duplicate_paths = json.loads(json.dumps(fixture))
    duplicate_paths["projects"][0]["protected_paths"] = ["Jarvis.bat", "jarvis.bat"]
    assert_rejected(duplicate_paths, "contains duplicate values")
    duplicate_commands = json.loads(json.dumps(fixture))
    duplicate_commands["projects"][0]["validation_command_ids"] = [
        "git_status_short",
        "git_status_short",
    ]
    assert_rejected(duplicate_commands, "contains duplicate values")
    unknown_command = json.loads(json.dumps(fixture))
    unknown_command["projects"][0]["validation_command_ids"] = ["git_commit"]
    assert_rejected(unknown_command, "unknown command ID")
    empty_commands = json.loads(json.dumps(fixture))
    empty_commands["projects"][0]["validation_command_ids"] = []
    assert_rejected(empty_commands, "must not be empty")

    try:
        normalize_project_registry(
            fixture,
            trusted_root_keys=[],
            validation_command_ids=commands,
        )
    except ProjectRegistryError as exc:
        assert "trusted_root_keys must not be empty" in str(exc)
    else:
        raise AssertionError("empty server root authority must be rejected")

    source = Path(__file__).with_name("project_control_registry.py").read_text(encoding="utf-8")
    forbidden_source_patterns = (
        "subprocess",
        "requests",
        "urlopen",
        ".read_text(",
        ".read_bytes(",
        ".write_text(",
        ".write_bytes(",
        "open(",
        "http.server",
    )
    assert all(pattern not in source for pattern in forbidden_source_patterns)


def _test_recent_milestone_evidence_contract() -> None:
    head = "a" * 40
    older = "b" * 40
    raw_log = (
        f"{RECORD_SEPARATOR}{head}{FIELD_SEPARATOR}jarvis-console: show recent milestone evidence\n\n"
        "apps/jarvis-console/recent_milestone_evidence.py\n"
        "apps/jarvis-console/run_web_app.py\n"
        f"{RECORD_SEPARATOR}{older}{FIELD_SEPARATOR}docs: record prior milestone\n\n"
        "docs/master-plan.md\n"
    )
    first = parse_recent_milestone_log(raw_log, head)
    second = parse_recent_milestone_log(raw_log, head)
    assert first == second
    assert first.contract_type == RECENT_MILESTONE_CONTRACT_TYPE
    assert first.version == RECENT_MILESTONE_VERSION
    assert first.repository_id == "jarvis-core"
    assert first.observed_head == head
    assert first.head_matches_latest_commit is True
    assert first.read_only is True
    assert len(first.commits) == 2
    assert first.commits[0].is_head is True
    assert first.commits[0].short_hash == "aaaaaaa"
    assert first.commits[0].changed_file_count == 2
    assert first.commits[0].changed_files == (
        "apps/jarvis-console/recent_milestone_evidence.py",
        "apps/jarvis-console/run_web_app.py",
    )
    assert first.commits[1].is_head is False
    assert first.commits[1].protected_path_present is False
    assert serialize_recent_milestone_evidence(first) == serialize_recent_milestone_evidence(second)
    serialized = recent_milestone_evidence_to_dict(first)
    assert serialized["head_matches_latest_commit"] is True
    assert serialized["commits"][0]["read_only"] is True

    try:
        first.observed_head = older  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("recent milestone evidence must be immutable")

    stale = parse_recent_milestone_log(raw_log, "c" * 40)
    assert stale.head_matches_latest_commit is False
    assert all(commit.is_head is False for commit in stale.commits)

    many_paths = "\n".join(f"docs/file-{index:02d}.md" for index in range(MAX_FILES_PER_COMMIT + 1))
    truncated = parse_recent_milestone_log(
        f"{RECORD_SEPARATOR}{head}{FIELD_SEPARATOR}bounded files\n\n{many_paths}\n",
        head,
    )
    assert truncated.commits[0].changed_file_count == MAX_FILES_PER_COMMIT + 1
    assert len(truncated.commits[0].changed_files) == MAX_FILES_PER_COMMIT
    assert truncated.commits[0].files_truncated is True

    protected = parse_recent_milestone_log(
        f"{RECORD_SEPARATOR}{head}{FIELD_SEPARATOR}protected fixture\n\njarvis.bat\n",
        head,
    )
    assert protected.commits[0].protected_path_present is True

    rejected = (
        (f"unexpected{RECORD_SEPARATOR}{head}{FIELD_SEPARATOR}subject\n", "before its first record"),
        (f"{RECORD_SEPARATOR}not-a-hash{FIELD_SEPARATOR}subject\n", "full lowercase Git hash"),
        (f"{RECORD_SEPARATOR}{head} subject\n", "header is malformed"),
        (f"{RECORD_SEPARATOR}{head}{FIELD_SEPARATOR}subject\n\n../outside.txt\n", "repository-relative"),
        (
            f"{RECORD_SEPARATOR}{head}{FIELD_SEPARATOR}one\n"
            f"{RECORD_SEPARATOR}{head}{FIELD_SEPARATOR}two\n",
            "duplicate commit",
        ),
        (
            "".join(
                f"{RECORD_SEPARATOR}{index + 1:040x}{FIELD_SEPARATOR}commit {index}\n"
                for index in range(RECENT_MILESTONE_MAX_COMMITS + 1)
            ),
            "too many commits",
        ),
        ("x" * (MAX_RAW_LOG_BYTES + 1), "exceeds the display limit"),
    )
    for payload, message in rejected:
        try:
            parse_recent_milestone_log(payload, head)
        except RecentMilestoneEvidenceError as exc:
            assert message in str(exc), str(exc)
        else:
            raise AssertionError(f"recent milestone evidence should fail closed: {message}")

    source = Path(__file__).with_name("recent_milestone_evidence.py").read_text(encoding="utf-8")
    forbidden_source_patterns = (
        "subprocess",
        "requests",
        "urlopen",
        ".read_text(",
        ".read_bytes(",
        ".write_text(",
        ".write_bytes(",
        "open(",
        "http.server",
    )
    assert all(pattern not in source for pattern in forbidden_source_patterns)


def _test_director_renderer_fails_closed_on_malformed_nested_data() -> None:
    app_js = Path(__file__).resolve().parent.joinpath("web", "app.js").read_text(
        encoding="utf-8"
    )
    escape_source = "function escapeHtml" + app_js.split(
        "function escapeHtml",
        1,
    )[1].split("function truncateText", 1)[0]
    director_source = "function renderDirectorReport" + app_js.split(
        "function renderDirectorReport",
        1,
    )[1].split("function renderManagerReport", 1)[0]
    valid = {
        "contract_type": DIRECTOR_CONTRACT_TYPE,
        "version": DIRECTOR_VERSION,
        "source_contract_type": MANAGER_CONTRACT_TYPE,
        "derived_view": True,
        "read_only": True,
        "authority_boundary": DIRECTOR_AUTHORITY_BOUNDARY,
        "milestone_id": "manager-reporting-v0.1",
        "milestone_summary": "Summarize the verified Manager result for the Owner.",
        "status": "in_progress",
        "owner_outcome": "The Owner sees one bounded Director Summary.",
        "completed_packages": [
            {
                "work_package_id": "manager-reporting-v0.1a",
                "result_type": "implementation",
                "summary": "Reporting contract completed.",
                "commit_hash": "a" * 40,
            }
        ],
        "risk_summary": [
            {"severity": "low", "summary": "Manual handoff remains required."}
        ],
        "owner_action": "none",
        "owner_decision": "",
        "next_recommendation": {
            "work_package_id": "manager-reporting-v0.1c",
            "summary": "Verify the Director projection.",
            "user_value": "The Owner gets a concise read-only summary.",
        },
    }
    malformed: list[dict[str, Any]] = []
    for field, value in (
        ("completed_packages", [None]),
        ("completed_packages", [7]),
        ("risk_summary", [None]),
        ("risk_summary", ["low"]),
        ("next_recommendation", []),
    ):
        item = json.loads(json.dumps(valid))
        item[field] = value
        malformed.append(item)
    missing_nested = json.loads(json.dumps(valid))
    missing_nested["completed_packages"][0].pop("commit_hash")
    malformed.append(missing_nested)
    wrong_nested_type = json.loads(json.dumps(valid))
    wrong_nested_type["completed_packages"][0]["summary"] = 7
    malformed.append(wrong_nested_type)
    missing_risk_field = json.loads(json.dumps(valid))
    missing_risk_field["risk_summary"][0].pop("summary")
    malformed.append(missing_risk_field)
    inconsistent_owner = json.loads(json.dumps(valid))
    inconsistent_owner.update({"status": "blocked", "owner_action": "none"})
    malformed.append(inconsistent_owner)

    harness = (
        f"{escape_source}\n{director_source}\n"
        f"const valid = {json.dumps(valid, ensure_ascii=False)};\n"
        f"const malformed = {json.dumps(malformed, ensure_ascii=False)};\n"
        """
const validHtml = renderDirectorReport(valid);
if (!validHtml.includes('aria-label="Director Summary"') ||
    validHtml.includes('Unavailable')) {
  throw new Error("valid Director payload did not render");
}
for (const [index, payload] of malformed.entries()) {
  let html;
  try {
    html = renderDirectorReport(payload);
  } catch (error) {
    throw new Error(`malformed payload ${index} threw: ${error}`);
  }
  if (!html.includes("Unavailable")) {
    throw new Error(`malformed payload ${index} did not fail closed`);
  }
}
"""
    )
    completed = subprocess.run(
        ("node", "-"),
        cwd=Path(__file__).resolve().parent,
        input=harness,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, (
        "Director renderer harness failed: "
        f"{completed.stdout}\n{completed.stderr}"
    )


def _test_task_transition_vertical_slice() -> None:
    fixture_root = run_web_app.REPO_ROOT / "task-transition-test-fixture"
    resolved_fixture = fixture_root.resolve()
    resolved_workspace = Path("C:/work").resolve()
    assert resolved_fixture.parent == run_web_app.REPO_ROOT.resolve()
    assert resolved_fixture.is_relative_to(resolved_workspace)
    assert not fixture_root.exists()

    watched_roots = (
        run_web_app.REPO_ROOT / "memory" / "tasks",
        run_web_app.REPO_ROOT / "reports",
    )

    def artifact_snapshot() -> tuple[tuple[str, int, int], ...]:
        snapshot: list[tuple[str, int, int]] = []
        for root in watched_roots:
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    stat_result = path.stat()
                    snapshot.append(
                        (
                            path.relative_to(run_web_app.REPO_ROOT).as_posix(),
                            stat_result.st_size,
                            stat_result.st_mtime_ns,
                        )
                    )
        return tuple(snapshot)

    before_artifacts = artifact_snapshot()
    fixture_root.mkdir()
    tasks_dir = fixture_root / "tasks"
    tasks_dir.mkdir()

    def task_bytes(
        task_id: str,
        status: str,
        *,
        title: str = "Fixture Task",
        summary: str = "Fixture summary",
        updated_at: str = "2026-07-23 10:00 UTC",
        newline: str = "\r\n",
        extra_lines: tuple[str, ...] = (),
    ) -> bytes:
        return (
            newline.join(
                [
                    f"# {task_id}",
                    "",
                    f"- id: `{task_id}`",
                    f"- title: `{title}`",
                    f"- status: `{status}`",
                    "- repo: `jarvis-core`",
                    "- created_at: `2026-07-23 09:00 UTC`",
                    f"- updated_at: `{updated_at}`",
                    f"- summary: `{summary}`",
                    *extra_lines,
                ]
            )
            + newline
        ).encode("utf-8")

    def write_task(
        task_id: str,
        status: str,
        **kwargs: Any,
    ) -> tuple[Path, bytes]:
        path = tasks_dir / f"{task_id}.md"
        raw = task_bytes(task_id, status, **kwargs)
        path.write_bytes(raw)
        return path, raw

    class TokenFactory:
        def __init__(self, prefix: str = "tasktransitiontoken") -> None:
            self.prefix = prefix
            self.counter = 0

        def __call__(self) -> str:
            self.counter += 1
            return f"{self.prefix}{self.counter:016d}"

    class FakeClock:
        def __init__(self) -> None:
            self.value = 1000.0

        def __call__(self) -> float:
            return self.value

    class FailingBinaryFile:
        def __init__(self, path: Path, stage: str) -> None:
            self.file = path.open("xb")
            self.stage = stage

        @property
        def closed(self) -> bool:
            return self.file.closed

        def write(self, data: bytes) -> int:
            if self.stage == "write":
                raise OSError("injected write failure")
            return self.file.write(data)

        def flush(self) -> None:
            if self.stage == "flush":
                raise OSError("injected flush failure")
            self.file.flush()

        def fileno(self) -> int:
            return self.file.fileno()

        def close(self) -> None:
            self.file.close()
            if self.stage == "close":
                raise OSError("injected close failure")

    try:
        writer_path, writer_before = write_task("task-7001-writer", "TODO")
        planned_start = "2026-07-23 10:30 UTC"
        start_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id="task-7001-writer",
            expected_digest=hashlib.sha256(writer_before).hexdigest(),
            current_status="TODO",
            target_status="DOING",
            planned_updated_at=planned_start,
            _temp_token_factory=lambda: "a" * 16,
        )
        assert start_result.result_type == "updated"
        start_bytes = writer_path.read_bytes()
        assert start_bytes == writer_before.replace(
            b"- status: `TODO`",
            b"- status: `DOING`",
            1,
        ).replace(
            b"- updated_at: `2026-07-23 10:00 UTC`",
            b"- updated_at: `2026-07-23 10:30 UTC`",
            1,
        )
        assert start_bytes.count(b"\r\n") == writer_before.count(b"\r\n")

        planned_complete = "2026-07-23 11:00 UTC"
        complete_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id="task-7001-writer",
            expected_digest=hashlib.sha256(start_bytes).hexdigest(),
            current_status="DOING",
            target_status="DONE",
            planned_updated_at=planned_complete,
            _temp_token_factory=lambda: "b" * 16,
        )
        assert complete_result.result_type == "updated"
        complete_bytes = writer_path.read_bytes()
        assert complete_bytes == start_bytes.replace(
            b"- status: `DOING`",
            b"- status: `DONE`",
            1,
        ).replace(
            b"- updated_at: `2026-07-23 10:30 UTC`",
            b"- updated_at: `2026-07-23 11:00 UTC`",
            1,
        )

        all_statuses = (
            "TODO",
            "DOING",
            "BLOCKED",
            "DONE",
            "FAILED",
            "NEEDS_APPROVAL",
        )
        for source_status in all_statuses:
            for target_status in all_statuses:
                if (source_status, target_status) in {
                    ("TODO", "DOING"),
                    ("DOING", "DONE"),
                }:
                    continue
                invalid_result = run_web_app.transition_task_file_status(
                    tasks_dir=tasks_dir,
                    task_id="task-7001-writer",
                    expected_digest=hashlib.sha256(complete_bytes).hexdigest(),
                    current_status=source_status,
                    target_status=target_status,
                    planned_updated_at=planned_complete,
                )
                assert invalid_result == run_web_app.TaskStatusTransitionResult(
                    "hold",
                    "invalid_task_transition",
                )

        traversal_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id="../escape",
            expected_digest="0" * 64,
            current_status="TODO",
            target_status="DOING",
            planned_updated_at=planned_start,
        )
        assert traversal_result.reason == "invalid_task_id"

        duplicate_path, duplicate_raw = write_task(
            "task-7002-duplicate",
            "TODO",
            extra_lines=("- status: `TODO`",),
        )
        duplicate_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id="task-7002-duplicate",
            expected_digest=hashlib.sha256(duplicate_raw).hexdigest(),
            current_status="TODO",
            target_status="DOING",
            planned_updated_at=planned_start,
        )
        assert duplicate_result.reason == "task_file_duplicate_metadata"
        assert duplicate_path.read_bytes() == duplicate_raw

        def assert_transition_grammar_rejected(
            task_id: str,
            raw: bytes,
            expected_reason: str,
        ) -> None:
            grammar_path = tasks_dir / f"{task_id}.md"
            grammar_path.write_bytes(raw)
            try:
                parsed = run_web_app.parse_task_view_text(
                    grammar_path.name,
                    raw.decode("utf-8", errors="strict"),
                )
            except UnicodeDecodeError:
                assert expected_reason == "task_file_invalid_utf8"
            else:
                assert parsed is not None
                assert parsed["parse_state"] != "valid"
            grammar_result = run_web_app.transition_task_file_status(
                tasks_dir=tasks_dir,
                task_id=task_id,
                expected_digest=hashlib.sha256(raw).hexdigest(),
                current_status="TODO",
                target_status="DOING",
                planned_updated_at=planned_start,
            )
            assert grammar_result == run_web_app.TaskStatusTransitionResult(
                "hold",
                expected_reason,
            )
            assert grammar_path.read_bytes() == raw

        grammar_cases: list[tuple[str, bytes, str]] = []

        missing_id = "task-7020-missing"
        missing_raw = task_bytes(missing_id, "TODO").replace(
            f"- title: `Fixture Task`\r\n".encode(),
            b"",
            1,
        )
        grammar_cases.append(
            (missing_id, missing_raw, "task_file_missing_metadata")
        )

        malformed_id = "task-7021-malformed"
        malformed_raw = task_bytes(malformed_id, "TODO").replace(
            b"- title: `Fixture Task`",
            b"- title: Fixture Task",
            1,
        )
        grammar_cases.append(
            (malformed_id, malformed_raw, "task_file_invalid_metadata")
        )

        unsupported_id = "task-7022-unsupported"
        unsupported_raw = task_bytes(
            unsupported_id,
            "TODO",
            extra_lines=("- owner: `local`",),
        )
        grammar_cases.append(
            (
                unsupported_id,
                unsupported_raw,
                "task_file_unsupported_metadata",
            )
        )

        invalid_id = "task-7023-invalid-id"
        invalid_id_raw = task_bytes(invalid_id, "TODO").replace(
            f"- id: `{invalid_id}`".encode(),
            b"- id: `bad`",
            1,
        )
        grammar_cases.append(
            (invalid_id, invalid_id_raw, "task_file_invalid_id")
        )

        path_mismatch_id = "task-7024-path-mismatch"
        path_mismatch_raw = task_bytes(path_mismatch_id, "TODO").replace(
            f"- id: `{path_mismatch_id}`".encode(),
            b"- id: `task-9998-other`",
            1,
        )
        grammar_cases.append(
            (
                path_mismatch_id,
                path_mismatch_raw,
                "task_id_path_mismatch",
            )
        )

        invalid_status_id = "task-7025-invalid-status"
        invalid_status_raw = task_bytes(
            invalid_status_id,
            "UNKNOWN",
        )
        grammar_cases.append(
            (
                invalid_status_id,
                invalid_status_raw,
                "task_file_invalid_status",
            )
        )

        invalid_created_id = "task-7026-invalid-created"
        invalid_created_raw = task_bytes(invalid_created_id, "TODO").replace(
            b"- created_at: `2026-07-23 09:00 UTC`",
            b"- created_at: `2026-07-23T09:00:00Z`",
            1,
        )
        grammar_cases.append(
            (
                invalid_created_id,
                invalid_created_raw,
                "task_file_invalid_updated_at",
            )
        )

        invalid_updated_id = "task-7027-invalid-updated"
        invalid_updated_raw = task_bytes(
            invalid_updated_id,
            "TODO",
            updated_at="2026-07-23 9:00 UTC",
        )
        grammar_cases.append(
            (
                invalid_updated_id,
                invalid_updated_raw,
                "task_file_invalid_updated_at",
            )
        )

        for number, field_name, original, oversized in (
            (7028, "title", "Fixture Task", "T" * 121),
            (7029, "repo", "jarvis-core", "r" * 81),
            (7030, "summary", "Fixture summary", "S" * 501),
        ):
            task_id = f"task-{number:04d}-{field_name}-limit"
            oversized_raw = task_bytes(task_id, "TODO").replace(
                f"- {field_name}: `{original}`".encode(),
                f"- {field_name}: `{oversized}`".encode(),
                1,
            )
            grammar_cases.append(
                (task_id, oversized_raw, "task_file_field_too_long")
            )

        empty_title_id = "task-7031-empty-title"
        empty_title_raw = task_bytes(
            empty_title_id,
            "TODO",
            title="   ",
        )
        grammar_cases.append(
            (empty_title_id, empty_title_raw, "task_file_invalid_text")
        )

        control_title_id = "task-7032-control-title"
        control_title_raw = task_bytes(
            control_title_id,
            "TODO",
            title="Unsafe\x00title",
        )
        grammar_cases.append(
            (control_title_id, control_title_raw, "task_file_invalid_text")
        )

        empty_optional_id = "task-7033-empty-optional"
        empty_optional_raw = task_bytes(
            empty_optional_id,
            "TODO",
            extra_lines=("- source_command: ``",),
        )
        grammar_cases.append(
            (empty_optional_id, empty_optional_raw, "task_file_invalid_text")
        )

        long_optional_id = "task-7034-long-optional"
        long_optional_raw = task_bytes(
            long_optional_id,
            "TODO",
            extra_lines=(f"- execution_request: `{'x' * 501}`",),
        )
        grammar_cases.append(
            (
                long_optional_id,
                long_optional_raw,
                "task_file_field_too_long",
            )
        )

        invalid_boolean_id = "task-7035-invalid-boolean"
        invalid_boolean_raw = task_bytes(
            invalid_boolean_id,
            "TODO",
            extra_lines=("- execution_candidate: `yes`",),
        )
        grammar_cases.append(
            (
                invalid_boolean_id,
                invalid_boolean_raw,
                "task_file_invalid_text",
            )
        )

        invalid_optional_time_id = "task-7036-invalid-optional-time"
        invalid_optional_time_raw = task_bytes(
            invalid_optional_time_id,
            "TODO",
            extra_lines=("- execution_updated_at: `yesterday`",),
        )
        grammar_cases.append(
            (
                invalid_optional_time_id,
                invalid_optional_time_raw,
                "task_file_invalid_updated_at",
            )
        )

        invalid_utf8_id = "task-7037-invalid-utf8"
        invalid_utf8_raw = task_bytes(invalid_utf8_id, "TODO").replace(
            b"Fixture summary",
            b"Fixture \xff summary",
            1,
        )
        grammar_cases.append(
            (
                invalid_utf8_id,
                invalid_utf8_raw,
                "task_file_invalid_utf8",
            )
        )

        for task_id, raw, expected_reason in grammar_cases:
            assert_transition_grammar_rejected(
                task_id,
                raw,
                expected_reason,
            )

        optional_id = "task-7038-valid-optional"
        optional_path, optional_raw = write_task(
            optional_id,
            "TODO",
            extra_lines=(
                "- source_command: `Start this task`",
                "- execution_request: `Review the implementation`",
                "- execution_result: `No execution performed`",
                "- execution_summary: `Status-only transition`",
                "- execution_candidate: `true`",
                "- executed: `false`",
                "- success: `true`",
                "- dry_run: `false`",
                "- execution_updated_at: `2026-07-23 10:15 UTC`",
            ),
        )
        parsed_optional = run_web_app.parse_task_view_text(
            optional_path.name,
            optional_raw.decode("utf-8", errors="strict"),
        )
        assert parsed_optional is not None
        assert parsed_optional["parse_state"] == "valid"
        optional_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id=optional_id,
            expected_digest=hashlib.sha256(optional_raw).hexdigest(),
            current_status="TODO",
            target_status="DOING",
            planned_updated_at=planned_start,
            _temp_token_factory=lambda: "e" * 16,
        )
        assert optional_result.result_type == "updated"
        assert optional_path.read_bytes() == optional_raw.replace(
            b"- status: `TODO`",
            b"- status: `DOING`",
            1,
        ).replace(
            b"- updated_at: `2026-07-23 10:00 UTC`",
            b"- updated_at: `2026-07-23 10:30 UTC`",
            1,
        )

        empty_optional_time_id = "task-7039-empty-optional-time"
        empty_optional_time_path, empty_optional_time_raw = write_task(
            empty_optional_time_id,
            "TODO",
            extra_lines=("- execution_updated_at: ``",),
        )
        parsed_empty_optional_time = run_web_app.parse_task_view_text(
            empty_optional_time_path.name,
            empty_optional_time_raw.decode("utf-8", errors="strict"),
        )
        assert parsed_empty_optional_time is not None
        assert parsed_empty_optional_time["parse_state"] == "valid"
        empty_optional_time_result = (
            run_web_app.transition_task_file_status(
                tasks_dir=tasks_dir,
                task_id=empty_optional_time_id,
                expected_digest=hashlib.sha256(
                    empty_optional_time_raw
                ).hexdigest(),
                current_status="TODO",
                target_status="DOING",
                planned_updated_at=planned_start,
                _temp_token_factory=lambda: "f" * 16,
            )
        )
        assert empty_optional_time_result.result_type == "updated"
        assert b"- execution_updated_at: ``" in empty_optional_time_path.read_bytes()

        mismatch_path, mismatch_raw = write_task(
            "task-7003-mismatch",
            "TODO",
        )
        digest_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id="task-7003-mismatch",
            expected_digest="0" * 64,
            current_status="TODO",
            target_status="DOING",
            planned_updated_at=planned_start,
        )
        assert digest_result.reason == "task_changed_since_preview"
        current_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id="task-7003-mismatch",
            expected_digest=hashlib.sha256(mismatch_raw).hexdigest(),
            current_status="DOING",
            target_status="DONE",
            planned_updated_at=planned_start,
        )
        assert current_result.reason == "task_changed_since_preview"
        assert mismatch_path.read_bytes() == mismatch_raw

        deleted_path, deleted_raw = write_task("task-7004-deleted", "TODO")
        deleted_digest = hashlib.sha256(deleted_raw).hexdigest()
        deleted_path.unlink()
        deleted_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id="task-7004-deleted",
            expected_digest=deleted_digest,
            current_status="TODO",
            target_status="DOING",
            planned_updated_at=planned_start,
        )
        assert deleted_result.reason == "task_changed_since_preview"

        final_path, final_raw = write_task("task-7005-final-check", "TODO")
        externally_changed = final_raw.replace(
            b"Fixture summary",
            b"Externally changed summary",
        )

        def change_before_final_check(path: Path) -> None:
            path.write_bytes(externally_changed)

        final_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id="task-7005-final-check",
            expected_digest=hashlib.sha256(final_raw).hexdigest(),
            current_status="TODO",
            target_status="DOING",
            planned_updated_at=planned_start,
            _temp_token_factory=lambda: "c" * 16,
            _before_final_check=change_before_final_check,
        )
        assert final_result.reason == "task_changed_since_preview"
        assert final_path.read_bytes() == externally_changed
        assert not list(tasks_dir.glob(".*.transition.tmp"))

        failure_expectations = {
            "open": "task_transition_temp_create_failed",
            "write": "task_transition_write_failed",
            "flush": "task_transition_flush_failed",
            "fsync": "task_transition_fsync_failed",
            "close": "task_transition_close_failed",
            "replace": "task_transition_replace_failed",
        }
        for index, (stage, expected_reason) in enumerate(
            failure_expectations.items(),
            start=7101,
        ):
            task_id = f"task-{index:04d}-{stage}"
            failure_path, failure_raw = write_task(task_id, "TODO")

            def open_file(path: Path, failure_stage: str = stage) -> Any:
                if failure_stage == "open":
                    raise OSError("injected open failure")
                return FailingBinaryFile(path, failure_stage)

            def fsync_file(_fd: int, failure_stage: str = stage) -> None:
                if failure_stage == "fsync":
                    raise OSError("injected fsync failure")
                return None

            def replace_file(
                temp_path: Path,
                target_path: Path,
                failure_stage: str = stage,
            ) -> None:
                if failure_stage == "replace":
                    raise OSError("injected replace failure")
                temp_path.replace(target_path)

            failure_result = run_web_app.transition_task_file_status(
                tasks_dir=tasks_dir,
                task_id=task_id,
                expected_digest=hashlib.sha256(failure_raw).hexdigest(),
                current_status="TODO",
                target_status="DOING",
                planned_updated_at=planned_start,
                _open_temp_file=open_file,
                _replace_file=replace_file,
                _fsync_file=fsync_file,
                _temp_token_factory=lambda: "d" * 16,
            )
            assert failure_result.reason == expected_reason
            assert failure_path.read_bytes() == failure_raw
            assert not list(tasks_dir.glob(".*.transition.tmp"))

        fixed_utc = lambda: "2026-07-23 12:00 UTC"
        registry = run_web_app.TaskTransitionRegistry(
            token_factory=TokenFactory(),
        )
        snapshot_path, snapshot_raw = write_task(
            "task-7999-snapshot-title",
            "TODO",
            title="Projected title",
        )
        authoritative_raw = snapshot_raw.replace(
            b"- title: `Projected title`",
            b"- title: `Authoritative title`",
            1,
        )

        def edit_title_after_selection(path: Path) -> None:
            assert path == snapshot_path.resolve()
            path.write_bytes(authoritative_raw)

        snapshot_registry = run_web_app.TaskTransitionRegistry(
            token_factory=TokenFactory("snapshottasktransition"),
        )
        snapshot_preview_status, snapshot_preview = (
            run_web_app.preview_task_transition(
                {
                    "task_id": "task-7999-snapshot-title",
                    "action": "start",
                },
                registry=snapshot_registry,
                tasks_dir=tasks_dir,
                utc_now=fixed_utc,
                _after_selection=edit_title_after_selection,
            )
        )
        assert snapshot_preview_status == HTTPStatus.OK
        assert snapshot_preview["preview"]["title"] == "Authoritative title"
        snapshot_confirm_status, snapshot_confirmed = (
            run_web_app.confirm_task_transition(
                {
                    "token": snapshot_preview["token"],
                    "confirmation": "START TASK",
                },
                registry=snapshot_registry,
                tasks_dir=tasks_dir,
            )
        )
        assert snapshot_confirm_status == HTTPStatus.OK
        assert (
            snapshot_confirmed["receipt"]["title"]
            == snapshot_preview["preview"]["title"]
        )
        snapshot_after = snapshot_path.read_bytes()
        assert b"- title: `Authoritative title`" in snapshot_after
        assert b"- status: `DOING`" in snapshot_after

        start_path, start_raw = write_task(
            "task-8001-start",
            "TODO",
            title="Start me",
            summary="No content inference is allowed.",
        )
        preview_status, start_preview = run_web_app.preview_task_transition(
            {"task_id": "task-8001-start", "action": "start"},
            registry=registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_utc,
        )
        assert preview_status == HTTPStatus.OK
        assert start_path.read_bytes() == start_raw
        assert start_preview["confirmation_literal"] == "START TASK"
        assert start_preview["preview"] == {
            "task_id": "task-8001-start",
            "title": "Start me",
            "current_state": "TODO",
            "transition": "TODO \u2192 DOING",
            "proposed_state": "DOING",
            "updated_at": "2026-07-23 12:00 UTC",
            "storage_location": (
                "task-transition-test-fixture/tasks/task-8001-start.md"
            ),
            "no_execution": True,
            "notice": run_web_app.TASK_TRANSITION_NOTICE,
            "warning": "",
        }
        complete_path, complete_raw = write_task(
            "task-8002-complete",
            "DOING",
            title="Complete me",
        )
        complete_preview_status, complete_preview = (
            run_web_app.preview_task_transition(
                {"task_id": "task-8002-complete", "action": "complete"},
                registry=registry,
                tasks_dir=tasks_dir,
                utc_now=fixed_utc,
            )
        )
        assert complete_preview_status == HTTPStatus.OK
        assert complete_path.read_bytes() == complete_raw
        assert complete_preview["confirmation_literal"] == "COMPLETE TASK"
        assert (
            complete_preview["preview"]["warning"]
            == run_web_app.TASK_TRANSITION_COMPLETE_WARNING
        )

        assert run_web_app.preview_task_transition(
            {"task_id": "task-8001-start", "action": "start", "path": "x"},
            registry=registry,
            tasks_dir=tasks_dir,
        )[1]["error"] == (
            "task_transition_preview_accepts_task_id_and_action_only"
        )
        assert run_web_app.preview_task_transition(
            {"task_id": "task-8001-start", "action": "retry"},
            registry=registry,
            tasks_dir=tasks_dir,
        )[1]["error"] == "invalid_task_transition_action"
        assert run_web_app.preview_task_transition(
            {"task_id": "task-8001-start", "action": "complete"},
            registry=registry,
            tasks_dir=tasks_dir,
        )[1]["error"] == "task_status_transition_not_allowed"

        varied_path, _ = write_task(
            "task-8003-varied",
            "TODO",
            title="Different title",
            summary="Completely unrelated summary and body.",
        )
        varied_status, varied_preview = run_web_app.preview_task_transition(
            {"task_id": "task-8003-varied", "action": "start"},
            registry=registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_utc,
        )
        assert varied_status == HTTPStatus.OK
        for field_name in (
            "current_state",
            "transition",
            "proposed_state",
            "updated_at",
            "no_execution",
            "notice",
            "warning",
        ):
            assert (
                varied_preview["preview"][field_name]
                == start_preview["preview"][field_name]
            )
        assert varied_preview["confirmation_literal"] == "START TASK"
        assert varied_path.exists()

        assert run_web_app.confirm_task_transition(
            {
                "token": start_preview["token"],
                "confirmation": "START TASK",
                "status": "DONE",
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )[1]["error"] == (
            "task_transition_confirm_accepts_token_and_confirmation_only"
        )
        assert run_web_app.confirm_task_transition(
            {
                "token": start_preview["token"],
                "confirmation": "COMPLETE TASK",
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )[1]["error"] == "exact_confirmation_required"
        confirm_status, confirmed = run_web_app.confirm_task_transition(
            {
                "token": start_preview["token"],
                "confirmation": "START TASK",
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert confirm_status == HTTPStatus.OK
        expected_receipt = {
            "task_id": "task-8001-start",
            "title": "Start me",
            "previous_state": "TODO",
            "transition": "TODO \u2192 DOING",
            "current_state": "DOING",
            "updated_at": "2026-07-23 12:00 UTC",
            "storage_location": (
                "task-transition-test-fixture/tasks/task-8001-start.md"
            ),
            "no_execution": True,
        }
        assert confirmed["receipt"] == expected_receipt
        assert (
            start_preview["preview"]["current_state"]
            == confirmed["receipt"]["previous_state"]
        )
        assert (
            start_preview["preview"]["transition"]
            == confirmed["receipt"]["transition"]
        )
        assert (
            start_preview["preview"]["proposed_state"]
            == confirmed["receipt"]["current_state"]
        )
        for field_name in ("task_id", "title", "updated_at", "storage_location"):
            assert (
                start_preview["preview"][field_name]
                == confirmed["receipt"][field_name]
            )
        actual_started = start_path.read_bytes()
        assert b"- status: `DOING`" in actual_started
        assert b"- updated_at: `2026-07-23 12:00 UTC`" in actual_started
        repeat_status, repeated = run_web_app.confirm_task_transition(
            {
                "token": start_preview["token"],
                "confirmation": "START TASK",
            },
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert repeat_status == HTTPStatus.OK
        assert repeated["result_type"] == "already_updated"
        assert repeated["receipt"] == confirmed["receipt"]

        two_path, _ = write_task("task-8004-dual-preview", "TODO")
        two_registry = run_web_app.TaskTransitionRegistry(
            token_factory=TokenFactory("twotasktransitiontoken"),
        )
        two_preview_results = [
            run_web_app.preview_task_transition(
                {"task_id": "task-8004-dual-preview", "action": "start"},
                registry=two_registry,
                tasks_dir=tasks_dir,
                utc_now=fixed_utc,
            )
            for _ in range(2)
        ]
        assert all(
            status == HTTPStatus.OK
            for status, _payload in two_preview_results
        )
        two_previews = [payload for _status, payload in two_preview_results]
        first_two = run_web_app.confirm_task_transition(
            {
                "token": two_previews[0]["token"],
                "confirmation": "START TASK",
            },
            registry=two_registry,
            tasks_dir=tasks_dir,
        )
        second_two = run_web_app.confirm_task_transition(
            {
                "token": two_previews[1]["token"],
                "confirmation": "START TASK",
            },
            registry=two_registry,
            tasks_dir=tasks_dir,
        )
        assert first_two[0] == HTTPStatus.OK
        assert second_two == (
            HTTPStatus.CONFLICT,
            {"ok": False, "error": "task_changed_since_preview"},
        )
        assert b"- status: `DOING`" in two_path.read_bytes()

        concurrent_path, _ = write_task("task-8005-concurrent", "TODO")
        concurrent_registry = run_web_app.TaskTransitionRegistry(
            token_factory=TokenFactory("concurrenttasktoken"),
        )
        concurrent_preview = run_web_app.preview_task_transition(
            {"task_id": "task-8005-concurrent", "action": "start"},
            registry=concurrent_registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_utc,
        )[1]
        writer_calls = 0
        writer_call_lock = threading.Lock()

        def counting_writer(**kwargs: Any) -> Any:
            nonlocal writer_calls
            with writer_call_lock:
                writer_calls += 1
            return run_web_app.transition_task_file_status(**kwargs)

        concurrent_results: list[tuple[int, dict[str, Any]]] = []

        def confirm_concurrently() -> None:
            concurrent_results.append(
                concurrent_registry.confirm(
                    token=concurrent_preview["token"],
                    confirmation="START TASK",
                    tasks_dir=tasks_dir,
                    writer=counting_writer,
                )
            )

        threads = [threading.Thread(target=confirm_concurrently) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive()
        assert writer_calls == 1
        assert sorted(
            result[1]["result_type"] for result in concurrent_results
        ) == ["already_updated", "updated"]
        assert (
            concurrent_results[0][1]["receipt"]
            == concurrent_results[1][1]["receipt"]
        )
        assert b"- status: `DOING`" in concurrent_path.read_bytes()

        stale_path, stale_raw = write_task("task-8006-stale", "TODO")
        stale_registry = run_web_app.TaskTransitionRegistry(
            token_factory=TokenFactory("staletasktransitiontoken"),
        )
        stale_preview = run_web_app.preview_task_transition(
            {"task_id": "task-8006-stale", "action": "start"},
            registry=stale_registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_utc,
        )[1]
        stale_path.write_bytes(
            stale_raw.replace(b"Fixture summary", b"Changed after preview")
        )
        assert run_web_app.confirm_task_transition(
            {
                "token": stale_preview["token"],
                "confirmation": "START TASK",
            },
            registry=stale_registry,
            tasks_dir=tasks_dir,
        ) == (
            HTTPStatus.CONFLICT,
            {"ok": False, "error": "task_changed_since_preview"},
        )

        delete_path, _ = write_task("task-8007-delete", "TODO")
        delete_registry = run_web_app.TaskTransitionRegistry(
            token_factory=TokenFactory("deletetasktransitiontoken"),
        )
        delete_preview = run_web_app.preview_task_transition(
            {"task_id": "task-8007-delete", "action": "start"},
            registry=delete_registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_utc,
        )[1]
        delete_path.unlink()
        assert run_web_app.confirm_task_transition(
            {
                "token": delete_preview["token"],
                "confirmation": "START TASK",
            },
            registry=delete_registry,
            tasks_dir=tasks_dir,
        )[1]["error"] == "task_changed_since_preview"

        expired_path, _ = write_task("task-8008-expired", "TODO")
        expired_clock = FakeClock()
        expired_registry = run_web_app.TaskTransitionRegistry(
            clock=expired_clock,
            token_factory=TokenFactory("expiredtasktransitiontoken"),
            ttl_seconds=10,
        )
        expired_preview = run_web_app.preview_task_transition(
            {"task_id": "task-8008-expired", "action": "start"},
            registry=expired_registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_utc,
        )[1]
        expired_clock.value += 11
        assert run_web_app.confirm_task_transition(
            {
                "token": expired_preview["token"],
                "confirmation": "START TASK",
            },
            registry=expired_registry,
            tasks_dir=tasks_dir,
        )[1]["error"] == "invalid_or_expired_task_transition_token"
        assert b"- status: `TODO`" in expired_path.read_bytes()

        consumed_path, _ = write_task("task-8009-consumed", "TODO")
        consumed_registry = run_web_app.TaskTransitionRegistry(
            token_factory=TokenFactory("consumedtasktransitiontoken"),
        )
        consumed_preview = run_web_app.preview_task_transition(
            {"task_id": "task-8009-consumed", "action": "start"},
            registry=consumed_registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_utc,
        )[1]

        class ErrorResult:
            result_type = "error"
            reason = "injected_transition_failure"

        assert consumed_registry.confirm(
            token=consumed_preview["token"],
            confirmation="START TASK",
            tasks_dir=tasks_dir,
            writer=lambda **_kwargs: ErrorResult(),
        )[1]["error"] == "injected_transition_failure"
        assert consumed_registry.confirm(
            token=consumed_preview["token"],
            confirmation="START TASK",
            tasks_dir=tasks_dir,
        )[1]["error"] == "task_transition_token_already_consumed"
        assert b"- status: `TODO`" in consumed_path.read_bytes()

        http_path, http_raw = write_task("task-8010-http", "TODO")
        direct_http_registry = run_web_app.TaskTransitionRegistry(
            token_factory=lambda: "h" * 32,
        )
        direct_preview = run_web_app.preview_task_transition(
            {"task_id": "task-8010-http", "action": "start"},
            registry=direct_http_registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_utc,
        )
        direct_confirm = run_web_app.confirm_task_transition(
            {
                "token": direct_preview[1]["token"],
                "confirmation": "START TASK",
            },
            registry=direct_http_registry,
            tasks_dir=tasks_dir,
        )
        assert direct_preview[0] == direct_confirm[0] == HTTPStatus.OK
        http_path.write_bytes(http_raw)

        http_registry = run_web_app.TaskTransitionRegistry(
            token_factory=lambda: "h" * 32,
        )
        server = run_web_app.ThreadingHTTPServer(
            (run_web_app.DEFAULT_HOST, 0),
            run_web_app.JarvisConsoleHandler,
        )
        server.task_transition_registry = http_registry
        server.task_transition_tasks_dir = tasks_dir
        server.task_transition_utc_now = fixed_utc
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        port = int(server.server_address[1])

        def post_transition(
            path: str,
            payload: dict[str, Any],
            *,
            origin: str | None = None,
        ) -> tuple[int, dict[str, Any]]:
            connection = HTTPConnection(run_web_app.DEFAULT_HOST, port, timeout=10)
            body = json.dumps(payload, ensure_ascii=True).encode("ascii")
            connection.request(
                "POST",
                path,
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Origin": origin or f"http://{run_web_app.DEFAULT_HOST}:{port}",
                },
            )
            response = connection.getresponse()
            response_payload = json.loads(response.read().decode("utf-8"))
            response_status = response.status
            connection.close()
            return response_status, response_payload

        try:
            rejected_status, rejected = post_transition(
                run_web_app.TASK_TRANSITION_PREVIEW_ENDPOINT,
                {"task_id": "task-8010-http", "action": "start"},
                origin="http://127.0.0.1:1",
            )
            assert rejected_status == HTTPStatus.FORBIDDEN
            assert rejected["error"] == "task_transition_origin_rejected"
            http_preview = post_transition(
                run_web_app.TASK_TRANSITION_PREVIEW_ENDPOINT,
                {"task_id": "task-8010-http", "action": "start"},
            )
            assert http_preview == direct_preview
            http_confirm = post_transition(
                run_web_app.TASK_TRANSITION_CONFIRM_ENDPOINT,
                {
                    "token": http_preview[1]["token"],
                    "confirmation": "START TASK",
                },
            )
            assert http_confirm == direct_confirm
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
        assert not server_thread.is_alive()
        assert http_path.read_bytes() == actual_started.replace(
            b"task-8001-start",
            b"task-8010-http",
        ).replace(
            b"Start me",
            b"Fixture Task",
        ).replace(
            b"No content inference is allowed.",
            b"Fixture summary",
        )

        app_js = Path(run_web_app.WEB_ROOT, "app.js").read_text(encoding="utf-8")
        web_source = Path(run_web_app.__file__).read_text(encoding="utf-8")
        for exact_text in (
            "/api/task-transition/preview",
            "/api/task-transition/confirm",
            "Start Task",
            "Complete Task",
            "Task Transition Preview",
            "Task Transition Receipt",
            "Previous State",
            "Transition",
            "Current State",
            "Proposed State",
            "No execution",
        ):
            assert exact_text in app_js or exact_text in web_source
        assert run_web_app.TASK_TRANSITION_COMPLETE_WARNING == (
            "Confirm Complete only if verification evidence is already recorded. "
            "Jarvis does not evaluate whether verification evidence exists or infer "
            "completion from task content or summary."
        )
        transition_renderer = app_js.split(
            "function actionableTaskItemMarkup",
            1,
        )[1].split("function renderActionableTaskView", 1)[0]
        assert 'view.status === "TODO"' in transition_renderer
        assert 'view.status === "DOING"' in transition_renderer
        assert "escapeHtml(preview.title || \"\")" in transition_renderer
        assert "escapeHtml(preview.current_state || \"\")" in transition_renderer
        assert "escapeHtml(preview.transition || \"\")" in transition_renderer
        assert "escapeHtml(preview.proposed_state || \"\")" in transition_renderer
        assert "escapeHtml(preview.warning)" in transition_renderer
        assert "escapeHtml(receipt.transition || \"\")" in transition_renderer
        assert "await loadOverview()" in transition_renderer
        transition_source = (
            inspect.getsource(run_web_app.preview_task_transition)
            + inspect.getsource(run_web_app.confirm_task_transition)
            + inspect.getsource(run_web_app.TaskTransitionRegistry)
        ).lower().replace("fullmatch", "")
        assert 'task_view["summary"]' not in transition_source
        assert "openai" not in transition_source
        assert "llm" not in transition_source
        assert "subprocess" not in transition_source
        assert not list(tasks_dir.glob(".*.transition.tmp"))
    finally:
        if fixture_root.exists():
            shutil.rmtree(fixture_root)

    assert not fixture_root.exists()
    actual_overview = run_web_app.overview_payload()
    assert len(actual_overview["tasks"]) == 5
    assert all(
        item["task_view"]["status"] == "DONE"
        for item in actual_overview["tasks"]
    )
    assert sum(
        item["task_view"]["status"] in {"TODO", "DOING"}
        for item in actual_overview["tasks"]
    ) == 0
    assert artifact_snapshot() == before_artifacts


def _test_completion_evidence_vertical_slice() -> None:
    fixture_root = run_web_app.REPO_ROOT / "completion-evidence-test-fixture"
    tasks_dir = fixture_root / "tasks"
    production_dir = run_web_app.REPO_ROOT / "memory" / "tasks"

    def production_snapshot() -> dict[str, str]:
        return {
            path.relative_to(production_dir).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(production_dir.rglob("*"))
            if path.is_file()
        }

    def task_bytes(
        task_id: str,
        status: str = "DOING",
        *,
        evidence: str | None = None,
        updated_at: str = "2026-07-24 01:00 UTC",
        newline: str = "\n",
    ) -> bytes:
        lines = [
            f"# {task_id}",
            "",
            f"- id: `{task_id}`",
            f"- title: `Evidence task`",
            f"- status: `{status}`",
            f"- repo: `jarvis-core`",
            f"- created_at: `2026-07-24 00:00 UTC`",
            f"- updated_at: `{updated_at}`",
            f"- summary: `Verify the bounded result`",
        ]
        if evidence is not None:
            lines.append(f"- completion_evidence: `{evidence}`")
        return (newline.join(lines) + newline).encode("utf-8")

    class TokenFactory:
        def __init__(self, prefix: str) -> None:
            self.prefix = prefix
            self.index = 0

        def __call__(self) -> str:
            self.index += 1
            return f"{self.prefix}{self.index:08d}"

    before_production = production_snapshot()
    assert fixture_root.resolve().parent == run_web_app.REPO_ROOT.resolve()
    assert run_web_app.TASK_ALLOWED_METADATA == (
        run_web_app.TASK_VIEW_ALLOWED_FIELDS
    )
    shutil.rmtree(fixture_root, ignore_errors=True)
    tasks_dir.mkdir(parents=True)
    try:
        assert run_web_app.normalize_completion_evidence(
            "  cafe\u0301\u00a0 proof  "
        ) == "café proof"
        for rejected in (
            "",
            " ",
            "line\rbreak",
            "line\nbreak",
            "line\u0085break",
            "line\u2028break",
            "line\u2029break",
            "bad`value",
            "bad\x00value",
            "bad\tvalue",
            "bad\u200bvalue",
            "bad\ud800value",
            "x" * 501,
        ):
            assert run_web_app.normalize_completion_evidence(rejected) is None
        assert run_web_app.normalize_completion_evidence("x" * 500) == "x" * 500
        assert run_web_app.normalize_completion_evidence(1) is None

        task_id = "task-9001-evidence"
        task_path = tasks_dir / f"{task_id}.md"
        original = task_bytes(task_id, newline="\r\n")
        task_path.write_bytes(original)
        view = run_web_app.parse_task_view_text(
            task_path.name,
            original.decode("utf-8"),
        )
        assert view is not None
        assert view["completion_evidence"] is None
        assert view["has_completion_evidence"] is False
        ordered = run_web_app.parse_task_view_text(
            "task-9010-ordered.md",
            task_bytes(
                "task-9010-ordered",
                evidence="proof",
            ).decode("utf-8"),
        )
        assert ordered is not None
        assert ordered["parse_state"] == "valid"
        assert ordered["completion_evidence"] == "proof"
        assert ordered["has_completion_evidence"] is True
        misordered_raw = task_bytes(
            "task-9011-misordered",
            evidence="proof",
        ).replace(
            (
                b"- summary: `Verify the bounded result`\n"
                b"- completion_evidence: `proof`\n"
            ),
            (
                b"- completion_evidence: `proof`\n"
                b"- summary: `Verify the bounded result`\n"
            ),
        )
        misordered = run_web_app.parse_task_view_text(
            "task-9011-misordered.md",
            misordered_raw.decode("utf-8"),
        )
        assert misordered is not None
        assert misordered["parse_state"] == "invalid"
        assert misordered["reason_field"] == "completion_evidence"

        registry = run_web_app.CompletionEvidenceRegistry(
            token_factory=TokenFactory("evidencepreviewtoken"),
        )
        preview_status, preview = run_web_app.preview_completion_evidence(
            {
                "task_id": task_id,
                "completion_evidence": "  build\u00a0 42 passed  ",
            },
            registry=registry,
            tasks_dir=tasks_dir,
            utc_now=lambda: "2026-07-24 02:00 UTC",
        )
        assert preview_status == HTTPStatus.OK
        assert task_path.read_bytes() == original
        assert set(preview) == {
            "ok",
            "product_name",
            "token",
            "expires",
            "confirmation_literal",
            "preview",
        }
        assert preview["product_name"] == "Record Completion Evidence"
        assert preview["confirmation_literal"] == "RECORD EVIDENCE"
        assert set(preview["preview"]) == {
            "task_id",
            "title",
            "current_status",
            "existing_evidence",
            "proposed_evidence",
            "observed_updated_at",
            "planned_updated_at",
            "storage_location",
            "evidence_validated",
            "status_changed",
            "no_execution",
            "notice",
        }
        assert preview["preview"]["proposed_evidence"] == "build 42 passed"
        assert preview["preview"]["current_status"] == "DOING"
        assert preview["preview"]["existing_evidence"] is None
        assert preview["preview"]["evidence_validated"] is False
        assert preview["preview"]["status_changed"] is False
        assert preview["preview"]["no_execution"] is True

        wrong_status, wrong = run_web_app.confirm_completion_evidence(
            {"token": preview["token"], "confirmation": "record evidence"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert wrong_status == HTTPStatus.BAD_REQUEST
        assert (
            wrong["error"]
            == "completion_evidence_exact_confirmation_required"
        )
        assert task_path.read_bytes() == original

        confirm_status, confirmed = run_web_app.confirm_completion_evidence(
            {"token": preview["token"], "confirmation": "RECORD EVIDENCE"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert confirm_status == HTTPStatus.OK
        assert confirmed["result_type"] == "recorded"
        assert confirmed["receipt"] == {
            "task_id": task_id,
            "title": "Evidence task",
            "current_status": "DOING",
            "completion_evidence": "build 42 passed",
            "updated_at": "2026-07-24 02:00 UTC",
            "storage_location": (
                "completion-evidence-test-fixture/tasks/task-9001-evidence.md"
            ),
            "evidence_validated": False,
            "status_changed": False,
            "no_execution": True,
            "recommendation": run_web_app.COMPLETION_EVIDENCE_RECOMMENDATION,
        }
        expected = original.replace(
            b"- updated_at: `2026-07-24 01:00 UTC`",
            b"- updated_at: `2026-07-24 02:00 UTC`",
        ).replace(
            b"- summary: `Verify the bounded result`\r\n",
            (
                b"- summary: `Verify the bounded result`\r\n"
                b"- completion_evidence: `build 42 passed`\r\n"
            ),
        )
        assert task_path.read_bytes() == expected
        recorded_view = run_web_app.parse_task_view_text(
            task_path.name,
            expected.decode("utf-8"),
        )
        assert recorded_view is not None
        assert recorded_view["completion_evidence"] == "build 42 passed"
        assert recorded_view["has_completion_evidence"] is True
        replay_status, replay = run_web_app.confirm_completion_evidence(
            {"token": preview["token"], "confirmation": "RECORD EVIDENCE"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert replay_status == HTTPStatus.OK
        assert replay["result_type"] == "already_recorded"
        assert replay["receipt"] == confirmed["receipt"]
        assert task_path.read_bytes() == expected

        existing_status, existing = run_web_app.preview_completion_evidence(
            {"task_id": task_id, "completion_evidence": "second"},
            registry=registry,
            tasks_dir=tasks_dir,
        )
        assert existing_status == HTTPStatus.CONFLICT
        assert existing["error"] == "completion_evidence_already_exists"

        complete_result = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id=task_id,
            expected_digest=hashlib.sha256(expected).hexdigest(),
            current_status="DOING",
            target_status="DONE",
            planned_updated_at="2026-07-24 03:00 UTC",
        )
        assert complete_result.result_type == "updated"
        completed_bytes = task_path.read_bytes()
        assert b"- completion_evidence: `build 42 passed`" in completed_bytes
        assert completed_bytes == expected.replace(
            b"- status: `DOING`",
            b"- status: `DONE`",
        ).replace(
            b"- updated_at: `2026-07-24 02:00 UTC`",
            b"- updated_at: `2026-07-24 03:00 UTC`",
        )

        created = run_web_app.write_task_file(
            {
                "title": "Created without evidence",
                "status": "TODO",
                "repo": "jarvis-core",
                "summary": "Creation must omit optional evidence.",
            },
            tasks_dir=tasks_dir,
        )
        assert created.result_type == "created"
        created_path = Path(created.file_path or "")
        created_raw = created_path.read_bytes()
        assert b"completion_evidence" not in created_raw
        started = run_web_app.transition_task_file_status(
            tasks_dir=tasks_dir,
            task_id=str(created.task_id),
            expected_digest=hashlib.sha256(created_raw).hexdigest(),
            current_status="TODO",
            target_status="DOING",
            planned_updated_at="2026-07-24 04:00 UTC",
        )
        assert started.result_type == "updated"
        assert b"completion_evidence" not in created_path.read_bytes()

        stale_id = "task-9002-stale"
        stale_path = tasks_dir / f"{stale_id}.md"
        stale_path.write_bytes(task_bytes(stale_id))
        stale_registry = run_web_app.CompletionEvidenceRegistry(
            token_factory=TokenFactory("evidencestaletoken"),
        )
        stale_preview = run_web_app.preview_completion_evidence(
            {"task_id": stale_id, "completion_evidence": "proof"},
            registry=stale_registry,
            tasks_dir=tasks_dir,
            utc_now=lambda: "2026-07-24 05:00 UTC",
        )[1]
        stale_path.write_bytes(
            stale_path.read_bytes().replace(
                b"Verify the bounded result",
                b"Changed after preview",
            )
        )
        stale_before = stale_path.read_bytes()
        stale_status, stale = run_web_app.confirm_completion_evidence(
            {
                "token": stale_preview["token"],
                "confirmation": "RECORD EVIDENCE",
            },
            registry=stale_registry,
            tasks_dir=tasks_dir,
        )
        assert stale_status == HTTPStatus.CONFLICT
        assert stale["error"] == "completion_evidence_task_changed_since_preview"
        assert stale_path.read_bytes() == stale_before
        consumed = run_web_app.confirm_completion_evidence(
            {
                "token": stale_preview["token"],
                "confirmation": "RECORD EVIDENCE",
            },
            registry=stale_registry,
            tasks_dir=tasks_dir,
        )
        assert consumed[0] == HTTPStatus.CONFLICT
        assert consumed[1]["error"] == "completion_evidence_token_already_consumed"

        class Clock:
            def __init__(self) -> None:
                self.value = 0.0

            def __call__(self) -> float:
                return self.value

        expired_id = "task-9003-expired"
        expired_path = tasks_dir / f"{expired_id}.md"
        expired_raw = task_bytes(expired_id)
        expired_path.write_bytes(expired_raw)
        clock = Clock()
        expired_registry = run_web_app.CompletionEvidenceRegistry(
            clock=clock,
            ttl_seconds=1,
            token_factory=TokenFactory("evidenceexpiredtoken"),
        )
        expired_preview = run_web_app.preview_completion_evidence(
            {"task_id": expired_id, "completion_evidence": "proof"},
            registry=expired_registry,
            tasks_dir=tasks_dir,
        )[1]
        clock.value = 2.0
        expired_confirm = run_web_app.confirm_completion_evidence(
            {
                "token": expired_preview["token"],
                "confirmation": "RECORD EVIDENCE",
            },
            registry=expired_registry,
            tasks_dir=tasks_dir,
        )
        assert expired_confirm[0] == HTTPStatus.NOT_FOUND
        assert expired_path.read_bytes() == expired_raw

        capacity_a_id = "task-9004-capacity-a"
        capacity_b_id = "task-9005-capacity-b"
        (tasks_dir / f"{capacity_a_id}.md").write_bytes(task_bytes(capacity_a_id))
        (tasks_dir / f"{capacity_b_id}.md").write_bytes(task_bytes(capacity_b_id))
        capacity_registry = run_web_app.CompletionEvidenceRegistry(
            capacity=1,
            token_factory=TokenFactory("evidencecapacitytoken"),
        )
        assert run_web_app.preview_completion_evidence(
            {"task_id": capacity_a_id, "completion_evidence": "proof a"},
            registry=capacity_registry,
            tasks_dir=tasks_dir,
        )[0] == HTTPStatus.OK
        capacity_status, capacity_payload = (
            run_web_app.preview_completion_evidence(
                {"task_id": capacity_b_id, "completion_evidence": "proof b"},
                registry=capacity_registry,
                tasks_dir=tasks_dir,
            )
        )
        assert capacity_status == HTTPStatus.SERVICE_UNAVAILABLE
        assert (
            capacity_payload["error"]
            == "completion_evidence_temporarily_unavailable"
        )

        concurrent_id = "task-9006-concurrent"
        concurrent_path = tasks_dir / f"{concurrent_id}.md"
        concurrent_path.write_bytes(task_bytes(concurrent_id))
        concurrent_registry = run_web_app.CompletionEvidenceRegistry(
            token_factory=TokenFactory("evidenceconcurrenttoken"),
        )
        concurrent_preview = run_web_app.preview_completion_evidence(
            {"task_id": concurrent_id, "completion_evidence": "one proof"},
            registry=concurrent_registry,
            tasks_dir=tasks_dir,
            utc_now=lambda: "2026-07-24 05:30 UTC",
        )[1]
        concurrent_results: list[tuple[int, dict[str, Any]]] = []

        def confirm_concurrently() -> None:
            concurrent_results.append(
                run_web_app.confirm_completion_evidence(
                    {
                        "token": concurrent_preview["token"],
                        "confirmation": "RECORD EVIDENCE",
                    },
                    registry=concurrent_registry,
                    tasks_dir=tasks_dir,
                )
            )

        threads = [
            threading.Thread(target=confirm_concurrently)
            for _ in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive()
        assert sorted(
            payload["result_type"] for _status, payload in concurrent_results
        ) == ["already_recorded", "recorded"]
        assert (
            concurrent_path.read_text(encoding="utf-8").count(
                "- completion_evidence:"
            )
            == 1
        )

        todo_id = "task-9007-not-doing"
        todo_path = tasks_dir / f"{todo_id}.md"
        todo_raw = task_bytes(todo_id, status="TODO")
        todo_path.write_bytes(todo_raw)
        not_doing = run_web_app.preview_completion_evidence(
            {"task_id": todo_id, "completion_evidence": "proof"},
            registry=run_web_app.CompletionEvidenceRegistry(
                token_factory=TokenFactory("evidencenotdoingtoken")
            ),
            tasks_dir=tasks_dir,
        )
        assert not_doing[0] == HTTPStatus.CONFLICT
        assert not_doing[1]["error"] == "completion_evidence_task_not_doing"
        assert todo_path.read_bytes() == todo_raw

        atomic_id = "task-9003-atomic"
        atomic_path = tasks_dir / f"{atomic_id}.md"
        atomic_raw = task_bytes(atomic_id)
        atomic_path.write_bytes(atomic_raw)

        def fail_replace(_temp: Path, _target: Path) -> None:
            raise OSError("injected replace failure")

        atomic_result = run_web_app.record_task_completion_evidence(
            tasks_dir=tasks_dir,
            task_id=atomic_id,
            completion_evidence="proof",
            expected_digest=hashlib.sha256(atomic_raw).hexdigest(),
            planned_updated_at="2026-07-24 06:00 UTC",
            _replace_file=fail_replace,
            _temp_token_factory=lambda: "0123456789abcdef",
        )
        assert atomic_result == run_web_app.CompletionEvidenceWriteResult(
            "error",
            "completion_evidence_replace_failed",
        )
        assert atomic_path.read_bytes() == atomic_raw
        assert not list(tasks_dir.glob(".*.evidence.tmp"))

        header_pairs = [
            ("Host", "127.0.0.1:8790"),
            ("Origin", "http://127.0.0.1:8790"),
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", "2"),
        ]
        assert run_web_app.validate_completion_evidence_http_request(
            path=run_web_app.COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
            query="",
            header_pairs=header_pairs,
            bound_port=8790,
        ) == (HTTPStatus.OK, {"ok": True, "body_length": 2})
        for pairs, expected_status, expected_error in (
            (
                header_pairs + [("Host", "127.0.0.1:8790")],
                HTTPStatus.BAD_REQUEST,
                "completion_evidence_headers_rejected",
            ),
            (
                [pair for pair in header_pairs if pair[0] != "Origin"],
                HTTPStatus.BAD_REQUEST,
                "completion_evidence_headers_rejected",
            ),
            (
                [
                    (name, "http://127.0.0.1:9999")
                    if name == "Origin"
                    else (name, value)
                    for name, value in header_pairs
                ],
                HTTPStatus.FORBIDDEN,
                "completion_evidence_origin_rejected",
            ),
            (
                [
                    (name, "text/plain")
                    if name == "Content-Type"
                    else (name, value)
                    for name, value in header_pairs
                ],
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "completion_evidence_json_required",
            ),
            (
                [
                    (name, "0")
                    if name == "Content-Length"
                    else (name, value)
                    for name, value in header_pairs
                ],
                HTTPStatus.BAD_REQUEST,
                "completion_evidence_invalid_content_length",
            ),
            (
                header_pairs + [("Transfer-Encoding", "chunked")],
                HTTPStatus.BAD_REQUEST,
                "completion_evidence_transfer_encoding_not_allowed",
            ),
        ):
            rejected_status, rejected_payload = (
                run_web_app.validate_completion_evidence_http_request(
                    path=run_web_app.COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
                    query="",
                    header_pairs=pairs,
                    bound_port=8790,
                )
            )
            assert rejected_status == expected_status
            assert rejected_payload["error"] == expected_error
        query_rejected = run_web_app.validate_completion_evidence_http_request(
            path=run_web_app.COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
            query="x=1",
            header_pairs=header_pairs,
            bound_port=8790,
        )
        assert query_rejected == (
            HTTPStatus.NOT_FOUND,
            {"ok": False, "error": "completion_evidence_not_found"},
        )
        path_rejected = run_web_app.validate_completion_evidence_http_request(
            path="/api/completion-evidence/other",
            query="",
            header_pairs=header_pairs,
            bound_port=8790,
        )
        assert path_rejected == (
            HTTPStatus.NOT_FOUND,
            {"ok": False, "error": "completion_evidence_not_found"},
        )
        assert run_web_app.validate_completion_evidence_http_request(
            path=run_web_app.COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
            query="",
            header_pairs=header_pairs
            + [(f"X-Test-{index}", "x") for index in range(29)],
            bound_port=8790,
        )[0] == HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE
        assert run_web_app.parse_completion_evidence_json_body(
            b'{"task_id":"a","task_id":"b"}'
        )[0] == HTTPStatus.BAD_REQUEST
        assert run_web_app.parse_completion_evidence_json_body(b"[]")[0] == (
            HTTPStatus.BAD_REQUEST
        )
        assert run_web_app.handle_post_api(
            run_web_app.COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
            {},
        )[0] == HTTPStatus.NOT_FOUND

        http_id = "task-9008-http"
        http_path = tasks_dir / f"{http_id}.md"
        http_raw = task_bytes(http_id)
        http_path.write_bytes(http_raw)
        fixed_http_utc = lambda: "2026-07-24 07:00 UTC"
        direct_registry = run_web_app.CompletionEvidenceRegistry(
            token_factory=lambda: "h" * 32,
        )
        direct_preview = run_web_app.preview_completion_evidence(
            {"task_id": http_id, "completion_evidence": "HTTP proof"},
            registry=direct_registry,
            tasks_dir=tasks_dir,
            utc_now=fixed_http_utc,
        )
        assert direct_preview[0] == HTTPStatus.OK
        assert http_path.read_bytes() == http_raw

        http_registry = run_web_app.CompletionEvidenceRegistry(
            token_factory=lambda: "h" * 32,
        )
        server = run_web_app.ThreadingHTTPServer(
            (run_web_app.DEFAULT_HOST, 0),
            run_web_app.JarvisConsoleHandler,
        )
        server.completion_evidence_registry = http_registry
        server.completion_evidence_tasks_dir = tasks_dir
        server.completion_evidence_utc_now = fixed_http_utc
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        port = int(server.server_address[1])

        def post_evidence(
            path: str,
            payload: dict[str, Any],
            *,
            origin: str | None = None,
        ) -> tuple[int, dict[str, Any]]:
            connection = HTTPConnection(
                run_web_app.DEFAULT_HOST,
                port,
                timeout=10,
            )
            body = json.dumps(payload, ensure_ascii=True).encode("ascii")
            connection.request(
                "POST",
                path,
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Origin": (
                        origin
                        or f"http://{run_web_app.DEFAULT_HOST}:{port}"
                    ),
                },
            )
            response = connection.getresponse()
            response_payload = json.loads(response.read().decode("utf-8"))
            response_status = response.status
            connection.close()
            return response_status, response_payload

        try:
            rejected_http = post_evidence(
                run_web_app.COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
                {"task_id": http_id, "completion_evidence": "HTTP proof"},
                origin="http://127.0.0.1:1",
            )
            assert rejected_http[0] == HTTPStatus.FORBIDDEN
            assert (
                rejected_http[1]["error"]
                == "completion_evidence_origin_rejected"
            )
            http_preview = post_evidence(
                run_web_app.COMPLETION_EVIDENCE_PREVIEW_ENDPOINT,
                {"task_id": http_id, "completion_evidence": "HTTP proof"},
            )
            assert http_preview == direct_preview
            http_confirm = post_evidence(
                run_web_app.COMPLETION_EVIDENCE_CONFIRM_ENDPOINT,
                {
                    "token": http_preview[1]["token"],
                    "confirmation": "RECORD EVIDENCE",
                },
            )
            assert http_confirm[0] == HTTPStatus.OK
            assert http_confirm[1]["result_type"] == "recorded"
            assert http_confirm[1]["receipt"]["current_status"] == "DOING"
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
        assert not server_thread.is_alive()
        assert (
            http_path.read_text(encoding="utf-8").count(
                "- completion_evidence: `HTTP proof`"
            )
            == 1
        )
    finally:
        shutil.rmtree(fixture_root, ignore_errors=True)

    assert not fixture_root.exists()
    assert production_snapshot() == before_production


def _test_actionable_task_view_vertical_slice() -> None:
    _test_task_transition_vertical_slice()
    _test_completion_evidence_vertical_slice()
    watched_roots = (
        run_web_app.REPO_ROOT / "memory" / "tasks",
        run_web_app.REPO_ROOT / "reports",
    )

    def artifact_snapshot() -> tuple[tuple[str, int, int], ...]:
        snapshot: list[tuple[str, int, int]] = []
        for root in watched_roots:
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    stat_result = path.stat()
                    snapshot.append(
                        (
                            path.relative_to(run_web_app.REPO_ROOT).as_posix(),
                            stat_result.st_size,
                            stat_result.st_mtime_ns,
                        )
                    )
        return tuple(snapshot)

    def task_markdown(
        task_id: str,
        status: str,
        *,
        title: str = "Task title",
        summary: str = "Task summary",
        created_at: str = "2026-07-23 09:00 UTC",
        updated_at: str = "2026-07-23 10:00 UTC",
        repo: str = "jarvis-core",
        optional_lines: tuple[str, ...] = (),
    ) -> str:
        return (
            "\n".join(
                [
                    f"# {task_id}",
                    "",
                    f"- id: `{task_id}`",
                    f"- title: `{title}`",
                    f"- status: `{status}`",
                    f"- repo: `{repo}`",
                    f"- created_at: `{created_at}`",
                    f"- updated_at: `{updated_at}`",
                    f"- summary: `{summary}`",
                    *optional_lines,
                ]
            )
            + "\n"
        )

    before_artifacts = artifact_snapshot()
    expected_status_rules = {
        "NEEDS_APPROVAL": (
            "needs_attention",
            10,
            "Review the summary and make the required decision outside Jarvis Console.",
        ),
        "BLOCKED": (
            "needs_attention",
            20,
            "Review the summary and clear the blocker outside Jarvis Console.",
        ),
        "FAILED": (
            "needs_attention",
            30,
            "Review the summary and decide the recovery outside Jarvis Console.",
        ),
        "DOING": (
            "in_progress",
            40,
            "Continue the work described in the summary outside Jarvis Console.",
        ),
        "TODO": (
            "ready",
            50,
            "Decide whether to start this task outside Jarvis Console.",
        ),
        "DONE": (
            "completed",
            60,
            "No next action is required.",
        ),
    }
    for index, (status, expected_rule) in enumerate(
        expected_status_rules.items(),
        start=101,
    ):
        task_id = f"task-{index:04d}-{status.lower().replace('_', '-')}"
        view = run_web_app.parse_task_view_text(
            f"{task_id}.md",
            task_markdown(task_id, status),
        )
        assert view is not None
        assert view["parse_state"] == "valid"
        assert (
            view["group_id"],
            view["display_rank"],
            view["next_action"],
        ) == expected_rule
        assert set(view) == {
            "parse_state",
            "id",
            "title",
            "status",
            "updated_at",
            "summary",
            "completion_evidence",
            "has_completion_evidence",
            "group_id",
            "display_rank",
            "next_action",
            "read_only",
        }
        assert view["read_only"] is True

    same_status_a = run_web_app.parse_task_view_text(
        "task-0201-copy-a.md",
        task_markdown(
            "task-0201-copy-a",
            "BLOCKED",
            title="First unrelated title",
            summary="First unrelated summary",
        ),
    )
    same_status_b = run_web_app.parse_task_view_text(
        "task-0202-copy-b.md",
        task_markdown(
            "task-0202-copy-b",
            "BLOCKED",
            title="Completely different title",
            summary="Completely different summary",
        ),
    )
    assert same_status_a is not None and same_status_b is not None
    assert (
        same_status_a["next_action"].encode("utf-8")
        == same_status_b["next_action"].encode("utf-8")
    )

    optional_lines = (
        "- source_command: `/task`",
        "- execution_candidate: `true`",
        "- execution_request: `request`",
        "- execution_result: `result`",
        "- executed: `true`",
        "- success: `false`",
        "- dry_run: `true`",
        "- execution_updated_at: ``",
        "- execution_summary: `summary`",
    )
    optional_view = run_web_app.parse_task_view_text(
        "task-0301-optional.md",
        task_markdown(
            "task-0301-optional",
            "TODO",
            optional_lines=optional_lines,
        ),
    )
    plain_view = run_web_app.parse_task_view_text(
        "task-0301-optional.md",
        task_markdown("task-0301-optional", "TODO"),
    )
    assert optional_view == plain_view
    assert optional_view is not None
    optional_false_view = run_web_app.parse_task_view_text(
        "task-0301-optional.md",
        task_markdown(
            "task-0301-optional",
            "TODO",
            optional_lines=("- execution_candidate: `false`",),
        ),
    )
    assert optional_false_view == plain_view
    optional_timestamp_view = run_web_app.parse_task_view_text(
        "task-0301-optional.md",
        task_markdown(
            "task-0301-optional",
            "TODO",
            optional_lines=(
                "- execution_updated_at: `2026-07-23 10:30 UTC`",
            ),
        ),
    )
    assert optional_timestamp_view == plain_view
    assert optional_view["completion_evidence"] is None
    assert optional_view["has_completion_evidence"] is False
    assert all(
        field_name not in optional_view
        for field_name in (
            (
                run_web_app.TASK_VIEW_OPTIONAL_TEXT_FIELDS
                - {"completion_evidence"}
            )
            | run_web_app.TASK_VIEW_OPTIONAL_BOOLEAN_FIELDS
            | run_web_app.TASK_VIEW_OPTIONAL_TIMESTAMP_FIELDS
        )
    )

    valid_base = task_markdown("task-0401-invalid", "TODO")
    invalid_cases = (
        (
            "task-0401-invalid.md",
            valid_base.replace("- summary: `Task summary`\n", ""),
            "missing_field",
            "summary",
        ),
        (
            "task-0401-invalid.md",
            valid_base + "- title: `Duplicate`\n",
            "duplicate_field",
            "title",
        ),
        (
            "task-0401-invalid.md",
            valid_base + "- unexpected: `value`\n",
            "unsupported_field",
            "unexpected",
        ),
        (
            "task-0401-invalid.md",
            task_markdown("not-a-task-id", "TODO"),
            "invalid_id",
            "id",
        ),
        (
            "task-0402-other.md",
            valid_base,
            "id_path_mismatch",
            "id",
        ),
        (
            "task-0401-invalid.md",
            task_markdown("task-0401-invalid", "UNKNOWN"),
            "invalid_status",
            "status",
        ),
        (
            "task-0401-invalid.md",
            task_markdown(
                "task-0401-invalid",
                "TODO",
                updated_at="2026-7-23 10:00 UTC",
            ),
            "invalid_updated_at",
            "updated_at",
        ),
        (
            "task-0401-invalid.md",
            task_markdown(
                "task-0401-invalid",
                "TODO",
                title="Unsafe\x00title",
            ),
            "invalid_text",
            "title",
        ),
        (
            "task-0401-invalid.md",
            task_markdown(
                "task-0401-invalid",
                "TODO",
                title="x" * 121,
            ),
            "field_too_long",
            "title",
        ),
        (
            "task-0401-invalid.md",
            valid_base.replace("- title: `Task title`", "- title: Task title"),
            "invalid_text",
            "title",
        ),
        (
            "task-0401-invalid.md",
            valid_base + "- executed: `True`\n",
            "invalid_text",
            "executed",
        ),
        (
            "task-0401-invalid.md",
            valid_base + "- execution_candidate: `candidate`\n",
            "invalid_text",
            "execution_candidate",
        ),
        (
            "task-0401-invalid.md",
            valid_base + "- source_command: ``\n",
            "invalid_text",
            "source_command",
        ),
        (
            "task-0401-invalid.md",
            valid_base + "- execution_updated_at: `yesterday`\n",
            "invalid_updated_at",
            "execution_updated_at",
        ),
        (
            "task-0401-invalid.md",
            valid_base
            + "- source_command: `/task`\n"
            + "- source_command: `/status`\n",
            "duplicate_field",
            "source_command",
        ),
    )
    for file_name, text, reason_code, reason_field in invalid_cases:
        invalid_view = run_web_app.parse_task_view_text(file_name, text)
        assert invalid_view is not None
        assert invalid_view == {
            "parse_state": "invalid",
            "group_id": "metadata_review",
            "display_rank": 0,
            "next_action": (
                "Review this task file's metadata outside Jarvis Console."
            ),
            "reason_code": reason_code,
            "reason_field": reason_field,
            "read_only": True,
        }
    assert (
        run_web_app.parse_task_view_text("task-template.md", valid_base) is None
    )
    assert run_web_app.parse_task_view_text("notes.md", valid_base) is None

    selected_items = [
        {"path": "memory/tasks/task-0507-invalid-b.md"},
        {"path": "memory/tasks/task-0506-invalid-a.md"},
        {"path": "memory/tasks/task-0501-todo-old.md"},
        {"path": "memory/tasks/task-0502-todo-new.md"},
        {"path": "memory/tasks/task-0503-blocked.md"},
        {"path": "memory/tasks/task-0504-done.md"},
        {"path": "memory/tasks/task-0505-doing.md"},
    ]
    task_texts = {
        "memory/tasks/task-0507-invalid-b.md": task_markdown(
            "task-0507-invalid-b",
            "TODO",
        ).replace("- summary: `Task summary`\n", ""),
        "memory/tasks/task-0506-invalid-a.md": task_markdown(
            "task-0506-invalid-a",
            "TODO",
        ).replace("- summary: `Task summary`\n", ""),
        "memory/tasks/task-0501-todo-old.md": task_markdown(
            "task-0501-todo-old",
            "TODO",
            updated_at="2026-07-22 10:00 UTC",
        ),
        "memory/tasks/task-0502-todo-new.md": task_markdown(
            "task-0502-todo-new",
            "TODO",
            updated_at="2026-07-23 10:00 UTC",
        ),
        "memory/tasks/task-0503-blocked.md": task_markdown(
            "task-0503-blocked",
            "BLOCKED",
        ),
        "memory/tasks/task-0504-done.md": task_markdown(
            "task-0504-done",
            "DONE",
        ),
        "memory/tasks/task-0505-doing.md": task_markdown(
            "task-0505-doing",
            "DOING",
        ),
    }

    def fixture_reader(path: Path) -> str:
        relative_path = path.relative_to(run_web_app.REPO_ROOT).as_posix()
        return task_texts[relative_path]

    first_projection = run_web_app.project_task_view_items(
        selected_items,
        text_reader=fixture_reader,
    )
    second_projection = run_web_app.project_task_view_items(
        selected_items,
        text_reader=fixture_reader,
    )
    assert first_projection == second_projection
    assert [item["path"] for item in first_projection] == [
        "memory/tasks/task-0506-invalid-a.md",
        "memory/tasks/task-0507-invalid-b.md",
        "memory/tasks/task-0503-blocked.md",
        "memory/tasks/task-0505-doing.md",
        "memory/tasks/task-0502-todo-new.md",
        "memory/tasks/task-0501-todo-old.md",
        "memory/tasks/task-0504-done.md",
    ]
    group_counts = {
        group_id: sum(
            item["task_view"]["group_id"] == group_id
            for item in first_projection
        )
        for group_id, _title in run_web_app.TASK_VIEW_GROUPS
    }
    assert group_counts == {
        "metadata_review": 2,
        "needs_attention": 1,
        "in_progress": 1,
        "ready": 2,
        "completed": 1,
    }

    cap_candidates = [
        *[
            {"path": f"memory/tasks/recent-note-{index}.md"}
            for index in range(9)
        ],
        {"path": "memory/tasks/task-0601-selected.md"},
        {"path": "memory/tasks/task-0602-not-selected.md"},
    ]
    cap_texts = {
        "memory/tasks/task-0601-selected.md": task_markdown(
            "task-0601-selected",
            "TODO",
        ),
        "memory/tasks/task-0602-not-selected.md": task_markdown(
            "task-0602-not-selected",
            "BLOCKED",
        ),
    }
    reader_calls: list[str] = []

    def cap_reader(path: Path) -> str:
        relative_path = path.relative_to(run_web_app.REPO_ROOT).as_posix()
        reader_calls.append(relative_path)
        return cap_texts[relative_path]

    capped_projection = run_web_app.project_task_view_items(
        cap_candidates[: run_web_app.OVERVIEW_MAX_ITEMS_PER_DIRECTORY],
        text_reader=cap_reader,
    )
    assert [item["path"] for item in capped_projection] == [
        "memory/tasks/task-0601-selected.md"
    ]
    assert reader_calls == ["memory/tasks/task-0601-selected.md"]

    direct_status, direct_payload = run_web_app.handle_get_api("/api/overview")
    repeat_status, repeat_payload = run_web_app.handle_get_api("/api/overview")
    assert direct_status == repeat_status == HTTPStatus.OK
    assert direct_payload == repeat_payload
    assert direct_payload["notes"][:2] == [
        "/api/overview discovery and basic details are read-only.",
        (
            "Only explicit Start / Complete Preview + Confirm may update "
            "a selected valid Task's status and updated_at. Record Completion "
            "Evidence Preview + Confirm may append one completion_evidence "
            "value and update only updated_at for an eligible DOING Task; it "
            "does not validate evidence, change status, complete, or execute "
            "the Task."
        ),
    ]
    assert all(
        "does not create or mutate tasks" not in note
        for note in direct_payload["notes"]
    )
    assert all("task_view" in item for item in direct_payload["tasks"])
    assert len(direct_payload["tasks"]) <= (
        run_web_app.OVERVIEW_MAX_ITEMS_PER_DIRECTORY
    )
    assert (
        [group["group_id"] for group in direct_payload["recent_groups"]][0]
        == "tasks"
    )
    assert all(
        "task_view" not in item
        for item in direct_payload["recent_groups"][0]["items"]
    )

    server = run_web_app.ThreadingHTTPServer(
        (run_web_app.DEFAULT_HOST, 0),
        run_web_app.JarvisConsoleHandler,
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    port = int(server.server_address[1])
    try:
        connection = HTTPConnection(run_web_app.DEFAULT_HOST, port, timeout=10)
        connection.request("GET", "/api/overview")
        response = connection.getresponse()
        http_payload = json.loads(response.read().decode("utf-8"))
        response_status = response.status
        connection.close()
        assert response_status == HTTPStatus.OK
        assert http_payload == direct_payload
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
    assert not server_thread.is_alive()

    app_js = Path(run_web_app.WEB_ROOT, "app.js").read_text(encoding="utf-8")
    web_app_source = Path(run_web_app.__file__).read_text(encoding="utf-8")
    for exact_text in (
        "Actionable Task View",
        "Read-only discovery",
        "Confirmed bounded Task updates only",
        "Preview + Confirm required",
        "Record Completion Evidence appends one evidence value and updates only updated_at for an eligible DOING Task.",
        "Needs metadata review",
        "Needs attention",
        "In progress",
        "Ready",
        "Completed",
        "Shows up to 10 files selected by existing Recent Tasks discovery before task validation; this is not the full backlog.",
        "Display order:",
        "Displayed total:",
        "Status",
        "Title",
        "Task ID",
        "Updated",
        "Summary",
        "Completion evidence",
        "Record Completion Evidence",
        "Next action",
        "Path",
        "Read-only",
    ):
        assert exact_text in app_js
    for _status, (_group_id, _rank, next_action) in (
        expected_status_rules.items()
    ):
        assert next_action in web_app_source
    renderer_source = app_js.split(
        "function actionableTaskItemMarkup",
        1,
    )[1].split("function memoryDraftPrompt", 1)[0]
    for escaping_contract in (
        "escapeHtml(title)",
        "escapeHtml(status)",
        "escapeHtml(taskId)",
        "escapeHtml(updatedAt)",
        "escapeHtml(summary)",
        "escapeHtml(accessClass)",
        "escapeHtml(accessLabel)",
        'escapeHtml(view.next_action || "")',
        'escapeHtml(item.path || "")',
        "escapeHtml(view.id)",
        "escapeHtml(action)",
    ):
        assert escaping_contract in renderer_source
    assert (
        'const action = valid && view.status === "TODO"\n'
        '    ? "start"\n'
        '    : valid && view.status === "DOING"\n'
        '      ? "complete"\n'
        '      : "";'
    ) in renderer_source
    assert "<form" not in renderer_source
    assert renderer_source.count(
        'fetch("/api/task-transition/preview"'
    ) == 1
    assert renderer_source.count(
        'fetch("/api/task-transition/confirm"'
    ) == 1
    assert renderer_source.count(
        'fetch("/api/completion-evidence/preview"'
    ) == 1
    assert renderer_source.count(
        'fetch("/api/completion-evidence/confirm"'
    ) == 1
    assert renderer_source.count("fetch(") == 4
    assert "onclick" not in renderer_source

    escape_source = "function escapeHtml" + app_js.split(
        "function escapeHtml",
        1,
    )[1].split("function truncateText", 1)[0]
    item_renderer_source = (
        "function actionableTaskItemMarkup"
        + app_js.split(
            "function actionableTaskItemMarkup",
            1,
        )[1].split("function taskTransitionReceiptMarkup", 1)[0]
    )
    badge_harness = (
        f"{escape_source}\n"
        "const taskTransitionLastReceipt = null;\n"
        "const completionEvidenceLastReceipt = null;\n"
        "function taskTransitionReceiptMarkup() { return \"\"; }\n"
        "function completionEvidenceReceiptMarkup() { return \"\"; }\n"
        f"{item_renderer_source}\n"
        """
function fixtureItem(status, parseState = "valid") {
  const valid = parseState === "valid";
  return {
    path: `memory/tasks/task-9001-${String(status).toLowerCase()}.md`,
    task_view: valid
      ? {
          parse_state: "valid",
          id: `task-9001-${String(status).toLowerCase().replaceAll("_", "-")}`,
          title: `${status} title`,
          status,
          updated_at: "2026-07-23 10:00 UTC",
          summary: `${status} summary`,
          next_action: "Review next action.",
        }
      : {
          parse_state: "invalid",
          reason_code: "missing_field",
          reason_field: "summary",
          next_action: "Repair metadata.",
        },
  };
}
const guardedBadge =
  '<span class="overview-badge approval-needed">Preview + Confirm required</span>';
const readOnlyBadge =
  '<span class="overview-badge read-only">Read-only</span>';
for (const status of ["TODO", "DOING"]) {
  const html = actionableTaskItemMarkup(fixtureItem(status));
  if (!html.includes(guardedBadge) || html.includes(readOnlyBadge)) {
    throw new Error(`${status} did not render the guarded badge exactly`);
  }
}
for (const status of ["DONE", "FAILED", "BLOCKED", "NEEDS_APPROVAL"]) {
  const html = actionableTaskItemMarkup(fixtureItem(status));
  if (!html.includes(readOnlyBadge) || html.includes(guardedBadge)) {
    throw new Error(`${status} did not render the read-only badge exactly`);
  }
  if (html.includes("preview-task-transition")) {
    throw new Error(`${status} unexpectedly rendered a transition action`);
  }
}
const metadataHtml = actionableTaskItemMarkup(
  fixtureItem("METADATA_REVIEW", "invalid"),
);
if (!metadataHtml.includes(readOnlyBadge) ||
    metadataHtml.includes(guardedBadge) ||
    metadataHtml.includes("preview-task-transition")) {
  throw new Error("metadata review did not render read-only exactly");
}
"""
    )
    badge_completed = subprocess.run(
        ("node", "-"),
        cwd=Path(__file__).resolve().parent,
        input=badge_harness,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=10,
    )
    assert badge_completed.returncode == 0, (
        "Actionable Task badge renderer harness failed: "
        f"{badge_completed.stdout}\n{badge_completed.stderr}"
    )
    parser_projection_source = (
        inspect.getsource(run_web_app.parse_task_view_text)
        + inspect.getsource(run_web_app.project_task_view_items)
    ).lower().replace("fullmatch", "")
    assert "llm" not in parser_projection_source
    assert "openai" not in parser_projection_source
    assert artifact_snapshot() == before_artifacts


def main() -> None:
    _test_tasks_reports_registry_copy()
    _test_actionable_task_view_vertical_slice()
    _test_director_renderer_fails_closed_on_malformed_nested_data()
    _test_read_only_git_preserves_porcelain_status()
    _test_project_control_snapshot()
    _test_project_control_reporting_state_invariants()
    _test_owner_decision_contract()
    _test_project_control_registry_primitives()
    _test_recent_milestone_evidence_contract()
    _test_evaluate_idea_vertical_slice()
    _test_evaluate_idea_create_task_vertical_slice()
    _test_evaluate_idea_create_task_client_state_machine()
    run_web_app.run_self_test()
    _test_codex_review_vertical_slice()
    _test_create_local_task_vertical_slice()

    status_code, status = run_web_app.handle_get_api("/api/status")
    assert status_code == HTTPStatus.OK
    assert status["ok"] is True
    assert status["console"] == "jarvis-console"
    assert status["mode"] == "local-only"
    assert status["registry_read_only"] is True
    assert len(status["skills"]) == 6
    assert {skill["skill_id"] for skill in status["skills"]}.issuperset(
        {"research_council", "daily_ai_radar", "hermes_manager"}
    )
    assert all({"docs", "tests", "examples", "action_guide", "when_to_use"}.issubset(skill) for skill in status["skills"])

    skill_code, skill_detail = run_web_app.handle_get_api("/api/skill", "skill_id=hermes_manager")
    assert skill_code == HTTPStatus.OK
    assert skill_detail["ok"] is True
    assert skill_detail["skill"]["skill_id"] == "hermes_manager"
    assert skill_detail["skill"]["docs"]
    assert skill_detail["skill"]["tests"]
    assert skill_detail["skill"]["action_guide"]
    assert skill_detail["skill"]["primary_next_action_label"] == "Open Hermes Manager"

    research_code, research_detail = run_web_app.handle_get_api("/api/skill", "skill_id=research_council")
    assert research_code == HTTPStatus.OK
    assert research_detail["skill"]["handoff_steps"][2] == "In the launcher, paste your idea, click Idea \uad6c\uccb4\ud654, then run the report."
    daily_code, daily_detail = run_web_app.handle_get_api("/api/skill", "skill_id=daily_ai_radar")
    assert daily_code == HTTPStatus.OK
    assert daily_detail["skill"]["handoff_steps"][2] == (
        "Read the generated radar report and review Executive Summary, Candidate Highlights, and Governance Notes."
    )
    assert "Radar recommendations are candidates, not implementation approval." in daily_detail["skill"]["safety_notes"]

    missing_skill_code, missing_skill = run_web_app.handle_get_api("/api/skill", "skill_id=missing")
    assert missing_skill_code == HTTPStatus.NOT_FOUND
    assert missing_skill["error"] == "unknown_skill"

    overview_code, overview = run_web_app.handle_get_api("/api/overview")
    assert overview_code == HTTPStatus.OK
    assert overview["ok"] is True
    assert overview["mode"] == "read-only"
    project_control = overview["project_control"]
    assert project_control["version"] == "project_control.v0.1F"
    assert project_control["mode"] == "read-only"
    assert project_control["source"] == "docs/master-plan.md"
    assert len(project_control["project_cards"]) == 1
    project_card = project_control["project_cards"][0]
    assert project_card["project_id"] == "jarvis-core"
    assert project_card["branch"] == overview["repo"]["branch"]
    assert project_card["live_head"] == overview["repo"]["head_short"]
    assert project_card["known_protected_untracked"] == ["jarvis.bat"]
    assert project_card["validation_commands"] == ["git status --short", "git diff --check"]
    owner_summary = project_card["owner_summary"]
    assert owner_summary["current_reason"]
    assert owner_summary["owner_outcome"]
    assert owner_summary["recent_completed"]
    assert owner_summary["approval_state"] in run_web_app.MASTER_PLAN_APPROVAL_STATES
    assert len(project_card["workstreams"]) == 6
    assert [item["workstream_id"] for item in project_card["workstreams"]] == [
        "hermes-manager",
        "memory-skills",
        "jarvis-console",
        "research-council",
        "daily-ai-radar",
        "task-discord-dashboard",
    ]
    assert all(item["read_only"] is True for item in project_card["workstreams"])
    director_report_payload = project_card["director_report"]
    assert director_report_payload["contract_type"] == DIRECTOR_CONTRACT_TYPE
    assert director_report_payload["version"] == DIRECTOR_VERSION
    assert director_report_payload["source_contract_type"] == MANAGER_CONTRACT_TYPE
    assert director_report_payload["derived_view"] is True
    assert director_report_payload["read_only"] is True
    assert director_report_payload["authority_boundary"] == DIRECTOR_AUTHORITY_BOUNDARY
    assert director_report_payload["completed_packages"]
    assert "evidence_summary" not in director_report_payload
    assert "source_conflicts" not in director_report_payload
    normalized_director_payload = dict(director_report_payload)
    normalized_director_payload.pop("read_only")
    assert normalize_director_report(normalized_director_payload)
    manager_report_payload = project_card["manager_report"]
    assert manager_report_payload["contract_type"] == MANAGER_CONTRACT_TYPE
    assert manager_report_payload["version"] == MANAGER_REPORTING_VERSION
    assert manager_report_payload["source_of_truth"] == "master_plan"
    assert manager_report_payload["derived_view"] is True
    assert manager_report_payload["read_only"] is True
    assert manager_report_payload["authority_boundary"] == "derived_reporting_only"
    assert manager_report_payload["completed_work_packages"]
    assert all(
        item["commit_hash"]
        for item in manager_report_payload["completed_work_packages"]
    )
    normalized_manager_payload = dict(manager_report_payload)
    normalized_manager_payload.pop("read_only")
    normalized_manager_payload.pop("authority_boundary")
    assert normalize_manager_report(normalized_manager_payload)
    assert director_report_payload["status"] == manager_report_payload["status"]
    assert (
        director_report_payload["owner_action"]
        == manager_report_payload["owner_action"]
    )
    assert (
        director_report_payload["owner_decision"]
        == manager_report_payload["owner_decision"]
    )
    current_snapshot = run_web_app.read_master_plan_snapshot()
    reporting_evidence = project_card["recent_milestone_evidence"]
    available_hashes = {
        overview["repo"]["head"],
        *[commit["hash"] for commit in reporting_evidence["commits"]],
    }
    expected_missing_references = []
    verified_head = current_snapshot["verified_implementation_head"]
    if not any(commit.startswith(verified_head) for commit in available_hashes):
        expected_missing_references.append(
            "Verified implementation HEAD is absent from live Git evidence"
        )
    expected_missing_references.extend(
        (
            f"Checkpoint package {package['work_package_id']} commit is absent "
            "from Git evidence"
        )
        for package in current_snapshot["manager_reporting_work_packages"]
        if package["commit_hash"] not in available_hashes
    )
    if expected_missing_references:
        assert manager_report_payload["source_conflicts"]
        assert manager_report_payload["status"] == "blocked"
        assert manager_report_payload["owner_action"] == "decision_required"
        assert manager_report_payload["owner_decision"]
        assert project_card["status"] == "attention"
        assert all(
            conflict in manager_report_payload["source_conflicts"]
            for conflict in expected_missing_references
        )
        assert all(
            conflict in project_card["attention_reasons"]
            for conflict in manager_report_payload["source_conflicts"]
        )
    elif current_snapshot["approval_state"] == "none":
        assert manager_report_payload["source_conflicts"] == []
        assert manager_report_payload["owner_action"] == "none"
        assert manager_report_payload["owner_decision"] == ""
        assert project_card["status"] == "observed"
        assert project_card["attention_reasons"] == []
    owner_decision_payload = project_card["owner_decision"]
    assert owner_decision_payload["contract_type"] == CONTRACT_TYPE
    assert owner_decision_payload["version"] == OWNER_DECISION_VERSION
    assert owner_decision_payload["project_id"] == PROJECT_ID
    assert owner_decision_payload["status"] == "selection_required"
    assert owner_decision_payload["authority_boundary"] == AUTHORITY_BOUNDARY
    assert owner_decision_payload["recommended_workstream_id"] == run_web_app.read_master_plan_snapshot()[
        "owner_decision_recommended_workstream_id"
    ]
    assert owner_decision_payload["selected_workstream_id"] is None
    assert owner_decision_payload["desired_outcome"] is None
    assert owner_decision_payload["response_template"] == RESPONSE_TEMPLATE
    assert owner_decision_payload["read_only"] is True
    assert len(owner_decision_payload["candidates"]) == 6
    assert normalize_owner_decision(owner_decision_payload) == build_owner_decision_from_snapshot(
        run_web_app.read_master_plan_snapshot()
    )
    recent_evidence = project_card["recent_milestone_evidence"]
    assert recent_evidence["contract_type"] == RECENT_MILESTONE_CONTRACT_TYPE
    assert recent_evidence["version"] == RECENT_MILESTONE_VERSION
    assert recent_evidence["observed_head"] == overview["repo"]["head"]
    assert recent_evidence["head_matches_latest_commit"] is True
    assert 1 <= len(recent_evidence["commits"]) <= 5
    assert recent_evidence["commits"][0]["is_head"] is True
    assert all(commit["read_only"] is True for commit in recent_evidence["commits"])
    assert all(not commit["protected_path_present"] for commit in recent_evidence["commits"])
    assert project_card["locked_capabilities"] == project_card["forbidden_actions"]
    assert any("commit" in item.lower() for item in project_card["forbidden_actions"])
    assert overview["repo"]["head_short"]
    assert "jarvis.bat" in overview["repo"]["protected_path_note"]
    assert len(overview["tasks"]) <= run_web_app.OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["reports"]) <= run_web_app.OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["checkpoints"]) <= run_web_app.OVERVIEW_MAX_TOTAL_ITEMS
    assert len(overview["docs_examples"]) <= run_web_app.OVERVIEW_MAX_TOTAL_ITEMS
    assert [group["group_id"] for group in overview["recent_groups"]] == [
        "tasks",
        "reports",
        "checkpoints",
        "docs_examples",
    ]
    assert [group["title"] for group in overview["recent_groups"]] == [
        "Recent Tasks",
        "Recent Reports",
        "Recent Checkpoints",
        "Recent Docs / Examples",
    ]
    assert all(group["read_only"] is True for group in overview["recent_groups"])
    assert overview["discovery"]["max_items_per_directory"] == run_web_app.OVERVIEW_MAX_ITEMS_PER_DIRECTORY
    assert overview["discovery"]["allowed_extensions"] == sorted(run_web_app.OVERVIEW_ALLOWED_EXTENSIONS)
    assert ".git" in overview["discovery"]["excluded"]
    assert "__pycache__" in overview["discovery"]["excluded"]
    assert any(skill["skill_id"] == "daily_ai_radar" for skill in overview["skills"])
    overview_items = [
        item
        for section in ("tasks", "reports", "checkpoints", "docs_examples")
        for item in overview[section]
    ]
    overview_items.extend(item for group in overview["recent_groups"] for item in group["items"])
    overview_items.extend(item for skill in overview["skills"] for item in skill["recent_items"])
    assert overview_items
    for item in overview_items:
        run_web_app.assert_overview_item_safety(item)
    assert any(item["source_area"] == "jarvis_console" for item in overview["checkpoints"] + overview["docs_examples"])
    assert any(item["item_type"] == "checkpoint" for item in overview["checkpoints"])
    assert all(item["item_type"] == "task" for item in overview["tasks"])
    assert all(item["item_type"] == "report" for item in overview["reports"])
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / "sample.md") is True
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / "sample.py") is False
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / ".git" / "config.txt") is False
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / "__pycache__" / "sample.md") is False
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / ".hidden.md") is False
    assert run_web_app.is_overview_candidate_path(run_web_app.REPO_ROOT / "docs" / "secret-plan.md") is False
    assert run_web_app.is_overview_candidate_path(
        run_web_app.REPO_ROOT / "docs" / "sample.md",
        run_web_app.REPO_ROOT / "reports",
    ) is False
    history_code, history = run_web_app.handle_get_api("/api/history")
    assert history_code == HTTPStatus.OK
    assert history["ok"] is True
    assert history["mode"] == "read-only"
    assert history["repo"]["head_short"]
    assert "root" not in history["repo"]
    assert "jarvis.bat" in history["repo"]["protected_path_note"]
    assert history["recent_commits"]
    assert len(history["recent_commits"]) <= run_web_app.HISTORY_MAX_COMMITS
    for commit in history["recent_commits"]:
        run_web_app.assert_history_commit_safety(commit)
    history_items = history["checkpoint_docs"] + history["related_items"]
    assert history_items
    for item in history_items:
        run_web_app.assert_overview_item_safety(item)
        assert run_web_app.is_history_candidate_name(Path(item["path"]))
    assert any(item["path"] == "docs/jarvis-console-v0.1-checkpoint.md" for item in history["checkpoint_docs"])
    assert [item["path"] for item in history["discovery"]["safe_directories"]] == [
        "docs",
        "apps/jarvis-console",
        "apps/hermes-manager-pilot/examples",
        "apps/daily-ai-radar/examples",
    ]
    assert ".git" in history["discovery"]["excluded"]
    assert "__pycache__" in history["discovery"]["excluded"]
    assert "This view is read-only." in history["notes"]
    assert "It does not create commits or checkpoints." in history["notes"]

    memory_code, memory = run_web_app.handle_get_api("/api/memory-skills")
    assert memory_code == HTTPStatus.OK
    assert memory["ok"] is True
    assert memory["mode"] == "read-only"
    assert memory["phase"] == "phase_2b_preview_only"
    assert memory["read_only"] is True
    assert memory["sample"] is True
    assert memory["preview_only"] is True
    assert memory["not_saved"] is True
    assert memory["no_persistence"] is True
    assert memory["runtime_write"] is False
    assert memory["save_endpoint"] is False
    assert memory["post_endpoints"] == "preview_only"
    assert memory["write_endpoints"] is False
    assert memory["preview_endpoint"] == run_web_app.MEMORY_PREVIEW_ENDPOINT
    assert memory["preview_endpoint_write_free"] is True
    assert memory["approval_gated_save_api"] is False
    assert memory["approval_gated_save_endpoint"] is False
    assert memory["candidate_write_helper"] == "tests_only"
    assert memory["request_guard"] == "internal_tests_only"
    assert memory["preview_token_subsystem"] == "internal_tests_only"
    assert memory["guarded_save_coordinator"] == "internal_tests_only"
    assert memory["http_metadata_adapter"] == "internal_tests_only"
    assert memory["session_bootstrap_primitive"] == "internal_tests_only"
    assert memory["save_preparation_coordinator"] == "internal_tests_only"
    assert memory["persisted_original_text_preview"] is False
    assert memory["preview_token_issuance"] is False
    assert memory["ui_save_action"] is False
    assert memory["voice_inbox_auto_save"] is False
    assert len(memory["candidates"]) == 3
    assert "Review Candidate" in memory["allowed_actions"]
    assert "Preview Local Candidate" in memory["allowed_actions"]
    assert "Copy Candidate" in memory["allowed_actions"]
    assert "Copy Skill Draft Prompt" in memory["allowed_actions"]
    assert "Open Skill Details" in memory["allowed_actions"]
    assert any("Voice Inbox" in item for item in memory["guidance"])
    assert any("No automatic memory save." == item for item in memory["safety_boundary"])
    assert any("No runtime file write." == item for item in memory["safety_boundary"])
    assert any("No UI save action." == item for item in memory["safety_boundary"])
    assert "No approval-gated save API endpoint." in memory["safety_boundary"]
    for candidate in memory["candidates"]:
        run_web_app.assert_memory_candidate_safety(candidate)

    run_web_app.run_memory_request_guard_token_self_tests()

    with TemporaryDirectory(prefix="jarvis-localappdata-") as fake_local_appdata_text:
        fake_local_appdata = Path(fake_local_appdata_text)
        windows_default_state = run_web_app.resolve_memory_skills_state_paths(
            env={"LOCALAPPDATA": str(fake_local_appdata)},
            is_windows=True,
        )
        assert windows_default_state["ok"] is True
        assert windows_default_state["source"] == "default_windows_localappdata"
        assert windows_default_state["state_root"] == run_web_app.normalize_filesystem_path(
            fake_local_appdata / "Jarvis-Core"
        )
        assert windows_default_state["candidate_dir"] == run_web_app.normalize_filesystem_path(
            fake_local_appdata / "Jarvis-Core" / "memory-skills" / "candidates"
        )
        assert windows_default_state["repo_internal"] is False
        assert windows_default_state["will_create_directory"] is False
        assert windows_default_state["will_write_files"] is False
        assert not windows_default_state["state_root"].exists()
        assert not windows_default_state["candidate_dir"].exists()

    with TemporaryDirectory(prefix="jarvis-home-") as fake_home_text:
        fake_home = Path(fake_home_text)
        home_default_state = run_web_app.resolve_memory_skills_state_paths(env={}, home_dir=fake_home, is_windows=False)
        assert home_default_state["ok"] is True
        assert home_default_state["source"] == "default_home"
        assert home_default_state["candidate_dir"] == run_web_app.normalize_filesystem_path(
            fake_home / ".jarvis-core" / "memory-skills" / "candidates"
        )
        assert not home_default_state["state_root"].exists()
        assert not home_default_state["candidate_dir"].exists()

    with TemporaryDirectory(prefix="jarvis-state-override-") as fake_override_root_text:
        fake_override_root = Path(fake_override_root_text)
        override_state = run_web_app.resolve_memory_skills_state_paths(
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(fake_override_root)}
        )
        assert override_state["ok"] is True
        assert override_state["source"] == "env_override"
        assert override_state["candidate_dir"] == run_web_app.normalize_filesystem_path(
            fake_override_root / "memory-skills" / "candidates"
        )
        assert not override_state["candidate_dir"].exists()
        assert not override_state["candidate_dir"].parent.exists()

    relative_override_state = run_web_app.resolve_memory_skills_state_paths(
        env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: "relative-state"}
    )
    assert relative_override_state["ok"] is False
    assert relative_override_state["error"] == "local_state_dir_must_be_absolute"

    repo_internal_state = run_web_app.resolve_memory_skills_state_paths(
        env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(run_web_app.REPO_ROOT / ".jarvis-local")}
    )
    assert repo_internal_state["ok"] is False
    assert repo_internal_state["error"] == "local_state_dir_inside_repo"
    assert repo_internal_state["repo_internal"] is True
    assert run_web_app.is_path_inside_repo(
        run_web_app.REPO_ROOT / ".jarvis-local" / "memory-skills" / "candidates"
    ) is True
    traversal_like_state = run_web_app.resolve_memory_skills_state_paths(
        env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(run_web_app.REPO_ROOT / "apps" / ".." / ".jarvis-local")}
    )
    assert traversal_like_state["ok"] is False
    assert traversal_like_state["error"] == "local_state_dir_inside_repo"
    fake_reparse_stat = type(
        "FakeReparseStat",
        (),
        {"st_mode": 0, "st_file_attributes": 0x0400},
    )()
    assert run_web_app.filesystem_stat_is_reparse_point(fake_reparse_stat) is True
    assert not run_web_app.APP_ROOT.joinpath("state").exists()
    assert not run_web_app.REPO_ROOT.joinpath(".jarvis-local").exists()

    preview_code, preview = run_web_app.handle_post_api(
        run_web_app.MEMORY_PREVIEW_ENDPOINT,
        {
            "source": "voice_inbox",
            "title": "Repeated workflow preview",
            "cleaned_text": "Preview this repeated workflow before any future local save.",
            "original_text_preview": "이 반복 작업 skill 후보로 기억해줘",
            "candidate_type": "repeated_workflow",
            "confidence": "medium",
            "tags": ["voice_inbox", "preview"],
            "safety_notes": ["Preview only; no local memory is written."],
        },
    )
    assert preview_code == HTTPStatus.OK
    assert preview["preview_only"] is True
    assert preview["not_saved"] is True
    assert preview["no_persistence"] is True
    assert preview["runtime_write"] is False
    assert preview["save_endpoint"] is False
    assert preview["privacy_warning"]
    assert preview["candidate_preview"]["status"] == "preview_only"
    assert preview["candidate_preview"]["user_approved_at"] is None
    assert preview["candidate_preview"]["id"] == "preview_only_not_persisted"
    assert len(preview["candidate_preview"]["original_text_preview"]) <= run_web_app.MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS
    assert run_web_app.handle_post_api(run_web_app.MEMORY_PREVIEW_ENDPOINT, {})[0] == HTTPStatus.BAD_REQUEST
    assert run_web_app.handle_post_api(run_web_app.MEMORY_PREVIEW_ENDPOINT, {"cleaned_text": ""})[0] == HTTPStatus.BAD_REQUEST
    assert run_web_app.handle_post_api(
        run_web_app.MEMORY_PREVIEW_ENDPOINT,
        {"cleaned_text": "x" * (run_web_app.MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS + 1)},
    )[0] == HTTPStatus.BAD_REQUEST
    assert run_web_app.parse_json_body(b"{not json")[0] == HTTPStatus.BAD_REQUEST
    traversal_preview_code, traversal_preview = run_web_app.handle_post_api(
        run_web_app.MEMORY_PREVIEW_ENDPOINT,
        {"cleaned_text": "../memory/tasks/secret", "candidate_type": "../escape", "source": "C:\\temp"},
    )
    assert traversal_preview_code == HTTPStatus.OK
    assert traversal_preview["candidate_preview"]["id"] == "preview_only_not_persisted"

    invalid_preview_payloads = (
        {"cleaned_text": "\ud800"},
        {"cleaned_text": "valid", "title": "bad\udfff"},
        {"cleaned_text": "valid", "original_text_preview": "bad\ud800"},
        {"cleaned_text": "valid", "tags": ["bad\ud800"]},
        {"cleaned_text": "valid", "safety_notes": ["bad\udfff"]},
        {"cleaned_text": "valid", "candidate_type": "bad\ud800"},
        {"cleaned_text": "valid", "confidence": "bad\ud800"},
        {"cleaned_text": "valid", "source": "bad\ud800"},
        {"cleaned_text": "bad\x00text"},
    )
    for invalid_preview_payload in invalid_preview_payloads:
        invalid_unicode_code, invalid_unicode_preview = run_web_app.handle_post_api(
            run_web_app.MEMORY_PREVIEW_ENDPOINT,
            invalid_preview_payload,
        )
        assert invalid_unicode_code == HTTPStatus.BAD_REQUEST
        assert invalid_unicode_preview == {"ok": False, "error": "invalid_unicode"}

    valid_unicode_code, valid_unicode_preview = run_web_app.handle_post_api(
        run_web_app.MEMORY_PREVIEW_ENDPOINT,
        {
            "title": "정상 한글 😀 𐐷",
            "cleaned_text": "반복 작업을 안전하게 정리 😀 𐐷",
            "original_text_preview": "원문 미리보기 😀",
            "tags": ["한글", "emoji-😀"],
            "safety_notes": ["정상 Unicode만 저장 후보로 사용 😀"],
        },
    )
    assert valid_unicode_code == HTTPStatus.OK
    assert valid_unicode_preview["candidate_preview"]["title"] == "정상 한글 😀 𐐷"
    assert valid_unicode_preview["candidate_preview"]["cleaned_text"] == "반복 작업을 안전하게 정리 😀 𐐷"

    save_dry_run_request = {
        "candidate_preview": preview["candidate_preview"],
        "explicit_confirmation": True,
        "privacy_reviewed": True,
        "save_scope": "local_only",
    }
    save_dry_run_code, save_dry_run = run_web_app.validate_memory_skills_save_dry_run(save_dry_run_request)
    assert save_dry_run_code == HTTPStatus.OK
    assert save_dry_run["dry_run"] is True
    assert save_dry_run["valid_for_local_save"] is True
    assert save_dry_run["will_write_files"] is False
    assert save_dry_run["will_create_directory"] is False
    assert save_dry_run["save_endpoint_enabled"] is False
    assert save_dry_run["phase"] == run_web_app.MEMORY_SAVE_DRY_RUN_PHASE
    assert save_dry_run["candidate"]["status"] == "preview_only"
    assert save_dry_run["candidate"]["user_approved_at"] is None
    assert any("Nothing has been saved" in warning for warning in save_dry_run["warnings"])

    def assert_save_dry_run_rejected(body, expected_error):
        rejected_code, rejected = run_web_app.validate_memory_skills_save_dry_run(body)
        assert rejected_code == HTTPStatus.BAD_REQUEST
        assert rejected["dry_run"] is True
        assert rejected["valid_for_local_save"] is False
        assert rejected["will_write_files"] is False
        assert rejected["will_create_directory"] is False
        assert rejected["save_endpoint_enabled"] is False
        assert rejected["error"] == expected_error

    def save_dry_run_body(body_updates=None, candidate_updates=None, remove_body_fields=(), remove_candidate_fields=()):
        body = dict(save_dry_run_request)
        body["candidate_preview"] = dict(preview["candidate_preview"])
        if body_updates:
            body.update(body_updates)
        if candidate_updates:
            body["candidate_preview"].update(candidate_updates)
        for field in remove_body_fields:
            body.pop(field, None)
        for field in remove_candidate_fields:
            body["candidate_preview"].pop(field, None)
        return body

    assert_save_dry_run_rejected([], "request_body_must_be_object")
    assert_save_dry_run_rejected(save_dry_run_body(remove_body_fields=("candidate_preview",)), "missing_candidate_preview")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"candidate_preview": []}), "candidate_preview_must_be_object")
    assert_save_dry_run_rejected(save_dry_run_body(remove_body_fields=("explicit_confirmation",)), "explicit_confirmation_required")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"explicit_confirmation": False}), "explicit_confirmation_required")
    assert_save_dry_run_rejected(save_dry_run_body(remove_body_fields=("privacy_reviewed",)), "privacy_review_required")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"privacy_reviewed": False}), "privacy_review_required")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"save_scope": "repo"}), "invalid_save_scope")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"status": "saved"}), "candidate_must_be_preview_only")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"suggested_skill_id": "hermes_manager"}), "invalid_suggested_skill_id")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"confirmation_required": False}), "confirmation_required_expected")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"user_approved_at": "2026-07-08"}), "candidate_already_approved")
    assert_save_dry_run_rejected(save_dry_run_body(remove_candidate_fields=("cleaned_text",)), "missing_cleaned_text")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"cleaned_text": ""}), "empty_cleaned_text")
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"cleaned_text": "x" * (run_web_app.MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS + 1)}),
        "cleaned_text_too_long",
    )
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"title": "x" * (run_web_app.MEMORY_PREVIEW_TITLE_MAX_CHARS + 1)}),
        "title_too_long",
    )
    assert_save_dry_run_rejected(
        save_dry_run_body(
            candidate_updates={"original_text_preview": "x" * (run_web_app.MEMORY_PREVIEW_ORIGINAL_TEXT_MAX_CHARS + 1)}
        ),
        "original_text_preview_too_long",
    )
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"candidate_type": "../escape"}), "invalid_candidate_type")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"confidence": "certain"}), "invalid_confidence")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"source": "C:\\temp"}), "invalid_source")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"tags": "not-list"}), "tags_must_be_list")
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"tags": [f"tag{i}" for i in range(run_web_app.MEMORY_PREVIEW_MAX_TAGS + 1)]}),
        "too_many_tags",
    )
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"tags": ["x" * (run_web_app.MEMORY_PREVIEW_TAG_MAX_CHARS + 1)]}),
        "tags_item_too_long",
    )
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"safety_notes": "not-list"}), "safety_notes_must_be_list")
    assert_save_dry_run_rejected(
        save_dry_run_body(
            candidate_updates={
                "safety_notes": [f"note{i}" for i in range(run_web_app.MEMORY_PREVIEW_MAX_SAFETY_NOTES + 1)]
            }
        ),
        "too_many_safety_notes",
    )
    assert_save_dry_run_rejected(
        save_dry_run_body(
            candidate_updates={"safety_notes": ["x" * (run_web_app.MEMORY_PREVIEW_SAFETY_NOTE_MAX_CHARS + 1)]}
        ),
        "safety_notes_item_too_long",
    )
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"raw_transcript": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"full_transcript": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"original_text": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"storage_path": "memory/skills/x.json"}), "path_field_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(body_updates={"repo_path": "memory/skills/x.json"}), "path_field_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"file_path": "memory/tasks/x.json"}), "path_field_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"candidate_file": "candidate.json"}), "path_field_not_allowed")
    assert_save_dry_run_rejected(save_dry_run_body(candidate_updates={"id": "../memory/tasks/x"}), "invalid_candidate_id")
    for scalar_field in (
        "title",
        "cleaned_text",
        "original_text_preview",
        "next_action",
        "privacy_note",
        "candidate_type",
        "confidence",
        "source",
    ):
        assert_save_dry_run_rejected(
            save_dry_run_body(candidate_updates={scalar_field: "bad\ud800"}),
            "invalid_unicode",
        )
    for list_field in ("tags", "safety_notes"):
        assert_save_dry_run_rejected(
            save_dry_run_body(candidate_updates={list_field: ["bad\udfff"]}),
            "invalid_unicode",
        )
    assert_save_dry_run_rejected(
        save_dry_run_body(candidate_updates={"cleaned_text": "bad\x00text"}),
        "invalid_unicode",
    )

    serialized_code, serialized_error, serialized_candidate = run_web_app.serialize_memory_candidate_json(
        {"title": "정상 한글 😀 𐐷"},
        max_bytes=1024,
    )
    assert serialized_code == HTTPStatus.OK
    assert serialized_error == ""
    assert json.loads(serialized_candidate.decode("utf-8"))["title"] == "정상 한글 😀 𐐷"
    assert run_web_app.serialize_memory_candidate_json({"title": "bad\ud800"})[:2] == (
        HTTPStatus.BAD_REQUEST,
        "invalid_unicode",
    )
    assert run_web_app.serialize_memory_candidate_json({"title": "bad\x00text"})[:2] == (
        HTTPStatus.BAD_REQUEST,
        "invalid_unicode",
    )
    assert run_web_app.serialize_memory_candidate_json({"title": "too large"}, max_bytes=1)[:2] == (
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        "candidate_json_too_large",
    )

    def assert_save_endpoint_rejected(body, expected_error, expected_status=HTTPStatus.BAD_REQUEST):
        rejected_code, rejected = run_web_app.save_memory_skills_candidate(body)
        assert rejected_code == expected_status
        assert rejected["ok"] is False
        assert rejected["saved"] is False
        assert rejected["error"] == expected_error
        assert rejected["skill_created"] is False
        assert rejected["registry_modified"] is False
        assert rejected["will_run_automatically"] is False
        assert "candidate_file" not in rejected

    assert_save_endpoint_rejected(save_dry_run_body(remove_body_fields=("explicit_confirmation",)), "explicit_confirmation_required")
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"explicit_confirmation": False}), "explicit_confirmation_required")
    assert_save_endpoint_rejected(save_dry_run_body(remove_body_fields=("privacy_reviewed",)), "privacy_review_required")
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"privacy_reviewed": False}), "privacy_review_required")
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"save_scope": "repo"}), "invalid_save_scope")
    assert_save_endpoint_rejected(save_dry_run_body(candidate_updates={"status": "saved"}), "candidate_must_be_preview_only")
    assert_save_endpoint_rejected(save_dry_run_body(candidate_updates={"user_approved_at": "2026-07-08"}), "candidate_already_approved")
    assert_save_endpoint_rejected(
        save_dry_run_body(candidate_updates={"cleaned_text": "x" * (run_web_app.MEMORY_PREVIEW_CLEANED_TEXT_MAX_CHARS + 1)}),
        "cleaned_text_too_long",
    )
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"raw_transcript": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_endpoint_rejected(save_dry_run_body(candidate_updates={"original_text": "full raw text"}), "raw_transcript_not_allowed")
    assert_save_endpoint_rejected(save_dry_run_body(body_updates={"storage_path": "memory/skills/x.json"}), "path_field_not_allowed")
    assert_save_endpoint_rejected(save_dry_run_body(candidate_updates={"candidate_file": "candidate.json"}), "path_field_not_allowed")

    endpoint_candidate_id = "mem_111111111111"
    endpoint_timestamp = "2026-07-08T00:00:00Z"
    with TemporaryDirectory(prefix="jarvis-candidate-endpoint-") as endpoint_root_text:
        endpoint_root = Path(endpoint_root_text)
        endpoint_code, endpoint_result = run_web_app.save_memory_skills_candidate(
            save_dry_run_request,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(endpoint_root)},
            id_generator=lambda: endpoint_candidate_id,
            clock=lambda: endpoint_timestamp,
        )
        assert endpoint_code == HTTPStatus.OK
        assert endpoint_result["saved"] is True
        assert endpoint_result["status"] == "saved"
        assert endpoint_result["candidate_id"] == endpoint_candidate_id
        assert endpoint_result["title"] == preview["candidate_preview"]["title"]
        assert "Saved locally as a candidate" in endpoint_result["message"]
        assert endpoint_result["skill_created"] is False
        assert endpoint_result["registry_modified"] is False
        assert endpoint_result["will_run_automatically"] is False
        assert endpoint_result["local_only"] is True
        assert "candidate_file" not in endpoint_result
        endpoint_candidate_dir = run_web_app.normalize_filesystem_path(endpoint_root / "memory-skills" / "candidates")
        endpoint_candidate_file = run_web_app.normalize_filesystem_path(endpoint_candidate_dir / f"{endpoint_candidate_id}.json")
        assert endpoint_candidate_file.exists()
        endpoint_stored_candidate = json.loads(endpoint_candidate_file.read_text(encoding="utf-8"))
        assert endpoint_stored_candidate["status"] == "saved"
        assert endpoint_stored_candidate["redaction_status"] == "user_confirmed"
        assert endpoint_stored_candidate["suggested_skill_id"] == "memory_skills"
        for forbidden_field in (
            "original_text_preview",
            "original_text",
            "raw_transcript",
            "full_transcript",
            "file_path",
            "path",
            "candidate_file",
            "storage_path",
            "repo_path",
        ):
            assert forbidden_field not in endpoint_stored_candidate
        before_endpoint_collision = endpoint_candidate_file.read_text(encoding="utf-8")
        endpoint_collision_code, endpoint_collision = run_web_app.save_memory_skills_candidate(
            save_dry_run_request,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(endpoint_root)},
            id_generator=lambda: endpoint_candidate_id,
            clock=lambda: endpoint_timestamp,
        )
        assert endpoint_collision_code == HTTPStatus.CONFLICT
        assert endpoint_collision["saved"] is False
        assert endpoint_collision["error"] == "candidate_file_exists"
        assert "candidate_file" not in endpoint_collision
        assert endpoint_candidate_file.read_text(encoding="utf-8") == before_endpoint_collision

    with TemporaryDirectory(prefix="jarvis-candidate-endpoint-invalid-") as invalid_endpoint_root_text:
        invalid_endpoint_root = Path(invalid_endpoint_root_text)
        invalid_endpoint_code, invalid_endpoint = run_web_app.save_memory_skills_candidate(
            save_dry_run_body(remove_body_fields=("explicit_confirmation",)),
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(invalid_endpoint_root)},
            id_generator=lambda: "mem_222222222222",
            clock=lambda: endpoint_timestamp,
        )
        assert invalid_endpoint_code == HTTPStatus.BAD_REQUEST
        assert invalid_endpoint["error"] == "explicit_confirmation_required"
        assert not (invalid_endpoint_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-candidate-endpoint-failure-") as endpoint_failure_root_text:
        endpoint_failure_root = Path(endpoint_failure_root_text)
        endpoint_blocking_path = endpoint_failure_root / "memory-skills"
        endpoint_blocking_path.write_text("not a directory", encoding="utf-8")
        endpoint_failure_code, endpoint_failure = run_web_app.save_memory_skills_candidate(
            save_dry_run_request,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(endpoint_failure_root)},
            id_generator=lambda: "mem_333333333333",
            clock=lambda: endpoint_timestamp,
        )
        assert endpoint_failure_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert endpoint_failure["saved"] is False
        assert endpoint_failure["error"] == "candidate_write_failed"
        assert "candidate_file" not in endpoint_failure
        assert endpoint_blocking_path.is_file()

    endpoint_repo_write_code, endpoint_repo_write = run_web_app.save_memory_skills_candidate(
        save_dry_run_request,
        env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(run_web_app.REPO_ROOT / ".jarvis-local")},
        id_generator=lambda: "mem_444444444444",
        clock=lambda: endpoint_timestamp,
    )
    assert endpoint_repo_write_code == HTTPStatus.BAD_REQUEST
    assert endpoint_repo_write["error"] == "local_state_dir_inside_repo"
    assert not run_web_app.REPO_ROOT.joinpath(".jarvis-local").exists()

    valid_unicode_save_request = {
        "candidate_preview": valid_unicode_preview["candidate_preview"],
        "explicit_confirmation": True,
        "privacy_reviewed": True,
        "save_scope": "local_only",
    }
    valid_unicode_dry_run_code, valid_unicode_dry_run = run_web_app.validate_memory_skills_save_dry_run(
        valid_unicode_save_request
    )
    assert valid_unicode_dry_run_code == HTTPStatus.OK
    with TemporaryDirectory(prefix="jarvis-unicode-candidate-write-") as unicode_write_root_text:
        unicode_write_root = Path(unicode_write_root_text)
        unicode_write_code, unicode_write = run_web_app.write_memory_skills_candidate(
            valid_unicode_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(unicode_write_root)},
            id_generator=lambda: "mem_555555555555",
            clock=lambda: "2026-07-08T00:00:00Z",
        )
        assert unicode_write_code == HTTPStatus.OK
        unicode_candidate_file = unicode_write_root / "memory-skills" / "candidates" / "mem_555555555555.json"
        unicode_stored_candidate = json.loads(unicode_candidate_file.read_text(encoding="utf-8"))
        assert unicode_stored_candidate["title"] == "정상 한글 😀 𐐷"
        assert unicode_stored_candidate["cleaned_text"] == "반복 작업을 안전하게 정리 😀 𐐷"
        assert not list(unicode_candidate_file.parent.glob("*.tmp"))

    for invalid_stored_text in ("bad\ud800", "bad\x00text"):
        with TemporaryDirectory(prefix="jarvis-invalid-unicode-write-") as invalid_unicode_root_text:
            invalid_unicode_root = Path(invalid_unicode_root_text)
            invalid_unicode_dry_run = dict(save_dry_run)
            invalid_unicode_dry_run["candidate"] = dict(save_dry_run["candidate"])
            invalid_unicode_dry_run["candidate"]["cleaned_text"] = invalid_stored_text
            invalid_unicode_write_code, invalid_unicode_write = run_web_app.write_memory_skills_candidate(
                invalid_unicode_dry_run,
                env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(invalid_unicode_root)},
                id_generator=lambda: "mem_666666666666",
                clock=lambda: "2026-07-08T00:00:00Z",
            )
            assert invalid_unicode_write_code == HTTPStatus.BAD_REQUEST
            assert invalid_unicode_write["error"] == "invalid_unicode"
            assert "candidate_file" not in invalid_unicode_write
            assert str(invalid_unicode_root) not in str(invalid_unicode_write)
            assert not (invalid_unicode_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-invalid-timestamp-write-") as invalid_timestamp_root_text:
        invalid_timestamp_root = Path(invalid_timestamp_root_text)
        invalid_timestamp_code, invalid_timestamp = run_web_app.write_memory_skills_candidate(
            save_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(invalid_timestamp_root)},
            id_generator=lambda: "mem_777777777777",
            clock=lambda: "bad\ud800",
        )
        assert invalid_timestamp_code == HTTPStatus.BAD_REQUEST
        assert invalid_timestamp["error"] == "invalid_unicode"
        assert not (invalid_timestamp_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-oversize-candidate-write-") as oversize_root_text:
        oversize_root = Path(oversize_root_text)
        oversize_code, oversize = run_web_app.write_memory_skills_candidate(
            save_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(oversize_root)},
            id_generator=lambda: "mem_888888888888",
            clock=lambda: "2026-07-08T00:00:00Z",
            max_json_bytes=1,
        )
        assert oversize_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
        assert oversize["error"] == "candidate_json_too_large"
        assert "candidate_file" not in oversize
        assert not (oversize_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-reparse-candidate-write-") as reparse_root_text:
        reparse_root = Path(reparse_root_text)
        reparse_target = reparse_root / "target"
        reparse_target.mkdir()
        reparse_state_root = reparse_root / "state-link"
        try:
            reparse_state_root.symlink_to(reparse_target, target_is_directory=True)
        except (NotImplementedError, OSError):
            pass
        else:
            reparse_code, reparse_result = run_web_app.write_memory_skills_candidate(
                save_dry_run,
                env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(reparse_state_root)},
                id_generator=lambda: "mem_999999999999",
                clock=lambda: "2026-07-08T00:00:00Z",
            )
            assert reparse_code == HTTPStatus.BAD_REQUEST
            assert reparse_result["error"] == "candidate_path_not_safe"
            assert "candidate_file" not in reparse_result
            assert not (reparse_target / "memory-skills").exists()

    fixed_candidate_id = "mem_0123456789ab"
    fixed_timestamp = "2026-07-08T00:00:00Z"
    with TemporaryDirectory(prefix="jarvis-candidate-write-") as write_root_text:
        write_root = Path(write_root_text)
        write_code, write_result = run_web_app.write_memory_skills_candidate(
            save_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(write_root)},
            id_generator=lambda: fixed_candidate_id,
            clock=lambda: fixed_timestamp,
        )
        assert write_code == HTTPStatus.OK
        assert write_result["saved"] is True
        assert write_result["status"] == "saved"
        assert write_result["candidate_id"] == fixed_candidate_id
        assert write_result["will_run_automatically"] is False
        assert write_result["skill_created"] is False
        assert write_result["registry_modified"] is False
        candidate_dir = run_web_app.normalize_filesystem_path(write_root / "memory-skills" / "candidates")
        candidate_file = run_web_app.normalize_filesystem_path(candidate_dir / f"{fixed_candidate_id}.json")
        assert Path(write_result["candidate_file"]) == candidate_file
        assert candidate_file.exists()
        assert not run_web_app.is_path_inside_repo(candidate_file)
        stored_candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
        assert stored_candidate["schema_version"] == "memory_candidate.v1"
        assert stored_candidate["storage_version"] == run_web_app.MEMORY_CANDIDATE_STORAGE_VERSION
        assert stored_candidate["id"] == fixed_candidate_id
        assert stored_candidate["status"] == "saved"
        assert stored_candidate["created_at"] == fixed_timestamp
        assert stored_candidate["updated_at"] == fixed_timestamp
        assert stored_candidate["user_approved_at"] == fixed_timestamp
        assert stored_candidate["redaction_status"] == "user_confirmed"
        assert stored_candidate["suggested_skill_id"] == "memory_skills"
        assert "original_text_preview" not in stored_candidate
        assert "original_text" not in stored_candidate
        assert "raw_transcript" not in stored_candidate
        assert "full_transcript" not in stored_candidate
        assert "file_path" not in stored_candidate
        assert "path" not in stored_candidate
        assert "candidate_file" not in stored_candidate
        assert "storage_path" not in stored_candidate
        assert "repo_path" not in stored_candidate
        assert not list(candidate_dir.glob(f".{fixed_candidate_id}.*.tmp"))
        before_collision_text = candidate_file.read_text(encoding="utf-8")
        collision_code, collision = run_web_app.write_memory_skills_candidate(
            save_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(write_root)},
            id_generator=lambda: fixed_candidate_id,
            clock=lambda: fixed_timestamp,
        )
        assert collision_code == HTTPStatus.CONFLICT
        assert collision["saved"] is False
        assert collision["error"] == "candidate_file_exists"
        assert candidate_file.read_text(encoding="utf-8") == before_collision_text
        assert not list(candidate_dir.glob(f".{fixed_candidate_id}.*.tmp"))
        invalid_id_code, invalid_id = run_web_app.write_memory_skills_candidate(
            save_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(write_root)},
            id_generator=lambda: "../memory/tasks/x",
            clock=lambda: fixed_timestamp,
        )
        assert invalid_id_code == HTTPStatus.BAD_REQUEST
        assert invalid_id["error"] == "invalid_candidate_id"
        assert len(list(candidate_dir.glob("*.json"))) == 1

    with TemporaryDirectory(prefix="jarvis-link-collision-write-") as link_collision_root_text:
        link_collision_root = Path(link_collision_root_text)
        link_collision_candidate = (
            link_collision_root / "memory-skills" / "candidates" / "mem_aaaaaaaaaaaa.json"
        )

        def collide_during_publish(_temp_file: Path, final_file: Path) -> None:
            final_file.write_bytes(b"existing candidate")
            raise FileExistsError

        link_collision_code, link_collision = run_web_app.write_memory_skills_candidate(
            save_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(link_collision_root)},
            id_generator=lambda: "mem_aaaaaaaaaaaa",
            clock=lambda: fixed_timestamp,
            linker=collide_during_publish,
        )
        assert link_collision_code == HTTPStatus.CONFLICT
        assert link_collision["error"] == "candidate_file_exists"
        assert "candidate_file" not in link_collision
        assert link_collision_candidate.read_bytes() == b"existing candidate"
        assert not list(link_collision_candidate.parent.glob("*.tmp"))

    with TemporaryDirectory(prefix="jarvis-link-failure-write-") as link_failure_root_text:
        link_failure_root = Path(link_failure_root_text)

        def fail_candidate_publish(_temp_file: Path, _final_file: Path) -> None:
            raise OSError("private filesystem detail")

        link_failure_code, link_failure = run_web_app.write_memory_skills_candidate(
            save_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(link_failure_root)},
            id_generator=lambda: "mem_bbbbbbbbbbbb",
            clock=lambda: fixed_timestamp,
            linker=fail_candidate_publish,
        )
        link_failure_candidate_dir = link_failure_root / "memory-skills" / "candidates"
        assert link_failure_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert link_failure["error"] == "candidate_write_failed"
        assert "candidate_file" not in link_failure
        assert "private filesystem detail" not in str(link_failure)
        assert str(link_failure_root) not in str(link_failure)
        assert not list(link_failure_candidate_dir.glob("*.tmp"))
        assert not list(link_failure_candidate_dir.glob("*.json"))

    with TemporaryDirectory(prefix="jarvis-invalid-candidate-write-") as invalid_write_root_text:
        invalid_write_root = Path(invalid_write_root_text)
        invalid_dry_run = dict(save_dry_run)
        invalid_dry_run["candidate"] = dict(save_dry_run["candidate"])
        invalid_dry_run["candidate"]["status"] = "saved"
        invalid_candidate_code, invalid_candidate = run_web_app.write_memory_skills_candidate(
            invalid_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(invalid_write_root)},
            id_generator=lambda: "mem_abcdefabcdef",
            clock=lambda: fixed_timestamp,
        )
        assert invalid_candidate_code == HTTPStatus.BAD_REQUEST
        assert invalid_candidate["error"] == "candidate_must_be_preview_only"
        assert not (invalid_write_root / "memory-skills").exists()

    with TemporaryDirectory(prefix="jarvis-candidate-write-failure-") as failure_root_text:
        failure_root = Path(failure_root_text)
        blocking_path = failure_root / "memory-skills"
        blocking_path.write_text("not a directory", encoding="utf-8")
        failure_code, failure = run_web_app.write_memory_skills_candidate(
            save_dry_run,
            env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(failure_root)},
            id_generator=lambda: "mem_abcdefabcdef",
            clock=lambda: fixed_timestamp,
        )
        assert failure_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert failure["saved"] is False
        assert failure["error"] == "candidate_write_failed"
        assert blocking_path.is_file()

    repo_write_code, repo_write = run_web_app.write_memory_skills_candidate(
        save_dry_run,
        env={run_web_app.JARVIS_LOCAL_STATE_DIR_ENV: str(run_web_app.REPO_ROOT / ".jarvis-local")},
        id_generator=lambda: "mem_abcdefabcdef",
        clock=lambda: fixed_timestamp,
    )
    assert repo_write_code == HTTPStatus.BAD_REQUEST
    assert repo_write["error"] == "local_state_dir_inside_repo"
    assert not run_web_app.REPO_ROOT.joinpath(".jarvis-local").exists()
    assert not run_web_app.APP_ROOT.joinpath("state").exists()
    assert not run_web_app.APP_ROOT.joinpath("examples", "memory-skills-sample.json").exists()
    assert not run_web_app.REPO_ROOT.joinpath(".jarvis-local").exists()
    assert not run_web_app.REPO_ROOT.joinpath("memory", "skills").exists()
    assert run_web_app.handle_post_api("/api/memory-skills", {})[0] == HTTPStatus.NOT_FOUND
    save_route_code, save_route = run_web_app.handle_post_api(run_web_app.MEMORY_SAVE_ENDPOINT, {})
    assert save_route_code == HTTPStatus.NOT_FOUND
    assert save_route == {"ok": False, "error": "not_found"}

    for args in (
        ("add", "."),
        ("commit", "-m", "test"),
        ("push",),
        ("reset", "--hard"),
        ("tag", "v0.1"),
        ("merge", "main"),
        ("rebase", "main"),
    ):
        try:
            run_web_app.validate_read_only_git_args(args)
        except run_web_app.RegistryError:
            pass
        else:
            raise AssertionError(f"unsafe git args were not rejected: {args}")

    suggestion_code, suggestion = run_web_app.handle_post_api(
        "/api/suggest-skill",
        {"message": "I need Codex to review a repo README before commit."},
    )
    assert suggestion_code == HTTPStatus.OK
    assert suggestion["ok"] is True
    assert suggestion["recommended_skill"] == "hermes_manager"
    assert "git_bash" in suggestion["commands"]
    assert "powershell" in suggestion["commands"]

    assert run_web_app.suggest_skill("\uc81c\uc870\uc7a5\ube44 \uc2dc\ubbac\ub808\uc774\uc158 \uc544\uc774\ub514\uc5b4 \uac80\uc99d\ud574\uc918")["recommended_skill"] == "research_council"
    assert run_web_app.suggest_skill("\ucc3d\uc5c5 \uc544\uc774\ub514\uc5b4 \uc0ac\uc5c5\uc131 \uac80\ud1a0\ud574\uc918")["recommended_skill"] == "research_council"
    assert run_web_app.suggest_skill("\uac04\ubcd1 \uc571 \uc544\uc774\ub514\uc5b4 MVP \uac80\uc99d\ud574\uc918")["recommended_skill"] == "research_council"
    assert run_web_app.suggest_skill("Codex \ucee4\ubc0b \ub9ac\ubdf0 \ub3c4\uc640\uc918")["recommended_skill"] == "hermes_manager"
    assert run_web_app.suggest_skill("MCP Agent Skills \uc0c8 \uae30\uc220 \ucc3e\uc544\ubd10")["recommended_skill"] == "daily_ai_radar"
    assert run_web_app.suggest_skill("\ubc18\ubcf5 \uc791\uc5c5 skill\ub85c \uae30\uc5b5\ud574\uc918")["recommended_skill"] == "memory_skills"
    assert run_web_app.suggest_skill("\uc624\ub298 \ubb50\ud558\uc9c0")["recommended_skill"] == "unknown"
    assert run_web_app.suggest_skill("\uc2dc\ubbac\ub808\uc774\uc158 \uac8c\uc784 \ucd94\ucc9c\ud574\uc918")["recommended_skill"] == "unknown"

    assert run_web_app.clean_voice_transcript("코덱스 케어노트 헤르메스") == "Codex CareNote Hermes"
    assert run_web_app.clean_voice_transcript("엠씨피 에이전트 스킬 데일리 레이더") == "MCP Agent Skills Daily AI Radar"
    assert run_web_app.clean_voice_transcript("고깃집 리뷰 정리해줘") == "고깃집 리뷰 정리해줘"
    assert run_web_app.clean_voice_transcript("영화 리뷰 정리해줘") == "영화 리뷰 정리해줘"
    assert run_web_app.clean_voice_transcript("영화 리뷰 수정해줘") == "영화 리뷰 수정해줘"
    assert run_web_app.clean_voice_transcript("프리뷰 화면 확인") == "프리뷰 화면 확인"
    voice_empty_code, voice_empty = run_web_app.handle_post_api("/api/voice-inbox/prepare", {"transcript": ""})
    assert voice_empty_code == HTTPStatus.BAD_REQUEST
    assert voice_empty["error"] == "empty_transcript"
    voice_missing_code, voice_missing = run_web_app.handle_post_api("/api/voice-inbox/prepare", {})
    assert voice_missing_code == HTTPStatus.BAD_REQUEST
    assert voice_missing["error"] == "missing_transcript"
    voice_type_code, voice_type = run_web_app.handle_post_api("/api/voice-inbox/prepare", {"transcript": 123})
    assert voice_type_code == HTTPStatus.BAD_REQUEST
    assert voice_type["error"] == "transcript_must_be_string"
    voice_long_code, voice_long = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "a" * (run_web_app.VOICE_INBOX_MAX_TRANSCRIPT_CHARS + 1)},
    )
    assert voice_long_code == HTTPStatus.BAD_REQUEST
    assert voice_long["error"] == "transcript_too_long"
    voice_research_code, voice_research = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "Jarvis, CareNote 복약 기록 UX 리스크를 Research Council로 검증해줘"},
    )
    assert voice_research_code == HTTPStatus.OK
    assert voice_research["task_candidate"]["suggested_skill"] == "research_council"
    assert voice_research["task_candidate"]["confidence"] == "high"
    assert voice_research["task_candidate"]["needs_confirmation"] is True
    assert "CareNote" in voice_research["cleaned_transcript"]
    assert "Research Council" in voice_research["cleaned_transcript"]
    voice_hermes_code, voice_hermes = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "코덱스한테 README 수정하고 커밋 리뷰 프롬프트 만들어줘"},
    )
    assert voice_hermes_code == HTTPStatus.OK
    assert voice_hermes["task_candidate"]["suggested_skill"] == "hermes_manager"
    assert "Codex" in voice_hermes["cleaned_transcript"]
    assert "commit" in voice_hermes["cleaned_transcript"]
    assert "review" in voice_hermes["cleaned_transcript"]
    voice_radar_code, voice_radar = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "MCP Agent Skills 새 기술 Daily Radar로 확인해줘"},
    )
    assert voice_radar_code == HTTPStatus.OK
    assert voice_radar["task_candidate"]["suggested_skill"] == "daily_ai_radar"
    voice_memory_code, voice_memory = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "이 반복 작업 skill 후보로 기억해줘"},
    )
    assert voice_memory_code == HTTPStatus.OK
    assert voice_memory["task_candidate"]["suggested_skill"] == "memory_skills"
    assert voice_memory["task_candidate"]["needs_confirmation"] is True
    assert "saved" not in voice_memory
    voice_unknown_code, voice_unknown = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "오늘 뭐하지"},
    )
    assert voice_unknown_code == HTTPStatus.OK
    assert voice_unknown["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_unknown["task_candidate"]["confidence"] == "low"
    voice_restaurant_code, voice_restaurant = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "고깃집 리뷰 정리해줘"},
    )
    assert voice_restaurant_code == HTTPStatus.OK
    assert voice_restaurant["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_restaurant["cleaned_transcript"] == "고깃집 리뷰 정리해줘"
    assert "고git" not in voice_restaurant["cleaned_transcript"]
    voice_movie_code, voice_movie = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "영화 리뷰 정리해줘"},
    )
    assert voice_movie_code == HTTPStatus.OK
    assert voice_movie["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_movie["cleaned_transcript"] == "영화 리뷰 정리해줘"
    voice_movie_edit_code, voice_movie_edit = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "영화 리뷰 수정해줘"},
    )
    assert voice_movie_edit_code == HTTPStatus.OK
    assert voice_movie_edit["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_movie_edit["cleaned_transcript"] == "영화 리뷰 수정해줘"
    voice_preview_code, voice_preview = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "프리뷰 화면 확인"},
    )
    assert voice_preview_code == HTTPStatus.OK
    assert voice_preview["task_candidate"]["suggested_skill"] == "unknown"
    assert voice_preview["cleaned_transcript"] == "프리뷰 화면 확인"
    voice_report_review_code, voice_report_review = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "report review draft"},
    )
    assert voice_report_review_code == HTTPStatus.OK
    assert voice_report_review["task_candidate"]["suggested_skill"] == "unknown"
    voice_daily_routine_code, voice_daily_routine = run_web_app.handle_post_api(
        "/api/voice-inbox/prepare",
        {"transcript": "데일리 루틴 정리"},
    )
    assert voice_daily_routine_code == HTTPStatus.OK
    assert voice_daily_routine["task_candidate"]["suggested_skill"] == "unknown"
    assert "This is a task candidate, not an execution." in voice_research["safety_notes"]

    app_js = Path(__file__).resolve().parent.joinpath("web", "app.js").read_text(encoding="utf-8")
    html = Path(__file__).resolve().parent.joinpath("web", "index.html").read_text(encoding="utf-8")
    web_app_source = Path(__file__).with_name("run_web_app.py").read_text(encoding="utf-8")
    assert "Voice Inbox" in html
    assert "Transcript / rough thought" in html
    assert "Prepare Task Candidate" in html
    assert "Paste From Clipboard" in html
    assert "Clear Transcript" in html
    assert "v0.1 does not record audio." in html
    assert "Jarvis will not run tools until you choose a handoff." in html
    assert "Create Local Task never auto-saves" in html
    assert "Refresh Project Control" in html
    assert "Refresh History" in html
    assert "Refresh Memory / Skills" in html
    assert "Checkpoints / History" in html
    assert "Codex Review" in html
    assert "Project Control" in html
    assert "Owner-facing local project dashboard" in html
    assert "Fresh local work review" in html
    assert "Load Read-Only Review" in html
    assert "already scope-approved raw queue" in html
    assert "copy-only Hermes review handoff" in html
    assert "queue + item_id envelope" in html
    assert "no queue/session persistence" in html
    assert "Owner-facing local project dashboard" in html
    assert "Record Completion Evidence appends one evidence value" in html
    assert "no flow executes or automatically completes Task work" in html
    assert "does not create commits" in html
    assert "preview-only: sample candidates" in html
    assert "no save endpoint" in html
    assert "no persistence" in html
    assert "no runtime write" in html
    assert "recommendedSkillId" in app_js
    assert "handoffStepsForSkill" in app_js
    assert "copyNextActionForHandoff" in app_js
    assert "/api/overview" in app_js
    assert "renderProjectControl" in app_js
    assert "renderDirectorReport" in app_js
    assert 'directorReport.contract_type !== "jarvis_director_report"' in app_js
    assert 'directorReport.source_contract_type !== "hermes_manager_report"' in app_js
    assert "directorReport.derived_view !== true" in app_js
    assert "directorReport.read_only !== true" in app_js
    assert (
        'directorReport.authority_boundary !== "derived_owner_summary_only"'
        in app_js
    )
    assert "Director Summary" in app_js
    assert "Owner가 얻게 된 기능" in app_js
    director_report_renderer = app_js.split(
        "function renderDirectorReport",
        1,
    )[1].split("function renderManagerReport", 1)[0]
    assert "<button" not in director_report_renderer
    assert "<form" not in director_report_renderer
    assert "fetch(" not in director_report_renderer
    assert "navigator.clipboard" not in director_report_renderer
    assert "renderManagerReport" in app_js
    assert 'managerReport.contract_type !== "hermes_manager_report"' in app_js
    assert 'managerReport.source_of_truth !== "master_plan"' in app_js
    assert "managerReport.derived_view !== true" in app_js
    assert "managerReport.read_only !== true" in app_js
    assert 'managerReport.authority_boundary !== "derived_reporting_only"' in app_js
    assert "Hermes Manager Report" in app_js
    assert "이번 milestone의 의미" in app_js
    assert "사용자가 얻은 결과" in app_js
    assert "Owner action:" in app_js
    assert 'managerReport?.owner_action === "none"' in app_js
    assert "project_control.v0.1F" in app_js
    manager_report_renderer = app_js.split("function renderManagerReport", 1)[1].split(
        "function renderProjectControl",
        1,
    )[0]
    assert "<button" not in manager_report_renderer
    assert "fetch(" not in manager_report_renderer
    assert "navigator.clipboard" not in manager_report_renderer
    project_control_renderer = app_js.split("function renderProjectControl", 1)[1].split(
        "function renderOwnerDecision",
        1,
    )[0]
    assert project_control_renderer.index(
        "${renderDirectorReport(directorReport)}"
    ) < project_control_renderer.index("${renderManagerReport(managerReport)}")
    assert "/api/director-report" not in app_js
    assert "/api/manager-report" not in app_js
    assert "/api/director-report" not in web_app_source
    assert "/api/manager-report" not in web_app_source
    assert "renderOwnerDecision" in app_js
    assert 'ownerDecision.contract_type !== "jarvis_owner_decision"' in app_js
    assert "다음 workstream 결정" in app_js
    assert "Conversation response template" in app_js
    assert "이 화면은 Decision 객체를 읽기만 합니다." in app_js
    owner_decision_renderer = app_js.split("function renderOwnerDecision", 1)[1].split(
        "function renderRepoStatus",
        1,
    )[0]
    assert "<button" not in owner_decision_renderer
    assert "fetch(" not in owner_decision_renderer
    assert "/api/owner-decision" not in app_js
    assert "/api/owner-decision" not in web_app_source
    assert "현재 만드는 이유" in app_js
    assert "이 단계가 끝나면 사용자가 얻는 것" in app_js
    assert "Jarvis-Core 내부 workstream" in app_js
    assert "승인 필요 여부" in app_js
    assert "잠긴 기능" in app_js
    assert (
        "Project Control overview refreshed: read-only discovery with "
        "confirmed status transitions only."
    ) in app_js
    assert "/api/history" in app_js
    assert "/api/memory-skills" in app_js
    assert "/api/memory-skills/candidates/preview" in app_js
    assert "/api/codex-review/preview" in app_js
    assert "/api/voice-inbox/prepare" in app_js
    assert "/api/create-local-task/preview" in app_js
    assert "/api/create-local-task/confirm" in app_js
    assert "Create Local Task Preview" in app_js
    assert "Create Local Task Receipt" in app_js
    assert "Task ID" in app_js
    assert "Storage location" in app_js
    assert "Next recommended action" in app_js
    assert "raw transcript is not saved" in app_js
    assert "renderCodexReview" in app_js
    assert "renderCodexReviewFailure" in app_js
    assert "loadCodexReview" in app_js
    assert '"queue" in parsed || "item_id" in parsed' in app_js
    assert "Hermes handoff fields must be exactly queue and item_id." in app_js
    assert "codexReviewItemId.value = itemId" in app_js
    assert "Fresh Codex work package loaded for read-only review." in app_js
    assert "No approval or action was created." in app_js
    assert "renderOverview" in app_js
    assert "renderRecentMilestoneEvidence" in app_js
    assert "jarvis_recent_milestone_evidence" in app_js
    assert "최근 로컬 작업 증거" in app_js
    assert "HEAD verified" in app_js
    assert "작업 증거 요약" in app_js
    assert "renderHistory" in app_js
    assert "renderMemorySkills" in app_js
    assert "loadMemorySkills" in app_js
    assert "memoryCandidateCards" in app_js
    assert "renderMemoryCandidatePreview" in app_js
    assert "previewMemoryCandidatePayload" in app_js
    assert "previewVoiceMemoryCandidate" in app_js
    assert "renderRecentCommits" in app_js
    assert "renderVoiceCandidate" in app_js
    assert "prepareVoiceCandidate" in app_js
    assert "jarvisCommandFromCleaned" in app_js
    assert "voiceUnknownGuidance" in app_js
    assert "renderRecentGroups" in app_js
    assert "normalizedOverviewItemsMarkup" in app_js
    assert "Read-only metadata" in app_js
    assert "overview-badge" in app_js
    assert "Open file" not in app_js
    assert "Edit file" not in app_js
    assert "Delete file" not in app_js
    assert "navigator.mediaDevices" not in app_js
    assert "getUserMedia" not in app_js
    assert "<audio" not in app_js
    assert "MediaRecorder" not in app_js
    assert "loadOverview" in app_js
    assert "loadHistory" in app_js
    assert "registeredSafetyNotes" in app_js
    assert "skill.safety_notes" in app_js
    assert "Suggested Skill Action Panel" in app_js
    assert "suggestion-action-panel" in app_js
    assert "Open Skill Details" in app_js
    assert "open-skill-details" in app_js
    assert "Open Local URL" in app_js
    assert "open-local-url" in app_js
    assert "Next handoff" in app_js
    assert "handoff-hint" in app_js
    assert "Copy Git Bash or PowerShell command." in app_js
    assert "Run it in your terminal." in app_js
    assert "Open the local URL after the server starts." in app_js
    assert "Follow the copied command output." in app_js
    assert "handoff_steps" in app_js
    assert "Run the command first if the page does not load." in app_js
    assert "data-copy-next-action" in app_js
    assert "Jarvis Console does not run it for you." in app_js
    assert "localOnlyUrl" in app_js
    assert "LOCAL_URL_PREFIX" in app_js
    assert "LOCAL_URL_PROTOCOL" in app_js
    assert "LOCAL_URL_HOSTNAME" in app_js
    assert "new URL(url)" in app_js
    assert "parsed.hostname === LOCAL_URL_HOSTNAME" in app_js
    assert "window.open" in app_js
    assert "noopener,noreferrer" in app_js
    assert "This only opens the URL. It does not start the server." in app_js
    assert "Commands are copy-only." in app_js
    assert "Choose a skill manually from the sidebar." in app_js
    assert "Copy Git Bash" in app_js
    assert "Copy PowerShell" in app_js
    assert "navigator.clipboard.writeText(command)" in app_js
    assert "navigator.clipboard.writeText(text)" in app_js
    assert "copy-text" in app_js
    assert "Copy Cleaned Task" in app_js
    assert "Copy As Jarvis Command" in app_js
    assert "Open Memory / Skills" in app_js
    assert "Copy Candidate" in app_js
    assert "Copy Skill Draft Prompt" in app_js
    assert "Review Candidate" in app_js
    assert "Preview Local Candidate" in app_js
    assert "Preview only" in app_js
    assert "Not saved" in app_js
    assert "No persistence" in app_js
    assert "No runtime write" in app_js
    assert "No candidate preview prepared yet." in app_js
    assert "This is only a preview of what could be saved later." in app_js
    assert "Nothing was saved." in app_js
    assert "Local save is not available in Phase 2B." in app_js
    assert "This is not an approved skill and will not run automatically." in app_js
    assert "Technical details" in app_js
    assert "save_endpoint" in app_js
    assert "Save endpoint" not in app_js
    assert "proposal-only prompt for manual Hermes/Codex review" in app_js
    assert "Paste it yourself when ready" in app_js
    assert "No automatic handoff, no skill creation, no commit." in app_js
    assert "Task: Prepare a Memory / Skills candidate draft for human review." in app_js
    assert "The user is manually pasting this into Hermes/Codex for review." in app_js
    assert "Treat it as a candidate, not an approved skill." in app_js
    assert "Candidate:" in app_js
    assert "Safety boundaries:" in app_js
    assert "Requested output:" in app_js
    assert "No automatic repo/file write." in app_js
    assert "No automatic git add/commit/push." in app_js
    assert "No external API/web/LLM calls." in app_js
    assert "No skill registry modification unless explicitly approved later." in app_js
    assert "Do not implement yet." in app_js
    assert "Do not commit or push." in app_js
    assert "Manual copy fallback" in app_js
    assert "Clipboard was not available. Copy the text below manually." in app_js
    assert "No file was created. No action was executed." in app_js
    assert "data-manual-copy-label" in app_js
    assert "showManualCopyFallback" in app_js
    assert "memoryCopyFallbackText" in app_js
    assert "fallbackText.value = text" in app_js
    assert "does not save this candidate automatically" in app_js
    assert "No persistence, no runtime write, and no automatic skill creation." in app_js
    assert "Save Candidate" not in app_js
    assert "Confirm Local Save" not in app_js
    assert "Review Save Candidate" not in app_js
    assert "Approve Codex Review" not in app_js
    assert "Execute Codex Review" not in app_js
    assert "Prepare Local Candidate" not in app_js
    assert "Create Skill" not in app_js
    assert "No matching skill yet." in app_js
    assert "Idea validation -> Research Council" in app_js
    assert ">Run<" not in app_js
    assert ">Execute<" not in app_js
    assert ">Start<" not in app_js
    assert ">Auto<" not in app_js
    assert "Install Skill Now" not in app_js
    assert "memoryCopyFallbackText.innerHTML" not in app_js

    styles = Path(__file__).resolve().parent.joinpath("web", "styles.css").read_text(encoding="utf-8")
    assert "manual-copy-fallback" in styles
    assert "memory-candidate-card" in styles
    assert "memory-preview-card" in styles
    assert "codex-review-layout" in styles
    assert "codex-review-card" in styles
    assert "codex-review-safety-grid" in styles
    assert "create-local-task-card" in styles
    assert "create-local-task-receipt" in styles

    print("Jarvis Console smoke tests passed")


if __name__ == "__main__":
    main()
