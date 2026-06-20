# Daily AI Radar MVP Contract

[Document Type]
- contract

## 1. Purpose

Daily AI Radar v0.1 defines a deterministic, metadata-first report contract for
reviewing curated AI and agent technology updates as possible Jarvis improvement
candidates.

The v0.1 pass is documentation-only. It does not implement a pipeline, crawler,
scheduler, LLM call, task writer, Discord command, database, API server, or live
Hermes/MCP/A2A integration.

## 2. Workflow

```text
curated source metadata
-> area classification
-> bounded scoring
-> recommendation category
-> Daily AI Radar Markdown report
-> optional Research Council or human review handoff
```

## 3. Non-Goals

- No web crawling.
- No network calls.
- No LLM or external API calls.
- No automatic code modification.
- No automatic task creation.
- No automatic commit or push.
- No scheduler or background worker.
- No DB, API server, Discord command, or dashboard integration.
- No real Hermes, MCP, or A2A integration.
- No changes to Research Council code, schemas, reports, snapshots, hashes,
  histories, smoke tests, or golden cases.

## 4. Input Contract

The v0.1 input is a manually curated collection of radar items. A future
implementation may name the top-level object `DailyAIRadarInput`, but this
contract defines only the stable fields.

Required top-level fields:

- `radar_date`: date string, `YYYY-MM-DD`.
- `input_type`: fixed string, `daily_ai_radar_curated_metadata`.
- `items`: array of radar item objects.

Optional top-level fields:

- `operator`: bounded operator label.
- `notes`: short note about the fixture or run.

Required item fields:

- `item_id`: stable local identifier, for example `radar-001`.
- `observed_date`: date string, `YYYY-MM-DD`.
- `source_name`: short source label.
- `source_type`: bounded source type label.
- `source_url_or_ref`: URL, durable reference, or local source reference.
- `title`: short title.
- `summary`: short metadata summary. This must not be a copied source body.
- `claimed_capability`: short statement of what the source claims or discusses.
- `area`: one allowed area label.
- `evidence_level`: bounded evidence label.
- `notes`: short triage note.

Allowed `area` values:

- `agent_skills`
- `memory`
- `orchestration`
- `mcp`
- `a2a`
- `hermes`
- `langgraph`
- `openai_agents`
- `anthropic`
- `evaluation`
- `security`
- `unknown`

Suggested `source_type` values:

- `manual_note`
- `vendor_doc_ref`
- `release_note_ref`
- `blog_ref`
- `paper_ref`
- `discussion_ref`
- `internal_observation`
- `fixture`

Allowed `evidence_level` values:

- `unverified_claim`
- `manual_summary`
- `documented_release`
- `local_demo_observed`
- `research_discussion`
- `unknown`

Input rules:

- The same input should produce the same recommendation and report if a future
  deterministic implementation is added.
- Empty `item_id`, `title`, `summary`, `claimed_capability`, `area`, or
  `evidence_level` is invalid for a real run.
- `source_url_or_ref` may be a placeholder in fixtures, but real reports should
  use a durable reference when available.
- Full source bodies, copyrighted articles, private transcripts, secrets,
  credentials, and sensitive personal data must not be stored.
- Vendor or community claims remain unverified unless a separate approved review
  establishes evidence.

## 5. Scoring Model

Each reviewed item may receive five integer scores from 1 to 5.

Required score fields:

- `relevance_to_jarvis`: 1 low, 5 high.
- `implementation_effort`: 1 small, 5 large.
- `risk`: 1 low, 5 high.
- `urgency`: 1 low, 5 high.
- `maturity`: 1 speculative, 5 mature.

Score interpretation:

- `relevance_to_jarvis` measures fit with Jarvis memory, skills,
  orchestration, evaluation, safety, or self-improvement goals.
- `implementation_effort` measures likely work, dependency, migration, or
  operational cost.
- `risk` measures security, privacy, permission, reliability, autonomy,
  vendor-lock, or governance exposure.
- `urgency` measures whether delaying review could block Jarvis progress or
  miss an important safety/control opportunity.
- `maturity` measures how stable and proven the candidate appears from the
  curated metadata.

Deterministic scoring expectations:

- Scoring must not depend on wall-clock time except the explicit `radar_date`.
- Tie-breakers should use stable ordering by `item_id`.
- Missing or unknown evidence should lower confidence, not inflate relevance.
- High vendor confidence language must not override low evidence.
- High-risk autonomy, permission, memory, security, or self-modification
  candidates must be routed to human or Research Council review.

## 6. Recommendation Categories

Allowed recommendation values:

- `DO_NOW`
- `WATCH`
- `IGNORE`
- `NEEDS_RESEARCH_COUNCIL`
- `NEEDS_HUMAN_REVIEW`

Category meanings:

- `DO_NOW`: Take the next review action now. This does not approve code changes.
- `WATCH`: Keep the item visible for later review; no immediate action.
- `IGNORE`: No Jarvis action recommended based on current metadata.
- `NEEDS_RESEARCH_COUNCIL`: Send the candidate to Research Council for evidence,
  risk, and experiment analysis before implementation planning.
- `NEEDS_HUMAN_REVIEW`: Human approval or policy review is required before any
  next step beyond documentation.

Suggested routing:

- Use `DO_NOW` only for low-risk documentation, evaluation, or review actions.
- Use `WATCH` for interesting but immature or low-urgency candidates.
- Use `IGNORE` for weak fit, redundant ideas, or unsupported claims.
- Use `NEEDS_RESEARCH_COUNCIL` when the value proposition, evidence, or
  experiment path is unclear.
- Use `NEEDS_HUMAN_REVIEW` when security, permissions, autonomy,
  self-improvement, memory retention, external access, or orchestration changes
  are involved.

## 7. Output Contract

A future structured output may be named `DailyAIRadarResult`. It should include:

- `result_type`: fixed string, `daily_ai_radar_result`.
- `version`: fixed string, `0.1`.
- `radar_date`: `YYYY-MM-DD`.
- `reviewed_items_count`: integer.
- `candidate_count`: integer.
- `executive_summary`: short summary.
- `candidate_highlights`: array of bounded candidate summaries.
- `risk_notes`: array of bounded risk notes.
- `recommended_next_actions`: array of bounded next actions.
- `human_approval_requirements`: array of approval boundary notes.
- `source_references`: array of source labels and refs.
- `rejected_or_ignored_items`: array of ignored item IDs and reasons.
- `unknowns`: array of open questions.
- `markdown_report`: report artifact.

Candidate highlight fields:

- `item_id`
- `topic`
- `area`
- `relevance_to_jarvis`
- `implementation_effort`
- `risk`
- `urgency`
- `maturity`
- `recommendation`
- `rationale`
- `human_approval_required`
- `research_council_handoff_recommended`

Output rules:

- Output must not include full source bodies.
- Output must identify unknowns instead of inventing evidence.
- Output must not claim implementation approval.
- Output must not create task files or mutate any repository file.
- Output must be deterministic for the same input.

## 8. Report Contract

The Markdown report must include these sections:

1. `Executive Summary`
2. `Candidate Highlights`
3. `Candidate Details`
4. `Ignored / Watch Items`
5. `Unknowns`
6. `Next Actions`

Required report content:

- Radar date.
- Items reviewed.
- Candidate count.
- Human approval required summary.
- Recommended next action.
- Candidate table with ID, topic, area, relevance, risk, and recommendation.
- Details for each actionable candidate.
- Risk notes.
- Source references.
- Rejected or ignored items.
- Unknowns.
- A clear statement that the report is not implementation approval or completed
  verification.

## 9. Handoff to Research Council

Daily AI Radar may recommend a Research Council handoff when:

- A candidate has high Jarvis relevance but unclear evidence.
- A candidate affects self-improvement, autonomy, memory, permissions,
  security, or orchestration.
- A candidate requires experiment design before adoption.
- A candidate appears promising but may be mostly vendor or community hype.

Handoff metadata should include:

- `source_item_id`
- `candidate_title`
- `why_it_matters_for_jarvis`
- `key_claims_to_test`
- `known_risks`
- `suggested_research_goal`

The handoff is descriptive in v0.1. It must not invoke Research Council
automatically or write Research Council inputs.

## 10. Optional Task Draft Boundary

Daily AI Radar may describe an optional task draft boundary for a human to copy
or approve later. It must not create `memory/tasks/*.md` files in v0.1.

Optional task draft metadata:

- `title`
- `repo`
- `status`: suggested value `NEEDS_APPROVAL`
- `summary`
- `approval_reason`
- `blocked_until`

Rules:

- Suggested task status should be `NEEDS_APPROVAL` for implementation,
  integration, security, permission, or self-improvement candidates.
- A suggested task draft is not an approved task.
- No `/approve`, `/run`, `/retry`, execution candidate, or status transition is
  triggered by Daily AI Radar.

## 11. App Boundary

The v0.1 app documentation lives under `apps/daily-ai-radar/`.

This v0.1 pass must not modify:

- `apps/research-council/`
- `adapters/discord/`
- `adapters/web/`
- `memory/tasks/`
- `orchestrator/`
- root `README.md`
- root `AGENTS.md`
- existing report, schema, hash, snapshot, history, smoke, or golden contracts

Contract evolution should remain additive unless a later task explicitly scopes
a breaking change.
