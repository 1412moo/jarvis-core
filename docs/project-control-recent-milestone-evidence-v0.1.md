# Project Control Recent Milestone Evidence v0.1

Status: implemented and locally verified on 2026-07-23.

Implementation commits:

- vertical slice: `2f04d4f`
- recommendation-contract test follow-up: `e25ba92`

## User value

The owner can see the five most recent local Jarvis-Core commits, their changed
file names, and whether the first item still matches the live HEAD directly in
Project Control. This reduces repeated requests for a recent-work summary while
keeping commit messages explicitly separate from validation or approval.

## Contract

`recent_milestone_evidence.py` defines frozen, transport-neutral evidence and
commit records. The core accepts caller-supplied text only and performs no Git,
filesystem, route, persistence, or network operation.

The contract is bounded to:

- one fixed `jarvis-core` repository identity;
- five commits;
- 256KB of raw log text;
- 160 characters per normalized subject;
- 20 visible file names and 300 characters per name;
- full lowercase Git hashes and repository-relative display paths.

Malformed separators, hashes, control characters, duplicate commits or paths,
absolute/traversing paths, oversized input, and excessive commit counts fail
closed. Stable JSON serialization does not mutate the input object.

## Local data collection

Jarvis Console runs one allowlisted read-only command equivalent to:

```text
git log -n 5 --format=<record-separator>%H<field-separator>%s --name-only
```

It uses `GIT_OPTIONAL_LOCKS=0`, a fixed trusted repository root, no shell
expansion, a five-second timeout, and the existing `/api/overview` response.
Project Control advances to `project_control.v0.1E`; no route is added.

The payload reports `head_matches_latest_commit`, marks the exact HEAD item,
shows bounded changed-file metadata, and raises Project Control Attention if the
log does not match the observed HEAD or a recent commit contains protected
`jarvis.bat`.

## Read-only UI

The existing single-repo owner card renders the evidence above Owner Decision:

- `HEAD verified` or `HEAD changed`;
- five recent commit subjects and short hashes;
- the exact bounded changed-file count and visible names;
- an explicit statement that the data is not completion, validation, approval,
  or execution authority.

The section contains no action button. It creates no commit, task, approval,
prompt, runtime state, cross-app call, or external request.

## Verification

- Deterministic tests cover immutability, stable serialization, HEAD match and
  mismatch, file truncation, protected-path visibility, malformed input,
  traversal, duplicate commits, raw-size bounds, and commit-count bounds.
- Jarvis Console self-test and full smoke tests passed.
- Hermes Manager, Research Council, and Daily AI Radar smoke tests passed
  sequentially with isolated local temporary directories.
- Browser QA showed five commit cards, one `HEAD verified` badge, no section
  action buttons, the implementation commit `2f04d4f` with five changed files,
  and zero browser warnings or errors.
- Temporary servers, logs, fixtures, and listeners were removed.

## Safety boundary

This evidence is observation only. It does not prove tests passed, grant human
approval, modify a repository, stage or commit files, push, create a PR, enable
Memory Save, call an external API/LLM, connect a second repository, or add
persistence.
