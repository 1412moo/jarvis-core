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

from .claim_extractor import _coerce_input
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
    input_data: Any, claims: list[Claim] | tuple[Claim, ...]
) -> list[EvidenceEntry]:
    """Build schema-compatible evidence entries for every claim.

    The ledger never invents citations. User-supplied text is labeled as local
    input or provided evidence, while unsupported truth claims are marked as
    missing, assumed, or needing external validation in the entry notes.
    """

    input_view = _coerce_input(input_data)
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
                summary=f"User-provided evidence: {_shorten(evidence_text)}",
                reference_label=f"provided_evidence:{len(entries) + 1:03d}",
                notes=(
                    "status=provided; source=user_supplied; this is local input only "
                    "and has not been externally verified."
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


def _primary_entry_for_claim(
    sequence_number: int,
    claim: Claim,
    status: str,
    raw_idea: str,
    goal: str,
) -> EvidenceEntry:
    if status == "provided":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="provided",
            summary=(
                "The claim is grounded in the user's local idea and goal: "
                f"idea={_shorten(raw_idea)}; goal={_shorten(goal)}"
            ),
            reference_label="user_input",
            notes=(
                "status=provided; source=user_input; this supports extraction only "
                "and is not an external citation or validation."
            ),
        )

    if status == "assumed":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="missing",
            summary=(
                "Assumption is explicit: no direct evidence was supplied for this "
                "claim beyond the local idea framing."
            ),
            notes=(
                "status=assumed; missing_evidence=user research, usage data, "
                "adoption signal, or domain validation."
            ),
        )

    if status == "needs_external_validation":
        return EvidenceEntry(
            id=f"evidence-{sequence_number:03d}",
            claim_id=claim.id,
            evidence_type="missing",
            summary=(
                "External validation is needed before this claim can be treated as "
                "supported."
            ),
            notes=(
                "status=needs_external_validation; missing_evidence=external research, "
                "prior-art review, regulatory review, material tests, market data, "
                "or other independently checked support as applicable."
            ),
        )

    return EvidenceEntry(
        id=f"evidence-{sequence_number:03d}",
        claim_id=claim.id,
        evidence_type="missing",
        summary=(
            "The claim was extracted from the idea structure, but no verifying evidence "
            "was supplied."
        ),
        notes=(
            "status=missing; missing_evidence=prototype result, measurement, interview, "
            "domain review, or other concrete support for the claim."
        ),
    )


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
