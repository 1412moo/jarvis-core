# Read-Only Dashboard MVP

## 1. Purpose

This document defines the minimum contract for a local read-only dashboard that shows `memory/tasks/*.md` in a browser.

The dashboard exists only to inspect current task records more easily. The source of truth remains the Markdown task files under `memory/tasks/`.

## 2. Non-Goals

- No task creation.
- No task editing.
- No task deletion.
- No `/approve`, `/run`, or `/retry` buttons.
- No execution trigger.
- No execution/status transition layer expansion.
- No database.
- No authentication.
- No network/public deploy scope.
- No changes to existing Discord command behavior.

## 3. MVP Screens

- Task list.
- Status count summary.
- Recently updated task list, sorted by `updated_at`.
- Single task detail view.
- Optional execution metadata display when existing metadata is present in the task file.

## 4. Data Source

- Read task records from `memory/tasks/*.md`.
- Keep the existing task metadata contract:
  - `id`
  - `title`
  - `status`
  - `repo`
  - `created_at`
  - `updated_at`
  - `summary`
- Optional execution metadata may be displayed only when it already exists in the task file.
- The dashboard must not write, create, rename, move, or delete task files.

## 5. Implementation Candidate

- Add a single local server file later: `adapters/web/dashboard.py`.
- Prefer Python standard library for the initial MVP.
- Avoid adding a UI framework, package manager, database, or new dependency.
- Avoid directly importing `adapters/discord/bot_minimal.py` in the initial MVP because it also contains Discord, approve, run, retry, and execution-related code.
- If parsing needs to be shared later, consider a separate read-only task reader as a future refactor, not as part of the first MVP.

## 6. Safety Principles

- Read-only only.
- Localhost first.
- No write endpoints.
- No execution endpoints.
- No approve/run/retry controls.
- No task status transition behavior.
- No mutation of `memory/tasks/*.md`.
- No change to Discord command routing or behavior.

## 7. Verification

- Review this document before implementation.
- When implementation starts, verify the dashboard separately from Discord smoke/self-check flows.
- Keep existing smoke/self-check commands stable:
  - `python -B orchestrator\discord-intake\run_smoke_tests.py`
  - Discord adapter self-check commands as applicable.

## 8. Next Step

After this contract is accepted, plan the minimal `adapters/web/dashboard.py` implementation separately.

