# Jarvis Console

Jarvis Console v0.1 is a local-only browser shell for the long-term Jarvis-Core
main UI. It is meant to feel closer to a ChatGPT/Codex-style command surface
than a collection of separate files, CLI commands, and JSON fixtures.

v0.1 is intentionally small. It shows the future console shape, skill tabs,
deterministic skill suggestions, usage-card skill details, a fresh read-only
Codex work review, and safety boundaries. It does not run the other Jarvis apps
automatically.

Skill cards, usage guides, and command suggestions are loaded from the read-only
`skills.json` registry. The registry is display and routing metadata only; it
does not grant execution permission. Copy command buttons copy text to the
clipboard only.

## Run

Start the local browser shell:

```bash
python -B apps/jarvis-console/run_web_app.py
```

PowerShell:

```powershell
python -B apps\jarvis-console\run_web_app.py
```

Run without opening a browser automatically:

```bash
python -B apps/jarvis-console/run_web_app.py --no-browser
```

Choose a local port:

```powershell
python -B apps\jarvis-console\run_web_app.py --port 8791
```

Default URL:

```text
http://127.0.0.1:8790/
```

Run the self-test:

```powershell
python -B apps\jarvis-console\run_web_app.py --self-test
```

Run the smoke test:

```powershell
python -B apps\jarvis-console\run_smoke_tests.py
```

## v0.1 Scope

Included:

- Local HTTP server bound to `127.0.0.1`.
- Browser UI with sidebar tabs.
- Chat / Command input.
- Deterministic keyword-based skill suggestion.
- Skill cards loaded from `skills.json`.
- Skill detail usage cards for what it does, when to use it, next action,
  commands, docs, safety notes, and non-goals.
- Copy command buttons that never execute commands.
- A `Codex Review` tab that accepts one copy-only Hermes handoff or an already
  scope-approved raw queue and displays a freshly revalidated review session.
- A write-free `POST /api/codex-review/preview` route fixed to the Jarvis-Core
  repository root.
- Read-only skill registry validation.
- Local-only safety banner.
- Status, skill detail, and suggestion API endpoints.
- Self-test and smoke test.

## Non-Goals

Out of scope for v0.1:

- No Codex automatic invocation.
- No ChatGPT automatic invocation.
- No Hermes automatic invocation.
- No Research Council automatic execution.
- No Daily AI Radar automatic execution.
- No git add, commit, or push.
- No repository auto-modification.
- No external network, API, or LLM calls.
- No scheduler.
- No database.
- No Discord command.
- No MCP or A2A integration.
- No auth or user accounts.

## Available Skills

Skill metadata is defined in `skills.json`. The console reads that file at
runtime and renders cards, commands, and deterministic route keywords from it.
Skill Detail uses action guide metadata to show a short human workflow. Those
steps are instructions for the user, not actions that Jarvis Console runs.

### Hermes Manager

Purpose: manage Codex/ChatGPT workflow prompts, reviews, commit prompts, and
checkpoints.

Manual command:

```bash
python -B apps/hermes-manager-pilot/run_web_app.py
```

PowerShell:

```powershell
python -B apps\hermes-manager-pilot\run_web_app.py
```

Local URL when run separately:

```text
http://127.0.0.1:8787/
```

Jarvis Console does not start Hermes Manager automatically.

### Codex Review

Purpose: show one current Codex work package only after the committed Hermes
evidence chain confirms that the supplied review handoff still matches the local
working tree.

Hermes Manager can produce one exact `queue + item_id` JSON envelope after the
user confirms scope and pastes a Codex result. The user copies that envelope
manually; Jarvis fills the item ID in the browser. A raw, already scope-approved
queue plus manually entered item ID remains supported. Jarvis Console normalizes
the queue, collects bounded local evidence, evaluates the observed item,
performs C0C-6a fresh revalidation, builds the C0C-6b review-only `SessionState`,
and returns a bounded presentation payload.

The preview route is local-only and write-free. It fixes filesystem authority to
the Jarvis-Core root and does not return raw file contents, evidence bytes,
approval digests, a rendered prompt, or a commit message. Invalid, stale,
out-of-scope, staged, or otherwise blocked handoffs display blocking reasons and
no review session.

The tab does not persist the pasted queue, evidence, session, or result. It does
not create approval, render or execute a prompt, invoke Codex/ChatGPT/Hermes,
stage, commit, push, or call an external service.

### Research Council

Purpose: evaluate ideas, MVP assumptions, risks, evidence gaps, and experiment
plans.

Manual command:

```bash
python -B apps/research-council/run_local_app.py
```

PowerShell:

```powershell
python -B apps\research-council\run_local_app.py
```

Jarvis Console does not run Research Council automatically.

### Daily AI Radar

Purpose: turn curated AI and agent technology metadata into a Jarvis improvement
candidate report.

Manual sample command:

```bash
python -B apps/daily-ai-radar/run_demo.py --input apps/daily-ai-radar/examples/sample-input.json
```

PowerShell:

```powershell
python -B apps\daily-ai-radar\run_demo.py --input apps\daily-ai-radar\examples\sample-input.json
```

Jarvis Console does not fetch sources or run Daily AI Radar automatically.

### Memory / Skills

Purpose: review repeated workflow candidates and future Jarvis operating rules
without turning proposals into automatic memory or executable skills.

Status: Phase 2B provides a read-only sample inbox and write-free candidate
preview. Phase 2C-0/1/2/3a/3b adds internal/tests-only path, validation,
hardened writer, request-guard, session, canonical snapshot/digest, and preview
token primitives. Phase 2C-3c completed the design/reopen-conditions review
with a `keep locked` verdict. Phase 2C-4a records the safer privacy default and
adds a route-free internal/tests-only guarded save coordinator: preview-token
issuance requires explicit privacy review, the final payload is token-only with
an exact confirmation literal, and persisted test candidates omit
`original_text_preview`. Phase 2C-4b adds a route-free internal/tests-only raw
HTTP metadata adapter. It requires duplicate-preserving header pairs, exactly
one Host, Origin, Content-Type, Cookie, CSRF, and Content-Length value, rejects
Transfer-Encoding and malformed or oversized lengths, and emits bounded input
for the existing request guard. The save endpoint remains disabled/non-success;
no live session/token issuance, UI Save/Confirm, Voice Inbox save, or saved
candidates dashboard is enabled.

Phase 2C-4c completes the design-only session-bootstrap contract review. It
defines a future explicit same-origin/no-body bootstrap, bounded atomic session
issue/rotation, separate Cookie/CSRF delivery, restart invalidation, and
deterministic test obligations. It adds no application behavior.

Next decision: Phase 2C-4d may implement only the route-free internal/tests-only
bootstrap primitive under separate approval. It does not authorize a bootstrap
route, handler integration, live session issue, save endpoint, UI Save/Confirm,
or Voice Inbox persistence. Phase 2C-4a/4b remain disconnected from live HTTP
dispatch.

## Safety Boundary

Jarvis Console v0.1 is a shell, not an autonomous executor.

- It is local-only.
- It binds to `127.0.0.1` only.
- It does not launch Codex, ChatGPT, Hermes, Research Council, or Daily AI
  Radar.
- It does not run git write commands.
- It does not modify repository files.
- It does not store secrets, credentials, tokens, private messages, or hidden
  reasoning.
- It treats Daily AI Radar recommendations as scouting output, not implementation
  approval.
- It treats Research Council reports as decision support, not final proof.
- It treats Hermes Manager as workflow coordination, not a Codex replacement.
- It treats a fresh Codex review session as inspection data, not review approval
  or execution authority.
- Human approval is required before implementation, commit, push, or any
  external action.

Protected path shown by default:

- `jarvis.bat`

## Future Phases

Possible later phases:

1. Add richer registry metadata such as icons, examples, and handoff contracts.
2. Add local report preview forms for existing deterministic renderers.
3. Refine the read-only review surface only from repeated local-use feedback.
4. Consider an approval queue only after a separate human-approval design.
5. Consider deeper worker handoff integration only after separate design and
   review.

See also [../../docs/jarvis-console.md](../../docs/jarvis-console.md).
See the read-only review design at
[../../docs/codex-review-read-only-v0.1-design.md](../../docs/codex-review-read-only-v0.1-design.md).
See the copy-only handoff design at
[../../docs/codex-review-copy-handoff-v0.1-design.md](../../docs/codex-review-copy-handoff-v0.1-design.md).
See the registry contract at
[contracts/skill-registry-v0.1.md](contracts/skill-registry-v0.1.md).
