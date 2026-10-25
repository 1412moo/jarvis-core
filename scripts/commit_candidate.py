"""Commit the staged change set only when the task record preflight passes (task-0197 pilot).

A manual SOP candidate is made after `check_task_record.py` reports PASS (SOP section 3). Running
the check and the commit as two shell steps let a BLOCKED preflight slip into a commit when the
steps were chained (task-0180, task-0181, task-0196). This script does both in one place and
commits nothing unless every check below holds:

1. at least one file is staged;
2. every staged file's working tree equals its staged content, so the commit is what was checked;
3. `git diff --cached --check` reports no whitespace error;
4. `check_task_record.check(record, baseline)` has no violation (with --require-quotes, an Owner
   sentence the Manager summary does not quote is a violation too).

It then runs only `git commit -F <message file>`. It never stages, edits or pushes anything.

Exit code 0: committed. 1: a check failed and nothing was committed. 2: usage, git or preflight
input error (for example a record check_task_record cannot read); nothing was committed either.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_task_record  # noqa: E402

EXIT_COMMITTED = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2
# A refusal that comes from a git or input error rather than from a failed check.
ERROR_PREFIX = "error: "


def _git(args: list[str], repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")


def refusals(record: str, baseline: str, repo: Path = ROOT, require_quotes: bool = False) -> list[str]:
    """Every reason not to commit now; an empty list means the commit may go ahead."""

    staged = _git(["diff", "--cached", "--name-only"], repo)
    if staged.returncode != 0:
        return [f"{ERROR_PREFIX}git diff --cached failed: {staged.stderr.strip()[:200]}"]
    paths = [p for p in staged.stdout.splitlines() if p.strip()]
    if not paths:
        return ["nothing is staged"]
    reasons = []
    worktree = _git(["diff", "--name-only", "--", *paths], repo)
    if worktree.returncode != 0:
        # A failed comparison must not read as "no difference".
        reasons.append(f"{ERROR_PREFIX}git diff failed: {worktree.stderr.strip()[:200]}")
    unstaged = [p for p in worktree.stdout.splitlines() if p.strip()]
    if unstaged:
        reasons.append("staged files differ from the working tree (stage them again): " + ", ".join(unstaged))
    whitespace = _git(["diff", "--cached", "--check"], repo)
    if whitespace.returncode != 0:
        detail = (whitespace.stdout.strip() or whitespace.stderr.strip() or "failed").splitlines()[0]
        reasons.append("git diff --cached --check: " + detail[:200])
    result = check_task_record.check(record, baseline, repo, require_quotes=require_quotes)
    if result.error:
        reasons.append(f"{ERROR_PREFIX}check_task_record error: {result.error}")
    for violation in result.violations:
        reasons.append(f"check_task_record {violation['check']}: {violation['problem']}")
    return reasons


def commit(record: str, baseline: str, message_file: str, repo: Path = ROOT, require_quotes: bool = False) -> tuple[int, list[str]]:
    reasons = refusals(record, baseline, repo, require_quotes)
    if reasons:
        return (EXIT_ERROR if any(r.startswith(ERROR_PREFIX) for r in reasons) else EXIT_REFUSED), reasons
    done = _git(["commit", "-q", "-F", message_file], repo)
    if done.returncode != 0:
        return EXIT_ERROR, [f"git commit failed: {(done.stderr or done.stdout).strip()[:300]}"]
    head = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    return EXIT_COMMITTED, [head]


# --- self-test ---------------------------------------------------------


def _run_self_test() -> tuple[int, list[str]]:
    failures: list[str] = []
    checks = 0

    def expect(name: str, condition: bool, detail: object = "") -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(f"{name}: {detail!r}")

    tmp = Path(tempfile.mkdtemp(prefix="jarvis_commit_candidate_"))
    try:
        repo = tmp / "repo"
        (repo / "memory" / "tasks").mkdir(parents=True)
        for args in (["init", "-q"], ["config", "user.email", "t@example.invalid"], ["config", "user.name", "t"],
                     ["config", "core.autocrlf", "false"]):
            _git(args, repo)
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        _git(["add", "-A"], repo)
        _git(["commit", "-q", "-m", "base"], repo)
        baseline = _git(["rev-parse", "HEAD"], repo).stdout.strip()
        record = "memory/tasks/task-9999-sample.md"
        good = check_task_record._GOOD
        message = tmp / "message.txt"
        message.write_text("test commit\n", encoding="utf-8")

        def head() -> str:
            return _git(["rev-parse", "HEAD"], repo).stdout.strip()

        code, out = commit(record, baseline, str(message), repo)
        expect("nothing staged is refused", code == EXIT_REFUSED and out == ["nothing is staged"], out)

        tool = "tools/new_tool.py"  # an owned path of the sample record
        (repo / "tools").mkdir()
        (repo / record).write_text(good, encoding="utf-8", newline="\n")
        (repo / tool).write_text("print('x')\n", encoding="utf-8", newline="\n")
        (repo / "other.py").write_text("print('y')\n", encoding="utf-8", newline="\n")
        _git(["add", record, tool, "other.py"], repo)
        before = head()
        code, out = commit(record, baseline, str(message), repo)
        expect("a BLOCKED preflight (unlisted file) commits nothing", code == EXIT_REFUSED and head() == before
               and any("C3" in r for r in out), out)

        _git(["rm", "-q", "--cached", "other.py"], repo)
        (repo / tool).write_text("print('changed after staging')\n", encoding="utf-8", newline="\n")
        code, out = commit(record, baseline, str(message), repo)
        expect("a working tree that differs from the index is refused", code == EXIT_REFUSED and head() == before
               and any("differ from the working tree" in r for r in out), out)

        (repo / tool).write_text("print('x')   \n", encoding="utf-8", newline="\n")
        _git(["add", tool], repo)
        code, out = commit(record, baseline, str(message), repo)
        expect("a whitespace error is refused", code == EXIT_REFUSED and head() == before
               and any("--check" in r for r in out), out)

        (repo / tool).write_text("print('x')\n", encoding="utf-8", newline="\n")
        (repo / record).write_text(good.replace('| M1 | "Add the tool." | x |', "| M1 | (none) | x |"),
                                   encoding="utf-8", newline="\n")
        _git(["add", record, tool], repo)
        code, out = commit(record, baseline, str(message), repo, require_quotes=True)
        expect("with require_quotes an unquoted Owner sentence is refused", code == EXIT_REFUSED and head() == before
               and any("C6" in r for r in out), out)

        code, out = commit(record, baseline, str(message), repo)
        expect("without require_quotes the same change set commits", code == EXIT_COMMITTED and head() != before
               and out == [head()], out)
        expect("the commit holds exactly the staged files", sorted(_git(["show", "--name-only", "--format=", "HEAD"], repo)
               .stdout.split()) == sorted([record, tool]))
        expect("nothing is left staged or pushed", _git(["diff", "--cached", "--name-only"], repo).stdout.strip() == ""
               and _git(["remote"], repo).stdout.strip() == "")

        # An input error of the preflight (here a Worker-path record) is an error exit, not a plain refusal.
        (repo / record).write_text(good.replace("- source_command: `Owner 요청`", "- source_command: `/task`"),
                                   encoding="utf-8", newline="\n")
        _git(["add", record], repo)
        after = head()
        code, out = commit(record, baseline, str(message), repo)
        expect("a preflight input error exits 2 and commits nothing", code == EXIT_ERROR and head() == after
               and any(r.startswith(ERROR_PREFIX) for r in out), out)
        _git(["reset", "-q"], repo)
    finally:
        check_task_record._remove(tmp)
    expect("the self-test leaves no temporary directory", not tmp.exists(), str(tmp))
    return checks, failures


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", help="task record path, e.g. memory/tasks/<task-id>.md")
    parser.add_argument("--baseline", help="the task's baseline commit")
    parser.add_argument("--message-file", help="file holding the commit message")
    parser.add_argument("--require-quotes", action="store_true", help="also refuse an Owner sentence the summary does not quote")
    parser.add_argument("--self-test", action="store_true", help="run the built-in cases in a temporary repository")
    args = parser.parse_args(argv)

    if args.self_test:
        checks, failures = _run_self_test()
        print("commit_candidate self-test")
        print(f"checks={checks}")
        print(f"failures={len(failures)}")
        for failure in failures:
            print(f"ERROR {failure}")
        print("status=" + ("FAIL" if failures else "PASS"))
        return 1 if failures else 0
    if not (args.record and args.baseline and args.message_file):
        parser.error("--record, --baseline and --message-file are required (or --self-test)")

    code, lines = commit(args.record, args.baseline, args.message_file, require_quotes=args.require_quotes)
    print("commit_candidate")
    if code == EXIT_COMMITTED:
        print(f"committed={lines[0]}")
        print("status=COMMITTED")
    else:
        for line in lines:
            print(f"REFUSED {line}")
        print("status=" + ("REFUSED" if code == EXIT_REFUSED else "ERROR"))
    return code


if __name__ == "__main__":
    sys.exit(main())
