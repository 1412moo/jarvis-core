"""Deterministic local reviewers for Research Council.

The functions in this module are intentionally simple, local, and
standard-library only. They do not perform web search, network calls, LLM calls,
or citation generation.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from textwrap import shorten

from .claim_extractor import DomainProfile, domain_profile_for, evidence_request_for
from .evidence_ledger import evidence_gap_category
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
    "implementation",
    "prototype",
    "device",
    "capsule",
    "sensor",
    "sensing",
    "power",
    "data",
    "manufacturing",
    "transit",
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
    "unsupported",
    "evidence",
    "adopt",
    "screen",
    "diagnostic",
    "safety",
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
    domain_profile = domain_profile_for(input_data)
    evidence_by_claim = _evidence_by_claim(evidence_list)
    missing_claim_ids = _missing_claim_ids(claim_list, evidence_by_claim)
    gap_category_by_claim = _gap_category_by_claim(evidence_list)

    critiques = [
        _build_technical_critique(
            claim_list, missing_claim_ids, gap_category_by_claim, domain_profile, 1
        ),
        _build_market_critique(
            claim_list, missing_claim_ids, gap_category_by_claim, domain_profile, 2
        ),
        _build_safety_critique(
            input_data, claim_list, missing_claim_ids, gap_category_by_claim, domain_profile, 3
        ),
        _build_red_team_critique(
            claim_list, missing_claim_ids, gap_category_by_claim, domain_profile, 4
        ),
    ]
    return critiques


def _build_technical_critique(
    claims: tuple[Claim, ...],
    missing_claim_ids: set[str],
    gap_category_by_claim: dict[str, str],
    domain_profile: DomainProfile,
    index: int,
) -> ReviewerCritique:
    claim = _select_claim_by_gap_category(
        claims, ("technical",), missing_claim_ids, gap_category_by_claim, _TECHNICAL_KEYWORDS
    )
    target = _claim_target_text(claim)
    gap_note = _claim_gap_note(claim, gap_category_by_claim, domain_profile, fallback="technical")
    severity = _severity_for_claim(claim, missing_claim_ids, default="medium")
    if domain_profile.id == "capsule_medical_environmental":
        finding = (
            f"The technical blocker is the capsule itself: {target} "
            "must show that a swallowable body can observe enough of the colon while moving, "
            "capture or retain usable data, and still pass safely despite orientation, occlusion, "
            f"power, and retrieval limits. {gap_note}"
        )
        suggested_action = (
            "Build a non-ingestible capsule-size bench mockup and test image or sensor capture "
            "through a simulated curved wet channel before considering any clinical path."
        )
    else:
        finding = (
            f"The technical case is not proven yet for {target}. "
            "The concept needs a small prototype or bench test that exposes the core mechanism, "
            f"performance threshold, and failure modes. {gap_note}"
        )
        suggested_action = (
            "Run the smallest local prototype or bench test that can falsify the core feasibility claim."
        )
    return ReviewerCritique(
        id=_critique_id(index),
        reviewer_role="technical",
        claim_id=claim.id if claim else None,
        finding=finding,
        severity=severity,
        suggested_action=suggested_action,
    )


def _build_market_critique(
    claims: tuple[Claim, ...],
    missing_claim_ids: set[str],
    gap_category_by_claim: dict[str, str],
    domain_profile: DomainProfile,
    index: int,
) -> ReviewerCritique:
    claim = _select_claim_by_gap_category(
        claims,
        ("user_adoption", "market"),
        missing_claim_ids,
        gap_category_by_claim,
        _MARKET_KEYWORDS,
    )
    target = _claim_target_text(claim)
    gap_note = _claim_gap_note(claim, gap_category_by_claim, domain_profile, fallback="user_adoption")
    severity = _severity_for_claim(claim, missing_claim_ids, default="medium")
    if domain_profile.id == "capsule_medical_environmental":
        finding = (
            f"Adoption is unproven for {target}. A less burdensome capsule story is appealing, "
            "but it does not show that patients would trust ingestion, clinicians would trust "
            "diagnostic quality, or payers and screening programs would prefer this pathway over "
            f"established alternatives. {gap_note}"
        )
        suggested_action = (
            "Run separate non-clinical interviews with one patient-like participant and one care-pathway "
            "operator to test trust, refusal points, and the decision this concept would change."
        )
    else:
        finding = (
            f"The demand and usefulness case remains weak for {target}. "
            "Interest in the idea has not been separated from a repeatable adoption trigger, "
            f"budget owner, or competing alternative. {gap_note}"
        )
        suggested_action = (
            "Run a lightweight adoption check with the target user and record the current workaround, "
            "switching trigger, and next decision."
        )
    return ReviewerCritique(
        id=_critique_id(index),
        reviewer_role="market",
        claim_id=claim.id if claim else None,
        finding=finding,
        severity=severity,
        suggested_action=suggested_action,
    )


def _build_safety_critique(
    input_data: ResearchCouncilInput,
    claims: tuple[Claim, ...],
    missing_claim_ids: set[str],
    gap_category_by_claim: dict[str, str],
    domain_profile: DomainProfile,
    index: int,
) -> ReviewerCritique:
    claim = _select_claim_by_gap_category(
        claims,
        ("safety_regulatory",),
        missing_claim_ids,
        gap_category_by_claim,
        _SAFETY_KEYWORDS,
    )
    target = _claim_target_text(claim)
    regulated_terms = _matched_terms(_input_text(input_data), _REGULATED_DOMAIN_KEYWORDS)
    regulated_note = (
        f" The idea mentions potentially regulated or sensitive terms: {', '.join(regulated_terms)}."
        if regulated_terms
        else ""
    )
    gap_note = _claim_gap_note(
        claim, gap_category_by_claim, domain_profile, fallback="safety_regulatory"
    )
    severity = (
        "high"
        if regulated_terms or domain_profile.id in {"capsule_medical_environmental", "medical_device"}
        else _severity_for_claim(claim, missing_claim_ids, default="medium")
    )
    if domain_profile.id == "capsule_medical_environmental":
        finding = (
            f"The safety boundary is the highest-impact blocker for {target}. "
            "The concept involves ingestion, possible retention or obstruction, biocompatibility, "
            "diagnostic false reassurance, patient discharge, and degradation byproducts entering "
            f"wastewater. {gap_note}"
        )
        suggested_action = (
            "Create a non-clinical safety table that lists hazards, stop conditions, required "
            "expert review, and what evidence is mandatory before any human-use experiment."
        )
    else:
        finding = (
            f"The safety and regulatory boundary is underspecified for {target}."
            f"{regulated_note} Safety-sensitive use, advice boundaries, data handling, and "
            f"review requirements need explicit constraints before broader use. {gap_note}"
        )
        suggested_action = (
            "Write a one-page boundary checklist covering sensitive use, required review, "
            "prohibited claims, and conditions that should pause the idea."
        )
    return ReviewerCritique(
        id=_critique_id(index),
        reviewer_role="safety_regulatory",
        claim_id=claim.id if claim else None,
        finding=finding,
        severity=severity,
        suggested_action=suggested_action,
    )


def _build_red_team_critique(
    claims: tuple[Claim, ...],
    missing_claim_ids: set[str],
    gap_category_by_claim: dict[str, str],
    domain_profile: DomainProfile,
    index: int,
) -> ReviewerCritique:
    claim = _select_claim_by_gap_category(
        claims,
        ("prior_art", "environmental"),
        missing_claim_ids,
        gap_category_by_claim,
        _RED_TEAM_KEYWORDS,
    )
    target = _claim_target_text(claim)
    gap_note = _claim_gap_note(claim, gap_category_by_claim, domain_profile, fallback="prior_art")
    severity = _severity_for_claim(claim, missing_claim_ids, default="high")
    if domain_profile.id == "capsule_medical_environmental":
        finding = (
            f"The easiest harmful overclaim for {target} is that a biodegradable capsule can be "
            "treated as a screening substitute before it has evidence on coverage, missed lesions, "
            "retention, degradation residue, and fit with existing care. The submitted description "
            f"defines a concept; it does not support those outcome claims. {gap_note}"
        )
        suggested_action = (
            "Rewrite the concept notes so every screening, safety, and environmental statement is "
            "labeled as user-provided, missing evidence, or a non-clinical experiment target."
        )
    else:
        finding = (
            f"The easiest failure mode for {target} is false confidence: a polished concept could "
            "make unsupported claims look researched. The next pass needs deliberate checks for "
            f"overclaiming and unfalsifiable next steps. {gap_note}"
        )
        suggested_action = (
            "Run an adversarial read where every high-impact statement maps to provided input, "
            "an explicit missing-evidence entry, or a cheap experiment."
        )
    return ReviewerCritique(
        id=_critique_id(index),
        reviewer_role="red_team",
        claim_id=claim.id if claim else None,
        finding=finding,
        severity=severity,
        suggested_action=suggested_action,
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


def _gap_category_by_claim(evidence_entries: Iterable[EvidenceEntry]) -> dict[str, str]:
    categories: dict[str, str] = {}
    for entry in evidence_entries:
        category = evidence_gap_category(entry)
        if category:
            categories.setdefault(entry.claim_id, category)
    return categories


def _claim_gap_note(
    claim: Claim | None,
    gap_category_by_claim: dict[str, str],
    domain_profile: DomainProfile,
    *,
    fallback: str,
) -> str:
    category = fallback
    if claim and claim.id in gap_category_by_claim:
        category = gap_category_by_claim[claim.id]
    request = evidence_request_for(domain_profile, category)
    return f"Evidence needed ({category}): {request}"


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


def _select_claim_by_gap_category(
    claims: tuple[Claim, ...],
    categories: tuple[str, ...],
    missing_claim_ids: set[str],
    gap_category_by_claim: dict[str, str],
    fallback_keywords: tuple[str, ...],
) -> Claim | None:
    for category in categories:
        for claim in claims:
            if claim.id in missing_claim_ids and gap_category_by_claim.get(claim.id) == category:
                return claim
    for category in categories:
        for claim in claims:
            if gap_category_by_claim.get(claim.id) == category:
                return claim
    return _select_claim(claims, fallback_keywords, missing_claim_ids)


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
