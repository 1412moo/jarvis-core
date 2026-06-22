# Codex Commit Prompt

This is a Hermes Manager Pilot conservative commit boundary.

## Commit Authorization

- Commit is allowed by session state: no
- Do not commit.
- Reason: `commit_allowed` is false.
- Human approval required: yes
- Human approval granted: no
- Push is allowed by session state: no
- Do not push.

## Required Before Any Future Commit Prompt

- User must explicitly approve a commit task.
- Validation commands must be run.
- `git status --short` must be checked.
- `.git/index.lock` absence must be confirmed.
- Only intended files may be staged.
- Protected paths must remain excluded.
- `git diff --cached --stat` and `git diff --cached --check` must pass.

## Protected Paths

- `jarvis.bat`

## Validation Commands

- `python -B -m py_compile apps\hermes-manager-pilot\run_demo.py apps\hermes-manager-pilot\run_smoke_tests.py apps\hermes-manager-pilot\hermes_manager_pilot\schemas.py apps\hermes-manager-pilot\hermes_manager_pilot\pipeline.py apps\hermes-manager-pilot\hermes_manager_pilot\prompt_renderer.py`
- `python -B apps\hermes-manager-pilot\run_smoke_tests.py`
- `python -B apps\research-council\run_smoke_tests.py`
- `python -B apps\daily-ai-radar\run_smoke_tests.py`
- `git diff --check`
