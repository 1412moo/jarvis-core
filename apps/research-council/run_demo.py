"""Run a local deterministic Research Council demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_council import (
    ALIASES,
    LLMAugmentationMode,
    ResearchCouncilInput,
    list_profiles,
    resolve_domain_profile,
    run_research_council,
    write_result_json,
)


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


def aliases_by_profile() -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    for alias, profile_id in sorted(ALIASES.items()):
        aliases.setdefault(profile_id, []).append(alias)
    return aliases


def format_profile_listing() -> str:
    aliases = aliases_by_profile()
    lines = ["Research Council profiles:"]
    for profile in list_profiles():
        profile_aliases = aliases.get(profile.id, [])
        alias_text = ", ".join(profile_aliases) if profile_aliases else "none"
        lines.append(f"- {profile.id}: {profile.label} (aliases: {alias_text})")
    return "\n".join(lines) + "\n"


def format_profile_description(profile_or_alias: str) -> str:
    profile = resolve_domain_profile(
        build_sample_input(),
        explicit_profile_id=profile_or_alias,
    ).profile
    profile_aliases = aliases_by_profile().get(profile.id, [])
    alias_text = ", ".join(profile_aliases) if profile_aliases else "none"

    lines = [
        "Research Council profile:",
        f"- id: {profile.id}",
        f"- label: {profile.label}",
        f"- aliases: {alias_text}",
        f"- summary: {profile.summary}",
    ]
    if profile.evidence_needs:
        lines.append("- evidence_needs:")
        for need in profile.evidence_needs:
            lines.append(f"  - {need.category}: {need.request}")
    return "\n".join(lines) + "\n"


def build_input_from_json(
    path: Path,
    parser: argparse.ArgumentParser,
) -> ResearchCouncilInput:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        parser.error(f"--input-json could not be read: {exc}")
    except json.JSONDecodeError as exc:
        parser.error(f"--input-json must contain valid JSON: {exc.msg}")

    if not isinstance(payload, dict):
        parser.error("--input-json must contain a JSON object.")

    allowed_keys = {
        "context",
        "constraints",
        "goal",
        "idea",
        "provided_evidence",
        "raw_idea",
    }
    unknown_keys = sorted(str(key) for key in payload if key not in allowed_keys)
    if unknown_keys:
        parser.error("--input-json contains unknown keys: " + ", ".join(unknown_keys))
    if "idea" in payload and "raw_idea" in payload:
        parser.error("--input-json must not contain both raw_idea and idea.")

    raw_idea = _optional_json_string(payload, "raw_idea", parser)
    idea = _optional_json_string(payload, "idea", parser)
    goal = _optional_json_string(payload, "goal", parser)
    context = _optional_json_string(payload, "context", parser)
    if raw_idea is None and idea is None:
        parser.error("--input-json must contain idea or raw_idea.")
    if goal is None:
        parser.error("--input-json must contain goal.")

    return ResearchCouncilInput(
        raw_idea=raw_idea if raw_idea is not None else str(idea),
        goal=goal,
        context=context,
        constraints=_json_string_list(payload, "constraints", parser),
        provided_evidence=_json_string_list(payload, "provided_evidence", parser),
    )


def _optional_json_string(
    payload: dict[object, object],
    key: str,
    parser: argparse.ArgumentParser,
) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str):
        parser.error(f"--input-json field {key} must be a string.")
    return value


def _json_string_list(
    payload: dict[object, object],
    key: str,
    parser: argparse.ArgumentParser,
) -> tuple[str, ...]:
    if key not in payload:
        return ()
    value = payload[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        parser.error(f"--input-json field {key} must be a list of strings.")
    return tuple(value)


def build_runtime_input(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> ResearchCouncilInput:
    if args.input_json:
        if any((args.idea, args.goal, args.context, args.constraints, args.provided_evidence)):
            parser.error(
                "--input-json cannot be combined with --idea, --goal, --context, "
                "--constraints, or --provided-evidence."
            )
        return build_input_from_json(args.input_json, parser)

    has_custom_input = any(
        (
            args.idea,
            args.goal,
            args.context,
            args.constraints,
            args.provided_evidence,
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
        provided_evidence=tuple(args.provided_evidence or ()),
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
            "  python run_demo.py --profile ai_saas\n"
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
        "--provided-evidence",
        action="append",
        default=[],
        metavar="TEXT",
        help=(
            "Optional locally supplied evidence for the custom run. Repeat this "
            "flag to provide multiple evidence notes."
        ),
    )
    parser.add_argument(
        "--profile",
        help=(
            "Optional deterministic domain profile id or alias. Known ids include "
            "general, medical_device, ai_saas, creator_tools, marketplace, enterprise_b2b, "
            "developer_tool, consumer_app, hardware_device, and materials_science."
        ),
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List deterministic profile ids and aliases, then exit.",
    )
    parser.add_argument(
        "--describe-profile",
        metavar="PROFILE",
        help="Describe one deterministic profile id or alias, then exit.",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        metavar="PATH",
        help="Optional local JSON object for custom Research Council input.",
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
    parser.add_argument(
        "--llm-augmentation-mode",
        choices=[mode.value for mode in LLMAugmentationMode],
        default=LLMAugmentationMode.OFF.value,
        help=(
            "Optional deterministic augmentation sandbox mode. Defaults to off; "
            "this does not make external LLM calls."
        ),
    )
    return parser


def parse_args() -> tuple[argparse.Namespace, argparse.ArgumentParser]:
    parser = build_parser()
    return parser.parse_args(), parser


def main() -> None:
    args, parser = parse_args()
    if args.list_profiles and args.describe_profile:
        parser.error("--list-profiles and --describe-profile cannot be used together.")
    if args.list_profiles:
        print(format_profile_listing(), end="")
        return
    if args.describe_profile:
        try:
            print(format_profile_description(args.describe_profile), end="")
        except ValueError as exc:
            if "unknown domain profile" in str(exc):
                parser.error(str(exc))
            raise
        return

    input_data = build_runtime_input(args, parser)
    try:
        result = run_research_council(
            input_data,
            profile=args.profile,
            llm_advisor_config=args.llm_augmentation_mode,
        )
    except ValueError as exc:
        if args.profile and "unknown domain profile" in str(exc):
            parser.error(str(exc))
        raise
    markdown = result.markdown_report.markdown
    print(markdown, end="")

    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
    if args.json_output:
        write_result_json(result, args.json_output)


if __name__ == "__main__":
    main()
