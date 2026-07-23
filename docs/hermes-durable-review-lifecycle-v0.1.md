# Hermes Durable Review Local Lifecycle v0.1C/v0.1D/v0.1E

Status: implemented and locally verified on 2026-07-23.

Implementation commits:

- v0.1C: `2d564e544a32c2ce839364fd3ba8cf76e9f70abb`
- v0.1D: `e1ea7e4c664153276eb55dfde3dbdfea0da05ab4`
- v0.1E record core: `a02605750f7cbd889e6c6ac6e3ac98719b5c89e6`
- v0.1E content verification: `701a77e58a8fa4af0c1bbfef80aee364eadd3143`

## User value

The owner can explicitly save one current Hermes Review on this computer,
reopen it read-only, determine whether an uncertain Save produced that exact
ID, and delete exactly one confirmed record without relying on clipboard state.
When the saved Git metadata still matches, the owner can also regenerate the
same copy-only Jarvis Review handoff after explicitly reconfirming its scope.
New Saves also bind bounded target-content evidence, so the handoff is produced
only when current target bytes still match the saved evidence.

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

## Reopen-to-Handoff v0.1D contract

- One exact saved Review ID and a fresh explicit target-scope reconfirmation are
  required before Git IO or handoff generation.
- The server rereads trusted branch, HEAD, and complete `git status --short`.
  Any mismatch returns `review_reopen_handoff_stale`, bounded blocking reasons,
  and no artifact.
- Canonical directory targets end in `/`. They cover only paths below that
  slash, never sibling prefixes, and cannot include a protected path.
- The regenerated artifact preserves both Git porcelain status columns and the
  original bounded Review task, scope, validation commands, and result summary.
- The response reports `freshness_basis=branch_head_status_only`,
  `git_metadata_matches=true`, and `content_evidence_verified=false`.
  Already-modified file content can change without changing short-status text,
  so downstream read-only review must collect content evidence.
- Those fields describe the historical v0.1D path. New v0.1B Saves use the
  v0.1E contract below and cannot produce a status-only fresh handoff.
- A blocked browser attempt clears the generated-output area. Hermes never
  reads or trusts the current clipboard value.
- The route is read-only with respect to the Review store and repository. It
  does not restore review, commit, push, or execution approval.

## Content Evidence Binding v0.1E contract

- Save preview creates a v0.1B record and binds the existing bounded local
  change-evidence digest without storing raw target content or an absolute
  evidence path.
- Directory scopes materialize only exact Git-visible changed descendants;
  sibling prefixes and protected `jarvis.bat` are excluded.
- Save confirmation recollects branch, HEAD, complete short status, and target
  evidence. A same-status byte change blocks the write and consumes the token.
- Reopen-to-Handoff performs the same recollection before output. A successful
  response reports `freshness_basis=branch_head_status_content_sha256` and
  `content_evidence_verified=true`.
- Evidence failure or mismatch returns bounded reasons, no artifact, and the
  browser clears any previous generated output.
- Legacy v0.1A records remain listable, read-only reopenable, recoverable, and
  exactly deletable. They cannot produce a content-verified handoff and are not
  migrated or backfilled automatically.
- Content equality is evidence, not approval. Review, commit, push, execution,
  external calls, and clipboard input remain absent.

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
- v0.1D browser QA confirmed the explicit scope gate, successful copy-only
  handoff regeneration, directory scope, status-drift blocking with no output,
  output-only clipboard behavior, and zero browser warnings or errors.
- v0.1E deterministic HTTP/lifecycle end-to-end tests confirmed matching-byte
  success, same-short-status byte-drift blocking for Save and handoff, restored
  content, directory materialization, and legacy v0.1A blocking. Hermes UI
  self-test and JavaScript syntax checks passed.
- Interactive v0.1E click QA was not run because no controllable browser was
  available in the desktop session. The temporary QA server and state were
  removed; this remains the next real-work validation, not an implementation
  blocker.
- Browser QA used an external temporary state override, which was deleted after
  validation. The default Review store and repository-local state were not
  created.

## Next candidate

[Durable Review Content Evidence Binding v0.1E](hermes-durable-review-content-evidence-v0.1-design.md)
is implemented end to end. The next action is owner-visible real-work feedback,
not another evidence primitive. Repeat one Save/Reopen/content-drift browser
exercise when an interactive browser is available, then choose the next product
workstream without expanding execution, external-call, push/PR, or Memory Save
authority.
