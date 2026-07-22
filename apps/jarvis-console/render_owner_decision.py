"""Render a bounded Owner Decision JSON document from stdin to stdout."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys
from typing import TextIO

from owner_decision import (
    MAX_JSON_BYTES,
    OwnerDecisionError,
    parse_owner_decision_json,
    render_owner_decision_markdown,
    serialize_owner_decision,
)


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Read only stdin and write one deterministic rendering to stdout."""

    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr
    parser = argparse.ArgumentParser(
        description="Render Owner Decision v0.1A JSON from stdin without persistence."
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format; both formats are written to stdout only.",
    )
    args = parser.parse_args(argv)

    text = input_stream.read(MAX_JSON_BYTES + 1)
    try:
        decision = parse_owner_decision_json(text)
        if args.format == "json":
            rendered = serialize_owner_decision(decision) + "\n"
        else:
            rendered = render_owner_decision_markdown(decision)
    except (OwnerDecisionError, UnicodeError) as exc:
        error_stream.write(f"Owner Decision error: {exc}\n")
        return 2
    output_stream.write(rendered)
    return 0


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
