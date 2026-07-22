# Codex Review Read-Only Vertical Slice v0.1

## 1. Owner Outcome

Jarvis Console should show one current Codex work package only after the existing
Hermes evidence chain confirms that the supplied review handoff still matches the
local working tree. The screen is for inspection only. It must not create an
approval, render or execute a prompt, persist a queue, or enable commit or push.

## 2. Smallest Safe Flow

```text
human-approved Hermes queue snapshot
  → normalize the supplied queue
  → collect bounded local evidence for the selected item
  → evaluate the observed queue
  → recollect and compare fresh evidence (C0C-6a)
  → build an exact review-only SessionState (C0C-6b)
  → return a bounded presentation payload
  → display it in Jarvis Console
```

The v0.1 route is a write-free local POST preview because the queue snapshot is
request input and no server-side review state is retained. The selected project
must resolve to the Jarvis-Core repository root supplied by the server; the
request cannot choose another filesystem root.

## 3. Local API Contract

Endpoint:

```text
POST /api/codex-review/preview
```

Request:

```json
{
  "queue": { "queue_type": "hermes_prompt_queue", "version": "0.1B-2" },
  "item_id": "one-selected-review-item"
}
```

`queue` is the complete normalized Hermes queue mapping, including the existing
scope-approval state and its current binding. Jarvis Console does not create,
repair, or upgrade that approval metadata. The selected item must be an
unreviewed `review` item with an empty change-evidence digest so the server can
attach a newly collected observation without replacing prior evidence.

Successful responses contain only presentation fields derived from the validated
review session: project label, branch and HEAD, goal, task, changed/target files,
validation commands, working-tree summary, next action, and explicit safety
flags. They do not contain raw target contents, canonical evidence bytes, a
rendered prompt, approval digests, secrets, or a commit message.

Malformed or inconsistent input returns a bounded validation error. A valid
handoff that is blocked or stale returns its blocking reasons and no review
session. No failure path falls back to an unverified display.

## 4. Jarvis Console UX

Add one `Codex Review` tab with:

- a textarea for manual paste of the approved Hermes queue snapshot;
- an item-ID input;
- a `Load Read-Only Review` button;
- an initially empty review panel;
- permanent wording that the action reads local state but does not save, approve,
  render, execute, commit, push, or call an external service.

The result view clearly separates work summary, changed files, validation commands,
and safety boundaries. Every value inserted into HTML is escaped. Reloading or
leaving the page discards the input and result because there is no persistence.

## 5. Implementation Boundary

In scope:

- one local-only write-free POST preview route;
- reuse of the committed Hermes C0C-2/C0C-5/C0C-6a/C0C-6b functions;
- one read-only Jarvis Console tab;
- deterministic API, UI-contract, blocked-state, and end-to-end temporary-repo
  tests;
- documentation and master-plan status sync after validation.

Out of scope:

- approval creation or confirmation controls;
- prompt rendering, Codex/ChatGPT/Hermes invocation, or command execution;
- queue/session/evidence persistence, background monitoring, or filesystem watch;
- arbitrary repository selection or raw file-content display;
- stage, commit authority inside the product, push, or pull requests;
- Memory / Skills save, UI Save/Confirm, Voice Inbox auto-save, or saved candidates.

## 6. Acceptance Criteria

1. A valid approved review queue for a temporary local repository traverses the
   complete evidence-to-session chain and produces a bounded read-only payload.
2. Invalid, blocked, stale, out-of-scope, staged, protected, or unsafe-builder
   states produce no displayable review session.
3. The HTTP route always fixes filesystem authority to the Jarvis-Core root.
4. The browser surface performs no write request other than this explicitly
   write-free preview and exposes no approval or execution action.
5. Existing Memory / Skills and Voice Inbox safety tests remain unchanged and
   passing.
