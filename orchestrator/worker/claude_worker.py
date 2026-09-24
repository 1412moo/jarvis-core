"""Jarvis v0.2 minimal Claude Worker pipeline (task-0142).

One Owner-approved Studyroom content change, run end to end without a person in
the terminal:

    isolated git worktree -> Claude Code worker -> tests -> candidate commit
    -> Reviewer (claude --agent reviewer) -> deterministic QA
    -> ff-only onto main (only if main is still at the baseline) -> task result
    -> checkpoint commit

Boundaries, all enforced here rather than trusted to the model:
- The worker runs in a worktree outside the repository, never in the main tree.
- The worker has no Bash: it can read and edit files, nothing else.
- Only files under ALLOWED_PREFIX may change; anything else fails the run.
- jarvis.bat is never read, staged or committed.
- Nothing is pushed. No external API or credential is used by this module.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKTREE_ROOT = Path(
    os.environ.get("JARVIS_WORKTREE_ROOT", str(REPO_ROOT.parent / "jarvis-core-worktrees"))
)
CLAUDE_BIN = os.environ.get("JARVIS_CLAUDE_BIN", "claude")

# The one supported kind of work in this slice.
WORK_KIND = "studyroom_content"
ALLOWED_PREFIX = "apps/studyroom/content/"
TEST_COMMAND = (sys.executable, "-B", "apps/studyroom/run_smoke_tests.py")
PROTECTED_PATHS = frozenset({"jarvis.bat"})

WORKER_TIMEOUT_SECONDS = int(os.environ.get("JARVIS_WORKER_TIMEOUT", "900"))
REVIEWER_TIMEOUT_SECONDS = int(os.environ.get("JARVIS_REVIEWER_TIMEOUT", "900"))
TEST_TIMEOUT_SECONDS = 300
GIT_TIMEOUT_SECONDS = 60

WORKER_ALLOWED_TOOLS = "Read,Edit,Write,Glob,Grep"
WORKER_DISALLOWED_TOOLS = "Bash,NotebookEdit,WebFetch,WebSearch"
REVIEWER_ALLOWED_TOOLS = (
    "Read",
    "Grep",
    "Glob",
    "Bash(git rev-parse:*)",
    "Bash(git cat-file:*)",
    "Bash(git log:*)",
    "Bash(git show:*)",
    "Bash(git diff:*)",
    "Bash(git grep:*)",
    "Bash(git status:*)",
)
VERDICT_PATTERN = re.compile(r"^\s*verdict:\s*(PASS|FINDINGS|BLOCKED)\b", re.MULTILINE)


@dataclass
class WorkerRunResult:
    task_id: str
    ok: bool = False
    stage: str = "preflight"
    reason: str = ""
    detail: str = ""
    baseline: str = ""
    branch: str = ""
    worktree: str = ""
    candidate: str = ""
    checkpoint: str = ""
    changed_files: list[str] = field(default_factory=list)
    test_summary: str = ""
    reviewer_verdict: str = ""
    reviewer_excerpt: str = ""
    qa_checks: dict[str, bool] = field(default_factory=dict)
    pushed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class StageFailure(Exception):
    def __init__(self, stage: str, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.stage = stage
        self.reason = reason
        self.detail = detail


def _run(
    args: list[str] | tuple[str, ...],
    *,
    cwd: Path,
    timeout: int,
    stdin_text: str | None = None,
) -> subprocess.CompletedProcess:
    """Run one process; on timeout kill its whole tree (claude.cmd spawns node)."""

    proc = subprocess.Popen(
        list(args),
        cwd=str(cwd),
        stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        out, err = proc.communicate(input=stdin_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
                check=False,
            )
        else:
            proc.kill()
        proc.communicate()
        raise
    return subprocess.CompletedProcess(proc.args, proc.returncode, out or "", err or "")


def _git(args: list[str], cwd: Path) -> str:
    completed = _run(["git", *args], cwd=cwd, timeout=GIT_TIMEOUT_SECONDS)
    if completed.returncode != 0:
        raise StageFailure("git", "git_failed", f"git {' '.join(args[:2])}: {completed.stderr.strip()[:200]}")
    return completed.stdout.strip()


def _claude_command() -> list[str]:
    resolved = shutil.which(CLAUDE_BIN)
    if resolved is None:
        raise StageFailure("worker", "claude_not_found", CLAUDE_BIN)
    return [resolved]


def _changed_paths(worktree: Path) -> list[str]:
    # Not _git(): its strip() would eat the leading status column of the first line.
    completed = _run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=worktree, timeout=GIT_TIMEOUT_SECONDS)
    if completed.returncode != 0:
        raise StageFailure("scope", "git_status_failed", completed.stderr.strip()[:200])
    paths = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.replace("\\", "/"))
    return sorted(set(paths))


def _scope_violations(paths: list[str]) -> list[str]:
    return [
        p
        for p in paths
        if p in PROTECTED_PATHS or not p.startswith(ALLOWED_PREFIX) or ".." in p.split("/")
    ]


def _run_tests(worktree: Path) -> tuple[bool, str]:
    try:
        completed = _run(TEST_COMMAND, cwd=worktree, timeout=TEST_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return False, "tests_timeout"
    tail = (completed.stdout.strip().splitlines() or [""])[-2:]
    return completed.returncode == 0, " ".join(line.strip("= ") for line in tail).strip()[:200]


def worker_prompt(task_id: str, request: str) -> str:
    return (
        f"You are the Jarvis-Core Implementer for {task_id}.\n"
        f"Owner request (verbatim): {request}\n\n"
        "Rules:\n"
        f"- Change only files under {ALLOWED_PREFIX}. Keep each JSON file's existing schema and formatting "
        "(2-space indent, UTF-8, ensure_ascii off). Keep existing entries unchanged.\n"
        "- Use only facts you can confirm by reading files in this repository (memory/tasks, docs, git-tracked "
        "sources). Do not invent facts.\n"
        "- Never read, open or change jarvis.bat or any .env file.\n"
        "- Do not run commands, do not commit, do not push. Only edit files.\n"
        "- When done, reply with one short line naming the file(s) you changed."
    )


def reviewer_call(
    *,
    task_id: str,
    candidate: str,
    baseline: str,
    changed_files: list[str],
    request: str,
    approval_command: str,
) -> str:
    scope = "\n".join(f"- {p}" for p in changed_files)
    return (
        f"Review request from Manager (the caller): {task_id}, first review of this candidate "
        "(Jarvis v0.2 worker pipeline).\n\n"
        f"Candidate commit (full hash): {candidate}\n"
        f"Parent: {baseline}\n"
        f"Baseline (full hash): {baseline}\n\n"
        f"File scope:\n{scope}\n\n"
        "Never access `jarvis.bat`.\n\n"
        "=== COMMAND FORM REQUIREMENT ===\n"
        'Follow the "Allowed commands" section of your own definition exactly as written.\n\n'
        "=== MANAGER SUMMARY ===\n"
        f"| 1 | Owner request | The worker changed only files under {ALLOWED_PREFIX} to satisfy the request. |\n"
        "| 2 | Worker limits | No commands, no commit, no push by the worker; the pipeline committed the candidate. |\n"
        "| 3 | Facts | Content must use only facts confirmed in this repository. |\n"
        "| 4 | Tests | Studyroom smoke tests passed in the isolated worktree before this call. |\n\n"
        "=== OWNER APPROVAL (verbatim) ===\n"
        f"/work {request}\n"
        f"{approval_command}\n"
    )


def _ensure_outside_repo(path: Path, repo_root: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return
    raise StageFailure("worktree", "worktree_inside_repo", str(resolved))


def run_pipeline(
    *,
    task_id: str,
    request: str,
    approval_command: str,
    repo_root: Path = REPO_ROOT,
    worktree_root: Path | None = None,
    record_result: Callable[[bool, str], tuple[bool, str]] | None = None,
) -> WorkerRunResult:
    """Run the whole slice once. Never raises; the result says where it stopped."""

    result = WorkerRunResult(task_id=task_id)
    worktree_root = worktree_root or WORKTREE_ROOT
    worktree = worktree_root / task_id
    branch = f"jarvis/{task_id}"
    result.branch = branch
    result.worktree = str(worktree)
    task_file = f"memory/tasks/{task_id}.md"
    try:
        # 1. Preflight: main is on main and clean (tracked files).
        result.stage = "preflight"
        if _git(["symbolic-ref", "--short", "HEAD"], repo_root) != "main":
            raise StageFailure("preflight", "main_not_checked_out")
        if _git(["status", "--porcelain", "--untracked-files=no"], repo_root):
            raise StageFailure("preflight", "main_tree_dirty")
        baseline = _git(["rev-parse", "HEAD"], repo_root)
        result.baseline = baseline

        # 2. Isolated worktree outside the repository.
        result.stage = "worktree"
        _ensure_outside_repo(worktree, repo_root)
        if worktree.exists():
            _git(["worktree", "remove", "--force", str(worktree)], repo_root)
        if _git(["branch", "--list", branch], repo_root):
            _git(["branch", "-D", branch], repo_root)
        worktree_root.mkdir(parents=True, exist_ok=True)
        _git(["worktree", "add", "-b", branch, str(worktree), baseline], repo_root)

        # 3. Worker.
        result.stage = "worker"
        try:
            completed = _run(
                [
                    *_claude_command(),
                    "-p",
                    "--output-format",
                    "json",
                    "--permission-mode",
                    "acceptEdits",
                    "--allowedTools",
                    WORKER_ALLOWED_TOOLS,
                    "--disallowedTools",
                    WORKER_DISALLOWED_TOOLS,
                ],
                cwd=worktree,
                timeout=WORKER_TIMEOUT_SECONDS,
                stdin_text=worker_prompt(task_id, request),
            )
        except subprocess.TimeoutExpired:
            raise StageFailure("worker", "worker_timeout", f"{WORKER_TIMEOUT_SECONDS}s")
        if completed.returncode != 0:
            raise StageFailure("worker", "worker_failed", (completed.stderr or completed.stdout).strip()[:200])

        # 4. Scope.
        result.stage = "scope"
        changed = _changed_paths(worktree)
        result.changed_files = changed
        if not changed:
            raise StageFailure("scope", "no_changes")
        violations = _scope_violations(changed)
        if violations:
            raise StageFailure("scope", "scope_violation", ", ".join(violations)[:200])

        # 5. Tests.
        result.stage = "tests"
        passed, summary = _run_tests(worktree)
        result.test_summary = summary
        if not passed:
            raise StageFailure("tests", "tests_failed", summary)

        # 6. Candidate commit on the worktree branch.
        result.stage = "candidate"
        _git(["add", "--", *changed], worktree)
        _git(
            ["commit", "-q", "-m", f"feat(studyroom): {task_id} Jarvis worker candidate\n\n{request[:300]}"],
            worktree,
        )
        candidate = _git(["rev-parse", "HEAD"], worktree)
        result.candidate = candidate

        # 7. Reviewer, pinned to the candidate, with the Owner text verbatim.
        result.stage = "reviewer"
        try:
            review = _run(
                [
                    *_claude_command(),
                    "-p",
                    "--agent",
                    "reviewer",
                    "--output-format",
                    "json",
                    "--allowedTools",
                    *REVIEWER_ALLOWED_TOOLS,
                ],
                cwd=repo_root,
                timeout=REVIEWER_TIMEOUT_SECONDS,
                stdin_text=reviewer_call(
                    task_id=task_id,
                    candidate=candidate,
                    baseline=baseline,
                    changed_files=changed,
                    request=request,
                    approval_command=approval_command,
                ),
            )
        except subprocess.TimeoutExpired:
            raise StageFailure("reviewer", "reviewer_timeout", f"{REVIEWER_TIMEOUT_SECONDS}s")
        review_text = review.stdout
        try:
            review_text = str(json.loads(review.stdout).get("result", review.stdout))
        except (json.JSONDecodeError, AttributeError):
            pass
        match = VERDICT_PATTERN.search(review_text)
        result.reviewer_verdict = match.group(1) if match else "UNKNOWN"
        findings = review_text.split("findings:", 1)[-1] if "findings:" in review_text else review_text
        result.reviewer_excerpt = " ".join(findings.split())[:300]
        if review.returncode != 0 or result.reviewer_verdict != "PASS":
            raise StageFailure("reviewer", f"reviewer_{result.reviewer_verdict.lower()}", result.reviewer_excerpt)

        # 8. QA: deterministic checks on the exact candidate.
        result.stage = "qa"
        qa: dict[str, bool] = {}
        qa["head_is_candidate"] = _git(["rev-parse", "HEAD"], worktree) == candidate
        diff_names = sorted(_git(["diff", "--name-only", baseline, candidate], repo_root).splitlines())
        qa["change_set_matches"] = diff_names == changed and not _scope_violations(diff_names)
        qa["diff_check"] = _run(["git", "diff", "--check", baseline, candidate], cwd=repo_root, timeout=GIT_TIMEOUT_SECONDS).returncode == 0
        qa["jarvis_bat_absent"] = not _git(["ls-tree", "-r", "--name-only", candidate, "--", "jarvis.bat"], repo_root)
        json_ok = True
        for path in changed:
            if path.endswith(".json"):
                try:
                    json.loads((worktree / path).read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    json_ok = False
        qa["json_valid"] = json_ok
        qa["tests_rerun"] = _run_tests(worktree)[0]
        result.qa_checks = qa
        if not all(qa.values()):
            raise StageFailure("qa", "qa_failed", ",".join(k for k, v in qa.items() if not v))

        # 9. Integrate: ff-only, and only if main has not moved.
        result.stage = "integrate"
        if _git(["rev-parse", "HEAD"], repo_root) != baseline:
            raise StageFailure("integrate", "baseline_moved")
        if _git(["status", "--porcelain", "--untracked-files=no"], repo_root):
            raise StageFailure("integrate", "main_tree_dirty")
        _git(["merge", "--ff-only", "-q", branch], repo_root)

        # 10. Task result (DOING -> DONE) and checkpoint commit.
        result.stage = "checkpoint"
        if record_result is not None:
            applied, why = record_result(True, f"worker candidate {candidate[:7]} passed Reviewer and QA")
            if not applied:
                raise StageFailure("checkpoint", "task_result_not_recorded", why)
        if (repo_root / task_file).exists():
            _git(["add", "--", task_file], repo_root)
            _git(["commit", "-q", "-m", f"docs(tasks): record {task_id} Jarvis worker result\n\nCandidate {candidate}."], repo_root)
        result.checkpoint = _git(["rev-parse", "HEAD"], repo_root)
        _git(["worktree", "remove", str(worktree)], repo_root)
        _git(["branch", "-d", branch], repo_root)
        result.ok = True
        result.stage = "done"
        return result
    except StageFailure as failure:
        result.stage = failure.stage
        result.reason = failure.reason
        result.detail = failure.detail
    except Exception as exc:  # noqa: BLE001 - the Owner must always get a report
        result.reason = "unexpected_error"
        result.detail = f"{type(exc).__name__}: {exc}"[:200]
    if record_result is not None:
        try:
            record_result(False, f"{result.stage}:{result.reason}")
        except Exception:  # noqa: BLE001
            pass
    return result


if __name__ == "__main__":  # manual dry inspection: python claude_worker.py <task-id> <request>
    print(json.dumps(run_pipeline(task_id=sys.argv[1], request=sys.argv[2], approval_command=f"/go {sys.argv[1]}").to_dict(), ensure_ascii=False, indent=2))
