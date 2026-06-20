# Codex Implementation Prompt

This is a Hermes Manager Pilot v0.2 draft. It is not an automatic Codex invocation.

## Session

- Repo: `C:\work\jarvis-core`
- Branch: `main`
- Expected HEAD: `8bc6b12`
- Working tree status: Sample fixture only. The expected pre-existing untracked file is jarvis.bat, and it must remain untouched.
- Next action: `PROMPT_FOR_CODEX`

## Goal

- Current goal: Implement Hermes Manager Pilot v0.2 as a local deterministic session and prompt renderer.
- Active task: Add local JSON validation, Codex prompt renderers, checkpoint summary renderer, sample fixtures, and smoke tests.
- Blocked by: none

## Scope

- `apps/hermes-manager-pilot/`

## Protected Paths

- `jarvis.bat`

## Guardrails

- Do not modify protected paths.
- Do not modify unrelated files.
- Do not commit unless the user explicitly provides a commit prompt.
- Do not push.
- Do not use web, network, API, or LLM calls unless explicitly approved.
- Do not add scheduler, crawler, database, Discord command, or live Hermes/MCP/A2A integration.
- Treat Daily AI Radar and Research Council handoffs as proposals, not automatic tasks.
- Do not store secrets, credentials, tokens, private messages, or hidden reasoning.

## Validation Commands

- `python -B -m py_compile apps\hermes-manager-pilot\run_demo.py apps\hermes-manager-pilot\run_smoke_tests.py apps\hermes-manager-pilot\hermes_manager_pilot\schemas.py apps\hermes-manager-pilot\hermes_manager_pilot\pipeline.py apps\hermes-manager-pilot\hermes_manager_pilot\prompt_renderer.py`
- `python -B apps\hermes-manager-pilot\run_smoke_tests.py`
- `python -B apps\research-council\run_smoke_tests.py`
- `python -B apps\daily-ai-radar\run_smoke_tests.py`
- `git diff --check`

## Final Report Requirements

- Summarize implementation scope.
- List changed files.
- Report validation commands and results.
- Report risks and non-goals.
- Report working tree status.
- Confirm protected paths were not touched.
- Do not create a commit unless the user separately asks for commit work.
