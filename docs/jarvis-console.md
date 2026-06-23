# Jarvis Console v0.1 Design

## 1. Purpose

Jarvis Console is the proposed long-term local browser UI for Jarvis-Core. Its
goal is to make Jarvis feel like a personal AI assistant rather than a set of
separate files, command-line tools, and JSON fixtures.

The console should provide a ChatGPT/Codex-style interaction surface where the
user can describe a goal in natural language, see which Jarvis skill or worker
is appropriate, review the proposed next step, and approve bounded handoffs.

Jarvis Console is not an autonomous execution engine in v0.1. It is a local
coordination shell for human-approved orchestration.

## 2. Recommended Document Location

Recommended location for this design: `docs/jarvis-console.md`.

Rationale:

- `docs/` already holds cross-cutting Jarvis architecture, workflow, and policy
  documents.
- Jarvis Console is not yet an implemented app. Creating
  `apps/jarvis-console/` now could imply a runnable product boundary.
- The console will eventually coordinate several app modules, including
  Research Council, Daily AI Radar, and Hermes Manager Pilot, so the first
  artifact should live at the orchestration/design layer.
- A later implementation task can create `apps/jarvis-console/` when the MVP
  shell is explicitly approved.

## 3. Current App Relationship

Jarvis-Core currently has several isolated app modules that can become console
skills or tabs.

| Module | Current role | Future console role |
| --- | --- | --- |
| Research Council | AI employee #1. Evaluates ideas, evidence gaps, risks, and experiment plans. | Research tab and research skill. |
| Daily AI Radar | AI employee #2. Turns curated technology metadata into Jarvis improvement candidate reports. | Radar tab and scout skill. |
| Hermes Manager Pilot | Middle manager for ChatGPT/Codex development workflows. | Development workflow tab and prompt handoff skill. |

The console should not erase the existing app boundaries. Each app keeps its
own contracts, governance, fixtures, and tests. Jarvis Console becomes the
human-facing shell that routes user intent to the right bounded workflow.

## 4. Design Candidate Comparison

### Candidate A: Unified Jarvis Console App

Build a new local browser app that contains chat, tabs, skill registry, task
state, approval queues, and report views from the beginning.

Advantages:

- Best long-term user experience.
- One front door for all Jarvis workflows.
- Easier for non-developers to understand.
- Makes ChatGPT/Codex-style interaction the default interface.

Disadvantages:

- Highest initial complexity.
- Risk of coupling independent app contracts too early.
- Larger safety surface if execution, approval, and reporting are all added at
  once.
- May duplicate code before stable shared contracts exist.

Implementation difficulty: high.

Safety: medium if built carefully, but higher risk for v0.1 because too much
could be bundled into the first app.

Recommendation: not recommended as the immediate next step.

### Candidate B: Keep Apps Separate, Add Console Links

Keep Research Council, Daily AI Radar, and Hermes Manager as separate apps. Add
a lightweight console page that links to each app and explains which one to use.

Advantages:

- Lowest risk.
- Preserves current app isolation.
- Minimal implementation effort.
- Avoids premature shared state and routing logic.

Disadvantages:

- Does not feel like Jarvis yet.
- The user still has to understand separate tools and workflows.
- Weak support for cross-skill orchestration.
- Does not solve the "what should I do next?" assistant experience.

Implementation difficulty: low.

Safety: high.

Recommendation: useful as a fallback, but too passive for the product
direction.

### Candidate C: Skill Registry First, UI Later

Define a skill registry contract before building a full console. Each skill
declares its purpose, inputs, outputs, approval boundary, validation commands,
and handoff rules.

Advantages:

- Good architecture foundation.
- Keeps skill boundaries explicit.
- Makes future UI routing deterministic.
- Helps prevent Daily AI Radar or Research Council outputs from being treated
  as automatic implementation approval.

Disadvantages:

- Does not immediately improve user experience.
- Registry work can become abstract if there is no UI dogfooding.
- May delay the local browser shell that the user already wants.

Implementation difficulty: medium.

Safety: high.

Recommendation: recommended as part of the path, but not sufficient alone.

### Candidate D: Local Browser Shell Reusing Hermes UI Pattern

Design first, then implement a small local browser shell that reuses the
Hermes Manager browser UI pattern: local-only server, simple HTML/CSS/JS,
guided steps, visible generated output, and no automatic external calls.

Advantages:

- Good balance between real user experience and safety.
- Reuses a proven local browser pattern from Hermes Manager Pilot v0.4.
- Lets the user dogfood a Jarvis-like shell early.
- Can start as read-only routing and prompt preparation before adding deeper
  integrations.
- Keeps human approval visible at every handoff.

Disadvantages:

- Still needs careful boundary design to avoid implying automation.
- Requires skill metadata to avoid hardcoded UI drift.
- Cross-app orchestration remains manual in the first version.

Implementation difficulty: medium.

Safety: high if it stays local-only and approval-gated.

Recommendation: recommended MVP direction after this design document.

## 5. Recommended UI Structure

Jarvis Console should use a local browser layout with three persistent regions:

1. Left sidebar or tabs for skills and records.
2. Center conversation or guided workflow area.
3. Right output and approval panel.

Recommended top-level navigation:

- Chat / Command
- Skills
- Research Council
- Daily AI Radar
- Hermes Manager
- Tasks / Reports
- Memory / Skills
- Settings / Safety

The first screen should be the actual assistant surface, not a landing page.
The user should be able to type a goal immediately.

## 6. Sidebar And Tab Design

### Chat / Command

Primary interaction surface.

Responsibilities:

- Accept natural-language goals.
- Ask clarifying questions when scope is ambiguous.
- Suggest the best skill or worker.
- Show a preview of the proposed handoff.
- Require human approval before any write, commit, push, or worker handoff.

Example:

```text
User: I want to evaluate whether this AI feature is worth building.
Jarvis: This looks like a Research Council task. I can prepare an idea review
draft. No files will be modified unless you approve a later implementation task.
```

### Skills

Registry view for available Jarvis capabilities.

Responsibilities:

- Show installed or proposed skills.
- Explain each skill's input, output, and approval boundary.
- Mark whether a skill is local-only, read-only, write-capable, or external.
- Show whether the skill is implemented, document-only, or future.

### Research Council

Dedicated workflow for idea evaluation.

Responsibilities:

- Input idea, goal, context, constraints, and locally provided evidence.
- Suggest or select a deterministic profile.
- Generate a research report.
- Summarize claims, evidence gaps, critiques, experiments, and recommendation.
- Keep reports distinct from implementation approval.

### Daily AI Radar

Dedicated workflow for technology scouting.

Responsibilities:

- Accept curated source metadata only.
- Generate a radar report.
- Highlight Jarvis relevance, risk, effort, urgency, and maturity.
- Mark candidates as `DO_NOW`, `WATCH`, `IGNORE`,
  `NEEDS_RESEARCH_COUNCIL`, or `NEEDS_HUMAN_REVIEW`.
- Offer Research Council handoff candidates without creating automatic tasks.

### Hermes Manager

Dedicated workflow for Codex/ChatGPT development coordination.

Responsibilities:

- Prepare bounded Codex implementation prompts.
- Accept pasted Codex results.
- Prepare review prompts.
- Prepare commit prompts only after explicit user approval.
- Generate checkpoint summaries.
- Keep protected paths such as `jarvis.bat` visible.

### Tasks / Reports

Operational overview.

Responsibilities:

- Show current tasks and blocked items.
- Show approval-needed items.
- Show recent reports and checkpoints.
- Show validation command status when supplied by the user or worker result.
- Distinguish draft, reviewed, approved, committed, and archived states.

### Memory / Skills

Longer-term Jarvis memory and skill governance.

Responsibilities:

- Show repeated workflow candidates.
- Show approved skills.
- Show rejected or retired skill proposals.
- Show operating rules and safety constraints.
- Keep secrets, credentials, tokens, private messages, and hidden reasoning out
  of stored memory.

## 7. ChatGPT/Codex-Style Interaction Model

Jarvis Console should feel conversational, but each action must resolve into a
bounded workflow state.

Interaction loop:

```text
user describes goal
-> Jarvis classifies intent
-> Jarvis suggests skill or worker
-> Jarvis previews inputs, outputs, and safety boundary
-> user approves the next step
-> Jarvis renders local prompt/report/task draft
-> user manually sends the prompt to Codex/ChatGPT or runs an approved local tool
-> user pastes result back
-> Jarvis summarizes, asks for review, or prepares the next approval gate
```

The console can be conversational without becoming autonomous. A generated
prompt is not an invocation. A recommendation is not approval. A report is not
verified truth.

## 8. Skill Registry Concept

Jarvis Console should eventually read a small skill registry instead of
hardcoding every tab.

Initial registry fields:

- `skill_id`
- `display_name`
- `status`
- `owner_app`
- `role`
- `input_summary`
- `output_summary`
- `allowed_actions`
- `forbidden_actions`
- `approval_required_for`
- `default_validation_commands`
- `protected_paths`
- `handoff_targets`
- `local_only`
- `external_calls_allowed`

Initial statuses:

- `document_only`
- `local_renderer`
- `local_ui`
- `approved_skill`
- `future_candidate`

The registry should be metadata-first. It should not grant broad tool
permissions by itself.

## 9. Skill Roles

### Research Council

Research Council is the review board. It evaluates an idea's assumptions,
evidence quality, risk, and experiment path.

It should not be presented as proof that an idea is true or implementation-ready.

### Daily AI Radar

Daily AI Radar is the scout. It tracks curated external technology candidates
and organizes them for Jarvis relevance.

It should not fetch the web, store full copyrighted source bodies, or convert a
radar recommendation directly into implementation.

### Hermes Manager

Hermes Manager is the workflow coordinator. It helps the user manage Codex and
ChatGPT handoffs by preparing prompts, reviews, commit prompts, and checkpoints.

It should not replace Codex, call Codex automatically, call ChatGPT
automatically, or commit on the user's behalf.

### Future Skills

Future skills may include memory management, personal routines, inbox triage,
calendar planning, coding project dashboards, local document analysis, or
developer operations helpers.

Every future skill must declare its safety boundary before implementation.

## 10. Data Flow

Recommended v0.1 data flow:

```text
Browser UI
-> local Jarvis Console shell
-> skill registry metadata
-> selected local app contract or renderer
-> generated Markdown/report/prompt
-> user approval
-> optional manual handoff to Codex, ChatGPT, or another worker
-> pasted result
-> report/checkpoint/task state update only after explicit approval
```

The console should prefer metadata and summaries over raw bodies. It should not
store full copyrighted source content, secrets, credentials, tokens, private
messages, or hidden reasoning.

## 11. Approval Flow

Approval should be visible and explicit.

Suggested approval states:

- `draft`
- `needs_user_confirmation`
- `ready_for_prompt`
- `prompt_copied`
- `result_pasted`
- `needs_review`
- `review_passed`
- `commit_prompt_allowed`
- `committed_by_codex`
- `checkpointed`
- `blocked`

Rules:

- Read-only report generation may be allowed after local input confirmation.
- Repo writes require an explicit implementation task and human approval.
- Commit prompt generation requires separate human approval.
- Actual commit execution is still performed by Codex only after a separate
  commit prompt.
- Push is never automatic and always requires a separate explicit approval.
- Daily AI Radar recommendations must pass through a separate approved task or
  Research Council review before implementation.
- Research Council reports are decision support, not verification completion.

## 12. Safety Boundary

Jarvis Console v0.1 design must preserve these boundaries:

- Local-only first.
- Bind local servers to `127.0.0.1` only when an implementation is approved.
- No Codex automatic invocation.
- No ChatGPT automatic invocation.
- No Hermes automatic invocation.
- No git commit or push execution.
- No automatic `git add`, `git checkout`, `git reset`, `git clean`, `git rm`,
  or destructive file operation.
- No network, external API, or LLM call.
- No scheduler, crawler, database, Discord command, MCP, or A2A integration in
  the first console MVP.
- No repository modification before explicit user approval.
- No auto task creation from radar or research recommendations.
- No source body or raw copyrighted content storage by default.
- No secrets, credentials, tokens, private messages, or hidden reasoning in
  persisted state.

## 13. Local-Only Principle

The first implementation should run only on the user's machine. If a browser UI
is built later, it should follow the Hermes Manager v0.4 pattern:

- Python standard library where practical.
- Static local HTML/CSS/JS.
- Server bound to `127.0.0.1`.
- No external network calls.
- Read-only git status helpers only.
- Generated output visible before any copy or handoff.
- Explicit approval gates for write-capable workflows.

## 14. Implementation Phases

### Phase 0: Design And Contract

Current phase.

Deliverables:

- This design document.
- No code.
- No new server.
- No UI implementation.
- No changes to existing app behavior.

### Phase 1: Static Local Browser Shell

Potential later task.

Scope:

- Create `apps/jarvis-console/`.
- Add local browser shell using the Hermes Manager v0.4 pattern.
- Show tabs and static skill metadata.
- Let users draft a goal and see a suggested skill.
- No live calls to app pipelines unless separately approved.

### Phase 2: Skill Registry MVP

Scope:

- Add a deterministic local skill registry.
- Register Research Council, Daily AI Radar, and Hermes Manager metadata.
- Show skill boundaries and validation commands.
- Keep all execution manual or approval-gated.

### Phase 3: Read-Only Report Launchers

Scope:

- Add local forms that prepare inputs for existing deterministic renderers.
- Generate reports to stdout or explicit user-selected output only.
- Preserve each app's existing contract.

### Phase 4: Approval Queue And Task Drafts

Scope:

- Add approval-needed list.
- Add task draft preview.
- Require human approval before writing any task or repo file.

### Phase 5: Worker Handoff Orchestration

Scope:

- Add safer handoff surfaces for Codex, ChatGPT, Hermes, or future workers.
- Still require explicit approval before every external or write-capable action.
- Consider MCP/A2A only after separate design, review, and approval.

## 15. v0.1 MVP Scope

Jarvis Console v0.1 should be design-only.

Included:

- Purpose and product direction.
- Relationship to existing apps.
- UI structure recommendation.
- Skill registry concept.
- Data flow.
- Approval flow.
- Safety boundary.
- Local-only principle.
- Implementation phases.
- Open questions.

## 16. v0.1 Non-Goals

Out of scope for v0.1:

- No new Python code.
- No new JavaScript code.
- No new HTML/CSS UI.
- No server.
- No scheduler.
- No database.
- No Discord command.
- No MCP or A2A integration.
- No Hermes runtime integration.
- No Codex automatic invocation.
- No ChatGPT automatic invocation.
- No web crawling.
- No external network, API, or LLM call.
- No repo modification by Jarvis Console.
- No automatic task creation.
- No automatic commit or push.
- No changes to Research Council, Daily AI Radar, or Hermes Manager code.

## 17. Open Questions

- Should Jarvis Console start as `docs` plus a static browser shell, or should a
  skill registry contract be committed first?
- Should the first console MVP only route to Hermes Manager, or include read-only
  views for all three current apps?
- What is the minimum persisted state: session-only browser state, local JSON,
  or existing `memory/` records?
- How should the console display approval history without becoming a task
  database too early?
- Should skill metadata live under `skills/`, each `apps/*/`, or a future
  `apps/jarvis-console/registry/` directory?
- How should future personal memory be separated from project memory?
- Which actions are safe enough for read-only buttons, and which must remain
  copy-paste prompts?
- What UI language should be the default for the user: Korean, English, or a
  configurable mix?

## 18. Recommended MVP

Recommendation:

1. Keep this v0.1 as a design document only.
2. Next, add a small skill registry design or fixture.
3. Then implement a local browser shell using the Hermes Manager v0.4 browser UI
   pattern.
4. Start with read-only routing, generated prompt previews, and approval
   boundaries.
5. Add deeper app integrations only after each handoff contract is reviewed.

This path gives Jarvis-Core a real console direction without prematurely
granting the console execution power.
