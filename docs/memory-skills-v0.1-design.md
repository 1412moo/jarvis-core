# Memory / Skills v0.1 Design

Last updated: 2026-07-03

## 1. Purpose

Memory / Skills v0.1 defines a safe inbox for repeated workflow candidates.
It is a place where Jarvis can help turn a repeated task, prompt pattern,
operating rule, or skill idea into a human-reviewable proposal.

In this design, "memory" does not mean automatic saving, automatic execution,
or autonomous behavior. Memory / Skills is local-first and human-approved. It
prepares candidates for review, but it does not create skills, edit files, run
tools, or commit changes without explicit user approval.

The v0.1 direction is:

- collect repeated workflow candidates as proposals;
- keep the proposal visible and reviewable;
- make confirmation requirements explicit;
- defer persistence, approval actions, and skill draft promotion to later
  phases.

## 2. Current Context

Jarvis-Core currently has these major components:

- Research Council: idea, MVP, market, business viability, and validation
  planning.
- Daily AI Radar: read-only AI and agent technology scouting reports.
- Hermes Manager Pilot: Codex, ChatGPT, review, commit prompt, and checkpoint
  workflow management.
- Jarvis Console: local browser shell, skill hub, operating dashboard, skill
  suggestion surface, Skill Detail usage cards, Tasks / Reports dashboard,
  Checkpoints / History view, and Voice Inbox v0.1.
- Voice Inbox v0.1: text-only transcript and rough-thought capture that
  prepares task candidates and manual skill handoffs.

The Skill Registry already contains `memory_skills` as a planned skill. Voice
Inbox and Chat / Command can route repeated workflow requests to
`memory_skills`, for example `이 반복 작업 skill 후보로 기억해줘`.

There is no actual memory persistence, no candidate database, no approval
queue, and no skill creation workflow yet.

## 3. v0.1 Scope

### In Scope

Memory / Skills v0.1 includes:

- defining the repeated workflow candidate concept;
- defining a candidate schema;
- designing a read-only sample candidate panel;
- connecting Voice Inbox and Chat / Command to `memory_skills` as a proposal
  destination;
- using manual handoff and copy-only UI language;
- showing safety notes and confirmation-required status clearly;
- keeping Phase 1 read-only, sample-based, and non-persistent.

### Out of Scope

Memory / Skills v0.1 excludes:

- automatic saving;
- automatic skill creation;
- automatic Skill Registry modification;
- automatic code modification;
- automatic Codex, ChatGPT, or Hermes invocation;
- automatic Research Council or Daily AI Radar execution;
- repo or file writes;
- `git add`, `git commit`, `git push`, or other git write operations;
- external API, web, or LLM calls;
- microphone, STT, TTS, or recording;
- background autonomous execution.

## 4. User Flow

The intended flow is:

1. The user enters a repeated workflow in Voice Inbox or Chat / Command.
2. Jarvis routes the text to `memory_skills` when the deterministic routing
   rules match repeated workflow or skill-candidate language.
3. Jarvis does not save the candidate immediately.
4. The UI shows the result as `candidate`, `confirmation required`, and `no
   automatic action`.
5. The user can copy the candidate text or copy a skill draft prompt for manual
   review.
6. Phase 2B should first add preview-only capture with no persistence.
7. Phase 2C or later may add explicit approval-gated local saving.
8. Phase 3 may add skill draft preparation, still without automatic skill
   creation.

This flow keeps Memory / Skills as an inbox for proposals, not an automation
engine.

Phase 2 is not automatic memory. A saved candidate, if Phase 2C later adds one,
is still not a skill, not an approved skill, not a Skill Registry entry, and not
an execution target.

## 5. Candidate Data Model

The candidate model can use this shape. In Phase 1 this is sample data only;
there is no persistence.

```json
{
  "id": "mem_20260703_short-hash",
  "title": "Short human-readable candidate title",
  "original_text_preview": "Optional truncated source text",
  "cleaned_text": "Normalized candidate text",
  "candidate_type": "repeated_workflow | operating_rule | skill_candidate | prompt_pattern",
  "suggested_skill_id": "memory_skills",
  "confidence": "low | medium | high",
  "status": "candidate",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "source": "voice_inbox | chat_command | manual",
  "confirmation_required": true,
  "user_approved_at": "ISO-8601, only after explicit confirmation",
  "next_action": "Review this as a skill proposal.",
  "safety_notes": [],
  "tags": [],
  "schema_version": "memory_candidate.v1",
  "redaction_status": "not_scanned | preview_only | user_confirmed",
  "privacy_note": "User-provided local candidate; avoid storing sensitive raw text."
}
```

Notes:

- `original_text_preview` should be a short preview, not full raw transcript
  storage.
- Phase 2 should still avoid storing the full raw transcript by default.
- Recommended Phase 2 limits: `original_text_preview` max 240 chars,
  `cleaned_text` max 1000 chars, `title` max 120 chars, and bounded
  `tags` / `safety_notes` lists.
- Sensitive personal information should be minimized.
- Phase 1 should use sample data only.
- Real local storage should wait until Phase 2 and require explicit user
  approval.
- Candidate IDs should be generated safely and should not expose absolute paths,
  path segments from user input, or sensitive text.
- `user_approved_at` should be set only after an explicit confirm action.
- A visible sensitive-info warning is required before any candidate is saved.

## 6. Storage Strategy

Several locations are possible, but they have different safety implications.

| Location | Pros | Cons | Recommendation |
| --- | --- | --- | --- |
| `apps/jarvis-console/examples/` | Good for read-only sample data; naturally versioned with the app. | Not appropriate for real user memory. | Good for Phase 1 samples. |
| `apps/jarvis-console/data/` | App-owned and easy to discover. | Can make runtime repo writes look normal. | Avoid for v0.1 runtime state. |
| `apps/jarvis-console/state/` | Clear local state naming. | Needs gitignore, privacy, and explicit approval policy. | Consider only after Phase 2 policy work. |
| `memory/tasks/` | Natural top-level Jarvis memory/task namespace. | Tracked user memory can expose sensitive text and be staged accidentally. | Do not use for Phase 2 user candidate storage. |
| `memory/skills/` | Natural place for skill proposals and drafts. | Could be confused with installed skills and tracked skill assets. | Do not use for Phase 2 user candidate storage. |
| `docs/` | Good for design and schema documentation. | Not suitable for user candidate storage. | Good for Phase 0 only. |
| User-local app state outside the repo, such as `%LOCALAPPDATA%\Jarvis-Core\memory-skills\` or `~/.jarvis-core/memory-skills/` | Keeps personal candidates out of git by default. | Harder to back up and inspect from the repo. | Preferred if Phase 2C adds persistence. |

Recommended path:

- Phase 0: create only `docs/memory-skills-v0.1-design.md`.
- Phase 1: consider `apps/jarvis-console/examples/memory-skills-sample.json`
  for read-only sample candidates.
- Phase 2B: add preview-only candidate capture first, with no persistence,
  no save endpoint, no runtime write, and no local state path implementation.
- Phase 2C or later: if persistence is added, prefer repo-external user-local
  app state. Allow `JARVIS_LOCAL_STATE_DIR` as an override and use temp dirs in
  tests.
- Avoid tracked repo paths such as `memory/tasks/`, `memory/skills/`, or
  `apps/jarvis-console/data/` for user memory. They can mix sensitive personal
  text into git history, increase `git add .` accident risk, and make users feel
  that private memory lives inside the project repo.
- Jarvis Console runtime should not automatically write into the repo in v0.1.

## 7. UI Design

Jarvis Console can add a `Memory / Skills` tab or panel. The UI should feel like
a review surface, not a task runner.

Recommended sections:

- Pending Candidates
- Draft Guidance
- Safety Notes
- Candidate Cards

Candidate cards should show:

- title;
- status badge;
- source badge;
- confidence;
- cleaned text or summary;
- suggested next action;
- tags;
- safety notes;
- confirmation-required badge;
- read-only badge.

Phase 2 approval UX should stay conservative:

1. Voice Inbox or Chat / Command detects a Memory / Skills candidate.
2. Jarvis does not save it automatically.
3. The user chooses `Review Save Candidate` or `Prepare Local Candidate`.
4. Jarvis shows a preview of exactly which fields would be saved.
5. Jarvis shows a sensitive-info warning.
6. Only `Confirm Local Save` may save a candidate, and only in Phase 2C or
   later.
7. Saved candidates remain local candidates, not approved skills, registry
   entries, or execution targets.

Safe Phase 2 wording includes `Review Save Candidate`, `Prepare Local
Candidate`, `Confirm Local Save`, `Cancel`, and `Discard Draft`. Avoid `Enable
Memory`, `Auto Save`, `Always Remember`, `Run`, `Execute`, `Install Skill`,
`Create Skill Now`, and `Approve and Run`. The `approved` status name should be
avoided in Phase 2 because it can sound like skill approval; prefer `saved`,
`reviewed`, or `discarded`.

Safe Phase 1 actions:

- `Review Candidate`
- `Copy Candidate`
- `Copy Skill Draft Prompt`
- `Open Skill Details`

Actions to avoid in Phase 1:

- `Mark Approved`
- `Mark Rejected`
- `Archive Candidate`
- `Run`
- `Execute`
- `Start`
- `Auto`
- `Install Skill Now`

`Mark Approved`, `Reject`, and `Archive` imply state mutation, so they belong in
Phase 2 or later. `Promote to Skill Draft` can sound like automatic skill
creation, so Phase 1 should prefer `Copy Skill Draft Prompt`.

## 8. API Design

Phase 1 should include read-only GET endpoints only. POST and write endpoints
are listed here as future candidates, not as Phase 1 scope.

| Endpoint | Purpose | Read/Write | Approval Required | Phase | Safety Risk | v0.1 Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `GET /api/memory-skills` | Return Memory / Skills status, notes, and sample overview. | Read | No | Phase 1 | Low | Include if implementing the panel. |
| `GET /api/memory-skills/candidates` | Return sample or saved read-only candidate metadata. | Read | No | Phase 1 or Phase 2D | Low | Include sample/read-only only until saved candidates exist. |
| `POST /api/memory-skills/candidates/preview` | Normalize input and return the payload that would be saved, plus privacy warnings. | Read-like, no write | No | Phase 2B | Low-medium | Recommended next implementation. |
| `POST /api/memory-skills/candidates` | Save a candidate locally. | Write | Yes | Phase 2 | Medium | Exclude from Phase 1. |
| `POST /api/memory-skills/candidates/{id}/approve` | Mark a candidate approved. | Write | Yes | Phase 2 | Medium | Exclude from Phase 1. |
| `POST /api/memory-skills/candidates/{id}/reject` | Mark a candidate rejected. | Write | Yes | Phase 2 | Medium | Exclude from Phase 1. |
| `POST /api/memory-skills/candidates/{id}/archive` | Archive a candidate. | Write | Yes | Phase 2 | Medium | Exclude from Phase 1. |
| `POST /api/memory-skills/candidates/{id}/prepare-skill-draft` | Prepare draft text or draft prompt from a candidate. | Write or copy-only depending on design | Yes | Phase 3 | Medium | Prefer copy-only prompt first. |

Phase 1 conclusion:

- GET only.
- Sample/read-only only.
- No POST.
- No persistence.
- No automatic save from Voice Inbox.

Phase 2 API direction:

- Keep `GET /api/memory-skills`.
- Add `POST /api/memory-skills/candidates/preview` first as a Phase 2B
  candidate. It must not write files; it only returns normalized preview fields
  and privacy warnings.
- Defer `POST /api/memory-skills/candidates` until Phase 2C or later. It must
  reject requests without explicit confirmation.
- Defer `GET /api/memory-skills/candidates` until saved candidates exist in
  Phase 2D or later.
- Defer archive/discard endpoints until Phase 2E or later.
- Voice Inbox must never call the save endpoint automatically.
- All POST endpoints must reject malformed JSON, oversized input, and any path
  traversal or arbitrary path fields.

## 9. Integration Points

### Voice Inbox

Voice Inbox can suggest `memory_skills` for repeated workflow or skill-candidate
phrases. It must not save the candidate automatically. The result should remain
a task candidate with manual copy or detail handoff actions.

In Phase 2B, Voice Inbox may link to a preview-only Memory / Skills flow. That
preview must not write files. In Phase 2C or later, a local save can happen only
after the user reviews the preview and confirms the local save.

### Chat / Command Skill Suggestion

Chat / Command can continue routing repeated workflow requests to
`memory_skills`. The action panel should present the result as a proposal, not
as an executable skill.

### Skill Registry

`memory_skills` can remain `planned` until the review surface is implemented.
Its registry entry should continue to state that candidates are proposals and
that there is no automatic memory write or skill installation.

### Suggested Skill Action Panel

For `memory_skills`, the panel should avoid command-like affordances. It can
show `Open Skill Details`, `Copy Candidate`, or similar copy-only actions.

### Skill Detail Usage Cards

The Skill Detail card should describe Memory / Skills as a proposal inbox and
make its non-goals visible.

### Tasks / Reports Dashboard

Future approved candidates can appear as read-only metadata. Phase 1 should not
create task files or report files.

### History / Checkpoints View

Later phases can show promoted candidates or checkpoint docs as read-only
history metadata. Phase 1 should not create checkpoints.

### Hermes Manager Pilot

Hermes can be connected later through copy-only prompt handoff. Codex or Hermes
must not be called automatically.

Phase 2 keeps the same boundary. A saved candidate can still offer `Copy Skill
Draft Prompt`, but Jarvis Console must not open Hermes, fetch from Hermes, start
Codex, or convert a candidate into a Hermes session automatically.

## 10. Safety Boundary

Memory / Skills must preserve these boundaries:

- no autonomous execution;
- no automatic memory save;
- no automatic skill creation;
- no automatic code modification;
- no automatic repo or file write;
- no tracked repo user-memory storage;
- no auto `git add`, `git commit`, or `git push`;
- no external API, web, or LLM calls;
- no microphone, STT, TTS, or recording;
- no background agents;
- human-approved only;
- local-first only.

## 11. Phase 2 Write Safety

Phase 2B should be preview-only and should not write any file. If Phase 2C or
later adds persistence, the write design should follow these rules:

- prefer one per-candidate JSON file in repo-external user-local app state;
- write through a temporary file and atomic replace;
- validate the JSON schema and `schema_version`;
- cap candidate file size and individual field lengths;
- reject path traversal and arbitrary path input;
- never use user text as a path segment;
- isolate tests with `TemporaryDirectory` or `JARVIS_LOCAL_STATE_DIR`;
- fail tests if `git status --short` shows unexpected repo files;
- do not run git commands as part of save;
- do not let app runtime write to arbitrary paths.

These are Phase 2C-or-later requirements. They should not be implemented in
Phase 2B.

## 12. Phased Plan

### Phase 0: Design Doc Only

- Goal: fix the scope, candidate model, UI direction, API boundary, and safety
  constraints in this document.
- Expected files: `docs/memory-skills-v0.1-design.md`.
- Validation: `git diff --check` and document review.
- Risk: wording may imply implemented behavior.
- Do not: add app code, sample data, storage directories, POST endpoints, or
  runtime behavior.

### Phase 1: Read-only Sample Memory / Skills Panel

- Goal: add a read-only panel that displays sample candidate metadata and
  safety guidance.
- Expected files: Jarvis Console web files, server endpoint, smoke tests, and
  possibly a sample JSON file under `apps/jarvis-console/examples/`.
- Validation: py_compile, Jarvis Console self-test, smoke tests, node check,
  `git diff --check`, no POST endpoint checks, no write behavior checks.
- Risk: sample candidates may be mistaken for persisted user memory.
- Do not: add POST endpoints, persistence, runtime writes, approve/reject
  mutation, or auto execution.

### Phase 2A: Phase 2 Design Update

- Goal: record approval, privacy, storage, API, and write-safety boundaries.
- Write: documentation only.
- Do not: add app code, endpoints, storage, or sample state.

### Phase 2B: Preview-only Candidate Capture

- Goal: show the user the candidate fields that would be saved later.
- Write: none.
- Expected files: Jarvis Console API/UI/tests only.
- Validation: preview endpoint does not write, malformed JSON and oversized
  input are rejected, Voice Inbox does not save automatically.
- Do not: add persistence, a save endpoint, runtime file writes, local state
  paths, or confirm/save behavior.

### Phase 2C: Approval-gated Local Save

- Goal: save a candidate only after explicit user confirmation.
- Write: repo-external user-local app state only.
- Expected files: API handlers, storage helper, tests, and UI confirmation flow.
- Validation: temp-dir storage tests, atomic-write checks, schema validation,
  no unexpected git status files.
- Do not: store raw transcripts long term, write user memory into tracked repo
  paths, save without preview, or save without explicit confirmation.

### Phase 2D: Saved Candidates Read-only List

- Goal: show saved local candidates as read-only local proposals.
- Write: none for listing.
- Do not: present saved candidates as approved skills or Skill Registry entries.

### Phase 2E: Archive / Discard Actions

- Goal: add explicit state-change actions for local candidates.
- Write: approval-gated local state only.
- Do not: use wording that sounds like skill approval or execution.

### Phase 2F: Hermes Handoff from Saved Candidates

- Goal: provide copy-only prompt handoff from saved candidates.
- Write: none.
- Do not: open Hermes, fetch from Hermes, invoke Codex/Hermes, or create skill
  registry changes automatically.

### Phase 3: Skill Draft Prompt Preparation

- Goal: prepare a candidate as a skill draft prompt or copy-only draft text.
- Expected files: UI, tests, and possibly a draft schema.
- Validation: copy-only behavior, no Skill Registry mutation, no automatic file
  creation unless separately approved.
- Risk: "promote" language may imply automatic skill creation.
- Do not: install skills, modify the Skill Registry automatically, edit code, or
  call Codex/Hermes automatically.

### Phase 4: Hermes/checkpoint Handoff

- Goal: connect reviewed candidates to Hermes/checkpoint workflows through
  manual handoff.
- Expected files: UI handoff, tests, and docs.
- Validation: no Codex/Hermes auto invocation, no auto commit, no auto push,
  read-only checkpoint display.
- Risk: handoff can blur into automation if button language is too strong.
- Do not: call Codex/Hermes, generate commits, push, or create checkpoints
  automatically.

## 13. Recommended First Implementation

The safest first implementation for the original v0.1 plan was Phase 1:

- add a read-only Memory / Skills candidate panel to Jarvis Console;
- render sample candidates only;
- expose GET-only API metadata;
- add no POST endpoints;
- add no persistence;
- perform no runtime writes;
- trigger no automatic execution;
- show Voice Inbox `memory_skills` results as panel/detail guidance only;
- keep all handoff actions copy-only.

This gives users a clear place to understand the future Memory / Skills flow
without introducing state mutation or automation risk.

After Phase 1, the recommended next implementation is Phase 2B preview-only
candidate capture:

- no persistence;
- no write;
- no save endpoint;
- no runtime file write;
- no local state path implementation;
- show the fields that would be saved later;
- show a privacy warning;
- connect Voice Inbox only to preview, not save.

Persistence should wait until Phase 2C or later. It should prefer repo-external
user-local app state, should not store raw transcripts long term, and should not
ship without a privacy/redaction policy.

## 14. Validation Plan

For the first implementation, run:

```text
python -B -m py_compile apps\jarvis-console\run_web_app.py apps\jarvis-console\run_smoke_tests.py
python -B apps\jarvis-console\run_web_app.py --self-test
python -B apps\jarvis-console\run_smoke_tests.py
python -B apps\hermes-manager-pilot\run_smoke_tests.py
python -B apps\research-council\run_smoke_tests.py
python -B apps\daily-ai-radar\run_smoke_tests.py
node --check apps\jarvis-console\web\app.js
git diff --check
```

Additional checks:

- verify no POST/write endpoints in Phase 1;
- verify no `Run`, `Execute`, `Start`, or `Auto` button wording;
- verify no external fetch or API call;
- verify no repo or file write behavior;
- verify no automatic save from Voice Inbox;
- verify `jarvis.bat` remains untracked and untouched.

Phase 2B validation should additionally verify:

- preview endpoint writes no files;
- no save endpoint exists yet;
- preview response escapes or text-renders unsafe HTML-like input;
- privacy warning is present;
- Voice Inbox never calls a save endpoint;
- `git status --short` has no unexpected files.

Phase 2C validation should additionally verify:

- save endpoint rejects missing explicit confirmation;
- storage tests use temp dirs or `JARVIS_LOCAL_STATE_DIR`;
- repo-internal tracked paths are not used for user memory;
- atomic write and schema validation paths are covered;
- malformed JSON, oversized input, and path traversal are rejected.

## 15. Risks

Key risks:

- "memory" may be mistaken for automatic saving.
- Raw transcripts may contain personal or sensitive information.
- Local state inside the repo may look like tracked project content.
- Approve/reject UI in Phase 1 may look functional even if it is only a
  concept.
- "Promote" wording may imply automatic skill creation.
- Voice Inbox routing may feel like automatic storage if the UI is not clear.
- Sample data and real local state may become confused.
- The status enum can become overdesigned before real usage patterns are known.
- Adding persistence before privacy/redaction policy can store sensitive family,
  health, or operational details unintentionally.
- Repo-internal user memory can be staged accidentally.

## 16. Open Questions

Questions to defer until later phases:

- Should real local state live inside the repo or outside it as app-local state?
- If stored inside the repo, what should the gitignore policy be?
- Should `memory/tasks/` or `memory/skills/` be the long-term namespace?
- How should sensitive text redaction work in v0.2?
- Should skill drafts be files, copy-only prompts, or approval-gated local
  records?
- When should approve/reject/archive UI be introduced?
- How much candidate history should be visible in Tasks / Reports and History?

Current Phase 2 recommendation:

- Do not add persistence immediately.
- Implement Phase 2B preview-only capture flow next.
- Avoid tracked repo user-memory storage.
- Consider repo-external user-local app state for Phase 2C or later.
- Do not add persistence without privacy/redaction policy.
- Do not let Voice Inbox save automatically.
- Do not call Hermes, Codex, or any external tool automatically.
