# Hermes Manager Pilot

Hermes Manager Pilot is a v0.1 design-only app module for testing Hermes as a
middle manager in the Jarvis-Core development workflow.

Hermes is not a coding worker. Hermes does not replace Codex. Hermes helps
manage Codex work by preserving context, waiting for responses, summarizing
results, suggesting next actions, and preparing safe prompts for the user to
approve.

## Purpose

Jarvis-Core is moving toward a personal AI assistant that can coordinate memory,
skills, multiple AI employees, and human-approved self-improvement. Today, the
user manually coordinates this loop:

```text
user
-> ChatGPT planning conversation
-> Codex implementation prompt
-> Codex result
-> ChatGPT review
-> Codex fix or commit prompt
```

Hermes Manager Pilot explores whether Hermes can hold the middle-management
state for this loop without becoming an autonomous implementer.

Response waiting means tracking what answer is needed next. It does not
authorize background execution, automatic Codex calls, or unattended commits.

## Role

Hermes acts as a response-waiting and workflow-management layer.

Example responsibilities:

- Maintain a short Jarvis-Core status summary.
- Track the current goal, blocked state, and last Codex result.
- Draft implementation prompts for Codex.
- Summarize Codex results for the user.
- Draft commit-before-review prompts.
- Maintain validation command checklists.
- Preserve excluded-file notes such as `jarvis.bat` must not be touched.
- Convert repeated workflow patterns into skill candidates.
- Propose next actions while leaving approval authority with the user.

Hermes must not:

- Edit repository files.
- Run Codex automatically.
- Call ChatGPT automatically.
- Commit or push changes.
- Treat any test as passed without evidence.
- Turn Daily AI Radar recommendations directly into implementation.

## Relationship To ChatGPT, Codex, And Jarvis-Core

| Actor | Role |
| --- | --- |
| User | Final approver and owner of decisions. |
| ChatGPT | Planning, review, and reasoning partner. |
| Codex | Coding agent that reads, edits, tests, and commits only when explicitly instructed. |
| Hermes | Middle manager that tracks state, waits for responses, prepares prompts, and recommends next actions. |
| Jarvis-Core | Source of truth for orchestration rules, records, contracts, and AI employee design. |

Hermes does not replace ChatGPT or Codex. It coordinates the workflow around
them and keeps the handoff state visible.

## v0.1 Scope

Included in v0.1:

- Document the Hermes middle-manager role.
- Define a session/state contract.
- Define prompt, review, commit, escalation, and skill-candidate boundaries.
- Provide sample session, Codex prompt, and review checklist examples.
- Preserve human approval as the authority boundary.

## v0.1 Non-Goals

Out of scope for v0.1:

- No Hermes installation.
- No Hermes runtime execution.
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
- No code modification.
- No automatic commit or push.
- No changes to Research Council, Daily AI Radar, Discord/web adapters, task
  memory, report schemas, snapshots, history, hashes, or tests.

## Basic Operating Flow

```text
user goal
-> Hermes creates a bounded Codex implementation prompt
-> user approves or edits the prompt
-> Codex works and reports result
-> Hermes summarizes result and creates a review prompt
-> user approves or edits the review prompt
-> Codex reviews and reports findings
-> Hermes creates a commit prompt only if the user explicitly asks to commit
-> Codex commits only after validation, status, staged diff, and exclusions are checked
-> Hermes records a checkpoint summary
```

The v0.1 module is documentation-only. It does not automate this flow.

## Contract

See [contracts/hermes-manager-pilot-v0.1.md](contracts/hermes-manager-pilot-v0.1.md).
