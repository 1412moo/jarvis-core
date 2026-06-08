"""Run Research Council demo inputs as a deterministic local batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


LLM_AUGMENTATION_MODES = ("off", "test_safe", "test_noisy")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run apps/research-council/run_demo.py for each JSON input in a "
            "directory and write per-case Markdown/JSON outputs."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing local Research Council input *.json files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for per-case Markdown/JSON output and batch-summary.json.",
    )
    parser.add_argument(
        "--profile",
        help="Optional deterministic profile id or alias to pass through to run_demo.py.",
    )
    parser.add_argument(
        "--llm-augmentation-mode",
        choices=LLM_AUGMENTATION_MODES,
        default="off",
        help=(
            "Optional deterministic augmentation sandbox mode to pass through to "
            "run_demo.py. Defaults to off."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir
    if not input_dir.is_dir():
        parser.error("--input-dir must be an existing directory.")

    input_paths = sorted(input_dir.glob("*.json"), key=lambda path: path.name)
    if not input_paths:
        parser.error("--input-dir must contain at least one *.json file.")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        parser.error(f"--output-dir could not be created: {exc}")

    run_demo_path = (
        Path(__file__).resolve().parents[1]
        / "apps"
        / "research-council"
        / "run_demo.py"
    )
    summary_path = output_dir / "batch-summary.json"
    print(f"Research Council demo batch: inputs={len(input_paths)}")
    print(f"Output dir: {output_dir}")

    items: list[dict[str, Any]] = []
    failed_return_code = 0
    for input_path in input_paths:
        markdown_path = output_dir / f"{input_path.stem}.md"
        json_path = output_dir / f"{input_path.stem}.json"
        command = [
            sys.executable,
            "-B",
            str(run_demo_path),
            "--input-json",
            str(input_path),
            "--output",
            str(markdown_path),
            "--json-output",
            str(json_path),
            "--llm-augmentation-mode",
            args.llm_augmentation_mode,
        ]
        if args.profile:
            command.extend(["--profile", args.profile])

        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        status = "ok" if completed.returncode == 0 else "failed"
        item: dict[str, Any] = {
            "input_filename": input_path.name,
            "markdown_output_path": str(markdown_path),
            "json_output_path": str(json_path),
            "return_code": completed.returncode,
            "status": status,
        }
        if status == "ok":
            item.update(_safe_result_metadata(json_path))
            print(f"- {input_path.name}: ok")
        else:
            failed_return_code = completed.returncode or 1
            print(f"- {input_path.name}: failed (exit {completed.returncode})")
        items.append(item)
        if status == "failed":
            break

    passed_count = sum(1 for item in items if item["status"] == "ok")
    failed_count = sum(1 for item in items if item["status"] == "failed")
    summary = {
        "failed_count": failed_count,
        "items": items,
        "passed_count": passed_count,
        "total_inputs": len(input_paths),
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Batch summary: {summary_path}")
    print(f"Completed: ok={passed_count}, failed={failed_count}")
    return failed_return_code


def _safe_result_metadata(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"metadata_status": "unavailable"}

    metadata: dict[str, Any] = {}
    profile = payload.get("profile")
    if isinstance(profile, dict):
        profile_id = _string_or_none(profile.get("profile_id"))
        if profile_id:
            metadata["profile_id"] = profile_id

    recommendation = payload.get("recommendation")
    if isinstance(recommendation, dict):
        decision = _string_or_none(recommendation.get("decision"))
        if decision:
            metadata["recommendation_decision"] = decision

    counts: dict[str, int] = {}
    for payload_key, count_key in (
        ("claims", "claims"),
        ("evidence_ledger", "evidence_entries"),
        ("experiments", "experiments"),
        ("reviewer_critiques", "reviewer_critiques"),
        ("warnings", "warnings"),
    ):
        value = payload.get(payload_key)
        if isinstance(value, list):
            counts[count_key] = len(value)
    if counts:
        metadata["counts"] = counts

    return metadata


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


if __name__ == "__main__":
    raise SystemExit(main())
