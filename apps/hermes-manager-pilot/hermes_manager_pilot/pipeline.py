"""Local deterministic pipeline for Hermes Manager Pilot v0.2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .prompt_renderer import render_mode
from .schemas import SessionState, ValidationError, normalize_session_state


def load_session_file(input_path: str | Path) -> SessionState:
    """Load and validate a local Hermes Manager Pilot session JSON file."""

    path = Path(input_path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"input_read_failed:{path}") from exc

    try:
        payload: Any = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"input_json_invalid:{exc.msg}") from exc

    return normalize_session_state(payload)


def run_hermes_manager_pilot(input_path: str | Path, mode: str) -> str:
    """Run the v0.2 local session/prompt renderer pipeline."""

    session = load_session_file(input_path)
    return render_mode(session, mode)
