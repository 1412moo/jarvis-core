# Memory / Skills Session Bootstrap v0.1 Design

Last updated: 2026-07-22

Status: Phase 2C-4c design review and Phase 2C-4d route-free internal/tests-only
primitive complete. No bootstrap route or live session issuance is enabled.

## 1. Owner Summary

The future local-save flow needs a short-lived browser session before it can
prepare or confirm a save. This bootstrap is a separate trust boundary because
the first request cannot already prove possession of a session cookie or CSRF
token.

This design allows only an explicit, same-origin, loopback POST with no body to
create or rotate one bounded process-local session. A successful bootstrap
would grant only the ability to attempt later guarded requests. It would not
grant preview-token issue, candidate save, skill approval, execution, or any
filesystem authority.

The current product remains unchanged:

- no bootstrap route;
- no live session or CSRF issue;
- no save or token-preparation route;
- `POST /api/memory-skills/candidates` remains disabled/non-success;
- preview remains write-free/token-free;
- no UI Save/Confirm, Voice Inbox token/save, or saved-candidates dashboard.

## 2. Decision

Phase 2C-4c chose the following contract. Phase 2C-4d implements its route-free
portions; live integration remains separately approved and locked:

1. Bootstrap is initiated only by an explicit future `Review Local Save`
   action. Page load, preview, Voice Inbox, and background code must not call it.
2. The endpoint name is not reserved here. A future route must be one exact POST
   allowlist entry and must reject a query string.
3. Bootstrap has a dedicated raw-metadata contract. The Phase 2C-4b guarded
   request adapter is not reused because it requires an existing Cookie, CSRF
   header, JSON Content-Type, and guarded-request semantics.
4. Validation completes before session allocation. Invalid requests consume no
   registry capacity and receive no cookie or CSRF value.
5. Session state is bounded, process-local, restart-invalidated, and never
   written to disk.
6. The session cookie and CSRF token are separate credentials. Possessing them
   authorizes only later request-guard evaluation.

## 3. Threat Model and Limits

Bootstrap is intended to reduce browser cross-origin, request-confusion, stale
session, and accidental replay risk for a loopback-only app.

It does not authenticate the OS user and does not defend against a malicious
local process or another user who can act with the same OS authority. If that
stronger threat model becomes required, live save remains locked until an
OS-backed authentication design is approved.

The server must remain bound to IPv4 `127.0.0.1`. `localhost`, IPv6 loopback,
LAN addresses, forwarded client headers, and proxy-derived authority are not
accepted as substitutes.

## 4. Future Request Contract

The future handler must validate transport context and duplicate-preserving raw
header pairs before it reads a body or calls `SessionRegistry`.

### Transport and target

- direct peer address: exactly `127.0.0.1`;
- server bind address: exactly `127.0.0.1`;
- method: exactly POST;
- path: one future explicit allowlist entry;
- query: absent;
- body: absent and never read.

### Required headers

Each required header occurs exactly once, case-insensitively:

- `Host: 127.0.0.1:<actual-bound-port>`;
- `Origin: http://127.0.0.1:<actual-bound-port>`;
- `Content-Length: 0`.

The actual ephemeral or configured server port is injected from the bound
server, not a module default or client payload. Values are compared as exact
ASCII strings after structural validation; aliases, whitespace variants,
comma-joined values, user-info, trailing dots, and default-port elision fail.

### Forbidden or constrained headers

- `Transfer-Encoding` is always rejected.
- `X-Jarvis-CSRF` is rejected. Bootstrap must not appear to validate a
  credential that does not yet exist.
- `Content-Type` is rejected because the request has no body.
- At most one raw `Cookie` header is accepted. It is optional and must be
  syntactically well formed. It may contain zero or one `jarvis_session` value;
  duplicate, empty, malformed, or oversized session values fail closed.
- A well-formed `jarvis_session` value is an untrusted rotation hint, not proof
  that the session exists or belongs to an identity.
- Other headers may be ignored only after the same bounded ASCII name/value,
  control-character, count, and size checks used by Phase 2C-4b.

Mappings are not valid raw-header input because they can hide duplicates.
Request errors never echo header or cookie values.

## 5. Session Lifecycle

The current internal `SessionRegistry` values are the proposed v0.1 bounds:

- maximum active sessions: 64;
- idle TTL: 30 minutes;
- entropy: at least 256 bits for both session and CSRF values;
- storage: process memory only;
- restart: all sessions become invalid;
- expiry: purged before capacity checks and verification;
- verification: successful guarded use extends the idle expiry.

A route-free bootstrap primitive now implements one atomic rotate-or-issue
operation:

1. Purge expired entries, then check capacity before looking up the hint. A full
   registry returns the same fixed capacity error whether the hint exists or
   not, so session existence is not disclosed.
2. Generate both replacement credentials before changing registry state.
3. If capacity remains and the untrusted rotation hint matches an existing
   entry, replace that entry under the registry lock.
4. If the hint is absent or unknown, add one entry only when capacity remains.
5. If generation, collision, or capacity handling fails, preserve the previous
   entry and issue no partial credential.
6. Concurrent requests may each succeed only if the global bound is preserved;
   no eviction of unrelated live sessions is allowed.

A future UI must allow only one bootstrap request in flight. If concurrency or
response ordering nevertheless leaves the browser cookie paired with a
different in-memory CSRF value, the next request guard must fail with the same
generic verification error. The client must discard the CSRF value and require
a new explicit bootstrap action; it must not retry bootstrap or save
automatically.

After a process restart, a well-formed stale browser cookie is an unknown hint
and can be replaced while capacity is available. The new `Set-Cookie` value
overwrites it in the browser.

## 6. Cookie and CSRF Delivery

On the future success path only:

- the session ID appears only in one `Set-Cookie` header;
- cookie name: `jarvis_session`;
- attributes: `HttpOnly`, `SameSite=Strict`, no `Domain`, and the narrowest
  approved Memory / Skills API path;
- `Secure` remains false only while the app is strictly loopback HTTP; any HTTPS
  deployment must require `Secure` before activation;
- no `Expires` or persistent browser lifetime is required for v0.1;
- the CSRF token appears only in the bounded JSON success payload;
- frontend memory is the only approved client-side CSRF storage; URL,
  localStorage, sessionStorage, DOM attributes, logs, and persisted state are
  prohibited;
- reload or lost in-memory CSRF state requires another explicit bootstrap and
  rotation.

The response serializer must keep cookie construction separate from the public
JSON payload so the session ID cannot be inserted into the body accidentally.

## 7. Response Contract

### Success

The future success response is `200 OK` with:

- `Cache-Control: no-store`;
- `Pragma: no-cache`;
- `Content-Type: application/json; charset=utf-8`;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: no-referrer`;
- exactly one bounded `Set-Cookie` as described above;
- no CORS allow-origin or allow-credentials header;
- a bounded public payload containing only `ok`, the newly issued
  `csrf_token`, `idle_ttl_seconds`, and a fixed non-authority note.

The public payload must not include the session ID, Cookie text, Host, Origin,
private paths, candidate data, canonical bytes, stack traces, or registry size.
The note must say that the session is local, temporary, and is not save or skill
approval.

### Failure

- structural framing errors use fixed bounded categories before allocation;
- peer/Host/Origin/Cookie/forbidden-header failures use one public
  `bootstrap_rejected` category and do not disclose which check failed;
- capacity and internal issuance failure return bounded retryable/non-retryable
  categories without registry counts or credential existence details;
- failure responses contain no `Set-Cookie`, CSRF value, credential echo, or
  automatic retry instruction;
- all responses remain `no-store` and logs remain credential-free.

The successful bootstrap CSRF value and session `Set-Cookie` are the only narrow
exceptions to the general rule that credentials are absent from responses.
Neither value may be echoed by any later endpoint or error.

## 8. Authority Separation

Bootstrap success proves only that one same-origin loopback request obtained one
temporary guarded-request credential pair. It does not prove:

- user identity;
- privacy review;
- candidate review or confirmation;
- preview-token authority;
- save approval;
- file path or storage authority;
- skill approval, installation, or execution.

Preview remains public to the local UI and token-free. Phase 2C-4e now proves
the route-free save-preparation composition can use both the session cookie and
CSRF header and independently require privacy review. No live request invokes
it. Final save must still require the one-time preview token and exact
confirmation literal.

## 9. Deterministic Validation Contract

The Phase 2C-4d route-free package uses fake clocks, deterministic token
generation, and no real server. Its coverage includes:

- valid no-cookie issue and valid stale-cookie rotation;
- exact actual-port Host/Origin matching;
- wrong peer, Host, Origin, method, path, or query;
- duplicate/missing required headers and mapping input;
- nonzero, negative, malformed, duplicated, comma-joined, and oversized
  Content-Length;
- any Transfer-Encoding, Content-Type, or CSRF header;
- malformed, duplicate, empty, non-ASCII, and oversized session cookies;
- header count/name/value/control-character bounds;
- invalid input causing no registry allocation;
- old-session invalidation only after successful atomic replacement;
- generator failure preserving the old entry;
- capacity, expiry purge, restart invalidation, and concurrency bounds;
- concurrent response ordering or credential mismatch failing at the request
  guard without automatic bootstrap or save retry;
- success response separation between `Set-Cookie` and public JSON;
- no secret, path, candidate, raw text, or stack trace in errors/logs;
- no route/handler/dispatcher/UI/Voice references;
- save endpoint remains 404/non-success and preview remains write-free/token-free;
- no repo state, candidate JSON, cache, log, listener, or generated artifact.

Real HTTP and browser tests remain a later integration gate. They must use an
ephemeral loopback port and isolated temporary state after route integration is
separately approved.

## 10. Phase 2C-4d Result and Next Boundary

Phase 2C-4d implemented:

- a bootstrap-specific duplicate-preserving raw metadata adapter;
- coordinator-owned transport validation before any session allocation;
- atomic bounded rotate-or-issue with uniform full-capacity behavior;
- a non-JSON-serializable private success object with redacted `repr`, separate
  `Set-Cookie` material, and a bounded public CSRF payload;
- narrowed Memory / Skills cookie path;
- deterministic success, rejection, rotation, failure, expiry, restart,
  collision, capacity, mismatch, and concurrency coverage.

The primitive is absent from `JarvisConsoleHandler`, dispatch, UI, Voice Inbox,
and runtime persistence. The live save and bootstrap routes remain disabled.

The wider Memory / Skills Phase 2C-4e route-free guarded save-preparation
coordinator is also complete. Phase 2C-4f reviewed live-integration readiness
and returned `keep locked`; see
[`memory-skills-live-integration-readiness-v0.1.md`](memory-skills-live-integration-readiness-v0.1.md).
No live HTTP integration is authorized by 2C-4d, 2C-4e, or 2C-4f.
