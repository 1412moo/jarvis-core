# Sample Hermes Review Checklist

This checklist is for reviewing Codex output before asking for fixes or a
commit. It is not a replacement for human approval.

## Scope

- Did Codex address the requested goal?
- Did Codex avoid unrelated files?
- Did Codex preserve explicitly excluded files such as `jarvis.bat`?
- Did Codex avoid broad refactors unless requested?
- Did Codex keep Research Council, Daily AI Radar, adapters, report schemas,
  snapshots, history, hashes, and tests unchanged unless scoped?

## Safety

- No autonomous code modification outside the approved scope.
- No destructive file operations without explicit approval.
- No auto commit.
- No auto push.
- No secrets, tokens, credentials, or sensitive data stored.
- No broad repo, filesystem, network, MCP, A2A, or tool permission expansion.
- No Daily AI Radar recommendation converted directly into implementation.

## Determinism

- Does the result avoid current clock dependence unless explicitly provided?
- Does the result avoid network, web, LLM/API, scheduler, crawler, and DB
  behavior unless approved?
- Are generated outputs deterministic for the same input?
- Are tie-breakers and ordering stable?

## Tests

- Were requested validation commands run?
- Are test outputs reported with command names?
- Were skipped tests explained?
- Did Codex avoid claiming success without validation evidence?
- Are smoke/golden or contract checks still aligned with the scope?

## Git Hygiene

- Was `git status --short` checked?
- Is `.git/index.lock` absent?
- Are only approved files changed or staged?
- Is `jarvis.bat` still untracked and unstaged if it started that way?
- Was `git diff --cached --stat` checked before commit?
- Was `git diff --cached --check` checked before commit?

## User Approval

- Did the user approve implementation?
- Did the user separately approve commit?
- Did the user separately approve push, if any?
- Are high-risk, destructive, permission, security, or self-improvement actions
  still waiting for explicit approval?

## Commit Readiness

- Scope is complete.
- Required validation passed or skipped with accepted reason.
- Risks are documented.
- Excluded files are untouched.
- Staged diff contains only approved files.
- Commit message is approved.
- Push is not included unless separately requested.
