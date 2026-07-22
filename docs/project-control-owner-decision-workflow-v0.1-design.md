# Project Control Owner Decision Workflow v0.1 Design

Status: v0.1A transport-neutral core and v0.1B read-only Console integration implemented; owner selection pending

This document defines how the owner selects the next Jarvis-Core product
workstream without turning Project Control into an approval, execution, or
persistence surface. The v0.1A core implements the transport-neutral contract,
normalization, stable serialization, Markdown rendering, and stdin/stdout CLI.
The v0.1B consumer adapts the bounded master-plan snapshot into that contract
and renders it through the existing Project Control payload. It adds no new
route, UI action control, runtime state, persistence, or authority.

## 1. Owner Problem

Project Control now shows why the current work exists, what recently completed,
which internal workstreams are waiting or locked, and whether a decision is
needed. After the v0.1D real-use validation, the remaining question is a product
direction decision: which Jarvis-Core workstream should receive the next small
user-visible work package?

An unqualified `continue` is not enough to answer that question. Inferring a
workstream from dashboard order, technical momentum, or dormant primitives could
silently broaden product scope. The owner needs a short, explicit selection that
is easy to make without confusing it with permission to execute code or unlock a
high-risk capability.

## 2. Decision Domains Must Stay Separate

The owner workstream decision is a distinct domain:

| Domain | Meaning | What it does not authorize |
| --- | --- | --- |
| Product workstream selection | Chooses where Codex may propose the next bounded work package | implementation, commit, route, persistence, external action, or a locked capability |
| Work-package approval | Accepts an exact goal, target-file boundary, validation plan, and non-goals | work outside that package, push, PR, external API, or destructive action |
| Prompt Queue scope/review/commit state | Detects whether supplied queue metadata and evidence match a bounded coding stage | authenticated human identity or authority by itself |
| Task `/approve` flow | Drafts a task-status transition for one full task ID | product direction selection or repository execution |
| Memory confirmation | May be considered only inside a separately approved live-save design | general workstream approval or current save activation |

Prompt Queue booleans and digests remain deterministic change-detection
metadata, not signatures or proof of a human decision. The existing task
`/approve` parser remains task-specific and must not be reused for this product
decision. Selecting Memory / Skills does not enable save; selecting Daily AI
Radar does not enable network collection; selecting Task / Discord / Dashboard
does not enable unattended or remote execution.

## 3. Bounded Selection Contract

The v0.1 decision applies to exactly one project, `Jarvis-Core`, and exactly one
of the existing internal workstreams:

1. `Hermes Manager`
2. `Memory / Skills`
3. `Jarvis Console`
4. `Research Council`
5. `Daily AI Radar`
6. `Task / Discord / Dashboard`

The human-readable selection must contain:

```text
Owner Decision
Project: Jarvis-Core
Workstream: <one exact allowed workstream name>
Desired outcome: <one bounded plain-language user result>
Decision: select for work-package proposal
```

This is a copy-only communication contract, not a parser or authenticated
record. A conversational equivalent is acceptable only when the project,
workstream, desired outcome, and intent to request a proposal are all explicit.
`Continue`, `go`, a dashboard status, a digest, or a previous implementation
approval does not resolve the selection gate.

The selection authorizes Codex to prepare one bounded work-package proposal. It
does not authorize implementation. The proposal must separately state its
result type, exact scope, target files, validations, safety boundaries, locked
capabilities, and expected user-visible result. Only explicit approval of that
complete package starts the already-established local implementation workflow.

## 4. Decision States

The v0.1A `OwnerDecision` contract uses only selection-domain states:

```text
selection_required -> selected_for_proposal
selection_required -> selection_rejected
selected_for_proposal -> superseded
```

v0.1A validates one immutable snapshot. It does not persist history or enforce a
transition between two snapshots; a later transition adapter remains outside
this core.

- `selection_required`: no workstream is inferred and implementation stops.
- `selected_for_proposal`: Codex may explain one bounded package only.
- `selection_rejected` or `superseded`: no authority carries forward.

`package_approval_required` and `bounded_package_approved` belong to the
separate work-package approval domain and are deliberately not valid
`OwnerDecision` statuses. A renderer cannot manufacture implementation authority
by changing selection data.

Changing the workstream, desired outcome, target files, route/UI behavior,
persistence, or any locked-capability boundary invalidates the prior package
approval and requires a new proposal. Push and PR always remain separate and
forbidden under the current operating rules.

## 5. Read-only Owner Experience

The implemented v0.1B vertical slice extends the existing single-repo Project
Control card with:

1. why a direction decision is needed;
2. the six existing workstream names and their current user-visible capability;
3. the safety consequence of choosing each locked or external-facing area;
4. one recommended workstream and the reason for that recommendation;
5. the copy-only `Owner Decision` response template.

The owner makes the decision in the conversation, not through an application
action. The dashboard remains read-only and reuses the existing
`GET /api/overview` flow. There is no approve/select button, POST route,
form submission, browser-supplied repository path, runtime persistence,
background worker, or automatic handoff.

That first `Jarvis Console` slice is now complete. The current recommendation is
`Hermes Manager`, to reduce manual prompt and review handoff friction through a
separately proposed bounded improvement. This recommendation is not the owner's
selection or implementation approval.

## 6. Source And Record Boundary

The v0.1A core remains independent of `docs/master-plan.md`, Project Control,
and other data sources. The v0.1B adapter consumes an already bounded snapshot
from the existing tracked master plan, which remains the only live Project
Control direction source. A human selection or later package approval is
reflected there only after the corresponding explicit conversation-level
decision. The document is an auditable project record, not proof of identity or
authorization.

No v0.1 decision registry, browser storage, cookie, token, task file, candidate
JSON, state directory, or cross-app session is introduced. The dormant
multi-project registry remains disconnected, and no second repository is
registered or displayed.

## 7. Safety Boundaries And Non-goals

The v0.1A core and v0.1B consumer do not authorize or add:

- a new route, UI action control, persistence, or runtime state;
- automatic workstream inference or implementation from an ambiguous message;
- authenticated identity, signatures, approval tokens, or a general approval
  service;
- Prompt Queue approval creation, prompt execution, staging, push, or PR;
- an external API, LLM call, API key, credential, or network collection;
- destructive change, background execution, mobile execution, or remote access;
- a second repository, repository picker, arbitrary path, or multi-project UI;
- Memory save endpoint, UI Save/Confirm, Voice Inbox auto-save, or saved
  candidates dashboard.

`jarvis.bat` remains protected and untracked. Existing local commit permission
inside an explicitly approved work package does not give Jarvis Console or
Hermes Manager application-level commit authority.

## 8. Acceptance Criteria

The design is complete when:

1. product direction, work-package approval, Prompt Queue metadata, task
   approval, and Memory confirmation are explicitly separated;
2. an ambiguous `continue` cannot be treated as a workstream selection;
3. selecting a workstream authorizes only a bounded proposal;
4. all six choices remain Jarvis-Core internal workstreams, not repositories;
5. locked capabilities stay locked regardless of the selected workstream;
6. the user-visible slice is read-only, copy-only, single-repo, and uses
   no new action route or persistence;
7. normalization, serialization, Markdown rendering, and CLI behavior are
   deterministic and fail closed;
8. the current master plan records that owner selection remains separate from
   implementation approval.

## 9. v0.1A Transport-neutral Core Result

The core is implemented in `apps/jarvis-console/owner_decision.py` as frozen,
slotted `OwnerDecision` and `OwnerDecisionCandidate` contracts. It requires the
exact six Jarvis-Core workstreams, fixes authority to
`work_package_proposal_only`, validates status/selection relationships, rejects
unknown or duplicate JSON fields, bounds text and JSON sizes, and canonicalizes
candidate and locked-capability order before stable serialization.

`apps/jarvis-console/render_owner_decision.py` reads bounded JSON from stdin and
writes deterministic Markdown or canonical JSON to stdout. It accepts no input
path and creates no file or runtime state. The pure Markdown renderer
revalidates the immutable object and does not mutate it.

Deterministic tests cover immutability, stable serialization, reordered input,
Markdown escaping, selected/unselected relationships, malformed and oversized
input, duplicate keys and candidates, noncanonical direct instances, CLI
success/failure output, and forbidden filesystem/network/integration imports.

Implementation commit:
`58d4767d4f7c3ca53bff4cebd195d9c15665d91a`.

## 10. v0.1B Result And Next Decision

`apps/jarvis-console/owner_decision_data.py` converts the bounded master-plan
snapshot into one normalized `OwnerDecision`. `run_web_app.py` serializes that
object into the existing Project Control payload, and `web/app.js` renders the
six candidates and response template without a control or new fetch. The core
contract remains authoritative; the adapter and UI consume but do not redefine
it.

Deterministic tests and local browser QA verified one decision section, six
candidates, one recommendation, zero button/form controls, and zero browser
warning/errors. Implementation commits:
`e6305a7d4833bdeb3264bab09cfaacc5bcf6f267` and
`e6ef70b15a9c3d7f15369b7baf1b5008ea0ab10f`.

The next step is not another implementation primitive. The owner must choose
one exact workstream and bounded desired outcome using the response contract.
That selection authorizes only a work-package proposal. All route, persistence,
action, external-call, automatic-execution, second-repository, and Memory-save
boundaries remain locked.
