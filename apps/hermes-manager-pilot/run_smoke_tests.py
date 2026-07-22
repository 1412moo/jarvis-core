"""Smoke tests for the Hermes renderer and in-memory Prompt Queue primitives."""

from __future__ import annotations

import copy
from dataclasses import replace
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import hermes_manager_pilot.change_evidence as change_evidence_module
from hermes_manager_pilot.approval_binding import (
    build_commit_approval_binding,
    build_review_approval_binding,
    build_scope_approval_binding,
    digest_matches,
)
from hermes_manager_pilot.change_evidence import (
    MAX_FILE_BYTES,
    MAX_GIT_OUTPUT_BYTES,
    WHOLE_STATUS_COVERAGE,
    apply_review_evidence_observation,
    build_review_evidence_handoff_decision,
    collect_local_change_evidence,
    collect_review_evidence_bundle,
    collect_whole_worktree_status_evidence,
    verify_local_change_evidence,
    verify_review_evidence_bundle,
    verify_whole_worktree_status_evidence,
)
from hermes_manager_pilot.pipeline import run_hermes_manager_pilot
from hermes_manager_pilot.prompt_queue import (
    REQUIRED_FORBIDDEN_ACTIONS,
    build_hermes_session,
    evaluate_queue_item,
    normalize_prompt_queue,
)
from hermes_manager_pilot.prompt_renderer import render_commit_prompt
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


def _test_browser_ui_mentions_manual_jarvis_handoff() -> None:
    index_html = (APP_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    _assert("Jarvis Console Memory / Skills candidate prompt" in index_html, "Jarvis Console handoff guidance missing")
    _assert("Manual review only" in index_html, "manual review guidance missing")
    _assert("nothing runs until you choose the next step" in index_html, "no-auto-run guidance missing")
    _assert("Send to Hermes" not in index_html, "automatic handoff wording must not appear")


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
        _test_local_change_evidence_rejects_scope_root_stage_and_size_violations,
        _test_local_change_evidence_rejects_reparse_and_unstable_reads,
        _test_local_change_evidence_status_parser_is_bounded_and_fail_closed,
        _test_browser_ui_mentions_manual_jarvis_handoff,
    )
    for test in tests:
        test()
    print("Hermes Manager Pilot smoke tests passed")


if __name__ == "__main__":
    main()
