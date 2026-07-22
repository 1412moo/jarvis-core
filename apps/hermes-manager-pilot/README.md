# Hermes Manager Pilot

Hermes Manager Pilot is a Jarvis-Core app module for testing Hermes as a middle
manager in the Jarvis-Core development workflow. It started as a v0.1
design-only contract and now includes local-only v0.2-v0.4 helper tools plus
internal Prompt Queue v0.1A, approval-binding v0.1B-1, and evaluator-enforcement
v0.1B-2 primitives, plus internal local change-evidence collection v0.1C-0A
and integrity verification v0.1C-0B, followed by bounded whole-worktree evidence
and review-observation helpers through v0.1C-0C-4.

Hermes is not a coding worker. Hermes does not replace Codex. Hermes helps
manage Codex work by preserving context, waiting for responses, summarizing
results, suggesting next actions, and preparing safe prompts for the user to
approve.

## Purpose

Jarvis-Core is moving toward a personal AI assistant that can coordinate memory,
skills, multiple AI employees, and human-approved self-improvement. Today, the
user manually coordinates this loop:

```text
user
-> ChatGPT planning conversation
-> Codex implementation prompt
-> Codex result
-> ChatGPT review
-> Codex fix or commit prompt
```

Hermes Manager Pilot explores whether Hermes can hold the middle-management
state for this loop without becoming an autonomous implementer.

Response waiting means tracking what answer is needed next. It does not
authorize background execution, automatic Codex calls, or unattended commits.

## Role

Hermes acts as a response-waiting and workflow-management layer.

Example responsibilities:

- Maintain a short Jarvis-Core status summary.
- Track the current goal, blocked state, and last Codex result.
- Draft implementation prompts for Codex.
- Summarize Codex results for the user.
- Draft commit-before-review prompts.
- Maintain validation command checklists.
- Preserve excluded-file notes such as `jarvis.bat` must not be touched.
- Convert repeated workflow patterns into skill candidates.
- Propose next actions while leaving approval authority with the user.

Hermes must not:

- Edit repository files.
- Run Codex automatically.
- Call ChatGPT automatically.
- Commit or push changes.
- Treat any test as passed without evidence.
- Turn Daily AI Radar recommendations directly into implementation.

## Relationship To ChatGPT, Codex, And Jarvis-Core

| Actor | Role |
| --- | --- |
| User | Final approver and owner of decisions. |
| ChatGPT | Planning, review, and reasoning partner. |
| Codex | Coding agent that reads, edits, tests, and commits only when explicitly instructed. |
| Hermes | Middle manager that tracks state, waits for responses, prepares prompts, and recommends next actions. |
| Jarvis-Core | Source of truth for orchestration rules, records, contracts, and AI employee design. |

Hermes does not replace ChatGPT or Codex. It coordinates the workflow around
them and keeps the handoff state visible.

## v0.1 Scope

Included in v0.1:

- Document the Hermes middle-manager role.
- Define a session/state contract.
- Define prompt, review, commit, escalation, and skill-candidate boundaries.
- Provide sample session, Codex prompt, and review checklist examples.
- Preserve human approval as the authority boundary.

## v0.1 Non-Goals

Out of scope for v0.1:

- No Hermes installation.
- No Hermes runtime execution.
- No Hermes API integration.
- No MCP or A2A integration.
- No Codex automatic invocation.
- No ChatGPT automatic invocation.
- No scheduler.
- No crawler.
- No database.
- No Discord command.
- No web search.
- No LLM/API call.
- No code modification.
- No automatic commit or push.
- No changes to Research Council, Daily AI Radar, Discord/web adapters, task
  memory, report schemas, snapshots, history, hashes, or tests.

## Basic Operating Flow

```text
user goal
-> Hermes creates a bounded Codex implementation prompt
-> user approves or edits the prompt
-> Codex works and reports result
-> Hermes summarizes result and creates a review prompt
-> user approves or edits the review prompt
-> Codex reviews and reports findings
-> Hermes creates a commit prompt only if the user explicitly asks to commit
-> Codex commits only after validation, status, staged diff, and exclusions are checked
-> Hermes records a checkpoint summary
```

The v0.1 module is documentation-only. It does not automate this flow.

## v0.2 Local Renderer Usage

v0.2 adds a local deterministic session and prompt renderer. It reads a local
session state JSON file, validates the management boundary, and renders one
Markdown artifact to stdout unless an output path is explicitly supplied.

It still does not install or run Hermes, call Codex, call ChatGPT, use a network
or API, create tasks, apply source-code changes, commit, push, schedule
background work, or integrate with MCP/A2A/Discord/DB systems.

Render an implementation prompt to stdout:

```powershell
python -B apps\hermes-manager-pilot\run_demo.py `
  --input apps\hermes-manager-pilot\examples\sample-session-state.json `
  --mode implementation-prompt
```

Render a checkpoint summary only when an output path is explicitly supplied:

```powershell
python -B apps\hermes-manager-pilot\run_demo.py `
  --input apps\hermes-manager-pilot\examples\sample-session-state.json `
  --mode checkpoint-summary `
  --output C:\work\hermes-checkpoint.md
```

Supported modes:

- `implementation-prompt`
- `review-prompt`
- `commit-prompt`
- `checkpoint-summary`

Run the local smoke tests:

```powershell
python -B apps\hermes-manager-pilot\run_smoke_tests.py
```

The sample fixture keeps `commit_allowed=false`, `push_allowed=false`,
`human_approval_required=true`, and `human_approval_granted=false`. A commit
prompt rendered from that fixture is a refusal boundary, not commit approval.
Even if `commit_allowed=true`, v0.2 renders an approval-needed boundary until
`human_approval_granted=true` is explicitly present in the local session state.

## v0.3 Local GUI Launcher

v0.3 adds a local-only tkinter launcher around the existing session validator
and prompt renderer. It uses a workflow guide plus `Primary`, `Advanced`, and
`Output` tabs so normal use starts with task description instead of raw session
state.

It still does not run Hermes, call Codex, call ChatGPT, use the network, create
tasks, apply source-code changes, commit, push, schedule background work, or
integrate with MCP/A2A/Discord/DB systems.

Start the GUI:

```powershell
python -B apps\hermes-manager-pilot\run_local_app.py
```

Run the GUI helper self-test without opening a window:

```powershell
python -B apps\hermes-manager-pilot\run_local_app.py --self-test
```

The GUI keeps `push_allowed=false`, includes `jarvis.bat` in default protected
paths, and separates `commit_allowed` from `human_approval_granted`. Without
granted human approval, generated commit prompts remain a no-commit boundary.

## Using The GUI For Codex Workflow

Use the GUI as a local prompt drafting surface for the existing ChatGPT/Codex
loop:

1. Load Git Status.
2. Describe the task in `Current goal`, `Active task`, and expected files.
3. Generate Implementation Prompt and copy it into Codex.
4. Paste the Codex result into `Latest Codex result summary`.
5. Generate Review Prompt.
6. Approve commit only when ready.
7. Enter a commit message and generate Commit Prompt.
8. Generate Checkpoint Summary after the commit result is known.
9. Reset Approval before the next task.

Use `Last prompt/action summary` for the most recent prompt, commit result, or
workflow note. Use `Latest Codex result summary` for the newest Codex output
that should be reviewed or checkpointed.

Generate a commit prompt only after explicit user approval. The GUI does not
call Codex, call ChatGPT, run Hermes, create tasks, modify files, commit, push,
or add live integrations. Before checkpoint summaries, the GUI refreshes git
status with read-only commands so the HEAD field is less likely to be stale.

## v0.4 Browser Guided UI

Recommended: use the browser guided UI for normal Codex workflow prompting.
The tkinter launcher remains a local legacy helper, but the browser UI is
designed around one current action and an always-visible generated output
panel.

Start the local browser UI:

```powershell
python -B apps\hermes-manager-pilot\run_web_app.py
```

Run without opening a browser automatically:

```powershell
python -B apps\hermes-manager-pilot\run_web_app.py --no-browser
```

Choose a local port:

```powershell
python -B apps\hermes-manager-pilot\run_web_app.py --port 8788
```

Run the browser UI self-test:

```powershell
python -B apps\hermes-manager-pilot\run_web_app.py --self-test
```

The server binds to `127.0.0.1` only. It serves local HTML/CSS/JS and exposes
local-only endpoints for preparing session metadata, rendering prompts,
validating session data, and reading git status with read-only commands.

Browser guided workflow:

1. Describe the task in `What do you want Codex to do?`.
2. Click `Prepare Session`.
3. Confirm the prepared scope. Review the target files, validation command
   count, and suggested commit message. If `NEEDS_USER_CONFIRMATION` appears,
   replace it with the exact intended path before continuing.
4. Click `Continue To Task Prompt`.
5. Click `Copy Task Prompt for Codex`.
6. Paste the generated prompt into Codex.
7. Paste or type Codex's result into the visible result field.
8. Click `Save Review Object and Continue`. The in-memory Review object becomes
   authoritative for the current task and confirmed target-file scope.
9. Click `Copy Jarvis Review Handoff` whenever the handoff is needed. Hermes
   regenerates it from the saved Review object and fresh local Git metadata.
10. Paste the copied JSON once into Jarvis Console Codex Review.
11. Alternative: click `Copy Review Prompt for Codex` for the existing direct
   review path.
12. Approve commit prompt generation only after review passes.
13. Click `Copy Commit Prompt for Codex`.
14. Paste the commit result back and create a checkpoint summary.
15. Reset approval before starting the next task.

The browser UI does not call Codex, call ChatGPT, run Hermes, use external
network services, modify repository files, run `git add`, commit, or push.
Commit approval only changes local session state so a commit prompt can be
rendered for the user to paste into Codex.

## Prompt Queue v0.1A Internal Primitives

Prompt Queue v0.1A established an in-memory schema and conservative safety evaluator
for future multi-project prompt coordination. It is an internal/tests-only
primitive, not a user-facing queue or an autonomous worker.

The current primitive can:

- Normalize multiple project cards and queue items.
- Keep expected branch, HEAD, protected paths, and known untracked paths
  separate from caller-supplied Git observations.
- Classify design, implementation, review, commit, and blocked result types.
- Convert branch, HEAD, scope, protected-path, staged-change, or approval
  mismatches to `BLOCKED_NEEDS_USER`.
- Require separate scope, review, and commit approval states.
- Map a safe result into the existing Hermes session renderer contract while
  keeping `push_allowed=false`.

The current primitive does not:

- Read a repository, execute Git, or validate claims against the filesystem.
- Persist project cards, queue items, approval state, prompts, or results.
- Add an HTTP route, browser API, GUI panel, dashboard, or mobile workflow.
- Call Codex, ChatGPT, Hermes, an external API, or an LLM.
- Modify files, stage changes, commit, push, or create a pull request.
- Treat approval booleans as authenticated proof of a human decision.

`repo_path` is metadata only, and all observed Git evidence must be supplied by
an internal caller. Prompt Queue v0.1A remains route-free. Approval binding is
not part of the v0.1A evaluator and is not enforced by its boolean approval
fields.

## Prompt Queue v0.1B-1 Approval-Binding Primitives

Prompt Queue v0.1B-1 adds deterministic, domain-separated approval-binding
primitives for normalized project cards and queue items. The primitives remain
internal/tests-only; v0.1B-2 connects them to the queue evaluator as described
below.

The binding chain has three purposes:

- Scope binding covers project identity, repository metadata, expected branch
  and HEAD, protected paths, known untracked paths, forbidden actions,
  validation commands, goal, task, and exact target files.
- Review binding covers the current scope digest, caller-supplied change
  evidence digest, observed branch and HEAD, and observed Git status.
- Commit binding covers the current scope and review digests, the same change
  evidence digest, observed Git state, and exact commit message.

Each purpose uses a different domain-separated SHA-256 prefix. A changed scope,
review evidence, Git observation, or commit message makes the prior binding
stale. Malformed digests, wrong result stages, and oversized canonical
snapshots are rejected.

These digests provide deterministic change detection only. They are not
signatures, secrets, one-time tokens, authenticated human approval, or
permission to execute. `change_evidence_digest` is caller-supplied and has no
trusted evidence collector in v0.1B-1 or v0.1B-2.

Prompt Queue v0.1B-1 does not read Git or the filesystem, persist data, expose a
route or UI, execute a prompt or command, stage, commit, push, create a pull
request, or call an external service.

## Prompt Queue v0.1B-2 Evaluator Enforcement

Prompt Queue v0.1B-2 changes the accepted internal queue schema version to
`0.1B-2` and adds these queue-item fields:

- `scope_approval_digest`
- `change_evidence_digest`
- `review_approval_digest`
- `commit_approval_digest`

The evaluator now requires approval booleans and their corresponding current
bindings to agree:

- Implementation requires an approved, matching scope binding.
- Review requires the matching scope binding and a bounded change-evidence
  digest. A passed review also requires a matching review binding.
- Commit requires matching scope, evidence, review, and commit bindings plus
  the exact approved commit message.
- Design and blocked items reject leftover approval metadata.
- Approval metadata from a later stage is rejected in an earlier stage.

Missing, malformed, stale, or stage-inappropriate binding metadata produces
`BLOCKED_NEEDS_USER`. Explicit legacy `version=0.1A` queue input is rejected
rather than silently upgraded. The existing `build_hermes_session()` path uses
the same evaluator, so stale commit approval cannot bypass enforcement through
renderer mapping.

v0.1B-2 is still internal/tests-only. It does not authenticate a user or prove
that change evidence came from Git. It adds no trusted evidence collector,
filesystem access, persistence, HTTP/API/GUI route, automated prompt execution,
staging, commit, push, pull request, network, or external-service behavior.

## Prompt Queue v0.1C-0A Local Change-Evidence Collector

Prompt Queue v0.1C-0A adds a bounded, local-only collector for normalized
project cards and review or commit queue items. The caller must supply an
explicitly trusted absolute local repository root. The collector verifies that
the root matches both the declared project path and Git top-level, then reads
the expected branch, HEAD, and status for only the exact target files and known
untracked paths.

The collector rejects unsafe or protected paths, UNC/device-prefixed roots,
symlink/reparse traversal, directories, staged or conflicted targets,
rename/copy status, oversized inputs, and repository changes detected between
collection passes. It hashes exact target contents without placing raw content
in the canonical manifest. Fixed read-only Git commands run with a sanitized
environment, disabled hooks and file-system monitor, optional locks disabled,
and bounded output and timeout limits.

v0.1C-0A remains internal/tests-only and route-free. Its status is explicitly
scoped rather than a whole-repository observation. Its digest is deterministic
change evidence, not a signature, secret, token, human identity check, approval,
or authority to execute. The collector is not connected to the queue evaluator,
approval bindings, HTTP/API/GUI, persistence, prompt execution, staging,
committing, pushing, or pull-request creation. It performs no external API,
LLM, or explicit network-client call and does not write evidence or application
state.

The later C0C design now binds repeated collector output into a review-evidence
bundle and a fail-closed observation adapter. It still does not update queue
state or supply human approval authority. Route, UI, persistence, and unattended
workflow remain separate and out of scope.

## Prompt Queue v0.1C-0B Evidence Integrity Verification

Prompt Queue v0.1C-0B supersedes the emitted evidence manifest version while
retaining the v0.1C-0A collection boundary. The manifest now exposes project
and item identity plus the declared repository path as typed fields and binds
the declared path into canonical bytes under a new v0.1C-0B domain prefix.

The new pure verifier checks type and version, project/item identity, local
absolute repository paths, expected branch and HEAD, exact status scope and
targets, canonical status ordering, target metadata bounds, canonical bytes and
byte size, and the domain-separated digest. Verification reads neither Git nor
the filesystem and does not modify the queue item.

Integrity verification does not prove provenance. The digest is unkeyed, so a
caller that constructs a new manifest can also compute a new digest. v0.1C-0B
therefore remains internal/tests-only, non-authoritative, route-free, and
disconnected from the queue evaluator and approval-binding chain.

The collected Git status is still explicitly scoped to target files and known
untracked paths. It must not be copied into `observed_git_status` as though it
were a complete working-tree observation. C0C-1 through C0C-4 provide separate
whole-worktree coverage and fail-closed mapping; actual queue integration is
still not implemented.

## Prompt Queue v0.1C-0C Whole-Worktree Evidence

Status: v0.1C-0C-1 bounded collector, v0.1C-0C-2 composite bundle,
v0.1C-0C-3 pure handoff decision, v0.1C-0C-4 queue observation adapter, and
v0.1C-0C-5 pure queue observation evaluator implemented as internal/tests-only.

v0.1C-0C keeps v0.1C-0B target-content evidence and adds a separate,
bounded observation of the complete Git-visible working tree. A composite
review-evidence bundle binds both artifacts to the same project, item, resolved
root, branch, HEAD, and repeated collection window. Only the complete
status—not scoped status—can populate a queue observation preview.

The selected design rejects two shortcuts: treating scoped status as complete,
and replacing explainable status with a clean/dirty boolean. Whole-worktree
status must preserve every Git-visible changed path, including unexpected
paths, so a fail-closed decision can explain why handoff is blocked. Ignored
files and non-Git filesystem state remain outside the claim.

C0C-1 uses fixed local read-only Git commands, sanitized environment settings,
bounded pipe readers, explicit output/entry/time limits, and repeated state
sampling. Exceeding a bound, encountering unsupported status, or observing a
state change blocks evidence creation. It preserves unexpected paths and
returns no file contents. Collector code does not explicitly open or hash
out-of-target files, but Git may inspect working-tree files while computing
status. The pure verifier performs no Git or filesystem read. This is not an
atomic filesystem snapshot and retains that residual race boundary.

C0C-1 adds no route, UI, persistence, evaluator integration, QueueItem mutation,
approval authority, staging, commit execution, or network call. It is not yet
allowed to populate queue observation fields by itself.

C0C-2 repeatedly samples whole status and exact target evidence, rejects any
change between samples, verifies status agreement, and binds the two nested
digests into a small domain-separated review-evidence bundle. Bundle verification
is pure and the composite remains unkeyed, non-authoritative, and disconnected
from the queue evaluator.

C0C-3 verifies the bundle and returns either deterministic blocking reasons with
no preview, or an immutable preview containing complete status and the composite
digest. Protected and out-of-scope paths, missing target changes, malformed
evidence, and target/expected-untracked overlap fail closed. The decision does
not mutate a QueueItem, set approvals, build approval bindings, or call the
evaluator.

C0C-4 applies only a safe C0C-3 preview to a new review-stage `QueueItem`. It
replaces exactly `observed_branch`, `observed_head`, complete
`observed_git_status`, and `change_evidence_digest`; the original item and all
scope, review, commit, prompt, and result metadata remain unchanged. Existing
evidence, passed-review metadata, commit-approval metadata, unsafe status, and
tampered bundles fail closed. The adapter performs no Git/filesystem read and
does not normalize or mutate queue state, call the evaluator, create an approval
binding, or expose route/UI/persistence/execution behavior. Queue persistence,
renderer/execution, and approval-flow integration remain separately gated.

### C0C-5 Queue Observation Evaluation

Status: implemented as internal/tests-only; no route, UI, or persistence is
connected.

The bounded bridge accepts an already normalized in-memory `PromptQueueState`,
one item ID, and a C0C-2 bundle. It uses C0C-4 to create a replacement review
item, places only that item into a new immutable queue snapshot, runs the
existing `evaluate_queue_item()` against the new snapshot, and returns both the
snapshot and evaluation. An evaluator-blocked result remains blocked and visible
rather than becoming an exception or authorization.

This bridge does not read Git, recollect evidence, normalize untrusted JSON,
mutate or persist queue state, create approval metadata, render or execute a
prompt, or expose route/UI/network behavior. It evaluates the captured evidence
snapshot; it does not prove that the working tree is still current. Collection
or stale-state revalidation at a later execution boundary remains separately
gated.

### C0C-6 Fresh Review Handoff

Status: C0C-6a and C0C-6b remain internal/tests-only primitives. A separately
approved Jarvis Console consumer now calls them through a write-free local
preview route and displays bounded review-session fields. No Hermes renderer,
route, or persistence was added.

C0C-6 is split into two separately gated units. C0C-6a validates a C0C-5
wrapper, rejects blocked or later-stage metadata before I/O, recollects one fresh
C0C-2 bundle from the explicitly trusted local root, and returns a handoff
preview only when digest, branch, HEAD, and complete status still match exactly.
C0C-6b accepts only that exact preview, recomputes its queue evaluation, maps it
through `build_hermes_session()`, and rejects any session that does not preserve
the exact review data and review-only safety conditions.

The fresh decision is still a repeated local sample, not an atomic
snapshot or authority to execute. No preview may be treated as commit approval,
and a mutation after the final collection sample remains possible. Jarvis
Console displays review fields only; prompt rendering, queue/session persistence,
command execution, approval creation, and external communication remain
unimplemented and separately gated.

### Copy-only Jarvis Review Handoff

Status: implemented and verified with one real local Codex work package.

After the existing `Confirm Scope` step and a pasted Codex result, Hermes can
build one deterministic `queue + item_id` envelope through
`POST /api/review-handoff`. The route fixes read-only Git inspection to the
Jarvis-Core root and requires `jarvis.bat` to remain protected and untracked.
It represents the explicitly confirmed scope with the existing scope-binding
primitive; that digest detects drift and is not proof of identity or authority.

The user copies the JSON manually into Jarvis Console. Hermes does not call the
Jarvis server. The envelope contains no fresh evidence digest, review approval,
commit approval, commit message, push permission, or execution authority.
Neither app persists the envelope or session. Jarvis recollects fresh bounded
evidence and may still block the handoff.

The guided UI stores an explicitly submitted result as a frozen in-memory
Review object bound to the current task and confirmed target-file scope. Every
`Copy Jarvis Review Handoff` regenerates the artifact from that object and fresh
local Git metadata, so clearing output or changing the clipboard does not lose
or replace review state. Hermes never reads the clipboard programmatically;
clipboard access is write-only output from explicit Copy actions.

The working Review object remains process-local and is cleared by reset, a new
prepared session, or page reload unless the user separately completes the
explicit Durable Review Save flow described below. Clipboard output is never
used as persistence or continuity state. Cross-device continuity remains
unimplemented.

Deterministic tests cover stable serialization, exact fields, stale/absent scope
confirmation, trusted repository authority, missing `jarvis.bat`, and forbidden
approval/side-effect operations. Full Hermes/Jarvis smoke suites and a real-work
browser path passed with zero browser errors.

## Durable Review Record v0.1A Core

Status: implemented as a transport-neutral core contract. v0.1C consumes this
contract, but the record model itself remains independent of routes and UI.

The immutable `ReviewRecordCandidate`, `ReviewGitSnapshot`, and `ReviewRecord`
contracts capture one privacy-reviewed, bounded result summary together with the
Jarvis-Core goal, task, target files, validation commands, and the exact branch,
HEAD, and `git status --short` snapshot at capture time. Target and status sets
are canonically ordered, duplicate or unsafe paths fail closed, staged changes
are rejected, changes outside the declared target scope are rejected, and
`jarvis.bat` must remain protected and untracked.

Review IDs are generated independently of user text. Stable JSON serialization
and a pure freshness decision allow a future consumer to block when current Git
metadata no longer matches the captured record. A Review record always remains
read-only with review, commit, and push authority false. The privacy-reviewed
field is a caller assertion, not proof that arbitrary text is safe; raw Codex
responses, file contents, private messages, secrets, credentials, and hidden
reasoning are outside the contract.

v0.1A itself performs no filesystem or Git read, creates no directory or file,
exposes no route or UI, reads no clipboard, and calls no external service. The
separately approved v0.1B-1 store and v0.1C lifecycle consume it. Cross-device
continuity and mobile access remain separate approval gates.

## Durable Review Store v0.1B-1 Internal Primitives

Status: implemented as route-free local store primitives. The separately
approved v0.1C lifecycle calls them through bounded local-only routes. Existing
manual Session Save/Load remains a different file format and storage flow.

The store resolves the shared Jarvis local-state root and uses the dedicated
`hermes-manager/reviews/v1` namespace. Windows defaults to
`%LOCALAPPDATA%\Jarvis-Core`; other systems default to `~/.jarvis-core`.
`JARVIS_LOCAL_STATE_DIR` may override the root only with an absolute path.
Repository-internal state, symlink/reparse paths, unsafe entries, and arbitrary
record filenames fail closed.

`write_review_record` accepts only a canonical v0.1A `ReviewRecord`, writes one
private exclusive temporary file, flushes and fsyncs it, and atomically
publishes a no-overwrite hard link. It never updates an existing Review ID.
`read_review_record` accepts one generated ID and requires a bounded regular
file, strict UTF-8, exact canonical bytes, a stable file snapshot, and matching
internal ID. `list_review_records` performs an index-free bounded scan and
returns metadata only; result summaries and absolute paths are omitted.

The store holds at most 256 records and never evicts old data. Its retention
policy is `manual_delete_only`: records remain until the user completes the
v0.1C exact-ID delete confirmation. Orphan temporary files, foreign entries,
corrupt records, and capacity overflow block the relevant operation and are not
automatically removed or repaired. Exact-ID read remains available when an
unrelated orphan temporary file needs recovery.

File fsync plus no-overwrite atomic publication protects against partial normal
process writes, but v0.1B-1 does not claim filesystem-wide power-loss recovery,
encryption at rest, user authentication, or cross-process transactional locking.
There is no archive/migration, automatic cleanup, external call, clipboard
input, approval, execution, commit, push, or PR.

## Durable Review Local Lifecycle v0.1C

Status: implemented as a local-only, human-confirmed user vertical slice in
commit `2d564e544a32c2ce839364fd3ba8cf76e9f70abb`.

The browser can now explicitly preview and confirm one durable Review Save,
list bounded metadata, reopen one exact record read-only, inspect an exact ID
for ambiguous Save recovery, preview one exact deletion without result text,
and delete that record only after the user types `DELETE <review_id>`.

Save preview is write-free. It captures fresh trusted Jarvis-Core branch, HEAD,
and complete `git status --short` metadata, requires confirmed target scope plus
separate privacy and retention acknowledgements, and issues a five-minute
single-use Save token bound to the local server session and immutable record.
Save confirmation recollects Git metadata and blocks if the snapshot changed.
An uncertain post-publish outcome returns the generated ID so the user can run
exact-ID recovery inspection instead of retrying blindly.

Delete uses a different operation-domain token. The preview omits result text
and shows ID, creation time, task, branch, HEAD, target count, digest, and the
exact confirmation text. Confirmation re-reads the canonical record and checks
the preview digest and file identity immediately before deleting one path. A
missing, changed, or corrupt target fails closed. Bulk delete, glob targeting,
automatic expiry, background cleanup, orphan cleanup, and corrupt-record
deletion are not available.

Lifecycle routes require JSON, an in-memory server-restart session header, an
exact same-origin request, loopback Host validation, and local client address.
Responses deny framing and include a same-origin content security policy. The
session and confirmation tokens are memory-only and never written to the Review
store. The store remains local, unencrypted, not cloud-synced, and retained
until exact manual deletion.

Reopen and recovery do not restore review, commit, push, or execution approval.
Memory / Skills candidate save remains disabled and separate. Hermes still does
not call Codex, ChatGPT, Jarvis, an external API, or an LLM; does not auto-save;
and does not stage, commit, push, or create a PR.

See [Durable Review Local Lifecycle v0.1C](../../docs/hermes-durable-review-lifecycle-v0.1.md)
for the route, confirmation, recovery, and security contract.

## Contract

See [contracts/hermes-manager-pilot-v0.1.md](contracts/hermes-manager-pilot-v0.1.md).
