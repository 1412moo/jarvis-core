"""Phase A skeleton for team-manager-bot (ChatGPT relay identity, Discord).

Approved scope (docs/chatgpt-discord-claude-auto-collab-v0.1-design.md,
task-0031): credential-free scaffolding only.

Explicit Phase A boundary:
- No Discord bot token is created, read from a real value, or connected.
- No external API (OpenAI or otherwise) is called. llm_provider.py is a
  stub that always returns None.
- No cost, no deployment, no long-running process is started by this file
  during Phase A. Only `--self-check` is exercised locally.
- This module never writes to ~/.claude/channels/discord/access.json,
  memory/tasks/*.md, or prompts/*.md. Approval-gate ownership stays with
  Owner/Claude Code exactly as docs/ai-team-operating-model.md defines --
  this bot is never given that write authority, in any phase.
- Does not import, read, or modify anything under adapters/discord/ (the
  existing jarvis-bot / discord-intake bot stays untouched).

Phase B (credential issuance), Phase C (wiring a real LLM call into
llm_provider.call_llm_for_intent), and Phase D (deployment) are separate,
explicitly Owner-approved follow-up steps. This file's real-connection path
(`main()`) is present as inert skeleton for those later phases and is not
invoked anywhere in Phase A.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    import discord
except ModuleNotFoundError:
    discord = None  # type: ignore[assignment]

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from llm_provider import call_llm_for_intent

TEAM_MANAGER_BOT_TOKEN_ENV = "TEAM_MANAGER_BOT_TOKEN"

STUB_REPLY_TEXT = (
    "team-manager-bot Phase A stub: no live LLM connection configured yet."
)


def _build_stub_reply(text: str) -> dict[str, Any]:
    """Pure function: run the stub LLM boundary and shape a deterministic reply.

    Never touches Discord, the network, or any repo write path. Used by both
    `--self-check` and (once Phase C wires a real client in) the eventual
    on_message handler, so the two paths stay provably identical.
    """

    llm_result = call_llm_for_intent(text)
    return {
        "result_type": "stub_reply",
        "input": text,
        "llm_result": llm_result,
        "reply": STUB_REPLY_TEXT,
    }


def _run_self_check(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"result_type": "error", "reason": "usage:--self-check <text>"}
    return _build_stub_reply(text)


def _missing_env_error() -> dict[str, Any]:
    return {
        "result_type": "error",
        "reason": f"missing_env:{TEAM_MANAGER_BOT_TOKEN_ENV}",
    }


class _TeamManagerBotClient:
    """Inert skeleton for the future real Discord client (Phase C+).

    Not instantiated or connected anywhere in Phase A. Kept here only so the
    eventual on_message wiring has a single, already-reviewed shape to fill
    in rather than being designed from scratch under a live credential.
    """

    def __init__(self, token: str) -> None:
        if discord is None:
            raise RuntimeError("discord.py is not installed")
        self._token = token

    async def on_message_stub(self, message_text: str) -> dict[str, Any]:
        """Same pure stub path as --self-check; no side effects."""

        return _build_stub_reply(message_text)

    def run(self) -> None:  # pragma: no cover - not exercised in Phase A
        raise NotImplementedError(
            "Phase A does not connect to Discord. This path is reserved for "
            "Phase C+ after Owner approval."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--self-check", metavar="TEXT", default=None)
    args = parser.parse_args(argv)

    if args.self_check is not None:
        result = _run_self_check(args.self_check)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("result_type") != "error" else 1

    token = os.environ.get(TEAM_MANAGER_BOT_TOKEN_ENV, "").strip()
    if not token:
        result = _missing_env_error()
        print(json.dumps(result, ensure_ascii=False))
        return 1

    # Phase A never reaches here in practice (no token is issued yet), and
    # even if a token were present, connecting is out of scope until Phase C.
    raise NotImplementedError(
        "Phase A does not start a live connection. See "
        "docs/chatgpt-discord-claude-auto-collab-v0.1-design.md."
    )


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "TEAM_MANAGER_BOT_TOKEN_ENV",
    "call_llm_for_intent",
    "main",
]
