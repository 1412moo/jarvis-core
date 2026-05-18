"""Evidence ledger construction for deterministic Research Council runs.

The stable v0.1 EvidenceEntry schema supports only ``provided`` and ``missing``
as evidence_type values. This module preserves that contract and records richer
local statuses in notes as ``status=<value>``:

- provided
- assumed
- missing
- needs_external_validation
"""

from __future__ import annotations

import re
from typing import Any

from .claim_extractor import (
    EVIDENCE_GAP_CATEGORIES,
    _coerce_input,
    domain_profile_for,
    evidence_request_for,
)
from .schemas import Claim, EvidenceEntry


EVIDENCE_STATUSES = frozenset(
    {"provided", "assumed", "missing", "needs_external_validation"}
)

_STATUS_BY_SOURCE_LABEL = {
    "user_provided": "provided",
    "extracted": "missing",
    "assumed": "assumed",
    "needs_evidence": "needs_external_validation",
}

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "before",
        "but",
        "by",
        "for",
        "from",
        "if",
        "in",
        "is",
        "it",
        "of",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)


def build_evidence_ledger(
    input_data: Any,
    claims: list[Claim] | tuple[Claim, ...],
    *,
    domain_profile: Any = None,
) -> list[EvidenceEntry]:
    """Build schema-compatible evidence entries for every claim.

    The ledger never invents citations. User-supplied text is labeled as local
    input or provided evidence, while unsupported truth claims are marked as
    missing, assumed, or needing external validation in the entry notes.
    """

    input_view = _coerce_input(input_data)
    domain_profile = _reasoning_profile_for(input_data, domain_profile)
    claim_list = list(claims)
    entries: list[EvidenceEntry] = []

    for claim in claim_list:
        status = _STATUS_BY_SOURCE_LABEL.get(claim.source_label, "missing")
        entries.append(
            _primary_entry_for_claim(
                sequence_number=len(entries) + 1,
                claim=claim,
                status=status,
                raw_idea=input_view.raw_idea,
                goal=input_view.goal,
                evidence_request=evidence_request_for(
                    domain_profile, _gap_category_for_claim(claim)
                ),
            )
        )

    for evidence_text in input_view.provided_evidence:
        target_claim = _best_claim_for_evidence(evidence_text, claim_list)
        if target_claim is None:
            continue
        entries.append(
            EvidenceEntry(
                id=f"evidence-{len(entries) + 1:03d}",
                claim_id=target_claim.id,
                evidence_type="provided",
                summary=(
                    "User-provided local support: "
                    f"{_shorten(evidence_text)}"
                ),
                reference_label=f"provided_evidence:{len(entries) + 1:03d}",
                notes=(
                    "status=provided; source=user_supplied; support_scope=local_input_only; "
                    "this may clarify the submitted concept but is not external validation."
                ),
            )
        )

    return entries


def evidence_status(entry: EvidenceEntry) -> str:
    """Return the richer local evidence status recorded in an entry's notes."""

    match = re.search(r"\bstatus=([a-z_]+)\b", entry.notes)
    if match and match.group(1) in EVIDENCE_STATUSES:
        return match.group(1)
    return entry.evidence_type


def evidence_gap_category(entry: EvidenceEntry) -> str | None:
    """Return the deterministic evidence-gap category recorded in entry notes."""

    match = re.search(r"\bgap_category=([a-z_]+)\b", entry.notes)
    if match and match.group(1) in EVIDENCE_GAP_CATEGORIES:
        return match.group(1)
    return None


def _primary_entry_for_claim(
    sequence_number: int,
    claim: Claim,
    status: str,
    raw_idea: str,
    goal: str,
    evidence_request: str,
) -> EvidenceEntry:
    if status == "provided":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="provided",
            summary=(
                "The user supplied the concept and goal being evaluated: "
                f"idea={_shorten(raw_idea)}; goal={_shorten(goal)}"
            ),
            reference_label="user_input",
            notes=(
                "status=provided; source=user_input; support_scope=concept_description_only; "
                "this does not validate feasibility, adoption, safety, environmental, "
                "prior-art, or market claims."
            ),
        )

    gap_category = _gap_category_for_claim(claim)
    if status == "assumed":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="missing",
            summary=(
                f"Assumption needs {gap_category.replace('_', ' ')} evidence: "
                f"{evidence_request}"
            ),
            notes=(
                f"status=assumed; gap_category={gap_category}; "
                f"missing_evidence={evidence_request}"
            ),
        )

    if status == "needs_external_validation":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="missing",
            summary=(
                f"Needs {gap_category.replace('_', ' ')} evidence before support: "
                f"{evidence_request}"
            ),
            notes=(
                f"status=needs_external_validation; gap_category={gap_category}; "
                f"missing_evidence={evidence_request}"
            ),
        )

    return EvidenceEntry(
        id=f"evidence-{sequence_number:03d}",
        claim_id=claim.id,
        evidence_type="missing",
        summary=(
            f"Missing {gap_category.replace('_', ' ')} evidence: {evidence_request}"
        ),
        notes=(
            f"status=missing; gap_category={gap_category}; "
            f"missing_evidence={evidence_request}"
        ),
    )


def _gap_category_for_claim(claim: Claim) -> str:
    text = f"{claim.text} {claim.rationale}".lower()
    if _contains_any(
        text,
        (
            "prior-art position",
            "prior art position",
            "novelty and prior-art",
            "differentiated from",
            "patent-office",
            "manual patent search",
            "existing products",
            "substitutes",
        ),
    ):
        return "prior_art"
    if _contains_any(
        text, ("wastewater", "biodegradable", "degradation", "environment", "discharge")
    ):
        return "environmental"
    if _contains_any(
        text,
        (
            "safety",
            "regulatory",
            "medical-device",
            "ingestion",
            "obstruction",
            "biocompatibility",
            "sanitation",
            "diagnostic-quality",
            "clinical oversight",
            "human use",
            "approval",
            "legal interpretation",
            "patentability",
            "infringement",
            "freedom-to-operate",
            "legal strategy",
            "trust",
            "verification boundaries",
            "professional-review",
            "hallucinated",
        ),
    ):
        return "safety_regulatory"
    if _contains_any(
        text,
        (
            "technical",
            "feasibility",
            "implementation",
            "prototype",
            "sensing",
            "power",
            "manufacturing",
            "experimentable",
            "automation",
            "output reliability",
            "quality checks",
            "source traceability",
            "error labels",
            "rubric",
        ),
    ):
        return "technical"
    if _contains_any(
        text,
        (
            "buyer",
            "payer",
            "willingness to pay",
            "pricing",
            "distribution",
            "channel access",
            "market includes",
            "commercial audience",
        ),
    ):
        return "market"
    if _contains_any(
        text,
        (
            "user need",
            "adoption",
            "clinician",
            "patient adoption",
            "demand",
            "workflow fit",
            "avoidance",
            "founder workflow",
            "workflow integration",
            "repeat usage",
            "retention",
            "current-workaround",
            "solo developers",
            "time savings",
        ),
    ):
        return "user_adoption"
    if _contains_any(text, ("market", "commercial")):
        return "market"
    if _contains_any(
        text,
        ("prior-art", "patents", "comparison", "differentiated", "differentiation", "generic ai"),
    ):
        return "prior_art"
    if claim.source_label == "assumed":
        return "user_adoption"
    return "technical"


def _reasoning_profile_for(input_data: Any, domain_profile: Any) -> Any:
    if domain_profile is None:
        return domain_profile_for(input_data)
    if _profile_id(domain_profile) == "medical_device":
        legacy_profile = domain_profile_for(input_data)
        if legacy_profile.id == "capsule_medical_environmental":
            return legacy_profile
    return domain_profile


def _profile_id(profile: Any) -> str:
    return str(getattr(profile, "id", "") or "").strip().lower()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _best_claim_for_evidence(evidence_text: str, claims: list[Claim]) -> Claim | None:
    if not claims:
        return None

    evidence_tokens = _tokens(evidence_text)
    if not evidence_tokens:
        return claims[0]

    best_claim = claims[0]
    best_score = -1
    for claim in claims:
        claim_tokens = _tokens(f"{claim.text} {claim.rationale}")
        score = len(evidence_tokens & claim_tokens)
        if score > best_score:
            best_claim = claim
            best_score = score
    return best_claim


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[0-9A-Za-z\uAC00-\uD7A3]+", text.lower())
        if len(token) > 1 and token not in _STOPWORDS
    }


def _shorten(text: str, limit: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", str(text)).strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}..."
