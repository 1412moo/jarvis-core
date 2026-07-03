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
6. Phase 2 may add explicit approval-gated local saving.
7. Phase 3 may add skill draft preparation, still without automatic skill
   creation.

This flow keeps Memory / Skills as an inbox for proposals, not an automation
engine.

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
  "next_action": "Review this as a skill proposal.",
  "safety_notes": [],
  "tags": [],
  "privacy_note": "User-provided local candidate; avoid storing sensitive raw text."
}
```

Notes:

- `original_text_preview` should be a short preview, not full raw transcript
  storage.
- Sensitive personal information should be minimized.
- Phase 1 should use sample data only.
- Real local storage should wait until Phase 2 and require explicit user
  approval.
- Candidate IDs should be deterministic and should not expose absolute paths or
  sensitive text.

## 6. Storage Strategy

Several locations are possible, but they have different safety implications.

| Location | Pros | Cons | Recommendation |
| --- | --- | --- | --- |
| `apps/jarvis-console/examples/` | Good for read-only sample data; naturally versioned with the app. | Not appropriate for real user memory. | Good for Phase 1 samples. |
| `apps/jarvis-console/data/` | App-owned and easy to discover. | Can make runtime repo writes look normal. | Avoid for v0.1 runtime state. |
| `apps/jarvis-console/state/` | Clear local state naming. | Needs gitignore, privacy, and explicit approval policy. | Consider only after Phase 2 policy work. |
| `memory/tasks/` | Natural top-level Jarvis memory/task namespace. | Needs storage schema, gitignore, and privacy decisions. | Candidate for Phase 2 or later. |
| `memory/skills/` | Natural place for skill proposals and drafts. | Could be confused with installed skills. | Candidate for Phase 3 or later. |
| `docs/` | Good for design and schema documentation. | Not suitable for user candidate storage. | Good for Phase 0 only. |

Recommended path:

- Phase 0: create only `docs/memory-skills-v0.1-design.md`.
- Phase 1: consider `apps/jarvis-console/examples/memory-skills-sample.json`
  for read-only sample candidates.
- Phase 2 or later: consider `memory/tasks/` or `memory/skills/` only after
  gitignore, privacy, and approval policy are explicit.
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
| `GET /api/memory-skills/candidates` | Return sample or approved read-only candidate metadata. | Read | No | Phase 1 | Low | Include sample/read-only only. |
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

## 9. Integration Points

### Voice Inbox

Voice Inbox can suggest `memory_skills` for repeated workflow or skill-candidate
phrases. It must not save the candidate automatically. The result should remain
a task candidate with manual copy or detail handoff actions.

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

## 10. Safety Boundary

Memory / Skills must preserve these boundaries:

- no autonomous execution;
- no automatic memory save;
- no automatic skill creation;
- no automatic code modification;
- no automatic repo or file write;
- no auto `git add`, `git commit`, or `git push`;
- no external API, web, or LLM calls;
- no microphone, STT, TTS, or recording;
- no background agents;
- human-approved only;
- local-first only.

## 11. Phased Plan

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

### Phase 2: Approval-gated Candidate Capture

- Goal: add explicit user-approved local candidate capture.
- Expected files: API handlers, validation tests, UI confirmation flow, and a
  storage policy.
- Validation: malformed input checks, path safety checks, confirmation checks,
  no automatic save from Voice Inbox, and no git write commands.
- Risk: local state may contain sensitive text or become confused with tracked
  repo content.
- Do not: save before explicit approval, write hidden files, write outside the
  approved storage path, or create commits automatically.

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

## 12. Recommended First Implementation

The safest first implementation is:

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

## 13. Validation Plan

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

## 14. Risks

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

## 15. Open Questions

Questions to defer until later phases:

- Should real local state live inside the repo or outside it as app-local state?
- If stored inside the repo, what should the gitignore policy be?
- Should `memory/tasks/` or `memory/skills/` be the long-term namespace?
- How should sensitive text redaction work in v0.2?
- Should skill drafts be files, copy-only prompts, or approval-gated local
  records?
- When should approve/reject/archive UI be introduced?
- How much candidate history should be visible in Tasks / Reports and History?
