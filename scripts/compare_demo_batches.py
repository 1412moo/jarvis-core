"""Compare two Research Council demo batch summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TRIAGE_FIELDS = (
    "confidence_blockers",
    "high_critiques",
    "missing_evidence",
    "warnings",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two scripts/run_demo_batch.py output directories by "
            "input filename and write bounded comparison summaries."
        )
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        required=True,
        help="Directory containing the baseline batch-summary.json.",
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        required=True,
        help="Directory containing the candidate batch-summary.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for comparison-summary.json and comparison-summary.md.",
    )
    parser.add_argument(
        "--baseline-label",
        default="baseline",
        help="Short label for the baseline batch. Defaults to baseline.",
    )
    parser.add_argument(
        "--candidate-label",
        default="candidate",
        help="Short label for the candidate batch. Defaults to candidate.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        baseline_summary = _load_batch_summary(args.baseline_dir, "baseline")
        candidate_summary = _load_batch_summary(args.candidate_dir, "candidate")
        comparison = _build_comparison_summary(
            baseline_summary,
            candidate_summary,
            baseline_label=args.baseline_label,
            candidate_label=args.candidate_label,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
    except ValueError as exc:
        parser.error(str(exc))
    except OSError as exc:
        parser.error(f"could not prepare --output-dir: {exc}")

    json_path = args.output_dir / "comparison-summary.json"
    markdown_path = args.output_dir / "comparison-summary.md"
    json_path.write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        _format_markdown_summary(comparison),
        encoding="utf-8",
    )

    print(
        "Research Council demo batch comparison: "
        f"matched={comparison['matched_count']}, "
        f"baseline_only={comparison['baseline_only_count']}, "
        f"candidate_only={comparison['candidate_only_count']}"
    )
    print(f"Comparison summary: {json_path}")
    print(f"Comparison index: {markdown_path}")
    print(
        "Changed: "
        f"profile={comparison['changed_profile_count']}, "
        f"decision={comparison['changed_decision_count']}, "
        f"triage={comparison['changed_triage_count']}"
    )
    return 0


def _load_batch_summary(directory: Path, label: str) -> dict[str, Any]:
    if not directory.is_dir():
        raise ValueError(f"--{label}-dir must be an existing directory.")

    summary_path = directory / "batch-summary.json"
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} batch-summary.json is missing.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} batch-summary.json is malformed JSON.") from exc
    except OSError as exc:
        raise ValueError(f"{label} batch-summary.json could not be read: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{label} batch-summary.json must contain a JSON object.")
    _items_by_filename(payload, label)
    return payload


def _build_comparison_summary(
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
    *,
    baseline_label: str,
    candidate_label: str,
) -> dict[str, Any]:
    baseline_items = _items_by_filename(baseline_summary, "baseline")
    candidate_items = _items_by_filename(candidate_summary, "candidate")
    all_filenames = sorted(set(baseline_items) | set(candidate_items))

    items = [
        _compare_item(
            filename,
            baseline_items.get(filename),
            candidate_items.get(filename),
        )
        for filename in all_filenames
    ]
    matched_count = sum(1 for item in items if item["match_status"] == "matched")
    baseline_only_count = sum(1 for item in items if item["match_status"] == "baseline_only")
    candidate_only_count = sum(1 for item in items if item["match_status"] == "candidate_only")

    return {
        "baseline_failed_count": baseline_summary.get("failed_count"),
        "baseline_label": baseline_label,
        "baseline_only_count": baseline_only_count,
        "baseline_passed_count": baseline_summary.get("passed_count"),
        "baseline_total_inputs": baseline_summary.get("total_inputs"),
        "candidate_failed_count": candidate_summary.get("failed_count"),
        "candidate_label": candidate_label,
        "candidate_only_count": candidate_only_count,
        "candidate_passed_count": candidate_summary.get("passed_count"),
        "candidate_total_inputs": candidate_summary.get("total_inputs"),
        "changed_decision_count": sum(1 for item in items if item["changed_decision"]),
        "changed_profile_count": sum(1 for item in items if item["changed_profile"]),
        "changed_triage_count": sum(1 for item in items if item["changed_triage"]),
        "items": items,
        "matched_count": matched_count,
        "total_inputs": len(items),
    }


def _items_by_filename(summary: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    items = summary.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{label} batch-summary.json must contain an items list.")

    indexed: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{label} item {index} must be a JSON object.")
        filename = item.get("input_filename")
        if not isinstance(filename, str) or not filename:
            raise ValueError(f"{label} item {index} is missing input_filename.")
        if filename in indexed:
            raise ValueError(f"{label} has duplicate input_filename: {filename}")
        indexed[filename] = item
    return indexed


def _compare_item(
    filename: str,
    baseline: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    match_status = (
        "matched"
        if baseline is not None and candidate is not None
        else "baseline_only"
        if baseline is not None
        else "candidate_only"
    )
    changed_profile = _changed(baseline, candidate, "selected_profile")
    changed_decision = _changed(baseline, candidate, "recommendation_decision")
    changed_triage = any(_changed(baseline, candidate, field) for field in TRIAGE_FIELDS)

    return {
        "baseline_confidence_blockers": _value(baseline, "confidence_blockers"),
        "baseline_high_critiques": _value(baseline, "high_critiques"),
        "baseline_json_filename": _path_name(_value(baseline, "json_output_path")),
        "baseline_markdown_filename": _path_name(_value(baseline, "markdown_output_path")),
        "baseline_missing_evidence": _value(baseline, "missing_evidence"),
        "baseline_recommendation_decision": _value(baseline, "recommendation_decision"),
        "baseline_return_code": _value(baseline, "return_code"),
        "baseline_selected_by": _value(baseline, "selected_by"),
        "baseline_selected_profile": _value(baseline, "selected_profile"),
        "baseline_status": _value(baseline, "status"),
        "baseline_warnings": _value(baseline, "warnings"),
        "candidate_confidence_blockers": _value(candidate, "confidence_blockers"),
        "candidate_high_critiques": _value(candidate, "high_critiques"),
        "candidate_json_filename": _path_name(_value(candidate, "json_output_path")),
        "candidate_markdown_filename": _path_name(_value(candidate, "markdown_output_path")),
        "candidate_missing_evidence": _value(candidate, "missing_evidence"),
        "candidate_recommendation_decision": _value(candidate, "recommendation_decision"),
        "candidate_return_code": _value(candidate, "return_code"),
        "candidate_selected_by": _value(candidate, "selected_by"),
        "candidate_selected_profile": _value(candidate, "selected_profile"),
        "candidate_status": _value(candidate, "status"),
        "candidate_warnings": _value(candidate, "warnings"),
        "changed_decision": changed_decision,
        "changed_profile": changed_profile,
        "changed_triage": changed_triage,
        "input_filename": filename,
        "match_status": match_status,
    }


def _format_markdown_summary(summary: dict[str, Any]) -> str:
    baseline_label = summary["baseline_label"]
    candidate_label = summary["candidate_label"]
    lines = [
        "# Research Council Demo Batch Comparison",
        "",
        f"- Baseline: {_md_code(baseline_label)}",
        f"- Candidate: {_md_code(candidate_label)}",
        f"- Matched: {_md_code(summary.get('matched_count'))}",
        f"- Baseline only: {_md_code(summary.get('baseline_only_count'))}",
        f"- Candidate only: {_md_code(summary.get('candidate_only_count'))}",
        f"- Changed profile: {_md_code(summary.get('changed_profile_count'))}",
        f"- Changed decision: {_md_code(summary.get('changed_decision_count'))}",
        f"- Changed triage: {_md_code(summary.get('changed_triage_count'))}",
        "",
        (
            "| Changed | Input | Profile | Selected by | Decision | Blockers | "
            "High critiques | Missing evidence | Warnings | Baseline MD | Candidate MD |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    items = summary.get("items", [])
    if isinstance(items, list):
        for item in sorted(
            (item for item in items if isinstance(item, dict)),
            key=_markdown_sort_key,
        ):
            lines.append(
                "| "
                + " | ".join(
                    (
                        _md_cell(_changed_label(item)),
                        _md_cell(item.get("input_filename")),
                        _md_cell(
                            _arrow(
                                item.get("baseline_selected_profile"),
                                item.get("candidate_selected_profile"),
                            )
                        ),
                        _md_cell(
                            _arrow(
                                item.get("baseline_selected_by"),
                                item.get("candidate_selected_by"),
                            )
                        ),
                        _md_cell(
                            _arrow(
                                item.get("baseline_recommendation_decision"),
                                item.get("candidate_recommendation_decision"),
                            )
                        ),
                        _md_cell(
                            _arrow(
                                item.get("baseline_confidence_blockers"),
                                item.get("candidate_confidence_blockers"),
                            )
                        ),
                        _md_cell(
                            _arrow(
                                item.get("baseline_high_critiques"),
                                item.get("candidate_high_critiques"),
                            )
                        ),
                        _md_cell(
                            _arrow(
                                item.get("baseline_missing_evidence"),
                                item.get("candidate_missing_evidence"),
                            )
                        ),
                        _md_cell(_arrow(item.get("baseline_warnings"), item.get("candidate_warnings"))),
                        _md_cell(item.get("baseline_markdown_filename")),
                        _md_cell(item.get("candidate_markdown_filename")),
                    )
                )
                + " |"
            )
    return "\n".join(lines) + "\n"


def _markdown_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    profile_or_decision = bool(item.get("changed_profile") or item.get("changed_decision"))
    triage = bool(item.get("changed_triage"))
    one_sided = item.get("match_status") != "matched"
    filename = str(item.get("input_filename") or "")
    return (
        0 if one_sided else 1,
        0 if profile_or_decision else 1,
        0 if triage else 1,
        filename,
    )


def _changed_label(item: dict[str, Any]) -> str:
    if item.get("match_status") != "matched":
        return str(item.get("match_status") or "unmatched")
    labels: list[str] = []
    if item.get("changed_profile"):
        labels.append("profile")
    if item.get("changed_decision"):
        labels.append("decision")
    if item.get("changed_triage"):
        labels.append("triage")
    return ", ".join(labels) if labels else "none"


def _changed(
    baseline: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
    field: str,
) -> bool:
    return baseline is not None and candidate is not None and baseline.get(field) != candidate.get(field)


def _value(item: dict[str, Any] | None, field: str) -> object:
    return item.get(field) if item is not None else None


def _path_name(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return Path(value).name


def _arrow(baseline: object, candidate: object) -> str:
    return f"{_display(baseline)} -> {_display(candidate)}"


def _display(value: object) -> str:
    return str(value if value not in (None, "") else "n/a")


def _md_cell(value: object) -> str:
    return _display(value).replace("|", "\\|").replace("\n", " ")


def _md_code(value: object) -> str:
    return f"`{_display(value).replace('`', '\\`')}`"


if __name__ == "__main__":
    raise SystemExit(main())
