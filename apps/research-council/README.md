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

Optional locally supplied evidence can also be repeated:

```powershell
python -B apps/research-council/run_demo.py `
  --idea "Care log assistant" `
  --goal "Evaluate evidence handling" `
  --provided-evidence "Caregivers need daily logs for reimbursement." `
  --provided-evidence "Manual logs create repeated admin work."
```

Longer custom inputs can be supplied as a local JSON object:

```json
{
  "idea": "Care log assistant",
  "goal": "Evaluate whether caregiver evidence supports a simple MVP",
  "context": "Family caregivers need repeatable daily documentation.",
  "constraints": [
    "No external services",
    "Keep the workflow local and deterministic"
  ],
  "provided_evidence": [
    "Manual logs create repeated admin work.",
    "Caregivers need daily records for reimbursement conversations."
  ]
}
```

```powershell
python -B apps/research-council/run_demo.py --input-json demo-input.json
```

Run the local desktop launcher:

```powershell
python -B apps/research-council/run_local_app.py
```

The launcher is a deterministic local Tk window for non-developer use. It does
not make external LLM/API calls, web requests, or citations. Each run writes
`input.json`, `report.md`, and `result.json` under the output directory selected
in the window. The default output root is the user's home directory under
`ResearchCouncilRuns`, not the repository, and launcher runs refuse repository
internal output directories.

Run its headless self-test:

```powershell
python -B apps/research-council/run_local_app.py --self-test --output-dir C:\work\rc-local-app-smoke
```

Run a local batch of JSON inputs into a user-selected output directory:

```powershell
python -B scripts/run_demo_batch.py `
  --input-dir demo-inputs `
  --output-dir demo-outputs `
  --profile ai_saas `
  --llm-augmentation-mode off
```

The batch helper processes `*.json` inputs by filename, writes per-case
Markdown/JSON outputs, and creates `batch-summary.json` plus a
`batch-summary.md` index with bounded metadata only. It does not copy raw input
text or full report bodies into the summaries. The index includes safe triage
counts such as confidence blockers, high critiques, missing evidence, and
warnings.

Compare two local batch output directories, for example an explicit profile run
against an automatic profile-selection run:

```powershell
python -B scripts/compare_demo_batches.py `
  --baseline-dir demo-outputs-explicit `
  --candidate-dir demo-outputs-auto `
  --output-dir demo-comparison `
  --baseline-label explicit `
  --candidate-label auto
```

The comparison helper reads only each directory's `batch-summary.json` and
writes `comparison-summary.json` plus a `comparison-summary.md` index with
profile, decision, and triage deltas. It does not copy raw input text or full
report bodies into the comparison summaries.

List available deterministic profiles and aliases:

```powershell
python -B apps/research-council/run_demo.py --list-profiles
```

Describe one deterministic profile by id or alias:

```powershell
python -B apps/research-council/run_demo.py --describe-profile software
```

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

Optionally include deterministic sandbox augmentation metadata in the JSON
export. This uses local deterministic fixtures only and does not make external
LLM calls:

```powershell
python -B apps/research-council/run_demo.py `
  --llm-augmentation-mode test_safe `
  --json-output apps/research-council/artifacts/sample-result.json
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

Replay deterministic benchmark governance decisions from existing metadata with
`run_governance_replay.py`. Use `--history` to compare the latest two entries in
a benchmark history file, or use `--before` and `--after` to compare explicit
snapshot files:

```bash
python -B apps\research-council\run_governance_replay.py --history benchmark_history.json
python -B apps\research-council\run_governance_replay.py --before baseline_snapshot.json --after current_snapshot.json
```

Optional expected checks can pin the first-line governance summary and benchmark
hashes:

```bash
python -B apps\research-council\run_governance_replay.py --history benchmark_history.json --expected-summary "<summary>" --expected-baseline-hash "<hash>" --expected-current-hash "<hash>"
```

Replay exit behavior:

- `0`: replay matched and any expected metadata matched.
- `1`: replay comparison completed, but expected metadata mismatched.
- `2`: usage, input, malformed metadata, missing file, or insufficient history
  error.

Replay output must stay bounded to metadata-only fields. It must not expose raw
idea, goal, `input_data`, scenario text or IDs, fixture internals, local paths,
raw benchmark/golden/mutation material, or raw expected CLI input. Replay should
not create or modify benchmark artifacts.

Detailed governance summary rules, operational handling, Codex Goal guidance,
authority rules, lifecycle rules, audit retention, compatibility sunset handling,
and generated benchmark artifact policy live in [governance.md](governance.md).

The demo prints Markdown to stdout. Generated reports are not written to committed
paths by default. The local `apps/research-council/artifacts/` directory is
ignored for generated JSON exports.

## Contract

See [contracts/research-council-mvp.md](contracts/research-council-mvp.md).
