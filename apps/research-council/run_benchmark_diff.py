"""View deterministic Research Council benchmark snapshot diffs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from research_council.benchmark_history import (
    build_benchmark_diff_view,
    build_benchmark_diff_view_from_history,
    classify_benchmark_governance_gate,
    format_benchmark_diff_view,
    format_benchmark_governance_summary,
    load_benchmark_history,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--history",
        type=Path,
        default=None,
        help="Benchmark history JSON file; compares latest to previous.",
    )
    source.add_argument(
        "--before",
        type=Path,
        default=None,
        help="Earlier benchmark snapshot JSON file.",
    )
    parser.add_argument(
        "--after",
        type=Path,
        default=None,
        help="Later benchmark snapshot JSON file. Required with --before.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Return exit code 1 when governance severity is critical.",
    )
    args = parser.parse_args(argv)

    if args.before is not None and args.after is None:
        parser.error("--after is required with --before")
    if args.before is None and args.after is not None:
        parser.error("--before is required with --after")
    if args.history is not None and args.after is not None:
        parser.error("--after cannot be used with --history")

    if args.history is not None:
        view = build_benchmark_diff_view_from_history(load_benchmark_history(args.history))
    else:
        view = build_benchmark_diff_view(args.before, args.after)
    print(format_benchmark_governance_summary(view))
    print(format_benchmark_diff_view(view))
    if args.fail_on_critical and classify_benchmark_governance_gate(view) == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
