# Jarvis Console v0.1 Checkpoint

Last updated: 2026-06-30

## Summary

Jarvis Console v0.1 is the current local browser shell, skill hub, and read-only operations dashboard for Jarvis.

It provides:

- A local-only browser UI at `http://127.0.0.1:8790/`.
- Chat / Command based skill suggestion.
- Suggested Skill Action Panel with copy-only commands and handoff guidance.
- Open Skill Details sync from a suggestion into the Skills tab.
- Skill Detail usage cards with commands, docs, safety notes, and non-goals.
- Tasks / Reports dashboard with read-only repo, skill, report, and checkpoint overview.
- Recent item grouping for tasks, reports, checkpoints, docs, examples, configs, and related metadata.

Jarvis Console does not execute skills automatically. It is a starting point and operations dashboard, not an autonomous runner.

## Current HEAD / Status

- HEAD: `bc5bde4`
- Commit: `jarvis-console: group read-only overview items`
- Baseline working tree before this checkpoint refresh: `?? jarvis.bat` only
- `jarvis.bat` remains untracked and protected
- This checkpoint document is intentionally updated after the baseline QA and should be the only tracked file changed by this task

## Connected Skills

### Hermes Manager

- Routes Codex work, repo review, commit prompt, and checkpoint management requests.
- Provides copy-only launch commands.
- Provides a local URL handoff to `http://127.0.0.1:8787/`.
- Verified end-to-end from Jarvis Console suggestion to Hermes Manager local handoff.

### Research Council

- Routes idea, MVP, business viability, market validation, manufacturing simulation idea, and startup review requests.
- Uses a local launcher flow.
- Suggested handoff tells the user to paste the idea, click `Idea 구체화`, then run the report.
- Verified end-to-end from Jarvis Console suggestion to Research Council handoff, detail card, self-test, smoke, and golden cases.

### Daily AI Radar

- Routes AI technology, MCP, Agent Skills, Hermes, OpenAI, Anthropic, LangGraph, and daily radar requests.
- Uses a copy-only report generation command.
- Suggested handoff tells the user to review Executive Summary, Candidate Highlights, and Governance Notes.
- Safety note states that radar recommendations are candidates, not implementation approval.
- Verified end-to-end from Jarvis Console suggestion to Daily AI Radar handoff, detail card, smoke, and demo report generation.

### Memory / Skills

- Planned skill for repeated workflow and skill candidate capture.
- Currently has no command.
- It appears in skill suggestion and detail surfaces as a planned capability.

### Tasks / Reports

- Read-only operations dashboard.
- Shows current repo status, skill status, recent tasks, recent reports, recent checkpoints, docs, examples, configs, safety notes, and discovery rules.
- No task creation, report generation, file mutation, or git write operation is exposed.

### Settings

- Placeholder for local-only settings and protected path visibility.
- Keeps the `jarvis.bat` protected-path convention visible.

## Verified Skill Suggestion Matrix

| Input | Expected skill | Verified result |
| --- | --- | --- |
| `Codex 커밋 리뷰 도와줘` | `hermes_manager` | `hermes_manager` |
| `간병 앱 아이디어 MVP 검증해줘` | `research_council` | `research_council` |
| `제조장비 시뮬레이션 아이디어 검증해줘` | `research_council` | `research_council` |
| `창업 아이디어 사업성 검토해줘` | `research_council` | `research_council` |
| `MCP Agent Skills 새 기술 찾아봐` | `daily_ai_radar` | `daily_ai_radar` |
| `Daily AI Radar 실행해줘` | `daily_ai_radar` | `daily_ai_radar` |
| `반복 작업 skill로 기억해줘` | `memory_skills` | `memory_skills` |
| `오늘 뭐하지` | `unknown` | `unknown` |

## Verified UI Flows

### Suggested Skill Action Panel

- Known skill suggestions show `Copy Git Bash`.
- Known skill suggestions show `Copy PowerShell`.
- Known skill suggestions show `Open Skill Details`.
- Hermes Manager shows `Open Local URL`.
- Research Council does not show `Open Local URL` because it has no local URL metadata.
- Daily AI Radar does not show `Open Local URL` because it has no local URL metadata.
- Unknown suggestions do not show action buttons.
- Commands are displayed as copy-only.
- The panel states that Jarvis Console does not run the skill.

### Open Skill Details Sync

- `Open Skill Details` switches to the Skills tab.
- The recommended skill card becomes selected.
- The detail panel shows the same recommended skill.
- Directly switching to the Skills tab after a known suggestion preserves the recommended selection.
- Unknown suggestions preserve the default/manual selection behavior.

### Skill Detail Usage Card

Hermes Manager, Research Council, and Daily AI Radar details were verified to include:

- What it does
- When to use
- Next action
- Commands
- Docs / Guides
- Safety notes
- Non-goals
- Selected skill state

### Tasks / Reports Dashboard

The Tasks / Reports tab was verified to show:

- Current Repo Status
- Skill Status
- Recent Tasks
- Recent Reports
- Recent Checkpoints
- Recent Docs / Examples
- Safety Notes
- Read-only Discovery Rules
- Refresh Overview
- Read-only badges on recent metadata items
- No file open, edit, or delete buttons

Recent items are grouped by section and normalized with deterministic metadata:

- `item_id`
- `title`
- `path`
- `source_area`
- `item_type`
- `summary`
- `modified_time`
- `size_bytes`
- `read_only: true`

## Read-only Discovery Rules

The overview discovery remains intentionally constrained:

- Safe directory allowlist only.
- Repo-relative paths only.
- No absolute paths in item metadata.
- No `..` path segments.
- No backslash paths.
- Extension allowlist: `.md`, `.json`, `.txt`.
- Hidden files and directories are excluded.
- `.git` is excluded.
- `__pycache__` is excluded.
- Secrets-like filenames are excluded.
- Directory item limit is preserved.
- Overall item limit is preserved.
- Only prefix/snippet content is read for summaries.
- Symlink allowed-root boundary is enforced.
- All discovered items are marked `read_only: true`.

## Safety Boundary

Jarvis Console v0.1 maintains these boundaries:

- Local-only bind on `127.0.0.1`.
- No automatic Codex invocation.
- No automatic ChatGPT invocation.
- No automatic Hermes invocation.
- No automatic Research Council execution.
- No automatic Daily AI Radar execution.
- No command auto-execution.
- Commands are copy-only.
- No `git add`.
- No `git commit`.
- No `git push`.
- No repo write from the dashboard.
- No task mutation.
- No report generation from Jarvis Console.
- No external network, API, or LLM call.
- `Open Local URL` only accepts `http://127.0.0.1`.
- `window.open` uses `noopener,noreferrer`.
- `jarvis.bat` remains protected and untracked.

## Final Baseline QA Results

Server and API checks passed:

- `/` returned 200 OK.
- `/api/status` returned OK.
- `/api/overview` returned grouped read-only overview metadata.
- `/api/suggest-skill` returned the expected routing matrix.
- `/api/skill?skill_id=hermes_manager` returned the Hermes Manager detail payload.

Manual browser checks passed:

- Suggested Skill Action Panel rendered correctly for Hermes Manager, Research Council, and Daily AI Radar.
- Unknown suggestion rendered without action buttons.
- Open Skill Details sync worked for the selected skill.
- Skill Detail usage cards showed all required sections.
- Tasks / Reports grouped dashboard rendered read-only recent item cards.
- No open, edit, or delete buttons were present in the Tasks / Reports dashboard.

Regression commands passed:

- `python -B apps\jarvis-console\run_web_app.py --self-test`
- `python -B apps\jarvis-console\run_smoke_tests.py`
- `python -B apps\hermes-manager-pilot\run_smoke_tests.py`
- `python -B apps\research-council\run_smoke_tests.py`
- `python -B apps\daily-ai-radar\run_smoke_tests.py`
- `node --check apps\jarvis-console\web\app.js`
- `git diff --check`

The Jarvis Console test server was stopped after QA, and no `127.0.0.1:8790` listener remained.

## Current UX Backlog

- Planned skill UX: Memory / Skills has no command yet, so the no-command state can be made clearer.
- Report template type split: sample reports and report templates may deserve separate item types.
- Recent item grouping: grouping can become more precise as more task/report/checkpoint indexes appear.
- Skill Detail visual polish: usage cards can be made easier to scan without changing behavior.
- Future Jarvis Console integration phases: add deeper handoffs once the safety boundary for each target skill is explicit.

## Recommended Next Development Candidates

### A. Planned Skill UX Polish

Priority: P1

Clarify planned skills that have no command yet. Show a first-class `No command yet` state and avoid generic handoff steps for planned-only capabilities.

### B. Report Template Type Split

Priority: P1

Separate generated reports, sample reports, and report templates so Recent Reports reads less like a mixed file inventory.

### C. Recent Item Grouping Refinement

Priority: P2

Improve source-area and item-type inference as real task, report, and checkpoint indexes become available.

### D. Skill Detail Visual Polish

Priority: P2

Improve the visual hierarchy of detail cards, command blocks, docs, safety notes, and non-goals while preserving copy-only behavior.

### E. Jarvis Console Checkpoint / History View

Priority: P2

Expose checkpoint docs and operational history as a dedicated read-only view.

### F. Research Council Report Summary Integration

Priority: P3

Show recent Research Council report summaries in Jarvis Console once a safe read-only report index exists.

### G. Daily AI Radar Report Viewer

Priority: P3

Show recent radar reports in a read-only viewer with Executive Summary, Candidate Highlights, and Governance Notes sections.

### H. Hermes Manager Result / Checkpoint Handoff

Priority: P3

Add a read-only handoff from Hermes Manager summaries or checkpoints into the Jarvis Console dashboard after the artifact boundary is stable.

## Non-goals

Jarvis Console v0.1 is not intended to provide:

- Automatic skill execution.
- Automatic Codex execution.
- Automatic ChatGPT execution.
- Automatic Hermes execution.
- Automatic Research Council or Daily AI Radar execution.
- Automatic commits.
- Automatic pushes.
- External API or LLM calls.
- Skill auto-installation.
- Background autonomous execution.
- Dashboard-driven repo mutation.
