# Hermes Manager Pilot v0.1 Contract

[Document Type]
- contract

## 1. Purpose

Hermes Manager Pilot v0.1 defines a documentation-only contract for using Hermes
as a middle manager in Jarvis-Core development workflows.

Hermes is not a coding worker. Hermes prepares prompts, tracks state, waits for
responses, summarizes results, and recommends next actions. Codex remains the
coding agent, and the user remains the final approver.

## 2. Non-Goals

- No Hermes installation.
- No Hermes API integration.
- No MCP or A2A integration.
- No Codex automatic invocation.
- No ChatGPT automatic invocation.
- No scheduler.
- No crawler.
- No database.
- No Discord command.
- No web search.
- No LLM/API call.
- No repo modification by Hermes.
- No automatic commit or push.

## 3. Session Contract

A Hermes manager session is a bounded state object for one workflow or checkpoint
chain.

Required session state fields:

- `repo`: repository path or repo label.
- `branch`: current branch label.
- `head`: expected HEAD commit or checkpoint.
- `working_tree_status`: bounded status summary.
- `current_goal`: active human goal.
- `active_task`: current task or request label.
- `blocked_by`: empty string or blocker summary.
- `last_codex_prompt`: reference or bounded prompt summary.
- `last_codex_result_summary`: bounded result summary.
- `validation_commands`: list of commands expected before commit.
- `files_touched`: list of files reported by Codex.
- `commit_allowed`: boolean.
- `push_allowed`: boolean.
- `human_approval_required`: boolean.

Optional session state fields:

- `excluded_files`: list of paths that must not be touched.
- `last_review_prompt`: reference or bounded prompt summary.
- `last_review_result_summary`: bounded review summary.
- `last_commit_hash`: commit hash when a commit was explicitly approved and
  completed.
- `open_risks`: bounded risk notes.
- `next_action`: proposed next action.

Rules:

- Session state is a management record, not proof of execution.
- `commit_allowed=false` and `push_allowed=false` are the default safe values.
- `human_approval_required=true` is the default when implementation, commit,
  push, destructive action, permission expansion, or self-improvement is
  involved.
- Local secrets, tokens, credentials, and private raw messages must not be stored.

## 4. Input Contract

Hermes inputs may include:

- Human goal or instruction.
- ChatGPT planning summary.
- Codex result summary.
- Codex review summary.
- Validation result summary.
- Git status summary.
- File list summary.
- Explicit human approval or rejection.

Hermes must distinguish:

- Observed facts.
- User instructions.
- Codex claims.
- ChatGPT analysis.
- Hermes recommendations.
- Unknowns.

## 5. Output Contract

Hermes outputs must use one of these categories:

- `PROMPT_FOR_CODEX`
- `REVIEW_REQUEST`
- `COMMIT_REQUEST`
- `STATUS_SUMMARY`
- `BLOCKED_NEEDS_USER`
- `SKILL_CANDIDATE`
- `DAILY_RADAR_HANDOFF`
- `RESEARCH_COUNCIL_HANDOFF`

Required output fields:

- `output_category`
- `summary`
- `requires_human_approval`
- `recommended_next_action`
- `scope`
- `non_goals`
- `risks`
- `references`

Rules:

- A `PROMPT_FOR_CODEX` is a draft, not an automatic Codex call.
- A `COMMIT_REQUEST` is allowed only after explicit user approval.
- `STATUS_SUMMARY` must not claim tests passed unless validation evidence is
  present.
- Handoffs are recommendations, not automatic execution.

## 6. State Tracking

Hermes should track:

- Current repo, branch, and expected HEAD.
- Current working tree state.
- Files that should be protected or excluded.
- Last prompt sent to Codex.
- Last result received from Codex.
- Review status.
- Validation status.
- Commit/push allowance.
- Current waiting state.

State transitions must be conservative. If a result is missing or ambiguous,
Hermes should move to `BLOCKED_NEEDS_USER`.

## 7. Waiting And Responding Behavior

Hermes should explicitly wait for:

- User approval before sending an implementation prompt.
- Codex result before generating a review prompt.
- Review result before generating a commit prompt.
- User commit approval before asking Codex to commit.
- Commit result before generating a checkpoint summary.

Hermes must not silently continue when:

- The user has not approved the next step.
- Codex reports failed or skipped tests.
- `git status` includes unexpected files.
- Excluded files appear in the changed or staged set.
- Required validation commands were not run.
- The task scope changed.

## 8. Codex Prompt Lifecycle

The normal Codex prompt lifecycle is:

1. Implementation prompt.
2. Codex result.
3. Review prompt.
4. Review result.
5. Commit prompt.
6. Commit result.
7. Checkpoint summary.

Each prompt should preserve:

- Repo path.
- Expected HEAD.
- Target files.
- Excluded files.
- Scope and non-goals.
- Validation commands.
- Commit/push policy.
- Reporting requirements.

## 9. Review Lifecycle

Review prompts should ask Codex to check:

- Scope fit.
- Safety boundaries.
- Determinism.
- Tests and validation evidence.
- Git hygiene.
- User approval boundary.
- Commit readiness.

Review results should list findings first. If no issues are found, the result
should say so and still identify residual risks or skipped tests.

## 10. Commit Lifecycle

Commit is allowed only when the user explicitly approves it.

Commit checklist:

- Confirm `git status --short`.
- Confirm `.git/index.lock` is absent.
- Confirm excluded files such as `jarvis.bat` are not staged.
- Run required validation commands.
- Stage only approved files.
- Check `git status --short` after staging.
- Check `git diff --cached --stat`.
- Check `git diff --cached --check`.
- Commit with the approved message.
- Report commit hash.
- Confirm final working tree state.

Push is not allowed unless the user separately asks for it.

## 11. Escalation Rules

Hermes should produce `BLOCKED_NEEDS_USER` when:

- Required approval is missing.
- Scope conflicts with prior constraints.
- Codex output is incomplete or contradicts the requested task.
- Tests failed or were skipped without explanation.
- Protected files were modified or staged.
- A destructive action is requested without explicit approval.
- Secrets or sensitive data appear in the workflow.

Hermes may produce handoffs:

- `RESEARCH_COUNCIL_HANDOFF` for unclear evidence, high uncertainty, or
  experiment design.
- `DAILY_RADAR_HANDOFF` for technology-watch items or implementation candidates
  discovered during the workflow.

Handoffs do not execute automatically.

## 12. Skill Candidate Boundary

Hermes may mark repeated workflows as `SKILL_CANDIDATE`.

Skill candidate metadata may include:

- `workflow_name`
- `trigger`
- `repeated_steps`
- `guardrails`
- `validation_commands`
- `approval_boundary`
- `source_sessions`

Rules:

- A skill candidate is not an installed skill.
- A skill candidate must not grant new permissions.
- A skill candidate must be reviewed by a human before use.
- If the skill changes code, permissions, memory behavior, or orchestration, it
  requires explicit approval and may require Research Council review.

## 13. Prompt Queue v0.1A Implementation Boundary

Prompt Queue v0.1A is implemented as an internal, in-memory schema and safety
evaluator. It extends the contract with multi-project coordination primitives;
it does not make the documented workflow autonomous or user-facing.

Project cards declare:

- Project identity and repository-path metadata.
- Expected branch and HEAD.
- Protected paths and expected pre-existing untracked paths.
- Forbidden actions and validation-command drafts.

Queue items declare:

- Project reference, goal, task, and result type.
- Exact target files.
- Caller-supplied branch, HEAD, and `git status --short` observations.
- Separate scope, review, and commit approval booleans.
- Optional bounded prompt/result summaries and commit message.

The v0.1A evaluator must fail closed:

- Structurally invalid input is rejected.
- Unknown project references are rejected.
- Branch or HEAD mismatch produces `BLOCKED_NEEDS_USER`.
- Missing expected untracked paths or unexpected out-of-scope untracked paths
  produce `BLOCKED_NEEDS_USER`.
- Tracked changes outside exact target files produce `BLOCKED_NEEDS_USER`.
- Protected target paths, protected tracked changes, and pre-staged changes
  produce `BLOCKED_NEEDS_USER`.
- Implementation, review, and commit require approved non-empty target scope.
- Review and commit require observed target changes.
- Commit additionally requires a passed review, explicit commit approval, and
  an approved commit message.
- Any blocked result maps only to a checkpoint summary, not an executable
  implementation, review, or commit prompt.
- Renderer mapping always keeps `push_allowed=false`.

Prompt Queue v0.1A is not an authorization boundary. Approval booleans are
internal metadata and are not authenticated, signed, or bound to a stable input
digest. The module does not read Git or the filesystem, persist state, expose an
HTTP/API/GUI route, execute a command, call an external service, stage, commit,
push, or create a pull request.

Before any route, UI, persistence, or unattended workflow is considered, a
future design step must define stale-approval invalidation and bind approval to
the exact project, expected HEAD, target files, result type, and commit message.
That approval-binding behavior is not implemented in v0.1A; the separate
v0.1B-1 primitives below are enforced only by the later v0.1B-2 evaluator, not
by the historical v0.1A evaluator.

## 14. Prompt Queue v0.1B-1 Approval-Binding Boundary

Prompt Queue v0.1B-1 implements deterministic canonical approval-binding
primitives for normalized v0.1A project cards and queue items. The primitives
provide change detection only and do not grant authority.

Binding purposes are domain-separated:

- `scope` binds the implementation result type, project identity and repository
  metadata, expected branch and HEAD, safety policy, goal, task, and exact
  target files.
- `review` binds the review result type, current scope digest, caller-supplied
  change evidence digest, and observed Git state.
- `commit` binds the commit result type, current scope and review digests, the
  same change evidence digest, observed Git state, and exact commit message.

Canonical snapshots use bounded UTF-8 JSON with sorted object keys and compact
separators. Set-like path and forbidden-action lists are sorted before hashing,
while validation-command order remains significant. Each purpose uses a
distinct domain prefix before SHA-256 hashing so a digest cannot be replayed as
another binding purpose.

The primitive must reject:

- A project/item identity mismatch.
- A wrong result stage for the requested binding purpose.
- Empty scope target files or an empty commit message.
- Missing, malformed, non-lowercase, stale scope, review, or evidence digests.
- A canonical snapshot larger than the implementation limit.

Mutable prompt/result summaries and approval booleans are excluded from
canonical binding input. This avoids circular approval state and prevents an
untrusted summary from becoming authority.

v0.1B-1 limitations are mandatory boundaries:

- A digest is not a signature, secret, token, identity check, or human approval.
- `change_evidence_digest` is supplied by the caller and does not prove which
  Git diff or file content produced it.
- No Git/filesystem reader, persistence, HTTP/API/GUI route, command execution,
  external call, staging, commit, push, or pull-request behavior is added.

The v0.1B-2 evaluator integration below enforces these bindings without changing
their non-authority boundary.

## 15. Prompt Queue v0.1B-2 Evaluator Enforcement Boundary

Prompt Queue v0.1B-2 is implemented as an internal/tests-only enforcement layer
over the v0.1A queue model and v0.1B-1 binding primitives. The accepted queue
schema version is now `0.1B-2`; explicitly versioned `0.1A` input is rejected
instead of being migrated implicitly.

Queue items add:

- `scope_approval_digest`
- `change_evidence_digest`
- `review_approval_digest`
- `commit_approval_digest`

Enforcement rules are:

- Implementation requires `scope_approved=true` and a matching current scope
  binding.
- Review requires the matching scope binding and a valid change-evidence
  digest. If `review_passed=true`, its review binding must also match.
- Commit requires matching scope, evidence, review, and commit bindings. It also
  retains the v0.1A passed-review, explicit-commit-approval, observed-change,
  and exact commit-message requirements.
- Design and blocked result types reject approval binding metadata.
- Implementation rejects review, commit, and change-evidence metadata.
- Review rejects commit approval metadata.
- Missing, malformed, stale, or orphan binding data produces
  `BLOCKED_NEEDS_USER`.

The standard queue evaluator performs binding checks before classifying an item
as actionable. `build_hermes_session()` calls that evaluator, filters protected
paths as before, and cannot turn a stale or incomplete commit binding into
`commit_allowed=true`.

v0.1B-2 remains non-authoritative:

- Approval booleans and digests can still be supplied by an internal caller.
- No human identity, signature, trusted session, or one-time approval is
  established.
- `change_evidence_digest` remains caller-supplied and is not derived by a
  trusted Git/filesystem collector.
- No route, UI, persistence, filesystem reader, command execution, external
  call, stage, commit, push, or pull-request behavior is added.

The v0.1C-0A primitive below adds bounded local change-evidence collection, but
does not change the v0.1B-2 evaluator or establish human approval authority.
Route, UI, persistence, and unattended execution remain out of scope.

## 16. Prompt Queue v0.1C-0A Local Change-Evidence Boundary

Prompt Queue v0.1C-0A implements a bounded, local-only change-evidence
collector for normalized project cards and review or commit queue items. The
caller supplies an explicitly trusted absolute local repository root. The
collector requires that root to match the declared project path and the actual
Git top-level before it reads evidence.

The collected manifest binds:

- Project and queue-item identity.
- The resolved repository root, current branch, and current HEAD.
- The exact status scope: target files plus declared known-untracked paths.
- Sorted scoped Git status, not a whole-repository status claim.
- Each target's path, status, kind, byte size, and SHA-256 content digest. A
  tracked deletion uses an explicit deletion marker and no content digest.

The manifest is bounded canonical UTF-8 JSON. Its evidence digest uses a
v0.1C-0A-specific domain prefix before SHA-256. Raw target content is never
placed in the manifest.

The collector must fail closed for:

- A UNC/device-prefixed, relative, missing, mismatched, or non-Git trusted root.
- Unsafe, protected, out-of-scope, absolute, traversal, pathspec-magic,
  symlink, junction, or reparse paths.
- Directory targets, unreadable files, oversized individual or combined target
  contents, excessive Git output, or an oversized canonical manifest.
- An unexpected branch or HEAD, a missing known-untracked path, staged or
  conflicted changes, and rename/copy status.
- Target or scoped repository state that changes during bounded repeated
  collection passes.

Only fixed read-only `git rev-parse` and scoped `git status --porcelain=v1 -z`
commands are used. The Git environment removes inherited `GIT_*` variables and
disables hooks, the file-system monitor, optional locks, paging, prompting,
global/system configuration, system attributes, and external diff execution.
Command duration and captured output are bounded. Deterministic tests cover
text, binary, untracked, deleted, protected, staged, oversized, reparse,
environment-injection, and state-mutation cases, and verify that the Git index
is unchanged.

v0.1C-0A remains an internal/tests-only evidence primitive:

- It does not grant approval or authenticate a human. Its digest is not a
  signature, secret, token, identity proof, or permission to execute.
- It is not automatically consumed by the v0.1B-2 evaluator or approval-binding
  chain, and it does not update queue observations.
- It exposes no route or UI, persists no evidence or application state, and
  performs no prompt execution, staging, commit, push, pull request, external
  API, LLM, or explicit network-client call.

The later C0C design now binds repeated evidence into a fail-closed review
observation. It does not insert that observation into queue state or provide a
human approval authority. Route, UI, persistence, and unattended execution
remain out of scope until separately approved.

## 17. Prompt Queue v0.1C-0B Evidence Integrity Boundary

Prompt Queue v0.1C-0B supersedes the emitted v0.1C-0A evidence manifest version
without expanding collection I/O. Project identity, item identity, and the
declared repository path are exposed as typed evidence fields. The declared
path is included in canonical bytes, and the evidence digest uses a new
v0.1C-0B-specific domain prefix.

`verify_local_change_evidence()` is a pure, in-memory structural verifier. It
requires:

- The supported evidence type and v0.1C-0B version.
- Matching project and item identities and the normalized declared repository
  path.
- Local absolute declared and collected repository paths.
- The expected branch and HEAD.
- Exact, canonically ordered status-scope and target paths.
- Canonical scoped Git status and status/target consistency.
- Valid file or deletion metadata, per-file and aggregate bounds, and lowercase
  SHA-256 content digests for files.
- Canonical manifest bytes, matching byte size, and a matching
  domain-separated evidence digest.

Verification performs no Git command or filesystem read. It does not collect
new evidence, modify a queue item, build an approval binding, or grant
authority.
Deterministic tests cover valid evidence, identity and scope drift, unsupported
versions, non-local paths, protected targets, non-canonical status, target and
manifest tampering, byte-size mismatch, and digest mismatch.

The verifier establishes internal consistency only. Because the digest is
unkeyed, it is not proof that the collector produced the manifest and remains
neither authentication nor human approval. It adds no route, UI, persistence,
network access, prompt execution, staging, commit, push, or pull request.

The status in v0.1C-0B evidence remains deliberately scoped. It is not a
complete working-tree observation and must not be mapped directly to the queue
item's `observed_git_status`. C0C-1 through C0C-4 add separate whole-repository
coverage, repeated stale-state checks, and fail-closed observation mapping;
human approval authority and actual queue integration remain separate.

## 18. Prompt Queue v0.1C-0C Whole-Worktree Evidence

Status: the v0.1C-0C-1 bounded whole-status collector/verifier and v0.1C-0C-2
composite bundle/verifier are implemented as internal/tests-only primitives.
The v0.1C-0C-3 pure handoff decision and v0.1C-0C-4 review-observation adapter
are also implemented internal/tests-only.

### 18.1 Problem

v0.1C-0B provides content-bound evidence for exact target files and status for
those targets plus declared known-untracked paths. This is sufficient for a
bounded target manifest but not for `QueueItem.observed_git_status`, whose
evaluator semantics assume every Git-visible working-tree change is present.
Mapping scoped status into that field would hide unrelated changes and weaken
protected-path and out-of-scope checks.

### 18.2 Decision

Retain scoped target-content evidence and add a separate whole-worktree status
artifact. A composite review-evidence bundle binds the two artifacts to one
repeated collection window.

The design has three layers:

1. `TargetChangeEvidence`: the existing v0.1C-0B exact-target content and status
   manifest.
2. `WholeWorktreeStatusEvidence`: every Git-visible tracked and untracked status
   entry, with an explicit `git-visible-whole-worktree` coverage marker.
3. `ReviewEvidenceBundle`: project/item identity, declared and resolved roots,
   branch, HEAD, target-evidence digest, whole-status evidence, collection
   bounds/version, and a domain-separated composite digest.

The composite digest—not the scoped target digest—is the only value C0C-4 may
apply as `change_evidence_digest`. The whole-worktree status—not scoped
status—is the only value it may apply as `observed_git_status`.

### 18.3 Rejected Alternatives

- Directly map `scoped_git_status` into `observed_git_status`: rejected because
  it would make an incomplete observation appear complete.
- Explicitly open or hash every changed file in collector code: rejected because
  it expands sensitive-content collection beyond approved target files.
  Whole-worktree evidence contains paths and Git status only; the underlying
  Git command may still inspect working-tree files while computing status.
- Store only a clean/dirty boolean: rejected because it cannot identify
  protected, unexpected, staged, conflicted, renamed, or copied paths and is not
  reviewable.
- Collect target and whole-worktree evidence in unrelated calls: rejected
  because state could change between artifacts without invalidating the bundle.

### 18.4 Composite Collection Algorithm

The v0.1C-0C-2 composite collector:

1. Require the same explicitly trusted local absolute root and normalized
   project/item boundary as v0.1C-0B.
2. Repeatedly samples branch, HEAD, and complete Git-visible status with fixed
   read-only Git commands around target hashing.
3. Collects exact-target content evidence twice inside the repeated whole-status
   window.
4. Rejects if whole status or target evidence differs between samples.
5. Verifies scoped/whole status agreement and creates one canonical composite
   bundle that binds both nested evidence digests.

The whole-status command must have no pathspec and must explicitly request all
untracked file entries in NUL-delimited porcelain format. It must retain the
existing sanitized Git environment, disabled hooks/file-system monitor,
optional-lock protection, paging/prompt suppression, and local-only execution.
Ignored files and filesystem objects unknown to Git are excluded; the coverage
marker must make that limitation explicit.

Collection is repeated and fail-closed, not atomic. A mutation can still occur
after the final sample. No design wording may claim an operating-system snapshot
or cryptographic provenance.

### 18.5 Bounds And Failure Rules

C0C-1 reuses conservative fixed limits for command duration, output, canonical
bytes, path length, and status-entry count. Bounded pipe readers terminate the
Git process when stdout or stderr exceeds the byte limit rather than accepting
truncated status. Any limit violation produces no status artifact.

Whole-status evidence creation fails for:

- A branch, HEAD, or status change between samples.
- Non-UTF-8, malformed, quoted, absolute, traversal, pathspec-magic, rename, or
  copy status that cannot be represented unambiguously.
- Staged or conflicted changes.
- Missing declared known-untracked paths.

Composite evidence creation additionally fails for target/status
disagreement, a protected target, symlink/reparse traversal in content targets,
directory or unsupported submodule targets, and content-size violations.

Unexpected but well-formed out-of-scope paths must remain present in the
whole-status artifact. They must produce blocking reasons and must never be
filtered out to manufacture an apparently safe observation.

Declared known-untracked paths must also remain present and bound in complete
status. They may be classified as expected only by exact normalized path; that
classification must not make them targets or authorize reading their content.

### 18.6 Handoff Boundary

The v0.1C-0C-3 pure handoff decision verifies the composite bundle and returns
either:

- A blocked result with explicit reasons and no queue-observation fields; or
- An immutable preview of `observed_branch`, `observed_head`, complete
  `observed_git_status`, and the composite `change_evidence_digest`.

The preview must not mutate a `QueueItem`, set approval booleans, construct a
review/commit approval digest, or call the evaluator automatically. C0C-4 may
apply a safe preview only by returning a new review-stage item; connecting that
item to queue normalization, storage, or evaluator flow remains a separate
implementation and approval step.

### 18.7 Safety And Non-Goals

v0.1C-0C does not design or authorize:

- Human identity, authenticated approval, signing, secrets, or one-time tokens.
- Route, API, UI, persistence, background monitoring, or unattended execution.
- Explicit content collection, hashing, or return outside exact approved
  targets. Whole-status approval still permits Git's normal local working-tree
  inspection required to compute status.
- Staging, committing, pushing, pull requests, deletion, archive, or migration.
- External API, LLM, network, or credential use.
- Memory/Skills save, UI Save/Confirm, or Voice Inbox auto-save behavior.

Implementation remains split into separately reviewable internal/tests-only
units: bounded whole-status collection, composite-bundle verification, pure
handoff decision, and review-observation adaptation. All four units are
implemented. They do not authorize queue-state integration, route, UI,
persistence, execution, or other user-facing behavior.

### 18.8 v0.1C-0C-1 Implementation Boundary

`collect_whole_worktree_status_evidence()` now collects branch, HEAD, and every
Git-visible porcelain status entry without a pathspec. It binds an explicit
`git-visible-whole-worktree` coverage marker and produces a domain-separated
v0.1C-0C-1 digest. Collector code does not explicitly open or hash out-of-target
files, and the artifact contains no file contents. The invoked Git status
command may perform its normal local working-tree inspection.

`verify_whole_worktree_status_evidence()` performs pure structural, canonical,
and digest verification without Git or filesystem reads. The digest remains
unkeyed and proves neither collector provenance nor human approval.

The Git runner now bounds stdout and stderr while the process is running and
terminates on overflow or timeout. Deterministic tests cover complete status,
unexpected and protected paths, known untracked paths, no-content behavior,
index stability, inherited safety settings, tampering, missing expected paths,
staged state, collection races, entry limits, and exact/oversized pipe bounds.

C0C-1 is not directly connected to the queue evaluator, approval bindings,
routes, UI, persistence, or execution. C0C-2 now binds it to C0B target
evidence, but neither artifact may populate a queue item automatically.

### 18.9 v0.1C-0C-2 Implementation Boundary

`collect_review_evidence_bundle()` collects whole status three times around two
exact-target evidence passes. It rejects whole-status drift, target-content
drift, and scoped/whole status disagreement. The repeated sequence reduces but
does not eliminate the documented post-sample race.

The resulting bundle binds project/item identity, declared and resolved roots,
branch, HEAD, the v0.1C-0B target-evidence digest, the v0.1C-0C-1 whole-status
digest and coverage marker, nested evidence versions, and a v0.1C-0C-2-specific
domain-separated bundle digest. Raw file content is not placed in the bundle.

`verify_review_evidence_bundle()` verifies both nested artifacts, their metadata
and status agreement, canonical bundle bytes and size, and the composite digest
without Git or filesystem reads. Deterministic tests cover complete unexpected
status preservation, nested digest binding, no-content output, pure verification,
target-content invalidation, metadata/canonical/digest tampering, explicit
status disagreement, and mutation between target samples.

C0C-2 does not mutate a queue item, populate observation fields, call the queue
evaluator, create approval bindings, or grant authority. Its unkeyed bundle
digest proves neither provenance nor human approval. C0C-3 consumes it only for
a pure blocked-or-preview decision, never an automatic queue transition.

### 18.10 v0.1C-0C-3 Implementation Boundary

`build_review_evidence_handoff_decision()` first verifies the complete C0C-2
bundle. Malformed, stale, inconsistent, or tampered evidence returns one
deterministic validation blocking reason and no preview.

For valid bundles, the decision classifies the complete whole-worktree status:

- Exact declared known-untracked paths remain tolerated exclusions.
- Protected paths and descendants produce blocking reasons.
- Tracked or untracked changes outside exact target files produce blocking
  reasons and remain visible.
- At least one target must have an observed Git change.
- A target may not overlap a declared known-untracked exclusion.

Only a decision with no blocking reasons contains an immutable
`QueueObservationPreview`. The preview carries project/item identity, observed
branch and HEAD, complete whole-worktree Git status, the C0C-2 composite digest,
and the explicit whole-worktree coverage marker. It carries no approval flags,
review result, commit message, or execution authority.

The handoff decision is deterministic and performs no Git/filesystem read. Tests
cover safe preview creation, complete-status and composite-digest selection,
absence of approval fields, QueueItem immutability, pure verification,
unexpected paths, protected descendants, tampered bundles, missing target
changes, and target/known-untracked overlap. The test Git fixture now pins
`core.autocrlf=false` so results do not depend on user-global Git configuration.

C0C-3 does not update queue state, call `evaluate_queue_item()`, build scope,
review, or commit approval bindings, or expose any route/UI/persistence. C0C-4
may apply its safe preview to a new in-memory review item, but actual queue-flow
integration remains a separate design and approval step.

### 18.11 v0.1C-0C-4 Implementation Boundary

`apply_review_evidence_observation()` accepts a normalized project, a
review-stage `QueueItem`, and a C0C-2 bundle. It recomputes the C0C-3 fail-closed
decision and raises `ValidationError` unless a safe preview is available. It
also rejects an item that already has a change-evidence digest, a passed review
or review-approval digest, or commit-approval metadata, so it cannot silently
replace evidence or carry a new observation across a later approval boundary.

For a safe input, the adapter returns a new immutable item with exactly four
replaced fields: `observed_branch`, `observed_head`, complete
`observed_git_status`, and the composite `change_evidence_digest`. The input
item remains unchanged. Scope approval fields and every other queue-item field
are preserved rather than created, cleared, or reinterpreted.

The adapter is deterministic and performs no Git/filesystem read. Tests cover
exact-field replacement, input immutability, approval-field preservation, pure
repeatability, wrong-stage and pre-existing-metadata rejection, tampered bundle
rejection, and unsafe whole-status rejection.

C0C-4 does not normalize, insert, replace, or persist an item in
`PromptQueueState`; call `evaluate_queue_item()`; create or validate a
scope/review/commit approval binding; grant human approval; or expose route, UI,
command execution, staging, commit, push, pull request, network, API, or LLM
behavior. Queue-flow and approval-flow integration remain unimplemented and
separately gated.
