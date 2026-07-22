# Hermes Durable Review Local Lifecycle v0.1C

Status: implemented and locally verified on 2026-07-23.

Implementation commit: `2d564e544a32c2ce839364fd3ba8cf76e9f70abb`.

## User value

The owner can explicitly save one current Hermes Review on this computer,
reopen it read-only, determine whether an uncertain Save produced that exact
ID, and delete exactly one confirmed record without relying on clipboard state.

## Flow

```text
Frozen in-memory Review + confirmed scope
  -> privacy and retention acknowledgements
  -> write-free Save preview
  -> single-use Save confirmation
  -> local canonical Review record
  -> metadata list / read-only Reopen / exact-ID recovery inspection
  -> result-free exact Delete preview
  -> type DELETE <review_id>
  -> single-use exact deletion
```

## Save contract

- The server reads fresh Git state from the trusted Jarvis-Core root. Client
  branch, HEAD, and working-tree text are not storage authority.
- The complete current status must remain unstaged, include untracked
  `jarvis.bat`, and stay inside the confirmed target scope.
- A directory target uses an explicit trailing slash. Git status paths remain
  file paths and may not use that suffix.
- Privacy and `manual_delete_only` retention acknowledgements are separate and
  both required.
- Preview creates no directory or record. It returns the exact immutable record,
  canonical SHA-256 digest, disclosures, and a five-minute Save-only token.
- Confirmation consumes the token once and recollects Git state. Any mismatch
  blocks the Save and requires a new preview.
- Publication remains private, atomic, append-only, and no-overwrite.
- An uncertain post-publication result returns the generated ID. The client
  instructs the user to inspect that ID and never retries automatically.

## Reopen and recovery contract

- List returns bounded metadata only and omits result text and local paths.
- Reopen reads one exact canonical record and displays it read-only.
- Recovery inspection returns one of `present_valid`, `absent`,
  `present_corrupt`, or `store_unavailable`.
- Recovery inspection never retries Save, repairs files, removes temporary
  files, quarantines data, or grants approval.
- Invalid IDs are rejected rather than classified as unavailable storage.

## Delete contract

- Delete preview accepts one generated Review ID and reopens that exact record.
- The preview omits result text and contains bounded identifying metadata, the
  canonical digest, and the literal `DELETE <review_id>`.
- Delete tokens are domain-separated from Save tokens, server-held, session
  bound, single-use, and expire after five minutes.
- Confirmation must match the literal exactly. A typo consumes the attempt and
  requires a new preview.
- Immediately before unlink, the store re-reads canonical bytes, checks the
  preview digest, and confirms a stable regular-file snapshot.
- Missing, changed, symlink/reparse, noncanonical, or corrupt targets fail
  closed. Normal deletion never removes corrupt records.
- There is no bulk, oldest, all, glob, archive, automatic expiration, capacity
  eviction, orphan cleanup, or background deletion.

## Local web security boundary

- The server binds only to `127.0.0.1`.
- Durable lifecycle POSTs require JSON, exact loopback Host and port, exact
  same-origin `Origin`, and an in-memory local-session header.
- The session secret resets with the server and is not persisted or an API key.
- Confirmation tokens are held only in bounded process memory.
- Responses use `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `nosniff`,
  `no-referrer`, and `no-store`.
- These controls reduce browser-origin and clickjacking risk. They are not
  multi-user authentication or protection from another process running as the
  same operating-system user.

## Storage and privacy disclosure

- Default Windows root: `%LOCALAPPDATA%\Jarvis-Core\hermes-manager\reviews\v1`.
- Default non-Windows root: `~/.jarvis-core/hermes-manager/reviews/v1`.
- `JARVIS_LOCAL_STATE_DIR` supports an absolute external override.
- Repository-internal and symlink/reparse state paths fail closed.
- Records are local, not encrypted by Jarvis, not cloud-synced by Jarvis, and
  retained until exact manual deletion.
- The user must review bounded Review content for privacy before preview.

## Authority boundary

A stored or reopened Review is input for later review only. It always has
`review_passed=false`, `commit_approved=false`, and `push_allowed=false`.
Save, Reopen, recovery, and Delete do not execute prompts or commands and do not
call Jarvis Console, Codex, ChatGPT, an external API, or an LLM.

Memory / Skills candidate save and its UI Save/Confirm, Voice Inbox auto-save,
and the saved candidates dashboard remain disabled or absent.

## Verification

- Deterministic tests cover immutable records, stable digest, bounded directory
  scope, append/read/list, post-publish uncertainty, exact digest-bound delete,
  corrupt-record preservation, operation-domain tokens, expiry, stale Git,
  ambiguous recovery, exact route fields, Host/same-origin protection, and
  frame security headers.
- Hermes browser and local self-tests, the full Hermes smoke suite, Jarvis
  Console self-test/smoke, Research Council smoke, Daily AI Radar smoke, Python
  compilation, JavaScript syntax, and `git diff --check` passed.
- Isolated browser QA completed Save preview, confirmed one record, listed and
  reopened it read-only, reported `present_valid`, deleted exactly that ID, and
  then reported `absent`, with zero browser warnings or errors.
- Browser QA used an external temporary state override, which was deleted after
  validation. The default Review store and repository-local state were not
  created.

## Next candidate

Design a separate read-only Reopen-to-Handoff slice. It may regenerate a handoff
only after fresh Git revalidation matches the stored Review and must block stale
records. It must not restore approval, auto-call another app, or execute work.
