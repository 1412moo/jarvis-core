"""Smoke tests for the Hermes Manager Pilot v0.2 deterministic renderer."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hermes_manager_pilot.pipeline import run_hermes_manager_pilot
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
        _test_browser_ui_mentions_manual_jarvis_handoff,
    )
    for test in tests:
        test()
    print("Hermes Manager Pilot smoke tests passed")


if __name__ == "__main__":
    main()
