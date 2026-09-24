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
        if mode in ("once", "mixedonce"):
            state = Path(os.environ["FAKE_STATE"])
            mode = "pass" if state.exists() else ("findings" if mode == "once" else "mixed")
            state.write_text("seen", encoding="utf-8")
        summary_item = ("- {severity: minor, evidence: the Manager summary restates the approval more broadly, impact: x, "
                        "minimum_correction: name the term in apps/studyroom/content/glossary.json in the summary}")
        content_item = "- {severity: major, evidence: apps/studyroom/content/glossary.json adds an unsupported fact, impact: x, minimum_correction: y}"
        if mode in ("summaryonly", "mixed"):
            items = [summary_item, summary_item] if mode == "summaryonly" else [summary_item, content_item]
            print(json.dumps({"result": "candidate_hash: x\\nverdict: FINDINGS\\nfindings: " + "\\n  ".join(items) + "\\nnote: n"}))
            sys.exit(0)
        if mode == "needevidence":
            mode = "pass" if "Evidence paths" in prompt and "- memory/tasks/task-0142-" in prompt else "findings"
        if mode in ("blocked", "garbage"):
            print(json.dumps({"result": "verdict: BLOCKED" if mode == "blocked" else "no verdict here"}))
            sys.exit(0)
        verdict = "PASS" if mode == "pass" else "FINDINGS"
        body = "findings: []" if mode == "pass" else "findings: " + content_item
        print(json.dumps({"result": f"candidate_hash: x\\nverdict: {verdict}\\n{body}"}))
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
    bot._audit_execution_result = lambda **kw: audits.append("execution") or None
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
    check("bot: /go resume on a non-FAILED task is refused", bot._run_command(f"/go {task_id} resume").get("reason", "").startswith(("resume_requires_failed", "status_not_startable")))
    check("bot: /go with an unknown argument is a usage error", bot._run_command(f"/go {task_id} again").get("reason") == "usage:/go <task-id> [resume]")
    check("bot: finished task is not startable again", bot._run_command(f"/go {task_id}").get("reason") == "status_not_startable:DONE")


def main() -> int:
    claude_worker.CLAUDE_BIN = "fakeclaude"
    claude_worker.WORKER_TIMEOUT_SECONDS = 5
    tmp = Path(tempfile.mkdtemp(prefix="jarvis_worker_smoke_"))
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
        check("summary: no Worker or test claims", "smoke tests passed" not in text and "No commands, no commit" not in text
              and "Content must use only facts confirmed" not in text)
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
        os.environ.pop("FAKE_LOG", None)
        check("worktree root is outside the clone", not str(worktrees.resolve()).startswith(str(clone.resolve())))
        bot_flow(clone, worktrees)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"total={len(RESULTS)} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
