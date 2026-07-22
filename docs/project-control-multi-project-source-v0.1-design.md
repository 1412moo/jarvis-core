# Project Control Trusted Multi-project Source v0.1 Design

Last updated: 2026-07-22

Status: dormant design/internal foundation. It is retained for reference but is
not on the current Project Control integration roadmap. No second repository,
route, persistence, action, or cross-app connection is implemented.

Implementation note: Project Control v0.1C now implements and locally verifies
the in-memory registry normalizer and bounded blocking decision described in
section 10. It remains route-free and filesystem-free; the design's live
multi-repository boundary is still unimplemented.

Current direction: Project Control stays a single-repository Owner Dashboard
for Jarvis-Core and treats Jarvis Console, Hermes Manager, Memory / Skills,
Research Council, and Daily AI Radar as internal workstreams/apps/capabilities.
Do not register a real second repository or connect this foundation to path
input, HTTP routes, UI, or persistence.

## 1. Goal

Define how Jarvis Console may eventually show multiple local project cards
without accepting filesystem authority from a browser request or silently
discovering repositories.

The owner should be able to compare each project's goal, current milestone,
next user-visible result, live Git observation, known protected paths, and
validation guidance. The panel remains an observation surface, not an approval
or execution surface.

## 2. v0.1B Decision

Use two server-owned layers:

1. A bounded tracked project-card registry contains portable display metadata
   and a `trusted_root_key`; it does not contain request-supplied paths.
2. A server-owned trusted-root map resolves each key to one canonical local
   repository root. The browser cannot add or replace mappings.

For the first implementation unit, the trusted-root map contains only
`jarvis_core -> REPO_ROOT`. Adding another key is a separately reviewed code or
operator-configuration change. No directory scan or automatic repo discovery is
allowed.

## 3. Proposed Registry Contract

The normalized registry uses this shape:

```json
{
  "registry_type": "jarvis_project_control",
  "version": "0.1B",
  "projects": [
    {
      "project_id": "jarvis-core",
      "display_name": "Jarvis-Core",
      "trusted_root_key": "jarvis_core",
      "master_plan_path": "docs/master-plan.md",
      "expected_branch": "main",
      "protected_paths": ["jarvis.bat"],
      "expected_untracked": ["jarvis.bat"],
      "validation_command_ids": ["git_status_short", "git_diff_check"]
    }
  ]
}
```

Limits and normalization:

- registry file: fixed app-owned path, regular UTF-8 file, at most 64KB;
- projects: 1 to 16 entries, stable registry order;
- IDs and trusted-root keys: lowercase ASCII letters, digits, `_`, and `-`, at
  most 64 characters, unique after normalization;
- display name: 1 to 120 Unicode characters, no control characters;
- master-plan and protected/untracked paths: normalized repo-relative POSIX
  paths only, no drive prefix, absolute path, `..`, empty component, NUL,
  Windows alternate-stream/wildcard characters, trailing dot/space, or reserved
  device name;
- list fields: bounded, duplicate-free, and order-preserving;
- unknown fields, unknown root keys, and unknown validation command IDs: reject;
- JSON duplicate object keys: reject before normalization.

Validation commands are display metadata resolved from a fixed server-owned ID
map. Project Control never executes them.

## 4. Filesystem Authority

The registry declares intent but grants no filesystem authority. Authority comes
only from the trusted-root map held by the server process.

For every project:

1. Resolve the trusted root with `strict=True`.
2. Require a regular Git worktree directory selected by the server mapping.
3. Resolve `master_plan_path` beneath that root.
4. Reject symlinks and any resolved path outside the canonical trusted root.
5. Read only the bounded master-plan fields already used by Project Control.
6. Run only fixed read-only Git commands with shell expansion disabled and
   `GIT_OPTIONAL_LOCKS=0`.

Neither an HTTP query/body nor the tracked registry may provide an absolute path
that is opened directly.

## 5. Declared Direction vs Live Observation

Every card keeps two groups visibly separate.

Source precedence is intentionally non-overwriting:

- the tracked registry defines structural safety expectations such as the
  trusted-root key, expected branch, protected paths, and command IDs;
- the master plan defines owner direction and its recorded branch/implementation
  checkpoint;
- fixed read-only Git commands provide current observation facts.

No layer rewrites another. A registry expected branch, master-plan branch, or
live Git branch mismatch becomes a bounded `attention` reason. It is not
silently reconciled and does not update either tracked source.

Declared direction:

- project display name;
- current goal and workstream;
- current milestone;
- recommended next step;
- next user-visible milestone;
- expected branch;
- known protected and expected-untracked paths;
- validation command labels.

Live observation:

- repository availability;
- observed branch and short HEAD;
- working-tree status;
- protected-path changes;
- unexpected untracked paths;
- whether the recorded verified implementation HEAD is recognizable locally.

Observed Git metadata is evidence, not approval. The card must never use status
labels such as `approved`, `safe to commit`, or `completed` based on observation
alone.

## 6. Display Status

Allowed top-level card states:

- `observed`: the trusted repo was read and no defined attention condition was
  found; this does not mean approved or clean;
- `attention`: the repo was read but branch, protected-path, unexpected
  untracked, or recorded-HEAD checks need owner attention;
- `unavailable`: the trusted root, Git metadata, or required master-plan fields
  could not be read safely.

The UI shows bounded attention reasons. It does not offer repair, approve,
execute, stage, commit, push, or PR actions.

## 7. Fail-closed Behavior

- Invalid registry envelope, duplicate project IDs, or unknown trusted-root key:
  reject the Project Control registry and show no inferred projects.
- One missing/unreadable repo: return its declared identity as `unavailable`
  without scanning parent directories or guessing another path.
- Branch mismatch: `attention`.
- Protected path tracked change or unexpected untracked protected path:
  `attention`.
- Expected untracked path missing: bounded attention reason, not automatic
  deletion or recreation.
- Unknown/stale verified implementation HEAD: `attention`; never rewrite the
  master plan automatically.
- Failure in one project must not grant more authority to another project.
- Registry or observation data is never persisted by the endpoint.

## 8. Endpoint and UI Boundary

The later read-only integration should continue using `GET /api/overview` and
the list-shaped `project_control` payload. No new action route is needed.

Out of scope:

- browser-supplied repo paths or project registration;
- automatic repository discovery under `C:\work` or another parent directory;
- database, runtime registry mutation, saved project state, or background poll;
- automatic Hermes/Codex/ChatGPT calls;
- task, approval, prompt, session, commit, push, or PR creation;
- external API, network, LLM, credential, or secret handling;
- Memory save endpoint, UI Save/Confirm, Voice Inbox save, or saved candidates.

## 9. Deterministic Test Obligations

The future internal implementation must cover:

- deterministic normalization and stable multi-project order;
- duplicate JSON key and unknown-field rejection;
- duplicate project/root/path/command rejection;
- unknown trusted-root key and validation command ID rejection;
- absolute, drive-prefixed, traversal, NUL, and malformed relative paths;
- root/master-plan symlink and resolved-outside-root rejection;
- missing repo and missing/duplicate/oversized master-plan fields;
- branch mismatch and unavailable Git metadata;
- protected-path and expected/untracked classification;
- no absolute root, file content, approval digest, secret, or command output in
  the presentation payload beyond bounded Git status metadata;
- source checks proving no write, persistence, subprocess shell, external call,
  prompt rendering, approval creation, or action route was added.

## 10. First Implementation Unit — Completed

Project Control v0.1C adds only an internal/tests-only registry normalizer and
deterministic card-source decision model.

It does:

- normalize an in-memory mapping;
- accept a server-supplied trusted-root-key set as data, without opening repos;
- return declared project records and blocking reasons;
- test one- and two-project fixtures.

It still must not:

- read a second live repository;
- connect the normalizer to HTTP or UI;
- create a runtime config or persistence file;
- accept a path from a browser;
- execute validation commands.

After v0.1C review, the owner chose to keep Project Control single-repository.
This primitive remains dormant. Any future multi-repository reactivation would
require a separate explicit product-direction decision before repository
selection or read-only integration design begins.
