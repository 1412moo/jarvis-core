"""Run deterministic Research Council golden-case evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from research_council.evaluation import (
    build_benchmark_analytics,
    evaluate_golden_cases,
    format_benchmark_analytics,
    format_regression_summary,
)
from research_council.benchmark_snapshot import export_benchmark_snapshot
from research_council.llm_advisor import LLMAugmentationMode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Optional golden case root. Defaults to apps/research-council/golden_cases.",
    )
    parser.add_argument(
        "--llm-augmentation-mode",
        choices=[mode.value for mode in LLMAugmentationMode],
        default=LLMAugmentationMode.OFF.value,
        help="Optional deterministic LLM augmentation sandbox mode. Defaults to off.",
    )
    parser.add_argument(
        "--show-analytics",
        action="store_true",
        help="Print deterministic benchmark analytics after the regression summary.",
    )
    parser.add_argument(
        "--export-snapshot",
        type=Path,
        default=None,
        help="Write a deterministic benchmark snapshot JSON file.",
    )
    args = parser.parse_args(argv)

    summary = evaluate_golden_cases(
        args.root,
        llm_advisor_config=args.llm_augmentation_mode,
    )
    print(format_regression_summary(summary))
    if args.show_analytics:
        print(format_benchmark_analytics(build_benchmark_analytics(summary)))
    if args.export_snapshot is not None:
        export_benchmark_snapshot(
            summary,
            args.export_snapshot,
            augmentation_mode=args.llm_augmentation_mode,
        )
        print(f"Benchmark snapshot exported: {args.export_snapshot}")
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
