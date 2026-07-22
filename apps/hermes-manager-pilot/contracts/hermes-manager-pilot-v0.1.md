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
are also implemented internal/tests-only. C0C-5 adds the internal/tests-only
pure queue observation evaluator described in Section 18.12. C0C-6 fresh review
revalidation and review-session adaptation are implemented internal/tests-only
as C0C-6a and C0C-6b in Section 18.13.

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
handoff decision, review-observation adaptation, and pure queue observation
evaluation, fresh review revalidation, and review-session adaptation. All seven
units are implemented. They do not authorize durable queue state, route, UI,
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
behavior. Queue persistence, renderer/execution, and approval-flow integration
remain unimplemented and separately gated.

### 18.12 v0.1C-0C-5 Queue Observation Evaluation

Status: the C0C-5 pure queue observation evaluator is implemented as
internal/tests-only. No route, UI, or persistence is connected.

#### 18.12.1 Problem

C0C-4 can return a safe replacement review item but deliberately has no queue
context and does not call the existing evaluator. A caller could otherwise
replace the wrong item, alter another queue entry, lose ordering, or treat a
safe evidence preview as though it had already passed scope and approval
checks. The bridge must make that transition deterministic without
turning an in-memory classification into execution authority.

#### 18.12.2 Implemented Interface

The implementation adds this immutable result type:

```python
@dataclass(frozen=True)
class QueueObservationEvaluation:
    queue: PromptQueueState
    item: QueueItem
    evaluation: QueueEvaluation
```

and this pure entry point:

```python
def evaluate_review_evidence_in_queue(
    queue: PromptQueueState,
    item_id: str,
    bundle: ReviewEvidenceBundle,
) -> QueueObservationEvaluation:
    ...
```

#### 18.12.3 Implemented Algorithm

1. Require a normalized `PromptQueueState`, a bounded non-empty item ID, and a
   `ReviewEvidenceBundle`.
2. Resolve exactly one item and its project from the supplied queue. Missing or
   inconsistent identity fails with `ValidationError`.
3. Call `apply_review_evidence_observation()` with that project and item. All
   C0C-4 wrong-stage, existing-metadata, bundle-integrity, protected-path, and
   out-of-scope checks remain authoritative.
4. Replace only the selected item in a new items tuple. Preserve project tuples,
   queue type/version, item order, every other item, and the original queue.
5. Create a new immutable `PromptQueueState` and call
   `evaluate_queue_item(new_queue, item_id)` exactly once.
6. Return the new queue, its selected replacement item, and the complete
   `QueueEvaluation` without rendering, persistence, or further transition.

An evidence or identity failure raises `ValidationError` and returns no partial
result. A valid evidence snapshot with missing, malformed, or stale scope
approval remains a successful bridge result whose evaluation is
`BLOCKED_NEEDS_USER`. The bridge must not convert evaluator blocking reasons
into success and must not create or repair approval metadata.

#### 18.12.4 Snapshot And Staleness Boundary

C0C-5 is pure after evidence collection. It performs no Git or filesystem read
and therefore can only classify the captured C0C-2 snapshot.
It must not claim that branch, HEAD, content, or whole-worktree status is still
current after collection. The existing repeated collector reduces in-window
races but cannot eliminate a mutation after its final sample.

Any future prompt execution, review approval, commit transition, persistence,
or unattended workflow must define and implement its own current-state
recollection or stale-evidence rejection before gaining authority. C0C-5 does
not satisfy that later boundary.

#### 18.12.5 Implemented Tests

Deterministic tests cover:

- Safe replacement of exactly one selected item with project and item order
  preserved.
- Original queue and all non-selected items remaining unchanged.
- Exact propagation of the C0C-4 four observation fields and preservation of
  all approval metadata.
- An evaluator-accepted review item when a valid existing scope binding is
  supplied.
- A visible `BLOCKED_NEEDS_USER` evaluation when scope approval is missing or
  stale, without discarding the new pure snapshot.
- Missing item/project, bundle identity mismatch, unsafe status, tampered
  evidence, wrong result stage, and existing later-stage metadata failing
  closed.
- No Git/filesystem read, renderer/pipeline call, queue persistence, approval
  creation, route, UI, network, API, or LLM behavior.

#### 18.12.6 Non-Goals And Approval Boundary

C0C-5 does not include JSON queue normalization, a durable queue store, queue
editing UI, background monitoring, prompt/session rendering, Codex or ChatGPT
invocation, command execution, review/commit approval creation, staging,
commit, push, pull request, Memory/Skills save, UI Save/Confirm, Voice Inbox
auto-save, credential use, or external communication.

The implementation remains internal/tests-only and limited to the pure bridge
and deterministic tests. `evaluate_review_evidence_in_queue()` validates queue
identity consistency, calls C0C-4, replaces one selected item in a new immutable
snapshot, and calls the existing evaluator exactly once. It returns evaluator
blocking reasons without upgrading authority and raises `ValidationError`
before evaluation when queue identity or evidence validation fails.

Connecting its output to `build_hermes_session()`, the renderer pipeline, a
route, UI, persistence, or any execution/approval flow is a separate scope gate.

### 18.13 v0.1C-0C-6 Fresh Review Handoff

Status: the C0C-6a fresh blocked-or-preview decision is implemented as
internal/tests-only. The C0C-6b review-session adapter is also implemented as
internal/tests-only. A separately approved Jarvis Console consumer now exposes a
write-free local preview route and bounded read-only session display. No Hermes
renderer connection, prompt display, approval creation, or persistence is
implemented.

#### 18.13.1 Problem

C0C-5 evaluates a verified C0C-2 snapshot without reading the repository. The
working tree can change after the bundle's final sample, so directly passing a
C0C-5 queue to `build_hermes_session()` would let a review prompt describe stale
branch, HEAD, target content, or whole-worktree status. The next boundary must
recollect current local evidence while preserving the distinction between a
fresh review observation and authority to render, execute, approve, or commit.

#### 18.13.2 Decision And Unit Split

C0C-6 is divided into two separately reviewable units:

1. C0C-6a fresh review decision: validates the complete C0C-5 wrapper, recollects
   current evidence, and returns either blocking reasons or an immutable handoff
   preview. It does not call `build_hermes_session()` or any renderer.
2. C0C-6b session adapter: accepts only a valid C0C-6a preview and maps its exact
   queue/item through `build_hermes_session()`. It does not render, execute,
   persist, or communicate externally.

This split keeps the Git/filesystem revalidation boundary separate from session
adaptation. The later Jarvis Console consumer composes these units without
changing either primitive's authority.

#### 18.13.3 Implemented C0C-6a Interface

The implementation adds these immutable values:

```python
@dataclass(frozen=True)
class FreshReviewHandoffPreview:
    queue: PromptQueueState
    item: QueueItem
    evaluation: QueueEvaluation
    fresh_bundle_digest: str


@dataclass(frozen=True)
class FreshReviewHandoffDecision:
    project_id: str
    item_id: str
    blocking_reasons: tuple[str, ...]
    preview: FreshReviewHandoffPreview | None
```

and this bounded local entry point:

```python
def build_fresh_review_handoff_decision(
    trusted_repo_root: str | Path,
    observation: QueueObservationEvaluation,
) -> FreshReviewHandoffDecision:
    ...
```

#### 18.13.4 C0C-6a Validation Before I/O

Before any repository read, the function must:

1. Require a `QueueObservationEvaluation` containing supported queue type and
   version, normalized tuple structure, unique item/project identities, and no
   orphan project references.
2. Resolve exactly one queue item matching `observation.item.item_id` and require
   exact equality with `observation.item`.
3. Recompute `evaluate_queue_item()` from the supplied queue and require exact
   equality with `observation.evaluation`. A caller-supplied evaluation is not
   trusted merely because it is frozen.
4. Return a blocked decision without Git/filesystem I/O if the recomputed
   evaluation is blocked.
5. For a non-blocked candidate, require `result_type=review`,
   `next_action=REVIEW_REQUEST`, `render_mode=review-prompt`, a valid current
   scope binding, a lowercase bounded change-evidence digest, no passed-review
   metadata, and no commit-approval metadata.

Malformed wrapper structure or inconsistent identities produce
`ValidationError`. A valid wrapper whose evaluator is blocked returns the
evaluator's deterministic blocking reasons and no preview.

#### 18.13.5 Fresh Collection And Comparison

Only after the pre-I/O gate passes may C0C-6a call
`collect_review_evidence_bundle()` once with the explicitly trusted local root,
the selected project, and the selected review item. The existing collector's
root validation, fixed local Git commands, sanitized environment, repeated
whole-status/target sampling, bounds, exact-target hashing, staged-state
rejection, and no-content artifact rules remain authoritative.

The fresh result must then pass `verify_review_evidence_bundle()` before any
field or digest comparison. Collector output is not trusted merely because it
has the expected Python type.

Collection or verification failure becomes a deterministic blocking reason and
no preview. For a newly collected bundle, all of these values must match the
C0C-5 item exactly:

- `fresh_bundle.bundle_digest` and `item.change_evidence_digest`, compared
  without treating the unkeyed digest as a secret or signature.
- Fresh branch and `item.observed_branch`.
- Fresh HEAD and `item.observed_head`.
- Fresh complete whole-worktree status and `item.observed_git_status`, including
  ordering and declared known-untracked entries.
- Project and item identity, declared/resolved repository root, target scope,
  and whole-worktree coverage already bound by C0C-2 verification.

Any mismatch returns a single stale-evidence blocking result and no preview. A
successful preview carries the exact immutable C0C-5 queue, selected item,
recomputed evaluation, and fresh bundle digest. It does not carry a session,
rendered prompt, approval, command, or execution flag.

#### 18.13.6 Implemented C0C-6b Review Session Adapter

C0C-6b must not accept an arbitrary queue or C0C-5 wrapper. It may accept only
the exact queue and item carried by a non-blocked C0C-6a preview. Before
returning a local `SessionState`, it must recompute the queue evaluation and
require the preview fields and evaluation to remain unchanged.

The implemented entry point is:

```python
def build_review_session_from_fresh_preview(
    preview: FreshReviewHandoffPreview,
) -> SessionState:
    ...
```

The resulting session must satisfy all of these review-only conditions:

- `next_action=REVIEW_REQUEST` and an empty `blocked_by` value.
- `commit_allowed=false` and `push_allowed=false`.
- `human_approval_required=true` and `human_approval_granted=false`.
- No commit message and no review/commit approval creation.
- Existing protected-path filtering and validation-command boundaries remain
  unchanged.

C0C-6b constructs and validates a session only. Calling a renderer,
displaying or persisting a prompt, invoking Codex/ChatGPT/Hermes, or executing a
command remains a later scope gate.

#### 18.13.7 Race And Authority Boundary

Fresh collection is repeated and fail-closed but is not an operating-system
snapshot. A working-tree mutation can occur after its final sample or after a
preview is returned. C0C-6a therefore supports a fresher local review-session
handoff only; it is not sufficient for commit authority, unattended execution,
or a later approval decision. Any future commit or execution boundary must
collect or verify its own current state again.

The bundle digest remains unkeyed. Matching it proves deterministic equality of
the bounded manifests, not collector provenance, human identity, authenticity,
or permission to act.

#### 18.13.8 Implemented C0C-6a And C0C-6b Tests

Deterministic tests cover:

- A valid C0C-5 review wrapper and unchanged repository producing one preview.
- Exact queue/item/evaluation preservation and fresh digest propagation.
- Blocked C0C-5 evaluation returning reasons without calling Git or the
  collector.
- Wrapper type, selected-item equality, queue identity, project reference, and
  caller-supplied evaluation inconsistencies failing before repository I/O.
- Wrong result stage, passed-review metadata, commit metadata, and malformed or
  missing evidence digest failing before repository I/O.
- Target content, whole status, branch, or HEAD changes producing no preview.
- Collector validation errors, unsafe paths, staged state, bounds, and
  collection races remaining fail-closed.
- C0C-6a performing no queue mutation or session construction, and neither unit
  calling a renderer/pipeline, creating approval, or adding route, UI,
  persistence, command execution, network, API, or LLM behavior.
- A valid fresh preview producing an exact deterministic review-only
  `SessionState` through one call to the existing session builder.
- Adapter input, queue/item/evaluation, fresh digest, commit-stage metadata, and
  blocked-review inconsistencies failing before session construction.
- The adapter performing no Git read and rejecting an unsafe session returned by
  the existing builder.

#### 18.13.9 Non-Goals And Approval Boundary

C0C-6 does not authorize prompt rendering or display, durable queue or evidence
storage, background monitoring, filesystem watching, route/API/UI/mobile
integration, automated Codex/ChatGPT/Hermes invocation, review or commit
approval creation, staging, commit, push, pull request, destructive operations,
credentials, external communication, Memory/Skills save, UI Save/Confirm, or
Voice Inbox auto-save.

C0C-6a and C0C-6b remain internal/tests-only. The first validates the C0C-5
wrapper before I/O, preserves evaluator blocks without collection, recollects
and verifies one fresh C0C-2 bundle for actionable review, and returns a preview
only for exact digest/branch/HEAD/status agreement. The second accepts only that
validated preview and returns an exact review-only `SessionState`.

The separately approved Jarvis Console v0.1 consumer is limited to one
write-free local preview route. It accepts a caller-supplied, already
scope-approved queue snapshot, fixes filesystem authority to the Jarvis-Core
root, re-runs C0C-2/C0C-5/C0C-6a/C0C-6b, and displays only bounded review-session
fields. It does not persist the input or output, create approval metadata, return
raw target contents or evidence bytes, render a prompt, execute a command, or
enable commit/push authority.

Any broader renderer, persistence, automatic handoff, approval, execution,
arbitrary-repository, or external consumer still requires a new explicit scope
approval.

## 19. Copy-only Jarvis Review Handoff Boundary

The separately approved copy-only integration adds one local Hermes route,
`POST /api/review-handoff`, and one Step 5 UI action. The route accepts the
current in-memory browser session plus the explicit claim that the existing
`Confirm Scope` step was completed. It fixes all Git reads to the Jarvis-Core
root and uses only the existing read-only Git allowlist.

The route builds one deterministic JSON envelope with exactly `queue` and
`item_id`. It binds the confirmed goal, task, target files, project safety
policy, branch, and HEAD with the existing scope-binding primitive. The binding
detects later changes to those inputs. It is not authentication, proof of human
identity, review approval, commit approval, or execution authority.

The exported item is at the unreviewed `review` stage. Change-evidence,
review-approval, and commit-approval digests are empty; `review_passed` and
`commit_approved` are false; the commit message is empty. Required forbidden
actions remain present and `jarvis.bat` must remain protected and untracked.

Jarvis accepts the exact envelope only as browser convenience, extracts its
queue and item ID locally, and sends the unchanged write-free preview request.
There is no Hermes-to-Jarvis request, durable queue/session/handoff storage,
prompt rendering, command execution, automatic commit/push/PR, arbitrary repo
selection, external call, Memory/Skills save, UI Save/Confirm, or Voice Inbox
auto-save.

The implementation was verified with deterministic tests, the full Hermes and
Jarvis smoke suites, and one real current-work browser path through fresh local
evidence and a read-only review display.
