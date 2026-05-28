# AI Handoff: Research Council

Use this note as a starting point for future AI-assisted sessions. Do not rely
on memory from earlier chats; inspect the repository state, read the governance
docs, and verify behavior from the current checkout.

## Repository

- Workspace root: `C:\work`
- Git repository: `C:\work\jarvis-core`
- Active app: `apps\research-council`
- Last known branch: `feature/research-council-domain-profiles`
- Last known stable commit: `87e75b41b96fea5c8ab0daa96b207f973c691cd1`

## Recently Completed

Commit `87e75b41b96fea5c8ab0daa96b207f973c691cd1` added the governance replay
CLI and smoke coverage:

- `apps\research-council\run_governance_replay.py`
- `apps\research-council\run_smoke_tests.py`

The replay CLI compares either the latest two benchmark history entries with
`--history` or explicit snapshots with `--before` and `--after`. It validates
expected summary and hash metadata with stable exit codes:

- `0`: successful metadata match.
- `1`: valid comparison mismatch.
- `2`: usage, malformed input, missing file, or insufficient history.

Replay output must remain bounded and metadata-only. It must not echo raw
expected CLI input, local paths, fixture internals, scenario content, benchmark
body text, golden-case text, mutation text, or user-provided idea material.

## Core Constraints

- Preserve deterministic behavior.
- Preserve metadata-only governance.
- Preserve append-only governance contract evolution.
- Preserve summary, hash, schema, and output stability.
- Do not store or print raw benchmark, golden, mutation, scenario, or
  user-provided input text.
- Do not expose raw idea, goal, input data, scenario IDs, fixture internals,
  local paths, or other raw test material in governance replay output.
- Do not add DB, API, UI, async worker, or new orchestration infrastructure
  unless explicitly requested.
- Prefer small, reviewable changes.

## Inspect First

- `README.md`
- `apps\research-council\README.md`
- `apps\research-council\governance.md`
- `apps\research-council\contracts\research-council-mvp.md`
- `apps\research-council\run_smoke_tests.py`
- `apps\research-council\run_golden_cases.py`
- `apps\research-council\run_governance_replay.py`

## Standard Verification

Run these before and after behavior changes:

```powershell
python -B apps\research-council\run_smoke_tests.py
python -B apps\research-council\run_golden_cases.py
```

For docs-only changes, tests may be skipped when no product behavior or app code
changed.

## Safe New-Session Workflow

1. Inspect current repository state before making assumptions:

   ```powershell
   cd C:\work\jarvis-core
   git status --short
   git branch --show-current
   git log --oneline -5
   git show --stat --oneline 87e75b41b96fea5c8ab0daa96b207f973c691cd1
   ```

2. Read the governance and contract docs listed in `Inspect First`.
3. Use read-only Git inspection before changing files:

   ```powershell
   git diff
   git diff --stat
   git diff --name-status
   ```

4. Keep the next change scoped to the user request. For Research Council,
   prefer metadata-only, deterministic, test-locked changes.
5. Run the standard smoke and golden commands for behavior or app-code changes.
   For docs-only changes, record that tests were skipped because no behavior
   changed.

## Patch Backups

Root patch backups may exist at:

- `C:\work\research-council-pending.patch`
- `C:\work\research-council-pending-with-untracked.patch`

Do not apply these files unless the user explicitly instructs it after
read-only inspection. At the last checkpoint, they appeared to be stale or
already-reflected broad backup bundles, and neither mentioned
`run_governance_replay.py`.

## Decision Rule

If a proposed change risks raw input leakage, nondeterminism, unstable output
contracts, hidden writes, path leakage in replay output, or broad orchestration
expansion, stop and narrow the change.

When unsure, prefer deterministic, metadata-only, test-locked behavior.
