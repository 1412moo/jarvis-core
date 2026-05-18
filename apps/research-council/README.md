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

Run the placeholder demo:

```powershell
python -B apps/research-council/run_demo.py
```

Run the smoke test:

```powershell
python -B apps/research-council/run_smoke_tests.py
```

The demo prints Markdown to stdout. Generated reports are not written to committed
paths by default.

## Contract

See [contracts/research-council-mvp.md](contracts/research-council-mvp.md).
