---
name: jarvis-reviewer-call
description: Assemble one Jarvis-Core Reviewer call for an exact candidate commit. Collects the candidate facts, checks the Manager summary against the Owner approval verbatim, and prints the call blocks for the Manager to send. Explicit invocation only; it never reviews, approves, judges, commits, or changes scope.
argument-hint: <40-char-candidate-hash> <task-id>
disable-model-invocation: true
allowed-tools: Read, Grep, Bash(git status:*), Bash(git rev-parse:*), Bash(git log:*), Bash(git diff:*), Bash(git ls-tree:*)
---

# Jarvis Reviewer Call (prototype)

Prepare one Reviewer call. You are the Manager's assistant for assembling the
call, not the Reviewer and not the Owner.

This skill exists because the same five blocks are rebuilt by hand for every
Reviewer call, and because a Manager summary that silently drops an Owner
approval condition has already caused repairs (task-0135, repair 1 and 2).

## When to use

- A candidate commit exists and the Manager is about to run the Reviewer.
- A repair produced a new candidate and a fresh Reviewer call is needed.

Do not use it to review, to decide a verdict, or to prepare QA.

## What this skill never does

- Decide or edit an Owner approval, or supply an approval the Owner did not give.
- Judge the candidate, or treat any check here as a Reviewer PASS.
- Change the candidate hash, widen the file scope, or raise a repair budget.
- Stage, commit, push, merge, or write any repository file.
- Create audit evidence, or write a Reviewer result into a task record.

Everything above belongs to Jarvis governance: the Owner decides approvals and
budgets, the Manager decides scope and order, the Reviewer decides the verdict.

## Current repository facts

Branch and working tree at skill start:

!`git status --short --branch`

Recent commits:

!`git log -5 --format=%h%x20%s`

These two facts are injected because they always succeed. Everything that
depends on the supplied hash is gathered in step 1, so a wrong hash produces a
BLOCKED report instead of aborting the skill.

## Inputs the Manager must supply

| Input | Required | Notes |
| --- | --- | --- |
| Candidate commit hash | yes | full 40 characters, `$1` |
| Task id | yes | `$2`; the record at `memory/tasks/<task-id>.md` holds the baseline, the approval and the summary |
| File scope | yes | exact repository-relative paths the Reviewer may review |
| Purpose | yes | first review of this candidate, or fresh review after repair N |
| Owner approval verbatim | yes | quoted in the task record, or pasted by the Manager |
| Baseline commit | yes | read from the record's `## 기준선` table; the Manager may override it in the request |

The baseline is the commit the task started from. The candidate's own diff shows
only the last commit, so the baseline is what makes the whole task change set
computable.

If the Manager pasted an approval that is not in the task record, say so in the
preflight table. Do not reconcile the two yourself.

## Step 1 — collect candidate facts

Run only these read-only forms, one command per fact:

- `git rev-parse --verify <hash>^{commit}` — a fact for the preflight table: does
  this repository hold that commit. The binding rule stays in the Reviewer
  definition
- `git log -1 --format=%H%n%P%n%s <hash>` — full hash, parents, subject
- `git diff --name-status <baseline> <hash>` — **the task change set**; every scope
  and `jarvis.bat` check below uses this set
- `git diff --name-status <hash>^ <hash>` — what the last commit alone changed;
  informational only, never a scope criterion
- `git log --format=%h%x20%s <baseline>..<hash>` — the commits in the range, for
  the commit-structure block
- `git status --short` — the working tree now
- `git ls-tree -r --name-only <hash> -- jarvis.bat` — must print nothing

Parent handling. Read the parent list from `git log -1 --format=%P`. Use
`<hash>^` only when that list holds exactly one parent, and only for the
informational last-commit diff. If the candidate is a merge (more than one
parent) or a root commit (none), do not pick a parent yourself: say so in the
preflight table, and compute the change set from the baseline instead. The task
change set always comes from the recorded baseline, never from `^`.

Never open `jarvis.bat` and never quote its contents. If it appears in a diff or
in the tree listing, that is a BLOCKED condition.

## Step 2 — read the task record

Read `memory/tasks/<task-id>.md`. From the record, read and keep separate:

- the baseline commit from the `## 기준선` table, unless the Manager supplied one
- the approved file scope, as the Owner approval and the Manager summary state it
- the Owner approval verbatim blocks, including answers to bounded questions
- the Manager summary table
- `status`, `retry_budget`, `retry_count`, `repair_budget`, `repair_count`
- the repair history, so the call states which repair this candidate follows

Quote the approval exactly. Never paraphrase, reflow, or summarize it.

## Step 3 — check the summary against the approval

Go through the verbatim approval condition by condition. For each condition, say
whether a Manager summary row states it. Report:

- conditions the summary leaves out
- summary rows the approval does not support
- summary rows that narrow an approval condition (for example an approval that
  says "other agent definitions" summarized as "other toml files")

This is a report for the Manager, not a correction. Do not edit the record.

## Step 4 — BLOCKED conditions

Print `preflight: BLOCKED`, list the reasons, and do not assemble the call when
any of these is true:

- the Manager supplied no candidate hash, so the call has nothing to pin. Whether
  a supplied hash satisfies the binding is decided by the "Candidate binding
  (fail closed)" section of `.claude/agents/reviewer.md`. Do not restate its
  thresholds here: report what the request and the record contain, and let that
  section bind
- the baseline is missing from both the request and the record's `## 기준선`, so
  the task change set cannot be computed
- the file scope is empty, or a scope path is absent from the **task change set**
  (`<baseline>..<hash>`); the last commit alone is never the criterion
- the task change set contains a path that the approved scope does not list, so
  the candidate is wider than what the Owner approved
- neither the request nor the record gives any Owner approval text to place under
  the marker, so the call cannot carry one. Whether a supplied approval satisfies
  the binding is decided by the "Approval binding (fail closed)" section of
  `.claude/agents/reviewer.md`; this preflight only establishes that the Manager
  has approval text to pass through
- the Manager summary table is missing
- tracked files outside the candidate have uncommitted changes, so the tree does
  not match the candidate
- `jarvis.bat` appears in the task change set or in the candidate's tree listing

A BLOCKED preflight names the smallest missing input. It never guesses a value,
and it never widens the scope to make a check pass.

## Step 5 — assemble the call

When the preflight passes, print the call in exactly this order, ready to send:

```text
Review request from Manager (the caller): <task id>, <purpose>.

Candidate commit (full hash): <hash>
Parent: <parent hash of the candidate>
Baseline: <baseline hash the task started from>

<commit structure, when the task spans several commits: list each commit, its
parent and what it changed, and say which earlier Reviewer results are now
invalid>

File scope:
- <path>
- <path>

Never access `jarvis.bat`.

=== COMMAND FORM REQUIREMENT ===
Follow the "Allowed commands" section of your own definition exactly as written,
including its restrictions on options and on grep patterns. If an output is too
large to read, narrow it with another allowed form; if you cannot, report that
as a finding instead of reading saved tool output.

=== MANAGER SUMMARY ===
<the Manager summary table, copied from the task record without edits>

=== OWNER APPROVAL (verbatim) ===
<every approval block from the task record, copied exactly, including answers
to bounded questions>
```

The marker lines are fixed. The Reviewer definition requires
`=== OWNER APPROVAL (verbatim) ===` exactly, and returns BLOCKED without it. The
command-form block points at that definition on purpose: the rules live there,
and repeating them here would let the two copies drift apart.

## Step 6 — report to the Manager

Print, in this order:

1. `preflight: PASS` or `preflight: BLOCKED` with reasons
2. a table of what was checked: hash resolves, baseline used, parent list,
   task change set, scope match in both directions, `jarvis.bat` absent,
   working tree state, approval present, summary rows missing a condition
3. the budget line, as recorded facts only: `retry_budget`, `retry_count`,
   `repair_budget`, `repair_count`, copied from the record. When
   `repair_count` equals `repair_budget`, add that a further repair would need
   a Manager → Director escalation and an Owner decision. Do not decide whether
   a repair is needed, and never propose or apply a higher budget
4. the assembled call from step 5, when the preflight passed
5. the next action, as a recommendation: run the Reviewer agent with this call,
   pinned to this hash

Stop there. The Manager sends the call and owns the decision.
