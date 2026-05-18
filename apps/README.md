# Jarvis Apps

`apps/` contains isolated Jarvis app modules.

Jarvis Core remains the orchestration, contract, and records layer. App modules may
define domain-specific workflows, schemas, demos, and tests, but they should not
change global Jarvis behavior unless a later integration task explicitly expands
that boundary.

## Current Apps

- `research-council/`: first practical app module for turning a raw idea and goal
  into claims, an evidence ledger, critiques, experiments, and a Markdown research
  report.

## Boundary Rules

- Keep app code under its own app folder.
- Do not import app code from Discord, dashboard, task memory, or global report
  flows during the first app pass.
- Prefer Python standard library for early MVPs.
- Generated app outputs should be printed to stdout by default. Persisted output
  paths can be added later behind explicit CLI flags and ignore rules.
