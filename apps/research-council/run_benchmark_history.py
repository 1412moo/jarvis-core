"""Append and compare deterministic Research Council benchmark history."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from research_council.benchmark_history import (
    append_benchmark_history,
    compare_latest_to_previous,
    format_benchmark_trend_summary,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        required=True,
        help="Benchmark snapshot JSON file to append to history.",
    )
    parser.add_argument(
        "--history",
        type=Path,
        required=True,
        help="Benchmark history JSON file to create or update.",
    )
    args = parser.parse_args(argv)

    history = append_benchmark_history(args.snapshot, args.history)
    print(format_benchmark_trend_summary(compare_latest_to_previous(history)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
