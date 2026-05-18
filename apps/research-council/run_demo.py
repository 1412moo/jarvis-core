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


def build_runtime_input(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> ResearchCouncilInput:
    has_custom_input = any(
        (
            args.idea,
            args.goal,
            args.context,
            args.constraints,
        )
    )
    if not has_custom_input:
        return build_sample_input()

    if not args.idea:
        parser.error("--idea is required when providing custom Research Council input.")
    if not args.goal:
        parser.error("--goal is required when providing custom Research Council input.")

    return ResearchCouncilInput(
        raw_idea=args.idea,
        goal=args.goal,
        context=args.context,
        constraints=tuple(args.constraints or ()),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the deterministic local Research Council against the sample fixture "
            "or a custom idea and goal."
        ),
        epilog=(
            "Examples:\n"
            "  python run_demo.py\n"
            "  python run_demo.py --idea \"AI patent analysis assistant for solo founders\" "
            "--goal \"Evaluate differentiation and market viability\"\n"
            "\n"
            "This demo is local-only: no web search, network calls, LLM calls, or "
            "citations are performed."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--idea",
        help=(
            "Raw idea to evaluate. When custom input is provided, --idea and --goal "
            "are both required."
        ),
    )
    parser.add_argument(
        "--goal",
        help=(
            "Decision goal for the Research Council pass. Required when using "
            "custom input."
        ),
    )
    parser.add_argument(
        "--context",
        help=(
            "Optional local context or background for the custom Research Council "
            "input."
        ),
    )
    parser.add_argument(
        "--constraints",
        action="append",
        default=[],
        metavar="TEXT",
        help=(
            "Optional constraint for the custom run. Repeat this flag to provide "
            "multiple constraints."
        ),
    )
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
    return parser


def parse_args() -> tuple[argparse.Namespace, argparse.ArgumentParser]:
    parser = build_parser()
    return parser.parse_args(), parser


def main() -> None:
    args, parser = parse_args()
    input_data = build_runtime_input(args, parser)
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
