"""Deterministic local reviewers for Research Council.

The functions in this module are intentionally simple, local, and
standard-library only. They do not perform web search, network calls, LLM calls,
or citation generation.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from textwrap import shorten

from .schemas import Claim, EvidenceEntry, ResearchCouncilInput, ReviewerCritique


REVIEWER_ROLES: tuple[str, ...] = (
    "technical",
    "market",
    "safety_regulatory",
    "red_team",
)

_TECHNICAL_KEYWORDS = (
    "build",
    "technical",
    "workflow",
    "module",
    "pipeline",
    "integration",
    "automate",
    "local",
    "experiment",
)
_MARKET_KEYWORDS = (
    "adopt",
    "market",
    "customer",
    "user",
    "pay",
    "willing",
    "demand",
    "useful",
    "value",
)
_SAFETY_KEYWORDS = (
    "safety",
    "regulatory",
    "compliance",
    "privacy",
    "legal",
    "medical",
    "health",
    "financial",
    "data",
    "risk",
)
_RED_TEAM_KEYWORDS = (
    "assume",
    "scale",
    "expand",
    "trust",
    "automate",
    "unsupported",
    "evidence",
    "adopt",
)
_REGULATED_DOMAIN_KEYWORDS = (
    "medical",
    "health",
    "clinical",
    "patient",
    "diagnosis",
    "legal",
    "lawyer",
    "contract",
    "financial",
    "investment",
    "insurance",
    "privacy",
    "personal data",
)


def run_reviewers(
    input_data: ResearchCouncilInput,
    claims: Sequence[Claim],
    evidence_entries: Sequence[EvidenceEntry],
) -> list[ReviewerCritique]:
    """Return deterministic critiques from all Research Council reviewer roles."""

    claim_list = tuple(claims)
    evidence_list = tuple(evidence_entries)
    evidence_by_claim = _evidence_by_claim(evidence_list)
    missing_claim_ids = _missing_claim_ids(claim_list, evidence_by_claim)
    evidence_gap_note = _evidence_gap_note(claim_list, evidence_list, missing_claim_ids)

    critiques = [
        _build_technical_critique(claim_list, missing_claim_ids, evidence_gap_note, 1),
        _build_market_critique(claim_list, missing_claim_ids, evidence_gap_note, 2),
        _build_safety_critique(input_data, claim_list, missing_claim_ids, evidence_gap_note, 3),
        _build_red_team_critique(claim_list, missing_claim_ids, evidence_gap_note, 4),
    ]
    return critiques


def _build_technical_critique(
    claims: tuple[Claim, ...],
    missing_claim_ids: set[str],
    evidence_gap_note: str,
    index: int,
) -> ReviewerCritique:
    claim = _select_claim(claims, _TECHNICAL_KEYWORDS, missing_claim_ids)
    target = _claim_target_text(claim)
    severity = _severity_for_claim(claim, missing_claim_ids, default="medium")
    return ReviewerCritique(
        id=_critique_id(index),
        reviewer_role="technical",
        claim_id=claim.id if claim else None,
        finding=(
            f"The technical case is not proven yet for {target}. "
            "The current materials need a small local run that demonstrates stable inputs, outputs, "
            f"and failure behavior before any pipeline integration. {evidence_gap_note}"
        ),
        severity=severity,
        suggested_action=(
            "Run a deterministic local spike against one or two representative ideas and record "
            "whether imports, object construction, and output validation pass without manual repair."
        ),
    )


def _build_market_critique(
    claims: tuple[Claim, ...],
    missing_claim_ids: set[str],
    evidence_gap_note: str,
    index: int,
) -> ReviewerCritique:
    claim = _select_claim(claims, _MARKET_KEYWORDS, missing_claim_ids)
    target = _claim_target_text(claim)
    severity = _severity_for_claim(claim, missing_claim_ids, default="medium")
    return ReviewerCritique(
        id=_critique_id(index),
        reviewer_role="market",
        claim_id=claim.id if claim else None,
        finding=(
            f"The demand and usefulness case remains weak for {target}. "
            "User interest, willingness to repeat the workflow, and decision value have not been "
            f"separated from enthusiasm for the idea. {evidence_gap_note}"
        ),
        severity=severity,
        suggested_action=(
            "Run a lightweight usefulness check with target users or realistic saved ideas and "
            "measure whether the report changes the next decision."
        ),
    )


def _build_safety_critique(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    missing_claim_ids: set[str],
    evidence_gap_note: str,
    index: int,
) -> ReviewerCritique:
    claim = _select_claim(claims, _SAFETY_KEYWORDS, missing_claim_ids)
    target = _claim_target_text(claim)
    regulated_terms = _matched_terms(_input_text(input_data), _REGULATED_DOMAIN_KEYWORDS)
    regulated_note = (
        f" The idea mentions potentially regulated or sensitive terms: {', '.join(regulated_terms)}."
        if regulated_terms
        else ""
    )
    severity = "high" if regulated_terms else _severity_for_claim(claim, missing_claim_ids, default="medium")
    return ReviewerCritique(
        id=_critique_id(index),
        reviewer_role="safety_regulatory",
        claim_id=claim.id if claim else None,
        finding=(
            f"The safety and regulatory boundary is underspecified for {target}."
            f"{regulated_note} Data handling, advice boundaries, and compliance assumptions need "
            f"explicit constraints before the workflow is used beyond a local draft. {evidence_gap_note}"
        ),
        severity=severity,
        suggested_action=(
            "Write a one-page boundary checklist covering data sensitivity, prohibited advice, "
            "human review requirements, and conditions that should pause the idea."
        ),
    )


def _build_red_team_critique(
    claims: tuple[Claim, ...],
    missing_claim_ids: set[str],
    evidence_gap_note: str,
    index: int,
) -> ReviewerCritique:
    claim = _select_claim(claims, _RED_TEAM_KEYWORDS, missing_claim_ids)
    target = _claim_target_text(claim)
    severity = _severity_for_claim(claim, missing_claim_ids, default="high")
    return ReviewerCritique(
        id=_critique_id(index),
        reviewer_role="red_team",
        claim_id=claim.id if claim else None,
        finding=(
            f"The easiest failure mode for {target} is false confidence: a polished report could "
            "make unsupported claims look researched. The workflow needs deliberate checks for "
            f"overclaiming, missing evidence, and unfalsifiable next steps. {evidence_gap_note}"
        ),
        severity=severity,
        suggested_action=(
            "Add a manual adversarial read where every high-impact statement must map to provided "
            "evidence, an explicit missing-evidence entry, or a cheap experiment."
        ),
    )


def _evidence_by_claim(evidence_entries: Iterable[EvidenceEntry]) -> dict[str, tuple[EvidenceEntry, ...]]:
    grouped: dict[str, list[EvidenceEntry]] = {}
    for entry in evidence_entries:
        grouped.setdefault(entry.claim_id, []).append(entry)
    return {claim_id: tuple(entries) for claim_id, entries in grouped.items()}


def _missing_claim_ids(
    claims: Iterable[Claim],
    evidence_by_claim: dict[str, tuple[EvidenceEntry, ...]],
) -> set[str]:
    missing: set[str] = set()
    for claim in claims:
        entries = evidence_by_claim.get(claim.id, ())
        has_provided_evidence = any(entry.evidence_type == "provided" for entry in entries)
        has_missing_evidence = any(entry.evidence_type == "missing" for entry in entries)
        if claim.source_label == "needs_evidence" or has_missing_evidence or not has_provided_evidence:
            missing.add(claim.id)
    return missing


def _evidence_gap_note(
    claims: tuple[Claim, ...],
    evidence_entries: tuple[EvidenceEntry, ...],
    missing_claim_ids: set[str],
) -> str:
    if not claims:
        return "Missing evidence: no structured claims were supplied for review."
    if not evidence_entries:
        return "Missing evidence: no evidence ledger entries were supplied."
    if missing_claim_ids:
        joined_ids = ", ".join(sorted(missing_claim_ids))
        return f"Missing evidence is explicit for: {joined_ids}."
    return "No missing evidence entries were supplied, so this critique is limited to the provided ledger."


def _select_claim(
    claims: tuple[Claim, ...],
    keywords: tuple[str, ...],
    missing_claim_ids: set[str],
) -> Claim | None:
    missing_matches = [
        claim for claim in claims if claim.id in missing_claim_ids and _contains_keyword(claim.text, keywords)
    ]
    if missing_matches:
        return missing_matches[0]

    keyword_matches = [claim for claim in claims if _contains_keyword(claim.text, keywords)]
    if keyword_matches:
        return keyword_matches[0]

    unsupported_claims = [
        claim for claim in claims if claim.id in missing_claim_ids or claim.confidence == "low"
    ]
    if unsupported_claims:
        return unsupported_claims[0]

    return claims[0] if claims else None


def _severity_for_claim(
    claim: Claim | None,
    missing_claim_ids: set[str],
    *,
    default: str,
) -> str:
    if claim is None:
        return "high"
    if claim.id in missing_claim_ids and claim.confidence == "low":
        return "high"
    if claim.source_label == "needs_evidence":
        return "high"
    if claim.id in missing_claim_ids:
        return "medium"
    return default


def _claim_target_text(claim: Claim | None) -> str:
    if claim is None:
        return "the overall idea"
    return f"`{claim.id}` ({shorten(claim.text, width=120, placeholder='...')})"


def _input_text(input_data: ResearchCouncilInput) -> str:
    parts = [
        _get_field(input_data, "raw_idea"),
        _get_field(input_data, "goal"),
        _get_field(input_data, "context"),
        " ".join(_get_sequence_field(input_data, "constraints")),
        " ".join(_get_sequence_field(input_data, "provided_evidence")),
    ]
    return " ".join(part for part in parts if part)


def _get_field(input_data: ResearchCouncilInput, field_name: str) -> str:
    if isinstance(input_data, dict):
        value = input_data.get(field_name, "")
    else:
        value = getattr(input_data, field_name, "")
    return str(value or "")


def _get_sequence_field(input_data: ResearchCouncilInput, field_name: str) -> tuple[str, ...]:
    if isinstance(input_data, dict):
        value = input_data.get(field_name, ())
    else:
        value = getattr(input_data, field_name, ())
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value if str(item).strip())


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _matched_terms(text: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
    lowered = text.lower()
    return tuple(keyword for keyword in keywords if keyword in lowered)


def _critique_id(index: int) -> str:
    return f"critique-{index:03d}"
