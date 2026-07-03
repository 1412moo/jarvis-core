# Jarvis Console v0.1 Checkpoint

Last updated: 2026-07-03

## Summary

Jarvis Console v0.1 is the current local browser shell, skill hub, read-only operations dashboard, read-only checkpoint/history view, and text-only Voice Inbox for Jarvis.

It provides:

- A local-only browser UI at `http://127.0.0.1:8790/`.
- Chat / Command skill suggestion from the read-only skill registry.
- Suggested Skill Action Panel with copy-only commands and handoff guidance.
- Open Skill Details sync from a suggestion into the Skills tab.
- Skill Detail usage cards with commands, docs, safety notes, and non-goals.
- Tasks / Reports dashboard with read-only repo, skill, report, checkpoint, docs, and example metadata.
- Recent item grouping for tasks, reports, checkpoints, docs, examples, configs, and related metadata.
- Checkpoints / History view with recent commits, checkpoint docs, related reports/examples, and read-only history discovery rules.
- Voice Inbox v0.1 for turning pasted voice-like transcripts or rough thoughts into task candidates and manual skill handoffs.

Jarvis Console does not execute skills automatically. It suggests, prepares, and displays handoffs; it is a starting point and operations dashboard, not an autonomous runner.

## Current HEAD / Status

- HEAD: `199672b`
- Commit: `jarvis-console: polish voice inbox task capture`
- Expected working tree after this checkpoint update: this document modified, plus `?? jarvis.bat`
- `jarvis.bat` remains untracked and protected

## Current Capabilities

### Chat / Command Skill Suggestion

- Deterministic keyword routing suggests a skill from the local registry.
- Known suggestions include Hermes Manager, Research Council, Daily AI Radar, and Memory / Skills.
- Unknown suggestions stay manual and do not create action buttons.

### Suggested Skill Action Panel

- Known suggestions show the recommended skill, recommendation reason, next action, 3-step handoff, commands, and safety notes.
- Buttons are limited to:
  - `Copy Git Bash`
  - `Copy PowerShell`
  - `Open Local URL`, only when a safe local URL exists
  - `Open Skill Details`
- Commands are copy-only and use clipboard copy.
- Jarvis Console does not run the recommended skill.

### Voice Inbox v0.1

Voice Inbox is a text-only capture surface for pasted voice-like transcripts, OS dictation text, user-provided transcript text, or rough thoughts.

It intentionally does not record audio or call any STT/TTS/LLM service. The user pastes text, then Jarvis Console prepares a local task candidate.

Voice Inbox produces:

- Raw transcript preview
- Cleaned transcript
- Task candidate title and summary
- Suggested skill
- Confidence
- Matched keywords
- `needs_confirmation`
- Next action
- Safety notes
- Manual handoff buttons when a known skill is suggested

Voice Inbox handoff actions are limited to:

- `Open Skill Details`
- `Copy Cleaned Task`
- `Copy As Jarvis Command`
- `Copy Git Bash`
- `Copy PowerShell`
- `Open Local URL`, only when the suggested skill has a safe `http://127.0.0.1` local URL

Voice Inbox does not run Codex, ChatGPT, Hermes Manager, Research Council, Daily AI Radar, git, shell commands, or external tools. It remains approval-oriented and local-only.

Recent Voice Inbox UX polish:

- `Copy As Jarvis Command` avoids duplicate `Jarvis` prefixes.
- Already-prefixed text such as `Jarvis, CareNote...` does not become `Jarvis, Jarvis, CareNote...`.
- Unprefixed text such as `CareNote...` receives exactly one `Jarvis, ` prefix.
- Korean/English Jarvis-like prefixes are handled conservatively.
- `리뷰 -> review` cleanup is limited to development/Codex-related contexts.
- Everyday review phrases remain conservative and unknown:
  - `고깃집 리뷰 정리해줘`
  - `영화 리뷰 정리해줘`
  - `영화 리뷰 수정해줘`
  - `프리뷰 화면 확인`
- Unknown candidates show guidance for expressions that route to Research Council, Hermes Manager, Daily AI Radar, or Memory / Skills.
- Unknown guidance does not show automatic execution affordances.

### Skill Detail Usage Cards

Skill details are rendered from the read-only registry and include:

- What it does
- When to use
- Next action
- Commands
- Docs / Guides
- Safety notes
- Non-goals
- Selected skill state

### Tasks / Reports Read-only Dashboard

The Tasks / Reports tab shows:

- Current Repo Status
- Skill Status
- Recent Tasks
- Recent Reports
- Recent Checkpoints
- Recent Docs / Examples
- Safety Notes
- Read-only Discovery Rules
- Refresh Overview

Recent items are normalized with deterministic read-only metadata:

- `item_id`
- `title`
- `path`
- `source_area`
- `item_type`
- `summary`
- `modified_time`
- `size_bytes`
- `read_only: true`

### Checkpoints / History Read-only View

The Checkpoints / History tab shows:

- Current Repo Status
- Recent Commits
- Checkpoint Docs
- Related Reports / Examples
- Safety Notes
- Read-only History Discovery
- Refresh History

The `/api/history` endpoint returns read-only metadata only:

- `repo`: branch, HEAD, short HEAD, working tree status, protected path note
- `recent_commits`: commit hash and subject from `git log --oneline -n 10`
- `checkpoint_docs`: checkpoint/summary metadata from allowlisted local paths
- `related_items`: report/example metadata from allowlisted local paths
- `notes`: read-only and no-mutation safety notes
- `discovery`: safe directories, extension allowlist, name markers, limits, and excludes

History rendering escapes commit subjects, file titles, summaries, paths, and metadata before insertion into the page. The view has no open, edit, delete, commit, or push buttons.

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

## Verified Voice Inbox Routing Matrix

| Transcript | Expected skill | Verified result |
| --- | --- | --- |
| `Jarvis, CareNote 복약 기록 UX 리스크를 Research Council로 검증해줘` | `research_council` | `research_council` |
| `코덱스한테 README 수정하고 커밋 리뷰 프롬프트 만들어줘` | `hermes_manager` | `hermes_manager` |
| `MCP Agent Skills 새 기술 Daily Radar로 확인해줘` | `daily_ai_radar` | `daily_ai_radar` |
| `이 반복 작업 skill 후보로 기억해줘` | `memory_skills` | `memory_skills` |
| `오늘 뭐하지` | `unknown` | `unknown` |
| `고깃집 리뷰 정리해줘` | `unknown` | `unknown` |
| `영화 리뷰 정리해줘` | `unknown` | `unknown` |
| `영화 리뷰 수정해줘` | `unknown` | `unknown` |
| `프리뷰 화면 확인` | `unknown` | `unknown` |
| `report review draft` | `unknown` | `unknown` |

## Verified Core Flows

### Voice Inbox Task Capture

- The user pastes a transcript or rough thought into Voice Inbox.
- `Prepare Task Candidate` calls `/api/voice-inbox/prepare`.
- The API applies deterministic cleanup and conservative term correction.
- The cleaned transcript is routed through the existing skill suggestion logic.
- The result card shows raw preview, cleaned transcript, task candidate title/summary, suggested skill, confidence, matched keywords, next action, and safety notes.
- Known suggestions show copy-only handoff buttons.
- Unknown suggestions show guidance and no skill handoff action buttons.
- `Copy Cleaned Task` copies only the cleaned transcript.
- `Copy As Jarvis Command` copies a Jarvis command without duplicating a leading `Jarvis` or `자비스` prefix.
- `Open Skill Details` only changes the UI selection and does not run the skill.
- Browser QA verified prefix handling and unknown guidance.

### Hermes Manager Handoff

- Chat / Command suggests Hermes Manager for Codex review and commit workflow requests.
- Suggested Action Panel shows copy-only Git Bash and PowerShell commands.
- Hermes Manager is the only connected skill with `Open Local URL`.
- Opening the local URL does not start the server.
- Open Skill Details sync selects Hermes Manager in the Skills tab.

### Research Council Handoff

- Chat / Command suggests Research Council for idea, MVP, business viability, market validation, and manufacturing simulation idea requests.
- Suggested Action Panel shows copy-only commands.
- Step 3 is launcher-specific: paste the idea, click `Idea 구체화`, then run the report.
- Research Council has no Open Local URL button.
- Open Skill Details sync selects Research Council in the Skills tab.

### Daily AI Radar Handoff

- Chat / Command suggests Daily AI Radar for AI technology, MCP, Agent Skills, Hermes, LangGraph, and radar requests.
- Suggested Action Panel shows copy-only commands.
- Step 3 tells the user to review Executive Summary, Candidate Highlights, and Governance Notes.
- The action panel states that radar recommendations are candidates, not implementation approval.
- Daily AI Radar has no Open Local URL button.

### Tasks / Reports Overview

- Refresh Overview calls `/api/overview`.
- Recent items are grouped into tasks, reports, checkpoints, and docs/examples.
- Cards show type badge, source area badge, repo-relative path, summary, size/time metadata, and read-only badge.
- No file open, edit, or delete buttons are present.

### History View

- Refresh History calls `/api/history`.
- Recent commits are shown from read-only `git log --oneline -n 10`.
- Checkpoint docs include `docs/jarvis-console-v0.1-checkpoint.md`.
- Related reports/examples are shown as metadata only.
- Read-only History Discovery explains safe directories, name markers, extension limits, and excludes.
- No open, edit, delete, commit, or push buttons are present.

## Read-only Discovery Rules

Overview and history discovery remain intentionally constrained:

- Safe directory allowlist only.
- Repo-relative paths only.
- No absolute paths in item metadata.
- No `..` path segments.
- No backslash paths.
- No Windows drive paths.
- Extension allowlist: `.md`, `.json`, `.txt`.
- Hidden files and directories are excluded.
- `.git` is excluded.
- `__pycache__` is excluded.
- Secrets-like filenames are excluded.
- Directory item limit is preserved.
- Overall item limit is preserved.
- Only prefix/snippet content is read for titles and summaries.
- Symlink allowed-root boundary is enforced.
- All discovered items are marked `read_only: true`.

History-specific discovery adds:

- Safe directories:
  - `docs`
  - `apps/jarvis-console`
  - `apps/hermes-manager-pilot/examples`
  - `apps/daily-ai-radar/examples`
- Name markers:
  - `checkpoint`
  - `summary`
  - `report`
- Recent commits limit: 10

## Safety Boundary

Jarvis Console v0.1 maintains these boundaries:

- Local-first operation.
- Human-approved handoffs.
- Skill-based orchestration.
- Local-only bind on `127.0.0.1`.
- No automatic Codex invocation.
- No automatic ChatGPT invocation.
- No automatic Hermes invocation.
- No automatic Research Council execution.
- No automatic Daily AI Radar execution.
- No automatic skill execution from Voice Inbox.
- No microphone access.
- No audio recording runtime.
- No STT runtime.
- No Whisper invocation.
- No TTS runtime.
- No Qwen invocation.
- No Claude Code hook integration.
- No command auto-execution.
- Commands are copy-only.
- No `git add`.
- No `git commit`.
- No `git push`.
- No `git checkout`.
- No `git reset`.
- No `git clean`.
- No `git rm`.
- No `git stash`.
- No `git tag`.
- No `git merge`.
- No `git rebase`.
- Read-only git status/log only.
- No autonomous code modification.
- No repo write from dashboards.
- No repo/file write behavior from Voice Inbox.
- No task mutation.
- No checkpoint generation.
- No report generation from Jarvis Console.
- No external network, API, or LLM call.
- No external API/web/LLM call by default.
- No external CDN or remote script dependency.
- `Open Local URL` only accepts `http://127.0.0.1`.
- `window.open` uses `noopener,noreferrer`.
- `jarvis.bat` remains protected and untracked.

Allowed read-only git commands:

- `git rev-parse --show-toplevel`
- `git rev-parse --abbrev-ref HEAD`
- `git rev-parse HEAD`
- `git status --short`
- `git log --oneline -n 10`

## Baseline QA Results

Server and API checks passed:

- `/` returned 200 OK.
- `/api/status` returned OK.
- `/api/overview` returned grouped read-only overview metadata.
- `/api/history` returned grouped read-only history metadata.
- `/api/suggest-skill` returned the expected routing matrix.
- `/api/skill?skill_id=hermes_manager` returned the Hermes Manager detail payload.

Manual browser checks passed:

- Suggested Skill Action Panel rendered correctly for Hermes Manager, Research Council, and Daily AI Radar.
- Unknown suggestion rendered without action buttons.
- Open Skill Details sync worked for the selected skill.
- Skill Detail usage cards showed all required sections.
- Tasks / Reports grouped dashboard rendered read-only recent item cards.
- Checkpoints / History rendered Recent Commits, Checkpoint Docs, Related Reports / Examples, Safety Notes, and Read-only History Discovery.
- No open, edit, delete, commit, or push buttons were present in read-only dashboards.
- Unsafe-looking HTML-like text is rendered through escaped/text-safe paths, not as executable HTML.

Regression commands passed:

- `python -B -m py_compile apps\jarvis-console\run_web_app.py apps\jarvis-console\run_smoke_tests.py`
- `python -B apps\jarvis-console\run_web_app.py --self-test`
- `python -B apps\jarvis-console\run_smoke_tests.py`
- `python -B apps\hermes-manager-pilot\run_smoke_tests.py`
- `python -B apps\research-council\run_smoke_tests.py`
- `python -B apps\daily-ai-radar\run_smoke_tests.py`
- `node --check apps\jarvis-console\web\app.js`
- `git diff --check`

Voice Inbox browser QA passed:

- `Copy As Jarvis Command` does not duplicate an existing `Jarvis` prefix.
- Unprefixed candidate text receives one `Jarvis, ` prefix.
- Unknown guidance appears for unmatched candidates.
- Unknown guidance does not display automatic execution affordances.

The Jarvis Console test server was stopped after QA, and no `127.0.0.1:8790` listener remained.

During QA, `jarvis.bat` remained untracked and untouched.

## Current Known Backlog

- Planned skill UX polish: Memory / Skills has no command yet, so the no-command state can be clearer.
- Template vs report item type separation: sample reports, generated reports, and report templates may deserve separate item types.
- Tasks / Reports grouping refinement: grouping can become more precise as real task/report/checkpoint indexes appear.
- History/checkpoint index refinement: a structured checkpoint index would make history grouping more intentional than filename markers alone.
- Memory / Skills v0.1: repeated workflow capture can become a first-class proposal surface.
- Daily AI Radar real source collection later, approval-gated.
- Hermes/Codex automation later, approval-gated.
- Skill Detail visual polish: usage cards can become easier to scan without changing behavior.
- Voice Inbox guidance can eventually be driven by registry metadata instead of static copy.
- Voice Inbox can later integrate optional STT only behind explicit approval and a separate safety boundary.

## Recommended Next Development Candidates

### A. Planned Skill UX Polish

Priority: P1

Clarify planned skills that have no command yet. Show a first-class `No command yet` state and avoid generic handoff steps for planned-only capabilities.

### B. Template vs Report Item Type Separation

Priority: P1

Separate generated reports, sample reports, and report templates so Recent Reports and History views read less like mixed file inventories.

### C. History / Checkpoint Index Refinement

Priority: P2

Introduce a read-only checkpoint index once checkpoint metadata becomes stable. Keep discovery read-only and approval-gated.

### D. Tasks / Reports Grouping Refinement

Priority: P2

Improve source-area and item-type inference as real task, report, and checkpoint indexes become available.

### E. Memory / Skills v0.1

Priority: P2

Turn repeated workflow capture into a clearer proposal workflow without installing or modifying skills automatically.

### F. Skill Detail Visual Polish

Priority: P2

Improve the visual hierarchy of detail cards, command blocks, docs, safety notes, and non-goals while preserving copy-only behavior.

### G. Voice Inbox Refinement

Priority: P2

Move unknown guidance and handoff examples toward registry-backed metadata while keeping Voice Inbox text-only, local-first, and approval-oriented.

### H. Daily AI Radar Source Collection

Priority: P3

Add real source collection later only behind explicit user approval and a clear external-network boundary.

### I. Hermes / Codex Automation

Priority: P3

Consider deeper Hermes/Codex handoffs later only behind explicit approval and with no automatic commit/push behavior.

## Non-goals

Jarvis Console v0.1 is not intended to provide:

- Automatic skill execution.
- Automatic Codex execution.
- Automatic ChatGPT execution.
- Automatic Hermes execution.
- Automatic Research Council or Daily AI Radar execution.
- Automatic commits.
- Automatic pushes.
- External connectors.
- External API or LLM calls.
- Microphone recording.
- STT or TTS runtime.
- Skill auto-installation.
- Background autonomous behavior.
- Dashboard-driven repo mutation.
