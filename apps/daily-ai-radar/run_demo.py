"""Run the Daily AI Radar v0.2 deterministic report renderer."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from daily_ai_radar.pipeline import run_daily_ai_radar
from daily_ai_radar.report_renderer import render_markdown_report
from daily_ai_radar.schemas import ValidationError


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a deterministic Daily AI Radar Markdown report from local curated metadata."
    )
    parser.add_argument("--input", required=True, help="Path to local curated source metadata JSON.")
    parser.add_argument("--output", help="Optional Markdown output path. Stdout is used when omitted.")
    parser.add_argument("--radar-date", help="Optional YYYY-MM-DD radar date override.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        result = run_daily_ai_radar(args.input, radar_date_override=args.radar_date)
        markdown = render_markdown_report(result)
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
