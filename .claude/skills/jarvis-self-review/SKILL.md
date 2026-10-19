---
name: jarvis-self-review
description: Run the one read-only Jarvis-Core self-review of STAGED changes before the first candidate commit (SOP 3, task-0172). Checks the preconditions, assembles the self-reviewer request and runs it in a separate read-only claude process. Explicit invocation only; it never reviews a candidate, gives no verdict, writes no repository file and does not replace the Reviewer or jarvis-reviewer-call.
argument-hint: <task-id> <40-char-baseline-hash>
disable-model-invocation: true
allowed-tools: Read, Bash(git status:*), Bash(git diff:*), Bash(python -B scripts/check_task_record.py:*), Bash(claude -p --agent self-reviewer:*)
---

# Jarvis Self-review (task-0172)

Run the self-review once per task, after the task-0171 preflight passes and before the first
candidate commit. It looks at the staged change set from the Reviewer's point of view so the
Implementer can fix, before the candidate exists, what the Reviewer would otherwise find after it.

## What this skill never does

- Review a commit, give a verdict (PASS, FINDINGS, BLOCKED), or stand in for the Reviewer. The
  official Reviewer still reviews the exact candidate commit through `jarvis-reviewer-call`.
- Change the repair budget, SOP §8 or any approval. A fix made here, before a candidate exists,
  is not a repair (SOP §5). Findings from the official Reviewer after the candidate follow §5.
- Write, stage or commit any repository file. The request text goes to a temporary file outside
  the repository; this skill does not pre-approve that write (no `Write` in allowed-tools), so it
  goes through the session's normal permission check. The Implementer (in a manual SOP task, the
  session that also acts as Manager) fixes the findings and records the result.
- Run a second self-review for the same task.

## Step 1 — preconditions

Stop and report when any is false:

1. `python -B scripts/check_task_record.py memory/tasks/$0.md --baseline $1` exits 0.
2. `git diff --name-only` prints nothing for the staged files: the working tree equals the index,
   so the self-reviewer's Read shows the staged content.
3. The task record has no `## Self-review` section yet (once per task).

## Step 2 — the request

Build the request text with these blocks, in this order:

```text
Self-review request from Manager (the caller): <task-id>.
Task record: memory/tasks/<task-id>.md
Baseline (full hash): <baseline>
The working tree equals the index for every staged file.

=== STAGED CHANGE SET (git diff --cached --no-renames <baseline>) ===
<output of git diff --cached --no-renames <baseline>>

=== TASK-0171 PREFLIGHT ===
<output of step 1.1>
```

## Step 3 — run it read-only

Write the request text from step 2 to a temporary file outside the repository (for example the
session scratchpad). From the repository root, pass that file on standard input to a separate
process whose tools are fixed to Read, Grep and Glob:

```text
claude -p --agent self-reviewer --tools Read,Grep,Glob --output-format json < <request file>
```

What is enforced and what is not:

- Enforced by the tool lists: the self-reviewer process has only Read, Grep and Glob. The
  `--tools` list and the agent's own `tools:` line both leave out every write and shell tool, and
  task-0172 checked in a temporary clone that it could neither write a file nor run a command,
  even when the CLI allowed Write and Bash.
- Not enforced, instruction only: that the request file is written outside the repository, that
  the process is started from the repository root, and that nothing else runs for the
  self-review. No tool setting limits those; this text does.

Run nothing else for the self-review.

## Step 4 — report and hand back

Print the `self_review_findings` list as returned, then stop. The Implementer:

1. adds a `## Self-review` section to the task record: each finding, whether it was fixed or
   left as it is and why, and the preflight result after the fixes;
2. stages the fixes and the record and runs step 1.1 again; the candidate is made only when it
   exits 0.
