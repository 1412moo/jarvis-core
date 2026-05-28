"""Run deterministic Research Council mutation tests."""

from __future__ import annotations

import sys

from research_council.mutation_tests import (
    format_mutation_summary,
    run_mutation_tests,
)


def main(argv: list[str] | None = None) -> int:
    if argv:
        print("run_mutation_tests.py does not accept arguments.", file=sys.stderr)
        return 2

    summary = run_mutation_tests()
    print(format_mutation_summary(summary))
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
