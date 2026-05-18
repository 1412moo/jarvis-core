# Research Council Report: Sample

## Executive Summary

This is an early research brief based only on structured Research Council data. The renderer does not add web research, external evidence, or citations.

- Claims reviewed: 3
- Evidence ledger: 1 provided; 2 missing; 3 total
- Reviewer critiques: 2
- Minimum viable experiments: 1
- Recommendation decision: `continue_with_minimum_experiment`
- Recommendation summary: Continue only through a small local experiment before adding integrations.

Warnings:
- No web search, network calls, LLM calls, or external evidence collection were performed.
- Missing evidence is represented explicitly in the evidence ledger.

## Input Idea and Goal

- Raw idea: A lightweight Research Council module could make vague product and research ideas easier to validate.
- Goal: Check whether Research Council has a useful v0.1 shape before connecting it to other Jarvis systems.
- Input summary: Evaluate whether the idea can support the goal: Check whether Research Council has a useful v0.1 shape.
- Context: This sample represents a local deterministic foundation pass, not a final scientific review.
- Constraints:
  - Python standard library only
  - No web search
  - No fake citations
- User-provided evidence:
  - The user requested the first schema and contract pass.

## Structured Claims

### claim-001

- Claim: The user's raw idea and goal define a research direction worth structuring.
- Source label: `user_provided`
- Confidence: `medium`
- Rationale: The user supplied both an idea and a goal.

### claim-002

- Claim: The idea can be evaluated through a small local experiment before broader Jarvis integration.
- Source label: `extracted`
- Confidence: `low`
- Rationale: The requested workflow can be checked through a local demo and report review.

### claim-003

- Claim: There is enough evidence to justify expanding Research Council beyond an isolated app module.
- Source label: `needs_evidence`
- Confidence: `low`
- Rationale: No adoption, usefulness, or quality evidence has been collected in this foundation pass.

## Evidence Ledger

### evidence-001

- Claim: `claim-001`
- Evidence status: `provided`
- Evidence summary: The user requested the first schema and contract pass.
- Reference label: user_input
- Notes: This is user-provided context, not externally verified evidence.

### evidence-002

- Claim: `claim-002`
- Evidence status: `missing`
- Missing evidence: No real local trial has been run against a user idea yet.
- Reference label: Not applicable; this entry describes missing evidence.
- Notes: A manual smoke experiment can fill this gap.

### evidence-003

- Claim: `claim-003`
- Evidence status: `missing`
- Missing evidence: No external validation, adoption signal, or report quality review exists yet.
- Reference label: Not applicable; this entry describes missing evidence.
- Notes: Do not treat this claim as supported until evidence is collected.

## Reviewer Critiques

### critique-001

- Reviewer role: skeptic
- Scope: `claim-003`
- Severity: `high`
- Finding: The expansion claim is unsupported because there is no usefulness or adoption evidence yet.
- Suggested action: Keep Research Council isolated until a local trial produces useful output.

### critique-002

- Reviewer role: operator
- Scope: whole brief
- Severity: `medium`
- Finding: The workflow should stay deterministic and local while the contract is stabilizing.
- Suggested action: Use smoke tests and stdout Markdown before adding persistence or adapters.

## Minimum Viable Experiments

### experiment-001: One-idea local report trial

- Hypothesis claims: `claim-001`, `claim-002`
- Method: Run the local demo with one real user idea, then inspect whether the report identifies claims, gaps, critiques, and next actions.
- Success metric: A human reviewer can name at least one useful next action from the Markdown report.
- Minimum sample: One real idea and one manual review session.
- Risk: A single trial may validate formatting without proving repeated usefulness.

## Recommendation

- Decision: `continue_with_minimum_experiment`
- Summary: Continue only through a small local experiment before adding integrations.
- Rationale: The current result exposes clear evidence gaps and can be validated without web search or app integrations.
- Immediate next step: Run one manual Research Council pass with a real idea and inspect whether the report produces useful next actions.

## Unknowns / Evidence Gaps

- Missing evidence entries:
  - `evidence-002` for `claim-002`: No real local trial has been run against a user idea yet.
  - `evidence-003` for `claim-003`: No external validation, adoption signal, or report quality review exists yet.
- Claims marked `needs_evidence`:
  - `claim-003`: There is enough evidence to justify expanding Research Council beyond an isolated app module.

## Next Steps

- Do next: Run one manual Research Council pass with a real idea and inspect whether the report produces useful next actions.
- Keep Research Council isolated until a local trial produces useful output.
- Use smoke tests and stdout Markdown before adding persistence or adapters.
- Run `experiment-001`: One-idea local report trial
