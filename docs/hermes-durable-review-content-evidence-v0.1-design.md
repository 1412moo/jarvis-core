# Hermes Durable Review Content Evidence Binding v0.1E Design

Status: implemented and deterministically verified on 2026-07-23.

Implementation commits:

- Record v0.1B core: `a02605750f7cbd889e6c6ac6e3ac98719b5c89e6`
- Save/Reopen content verification: `701a77e58a8fa4af0c1bbfef80aee364eadd3143`

## User value

The owner can regenerate a saved
Review handoff only when the current target-file content is the same content
that was explicitly previewed for the durable Save. A matching branch, HEAD,
and short-status string alone will no longer be described as content freshness.

## Decision summary

v0.1E extends the Durable Review Record with a small, versioned content
evidence binding. It will reuse the existing bounded `LocalChangeEvidence`
collector and its stable SHA-256 digest instead of introducing another file
hasher. The binding stores no raw file content.

The implementation order remains:

```text
versioned record contract and compatibility parser
  -> bounded evidence adapter
  -> write-free Save preview binding
  -> confirmation-time recollection
  -> read-only Reopen-to-Handoff verification
  -> minimal browser wording and end-to-end QA
```

No implemented step grants review, commit, push, prompt-execution, or external-call
authority.

## Implementation result

- Save preview now creates an immutable v0.1B record with bounded content
  evidence and remains write-free.
- Save confirmation recollects metadata and content; same-status byte drift
  consumes the attempt and writes no record.
- Reopen-to-Handoff recollects the evidence and emits an artifact only when the
  saved and current bindings match exactly.
- A successful response reports
  `freshness_basis=branch_head_status_content_sha256` and
  `content_evidence_verified=true`.
- Legacy v0.1A records remain readable, recoverable, and exactly deletable but
  cannot produce a content-verified handoff and are never auto-migrated.
- Deterministic end-to-end tests exercise matching content, byte drift with the
  same short status, restored content, directory scope, and legacy blocking.

## Current gap

Durable Review Reopen-to-Handoff v0.1D rereads the trusted branch, HEAD, and
complete `git status --short`. This blocks metadata drift, staged changes,
missing protection for untracked `jarvis.bat`, and changes outside the stored
scope. It deliberately returns:

- `freshness_basis=branch_head_status_only`
- `git_metadata_matches=true`
- `content_evidence_verified=false`

An already-modified file can change from one modified byte sequence to another
while its short-status line remains `M`. Therefore v0.1D cannot prove that the
content seen at Save time is still present.

## Record contract decision

The existing `hermes_review_record` v0.1A contract remains valid. A new v0.1B
variant will add one required `content_evidence_binding` object while retaining
all v0.1A authority fields and their false/read-only values.

Proposed binding fields:

```json
{
  "binding_type": "hermes_review_content_evidence_binding",
  "version": "0.1E",
  "source_evidence_type": "hermes_local_change_evidence",
  "source_evidence_version": "0.1C-0B",
  "coverage": "git-visible-review-target-content",
  "manifest_target_count": 2,
  "manifest_total_bytes": 1234,
  "change_evidence_digest": "<64 lowercase hex characters>"
}
```

Contract rules:

- The binding is immutable and included in canonical Review serialization and
  `review_record_digest`.
- Unknown fields, unsupported type/version/coverage, noncanonical integers,
  malformed digests, and inconsistent counts fail closed.
- `manifest_target_count` is an integer from 1 through the existing evidence
  target limit of 64; a boolean is not an integer for this contract.
- `manifest_total_bytes` is an integer from 0 through the existing aggregate
  limit of 16 MiB; a boolean is not an integer for this contract.
- The Review JSON remains bounded by the existing 64 KiB record limit.
- Only the binding metadata and digest are persisted. Raw bytes and the
  collector's absolute repository path are not added to the Review record.
- The source evidence type and version are explicit so future collector changes
  cannot silently reinterpret an old digest.

The record `contract_type` remains `hermes_review_record`. The record `version`
is the discriminant: `0.1A` has no binding; `0.1B` requires exactly one valid
binding. The local `reviews/v1` directory remains a store-format namespace, not
a claim that every contained record has one schema version.

## Existing v0.1A compatibility

Compatibility is read-only and migration-free:

- Existing v0.1A files remain listable, reopenable for display, recoverable by
  exact ID, and manually deletable through the existing exact confirmation.
- The parser dispatches by the duplicate-safe top-level `version` value and
  applies the strict field set for that version. It does not relax v0.1A.
- New successful Saves create v0.1B records through the verified v0.1E
  lifecycle.
- A v0.1A record is not eligible for a content-verified handoff. The operation
  fails closed with a bounded reason such as
  `review_content_evidence_unavailable_for_record_version` and no artifact.
- No automatic migration, rewrite, or evidence backfill is allowed. Hashing
  current files cannot prove what their bytes were when a legacy record was
  saved.
- A user may reopen a legacy Review as read-only input and explicitly create a
  new Save preview under the new contract; this is a new record, not migration.

Corrupt, unknown-version, noncanonical, symlink/reparse, or unstable stored
records keep the existing fail-closed recovery behavior.

## Evidence collection and coverage

v0.1E reuses `collect_local_change_evidence` and its existing guarantees:

- trusted absolute Git root and expected branch/HEAD
- complete bounded Git-visible status validation
- at most 64 manifest targets
- at most 4 MiB per regular file and 16 MiB total
- stable `lstat`/open-file snapshot checks around bounded binary reads
- repeated repository and target collection to detect concurrent changes
- SHA-256 per file plus a domain-separated canonical manifest digest
- explicit deleted-file representation
- no symlink, reparse point, directory, rename/copy, conflict, protected path,
  path traversal, or out-of-scope target

The lifecycle needs a small adapter because a Review scope may contain a
canonical directory target ending in `/`, while the existing collector hashes
exact files:

1. Start from the freshly collected complete short-status snapshot.
2. Retain each explicit file target.
3. Expand each directory scope only to exact Git-visible changed paths below
   that slash; never use sibling-prefix matching.
4. Exclude and protect `jarvis.bat`; it remains an expected untracked status
   line and is never opened or hashed.
5. Canonically deduplicate and sort the concrete file manifest.
6. Feed that exact manifest to the existing collector under the same trusted
   repository, branch, HEAD, scope, and protected-path policy.

If materialization produces no concrete file, collection fails closed instead
of manufacturing an empty evidence claim. The adapter uses one deterministic
evidence subject identity derived from the normalized Review candidate and
original declared scope. The same versioned adapter must recreate that identity
at Save confirmation and Reopen; the browser does not supply it.

Coverage is intentionally named `git-visible-review-target-content`. It proves
the bytes of explicit file targets and Git-visible changed files materialized
from directory scopes. Unchanged tracked files are bound by the unchanged HEAD;
ignored files and arbitrary directory contents are not claimed as covered.
Unsupported or ambiguous status shapes fail closed rather than reducing
coverage. The current evidence digest also binds the trusted repository
identity. Moving the repository therefore invalidates the old binding and
requires a new explicit Review Save; it is not silently rebased to a new path.

## Save binding flow

The implemented Save flow is:

1. Require the existing explicit scope, privacy, and retention confirmations.
2. Read trusted branch, HEAD, and complete short status.
3. Materialize the concrete evidence targets and collect stable local change
   evidence.
4. Create a v0.1B record whose binding matches that evidence.
5. Return the exact record and digest in the existing write-free Save preview.
6. Bind the single-use, session-scoped confirmation token to that exact record.
7. On confirmation, consume the token, reread Git metadata, recollect content
   evidence, and require exact binding equality before append-only publication.

Any collection failure, metadata drift, digest mismatch, unsupported target,
expired token, or unstable read produces no record. Preview remains write-free;
only the already human-confirmed Save confirmation may write one new record.

## Reopen-to-Handoff verification flow

The implemented read-only handoff flow is:

1. Require one exact saved Review ID and a fresh explicit scope confirmation.
2. Read and strictly parse that exact record.
3. Require a v0.1B content binding; legacy v0.1A stops here without output.
4. Reread trusted branch, HEAD, and complete short status and require the
   existing exact metadata match.
5. Recreate the concrete manifest, collect stable evidence, and compare the
   type, version, coverage, count, total bytes, and digest to the stored binding.
6. Generate the copy-only artifact only after every comparison succeeds.

A successful response may then report:

- `freshness_basis=branch_head_status_content_sha256`
- `git_metadata_matches=true`
- `content_evidence_verified=true`

All blocked paths return no artifact and clear any prior generated output in
the browser. Error responses use bounded categories and do not disclose file
content, hashes, absolute paths, or exception text.

## Privacy and authority boundary

Content hashes are correlation metadata and may reveal whether two byte
sequences are equal. They remain local in the Review record and are not sent to
another app unless a separately approved contract explicitly includes them.
The copy-only handoff does not need to expose the stored hash.

Content evidence proves only bounded local byte equality under this collector's
coverage and threat model. It is not source authenticity, authorship, semantic
correctness, privacy approval, review approval, commit approval, or execution
approval. Same-user local tampering is outside the authentication claims of the
current local app.

The following remain absent or locked:

- automatic app/LLM/API calls and prompt execution
- stage, commit, push, PR, background work, or mobile execution
- automatic migration, cleanup, retention expiry, or record overwrite
- Memory / Skills candidate Save, UI Save/Confirm, Voice Inbox auto-save, and
  saved candidates dashboard

Clipboard remains output only and is never evidence or workflow state.

## Implementation packages

### v0.1E-A — versioned record core and compatibility

Status: completed.

- Immutable binding and Review Record v0.1B contracts
- Duplicate-safe v0.1A/v0.1B parser dispatch
- Stable serialization and digest behavior
- Existing v0.1A list/read/delete compatibility tests
- No lifecycle, route, UI, Git collection, or new persistence behavior

### v0.1E-B — bounded evidence adapter and Save binding

Status: completed.

- Directory-scope materialization into exact evidence files
- Existing collector reuse
- Write-free preview binding and confirmation-time recollection
- Deterministic unstable-read, deletion, size, scope, and mismatch tests
- No new route or UI surface

### v0.1E-C — read-only handoff integration

Status: completed.

- Exact-record content verification before artifact generation
- Legacy-record blocking reason and no-output behavior
- Minimal existing-route response/wording update
- Browser QA for success, changed bytes with unchanged `M`, stale output clear,
  legacy record, and clipboard output-only behavior

Each package requires its own approved scope. A package may not silently absorb
the next one.

## Acceptance criteria

- Same branch, HEAD, and short status but different modified bytes is blocked.
- Identical metadata and identical target bytes can regenerate the handoff.
- A directory scope covers only exact changed descendants, never siblings.
- Deleted targets compare canonically without opening a missing file.
- Legacy v0.1A records remain readable/deletable but cannot claim content
  verification and produce no fresh handoff.
- Unstable reads, over-limit files, reparse paths, malformed evidence, unknown
  versions, and evidence mismatches fail closed.
- Preview and Reopen-to-Handoff are write-free.
- Stored records contain no raw target content or absolute repository path from
  the evidence manifest.
- `jarvis.bat` remains untracked, protected, unopened, and unstaged.
- No external call, background worker, execution, stage, commit, push, or PR is
  introduced by the product implementation.

## Final recommendation

Treat v0.1E as one completed user vertical slice rather than opening another
evidence primitive. The next useful action is one owner-visible real Review
Save/Reopen/content-drift exercise when an interactive browser is available,
then use that feedback to choose the next product workstream. Do not broaden
execution, external-call, push/PR, or Memory Save authority as part of that
validation.
