# Sample Research Council Input

This example is documentation only. The demo script builds an equivalent
`ResearchCouncilInput` object directly in Python.

```text
raw_idea:
A swallowable biodegradable capsule could screen the colon for early signs of
colorectal cancer, collect images or sensor data during transit, and then safely
break down after discharge through wastewater.

goal:
Decide whether the capsule colon screening concept has enough grounded promise
for only non-clinical minimum viable experiments.

context:
This is a deterministic v0.1 Research Council pass. It should identify claims,
evidence gaps, reviewer critiques, minimum experiments, and a recommendation
without doing web search or creating citations.

constraints:
- Python standard library only.
- No web search, network calls, LLM calls, or fake citations.
- Keep missing evidence explicit.
- Do not recommend human testing from this local pass.

provided_evidence:
- The user supplied the concept of a swallowable capsule for colon screening.
- The user supplied the desired biodegradable wastewater-discharge behavior.
```
