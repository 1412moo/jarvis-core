"""Generate deterministic Research Council benchmark scenarios."""

from __future__ import annotations

import argparse
import sys

from research_council.scenario_templates import (
    CATEGORY_ORDER,
    build_scenario_summary,
    format_scenario_summary,
    generate_scenarios,
    scenarios_to_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic Research Council scenario templates."
    )
    parser.add_argument(
        "--category",
        choices=CATEGORY_ORDER,
        help="Limit generated scenarios to one deterministic template category.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print stable JSON instead of the concise text summary.",
    )
    args = parser.parse_args(argv)

    scenarios = generate_scenarios(category=args.category)
    summary = build_scenario_summary(scenarios)
    if args.json:
        print(scenarios_to_json(summary), end="")
    else:
        print(format_scenario_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
