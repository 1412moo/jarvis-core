"""Optional LLM advisor skeleton for Research Council.

This module intentionally does not call an LLM. It only defines the future
extension boundary: an LLM may add advisory observations after the deterministic
pipeline has produced the source-of-truth result.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMInsightBundle:
    """Optional advisory notes that cannot replace deterministic artifacts."""

    observations: tuple[str, ...] = ()
    follow_up_questions: tuple[str, ...] = ()
    evidence_requests: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    confidence_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", _tuple_of_strings(self.observations))
        object.__setattr__(
            self,
            "follow_up_questions",
            _tuple_of_strings(self.follow_up_questions),
        )
        object.__setattr__(
            self,
            "evidence_requests",
            _tuple_of_strings(self.evidence_requests),
        )
        object.__setattr__(self, "risk_flags", _tuple_of_strings(self.risk_flags))
        object.__setattr__(self, "caveats", _tuple_of_strings(self.caveats))
        object.__setattr__(
            self,
            "confidence_notes",
            _tuple_of_strings(self.confidence_notes),
        )


class LLMResearchAdvisor:
    """Future optional collaborator interface.

    Implementations must consume a completed deterministic result and return an
    advisory bundle. They must not mutate claims, evidence, critiques,
    experiments, recommendation, warnings, profile metadata, or quality signals.
    """

    def advise(
        self,
        deterministic_result: Any,
        *,
        domain_profile: Any = None,
    ) -> LLMInsightBundle:
        raise NotImplementedError(
            "LLMResearchAdvisor is an optional future extension and is not wired "
            "into the deterministic Research Council pipeline."
        )


def validate_llm_insight_bundle(bundle: LLMInsightBundle) -> tuple[str, ...]:
    """Return deterministic validation issues for an optional LLM bundle."""

    issues: list[str] = []
    combined_text = " ".join(_all_bundle_text(bundle)).lower()
    blocked_phrases = (
        "replace deterministic",
        "override deterministic",
        "source of truth",
        "validated by the llm",
    )
    for phrase in blocked_phrases:
        if phrase in combined_text:
            issues.append(
                f"LLM advisory bundle must not claim deterministic replacement: {phrase}"
            )
    return tuple(issues)


def _all_bundle_text(bundle: LLMInsightBundle) -> tuple[str, ...]:
    return (
        bundle.observations
        + bundle.follow_up_questions
        + bundle.evidence_requests
        + bundle.risk_flags
        + bundle.caveats
        + bundle.confidence_notes
    )


def _tuple_of_strings(values: Sequence[str] | str | None) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    return tuple(str(value).strip() for value in values if str(value).strip())


__all__ = [
    "LLMInsightBundle",
    "LLMResearchAdvisor",
    "validate_llm_insight_bundle",
]
