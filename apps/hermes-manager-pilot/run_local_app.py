"""Local GUI launcher for Hermes Manager Pilot v0.3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Callable

from hermes_manager_pilot.prompt_renderer import render_mode
from hermes_manager_pilot.schemas import ValidationError, normalize_session_state


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent.parent

DEFAULT_VALIDATION_COMMANDS = (
    "python -B -m py_compile apps\\hermes-manager-pilot\\run_local_app.py apps\\hermes-manager-pilot\\run_demo.py apps\\hermes-manager-pilot\\run_smoke_tests.py apps\\hermes-manager-pilot\\hermes_manager_pilot\\schemas.py apps\\hermes-manager-pilot\\hermes_manager_pilot\\pipeline.py apps\\hermes-manager-pilot\\hermes_manager_pilot\\prompt_renderer.py",
    "python -B apps\\hermes-manager-pilot\\run_local_app.py --self-test",
    "python -B apps\\hermes-manager-pilot\\run_smoke_tests.py",
    "python -B apps\\research-council\\run_smoke_tests.py",
    "python -B apps\\daily-ai-radar\\run_smoke_tests.py",
    "git diff --check",
)

ALLOWED_READ_ONLY_GIT_ARGS = frozenset(
    {
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("rev-parse", "HEAD"),
        ("status", "--short"),
    }
)


def default_session_state() -> dict[str, Any]:
    """Return an in-memory default session state for the local GUI."""

    return {
        "session_type": "hermes_manager_session_state",
        "version": "0.2",
        "repo": str(REPO_ROOT),
        "branch": "main",
        "head": "unknown",
        "working_tree_status": "Manual entry. Use Load Git Status for a read-only refresh.",
        "current_goal": "Prepare a bounded Codex prompt for a Jarvis-Core task.",
        "active_task": "Describe the next Codex task here.",
        "blocked_by": "",
        "last_codex_prompt": "",
        "last_codex_result_summary": "",
        "validation_commands": list(DEFAULT_VALIDATION_COMMANDS),
        "files_touched": ["apps/hermes-manager-pilot/"],
        "target_files": ["apps/hermes-manager-pilot/"],
        "protected_paths": ["jarvis.bat"],
        "commit_allowed": False,
        "push_allowed": False,
        "human_approval_required": True,
        "human_approval_granted": False,
        "next_action": "PROMPT_FOR_CODEX",
        "commit_message": "hermes-manager-pilot: update local workflow",
    }


def render_from_payload(payload: dict[str, Any], mode: str) -> str:
    """Validate a session payload and render a deterministic Markdown artifact."""

    session = normalize_session_state(payload)
    return render_mode(session, mode)


def save_session_file(payload: dict[str, Any], output_path: str | Path) -> None:
    """Write an explicitly requested session JSON file."""

    path = Path(output_path)
    if path.parent and not path.parent.exists():
        raise ValidationError(f"output_parent_not_found:{path.parent}")
    normalized = normalize_session_state(payload)
    safe_payload = {
        "session_type": normalized.session_type,
        "version": normalized.version,
        "repo": normalized.repo,
        "branch": normalized.branch,
        "head": normalized.head,
        "working_tree_status": normalized.working_tree_status,
        "current_goal": normalized.current_goal,
        "active_task": normalized.active_task,
        "blocked_by": normalized.blocked_by,
        "last_codex_prompt": normalized.last_codex_prompt,
        "last_codex_result_summary": normalized.last_codex_result_summary,
        "validation_commands": list(normalized.validation_commands),
        "files_touched": list(normalized.files_touched),
        "target_files": list(normalized.target_files),
        "protected_paths": list(normalized.protected_paths),
        "commit_allowed": normalized.commit_allowed,
        "push_allowed": False,
        "human_approval_required": normalized.human_approval_required,
        "human_approval_granted": normalized.human_approval_granted,
        "next_action": normalized.next_action,
        "commit_message": normalized.commit_message,
    }
    path.write_text(json.dumps(safe_payload, indent=2) + "\n", encoding="utf-8")


def load_session_file(input_path: str | Path) -> dict[str, Any]:
    """Load a local session JSON file and validate it."""

    path = Path(input_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"input_read_failed:{path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"input_json_invalid:{exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValidationError("session state must be a JSON object")
    normalize_session_state(payload)
    payload["push_allowed"] = False
    return payload


def load_git_status(repo_path: str | Path) -> dict[str, str]:
    """Read repo state with read-only git commands."""

    repo_text = str(repo_path).strip()
    if not repo_text:
        raise ValidationError("repo path is required for Load Git Status")
    repo = Path(repo_text)
    _run_read_only_git(repo, ("rev-parse", "--show-toplevel"))
    branch = _run_read_only_git(repo, ("rev-parse", "--abbrev-ref", "HEAD"))
    head = _run_read_only_git(repo, ("rev-parse", "HEAD"))
    status = _run_read_only_git(repo, ("status", "--short"))
    return {
        "branch": branch or "unknown",
        "head": head or "unknown",
        "working_tree_status": status or "clean",
    }


def launch_gui() -> None:
    """Launch the local tkinter GUI."""

    import tkinter as tk
    from tkinter import filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("Hermes Manager Pilot v0.3")
    root.geometry("1180x860")

    text_fields: dict[str, tk.Entry | ScrolledText] = {}
    commit_allowed_var = tk.BooleanVar(value=False)
    human_approval_granted_var = tk.BooleanVar(value=False)
    status_var = tk.StringVar(value="Ready. Local-only renderer; no Codex, ChatGPT, Hermes, commit, push, or network call.")

    def add_labeled_entry(parent: tk.Widget, label: str, key: str, row: int, width: int = 90) -> None:
        tk.Label(parent, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=4, pady=2)
        entry = tk.Entry(parent, width=width)
        entry.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
        text_fields[key] = entry

    def add_labeled_text(parent: tk.Widget, label: str, key: str, row: int, height: int) -> None:
        tk.Label(parent, text=label, anchor="nw").grid(row=row, column=0, sticky="nw", padx=4, pady=2)
        text = ScrolledText(parent, width=90, height=height, wrap=tk.WORD)
        text.grid(row=row, column=1, sticky="nsew", padx=4, pady=2)
        text_fields[key] = text

    container = tk.Frame(root)
    container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    container.columnconfigure(0, weight=1)
    container.columnconfigure(1, weight=1)
    container.rowconfigure(0, weight=1)

    left = tk.Frame(container)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    left.columnconfigure(1, weight=1)

    right = tk.Frame(container)
    right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    right.columnconfigure(0, weight=1)
    right.rowconfigure(1, weight=1)

    repo_frame = tk.LabelFrame(left, text="Repo Status")
    repo_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=4)
    repo_frame.columnconfigure(1, weight=1)
    add_labeled_entry(repo_frame, "Repo path", "repo", 0)
    add_labeled_entry(repo_frame, "Branch", "branch", 1)
    add_labeled_entry(repo_frame, "HEAD", "head", 2)
    add_labeled_text(repo_frame, "Working tree status", "working_tree_status", 3, 4)
    add_labeled_text(repo_frame, "Protected paths", "protected_paths", 4, 2)

    tk.Button(repo_frame, text="Load Git Status", command=lambda: _gui_load_git_status()).grid(
        row=5,
        column=1,
        sticky="e",
        padx=4,
        pady=4,
    )

    task_frame = tk.LabelFrame(left, text="Task")
    task_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)
    task_frame.columnconfigure(1, weight=1)
    add_labeled_text(task_frame, "Current goal", "current_goal", 0, 3)
    add_labeled_text(task_frame, "Active task", "active_task", 1, 3)
    add_labeled_text(task_frame, "Files touched", "files_touched", 2, 3)
    add_labeled_text(task_frame, "Target files", "target_files", 3, 2)
    add_labeled_text(task_frame, "Validation commands", "validation_commands", 4, 5)
    add_labeled_entry(task_frame, "Blocked by", "blocked_by", 5)

    codex_frame = tk.LabelFrame(left, text="Codex Result")
    codex_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)
    codex_frame.columnconfigure(1, weight=1)
    add_labeled_text(codex_frame, "Last Codex prompt summary", "last_codex_prompt", 0, 3)
    add_labeled_text(codex_frame, "Last Codex result summary", "last_codex_result_summary", 1, 4)

    approval_frame = tk.LabelFrame(left, text="Approval")
    approval_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)
    tk.Checkbutton(approval_frame, text="commit_allowed", variable=commit_allowed_var).grid(
        row=0,
        column=0,
        sticky="w",
        padx=4,
        pady=2,
    )
    tk.Checkbutton(
        approval_frame,
        text="human_approval_granted",
        variable=human_approval_granted_var,
    ).grid(row=0, column=1, sticky="w", padx=4, pady=2)
    tk.Label(
        approval_frame,
        text="human_approval_required is always true. push_allowed is always false. Commit prompt requires explicit user approval.",
        anchor="w",
    ).grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=2)

    buttons_frame = tk.Frame(right)
    buttons_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    for index in range(4):
        buttons_frame.columnconfigure(index, weight=1)

    tk.Button(buttons_frame, text="Generate Implementation Prompt", command=lambda: _gui_generate("PROMPT_FOR_CODEX", "implementation-prompt")).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
    tk.Button(buttons_frame, text="Generate Review Prompt", command=lambda: _gui_generate("REVIEW_REQUEST", "review-prompt")).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
    tk.Button(buttons_frame, text="Generate Commit Prompt", command=lambda: _gui_generate("COMMIT_REQUEST", "commit-prompt")).grid(row=0, column=2, sticky="ew", padx=2, pady=2)
    tk.Button(buttons_frame, text="Generate Checkpoint Summary", command=lambda: _gui_generate("STATUS_SUMMARY", "checkpoint-summary")).grid(row=0, column=3, sticky="ew", padx=2, pady=2)
    tk.Button(buttons_frame, text="Copy Output", command=lambda: _gui_copy_output()).grid(row=1, column=0, sticky="ew", padx=2, pady=2)
    tk.Button(buttons_frame, text="Save Session", command=lambda: _gui_save_session()).grid(row=1, column=1, sticky="ew", padx=2, pady=2)
    tk.Button(buttons_frame, text="Load Session", command=lambda: _gui_load_session()).grid(row=1, column=2, sticky="ew", padx=2, pady=2)
    tk.Button(buttons_frame, text="Clear Output", command=lambda: _set_output("")).grid(row=1, column=3, sticky="ew", padx=2, pady=2)

    output = ScrolledText(right, width=90, height=40, wrap=tk.WORD)
    output.grid(row=1, column=0, sticky="nsew")

    status = tk.Label(root, textvariable=status_var, anchor="w")
    status.pack(fill=tk.X, padx=8, pady=(0, 8))

    def _gui_load_git_status() -> None:
        try:
            git_state = load_git_status(_field_value("repo"))
            _set_field("branch", git_state["branch"])
            _set_field("head", git_state["head"])
            _set_field("working_tree_status", git_state["working_tree_status"])
            status_var.set("Loaded read-only git status.")
        except (OSError, subprocess.SubprocessError, ValidationError) as exc:
            status_var.set(f"Git status load failed; manual entry is still allowed: {exc}")

    def _gui_generate(next_action: str, mode: str) -> None:
        try:
            payload = _payload_from_form(next_action)
            rendered = render_from_payload(payload, mode)
            _set_output(rendered)
            status_var.set(f"Rendered {mode}. No external call was made.")
        except ValidationError as exc:
            _set_output(f"Validation error: {exc}\n")
            status_var.set("Validation failed. Fix the form values and try again.")

    def _gui_copy_output() -> None:
        try:
            text = output.get("1.0", tk.END).strip()
            root.clipboard_clear()
            root.clipboard_append(text)
            status_var.set("Output copied to clipboard.")
        except tk.TclError as exc:
            status_var.set(f"Copy failed; output remains visible: {exc}")
            messagebox.showerror("Copy failed", str(exc))

    def _gui_save_session() -> None:
        path = filedialog.asksaveasfilename(
            title="Save Hermes session",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            save_session_file(_payload_from_form("STATUS_SUMMARY"), path)
            status_var.set(f"Session saved: {path}")
        except ValidationError as exc:
            messagebox.showerror("Save failed", str(exc))
            status_var.set("Session save failed.")

    def _gui_load_session() -> None:
        path = filedialog.askopenfilename(
            title="Load Hermes session",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            payload = load_session_file(path)
            _populate_form(payload)
            status_var.set(f"Session loaded: {path}")
        except ValidationError as exc:
            messagebox.showerror("Load failed", str(exc))
            status_var.set("Session load failed.")

    def _payload_from_form(next_action: str) -> dict[str, Any]:
        payload = {
            "session_type": "hermes_manager_session_state",
            "version": "0.2",
            "repo": _field_value("repo"),
            "branch": _field_value("branch"),
            "head": _field_value("head"),
            "working_tree_status": _field_value("working_tree_status"),
            "current_goal": _field_value("current_goal"),
            "active_task": _field_value("active_task"),
            "blocked_by": _field_value("blocked_by"),
            "last_codex_prompt": _field_value("last_codex_prompt"),
            "last_codex_result_summary": _field_value("last_codex_result_summary"),
            "validation_commands": _lines("validation_commands"),
            "files_touched": _lines("files_touched"),
            "target_files": _lines("target_files"),
            "protected_paths": _lines("protected_paths"),
            "commit_allowed": bool(commit_allowed_var.get()),
            "push_allowed": False,
            "human_approval_required": True,
            "human_approval_granted": bool(human_approval_granted_var.get()),
            "next_action": next_action,
            "commit_message": "hermes-manager-pilot: update local workflow",
        }
        return payload

    def _populate_form(payload: dict[str, Any]) -> None:
        normalized = normalize_session_state(payload)
        _set_field("repo", normalized.repo)
        _set_field("branch", normalized.branch)
        _set_field("head", normalized.head)
        _set_field("working_tree_status", normalized.working_tree_status)
        _set_field("current_goal", normalized.current_goal)
        _set_field("active_task", normalized.active_task)
        _set_field("blocked_by", normalized.blocked_by)
        _set_field("last_codex_prompt", normalized.last_codex_prompt)
        _set_field("last_codex_result_summary", normalized.last_codex_result_summary)
        _set_field("validation_commands", "\n".join(normalized.validation_commands))
        _set_field("files_touched", "\n".join(normalized.files_touched))
        _set_field("target_files", "\n".join(normalized.target_files))
        _set_field("protected_paths", "\n".join(normalized.protected_paths))
        commit_allowed_var.set(normalized.commit_allowed)
        human_approval_granted_var.set(normalized.human_approval_granted)

    def _field_value(key: str) -> str:
        widget = text_fields[key]
        if isinstance(widget, ScrolledText):
            return widget.get("1.0", tk.END).strip()
        return widget.get().strip()

    def _set_field(key: str, value: str) -> None:
        widget = text_fields[key]
        if isinstance(widget, ScrolledText):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", value)
        else:
            widget.delete(0, tk.END)
            widget.insert(0, value)

    def _lines(key: str) -> list[str]:
        return [line.strip() for line in _field_value(key).splitlines() if line.strip()]

    def _set_output(text: str) -> None:
        output.delete("1.0", tk.END)
        output.insert("1.0", text)

    _populate_form(default_session_state())
    root.mainloop()


def run_self_test() -> None:
    """Run GUI helper tests without opening a window."""

    before = _repo_file_set()
    payload = default_session_state()
    _assert("jarvis.bat" in payload["protected_paths"], "default protected_paths must include jarvis.bat")
    _assert(payload["push_allowed"] is False, "default push_allowed must be false")

    implementation_prompt = render_from_payload({**payload, "next_action": "PROMPT_FOR_CODEX"}, "implementation-prompt")
    _assert("# Codex Implementation Prompt" in implementation_prompt, "implementation prompt missing")

    review_prompt = render_from_payload({**payload, "next_action": "REVIEW_REQUEST"}, "review-prompt")
    _assert("# Codex Review Prompt" in review_prompt, "review prompt missing")

    commit_refusal = render_from_payload({**payload, "next_action": "COMMIT_REQUEST"}, "commit-prompt")
    _assert("Do not commit." in commit_refusal, "commit_allowed=false should refuse commit")

    approval_needed = render_from_payload(
        {
            **payload,
            "next_action": "COMMIT_REQUEST",
            "commit_allowed": True,
            "human_approval_granted": False,
        },
        "commit-prompt",
    )
    _assert("approval has not been recorded" in approval_needed, "missing approval-needed commit boundary")
    _assert("Run `git status --short`." not in approval_needed, "commit checklist rendered before approval")

    approved_commit_prompt = render_from_payload(
        {
            **payload,
            "next_action": "COMMIT_REQUEST",
            "commit_allowed": True,
            "human_approval_granted": True,
        },
        "commit-prompt",
    )
    for expected in (
        "Run `git status --short`.",
        "Run `git diff --cached --check`.",
        "jarvis.bat",
        "Validation Commands",
    ):
        _assert(expected in approved_commit_prompt, f"approved commit prompt missing: {expected}")

    checkpoint_summary = render_from_payload({**payload, "next_action": "STATUS_SUMMARY"}, "checkpoint-summary")
    _assert("# Hermes Manager Pilot Checkpoint Summary" in checkpoint_summary, "checkpoint summary missing")

    protected_payload = {**payload, "files_touched": ["jarvis.bat"]}
    _assert_raises(lambda: render_from_payload(protected_payload, "implementation-prompt"), "protected path should fail")

    empty_validation_prompt = render_from_payload(
        {**payload, "validation_commands": [], "next_action": "PROMPT_FOR_CODEX"},
        "implementation-prompt",
    )
    _assert(
        "No validation commands are listed" in empty_validation_prompt,
        "empty validation command list should render as missing validation",
    )

    _assert_raises(lambda: load_git_status(""), "empty repo path should fail read-only git status")
    with tempfile.TemporaryDirectory(prefix="hermes-local-app-not-git-") as temp_dir:
        _assert_raises(lambda: load_git_status(temp_dir), "non-git repo path should fail safely")

    git_state = load_git_status(REPO_ROOT)
    _assert(git_state["branch"], "read-only git status should return branch")
    _assert(git_state["head"], "read-only git status should return head")
    _assert_raises(lambda: _run_read_only_git(REPO_ROOT, ("add", ".")), "git add must be blocked")

    with tempfile.TemporaryDirectory(prefix="hermes-local-app-self-test-") as temp_dir:
        roundtrip_path = Path(temp_dir) / "session.json"
        save_session_file(payload, roundtrip_path)
        loaded = load_session_file(roundtrip_path)
        _assert(loaded["protected_paths"] == ["jarvis.bat"], "roundtrip lost protected path")
        _assert(loaded["push_allowed"] is False, "roundtrip changed push_allowed")

        push_true_path = Path(temp_dir) / "push-true.json"
        push_true_payload = {**payload, "push_allowed": True}
        push_true_path.write_text(json.dumps(push_true_payload), encoding="utf-8")
        _assert_raises(lambda: load_session_file(push_true_path), "push_allowed=true load should fail")

        token_path = Path(temp_dir) / "token.json"
        token_payload = {**payload, "token": "do-not-store"}
        token_path.write_text(json.dumps(token_payload), encoding="utf-8")
        _assert_raises(lambda: load_session_file(token_path), "token field load should fail")

        reasoning_path = Path(temp_dir) / "chain-of-thought.json"
        reasoning_payload = {**payload, "chain_of_thought": "do-not-store"}
        reasoning_path.write_text(json.dumps(reasoning_payload), encoding="utf-8")
        _assert_raises(
            lambda: load_session_file(reasoning_path),
            "chain_of_thought field load should fail",
        )

    after = _repo_file_set()
    _assert(before == after, "self-test changed repository files")
    print("Hermes Manager Pilot local app self-test passed")


def _run_read_only_git(repo: Path, args: tuple[str, ...]) -> str:
    if args not in ALLOWED_READ_ONLY_GIT_ARGS:
        raise ValidationError(f"git command is not allowed in local GUI: git {' '.join(args)}")
    completed = subprocess.run(
        ("git", *args),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ValidationError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _repo_file_set() -> set[str]:
    return {
        str(path.relative_to(REPO_ROOT))
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_raises(fn: Callable[[], object], message: str) -> None:
    try:
        fn()
    except ValidationError:
        return
    raise AssertionError(message)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Hermes Manager Pilot v0.3 local GUI.")
    parser.add_argument("--self-test", action="store_true", help="Run helper tests without opening the GUI.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.self_test:
        run_self_test()
        return
    launch_gui()


if __name__ == "__main__":
    main()
