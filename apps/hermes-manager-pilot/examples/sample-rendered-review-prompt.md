# Codex Review Prompt

This is a Hermes Manager Pilot v0.2 review draft. It is not an automatic Codex invocation.

## Session

- Repo: `C:\work\jarvis-core`
- Branch: `main`
- Expected HEAD: `8bc6b12`
- Current goal: Implement Hermes Manager Pilot v0.2 as a local deterministic session and prompt renderer.
- Active task: Add local JSON validation, Codex prompt renderers, checkpoint summary renderer, sample fixtures, and smoke tests.

## Claimed Codex Result

- Last prompt summary: User requested v0.2 design and implementation. The request explicitly excludes Hermes runtime integration, automatic Codex or ChatGPT calls, auto commit, auto push, web search, scheduler, database, Discord command, and repo modification outside the scoped files.
- Last result summary: No external Hermes, Codex, or ChatGPT execution is represented by this fixture. Rendered artifacts are local deterministic examples only.

## Changed Files To Review

- `apps/hermes-manager-pilot/README.md`
- `apps/hermes-manager-pilot/hermes_manager_pilot/__init__.py`
- `apps/hermes-manager-pilot/hermes_manager_pilot/schemas.py`
- `apps/hermes-manager-pilot/hermes_manager_pilot/pipeline.py`
- `apps/hermes-manager-pilot/hermes_manager_pilot/prompt_renderer.py`
- `apps/hermes-manager-pilot/examples/sample-session-state.json`
- `apps/hermes-manager-pilot/examples/sample-rendered-implementation-prompt.md`
- `apps/hermes-manager-pilot/examples/sample-rendered-review-prompt.md`
- `apps/hermes-manager-pilot/examples/sample-rendered-commit-prompt.md`
- `apps/hermes-manager-pilot/examples/sample-checkpoint-summary.md`
- `apps/hermes-manager-pilot/run_demo.py`
- `apps/hermes-manager-pilot/run_smoke_tests.py`

## Review Checklist

- Scope: confirm the result matches the requested goal and avoids unrelated files.
- Safety: confirm no autonomous execution, destructive action, auto commit, or auto push occurred.
- Protected paths: confirm protected paths such as `jarvis.bat` were not touched or staged.
- Determinism: confirm no current clock, network, web, LLM/API, scheduler, crawler, DB, or live integration was added unless approved.
- Tests: verify each requested validation command with evidence; do not accept claims without command output.
- Git hygiene: check `git status --short`, `.git/index.lock`, staged diff, and unstaged/untracked files.
- Commit readiness: provide an opinion, but do not commit from this review prompt.

## Validation Commands

- `python -B -m py_compile apps\hermes-manager-pilot\run_demo.py apps\hermes-manager-pilot\run_smoke_tests.py apps\hermes-manager-pilot\hermes_manager_pilot\schemas.py apps\hermes-manager-pilot\hermes_manager_pilot\pipeline.py apps\hermes-manager-pilot\hermes_manager_pilot\prompt_renderer.py`
- `python -B apps\hermes-manager-pilot\run_smoke_tests.py`
- `python -B apps\research-council\run_smoke_tests.py`
- `python -B apps\daily-ai-radar\run_smoke_tests.py`
- `git diff --check`

## Required Review Output

- Findings first, ordered by severity.
- Explicitly state if no issues are found.
- List test gaps or skipped validation.
- Confirm protected path status.
- State whether a separate user-approved commit prompt is reasonable.
