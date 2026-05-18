"""Run a local deterministic Research Council demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from research_council import ResearchCouncilInput, run_research_council, write_result_json
from research_council.claim_extractor import domain_profile_for


def build_sample_input() -> ResearchCouncilInput:
    return ResearchCouncilInput(
        raw_idea=(
            "A swallowable biodegradable capsule could screen the colon for early signs "
            "of colorectal cancer, collect images or sensor data during transit, and "
            "then safely break down after discharge through wastewater."
        ),
        goal=(
            "Decide whether the capsule colon screening concept has enough grounded "
            "promise for only non-clinical minimum viable experiments."
        ),
        context=(
            "This is a deterministic v0.1 Research Council pass. It should identify "
            "claims, evidence gaps, reviewer critiques, minimum experiments, and a "
            "recommendation without doing web search or creating citations."
        ),
        constraints=(
            "Python standard library only.",
            "No web search, network calls, LLM calls, or fake citations.",
            "Keep missing evidence explicit.",
            "Do not recommend human testing from this local pass.",
        ),
        provided_evidence=(
            "The user supplied the concept of a swallowable capsule for colon screening.",
            "The user supplied the desired biodegradable wastewater-discharge behavior.",
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Research Council sample.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for writing the Markdown report; stdout is always used.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for writing the structured Research Council JSON result.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_data = build_sample_input()
    result = run_research_council(input_data)
    markdown = result.markdown_report.markdown
    print(markdown, end="")

    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
    if args.json_output:
        write_result_json(
            result,
            args.json_output,
            domain_profile=domain_profile_for(input_data),
        )


if __name__ == "__main__":
    main()
