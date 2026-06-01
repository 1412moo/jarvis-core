# Research Council Governance

Detailed governance guidance for Research Council lives here. The v0.1 schema
boundary remains in
[contracts/research-council-mvp.md](contracts/research-council-mvp.md).

## Domain Profile Governance

Domain profiles are deterministic metadata in
`research_council/domain_profiles.py`. They shape local profile selection,
profile-scoped reasoning policy, and compact JSON profile metadata. They do not
authorize network calls, LLM calls, databases, APIs, UI behavior, async workers,
or new orchestration systems.

Safe profile evolution rules:

- Prefer README-only or contract-only clarification when changing operator
  expectations, support status, or review policy.
- Keep profile IDs, aliases, registry order, safety tie-breaker order,
  `selected_by` labels, JSON `profile` keys, and `quality_signals` keys stable
  unless an explicit breaking-contract change is scoped.
- Additive profile registry changes require deterministic selection keywords,
  profile policy metadata, and benchmark coverage before they can be treated as
  supported by the core benchmark pack.
- If the registry grows without benchmark coverage, do not claim core-v1
  benchmark support for the new profile until golden, mutation, or scenario
  coverage and the frozen pack metadata are intentionally updated together.
- Benchmark governance remains metadata-only: snapshots, history entries, diff
  reports, and audit records may store profile IDs, counts, case IDs, selection
  outcomes, hashes, bounded deltas, and mismatch reasons, but must not store raw
  benchmark, golden, mutation, scenario, or user-provided input text.
- The first-line governance summary stays bounded to gate, action, and policy
  trigger metadata. Put profile-specific detail in benchmark analytics, diff
  reports, or README guidance rather than adding summary fields.
- Profile deprecation is append-only: keep the old ID or alias resolvable, add a
  replacement path, and document support status. Do not repurpose an existing
  profile ID, alias, keyword meaning, or output metadata field.
- Any intentional benchmark-pack composition change must update the frozen pack
  metadata, exact smoke expectations, and README examples in the same scoped
  step, then run smoke and golden validation.

Core-v1 benchmark profile support status:

| Status | Profile IDs | Governance meaning |
| --- | --- | --- |
| Benchmark-covered | `general`, `medical_device`, `ai_saas`, `creator_tools`, `marketplace`, `enterprise_b2b`, `developer_tool` | Covered by the frozen core-v1 benchmark pack metadata and scenario-template profile coverage. |
| Registry-only | `consumer_app`, `hardware_device`, `materials_science` | Available to deterministic local profile resolution, but not core-v1 benchmark-supported until coverage and frozen pack metadata are updated together. |

This support-status table is governance guidance, not a schema migration. It
does not change `ResearchCouncilInput`, `ResearchCouncilResult`, JSON field
names, CLI behavior, benchmark hashes, or the first-line governance summary.
For the v0.1 contract boundary, see
[Governance Metadata Boundary](contracts/research-council-mvp.md#13-governance-metadata-boundary).

Profile governance terminology:

- Use `profile_support_status` only for the current support state:
  `benchmark-covered`, `registry-only`, `deprecated`, or `legacy-alias`.
- Use `change_type` only for the event being recorded, such as `promotion`,
  `deprecation`, `alias_added`, `alias_retained`, `coverage_added`, or
  `support_status_change`.
- Treat core-v1 benchmark support as benchmark-pack coverage, not as general
  profile availability. Registry presence alone is not benchmark support.

Registry-only promotion checklist:

- Keep the existing profile ID resolvable and append any new aliases without
  repurposing old aliases.
- Add benchmark coverage through golden, mutation, or scenario fixtures in the
  same scoped change; do not rely on registry presence alone.
- Update frozen pack metadata, exact smoke expectations, and README support
  status together when the benchmark pack composition intentionally changes.
- Verify exported benchmark metadata remains count-, ID-, hash-, and
  outcome-based only; do not copy raw benchmark, golden, mutation, scenario, or
  user-provided input text into snapshots, history, reports, or audit records.
- Preserve the existing first-line governance summary fields unless a separate
  append-only summary contract change is explicitly scoped.
- Run smoke and golden validation before treating the profile as
  benchmark-covered.

Profile deprecation and alias retirement:

- Treat deprecation as a support-status transition, not a registry deletion.
  Keep the deprecated profile ID resolvable until a separately scoped breaking
  change is approved.
- Retire aliases by documenting them as legacy aliases while keeping them
  mapped to the same canonical profile. Do not remap an old alias to a different
  profile to force new behavior.
- Add replacement aliases or profiles append-only, then document the replacement
  path in README guidance. Existing JSON `profile_id`, `selected_by`,
  `score_by_profile`, and `matched_keywords` metadata must remain interpretable.
- If a deprecated profile stays in the registry but leaves benchmark-covered
  support, update the support-status table and frozen pack metadata in the same
  scoped change.
- Deprecation audit records should store profile IDs, alias names, support
  status, owner, rationale, and validation command references only. Do not copy
  raw benchmark, golden, mutation, scenario, or user-provided input text.

Profile governance audit record checklist:

- `profile_id`: canonical profile ID being assessed.
- `profile_support_status`: `benchmark-covered`, `registry-only`, `deprecated`,
  or `legacy-alias`.
- `change_type`: bounded label such as `promotion`, `deprecation`,
  `alias_added`, `alias_retained`, `coverage_added`, or `support_status_change`.
- `owner`: person, team, or CI role accountable for the operational decision.
- `rationale`: short policy reason, without copying raw benchmark or user input.
- `benchmark_reference`: snapshot, history, CI run, branch, or durable artifact
  reference.
- `benchmark_hash`: hash value when a snapshot or history comparison exists.
- `governance_summary`: unchanged first-line governance summary when applicable.
- `validation_commands`: the exact smoke and golden commands that were run.
- `validation_result`: bounded result label, exit code, or durable log reference.

Do not add raw fixture text, generated scenario text, mutation input text,
golden-case body text, user-provided idea text, local filesystem paths, machine
identifiers, timestamps used as behavior inputs, or ad hoc summary fields to
profile governance audit records.

Profile governance audit lifecycle:

- Create a new profile governance audit record when support status changes,
  benchmark coverage is added or removed, alias handling changes, ownership
  changes, or the benchmark hash or comparison baseline changes.
- Link renewal, supersession, closure, or sunset records to the prior profile
  audit record instead of editing the prior record in place.
- Treat profile audit retention and sunset as operational metadata governed by
  the retention and compatibility sunset policies below. They do not mutate
  snapshots, history entries, benchmark hashes, formatter output, JSON profile
  metadata, or the first-line governance summary.
- If a profile governance audit record expires or is superseded, keep the prior
  record visible with bounded status metadata such as `expired`, `superseded`,
  `renewed`, or `closed`.
- Revalidate before relying on an old profile audit record after a benchmark
  hash change, baseline change, support-status change, owner transfer, or
  governance summary change.

Governance section reading order:

- Use `Domain Profile Governance` to decide whether a profile is benchmark-covered
  or registry-only.
- Use [Benchmark Governance CI Usage](README.md#benchmark-governance-ci-usage)
  to run deterministic benchmark commands and interpret exit behavior.
- Use `Governance summary contract rules` before changing first-line summary
  fields, order, spacing, or suffixes.
- Use the override, acknowledgement, ownership, transition, renewal,
  escalation, delegation, dispute, retention, and sunset notes only for
  operational audit handling outside the benchmark contract.

## Operator Checklist

Before code changes:

- Confirm branch and worktree status.
- Read README, governance, handoff, and relevant contract or test files.
- Identify whether the change is docs-only, test-only, or behavior-affecting.
- State whether schema, hash, output, CLI, API, UI, or DB behavior is expected
  to remain unchanged.
- Prefer the smallest scoped change and do not broaden orchestration.

Before PR:

- Review the diff for raw input, fixture, path, scenario, golden, mutation, or
  user text leakage.
- Confirm generated benchmark artifacts are not committed.
- Confirm summary fields, order, spacing, and hashes changed only if explicitly
  scoped.
- Run smoke and golden validation for behavior or app-code changes.
- For docs-only changes, record why tests were skipped.

Before merge:

- Confirm governance summary and replay output remain bounded and
  deterministic.
- Confirm any critical, strict, or blocking result has owner, scope,
  acknowledgement, and follow-up if proceeding operationally.
- Confirm contract evolution is append-only and exact smoke expectations were
  updated when summary output intentionally changed.

After merge:

- Retain audit references as bounded metadata: command context, hash, summary,
  owner, scope, and validation result.
- Revalidate if benchmark hash, baseline, compatibility, strictness, lifecycle,
  escalation reason, or owner changes.
- Remove local generated benchmark artifacts unless policy explicitly says to
  keep them.

Forbidden actions:

- Do not store or print raw benchmark, golden, mutation, scenario, fixture, or
  user-provided input text.
- Do not leak local filesystem paths or raw expected CLI input in replay or
  governance output.
- Do not edit snapshots, history, hashes, fixtures, or governance fields to make
  risk look lower.
- Do not remove, reorder, rename, or repurpose existing summary fields without
  an explicit breaking-contract scope.
- Do not add DB, API, UI, network, LLM, async, or orchestration behavior as part
  of checklist docs.

## Codex Goals Usage

Use Codex Goals as the orchestration layer for long-running
research-council governance objectives. A Goal should keep work scoped,
verified, and auditable across sessions, while this repo, its README, and its
contracts remain the source of truth.

Codex Goals manage work objectives; they do not replace smoke tests, golden
cases, schemas, benchmark hashes, governance contracts, or required command
output. research-council owns deterministic benchmark governance, so Goals must
preserve deterministic behavior, metadata-only governance, append-only contract
evolution, summary growth control, schema/hash stability, and the rule against
storing raw benchmark, golden, mutation, scenario, or user-provided input text.

Reusable Goal template:

```text
Repo path: C:\work\jarvis-core
Branch: <branch name>
Objective: <bounded governance objective>
Constraints:
- Prefer README-only or contract-only changes unless implementation is
  explicitly required.
- Preserve deterministic behavior, metadata-only governance, append-only
  contract evolution, summary growth control, and schema/hash stability.
- Do not store raw benchmark, golden, mutation, scenario, or user-provided input
  text.
Validation commands:
- python -B apps\research-council\run_smoke_tests.py
- python -B apps\research-council\run_golden_cases.py
Stop condition: Stop when the scoped objective is documented or implemented,
validation has run, and any governance risk is reported.
Report format: Changed files; objective summary; validation results;
confirmation that output, schema, hash, CLI/API/UI/DB behavior, and governance
contracts remain unchanged unless explicitly scoped.
```

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

Governance compatibility sunset lifecycle:

- Compatibility sunset is an operational lifecycle decision, not a benchmark
  rewrite. It closes or retires an old compatibility exception, grace period, or
  override while preserving the original governance summary and benchmark
  references.
- Compatibility grace expires when its bounded duration, CI run, branch, release
  candidate, or benchmark history comparison scope ends; when the benchmark hash
  or baseline changes; or when `compatibility_tier`, `strictness_tier`,
  `lifecycle_phase`, or `escalation_reason` changes.
- An expired compatibility exception is not hidden approval. After sunset, the
  affected scope requires explicit revalidation before continued operational
  acceptance.
- Treat a compatibility state as operationally unsupported when the sunset
  condition has passed, the required owner or delegate is unavailable, renewal is
  rejected or expired, the fallback owner rejects the grace, or revalidation is
  required but not completed.
- Unsupported compatibility is an escalation or review trigger, not a local
  ignore. For strict or blocking results, unsupported state should stop
  operational acceptance until an authorized owner resolves, revalidates, or
  replaces the exception.
- Compatibility downgrade or upgrade across summaries should keep the audit
  chain intact. Record the previous compatibility state, new governance summary,
  reason for transition, owner, timestamp or durable reference, and linked
  snapshot or history artifact.
- Sunset metadata should include the sunset owner, sunset trigger, timestamp or
  durable reference, affected scope, required revalidation, archive reference,
  and fallback operational state.
- Sunset records should be archived with immutable benchmark references. Do not
  copy raw benchmark, golden, mutation, scenario, or user-provided input text
  into sunset records.
- Sunset state is operational metadata outside the benchmark governance contract.
  Do not add summary fields, mutate snapshots or history, alter benchmark
  hashes, or change formatter output to represent compatibility sunset,
  unsupported state, or post-sunset revalidation.

## Generated Benchmark Artifacts

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
