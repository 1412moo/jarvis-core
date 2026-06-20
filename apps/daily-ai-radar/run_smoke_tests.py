"""Smoke tests for the Daily AI Radar v0.2 deterministic renderer."""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
from pathlib import Path

from daily_ai_radar.pipeline import run_daily_ai_radar
from daily_ai_radar.report_renderer import render_markdown_report
from daily_ai_radar.schemas import ValidationError, build_result, normalize_input


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent.parent
SAMPLE_INPUT = APP_ROOT / "examples" / "sample-input.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _sample_payload() -> dict[str, object]:
    import json

    return json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))


def _render_sample() -> str:
    result = run_daily_ai_radar(SAMPLE_INPUT)
    return render_markdown_report(result)


def _test_sample_report_sections() -> None:
    report = _render_sample()
    _assert(report.startswith("# Daily AI Radar Report\n"), "report title missing")
    for expected in (
        "## Executive Summary",
        "## Candidate Highlights",
        "## Candidate Details",
        "## Governance Notes",
        "This report is not implementation approval.",
    ):
        _assert(expected in report, f"missing report section or note: {expected}")


def _test_raw_body_rejected_and_not_rendered() -> None:
    for raw_field in ("source_body", "raw_body", "full_text", "content"):
        payload = _sample_payload()
        items = payload["items"]
        assert isinstance(items, list)
        first_item = items[0]
        assert isinstance(first_item, dict)
        first_item[raw_field] = "This full source body must never be accepted."
        try:
            normalize_input(payload)
        except ValidationError as exc:
            _assert(f"{raw_field} is not allowed" in str(exc), f"unexpected validation error: {exc}")
        else:
            raise AssertionError(f"{raw_field} field should fail validation")

    report = _render_sample()
    _assert("This full source body must never be accepted." not in report, "raw body leaked")
    _assert("source_body" not in report, "raw body field name leaked")


def _test_high_risk_routing() -> None:
    result = run_daily_ai_radar(SAMPLE_INPUT)
    recommendations = {item.item_id: item.recommendation for item in result.items}
    _assert(
        recommendations["radar-002"] in {"NEEDS_RESEARCH_COUNCIL", "NEEDS_HUMAN_REVIEW"},
        "Hermes self-improvement fixture should route to review",
    )
    _assert(
        recommendations["radar-003"] in {"NEEDS_RESEARCH_COUNCIL", "NEEDS_HUMAN_REVIEW"},
        "MCP security fixture should route to review",
    )
    _assert(
        recommendations["radar-005"] in {"NEEDS_RESEARCH_COUNCIL", "NEEDS_HUMAN_REVIEW"},
        "high-risk recursive self-improvement context should route to review",
    )


def _test_explicit_recommendation_safety_override() -> None:
    payload = _sample_payload()
    payload["items"] = [
        {
            "item_id": "radar-999",
            "observed_date": "2026-06-18",
            "source_name": "Manual MCP edge note",
            "source_type": "fixture",
            "source_url_or_ref": "source_ref:explicit-do-now-mcp-risk",
            "title": "MCP high-risk explicit recommendation edge",
            "summary": "Fixture metadata for a high-risk MCP permission boundary.",
            "claimed_capability": "The source claims a tool permission pattern may be useful.",
            "area": "mcp",
            "evidence_level": "manual_summary",
            "notes": "Explicit DO_NOW must not bypass the safety gate.",
            "relevance_to_jarvis": 5,
            "implementation_effort": 3,
            "risk": 5,
            "urgency": 4,
            "maturity": 3,
            "recommendation": "DO_NOW",
        }
    ]
    result = build_result(normalize_input(payload))
    item = result.items[0]
    _assert(item.recommendation == "NEEDS_HUMAN_REVIEW", "explicit DO_NOW bypassed MCP safety gate")
    _assert(item.recommendation_source == "safety_override", "safety override source not recorded")


def _test_self_improvement_high_risk_routing() -> None:
    payload = _sample_payload()
    payload["items"] = [
        {
            "item_id": "radar-998",
            "observed_date": "2026-06-18",
            "source_name": "Manual self-improvement edge note",
            "source_type": "fixture",
            "source_url_or_ref": "source_ref:self-improvement-risk",
            "title": "Recursive self-improvement control loop",
            "summary": "Fixture metadata about recursive self-improvement and self-modification behavior.",
            "claimed_capability": "The source claims an agent can improve itself from repeated work.",
            "area": "unknown",
            "evidence_level": "unverified_claim",
            "notes": "Self-modification language with risk must route to review.",
            "relevance_to_jarvis": 3,
            "implementation_effort": 4,
            "risk": 3,
            "urgency": 3,
            "maturity": 1,
        }
    ]
    result = build_result(normalize_input(payload))
    _assert(
        result.items[0].recommendation in {"NEEDS_RESEARCH_COUNCIL", "NEEDS_HUMAN_REVIEW"},
        "high-risk self-improvement should route to review",
    )


def _test_invalid_score_fails() -> None:
    for invalid_value in (0, 6, "high"):
        payload = _sample_payload()
        items = payload["items"]
        assert isinstance(items, list)
        first_item = copy.deepcopy(items[0])
        assert isinstance(first_item, dict)
        first_item["risk"] = invalid_value
        payload["items"] = [first_item]
        try:
            normalize_input(payload)
        except ValidationError as exc:
            _assert("risk must be" in str(exc), f"unexpected error: {exc}")
        else:
            raise AssertionError(f"invalid score should fail: {invalid_value!r}")


def _test_missing_required_field_fails() -> None:
    payload = _sample_payload()
    items = payload["items"]
    assert isinstance(items, list)
    first_item = copy.deepcopy(items[0])
    assert isinstance(first_item, dict)
    del first_item["title"]
    payload["items"] = [first_item]
    try:
        normalize_input(payload)
    except ValidationError as exc:
        _assert("title must be a non-empty string" in str(exc), f"unexpected error: {exc}")
    else:
        raise AssertionError("missing required field should fail")


def _test_unknown_area_fails() -> None:
    payload = _sample_payload()
    items = payload["items"]
    assert isinstance(items, list)
    first_item = copy.deepcopy(items[0])
    assert isinstance(first_item, dict)
    first_item["area"] = "not_a_real_area"
    payload["items"] = [first_item]
    try:
        normalize_input(payload)
    except ValidationError as exc:
        _assert("area is invalid" in str(exc), f"unexpected error: {exc}")
    else:
        raise AssertionError("invalid area should fail")


def _test_stdout_mode_does_not_create_repo_file() -> None:
    before = _repo_file_set()
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(APP_ROOT / "run_demo.py"),
            "--input",
            str(SAMPLE_INPUT),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    after = _repo_file_set()
    _assert(completed.returncode == 0, f"stdout demo failed: {completed.stderr}")
    _assert("# Daily AI Radar Report" in completed.stdout, "stdout report missing")
    _assert(before == after, "stdout mode created or removed repository files")


def _test_output_mode_writes_only_requested_file() -> None:
    before = _repo_file_set()
    with tempfile.TemporaryDirectory(prefix="daily-ai-radar-smoke-") as temp_dir:
        output_path = Path(temp_dir) / "radar-report.md"
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(APP_ROOT / "run_demo.py"),
                "--input",
                str(SAMPLE_INPUT),
                "--output",
                str(output_path),
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        after = _repo_file_set()
        _assert(completed.returncode == 0, f"output demo failed: {completed.stderr}")
        _assert(output_path.exists(), "explicit output file was not created")
        _assert("# Daily AI Radar Report" in output_path.read_text(encoding="utf-8"), "output report missing")
        _assert(before == after, "output mode changed repository files")


def _repo_file_set() -> set[str]:
    return {
        str(path.relative_to(REPO_ROOT))
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


def _test_radar_date_default_and_override() -> None:
    payload = _sample_payload()
    payload.pop("radar_date", None)
    input_data = normalize_input(payload)
    _assert(input_data.radar_date == "2026-06-18", "missing radar_date should use fixed default")
    override_input = normalize_input(payload, radar_date_override="2026-06-20")
    result = build_result(override_input)
    _assert(result.radar_date == "2026-06-20", "radar date override not applied")


def main() -> None:
    tests = (
        _test_sample_report_sections,
        _test_raw_body_rejected_and_not_rendered,
        _test_high_risk_routing,
        _test_explicit_recommendation_safety_override,
        _test_self_improvement_high_risk_routing,
        _test_invalid_score_fails,
        _test_missing_required_field_fails,
        _test_unknown_area_fails,
        _test_stdout_mode_does_not_create_repo_file,
        _test_output_mode_writes_only_requested_file,
        _test_radar_date_default_and_override,
    )
    for test in tests:
        test()
    print("Daily AI Radar smoke tests passed")


if __name__ == "__main__":
    main()
