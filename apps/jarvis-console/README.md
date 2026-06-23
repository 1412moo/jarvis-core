# Jarvis Console

Jarvis Console v0.1 is a local-only browser shell for the long-term Jarvis-Core
main UI. It is meant to feel closer to a ChatGPT/Codex-style command surface
than a collection of separate files, CLI commands, and JSON fixtures.

v0.1 is intentionally small. It shows the future console shape, skill tabs,
deterministic skill suggestions, and safety boundaries. It does not run the
other Jarvis apps automatically.

Skill cards and command suggestions are loaded from the read-only
`skills.json` registry. The registry is display and routing metadata only; it
does not grant execution permission.

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
- Read-only skill registry validation.
- Local-only safety banner.
- Status and suggestion API endpoints.
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

Purpose: future area for repeated workflow candidates, approved skills, and
Jarvis operating rules.

Status: planned placeholder in v0.1.

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
- Human approval is required before implementation, commit, push, or any
  external action.

Protected path shown by default:

- `jarvis.bat`

## Future Phases

Possible later phases:

1. Add richer registry metadata such as icons, examples, and handoff contracts.
2. Add local report preview forms for existing deterministic renderers.
3. Add an approval queue with explicit human approval states.
4. Consider deeper worker handoff integration only after separate design and
   review.

See also [../../docs/jarvis-console.md](../../docs/jarvis-console.md).
See the registry contract at
[contracts/skill-registry-v0.1.md](contracts/skill-registry-v0.1.md).
