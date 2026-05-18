"""Run deterministic Research Council golden-case evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from research_council.evaluation import evaluate_golden_cases, format_regression_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Optional golden case root. Defaults to apps/research-council/golden_cases.",
    )
    args = parser.parse_args(argv)

    summary = evaluate_golden_cases(args.root)
    print(format_regression_summary(summary))
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
