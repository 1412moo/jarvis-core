# Memory / Skills v0.1 Design

Last updated: 2026-07-22

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

There is still no user-facing memory persistence, live save endpoint, saved
candidates dashboard, approval queue, or skill creation workflow. Phase 2B
preview-only capture and the Phase 2C-0/1/2/3a/3b internal helpers exist. Phase
2C-3c completed the design/reopen-conditions review but did not reopen anything.
Phase 2C-4a adds privacy-required token issue and a route-free guarded save
coordinator for internal/tests-only coverage. The candidate writer, request
guard, session registry, preview token registry, and coordinator are not
connected to live HTTP routes, UI, or Voice Inbox. Phase 2C-4b adds a bounded
raw HTTP metadata adapter for internal/tests-only coverage; it is also absent
from the HTTP handler and dispatcher. Phase 2C-4c completes the design-only
session-bootstrap contract review without changing application behavior. Phase
2C-4d implements the contract as route-free internal/tests-only primitives and
still adds no live session or route. Phase 2C-4e composes guarded raw request
validation, strict JSON framing, privacy review, canonicalization, and
session-bound preview-token issue behind another route-free internal/tests-only
coordinator.

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
- automatic or user-facing repo/file writes;
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
6. Phase 2B preview-only capture can show a normalized candidate with no
   persistence.
7. Phase 2C-3a/3b hardens internal storage and guarded-request primitives, but
   does not expose local saving.
8. A later explicitly approved phase may decide whether and how to expose
   approval-gated local saving.
9. Phase 3 may add skill draft preparation, still without automatic skill
   creation.

This flow keeps Memory / Skills as an inbox for proposals, not an automation
engine.

Phase 2 is not automatic memory. A saved candidate, if a later user-facing
phase adds one, is still not a skill, not an approved skill, not a Skill
Registry entry, and not an execution target.

After Phase 2C-4e, hardened candidate-write and guarded-request/token
primitives, a route-free coordinator, and a route-free raw HTTP metadata
adapter, bootstrap primitive, and guarded save-preparation coordinator exist,
but user-facing local save is not enabled. `POST /api/memory-skills/candidates`
remains disabled/non-success, and there is no UI
`Save` / `Confirm Local Save` flow, Voice Inbox token/save path, or saved
candidates dashboard.

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
- Phase 2C-4a keeps `original_text_preview` in the write-free review snapshot
  but omits it from every persisted candidate JSON by default.
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
- Phase 2B: preview-only candidate capture is implemented. It has no
  persistence, no save endpoint, no runtime write, and the preview endpoint is
  write-free.
- Phase 2C-0: a storage path safety helper and local state path calculation are
  implemented. The helper calculates and validates repo-external user-local
  paths, but it does not create directories or write files. The default
  candidate path is
  `%LOCALAPPDATA%\Jarvis-Core\memory-skills\candidates` on Windows, with
  `~/.jarvis-core/memory-skills/candidates` as the fallback and
  `JARVIS_LOCAL_STATE_DIR` as an absolute override. Repo-internal paths,
  relative overrides, and traversal-like repo-internal paths are rejected.
- Phase 2C-1: a save request dry-run validation helper is implemented. It is
  save preflight validation, not saving.
- Phase 2C-2: a candidate write helper is implemented for self-test and smoke
  test coverage only. It uses the storage path helper and TemporaryDirectory
  tests. It is not connected to API, UI, or Voice Inbox.
- Phase 2C-3a: the tests-only candidate writer is hardened against reparse-point
  paths, collisions, overwrite races, invalid Unicode, oversized JSON, and
  unsafe publication. The live save route remains disabled.
- Phase 2C-3b: process-local `SessionRegistry`, `LocalRequestGuard`, canonical
  preview snapshot/digest, and one-time `PreviewTokenRegistry` primitives are
  implemented for internal tests only. They issue no live cookie or token and
  are not connected to HTTP dispatch, UI, or Voice Inbox.
- Phase 2C-3c: the live-save trust boundary, proposed approval sequence, and
  mandatory reopen checklist are documented. The review verdict is `keep
  locked`; no app code, route, UI, or persistence behavior was added.
- Phase 2C-4a: the privacy default is resolved as persisted source-preview
  omission. Token issue requires explicit privacy review, and a route-free
  internal/tests-only coordinator composes guard validation, one-time claim,
  canonical revalidation, dry-run validation, and hardened writing. Tests use
  temporary state only.
- Phase 2C-4b: a route-free internal/tests-only raw HTTP metadata adapter
  preserves duplicate visibility, enforces exact single security headers, and
  bounds Content-Length before request-guard use. It is not connected to HTTP
  dispatch and reads no body.
- Phase 2C-4c/4d: the bootstrap contract is designed and implemented as a
  route-free internal/tests-only adapter, atomic session rotate-or-issue path,
  and private Cookie/public JSON result. No live session is issued.
- Phase 2C-4e: strict raw-header/body validation, request guard, explicit
  privacy review, server canonicalization, and session-bound token issue are
  composed route-free. No live token is issued.
- A later explicitly approved phase may connect to these helpers instead of
  duplicating validation, storage, or request-guard logic.
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

Current Phase 2B UI status:

- the preview card shows `Preview only`, `Not saved`, `No persistence`, and `No
  runtime write`;
- Voice Inbox can manually connect to preview;
- Voice Inbox does not auto-save;
- no UI `Save` / `Confirm Local Save` action is enabled yet.

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
| `GET /api/memory-skills/candidates` | Return sample or saved read-only candidate metadata. | Read | No | Phase 2D or later | Low | Not implemented; keep saved-candidate listing deferred. |
| `POST /api/memory-skills/candidates/preview` | Normalize input and return the payload that would be saved, plus privacy warnings. | Read-like, no write | No | Phase 2B | Low-medium | Implemented; write-free. |
| `POST /api/memory-skills/candidates` | Save a candidate locally. | Write | Yes | Later explicit phase | Medium | Disabled/non-success after Phase 2C-4e; guarded composition, metadata adaptation, bootstrap, and save preparation remain route-free/internal-tests-only. |
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
- `POST /api/memory-skills/candidates/preview` exists as the implemented Phase
  2B endpoint. It must not write files; it only returns normalized preview
  fields and privacy warnings.
- `POST /api/memory-skills/candidates` remains disabled/non-success. Phase
  2C-1/2/3a added validation and hardened write composition for internal tests,
  Phase 2C-3b added route-free request-guard and preview-token primitives, and
  Phase 2C-4a added route-free guarded coordination with persisted
  source-preview omission. Phase 2C-4b added route-free raw HTTP metadata
  adaptation without handler integration. Phase 2C-4c/4d designed and
  implemented route-free bootstrap primitives without registering a route.
  Phase 2C-4e added route-free guarded save preparation without handler use.
- Defer any live `POST /api/memory-skills/candidates` route until separate
  explicit approval. It must reject requests without explicit confirmation and
  must not trust a client-supplied digest as standalone authorization.
- `GET /api/memory-skills/candidates` is not implemented. Defer it until saved
  candidates exist in Phase 2D or later.
- Defer archive/discard endpoints until Phase 2E or later.
- Voice Inbox must never call the save endpoint automatically.
- All POST endpoints must reject malformed JSON, oversized input, and any path
  traversal or arbitrary path fields.

## 9. Integration Points

### Voice Inbox

Voice Inbox can suggest `memory_skills` for repeated workflow or skill-candidate
phrases. It must not save the candidate automatically. The result should remain
a task candidate with manual copy or detail handoff actions.

In Phase 2B, Voice Inbox can link manually to a preview-only Memory / Skills
flow. That preview must not write files or issue preview tokens. After Phase
2C-4e, Voice Inbox still does not auto-save, request tokens, or call a save
endpoint. Any future local save requires separate explicit approval and can
happen only after the user reviews the preview and confirms the local save.

### Chat / Command Skill Suggestion

Chat / Command can continue routing repeated workflow requests to
`memory_skills`. The action panel should present the result as a proposal, not
as an executable skill.

### Skill Registry

`memory_skills` can remain `planned` until the review surface is implemented.
Its registry entry should continue to state that candidates are proposals and
that there is no automatic memory write or skill installation.

Saved candidates, when user-facing save is later enabled, must remain separate
from the Skill Registry. A saved candidate is not an approved skill and is not
executable.

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
- no Skill Registry modification;
- no automatic code modification;
- no automatic repo or file write;
- no Hermes/Codex automatic invocation;
- no repo-internal tracked user memory;
- no raw transcript full storage;
- no auto `git add`, `git commit`, or `git push`;
- no pull request creation;
- no external API, web, or LLM calls;
- no microphone, STT, TTS, or recording;
- no background agents;
- human-approved only;
- local-first only;
- user-facing save is still not enabled after Phase 2C-4e.

## 11. Phase 2 Write Safety

Phase 2B is preview-only and does not write any file. Phase
2C-0/1/2/3a/3b has implemented internal helpers, but it has not enabled
user-facing local save. If a later explicitly approved phase exposes
persistence, the write design should follow these rules:

- prefer one per-candidate JSON file in repo-external user-local app state;
- write through an exclusively created temporary file and no-overwrite atomic
  publication;
- validate the JSON schema and `schema_version`;
- cap candidate file size and individual field lengths;
- reject path traversal and arbitrary path input;
- never use user text as a path segment;
- isolate tests with `TemporaryDirectory` or `JARVIS_LOCAL_STATE_DIR`;
- fail tests if `git status --short` shows unexpected repo files;
- do not run git commands as part of save;
- do not let app runtime write to arbitrary paths.

Current helper status and design decision through Phase 2C-4e:

- Phase 2C-0 implemented a storage path helper. It calculates and validates
  paths only. It rejects repo-internal paths, relative overrides, and
  traversal-like repo-internal paths, and it does not create directories or
  write files.
- Phase 2C-1 implemented save request dry-run validation. It validates the
  future save request shape and requires `explicit_confirmation: true`,
  `privacy_reviewed: true`,
  `save_scope: local_only`, `candidate_preview.status: preview_only`,
  `candidate_preview.user_approved_at: null`,
  `suggested_skill_id: memory_skills`, and `confirmation_required: true`. It
  rejects raw transcript fields, path/file/storage fields, and saved- or
  approved-like preview payloads. It returns a dry-run result only, writes no
  files, creates no directories, and enables no save endpoint.
- Phase 2C-2 implemented a candidate write helper. It can write one
  per-candidate JSON file, uses the storage path helper, rejects repo-internal
  paths before `mkdir` or write, uses a safe schema, and does not write raw
  transcript or path fields. It is used only by self-test/smoke tests, and
  candidate JSON writes occur only inside TemporaryDirectory tests.
- Phase 2C-3a hardened the writer with repeated path validation, reparse-point
  rejection, exclusive temporary-file creation, strict UTF-8 and size checks,
  flush/fsync, and no-overwrite publication through a hard link. Collision and
  failure paths clean up temporary files without exposing private paths.
- Phase 2C-3b implemented bounded process-local session/CSRF request-guard and
  one-time preview-token primitives. Tokens are bound to canonical server-held
  snapshots, expire deterministically, use digest keys, and are claimed once
  under a lock. These primitives perform no filesystem write and remain
  route-free/internal-tests-only.
- Phase 2C-3c reviewed how those primitives could be composed safely and kept
  live save locked. No raw metadata adapter, live session/bootstrap lifecycle,
  token-issuance route, save coordinator, confirmation UI, or recovery flow is
  connected to live behavior.
- Phase 2C-4a implemented `coordinate_guarded_memory_skills_save` for
  internal/tests-only coverage. Preview-token issue now requires
  `privacy_reviewed=True`; the coordinator validates guarded synthetic metadata,
  accepts exactly a one-time token and `save_local_candidate` confirmation,
  revalidates the server-held canonical snapshot/digest, claims before writing,
  and never retries automatically. The persisted schema omits
  `original_text_preview`. Tests write only under `TemporaryDirectory`.
- Phase 2C-4b implemented `adapt_memory_guarded_http_metadata` for
  route-free internal/tests-only coverage. It accepts duplicate-preserving raw
  header pairs, enforces exact single required security headers, rejects
  Transfer-Encoding, and bounds canonical Content-Length values before guard
  use. It is not referenced by the HTTP handler or dispatcher.
- Phase 2C-4c completed the dedicated session-bootstrap contract review. It
  defines future same-origin no-body request validation, atomic issue/rotation,
  credential delivery, lifecycle bounds, and deterministic test obligations.
  It added no app code or runtime authority.
- Phase 2C-4d implemented the bootstrap-specific raw metadata adapter and made
  the coordinator own that validation before allocation. `SessionRegistry`
  rotates atomically when capacity remains and returns one uniform capacity
  error before hint lookup when full. Private Cookie material and the public
  CSRF payload are held in a non-JSON-serializable redacted result. The
  primitive remains absent from HTTP dispatch.
- Phase 2C-4e implemented `coordinate_memory_skills_save_preparation`. The
  coordinator owns raw-header adaptation and exact Content-Length/body matching,
  rejects duplicate JSON keys, requires `privacy_reviewed: true`, canonicalizes
  server-side, and issues one session-bound token. Its redacted private result
  exposes only bounded token/display metadata when explicitly converted.
- Saved JSON uses `status: saved`, but a saved candidate is still only a local
  candidate, not an approved skill and not executable.
- The write helper, adapter, guard, token, and coordinator are not connected to
  API, UI, or Voice Inbox. There is still
  no save endpoint, no UI `Save` / `Confirm Local Save`, no Voice Inbox
  auto-save, and no saved candidates dashboard.

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
- Current status: implemented.
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
- Current status through Phase 2C-4e: storage path, dry-run validation, hardened
  candidate writer, request guard, session registry, canonical snapshot/digest,
  preview token helpers, guarded save coordinator, raw HTTP metadata adapter,
  bootstrap primitive, and save-preparation coordinator exist. They remain
  internal/tests-only. The 2C-3c/4a/4b/4c/4d/4e work kept user-facing save
  disabled and connected none of them to live HTTP routes, UI, or Voice Inbox.

### Phase 2C-3: Approval-gated Local Save Safety Decision

- Goal: determine whether the safety and product prerequisites are sufficient
  before any decision to expose approval-gated local save.
- Phase 2C-3a/3b does not expose local save, and Phase 2C-3c was completed as a
  design/review-only step. Any later implementation still requires separate
  explicit approval.
- Any future save must not be automatic.
- It should require preview, explicit confirmation, privacy review, and
  `local_only` scope.
- It should connect to the existing helpers instead of duplicating validation or
  write logic.
- It must keep Voice Inbox from auto-saving.
- It must keep saved candidates separate from Skill Registry and skill
  execution.

#### Phase 2C-3a: Storage Primitive Hardening

- Status: implemented for internal/tests-only writer coverage.
- Result: hardened path validation, serialization, collision handling, and
  no-overwrite publication.
- Boundary: the save route remains disabled/non-success.

#### Phase 2C-3b: Request Guard and Preview Token Primitives

- Status: implemented for internal/tests-only coverage.
- Result: bounded process-local sessions, strict loopback request metadata
  checks, canonical candidate digesting, and session-bound one-time preview
  tokens.
- Boundary: no live session/bootstrap/token route, no save route, no UI action,
  and no Voice Inbox token/save path.

#### Phase 2C-3c: Live Save Design and Reopen Conditions Review

- Status: design/review completed on 2026-07-22; no application behavior was
  implemented.
- Reopen verdict: **keep locked**. The internal 2C-3a/3b primitives are useful
  prerequisites, but they are not a complete live-save security or product
  flow.
- Boundary: `POST /api/memory-skills/candidates` remains disabled/non-success;
  the preview endpoint remains write-free/token-free; request guard/token and
  coordinator primitives remain internal/tests-only.

##### Trust and authority model

- Loopback binding is not authentication. The future guard is intended to
  reduce browser cross-origin and confused-request risk; it does not protect
  against a malicious process or another OS user that can act as the current
  user. If that stronger threat model becomes required, live save must remain
  locked until OS-backed authentication or an equivalent control is designed.
- The current write-free preview is informational only. It must never issue a
  session, preview token, save authority, or persistent identifier.
- A future save-preparation action must be separate from preview, guarded by the
  actual bound `127.0.0.1:<port>`, and initiated by an explicit user action.
- The server-held canonical snapshot is the only candidate content authority
  after token issuance. A final request must not supply candidate text, a file
  path, storage root, candidate digest, or approval timestamp as authority.
- A token proves only that one guarded session prepared one exact snapshot. It
  is not proof of identity, privacy review, skill approval, or execution
  approval.
- A saved record remains a local candidate. It is not an approved skill, Skill
  Registry entry, command, prompt execution request, or Voice Inbox action.

##### Proposed future flow, not implemented

1. The user creates a normalized candidate through the existing write-free,
   token-free preview endpoint.
2. A future explicit `Review Local Save` action requests a process-local
   session/bootstrap if needed. Bootstrap must validate loopback client, exact
   Host, and exact Origin before issuing an `HttpOnly`, `SameSite=Strict`
   session cookie and a separate CSRF value.
3. A distinct guarded save-preparation request submits the reviewed preview and
   an explicit privacy acknowledgement. The server revalidates and canonicalizes
   it, stores the canonical bytes only in the bounded process-local token
   registry, and returns a short-lived one-time token plus non-secret display
   metadata.
4. The UI displays the exact canonical fields, storage scope, retention note,
   and the statements `candidate only`, `not a skill`, and `will not run`.
5. A separate final action sends only the one-time preview token and an exact
   confirmation literal. Generic booleans, candidate payloads, client paths,
   client timestamps, or a digest alone are insufficient.
6. The server re-runs the actual-port request guard, atomically consumes the
   session-bound token, reconstructs the existing dry-run contract from the
   server-held snapshot, and calls the hardened no-overwrite writer.
7. Success returns bounded receipt fields such as candidate ID and title. It
   does not return raw content, token material, stack traces, or a private
   filesystem path.

The exact bootstrap and save-preparation route names are deliberately not
reserved by this design. Choosing names does not authorize registering them in
the HTTP handler.

##### Mandatory reopen checklist

Every item below must be implemented in approved work packages, locally
validated, self-reviewed, and approved before a live save route can be exposed:

1. **Session bootstrap:** one bounded process-local bootstrap lifecycle with
   exact loopback Host/Origin checks, no token in URLs or logs, `Cache-Control:
   no-store`, expiry, capacity behavior, and restart invalidation. Phase 2C-4c
   defines the design contract and Phase 2C-4d implements the route-free
   primitive; live integration remains incomplete and locked.
2. **Raw HTTP metadata adapter:** preserve or reject duplicate security headers
   rather than silently merging them; validate exact Host, Origin,
   `Content-Type`, cookie, and CSRF values before JSON use; reject missing,
   negative, conflicting, or oversized lengths before reading the body. The
   route-free structural adapter portion is implemented in Phase 2C-4b; live
   handler integration remains incomplete and locked.
3. **Route allowlist:** bootstrap, save preparation, and final save must each be
   explicit allowlist entries. Unknown methods and paths fail closed. The
   preview route remains unchanged and token-free.
4. **Canonical authority:** save preparation must bind a one-time token to the
   server-held bytes produced by `canonicalize_memory_candidate_snapshot`.
   Final save accepts no replacement candidate, path, or client-supplied
   digest.
5. **Confirmation semantics:** the final action requires a dedicated UI step
   and an exact confirmation literal tied to the displayed snapshot. Session,
   token, privacy acknowledgement, and confirmation are independent checks.
6. **Privacy contract:** the v0.1 decision is to omit
   `original_text_preview` from persisted candidate JSON while retaining the
   bounded value only in the write-free review snapshot and process-local token
   snapshot. Full transcripts and arbitrary path fields stay prohibited.
7. **One-claim failure behavior:** each token can authorize at most one write
   attempt, and token claim occurs before that attempt. If validation or writing
   then fails, that token is dead and the user must preview and confirm again;
   the system must never retry a write automatically. The UI must explain
   ambiguous response recovery so the user does not unknowingly create
   duplicates.
8. **Restart and recovery:** restart invalidates all sessions and outstanding
   tokens without deleting saved files. Partial temporary files are cleaned up;
   an already published candidate is never overwritten. Retention and manual
   recovery instructions must be visible before the first live save.
9. **Bounded responses and logs:** except for the newly issued CSRF value in one
   successful bootstrap JSON response and the session ID in its `Set-Cookie`,
   credentials, canonical bytes, raw text, private paths, stack traces, and
   security-header values are absent from responses and logs. Neither bootstrap
   credential is echoed later. Errors use fixed categories and do not reveal
   whether a session or token existed.
10. **Deterministic integration tests:** use an ephemeral loopback port and
    isolated temporary state to cover valid flow, duplicate/missing headers,
    wrong Host/Origin, media-type variants, malformed/oversized bodies, expired
    and cross-session tokens, replay and concurrent claims, restart, capacity,
    collision, reparse/path attacks, writer failure after claim, response
    bounds, and disabled routes.
11. **Browser safety tests:** prove that no Save/Confirm control exists until a
    separately approved UI package, the exact snapshot is escaped and visible
    before confirmation, double-click/retry cannot submit twice, and Voice
    Inbox never requests a session or token and never saves.
12. **Repository and operational checks:** tests leave no candidate JSON,
    storage directory, runtime state, cache, log, listener, or tracked/untracked
    artifact in the repo. `jarvis.bat` remains untouched and untracked.

##### Explicit non-goals of any first reopened slice

- no automatic or Voice Inbox save;
- no saved-candidates dashboard, archive, discard, approve, or promote action;
- no Skill Registry mutation or skill execution;
- no external API, LLM, credential store, background worker, or scheduler;
- no repo-internal user state, git write, push, or PR;
- no durable browser session or token across process restart.

##### Decision and next safe unit

Phase 2C-4a satisfies the internal coordinator and privacy-default portions of
this design. Phase 2C-4b satisfies the route-free structural raw-metadata
adapter portion. Phase 2C-4c settles the session-bootstrap design contract in
[`memory-skills-session-bootstrap-v0.1-design.md`](memory-skills-session-bootstrap-v0.1-design.md).
Phase 2C-4d implements that contract as route-free internal/tests-only code.
Phase 2C-4e implements guarded save preparation as route-free
internal/tests-only code. None grants HTTP or UI authority. The next candidate
is a separately approved Phase 2C-4f design/review-only live-integration
readiness checkpoint. Live HTTP integration stays locked until the remaining
checklist items are complete and separately approved.

#### Phase 2C-4a: Guarded Save Coordinator and Privacy Default

- Status: implemented for internal/tests-only coverage.
- Privacy result: persisted candidate JSON omits `original_text_preview` by
  default. The field remains available only in the bounded preview and
  process-local canonical snapshot used for exact review binding.
- Token result: `PreviewTokenRegistry.issue` rejects missing or false privacy
  review and stores no token in those cases.
- Coordinator result: exact guarded metadata, one session-bound token, and the
  literal `save_local_candidate` are required. Client candidate content, path,
  digest, timestamp, and extra fields are rejected.
- Failure result: token claim happens before validation/write. Replay,
  cross-session use, digest mismatch, and automatic retry fail closed. A writer
  failure leaves the token dead and requires a fresh review flow.
- Test result: deterministic success and failure coverage writes only inside
  `TemporaryDirectory`; no runtime state or repo artifact remains.
- Boundary: no handler registration, session/bootstrap route, token route,
  live save route, UI Save/Confirm, Voice Inbox path, or saved dashboard.

#### Phase 2C-4b: Raw HTTP Metadata Adapter

- Status: implemented for route-free internal/tests-only coverage.
- Input result: accepts only a duplicate-preserving iterable of raw header
  pairs; mappings and malformed, non-ASCII, control-bearing, or oversized
  metadata fail closed.
- Security-header result: requires exactly one Host, Origin, Content-Type,
  Cookie, `X-Jarvis-CSRF`, and Content-Length value and rejects
  Transfer-Encoding.
- Body-bound result: Content-Length must be one canonical non-negative decimal
  within the configured JSON body limit before any future body read.
- Error result: fixed error categories do not echo session, CSRF, header, body,
  or private-path values.
- Test result: deterministic valid, duplicate, missing, malformed, oversized,
  and request-guard handoff cases leave no runtime state or repo artifact.
- Boundary: no handler/dispatcher reference, bootstrap route, token route, live
  save route, UI Save/Confirm, Voice Inbox path, or saved dashboard.

#### Phase 2C-4c: Session Bootstrap Contract Review

- Status: design/review completed on 2026-07-22; no application behavior was
  implemented.
- Request result: future bootstrap is one explicit same-origin loopback POST
  with no body, exact actual-port Host/Origin, and a dedicated raw-header
  contract that does not reuse the guarded-request adapter.
- Lifecycle result: session issue/rotation is bounded, atomic, process-local,
  expiry-aware, and restart-invalidated; invalid input allocates nothing.
- Delivery result: the session ID appears only in `Set-Cookie`; the CSRF value
  appears only in the no-store success body and frontend memory.
- Authority result: bootstrap grants only a later request-guard attempt, never
  privacy review, preview-token issue, save, skill approval, or execution.
- Implementation result: Phase 2C-4d completed the route-free
  bootstrap-specific adapter plus atomic rotate-or-issue primitive with
  deterministic tests.
- Boundary: no route name or registration, handler/UI/Voice change, live
  session issue, persistence, save endpoint, or dashboard.

#### Phase 2C-4d: Route-free Session Bootstrap Primitive

- Status: implemented for route-free internal/tests-only coverage.
- Validation result: the coordinator itself requires exact synthetic peer,
  bound host/port, method, target, and duplicate-preserving raw headers before
  it can allocate a session.
- Lifecycle result: rotate-or-issue is atomic under the registry lock, preserves
  the old session on generation/collision failure, enforces expiry and capacity,
  and does not evict unrelated live sessions.
- Side-channel result: a full registry returns the same bounded capacity error
  before checking whether the untrusted hint exists.
- Delivery result: private Cookie and public CSRF fields are separated in a
  non-JSON-serializable dataclass whose `repr` hides both credentials.
- Test result: deterministic success, malformed transport/header/cookie,
  rotation, mismatch, capacity, expiry, restart, generator failure, collision,
  and concurrency coverage leaves no runtime state or repo artifact.
- Boundary: no handler/dispatcher/route/UI/Voice reference, no live session or
  token issue, no save endpoint, persistence, or dashboard.
- Implementation result: Phase 2C-4e completed the route-free guarded
  save-preparation coordinator with deterministic tests.

#### Phase 2C-4e: Route-free Guarded Save Preparation

- Status: implemented for route-free internal/tests-only coverage.
- Input result: the coordinator owns duplicate-preserving raw-header adaptation,
  exact Content-Length/body matching, strict UTF-8 JSON parsing, and duplicate
  key rejection before accepting the exact preparation payload.
- Guard result: actual-port Host/Origin, approved JSON media type, session
  cookie, and CSRF must pass before body interpretation or token issue.
- Authority result: exactly `candidate_preview` plus `privacy_reviewed: true`
  reaches server canonicalization; client paths, confirmation fields, and
  replacement digests are rejected.
- Token result: one session-bound token is issued for the server-held canonical
  snapshot. Duplicate/capacity failures use a generic unavailable result, and
  malformed registry success is consumed instead of leaving an orphan token.
- Response result: the redacted non-JSON-serializable private result hides the
  token from `repr`; explicit public conversion returns only the token, digest,
  TTL, and bounded candidate-only display metadata without raw candidate text.
- Test result: deterministic malformed header/body, duplicate key, wrong
  Origin/session, privacy, canonicalization, capacity, generator failure,
  corruption cleanup, cross-session claim, and concurrency coverage writes no
  file and leaves no runtime or repo artifact.
- Boundary: no handler/dispatcher/route/UI/Voice reference, no live session or
  token issue, no save endpoint, persistence, or dashboard.
- Next candidate: separately approved Phase 2C-4f design/review-only
  live-integration readiness checkpoint.

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

At the current Phase 2C-4e status, Phase 2B preview-only capture, the Phase
2C-0/1/2/3a/3b internal helpers, the Phase 2C-3c trust model/checklist, and the
route-free guarded save coordinator and raw HTTP metadata adapter are
implemented, and the session-bootstrap and guarded save-preparation primitives
are complete. The privacy default omits `original_text_preview` from persisted
JSON. The verdict remains to keep live save locked; no route, UI action, Voice
Inbox path, or runtime persistence behavior is authorized.

User-facing persistence should still wait for a separate explicit decision.
It should prefer repo-external user-local app state, should not store raw
transcripts long term, should not ship without a privacy/redaction policy, and
must remain local-only and human-approved.

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

Phase 2C-0/1/2/3a validation should additionally verify:

- storage path helper rejects repo-internal, relative override, and
  traversal-like repo-internal paths;
- dry-run validation rejects missing explicit confirmation, missing privacy
  review, non-`local_only` scope, raw transcript fields, path/file/storage
  fields, and saved- or approved-like preview payloads;
- storage tests use temp dirs or `JARVIS_LOCAL_STATE_DIR`;
- repo-internal tracked paths are not used for user memory;
- atomic write and schema validation paths are covered;
- malformed JSON, oversized input, and path traversal are rejected;
- write helper tests write only inside TemporaryDirectory tests;
- no save endpoint, UI save action, Voice Inbox auto-save, or saved candidates
  dashboard is enabled or available through Phase 2C-3a.

Phase 2C-3b validation should additionally verify:

- the request guard accepts only the actual `127.0.0.1:<port>` Host and matching
  HTTP Origin, approved JSON content types, and a valid session/CSRF pair;
- sessions and preview tokens are bounded, process-local, deterministic under
  fake clocks, and invalidated by expiry or process restart;
- canonical snapshots contain only allowed normalized fields and use
  domain-separated deterministic SHA-256 digests;
- preview tokens are session-bound, digest-keyed, one-time, and never issued by
  the live preview endpoint;
- the subsystem writes no file or directory and remains disconnected from HTTP
  dispatch, UI, and Voice Inbox;
- `POST /api/memory-skills/candidates` remains disabled/non-success.

Phase 2C-3c validation should additionally verify:

- the design distinguishes preview, privacy review, token preparation, final
  confirmation, writing, and skill approval as separate authorities;
- the final-save design trusts only a guarded session and server-held canonical
  snapshot, not client candidate data, paths, timestamps, or digests;
- the reopen checklist covers raw HTTP metadata, one-claim failure behavior,
  restart/recovery, privacy, browser semantics, deterministic HTTP tests, and
  repository cleanliness;
- the privacy decision for persisted `original_text_preview` is explicit and
  defaults to omission;
- no route, UI, Voice Inbox, persistence, or dashboard implementation is
  claimed.

Phase 2C-4a validation should additionally verify:

- token issue rejects missing/false privacy review without allocating a token;
- final composition accepts only the one-time token and exact confirmation
  literal after synthetic request-guard validation;
- wrong Origin/session, extra payload fields, replay, digest corruption, and
  writer failure after claim fail closed without secret/path disclosure;
- a failed write consumes the token and retry with that token cannot write;
- stored candidate JSON omits `original_text_preview`, raw transcript, and path
  fields while preserving the normalized `cleaned_text` candidate;
- all writes occur only inside temporary test state and the coordinator remains
  absent from HTTP dispatch, UI, and Voice Inbox;
- `POST /api/memory-skills/candidates` remains disabled/non-success and preview
  remains write-free/token-free.

Phase 2C-4b validation should additionally verify:

- raw duplicate-preserving header pairs succeed only when every required
  security header occurs exactly once;
- mappings, duplicate/missing headers, Transfer-Encoding, invalid syntax,
  control characters, non-ASCII values, and configured header-count/value
  bounds fail closed;
- Content-Length accepts only canonical non-negative decimal form within the
  configured JSON body limit;
- successful metadata passes the existing request guard, while errors contain
  no session ID, CSRF token, header value, body, or path;
- the adapter remains absent from HTTP handler/dispatch, save remains 404, and
  preview remains write-free/token-free;
- tests leave no runtime state, candidate, listener, cache, or log artifact.

Phase 2C-4c validation should additionally verify:

- the bootstrap contract does not require an existing session or CSRF token and
  does not reuse the guarded-request adapter;
- exact peer, actual-port Host/Origin, no-body framing, optional stale-cookie
  rotation, lifecycle bounds, and restart behavior are decided;
- session cookie and CSRF delivery are separated and no later response may echo
  either credential;
- bootstrap authority is explicitly weaker than privacy review, token issue,
  save confirmation, skill approval, and execution;
- the next implementation unit is route-free/internal-tests-only and no route,
  handler, UI, Voice Inbox, or persistence behavior is claimed.

Phase 2C-4d validation should additionally verify:

- coordinator-owned raw transport validation completes before allocation and
  cannot be bypassed with a directly constructed adapter result;
- exact same-origin no-body requests issue or rotate one bounded process-local
  session while malformed, forbidden, duplicate, and oversized input allocates
  nothing;
- full-capacity behavior is identical for existing and unknown hints;
- generator/collision failure preserves the old session, expiry and restart
  invalidate old credentials, and concurrency never exceeds capacity;
- Cookie material is absent from public JSON and both credentials are absent
  from `repr`, errors, logs, and later responses;
- handler, dispatcher, UI, Voice Inbox, save endpoint, preview behavior, and
  runtime persistence remain unchanged.

Phase 2C-4e validation should additionally verify:

- the coordinator owns raw-header adaptation, exact Content-Length/body
  matching, strict UTF-8 JSON parsing, and nested duplicate-key rejection;
- guarded Host/Origin/media type/session/CSRF checks complete before JSON use,
  while failures allocate no token and echo no request or credential material;
- the exact top-level payload contains only the reviewed candidate and literal
  `privacy_reviewed: true`, followed by server canonicalization;
- success returns one session-bound token, deterministic digest/TTL, and bounded
  display metadata without cleaned text, source preview, paths, Cookie, or CSRF;
- duplicate/capacity/generator/corrupt-result and concurrent attempts fail
  closed without orphaning more than one active token;
- the token remains cross-session protected and the coordinator stays absent
  from handler, dispatcher, preview, UI, Voice Inbox, and persistence code;
- save remains disabled/non-success and preview remains write-free/token-free.

Future live-save validation, if user-facing save is explicitly approved, should
additionally verify:

- save endpoint rejects missing explicit confirmation;
- preview, explicit confirmation, privacy review, and `local_only` scope are
  required;
- Voice Inbox still never calls save automatically;
- saved candidates stay separate from Skill Registry and execution.

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

- Do not expose user-facing persistence without separate explicit approval of
  the approval-gated local save flow.
- Treat Phase 2C-3c as a completed design/reopen review with a `keep locked`
  verdict; do not connect routes, UI, Voice Inbox, or persistence from that
  documentation.
- Keep the implemented Phase 2B preview-only capture flow write-free.
- Keep the implemented Phase 2C-0/1/2/3a/3b/4a/4b/4d/4e helpers
  internal/tests-only, not user-facing save.
- Treat Phase 2C-4c as a completed design-only session-bootstrap contract
  review; it authorizes no route or runtime session issue.
- If separately approved, make the next unit a Phase 2C-4f design/review-only
  live-integration readiness checkpoint. Audit the remaining route allowlist,
  no-store response, browser confirmation/recovery, ephemeral HTTP-test,
  privacy, and operational gates before recommending keep locked or a scoped
  vertical slice.
- Avoid tracked repo user-memory storage.
- Use repo-external user-local app state for any future saved candidates.
- Do not add persistence without privacy/redaction policy.
- Do not let Voice Inbox save automatically.
- Do not call Hermes, Codex, or any external tool automatically.
