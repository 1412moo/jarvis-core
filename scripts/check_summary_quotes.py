"""List Owner verbatim sentences that a task record's Manager summary does not quote.

SOP §3 (Manager) asks the Manager to quote the Owner approval's conditions in the
task record without summarizing, and the Reviewer reports every condition the
Manager summary leaves out. Records from task-0133 to task-0168 show that finding
again and again, each one costing a repair, a repair-budget increase or an SOP §8
acceptance by the Owner. This script runs the same comparison deterministically
before the Reviewer is called, so the Manager can fix the summary first.

It reads one task record and nothing else. Owner text is every fenced block under
a heading that says it is verbatim (`원문` or `verbatim`), except the Manager
summary itself. The summary is the section whose heading starts with
`Manager 요약`. A sentence counts as quoted when its whitespace-normalized text
appears in the summary section.

The result is advice for the Manager, not a verdict: the Reviewer still compares
conditions, and a listed sentence that is not a condition (a greeting, a heading)
can be left as it is. It never writes a file, calls git or touches the network.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SUMMARY_HEADING_PREFIX = "Manager 요약"
VERBATIM_HEADING_MARKERS = ("원문", "verbatim")
HEADING = re.compile(r"^(#{2,6})\s+(.*?)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
LIST_MARKER = re.compile(r"^\s*(?:[*+\-]|\d+\\?[.)])\s+")
SENTENCE_END = re.compile(r"(?<=[.?!])\s+")
MARKDOWN_ESCAPE = re.compile(r"\\([|.*_`\[\]()#>+\-!])")
WHITESPACE = re.compile(r"\s+")
# Shorter pieces are list labels or fragments ("A안", "1.") rather than conditions.
MIN_SENTENCE_CHARS = 6

EXIT_ALL_QUOTED = 0
EXIT_UNQUOTED = 1
EXIT_ERROR = 2


@dataclass(frozen=True)
class Sentence:
    section: str
    line: int
    text: str


@dataclass
class Report:
    record: str
    summary_heading: str = ""
    verbatim_sections: int = 0
    sentences: int = 0
    unquoted: list[Sentence] | None = None
    error: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["unquoted"] = [asdict(s) for s in self.unquoted or []]
        return data


def normalize(text: str) -> str:
    return WHITESPACE.sub(" ", MARKDOWN_ESCAPE.sub(r"\1", text)).strip()


def _sections(lines: list[str]) -> list[tuple[str, list[tuple[int, str]]]]:
    """Split a record into (heading, [(line number, line)]) pairs; fences hide headings."""

    sections: list[tuple[str, list[tuple[int, str]]]] = []
    in_fence = False
    for number, line in enumerate(lines, start=1):
        if FENCE.match(line):
            in_fence = not in_fence
        heading = None if in_fence else HEADING.match(line)
        if heading:
            sections.append((heading.group(2), []))
        elif sections:
            sections[-1][1].append((number, line))
    return sections


def is_summary_heading(heading: str) -> bool:
    return heading.strip().startswith(SUMMARY_HEADING_PREFIX)


def is_verbatim_heading(heading: str) -> bool:
    lowered = heading.lower()
    return not is_summary_heading(heading) and any(m in lowered for m in VERBATIM_HEADING_MARKERS)


def _fenced_sentences(heading: str, body: list[tuple[int, str]]) -> list[Sentence]:
    sentences: list[Sentence] = []
    in_fence = False
    for number, line in body:
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        # A heading inside the Owner text is its structure, not a condition.
        if not in_fence or HEADING.match(line):
            continue
        for piece in SENTENCE_END.split(LIST_MARKER.sub("", line).strip()):
            text = normalize(piece)
            if len(text) >= MIN_SENTENCE_CHARS:
                sentences.append(Sentence(heading, number, text))
    return sentences


def _is_quoted(text: str, summary: str) -> bool:
    # A summary row may quote a sentence without its closing period.
    return text in summary or text.rstrip(".") in summary


def check_text(text: str, record: str = "<text>") -> Report:
    report = Report(record=record)
    sections = _sections(text.splitlines())
    summaries = [(h, body) for h, body in sections if is_summary_heading(h)]
    if not summaries:
        report.error = "no_manager_summary_section"
        return report
    report.summary_heading = summaries[0][0]
    summary = normalize(" ".join(line for _, body in summaries for _, line in body))

    seen: set[str] = set()
    unquoted: list[Sentence] = []
    for heading, body in sections:
        if not is_verbatim_heading(heading):
            continue
        found = _fenced_sentences(heading, body)
        if not found:
            continue
        report.verbatim_sections += 1
        for sentence in found:
            if sentence.text in seen:
                continue
            seen.add(sentence.text)
            report.sentences += 1
            if not _is_quoted(sentence.text, summary):
                unquoted.append(sentence)
    report.unquoted = unquoted
    if report.verbatim_sections == 0:
        report.error = "no_verbatim_blocks"
    return report


def check_record(path: Path) -> Report:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return Report(record=str(path), error=f"unreadable: {type(exc).__name__}")
    return check_text(text, record=str(path))


def exit_code(report: Report) -> int:
    if report.error:
        return EXIT_ERROR
    return EXIT_UNQUOTED if report.unquoted else EXIT_ALL_QUOTED


# --- self-test ---------------------------------------------------------

_FIXTURE = """# task-9999

## Owner 결정 (원문)

```text
1. 기존 run_pipeline을 그대로 재사용한다.
2. Radar는 두 번째 작업 종류만 추가한다. push는 하지 않는다
- `jarvis.bat`은 열지 마세요.
A안
## 펜스 안 제목은 제목이 아니다.
```

이 줄은 펜스 밖이라 Owner 원문으로 보지 않는다.

## Manager 요약 (원문 해석)

| # | 원문 | 해석 |
| --- | --- | --- |
| A1 | "기존 run_pipeline을 그대로 재사용한다." | 유지 |
| A2 | "push는 하지 않는다" \\| 열지 않음: "`jarvis.bat`은 열지 마세요" | 금지 |

## Owner 승인 (원문)

```text
기존 run_pipeline을 그대로 재사용한다.
```
"""


def _run_self_test() -> tuple[int, list[str]]:
    failures: list[str] = []
    checks = 0

    def expect(name: str, condition: bool, detail: object = "") -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(f"{name}: {detail!r}")

    report = check_text(_FIXTURE)
    unquoted = [s.text for s in report.unquoted or []]
    expect("summary heading with a suffix is the summary", report.summary_heading == "Manager 요약 (원문 해석)", report.summary_heading)
    expect("summary heading is not read as Owner text", report.verbatim_sections == 2, report.verbatim_sections)
    expect("only the unquoted condition is listed", unquoted == ["Radar는 두 번째 작업 종류만 추가한다."], unquoted)
    expect("a repeated sentence counts once", report.sentences == 4, report.sentences)
    expect("a heading inside a fence neither splits the section nor counts", report.verbatim_sections == 2, report.to_dict())
    expect("short labels are skipped", "A안" not in unquoted, unquoted)
    expect("text outside fences is ignored", not any("펜스 밖" in t for t in unquoted), unquoted)
    expect("line number points into the record", bool(report.unquoted) and report.unquoted[0].line == 7, report.unquoted)
    expect("unquoted sentence exits 1", exit_code(report) == EXIT_UNQUOTED, exit_code(report))

    quoted_all = _FIXTURE.replace(
        "| A2 |",
        '| A0 | "Radar는 두 번째 작업 종류만 추가한다" | 범위 |\n| A2 |',
    )
    report = check_text(quoted_all)
    expect("a quote without its closing period counts", not report.unquoted, report.unquoted)
    expect("all quoted exits 0", exit_code(report) == EXIT_ALL_QUOTED, exit_code(report))

    report = check_text("## Owner 결정 (원문)\n\n```text\n조건 문장입니다.\n```\n")
    expect("missing summary is an error", report.error == "no_manager_summary_section", report.error)
    expect("missing summary exits 2", exit_code(report) == EXIT_ERROR, exit_code(report))

    report = check_text("## Manager 요약\n\n| a | b |\n\n## 구현\n\n```text\n원문 아님 문장입니다.\n```\n")
    expect("no verbatim block is an error", report.error == "no_verbatim_blocks", report.error)

    report = check_text("## Owner verbatim approval\n\n```text\nShip it only after QA.\n```\n\n## Manager 요약\n\nnone\n")
    expect("an English verbatim heading counts", report.verbatim_sections == 1 and len(report.unquoted or []) == 1, report.to_dict())

    report = check_record(Path("does-not-exist-task-record.md"))
    expect("unreadable record is an error", report.error.startswith("unreadable"), report.error)
    return checks, failures


# --- CLI -----------------------------------------------------------------


def _print_report(report: Report) -> None:
    print("check_summary_quotes")
    print(f"record={report.record}")
    if report.error:
        print(f"error={report.error}")
        print("status=ERROR")
        return
    print(f"summary_heading={report.summary_heading}")
    print(f"verbatim_sections={report.verbatim_sections}")
    print(f"sentences={report.sentences}")
    print(f"unquoted={len(report.unquoted or [])}")
    print("status=" + ("UNQUOTED" if report.unquoted else "ALL_QUOTED"))
    for sentence in report.unquoted or []:
        print(f"{report.record}:{sentence.line} [{sentence.section}] {sentence.text}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        # The records are Korean; a cp949 console must not stop the report (task-0158).
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("record", nargs="?", help="task record path, e.g. memory/tasks/<task-id>.md")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--self-test", action="store_true", help="run the built-in fixtures instead of a record")
    args = parser.parse_args(argv)

    if args.self_test:
        checks, failures = _run_self_test()
        print("check_summary_quotes self-test")
        print(f"checks={checks}")
        print(f"failures={len(failures)}")
        for failure in failures:
            print(f"ERROR {failure}")
        print("status=" + ("FAIL" if failures else "PASS"))
        return 1 if failures else 0
    if not args.record:
        parser.error("a task record path is required (or --self-test)")

    report = check_record(Path(args.record))
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_report(report)
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
