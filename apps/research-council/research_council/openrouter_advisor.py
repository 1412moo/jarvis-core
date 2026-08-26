"""OpenRouter live augmentation adapter for Research Council.

This adapter is the only place in the repository that performs an external LLM
call. It is reachable exclusively through ``LLMAugmentationMode.LIVE``, which no
default selects and which the deterministic runners refuse.

The adapter produces ``LLMAugmentationCandidate`` values and nothing else. Every
candidate still passes the deterministic validation filters in ``llm_advisor``
before it can reach a result, and the merged output is confined to the single
``optional_llm_augments`` field. The deterministic source of truth is read-only
here.

Failure is never propagated. A missing key, a timeout, a rate limit, a transport
error or a malformed response all return an empty tuple, which validates into an
OFF-equivalent result.

Approved under package research-council-live-augmentation-v0.1.
"""

from __future__ import annotations

from collections.abc import Sequence
import json
import os
import urllib.error
import urllib.request
from typing import Any

from .llm_advisor import ALLOWED_AUGMENTATION_CATEGORIES, LLMAugmentationCandidate


OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"

# Verified against the official OpenRouter endpoints API and the authoritative
# Zero Data Retention list at https://openrouter.ai/api/v1/endpoints/zdr on
# 2026-08-25. Provider and model are pinned; OpenRouter routing and fallback are
# disabled, so these two constants fully determine where a request goes.
OPENROUTER_MODEL_ID = "z-ai/glm-4.6"
OPENROUTER_PROVIDER_TAG = "deepinfra/fp4"
OPENROUTER_CONTEXT_LENGTH = 202752
OPENROUTER_PRICE_PROMPT = "0.0000005"
OPENROUTER_PRICE_COMPLETION = "0.000002"

REQUEST_TIMEOUT_SECONDS = 20
MAX_OUTPUT_TOKENS = 700
MAX_CANDIDATES = 5
MAX_CANDIDATE_CHARS = 400
REQUEST_SEED = 7

LIVE_SOURCE = "openrouter_live_advisor"

_SYSTEM_PROMPT = (
    "You add optional review notes to an evaluation that is already final. "
    "You cannot change, restate, rank or overrule any part of it. "
    "Return JSON only, shaped as "
    '{"suggestions": [{"category": "...", "text": "..."}]}. '
    "Allowed category values: "
    + ", ".join(sorted(ALLOWED_AUGMENTATION_CATEGORIES))
    + ". Each text is one sentence, under 400 characters, plainly worded, and "
    "adds something the evaluation does not already say. Never restate the "
    "recommendation, never claim higher confidence, never ask for hidden "
    "reasoning, and never echo the raw input. Return at most "
    + str(MAX_CANDIDATES)
    + " suggestions. Return an empty list rather than padding."
)


def build_openrouter_payload(deterministic_text: str, profile_id: str) -> dict[str, Any]:
    """Build the exact request body, with routing pinned and fallbacks disabled."""

    return {
        "model": OPENROUTER_MODEL_ID,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Domain profile: {profile_id}\n"
                    f"Final evaluation:\n{deterministic_text}"
                ),
            },
        ],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0,
        "seed": REQUEST_SEED,
        "provider": {
            "order": [OPENROUTER_PROVIDER_TAG],
            "allow_fallbacks": False,
            "zdr": True,
            "data_collection": "deny",
        },
    }


def openrouter_candidates(
    deterministic_result: Any,
    *,
    input_data: Any = None,
    domain_profile: Any = None,
    config: Any = None,
) -> tuple[LLMAugmentationCandidate, ...]:
    """Return live candidates, or an empty tuple when anything goes wrong."""

    api_key = os.environ.get(OPENROUTER_API_KEY_ENV, "").strip()
    if not api_key:
        return ()

    profile_id = str(getattr(domain_profile, "id", "") or "")
    deterministic_text = _summarize_for_prompt(deterministic_result)
    payload = build_openrouter_payload(deterministic_text, profile_id)

    try:
        raw = _post_json(payload, api_key)
    except Exception:  # noqa: BLE001 - degrade, never propagate
        return ()
    return parse_openrouter_candidates(raw)


def parse_openrouter_candidates(raw: Any) -> tuple[LLMAugmentationCandidate, ...]:
    """Parse a response body into candidates, tolerating any malformed shape."""

    try:
        choices = raw["choices"]
        content = choices[0]["message"]["content"]
    except (TypeError, KeyError, IndexError):
        return ()
    if not isinstance(content, str):
        return ()
    try:
        parsed = json.loads(_strip_code_fence(content))
    except (ValueError, TypeError):
        return ()
    suggestions = parsed.get("suggestions") if isinstance(parsed, dict) else None
    if not isinstance(suggestions, (list, tuple)):
        return ()

    candidates: list[LLMAugmentationCandidate] = []
    for suggestion in suggestions:
        if len(candidates) >= MAX_CANDIDATES:
            break
        if not isinstance(suggestion, dict):
            continue
        category = str(suggestion.get("category", "") or "").strip()
        text = str(suggestion.get("text", "") or "").strip()
        if category not in ALLOWED_AUGMENTATION_CATEGORIES:
            continue
        if not text or len(text) > MAX_CANDIDATE_CHARS:
            continue
        candidates.append(
            LLMAugmentationCandidate(
                category=category,
                text=text,
                source=LIVE_SOURCE,
            )
        )
    return tuple(candidates)


def _post_json(payload: dict[str, Any], api_key: str) -> Any:
    request = urllib.request.Request(
        OPENROUTER_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise OpenRouterCallFailed(f"http status {exc.code}") from None
    except urllib.error.URLError:
        raise OpenRouterCallFailed("transport error") from None


class OpenRouterCallFailed(RuntimeError):
    """Raised internally on a failed call; the message never carries the key."""


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    body = lines[1:]
    if body and body[-1].strip().startswith("```"):
        body = body[:-1]
    return "\n".join(body).strip()


def _summarize_for_prompt(deterministic_result: Any) -> str:
    parts: list[str] = []
    summary = getattr(deterministic_result, "input_summary", "")
    if summary:
        parts.append(f"Summary: {summary}")
    recommendation = getattr(deterministic_result, "recommendation", None)
    decision = getattr(recommendation, "decision", "")
    if decision:
        parts.append(f"Recommendation: {decision}")
    parts.append(f"Claims: {_count(getattr(deterministic_result, 'claims', ()))}")
    parts.append(
        f"Critiques: {_count(getattr(deterministic_result, 'reviewer_critiques', ()))}"
    )
    parts.append(
        f"Experiments: {_count(getattr(deterministic_result, 'experiments', ()))}"
    )
    return "\n".join(parts)


def _count(value: Any) -> int:
    if isinstance(value, Sequence):
        return len(value)
    return 0


__all__ = [
    "LIVE_SOURCE",
    "OPENROUTER_API_KEY_ENV",
    "OPENROUTER_CONTEXT_LENGTH",
    "OPENROUTER_ENDPOINT",
    "OPENROUTER_MODEL_ID",
    "OPENROUTER_PRICE_COMPLETION",
    "OPENROUTER_PRICE_PROMPT",
    "OPENROUTER_PROVIDER_TAG",
    "OpenRouterCallFailed",
    "build_openrouter_payload",
    "openrouter_candidates",
    "parse_openrouter_candidates",
]
