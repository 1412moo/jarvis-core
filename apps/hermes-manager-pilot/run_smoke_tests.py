"""Smoke tests for the Hermes renderer and in-memory Prompt Queue primitives."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hermes_manager_pilot.approval_binding import (
    build_commit_approval_binding,
    build_review_approval_binding,
    build_scope_approval_binding,
    digest_matches,
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


def _sample_payload() -> dict[str, object]:
    return json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))


def _render_sample(mode: str) -> str:
    return run_hermes_manager_pilot(SAMPLE_INPUT, mode)


def _sample_queue_payload(result_type: str = "implementation") -> dict[str, object]:
    return {
        "queue_type": "hermes_prompt_queue",
        "version": "0.1A",
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
                "scope_approved": True,
                "review_passed": False,
                "commit_approved": False,
                "commit_message": "",
                "last_prompt_summary": "Implement the approved v0.1A unit.",
                "last_result_summary": "",
            }
        ],
    }


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
        _test_browser_ui_mentions_manual_jarvis_handoff,
    )
    for test in tests:
        test()
    print("Hermes Manager Pilot smoke tests passed")


if __name__ == "__main__":
    main()
