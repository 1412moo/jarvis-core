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

## Governance Overview

Research Council governance is deterministic, metadata-only, and append-only by
default. Detailed domain-profile governance, first-line summary contract rules,
operational workflows, authority rules, lifecycle rules, and auditability rules
live in [governance.md](governance.md).

Key invariants:

- Preserve deterministic behavior.
- Preserve metadata-only governance.
- Preserve append-only governance contract evolution.
- Preserve summary growth control and first-line summary stability.
- Preserve schema/hash/output stability.
- Do not store raw benchmark, golden, mutation, scenario, or user-provided input
  text.
- Do not add DB/API/UI/async workers or new orchestration systems.

The v0.1 input/output contract boundary is documented in
[Governance Metadata Boundary](contracts/research-council-mvp.md#13-governance-metadata-boundary).

## Benchmark Governance CI Usage

Use deterministic benchmark governance commands to check benchmark composition,
drift categories, severity, and the opt-in CI gate from a terminal or CI job.
The gate only fails when `--fail-on-critical` is supplied and the benchmark
governance severity is `critical`; the default diff command preserves exit code
`0` after printing the report.

Basic command sequence:

```bash
python -B apps\research-council\run_golden_cases.py
python -B apps\research-council\run_golden_cases.py --export-snapshot benchmark_snapshot.json
python -B apps\research-council\run_benchmark_history.py --snapshot benchmark_snapshot.json --history benchmark_history.json
python -B apps\research-council\run_benchmark_diff.py --history benchmark_history.json --fail-on-critical
```

Expected exit behavior:

- `run_golden_cases.py` exits nonzero only when golden-case invariants fail.
- `run_benchmark_diff.py --fail-on-critical` exits `1` only for
  `severity=critical`.
- `severity=stable`, `severity=info`, and `severity=warning` remain pass-only
  for the opt-in gate.
- Without `--fail-on-critical`, `run_benchmark_diff.py` keeps the default
  reporting behavior; successful diff rendering returns exit code `0`.

Detailed governance summary rules, operational handling, Codex Goal guidance,
authority rules, lifecycle rules, audit retention, compatibility sunset handling,
and generated benchmark artifact policy live in [governance.md](governance.md).

The demo prints Markdown to stdout. Generated reports are not written to committed
paths by default. The local `apps/research-council/artifacts/` directory is
ignored for generated JSON exports.

## Contract

See [contracts/research-council-mvp.md](contracts/research-council-mvp.md).
