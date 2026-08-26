"""Deterministic Phase A smoke tests for team-manager-bot.

Exercises only the credential-free, network-free paths: --self-check and the
missing-token error path. Never imports discord.py's networking pieces in a
way that could attempt a connection, never reads or writes an env var value,
and never touches memory/tasks, prompts, or access.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
BOT_SCRIPT = THIS_DIR / "bot_minimal.py"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BOT_SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
        env=env,
    )


def test_self_check_returns_stub_reply() -> None:
    completed = _run(["--self-check", "hello team manager"])
    _assert(completed.returncode == 0, f"expected exit 0, got {completed.returncode}: {completed.stderr}")
    payload = json.loads(completed.stdout)
    _assert(payload["result_type"] == "stub_reply", "must be a stub_reply")
    _assert(payload["input"] == "hello team manager", "input must be echoed back")
    _assert(payload["llm_result"] is None, "Phase A llm_result must always be null")
    _assert(isinstance(payload["reply"], str) and payload["reply"], "reply must be a non-empty string")


def test_self_check_rejects_empty_input() -> None:
    completed = _run(["--self-check", ""])
    _assert(completed.returncode == 1, "empty self-check input must fail")
    payload = json.loads(completed.stdout)
    _assert(payload["result_type"] == "error", "must be an error result")
    _assert(payload["reason"] == "usage:--self-check <text>", "must report usage reason")


def test_missing_token_fails_closed_without_self_check() -> None:
    env = {key: value for key, value in os.environ.items() if key != "TEAM_MANAGER_BOT_TOKEN"}
    completed = _run([], env=env)
    _assert(completed.returncode == 1, "missing token must exit non-zero")
    payload = json.loads(completed.stdout)
    _assert(payload["result_type"] == "error", "must be an error result")
    _assert(
        payload["reason"] == "missing_env:TEAM_MANAGER_BOT_TOKEN",
        "must report the exact missing-env reason",
    )


def main() -> None:
    test_self_check_returns_stub_reply()
    test_self_check_rejects_empty_input()
    test_missing_token_fails_closed_without_self_check()
    print("team-manager-bot Phase A smoke tests passed")


if __name__ == "__main__":
    main()
