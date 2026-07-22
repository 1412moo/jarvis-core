"""Smoke tests for Jarvis Console v0.1."""

from __future__ import annotations

from dataclasses import replace
import json
from http import HTTPStatus
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from typing import Any

import run_web_app
import codex_review
from hermes_manager_pilot.approval_binding import build_scope_approval_binding
from hermes_manager_pilot.prompt_queue import (
    REQUIRED_FORBIDDEN_ACTIONS,
    normalize_prompt_queue,
)
from hermes_manager_pilot.schemas import ValidationError


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


def main() -> None:
    run_web_app.run_self_test()
    _test_codex_review_vertical_slice()

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
    assert "Voice Inbox" in html
    assert "Transcript / rough thought" in html
    assert "Prepare Task Candidate" in html
    assert "Paste From Clipboard" in html
    assert "Clear Transcript" in html
    assert "v0.1 does not record audio." in html
    assert "Jarvis will not run tools until you choose a handoff." in html
    assert "Refresh Overview" in html
    assert "Refresh History" in html
    assert "Refresh Memory / Skills" in html
    assert "Checkpoints / History" in html
    assert "Codex Review" in html
    assert "Fresh local work review" in html
    assert "Load Read-Only Review" in html
    assert "already scope-approved raw queue" in html
    assert "copy-only Hermes review handoff" in html
    assert "queue + item_id envelope" in html
    assert "no queue/session persistence" in html
    assert "Read-only operations dashboard" in html
    assert "does not create tasks" in html
    assert "does not create commits" in html
    assert "preview-only: sample candidates" in html
    assert "no save endpoint" in html
    assert "no persistence" in html
    assert "no runtime write" in html
    assert "recommendedSkillId" in app_js
    assert "handoffStepsForSkill" in app_js
    assert "copyNextActionForHandoff" in app_js
    assert "/api/overview" in app_js
    assert "/api/history" in app_js
    assert "/api/memory-skills" in app_js
    assert "/api/memory-skills/candidates/preview" in app_js
    assert "/api/codex-review/preview" in app_js
    assert "/api/voice-inbox/prepare" in app_js
    assert "renderCodexReview" in app_js
    assert "renderCodexReviewFailure" in app_js
    assert "loadCodexReview" in app_js
    assert '"queue" in parsed || "item_id" in parsed' in app_js
    assert "Hermes handoff fields must be exactly queue and item_id." in app_js
    assert "codexReviewItemId.value = itemId" in app_js
    assert "Fresh Codex work package loaded for read-only review." in app_js
    assert "No approval or action was created." in app_js
    assert "renderOverview" in app_js
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

    print("Jarvis Console smoke tests passed")


if __name__ == "__main__":
    main()
