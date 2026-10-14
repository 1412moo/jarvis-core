"""Smoke tests for the Jarvis v0.2 Claude Worker pipeline (task-0142).

Runs the real pipeline against a throwaway local clone of this repository with a
fake `claude` executable, so no model, network or credential is involved. Each
case checks where the run stopped and that main, push state and jarvis.bat stay
untouched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import claude_worker  # noqa: E402

FAKE_CLAUDE = textwrap.dedent(
    """
    import json, os, subprocess, sys, time
    from pathlib import Path
    args = sys.argv[1:]
    prompt = sys.stdin.read()
    if os.environ.get("FAKE_LOG"):
        with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
            log.write(("REVIEWER" if "--agent" in args else "WORKER") + "\\n" + prompt + "\\n=====\\n")
    if "--agent" in args:
        mode = os.environ.get("FAKE_REVIEW", "pass")
        if mode == "move":
            subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "moved"], check=True)
            mode = "pass"
        if mode == "dirtymain":
            with open("README.md", "a", encoding="utf-8") as readme:
                readme.write("changed during review\\n")
            mode = "pass"
        if mode in ("once", "mixedonce"):
            state = Path(os.environ["FAKE_STATE"])
            mode = "pass" if state.exists() else ("findings" if mode == "once" else "mixed")
            state.write_text("seen", encoding="utf-8")
        summary_item = ("- {severity: minor, evidence: the Manager summary restates the approval more broadly, impact: x, "
                        "minimum_correction: name the term in apps/studyroom/content/glossary.json in the summary}")
        content_item = "- {severity: major, evidence: apps/studyroom/content/glossary.json adds an unsupported fact, impact: x, minimum_correction: y}"
        if mode in ("summaryonly", "mixed"):
            items = [summary_item, summary_item] if mode == "summaryonly" else [summary_item, content_item]
            print(json.dumps({"result": "candidate_hash: x\\nverdict: FINDINGS\\nfindings: " + "\\n  ".join(items)
                              + "\\nunverified: []\\nself_deviations: []\\nnote: n"}))
            sys.exit(0)
        # task-0148: report fields that never change the verdict.
        # Repair 2: a missing or malformed field cannot be classified.
        if mode == "badselfdevonce":
            state = Path(os.environ["FAKE_STATE"])
            mode = "unverifiedpass" if state.exists() else "badselfdev"
            state.write_text("seen", encoding="utf-8")
        if mode in ("nounverified", "badunverified", "noselfdev", "badselfdev"):
            fields = {
                "nounverified": "self_deviations: []",
                "badunverified": "unverified: {item: tests pass, not_run: python, qa: tests_rerun}\\nself_deviations: []",
                "noselfdev": "unverified: []",
                "badselfdev": "unverified: []\\nself_deviations: none that I noticed",
            }[mode]
            print(json.dumps({"result": "candidate_hash: x\\nverdict: PASS\\nfindings: []\\n" + fields + "\\n\\nnote: n"}))
            sys.exit(0)
        if mode == "deviateonce":
            state = Path(os.environ["FAKE_STATE"])
            mode = "unverifiedpass" if state.exists() else "deviate"
            state.write_text("seen", encoding="utf-8")
        if mode in ("unverifiednone", "unverifiedbadqa", "unverifiednoqa"):
            qa = {"unverifiednone": ", qa: none", "unverifiedbadqa": ", qa: tests_passed", "unverifiednoqa": ""}[mode]
            entries = ("- {item: Studyroom smoke tests pass, not_run: python -B apps/studyroom/run_smoke_tests.py, qa: tests_rerun}\\n  "
                       "- {item: the new term matches the task-0142 record, not_run: none" + qa + "}")
            print(json.dumps({"result": "candidate_hash: x\\nverdict: PASS\\nfindings: []\\nunverified: " + entries
                              + "\\nself_deviations: []\\n\\nnote: n"}))
            sys.exit(0)
        if mode in ("unverifiedpass", "deviate", "deviatealways"):
            unverified = "- {item: Studyroom smoke tests pass, not_run: python -B apps/studyroom/run_smoke_tests.py, qa: tests_rerun}"
            deviation = "- {command: git grep -n a|b x -- f, rule: single grep pattern}" if mode != "unverifiedpass" else "[]"
            print(json.dumps({"result": "candidate_hash: x\\nverdict: PASS\\nfindings: []\\nunverified: " + unverified
                              + "\\nself_deviations: " + deviation + "\\n\\nnote: n"}))
            sys.exit(0)
        if mode == "needevidence":
            mode = "pass" if "Evidence paths" in prompt and "- memory/tasks/task-0142-" in prompt else "findings"
        if mode in ("blocked", "garbage"):
            print(json.dumps({"result": "verdict: BLOCKED\\nfindings: []\\nunverified: []\\nself_deviations: []"
                              if mode == "blocked" else "no verdict here"}))
            sys.exit(0)
        verdict = "PASS" if mode == "pass" else "FINDINGS"
        body = "findings: []" if mode == "pass" else "findings: " + content_item
        print(json.dumps({"result": f"candidate_hash: x\\nverdict: {verdict}\\n{body}\\nunverified: []\\nself_deviations: []"}))
        sys.exit(3 if mode == "crashfindings" else 0)
    mode = os.environ.get("FAKE_WORKER", "ok")
    if mode == "timeout":
        time.sleep(30)
    if mode == "fail":
        print("boom", file=sys.stderr)
        sys.exit(3)
    if mode == "scope_on_repair":
        mode = "scope" if "This is a repair." in prompt else "ok"
    if mode == "scope":
        Path("docs/should-not-change.md").write_text("x\\n", encoding="utf-8")
    elif mode == "jarvisbat":
        Path("jarvis.bat").write_text("echo x\\n", encoding="utf-8")
    elif mode == "badjson":
        Path("apps/studyroom/content/glossary.json").write_text("{not json", encoding="utf-8")
    elif mode == "ok":
        p = Path("apps/studyroom/content/glossary.json")
        data = json.loads(p.read_text(encoding="utf-8"))
        data.append({"id": f"fake-term-{len(data)}", "term": "Fake", "dev_definition": "d", "simple_explanation": "s", "jarvis_example": "e"})
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8", newline="\\n")
    print(json.dumps({"result": "edited"}))
    """
)

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (f" ({detail})" if detail and not ok else ""))


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def make_env(tmp: Path) -> tuple[Path, Path]:
    clone = tmp / "repo"
    subprocess.run(["git", "clone", "-q", "--local", str(REPO_ROOT), str(clone)], check=True)
    git(["config", "user.email", "smoke@example.invalid"], clone)
    git(["config", "user.name", "smoke"], clone)
    fake_dir = tmp / "bin"
    fake_dir.mkdir()
    (fake_dir / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="utf-8")
    if os.name == "nt":
        (fake_dir / "fakeclaude.cmd").write_text(f'@"{sys.executable}" "{fake_dir / "fake_claude.py"}" %*\r\n', encoding="utf-8")
    else:
        shim = fake_dir / "fakeclaude"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake_dir / "fake_claude.py"}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
    return clone, fake_dir


def write_task(clone: Path, task_id: str) -> None:
    (clone / "memory" / "tasks" / f"{task_id}.md").write_text(f"# {task_id}\n", encoding="utf-8")


def run_case(name: str, clone: Path, worktrees: Path, *, worker: str, review: str = "pass", prepare=None,
             request: str = "Studyroom glossary에 용어 1개 추가", task_id: str | None = None, resume: bool = False, repair_budget: int | None = None):
    os.environ["FAKE_WORKER"] = worker
    os.environ["FAKE_REVIEW"] = review
    task_id = task_id or f"task-8000-{name}"
    write_task(clone, task_id)
    if prepare:
        prepare(clone)
    calls: list[tuple[bool, str]] = []

    def record(success: bool, summary: str) -> tuple[bool, str]:
        calls.append((success, summary))
        return True, ""

    before = git(["rev-parse", "HEAD"], clone)
    origin_before = git(["rev-parse", "origin/main"], clone)
    result = claude_worker.run_pipeline(
        task_id=task_id,
        request=request,
        approval_command=f"/go {task_id}",
        repo_root=clone,
        worktree_root=worktrees,
        record_result=record,
        resume=resume,
        repair_budget=repair_budget,
    )
    after = git(["rev-parse", "HEAD"], clone)
    check(f"{name}: no push", git(["rev-parse", "origin/main"], clone) == origin_before and not result.pushed)
    check(f"{name}: jarvis.bat never in main index or tree", not git(["ls-files", "--", "jarvis.bat"], clone))
    return result, calls, before, after


def bot_flow(clone: Path, worktrees: Path) -> None:
    """/work -> /go -> worker job through the Discord adapter, against the clone.

    The adapter's repository root, task writer and audit hooks are pointed at the
    clone or stubbed, so the real task directory and audit chain stay untouched.
    """

    import functools

    sys.path.insert(0, str(REPO_ROOT / "adapters" / "discord"))
    import bot_minimal as bot

    bot.REPO_ROOT = clone
    bot.write_task_file = functools.partial(bot.write_task_file, tasks_dir=clone / "memory" / "tasks")
    audits: list[str] = []
    bot._audit_owner_approval = lambda **kw: audits.append("approval") or None

    # The execution audit runs the adapter's real payload build and the real payload
    # validator; only the chain append is replaced, so a rejected source shows up here.
    from audit_entry import validate_payload

    execution_sources: list[str] = []
    execution_audit_errors: list[str | None] = []

    def validate_execution_record(**fields: object) -> None:
        execution_sources.append(str(fields["source"]))
        validate_payload("execution_result", {key: value for key, value in fields.items() if key != "task_id"})

    bot.record_execution_result = validate_execution_record
    real_audit_execution_result = bot._audit_execution_result

    def audit_execution_result(**kw: object) -> str | None:
        audits.append("execution")
        execution_audit_errors.append(real_audit_execution_result(**kw))
        return execution_audit_errors[-1]

    bot._audit_execution_result = audit_execution_result
    claude_worker.WORKTREE_ROOT = worktrees

    def status_of(task_id: str) -> str:
        meta = bot._read_task_metadata(clone / "memory" / "tasks" / f"{task_id}.md") or {}
        return meta.get("status", "")

    hold = bot._run_command("/work README 문장 고쳐줘")
    check("bot: non-Studyroom request is held", hold.get("result_type") == "hold" and "studyroom_content_only" in hold.get("reason", ""))

    owner = "111111111111111111"
    os.environ[bot.OWNER_IDS_ENV] = owner
    check("bot: /work and /go are Owner-only", bot._authorize_command("/work studyroom x", "999999999999999999")[0] is False
          and bot._authorize_command("/go task-0001-x", "999999999999999999")[0] is False
          and bot._authorize_command("/go task-0001-x", owner)[0] is True)

    planned = bot._run_command("/work Studyroom glossary에 용어 1개 추가")
    task_id = planned.get("task_id", "")
    check("bot: /work creates a TODO task and a plan", planned.get("result_type") == "work_planned" and status_of(task_id) == "TODO")
    check("bot: plan reply names the approval command", f"/go {task_id}" in bot._format_reply(planned))

    os.environ["FAKE_WORKER"], os.environ["FAKE_REVIEW"] = "scope", "pass"
    started = bot._run_command(f"/go {task_id}")
    check("bot: /go moves TODO to DOING and audits the approval", started.get("result_type") == "work_started" and status_of(task_id) == "DOING" and audits[-1] == "approval")
    check("bot: second /go while running is refused", bot._run_command(f"/go {task_id}").get("reason", "").startswith(("worker_busy", "status_not_startable")))
    failed = bot._run_worker_job(task_id, started["request"], started["command"])
    reply = bot._format_reply(failed)
    check("bot: failure recorded as FAILED with options", status_of(task_id) == "FAILED" and "재시도" in reply and "scope_violation" in reply)
    unfixable = bot._format_reply(dict(failed, stage="reviewer", reason="reviewer_findings_not_repairable"))
    check("bot: not-repairable FINDINGS reply asks for an Owner decision",
          "변경 파일과 무관해 Worker가 고칠 수 없습니다. Owner 결정이 필요합니다." in unfixable)

    os.environ["FAKE_WORKER"] = "ok"
    head_before = git(["rev-parse", "HEAD"], clone)
    retry = bot._run_command(f"/go {task_id}")
    check("bot: /go on FAILED retries (FAILED -> TODO -> DOING)", retry.get("result_type") == "work_started" and retry.get("retry") is True and status_of(task_id) == "DOING")
    done = bot._run_worker_job(task_id, retry["request"], retry["command"])
    check("bot: success reply and task DONE", done.get("ok") is True and status_of(task_id) == "DONE" and "✅" in bot._format_reply(done), f"{done.get('stage')}:{done.get('reason')}:{done.get('detail')}")
    check("bot: checkpoint commit tracks the task record", git(["log", "-1", "--format=%H"], clone) == done.get("checkpoint")
          and f"memory/tasks/{task_id}.md" in git(["show", "--name-only", "--format=", "HEAD"], clone)
          and git(["rev-list", "--count", f"{head_before}..HEAD"], clone) == "2")
    check("bot: execution results audited", audits.count("execution") == 2)
    check("bot: /go execution audits send source go", execution_sources == ["go", "go"], str(execution_sources))
    check("bot: /go execution audits pass the payload validator", execution_audit_errors == [None, None], str(execution_audit_errors))

    # task-0157: a committed task record. The /go transition then changes a tracked file before the run.
    def commit_record(tid: str) -> None:
        git(["add", "--", f"memory/tasks/{tid}.md"], clone)
        git(["commit", "-q", "-m", f"track {tid}"], clone)

    os.environ["FAKE_WORKER"] = "ok"
    tracked_todo = bot._run_command("/work Studyroom glossary에 용어 1개 추가")["task_id"]
    commit_record(tracked_todo)
    started = bot._run_command(f"/go {tracked_todo}")
    done = bot._run_worker_job(tracked_todo, started["request"], started["command"])
    check("bot: /go on a TODO task with a committed record runs to DONE", started.get("result_type") == "work_started"
          and done.get("ok") is True and status_of(tracked_todo) == "DONE"
          and not git(["status", "--porcelain", "--untracked-files=no"], clone), f"{done.get('stage')}:{done.get('reason')}")

    os.environ["FAKE_WORKER"] = "scope"
    tracked_failed = bot._run_command("/work Studyroom glossary에 용어 1개 추가")["task_id"]
    started = bot._run_command(f"/go {tracked_failed}")
    bot._run_worker_job(tracked_failed, started["request"], started["command"])
    commit_record(tracked_failed)
    os.environ["FAKE_WORKER"] = "ok"
    retry = bot._run_command(f"/go {tracked_failed}")
    done = bot._run_worker_job(tracked_failed, retry["request"], retry["command"])
    check("bot: /go retry of a FAILED task with a committed record runs to DONE (task-0143 shape)",
          retry.get("retry") is True and done.get("ok") is True and status_of(tracked_failed) == "DONE"
          and f"memory/tasks/{tracked_failed}.md" in git(["show", "--name-only", "--format=", "HEAD"], clone)
          and not git(["status", "--porcelain", "--untracked-files=no"], clone), f"{done.get('stage')}:{done.get('reason')}")
    check("bot: /go resume on a non-FAILED task is refused", bot._run_command(f"/go {task_id} resume").get("reason", "").startswith(("resume_requires_failed", "status_not_startable")))
    check("bot: /go with an unknown argument is a usage error", bot._run_command(f"/go {task_id} again").get("reason") == "usage:/go <task-id> [resume|accept]")
    check("bot: finished task is not startable again", bot._run_command(f"/go {task_id}").get("reason") == "status_not_startable:DONE")

    # task-0151: /go <id> accept through the adapter.
    check("bot: accept on a DONE task is refused", bot._run_command(f"/go {task_id} accept").get("reason") == "accept_requires_failed:DONE")
    other = bot._run_command("/work Studyroom glossary에 용어 1개 더 추가").get("task_id", "")
    os.environ["FAKE_WORKER"], os.environ["FAKE_REVIEW"] = "scope", "pass"
    started = bot._run_command(f"/go {other}")
    bot._run_worker_job(other, started["request"], started["command"])
    check("bot: accept on a task failed for another reason is refused", status_of(other) == "FAILED"
          and bot._run_command(f"/go {other} accept").get("reason") == "accept_record_invalid")

    owner_task = bot._run_command("/work Studyroom glossary에 확인 대기 용어 추가").get("task_id", "")
    os.environ["FAKE_WORKER"], os.environ["FAKE_REVIEW"] = "ok", "unverifiednone"
    started = bot._run_command(f"/go {owner_task}")
    stopped = bot._run_worker_job(owner_task, started["request"], started["command"])
    task_path = clone / "memory" / "tasks" / f"{owner_task}.md"
    record = bot._owner_review_record(task_path)
    check("bot: qa_unverified_owner_review stop leaves FAILED and the exact record", status_of(owner_task) == "FAILED"
          and record == claude_worker.owner_review_record(stopped["candidate"], stopped["baseline"], 1), str(record))
    check("bot: that reply offers /go <id> accept", f"`/go {owner_task} accept` 확인을 마친 candidate 반영" in bot._format_reply(stopped))

    approvals_before = audits.count("approval")
    started = bot._run_command(f"/go {owner_task} accept")
    check("bot: accept starts without a status change or approval audit", started.get("result_type") == "work_started"
          and started.get("accept") is True and status_of(owner_task) == "FAILED" and audits.count("approval") == approvals_before)
    check("bot: accept started reply", bot._format_reply(started).startswith(f"▶️ 승인됨 (accept): {owner_task} → "))
    check("bot: a second /go while accept runs is refused", bot._run_command(f"/go {owner_task} accept").get("reason") == "worker_busy")
    real_run_tests = claude_worker._run_tests
    claude_worker._run_tests = lambda worktree: (False, "forced failure")
    qa_failed = bot._run_worker_job(owner_task, started["request"], started["command"], False, True)
    claude_worker._run_tests = real_run_tests
    check("bot: accept QA failure keeps FAILED, the record and no approval audit", qa_failed.get("reason") == "accept_qa_failed"
          and status_of(owner_task) == "FAILED" and bot._owner_review_record(task_path) == record
          and audits.count("approval") == approvals_before and qa_failed.get("audit_error") is None)
    check("bot: that reply offers accept again", f"`/go {owner_task} accept`" in bot._format_reply(qa_failed))

    head_before = git(["rev-parse", "HEAD"], clone)
    executions_before = audits.count("execution")
    started = bot._run_command(f"/go {owner_task} accept")
    accepted = bot._run_worker_job(owner_task, started["request"], started["command"], False, True)
    check("bot: accept integrates and marks DONE", accepted.get("ok") is True and status_of(owner_task) == "DONE"
          and git(["rev-parse", "HEAD^"], clone) == stopped["candidate"] and git(["rev-list", "--count", f"{head_before}..HEAD"], clone) == "2",
          f"{accepted.get('stage')}:{accepted.get('reason')}:{accepted.get('detail')}")
    check("bot: accept audits the approval once and the execution with source go",
          audits.count("approval") == approvals_before + 1 and audits.count("execution") == executions_before + 1
          and execution_sources[-1] == "go" and execution_audit_errors[-1] is None)
    check("bot: accept success reply says the Reviewer was not called again", "- Reviewer: 재호출 없음 (Owner accept)" in bot._format_reply(accepted))


def attempt_of(task_id: str, branch: str) -> int:
    name = branch[len("jarvis/"):]
    return 1 if name == task_id else int(name.rsplit("-r", 1)[1])


def accept_flow(clone: Path, worktrees: Path) -> None:
    """task-0151: claude_worker.accept_candidate against preserved qa_unverified_owner_review attempts."""

    def owner_review_attempt(task_id: str, earlier: tuple[str, ...] = ()):
        for review in earlier:
            run_case(task_id[len("task-8000-"):], clone, worktrees, worker="ok", review=review, task_id=task_id)
        r, calls, *_ = run_case(task_id[len("task-8000-"):], clone, worktrees, worker="ok", review="unverifiednone", task_id=task_id)
        return r, calls[-1][1]

    def accept(task_id: str, record: str, approve_result: tuple[bool, str] = (True, ""), before_approve=None):
        approvals: list[int] = []
        calls: list[tuple[bool, str]] = []

        def approve() -> tuple[bool, str]:
            approvals.append(1)
            if before_approve:
                before_approve()
            return approve_result

        def record_result(success: bool, summary: str) -> tuple[bool, str]:
            calls.append((success, summary))
            return True, ""

        origin_before = git(["rev-parse", "origin/main"], clone)
        r = claude_worker.accept_candidate(task_id=task_id, record=record, approve=approve, repo_root=clone,
                                           worktree_root=worktrees, record_result=record_result)
        check(f"accept {task_id}: no push", git(["rev-parse", "origin/main"], clone) == origin_before and not r.pushed)
        return r, approvals, calls

    def refused(name: str, r, approvals, calls, reason: str, head: str, attempt) -> None:
        check(f"accept refusal: {name} -> {reason}, nothing changed or recorded",
              (not r.ok) and r.reason == reason and r.accept_retryable and not approvals and not calls
              and git(["rev-parse", "HEAD"], clone) == head and git(["rev-parse", attempt.branch], clone) == attempt.candidate
              and Path(attempt.worktree).exists(), f"{r.stage}:{r.reason}:{r.detail}")

    # The failure record names the exact candidate; other failure records stay "stage:reason".
    attempt, record = owner_review_attempt("task-8000-accref")
    check("accept record: qa_unverified_owner_review records candidate, baseline and attempt",
          record == claude_worker.owner_review_record(attempt.candidate, attempt.baseline, attempt_of("task-8000-accref", attempt.branch))
          and claude_worker.parse_owner_review_record(record) == (attempt.candidate, attempt.baseline, 1), record)
    head = git(["rev-parse", "HEAD"], clone)
    wt, branch = Path(attempt.worktree), attempt.branch

    r, a, c = accept("task-8000-accref", "qa:qa_unverified_owner_review")
    refused("bare record", r, a, c, "accept_record_invalid", head, attempt)
    r, a, c = accept("task-8000-accref", record.replace(attempt.candidate, attempt.baseline))
    refused("tip differs from the recorded candidate", r, a, c, "accept_candidate_mismatch", head, attempt)
    r, a, c = accept("task-8000-accref", record.replace(attempt.baseline, git(["rev-parse", f"{attempt.baseline}^"], clone)))
    refused("recorded baseline is not the candidate's parent", r, a, c, "accept_chain_mismatch", head, attempt)

    git(["update-ref", "-d", f"refs/heads/{branch}"], clone)
    r, a, c = accept("task-8000-accref", record)
    git(["update-ref", f"refs/heads/{branch}", attempt.candidate], clone)
    refused("branch missing", r, a, c, "accept_branch_missing", head, attempt)

    moved_wt = wt.with_name(wt.name + "-moved")
    wt.rename(moved_wt)
    r, a, c = accept("task-8000-accref", record)
    moved_wt.rename(wt)
    refused("worktree missing", r, a, c, "accept_worktree_missing", head, attempt)

    git(["checkout", "-q", "--detach"], wt)
    r, a, c = accept("task-8000-accref", record)
    git(["checkout", "-q", branch], wt)
    refused("worktree not on the attempt branch", r, a, c, "accept_worktree_mismatch", head, attempt)

    git(["update-ref", f"refs/heads/{branch}", f"{attempt.candidate}^"], clone)
    r, a, c = accept("task-8000-accref", record)
    git(["update-ref", f"refs/heads/{branch}", attempt.candidate], clone)
    refused("HEAD and tip moved off the candidate", r, a, c, "accept_candidate_mismatch", head, attempt)

    (wt / "apps/studyroom/content/untracked.txt").write_text("x\n", encoding="utf-8")
    r, a, c = accept("task-8000-accref", record)
    (wt / "apps/studyroom/content/untracked.txt").unlink()
    refused("dirty worktree", r, a, c, "accept_worktree_dirty", head, attempt)

    (wt / "docs" / "outside.md").write_text("x\n", encoding="utf-8")
    git(["add", "docs/outside.md"], wt)
    git(["commit", "-q", "-m", "feat(studyroom): task-8000-accref Jarvis worker repair 1 candidate"], wt)
    outside = git(["rev-parse", "HEAD"], wt)
    r, a, c = accept("task-8000-accref", record.replace(attempt.candidate, outside))
    git(["reset", "-q", "--hard", attempt.candidate], wt)
    refused("a candidate chain that leaves the allowed path", r, a, c, "accept_scope_violation", head, attempt)

    (clone / "memory" / "tasks" / "task-8000-accref-r2.md").write_text("# task-8000-accref-r2\n", encoding="utf-8")
    r, a, c = accept("task-8000-accref", record)
    (clone / "memory" / "tasks" / "task-8000-accref-r2.md").unlink()
    refused("another task named like an attempt", r, a, c, "accept_attempt_ambiguous", head, attempt)

    (clone / "docs" / "accept-moved.md").write_text("x\n", encoding="utf-8")
    git(["add", "docs/accept-moved.md"], clone)
    git(["commit", "-q", "-m", "move main"], clone)
    r, a, c = accept("task-8000-accref", record)
    check("accept refusal: main moved off the baseline, main left where it is", (not r.ok) and r.reason == "accept_baseline_moved"
          and r.accept_retryable and not a and not c and git(["rev-parse", "HEAD^"], clone) == head, f"{r.reason}")
    git(["reset", "-q", "--hard", head], clone)

    readme = clone / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "x\n", encoding="utf-8")
    r, a, c = accept("task-8000-accref", record)
    git(["checkout", "--", "README.md"], clone)
    refused("main has tracked changes", r, a, c, "accept_main_dirty", head, attempt)

    real_run_tests = claude_worker._run_tests
    claude_worker._run_tests = lambda worktree: (False, "forced failure")
    r, a, c = accept("task-8000-accref", record)
    claude_worker._run_tests = real_run_tests
    refused("QA re-run fails", r, a, c, "accept_qa_failed", head, attempt)
    check("accept refusal: the QA failure names the failed check", r.detail == "tests_rerun" and r.qa_checks.get("tests_rerun") is False, r.detail)

    def dirtying_tests(worktree: Path) -> tuple[bool, str]:
        (worktree / "apps/studyroom/content/left-behind.txt").write_text("x\n", encoding="utf-8")
        return True, "ok"

    claude_worker._run_tests = dirtying_tests
    r, a, c = accept("task-8000-accref", record)
    claude_worker._run_tests = real_run_tests
    (wt / "apps/studyroom/content/left-behind.txt").unlink()
    refused("QA run leaves changes behind", r, a, c, "accept_worktree_dirty", head, attempt)

    r, a, c = accept("task-8000-accref", record, approve_result=(False, "status_mismatch"))
    check("accept: a refused approval transition records nothing and is not offered again", (not r.ok)
          and r.reason == "accept_transition_failed" and a == [1] and not c and not r.accept_retryable
          and git(["rev-parse", "HEAD"], clone) == head, f"{r.reason}")

    def move_main() -> None:
        (clone / "docs" / "accept-race.md").write_text("x\n", encoding="utf-8")
        git(["add", "docs/accept-race.md"], clone)
        git(["commit", "-q", "-m", "move main during approval"], clone)

    r, a, c = accept("task-8000-accref", record, before_approve=move_main)
    check("accept: main moving after approval fails like run_pipeline (integrate:baseline_moved recorded, no ff)",
          (not r.ok) and r.stage == "integrate" and r.reason == "baseline_moved" and not r.accept_retryable
          and c == [(False, "integrate:baseline_moved")] and git(["rev-parse", "HEAD^"], clone) == head
          and git(["rev-parse", branch], clone) == attempt.candidate and wt.exists(), f"{r.stage}:{r.reason}:{c}")
    git(["reset", "-q", "--hard", head], clone)

    # After every refusal above the same record still accepts (QA failure included).
    r, a, c = accept("task-8000-accref", record)
    check("accept: the recorded candidate integrates after earlier refusals", r.ok and r.stage == "done" and r.accepted
          and a == [1] and len(c) == 1 and c[0][0] is True and "accepted by the Owner" in c[0][1], f"{r.stage}:{r.reason}:{r.detail}")
    check("accept: main is candidate + checkpoint, attempt cleaned", git(["rev-parse", "HEAD^"], clone) == attempt.candidate
          and git(["rev-list", "--count", f"{head}..HEAD"], clone) == "2" and r.checkpoint == git(["rev-parse", "HEAD"], clone)
          and not wt.exists() and not git(["branch", "--list", branch], clone), f"{r.checkpoint}")
    check("accept: all six QA checks re-ran and the Reviewer was not called", len(r.qa_checks) == 6 and all(r.qa_checks.values())
          and r.reviewer_verdict == "")
    check("accept: jarvis.bat never in main index or tree", not git(["ls-files", "--", "jarvis.bat"], clone))

    r, a, c = accept("task-8000-accnone", claude_worker.owner_review_record("a" * 40, "b" * 40, 1))
    check("accept refusal: no attempt at all -> accept_branch_missing", (not r.ok) and r.reason == "accept_branch_missing" and not a and not c, r.reason)

    # A later attempt exists: the record is stale.
    stale, stale_record = owner_review_attempt("task-8000-accnewer")
    run_case("accnewer", clone, worktrees, worker="ok", review="findings", task_id="task-8000-accnewer")
    head = git(["rev-parse", "HEAD"], clone)
    r, a, c = accept("task-8000-accnewer", stale_record)
    refused("a later attempt exists", r, a, c, "accept_newer_attempt", head, stale)

    # task-0149 shape: two attempts on the same baseline with the same commit subject; the record picks its own.
    two, two_record = owner_review_attempt("task-8000-acctwo", earlier=("findings",))
    first = git(["rev-parse", "jarvis/task-8000-acctwo"], clone)
    check("accept setup: two attempts share the baseline", two.branch == "jarvis/task-8000-acctwo-r2"
          and git(["merge-base", first, two.candidate], clone) == two.baseline)
    head = git(["rev-parse", "HEAD"], clone)
    r, a, c = accept("task-8000-acctwo", two_record)
    check("accept: with an earlier attempt on the same baseline, the recorded one integrates", r.ok
          and git(["rev-parse", "HEAD^"], clone) == two.candidate and git(["rev-parse", "jarvis/task-8000-acctwo"], clone) == first,
          f"{r.stage}:{r.reason}:{r.detail}")

    # task-0143 shape: earlier attempts removed, only -r3 left.
    gap, gap_record = owner_review_attempt("task-8000-accgap", earlier=("findings", "findings"))
    for name in ("task-8000-accgap", "task-8000-accgap-r2"):
        git(["worktree", "remove", "--force", str(worktrees / name)], clone)
        git(["branch", "-D", f"jarvis/{name}"], clone)
    check("accept setup: only -r3 is left", gap.branch == "jarvis/task-8000-accgap-r3"
          and claude_worker._attempt_numbers(clone, worktrees, "task-8000-accgap") == ({3}, False))
    r, a, c = accept("task-8000-accgap", gap_record)
    check("accept: a gap in attempt numbers does not hide the recorded attempt", r.ok and git(["rev-parse", "HEAD^"], clone) == gap.candidate,
          f"{r.stage}:{r.reason}:{r.detail}")

    # task-0157: a committed record, as in the real sequence. The record is committed before the run, so the
    # attempt's baseline holds it (run_case rewrites the same content). The stopped run then writes its failure
    # result into that record (the bot's record callback; the fake here does not, so it is written by hand),
    # which leaves a tracked change on main before /go <id> accept. The approval writes into it again.
    write_task(clone, "task-8000-acctracked")
    git(["add", "--", "memory/tasks/task-8000-acctracked.md"], clone)
    git(["commit", "-q", "-m", "track task-8000-acctracked"], clone)
    tracked, tracked_record = owner_review_attempt("task-8000-acctracked")
    record_path = clone / "memory" / "tasks" / "task-8000-acctracked.md"
    head = git(["rev-parse", "HEAD"], clone)
    check("accept setup: the committed record is unchanged at the attempt baseline",
          tracked.baseline == head and not git(["status", "--porcelain", "--untracked-files=no"], clone))
    record_path.write_text(record_path.read_text(encoding="utf-8") + f"- execution_summary: `{tracked_record}`\n", encoding="utf-8")

    # Any other tracked change still stops accept before approval, and nothing is changed or recorded.
    (clone / "README.md").write_text((clone / "README.md").read_text(encoding="utf-8") + "x\n", encoding="utf-8")
    r, a, c = accept("task-8000-acctracked", tracked_record)
    refused("another tracked change besides the own record", r, a, c, "accept_main_dirty", head, tracked)
    git(["checkout", "--", "README.md"], clone)

    def approve_writes_record() -> None:
        record_path.write_text(record_path.read_text(encoding="utf-8") + "- status: `DOING`\n", encoding="utf-8")

    r, a, c = accept("task-8000-acctracked", tracked_record, before_approve=approve_writes_record)
    committed = git(["show", "HEAD:memory/tasks/task-8000-acctracked.md"], clone)
    check("accept: with the failure result written into the committed record, the candidate integrates", r.ok and r.stage == "done"
          and git(["rev-parse", "HEAD^"], clone) == tracked.candidate
          and f"- execution_summary: `{tracked_record}`" in committed and "- status: `DOING`" in committed
          and not git(["status", "--porcelain", "--untracked-files=no"], clone), f"{r.stage}:{r.reason}:{r.detail}")


def attempt_numbering(clone: Path, worktrees: Path) -> None:
    """task-0152: attempts are found whatever the gaps, and a new one goes after the highest."""

    def worktree(name: str) -> Path:
        path = worktrees / name
        git(["worktree", "add", "-q", "-b", f"jarvis/{name}", str(path), "HEAD"], clone)
        return path

    cases = {
        "none": ((), (), (), []),
        "base": (("",), (), (), [1]),
        "contiguous": (("", "-r2", "-r3"), (), (), [1, 2, 3]),
        "r3only": (("-r3",), (), (), [3]),
        "baser3": (("", "-r3"), (), (), [1, 3]),
        "r5r7": (("-r5", "-r7"), (), (), [5, 7]),
        "branchonly": ((), ("-r2",), (), [2]),
        "dironly": ((), (), ("-r4",), [4]),
    }
    for name, (trees, branches, dirs, expected) in cases.items():
        task_id = f"task-8000-num{name}"
        for suffix in trees:
            worktree(task_id + suffix)
        for suffix in branches:
            git(["branch", f"jarvis/{task_id}{suffix}", "HEAD"], clone)
        for suffix in dirs:
            (worktrees / f"{task_id}{suffix}").mkdir(parents=True)
        found = claude_worker._existing_attempts(clone, worktrees, task_id)
        check(f"attempt numbers: {name} -> {expected}", found == expected, str(found))

    def glossary_edit(path: Path, term: str) -> None:
        glossary = path / "apps/studyroom/content/glossary.json"
        data = json.loads(glossary.read_text(encoding="utf-8"))
        data.append({"id": term, "term": term, "dev_definition": "d", "simple_explanation": "s", "jarvis_example": "e"})
        glossary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Only -r3 left (task-0143 shape): /go makes -r4 and leaves -r3 alone.
    r3 = worktree("task-8000-gapgo-r3")
    r3_tip = git(["rev-parse", "jarvis/task-8000-gapgo-r3"], clone)
    r = run_case("gapgo", clone, worktrees, worker="ok", task_id="task-8000-gapgo")[0]
    check("attempt numbers: with only -r3, /go makes -r4", r.ok and r.branch == "jarvis/task-8000-gapgo-r4", f"{r.branch}:{r.stage}:{r.reason}")
    check("attempt numbers: the existing -r3 branch, tip and worktree are kept", r3.exists()
          and git(["rev-parse", "jarvis/task-8000-gapgo-r3"], clone) == r3_tip and not git(["branch", "--list", "jarvis/task-8000-gapgo"], clone))

    # Only -r3 left: resume finds it instead of resume_no_previous_attempt.
    r3 = worktree("task-8000-gapresume-r3")
    glossary_edit(r3, "gap-resume-r3")
    r = run_case("gapresume", clone, worktrees, worker="fail", resume=True, task_id="task-8000-gapresume")[0]
    check("attempt numbers: with only -r3, resume carries -r3 into -r4", r.ok and r.resumed_from == "jarvis/task-8000-gapresume-r3"
          and r.branch == "jarvis/task-8000-gapresume-r4" and r.reason != "resume_no_previous_attempt", f"{r.stage}:{r.reason}:{r.resumed_from}")

    # Attempt 1 and -r3, no -r2: resume picks the latest, -r3, not attempt 1.
    old = run_case("gapboth", clone, worktrees, worker="ok", review="findings", task_id="task-8000-gapboth")[0]
    r3 = worktree("task-8000-gapboth-r3")
    glossary_edit(r3, "gap-both-r3")
    r = run_case("gapboth", clone, worktrees, worker="fail", resume=True, task_id="task-8000-gapboth")[0]
    check("attempt numbers: with attempt 1 and -r3, resume picks -r3", r.ok and r.resumed_from == "jarvis/task-8000-gapboth-r3"
          and "gap-both-r3" in git(["show", f"{r.candidate}:apps/studyroom/content/glossary.json"], clone),
          f"{r.stage}:{r.reason}:{r.resumed_from}")
    check("attempt numbers: attempt 1 and -r3 are kept", git(["rev-parse", old.branch], clone) == old.candidate and r3.exists())


def owner_review_replies(results: dict[str, dict]) -> None:
    """task-0150: the Discord reply for qa_unverified_owner_review lists the pending entries."""

    import bot_minimal as bot

    for mode in ("unverifiednone", "unverifiedbadqa", "unverifiednoqa"):
        reply = bot._format_reply(results[mode])
        check(f"owner review reply: {mode} lists the pending entry and says QA passed",
              "- QA 6개 검사는 모두 통과했지만" in reply and "Owner 확인이 필요합니다." in reply
              and "- 확인 대기 1/1: {item: the new term matches the task-0142 record" in reply, reply)
        check(f"owner review reply: {mode} leaves out the entry paired with tests_rerun",
              "Studyroom smoke tests" not in reply and "확인 대기 2/" not in reply, reply)
        check(f"owner review reply: {mode} offers /go <id> accept (task-0151)",
              f"· `/go {results[mode]['task_id']} accept` 확인을 마친 candidate 반영 · `/status " in reply, reply)
    for mode in ("nounverified", "badunverified"):
        reply = bot._format_reply(results[mode])
        check(f"owner review reply: {mode} explains the unreadable field",
              "- 확인 대기 1/1: Reviewer 보고의 unverified 필드가 없거나 형식이 맞지 않아 항목을 읽을 수 없습니다" in reply, reply)

    base = results["unverifiednone"]
    long_id = "task-9999-" + "x" * 90
    many = dict(base, task_id=long_id, detail="d" * 400, worktree="C:/" + "w" * 200, branch="jarvis/" + long_id,
                candidates=["a" * 40, "b" * 40, "c" * 40],
                reviewer_unverified=[f"{{item: entry {i:02d} " + "y" * 480 + ", qa: none}" for i in range(12)])
    reply = bot._format_reply(many)
    check("owner review reply: 12 pending entries show 5 and 외 7건", "- 확인 대기 5/12: {item: entry 04" in reply
          and "확인 대기 6/12" not in reply and "- 외 7건" in reply, reply[-600:])
    check("owner review reply: the whole reply stays within 2000 characters", len(reply) <= 2000, str(len(reply)))
    check("owner review reply: other lines are kept when entries are narrowed",
          f"다음 선택지: `/go {long_id}` 처음부터 재시도" in reply and "- 상세: " + "d" * 300 in reply, reply[:200])
    roomy = dict(base, reviewer_unverified=["{item: " + "z" * 300 + ", qa: none}", "{item: short, qa: tests_rerun}"])
    entry_lines = [line for line in bot._format_reply(roomy).splitlines() if line.startswith("- 확인 대기")]
    check("owner review reply: an entry is cut at 200 characters when there is room",
          len(entry_lines) == 1 and len(entry_lines[0].split(": ", 1)[1]) == 200 and entry_lines[0].endswith("…"), str(entry_lines))

    # task-0150 repair 1: when 40-character entries still do not fit, only a count line stays,
    # and when that does not fit either, no owner review line is added at all.
    def owner_review_part(line: str) -> bool:
        return line.startswith(("- 확인 대기", "- 외 ")) or ("개 검사는 모두 통과했지만" in line and line.startswith("- QA "))

    # task-0151 repair 1: the accept choice is placed first, so the count-line regime starts earlier.
    counted = bot._format_reply(dict(many, worktree="C:/" + "w" * 560))
    check("owner review reply: past the minimum width only the count line stays, within 2000",
          len(counted) <= 2000 and "- 확인 대기 12건: Discord 메시지 길이 제한으로 항목 내용을 생략했습니다" in counted
          and "확인 대기 1/12" not in counted and "- 외 " not in counted and "개 검사는 모두 통과했지만" in counted,
          f"{len(counted)}:{counted[-400:]}")
    bare = bot._format_reply(dict(many, worktree="C:/" + "w" * 700))
    check("owner review reply: when even the count line does not fit, no owner review line is added",
          len(bare) <= 2000 and not any(owner_review_part(line) for line in bare.splitlines()), f"{len(bare)}")
    overflow = [length for length in range(0, 2001, 25)
                for reply in [bot._format_reply(dict(many, worktree="C:/" + "w" * length))]
                if len("\n".join(line for line in reply.splitlines() if not owner_review_part(line))) <= 2000 < len(reply)]
    check("owner review reply: the added lines never push a reply that fits over 2000", overflow == [], str(overflow))

    # task-0151 repair 1: the accept choice is always offered; the owner review lines give way to it.
    accept_choice = f"`/go {long_id} accept` 확인을 마친 candidate 반영"
    check("accept choice: offered beside 5 long entries within 2000", accept_choice in reply and "- 확인 대기 5/12:" in reply
          and len(reply) <= 2000, f"{len(reply)}")
    missing = [length for length in range(0, 2001, 25)
               if accept_choice not in bot._format_reply(dict(many, worktree="C:/" + "w" * length))]
    check("accept choice: never dropped, whatever the length of the other lines", missing == [], str(missing))
    check("accept choice: the count-line and no-review-line replies keep it", accept_choice in counted and accept_choice in bare)
    retryable = bot._format_reply(dict(many, stage="accept", reason="accept_qa_failed", detail="tests_rerun", accept_retryable=True))
    check("accept choice: offered after an accept refusal that kept the record", accept_choice in retryable and len(retryable) <= 2000)

    # Unchanged: the success reply and other failure replies, even when unverified entries are present.
    common = {"result_type": "work_result", "task_id": "task-8000-x", "reviewer_unverified": ["{item: a, qa: none}"]}
    success = dict(common, ok=True, changed_files=["apps/studyroom/content/glossary.json"], test_summary="5/5",
                   reviewer_verdict="PASS", qa_checks={"a": True}, repairs=0, resumed_from="", candidate="c" * 40, checkpoint="d" * 40)
    check("owner review reply: success reply unchanged", bot._format_reply(success) == (
        "✅ 완료: task-8000-x\n- 변경 파일: apps/studyroom/content/glossary.json\n- 테스트: 5/5\n- Reviewer: PASS\n"
        "- QA: PASS (1개 검사)\n- 자동 repair: 0회\n- candidate: ccccccc / checkpoint: ddddddd\n- push: 하지 않음"))
    for reason in ("qa_failed", "scope_violation", "reviewer_findings"):
        failed = dict(common, ok=False, stage="qa", reason=reason, detail="tests_rerun", candidate="c" * 40,
                      candidates=["c" * 40], branch="jarvis/task-8000-x", repairs=1, worktree="W")
        check(f"owner review reply: {reason} failure reply unchanged", bot._format_reply(failed) == (
            f"❌ 실패: task-8000-x — 단계 `qa`, 사유 `{reason}`\n- 상세: tests_rerun\n"
            "- candidate: ccccccc (브랜치 jarvis/task-8000-x 보존, 자동 repair 1회)\n- main은 변경되지 않았고 push도 없습니다.\n"
            "다음 선택지: `/go task-8000-x` 처음부터 재시도 · `/go task-8000-x resume` 이 시도에서 이어가기 · "
            "`/status task-8000-x` 상태 확인 · 직접 개입(worktree W)"))


def main() -> int:
    claude_worker.CLAUDE_BIN = "fakeclaude"
    claude_worker.WORKER_TIMEOUT_SECONDS = 5
    tmp = Path(tempfile.mkdtemp(prefix="jarvis_worker_smoke_"))
    owner_review_results: dict[str, dict] = {}
    try:
        clone, fake_dir = make_env(tmp)
        os.environ["PATH"] = str(fake_dir) + os.pathsep + os.environ["PATH"]
        worktrees = tmp / "worktrees"

        r, calls, before, after = run_case("success", clone, worktrees, worker="ok")
        check("success: ok and stage done", r.ok and r.stage == "done", f"{r.stage}:{r.reason}:{r.detail}")
        check("success: only allowed files changed", r.changed_files == ["apps/studyroom/content/glossary.json"], str(r.changed_files))
        check("success: reviewer PASS and all QA checks", r.reviewer_verdict == "PASS" and r.qa_checks and all(r.qa_checks.values()), str(r.qa_checks))
        check("success: main advanced by candidate + checkpoint", git(["rev-list", "--count", f"{before}..{after}"], clone) == "2")
        check("success: checkpoint is HEAD and candidate is its parent", r.checkpoint == after and git(["rev-parse", f"{after}^"], clone) == r.candidate)
        check("success: task recorded as success", calls == [(True, calls[0][1])] if calls else False)
        check("success: worktree and branch cleaned", not Path(r.worktree).exists() and not git(["branch", "--list", r.branch], clone))

        def expect_fail(name: str, worker: str, stage: str, reason: str, review: str = "pass", prepare=None):
            r, calls, before, after = run_case(name, clone, worktrees, worker=worker, review=review, prepare=prepare)
            check(f"{name}: stopped at {stage}/{reason}", (not r.ok) and r.stage == stage and r.reason == reason, f"{r.stage}:{r.reason}:{r.detail}")
            if reason != "baseline_moved":
                check(f"{name}: main unchanged", before == after)
            check(f"{name}: task recorded as failure", bool(calls) and calls[-1][0] is False)
            check(f"{name}: failure record stays stage:reason (task-0151)", bool(calls) and calls[-1][1] == f"{stage}:{reason}",
                  calls[-1][1] if calls else "")
            return r

        expect_fail("scope", "scope", "scope", "scope_violation")
        expect_fail("jarvisbat", "jarvisbat", "scope", "scope_violation")
        expect_fail("timeout", "timeout", "worker", "worker_timeout")
        expect_fail("workerfail", "fail", "worker", "worker_failed")
        expect_fail("tests", "badjson", "tests", "tests_failed")
        r = expect_fail("findings", "ok", "reviewer", "reviewer_findings", review="findings")
        check("findings: branch kept for inspection", bool(git(["branch", "--list", r.branch], clone)))

        def dirty(c: Path) -> None:
            (c / "README.md").write_text((c / "README.md").read_text(encoding="utf-8") + "x\n", encoding="utf-8")

        expect_fail("dirty", "ok", "preflight", "main_tree_dirty", prepare=dirty)
        git(["checkout", "--", "README.md"], clone)

        # task-0157: /go writes the approval transition into the task's own record before the run. A record
        # that is already committed then shows as a tracked change; only that one file is exempt.
        def tracked_record(task_id: str, extra=None):
            def prepare(c: Path) -> None:
                git(["add", "--", f"memory/tasks/{task_id}.md"], c)
                git(["commit", "-q", "-m", f"track {task_id}"], c)
                record = c / "memory" / "tasks" / f"{task_id}.md"
                record.write_text(record.read_text(encoding="utf-8") + "- status: `DOING`\n", encoding="utf-8")
                if extra:
                    extra(c)
            return prepare

        r, calls, before, after = run_case("trackedrecord", clone, worktrees, worker="ok",
                                           prepare=tracked_record("task-8000-trackedrecord"))
        check("tracked record: a committed, changed own record passes preflight and integrate", r.ok and r.stage == "done",
              f"{r.stage}:{r.reason}:{r.detail}")
        check("tracked record: checkpoint commits the changed record, main is candidate + checkpoint",
              r.checkpoint == after and git(["rev-list", "--count", f"{before}..{after}"], clone) == "2"
              and "- status: `DOING`" in git(["show", f"{after}:memory/tasks/task-8000-trackedrecord.md"], clone)
              and not git(["status", "--porcelain", "--untracked-files=no"], clone))

        r = expect_fail("trackedother", "ok", "preflight", "main_tree_dirty",
                        prepare=tracked_record("task-8000-trackedother", extra=dirty))
        check("tracked record: the exemption covers only the own record, not README.md",
              "README.md" in git(["status", "--porcelain", "--untracked-files=no"], clone))
        git(["checkout", "--", "README.md", "memory/tasks/task-8000-trackedother.md"], clone)

        def other_record(c: Path) -> None:
            git(["add", "--", "memory/tasks/task-8000-trackedrecord.md"], c)
            (c / "memory" / "tasks" / "task-8000-trackedrecord.md").write_text("# another task's record\n", encoding="utf-8")

        expect_fail("trackedneighbour", "ok", "preflight", "main_tree_dirty", prepare=other_record)
        git(["checkout", "--", "memory/tasks/task-8000-trackedrecord.md"], clone)

        expect_fail("trackedintegrate", "ok", "integrate", "main_tree_dirty", review="dirtymain",
                    prepare=tracked_record("task-8000-trackedintegrate"))
        git(["checkout", "--", "README.md", "memory/tasks/task-8000-trackedintegrate.md"], clone)

        run_case("trackedresume", clone, worktrees, worker="ok", review="findings", task_id="task-8000-trackedresume")
        r, *_ = run_case("trackedresume", clone, worktrees, worker="fail", resume=True, task_id="task-8000-trackedresume",
                         prepare=tracked_record("task-8000-trackedresume"))
        check("tracked record: resume with a committed, changed own record integrates", r.ok
              and r.resumed_from == "jarvis/task-8000-trackedresume", f"{r.stage}:{r.reason}:{r.resumed_from}")
        expect_fail("moved", "ok", "integrate", "baseline_moved", review="move")

        # task-0143 follow-up: evidence paths reach the Reviewer, retries keep earlier attempts.
        r, *_ = run_case("evidence", clone, worktrees, worker="ok", review="needevidence",
                         request="Studyroom glossary에 용어 1개 추가 (jarvis_example은 task-0142 기록에 있는 사실만)")
        check("evidence: Reviewer received the exact task-0142 record path", r.ok and r.reviewer_verdict == "PASS", f"{r.stage}:{r.reason}")
        r, *_ = run_case("noevidence", clone, worktrees, worker="ok", review="needevidence")
        check("evidence: no task reference, no evidence block", (not r.ok) and r.reason == "reviewer_findings")
        old = run_case("keep", clone, worktrees, worker="ok", review="findings")[0]
        new = run_case("keep", clone, worktrees, worker="ok", task_id="task-8000-keep")[0]
        check("retry: new attempt succeeds under a new name", new.ok and new.branch == "jarvis/task-8000-keep-r2", f"{new.branch}:{new.stage}:{new.reason}")
        check("retry: earlier candidate branch and worktree preserved", bool(git(["branch", "--list", old.branch], clone)) and Path(old.worktree).exists()
              and git(["rev-parse", old.branch], clone) == old.candidate)
        # task-0144: automatic repair (budget 1) and /go resume.
        log = worktrees.parent / "fake.log"
        os.environ["FAKE_LOG"] = str(log)
        os.environ["FAKE_STATE"] = str(worktrees.parent / "fake.state")
        log.write_text("", encoding="utf-8")
        r, calls, before, after = run_case("repairpass", clone, worktrees, worker="ok", review="once")
        check("repair: FINDINGS -> 1 repair -> PASS", r.ok and r.repairs == 1 and len(r.candidates) == 2, f"{r.stage}:{r.reason}:{r.detail}")
        check("repair: repair candidate's parent is the first candidate", git(["rev-parse", f"{r.candidates[1]}^"], clone) == r.candidates[0] if len(r.candidates) == 2 else False)
        text = log.read_text(encoding="utf-8")
        check("repair: Worker got the Reviewer report verbatim", "This is a repair." in text and "verdict: FINDINGS" in text)
        check("repair: fresh Reviewer names the previous candidate as parent", "fresh review after repair 1" in text and f"Parent: {r.candidates[0]}" in text if r.candidates else False)
        n = git(["rev-list", "--count", f"{before}..{after}"], clone)
        check("repair: main advanced by first candidate, repair candidate, checkpoint", n == "3", n)

        r = run_case("repairexhausted", clone, worktrees, worker="ok", review="findings")[0]
        check("repair: second FINDINGS stops with budget exhausted", (not r.ok) and r.reason == "reviewer_findings" and r.repairs == 1
              and "exhausted" in r.detail and len(r.candidates) == 2, f"{r.stage}:{r.reason}:{r.repairs}:{r.detail}")
        exhausted = r

        r = run_case("repairscope", clone, worktrees, worker="scope_on_repair", review="findings")[0]
        check("repair: scope violation during repair fails", (not r.ok) and r.stage == "scope" and r.reason == "scope_violation" and r.repairs == 1)

        r = run_case("resumenone", clone, worktrees, worker="ok", resume=True)[0]
        check("resume: no previous attempt is refused before any worktree", (not r.ok) and r.reason == "resume_no_previous_attempt"
              and not (worktrees / "task-8000-resumenone").exists())

        # Previous attempt = the exhausted run. Add an uncommitted fix there and move main in another file.
        prev_wt = Path(exhausted.worktree)
        glossary = prev_wt / "apps/studyroom/content/glossary.json"
        data = json.loads(glossary.read_text(encoding="utf-8"))
        data.append({"id": "resumed-term", "term": "Resumed", "dev_definition": "d", "simple_explanation": "s", "jarvis_example": "e"})
        glossary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (clone / "docs" / "moved-main.md").write_text("x\n", encoding="utf-8")
        git(["add", "docs/moved-main.md"], clone)
        git(["commit", "-q", "-m", "move main"], clone)
        r, calls, before, after = run_case("resume", clone, worktrees, worker="fail", resume=True, task_id="task-8000-repairexhausted")
        check("resume: previous changes re-applied on current main without calling the Worker", r.ok and r.resumed_from == exhausted.branch
              and r.baseline == before, f"{r.stage}:{r.reason}:{r.detail}")
        check("resume: candidate carries the uncommitted fix", "resumed-term" in git(["show", f"{r.candidate}:apps/studyroom/content/glossary.json"], clone) if r.candidate else False)
        check("resume: previous attempt branch, candidate and worktree preserved", prev_wt.exists()
              and git(["rev-parse", exhausted.branch], clone) == exhausted.candidate and "resumed-term" in glossary.read_text(encoding="utf-8"))

        old = run_case("conflictprev", clone, worktrees, worker="ok", review="findings")[0]
        g = clone / "apps/studyroom/content/glossary.json"
        g.write_text(g.read_text(encoding="utf-8").replace('"Fake"', '"Fake2"', 1), encoding="utf-8")
        git(["commit", "-q", "-am", "main changes glossary"], clone)
        r = run_case("conflict", clone, worktrees, worker="ok", resume=True, task_id="task-8000-conflictprev")[0]
        check("resume: same file changed on main is refused", (not r.ok) and r.reason == "resume_conflict", f"{r.stage}:{r.reason}")
        check("resume: a refused resume leaves no new attempt behind", not (worktrees / "task-8000-conflictprev-r2").exists()
              and not git(["branch", "--list", "jarvis/task-8000-conflictprev-r2"], clone))
        for mode, reason in (("blocked", "reviewer_blocked"), ("garbage", "reviewer_unknown"), ("crashfindings", "reviewer_unknown")):
            r = run_case(f"verdict{mode}", clone, worktrees, worker="ok", review=mode)[0]
            check(f"repair: {mode} verdict fails without a repair", (not r.ok) and r.reason == reason and r.repairs == 0, f"{r.reason}:{r.repairs}")
        capped = run_case("budgetcap", clone, worktrees, worker="ok", review="findings", repair_budget=5)[0]
        check("repair: a requested budget of 5 is capped at 1", capped.repairs == 1 and len(capped.candidates) == 2 and "budget 1 exhausted" in capped.detail, f"{capped.repairs}:{capped.detail}")

        # task-0145: Owner request verbatim, no unverifiable claims, non-repairable FINDINGS escalate.
        log.write_text("", encoding="utf-8")
        run_case("summarycall", clone, worktrees, worker="ok")
        text = log.read_text(encoding="utf-8")
        check("summary: Reviewer call quotes the Owner request verbatim",
              "Owner condition (verbatim, the only one): Studyroom glossary에 용어 1개 추가" in text)
        check("summary: pipeline limit is separate from the Owner condition and names the change set",
              "Pipeline limit, not an Owner condition" in text and "(check with git diff --name-status): apps/studyroom/content/glossary.json" in text)
        check("summary: no Worker, test or pipeline-behaviour claims", "smoke tests passed" not in text and "No commands, no commit" not in text
              and "Content must use only facts confirmed" not in text and "refuses" not in text and "re-runs the tests" not in text)
        log.write_text("", encoding="utf-8")
        r = run_case("summaryonly", clone, worktrees, worker="ok", review="summaryonly")[0]
        text = log.read_text(encoding="utf-8")
        check("not repairable: summary-only FINDINGS fail without a repair", (not r.ok) and r.stage == "reviewer"
              and r.reason == "reviewer_findings_not_repairable" and r.repairs == 0 and len(r.candidates) == 1, f"{r.stage}:{r.reason}:{r.repairs}")
        check("not repairable: the repair Worker was never called", text.count("WORKER\n") == 1 and "This is a repair." not in text)
        log.write_text("", encoding="utf-8")
        Path(os.environ["FAKE_STATE"]).unlink(missing_ok=True)
        r = run_case("mixed", clone, worktrees, worker="ok", review="mixedonce")[0]
        text = log.read_text(encoding="utf-8")
        check("mixed: content + summary FINDINGS -> 1 repair -> PASS", r.ok and r.repairs == 1, f"{r.stage}:{r.reason}:{r.detail}")
        check("mixed: repair prompt limits the Worker to findings on the changed files",
              "Candidate changed files: apps/studyroom/content/glossary.json" in text and "Ignore findings about the Manager summary" in text)
        r3_like = ("verdict: FINDINGS\nfindings:       - {severity: minor, evidence: the verbatim approval states x, but the Manager summary "
                   "states y, impact: z, minimum_correction: state the bound in apps/studyroom/content/glossary.json}\n"
                   "                - {severity: minor, evidence: Manager summary rows 2 and 4 assert tests passed, impact: z, minimum_correction: w}\n"
                   "note: n")
        files = ["apps/studyroom/content/glossary.json"]
        check("classify: task-0143 r3 shaped findings are not repairable", not claude_worker.findings_repairable(r3_like, files))
        check("classify: evidence on a changed file is repairable",
              claude_worker.findings_repairable("findings: - {severity: major, evidence: apps/studyroom/content/glossary.json:5 wrong, impact: z}", files))
        check("classify: unknown report shape stays repairable", claude_worker.findings_repairable("verdict: FINDINGS\nsomething is off", files))

        # task-0148: unverified and self_deviations are separate from findings.
        r = run_case("unverifiedpass", clone, worktrees, worker="ok", review="unverifiedpass")[0]
        check("fields: unverified alone gives a Reviewer-stage PASS, recorded, not a verdict", r.reviewer_verdict == "PASS"
              and len(r.reviewer_unverified) == 1 and r.repairs == 0, f"{r.stage}:{r.reason}:{r.reviewer_unverified}")
        check("fields: a Reviewer-stage PASS with unverified still goes through all QA checks", r.ok and len(r.qa_checks) == 6
              and all(r.qa_checks.values()), f"{r.stage}:{r.reason}:{r.qa_checks}")
        log.write_text("", encoding="utf-8")
        Path(os.environ["FAKE_STATE"]).unlink(missing_ok=True)
        r = run_case("deviateonce", clone, worktrees, worker="ok", review="deviateonce")[0]
        text = log.read_text(encoding="utf-8")
        check("fields: self_deviations -> one review retry -> PASS, no repair", r.ok and r.reviewer_retries == 1 and r.repairs == 0
              and text.count("REVIEWER\n") == 2 and "This is a repair." not in text, f"{r.stage}:{r.reason}:{r.reviewer_retries}")
        log.write_text("", encoding="utf-8")
        r = run_case("deviatealways", clone, worktrees, worker="ok", review="deviatealways")[0]
        text = log.read_text(encoding="utf-8")
        check("fields: self_deviations again after the retry fails as reviewer_self_deviation", (not r.ok) and r.stage == "reviewer"
              and r.reason == "reviewer_self_deviation" and r.reviewer_retries == 1, f"{r.stage}:{r.reason}:{r.reviewer_retries}")
        check("fields: that failure never spends the repair budget", r.repairs == 0 and len(r.candidates) == 1
              and text.count("REVIEWER\n") == 2 and "This is a repair." not in text)
        report = ("verdict: FINDINGS\nfindings:       - {severity: minor, evidence: the Manager summary omits a condition, impact: x, minimum_correction: y}\n"
                  "unverified:     - {item: apps/studyroom/content/glossary.json passes the smoke tests, not_run: python}\n"
                  "self_deviations: []\n\nnote: n")
        check("fields: findings end where unverified starts", len(claude_worker._split_findings(report)) == 1
              and claude_worker.report_field(report, "unverified") and claude_worker.report_field(report, "self_deviations") == [])
        check("fields: a changed file named only under unverified does not make findings repairable",
              not claude_worker.findings_repairable(report, files))
        check("classify: a finding on a fact outside the named record (task-0146 shape) stays repairable",
              claude_worker.findings_repairable("findings: - {severity: minor, evidence: apps/studyroom/content/glossary.json:336 states a clause "
                                                "the task-0142 record does not have, impact: x, minimum_correction: y}", files))
        for mode in ("unverifiednone", "unverifiedbadqa", "unverifiednoqa"):
            r, calls, before, after = run_case(mode, clone, worktrees, worker="ok", review=mode)
            check(f"qa pairing: {mode} passes QA but stops for the Owner, main untouched", (not r.ok) and r.stage == "qa"
                  and r.reason == "qa_unverified_owner_review" and all(r.qa_checks.values()) and before == after
                  and "the new term matches" in r.detail and "Studyroom smoke tests" not in r.detail
                  and git(["rev-parse", r.branch], clone) == r.candidate, f"{r.stage}:{r.reason}:{r.detail}")
            check(f"qa pairing: {mode} records FAILED, not DONE", bool(calls) and calls[-1][0] is False)
            check(f"qa pairing: {mode} failure record names candidate, baseline and attempt (task-0151)", bool(calls)
                  and calls[-1][1] == claude_worker.owner_review_record(r.candidate, r.baseline, attempt_of(f"task-8000-{mode}", r.branch)),
                  calls[-1][1] if calls else "")
            owner_review_results[mode] = {"result_type": "work_result", **r.to_dict()}
        # task-0148 repair 2: a missing or malformed field is unclassifiable, never "no entries".
        for mode in ("nounverified", "badunverified"):
            r, calls, before, after = run_case(mode, clone, worktrees, worker="ok", review=mode)
            check(f"fail closed: {mode} stops for the Owner after QA, main untouched", (not r.ok) and r.stage == "qa"
                  and r.reason == "qa_unverified_owner_review" and "unverified field missing or malformed" in r.detail
                  and all(r.qa_checks.values()) and before == after and bool(calls) and calls[-1][0] is False,
                  f"{r.stage}:{r.reason}:{r.detail}")
            owner_review_results[mode] = {"result_type": "work_result", **r.to_dict()}
        log.write_text("", encoding="utf-8")
        r = run_case("noselfdev", clone, worktrees, worker="ok", review="noselfdev")[0]
        text = log.read_text(encoding="utf-8")
        check("fail closed: a missing self_deviations field is an invalid review, retried once, then reviewer_self_deviation",
              (not r.ok) and r.reason == "reviewer_self_deviation" and r.reviewer_retries == 1 and r.repairs == 0
              and "missing or malformed" in r.detail and text.count("REVIEWER\n") == 2 and "This is a repair." not in text,
              f"{r.stage}:{r.reason}:{r.reviewer_retries}:{r.detail}")
        log.write_text("", encoding="utf-8")
        Path(os.environ["FAKE_STATE"]).unlink(missing_ok=True)
        r = run_case("badselfdevonce", clone, worktrees, worker="ok", review="badselfdevonce")[0]
        text = log.read_text(encoding="utf-8")
        check("fail closed: a malformed self_deviations field is retried once and a clean review proceeds",
              r.ok and r.reviewer_retries == 1 and r.repairs == 0 and text.count("REVIEWER\n") == 2, f"{r.stage}:{r.reason}")
        check("fail closed: `[]` is an empty list, a missing field is None",
              claude_worker.report_field("unverified: []\nself_deviations: []", "unverified") == []
              and claude_worker.report_field("self_deviations: []", "unverified") is None
              and claude_worker.report_field("unverified: {item: x}\nself_deviations: []", "unverified") is None)
        call = claude_worker.reviewer_call(task_id="t", candidate="c", baseline="b", changed_files=["f"], request="r",
                                           approval_command="/go t")
        check("qa pairing: the Reviewer call names every pipeline QA check",
              all(f"- {name}: " in call for name in claude_worker.QA_CHECKS) and "use these names for `qa`" in call)
        prompt = claude_worker.worker_prompt("task-8000-x", "req")
        check("worker prompt: facts only from the source the request names, history cited as history",
              "use only facts stated in that source" in prompt and "cite them as what the record says" in prompt
              and "Describe current behavior only from source code" in prompt and "(memory/tasks, docs, git-tracked" not in prompt)
        os.environ.pop("FAKE_LOG", None)
        check("worktree root is outside the clone", not str(worktrees.resolve()).startswith(str(clone.resolve())))
        bot_flow(clone, worktrees)
        owner_review_replies(owner_review_results)
        accept_flow(clone, worktrees)
        attempt_numbering(clone, worktrees)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"total={len(RESULTS)} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
