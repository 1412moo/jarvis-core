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
