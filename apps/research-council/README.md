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

Governance summary examples:

```text
Benchmark governance: status=stable categories=none regressions=0 severity=stable recommended_action=continue profile_change_rollup=added:0,removed:0,deltas:0,selection_changes:0 policy_reason=stable_no_drift escalation_reason=no_escalation
Benchmark governance: status=warning categories=regression,contract_mismatch regressions=5 severity=critical recommended_action=block_and_review profile_change_rollup=added:0,removed:1,deltas:1,selection_changes:1 policy_reason=critical_regression_or_contract_mismatch escalation_reason=regression_and_contract_mismatch
```

Governance summary contract rules:

- Field order, spacing, and suffix order are contract.
- `recommended_action`, `profile_change_rollup`, `policy_reason`, and
  `escalation_reason` must remain present.
- Any intentional summary string change must update the smoke test exact
  expected strings.
- Keep this line bounded to gate, action, and policy-trigger metadata.
- Put per-profile detail, regression signals, scenario telemetry, and pack
  metadata detail in the benchmark diff report instead of adding summary fields.
- Add a new suffix only when CI triage needs the value on the first line.
- Contract evolution is append-only: new metadata may be added only as a final
  suffix, with README examples and smoke exact expected strings updated together.
- Reordering, removing, renaming, changing spacing, or changing existing field
  semantics is a breaking governance contract change.
- Deprecate by leaving the existing field stable and appending a replacement
  suffix; do not repurpose an existing field.

`benchmark_snapshot.json` and `benchmark_history.json` are generated benchmark
artifacts. Keep them out of commits unless a future explicit benchmark artifact
policy says otherwise. If the files are created in the repository root during
local or CI checks, remove them after the run:

```bash
rm -f benchmark_snapshot.json benchmark_history.json
```

A history file with only one entry is useful for validating serialization and
report formatting, but it is not a baseline-vs-current regression comparison.
Do not treat a newly created single-entry history as a regression comparison.
For real CI gating, use an intentional baseline snapshot or history strategy
when comparing feature-branch output against an established benchmark pack.

Non-goals for this usage note:

- No GitHub Actions workflow file is added yet.
- No default-branch baseline automation is added yet.
- No generated artifact persistence policy is defined yet.

The demo prints Markdown to stdout. Generated reports are not written to committed
paths by default. The local `apps/research-council/artifacts/` directory is
ignored for generated JSON exports.

## Contract

See [contracts/research-council-mvp.md](contracts/research-council-mvp.md).
