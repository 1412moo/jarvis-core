"""LLM provider boundary for team-manager-bot (Phase A stub).

Phase A boundary only: no network client, no external API, no subprocess,
and no credential/environment-variable dependency. This module is the ONLY
place a future LLM call is allowed to happen; the bot skeleton treats its
return value as untrusted data.

Approved under docs/chatgpt-discord-claude-auto-collab-v0.1-design.md. Phase
B (credential issuance) and Phase C (wiring a real provider call into the
body of `call_llm_for_intent`) are separate, explicitly Owner-approved steps
per that design. The function contract (`str -> dict | None`, never raises)
must not change, so callers never need to change when a real provider is
wired in.

Mirrors orchestrator/discord-nl-intent/llm_provider.py's Phase 2A stub
pattern deliberately -- same contract, same boundary, different bot.
"""

from __future__ import annotations

from typing import Any


def call_llm_for_intent(text: str) -> dict[str, Any] | None:
    """Phase A: always returns None. No network, subprocess, or API key.

    Once Phase B/C are approved and a provider is wired in, this function may
    call it, but must still return None on any timeout, error, or malformed
    response -- never raise, never propagate a provider-specific exception.
    """

    return None


__all__ = ["call_llm_for_intent"]
