"""Check a manual SOP task record against the staged candidate before the candidate commit.

Records from task-0160 to task-0170 show the first Reviewer returning FINDINGS about the
task record alone in 7 of 10 tasks, each one spending the repair budget that real code
findings needed (task-0171). This script runs the checks that need no judgement, on the
record as it is staged, so the Manager fixes them before the candidate exists:

- C1 the canonical parser (task_file_writer._transition_metadata) reads the record
- C2 the Jarvis Console parser (parse_task_view_text) reads it as valid, so Start and
  Complete will not refuse it later (task-0168: backticks inside the summary)
- C3 every file staged since the baseline is listed in an `| owned |` row (a path or a
  directory ending in "/"); the record itself is always allowed
- C4 when the record differs from HEAD, its updated_at differs too (task-model §7)
- C5 the record ends with a newline, as the canonical writer writes it
- C6 the task-0169 verbatim quote check, printed for the Manager; it never changes the
  exit code, because its list mixes conditions with headings

Exit code 0: no violation. 1: a violation; the Manager does not make the candidate
(SOP §3). 2: the input cannot be checked (not staged, Worker-path record, git error).
It reads git and the record only: no file write, no network. Whether the summary still
describes the task is not checkable here and stays with the Reviewer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "scripts", ROOT / "orchestrator" / "discord-intake", ROOT / "apps" / "jarvis-console"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import check_summary_quotes  # noqa: E402
from task_file_writer import _transition_metadata  # noqa: E402

OWNED_ROW = re.compile(r"^\|\s*owned\s*\|(.*)$")
BACKTICKED = re.compile(r"`([^`\s]+)`")
FILE_LIKE = re.compile(r"^[\w.-]+\.[A-Za-z0-9]+$")
META_LINE = re.compile(r"^- ([a-z_]+): `(.*)`$")
WORKER_SOURCE_COMMAND = "/task"

EXIT_PASS = 0
EXIT_VIOLATION = 1
EXIT_ERROR = 2


@dataclass
class Result:
    record: str
    baseline: str = ""
    staged_files: list[str] = field(default_factory=list)
    violations: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quote_unquoted: list[str] = field(default_factory=list)
    error: str = ""

    def add(self, check: str, problem: str, fix: str) -> None:
        self.violations.append({"check": check, "problem": problem, "fix": fix})


def _git(args: list[str], repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, check=False)


def _metadata(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = META_LINE.match(line)
        if match and match.group(1) not in values:
            values[match.group(1)] = match.group(2)
    return values


def owned_entries(text: str) -> list[str]:
    """Path-like backticked tokens of every `| owned |` row; names like `run_pipeline` are skipped.

    A token with "*" is kept but never matches a file: patterns are not part of the approved
    C3 design (task-0171 Reviewer 1), so every file a pattern would cover must be listed itself.
    """

    entries: list[str] = []
    for line in text.splitlines():
        match = OWNED_ROW.match(line.strip())
        if not match:
            continue
        for token in BACKTICKED.findall(match.group(1)):
            if "/" in token or "*" in token or FILE_LIKE.match(token):
                entries.append(token)
    return entries


def _owned(path: str, entries: list[str]) -> bool:
    for entry in entries:
        if entry.endswith("/") and path.startswith(entry):
            return True
        if path == entry:
            return True
    return False


def _console_view(file_name: str, text: str) -> dict | None:
    import run_web_app  # noqa: PLC0415 - heavy module, only needed for C2

    return run_web_app.parse_task_view_text(file_name, text)


def check(record: str, baseline: str, repo: Path = ROOT) -> Result:
    result = Result(record=record.replace("\\", "/"), baseline=baseline)
    rel = result.record
    name = rel.rsplit("/", 1)[-1]

    staged = _git(["show", f":{rel}"], repo)
    if staged.returncode != 0:
        result.error = f"record_not_staged: stage {rel} first (git add -- {rel})"
        return result
    raw = staged.stdout
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        result.add("C1", "the record is not valid UTF-8", "save the record as UTF-8")
        return result
    if _metadata(text).get("source_command") == WORKER_SOURCE_COMMAND:
        result.error = "worker_path_record: Worker-path records are written by the pipeline and are not checked here"
        return result
    diff = _git(["diff", "--cached", "--name-only", baseline], repo)
    if diff.returncode != 0:
        result.error = f"baseline_unreadable: {diff.stderr.decode('utf-8', 'replace').strip()[:200]}"
        return result
    result.staged_files = sorted(p for p in diff.stdout.decode("utf-8").splitlines() if p)

    # C1 canonical parser.
    _, error = _transition_metadata(raw, name)
    if error:
        result.add("C1", f"the canonical parser refuses the record: {error}",
                   "fix the metadata block: each field one line, `- name: `value``, no backtick inside a value")

    # C2 Jarvis Console parser.
    view = _console_view(name, text)
    if view is None:
        result.add("C2", "Jarvis Console does not read this file name as a task record",
                   "name the record memory/tasks/task-NNNN-<slug>.md")
    elif view.get("parse_state") != "valid":
        field_name = view.get("reason_field") or "-"
        result.add("C2", f"Jarvis Console reads the record as {view.get('reason_code')} (field {field_name})",
                   f"fix the {field_name} metadata value; a value cannot contain a backtick")

    # C3 owned rows against the staged change set.
    entries = owned_entries(text)
    if not entries:
        result.add("C3", "the record has no `| owned |` row with backticked paths",
                   "add a row: | owned | `path/one.py`, `docs/dir/` |")
    else:
        outside = [p for p in result.staged_files if p != rel and not _owned(p, entries)]
        if outside:
            result.add("C3", "staged files not listed in an owned row: " + ", ".join(outside),
                       "add each file to the owned row if it is in the approved scope, otherwise unstage it")
        for entry in entries:
            if "*" in entry or entry.endswith("/") or entry == rel:
                continue
            if entry not in result.staged_files:
                result.warnings.append(f"owned but not changed since the baseline: {entry}")

    # C4 updated_at against HEAD.
    head = _git(["show", f"HEAD:{rel}"], repo)
    if head.returncode == 0 and head.stdout != raw:
        before = _metadata(head.stdout.decode("utf-8", "replace")).get("updated_at", "")
        after = _metadata(text).get("updated_at", "")
        if before == after:
            result.add("C4", f"the record changed since HEAD but updated_at is still {after or '(missing)'}",
                       "set updated_at to the current UTC time, YYYY-MM-DD HH:MM UTC (task-model §7)")

    # C5 final newline.
    if not raw.endswith(b"\n"):
        result.add("C5", "the record does not end with a newline", "add a newline after the last line")

    # C6 task-0169 quote check, advice only.
    quotes = check_summary_quotes.check_text(text, record=rel)
    result.quote_unquoted = [f"{s.line}: {s.text}" for s in quotes.unquoted or []]
    if quotes.error:
        result.warnings.append(f"quote check: {quotes.error}")
    return result


def exit_code(result: Result) -> int:
    if result.error:
        return EXIT_ERROR
    return EXIT_VIOLATION if result.violations else EXIT_PASS


def _print(result: Result) -> None:
    print("check_task_record")
    print(f"record={result.record}")
    print(f"baseline={result.baseline}")
    if result.error:
        print(f"error={result.error}")
        print("status=ERROR")
        return
    print(f"staged_files={len(result.staged_files)}")
    print(f"violations={len(result.violations)}")
    for v in result.violations:
        print(f"VIOLATION {v['check']}: {v['problem']}")
        print(f"  fix: {v['fix']}")
    for w in result.warnings:
        print(f"WARNING {w}")
    print(f"quote_check_unquoted={len(result.quote_unquoted)} (advice only, see check_summary_quotes.py)")
    for line in result.quote_unquoted:
        print(f"  quote: {line}")
    print("status=" + ("BLOCKED" if result.violations else "PASS"))


# --- self-test ---------------------------------------------------------

_GOOD = """# task-9999-sample

- id: `task-9999-sample`
- title: `sample`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-19 10:00 UTC`
- updated_at: `2026-10-19 10:00 UTC`
- summary: `A sample record for the self-test.`
- source_command: `Owner 요청`

## Owner 요청 (원문)

```text
Add the tool.
```

## Manager 요약

| # | Owner 원문 | 해석 |
| --- | --- | --- |
| M1 | "Add the tool." | x |

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `tools/new_tool.py`(신규, `run_tool` 함수), `docs/guide/`, `docs/*.txt`, 이 기록 |
| deny | `jarvis.bat` |
"""


def _remove(path: Path) -> None:
    def retry(func, target, _exc) -> None:
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onexc=retry)


def _run_self_test() -> tuple[int, list[str]]:
    failures: list[str] = []
    checks = 0

    def expect(name: str, condition: bool, detail: object = "") -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(f"{name}: {detail!r}")

    tmp = Path(tempfile.mkdtemp(prefix="jarvis_check_task_record_"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        record = "memory/tasks/task-9999-sample.md"

        def write(rel: str, content: str | bytes) -> None:
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

        def stage(*rels: str) -> None:
            _git(["add", "--", *rels], repo)

        def codes(result: Result) -> list[str]:
            return [v["check"] for v in result.violations]

        for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@example.invalid"],
                     ["config", "user.name", "t"], ["config", "core.autocrlf", "false"]):
            _git(args, repo)
        write("README.md", "base\n")
        stage("README.md")
        _git(["commit", "-q", "-m", "base"], repo)
        baseline = _git(["rev-parse", "HEAD"], repo).stdout.decode().strip()

        result = check(record, baseline, repo)
        expect("an unstaged record is an input error", result.error.startswith("record_not_staged"), result.error)

        write(record, _GOOD)
        write("tools/new_tool.py", "print('x')\n")
        write("docs/guide/a.md", "a\n")
        stage(record, "tools/new_tool.py", "docs/guide/a.md")
        result = check(record, baseline, repo)
        expect("T1/T5 a new file and a directory in owned pass", exit_code(result) == EXIT_PASS, result.violations)
        expect("a backticked name that is not a path is not an owned path", "run_tool" not in owned_entries(_GOOD))
        write("docs/notes.txt", "n\n")
        stage("docs/notes.txt")
        result = check(record, baseline, repo)
        expect("a \"*\" pattern in owned covers no file (Reviewer 1)",
               codes(result) == ["C3"] and "docs/notes.txt" in result.violations[0]["problem"], result.violations)
        _git(["rm", "-q", "--cached", "--", "docs/notes.txt"], repo)

        write("README.md", "changed\n")
        stage("README.md")
        result = check(record, baseline, repo)
        expect("T4 a staged file outside owned is C3", codes(result) == ["C3"] and "README.md" in result.violations[0]["problem"], result.violations)
        _git(["reset", "-q", "--", "README.md"], repo)
        write("README.md", "base\n")

        write(record, _GOOD.replace("- status: `DOING`", "- status: DOING"))
        stage(record)
        result = check(record, baseline, repo)
        expect("T2 a malformed metadata line is C1", "C1" in codes(result), result.violations)

        write(record, _GOOD.replace("A sample record for the self-test.", "Candidate `abc1234` passed."))
        stage(record)
        result = check(record, baseline, repo)
        expect("T3 a backtick inside the summary is C2 (task-0168)", "C2" in codes(result), result.violations)

        write(record, _GOOD.replace("| owned |", "| scope |"))
        stage(record)
        result = check(record, baseline, repo)
        expect("D2 a record without an owned row is C3",
               codes(result) == ["C3"] and "no `| owned |` row" in result.violations[0]["problem"], result.violations)

        write(record, _GOOD.rstrip("\n"))
        stage(record)
        result = check(record, baseline, repo)
        expect("T7 a missing final newline is C5", codes(result) == ["C5"], result.violations)

        write(record, _GOOD)
        stage(record)
        _git(["commit", "-q", "-m", "candidate"], repo)
        write(record, _GOOD + "\n## QA\n\nPASS\n")
        stage(record)
        result = check(record, baseline, repo)
        expect("T6 a changed record with the same updated_at is C4", codes(result) == ["C4"], result.violations)
        write(record, (_GOOD + "\n## QA\n\nPASS\n").replace("updated_at: `2026-10-19 10:00 UTC`", "updated_at: `2026-10-19 11:00 UTC`"))
        stage(record)
        result = check(record, baseline, repo)
        expect("T6 a changed record with a new updated_at passes", exit_code(result) == EXIT_PASS, result.violations)

        write(record, _GOOD.replace('| M1 | "Add the tool." | x |', "| M1 | (none) | x |").replace(
            "updated_at: `2026-10-19 10:00 UTC`", "updated_at: `2026-10-19 12:00 UTC`"))
        stage(record)
        result = check(record, baseline, repo)
        expect("T8 an unquoted Owner sentence is advice only",
               exit_code(result) == EXIT_PASS and bool(result.quote_unquoted), asdict(result))

        write(record, _GOOD.replace("- source_command: `Owner 요청`", "- source_command: `/task`"))
        stage(record)
        result = check(record, baseline, repo)
        expect("a Worker-path record is not checked", result.error.startswith("worker_path_record"), result.error)
    finally:
        _remove(tmp)
    expect("the self-test leaves no temporary directory", not tmp.exists(), str(tmp))
    return checks, failures


# --- CLI -----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("record", nargs="?", help="task record path, e.g. memory/tasks/<task-id>.md")
    parser.add_argument("--baseline", help="the task's baseline commit (the record's 기준선)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--self-test", action="store_true", help="run the built-in cases in a temporary repository")
    args = parser.parse_args(argv)

    if args.self_test:
        checks, failures = _run_self_test()
        print("check_task_record self-test")
        print(f"checks={checks}")
        print(f"failures={len(failures)}")
        for failure in failures:
            print(f"ERROR {failure}")
        print("status=" + ("FAIL" if failures else "PASS"))
        return 1 if failures else 0
    if not args.record or not args.baseline:
        parser.error("a task record path and --baseline are required (or --self-test)")

    result = check(args.record, args.baseline)
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        _print(result)
    return exit_code(result)


if __name__ == "__main__":
    sys.exit(main())
