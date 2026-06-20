"""Run the Hermes Manager Pilot v0.2 deterministic prompt renderer."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from hermes_manager_pilot.pipeline import run_hermes_manager_pilot
from hermes_manager_pilot.prompt_renderer import ALLOWED_RENDER_MODES
from hermes_manager_pilot.schemas import ValidationError


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render deterministic Hermes Manager Pilot Markdown from local session JSON."
    )
    parser.add_argument("--input", required=True, help="Path to local session state JSON.")
    parser.add_argument(
        "--mode",
        required=True,
        choices=sorted(ALLOWED_RENDER_MODES),
        help="Markdown artifact to render.",
    )
    parser.add_argument("--output", help="Optional Markdown output path. Stdout is used when omitted.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        markdown = run_hermes_manager_pilot(args.input, args.mode)
        if args.output:
            output_path = Path(args.output)
            if output_path.parent and not output_path.parent.exists():
                raise ValidationError(f"output_parent_not_found:{output_path.parent}")
            output_path.write_text(markdown, encoding="utf-8")
        else:
            sys.stdout.write(markdown)
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
