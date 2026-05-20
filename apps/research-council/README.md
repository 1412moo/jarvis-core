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
Benchmark governance: status=stable categories=none regressions=0 severity=stable recommended_action=continue profile_change_rollup=added:0,removed:0,deltas:0,selection_changes:0 policy_reason=stable_no_drift escalation_reason=no_escalation compatibility_tier=compatible strictness_tier=advisory lifecycle_phase=observe
Benchmark governance: status=warning categories=regression,contract_mismatch regressions=5 severity=critical recommended_action=block_and_review profile_change_rollup=added:0,removed:1,deltas:1,selection_changes:1 policy_reason=critical_regression_or_contract_mismatch escalation_reason=regression_and_contract_mismatch compatibility_tier=breaking_contract_change strictness_tier=blocking lifecycle_phase=block
```

Governance summary contract rules:

- Field order, spacing, and suffix order are contract.
- `recommended_action`, `profile_change_rollup`, `policy_reason`, and
  `escalation_reason`, `compatibility_tier`, `strictness_tier`, and
  `lifecycle_phase` must remain present.
- Any intentional summary string change must update the smoke test exact
  expected strings.
- Keep this line bounded to gate, action, and policy-trigger metadata.
- Put per-profile detail, regression signals, scenario telemetry, and pack
  metadata detail in the benchmark diff report instead of adding summary fields.
- Add a new suffix only when CI triage needs the value on the first line.
- `compatibility_tier` is first-line compatibility-impact metadata:
  `compatible` for stable/hash-only drift, `additive_contract_change` for
  composition-only drift, and `breaking_contract_change` for regression or
  contract mismatch drift.
- `strictness_tier` is first-line CI/operator handling metadata derived from
  severity and compatibility impact: stable/info -> `advisory`, warning ->
  `review`, critical compatible/additive -> `strict`, and critical breaking ->
  `blocking`. It does not change the `--fail-on-critical` exit-code contract.
- `lifecycle_phase` is first-line CI/operator next-step metadata derived from
  severity and compatibility impact: stable/info -> `observe`, warning ->
  `review`, critical compatible/additive -> `stabilize`, and critical breaking
  -> `block`. It describes operational phase, not enforcement strength.
- Contract evolution is append-only: new metadata may be added only as a final
  suffix, with README examples and smoke exact expected strings updated together.
- Reordering, removing, renaming, changing spacing, or changing existing field
  semantics is a breaking governance contract change.
- Deprecate by leaving the existing field stable and appending a replacement
  suffix; do not repurpose an existing field.

Governance override philosophy:

- Governance metadata is the deterministic record of benchmark drift, not an
  operational permission system. An override is a downstream operator or CI
  decision to proceed despite the visible governance result.
- Overrides may be routine for `strictness_tier=advisory` / `lifecycle_phase=observe`
  and policy-reviewed for `strictness_tier=review` / `lifecycle_phase=review`,
  but they must not hide, rewrite, or suppress the original summary line.
- `strictness_tier=strict` / `lifecycle_phase=stabilize` and
  `strictness_tier=blocking` / `lifecycle_phase=block` require explicit
  acknowledgement with an owner, reason, scope, and follow-up expectation before
  proceeding operationally.
- Override audit records should keep the original governance summary, command
  context, snapshot or history reference, approver or owner, and rationale.
- Overrides are operational decisions, not benchmark rewrites: do not edit
  snapshots, history entries, benchmark hashes, golden fixtures, or governance
  fields merely to make a run appear lower risk.
- The `--fail-on-critical` contract remains unchanged. CI may decide how to
  handle that exit code, but the benchmark governance report must remain visible
  and deterministic.
- Override policy does not evolve the governance contract. Contract changes
  still follow append-only evolution, exact smoke fixtures, and summary growth
  control.

Governance acknowledgement workflow:

- Acknowledgement is optional for `strictness_tier=advisory` /
  `lifecycle_phase=observe` and `strictness_tier=review` /
  `lifecycle_phase=review`; those phases may still require local review policy,
  but benchmark governance does not require a special acknowledgement record.
- Acknowledgement is required before proceeding operationally with
  `strictness_tier=strict` / `lifecycle_phase=stabilize` or
  `strictness_tier=blocking` / `lifecycle_phase=block`.
- Acknowledgement differs from override: override is the decision to proceed,
  while acknowledgement is the auditable record that the operator or CI owner saw
  the deterministic governance result and accepted the operational risk.
- Acknowledgement metadata should include the owner, rationale, scope,
  follow-up expectation, timestamp or durable reference, original governance
  summary, `compatibility_tier`, `escalation_reason`, and the snapshot or
  history artifact being assessed.
- The acknowledgement scope should be no broader than the benchmark result it
  accepts. For example, acknowledge one CI run, branch, release candidate, or
  benchmark history comparison rather than changing future governance behavior.
- Acknowledgement must not mutate snapshots, history entries, benchmark hashes,
  golden fixtures, governance fields, or formatter output. It preserves
  deterministic visibility and records an operational acceptance alongside it.
- CI may store acknowledgement evidence in its own approval, deployment, or
  incident process, but that process is outside the benchmark governance
  contract and must not make the governance summary disappear.

Governance ownership semantics:

- The governance result is owned by the deterministic benchmark process; the
  operational response is owned by the CI operator, release owner, or explicitly
  assigned governance owner.
- `strictness_tier=advisory` / `lifecycle_phase=observe` and
  `strictness_tier=review` / `lifecycle_phase=review` may use local operator
  ownership according to the consuming team's CI policy.
- `strictness_tier=strict` / `lifecycle_phase=stabilize` and
  `strictness_tier=blocking` / `lifecycle_phase=block` require an explicit
  governance owner before acknowledgement or override can be treated as
  accepted.
- Acknowledgement authority belongs to the assigned governance owner or a
  documented delegate with authority for the affected benchmark scope. CI should
  not infer acknowledgement merely from a rerun, retry, or ignored exit code.
- Override authority is narrower than ownership: an owner may approve a scoped
  operational override, but that approval does not lower the reported severity,
  compatibility, strictness, lifecycle phase, or escalation reason.
- If no owner is available, proceeding is a temporary operational exception.
  The audit record should say owner unavailable, name the temporary approver,
  limit the scope and time horizon, and create a follow-up to assign ownership.
- Ownership transfer does not change the original governance summary or
  benchmark artifacts. Record the prior owner, new owner, transfer rationale,
  timestamp or durable reference, and the unchanged governance summary in audit
  metadata.
- Accountability must stay visible next to the deterministic result: ownership
  records should point to the exact summary, snapshot or history artifact,
  command context, and CI run or release decision they cover.

Governance transition lifecycle:

- Expiration is optional for `strictness_tier=advisory` /
  `lifecycle_phase=observe` and `strictness_tier=review` /
  `lifecycle_phase=review`, unless local CI policy requires a review window.
- Temporary acknowledgement or override for `strictness_tier=strict` /
  `lifecycle_phase=stabilize` and `strictness_tier=blocking` /
  `lifecycle_phase=block` must include an expiration condition. Use a bounded
  timestamp, CI run, branch, release candidate, or benchmark history comparison
  scope; do not leave strict or blocking acceptance open-ended.
- Revalidation is required when the benchmark hash changes, the compared
  snapshot or history baseline changes, `compatibility_tier`,
  `strictness_tier`, `lifecycle_phase`, or `escalation_reason` changes, the
  acknowledgement scope expires, or ownership transfers to a new accountable
  owner.
- A compatibility grace period is an operational exception, not a governance
  downgrade. It must name the compatibility issue, owner, rationale, bounded
  duration or scope, and follow-up expectation.
- Expired acknowledgement, override, or grace does not hide or rewrite the
  governance result. The latest deterministic summary remains visible, and CI or
  operators must either revalidate, renew with a new audit record, or stop the
  operational acceptance.
- Escalation upgrades, such as review -> strict or strict -> blocking, require a
  fresh acknowledgement before proceeding. Escalation downgrades may close the
  prior acknowledgement, but they should still record the new summary and the
  reason the previous higher-risk state no longer applies.
- Transition state is expressed only in audit metadata outside the benchmark
  contract. Do not add ad hoc lifecycle fields, mutate snapshots or history, or
  alter formatter output to represent grace, expiry, renewal, downgrade, or
  upgrade.

Governance acknowledgement renewal workflow:

- Acknowledgement, override, and grace decisions are not permanent approvals.
  Renewal is required when their expiration condition is reached and the
  operator still wants to proceed under the same unresolved governance result.
- Renewal differs from revalidation: renewal extends an existing operational
  acceptance for the same deterministic governance result, while revalidation
  reassesses the result after benchmark hash, baseline, compatibility,
  strictness, lifecycle, `escalation_reason`, ownership, or delegation changes.
- Renewal authority belongs to the assigned governance owner or an authorized
  delegate whose delegation remains valid for the renewed scope. CI should not
  treat a rerun, retry, or ignored exit code as renewal authority.
- Renewal triggers include acknowledgement expiration, grace-period expiration,
  unresolved strict or blocking state at the end of a review window, owner
  transfer, delegation expiration, or an escalation owner accepting renewal
  responsibility.
- Renewal metadata should include the renewal owner, renewal reason, renewal
  scope, timestamp or durable reference, renewed expiration condition, linked
  original acknowledgement or override, revalidation requirement, current
  governance summary, and escalation fallback owner.
- Stale acknowledgement, override, or grace records must not silently continue.
  If renewal authority is missing or expired, transition to review, escalation,
  or block according to the current `strictness_tier` and `lifecycle_phase`.
- Renewal failure for `strictness_tier=strict` / `lifecycle_phase=stabilize`
  should trigger escalation or remediation planning. Renewal failure for
  `strictness_tier=blocking` / `lifecycle_phase=block` should stop operational
  acceptance until an authorized owner resolves or renews it.
- Renewal state is audit metadata outside the benchmark governance contract. Do
  not add summary fields, mutate snapshots or history, alter benchmark hashes,
  or change formatter output to represent renewal, stale acceptance, or renewal
  failure.

Governance accountability escalation policy:

- `strictness_tier=advisory` / `lifecycle_phase=observe` and
  `strictness_tier=review` / `lifecycle_phase=review` may stay within local
  operator handling unless local CI policy defines a review timeout.
- `strictness_tier=strict` / `lifecycle_phase=stabilize` requires a bounded
  review window. If the issue remains unresolved after that window, escalate to
  the assigned governance owner or documented delegate for renewal, rejection,
  or remediation planning.
- `strictness_tier=blocking` / `lifecycle_phase=block` requires escalation when
  unresolved past its acknowledgement timeout, when no owner is assigned, or when
  the owner is inactive. Blocking escalation should not wait for another
  benchmark rewrite to make the state look lower risk.
- Expired acknowledgement, owner inactivity, retry-only handling, or ignored
  `--fail-on-critical` exit codes are not automatic approval. They are
  escalation triggers.
- Escalation authority should follow the consuming team's ownership chain:
  local operator -> governance owner -> delegated release or incident owner. The
  benchmark governance process only supplies deterministic evidence; it does not
  choose the human authority.
- Escalation audit metadata should include the original owner, escalation owner,
  escalation trigger, escalation timestamp or durable reference, escalation
  scope, original governance summary, snapshot or history artifact, and
  revalidation expectation.
- Acknowledgement renewal is the escalation owner's responsibility once the
  escalation is accepted. Renewal must cite the current governance result and
  cannot reuse stale acknowledgement metadata after a benchmark hash, baseline,
  compatibility, strictness, lifecycle, or escalation reason change.
- Escalation transition is operational, not a benchmark rewrite. Do not mutate
  snapshots, history, benchmark hashes, governance fields, or formatter output to
  represent unresolved, escalated, renewed, or delegated states.

Governance delegated authority chain:

- Delegation is operational authority delegation, not benchmark ownership
  transfer. The original governance summary and benchmark artifacts remain the
  deterministic source of truth.
- A governance owner may delegate acknowledgement or override authority only
  with explicit scope, authority level, reason, expiration condition,
  revalidation expectation, and escalation fallback owner.
- Delegated acknowledgement authority permits the delegate to record acceptance
  for the named benchmark scope. It does not permit changing the reported
  severity, compatibility, strictness, lifecycle phase, escalation reason, or
  benchmark artifacts.
- Delegated override authority permits a scoped operational proceed decision.
  It must preserve the original governance summary and cannot be broadened into
  future runs, other branches, or other benchmark histories without a new
  delegation record.
- Delegation for `strictness_tier=blocking` / `lifecycle_phase=block` must be
  time-bounded or run-bounded. It expires automatically when the expiration
  condition is reached, the benchmark hash or baseline changes, governance
  metadata changes, or the escalation fallback owner rejects or supersedes it.
- Delegation chains should stay short and auditable. If authority is delegated
  again, the audit record must retain the original owner, current delegate,
  intermediate delegate if any, delegated scope, authority level, reason,
  timestamp or durable reference, expiration condition, revalidation
  expectation, and fallback owner.
- After delegation expires, acknowledgement or override authority returns to the
  original owner or fallback escalation owner. Expired delegation is not implied
  approval and must not be inferred from a passing retry or ignored exit code.
- Delegation state is audit metadata outside the benchmark governance contract.
  Do not add summary fields, mutate snapshots or history, alter benchmark
  hashes, or change formatter output to represent delegated authority.

Governance dispute resolution policy:

- A dispute is a governance interpretation disagreement among the owner,
  operator, delegate, or escalation owner. It is not a request to rewrite the
  benchmark result, lower severity, or hide the governance summary.
- Disputes should cite the exact governance summary, disputed fields, snapshot
  or history artifact, command context, initiator, rationale, requested
  resolution, and provisional operational scope if any.
- Override and dispute are separate states: an override is a proceed decision,
  while a dispute is an unresolved interpretation question. A disputed
  acknowledgement may be treated as provisional only within an explicitly
  bounded scope and expiration condition.
- Authority conflicts escalate to the assigned governance owner first, then to
  the delegated escalation owner if the governance owner is unavailable,
  conflicted, or inactive. CI should not resolve authority conflicts by
  suppressing the report or retrying until a lower-risk result appears.
- Ownership conflicts require an explicit owner resolution before strict or
  blocking acknowledgement can be final. Until resolved, the original governance
  summary remains authoritative and any operational proceed decision must be
  recorded as provisional.
- `strictness_tier=blocking` / `lifecycle_phase=block` disputes require explicit
  governance owner or escalation owner resolution before acceptance. Blocking
  disagreement cannot be downgraded by local operator interpretation alone.
- Dispute resolution audit metadata should include the dispute initiator,
  disputed governance summary, disputed fields, rationale, escalation owner,
  resolution expectation, timestamp or durable reference, provisional scope, and
  final resolution.
- Resolution is operational metadata outside the benchmark governance contract.
  Do not mutate snapshots, history, benchmark hashes, governance fields, or
  formatter output to represent disputed, provisional, resolved, or rejected
  interpretation states.

Governance audit retention policy:

- Governance audit records should be retained for the consuming team's required
  release, incident, compliance, or CI audit window. Retention is owned by the
  governance owner or the CI/release owner named in the operational record.
- Archive audit records rather than deleting them when they document strict or
  blocking acknowledgement, override, dispute, escalation, delegation, grace, or
  ownership transfer. Deletion should be reserved for local scratch artifacts or
  records explicitly covered by the consuming team's data-retention policy.
- Audit records should keep immutable benchmark references: the original
  governance summary, command context, benchmark hash, snapshot or history
  artifact reference, CI run or release reference, owner, scope, and timestamp.
- Expired acknowledgement, override, dispute, escalation, delegation, or grace
  records remain part of the audit trail. Mark them expired, superseded, renewed,
  or closed in audit metadata instead of removing the original record.
- Retention records must not include raw benchmark, golden, mutation, scenario,
  or user-provided input text. Keep references and bounded governance metadata
  rather than copying benchmark payload content into the audit trail.
- Revalidation should create a new audit record linked to the prior one when the
  benchmark hash, baseline, compatibility, strictness, lifecycle,
  `escalation_reason`, owner, or delegated authority changes.
- Sunset handling should name the retention owner, sunset reason, final
  disposition, and durable reference to any archived record. Sunset does not
  change the original governance summary or benchmark artifacts.
- Retention state is operational metadata outside the benchmark governance
  contract. Do not add summary fields, mutate snapshots or history, alter
  benchmark hashes, or change formatter output to represent retention, archival,
  deletion, renewal, or sunset.

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
