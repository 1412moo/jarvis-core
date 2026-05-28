# Research Council Report

## Executive Summary

This local-only brief uses the supplied input and evidence ledger. It does not add web research, external evidence, or citations.

- Claims reviewed: 9
- Evidence ledger: 3 provided; 8 missing; 11 total
- Reviewer critiques: 4
- Minimum viable experiments: 4
- Recommendation decision: `pause_broad_use_resolve_safety_blocker`
- Recommendation summary: Primary blocker: safety regulatory evidence for `claim-005`. Treat the submitted description as concept input, not proof of feasibility, safety, adoption, environmental performance, or market demand.

Warnings:
- No web search, network calls, LLM calls, or external evidence collection were performed.
- No citations are generated; user-provided evidence is local input only.
- Missing evidence is represented explicitly in the evidence ledger.
- At least one claim has explicit missing evidence; do not treat the report as validated research.

## Input Idea and Goal

- Raw idea: A swallowable biodegradable capsule could screen the colon for early signs of colorectal cancer, collect images or sensor data during transit, and then safely break down after discharge through wastewater.
- Goal: Decide whether the capsule colon screening concept has enough grounded promise for only non-clinical minimum viable experiments.
- Input summary: Evaluate whether the idea can support the goal: Decide whether the capsule colon screening concept has enough grounded promise for only non-clinical minimum viable experiments.
- Context: This is a deterministic v0.1 Research Council pass. It should identify claims, evidence gaps, reviewer critiques, minimum experiments, and a recommendation without doing web search or creating citations.
- Constraints:
  - Python standard library only.
  - No web search, network calls, LLM calls, or fake citations.
  - Keep missing evidence explicit.
  - Do not recommend human testing from this local pass.
- User-provided evidence:
  - The user supplied the concept of a swallowable capsule for colon screening.
  - The user supplied the desired biodegradable wastewater-discharge behavior.

## Structured Claims

- `claim-001` [`user_provided`, `high`]: The submitted idea proposes: A swallowable biodegradable capsule could screen the colon for early signs of colorectal cancer, collect images or sensor data during transit, and then safely break down after dis...
  Rationale: This restates the user's local input and goal; it does not validate the concept itself: Decide whether the capsule colon screening concept has enough grounded promise for only non-clinical minimum viable experiments.
- `claim-002` [`extracted`, `low`]: An ingestible capsule-style colon inspection device is technically plausible as a product concept, but feasibility depends on miniaturized sensing, power, data capture, safe transit, and reliable examination quality.
  Rationale: The raw idea gives a product direction, but does not provide engineering tests, materials data, prototypes, or performance results.
- `claim-003` [`assumed`, `low`]: The concept targets a plausible user need around less burdensome colorectal inspection or screening, especially if it reduces discomfort, logistics, or avoidance compared with current care pathways.
  Rationale: User need is inferred from the idea framing; no interviews, usage data, or demand evidence were supplied.
- `claim-004` [`needs_evidence`, `low`]: Novelty and prior-art position are unresolved; the idea needs comparison against capsule-based gastrointestinal inspection, colorectal screening workflows, biodegradable device materials, and disposal approaches.
  Rationale: This local pass does not perform web search, patent search, market research, or citation gathering.
- `claim-005` [`extracted`, `low`]: Because the product would be ingested and used for colon examination, it likely requires medical-device safety, biocompatibility, sanitation, data-quality, clinical, and regulatory validation before human use.
  Rationale: The local input is enough to flag possible safety review, but not enough to establish compliance requirements or approval paths.
- `claim-006` [`extracted`, `low`]: Implementation would need to specify inspection modality, capsule retention and transit behavior, data retrieval, biocompatible materials, manufacturing, and what happens after wastewater discharge.
  Rationale: The implementation components are derived from the idea category, while the actual design details remain unspecified.
- `claim-007` [`needs_evidence`, `low`]: The environmental claim depends on measured degradation behavior after discharge, including breakdown timing, byproducts, wastewater compatibility, and whether the structure avoids shifting risk into sewage treatment systems.
  Rationale: The raw idea states an eco-friendly degradation outcome, but provides no material test, lifecycle analysis, or wastewater evidence.
- `claim-008` [`assumed`, `low`]: The plausible market includes colorectal screening stakeholders, but buyer, payer, clinician, institution, and patient adoption are unproven.
  Rationale: Market demand is not established by the local idea text or by any supplied evidence.
- `claim-009` [`extracted`, `medium`]: The idea is experimentable through non-clinical first steps such as capsule-size mockups, bench material degradation tests, data-capture prototypes, workflow interviews, and simulated disposal checks before any human testing.
  Rationale: Minimum experiments can be proposed from the idea structure without collecting external evidence.

## Evidence Ledger

Provided local input:
- `evidence-001` -> `claim-001`: The user supplied the concept and goal being evaluated: idea=A swallowable biodegradable capsule could screen the colon for early signs of colorectal cancer, collect images or sensor data during transit, and then safely break down after discharge through wastewater.; goal=Decide whether the capsule colon screening concept has enough grounded promise for only non-clinical minimum viable experiments.
- `evidence-010` -> `claim-001`: User-provided local support: The user supplied the concept of a swallowable capsule for colon screening.
- `evidence-011` -> `claim-006`: User-provided local support: The user supplied the desired biodegradable wastewater-discharge behavior.

Missing evidence entries:
- `evidence-002` [technical] for `claim-002`: Missing technical evidence: Show that a swallowable capsule-sized mockup can capture useful colon observations during transit, retain/recover data, and tolerate occlusion, orientation changes, power limits, and safe passage constraints.
- `evidence-003` [user_adoption] for `claim-003`: Assumption needs user adoption evidence: Check whether patients, clinicians, and screening program operators would trust and use the capsule pathway compared with colonoscopy, stool tests, and other existing screening routes.
- `evidence-004` [prior_art] for `claim-004`: Needs prior art evidence before support: Map the concept against capsule endoscopy, colorectal screening workflows, biodegradable ingestible devices, retrieval/disposal approaches, and any user-supplied offline prior-art references.
- `evidence-005` [safety_regulatory] for `claim-005`: Missing safety regulatory evidence: Define ingestion, retention, obstruction, biocompatibility, sanitation, diagnostic-quality, clinical oversight, and medical-device approval risks before any human-use claim.
- `evidence-006` [safety_regulatory] for `claim-006`: Missing safety regulatory evidence: Define ingestion, retention, obstruction, biocompatibility, sanitation, diagnostic-quality, clinical oversight, and medical-device approval risks before any human-use claim.
- `evidence-007` [environmental] for `claim-007`: Needs environmental evidence before support: Measure degradation time, byproducts, micro-fragment risk, wastewater treatment compatibility, and whether the capsule remains safe after patient discharge.
- `evidence-008` [market] for `claim-008`: Assumption needs market evidence: Identify who pays for the screening pathway, who buys or prescribes it, reimbursement assumptions, procurement barriers, and adoption triggers.
- `evidence-009` [environmental] for `claim-009`: Missing environmental evidence: Measure degradation time, byproducts, micro-fragment risk, wastewater treatment compatibility, and whether the capsule remains safe after patient discharge.

## Reviewer Critiques

- `critique-001` technical (`high`, scope `claim-002`): The technical blocker is the capsule itself: `claim-002` (An ingestible capsule-style colon inspection device is technically plausible as a product concept, but feasibility...) must show that a swallowable body can observe enough of the colon while moving, capture or retain usable data, and still pass safely despite orientation, occlusion, power, and retrieval limits. Evidence needed (technical): Show that a swallowable capsule-sized mockup can capture useful colon observations during transit, retain/recover data, and tolerate occlusion, orientation changes, power limits, and safe passage constraints.
  Suggested action: Build a non-ingestible capsule-size bench mockup and test image or sensor capture through a simulated curved wet channel before considering any clinical path.
- `critique-002` market (`high`, scope `claim-003`): Adoption is unproven for `claim-003` (The concept targets a plausible user need around less burdensome colorectal inspection or screening, especially if it...). A less burdensome capsule story is appealing, but it does not show that patients would trust ingestion, clinicians would trust diagnostic quality, or payers and screening programs would prefer this pathway over established alternatives. Evidence needed (user_adoption): Check whether patients, clinicians, and screening program operators would trust and use the capsule pathway compared with colonoscopy, stool tests, and other existing screening routes.
  Suggested action: Run separate non-clinical interviews with one patient-like participant and one care-pathway operator to test trust, refusal points, and the decision this concept would change.
- `critique-003` safety_regulatory (`high`, scope `claim-005`): The safety boundary is the highest-impact blocker for `claim-005` (Because the product would be ingested and used for colon examination, it likely requires medical-device safety,...). The concept involves ingestion, possible retention or obstruction, biocompatibility, diagnostic false reassurance, patient discharge, and degradation byproducts entering wastewater. Evidence needed (safety_regulatory): Define ingestion, retention, obstruction, biocompatibility, sanitation, diagnostic-quality, clinical oversight, and medical-device approval risks before any human-use claim.
  Suggested action: Create a non-clinical safety table that lists hazards, stop conditions, required expert review, and what evidence is mandatory before any human-use experiment.
- `critique-004` red_team (`high`, scope `claim-004`): The easiest harmful overclaim for `claim-004` (Novelty and prior-art position are unresolved; the idea needs comparison against capsule-based gastrointestinal...) is that a biodegradable capsule can be treated as a screening substitute before it has evidence on coverage, missed lesions, retention, degradation residue, and fit with existing care. The submitted description defines a concept; it does not support those outcome claims. Evidence needed (prior_art): Map the concept against capsule endoscopy, colorectal screening workflows, biodegradable ingestible devices, retrieval/disposal approaches, and any user-supplied offline prior-art references.
  Suggested action: Rewrite the concept notes so every screening, safety, and environmental statement is labeled as user-provided, missing evidence, or a non-clinical experiment target.

## Minimum Viable Experiments

### experiment-001: Non-clinical capsule safety boundary table

- Hypothesis claims: `claim-005`
- Method: Hypothesis: The capsule concept can define safety blockers and stop conditions clearly enough to decide which non-clinical tests are permissible next. Method: Create a table for ingestion, retention, obstruction, biocompatibility, sanitation, diagnostic false reassurance, data quality, discharge, and degradation-byproduct risks. For each row, record the minimum evidence required before moving beyond bench work. Respect these constraints: Python standard library only.; No web search, network calls, LLM calls, or fake citations.; Keep missing evidence explicit.; Do not.... Estimated time: 45-60 minutes. Estimated cost level: free. Stop criteria: Stop if any ingestion, retention, diagnostic, or degradation risk lacks a bench-only test boundary. Decision impact: Decide whether the idea is safe to explore through non-clinical bench tests only, or whether it should pause until expert safety input is available.
- Success metric: Metric: Every human-use or clinical-quality claim is either blocked, narrowed to bench-only language, or paired with a named expert-review requirement.
- Minimum sample: One structured hazard table covering the current capsule concept.
- Risk: A table is not medical, regulatory, or toxicology clearance; it only prevents premature scope expansion.

### experiment-002: Bench capsule sensing and transit mockup

- Hypothesis claims: `claim-002`
- Method: Hypothesis: A capsule-sized non-ingestible mockup can collect interpretable observations while moving through a curved, wet, colon-like channel. Method: Use an inert capsule-size shell or fixture in a simulated channel. Vary orientation, fluid, occlusion, and speed; record whether images or sensor readings remain readable and whether data capture assumptions are plausible. Do not use biological samples or people. Estimated time: 2-4 hours. Estimated cost level: low. Stop criteria: Stop if the mockup cannot produce interpretable readings under basic wet-channel conditions. Decision impact: Proceed to more detailed engineering only if bench sensing survives the simplest transit conditions.
- Success metric: Metric: At least one sensing mode produces readable observations across the simulated path and records the failure cases that would make the concept impractical.
- Minimum sample: Three passes through one bench channel with different orientation or occlusion conditions.
- Risk: A bench channel cannot prove clinical accuracy, safe ingestion, or full colon coverage.

### experiment-003: Wastewater degradation screen

- Hypothesis claims: `claim-007`
- Method: Hypothesis: Candidate capsule materials can break down under simulated discharge conditions without obvious persistent fragments or residue. Method: Expose material coupons or a nonfunctional shell to simulated wastewater conditions. Record visible breakdown, mass change if measurable, fragments, residue, and timing. Treat this as a screen, not environmental proof. Estimated time: 1-7 days. Estimated cost level: low. Stop criteria: Stop if the material remains intact, leaves persistent fragments, or creates unknown residue. Decision impact: Decide whether the biodegradable claim deserves more materials work or should be removed from the concept.
- Success metric: Metric: The test produces a timed degradation curve or a clear failure result for at least one candidate material.
- Minimum sample: One candidate material in three small containers or time checkpoints.
- Risk: A simple screen does not establish toxicology, wastewater treatment compatibility, or lifecycle impact.

### experiment-004: Care-pathway adoption check

- Hypothesis claims: `claim-003`
- Method: Hypothesis: The capsule concept changes a real screening decision for at least one stakeholder without relying on unsupported clinical claims. Method: Show the concept as a hypothetical non-clinical storyboard to one patient-like user and one clinician, operator, or payer-like stakeholder. Ask what they would trust, reject, compare against, or need to see before considering it. Keep the goal in frame: Decide whether the capsule colon screening concept has enough grounded promise for only non-clinical minimum viable.... Estimated time: 60-120 minutes. Estimated cost level: free-to-low. Stop criteria: Stop if participants treat the idea as clinically proven or cannot identify a decision it would change. Decision impact: Decide whether adoption uncertainty is worth testing after safety and bench feasibility blockers.
- Success metric: Metric: Each stakeholder names one decision requirement, refusal point, or competing pathway that would determine adoption.
- Minimum sample: Two structured interviews or readouts, separated by stakeholder type.
- Risk: Interview interest is not clinical validation, market proof, or reimbursement evidence.

## Recommendation

- Decision: `pause_broad_use_resolve_safety_blocker`
- Summary: Primary blocker: safety regulatory evidence for `claim-005`. Treat the submitted description as concept input, not proof of feasibility, safety, adoption, environmental performance, or market demand.
- Rationale: Blockers ranked by decision impact: safety_regulatory on claim-005; technical on claim-002; safety_regulatory on claim-006; user_adoption on claim-003. User-provided evidence establishes what the concept says; actual support still requires the missing evidence named in the ledger. High-severity critiques were raised by: market, red_team, safety_regulatory, technical.
- Immediate next step: Run `experiment-001` (Non-clinical capsule safety boundary table) as the primary next experiment.

## Unknowns / Evidence Gaps

- Missing evidence entries by category:
  - technical: `claim-002`. Missing technical evidence: Show that a swallowable capsule-sized mockup can capture useful colon observations during transit, retain/recover data, and tolerate occlusion, orientation changes, power limits, and safe passage constraints.
  - user_adoption: `claim-003`. Assumption needs user adoption evidence: Check whether patients, clinicians, and screening program operators would trust and use the capsule pathway compared with colonoscopy, stool tests, and other existing screening routes.
  - prior_art: `claim-004`. Needs prior art evidence before support: Map the concept against capsule endoscopy, colorectal screening workflows, biodegradable ingestible devices, retrieval/disposal approaches, and any user-supplied offline prior-art references.
  - safety_regulatory: `claim-005`, `claim-006`. Missing safety regulatory evidence: Define ingestion, retention, obstruction, biocompatibility, sanitation, diagnostic-quality, clinical oversight, and medical-device approval risks before any human-use claim.
  - environmental: `claim-007`, `claim-009`. Needs environmental evidence before support: Measure degradation time, byproducts, micro-fragment risk, wastewater treatment compatibility, and whether the capsule remains safe after patient discharge.
  - market: `claim-008`. Assumption needs market evidence: Identify who pays for the screening pathway, who buys or prescribes it, reimbursement assumptions, procurement barriers, and adoption triggers.
- Claims marked `needs_evidence`:
  - `claim-004`: Novelty and prior-art position are unresolved; the idea needs comparison against capsule-based gastrointestinal inspection, colorectal screening workflows, biodegradable device materials, and disposal approaches.
  - `claim-007`: The environmental claim depends on measured degradation behavior after discharge, including breakdown timing, byproducts, wastewater compatibility, and whether the structure avoids shifting risk into sewage treatment systems.

## Next Steps

- Do next: Run `experiment-001` (Non-clinical capsule safety boundary table) as the primary next experiment.
- Use secondary experiments only after the primary blocker result is known.
