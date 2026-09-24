"""Smoke tests for the Jarvis v0.2 Claude Worker pipeline (task-0142).

Runs the real pipeline against a throwaway local clone of this repository with a
fake `claude` executable, so no model, network or credential is involved. Each
case checks where the run stopped and that main, push state and jarvis.bat stay
untouched.
"""

from __future__ import annotations

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
    sys.stdin.read()
    if "--agent" in args:
        mode = os.environ.get("FAKE_REVIEW", "pass")
        if mode == "move":
            subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "moved"], check=True)
            mode = "pass"
        verdict = "PASS" if mode == "pass" else "FINDINGS"
        body = "findings: []" if mode == "pass" else "findings: - {severity: major, evidence: fake}"
        print(json.dumps({"result": f"candidate_hash: x\\nverdict: {verdict}\\n{body}"}))
        sys.exit(0)
    mode = os.environ.get("FAKE_WORKER", "ok")
    if mode == "timeout":
        time.sleep(30)
    if mode == "fail":
        print("boom", file=sys.stderr)
        sys.exit(3)
    if mode == "scope":
        Path("docs/should-not-change.md").write_text("x\\n", encoding="utf-8")
    elif mode == "jarvisbat":
        Path("jarvis.bat").write_text("echo x\\n", encoding="utf-8")
    elif mode == "badjson":
        Path("apps/studyroom/content/glossary.json").write_text("{not json", encoding="utf-8")
    elif mode == "ok":
        p = Path("apps/studyroom/content/glossary.json")
        data = json.loads(p.read_text(encoding="utf-8"))
        data.append({"id": "fake-term", "term": "Fake", "dev_definition": "d", "simple_explanation": "s", "jarvis_example": "e"})
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


def run_case(name: str, clone: Path, worktrees: Path, *, worker: str, review: str = "pass", prepare=None):
    os.environ["FAKE_WORKER"] = worker
    os.environ["FAKE_REVIEW"] = review
    task_id = f"task-8000-{name}"
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
        request="Studyroom glossary에 용어 1개 추가",
        approval_command=f"/go {task_id}",
        repo_root=clone,
        worktree_root=worktrees,
        record_result=record,
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

        check("worktree root is outside the clone", not str(worktrees.resolve()).startswith(str(clone.resolve())))
        bot_flow(clone, worktrees)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"total={len(RESULTS)} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
