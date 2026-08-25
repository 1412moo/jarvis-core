"""LLM provider boundary for the Discord NL intent layer (Phase 2A stub).

Phase 2A boundary only: no network client, no external API, no subprocess,
and no credential/environment-variable dependency. This module is the ONLY
place a future LLM call is allowed to happen; every other module in this
package treats its return value as untrusted data.

Phase 2B (a separate, explicitly Owner-approved package -- per
docs/codex-operating-rules.md, the OpenRouter approval scope for
research-council-live-augmentation-v0.1 explicitly excludes Hermes and the
Discord adapter, so this needs its own approval) may replace only the body of
`call_llm_for_intent` with a real provider call. The function contract
(`str -> dict | None`, never raises) must not change, so callers never need
to change when a real provider is wired in.
"""

from __future__ import annotations

from typing import Any


def call_llm_for_intent(text: str) -> dict[str, Any] | None:
    """Phase 2A: always returns None. No network, subprocess, or API key.

    Once a provider is approved and wired in (Phase 2B), this function may
    call it, but must still return None on any timeout, error, or malformed
    response -- never raise, never propagate a provider-specific exception.
    """

    return None


__all__ = ["call_llm_for_intent"]
