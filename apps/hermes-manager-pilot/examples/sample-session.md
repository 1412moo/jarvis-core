# Sample Hermes Manager Pilot Session

This is a sample only. It is not a record of actual command execution, test
results, commits, or production behavior.

## Scenario

The user wants to improve Research Council while keeping Jarvis-Core governance
stable.

## 1. User Goal

```text
Improve Research Council Korean refinement coverage. Keep the change
deterministic, metadata-first, and covered by smoke/golden validation.
Do not touch jarvis.bat.
```

## 2. Hermes Creates Codex Implementation Prompt

Hermes output category: `PROMPT_FOR_CODEX`

Hermes prepares a bounded prompt:

- Repo: `C:\work\jarvis-core`
- Expected HEAD: sample checkpoint only
- Target area: `apps/research-council/`
- Excluded file: `jarvis.bat`
- Non-goals: no Discord, no DB, no web/API calls, no auto commit
- Validation:
  - `python -B apps\research-council\run_smoke_tests.py`
  - `python -B apps\research-council\run_golden_cases.py`

The user reviews or edits the prompt before Codex receives it.

## 3. Codex Reports Implementation Result

Sample Codex result summary:

- Changed files: sample list only.
- Tests run: smoke and golden commands are claimed in this sample and still
  require review evidence before being treated as accepted.
- Risks: Korean wording coverage may still need review.
- Commit: not created.

Hermes does not treat this as final truth without review evidence.

## 4. Hermes Creates Review Prompt

Hermes output category: `REVIEW_REQUEST`

Hermes asks Codex to review:

- Scope fit.
- Determinism.
- Metadata-only governance.
- Missing tests.
- Raw input leakage.
- Git hygiene.
- Excluded file protection.

## 5. Codex Reports Review Result

Sample review result summary:

- Findings: none in this sample.
- Residual risk: sample wording still needs human acceptance.
- Tests: smoke/golden reported in the sample, not independently verified by
  Hermes.

Hermes summarizes the review for the user and waits.

## 6. Hermes Creates Commit Prompt

Hermes output category: `COMMIT_REQUEST`

This happens only after the user explicitly asks for a commit.

Commit prompt includes:

- Check `git status --short`.
- Confirm `.git/index.lock` is absent.
- Confirm `jarvis.bat` is untracked and not staged.
- Stage only approved Research Council files.
- Run required validation.
- Check `git diff --cached --stat`.
- Check `git diff --cached --check`.
- Commit with the approved message.

## 7. Codex Reports Commit Result

Sample Codex result summary:

- Commit hash: sample placeholder.
- Final working tree: sample placeholder.
- Excluded file: `jarvis.bat` remained untracked in this sample.

## 8. Hermes Creates Checkpoint Summary

Hermes output category: `STATUS_SUMMARY`

Sample checkpoint:

- Goal: Research Council Korean refinement coverage.
- State: commit reported in sample, not independently verified by Hermes.
- Validation: smoke/golden reported in sample.
- Exclusions: `jarvis.bat` protected.
- Next action: wait for user direction.

This sample does not authorize future commits, pushes, or implementation work.
