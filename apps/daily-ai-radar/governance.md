# Daily AI Radar Governance

Daily AI Radar governance keeps the scout role safe, deterministic, and
metadata-first. The v0.1 app is a reporting contract only. It does not authorize
web crawling, LLM calls, task creation, code changes, commits, pushes, or live
agent orchestration.

## Safety Principles

- Preserve deterministic behavior for the same curated input.
- Keep reports metadata-first and bounded.
- Treat vendor, platform, and community claims as unverified until reviewed.
- Separate discovery from evaluation, approval, and implementation.
- Prefer references, short summaries, labels, and scores over copied source
  bodies.
- Keep self-improvement proposals visible to humans before any action.

## Human-Approved Self-Improvement Loop

Daily AI Radar may identify Jarvis self-improvement candidates, but it must not
apply them.

Allowed v0.1 loop:

```text
Daily AI Radar report
-> human review
-> optional Research Council evaluation
-> optional human-approved Jarvis task
-> Codex/human implementation review loop
-> explicit verification
```

Daily AI Radar does not directly modify Jarvis-Core. It reports improvement
candidates only. Implementation may proceed only through a separate approved
task and Codex/human review loop.

## Forbidden Actions

Daily AI Radar must not perform:

- Autonomous code modification.
- Automatic commits, including any `auto commit` behavior.
- Automatic pushes, including any `auto push` behavior.
- Uncontrolled web crawling.
- LLM or external API calls in v0.1.
- Automatic task creation.
- Scheduler, worker, or background polling behavior.
- Runtime integration with Hermes, MCP, A2A, Discord, web dashboard, or task
  memory.
- Storing full copyrighted source bodies.
- Treating vendor claims as verified truth.
- Bypassing Research Council or human review for high-risk changes.
- Changing Research Council contracts, benchmark hashes, snapshots, history, or
  smoke/golden expectations.

## Actions Requiring Human Approval

The following require explicit human approval before implementation work:

- Any code, configuration, prompt, or workflow change in Jarvis-Core.
- Any new dependency, package, crawler, web fetcher, scheduler, DB, API server,
  Discord command, or worker.
- Any permission, security, authentication, token, filesystem, or network access
  change.
- Any MCP, A2A, Hermes, LangGraph, OpenAI Agents, Anthropic, or other agent
  platform integration.
- Any self-improvement loop that changes Jarvis behavior.
- Any candidate that would create, edit, delete, move, commit, push, or deploy
  files.

## Metadata-First Rule

Daily AI Radar records only bounded metadata needed for triage.

Preferred fields:

- `item_id`
- `observed_date`
- `source_name`
- `source_type`
- `source_url_or_ref`
- `title`
- `summary`
- `claimed_capability`
- `area`
- `evidence_level`
- `notes`
- bounded scores and recommendation category

Avoid:

- Full article bodies.
- Full documentation pages.
- Full transcripts.
- Full benchmark or fixture bodies.
- Secrets, tokens, account information, private messages, or personal sensitive
  data.
- Local machine paths unless needed for a deliberately local reference.

Short excerpts may be used only when they are necessary, lawful, and bounded.
Prefer paraphrase and source references.

## Source Body and Raw Content Limits

Source material should be represented by references and short summaries. The
radar report should say what was observed, why it may matter, and what remains
unknown. It should not copy source bodies into committed fixtures or reports.

If a source body is needed for deeper evaluation, create a separate approved
research task and use bounded references. Do not expand Daily AI Radar into a
content archive.

## Jarvis Self-Improvement Guardrails

Daily AI Radar may propose self-improvement candidates only as reviewable
metadata. It must keep these guardrails visible:

- No implementation is approved by a radar recommendation alone.
- `DO_NOW` means "create or perform the next review action now", not "change
  code now".
- High-risk candidates should use `NEEDS_HUMAN_REVIEW` or
  `NEEDS_RESEARCH_COUNCIL`.
- Security, permission, autonomy, memory, and orchestration changes require
  explicit human approval before implementation.
- Research Council should review candidates with unclear evidence, high
  uncertainty, broad self-improvement impact, or non-obvious risk.

## Operator Checklist

Before changing Daily AI Radar:

- Confirm worktree status and preserve unrelated user changes.
- Keep the change additive and scoped to `apps/daily-ai-radar/` unless a later
  task explicitly expands integration.
- Confirm no code pipeline, crawler, scheduler, Discord command, DB, API, or
  real Hermes/MCP/A2A integration is being added in v0.1.
- Confirm no full copyrighted source bodies or sensitive data are stored.
- Confirm recommendations do not imply implementation approval.
- For docs-only changes, record why code tests were skipped or run optional
  smoke/golden checks for adjacent app safety.
