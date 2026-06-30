# Jarvis Console v0.1 Baseline Checkpoint

Date: 2026-06-30

## 1. Summary

Jarvis Console v0.1 now works as a local browser shell, skill hub, and
read-only operations dashboard for Jarvis-Core.

The console provides:

- Chat / Command input for deterministic skill suggestion.
- Suggested Skill Action Panel for copy-only handoff guidance.
- Skill Detail cards with usage guidance, commands, docs, safety notes, and
  non-goals.
- Tasks / Reports dashboard for read-only repo, skill, report, and checkpoint
  visibility.

Jarvis Console v0.1 is not an autonomous execution engine. It is a local,
human-facing coordination surface for choosing the right bounded workflow and
making the next manual step clear.

## 2. Current HEAD / Status

- HEAD: `e53d109`
- Commit: `jarvis-console: add read-only operations dashboard`
- Baseline QA status: passed
- Working tree at checkpoint: `?? jarvis.bat` only
- `jarvis.bat` status: untracked and protected

`jarvis.bat` must remain unstaged, unmodified, and outside Jarvis Console
automation.

## 3. Connected Skills

### Hermes Manager

- Purpose: Codex task, review, commit prompt, and checkpoint workflow
  management.
- Handoff: copy command, run Hermes Manager manually, then open its local URL.
- Local URL: `http://127.0.0.1:8787/`
- Status: E2E verified from Jarvis Console.

### Research Council

- Purpose: idea, MVP, business viability, and validation request routing.
- Handoff: copy command, run the launcher manually, paste the idea, use
  `Idea 구체화`, then run the report.
- Status: E2E verified from Jarvis Console.

### Daily AI Radar

- Purpose: AI technology, MCP, Agent Skills, Hermes, OpenAI, Anthropic, and
  LangGraph trend scouting.
- Handoff: copy command, run the radar renderer manually, then review the
  generated report.
- Safety note: radar recommendations are candidates, not implementation
  approval.
- Status: E2E verified from Jarvis Console.

### Memory / Skills

- Purpose: planned skill candidate and repeated workflow memory surface.
- Status: planned skill.
- Command status: no command registered.
- Current use: route repeated-workflow intent to a proposal-only skill
  candidate workflow.

### Tasks / Reports

- Purpose: read-only operations dashboard for repo status, skill status, recent
  tasks, reports/examples, checkpoints, and discovery rules.
- Mutation status: no task creation, report generation, file mutation, git
  staging, commit, or push.

### Settings

- Purpose: local-only and protected path visibility, plus future settings
  placeholder.
- Current status: informational placeholder.

## 4. Verified Skill Suggestion Matrix

| Input | Expected skill | Result |
| --- | --- | --- |
| `Codex 커밋 리뷰 도와줘` | `hermes_manager` | Passed |
| `간병 앱 아이디어 MVP 검증해줘` | `research_council` | Passed |
| `제조장비 시뮬레이션 아이디어 검증해줘` | `research_council` | Passed |
| `MCP Agent Skills 새 기술 찾아봐` | `daily_ai_radar` | Passed |
| `반복 작업 skill로 기억해줘` | `memory_skills` | Passed |
| `오늘 뭐하지` | `unknown` | Passed |

## 5. Verified UI Flows

### Suggested Skill Action Panel

Verified for Hermes Manager, Research Council, Daily AI Radar, and
Memory / Skills.

Known available skills show:

- Recommended skill display name.
- Recommendation reason.
- Next action.
- Three-step handoff guidance.
- Safety text stating that Jarvis Console does not run the skill.
- Copy-only command behavior where commands exist.

Memory / Skills is a planned skill and has no command registered, so the panel
shows `No command yet` and does not provide command copy buttons.

### Action Buttons

Verified:

- `Copy Git Bash`
- `Copy PowerShell`
- `Open Skill Details`
- `Open Local URL` for Hermes Manager only

`Open Local URL` is shown only when the skill registry provides a local
`http://127.0.0.1` URL.

### Skill Detail

Verified for:

- Research Council
- Daily AI Radar
- Hermes Manager

Each detail view shows:

- What it does
- When to use
- Next action
- Commands
- Docs / Guides
- Safety notes
- Non-goals
- Selected skill state

### Tasks / Reports Refresh Overview

Verified dashboard sections:

- Current Repo Status
- Skill Status
- Recent Tasks
- Recent Reports / Examples
- Checkpoints
- Safety Notes
- Read-only Discovery Rules

The dashboard clearly states that it is read-only and that `jarvis.bat` remains
protected.

## 6. Safety Boundary

Jarvis Console v0.1 maintains the following safety boundary:

- Local-only server bind: `127.0.0.1`.
- No automatic Codex invocation.
- No automatic ChatGPT invocation.
- No automatic Hermes invocation.
- No automatic Research Council execution.
- No automatic Daily AI Radar execution.
- Commands are copy-only.
- No command auto-execution.
- No `git add`.
- No `git commit`.
- No `git push`.
- No repo write from Jarvis Console dashboard or skill suggestion flows.
- No external network/API/LLM calls.
- `Open Local URL` only allows `http://127.0.0.1`.
- `window.open` uses `noopener,noreferrer`.
- `jarvis.bat` remains protected and untracked.

## 7. Baseline QA Results

Baseline QA completed successfully.

Verified:

- Jarvis Console `/` returns 200 OK.
- `/api/status` returns local-only status.
- `/api/overview` returns read-only overview data.
- Jarvis Console self-test passed.
- Jarvis Console smoke tests passed.
- Hermes Manager smoke tests passed.
- Research Council smoke tests passed.
- Daily AI Radar smoke tests passed.
- `node --check apps/jarvis-console/web/app.js` passed.
- Manual browser verification completed with the in-app browser.
- Test server was stopped.
- No listener remained on `127.0.0.1:8790`.

## 8. UX Backlog

- Memory / Skills is a planned skill and has no command. The `No command yet`
  state could be made more explicit in the action panel.
- Planned skill handoff Step 3 can feel awkward when no command exists.
- Skill Detail cards can be visually refined for scanning and repeated use.
- Tasks / Reports recent item grouping can be improved, especially when
  reports, examples, docs, and console files appear in the same list.

## 9. Recommended Next Development Candidates

| Priority | Candidate | Description |
| --- | --- | --- |
| P1 | Planned skill UX polish | Clarify `No command yet` and planned-skill handoff states so Memory / Skills feels intentional rather than incomplete. |
| P1 | Tasks / Reports dashboard recent item grouping | Group recent items by source and type so tasks, reports, examples, docs, and checkpoints are easier to scan. |
| P2 | Jarvis Console checkpoint/history view | Add a read-only view of prior checkpoints and QA milestones. |
| P2 | Hermes Manager result/checkpoint handoff into Jarvis Console | Surface Hermes checkpoint summaries in Jarvis Console without automatic execution or mutation. |
| P3 | Research Council report summary integration | Show existing Research Council report summaries as read-only context in Jarvis Console. |
| P3 | Daily AI Radar report viewer | Show generated radar reports in a read-only viewer with clear candidate/not-approval language. |

## 10. Non-goals

Jarvis Console v0.1 does not provide:

- Automatic execution.
- Automatic commits.
- Automatic pushes.
- External API calls.
- External LLM calls.
- Automatic skill installation.
- Background autonomous execution.
- Autonomous repo mutation.
- Replacement for Codex, Hermes Manager, Research Council, or Daily AI Radar.
