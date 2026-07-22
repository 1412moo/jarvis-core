# Memory / Skills Live-integration Readiness v0.1

Last updated: 2026-07-22

Status: Phase 2C-4f design/review-only checkpoint complete.

Verdict: **KEEP LOCKED**. No live bootstrap, token-preparation, or save route is
ready to open. The existing preview remains the only user-facing Memory / Skills
POST flow and stays write-free/token-free.

## 1. Owner Summary

The internal safety pieces are now substantial: bounded sessions and tokens,
canonical snapshots, hardened storage, raw-header adapters, route-free
bootstrap, guarded preparation, exact confirmation, and one-claim writing all
have deterministic coverage.

That does not make local save a product feature. The current HTTP handler and UI
do not connect those pieces, and several activation-critical contracts do not
yet exist at the live boundary. Reusing the generic POST path would weaken the
internal guarantees rather than preserve them.

The safe decision is therefore:

- keep `POST /api/memory-skills/candidates` disabled/non-success;
- keep preview write-free/token-free;
- issue no live session, CSRF value, or preview token;
- add no UI Save/Confirm or Voice Inbox token/save action;
- do not start another automatic internal-primitive package;
- require an owner decision before any complete user-visible save milestone.

## 2. Evidence Reviewed

Review baseline:

- branch: `main`;
- implementation HEAD: `f1e6b62ec2aa11437d602b7ec23f03f132468245`;
- implementation commit: `jarvis-console: add memory save preparation coordinator`;
- protected untracked file: `jarvis.bat`;
- no external API, web, LLM, server, or browser call was used for this review.

Primary evidence:

- `apps/jarvis-console/run_web_app.py`;
- `apps/jarvis-console/run_smoke_tests.py`;
- `apps/jarvis-console/web/app.js`;
- `apps/jarvis-console/web/index.html`;
- `apps/jarvis-console/web/styles.css`;
- `docs/memory-skills-v0.1-design.md`;
- `docs/memory-skills-session-bootstrap-v0.1-design.md`;
- `docs/master-plan.md`.

## 3. Readiness Matrix

| Reopen condition | Internal result | Live/product result | Readiness |
| --- | --- | --- | --- |
| Session bootstrap | Route-free adapter and atomic bounded rotate-or-issue complete | No route, server-owned registry lifecycle, or live credential delivery | Blocked |
| Raw HTTP metadata | Duplicate-preserving bounded adapters complete | Generic handler does not apply them before body read | Blocked |
| Exact route allowlist | Current live allowlist safely excludes all new routes | Future bootstrap/preparation/save paths, query rejection, and method behavior are not integrated | Blocked |
| Canonical authority | Server canonicalization and token-held snapshot complete | No live preparation/final-save composition | Blocked |
| Confirmation semantics | Exact final literal and one-token payload complete internally | No exact-snapshot confirmation UI or double-submit control | Blocked |
| Privacy contract | Persisted source preview omission decided and tested | No live disclosure, acknowledgement, or retention presentation | Blocked |
| One-claim behavior | Claim-before-write and replay failure complete internally | Ambiguous response recovery is not designed for users | Blocked |
| Restart and recovery | Sessions/tokens invalidate on restart; writer is no-overwrite | No user recovery or receipt lookup after restart/timeout | Blocked |
| Bounded response/logging | Private result types redact credentials; generic JSON uses `no-store`; handler logging is disabled | Cookie/token response integration and audit rules are unverified | Blocked |
| Real HTTP tests | Deterministic route-free coverage complete | No ephemeral-port duplicate-header, framing, concurrency, or restart integration suite | Blocked |
| Browser safety | Current UI proves Save/Confirm is absent and escapes preview content | No positive confirmation, retry, timeout, or recovery test | Blocked |
| Operations | Tests leave repo/runtime artifacts clean | Live state location, retention, inspection, and recovery guidance are not user-ready | Blocked |

No row authorizes live activation by itself. All activation-critical rows must
pass together because a partial connection could create credentials or writes
without a complete user recovery path.

## 4. Blocking HTTP Findings

The current `JarvisConsoleHandler.do_POST` does not expose Memory write
authority because the save routes are absent. Its framing behavior is still
insufficient for a live Memory / Skills authority path and must not be reused
unchanged.

Activation blockers:

1. It converts one `Content-Length` string with `int()` but does not reject a
   negative value before `rfile.read(length)`.
2. It does not preserve and validate duplicate security headers through the
   approved raw-header adapter before body read.
3. It does not reject `Transfer-Encoding` before body read.
4. It extracts only the parsed path, so a query-bearing POST can match an
   allowlisted path instead of failing exact-target validation.
5. It does not validate exact Host, Origin, JSON media type, Cookie, or CSRF
   before parsing the body.
6. Its generic JSON parser does not reject duplicate JSON keys at every depth.
7. It has no server-owned `SessionRegistry` / `PreviewTokenRegistry` lifecycle
   or actual-bound-port injection for live requests.

These are activation blockers, not a claim that current preview creates saved
state. The present save route remains absent, so the review does not authorize
an emergency code change inside this design-only package.

## 5. Blocking UX and Recovery Findings

The current Memory / Skills UI correctly shows preview-only status and has no
Save or Confirm control. A future complete save milestone still needs:

- one explicit action that starts guarded review, never page load or Voice Inbox;
- the exact server-canonical candidate fields displayed before confirmation;
- privacy acknowledgement separate from final confirmation;
- storage scope, source-preview omission, retention, and `candidate only / not a
  skill / will not run` statements;
- a final exact confirmation action protected against double-click and retry;
- token expiry/restart messaging;
- ambiguous timeout guidance that prevents blind resubmission;
- a recovery choice: bounded read-only receipt lookup or explicit manual local
  state inspection. A saved-candidates dashboard remains out of scope unless
  separately approved.

The recovery choice is a product decision, not an implementation detail. The
current one-claim contract deliberately kills a token before a write attempt,
so an uncertain client response cannot safely be treated as permission to retry.

## 6. Required Validation Before Activation

Any later approved complete vertical slice must pass all of the following before
its routes or controls are considered enabled:

- exact method/path/query/peer/Host/Origin validation on the actual bound port;
- duplicate-preserving headers, canonical non-negative Content-Length, exact
  body-length matching, and unconditional Transfer-Encoding rejection;
- strict UTF-8 JSON with nested duplicate-key rejection;
- process-local registry ownership, capacity, expiry, rotation, concurrency,
  and restart invalidation through the real handler;
- separate Cookie/CSRF delivery with `no-store` and no secret logging;
- canonical preparation, cross-session rejection, exact confirmation,
  claim-before-write, replay failure, writer failure, and ambiguous recovery;
- escaped exact-snapshot UI, separate privacy/confirmation steps, double-submit
  prevention, expiry/restart/error states, and no Voice Inbox invocation;
- ephemeral loopback HTTP tests using isolated temporary local state;
- browser tests for the full success and fail-closed matrix;
- final repository cleanliness, no listener, no runtime artifact, and protected
  `jarvis.bat` verification.

Passing route-free unit tests alone is not sufficient.

## 7. Recommended Product Decision

Recommendation: **defer live Memory / Skills save for now** and return the next
user-visible milestone to the Jarvis/Hermes Prompt Queue / Project Control Panel
workstream. That work directly reduces the owner's current instruction,
validation, and approval burden without opening persistence or credential routes.

If local candidate save becomes the higher product priority, approve one named
complete vertical-slice milestone rather than an open-ended series of internal
primitives. That approval must explicitly include or reject:

- live bootstrap and save-preparation credential routes;
- final local-save route;
- exact review/privacy/confirmation UI;
- the recovery choice;
- retention and local-state guidance;
- ephemeral HTTP and browser integration tests.

Until that owner decision, Phase 2C remains `keep locked` and no subsequent
Memory / Skills implementation package is automatically authorized.

## 8. Non-goals

This review does not:

- modify application code;
- reserve or register route names;
- enable a save endpoint or token endpoint;
- add UI Save/Confirm;
- connect Voice Inbox to session, token, or save behavior;
- add persistence, candidate JSON, a storage directory, or a dashboard;
- call an external API, web service, LLM, push, or PR workflow.
