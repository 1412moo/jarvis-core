"""Deterministic scenario generation templates for benchmark scalability."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any

from .llm_advisor import LLMAugmentationMode


SCENARIO_GOAL = "Evaluate deterministic scenario template robustness for this concept."

PROFILE_ORDER = (
    "ai_saas",
    "developer_tool",
    "enterprise_b2b",
    "marketplace",
    "creator_tools",
    "medical_device",
    "general",
)

CATEGORY_ORDER = (
    "negation_template",
    "weak_keyword_template",
    "contamination_template",
    "structural_anchor_template",
    "confidence_escalation_template",
    "ambiguity_template",
)


@dataclass(frozen=True)
class ScenarioTemplate:
    """One fixed template pattern for deterministic scenario generation."""

    template_id: str
    category: str
    pattern: str
    description: str


@dataclass(frozen=True)
class GeneratedScenario:
    """One generated deterministic scenario with optional mutation expectations."""

    scenario_id: str
    category: str
    profile_id: str
    raw_idea: str
    goal: str = SCENARIO_GOAL
    expected_profile: str | None = None
    forbidden_profiles: tuple[str, ...] = ()
    zero_score_profiles: tuple[str, ...] = ()
    require_consistency_pass: bool = False
    llm_augmentation_mode: str = LLMAugmentationMode.OFF.value
    expected_rejection_reasons: tuple[str, ...] = ()
    forbidden_accepted_terms: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScenarioTemplateSummary:
    """Aggregate telemetry for generated deterministic scenarios."""

    scenarios: tuple[GeneratedScenario, ...]

    @property
    def total_scenarios(self) -> int:
        return len(self.scenarios)

    @property
    def categories_covered(self) -> tuple[str, ...]:
        return tuple(sorted({scenario.category for scenario in self.scenarios}))

    @property
    def profiles_covered(self) -> tuple[str, ...]:
        return tuple(
            profile_id
            for profile_id in PROFILE_ORDER
            if any(scenario.profile_id == profile_id for scenario in self.scenarios)
        )

    @property
    def cases_by_category(self) -> Mapping[str, int]:
        counter: Counter[str] = Counter(scenario.category for scenario in self.scenarios)
        return {category: counter[category] for category in sorted(counter)}

    @property
    def cases_by_profile(self) -> Mapping[str, int]:
        counter: Counter[str] = Counter(scenario.profile_id for scenario in self.scenarios)
        return {
            profile_id: counter[profile_id]
            for profile_id in PROFILE_ORDER
            if counter[profile_id]
        }


@dataclass(frozen=True)
class _ProfileScenarioSpec:
    profile_id: str
    strong_anchor: str
    weak_terms: tuple[str, ...]
    workflow_term: str
    required_terms: tuple[str, ...]
    pitch: str
    contamination_noise: str
    ambiguity_signal: str


def build_scenario_templates() -> tuple[ScenarioTemplate, ...]:
    """Return fixed scenario templates in stable category order."""

    return (
        ScenarioTemplate(
            template_id="negation_template",
            category="negation_template",
            pattern="No {profile_anchor}, {weak_terms}, or {workflow_term} is planned.",
            description="Negated anchor and weak-term list should not select the negated profile.",
        ),
        ScenarioTemplate(
            template_id="weak_keyword_template",
            category="weak_keyword_template",
            pattern="{weak_terms} management app for small teams without {profile_anchor}.",
            description="Weak wording should not over-select a specialized profile.",
        ),
        ScenarioTemplate(
            template_id="contamination_template",
            category="contamination_template",
            pattern="{intended_profile_pitch} Also mentions {other_profile_noise}.",
            description="Intended profile should survive realistic cross-profile noise.",
        ),
        ScenarioTemplate(
            template_id="structural_anchor_template",
            category="structural_anchor_template",
            pattern="{strong_profile_anchor} with {required_reasoning_terms}.",
            description="Strong structural anchors should select the intended profile.",
        ),
        ScenarioTemplate(
            template_id="confidence_escalation_template",
            category="confidence_escalation_template",
            pattern="{intended_profile_pitch} Claims guaranteed adoption and proven safety without evidence.",
            description="Confidence escalation language should remain bounded by evidence.",
        ),
        ScenarioTemplate(
            template_id="ambiguity_template",
            category="ambiguity_template",
            pattern="Broad product pitch with {mixed_weak_signals} and no strong anchor.",
            description="Ambiguous mixed signals should not rely on a single weak keyword.",
        ),
    )


def generate_scenarios(
    category: str | None = None,
    profiles: Sequence[str] | None = None,
) -> tuple[GeneratedScenario, ...]:
    """Generate deterministic scenario cases from fixed templates."""

    selected_categories = _selected_categories(category)
    selected_profiles = _selected_profiles(profiles)
    scenarios: list[GeneratedScenario] = []
    specs = {spec.profile_id: spec for spec in _profile_specs()}
    for category_id in selected_categories:
        for profile_id in selected_profiles:
            spec = specs[profile_id]
            scenarios.append(_build_generated_scenario(category_id, spec))
    return tuple(scenarios)


def build_scenario_summary(
    scenarios: Sequence[GeneratedScenario] | None = None,
) -> ScenarioTemplateSummary:
    """Build deterministic scenario generation telemetry."""

    return ScenarioTemplateSummary(tuple(scenarios) if scenarios is not None else generate_scenarios())


def format_scenario_summary(summary: ScenarioTemplateSummary) -> str:
    """Format scenario generation as concise deterministic telemetry."""

    return (
        "Scenario templates generated: "
        f"{summary.total_scenarios} {_plural(summary.total_scenarios, 'scenario')}, "
        f"{len(summary.categories_covered)} "
        f"{_plural(len(summary.categories_covered), 'category')}, "
        f"{len(summary.profiles_covered)} {_plural(len(summary.profiles_covered), 'profile')}."
    )


def scenario_to_json_dict(scenario: GeneratedScenario) -> dict[str, Any]:
    """Convert a generated scenario to a deterministic JSON-ready mapping."""

    return {
        "category": scenario.category,
        "expected_profile": scenario.expected_profile,
        "forbidden_accepted_terms": list(scenario.forbidden_accepted_terms),
        "forbidden_profiles": list(scenario.forbidden_profiles),
        "goal": scenario.goal,
        "llm_augmentation_mode": scenario.llm_augmentation_mode,
        "profile_id": scenario.profile_id,
        "raw_idea": scenario.raw_idea,
        "require_consistency_pass": scenario.require_consistency_pass,
        "scenario_id": scenario.scenario_id,
        "tags": list(scenario.tags),
        "expected_rejection_reasons": list(scenario.expected_rejection_reasons),
        "zero_score_profiles": list(scenario.zero_score_profiles),
    }


def summary_to_json_dict(summary: ScenarioTemplateSummary) -> dict[str, Any]:
    """Convert scenario telemetry to deterministic JSON-ready data."""

    return {
        "cases_by_category": dict(summary.cases_by_category),
        "cases_by_profile": dict(summary.cases_by_profile),
        "categories_covered": list(summary.categories_covered),
        "profiles_covered": list(summary.profiles_covered),
        "scenarios": [scenario_to_json_dict(scenario) for scenario in summary.scenarios],
        "total_scenarios": summary.total_scenarios,
    }


def scenarios_to_json(summary: ScenarioTemplateSummary) -> str:
    """Serialize generated scenarios as stable JSON."""

    return json.dumps(summary_to_json_dict(summary), indent=2, sort_keys=True) + "\n"


def _build_generated_scenario(
    category: str,
    spec: _ProfileScenarioSpec,
) -> GeneratedScenario:
    builder = {
        "negation_template": _negation_scenario,
        "weak_keyword_template": _weak_keyword_scenario,
        "contamination_template": _contamination_scenario,
        "structural_anchor_template": _structural_anchor_scenario,
        "confidence_escalation_template": _confidence_escalation_scenario,
        "ambiguity_template": _ambiguity_scenario,
    }[category]
    return builder(spec)


def _negation_scenario(spec: _ProfileScenarioSpec) -> GeneratedScenario:
    weak_terms = ", ".join(spec.weak_terms[:3])
    raw_idea = (
        f"No {spec.strong_anchor}, {weak_terms}, or {spec.workflow_term} is planned. "
        "This is a broad internal planning concept with no specialized operating model."
    )
    zero_profiles = () if spec.profile_id == "general" else (spec.profile_id,)
    return GeneratedScenario(
        scenario_id=f"scenario_negation_{spec.profile_id}",
        category="negation_template",
        profile_id=spec.profile_id,
        raw_idea=raw_idea,
        forbidden_profiles=zero_profiles,
        zero_score_profiles=zero_profiles,
        tags=("negation", "selector_guard"),
    )


def _weak_keyword_scenario(spec: _ProfileScenarioSpec) -> GeneratedScenario:
    weak_terms = ", ".join(spec.weak_terms)
    raw_idea = (
        f"{weak_terms} management app for small teams without {spec.strong_anchor} "
        f"or {spec.workflow_term}."
    )
    zero_profiles = (
        (spec.profile_id,)
        if spec.profile_id in {"marketplace", "creator_tools", "developer_tool"}
        else ()
    )
    return GeneratedScenario(
        scenario_id=f"scenario_weak_keyword_{spec.profile_id}",
        category="weak_keyword_template",
        profile_id=spec.profile_id,
        raw_idea=raw_idea,
        forbidden_profiles=zero_profiles,
        zero_score_profiles=zero_profiles,
        tags=("weak_keyword", "over_selection_guard"),
    )


def _contamination_scenario(spec: _ProfileScenarioSpec) -> GeneratedScenario:
    return GeneratedScenario(
        scenario_id=f"scenario_contamination_{spec.profile_id}",
        category="contamination_template",
        profile_id=spec.profile_id,
        raw_idea=(
            f"{spec.pitch} Also mentions {spec.contamination_noise} as secondary "
            "marketing copy, but the operating model remains unchanged."
        ),
        expected_profile=None if spec.profile_id == "general" else spec.profile_id,
        forbidden_profiles=(),
        require_consistency_pass=spec.profile_id != "general",
        tags=("contamination", "profile_boundary"),
    )


def _structural_anchor_scenario(spec: _ProfileScenarioSpec) -> GeneratedScenario:
    required_terms = ", ".join(spec.required_terms)
    return GeneratedScenario(
        scenario_id=f"scenario_structural_anchor_{spec.profile_id}",
        category="structural_anchor_template",
        profile_id=spec.profile_id,
        raw_idea=f"{spec.strong_anchor} with {required_terms}.",
        expected_profile=spec.profile_id,
        require_consistency_pass=True,
        tags=("structural_anchor", "positive_selection"),
    )


def _confidence_escalation_scenario(spec: _ProfileScenarioSpec) -> GeneratedScenario:
    rejection_reasons: tuple[str, ...] = ("unsupported confidence escalation",)
    forbidden_terms: tuple[str, ...] = (
        "high confidence",
        "concept is proven",
        "safe to proceed",
    )
    raw_idea = (
        f"{spec.pitch} Marketing copy says guaranteed adoption, proven ROI, and high "
        "confidence without evidence."
    )
    if spec.profile_id == "medical_device":
        raw_idea = (
            f"{spec.pitch} Marketing copy says clinically validated, regulatory cleared, "
            "safe for patients, and high confidence without evidence."
        )
        rejection_reasons = ("unsafe medical claim", "unsupported confidence escalation")
        forbidden_terms = (
            "safe for patients",
            "clinically validated",
            "regulatory cleared",
            "high confidence",
            "concept is proven",
        )

    return GeneratedScenario(
        scenario_id=f"scenario_confidence_escalation_{spec.profile_id}",
        category="confidence_escalation_template",
        profile_id=spec.profile_id,
        raw_idea=raw_idea,
        expected_profile=spec.profile_id if spec.profile_id != "general" else None,
        require_consistency_pass=True,
        llm_augmentation_mode=LLMAugmentationMode.TEST_NOISY.value,
        expected_rejection_reasons=rejection_reasons,
        forbidden_accepted_terms=forbidden_terms,
        tags=("confidence_escalation", "augmentation_validation"),
    )


def _ambiguity_scenario(spec: _ProfileScenarioSpec) -> GeneratedScenario:
    expected_profile = "general" if spec.profile_id == "general" else None
    return GeneratedScenario(
        scenario_id=f"scenario_ambiguity_{spec.profile_id}",
        category="ambiguity_template",
        profile_id=spec.profile_id,
        raw_idea=(
            "Broad product pitch with "
            f"{spec.ambiguity_signal}, light automation claims, dashboard reporting, "
            "and no strong workflow, buyer, safety, or marketplace anchor."
        ),
        expected_profile=expected_profile,
        forbidden_profiles=() if spec.profile_id == "general" else (spec.profile_id,),
        tags=("ambiguity", "weak_signal"),
    )


def _selected_categories(category: str | None) -> tuple[str, ...]:
    if category is None:
        return CATEGORY_ORDER
    if category not in CATEGORY_ORDER:
        raise ValueError(f"unknown scenario template category: {category}")
    return (category,)


def _selected_profiles(profiles: Sequence[str] | None) -> tuple[str, ...]:
    if profiles is None:
        return PROFILE_ORDER
    unknown = tuple(profile_id for profile_id in profiles if profile_id not in PROFILE_ORDER)
    if unknown:
        raise ValueError("unknown scenario template profile: " + ", ".join(sorted(unknown)))
    return tuple(profile_id for profile_id in PROFILE_ORDER if profile_id in set(profiles))


def _profile_specs() -> tuple[_ProfileScenarioSpec, ...]:
    return (
        _ProfileScenarioSpec(
            profile_id="ai_saas",
            strong_anchor="AI SaaS workflow assistant",
            weak_terms=("automation", "dashboard", "subscription"),
            workflow_term="buyer workflow",
            required_terms=("workflow", "buyer", "retention", "differentiation", "reliability"),
            pitch=(
                "An AI SaaS workflow assistant for finance teams with buyer workflow "
                "ownership, retention triggers, differentiation risk, and reliability checks."
            ),
            contamination_noise="booking reviews and local listings language",
            ambiguity_signal="content analytics and workflow dashboards",
        ),
        _ProfileScenarioSpec(
            profile_id="developer_tool",
            strong_anchor="developer workflow CLI tool",
            weak_terms=("logs", "dashboard", "monitoring"),
            workflow_term="setup complexity",
            required_terms=(
                "developer workflow",
                "setup complexity",
                "integration burden",
                "time-to-value",
                "compatibility",
            ),
            pitch=(
                "A developer workflow CLI for production debugging with setup complexity, "
                "integration burden, observability value, compatibility, and time-to-value."
            ),
            contamination_noise="enterprise procurement and compliance claims",
            ambiguity_signal="logs and reporting references",
        ),
        _ProfileScenarioSpec(
            profile_id="enterprise_b2b",
            strong_anchor="enterprise workflow platform",
            weak_terms=("security", "compliance", "ROI"),
            workflow_term="procurement path",
            required_terms=(
                "procurement",
                "stakeholder alignment",
                "budget owner",
                "security/compliance",
                "rollout",
                "ROI",
            ),
            pitch=(
                "An enterprise B2B workflow platform with procurement, budget owner "
                "clarity, stakeholder alignment, security/compliance review, rollout, and ROI proof."
            ),
            contamination_noise="developer logs and observability wording",
            ambiguity_signal="security and rollout buzzwords",
        ),
        _ProfileScenarioSpec(
            profile_id="marketplace",
            strong_anchor="two-sided marketplace",
            weak_terms=("booking", "reviews", "transaction"),
            workflow_term="supply and demand loop",
            required_terms=(
                "liquidity",
                "supply/demand",
                "cold start",
                "trust/safety",
                "transaction frequency",
            ),
            pitch=(
                "A two-sided marketplace for local services with supply and demand, "
                "liquidity thresholds, cold-start density, trust/safety, and transaction frequency."
            ),
            contamination_noise="SaaS workflow dashboard language",
            ambiguity_signal="booking and reviews wording",
        ),
        _ProfileScenarioSpec(
            profile_id="creator_tools",
            strong_anchor="creator tool for newsletter creators",
            weak_terms=("content calendar", "monetization", "distribution channel"),
            workflow_term="creator workflow",
            required_terms=(
                "creator workflow",
                "content production",
                "audience growth",
                "fan community",
                "monetization",
                "platform dependency",
            ),
            pitch=(
                "A creator tool for newsletter creators and streamers with creator workflow, "
                "content production cadence, audience growth, fan community engagement, "
                "monetization, and platform dependency risk."
            ),
            contamination_noise="marketplace community and listing wording",
            ambiguity_signal="content marketing and monetization analytics",
        ),
        _ProfileScenarioSpec(
            profile_id="medical_device",
            strong_anchor="medical device concept",
            weak_terms=("clinical", "remote monitoring", "screening"),
            workflow_term="intended use",
            required_terms=(
                "patient safety",
                "clinical validation",
                "regulatory",
                "intended use",
                "conservative confidence",
            ),
            pitch=(
                "A medical device concept for remote monitoring with intended use limits, "
                "patient safety boundaries, clinical validation needs, regulatory pathway "
                "uncertainty, and conservative confidence."
            ),
            contamination_noise="business ROI and adoption claims",
            ambiguity_signal="wellness monitoring and optimistic clinical language",
        ),
        _ProfileScenarioSpec(
            profile_id="general",
            strong_anchor="broad business concept",
            weak_terms=("planning", "notes", "reports"),
            workflow_term="target user definition",
            required_terms=("target user", "problem severity", "alternatives", "adoption evidence"),
            pitch=(
                "A broad business concept for organizing team planning notes with unclear "
                "target user, problem severity, alternatives, and adoption evidence."
            ),
            contamination_noise="AI, marketplace, enterprise, creator, developer, and medical buzzwords",
            ambiguity_signal="mixed business buzzwords",
        ),
    )


def _plural(count: int, singular: str) -> str:
    if count == 1:
        return singular
    if singular == "category":
        return "categories"
    return singular + "s"


__all__ = [
    "CATEGORY_ORDER",
    "PROFILE_ORDER",
    "GeneratedScenario",
    "SCENARIO_GOAL",
    "ScenarioTemplate",
    "ScenarioTemplateSummary",
    "build_scenario_summary",
    "build_scenario_templates",
    "format_scenario_summary",
    "generate_scenarios",
    "scenario_to_json_dict",
    "scenarios_to_json",
    "summary_to_json_dict",
]
