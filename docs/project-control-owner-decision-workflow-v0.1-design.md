# Project Control Owner Decision Workflow v0.1 Design

Status: design-only

This document defines how the owner selects the next Jarvis-Core product
workstream without turning Project Control into an approval, execution, or
persistence surface. It adds no application code, route, UI control, runtime
state, or authority.

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

The workflow uses these conceptual states:

```text
selection_required
  -> selected_for_proposal
  -> package_approval_required
  -> bounded_package_approved | selection_rejected | superseded
```

- `selection_required`: no workstream is inferred and implementation stops.
- `selected_for_proposal`: Codex may explain one bounded package only.
- `package_approval_required`: the owner reviews scope, safety, and outcome.
- `bounded_package_approved`: implementation may follow the standing approved
  work-package rules, including local commit only after validation and clean
  self-review.
- `selection_rejected` or `superseded`: no authority carries forward.

Changing the workstream, desired outcome, target files, route/UI behavior,
persistence, or any locked-capability boundary invalidates the prior package
approval and requires a new proposal. Push and PR always remain separate and
forbidden under the current operating rules.

## 5. Read-only Owner Experience

A future, separately approved complete vertical slice may extend the existing
single-repo Project Control card with:

1. why a direction decision is needed;
2. the six existing workstream names and their current user-visible capability;
3. the safety consequence of choosing each locked or external-facing area;
4. one recommended workstream and the reason for that recommendation;
5. the copy-only `Owner Decision` response template.

The owner makes the decision in the conversation, not through an application
action. The dashboard would remain read-only and reuse the existing
`GET /api/overview` flow. There would be no approve/select button, POST route,
form submission, browser-supplied repository path, runtime persistence,
background worker, or automatic handoff.

The recommended first slice is the `Jarvis Console` workstream: show the bounded
decision candidates and copy-only response format in the existing Owner
Dashboard. This directly reduces document lookup and ambiguity while preserving
the current human conversation as the authority boundary. This recommendation
is not the owner's selection.

## 6. Source And Record Boundary

Until a separate implementation is approved, the current tracked
`docs/master-plan.md` remains the only Project Control direction source. A
human selection or later package approval is reflected there only after the
corresponding explicit conversation-level decision. The document is an
auditable project record, not proof of identity or authorization.

No v0.1 decision registry, browser storage, cookie, token, task file, candidate
JSON, state directory, or cross-app session is introduced. The dormant
multi-project registry remains disconnected, and no second repository is
registered or displayed.

## 7. Safety Boundaries And Non-goals

This design does not authorize or add:

- application code, route, UI control, persistence, or runtime state;
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

## 8. Design Acceptance Criteria

The design is complete when:

1. product direction, work-package approval, Prompt Queue metadata, task
   approval, and Memory confirmation are explicitly separated;
2. an ambiguous `continue` cannot be treated as a workstream selection;
3. selecting a workstream authorizes only a bounded proposal;
4. all six choices remain Jarvis-Core internal workstreams, not repositories;
5. locked capabilities stay locked regardless of the selected workstream;
6. the future user-visible slice is read-only, copy-only, single-repo, and uses
   no new action route or persistence;
7. the current master plan records that an owner decision is still required.

## 9. Recommended Next Decision

The owner should explicitly choose one Jarvis-Core workstream and desired user
outcome. The recommended option is `Jarvis Console` with the outcome “show the
next-workstream choices, consequences, and copy-only decision template in the
single-repo Owner Dashboard.” If selected, Codex should first present the exact
complete vertical-slice work package for approval; it must not infer approval
from this design.
