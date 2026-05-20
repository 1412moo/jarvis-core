# Research Council MVP Contract

[Document Type]
- contract

## 1. Purpose

Research Council v0.1 defines a local, deterministic app workflow that converts a
raw idea and goal into a structured research report.

The first pass is a schema and contract foundation. It intentionally avoids real
research automation. The pipeline may return placeholder deterministic outputs as
long as those outputs match the stable schema.

## 2. Workflow

```text
raw idea + goal
-> structured claims
-> evidence ledger
-> reviewer critiques
-> minimum viable experiments
-> markdown research report
```

## 3. Non-Goals

- No web search.
- No network calls.
- No LLM calls.
- No fake citations.
- No Discord integration.
- No dashboard integration.
- No task memory integration.
- No writes to global `reports/`.
- No full agent orchestration implementation.

## 4. Input Contract

`ResearchCouncilInput` is the single pipeline input object.

Required fields:

- `raw_idea`: string. The user's unstructured idea.
- `goal`: string. The outcome the user wants to understand, validate, or reach.

Optional fields:

- `context`: string or null. Extra background supplied by the user.
- `constraints`: tuple of strings. User-supplied limits such as budget, timing, or
  scope.
- `provided_evidence`: tuple of strings. Evidence supplied directly by the user.

Rules:

- Empty `raw_idea` or `goal` is invalid for a real run.
- `provided_evidence` may be empty.
- External evidence must not be invented.

## 5. Output Contract

`ResearchCouncilResult` is the single pipeline result object.

Required fields:

- `result_type`: string, fixed as `research_council_result`.
- `version`: string, fixed initially as `0.1`.
- `input_summary`: string.
- `claims`: tuple of `Claim`.
- `evidence_ledger`: tuple of `EvidenceEntry`.
- `reviewer_critiques`: tuple of `ReviewerCritique`.
- `experiments`: tuple of `ExperimentPlan`.
- `recommendation`: `Recommendation`.
- `markdown_report`: `MarkdownReport`.
- `warnings`: tuple of strings.

The result must contain at least one claim, one evidence ledger entry, one critique,
one experiment, one recommendation, and one Markdown report.

## 6. Claim Contract

`Claim` represents a structured research claim.

Fields:

- `id`: stable local identifier, for example `claim-001`.
- `text`: claim statement.
- `source_label`: one of:
  - `user_provided`
  - `extracted`
  - `assumed`
  - `needs_evidence`
- `confidence`: string label such as `low`, `medium`, or `high`.
- `rationale`: short explanation of why the claim exists.

Rules:

- Claim IDs are local to a single result.
- `needs_evidence` is used when a statement is important but not yet supported.
- `assumed` is used only when the pipeline makes an explicit placeholder
  assumption.

## 7. Evidence Ledger Contract

`EvidenceEntry` records support or gaps for claims.

Fields:

- `id`: stable local identifier, for example `evidence-001`.
- `claim_id`: claim identifier the entry refers to.
- `evidence_type`: `provided` or `missing`.
- `summary`: evidence summary or missing evidence description.
- `reference_label`: string or null. User-provided source label when available.
- `notes`: extra caveats.

Rules:

- Missing evidence must be represented explicitly with `evidence_type="missing"`.
- If no user evidence exists for a claim, the ledger must include a missing entry.
- No fake citations, URLs, papers, or source names may be generated.

## 8. Reviewer Critique Contract

`ReviewerCritique` captures local deterministic review feedback.

Fields:

- `id`: stable local identifier.
- `reviewer_role`: role name, for example `skeptic` or `operator`.
- `claim_id`: related claim identifier or null for whole-report critique.
- `finding`: critique text.
- `severity`: `low`, `medium`, or `high`.
- `suggested_action`: concrete next action.

Rules:

- Critiques should focus on uncertainty, evidence gaps, experimentability, or scope.
- Critiques do not require agent execution in v0.1.

## 9. Experiment Plan Contract

`ExperimentPlan` describes a minimum viable experiment.

Fields:

- `id`: stable local identifier.
- `title`: short experiment title.
- `hypothesis_claim_ids`: tuple of claim IDs.
- `method`: concise test method.
- `success_metric`: observable success measure.
- `minimum_sample`: smallest reasonable sample or trial count.
- `risk`: known limitation or risk.

Rules:

- Experiments should be small and falsifiable.
- Experiments should not require web search in v0.1.

## 10. Recommendation Contract

`Recommendation` summarizes what to do next.

Fields:

- `decision`: short decision label.
- `summary`: human-readable recommendation.
- `next_step`: the immediate next action.
- `rationale`: why this recommendation follows from the current evidence state.

## 11. Markdown Report Contract

`MarkdownReport` is the report artifact returned by the pipeline.

Fields:

- `title`: report title.
- `markdown`: complete Markdown body.
- `artifact_type`: fixed as `markdown`.

Rules:

- The report must disclose that no web search or external evidence collection was
  performed.
- The report must not include fake citations.
- The report should include sections for claims, evidence ledger, critiques,
  experiments, and recommendation.

## 12. App Boundary

The v0.1 app lives under `apps/research-council/`.

This pass must not modify:

- `adapters/discord/`
- `adapters/web/`
- `memory/tasks/`
- `orchestrator/discord-intake/`
- root `README.md`
- root `AGENTS.md`
- `docs/architecture.md`

## 13. Governance Metadata Boundary

README governance guidance may define operational metadata for domain profile
support status, benchmark coverage, acknowledgement, audit retention, or
compatibility sunset handling.

That guidance does not change this v0.1 input/output contract unless the schema
dataclasses and this contract are explicitly updated in the same scoped change.
Governance records are operational metadata outside `ResearchCouncilInput`,
`ResearchCouncilResult`, benchmark snapshots, history entries, benchmark hashes,
and Markdown report output.

Rules:

- Governance metadata must remain deterministic, bounded, and reference-based.
- Governance metadata must not require network calls, LLM calls, databases, API
  services, UI behavior, async workers, or new orchestration systems.
- Governance metadata must not store raw benchmark, golden, mutation, scenario,
  or user-provided input text.
- Governance metadata must not mutate benchmark snapshots, history entries,
  benchmark hashes, formatter output, or the first-line governance summary.
