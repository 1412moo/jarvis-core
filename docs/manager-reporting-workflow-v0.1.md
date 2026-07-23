# Manager Reporting Workflow v0.1

Status: v0.1A transport-neutral contracts and v0.1B pure existing-evidence
adapters implemented; v0.1C-v0.1D remain inside the approved milestone boundary.

## User value

Codex Worker can report detailed implementation evidence to Hermes Manager
without requiring the Owner to manage each file, test, repair, or local commit.
Hermes derives a short Owner report containing the milestone meaning, user
outcome, risks, next recommendation, and only the decision that actually needs
Owner authority.

## Authority boundary

The Owner approves product direction and a bounded milestone boundary. Hermes
may divide that approved boundary into smaller work packages, review Worker
evidence, and recommend the next package. Codex Worker may implement, validate,
self-review, make minimal safe fixes, synchronize documentation, and create a
validated local commit when the approved package allows it.

Hermes does not edit the repository, invoke Codex, approve its own work, create
a commit, expand scope, or unlock a capability. The current handoff remains
manual and copy-only. Push, PR, external API/LLM, credentials, destructive
actions, automatic execution, background workers, Memory save, UI Save/Confirm,
and Voice Inbox auto-save remain separate Owner gates.

## Source hierarchy

1. `docs/master-plan.md` is the source of truth for the overall goal, current
   milestone, workstream state, and locked capabilities.
2. Worker Report, Review Record, Prompt Queue evaluation, and current Git
   evidence are bounded evidence inputs.
3. Manager Report is a derived view and has no independent authority.
4. A source mismatch fails closed. Hermes does not infer, repair, or overwrite
   a source silently.
5. Worker claims do not prove validation; Hermes rechecks locally where the
   approved QA strategy permits.

## v0.1A contracts

`hermes_manager_pilot.manager_reporting` defines frozen, slotted,
transport-neutral report contracts. It imports no repository, process, browser,
network, persistence, or clipboard integration.

### Worker Report

The detailed Worker contract contains:

- exact work package and milestone references;
- result type and changed files;
- validation result names, status, and bounded evidence;
- the lightest selected QA level, its reason, server-use flag, and cleanup
  result;
- self-review findings;
- optional full commit hash and subject;
- final bounded `git status --short` lines;
- blockers and explicit safety-boundary facts.

A non-blocked Worker Report rejects failed validation, blockers, protected-path
touches, external calls, push/PR, destructive changes, clipboard-as-state,
unexpected repository changes, and failed process cleanup. A blocked report
must contain a reason.

### Manager Report

The Owner-facing derived contract contains:

- current overall goal and milestone ID;
- milestone meaning and user outcome;
- completed work-package summaries and commit hashes;
- current position and status;
- bounded evidence summaries;
- source conflicts and classified risks;
- at most one next bounded recommendation;
- `owner_action` and one decision request when required.

The source of truth is fixed to `master_plan` and `derived_view` is always true.
Source conflicts or blocking risks require `status=blocked`,
`owner_action=decision_required`, and one non-empty decision request. When no
decision is required, the Markdown renderer prints `Owner action: none`.

Both contracts reject unknown fields, duplicate JSON keys and list identities,
unsafe paths, malformed hashes, non-finite JSON, oversized input, and
non-canonical direct instances. Serialization is stable UTF-8 JSON. The pure
Markdown renderers revalidate and do not mutate their input.

## QA and long-running process evidence

The Worker Report records the selected QA level in this order:

1. unit/deterministic tests;
2. CLI output;
3. file inspection;
4. static UI verification;
5. browser QA;
6. manual interactive QA.

Documentation-only work must not start a server or browser. A started server
must have a confirmed cleanup result before a non-blocked report is valid.
Foreground indefinite servers are forbidden. Interactive QA uses a bounded
timeout and verifies process and port cleanup.

The 2026-07-23 foreground web-server incident is the motivating operating case:
the app code was not the defect; the validation process was started with no safe
completion strategy. The process was terminated, ports and Git state were
verified, and `docs/codex-operating-rules.md` now requires need assessment,
background execution, timeout, cleanup, and final PID/port confirmation.

## v0.1B-v0.1D plan

v0.1B is implemented in `manager_reporting_data.py`. The Worker adapter
cross-checks normalized SessionState, Prompt Queue item/evaluation, project
boundary, and optional Review Record before it derives a Worker Report. The
Manager adapter cross-checks the bounded Master Plan snapshot, normalized
Worker Reports, and caller-supplied live Git/recent-commit evidence. A branch,
milestone, validation, protected-path, verified-HEAD, or package-commit mismatch
produces only a blocked Manager Report with one Owner decision request.

The adapter performs no Git or filesystem read, process start, persistence,
network access, route, or UI action. `manager_report_projection` only adds
`read_only=true` and `authority_boundary=derived_reporting_only` to a detached
presentation mapping.

Remaining plan:

1. v0.1C adds the Manager Report as a read-only consumer of the existing
   `/api/overview` Project Control payload. It adds no route, action, or
   persistence.
2. v0.1D validates one actual milestone from Worker Report through Manager
   review to the Project Control Owner view. Browser QA is allowed only for
   that changed UI and must follow the bounded process policy.
