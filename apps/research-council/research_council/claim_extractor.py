"""Deterministic local claim extraction for Research Council.

This module intentionally performs no network, web-search, LLM, or citation
work. It turns user-provided idea text into schema-compatible Claim objects and
marks unsupported research statements as assumptions or evidence needs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

from .schemas import Claim


DEFAULT_GOAL = (
    "Evaluate feasibility, evidence gaps, and the smallest useful validation step."
)

_MAX_FOCUS_LENGTH = 180
EVIDENCE_GAP_CATEGORIES: tuple[str, ...] = (
    "technical",
    "user_adoption",
    "prior_art",
    "safety_regulatory",
    "environmental",
    "market",
)

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "capsule": (
        "capsule",
        "ingestible",
        "swallow",
        "swallowed",
        "\uba39\ub294",
        "\uc0bc\ud0a4",
        "\ucea1\uc290",
        "\ucea1\uc290\ud615",
    ),
    "medical": (
        "medical",
        "clinical",
        "diagnostic",
        "diagnosis",
        "screening",
        "colonoscopy",
        "colon",
        "colorectal",
        "patient",
        "\ub300\uc7a5",
        "\uac80\uc0ac",
        "\uc9c4\ub2e8",
        "\uc758\ub8cc",
        "\ud658\uc790",
        "\ubcd1\uc6d0",
        "\ub0b4\uc2dc\uacbd",
    ),
    "environmental": (
        "biodegradable",
        "degradable",
        "eco",
        "environment",
        "sewer",
        "wastewater",
        "compost",
        "\uce5c\ud658\uacbd",
        "\ud558\uc218",
        "\ubd84\ud574",
        "\ubc30\ucd9c",
        "\uc0dd\ubd84\ud574",
    ),
    "hardware": (
        "device",
        "equipment",
        "hardware",
        "sensor",
        "robot",
        "capsule",
        "\uc7a5\ube44",
        "\uae30\uae30",
        "\uc13c\uc11c",
        "\ub85c\ubd07",
        "\ucea1\uc290",
    ),
    "software": (
        "app",
        "software",
        "platform",
        "dashboard",
        "automation",
        "ai",
        "model",
        "\uc571",
        "\uc18c\ud504\ud2b8\uc6e8\uc5b4",
        "\ud50c\ub7ab\ud3fc",
        "\uc790\ub3d9\ud654",
    ),
    "market": (
        "market",
        "customer",
        "buyer",
        "hospital",
        "clinic",
        "patient",
        "consumer",
        "\uc0ac\uc6a9\uc790",
        "\uace0\uac1d",
        "\uc2dc\uc7a5",
        "\ubcd1\uc6d0",
        "\ud658\uc790",
    ),
    "regulated": (
        "medical",
        "clinical",
        "diagnostic",
        "patient",
        "health",
        "finance",
        "legal",
        "child",
        "safety",
        "regulatory",
        "\uc758\ub8cc",
        "\uc9c4\ub2e8",
        "\ud658\uc790",
        "\uc548\uc804",
        "\uaddc\uc81c",
        "\uac80\uc0ac",
        "\ub300\uc7a5",
    ),
}


@dataclass(frozen=True)
class _InputView:
    raw_idea: str
    goal: str
    context: str | None = None
    constraints: tuple[str, ...] = ()
    provided_evidence: tuple[str, ...] = ()

    @property
    def combined_text(self) -> str:
        parts: list[str] = [self.raw_idea, self.goal]
        if self.context:
            parts.append(self.context)
        parts.extend(self.constraints)
        return " ".join(part for part in parts if part)


@dataclass(frozen=True)
class _ClaimSpec:
    text: str
    source_label: str
    confidence: str
    rationale: str


@dataclass(frozen=True)
class EvidenceNeed:
    category: str
    request: str


@dataclass(frozen=True)
class DomainProfile:
    id: str
    label: str
    concept_label: str
    evidence_needs: tuple[EvidenceNeed, ...]
    blocker_order: tuple[str, ...]


def extract_claims(
    input_data: Any, goal: Any = None, *, domain_profile: Any = None
) -> list[Claim]:
    """Extract deterministic structured claims from a ResearchCouncilInput-like value.

    Accepted inputs include a ResearchCouncilInput instance, an object with
    matching attributes, a mapping with ``raw_idea``/``goal`` keys, a
    ``(raw_idea, goal)`` sequence, a raw idea string, or raw idea and goal
    strings passed as two arguments.
    """

    input_view = _coerce_input(input_data, goal_override=goal)
    signals = _detect_signals(input_view)
    focus = _idea_focus(input_view.raw_idea)
    profile_id = _profile_id(domain_profile)

    if profile_id in {"ai_saas", "marketplace", "developer_tool", "enterprise_b2b"}:
        if profile_id == "developer_tool":
            specs = _developer_tool_claim_specs(input_view, focus)
        elif profile_id == "enterprise_b2b":
            specs = _enterprise_b2b_claim_specs(input_view, focus)
        elif profile_id == "marketplace":
            specs = _marketplace_claim_specs(input_view, focus)
        else:
            specs = _ai_saas_claim_specs(input_view, focus)
        return [
            Claim(
                id=f"claim-{index:03d}",
                text=spec.text,
                source_label=spec.source_label,  # type: ignore[arg-type]
                confidence=spec.confidence,  # type: ignore[arg-type]
                rationale=spec.rationale,
            )
            for index, spec in enumerate(_dedupe_specs(specs), start=1)
        ]

    specs: list[_ClaimSpec] = [
        _concept_claim(input_view, focus),
        _technical_feasibility_claim(signals),
        _user_need_claim(signals),
        _novelty_claim(signals),
        _safety_regulatory_claim(signals),
        _implementation_claim(signals),
    ]
    if signals["environmental"]:
        specs.append(_environmental_claim())
    specs.extend(
        [
            _market_claim(signals),
            _experimentability_claim(signals),
        ]
    )

    return [
        Claim(
            id=f"claim-{index:03d}",
            text=spec.text,
            source_label=spec.source_label,  # type: ignore[arg-type]
            confidence=spec.confidence,  # type: ignore[arg-type]
            rationale=spec.rationale,
        )
        for index, spec in enumerate(_dedupe_specs(specs), start=1)
    ]


def domain_profile_for(input_data: Any) -> DomainProfile:
    """Return a deterministic domain profile for local reviewer/report heuristics."""

    input_view = _coerce_input(input_data)
    return _domain_profile_from_signals(_detect_signals(input_view))


def evidence_request_for(profile: DomainProfile, category: str) -> str:
    """Return the most specific evidence request for a category in a profile."""

    if _profile_id(profile) == "ai_saas":
        request = _AI_SAAS_EVIDENCE_REQUESTS.get(category)
        if request:
            return request

    for need in profile.evidence_needs:
        if need.category == category:
            return need.request
    return _GENERIC_EVIDENCE_REQUESTS.get(category, _GENERIC_FALLBACK_REQUEST)


def _coerce_input(input_data: Any, goal_override: Any = None) -> _InputView:
    if isinstance(input_data, str):
        raw_idea = _clean_text(input_data)
        if not raw_idea:
            raise ValueError("raw_idea must be non-empty")
        return _InputView(
            raw_idea=raw_idea,
            goal=_clean_text(goal_override) or DEFAULT_GOAL,
        )

    if isinstance(input_data, Mapping):
        raw_idea = _first_mapping_value(
            input_data, "raw_idea", "idea", "raw", "description"
        )
        goal = goal_override or _first_mapping_value(
            input_data, "goal", "objective", "outcome"
        )
        context = _first_mapping_value(input_data, "context", "background")
        constraints = _tuple_of_strings(input_data.get("constraints"))
        provided_evidence = _tuple_of_strings(
            input_data.get("provided_evidence", input_data.get("evidence"))
        )
        return _build_input_view(raw_idea, goal, context, constraints, provided_evidence)

    if _is_sequence_input(input_data):
        values = list(input_data)
        raw_idea = values[0] if values else ""
        goal = goal_override or (values[1] if len(values) > 1 else DEFAULT_GOAL)
        context = values[2] if len(values) > 2 else None
        return _build_input_view(raw_idea, goal, context, (), ())

    raw_idea = getattr(input_data, "raw_idea", None)
    goal = goal_override or getattr(input_data, "goal", None)
    context = getattr(input_data, "context", None)
    constraints = _tuple_of_strings(getattr(input_data, "constraints", ()))
    provided_evidence = _tuple_of_strings(getattr(input_data, "provided_evidence", ()))
    return _build_input_view(raw_idea, goal, context, constraints, provided_evidence)


def _build_input_view(
    raw_idea: Any,
    goal: Any,
    context: Any,
    constraints: tuple[str, ...],
    provided_evidence: tuple[str, ...],
) -> _InputView:
    cleaned_raw_idea = _clean_text(raw_idea)
    if not cleaned_raw_idea:
        raise ValueError("raw_idea must be non-empty")

    cleaned_goal = _clean_text(goal) or DEFAULT_GOAL
    cleaned_context = _clean_text(context) or None
    return _InputView(
        raw_idea=cleaned_raw_idea,
        goal=cleaned_goal,
        context=cleaned_context,
        constraints=constraints,
        provided_evidence=provided_evidence,
    )


def _is_sequence_input(input_data: Any) -> bool:
    return isinstance(input_data, Sequence) and not isinstance(
        input_data, (str, bytes, bytearray)
    )


def _first_mapping_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _tuple_of_strings(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    return tuple(_clean_text(value) for value in values if _clean_text(value))


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _detect_signals(input_view: _InputView) -> dict[str, bool]:
    text = input_view.combined_text.lower()
    signals = {
        name: _contains_any(text, keywords) for name, keywords in _KEYWORDS.items()
    }
    signals["medical_device"] = signals["medical"] and (
        signals["hardware"] or signals["capsule"]
    )
    signals["regulated"] = signals["regulated"] or signals["medical_device"]
    signals["market"] = signals["market"] or signals["medical"] or signals["hardware"]
    return signals


_GENERIC_FALLBACK_REQUEST = (
    "Define the smallest observable result that would make this claim decision-relevant."
)

_GENERIC_EVIDENCE_REQUESTS: dict[str, str] = {
    "technical": (
        "Specify the core mechanism, a prototype path, measurable performance threshold, "
        "and at least one failure-mode test."
    ),
    "user_adoption": (
        "Identify the target user, current workaround, switching trigger, and a direct signal "
        "that the problem is painful enough to change behavior."
    ),
    "prior_art": (
        "Compare the concept against known substitutes, published work, patents, products, "
        "or offline references supplied by the user."
    ),
    "safety_regulatory": (
        "List the safety-sensitive uses, required review boundaries, approval assumptions, "
        "and stop conditions before broader use."
    ),
    "environmental": (
        "Measure material breakdown timing, residue, disposal pathway compatibility, and "
        "whether the approach shifts risk elsewhere."
    ),
    "market": (
        "Name the buyer, payer or budget owner, competing alternative, adoption barrier, "
        "and willingness-to-pay signal."
    ),
}

_AI_SAAS_EVIDENCE_REQUESTS: dict[str, str] = {
    "technical": (
        "Define input sources, output-quality rubric, source traceability, failure handling, "
        "hallucination checks, privacy controls, and operational reliability thresholds."
    ),
    "user_adoption": (
        "Interview target founders about the current prior-art search workflow, buyer/workflow "
        "owner, pain frequency, time cost, switching cost, trust blockers, integration needs, "
        "and repeat usage triggers."
    ),
    "prior_art": (
        "Map differentiation and AI wrapper risk against manual patent search, patent-office "
        "databases, generic AI assistants, spreadsheets, attorney intake, and user-supplied "
        "offline references."
    ),
    "safety_regulatory": (
        "Define trust and verification boundaries: no unsupported legal interpretation, no fake "
        "citations, visible source checks, and clear escalation to professional review."
    ),
    "market": (
        "Test buyer urgency, willingness to pay, packaging, distribution channel, switching "
        "cost, competing workflow substitute, and whether repeat patent-analysis moments can "
        "support SaaS retention."
    ),
}


def _domain_profile_from_signals(signals: dict[str, bool]) -> DomainProfile:
    if signals["capsule"] and signals["medical"] and signals["environmental"]:
        return DomainProfile(
            id="capsule_medical_environmental",
            label="Capsule medical environmental",
            concept_label="swallowable biodegradable colon-screening capsule",
            evidence_needs=(
                EvidenceNeed(
                    "technical",
                    (
                        "Show that a swallowable capsule-sized mockup can capture useful colon "
                        "observations during transit, retain/recover data, and tolerate occlusion, "
                        "orientation changes, power limits, and safe passage constraints."
                    ),
                ),
                EvidenceNeed(
                    "user_adoption",
                    (
                        "Check whether patients, clinicians, and screening program operators would "
                        "trust and use the capsule pathway compared with colonoscopy, stool tests, "
                        "and other existing screening routes."
                    ),
                ),
                EvidenceNeed(
                    "prior_art",
                    (
                        "Map the concept against capsule endoscopy, colorectal screening workflows, "
                        "biodegradable ingestible devices, retrieval/disposal approaches, and any "
                        "user-supplied offline prior-art references."
                    ),
                ),
                EvidenceNeed(
                    "safety_regulatory",
                    (
                        "Define ingestion, retention, obstruction, biocompatibility, sanitation, "
                        "diagnostic-quality, clinical oversight, and medical-device approval risks "
                        "before any human-use claim."
                    ),
                ),
                EvidenceNeed(
                    "environmental",
                    (
                        "Measure degradation time, byproducts, micro-fragment risk, wastewater "
                        "treatment compatibility, and whether the capsule remains safe after "
                        "patient discharge."
                    ),
                ),
                EvidenceNeed(
                    "market",
                    (
                        "Identify who pays for the screening pathway, who buys or prescribes it, "
                        "reimbursement assumptions, procurement barriers, and adoption triggers."
                    ),
                ),
            ),
            blocker_order=(
                "safety_regulatory",
                "technical",
                "environmental",
                "user_adoption",
                "prior_art",
                "market",
            ),
        )

    if signals["medical_device"]:
        return DomainProfile(
            id="medical_device",
            label="Medical device",
            concept_label="medical device concept",
            evidence_needs=(
                EvidenceNeed(
                    "technical",
                    (
                        "Demonstrate the device mechanism, performance threshold, reliability, "
                        "data capture, and safe-use failure modes in a non-clinical prototype."
                    ),
                ),
                EvidenceNeed(
                    "user_adoption",
                    (
                        "Check clinician, patient, and institution workflow fit before assuming "
                        "that a plausible health benefit becomes adoption."
                    ),
                ),
                EvidenceNeed(
                    "prior_art",
                    (
                        "Compare against existing devices, care pathways, clinical substitutes, "
                        "and any user-supplied offline references."
                    ),
                ),
                EvidenceNeed(
                    "safety_regulatory",
                    (
                        "Identify patient safety, clinical oversight, data quality, privacy, "
                        "and regulatory approval boundaries before use beyond research planning."
                    ),
                ),
                EvidenceNeed("environmental", _GENERIC_EVIDENCE_REQUESTS["environmental"]),
                EvidenceNeed("market", _GENERIC_EVIDENCE_REQUESTS["market"]),
            ),
            blocker_order=(
                "safety_regulatory",
                "technical",
                "user_adoption",
                "prior_art",
                "market",
                "environmental",
            ),
        )

    if signals["hardware"]:
        return DomainProfile(
            id="hardware",
            label="Hardware",
            concept_label="hardware concept",
            evidence_needs=tuple(
                EvidenceNeed(category, request)
                for category, request in _GENERIC_EVIDENCE_REQUESTS.items()
            ),
            blocker_order=(
                "technical",
                "safety_regulatory",
                "user_adoption",
                "market",
                "prior_art",
                "environmental",
            ),
        )

    if signals["software"]:
        return DomainProfile(
            id="ai_saas",
            label="AI SaaS",
            concept_label="AI SaaS concept",
            evidence_needs=tuple(
                EvidenceNeed(category, request)
                for category, request in _AI_SAAS_EVIDENCE_REQUESTS.items()
            ),
            blocker_order=(
                "user_adoption",
                "technical",
                "safety_regulatory",
                "market",
                "prior_art",
                "environmental",
            ),
        )

    return DomainProfile(
        id="general",
        label="General",
        concept_label="submitted concept",
        evidence_needs=tuple(
            EvidenceNeed(category, request)
            for category, request in _GENERIC_EVIDENCE_REQUESTS.items()
        ),
        blocker_order=(
            "technical",
            "user_adoption",
            "prior_art",
            "safety_regulatory",
            "market",
            "environmental",
        ),
    )


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _profile_id(profile: Any) -> str:
    return _clean_text(getattr(profile, "id", "")).lower()


def _idea_focus(raw_idea: str) -> str:
    first_sentence = re.split(r"(?<=[.!?。！？])\s+", raw_idea, maxsplit=1)[0]
    text = _clean_text(first_sentence)
    if len(text) <= _MAX_FOCUS_LENGTH:
        return text
    return f"{text[: _MAX_FOCUS_LENGTH - 1].rstrip()}..."


def _concept_claim(input_view: _InputView, focus: str) -> _ClaimSpec:
    goal = _clean_text(input_view.goal)
    return _ClaimSpec(
        text=f"The submitted idea proposes: {focus}",
        source_label="user_provided",
        confidence="high",
        rationale=(
            "This restates the user's local input and goal; it does not validate the "
            f"concept itself: {goal}"
        ),
    )


def _ai_saas_claim_specs(input_view: _InputView, focus: str) -> list[_ClaimSpec]:
    return [
        _concept_claim(input_view, focus),
        _ClaimSpec(
            text=(
                "The SaaS value depends on a painful, repeated founder workflow: solo "
                "developers must decide whether an invention idea deserves patent-analysis "
                "time, tool setup, or professional budget."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "The target user and decision goal imply workflow pain, but no founder "
                "interviews, usage logs, or current-workaround evidence were supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "Automation creates value only if it shortens prior-art triage while keeping "
                "the user's invention description, claim elements, comparison logic, and "
                "verification steps visible."
            ),
            source_label="extracted",
            confidence="low",
            rationale=(
                "The idea is framed as an automatic analysis tool, but the local input does "
                "not show a working workflow, time savings, or quality threshold."
            ),
        ),
        _ClaimSpec(
            text=(
                "Prior-art position is unresolved; the product must be differentiated from "
                "manual patent search, patent-office databases, generic AI assistants, "
                "spreadsheets, attorney intake workflows, and other analysis substitutes. "
                "If the narrow wedge is only a generic AI wrapper, defensibility and "
                "switching motivation are weak."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "This local pass does not perform web search, patent search, market research, "
                "or citation gathering."
            ),
        ),
        _ClaimSpec(
            text=(
                "Output reliability is a core product risk: summaries, claim charts, novelty "
                "flags, and comparison tables need a deterministic rubric, source traceability, "
                "error labels, and repeatable quality checks."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "No output samples, evaluation set, accuracy rubric, or failure analysis were "
                "provided."
            ),
        ),
        _ClaimSpec(
            text=(
                "The tool risks hallucinated or overconfident legal interpretation if it "
                "presents patentability, infringement, freedom-to-operate, filing, or legal "
                "strategy conclusions without verification and professional-review boundaries."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "Patent analysis touches legal interpretation risk, but the current concept "
                "does not define allowed output boundaries or review requirements."
            ),
        ),
        _ClaimSpec(
            text=(
                "Trust depends on verification boundaries: users need to see which outputs are "
                "grounded in supplied text, which are uncertain, which require source checks, "
                "and which must be escalated to a qualified professional."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "The idea promises analysis, but trust and verification behavior are not yet "
                "specified."
            ),
        ),
        _ClaimSpec(
            text=(
                "Buyer/workflow integration is unproven; adoption likely depends on importing "
                "an invention disclosure, saving search notes, exporting comparison tables, "
                "absorbing switching cost, and handing off reviewed outputs to founder, team, "
                "or attorney workflows."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "Integration needs are inferred from the patent-analysis workflow; no target "
                "user workflow artifacts were supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "SaaS retention depends on repeat usage triggers such as new invention ideas, "
                "competitor monitoring, disclosure reviews, investor diligence, office-action "
                "preparation, or portfolio refreshes; a one-time report may not support a "
                "subscription."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "Recurring use is a SaaS requirement, but the local input does not provide "
                "retention data or repeated job frequency."
            ),
        ),
        _ClaimSpec(
            text=(
                "Willingness to pay and distribution are unproven; the concept needs evidence "
                "for founder budget, pricing threshold, channel access, and why users would pay "
                "instead of using generic AI, manual search, or professional services."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "Marketability and differentiation are decision goals, but no buyer evidence, "
                "pricing tests, or distribution signal were supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "The idea is experimentable through workflow interviews, output-quality "
                "evaluation, trust and verification boundary checks, and differentiation "
                "mapping before any production SaaS build."
            ),
            source_label="extracted",
            confidence="medium",
            rationale=(
                "Minimum experiments can be proposed from the idea structure without collecting "
                "external evidence."
            ),
        ),
    ]


def _developer_tool_claim_specs(input_view: _InputView, focus: str) -> list[_ClaimSpec]:
    return [
        _concept_claim(input_view, focus),
        _ClaimSpec(
            text=(
                "Developer adoption depends on a specific target developer segment with "
                "pain in an existing debugging, observability, CLI, SDK, API, CI/CD, "
                "or local development workflow."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "The idea implies a developer workflow, but no developer interviews, "
                "workflow artifacts, or current-workaround evidence were supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "Setup complexity and integration burden are core product risks: the "
                "tool must prove time-to-first-value, configuration effort, permissions, "
                "and compatibility with the developer's existing stack."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "Developer tools often fail when setup or integration costs exceed the "
                "first useful debugging or observability payoff."
            ),
        ),
        _ClaimSpec(
            text=(
                "Debugging or observability value is unproven until the tool shows that "
                "logs, traces, errors, or workflow state become easier to inspect and act on."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "No before/after debugging task, observability artifact, or failure-analysis "
                "example was provided."
            ),
        ),
        _ClaimSpec(
            text=(
                "Ecosystem compatibility and switching cost are unresolved; the tool needs "
                "comparison against existing IDE, CLI, logging, monitoring, CI/CD, GitHub, "
                "and manual debugging workflows."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "This local pass does not compare the concept against current developer "
                "stacks or toolchain substitutes."
            ),
        ),
        _ClaimSpec(
            text=(
                "Documentation and support burden may block time-to-value if developers "
                "cannot understand installation, integration, error handling, or team rollout "
                "without handholding."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "Documentation needs are inferred from setup and integration risk; no docs "
                "comprehension evidence was supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "Repeat usage and workflow fit are unproven; durable value depends on "
                "recurring debugging, observability, monitoring, or development moments, not "
                "one successful setup session."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "No repeat-use trigger, usage log, or team adoption path was supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "The idea is experimentable through developer workflow interviews, setup "
                "friction tests, integration prototypes, time-to-first-value checks, "
                "documentation comprehension tests, and existing-tool comparisons."
            ),
            source_label="extracted",
            confidence="medium",
            rationale=(
                "Minimum developer-tool experiments can be proposed from the idea structure "
                "without collecting external evidence."
            ),
        ),
    ]


def _marketplace_claim_specs(input_view: _InputView, focus: str) -> list[_ClaimSpec]:
    return [
        _concept_claim(input_view, focus),
        _ClaimSpec(
            text=(
                "Marketplace viability depends on solving the liquidity problem with a "
                "specific cold-start wedge, local or niche density threshold, and clear "
                "chicken-and-egg strategy."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "The concept implies a two-sided market, but no liquidity threshold, density "
                "target, or cold-start evidence was supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "Supply-side acquisition and demand-side acquisition must be proven separately; "
                "seller/provider onboarding, buyer/customer demand, and retention by side cannot "
                "be treated as one generic user-adoption signal."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "No supply-side interviews, demand-side interviews, channel evidence, or "
                "side-specific retention signal was provided."
            ),
        ),
        _ClaimSpec(
            text=(
                "Matching efficiency is unproven until listings, booking flow, response time, "
                "quality control, and matching frequency show that the marketplace can create "
                "reliable transactions."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "The local input does not include concierge matches, completed bookings, "
                "matching latency, transaction frequency, or quality-control evidence."
            ),
        ),
        _ClaimSpec(
            text=(
                "Trust and safety, moderation burden, reputation system behavior, escrow or "
                "payment dispute boundaries, review abuse, fraud, and quality-control failure "
                "modes are unresolved marketplace blockers."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "Marketplaces depend on trust mechanisms, but no trust/safety review, "
                "moderation plan, dispute boundary, or reputation-system evidence was supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "Take-rate monetization, transaction frequency, repeat transactions, and "
                "disintermediation risk are unproven; the marketplace must show why both sides "
                "continue transacting through the platform instead of going direct."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "No pricing test, take-rate evidence, repeat transaction cohort, or "
                "off-platform substitution evidence was provided."
            ),
        ),
        _ClaimSpec(
            text=(
                "The idea is experimentable through supply-side interviews, demand-side "
                "interviews, concierge matching tests, liquidity threshold tests, cold-start "
                "landing pages, trust/safety risk reviews, pricing/take-rate tests, and repeat "
                "transaction cohort checks."
            ),
            source_label="extracted",
            confidence="medium",
            rationale=(
                "The marketplace structure can be decomposed into deterministic acquisition, "
                "matching, trust, monetization, and repeat-use validation steps."
            ),
        ),
    ]


def _enterprise_b2b_claim_specs(input_view: _InputView, focus: str) -> list[_ClaimSpec]:
    return [
        _concept_claim(input_view, focus),
        _ClaimSpec(
            text=(
                "Enterprise adoption depends on stakeholder alignment across the champion, "
                "budget owner, economic buyer, IT/security, procurement, and department "
                "workflow owners."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "The idea implies enterprise workflow value, but no stakeholder map, budget "
                "owner, or buyer/champion distinction was supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "Procurement path and ROI proof are unresolved; the product needs evidence "
                "for buying process, long sales cycle, approval steps, budget timing, and "
                "measurable ROI before enterprise confidence can rise."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "No procurement interview, budget-owner validation, purchase process, or ROI "
                "threshold was provided."
            ),
        ),
        _ClaimSpec(
            text=(
                "Security/compliance requirements are a core blocker: SOC2 expectations, "
                "security review, SSO, admin controls, audit logs, governance, data access, "
                "and IT approval must be known before rollout."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "Enterprise deployment depends on compliance and security review, but those "
                "requirements are not evidenced in the local input."
            ),
        ),
        _ClaimSpec(
            text=(
                "Integration burden and workflow integration depth are unmeasured; the concept "
                "must prove enterprise integration requirements, deployment responsibility, "
                "vendor reliability expectations, and compatibility with current systems."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "The current description does not measure integration work, reliability "
                "expectations, deployment ownership, or migration effort."
            ),
        ),
        _ClaimSpec(
            text=(
                "Rollout complexity, onboarding/training burden, and org-wide adoption risk "
                "remain open; enterprise value depends on repeatable department rollout, "
                "training cost, and support ownership."
            ),
            source_label="assumed",
            confidence="low",
            rationale=(
                "Rollout and enablement needs are inferred from the enterprise context; no "
                "rollout simulation, training test, or adoption plan was supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "Switching cost and vendor trust are unresolved; the product must compare "
                "against current enterprise systems, internal tools, manual processes, and "
                "vendor alternatives before claiming durable adoption."
            ),
            source_label="needs_evidence",
            confidence="low",
            rationale=(
                "No substitute map, migration plan, reliability proof, or vendor trust signal "
                "was supplied."
            ),
        ),
        _ClaimSpec(
            text=(
                "The idea is experimentable through procurement interviews, security/compliance "
                "review mapping, stakeholder mapping exercises, rollout simulations, onboarding "
                "friction tests, ROI validation interviews, and integration pilots."
            ),
            source_label="extracted",
            confidence="medium",
            rationale=(
                "Minimum enterprise B2B experiments can be proposed deterministically without "
                "collecting external evidence."
            ),
        ),
    ]


def _technical_feasibility_claim(signals: dict[str, bool]) -> _ClaimSpec:
    if signals["capsule"] and signals["medical"]:
        text = (
            "An ingestible capsule-style colon inspection device is technically plausible "
            "as a product concept, but feasibility depends on miniaturized sensing, power, "
            "data capture, safe transit, and reliable examination quality."
        )
    elif signals["hardware"]:
        text = (
            "The idea appears to require a physical device or equipment layer, so technical "
            "feasibility depends on manufacturable components, power, reliability, "
            "and safe use."
        )
    elif signals["software"]:
        text = (
            "The idea appears technically implementable as software, but feasibility depends "
            "on data availability, workflow fit, accuracy, security, and operational reliability."
        )
    else:
        text = (
            "The idea can likely be decomposed into testable technical components, but the "
            "critical feasibility constraints are not yet specified."
        )
    return _ClaimSpec(
        text=text,
        source_label="extracted",
        confidence="low",
        rationale=(
            "The raw idea gives a product direction, but does not provide engineering tests, "
            "materials data, prototypes, or performance results."
        ),
    )


def _user_need_claim(signals: dict[str, bool]) -> _ClaimSpec:
    if signals["medical"]:
        text = (
            "The concept targets a plausible user need around less burdensome colorectal "
            "inspection or screening, especially if it reduces discomfort, logistics, or "
            "avoidance compared with current care pathways."
        )
    else:
        text = (
            "The idea implies a user need, but the specific audience, pain intensity, and "
            "frequency of the problem are not yet proven."
        )
    return _ClaimSpec(
        text=text,
        source_label="assumed",
        confidence="low",
        rationale=(
            "User need is inferred from the idea framing; no interviews, usage data, or "
            "demand evidence were supplied."
        ),
    )


def _novelty_claim(signals: dict[str, bool]) -> _ClaimSpec:
    if signals["capsule"] and signals["medical"]:
        text = (
            "Novelty and prior-art position are unresolved; the idea needs comparison "
            "against capsule-based gastrointestinal inspection, colorectal screening "
            "workflows, biodegradable device materials, and disposal approaches."
        )
    else:
        text = (
            "Novelty and prior-art position are unresolved; the idea needs external "
            "comparison against existing products, research, patents, and substitutes."
        )
    return _ClaimSpec(
        text=text,
        source_label="needs_evidence",
        confidence="low",
        rationale=(
            "This local pass does not perform web search, patent search, market research, "
            "or citation gathering."
        ),
    )


def _safety_regulatory_claim(signals: dict[str, bool]) -> _ClaimSpec:
    if signals["medical_device"]:
        text = (
            "Because the product would be ingested and used for colon examination, it likely "
            "requires medical-device safety, biocompatibility, sanitation, data-quality, "
            "clinical, and regulatory validation before human use."
        )
        source_label = "extracted"
    elif signals["regulated"]:
        text = (
            "The idea may involve regulated or safety-sensitive use, so legal, safety, "
            "privacy, and compliance requirements must be identified before launch."
        )
        source_label = "needs_evidence"
    else:
        text = (
            "Safety and regulatory exposure are not established yet; any physical-world, "
            "health, finance, legal, child, or sensitive-data use would require "
            "explicit review."
        )
        source_label = "needs_evidence"
    return _ClaimSpec(
        text=text,
        source_label=source_label,
        confidence="low",
        rationale=(
            "The local input is enough to flag possible safety review, but not enough to "
            "establish compliance requirements or approval paths."
        ),
    )


def _implementation_claim(signals: dict[str, bool]) -> _ClaimSpec:
    if signals["capsule"] and signals["medical"] and signals["environmental"]:
        text = (
            "Implementation would need to specify inspection modality, capsule retention "
            "and transit behavior, data retrieval, biocompatible materials, manufacturing, "
            "and what happens after wastewater discharge."
        )
    elif signals["hardware"]:
        text = (
            "Implementation would need a concrete bill of materials, prototype path, safety "
            "tests, manufacturing assumptions, and maintenance workflow."
        )
    elif signals["software"]:
        text = (
            "Implementation would need user flows, data inputs, deterministic behavior, "
            "security controls, failure handling, and measurable quality checks."
        )
    else:
        text = (
            "Implementation would need a clearer workflow, required resources, operating "
            "constraints, failure modes, and owner responsibilities."
        )
    return _ClaimSpec(
        text=text,
        source_label="extracted",
        confidence="low",
        rationale=(
            "The implementation components are derived from the idea category, while the "
            "actual design details remain unspecified."
        ),
    )


def _environmental_claim() -> _ClaimSpec:
    return _ClaimSpec(
        text=(
            "The environmental claim depends on measured degradation behavior after discharge, "
            "including breakdown timing, byproducts, wastewater compatibility, and whether "
            "the structure avoids shifting risk into sewage treatment systems."
        ),
        source_label="needs_evidence",
        confidence="low",
        rationale=(
            "The raw idea states an eco-friendly degradation outcome, but provides no material "
            "test, lifecycle analysis, or wastewater evidence."
        ),
    )


def _market_claim(signals: dict[str, bool]) -> _ClaimSpec:
    if signals["medical"]:
        text = (
            "The plausible market includes colorectal screening stakeholders, but buyer, "
            "payer, clinician, institution, and patient adoption are unproven."
        )
    elif signals["market"]:
        text = (
            "The idea may have a commercial audience, but segment size, buyer urgency, "
            "willingness to pay, and competing alternatives are unproven."
        )
    else:
        text = (
            "Market relevance is unknown until the target audience, budget owner, competing "
            "alternatives, and adoption trigger are identified."
        )
    return _ClaimSpec(
        text=text,
        source_label="assumed",
        confidence="low",
        rationale=(
            "Market demand is not established by the local idea text or by any supplied "
            "evidence."
        ),
    )


def _experimentability_claim(signals: dict[str, bool]) -> _ClaimSpec:
    if signals["capsule"] and signals["medical"] and signals["environmental"]:
        text = (
            "The idea is experimentable through non-clinical first steps such as capsule-size "
            "mockups, bench material degradation tests, data-capture prototypes, workflow "
            "interviews, and simulated disposal checks before any human testing."
        )
    elif signals["hardware"]:
        text = (
            "The idea is experimentable through small prototypes, bench tests, failure-mode "
            "reviews, and user workflow observations before expensive development."
        )
    elif signals["software"]:
        text = (
            "The idea is experimentable through a local prototype, task-based user trial, "
            "quality rubric, and error analysis before production integration."
        )
    else:
        text = (
            "The idea is experimentable if it is reduced to one falsifiable hypothesis, one "
            "target user, and one observable success metric."
        )
    return _ClaimSpec(
        text=text,
        source_label="extracted",
        confidence="medium",
        rationale=(
            "Minimum experiments can be proposed from the idea structure without collecting "
            "external evidence."
        ),
    )


def _dedupe_specs(specs: list[_ClaimSpec]) -> list[_ClaimSpec]:
    seen: set[str] = set()
    deduped: list[_ClaimSpec] = []
    for spec in specs:
        key = spec.text.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(spec)
    return deduped
