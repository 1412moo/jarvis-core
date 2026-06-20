"""Deterministic pipeline for Daily AI Radar curated metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import DailyAIRadarInput, DailyAIRadarResult, ValidationError, build_result, normalize_input


def load_input_file(input_path: str | Path, radar_date_override: str | None = None) -> DailyAIRadarInput:
    """Load and validate a local curated metadata JSON file."""

    path = Path(input_path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"input_read_failed:{path}") from exc

    try:
        payload: Any = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"input_json_invalid:{exc.msg}") from exc

    return normalize_input(payload, radar_date_override=radar_date_override)


def run_daily_ai_radar(
    input_path: str | Path,
    radar_date_override: str | None = None,
) -> DailyAIRadarResult:
    """Run the v0.2 local deterministic renderer pipeline."""

    input_data = load_input_file(input_path, radar_date_override=radar_date_override)
    return build_result(input_data)
