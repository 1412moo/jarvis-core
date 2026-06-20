# Daily AI Radar

Daily AI Radar is a candidate second Jarvis AI employee. Its role is to act as a
scout for new AI, agent, framework, protocol, and platform updates that may
matter to Jarvis.

The app does not implement those updates. It turns curated technology metadata
into a bounded radar report so a human can decide whether a candidate should be
watched, ignored, reviewed by Research Council, or converted into an explicitly
approved follow-up task.

## Role

Daily AI Radar observes and organizes possible Jarvis improvement candidates
from manually supplied source metadata.

Examples of tracked areas:

- Agent Skills and reusable task procedures
- Memory and personal context systems
- Agent orchestration patterns
- MCP, A2A, Hermes, LangGraph, OpenAI Agents, and related agent platforms
- Evaluation, security, permissions, and governance patterns

The scout role is intentionally limited:

- It may identify a possible improvement.
- It may explain why the improvement could matter to Jarvis.
- It may recommend a next review step.
- It must not modify Jarvis-Core, create code, or apply the improvement itself.

## Difference From Research Council

Daily AI Radar and Research Council have different jobs.

| App | Primary job | Output |
| --- | --- | --- |
| Daily AI Radar | Discover and classify externally or manually supplied technology candidates. | A radar report with relevance, risk, recommendation, and approval boundary metadata. |
| Research Council | Evaluate a candidate idea's validation risks, evidence gaps, and minimum experiments. | A research report with claims, evidence ledger, critiques, experiments, and recommendation. |

Daily AI Radar is the scout. Research Council is the review board.

## v0.1 Scope

Daily AI Radar v0.1 is a document and contract foundation only.

Included:

- Assume input comes from human-curated source metadata.
- Define a report format.
- Define recommendation categories.
- Define the human approval boundary for self-improvement candidates.
- Provide a deterministic sample input and sample report.

## v0.1 Non-Goals

Out of scope for v0.1:

- No web crawling.
- No web fetcher.
- No scheduler.
- No LLM or external API calls.
- No Python package or code pipeline.
- No Discord command.
- No database.
- No API server.
- No automatic task creation.
- No autonomous code modification.
- No automatic commit or push.
- No real Hermes, MCP, or A2A integration.
- No changes to Research Council, Discord, web dashboard, task memory, reports,
  benchmark snapshots, hashes, or existing test contracts.

## Basic Flow

```text
curated source metadata
-> normalize candidate fields
-> classify area
-> score Jarvis relevance, effort, risk, urgency, and maturity
-> assign recommendation category
-> render Daily AI Radar report
-> optionally hand off a candidate to Research Council or a human-approved task draft
```

The optional handoff is descriptive in v0.1. No task file is created, no code is
changed, and no integration is executed by Daily AI Radar itself.

## Approval Boundary

Daily AI Radar reports are not implementation approval. A candidate must pass
through a separate human-approved Jarvis task and review loop before any code,
configuration, workflow, or integration change is made.

Any high-risk, security-sensitive, permission-changing, orchestration-changing,
or self-improvement candidate should be marked `NEEDS_HUMAN_REVIEW` or
`NEEDS_RESEARCH_COUNCIL` before implementation is considered.

## Contract

See [contracts/daily-ai-radar-mvp.md](contracts/daily-ai-radar-mvp.md).
