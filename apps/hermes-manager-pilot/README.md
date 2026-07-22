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
7. Paste Codex's result back into the browser UI.
8. Click `Copy Review Prompt for Codex`.
9. Approve commit prompt generation only after review passes.
10. Click `Copy Commit Prompt for Codex`.
11. Paste the commit result back and create a checkpoint summary.
12. Reset approval before starting the next task.

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

### C0C-6 Fresh Review Handoff Design

Status: design-only; no C0C-6 application code is implemented.

C0C-6 is split into two separately gated units. C0C-6a would validate a C0C-5
wrapper, reject blocked or later-stage metadata before I/O, recollect one fresh
C0C-2 bundle from the explicitly trusted local root, and return a handoff
preview only when digest, branch, HEAD, and complete status still match exactly.
C0C-6b could later map only that exact preview through
`build_hermes_session()` after checking the review-only renderer conditions.

The fresh decision would still be a repeated local sample, not an atomic
snapshot or authority to execute. No preview may be treated as commit approval,
and a mutation after the final collection sample remains possible. The first
implementation unit is C0C-6a only; session construction, prompt rendering,
route/UI/persistence, command execution, and external communication remain
unimplemented and separately gated.

## Contract

See [contracts/hermes-manager-pilot-v0.1.md](contracts/hermes-manager-pilot-v0.1.md).
