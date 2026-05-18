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


def extract_claims(input_data: Any, goal: Any = None) -> list[Claim]:
    """Extract deterministic structured claims from a ResearchCouncilInput-like value.

    Accepted inputs include a ResearchCouncilInput instance, an object with
    matching attributes, a mapping with ``raw_idea``/``goal`` keys, a
    ``(raw_idea, goal)`` sequence, a raw idea string, or raw idea and goal
    strings passed as two arguments.
    """

    input_view = _coerce_input(input_data, goal_override=goal)
    signals = _detect_signals(input_view)
    focus = _idea_focus(input_view.raw_idea)

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


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


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
            "This claim restates the user's local input and anchors the research pass "
            f"to the stated goal: {goal}"
        ),
    )


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
