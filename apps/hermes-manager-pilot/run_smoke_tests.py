"""Smoke tests for the Hermes renderer and in-memory Prompt Queue primitives."""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timezone
import http.client
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import hermes_manager_pilot.change_evidence as change_evidence_module
import run_web_app as hermes_web_app
from hermes_manager_pilot.approval_binding import (
    build_commit_approval_binding,
    build_review_approval_binding,
    build_scope_approval_binding,
    digest_matches,
)
from hermes_manager_pilot.change_evidence import (
    FreshReviewHandoffDecision,
    MAX_FILE_BYTES,
    MAX_GIT_OUTPUT_BYTES,
    QueueObservationEvaluation,
    WHOLE_STATUS_COVERAGE,
    apply_review_evidence_observation,
    build_fresh_review_handoff_decision,
    build_review_session_from_fresh_preview,
    build_review_evidence_handoff_decision,
    collect_local_change_evidence,
    collect_review_evidence_bundle,
    collect_whole_worktree_status_evidence,
    evaluate_review_evidence_in_queue,
    verify_local_change_evidence,
    verify_review_evidence_bundle,
    verify_whole_worktree_status_evidence,
)
from hermes_manager_pilot.pipeline import run_hermes_manager_pilot
from hermes_manager_pilot.prompt_queue import (
    PromptQueueState,
    REQUIRED_FORBIDDEN_ACTIONS,
    build_hermes_session,
    evaluate_queue_item,
    normalize_prompt_queue,
)
from hermes_manager_pilot.prompt_renderer import render_commit_prompt
from hermes_manager_pilot.review_handoff import (
    HANDOFF_ENDPOINT,
    build_copy_only_review_handoff,
    render_copy_only_review_handoff,
)
import hermes_manager_pilot.review_lifecycle as review_lifecycle_module
from hermes_manager_pilot.review_lifecycle import (
    ReviewLifecycleError,
    ReviewLifecycleService,
    delete_preview_to_dict,
    recovery_inspection_to_dict,
    save_preview_to_dict,
)
import hermes_manager_pilot.review_record as review_record_module
from hermes_manager_pilot.review_record import (
    AUTHORITY_BOUNDARY as REVIEW_RECORD_AUTHORITY_BOUNDARY,
    CONTRACT_TYPE as REVIEW_RECORD_CONTRACT_TYPE,
    VERSION as REVIEW_RECORD_VERSION,
    ReviewRecord,
    ReviewRecordCandidate,
    ReviewRecordError,
    create_review_record,
    evaluate_review_record_freshness,
    normalize_review_record,
    normalize_review_record_candidate,
    parse_review_record_json,
    review_record_digest,
    review_record_to_dict,
    serialize_review_record,
)
import hermes_manager_pilot.review_store as review_store_module
from hermes_manager_pilot.review_store import (
    JARVIS_LOCAL_STATE_DIR_ENV as REVIEW_STORE_STATE_DIR_ENV,
    RETENTION_POLICY as REVIEW_STORE_RETENTION_POLICY,
    ReviewStoreError,
    delete_review_record,
    list_review_records,
    read_review_record,
    resolve_review_store_paths,
    write_review_record,
)
from hermes_manager_pilot.schemas import ValidationError, normalize_session_state


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent.parent
SAMPLE_INPUT = APP_ROOT / "examples" / "sample-session-state.json"
SAMPLE_RENDERED_FILES = {
    "implementation-prompt": APP_ROOT / "examples" / "sample-rendered-implementation-prompt.md",
    "review-prompt": APP_ROOT / "examples" / "sample-rendered-review-prompt.md",
    "commit-prompt": APP_ROOT / "examples" / "sample-rendered-commit-prompt.md",
    "checkpoint-summary": APP_ROOT / "examples" / "sample-checkpoint-summary.md",
}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_validation_error(fn: object, expected_text: str) -> None:
    assert callable(fn)
    try:
        fn()
    except ValidationError as exc:
        _assert(expected_text in str(exc), f"unexpected validation error: {exc}")
    else:
        raise AssertionError(f"expected ValidationError containing: {expected_text}")


def _assert_review_record_error(fn: object, expected_text: str) -> None:
    assert callable(fn)
    try:
        fn()
    except ReviewRecordError as exc:
        _assert(expected_text in str(exc), f"unexpected ReviewRecordError: {exc}")
    else:
        raise AssertionError(f"expected ReviewRecordError containing: {expected_text}")


def _assert_review_store_error(fn: object, expected_code: str) -> None:
    assert callable(fn)
    try:
        fn()
    except ReviewStoreError as exc:
        _assert(exc.code == expected_code, f"unexpected ReviewStoreError: {exc.code}")
        _assert(str(exc) == expected_code, "Review store error disclosed extra detail")
    else:
        raise AssertionError(f"expected ReviewStoreError: {expected_code}")


def _assert_review_lifecycle_error(fn: object, expected_code: str) -> None:
    assert callable(fn)
    try:
        fn()
    except ReviewLifecycleError as exc:
        _assert(exc.code == expected_code, f"unexpected ReviewLifecycleError: {exc.code}")
        _assert(str(exc) == expected_code, "Review lifecycle error disclosed extra detail")
    else:
        raise AssertionError(f"expected ReviewLifecycleError: {expected_code}")


def _sample_payload() -> dict[str, object]:
    return json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))


def _render_sample(mode: str) -> str:
    return run_hermes_manager_pilot(SAMPLE_INPUT, mode)


def _sample_queue_payload(result_type: str = "implementation") -> dict[str, object]:
    approval_stage = result_type in {"implementation", "review", "commit"}
    payload: dict[str, object] = {
        "queue_type": "hermes_prompt_queue",
        "version": "0.1B-2",
        "projects": [
            {
                "project_id": "jarvis-core",
                "display_name": "Jarvis Core",
                "repo_path": r"C:\work\jarvis-core",
                "expected_branch": "main",
                "expected_head": "3b64e92",
                "protected_paths": ["jarvis.bat"],
                "expected_untracked": ["jarvis.bat"],
                "forbidden_actions": sorted(REQUIRED_FORBIDDEN_ACTIONS),
                "validation_commands": [
                    "python -B apps/hermes-manager-pilot/run_smoke_tests.py",
                    "git diff --check",
                ],
            }
        ],
        "items": [
            {
                "item_id": "queue-001",
                "project_id": "jarvis-core",
                "current_goal": "Build a human-approved local prompt queue.",
                "current_task": "Add in-memory queue validation.",
                "result_type": result_type,
                "target_files": [
                    "apps/hermes-manager-pilot/hermes_manager_pilot/prompt_queue.py",
                    "apps/hermes-manager-pilot/run_smoke_tests.py",
                ],
                "observed_branch": "main",
                "observed_head": "3b64e92",
                "observed_git_status": [
                    " M apps/hermes-manager-pilot/run_smoke_tests.py",
                    "?? apps/hermes-manager-pilot/hermes_manager_pilot/prompt_queue.py",
                    "?? jarvis.bat",
                ],
                "scope_approved": approval_stage,
                "review_passed": False,
                "commit_approved": False,
                "scope_approval_digest": "",
                "change_evidence_digest": "5" * 64 if result_type in {"review", "commit"} else "",
                "review_approval_digest": "",
                "commit_approval_digest": "",
                "commit_message": "",
                "last_prompt_summary": "Implement the approved v0.1B-2 unit.",
                "last_result_summary": "",
            }
        ],
    }
    if approval_stage:
        scope_payload = copy.deepcopy(payload)
        scope_items = scope_payload["items"]
        assert isinstance(scope_items, list) and isinstance(scope_items[0], dict)
        scope_items[0]["result_type"] = "implementation"
        scope_items[0]["change_evidence_digest"] = ""
        scope_queue = normalize_prompt_queue(scope_payload)
        scope_binding = build_scope_approval_binding(
            scope_queue.projects[0],
            scope_queue.items[0],
        )
        items = payload["items"]
        assert isinstance(items, list) and isinstance(items[0], dict)
        items[0]["scope_approval_digest"] = scope_binding.digest
    return payload


def _complete_commit_approval_bindings(payload: dict[str, object]) -> None:
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    item = items[0]
    scope_digest = item["scope_approval_digest"]
    evidence_digest = item["change_evidence_digest"]
    assert isinstance(scope_digest, str) and isinstance(evidence_digest, str)

    review_payload = copy.deepcopy(payload)
    review_items = review_payload["items"]
    assert isinstance(review_items, list) and isinstance(review_items[0], dict)
    review_items[0]["result_type"] = "review"
    review_items[0]["commit_approved"] = False
    review_items[0]["commit_approval_digest"] = ""
    review_queue = normalize_prompt_queue(review_payload)
    review_binding = build_review_approval_binding(
        review_queue.projects[0],
        review_queue.items[0],
        scope_digest=scope_digest,
        change_evidence_digest=evidence_digest,
    )
    item["review_approval_digest"] = review_binding.digest

    commit_queue = normalize_prompt_queue(payload)
    commit_binding = build_commit_approval_binding(
        commit_queue.projects[0],
        commit_queue.items[0],
        scope_digest=scope_digest,
        review_digest=review_binding.digest,
        change_evidence_digest=evidence_digest,
    )
    item["commit_approval_digest"] = commit_binding.digest


def _run_fixture_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(f"fixture git command failed: git {' '.join(args)}: {completed.stderr}")
    return completed.stdout.strip()


def _create_change_evidence_fixture(temp_dir: str) -> tuple[Path, object, object]:
    repo = Path(temp_dir).resolve()
    _run_fixture_git(repo, "init", "-b", "main")
    _run_fixture_git(repo, "config", "user.email", "hermes-smoke@example.invalid")
    _run_fixture_git(repo, "config", "user.name", "Hermes Smoke")
    _run_fixture_git(repo, "config", "core.autocrlf", "false")

    source_dir = repo / "src"
    source_dir.mkdir()
    (source_dir / "tracked.txt").write_text("baseline tracked\n", encoding="utf-8")
    (source_dir / "deleted.txt").write_text("delete this baseline\n", encoding="utf-8")
    (source_dir / "binary.bin").write_bytes(b"\x00baseline\xff")
    _run_fixture_git(repo, "add", "src/tracked.txt", "src/deleted.txt", "src/binary.bin")
    _run_fixture_git(repo, "commit", "-m", "baseline")
    head = _run_fixture_git(repo, "rev-parse", "HEAD")

    (repo / "known.local").write_text("known untracked boundary\n", encoding="utf-8")
    (source_dir / "tracked.txt").write_text("changed tracked evidence\n", encoding="utf-8")
    (source_dir / "deleted.txt").unlink()
    (source_dir / "binary.bin").write_bytes(b"\x00changed evidence\xfe")
    (source_dir / "new.txt").write_text("new untracked evidence\n", encoding="utf-8")

    payload = {
        "queue_type": "hermes_prompt_queue",
        "version": "0.1B-2",
        "projects": [
            {
                "project_id": "evidence-fixture",
                "display_name": "Evidence Fixture",
                "repo_path": str(repo),
                "expected_branch": "main",
                "expected_head": head,
                "protected_paths": ["known.local"],
                "expected_untracked": ["known.local"],
                "forbidden_actions": sorted(REQUIRED_FORBIDDEN_ACTIONS),
                "validation_commands": ["git diff --check"],
            }
        ],
        "items": [
            {
                "item_id": "evidence-001",
                "project_id": "evidence-fixture",
                "current_goal": "Collect bounded local change evidence.",
                "current_task": "Hash exact target files without persistence.",
                "result_type": "review",
                "target_files": [
                    "src/tracked.txt",
                    "src/deleted.txt",
                    "src/binary.bin",
                    "src/new.txt",
                ],
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
                "last_prompt_summary": "",
                "last_result_summary": "",
            }
        ],
    }
    queue = normalize_prompt_queue(payload)
    return repo, queue.projects[0], queue.items[0]


def _create_valid_review_observation_fixture(
    temp_dir: str,
) -> tuple[Path, object, object, object, QueueObservationEvaluation]:
    repo, project, item = _create_change_evidence_fixture(temp_dir)
    implementation_item = replace(item, result_type="implementation")
    scope_binding = build_scope_approval_binding(project, implementation_item)
    review_item = replace(
        item,
        scope_approved=True,
        scope_approval_digest=scope_binding.digest,
    )
    bundle = collect_review_evidence_bundle(repo, project, review_item)
    queue = PromptQueueState(projects=(project,), items=(review_item,))
    observation = evaluate_review_evidence_in_queue(
        queue,
        review_item.item_id,
        bundle,
    )
    return repo, project, review_item, bundle, observation


def _test_implementation_prompt_deterministic() -> None:
    first = _render_sample("implementation-prompt")
    second = _render_sample("implementation-prompt")
    _assert(first == second, "implementation prompt should be deterministic")
    _assert("# Codex Implementation Prompt" in first, "implementation prompt title missing")


def _test_review_prompt_deterministic() -> None:
    first = _render_sample("review-prompt")
    second = _render_sample("review-prompt")
    _assert(first == second, "review prompt should be deterministic")
    _assert("# Codex Review Prompt" in first, "review prompt title missing")


def _test_commit_prompt_deterministic() -> None:
    first = _render_sample("commit-prompt")
    second = _render_sample("commit-prompt")
    _assert(first == second, "commit prompt should be deterministic")
    _assert("# Codex Commit Prompt" in first, "commit prompt title missing")


def _test_checkpoint_summary_deterministic() -> None:
    first = _render_sample("checkpoint-summary")
    second = _render_sample("checkpoint-summary")
    _assert(first == second, "checkpoint summary should be deterministic")
    _assert("# Hermes Manager Pilot Checkpoint Summary" in first, "checkpoint title missing")


def _test_sample_rendered_files_match_renderer_output() -> None:
    for mode, sample_path in SAMPLE_RENDERED_FILES.items():
        rendered = _render_sample(mode)
        expected = sample_path.read_text(encoding="utf-8")
        _assert(rendered == expected, f"sample rendered file is stale for {mode}")


def _test_stdout_mode_does_not_create_repo_file() -> None:
    before = _repo_file_set()
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(APP_ROOT / "run_demo.py"),
            "--input",
            str(SAMPLE_INPUT),
            "--mode",
            "implementation-prompt",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    after = _repo_file_set()
    _assert(completed.returncode == 0, f"stdout demo failed: {completed.stderr}")
    _assert("# Codex Implementation Prompt" in completed.stdout, "stdout prompt missing")
    _assert(before == after, "stdout mode created or removed repository files")


def _test_output_mode_writes_only_requested_file() -> None:
    before = _repo_file_set()
    with tempfile.TemporaryDirectory(prefix="hermes-manager-pilot-smoke-") as temp_dir:
        output_path = Path(temp_dir) / "implementation-prompt.md"
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(APP_ROOT / "run_demo.py"),
                "--input",
                str(SAMPLE_INPUT),
                "--mode",
                "implementation-prompt",
                "--output",
                str(output_path),
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        after = _repo_file_set()
        _assert(completed.returncode == 0, f"output demo failed: {completed.stderr}")
        _assert(output_path.exists(), "explicit output file was not created")
        _assert("# Codex Implementation Prompt" in output_path.read_text(encoding="utf-8"), "output prompt missing")
        _assert(before == after, "output mode changed repository files")


def _test_push_allowed_true_fails_validation() -> None:
    payload = _sample_payload()
    payload["push_allowed"] = True
    try:
        normalize_session_state(payload)
    except ValidationError as exc:
        _assert("push_allowed=true is not allowed" in str(exc), f"unexpected error: {exc}")
    else:
        raise AssertionError("push_allowed=true should fail validation")


def _test_commit_allowed_without_approval_fails_validation() -> None:
    payload = _sample_payload()
    payload["commit_allowed"] = True
    payload["human_approval_required"] = False
    try:
        normalize_session_state(payload)
    except ValidationError as exc:
        _assert("commit_allowed=true requires" in str(exc), f"unexpected error: {exc}")
    else:
        raise AssertionError("commit_allowed=true without approval boundary should fail validation")


def _test_commit_allowed_without_granted_approval_renders_boundary() -> None:
    payload = _sample_payload()
    payload["commit_allowed"] = True
    payload["human_approval_required"] = True
    payload["human_approval_granted"] = False
    session = normalize_session_state(payload)
    rendered = render_commit_prompt(session)
    _assert("Do not commit." in rendered, "commit prompt should not instruct commit without granted approval")
    _assert("approval has not been recorded" in rendered, "missing approval boundary explanation")
    _assert("Run `git status --short`." not in rendered, "executable commit checklist rendered too early")


def _test_protected_path_in_files_touched_fails_validation() -> None:
    payload = _sample_payload()
    files_touched = copy.deepcopy(payload["files_touched"])
    assert isinstance(files_touched, list)
    files_touched.append("jarvis.bat")
    payload["files_touched"] = files_touched
    try:
        normalize_session_state(payload)
    except ValidationError as exc:
        _assert("protected paths must not appear" in str(exc), f"unexpected error: {exc}")
    else:
        raise AssertionError("protected path in files_touched should fail validation")


def _test_secret_like_fields_fail_validation() -> None:
    for forbidden_field in ("api_key", "token", "password", "secret", "credential"):
        payload = _sample_payload()
        payload[forbidden_field] = "do-not-store"
        try:
            normalize_session_state(payload)
        except ValidationError as exc:
            _assert("secrets must not be stored" in str(exc), f"unexpected error: {exc}")
        else:
            raise AssertionError(f"{forbidden_field} should fail validation")

    payload = _sample_payload()
    payload["nested"] = [{"token": "do-not-store"}]
    try:
        normalize_session_state(payload)
    except ValidationError as exc:
        _assert("secrets must not be stored" in str(exc), f"unexpected error: {exc}")
    else:
        raise AssertionError("nested secret-like field should fail validation")

    for forbidden_reasoning_field in (
        "chain_of_thought",
        "chain-of-thought",
        "hidden_reasoning",
        "scratchpad",
        "private_notes",
    ):
        payload = _sample_payload()
        payload[forbidden_reasoning_field] = "do-not-store"
        try:
            normalize_session_state(payload)
        except ValidationError as exc:
            _assert("hidden reasoning must not be stored" in str(exc), f"unexpected error: {exc}")
        else:
            raise AssertionError(f"{forbidden_reasoning_field} should fail validation")


def _test_unknown_next_action_fails_validation() -> None:
    payload = _sample_payload()
    payload["next_action"] = "AUTO_RUN_CODEX"
    try:
        normalize_session_state(payload)
    except ValidationError as exc:
        _assert("next_action is invalid" in str(exc), f"unexpected error: {exc}")
    else:
        raise AssertionError("unknown next_action should fail validation")


def _test_list_fields_must_be_lists() -> None:
    for field in ("validation_commands", "files_touched"):
        payload = _sample_payload()
        payload[field] = "python -B example.py"
        try:
            normalize_session_state(payload)
        except ValidationError as exc:
            _assert(f"{field} must be a list of strings" in str(exc), f"unexpected error: {exc}")
        else:
            raise AssertionError(f"{field} as a string should fail validation")


def _test_protected_paths_required_and_sample_includes_jarvis() -> None:
    payload = _sample_payload()
    protected_paths = payload["protected_paths"]
    _assert(isinstance(protected_paths, list), "sample protected_paths must be a list")
    _assert("jarvis.bat" in protected_paths, "sample protected_paths must include jarvis.bat")

    payload["protected_paths"] = []
    try:
        normalize_session_state(payload)
    except ValidationError as exc:
        _assert("protected_paths must include" in str(exc), f"unexpected error: {exc}")
    else:
        raise AssertionError("empty protected_paths should fail validation")


def _test_prompts_include_jarvis_protection() -> None:
    for mode in ("implementation-prompt", "review-prompt", "commit-prompt", "checkpoint-summary"):
        rendered = _render_sample(mode)
        _assert("jarvis.bat" in rendered, f"jarvis.bat protection missing from {mode}")


def _test_prompts_include_no_auto_push() -> None:
    for mode in ("implementation-prompt", "review-prompt", "commit-prompt", "checkpoint-summary"):
        rendered = _render_sample(mode)
        _assert("Do not push" in rendered or "auto push" in rendered or "Push allowed: no" in rendered, f"no-push boundary missing from {mode}")


def _test_prompts_include_validation_commands() -> None:
    payload = _sample_payload()
    commands = payload["validation_commands"]
    assert isinstance(commands, list)
    for mode in ("implementation-prompt", "review-prompt", "commit-prompt", "checkpoint-summary"):
        rendered = _render_sample(mode)
        for command in commands:
            _assert(str(command) in rendered, f"validation command missing from {mode}: {command}")


def _test_commit_prompt_refuses_when_commit_disallowed() -> None:
    rendered = _render_sample("commit-prompt")
    _assert("Do not commit." in rendered, "commit prompt should refuse when commit_allowed is false")
    _assert("`commit_allowed` is false" in rendered, "commit refusal reason missing")


def _test_prompt_queue_evaluation_is_deterministic() -> None:
    payload = _sample_queue_payload()
    first_queue = normalize_prompt_queue(payload)
    second_queue = normalize_prompt_queue(copy.deepcopy(payload))
    first = evaluate_queue_item(first_queue, "queue-001")
    second = evaluate_queue_item(second_queue, "queue-001")
    _assert(first_queue == second_queue, "prompt queue normalization should be deterministic")
    _assert(first == second, "prompt queue evaluation should be deterministic")
    _assert(not first.is_blocked, f"valid implementation item was blocked: {first.blocking_reasons}")
    _assert(first.result_type == "implementation", "implementation result type was not preserved")
    _assert(first.next_action == "PROMPT_FOR_CODEX", "implementation next action is wrong")
    _assert(first.render_mode == "implementation-prompt", "implementation render mode is wrong")


def _test_prompt_queue_result_types_map_to_safe_actions() -> None:
    expected = {
        "design": ("STATUS_SUMMARY", "checkpoint-summary", False),
        "review": ("REVIEW_REQUEST", "review-prompt", False),
        "blocked": ("BLOCKED_NEEDS_USER", "checkpoint-summary", True),
    }
    for requested_type, (next_action, render_mode, should_block) in expected.items():
        queue = normalize_prompt_queue(_sample_queue_payload(result_type=requested_type))
        evaluation = evaluate_queue_item(queue, "queue-001")
        _assert(evaluation.is_blocked == should_block, f"wrong blocked state for {requested_type}")
        _assert(evaluation.next_action == next_action, f"wrong next action for {requested_type}")
        _assert(evaluation.render_mode == render_mode, f"wrong render mode for {requested_type}")


def _test_prompt_queue_supports_multiple_project_cards() -> None:
    payload = _sample_queue_payload(result_type="design")
    projects = payload["projects"]
    assert isinstance(projects, list)
    second_project = copy.deepcopy(projects[0])
    assert isinstance(second_project, dict)
    second_project.update(
        {
            "project_id": "second-local-project",
            "display_name": "Second Local Project",
            "repo_path": r"C:\work\second-local-project",
            "expected_head": "abc1234",
            "protected_paths": ["local-only.bat"],
            "expected_untracked": [],
        }
    )
    projects.append(second_project)
    queue = normalize_prompt_queue(payload)
    _assert(len(queue.projects) == 2, "multiple project cards were not preserved")
    _assert(queue.projects[1].repo_path == r"C:\work\second-local-project", "second repo path changed")


def _test_prompt_queue_git_mismatch_blocks_for_user() -> None:
    payload = _sample_queue_payload()
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["observed_head"] = "unexpected-head"
    items[0]["observed_git_status"] = [
        " M docs/unrelated.md",
        "?? unexpected.tmp",
    ]
    queue = normalize_prompt_queue(payload)
    evaluation = evaluate_queue_item(queue, "queue-001")
    reasons = "\n".join(evaluation.blocking_reasons)
    _assert(evaluation.is_blocked, "git mismatch should block the queue item")
    _assert(evaluation.result_type == "blocked", "blocked result type was not assigned")
    _assert(evaluation.next_action == "BLOCKED_NEEDS_USER", "blocked next action is wrong")
    _assert(evaluation.render_mode == "checkpoint-summary", "blocked item should only render a summary")
    _assert("does not match expected HEAD" in reasons, "HEAD mismatch reason missing")
    _assert("outside target files" in reasons, "out-of-scope change reason missing")
    _assert("unexpected untracked path" in reasons, "unexpected untracked reason missing")
    _assert("expected untracked path is missing" in reasons, "missing expected untracked reason missing")


def _test_prompt_queue_protected_or_staged_change_blocks() -> None:
    payload = _sample_queue_payload()
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["observed_git_status"] = [
        "M  apps/hermes-manager-pilot/run_smoke_tests.py",
        "M  jarvis.bat",
        "?? jarvis.bat",
    ]
    queue = normalize_prompt_queue(payload)
    evaluation = evaluate_queue_item(queue, "queue-001")
    reasons = "\n".join(evaluation.blocking_reasons)
    _assert(evaluation.is_blocked, "protected or staged changes should block")
    _assert("protected path has tracked changes: jarvis.bat" in reasons, "protected path reason missing")
    _assert("staged change exists" in reasons, "staged change reason missing")

    payload = _sample_queue_payload()
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    target_files = items[0]["target_files"]
    assert isinstance(target_files, list)
    target_files.append("jarvis.bat")
    target_evaluation = evaluate_queue_item(normalize_prompt_queue(payload), "queue-001")
    _assert(target_evaluation.is_blocked, "protected target file should block")
    _assert(
        "target file is protected: jarvis.bat" in target_evaluation.blocking_reasons,
        "protected target reason missing",
    )


def _test_prompt_queue_scope_and_commit_approvals_are_separate() -> None:
    implementation_payload = _sample_queue_payload()
    implementation_items = implementation_payload["items"]
    assert isinstance(implementation_items, list) and isinstance(implementation_items[0], dict)
    implementation_items[0]["scope_approved"] = False
    implementation_queue = normalize_prompt_queue(implementation_payload)
    implementation_evaluation = evaluate_queue_item(implementation_queue, "queue-001")
    _assert(implementation_evaluation.is_blocked, "implementation without scope approval should block")
    _assert(
        "scope approval is required" in implementation_evaluation.blocking_reasons,
        "scope approval gate reason missing",
    )

    empty_scope_payload = _sample_queue_payload()
    empty_scope_items = empty_scope_payload["items"]
    assert isinstance(empty_scope_items, list) and isinstance(empty_scope_items[0], dict)
    empty_scope_items[0]["target_files"] = []
    empty_scope_items[0]["observed_git_status"] = ["?? jarvis.bat"]
    empty_scope_evaluation = evaluate_queue_item(
        normalize_prompt_queue(empty_scope_payload), "queue-001"
    )
    _assert(empty_scope_evaluation.is_blocked, "implementation with empty target scope should block")
    _assert(
        "an explicit target file scope is required" in empty_scope_evaluation.blocking_reasons,
        "empty target scope reason missing",
    )

    empty_review_payload = _sample_queue_payload(result_type="review")
    empty_review_items = empty_review_payload["items"]
    assert isinstance(empty_review_items, list) and isinstance(empty_review_items[0], dict)
    empty_review_items[0]["observed_git_status"] = ["?? jarvis.bat"]
    empty_review_evaluation = evaluate_queue_item(
        normalize_prompt_queue(empty_review_payload), "queue-001"
    )
    _assert(empty_review_evaluation.is_blocked, "review without observed changes should block")
    _assert(
        "review and commit steps require observed target changes"
        in empty_review_evaluation.blocking_reasons,
        "missing review evidence reason absent",
    )

    payload = _sample_queue_payload(result_type="commit")
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    queue = normalize_prompt_queue(payload)
    evaluation = evaluate_queue_item(queue, "queue-001")
    reasons = "\n".join(evaluation.blocking_reasons)
    _assert(evaluation.is_blocked, "commit without review and approval should block")
    _assert("passed review" in reasons, "review gate reason missing")
    _assert("explicit commit approval" in reasons, "commit approval gate reason missing")
    _assert("approved commit message" in reasons, "commit message gate reason missing")

    items[0]["review_passed"] = True
    items[0]["commit_approved"] = True
    items[0]["commit_message"] = "hermes: add prompt queue primitives"
    _complete_commit_approval_bindings(payload)
    approved_queue = normalize_prompt_queue(payload)
    approved = evaluate_queue_item(approved_queue, "queue-001")
    _assert(not approved.is_blocked, f"approved commit item was blocked: {approved.blocking_reasons}")
    _assert(approved.result_type == "commit", "approved commit result type is wrong")
    _assert(approved.next_action == "COMMIT_REQUEST", "approved commit next action is wrong")
    _assert(approved.render_mode == "commit-prompt", "approved commit render mode is wrong")


def _test_prompt_queue_missing_safety_policy_blocks() -> None:
    payload = _sample_queue_payload()
    projects = payload["projects"]
    assert isinstance(projects, list) and isinstance(projects[0], dict)
    projects[0]["forbidden_actions"] = ["push"]
    queue = normalize_prompt_queue(payload)
    evaluation = evaluate_queue_item(queue, "queue-001")
    reasons = "\n".join(evaluation.blocking_reasons)
    _assert(evaluation.is_blocked, "incomplete forbidden actions should block")
    _assert("missing forbidden actions" in reasons, "missing safety policy reason absent")


def _test_prompt_queue_rejects_unknown_fields_and_unsafe_paths() -> None:
    payload = _sample_queue_payload()
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["api_key"] = "must-not-be-stored"
    try:
        normalize_prompt_queue(payload)
    except ValidationError as exc:
        _assert("unknown fields" in str(exc), f"unexpected unknown-field error: {exc}")
    else:
        raise AssertionError("unknown secret-like fields should fail closed")

    payload = _sample_queue_payload()
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["target_files"] = [r"C:\work\outside.txt"]
    try:
        normalize_prompt_queue(payload)
    except ValidationError as exc:
        _assert("repository-relative paths" in str(exc), f"unexpected path error: {exc}")
    else:
        raise AssertionError("absolute target paths should fail validation")

    payload = _sample_queue_payload()
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["observed_git_status"] = [" ? unsafe.txt", "?? jarvis.bat"]
    queue = normalize_prompt_queue(payload)
    evaluation = evaluate_queue_item(queue, "queue-001")
    _assert(evaluation.is_blocked, "unsupported git status codes should fail closed")
    _assert(
        any("unsupported git status code" in reason for reason in evaluation.blocking_reasons),
        "unsupported status reason missing",
    )


def _test_prompt_queue_renderer_mapping_preserves_safety_boundaries() -> None:
    payload = _sample_queue_payload(result_type="commit")
    queue = normalize_prompt_queue(payload)
    blocked_session = build_hermes_session(queue, "queue-001")
    _assert(blocked_session.next_action == "BLOCKED_NEEDS_USER", "blocked session next action is unsafe")
    _assert(not blocked_session.commit_allowed, "blocked session must not allow commit")
    _assert(not blocked_session.push_allowed, "queue sessions must never allow push")
    _assert(not blocked_session.human_approval_granted, "blocked session must not grant approval")
    _assert("jarvis.bat" not in blocked_session.files_touched, "protected path leaked into files_touched")

    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["review_passed"] = True
    items[0]["commit_approved"] = True
    items[0]["commit_message"] = "hermes: add prompt queue primitives"
    _complete_commit_approval_bindings(payload)
    approved_session = build_hermes_session(normalize_prompt_queue(payload), "queue-001")
    _assert(approved_session.next_action == "COMMIT_REQUEST", "approved session next action is wrong")
    _assert(approved_session.commit_allowed, "approved session should allow a local commit prompt")
    _assert(approved_session.human_approval_granted, "explicit commit approval was not mapped")
    _assert(not approved_session.push_allowed, "approved commit must still prohibit push")


def _test_approval_bindings_are_deterministic_and_domain_separated() -> None:
    implementation_queue = normalize_prompt_queue(_sample_queue_payload())
    project = implementation_queue.projects[0]
    implementation_item = implementation_queue.items[0]
    first_scope = build_scope_approval_binding(project, implementation_item)
    second_scope = build_scope_approval_binding(project, implementation_item)
    _assert(first_scope == second_scope, "scope approval binding should be deterministic")
    _assert(digest_matches(first_scope, first_scope.digest), "scope digest should match itself")
    _assert(not digest_matches(first_scope, first_scope.digest.upper()), "uppercase digest should fail closed")

    evidence_digest = "1" * 64
    review_queue = normalize_prompt_queue(_sample_queue_payload(result_type="review"))
    review = build_review_approval_binding(
        review_queue.projects[0],
        review_queue.items[0],
        scope_digest=first_scope.digest,
        change_evidence_digest=evidence_digest,
    )

    commit_payload = _sample_queue_payload(result_type="commit")
    commit_items = commit_payload["items"]
    assert isinstance(commit_items, list) and isinstance(commit_items[0], dict)
    commit_items[0]["commit_message"] = "hermes: bind prompt queue approvals"
    commit_queue = normalize_prompt_queue(commit_payload)
    commit = build_commit_approval_binding(
        commit_queue.projects[0],
        commit_queue.items[0],
        scope_digest=first_scope.digest,
        review_digest=review.digest,
        change_evidence_digest=evidence_digest,
    )

    _assert(len({first_scope.digest, review.digest, commit.digest}) == 3, "binding domains overlap")
    _assert(first_scope.snapshot()["result_type"] == "implementation", "scope result type missing")
    _assert(review.snapshot()["result_type"] == "review", "review result type missing")
    _assert(commit.snapshot()["result_type"] == "commit", "commit result type missing")
    _assert(commit.snapshot()["commit_message"] == commit_queue.items[0].commit_message, "commit message not bound")


def _test_scope_binding_is_stable_for_set_order_and_changes_for_scope_mutation() -> None:
    payload = _sample_queue_payload()
    queue = normalize_prompt_queue(payload)
    baseline = build_scope_approval_binding(queue.projects[0], queue.items[0])

    reordered = copy.deepcopy(payload)
    projects = reordered["projects"]
    items = reordered["items"]
    assert isinstance(projects, list) and isinstance(projects[0], dict)
    assert isinstance(items, list) and isinstance(items[0], dict)
    forbidden_actions = projects[0]["forbidden_actions"]
    target_files = items[0]["target_files"]
    assert isinstance(forbidden_actions, list) and isinstance(target_files, list)
    projects[0]["forbidden_actions"] = list(reversed(forbidden_actions))
    items[0]["target_files"] = list(reversed(target_files))
    reordered_queue = normalize_prompt_queue(reordered)
    reordered_binding = build_scope_approval_binding(
        reordered_queue.projects[0], reordered_queue.items[0]
    )
    _assert(baseline.digest == reordered_binding.digest, "set-like input order changed scope digest")

    mutations = (
        ("expected HEAD", lambda value: value["projects"][0].__setitem__("expected_head", "changed-head")),
        ("goal", lambda value: value["items"][0].__setitem__("current_goal", "Changed goal.")),
        (
            "target files",
            lambda value: value["items"][0]["target_files"].append("docs/new-scope.md"),
        ),
        (
            "protected paths",
            lambda value: value["projects"][0]["protected_paths"].append("protected.local"),
        ),
    )
    for label, mutate in mutations:
        changed_payload = copy.deepcopy(payload)
        mutate(changed_payload)
        changed_queue = normalize_prompt_queue(changed_payload)
        changed = build_scope_approval_binding(changed_queue.projects[0], changed_queue.items[0])
        _assert(changed.digest != baseline.digest, f"{label} mutation did not invalidate scope digest")


def _test_approval_binding_chain_rejects_stale_scope_review_and_message() -> None:
    implementation_queue = normalize_prompt_queue(_sample_queue_payload())
    scope = build_scope_approval_binding(
        implementation_queue.projects[0], implementation_queue.items[0]
    )
    evidence_digest = "2" * 64

    changed_review_payload = _sample_queue_payload(result_type="review")
    changed_review_items = changed_review_payload["items"]
    assert isinstance(changed_review_items, list) and isinstance(changed_review_items[0], dict)
    targets = changed_review_items[0]["target_files"]
    assert isinstance(targets, list)
    targets.append("docs/stale-scope.md")
    changed_review_queue = normalize_prompt_queue(changed_review_payload)
    try:
        build_review_approval_binding(
            changed_review_queue.projects[0],
            changed_review_queue.items[0],
            scope_digest=scope.digest,
            change_evidence_digest=evidence_digest,
        )
    except ValidationError as exc:
        _assert("scope approval binding is stale" in str(exc), f"unexpected stale scope error: {exc}")
    else:
        raise AssertionError("changed scope should reject a prior scope binding")

    review_queue = normalize_prompt_queue(_sample_queue_payload(result_type="review"))
    review = build_review_approval_binding(
        review_queue.projects[0],
        review_queue.items[0],
        scope_digest=scope.digest,
        change_evidence_digest=evidence_digest,
    )
    commit_payload = _sample_queue_payload(result_type="commit")
    commit_items = commit_payload["items"]
    assert isinstance(commit_items, list) and isinstance(commit_items[0], dict)
    commit_items[0]["commit_message"] = "hermes: bind prompt queue approvals"
    commit_queue = normalize_prompt_queue(commit_payload)
    try:
        build_commit_approval_binding(
            commit_queue.projects[0],
            commit_queue.items[0],
            scope_digest=scope.digest,
            review_digest=review.digest,
            change_evidence_digest="3" * 64,
        )
    except ValidationError as exc:
        _assert("review approval binding is stale" in str(exc), f"unexpected stale review error: {exc}")
    else:
        raise AssertionError("changed evidence should reject a prior review binding")

    first_commit = build_commit_approval_binding(
        commit_queue.projects[0],
        commit_queue.items[0],
        scope_digest=scope.digest,
        review_digest=review.digest,
        change_evidence_digest=evidence_digest,
    )
    commit_items[0]["commit_message"] = "hermes: use a different approved message"
    changed_commit_queue = normalize_prompt_queue(commit_payload)
    changed_commit = build_commit_approval_binding(
        changed_commit_queue.projects[0],
        changed_commit_queue.items[0],
        scope_digest=scope.digest,
        review_digest=review.digest,
        change_evidence_digest=evidence_digest,
    )
    _assert(first_commit.digest != changed_commit.digest, "commit message change did not invalidate binding")


def _test_approval_binding_rejects_wrong_stage_bad_digest_and_oversize_snapshot() -> None:
    review_queue = normalize_prompt_queue(_sample_queue_payload(result_type="review"))
    try:
        build_scope_approval_binding(review_queue.projects[0], review_queue.items[0])
    except ValidationError as exc:
        _assert("result_type=implementation" in str(exc), f"unexpected stage error: {exc}")
    else:
        raise AssertionError("scope binding should reject a review item")

    try:
        build_review_approval_binding(
            review_queue.projects[0],
            review_queue.items[0],
            scope_digest="not-a-digest",
            change_evidence_digest="4" * 64,
        )
    except ValidationError as exc:
        _assert("lowercase SHA-256" in str(exc), f"unexpected digest error: {exc}")
    else:
        raise AssertionError("malformed prior digest should fail validation")

    oversized_payload = _sample_queue_payload()
    projects = oversized_payload["projects"]
    assert isinstance(projects, list) and isinstance(projects[0], dict)
    projects[0]["validation_commands"] = ["x" * 1000 for _ in range(128)]
    oversized_queue = normalize_prompt_queue(oversized_payload)
    try:
        build_scope_approval_binding(oversized_queue.projects[0], oversized_queue.items[0])
    except ValidationError as exc:
        _assert("snapshot is too large" in str(exc), f"unexpected size error: {exc}")
    else:
        raise AssertionError("oversized approval snapshot should fail validation")


def _test_approval_binding_excludes_mutable_summaries_and_authorization_flags() -> None:
    payload = _sample_queue_payload()
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["last_prompt_summary"] = "mutable prompt summary"
    items[0]["last_result_summary"] = "mutable result summary"
    items[0]["scope_approved"] = True
    queue = normalize_prompt_queue(payload)
    binding = build_scope_approval_binding(queue.projects[0], queue.items[0])
    canonical_text = binding.canonical_bytes.decode("utf-8")
    for excluded in (
        "mutable prompt summary",
        "mutable result summary",
        "scope_approved",
        "review_passed",
        "commit_approved",
    ):
        _assert(excluded not in canonical_text, f"non-authority field leaked into binding: {excluded}")


def _test_binding_enforcement_rejects_legacy_missing_malformed_and_stale_scope() -> None:
    legacy_payload = _sample_queue_payload()
    legacy_payload["version"] = "0.1A"
    try:
        normalize_prompt_queue(legacy_payload)
    except ValidationError as exc:
        _assert("version must be 0.1B-2" in str(exc), f"unexpected legacy version error: {exc}")
    else:
        raise AssertionError("legacy queue version should fail closed")

    for supplied_digest, expected_reason in (
        ("", "scope approval digest is missing"),
        ("NOT-A-DIGEST", "scope approval digest is malformed"),
    ):
        payload = _sample_queue_payload()
        items = payload["items"]
        assert isinstance(items, list) and isinstance(items[0], dict)
        items[0]["scope_approval_digest"] = supplied_digest
        evaluation = evaluate_queue_item(normalize_prompt_queue(payload), "queue-001")
        _assert(evaluation.is_blocked, "missing or malformed scope digest should block")
        _assert(expected_reason in evaluation.blocking_reasons, f"missing binding reason: {expected_reason}")

    stale_payload = _sample_queue_payload()
    stale_items = stale_payload["items"]
    assert isinstance(stale_items, list) and isinstance(stale_items[0], dict)
    stale_items[0]["current_task"] = "Changed after scope approval."
    stale_evaluation = evaluate_queue_item(normalize_prompt_queue(stale_payload), "queue-001")
    _assert(stale_evaluation.is_blocked, "changed task should invalidate scope approval")
    _assert(
        "scope approval binding is stale" in stale_evaluation.blocking_reasons,
        "stale scope binding reason missing",
    )


def _test_binding_enforcement_requires_review_evidence_and_matching_review_digest() -> None:
    missing_evidence_payload = _sample_queue_payload(result_type="review")
    missing_evidence_items = missing_evidence_payload["items"]
    assert isinstance(missing_evidence_items, list) and isinstance(missing_evidence_items[0], dict)
    missing_evidence_items[0]["change_evidence_digest"] = ""
    missing_evidence = evaluate_queue_item(
        normalize_prompt_queue(missing_evidence_payload), "queue-001"
    )
    _assert(missing_evidence.is_blocked, "review without change evidence should block")
    _assert(
        "change evidence digest is missing" in missing_evidence.blocking_reasons,
        "missing evidence reason absent",
    )

    payload = _sample_queue_payload(result_type="review")
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["review_passed"] = True
    missing_review = evaluate_queue_item(normalize_prompt_queue(payload), "queue-001")
    _assert(missing_review.is_blocked, "passed review without binding should block")
    _assert(
        "review approval digest is missing" in missing_review.blocking_reasons,
        "missing review binding reason absent",
    )

    review_queue = normalize_prompt_queue(payload)
    review_binding = build_review_approval_binding(
        review_queue.projects[0],
        review_queue.items[0],
        scope_digest=review_queue.items[0].scope_approval_digest,
        change_evidence_digest=review_queue.items[0].change_evidence_digest,
    )
    items[0]["review_approval_digest"] = review_binding.digest
    approved_review = evaluate_queue_item(normalize_prompt_queue(payload), "queue-001")
    _assert(not approved_review.is_blocked, f"matching review binding was blocked: {approved_review.blocking_reasons}")

    observed_status = items[0]["observed_git_status"]
    assert isinstance(observed_status, list)
    observed_status[1] = " M apps/hermes-manager-pilot/hermes_manager_pilot/prompt_queue.py"
    stale_review = evaluate_queue_item(normalize_prompt_queue(payload), "queue-001")
    _assert(stale_review.is_blocked, "changed Git observation should invalidate review binding")
    _assert(
        "review approval binding is stale" in stale_review.blocking_reasons,
        "stale review binding reason missing",
    )


def _test_binding_enforcement_requires_matching_commit_digest_and_blocks_renderer() -> None:
    payload = _sample_queue_payload(result_type="commit")
    items = payload["items"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    items[0]["review_passed"] = True
    items[0]["commit_approved"] = True
    items[0]["commit_message"] = "hermes: enforce approval bindings"
    _complete_commit_approval_bindings(payload)

    approved_queue = normalize_prompt_queue(payload)
    approved = evaluate_queue_item(approved_queue, "queue-001")
    _assert(not approved.is_blocked, f"complete binding chain was blocked: {approved.blocking_reasons}")
    approved_session = build_hermes_session(approved_queue, "queue-001")
    _assert(approved_session.commit_allowed, "complete binding chain should allow commit prompt")

    items[0]["commit_message"] = "hermes: changed after commit approval"
    stale_queue = normalize_prompt_queue(payload)
    stale = evaluate_queue_item(stale_queue, "queue-001")
    _assert(stale.is_blocked, "changed commit message should invalidate commit binding")
    _assert(
        "commit approval binding is stale" in stale.blocking_reasons,
        "stale commit binding reason missing",
    )
    stale_session = build_hermes_session(stale_queue, "queue-001")
    _assert(not stale_session.commit_allowed, "renderer mapping bypassed stale commit binding")
    _assert(stale_session.next_action == "BLOCKED_NEEDS_USER", "stale commit did not block renderer")


def _test_binding_enforcement_rejects_orphan_metadata() -> None:
    design_payload = _sample_queue_payload(result_type="design")
    design_items = design_payload["items"]
    assert isinstance(design_items, list) and isinstance(design_items[0], dict)
    design_items[0]["scope_approved"] = True
    design_items[0]["scope_approval_digest"] = "6" * 64
    design_evaluation = evaluate_queue_item(normalize_prompt_queue(design_payload), "queue-001")
    _assert(design_evaluation.is_blocked, "design item with approval metadata should block")
    _assert(
        "approval binding metadata is not allowed for result_type=design"
        in design_evaluation.blocking_reasons,
        "orphan design approval reason missing",
    )

    implementation_payload = _sample_queue_payload()
    implementation_items = implementation_payload["items"]
    assert isinstance(implementation_items, list) and isinstance(implementation_items[0], dict)
    implementation_items[0]["review_approval_digest"] = "7" * 64
    implementation_evaluation = evaluate_queue_item(
        normalize_prompt_queue(implementation_payload), "queue-001"
    )
    _assert(implementation_evaluation.is_blocked, "implementation with review metadata should block")
    _assert(
        "review approval metadata is not allowed for implementation"
        in implementation_evaluation.blocking_reasons,
        "orphan implementation review reason missing",
    )


def _test_local_change_evidence_is_deterministic_bounded_and_read_only() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-change-evidence-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        index_path = repo / ".git" / "index"
        index_mtime_before = index_path.stat().st_mtime_ns
        prior_git_dir = os.environ.get("GIT_DIR")
        prior_config = os.environ.get("GIT_CONFIG_PARAMETERS")
        os.environ["GIT_DIR"] = str(repo / "missing-git-dir")
        os.environ["GIT_CONFIG_PARAMETERS"] = "'core.fsmonitor'='malicious-helper'"
        try:
            first = collect_local_change_evidence(repo, project, item)
        finally:
            if prior_git_dir is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = prior_git_dir
            if prior_config is None:
                os.environ.pop("GIT_CONFIG_PARAMETERS", None)
            else:
                os.environ["GIT_CONFIG_PARAMETERS"] = prior_config

        second = collect_local_change_evidence(repo, project, item)
        _assert(first == second, "local change evidence should be deterministic")
        _assert(first.project_id == project.project_id, "evidence project identity missing")
        _assert(first.item_id == item.item_id, "evidence item identity missing")
        _assert(first.version == "0.1C-0B", "evidence version is wrong")
        _assert(first.declared_repo_path, "declared repository path missing")
        _assert(len(first.change_evidence_digest) == 64, "change evidence digest length is wrong")
        _assert(first.branch == "main", "trusted branch was not collected")
        _assert(first.head == project.expected_head, "trusted HEAD was not collected")
        _assert("?? known.local" in first.scoped_git_status, "known untracked status missing")
        _assert("known.local" in first.status_scope_paths, "known untracked scope is not explicit")
        _assert("scoped_git_status" in first.snapshot(), "scoped status label missing")
        _assert("observed_git_status" not in first.snapshot(), "scoped status looks globally authoritative")
        _assert(index_path.stat().st_mtime_ns == index_mtime_before, "collector modified Git index")

        target_by_path = {target.path: target for target in first.targets}
        _assert(target_by_path["src/deleted.txt"].kind == "deleted", "deletion marker missing")
        _assert(target_by_path["src/deleted.txt"].content_sha256 == "", "deleted content digest must be empty")
        _assert(target_by_path["src/new.txt"].status == "??", "untracked target status missing")
        _assert(target_by_path["src/binary.bin"].content_sha256, "binary target digest missing")
        _assert(b"changed tracked evidence" not in first.canonical_bytes, "raw text leaked into evidence")
        _assert(b"new untracked evidence" not in first.canonical_bytes, "untracked content leaked")
        _assert(b"changed evidence" not in first.canonical_bytes, "binary content leaked")

        (repo / "src" / "tracked.txt").write_text(
            "changed again after first evidence\n",
            encoding="utf-8",
        )
        changed = collect_local_change_evidence(repo, project, item)
        _assert(
            changed.change_evidence_digest != first.change_evidence_digest,
            "content change did not change evidence digest",
        )


def _test_local_change_evidence_verifier_rejects_tampering_and_scope_drift() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-change-evidence-verify-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        evidence = collect_local_change_evidence(repo, project, item)
        original_run_git = change_evidence_module._run_git_bytes

        def forbidden_git_read(*args: object, **kwargs: object) -> bytes:
            raise AssertionError("evidence verification must not read Git")

        change_evidence_module._run_git_bytes = forbidden_git_read
        try:
            _assert(
                verify_local_change_evidence(evidence, project, item) is None,
                "valid local change evidence should verify",
            )
        finally:
            change_evidence_module._run_git_bytes = original_run_git

        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, project_id="different-project"),
                project,
                item,
            ),
            "project does not match",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, item_id="different-item"),
                project,
                item,
            ),
            "item does not match",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, version="0.1C-0A"),
                project,
                item,
            ),
            "type or version is unsupported",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                evidence,
                replace(project, repo_path=str(repo.parent)),
                item,
            ),
            "declared repo path does not match",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, declared_repo_path=str(repo.parent).replace("\\", "/")),
                project,
                item,
            ),
            "declared repo path does not match",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, repo_root="."),
                project,
                item,
            ),
            "change evidence repo_root must be a local absolute path",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, repo_root=r"\\example.invalid\share\repo"),
                project,
                item,
            ),
            "change evidence repo_root must be a local absolute path",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                evidence,
                project,
                replace(item, target_files=("src/tracked.txt",)),
            ),
            "status scope does not match",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                evidence,
                replace(project, protected_paths=("known.local", "src/tracked.txt")),
                item,
            ),
            "target path is protected",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, status_scope_paths=tuple(reversed(evidence.status_scope_paths))),
                project,
                item,
            ),
            "status scope does not match",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, scoped_git_status=tuple(reversed(evidence.scoped_git_status))),
                project,
                item,
            ),
            "Git status is not canonical",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(
                    evidence,
                    targets=(
                        replace(evidence.targets[0], content_sha256="0" * 64),
                        *evidence.targets[1:],
                    ),
                ),
                project,
                item,
            ),
            "canonical manifest is inconsistent",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, canonical_bytes=evidence.canonical_bytes + b" "),
                project,
                item,
            ),
            "canonical manifest is inconsistent",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, change_evidence_digest="0" * 64),
                project,
                item,
            ),
            "digest is inconsistent",
        )
        _assert_validation_error(
            lambda: verify_local_change_evidence(
                replace(evidence, byte_size=evidence.byte_size + 1),
                project,
                item,
            ),
            "byte size is inconsistent",
        )


def _test_whole_worktree_status_evidence_is_complete_deterministic_and_read_only() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-whole-status-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        outside_content = "outside target content must not be collected\n"
        (repo / "outside.txt").write_text(outside_content, encoding="utf-8")
        index_path = repo / ".git" / "index"
        index_mtime_before = index_path.stat().st_mtime_ns

        first = collect_whole_worktree_status_evidence(repo, project, item)
        second = collect_whole_worktree_status_evidence(repo, project, item)
        _assert(first == second, "whole-worktree status evidence should be deterministic")
        _assert(first.version == "0.1C-0C-1", "whole-status evidence version is wrong")
        _assert(first.coverage == WHOLE_STATUS_COVERAGE, "whole-status coverage is wrong")
        _assert("?? outside.txt" in first.whole_git_status, "outside status was hidden")
        _assert("?? known.local" in first.whole_git_status, "known untracked status missing")
        _assert(
            " M src/tracked.txt" in first.whole_git_status,
            "tracked target status missing from whole status",
        )
        _assert(
            outside_content.encode("utf-8") not in first.canonical_bytes,
            "outside target content leaked into whole-status evidence",
        )
        _assert(index_path.stat().st_mtime_ns == index_mtime_before, "whole status modified index")

        original_run_git = change_evidence_module._run_git_bytes

        def forbidden_git_read(*args: object, **kwargs: object) -> bytes:
            raise AssertionError("whole-status verification must not read Git")

        change_evidence_module._run_git_bytes = forbidden_git_read
        try:
            _assert(
                verify_whole_worktree_status_evidence(first, project, item) is None,
                "valid whole-worktree status evidence should verify",
            )
            verify_whole_worktree_status_evidence(
                first,
                replace(project, protected_paths=("known.local", "outside.txt")),
                item,
            )
        finally:
            change_evidence_module._run_git_bytes = original_run_git

        (repo / "outside.txt").write_text("different outside content\n", encoding="utf-8")
        content_changed = collect_whole_worktree_status_evidence(repo, project, item)
        _assert(
            content_changed.status_evidence_digest == first.status_evidence_digest,
            "path/status-only evidence should not hash outside content",
        )


def _test_whole_worktree_status_evidence_rejects_tampering_and_unsafe_state() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-whole-status-verify-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        evidence = collect_whole_worktree_status_evidence(repo, project, item)

        _assert_validation_error(
            lambda: verify_whole_worktree_status_evidence(
                replace(evidence, coverage="scoped"),
                project,
                item,
            ),
            "metadata is unsupported",
        )
        _assert_validation_error(
            lambda: verify_whole_worktree_status_evidence(
                replace(evidence, whole_git_status=tuple(reversed(evidence.whole_git_status))),
                project,
                item,
            ),
            "Git status is not canonical",
        )
        _assert_validation_error(
            lambda: verify_whole_worktree_status_evidence(
                replace(evidence, canonical_bytes=evidence.canonical_bytes + b" "),
                project,
                item,
            ),
            "canonical manifest is inconsistent",
        )
        _assert_validation_error(
            lambda: verify_whole_worktree_status_evidence(
                replace(evidence, status_evidence_digest="0" * 64),
                project,
                item,
            ),
            "digest is inconsistent",
        )

        (repo / "known.local").unlink()
        _assert_validation_error(
            lambda: collect_whole_worktree_status_evidence(repo, project, item),
            "expected untracked path is missing",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-whole-status-staged-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        _run_fixture_git(repo, "add", "src/tracked.txt")
        _assert_validation_error(
            lambda: collect_whole_worktree_status_evidence(repo, project, item),
            "staged changes are not allowed in whole status",
        )


def _test_whole_worktree_status_evidence_rejects_unstable_and_excessive_state() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-whole-status-unstable-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        original_collect = change_evidence_module._collect_whole_repository_state
        call_count = 0

        def mutating_collect(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            result = original_collect(*args, **kwargs)
            call_count += 1
            if call_count == 1:
                (repo / "outside-after-first-sample.txt").write_text(
                    "changed during whole-status collection\n",
                    encoding="utf-8",
                )
            return result

        change_evidence_module._collect_whole_repository_state = mutating_collect
        try:
            _assert_validation_error(
                lambda: collect_whole_worktree_status_evidence(repo, project, item),
                "repository changed during whole-status collection",
            )
        finally:
            change_evidence_module._collect_whole_repository_state = original_collect

    with tempfile.TemporaryDirectory(prefix="hermes-whole-status-count-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        generated = repo / "generated"
        generated.mkdir()
        for index in range(129):
            (generated / f"file-{index:03d}.txt").write_text("x\n", encoding="utf-8")
        _assert_validation_error(
            lambda: collect_whole_worktree_status_evidence(repo, project, item),
            "too many evidence entries",
        )

    exact_chunks: list[bytes] = []
    exact_overflow = change_evidence_module.threading.Event()
    exact_errors: list[Exception] = []
    change_evidence_module._read_bounded_pipe(
        io.BytesIO(b"x" * MAX_GIT_OUTPUT_BYTES),
        exact_chunks,
        exact_overflow,
        exact_errors,
    )
    _assert(not exact_overflow.is_set(), "exact Git output limit should be accepted")
    _assert(not exact_errors, "exact Git output limit produced a reader error")

    overflow_chunks: list[bytes] = []
    overflow = change_evidence_module.threading.Event()
    overflow_errors: list[Exception] = []
    change_evidence_module._read_bounded_pipe(
        io.BytesIO(b"x" * (MAX_GIT_OUTPUT_BYTES + 1)),
        overflow_chunks,
        overflow,
        overflow_errors,
    )
    _assert(overflow.is_set(), "oversized Git output was not rejected")
    _assert(not overflow_errors, "oversized Git output produced a reader error")


def _test_review_evidence_bundle_is_deterministic_complete_and_purely_verifiable() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-bundle-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        outside_content = "outside content remains outside the target digest\n"
        (repo / "outside.txt").write_text(outside_content, encoding="utf-8")

        first = collect_review_evidence_bundle(repo, project, item)
        second = collect_review_evidence_bundle(repo, project, item)
        _assert(first == second, "review evidence bundle should be deterministic")
        _assert(first.version == "0.1C-0C-2", "review evidence bundle version is wrong")
        _assert(
            "?? outside.txt" in first.whole_status_evidence.whole_git_status,
            "review bundle hid an outside path",
        )
        snapshot = first.snapshot()
        _assert(
            snapshot["target_evidence"]["digest"]
            == first.target_evidence.change_evidence_digest,
            "review bundle did not bind target evidence",
        )
        _assert(
            snapshot["whole_status_evidence"]["digest"]
            == first.whole_status_evidence.status_evidence_digest,
            "review bundle did not bind whole status evidence",
        )
        _assert(
            outside_content.encode("utf-8") not in first.canonical_bytes,
            "review bundle leaked outside content",
        )

        original_run_git = change_evidence_module._run_git_bytes

        def forbidden_git_read(*args: object, **kwargs: object) -> bytes:
            raise AssertionError("review bundle verification must not read Git")

        change_evidence_module._run_git_bytes = forbidden_git_read
        try:
            _assert(
                verify_review_evidence_bundle(first, project, item) is None,
                "valid review evidence bundle should verify",
            )
        finally:
            change_evidence_module._run_git_bytes = original_run_git

        (repo / "src" / "tracked.txt").write_text(
            "target content changed after the first bundle\n",
            encoding="utf-8",
        )
        target_changed = collect_review_evidence_bundle(repo, project, item)
        _assert(
            target_changed.bundle_digest != first.bundle_digest,
            "target content change did not invalidate review bundle",
        )


def _test_review_evidence_bundle_rejects_tampering_and_collection_races() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-bundle-verify-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        bundle = collect_review_evidence_bundle(repo, project, item)

        _assert_validation_error(
            lambda: verify_review_evidence_bundle(
                replace(bundle, version="0.1C-0C-1"),
                project,
                item,
            ),
            "metadata is unsupported",
        )
        _assert_validation_error(
            lambda: verify_review_evidence_bundle(
                replace(bundle, canonical_bytes=bundle.canonical_bytes + b" "),
                project,
                item,
            ),
            "canonical manifest is inconsistent",
        )
        _assert_validation_error(
            lambda: verify_review_evidence_bundle(
                replace(bundle, bundle_digest="0" * 64),
                project,
                item,
            ),
            "bundle digest is inconsistent",
        )

        whole_without_target = replace(
            bundle.whole_status_evidence,
            whole_git_status=tuple(
                line
                for line in bundle.whole_status_evidence.whole_git_status
                if not line.endswith("src/tracked.txt")
            ),
        )
        _assert_validation_error(
            lambda: change_evidence_module._validate_target_and_whole_status_consistency(
                bundle.target_evidence,
                whole_without_target,
            ),
            "target and whole status disagree",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-review-bundle-race-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        original_collect = change_evidence_module.collect_local_change_evidence
        call_count = 0

        def mutating_target_collect(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            result = original_collect(*args, **kwargs)
            call_count += 1
            if call_count == 1:
                (repo / "src" / "tracked.txt").write_text(
                    "target changed between bundle samples\n",
                    encoding="utf-8",
                )
            return result

        change_evidence_module.collect_local_change_evidence = mutating_target_collect
        try:
            _assert_validation_error(
                lambda: collect_review_evidence_bundle(repo, project, item),
                "repository changed during review evidence collection",
            )
        finally:
            change_evidence_module.collect_local_change_evidence = original_collect


def _test_review_evidence_handoff_returns_only_verified_safe_preview() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-evidence-handoff-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        original_item = item
        bundle = collect_review_evidence_bundle(repo, project, item)

        first = build_review_evidence_handoff_decision(project, item, bundle)
        second = build_review_evidence_handoff_decision(project, item, bundle)
        _assert(first == second, "evidence handoff decision should be deterministic")
        _assert(not first.is_blocked, "safe evidence handoff should not be blocked")
        _assert(first.preview is not None, "safe evidence handoff preview is missing")
        preview = first.preview
        _assert(preview.version == "0.1C-0C-3", "handoff preview version is wrong")
        _assert(preview.observed_branch == bundle.branch, "handoff branch is wrong")
        _assert(preview.observed_head == bundle.head, "handoff HEAD is wrong")
        _assert(
            preview.observed_git_status == bundle.whole_status_evidence.whole_git_status,
            "handoff did not use complete whole status",
        )
        _assert(
            preview.change_evidence_digest == bundle.bundle_digest,
            "handoff did not use composite evidence digest",
        )
        _assert(not hasattr(preview, "scope_approved"), "preview must not carry scope approval")
        _assert(not hasattr(preview, "commit_approved"), "preview must not carry commit approval")
        _assert(item == original_item, "handoff decision mutated the queue item")

        original_run_git = change_evidence_module._run_git_bytes

        def forbidden_git_read(*args: object, **kwargs: object) -> bytes:
            raise AssertionError("handoff decision must not read Git")

        change_evidence_module._run_git_bytes = forbidden_git_read
        try:
            pure = build_review_evidence_handoff_decision(project, item, bundle)
            _assert(pure == first, "pure handoff verification changed the decision")
        finally:
            change_evidence_module._run_git_bytes = original_run_git


def _test_review_evidence_handoff_blocks_unsafe_incomplete_or_tampered_evidence() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-evidence-handoff-blocked-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        (repo / "outside.txt").write_text("unexpected\n", encoding="utf-8")
        protected_dir = repo / "protected-dir"
        protected_dir.mkdir()
        (protected_dir / "child.txt").write_text("protected\n", encoding="utf-8")
        protected_project = replace(
            project,
            protected_paths=("known.local", "protected-dir"),
        )
        bundle = collect_review_evidence_bundle(repo, protected_project, item)
        blocked = build_review_evidence_handoff_decision(
            protected_project,
            item,
            bundle,
        )
        _assert(blocked.is_blocked, "unsafe evidence handoff should block")
        _assert(blocked.preview is None, "blocked handoff must not expose a preview")
        _assert(
            "unexpected untracked path: outside.txt" in blocked.blocking_reasons,
            "unexpected path blocking reason missing",
        )
        _assert(
            "protected path is unexpectedly untracked: protected-dir/child.txt"
            in blocked.blocking_reasons,
            "protected descendant blocking reason missing",
        )

        tampered = build_review_evidence_handoff_decision(
            protected_project,
            item,
            replace(bundle, bundle_digest="0" * 64),
        )
        _assert(tampered.is_blocked, "tampered evidence handoff should block")
        _assert(tampered.preview is None, "tampered handoff must not expose a preview")
        _assert(
            tampered.blocking_reasons[0].startswith("review evidence validation failed:"),
            "tampered evidence validation reason missing",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-evidence-handoff-empty-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        _run_fixture_git(repo, "restore", "--worktree", "src/tracked.txt")
        unchanged_item = replace(item, target_files=("src/tracked.txt",))
        bundle = collect_review_evidence_bundle(repo, project, unchanged_item)
        blocked = build_review_evidence_handoff_decision(project, unchanged_item, bundle)
        _assert(blocked.is_blocked, "handoff without target changes should block")
        _assert(
            "review handoff requires observed target changes" in blocked.blocking_reasons,
            "missing target-change reason missing",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-evidence-overlap-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                replace(project, protected_paths=("protected.never",)),
                replace(item, target_files=("known.local",)),
            ),
            "target path overlaps expected untracked exclusion",
        )


def _test_review_evidence_observation_adapter_updates_only_observations() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-evidence-observation-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        stale_observations = replace(
            item,
            observed_branch="stale-branch",
            observed_head="stale-head",
            observed_git_status=("?? stale.txt",),
            scope_approved=True,
            scope_approval_digest="a" * 64,
            last_prompt_summary="keep prompt summary",
            last_result_summary="keep result summary",
        )
        bundle = collect_review_evidence_bundle(repo, project, stale_observations)
        original_item = copy.deepcopy(stale_observations)

        first = apply_review_evidence_observation(project, stale_observations, bundle)
        second = apply_review_evidence_observation(project, stale_observations, bundle)
        expected = replace(
            stale_observations,
            observed_branch=bundle.branch,
            observed_head=bundle.head,
            observed_git_status=bundle.whole_status_evidence.whole_git_status,
            change_evidence_digest=bundle.bundle_digest,
        )
        _assert(first == second, "evidence observation adapter should be deterministic")
        _assert(first == expected, "adapter changed fields outside queue observations")
        _assert(first is not stale_observations, "adapter must return a new queue item")
        _assert(stale_observations == original_item, "adapter mutated the original queue item")
        _assert(first.result_type == "review", "adapter changed the result type")
        _assert(first.scope_approved, "adapter changed scope approval")
        _assert(
            first.scope_approval_digest == "a" * 64,
            "adapter changed scope approval binding",
        )
        _assert(not first.review_passed, "adapter granted review approval")
        _assert(not first.commit_approved, "adapter granted commit approval")
        _assert(not first.review_approval_digest, "adapter created review approval binding")
        _assert(not first.commit_approval_digest, "adapter created commit approval binding")

        original_run_git = change_evidence_module._run_git_bytes

        def forbidden_git_read(*args: object, **kwargs: object) -> bytes:
            raise AssertionError("observation adapter must not read Git")

        change_evidence_module._run_git_bytes = forbidden_git_read
        try:
            pure = apply_review_evidence_observation(project, stale_observations, bundle)
            _assert(pure == first, "pure observation adapter changed its result")
        finally:
            change_evidence_module._run_git_bytes = original_run_git


def _test_review_evidence_observation_adapter_fails_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-evidence-observation-blocked-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        bundle = collect_review_evidence_bundle(repo, project, item)

        _assert_validation_error(
            lambda: apply_review_evidence_observation(
                project,
                replace(item, result_type="commit"),
                bundle,
            ),
            "requires result_type=review",
        )
        _assert_validation_error(
            lambda: apply_review_evidence_observation(
                project,
                replace(item, change_evidence_digest="b" * 64),
                bundle,
            ),
            "must not replace an existing digest",
        )
        _assert_validation_error(
            lambda: apply_review_evidence_observation(
                project,
                replace(item, review_passed=True),
                bundle,
            ),
            "requires an unreviewed item",
        )
        _assert_validation_error(
            lambda: apply_review_evidence_observation(
                project,
                replace(item, review_approval_digest="c" * 64),
                bundle,
            ),
            "requires an unreviewed item",
        )
        _assert_validation_error(
            lambda: apply_review_evidence_observation(
                project,
                replace(item, commit_approved=True),
                bundle,
            ),
            "requires an unapproved commit state",
        )
        _assert_validation_error(
            lambda: apply_review_evidence_observation(
                project,
                replace(item, commit_approval_digest="d" * 64),
                bundle,
            ),
            "requires an unapproved commit state",
        )
        _assert_validation_error(
            lambda: apply_review_evidence_observation(
                project,
                item,
                replace(bundle, bundle_digest="0" * 64),
            ),
            "evidence observation is blocked: review evidence validation failed:",
        )

        (repo / "outside.txt").write_text("unexpected\n", encoding="utf-8")
        unsafe_bundle = collect_review_evidence_bundle(repo, project, item)
        _assert_validation_error(
            lambda: apply_review_evidence_observation(project, item, unsafe_bundle),
            "evidence observation is blocked: unexpected untracked path: outside.txt",
        )


def _test_review_evidence_queue_bridge_replaces_one_item_and_evaluates() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-evidence-queue-bridge-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        implementation_item = replace(item, result_type="implementation")
        scope_binding = build_scope_approval_binding(project, implementation_item)
        review_item = replace(
            item,
            scope_approved=True,
            scope_approval_digest=scope_binding.digest,
            last_prompt_summary="preserve prompt summary",
        )
        other_item = replace(
            item,
            item_id="evidence-other",
            result_type="design",
            target_files=(),
            observed_git_status=(),
        )
        queue = PromptQueueState(
            projects=(project,),
            items=(other_item, review_item),
        )
        original_queue = copy.deepcopy(queue)
        bundle = collect_review_evidence_bundle(repo, project, review_item)

        original_evaluator = change_evidence_module.evaluate_queue_item
        evaluation_calls = 0

        def counting_evaluator(*args: object, **kwargs: object) -> object:
            nonlocal evaluation_calls
            evaluation_calls += 1
            return original_evaluator(*args, **kwargs)

        change_evidence_module.evaluate_queue_item = counting_evaluator
        try:
            first = evaluate_review_evidence_in_queue(
                queue,
                review_item.item_id,
                bundle,
            )
        finally:
            change_evidence_module.evaluate_queue_item = original_evaluator

        second = evaluate_review_evidence_in_queue(queue, review_item.item_id, bundle)
        expected_item = replace(
            review_item,
            observed_branch=bundle.branch,
            observed_head=bundle.head,
            observed_git_status=bundle.whole_status_evidence.whole_git_status,
            change_evidence_digest=bundle.bundle_digest,
        )
        _assert(first == second, "queue evidence bridge should be deterministic")
        _assert(evaluation_calls == 1, "queue evidence bridge should evaluate exactly once")
        _assert(queue == original_queue, "queue evidence bridge mutated the original queue")
        _assert(first.queue is not queue, "queue evidence bridge must return a new queue")
        _assert(first.queue.projects is queue.projects, "queue project tuple should be preserved")
        _assert(first.queue.items[0] is other_item, "non-selected queue item was replaced")
        _assert(first.queue.items[1] is first.item, "selected item is not in the new queue")
        _assert(first.item is not review_item, "selected queue item was not replaced")
        _assert(first.item == expected_item, "queue bridge changed non-observation fields")
        _assert(
            first.item.observed_branch == bundle.branch
            and first.item.observed_head == bundle.head
            and first.item.observed_git_status
            == bundle.whole_status_evidence.whole_git_status
            and first.item.change_evidence_digest == bundle.bundle_digest,
            "queue evidence bridge did not propagate exact evidence observations",
        )
        _assert(first.item.scope_approved, "queue evidence bridge changed scope approval")
        _assert(
            first.item.scope_approval_digest == scope_binding.digest,
            "queue evidence bridge changed the scope binding",
        )
        _assert(not first.evaluation.is_blocked, "valid review evaluation was blocked")
        _assert(first.evaluation.result_type == "review", "review result type changed")
        _assert(first.evaluation.next_action == "REVIEW_REQUEST", "review action is wrong")

        original_run_git = change_evidence_module._run_git_bytes

        def forbidden_git_read(*args: object, **kwargs: object) -> bytes:
            raise AssertionError("queue evidence bridge must not read Git")

        change_evidence_module._run_git_bytes = forbidden_git_read
        try:
            pure = evaluate_review_evidence_in_queue(queue, review_item.item_id, bundle)
            _assert(pure == first, "pure queue evidence bridge changed its result")
        finally:
            change_evidence_module._run_git_bytes = original_run_git


def _test_review_evidence_queue_bridge_preserves_blocking_and_fails_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-evidence-queue-blocked-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        queue = PromptQueueState(projects=(project,), items=(item,))
        bundle = collect_review_evidence_bundle(repo, project, item)

        blocked = evaluate_review_evidence_in_queue(queue, item.item_id, bundle)
        _assert(blocked.evaluation.is_blocked, "missing scope approval should remain blocked")
        _assert(
            blocked.evaluation.next_action == "BLOCKED_NEEDS_USER",
            "blocked bridge result changed next action",
        )
        _assert(
            "scope approval is required" in blocked.evaluation.blocking_reasons,
            "scope approval blocking reason is missing",
        )
        _assert(
            blocked.item.change_evidence_digest == bundle.bundle_digest,
            "blocked evaluation discarded the pure evidence snapshot",
        )

        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(queue, "missing-item", bundle),
            "unknown queue item",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(queue, projects=()),
                item.item_id,
                bundle,
            ),
            "unknown project",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(queue, items=(item, copy.deepcopy(item))),
                item.item_id,
                bundle,
            ),
            "queue item identity is ambiguous",
        )
        other_item = replace(item, item_id="other-item")
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(
                    queue,
                    items=(item, other_item, copy.deepcopy(other_item)),
                ),
                item.item_id,
                bundle,
            ),
            "queue item identities must be unique",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(queue, projects=(project, copy.deepcopy(project))),
                item.item_id,
                bundle,
            ),
            "project identity is ambiguous",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(
                    queue,
                    items=(item, replace(other_item, project_id="missing-project")),
                ),
                item.item_id,
                bundle,
            ),
            "queue item references unknown project",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(queue, " item ", bundle),
            "bounded normalized string",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(queue, version="0.1C-0C-5"),
                item.item_id,
                bundle,
            ),
            "queue type or version is unsupported",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                queue,
                item.item_id,
                replace(bundle, bundle_digest="0" * 64),
            ),
            "evidence observation is blocked: review evidence validation failed:",
        )
        mismatched_item = replace(item, item_id="different-review-item")
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(queue, items=(mismatched_item,)),
                mismatched_item.item_id,
                bundle,
            ),
            "review evidence bundle item does not match queue item",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(queue, items=(replace(item, result_type="commit"),)),
                item.item_id,
                bundle,
            ),
            "requires result_type=review",
        )
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                replace(queue, items=(replace(item, review_passed=True),)),
                item.item_id,
                bundle,
            ),
            "requires an unreviewed item",
        )

        (repo / "outside.txt").write_text("unexpected\n", encoding="utf-8")
        unsafe_bundle = collect_review_evidence_bundle(repo, project, item)
        _assert_validation_error(
            lambda: evaluate_review_evidence_in_queue(
                queue,
                item.item_id,
                unsafe_bundle,
            ),
            "evidence observation is blocked: unexpected untracked path: outside.txt",
        )


def _test_fresh_review_handoff_returns_only_exact_current_preview() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-handoff-") as temp_dir:
        repo, _, _, bundle, observation = _create_valid_review_observation_fixture(
            temp_dir
        )
        original_observation = copy.deepcopy(observation)
        original_collect = change_evidence_module.collect_review_evidence_bundle
        collection_calls = 0

        def counting_collect(*args: object, **kwargs: object) -> object:
            nonlocal collection_calls
            collection_calls += 1
            return original_collect(*args, **kwargs)

        change_evidence_module.collect_review_evidence_bundle = counting_collect
        try:
            first = build_fresh_review_handoff_decision(repo, observation)
        finally:
            change_evidence_module.collect_review_evidence_bundle = original_collect

        second = build_fresh_review_handoff_decision(repo, observation)
        _assert(first == second, "fresh review handoff should be deterministic")
        _assert(collection_calls == 1, "fresh handoff should collect exactly once")
        _assert(
            isinstance(first, FreshReviewHandoffDecision),
            "fresh handoff returned the wrong decision type",
        )
        _assert(not first.is_blocked, "unchanged fresh review handoff was blocked")
        _assert(first.preview is not None, "fresh review handoff preview is missing")
        preview = first.preview
        _assert(preview.queue is observation.queue, "fresh preview changed the queue")
        _assert(preview.item is observation.item, "fresh preview changed the item")
        _assert(
            preview.evaluation == observation.evaluation,
            "fresh preview changed the evaluation",
        )
        _assert(
            preview.fresh_bundle_digest == bundle.bundle_digest,
            "fresh preview digest is wrong",
        )
        _assert(not hasattr(preview, "session"), "fresh preview must not carry a session")
        _assert(
            observation == original_observation,
            "fresh handoff mutated the C0C-5 observation",
        )


def _test_fresh_review_handoff_blocks_before_io_when_not_actionable() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-blocked-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        bundle = collect_review_evidence_bundle(repo, project, item)
        queue = PromptQueueState(projects=(project,), items=(item,))
        blocked_observation = evaluate_review_evidence_in_queue(
            queue,
            item.item_id,
            bundle,
        )
        original_collect = change_evidence_module.collect_review_evidence_bundle

        def forbidden_collect(*args: object, **kwargs: object) -> object:
            raise AssertionError("blocked fresh handoff must not collect evidence")

        change_evidence_module.collect_review_evidence_bundle = forbidden_collect
        try:
            blocked = build_fresh_review_handoff_decision(repo, blocked_observation)
        finally:
            change_evidence_module.collect_review_evidence_bundle = original_collect

        _assert(blocked.is_blocked, "blocked queue evaluation became actionable")
        _assert(blocked.preview is None, "blocked fresh handoff exposed a preview")
        _assert(
            blocked.blocking_reasons == blocked_observation.evaluation.blocking_reasons,
            "fresh handoff changed evaluator blocking reasons",
        )


def _test_fresh_review_handoff_rejects_inconsistent_wrappers_before_io() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-wrapper-") as temp_dir:
        repo, project, _, _, observation = _create_valid_review_observation_fixture(
            temp_dir
        )
        original_collect = change_evidence_module.collect_review_evidence_bundle

        def forbidden_collect(*args: object, **kwargs: object) -> object:
            raise AssertionError("invalid fresh handoff must fail before collection")

        change_evidence_module.collect_review_evidence_bundle = forbidden_collect
        try:
            _assert_validation_error(
                lambda: build_fresh_review_handoff_decision(repo, object()),
                "observation must be QueueObservationEvaluation",
            )
            _assert_validation_error(
                lambda: build_fresh_review_handoff_decision(
                    repo,
                    replace(
                        observation,
                        item=replace(
                            observation.item,
                            last_result_summary="tampered item",
                        ),
                    ),
                ),
                "observation item does not match its queue snapshot",
            )
            _assert_validation_error(
                lambda: build_fresh_review_handoff_decision(
                    repo,
                    replace(
                        observation,
                        evaluation=replace(
                            observation.evaluation,
                            next_action="BLOCKED_NEEDS_USER",
                        ),
                    ),
                ),
                "observation evaluation does not match its queue snapshot",
            )
            _assert_validation_error(
                lambda: build_fresh_review_handoff_decision(
                    repo,
                    replace(
                        observation,
                        queue=replace(
                            observation.queue,
                            items=(
                                observation.item,
                                copy.deepcopy(observation.item),
                            ),
                        ),
                    ),
                ),
                "queue item identity is ambiguous",
            )
            _assert_validation_error(
                lambda: build_fresh_review_handoff_decision(
                    repo,
                    replace(
                        observation,
                        queue=replace(observation.queue, projects=()),
                    ),
                ),
                "unknown project",
            )

            missing_digest_item = replace(
                observation.item,
                change_evidence_digest="",
            )
            missing_digest_queue = replace(
                observation.queue,
                items=(missing_digest_item,),
            )
            missing_digest_observation = QueueObservationEvaluation(
                queue=missing_digest_queue,
                item=missing_digest_item,
                evaluation=evaluate_queue_item(
                    missing_digest_queue,
                    missing_digest_item.item_id,
                ),
            )
            missing_digest = build_fresh_review_handoff_decision(
                repo,
                missing_digest_observation,
            )
            _assert(missing_digest.is_blocked, "missing evidence digest was accepted")
            _assert(
                "change evidence digest is missing"
                in missing_digest.blocking_reasons,
                "missing evidence digest reason is absent",
            )

            commit_metadata_item = replace(
                observation.item,
                commit_approved=True,
                commit_approval_digest="f" * 64,
            )
            commit_metadata_queue = replace(
                observation.queue,
                items=(commit_metadata_item,),
            )
            commit_metadata_observation = QueueObservationEvaluation(
                queue=commit_metadata_queue,
                item=commit_metadata_item,
                evaluation=evaluate_queue_item(
                    commit_metadata_queue,
                    commit_metadata_item.item_id,
                ),
            )
            commit_metadata = build_fresh_review_handoff_decision(
                repo,
                commit_metadata_observation,
            )
            _assert(commit_metadata.is_blocked, "commit metadata was accepted")
            _assert(commit_metadata.preview is None, "commit metadata exposed a preview")

            design_item = replace(
                observation.item,
                result_type="design",
                target_files=(),
                observed_git_status=("?? known.local",),
                scope_approved=False,
                scope_approval_digest="",
                change_evidence_digest="",
            )
            design_queue = replace(observation.queue, items=(design_item,))
            design_observation = QueueObservationEvaluation(
                queue=design_queue,
                item=design_item,
                evaluation=evaluate_queue_item(design_queue, design_item.item_id),
            )
            _assert(not design_observation.evaluation.is_blocked, "design fixture is blocked")
            _assert_validation_error(
                lambda: build_fresh_review_handoff_decision(
                    repo,
                    design_observation,
                ),
                "requires an actionable review item",
            )

            review_binding = build_review_approval_binding(
                project,
                observation.item,
                scope_digest=observation.item.scope_approval_digest,
                change_evidence_digest=observation.item.change_evidence_digest,
            )
            passed_item = replace(
                observation.item,
                review_passed=True,
                review_approval_digest=review_binding.digest,
            )
            passed_queue = replace(observation.queue, items=(passed_item,))
            passed_observation = QueueObservationEvaluation(
                queue=passed_queue,
                item=passed_item,
                evaluation=evaluate_queue_item(passed_queue, passed_item.item_id),
            )
            _assert(not passed_observation.evaluation.is_blocked, "passed fixture is blocked")
            _assert_validation_error(
                lambda: build_fresh_review_handoff_decision(
                    repo,
                    passed_observation,
                ),
                "requires an unreviewed item",
            )
        finally:
            change_evidence_module.collect_review_evidence_bundle = original_collect


def _test_fresh_review_handoff_detects_stale_content_status_branch_and_head() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-content-") as temp_dir:
        repo, _, _, _, observation = _create_valid_review_observation_fixture(temp_dir)
        (repo / "src" / "tracked.txt").write_text(
            "changed after C0C-5 observation\n",
            encoding="utf-8",
        )
        stale = build_fresh_review_handoff_decision(repo, observation)
        _assert(stale.is_blocked, "stale target content was accepted")
        _assert(
            stale.blocking_reasons
            == ("fresh review evidence does not match queue observation",),
            "stale target content reason is wrong",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-status-") as temp_dir:
        repo, _, _, _, observation = _create_valid_review_observation_fixture(temp_dir)
        reordered_item = replace(
            observation.item,
            observed_git_status=tuple(reversed(observation.item.observed_git_status)),
        )
        reordered_queue = replace(observation.queue, items=(reordered_item,))
        reordered_observation = QueueObservationEvaluation(
            queue=reordered_queue,
            item=reordered_item,
            evaluation=evaluate_queue_item(reordered_queue, reordered_item.item_id),
        )
        _assert(
            not reordered_observation.evaluation.is_blocked,
            "reordered status fixture is blocked",
        )
        stale = build_fresh_review_handoff_decision(repo, reordered_observation)
        _assert(stale.is_blocked, "non-exact whole status was accepted")
        _assert(stale.preview is None, "stale whole status exposed a preview")

    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-outside-") as temp_dir:
        repo, _, _, _, observation = _create_valid_review_observation_fixture(temp_dir)
        (repo / "outside.txt").write_text("new whole-status entry\n", encoding="utf-8")
        stale = build_fresh_review_handoff_decision(repo, observation)
        _assert(stale.is_blocked, "changed whole-worktree status was accepted")
        _assert(
            stale.blocking_reasons
            == ("fresh review evidence does not match queue observation",),
            "changed whole-status reason is wrong",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-staged-") as temp_dir:
        repo, _, _, _, observation = _create_valid_review_observation_fixture(temp_dir)
        _run_fixture_git(repo, "add", "src/tracked.txt")
        blocked = build_fresh_review_handoff_decision(repo, observation)
        _assert(blocked.is_blocked, "staged state was accepted")
        _assert(
            blocked.blocking_reasons[0].startswith(
                "fresh review evidence validation failed:"
            ),
            "staged-state validation reason is missing",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-branch-") as temp_dir:
        repo, _, _, _, observation = _create_valid_review_observation_fixture(temp_dir)
        _run_fixture_git(repo, "switch", "-c", "other")
        blocked = build_fresh_review_handoff_decision(repo, observation)
        _assert(blocked.is_blocked, "changed branch was accepted")
        _assert(
            blocked.blocking_reasons[0].startswith(
                "fresh review evidence validation failed:"
            ),
            "changed branch validation reason is missing",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-head-") as temp_dir:
        repo, _, _, _, observation = _create_valid_review_observation_fixture(temp_dir)
        _run_fixture_git(repo, "commit", "--allow-empty", "-m", "head changed")
        blocked = build_fresh_review_handoff_decision(repo, observation)
        _assert(blocked.is_blocked, "changed HEAD was accepted")
        _assert(
            blocked.blocking_reasons[0].startswith(
                "fresh review evidence validation failed:"
            ),
            "changed HEAD validation reason is missing",
        )


def _test_fresh_review_handoff_verifies_collector_output() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-verify-") as temp_dir:
        repo, _, _, bundle, observation = _create_valid_review_observation_fixture(
            temp_dir
        )
        original_collect = change_evidence_module.collect_review_evidence_bundle

        def tampered_collect(*args: object, **kwargs: object) -> object:
            return replace(bundle, bundle_digest="0" * 64)

        change_evidence_module.collect_review_evidence_bundle = tampered_collect
        try:
            blocked = build_fresh_review_handoff_decision(repo, observation)
        finally:
            change_evidence_module.collect_review_evidence_bundle = original_collect

        _assert(blocked.is_blocked, "tampered fresh collector output was accepted")
        _assert(blocked.preview is None, "tampered collector output exposed a preview")
        _assert(
            blocked.blocking_reasons[0].startswith(
                "fresh review evidence validation failed:"
            ),
            "tampered collector validation reason is missing",
        )


def _test_fresh_review_session_adapter_is_review_only_and_fail_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-fresh-review-session-") as temp_dir:
        repo, project, _, _, observation = _create_valid_review_observation_fixture(
            temp_dir
        )
        decision = build_fresh_review_handoff_decision(repo, observation)
        _assert(decision.preview is not None, "fresh session fixture has no preview")
        preview = decision.preview
        original_preview = copy.deepcopy(preview)
        original_builder = change_evidence_module.build_hermes_session
        builder_calls = 0

        def counting_builder(*args: object, **kwargs: object) -> object:
            nonlocal builder_calls
            builder_calls += 1
            return original_builder(*args, **kwargs)

        change_evidence_module.build_hermes_session = counting_builder
        try:
            first = build_review_session_from_fresh_preview(preview)
        finally:
            change_evidence_module.build_hermes_session = original_builder

        second = build_review_session_from_fresh_preview(preview)
        _assert(first == second, "fresh review session should be deterministic")
        _assert(builder_calls == 1, "fresh review session should build exactly once")
        _assert(preview == original_preview, "session adapter mutated the fresh preview")
        _assert(first.repo == project.repo_path, "review session repository is wrong")
        _assert(first.branch == project.expected_branch, "review session branch is wrong")
        _assert(first.head == project.expected_head, "review session HEAD is wrong")
        _assert(
            first.files_touched == preview.evaluation.observed_changed_files,
            "review session changed observed files",
        )
        _assert(first.target_files == preview.item.target_files, "review targets changed")
        _assert(first.next_action == "REVIEW_REQUEST", "review session action is wrong")
        _assert(not first.blocked_by, "review session unexpectedly contains blockers")
        _assert(not first.commit_allowed, "review session allowed commit")
        _assert(not first.push_allowed, "review session allowed push")
        _assert(first.human_approval_required, "review session removed human approval")
        _assert(
            not first.human_approval_granted,
            "review session granted human approval",
        )
        _assert(not first.commit_message, "review session exposed a commit message")

        original_run_git = change_evidence_module._run_git_bytes

        def forbidden_git_read(*args: object, **kwargs: object) -> bytes:
            raise AssertionError("session adapter must not read Git")

        change_evidence_module._run_git_bytes = forbidden_git_read
        try:
            pure = build_review_session_from_fresh_preview(preview)
            _assert(pure == first, "pure review session adapter changed its result")
        finally:
            change_evidence_module._run_git_bytes = original_run_git

        def forbidden_builder(*args: object, **kwargs: object) -> object:
            raise AssertionError("invalid preview must fail before session construction")

        change_evidence_module.build_hermes_session = forbidden_builder
        try:
            _assert_validation_error(
                lambda: build_review_session_from_fresh_preview(object()),
                "preview must be FreshReviewHandoffPreview",
            )
            _assert_validation_error(
                lambda: build_review_session_from_fresh_preview(
                    replace(
                        preview,
                        item=replace(
                            preview.item,
                            last_result_summary="tampered preview item",
                        ),
                    ),
                ),
                "observation item does not match its queue snapshot",
            )
            _assert_validation_error(
                lambda: build_review_session_from_fresh_preview(
                    replace(
                        preview,
                        evaluation=replace(
                            preview.evaluation,
                            next_action="BLOCKED_NEEDS_USER",
                        ),
                    ),
                ),
                "observation evaluation does not match its queue snapshot",
            )
            _assert_validation_error(
                lambda: build_review_session_from_fresh_preview(
                    replace(preview, fresh_bundle_digest="0" * 64),
                ),
                "fresh preview digest does not match its queue item",
            )

            commit_message_item = replace(
                preview.item,
                commit_message="must not reach review session",
            )
            commit_message_queue = replace(
                preview.queue,
                items=(commit_message_item,),
            )
            commit_message_preview = replace(
                preview,
                queue=commit_message_queue,
                item=commit_message_item,
                evaluation=evaluate_queue_item(
                    commit_message_queue,
                    commit_message_item.item_id,
                ),
            )
            _assert_validation_error(
                lambda: build_review_session_from_fresh_preview(
                    commit_message_preview,
                ),
                "contains commit-stage metadata",
            )

            blocked_item = replace(
                preview.item,
                scope_approved=False,
                scope_approval_digest="",
            )
            blocked_queue = replace(preview.queue, items=(blocked_item,))
            blocked_preview = replace(
                preview,
                queue=blocked_queue,
                item=blocked_item,
                evaluation=evaluate_queue_item(blocked_queue, blocked_item.item_id),
            )
            _assert_validation_error(
                lambda: build_review_session_from_fresh_preview(blocked_preview),
                "requires an actionable review item",
            )
        finally:
            change_evidence_module.build_hermes_session = original_builder

        valid_session = original_builder(preview.queue, preview.item.item_id)

        def unsafe_builder(*args: object, **kwargs: object) -> object:
            return replace(valid_session, push_allowed=True)

        change_evidence_module.build_hermes_session = unsafe_builder
        try:
            _assert_validation_error(
                lambda: build_review_session_from_fresh_preview(preview),
                "violates review-only safety conditions",
            )
        finally:
            change_evidence_module.build_hermes_session = original_builder


def _test_local_change_evidence_rejects_scope_root_stage_and_size_violations() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-change-evidence-safety-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        _assert_validation_error(
            lambda: collect_local_change_evidence(repo.parent, project, item),
            "trusted repo root does not match project repo_path",
        )
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                r"\\example.invalid\share\repo",
                project,
                item,
            ),
            "trusted repo root must be a local absolute path",
        )
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                project,
                replace(item, target_files=("../outside.txt",)),
            ),
            "repository-relative",
        )
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                project,
                replace(item, target_files=(".git/config",)),
            ),
            "repository-relative",
        )
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                project,
                replace(item, target_files=(":(glob)**",)),
            ),
            "repository-relative",
        )
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                project,
                replace(item, target_files=("known.local",)),
            ),
            "target path is protected",
        )
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                replace(project, protected_paths=("src",)),
                item,
            ),
            "target path is protected",
        )
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                project,
                replace(item, result_type="implementation"),
            ),
            "result_type=review or commit",
        )
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                project,
                replace(item, target_files=("src",)),
            ),
            "target path must be a file",
        )

        large_path = repo / "src" / "large.bin"
        large_path.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
        _assert_validation_error(
            lambda: collect_local_change_evidence(
                repo,
                project,
                replace(item, target_files=("src/large.bin",)),
            ),
            "target file exceeds evidence size limit",
        )

        _run_fixture_git(repo, "add", "src/tracked.txt")
        _assert_validation_error(
            lambda: collect_local_change_evidence(repo, project, item),
            "staged target changes are not allowed",
        )


def _test_local_change_evidence_rejects_reparse_and_unstable_reads() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-change-evidence-reparse-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        original_reparse_check = change_evidence_module._is_reparse_or_symlink

        def simulated_reparse(path: Path) -> bool:
            return path.name == "tracked.txt" or original_reparse_check(path)

        change_evidence_module._is_reparse_or_symlink = simulated_reparse
        try:
            _assert_validation_error(
                lambda: collect_local_change_evidence(repo, project, item),
                "crosses a symlink or reparse point",
            )
        finally:
            change_evidence_module._is_reparse_or_symlink = original_reparse_check

    with tempfile.TemporaryDirectory(prefix="hermes-change-evidence-unstable-") as temp_dir:
        repo, project, item = _create_change_evidence_fixture(temp_dir)
        original_collect = change_evidence_module._collect_target_manifest
        call_count = 0

        def mutating_collect(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            result = original_collect(*args, **kwargs)
            call_count += 1
            if call_count == 1:
                (repo / "src" / "tracked.txt").write_text(
                    "changed during evidence collection\n",
                    encoding="utf-8",
                )
            return result

        change_evidence_module._collect_target_manifest = mutating_collect
        try:
            _assert_validation_error(
                lambda: collect_local_change_evidence(repo, project, item),
                "repository changed during evidence collection",
            )
        finally:
            change_evidence_module._collect_target_manifest = original_collect


def _test_local_change_evidence_status_parser_is_bounded_and_fail_closed() -> None:
    rename_status = b"R  src/new-name.txt\x00src/old-name.txt\x00"
    parsed = change_evidence_module._parse_porcelain_status(rename_status)
    _assert(parsed == (("R ", "src/new-name.txt"),), "rename status parsing is not deterministic")

    too_many = b"".join(
        f"?? generated/file-{index:03d}.txt".encode("utf-8") + b"\x00"
        for index in range(129)
    )
    _assert_validation_error(
        lambda: change_evidence_module._parse_porcelain_status(too_many),
        "too many evidence entries",
    )
    _assert_validation_error(
        lambda: change_evidence_module._parse_porcelain_status(b"?? ../escape.txt\x00"),
        "repository-relative",
    )


def _review_record_candidate_payload() -> dict[str, object]:
    return {
        "project_id": "jarvis-core",
        "git_snapshot": {
            "branch": "main",
            "head": "a" * 40,
            "status": [
                "?? jarvis.bat",
                " M docs/master-plan.md",
                " M apps/hermes-manager-pilot/README.md",
            ],
        },
        "current_goal": "Make Hermes review handoffs safely reusable.",
        "active_task": "Define a transport-neutral durable Review record.",
        "target_files": [
            "docs/master-plan.md",
            "apps/hermes-manager-pilot/README.md",
        ],
        "validation_commands": [
            "python -B apps/hermes-manager-pilot/run_smoke_tests.py",
            "git diff --check",
        ],
        "last_codex_prompt_summary": "Implement one bounded Review contract.",
        "result_summary": "Implemented the immutable contract and deterministic tests.",
        "privacy_reviewed": True,
    }


def _test_review_record_contract_is_immutable_canonical_and_authority_free() -> None:
    payload = _review_record_candidate_payload()
    candidate = normalize_review_record_candidate(payload)
    _assert(
        candidate.target_files
        == (
            "apps/hermes-manager-pilot/README.md",
            "docs/master-plan.md",
        ),
        "Review target scope is not canonical",
    )
    _assert(
        candidate.git_snapshot.status
        == (
            " M apps/hermes-manager-pilot/README.md",
            " M docs/master-plan.md",
            "?? jarvis.bat",
        ),
        "Review Git snapshot is not canonical",
    )
    _assert(isinstance(candidate.target_files, tuple), "Review targets must be immutable")
    _assert(isinstance(candidate.git_snapshot.status, tuple), "Review status must be immutable")

    record = create_review_record(
        candidate,
        id_generator=lambda: "review_0123456789abcdef01234567",
        clock=lambda: datetime(2026, 7, 22, 3, 4, 5, 999999, tzinfo=timezone.utc),
    )
    _assert(record.contract_type == REVIEW_RECORD_CONTRACT_TYPE, "Review contract type mismatch")
    _assert(record.version == REVIEW_RECORD_VERSION, "Review contract version mismatch")
    _assert(record.review_id == "review_0123456789abcdef01234567", "Review ID mismatch")
    _assert(record.created_at == "2026-07-22T03:04:05Z", "Review timestamp is not canonical")
    _assert(
        record.authority_boundary == REVIEW_RECORD_AUTHORITY_BOUNDARY,
        "Review authority boundary mismatch",
    )
    _assert(record.read_only is True, "Review record must be read-only")
    _assert(record.review_passed is False, "Review record granted review authority")
    _assert(record.commit_approved is False, "Review record granted commit authority")
    _assert(record.push_allowed is False, "Review record granted push authority")

    try:
        record.active_task = "mutated"  # type: ignore[misc]
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("ReviewRecord must be immutable")

    first = serialize_review_record(record)
    second = serialize_review_record(record)
    _assert(first == second, "Review record serialization is not stable")
    _assert(
        review_record_digest(record) == review_record_digest(parse_review_record_json(first)),
        "Review record digest is not stable across canonical round-trip",
    )
    _assert(len(review_record_digest(record)) == 64, "Review record digest is not SHA-256")
    _assert(parse_review_record_json(first) == record, "Review record JSON did not round-trip")
    transport = review_record_to_dict(record)
    transport["target_files"].append("docs/added-after-copy.md")
    transport["git_snapshot"]["status"].append("?? docs/added-after-copy.md")
    _assert(
        "docs/added-after-copy.md" not in record.target_files,
        "transport mapping mutated Review target scope",
    )
    _assert(
        "?? docs/added-after-copy.md" not in record.git_snapshot.status,
        "transport mapping mutated Review Git snapshot",
    )


def _test_review_record_contract_fails_closed_on_unsafe_input() -> None:
    payload = _review_record_candidate_payload()

    directory_scope = copy.deepcopy(payload)
    directory_scope["target_files"] = ["apps/hermes-manager-pilot/", "docs/master-plan.md"]
    directory_candidate = normalize_review_record_candidate(directory_scope)
    _assert(
        "apps/hermes-manager-pilot/" in directory_candidate.target_files,
        "Review target normalization rejected a bounded directory scope",
    )

    unknown = copy.deepcopy(payload)
    unknown["raw_codex_result"] = "must not be stored"
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(unknown),
        "unknown fields",
    )
    no_privacy = {**payload, "privacy_reviewed": False}
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(no_privacy),
        "privacy_reviewed must be true",
    )
    wrong_project = {**payload, "project_id": "other-repo"}
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(wrong_project),
        "project_id must be jarvis-core",
    )
    unsafe_target = copy.deepcopy(payload)
    unsafe_target["target_files"] = ["../outside.md"]
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(unsafe_target),
        "safe repository-relative path",
    )
    protected_target = copy.deepcopy(payload)
    protected_target["target_files"] = ["jarvis.bat"]
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(protected_target),
        "must not be a Review target",
    )
    duplicate_target = copy.deepcopy(payload)
    duplicate_target["target_files"] = [
        "docs/master-plan.md",
        "DOCS/master-plan.md",
    ]
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(duplicate_target),
        "duplicate values",
    )
    missing_protected = copy.deepcopy(payload)
    missing_protected["git_snapshot"]["status"] = [
        " M docs/master-plan.md",
        " M apps/hermes-manager-pilot/README.md",
    ]
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(missing_protected),
        "jarvis.bat must remain untracked",
    )
    staged = copy.deepcopy(payload)
    staged["git_snapshot"]["status"][1] = "M  docs/master-plan.md"
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(staged),
        "must not contain staged changes",
    )
    outside_scope = copy.deepcopy(payload)
    outside_scope["git_snapshot"]["status"].append(" M docs/unexpected.md")
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(outside_scope),
        "outside target_files",
    )
    contradictory_status = copy.deepcopy(payload)
    contradictory_status["git_snapshot"]["status"].append("?? docs/master-plan.md")
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(contradictory_status),
        "status paths contains duplicate values",
    )
    oversized = {**payload, "result_summary": "x" * 1201}
    _assert_review_record_error(
        lambda: normalize_review_record_candidate(oversized),
        "result_summary is too long",
    )

    candidate = normalize_review_record_candidate(payload)
    malformed_candidate = ReviewRecordCandidate(
        project_id=candidate.project_id,
        git_snapshot="not-a-snapshot",  # type: ignore[arg-type]
        current_goal=candidate.current_goal,
        active_task=candidate.active_task,
        target_files=candidate.target_files,
        validation_commands=candidate.validation_commands,
        last_codex_prompt_summary=candidate.last_codex_prompt_summary,
        result_summary=candidate.result_summary,
        privacy_reviewed=True,
    )
    _assert_review_record_error(
        lambda: create_review_record(malformed_candidate),
        "ReviewGitSnapshot must be an immutable contract",
    )
    _assert_review_record_error(
        lambda: create_review_record(
            candidate,
            id_generator=lambda: "review_from_user_text",
            clock=lambda: datetime.now(timezone.utc),
        ),
        "generated review_id is invalid",
    )
    _assert_review_record_error(
        lambda: create_review_record(
            candidate,
            id_generator=lambda: "review_0123456789abcdef01234567",
            clock=lambda: datetime(2026, 7, 22, 3, 4, 5),
        ),
        "timezone-aware",
    )

    record = create_review_record(
        candidate,
        id_generator=lambda: "review_0123456789abcdef01234567",
        clock=lambda: datetime(2026, 7, 22, 3, 4, 5, tzinfo=timezone.utc),
    )
    for field, unsafe_value in (
        ("read_only", False),
        ("review_passed", True),
        ("commit_approved", True),
        ("push_allowed", True),
    ):
        unsafe_record = review_record_to_dict(record)
        unsafe_record[field] = unsafe_value
        _assert_review_record_error(
            lambda value=unsafe_record: normalize_review_record(value),
            f"{field} must be",
        )
    duplicate_json = serialize_review_record(record).replace(
        '"version":"0.1A"',
        '"version":"0.1A","version":"0.1A"',
        1,
    )
    _assert_review_record_error(
        lambda: parse_review_record_json(duplicate_json),
        "duplicate key",
    )


def _test_review_record_freshness_is_exact_and_fail_closed() -> None:
    candidate = normalize_review_record_candidate(_review_record_candidate_payload())
    record = create_review_record(
        candidate,
        id_generator=lambda: "review_0123456789abcdef01234567",
        clock=lambda: datetime(2026, 7, 22, 3, 4, 5, tzinfo=timezone.utc),
    )
    same_snapshot = {
        "branch": record.git_snapshot.branch,
        "head": record.git_snapshot.head,
        "status": list(reversed(record.git_snapshot.status)),
    }
    fresh = evaluate_review_record_freshness(record, same_snapshot)
    _assert(fresh.matches is True, "equivalent current Review snapshot was blocked")
    _assert(fresh.blocking_reasons == (), "fresh Review snapshot has blocking reasons")

    changed = copy.deepcopy(same_snapshot)
    changed["branch"] = "other-branch"
    changed["head"] = "b" * 40
    changed["status"] = [
        "M  apps/hermes-manager-pilot/README.md",
        " M docs/master-plan.md",
        " M docs/unexpected.md",
    ]
    blocked = evaluate_review_record_freshness(record, changed)
    _assert(blocked.matches is False, "stale or unsafe Review snapshot was accepted")
    _assert(
        blocked.blocking_reasons
        == (
            "current branch differs from the captured Review branch",
            "current HEAD differs from the captured Review HEAD",
            "current working tree differs from the captured Review snapshot",
            "jarvis.bat is not protected and untracked",
            "current working tree contains staged changes",
            "current working tree contains changes outside the Review target scope",
        ),
        "Review freshness reasons are incomplete or unstable",
    )


def _test_review_record_core_has_no_io_route_or_clipboard_dependency() -> None:
    source = Path(review_record_module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "from pathlib",
        "import os",
        "subprocess",
        "requests",
        "urlopen",
        ".write_text(",
        ".write_bytes(",
        "navigator.clipboard",
        "HANDOFF_ENDPOINT",
    ):
        _assert(forbidden not in source, f"Review record core contains forbidden dependency: {forbidden}")


def _review_store_record(index: int) -> ReviewRecord:
    candidate = normalize_review_record_candidate(_review_record_candidate_payload())
    return create_review_record(
        candidate,
        id_generator=lambda: f"review_{index:024x}",
        clock=lambda: datetime(2026, 7, 22, 3, 4, index, tzinfo=timezone.utc),
    )


def _review_store_fixture(temp_dir: str) -> tuple[Path, Path, dict[str, str]]:
    root = Path(temp_dir)
    repo = root / "repo"
    repo.mkdir()
    state_root = root / "local-state"
    return repo, state_root, {REVIEW_STORE_STATE_DIR_ENV: str(state_root)}


def _test_review_store_path_policy_is_external_and_write_free() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-store-paths-") as temp_dir:
        root = Path(temp_dir)
        repo = root / "repo"
        repo.mkdir()
        local_appdata = root / "local-appdata"
        windows_paths = resolve_review_store_paths(
            env={"LOCALAPPDATA": str(local_appdata)},
            repo_root=repo,
            is_windows=True,
        )
        _assert(
            windows_paths.review_dir
            == (local_appdata / "Jarvis-Core" / "hermes-manager" / "reviews" / "v1").resolve(),
            "Windows Review store path mismatch",
        )
        _assert(windows_paths.source == "default_windows_localappdata", "Windows path source mismatch")
        _assert(not windows_paths.review_dir.exists(), "path resolution created the Review store")

        home = root / "home"
        home_paths = resolve_review_store_paths(
            env={},
            home_dir=home,
            repo_root=repo,
            is_windows=False,
        )
        _assert(
            home_paths.review_dir
            == (home / ".jarvis-core" / "hermes-manager" / "reviews" / "v1").resolve(),
            "home Review store path mismatch",
        )
        _assert(not home_paths.review_dir.exists(), "home path resolution created state")

        _assert_review_store_error(
            lambda: resolve_review_store_paths(
                env={REVIEW_STORE_STATE_DIR_ENV: "relative-state"},
                repo_root=repo,
            ),
            "local_state_dir_must_be_absolute",
        )
        _assert_review_store_error(
            lambda: resolve_review_store_paths(
                env={REVIEW_STORE_STATE_DIR_ENV: str(repo / ".jarvis-local")},
                repo_root=repo,
            ),
            "local_state_dir_inside_repo",
        )

        state_root = root / "simulated-reparse-state"
        original_check = review_store_module._existing_path_chain_has_reparse_point
        review_store_module._existing_path_chain_has_reparse_point = lambda _path: True
        try:
            _assert_review_store_error(
                lambda: list_review_records(
                    env={REVIEW_STORE_STATE_DIR_ENV: str(state_root)},
                    repo_root=repo,
                ),
                "review_store_path_not_safe",
            )
        finally:
            review_store_module._existing_path_chain_has_reparse_point = original_check


def _test_review_store_append_read_and_bounded_list() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-store-roundtrip-") as temp_dir:
        repo, state_root, env = _review_store_fixture(temp_dir)
        empty = list_review_records(env=env, repo_root=repo)
        _assert(empty.records == (), "missing Review store was not listed as empty")
        _assert(empty.count == 0, "empty Review store count mismatch")
        _assert(empty.retention_policy == REVIEW_STORE_RETENTION_POLICY, "retention policy mismatch")
        _assert(not state_root.exists(), "empty list created local state")

        first = _review_store_record(1)
        second = _review_store_record(2)
        first_receipt = write_review_record(first, env=env, repo_root=repo)
        second_receipt = write_review_record(second, env=env, repo_root=repo)
        _assert(first_receipt.stored is True, "first Review record was not stored")
        _assert(second_receipt.review_id == second.review_id, "second Review receipt ID mismatch")
        _assert(first_receipt.retention_policy == "manual_delete_only", "write retention mismatch")
        _assert(not hasattr(first_receipt, "path"), "write receipt exposed a local path")

        paths = resolve_review_store_paths(env=env, repo_root=repo)
        stored_files = sorted(paths.review_dir.glob("*.json"))
        _assert(len(stored_files) == 2, "Review store did not contain exactly two JSON files")
        _assert(not list(paths.review_dir.glob("*.tmp")), "Review store left a temporary file")
        if os.name != "nt":
            for stored_file in stored_files:
                _assert(
                    stat.S_IMODE(stored_file.stat().st_mode) == 0o600,
                    "Review record file permissions are not private",
                )

        _assert(read_review_record(first.review_id, env=env, repo_root=repo) == first, "first Review read mismatch")
        listing = list_review_records(env=env, repo_root=repo)
        _assert(listing.count == 2, "Review listing count mismatch")
        _assert(
            tuple(summary.review_id for summary in listing.records)
            == (second.review_id, first.review_id),
            "Review listing order is not deterministic newest-first",
        )
        _assert(listing.records[0].active_task == second.active_task, "Review listing task mismatch")
        _assert(listing.records[0].target_count == len(second.target_files), "Review target count mismatch")
        _assert(not hasattr(listing.records[0], "result_summary"), "Review listing exposed result text")
        _assert(not hasattr(listing.records[0], "file_path"), "Review listing exposed a file path")

        before_collision = (paths.review_dir / f"{first.review_id}.json").read_bytes()
        _assert_review_store_error(
            lambda: write_review_record(first, env=env, repo_root=repo),
            "review_record_exists",
        )
        _assert(
            (paths.review_dir / f"{first.review_id}.json").read_bytes() == before_collision,
            "Review collision overwrote the existing record",
        )
        _assert_review_store_error(
            lambda: read_review_record("../escape", env=env, repo_root=repo),
            "review_id_invalid",
        )
        _assert_review_store_error(
            lambda: read_review_record("review_ffffffffffffffffffffffff", env=env, repo_root=repo),
            "review_record_not_found",
        )


def _test_review_store_write_failure_and_recovery_states_fail_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-store-failure-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        record = _review_store_record(3)

        def fail_publish(_temp: Path, _final: Path) -> None:
            raise OSError("simulated publish failure")

        _assert_review_store_error(
            lambda: write_review_record(
                record,
                env=env,
                repo_root=repo,
                publisher=fail_publish,
                temp_token_generator=lambda: "a" * 32,
            ),
            "review_record_write_failed",
        )
        paths = resolve_review_store_paths(env=env, repo_root=repo)
        _assert(not list(paths.review_dir.iterdir()), "failed Review write left an artifact")
        _assert_review_store_error(
            lambda: write_review_record(
                record,
                env=env,
                repo_root=repo,
                temp_token_generator=lambda: "unsafe-token",
            ),
            "review_record_write_failed",
        )
        _assert(not list(paths.review_dir.iterdir()), "invalid token write left an artifact")

    with tempfile.TemporaryDirectory(prefix="hermes-review-store-uncertain-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        record = _review_store_record(14)
        original_reader = review_store_module._read_record_file

        def fail_post_publish(path: Path, *, expected_review_id: str) -> ReviewRecord:
            if path.name == f"{record.review_id}.json":
                raise ReviewStoreError("review_record_read_failed")
            return original_reader(path, expected_review_id=expected_review_id)

        review_store_module._read_record_file = fail_post_publish
        try:
            _assert_review_store_error(
                lambda: write_review_record(record, env=env, repo_root=repo),
                "review_record_write_outcome_uncertain",
            )
        finally:
            review_store_module._read_record_file = original_reader
        paths = resolve_review_store_paths(env=env, repo_root=repo)
        _assert(
            (paths.review_dir / f"{record.review_id}.json").exists(),
            "uncertain post-publish Save did not preserve exact-ID recovery evidence",
        )
        _assert(
            read_review_record(record.review_id, env=env, repo_root=repo) == record,
            "exact-ID recovery could not resolve uncertain post-publish Save",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-review-store-recovery-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        first = _review_store_record(4)
        second = _review_store_record(5)
        write_review_record(first, env=env, repo_root=repo)
        paths = resolve_review_store_paths(env=env, repo_root=repo)
        orphan = paths.review_dir / f".{first.review_id}.{'b' * 32}.tmp"
        orphan.write_bytes(b"incomplete")
        _assert_review_store_error(
            lambda: list_review_records(env=env, repo_root=repo),
            "review_store_recovery_required",
        )
        _assert_review_store_error(
            lambda: write_review_record(second, env=env, repo_root=repo),
            "review_store_recovery_required",
        )
        _assert(
            read_review_record(first.review_id, env=env, repo_root=repo) == first,
            "exact read was incorrectly blocked by an unrelated orphan temp file",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-review-store-foreign-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        record = _review_store_record(6)
        write_review_record(record, env=env, repo_root=repo)
        paths = resolve_review_store_paths(env=env, repo_root=repo)
        (paths.review_dir / "unexpected.txt").write_text("foreign", encoding="utf-8")
        _assert_review_store_error(
            lambda: list_review_records(env=env, repo_root=repo),
            "review_store_unexpected_entry",
        )


def _test_review_store_rejects_corruption_id_mismatch_and_capacity_overflow() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-store-corrupt-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        record = _review_store_record(7)
        write_review_record(record, env=env, repo_root=repo)
        paths = resolve_review_store_paths(env=env, repo_root=repo)
        record_file = paths.review_dir / f"{record.review_id}.json"
        record_file.write_bytes(b"{not canonical json}\n")
        _assert_review_store_error(
            lambda: read_review_record(record.review_id, env=env, repo_root=repo),
            "review_record_corrupt",
        )
        _assert_review_store_error(
            lambda: list_review_records(env=env, repo_root=repo),
            "review_record_corrupt",
        )
        _assert_review_store_error(
            lambda: write_review_record(_review_store_record(13), env=env, repo_root=repo),
            "review_record_corrupt",
        )
        record_file.write_bytes(b"\xff\xfe\n")
        _assert_review_store_error(
            lambda: read_review_record(record.review_id, env=env, repo_root=repo),
            "review_record_corrupt",
        )
        record_file.write_bytes(
            f"{serialize_review_record(record)} \n".encode("utf-8")
        )
        _assert_review_store_error(
            lambda: read_review_record(record.review_id, env=env, repo_root=repo),
            "review_record_corrupt",
        )
        record_file.write_bytes(b"x" * (review_store_module.MAX_STORED_BYTES + 1))
        _assert_review_store_error(
            lambda: read_review_record(record.review_id, env=env, repo_root=repo),
            "review_record_corrupt",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-review-store-id-mismatch-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        first = _review_store_record(8)
        second = _review_store_record(9)
        write_review_record(first, env=env, repo_root=repo)
        paths = resolve_review_store_paths(env=env, repo_root=repo)
        first_file = paths.review_dir / f"{first.review_id}.json"
        mismatched_file = paths.review_dir / f"{second.review_id}.json"
        mismatched_file.write_bytes(first_file.read_bytes())
        _assert_review_store_error(
            lambda: read_review_record(second.review_id, env=env, repo_root=repo),
            "review_record_corrupt",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-review-store-capacity-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        original_capacity = review_store_module.MAX_RECORDS
        review_store_module.MAX_RECORDS = 2
        try:
            write_review_record(_review_store_record(10), env=env, repo_root=repo)
            write_review_record(_review_store_record(11), env=env, repo_root=repo)
            listing = list_review_records(env=env, repo_root=repo)
            _assert(listing.capacity == 2 and listing.count == 2, "bounded capacity metadata mismatch")
            _assert_review_store_error(
                lambda: write_review_record(_review_store_record(12), env=env, repo_root=repo),
                "review_store_capacity_reached",
            )
        finally:
            review_store_module.MAX_RECORDS = original_capacity
        original_entry_limit = review_store_module.MAX_DIRECTORY_ENTRIES
        review_store_module.MAX_DIRECTORY_ENTRIES = 1
        try:
            _assert_review_store_error(
                lambda: list_review_records(env=env, repo_root=repo),
                "review_store_too_many_entries",
            )
        finally:
            review_store_module.MAX_DIRECTORY_ENTRIES = original_entry_limit


def _test_review_store_exact_delete_is_digest_bound_and_single_record_only() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-store-delete-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        first = _review_store_record(20)
        second = _review_store_record(21)
        write_review_record(first, env=env, repo_root=repo)
        write_review_record(second, env=env, repo_root=repo)

        _assert_review_store_error(
            lambda: delete_review_record(
                first.review_id,
                "0" * 64,
                env=env,
                repo_root=repo,
            ),
            "review_delete_target_changed",
        )
        _assert(read_review_record(first.review_id, env=env, repo_root=repo) == first, "digest mismatch deleted a Review")
        receipt = delete_review_record(
            first.review_id,
            review_record_digest(first),
            env=env,
            repo_root=repo,
        )
        _assert(receipt.deleted is True, "exact Review deletion did not report success")
        _assert(receipt.review_id == first.review_id, "delete receipt Review ID mismatch")
        _assert(not hasattr(receipt, "path"), "delete receipt exposed a local path")
        _assert_review_store_error(
            lambda: read_review_record(first.review_id, env=env, repo_root=repo),
            "review_record_not_found",
        )
        _assert(read_review_record(second.review_id, env=env, repo_root=repo) == second, "exact deletion changed another Review")

        paths = resolve_review_store_paths(env=env, repo_root=repo)
        second_file = paths.review_dir / f"{second.review_id}.json"
        second_file.write_bytes(b"{corrupt}\n")
        _assert_review_store_error(
            lambda: delete_review_record(
                second.review_id,
                review_record_digest(second),
                env=env,
                repo_root=repo,
            ),
            "review_record_corrupt",
        )
        _assert(second_file.exists(), "normal exact delete removed a corrupt Review")


def _review_lifecycle_session(repo: Path) -> dict[str, object]:
    payload = _sample_payload()
    payload.update(
        {
            "repo": str(repo),
            "branch": "main",
            "head": "a" * 40,
            "working_tree_status": " M docs/master-plan.md\n M apps/hermes-manager-pilot/README.md\n?? jarvis.bat",
            "current_goal": "Make local Review history safely reusable.",
            "active_task": "Complete one local Save/Reopen/Delete Review lifecycle.",
            "last_codex_prompt": "Implement the approved bounded lifecycle.",
            "last_codex_result_summary": "Implemented the bounded lifecycle.",
            "validation_commands": [
                "python -B apps/hermes-manager-pilot/run_smoke_tests.py",
                "git diff --check",
            ],
            "files_touched": [
                "apps/hermes-manager-pilot/README.md",
                "docs/master-plan.md",
            ],
            "target_files": [
                "apps/hermes-manager-pilot/README.md",
                "docs/master-plan.md",
            ],
            "protected_paths": ["jarvis.bat"],
            "commit_allowed": False,
            "push_allowed": False,
            "human_approval_required": True,
            "human_approval_granted": False,
            "next_action": "REVIEW_REQUEST",
        }
    )
    return payload


def _review_lifecycle_snapshot() -> dict[str, object]:
    return {
        "branch": "main",
        "head": "a" * 40,
        "status": [
            " M docs/master-plan.md",
            " M apps/hermes-manager-pilot/README.md",
            "?? jarvis.bat",
        ],
    }


def _test_review_lifecycle_is_confirmed_recoverable_and_fail_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-lifecycle-") as temp_dir:
        repo, state_root, env = _review_store_fixture(temp_dir)
        session = _review_lifecycle_session(repo)
        snapshot = _review_lifecycle_snapshot()
        now = [100.0]
        tokens = iter(
            (
                "save_confirmation_000000000001",
                "delete_confirmation_00000001",
                "delete_confirmation_00000002",
                "delete_confirmation_00000003",
            )
        )
        service = ReviewLifecycleService(
            trusted_repo_root=repo,
            git_snapshot_loader=lambda: copy.deepcopy(snapshot),
            store_kwargs={"env": env, "repo_root": repo},
            record_id_generator=lambda: "review_000000000000000000000020",
            record_clock=lambda: datetime(2026, 7, 23, 1, 2, 3, tzinfo=timezone.utc),
            token_generator=lambda: next(tokens),
            monotonic_clock=lambda: now[0],
        )
        _assert_review_lifecycle_error(
            lambda: service.prepare_save(
                session,
                "Implemented and validated the lifecycle.",
                scope_confirmed=True,
                privacy_acknowledged=False,
                retention_acknowledged=True,
                session_id="local_session_0000000000000001",
            ),
            "review_privacy_not_acknowledged",
        )
        preview = service.prepare_save(
            session,
            "Implemented and validated the lifecycle.",
            scope_confirmed=True,
            privacy_acknowledged=True,
            retention_acknowledged=True,
            session_id="local_session_0000000000000001",
        )
        _assert(not state_root.exists(), "write-free Save preview created local state")
        preview_mapping = save_preview_to_dict(preview)
        _assert(preview_mapping["local_only"] is True, "Save preview omitted local-only disclosure")
        _assert(preview_mapping["encrypted"] is False, "Save preview falsely claimed encryption")
        _assert(preview_mapping["cloud_synced"] is False, "Save preview falsely claimed cloud sync")
        _assert(preview.record.review_passed is False, "Save preview granted Review approval")
        receipt = service.confirm_save(
            preview.confirmation_token,
            session_id="local_session_0000000000000001",
        )
        _assert(receipt["stored"] is True, "confirmed Save did not persist the exact Review")
        _assert_review_lifecycle_error(
            lambda: service.confirm_save(
                preview.confirmation_token,
                session_id="local_session_0000000000000001",
            ),
            "review_confirmation_expired_or_unknown",
        )
        listing = service.list_saved()
        _assert(listing["count"] == 1, "saved Review listing count mismatch")
        _assert("result_summary" not in listing["records"][0], "Review listing exposed result text")
        reopened = service.reopen(receipt["review_id"])
        _assert(reopened.result_summary == "Implemented and validated the lifecycle.", "read-only reopen lost Review content")
        _assert(reopened.commit_approved is False and reopened.push_allowed is False, "reopen restored authority")
        recovery = service.inspect_recovery(receipt["review_id"])
        _assert(recovery.status == "present_valid", "known saved Review recovery status mismatch")
        _assert(recovery_inspection_to_dict(recovery)["record"]["read_only"] is True, "recovery mapping lost read-only boundary")

        delete_preview = service.prepare_delete(
            receipt["review_id"],
            session_id="local_session_0000000000000001",
        )
        delete_mapping = delete_preview_to_dict(delete_preview)
        _assert("result_summary" not in delete_mapping, "Delete preview exposed result text")
        _assert(delete_preview.confirmation_text == f"DELETE {receipt['review_id']}", "Delete confirmation text mismatch")
        _assert_review_lifecycle_error(
            lambda: service.confirm_save(
                delete_preview.confirmation_token,
                session_id="local_session_0000000000000001",
            ),
            "review_confirmation_scope_mismatch",
        )
        _assert(service.reopen(receipt["review_id"]) == reopened, "wrong-domain token deleted a Review")

        mistyped_preview = service.prepare_delete(
            receipt["review_id"],
            session_id="local_session_0000000000000001",
        )
        _assert_review_lifecycle_error(
            lambda: service.confirm_delete(
                mistyped_preview.confirmation_token,
                "DELETE review_wrong",
                session_id="local_session_0000000000000001",
            ),
            "review_delete_confirmation_mismatch",
        )
        _assert(service.reopen(receipt["review_id"]) == reopened, "mistyped confirmation deleted a Review")
        final_preview = service.prepare_delete(
            receipt["review_id"],
            session_id="local_session_0000000000000001",
        )
        delete_receipt = service.confirm_delete(
            final_preview.confirmation_token,
            final_preview.confirmation_text,
            session_id="local_session_0000000000000001",
        )
        _assert(delete_receipt["operation"] == "exact_delete", "delete receipt operation mismatch")
        _assert(delete_receipt["deleted"] is True, "exact delete did not succeed")
        absent = service.inspect_recovery(receipt["review_id"])
        _assert(absent.status == "absent" and absent.record is None, "deleted Review recovery status mismatch")
        _assert_review_lifecycle_error(
            lambda: service.inspect_recovery("../not-an-id"),
            "review_id_invalid",
        )

    with tempfile.TemporaryDirectory(prefix="hermes-review-lifecycle-stale-") as temp_dir:
        repo, state_root, env = _review_store_fixture(temp_dir)
        snapshot = _review_lifecycle_snapshot()
        clock = [0.0]
        service = ReviewLifecycleService(
            trusted_repo_root=repo,
            git_snapshot_loader=lambda: copy.deepcopy(snapshot),
            store_kwargs={"env": env, "repo_root": repo},
            record_id_generator=lambda: "review_000000000000000000000021",
            record_clock=lambda: datetime(2026, 7, 23, 1, 2, 4, tzinfo=timezone.utc),
            token_generator=lambda: "save_confirmation_000000000021",
            monotonic_clock=lambda: clock[0],
        )
        preview = service.prepare_save(
            _review_lifecycle_session(repo),
            "Stale save must remain blocked.",
            scope_confirmed=True,
            privacy_acknowledged=True,
            retention_acknowledged=True,
            session_id="local_session_0000000000000021",
        )
        snapshot["head"] = "b" * 40
        _assert_review_lifecycle_error(
            lambda: service.confirm_save(
                preview.confirmation_token,
                session_id="local_session_0000000000000021",
            ),
            "review_save_snapshot_stale",
        )
        _assert(not state_root.exists(), "stale Save confirmation created local state")

        snapshot["head"] = "a" * 40
        preview = service.prepare_save(
            _review_lifecycle_session(repo),
            "Expired save must remain blocked.",
            scope_confirmed=True,
            privacy_acknowledged=True,
            retention_acknowledged=True,
            session_id="local_session_0000000000000021",
        )
        clock[0] = review_lifecycle_module.CONFIRMATION_TTL_SECONDS + 1
        _assert_review_lifecycle_error(
            lambda: service.confirm_save(
                preview.confirmation_token,
                session_id="local_session_0000000000000021",
            ),
            "review_confirmation_expired_or_unknown",
        )
        _assert(not state_root.exists(), "expired Save confirmation created local state")


def _test_review_lifecycle_routes_are_exact_and_session_bound() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-lifecycle-routes-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        service = ReviewLifecycleService(
            trusted_repo_root=repo,
            git_snapshot_loader=_review_lifecycle_snapshot,
            store_kwargs={"env": env, "repo_root": repo},
            record_id_generator=lambda: "review_000000000000000000000022",
            record_clock=lambda: datetime(2026, 7, 23, 1, 2, 5, tzinfo=timezone.utc),
            token_generator=lambda: "route_confirmation_000000000022",
            monotonic_clock=lambda: 10.0,
        )
        session_id = "local_session_0000000000000022"
        preview_payload = {
            "session": _review_lifecycle_session(repo),
            "result_summary": "Route lifecycle completed.",
            "scope_confirmed": True,
            "privacy_acknowledged": True,
            "retention_acknowledged": True,
        }
        invalid_status, invalid = hermes_web_app.handle_api_request(
            "/api/reviews/save-preview",
            {**preview_payload, "unexpected": True},
            lifecycle=service,
            local_session_id=session_id,
        )
        _assert(invalid_status == 400 and invalid["error"] == "review_save_preview_fields_invalid", "Review route accepted unknown fields")
        preview_status, preview_response = hermes_web_app.handle_api_request(
            "/api/reviews/save-preview",
            preview_payload,
            lifecycle=service,
            local_session_id=session_id,
        )
        _assert(preview_status == 200 and preview_response["ok"] is True, "Review Save preview route failed")
        token = preview_response["preview"]["confirmation_token"]
        save_status, save_response = hermes_web_app.handle_api_request(
            "/api/reviews/save-confirm",
            {"confirmation_token": token},
            lifecycle=service,
            local_session_id=session_id,
        )
        review_id = save_response["receipt"]["review_id"]
        _assert(save_status == 200, "Review Save confirmation route failed")
        reopen_status, reopen_response = hermes_web_app.handle_api_request(
            "/api/reviews/reopen",
            {"review_id": review_id},
            lifecycle=service,
            local_session_id=session_id,
        )
        _assert(reopen_status == 200 and reopen_response["record"]["read_only"] is True, "read-only reopen route failed")
        recovery_status, recovery_response = hermes_web_app.handle_api_request(
            "/api/reviews/recovery",
            {"review_id": review_id},
            lifecycle=service,
            local_session_id=session_id,
        )
        _assert(recovery_status == 200 and recovery_response["inspection"]["status"] == "present_valid", "recovery route failed")


def _test_review_lifecycle_http_guard_is_same_origin_and_clickjacking_safe() -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-review-http-guard-") as temp_dir:
        repo, _state_root, env = _review_store_fixture(temp_dir)
        lifecycle = ReviewLifecycleService(
            trusted_repo_root=repo,
            git_snapshot_loader=_review_lifecycle_snapshot,
            store_kwargs={"env": env, "repo_root": repo},
        )
        original_lifecycle = hermes_web_app.REVIEW_LIFECYCLE
        original_session = hermes_web_app.LOCAL_SESSION_ID
        server = hermes_web_app.ThreadingHTTPServer(
            ("127.0.0.1", 0),
            hermes_web_app.HermesWebHandler,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        hermes_web_app.REVIEW_LIFECYCLE = lifecycle
        hermes_web_app.LOCAL_SESSION_ID = "http_session_0000000000000001"
        thread.start()
        port = server.server_port
        try:
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", hermes_web_app.LOCAL_SESSION_ENDPOINT)
            response = connection.getresponse()
            session_payload = json.loads(response.read().decode("utf-8"))
            _assert(response.status == 200, "local session bootstrap failed")
            _assert(session_payload["local_session_id"] == hermes_web_app.LOCAL_SESSION_ID, "local session ID mismatch")
            _assert(response.getheader("X-Frame-Options") == "DENY", "frame denial header missing")
            _assert("frame-ancestors 'none'" in (response.getheader("Content-Security-Policy") or ""), "frame CSP missing")
            connection.close()

            origin = f"http://127.0.0.1:{port}"
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request(
                "POST",
                "/api/reviews/list",
                body="{}",
                headers={
                    "Content-Type": "application/json",
                    hermes_web_app.LOCAL_SESSION_HEADER: hermes_web_app.LOCAL_SESSION_ID,
                    "Origin": origin,
                },
            )
            response = connection.getresponse()
            list_payload = json.loads(response.read().decode("utf-8"))
            _assert(response.status == 200 and list_payload["listing"]["count"] == 0, "same-origin Review list failed")
            connection.close()

            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request(
                "POST",
                "/api/reviews/list",
                body="{}",
                headers={
                    "Content-Type": "application/json",
                    hermes_web_app.LOCAL_SESSION_HEADER: hermes_web_app.LOCAL_SESSION_ID,
                },
            )
            response = connection.getresponse()
            blocked_payload = json.loads(response.read().decode("utf-8"))
            _assert(response.status == 403 and blocked_payload["error"] == "same_origin_required", "missing Origin was not blocked")
            connection.close()

            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.putrequest("GET", "/", skip_host=True)
            connection.putheader("Host", f"attacker.example:{port}")
            connection.endheaders()
            response = connection.getresponse()
            host_payload = json.loads(response.read().decode("utf-8"))
            _assert(response.status == 403 and host_payload["error"] == "local_host_required", "non-loopback Host was not blocked")
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            hermes_web_app.REVIEW_LIFECYCLE = original_lifecycle
            hermes_web_app.LOCAL_SESSION_ID = original_session


def _test_review_store_remains_route_and_external_free() -> None:
    source = Path(review_store_module.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "BaseHTTPRequestHandler",
        "handle_api_request",
        "navigator.clipboard",
        "requests",
        "urlopen",
        "subprocess",
        "archive_review_record",
        "shutil.rmtree",
    ):
        _assert(forbidden not in source, f"Review store contains forbidden integration: {forbidden}")
    _assert("def delete_review_record(" in source, "exact Review delete primitive is missing")
    _assert("glob(" not in source, "Review store deletion must not use glob targeting")
    lifecycle_source = Path(review_lifecycle_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("requests", "urlopen", "subprocess", "rmtree", "threading.thread", "threading.timer"):
        _assert(forbidden not in lifecycle_source.lower(), f"Review lifecycle contains forbidden capability: {forbidden}")


def _test_browser_ui_mentions_manual_jarvis_handoff() -> None:
    index_html = (APP_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    app_js = (APP_ROOT / "web" / "app.js").read_text(encoding="utf-8")
    web_source = (APP_ROOT / "run_web_app.py").read_text(encoding="utf-8")
    _assert("Jarvis Console Memory / Skills candidate prompt" in index_html, "Jarvis Console handoff guidance missing")
    _assert("Manual review only" in index_html, "manual review guidance missing")
    _assert("nothing runs until you choose the next step" in index_html, "no-auto-run guidance missing")
    _assert("Save Review Object and Continue" in index_html, "Review object save action is missing")
    _assert("Clipboard is output only." in index_html, "clipboard output-only guidance missing")
    _assert("function reviewMatchesSession()" in app_js, "Review object/session binding is missing")
    review_save_source = app_js.split("function saveResultAndContinue()", 1)[1].split(
        "function approveCommit()",
        1,
    )[0]
    _assert("state.review = Object.freeze" in review_save_source, "Review object must be immutable")
    _assert("targetFiles: Object.freeze" in review_save_source, "Review target scope must be immutable")
    copy_handoff_source = app_js.split("async function copyJarvisReviewHandoff()", 1)[1].split(
        "async function renderPrompt",
        1,
    )[0]
    _assert("reviewMatchesSession()" in copy_handoff_source, "handoff must verify the saved Review object")
    _assert("state.review.resultSummary" in copy_handoff_source, "handoff must consume the saved Review object")
    _assert("elements.codexResult.value" not in copy_handoff_source, "handoff must not use the current textarea as state")
    _assert("navigator.clipboard.readText" not in app_js, "clipboard must never be read as workflow state")
    _assert("Send to Hermes" not in index_html, "automatic handoff wording must not appear")
    _assert("Local Durable Reviews" in index_html, "durable Review lifecycle UI is missing")
    _assert("retained locally until exact deletion" in index_html, "Review retention disclosure is missing")
    _assert("not encrypted, cloud-synced" in index_html, "Review privacy disclosure is missing")
    _assert("Memory / Skills save remains separate and disabled" in index_html, "Memory save boundary is missing")
    _assert("X-Hermes-Local-Session" in app_js, "Review lifecycle session header is missing")
    _assert("/api/reviews/save-preview" in app_js, "Review Save preview UI is missing")
    _assert("/api/reviews/reopen" in app_js, "Review read-only reopen UI is missing")
    _assert("/api/reviews/delete-preview" in app_js, "Review exact delete preview UI is missing")
    _assert("/api/memory-skills/candidates" not in app_js, "Hermes UI activated Memory candidate save")
    _assert("setInterval(" not in app_js, "Review lifecycle added background polling")
    _assert("local_host_header_is_valid" in web_source, "local Host validation is missing")
    _assert("same_origin_required" in web_source, "Review lifecycle same-origin guard is missing")
    _assert("frame-ancestors 'none'" in web_source, "clickjacking protection is missing")
    _assert("X-Frame-Options" in web_source, "frame protection header is missing")


def _test_copy_only_jarvis_review_handoff_is_deterministic_and_bounded() -> None:
    session = _sample_payload()
    target = "apps/hermes-manager-pilot/README.md"
    session.update(
        {
            "repo": str(REPO_ROOT),
            "branch": "stale-client-value",
            "head": "stale-client-value",
            "working_tree_status": "stale-client-value",
            "active_task": "Review the copy-only Jarvis handoff implementation.",
            "last_codex_result_summary": "Implementation completed with local tests.",
            "files_touched": [target],
            "target_files": [target],
            "commit_allowed": False,
            "human_approval_granted": False,
            "push_allowed": False,
        }
    )
    git_state = {
        "branch": "main",
        "head": "a" * 40,
        "working_tree_status": f" M {target}\n?? jarvis.bat",
    }

    first = build_copy_only_review_handoff(
        session,
        git_state,
        trusted_repo_root=REPO_ROOT,
        scope_confirmed=True,
    )
    second = build_copy_only_review_handoff(
        session,
        git_state,
        trusted_repo_root=REPO_ROOT,
        scope_confirmed=True,
    )
    _assert(first == second, "copy-only review handoff must be deterministic")
    _assert(set(first) == {"queue", "item_id"}, "handoff envelope fields changed")
    queue = normalize_prompt_queue(first["queue"])
    item = queue.items[0]
    project = queue.projects[0]
    _assert(item.item_id == first["item_id"], "handoff item ID mismatch")
    _assert(item.result_type == "review", "handoff must target review stage")
    _assert(item.scope_approved, "confirmed scope was not represented")
    expected_scope = build_scope_approval_binding(
        project,
        replace(item, result_type="implementation"),
    )
    _assert(
        digest_matches(expected_scope, item.scope_approval_digest),
        "scope confirmation binding is stale",
    )
    _assert(item.change_evidence_digest == "", "handoff must not carry evidence approval")
    _assert(not item.review_passed, "handoff must not approve review")
    _assert(not item.commit_approved, "handoff must not approve commit")
    _assert(item.review_approval_digest == "", "review digest must be absent")
    _assert(item.commit_approval_digest == "", "commit digest must be absent")
    _assert(item.commit_message == "", "commit message must be absent")
    _assert(project.expected_untracked == ("jarvis.bat",), "jarvis.bat boundary changed")
    _assert(
        set(project.forbidden_actions) == set(REQUIRED_FORBIDDEN_ACTIONS),
        "required forbidden actions changed",
    )
    rendered = render_copy_only_review_handoff(first)
    _assert(rendered == render_copy_only_review_handoff(second), "rendered handoff changed")
    _assert(json.loads(rendered)["item_id"] == first["item_id"], "rendered item ID missing")

    _assert_validation_error(
        lambda: build_copy_only_review_handoff(
            session,
            git_state,
            trusted_repo_root=REPO_ROOT,
            scope_confirmed=False,
        ),
        "scope must be explicitly confirmed",
    )
    missing_result = {**session, "last_codex_result_summary": ""}
    _assert_validation_error(
        lambda: build_copy_only_review_handoff(
            missing_result,
            git_state,
            trusted_repo_root=REPO_ROOT,
            scope_confirmed=True,
        ),
        "Codex result is required",
    )
    approved_commit = {
        **session,
        "commit_allowed": True,
        "human_approval_granted": True,
    }
    _assert_validation_error(
        lambda: build_copy_only_review_handoff(
            approved_commit,
            git_state,
            trusted_repo_root=REPO_ROOT,
            scope_confirmed=True,
        ),
        "must not contain commit approval",
    )
    missing_jarvis = {**git_state, "working_tree_status": f" M {target}"}
    _assert_validation_error(
        lambda: build_copy_only_review_handoff(
            session,
            missing_jarvis,
            trusted_repo_root=REPO_ROOT,
            scope_confirmed=True,
        ),
        "jarvis.bat must remain untracked",
    )


def _test_copy_only_review_handoff_route_fixes_repository_authority() -> None:
    session = _sample_payload()
    target = "apps/hermes-manager-pilot/README.md"
    session.update(
        {
            "repo": str(REPO_ROOT),
            "last_codex_result_summary": "Local implementation completed.",
            "files_touched": [target],
            "target_files": [target],
            "commit_allowed": False,
            "human_approval_granted": False,
            "push_allowed": False,
        }
    )
    captured_roots: list[Path] = []
    original_loader = hermes_web_app.load_git_status

    def fake_loader(root: str | Path) -> dict[str, str]:
        captured_roots.append(Path(root))
        return {
            "branch": "main",
            "head": "b" * 40,
            "working_tree_status": f" M {target}\n?? jarvis.bat",
        }

    hermes_web_app.load_git_status = fake_loader
    try:
        status, payload = hermes_web_app.handle_api_request(
            HANDOFF_ENDPOINT,
            {"session": session, "scope_confirmed": True},
        )
    finally:
        hermes_web_app.load_git_status = original_loader
    _assert(status == 200, "copy-only handoff route failed")
    _assert(payload["ok"] is True, "copy-only handoff route did not succeed")
    _assert(payload["copy_only"] is True, "handoff route is not copy-only")
    _assert(payload["no_persistence"] is True, "handoff route persistence boundary changed")
    _assert(captured_roots == [REPO_ROOT], "handoff route accepted caller repository authority")
    rendered = json.loads(payload["artifact"])
    _assert(rendered["item_id"] == payload["item_id"], "route item ID mismatch")

    source = Path(build_copy_only_review_handoff.__code__.co_filename).read_text(encoding="utf-8")
    for forbidden in (
        ".write_text(",
        ".write_bytes(",
        "subprocess",
        "requests",
        "urlopen",
        "render_mode",
        "execute",
    ):
        _assert(forbidden not in source, f"handoff helper contains forbidden operation: {forbidden}")


def _repo_file_set() -> set[str]:
    return {
        str(path.relative_to(REPO_ROOT))
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


def main() -> None:
    tests = (
        _test_implementation_prompt_deterministic,
        _test_review_prompt_deterministic,
        _test_commit_prompt_deterministic,
        _test_checkpoint_summary_deterministic,
        _test_sample_rendered_files_match_renderer_output,
        _test_stdout_mode_does_not_create_repo_file,
        _test_output_mode_writes_only_requested_file,
        _test_push_allowed_true_fails_validation,
        _test_commit_allowed_without_approval_fails_validation,
        _test_commit_allowed_without_granted_approval_renders_boundary,
        _test_protected_path_in_files_touched_fails_validation,
        _test_secret_like_fields_fail_validation,
        _test_unknown_next_action_fails_validation,
        _test_list_fields_must_be_lists,
        _test_protected_paths_required_and_sample_includes_jarvis,
        _test_prompts_include_jarvis_protection,
        _test_prompts_include_no_auto_push,
        _test_prompts_include_validation_commands,
        _test_commit_prompt_refuses_when_commit_disallowed,
        _test_prompt_queue_evaluation_is_deterministic,
        _test_prompt_queue_result_types_map_to_safe_actions,
        _test_prompt_queue_supports_multiple_project_cards,
        _test_prompt_queue_git_mismatch_blocks_for_user,
        _test_prompt_queue_protected_or_staged_change_blocks,
        _test_prompt_queue_scope_and_commit_approvals_are_separate,
        _test_prompt_queue_missing_safety_policy_blocks,
        _test_prompt_queue_rejects_unknown_fields_and_unsafe_paths,
        _test_prompt_queue_renderer_mapping_preserves_safety_boundaries,
        _test_approval_bindings_are_deterministic_and_domain_separated,
        _test_scope_binding_is_stable_for_set_order_and_changes_for_scope_mutation,
        _test_approval_binding_chain_rejects_stale_scope_review_and_message,
        _test_approval_binding_rejects_wrong_stage_bad_digest_and_oversize_snapshot,
        _test_approval_binding_excludes_mutable_summaries_and_authorization_flags,
        _test_binding_enforcement_rejects_legacy_missing_malformed_and_stale_scope,
        _test_binding_enforcement_requires_review_evidence_and_matching_review_digest,
        _test_binding_enforcement_requires_matching_commit_digest_and_blocks_renderer,
        _test_binding_enforcement_rejects_orphan_metadata,
        _test_local_change_evidence_is_deterministic_bounded_and_read_only,
        _test_local_change_evidence_verifier_rejects_tampering_and_scope_drift,
        _test_whole_worktree_status_evidence_is_complete_deterministic_and_read_only,
        _test_whole_worktree_status_evidence_rejects_tampering_and_unsafe_state,
        _test_whole_worktree_status_evidence_rejects_unstable_and_excessive_state,
        _test_review_evidence_bundle_is_deterministic_complete_and_purely_verifiable,
        _test_review_evidence_bundle_rejects_tampering_and_collection_races,
        _test_review_evidence_handoff_returns_only_verified_safe_preview,
        _test_review_evidence_handoff_blocks_unsafe_incomplete_or_tampered_evidence,
        _test_review_evidence_observation_adapter_updates_only_observations,
        _test_review_evidence_observation_adapter_fails_closed,
        _test_review_evidence_queue_bridge_replaces_one_item_and_evaluates,
        _test_review_evidence_queue_bridge_preserves_blocking_and_fails_closed,
        _test_fresh_review_handoff_returns_only_exact_current_preview,
        _test_fresh_review_handoff_blocks_before_io_when_not_actionable,
        _test_fresh_review_handoff_rejects_inconsistent_wrappers_before_io,
        _test_fresh_review_handoff_detects_stale_content_status_branch_and_head,
        _test_fresh_review_handoff_verifies_collector_output,
        _test_fresh_review_session_adapter_is_review_only_and_fail_closed,
        _test_local_change_evidence_rejects_scope_root_stage_and_size_violations,
        _test_local_change_evidence_rejects_reparse_and_unstable_reads,
        _test_local_change_evidence_status_parser_is_bounded_and_fail_closed,
        _test_review_record_contract_is_immutable_canonical_and_authority_free,
        _test_review_record_contract_fails_closed_on_unsafe_input,
        _test_review_record_freshness_is_exact_and_fail_closed,
        _test_review_record_core_has_no_io_route_or_clipboard_dependency,
        _test_review_store_path_policy_is_external_and_write_free,
        _test_review_store_append_read_and_bounded_list,
        _test_review_store_write_failure_and_recovery_states_fail_closed,
        _test_review_store_rejects_corruption_id_mismatch_and_capacity_overflow,
        _test_review_store_exact_delete_is_digest_bound_and_single_record_only,
        _test_review_lifecycle_is_confirmed_recoverable_and_fail_closed,
        _test_review_lifecycle_routes_are_exact_and_session_bound,
        _test_review_lifecycle_http_guard_is_same_origin_and_clickjacking_safe,
        _test_review_store_remains_route_and_external_free,
        _test_browser_ui_mentions_manual_jarvis_handoff,
        _test_copy_only_jarvis_review_handoff_is_deterministic_and_bounded,
        _test_copy_only_review_handoff_route_fixes_repository_authority,
    )
    for test in tests:
        test()
    print("Hermes Manager Pilot smoke tests passed")


if __name__ == "__main__":
    main()
