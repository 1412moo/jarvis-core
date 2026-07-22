# Codex Review Copy-only Handoff v0.1

## Owner outcome

After a Codex result is pasted into Hermes Manager, the user can copy one exact
JSON envelope and paste it into Jarvis Console. Jarvis fills the review item ID
from the envelope and revalidates the current local work before displaying it.

## Flow

```text
Confirm Scope in Hermes
  → copy implementation prompt
  → paste Codex result
  → Copy Jarvis Review Handoff
  → paste once in Jarvis Codex Review
  → fresh local revalidation
  → read-only review or blocked reasons
```

## Contract

- The Hermes endpoint is local-only and fixes Git reads to the Jarvis-Core root.
- Input is the current in-memory Hermes session plus an explicit indication that
  the existing Confirm Scope step was completed.
- Output contains exactly `queue` and `item_id` and is deterministic for the
  same confirmed scope and Git state.
- The existing scope confirmation is represented by the committed scope-binding
  primitive. The binding detects scope drift; it is not identity proof or
  execution authority.
- Review approval, commit approval, evidence approval, prompt execution, and
  push authority remain false or absent.
- Neither app persists the envelope, queue, session, result, or fresh evidence.
- There is no Hermes-to-Jarvis HTTP call. Clipboard/manual copy is the only
  application handoff.
- Jarvis continues to collect and compare fresh bounded evidence before showing
  a review session.

## UI

Hermes Step 5 gains `Copy Jarvis Review Handoff`. It is available only after the
user confirmed scope and pasted a Codex result. The generated JSON remains
visible in the existing read-only output area for manual copy fallback.

Jarvis Codex Review accepts either the existing raw queue JSON or the new exact
`queue + item_id` envelope. An envelope fills the item ID locally in the browser
before the unchanged write-free preview request is sent.

## Out of scope

- server-to-server calls;
- durable queue or session storage;
- automatic approval, review, commit, push, or PR;
- prompt rendering or command execution in the review handoff;
- arbitrary repository selection;
- Memory / Skills save, UI Save/Confirm, or Voice Inbox auto-save;
- external API, web, or LLM calls.
