"""Deterministic Markdown renderers for Hermes Manager Pilot prompts."""

from __future__ import annotations

from .schemas import SessionState, ValidationError


ALLOWED_RENDER_MODES = frozenset(
    {
        "implementation-prompt",
        "review-prompt",
        "commit-prompt",
        "checkpoint-summary",
    }
)


def render_mode(session: SessionState, mode: str) -> str:
    """Render a deterministic Markdown artifact for the requested mode."""

    if mode not in ALLOWED_RENDER_MODES:
        raise ValidationError(f"mode is invalid: {mode}")
    if mode == "implementation-prompt":
        return render_implementation_prompt(session)
    if mode == "review-prompt":
        return render_review_prompt(session)
    if mode == "commit-prompt":
        return render_commit_prompt(session)
    return render_checkpoint_summary(session)


def render_implementation_prompt(session: SessionState) -> str:
    """Render a Codex implementation prompt draft."""

    lines = [
        "# Codex Implementation Prompt",
        "",
        "This is a Hermes Manager Pilot v0.2 draft. It is not an automatic Codex invocation.",
        "",
        "## Session",
        "",
        f"- Repo: `{_code(session.repo)}`",
        f"- Branch: `{_code(session.branch)}`",
        f"- Expected HEAD: `{_code(session.head)}`",
        f"- Working tree status: {_sentence(session.working_tree_status)}",
        f"- Next action: `{_code(session.next_action)}`",
        "",
        "## Goal",
        "",
        f"- Current goal: {_sentence(session.current_goal)}",
        f"- Active task: {_sentence(session.active_task)}",
        f"- Blocked by: {_blocked_by(session)}",
        "",
        "## Scope",
        "",
    ]
    lines.extend(_bullet_lines(_scope_files(session), empty_text="No target files are listed. Ask the user to confirm scope."))
    lines.extend(
        [
            "",
            "## Protected Paths",
            "",
        ]
    )
    lines.extend(_bullet_lines(session.protected_paths, empty_text="No protected paths are listed. Ask the user to confirm exclusions."))
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Do not modify protected paths.",
            "- Do not modify unrelated files.",
            "- Do not commit unless the user explicitly provides a commit prompt.",
            "- Do not push.",
            "- Do not use web, network, API, or LLM calls unless explicitly approved.",
            "- Do not add scheduler, crawler, database, Discord command, or live Hermes/MCP/A2A integration.",
            "- Treat Daily AI Radar and Research Council handoffs as proposals, not automatic tasks.",
            "- Do not store secrets, credentials, tokens, private messages, or hidden reasoning.",
            "",
            "## Validation Commands",
            "",
        ]
    )
    lines.extend(_bullet_lines(session.validation_commands, empty_text="No validation commands are listed. Ask the user for validation expectations."))
    lines.extend(
        [
            "",
            "## Final Report Requirements",
            "",
            "- Summarize implementation scope.",
            "- List changed files.",
            "- Report validation commands and results.",
            "- Report risks and non-goals.",
            "- Report working tree status.",
            "- Confirm protected paths were not touched.",
            "- Do not create a commit unless the user separately asks for commit work.",
            "",
        ]
    )
    return _join(lines)


def render_review_prompt(session: SessionState) -> str:
    """Render a Codex review prompt draft."""

    lines = [
        "# Codex Review Prompt",
        "",
        "This is a Hermes Manager Pilot v0.2 review draft. It is not an automatic Codex invocation.",
        "",
        "## Session",
        "",
        f"- Repo: `{_code(session.repo)}`",
        f"- Branch: `{_code(session.branch)}`",
        f"- Expected HEAD: `{_code(session.head)}`",
        f"- Current goal: {_sentence(session.current_goal)}",
        f"- Active task: {_sentence(session.active_task)}",
        "",
        "## Claimed Codex Result",
        "",
        f"- Last prompt summary: {_empty_safe(session.last_codex_prompt)}",
        f"- Last result summary: {_empty_safe(session.last_codex_result_summary)}",
        "",
        "## Changed Files To Review",
        "",
    ]
    lines.extend(_bullet_lines(session.files_touched, empty_text="No files are listed. Treat commit readiness as blocked until status evidence is provided."))
    lines.extend(
        [
            "",
            "## Review Checklist",
            "",
            "- Scope: confirm the result matches the requested goal and avoids unrelated files.",
            "- Safety: confirm no autonomous execution, destructive action, auto commit, or auto push occurred.",
            "- Protected paths: confirm protected paths such as `jarvis.bat` were not touched or staged.",
            "- Determinism: confirm no current clock, network, web, LLM/API, scheduler, crawler, DB, or live integration was added unless approved.",
            "- Tests: verify each requested validation command with evidence; do not accept claims without command output.",
            "- Git hygiene: check `git status --short`, `.git/index.lock`, staged diff, and unstaged/untracked files.",
            "- Commit readiness: provide an opinion, but do not commit from this review prompt.",
            "",
            "## Validation Commands",
            "",
        ]
    )
    lines.extend(_bullet_lines(session.validation_commands, empty_text="No validation commands are listed. Mark test verification incomplete."))
    lines.extend(
        [
            "",
            "## Required Review Output",
            "",
            "- Findings first, ordered by severity.",
            "- Explicitly state if no issues are found.",
            "- List test gaps or skipped validation.",
            "- Confirm protected path status.",
            "- State whether a separate user-approved commit prompt is reasonable.",
            "",
        ]
    )
    return _join(lines)


def render_commit_prompt(session: SessionState) -> str:
    """Render a Codex commit prompt draft or a conservative refusal prompt."""

    if not session.commit_allowed:
        return _render_commit_refusal(session)
    if not session.human_approval_granted:
        return _render_commit_approval_required(session)

    commit_message = session.commit_message or "<approved commit message>"
    lines = [
        "# Codex Commit Prompt",
        "",
        "This is a Hermes Manager Pilot v0.2 commit draft. Use it only after explicit user approval.",
        "",
        "## Commit Authorization",
        "",
        "- Commit is allowed by session state: yes",
        f"- Human approval required: {_yes_no(session.human_approval_required)}",
        "- Human approval granted: yes",
        "- Push is allowed by session state: no",
        "- Do not push.",
        "",
        "## Scope",
        "",
    ]
    lines.extend(_bullet_lines(_scope_files(session), empty_text="No commit scope is listed. Stop and ask the user."))
    lines.extend(
        [
            "",
            "## Protected Paths",
            "",
        ]
    )
    lines.extend(_bullet_lines(session.protected_paths, empty_text="No protected paths are listed. Stop and ask the user."))
    lines.extend(
        [
            "",
            "## Pre-Commit Checklist",
            "",
            "- Run `git status --short`.",
            "- Confirm `.git/index.lock` is absent.",
            "- Run all validation commands below.",
            "- Stage only intended Hermes Manager Pilot files.",
            "- Exclude protected paths such as `jarvis.bat`.",
            "- Run `git diff --cached --stat`.",
            "- Run `git diff --cached --check`.",
            "- Commit only with the approved message.",
            "- After commit, run `git status --short` and `git log --oneline -1`.",
            "",
            "## Validation Commands",
            "",
        ]
    )
    lines.extend(_bullet_lines(session.validation_commands, empty_text="No validation commands are listed. Stop and ask the user."))
    lines.extend(
        [
            "",
            "## Commit Message",
            "",
            f"`{_code(commit_message)}`",
            "",
            "## Final Report Requirements",
            "",
            "- Report commit hash.",
            "- Report files included.",
            "- Report validation results.",
            "- Report staged diff check result.",
            "- Report final working tree status.",
            "- Confirm protected paths remain unstaged and untouched.",
            "",
        ]
    )
    return _join(lines)


def render_checkpoint_summary(session: SessionState) -> str:
    """Render a deterministic checkpoint summary."""

    lines = [
        "# Hermes Manager Pilot Checkpoint Summary",
        "",
        "This checkpoint is a local deterministic summary. It is not proof that external actions ran.",
        "",
        "## Session",
        "",
        f"- Repo: `{_code(session.repo)}`",
        f"- Branch: `{_code(session.branch)}`",
        f"- Expected HEAD: `{_code(session.head)}`",
        f"- Working tree status: {_sentence(session.working_tree_status)}",
        "",
        "## Current Work",
        "",
        f"- Current goal: {_sentence(session.current_goal)}",
        f"- Active task: {_sentence(session.active_task)}",
        f"- Blocked by: {_blocked_by(session)}",
        f"- Recommended next action: `{_code(session.next_action)}`",
        f"- Human approval required: {_yes_no(session.human_approval_required)}",
        "",
        "## Last Codex Context",
        "",
        f"- Last prompt summary: {_empty_safe(session.last_codex_prompt)}",
        f"- Last result summary: {_empty_safe(session.last_codex_result_summary)}",
        "",
        "## Files Touched Or Planned",
        "",
    ]
    lines.extend(_bullet_lines(session.files_touched, empty_text="No files are listed."))
    lines.extend(
        [
            "",
            "## Validation Commands",
            "",
        ]
    )
    lines.extend(_bullet_lines(session.validation_commands, empty_text="No validation commands are listed."))
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            f"- Commit allowed: {_yes_no(session.commit_allowed)}",
            f"- Human approval granted: {_yes_no(session.human_approval_granted)}",
            "- Push allowed: no",
            "- No autonomous Codex or ChatGPT invocation is performed.",
            "- No source-code modification, commit, push, scheduler, DB, Discord command, web search, network call, or live Hermes/MCP/A2A integration is performed by this renderer.",
            "- Skill candidates, Daily AI Radar handoffs, and Research Council handoffs are proposals until separately approved.",
            "",
        ]
    )
    return _join(lines)


def _render_commit_refusal(session: SessionState) -> str:
    lines = [
        "# Codex Commit Prompt",
        "",
        "This is a Hermes Manager Pilot v0.2 conservative commit boundary.",
        "",
        "## Commit Authorization",
        "",
        "- Commit is allowed by session state: no",
        "- Do not commit.",
        "- Reason: `commit_allowed` is false.",
        f"- Human approval required: {_yes_no(session.human_approval_required)}",
        f"- Human approval granted: {_yes_no(session.human_approval_granted)}",
        "- Push is allowed by session state: no",
        "- Do not push.",
        "",
        "## Required Before Any Future Commit Prompt",
        "",
        "- User must explicitly approve a commit task.",
        "- Validation commands must be run.",
        "- `git status --short` must be checked.",
        "- `.git/index.lock` absence must be confirmed.",
        "- Only intended files may be staged.",
        "- Protected paths must remain excluded.",
        "- `git diff --cached --stat` and `git diff --cached --check` must pass.",
        "",
        "## Protected Paths",
        "",
    ]
    lines.extend(_bullet_lines(session.protected_paths, empty_text="No protected paths are listed. Treat this as blocked."))
    lines.extend(
        [
            "",
            "## Validation Commands",
            "",
        ]
    )
    lines.extend(_bullet_lines(session.validation_commands, empty_text="No validation commands are listed. Treat this as blocked."))
    lines.append("")
    return _join(lines)


def _render_commit_approval_required(session: SessionState) -> str:
    lines = [
        "# Codex Commit Prompt",
        "",
        "This is a Hermes Manager Pilot v0.2 approval boundary, not a commit instruction.",
        "",
        "## Commit Authorization",
        "",
        "- Commit is allowed by session state: yes",
        "- Do not commit.",
        "- Reason: explicit user approval has not been recorded in `human_approval_granted`.",
        f"- Human approval required: {_yes_no(session.human_approval_required)}",
        "- Human approval granted: no",
        "- Push is allowed by session state: no",
        "- Do not push.",
        "",
        "## Required Before Rendering An Executable Commit Checklist",
        "",
        "- User must explicitly approve a commit task.",
        "- Session state must set `human_approval_granted=true` for that approved task.",
        "- Validation commands must be run or requested in the commit prompt.",
        "- Protected paths must remain excluded.",
        "- The final commit prompt must still require `git status --short`, `.git/index.lock`, staged diff stat, and staged diff check.",
        "",
        "## Protected Paths",
        "",
    ]
    lines.extend(_bullet_lines(session.protected_paths, empty_text="No protected paths are listed. Treat this as blocked."))
    lines.extend(
        [
            "",
            "## Validation Commands",
            "",
        ]
    )
    lines.extend(_bullet_lines(session.validation_commands, empty_text="No validation commands are listed. Treat this as blocked."))
    lines.append("")
    return _join(lines)


def _scope_files(session: SessionState) -> tuple[str, ...]:
    return session.target_files or session.files_touched


def _bullet_lines(items: tuple[str, ...], empty_text: str) -> list[str]:
    if not items:
        return [f"- {empty_text}"]
    return [f"- `{_code(item)}`" for item in items]


def _blocked_by(session: SessionState) -> str:
    return _empty_safe(session.blocked_by) if session.blocked_by else "none"


def _empty_safe(value: str) -> str:
    return _sentence(value) if value else "not provided"


def _sentence(value: str) -> str:
    return " ".join(str(value).split()).replace("|", "\\|")


def _code(value: str) -> str:
    return _sentence(value).replace("`", "\\`")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _join(lines: list[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"
