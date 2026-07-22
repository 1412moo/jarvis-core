# Project Control Single-repo Workstream Visibility v0.1D Design

Last updated: 2026-07-22

Status: implemented and locally verified on 2026-07-22.

Implementation commit: `e69dbea27a1f77d0b9fe40fc4f5ca76eb13e37fb`.

The implementation adds no new route, persistence, repository connection, or
action authority.

## 1. Owner Outcome

Project Control should let a non-developer owner understand within 30 seconds:

- why the current Jarvis-Core work is being done;
- what the owner gains when the current stage is complete;
- which internal workstreams are complete, active, locked, or waiting;
- what finished recently, what milestone is current, and what comes next;
- whether a human decision is currently required.

The dashboard remains an observation surface for one repository. Jarvis Console,
Hermes Manager, Memory / Skills, Research Council, Daily AI Radar, and Task /
Discord / Dashboard are Jarvis-Core workstreams, apps, or capabilities. They are
not separate projects.

## 2. Smallest Safe Flow

```text
tracked docs/master-plan.md
  -> bounded current-baseline parser
  -> bounded internal-workstream table parser
  -> one Jarvis-Core owner-card payload
  -> existing GET /api/overview
  -> read-only Owner Dashboard sections
```

There is no registry file, second repository, path input, discovery, new route,
write request, or runtime state in this flow. The dormant v0.1B/v0.1C
multi-project foundation is not imported or connected.

## 3. Trusted Source Contract

The only direction source is the existing tracked `docs/master-plan.md` inside
the server-owned Jarvis-Core root. The existing regular-file, trusted-root,
UTF-8, 128KB, duplicate-field, missing-field, and 500-character value boundaries
remain mandatory.

### 3.1 Owner summary fields

The existing `## 2. 현재 기준점` snapshot gains these exact one-line fields:

```text
- Current reason: <plain-language reason>
- Owner outcome: <plain-language result>
- Recent completed: <most recent meaningful result>
- Approval state: none | required | blocked
- Approval note: <plain-language decision or reason>
```

`Current reason` and `Owner outcome` are mandatory and must be shown before
technical stage codes. Missing, duplicated, empty, oversized, or invalid
`Approval state` values fail closed. The existing baseline fields remain
required and keep their current meaning.

### 3.2 Internal workstream table

The existing `## 5. 작업 축별 상태` table remains the workstream source. The
first slice accepts only this exact four-column shape:

```text
작업 축 | 현재 상태 | 사용자에게 보이는 기능 | 다음 안전 단계
```

The allowed, deterministic display order is:

1. Hermes Manager
2. Memory / Skills
3. Jarvis Console
4. Research Council
5. Daily AI Radar
6. Task / Discord / Dashboard

The parser must reject a missing section, changed header, missing or extra row,
duplicate workstream, empty cell, control character, overlong cell, or unknown
workstream. It must never infer repositories, paths, commands, approval, or
execution authority from prose in the table.

## 4. Presentation Payload

The existing `project_control` object remains inside `GET /api/overview`, stays
`mode: read-only`, and contains exactly one `jarvis-core` project card. The live
contract advances to `project_control.v0.1D` only when the complete vertical
slice is implemented and verified.

The card keeps its current repository facts and adds bounded presentation data:

```json
{
  "owner_summary": {
    "current_reason": "...",
    "owner_outcome": "...",
    "recent_completed": "...",
    "current_milestone": "...",
    "recommended_next_step": "...",
    "next_user_visible_milestone": "...",
    "approval_state": "none",
    "approval_note": "..."
  },
  "workstreams": [
    {
      "workstream_id": "hermes-manager",
      "display_name": "Hermes Manager",
      "status_summary": "...",
      "user_visible_capability": "...",
      "next_safe_step": "...",
      "read_only": true
    }
  ],
  "locked_capabilities": ["..."]
}
```

`locked_capabilities` reuses the server-owned Project Control forbidden-action
boundary. It does not come from browser input and does not grant an action when
an item is absent. Existing fields may remain for compatibility during v0.1D.

## 5. Owner Dashboard UX

The existing Project Control tab is extended in this order:

1. `현재 만드는 이유`
2. `이 단계가 끝나면 사용자가 얻는 것`
3. recent completion, current milestone, next step, and approval state
4. internal workstream status cards
5. locked capabilities and live repository facts

Technical codes such as `v0.1D` remain visible but secondary. Every value is
HTML-escaped. The only control remains the existing read-only refresh button.
There is no Save, Confirm, approve, execute, stage, commit, push, PR, repository
picker, path field, or second-project card.

## 6. Complete Vertical Slice Boundary

The implementation was completed as one user-visible work package, not another
standalone primitive chain.

In scope:

- extend the bounded master-plan snapshot and workstream-table parser;
- add the owner summary and workstream list to the one-card payload;
- render the ordered read-only sections in the existing Project Control tab;
- add deterministic parser, payload, UI-contract, and browser validation;
- sync current documentation after verification.

Out of scope:

- importing or wiring `project_control_registry.py`;
- registering, reading, or displaying a second repository;
- browser-supplied paths, automatic discovery, or parent-directory scanning;
- a new route, POST request, runtime config, persistence, or background worker;
- approval/action buttons or automatic stage, commit, push, or PR;
- external API, LLM, credential, or cross-app invocation;
- Memory save endpoint, UI Save/Confirm, Voice Inbox save, or saved candidates.

## 7. Deterministic Validation

The implementation work package verified:

1. the current master plan produces exactly one Jarvis-Core card and the six
   ordered internal workstreams;
2. owner reason and owner outcome are present and rendered ahead of technical
   details;
3. missing, duplicate, unknown, malformed, empty, controlled, and oversized
   source values fail closed without a stale fallback;
4. approval state is restricted to `none`, `required`, or `blocked`;
5. the payload and UI expose no absolute path, raw file content, secret,
   approval authority, prompt, command execution, or mutation action;
6. `POST /api/memory-skills/candidates` remains non-success, preview remains
   write-free/token-free, and Voice Inbox remains save-free;
7. full Jarvis Console smoke tests and local browser QA pass with no generated
   state or lingering listener.

## 8. Risks and Decisions

- Markdown is human-editable, so strict bounded parsing may make Project Control
  unavailable after a malformed table. This is preferred to silently showing
  stale or inferred status.
- The master plan contains both owner prose and bounded snapshot fields. The
  milestone update checklist must keep them semantically aligned.
- Fixed workstream names trade extensibility for a small deterministic v0.1D
  boundary. Adding or renaming a workstream requires an explicit reviewed code
  and documentation change.
- The dormant multi-project primitive remains tested but unused. Its existence
  must not be presented as a current product feature or next step.

## 9. Implementation Approval Boundary

This design does not authorize multi-project integration or any write/action
surface. The implemented package stayed within the complete read-only
single-repo slice described above. Any scope beyond it requires a new owner
decision.

## 10. Verification Result

- The master-plan parser returns the five owner-summary fields and exactly six
  ordered internal workstreams, and rejects malformed bounded fixtures.
- `GET /api/overview` returns one `project_control.v0.1D` Jarvis-Core card with
  no dormant-registry or second-repository connection.
- Jarvis Console smoke tests and JavaScript syntax checks passed.
- Local browser QA showed current reason and owner outcome before technical
  details, all six workstream cards, locked capabilities, and approval state.
- The Project Control card contained zero action buttons and browser console
  errors.
- The QA server was stopped without creating runtime state. Memory save, UI
  Save/Confirm, Voice Inbox save, and saved candidates remain unavailable.
