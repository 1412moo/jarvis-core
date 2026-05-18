# Research Council

Research Council is an isolated Jarvis app module.

Its v0.1 goal is to turn a user's raw idea and goal into a small research bundle:

1. Structured research claims
2. An evidence ledger
3. Reviewer critiques
4. Minimum viable experiment plans
5. A Markdown research report

## Scope

Included in v0.1 foundation:

- Stable schema dataclasses
- A documented input/output contract
- A deterministic placeholder pipeline
- A local demo script
- A local smoke test

Out of scope for this pass:

- Web search
- Network calls
- LLM calls
- Fake citations
- Discord integration
- Dashboard integration
- Task memory integration
- Full research reasoning implementation

## Local Usage

Run the default capsule sample:

```powershell
python -B apps/research-council/run_demo.py
```

Run against a custom local idea and goal:

```powershell
python -B apps/research-council/run_demo.py `
  --idea "AI patent analysis assistant for solo founders" `
  --goal "Evaluate differentiation and market viability"
```

Optional local context and repeated constraints can be supplied with
`--context` and `--constraints`.

Optionally force a deterministic domain profile:

```powershell
python -B apps/research-council/run_demo.py --profile ai_saas
```

If `--profile` is omitted, the app resolves one locally from the idea, goal,
context, and constraints. JSON exports include compact profile-selection
metadata under `profile`.

Optionally export the structured JSON result while preserving Markdown stdout:

```powershell
python -B apps/research-council/run_demo.py --json-output apps/research-council/artifacts/sample-result.json
```

Run the smoke test:

```powershell
python -B apps/research-council/run_smoke_tests.py
```

Run only the deterministic golden-case evaluation harness:

```powershell
python -B apps/research-council/run_golden_cases.py
```

Golden cases live under `golden_cases/` and assert invariant-level behavior,
such as profile selection, required risk language, confidence blockers,
reasoning traces, and JSON `quality_signals`. They intentionally avoid exact
snapshot diffs.

The demo prints Markdown to stdout. Generated reports are not written to committed
paths by default. The local `apps/research-council/artifacts/` directory is
ignored for generated JSON exports.

## Contract

See [contracts/research-council-mvp.md](contracts/research-council-mvp.md).
