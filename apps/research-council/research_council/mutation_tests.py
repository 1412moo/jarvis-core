"""Deterministic mutation tests for Research Council profile robustness."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

from .evaluation import ConsistencyResult, evaluate_profile_consistency
from .json_export import result_to_json_dict
from .llm_advisor import LLMAugmentationMode
from .pipeline import run_research_council
from .schemas import ResearchCouncilInput


_MUTATION_GOAL = "Evaluate deterministic mutation robustness for this concept."


@dataclass(frozen=True)
class MutationCase:
    """One fixed mutation fixture with deterministic expectations."""

    case_id: str
    category: str
    input_data: ResearchCouncilInput
    expected_profile: str | None = None
    forbidden_profiles: tuple[str, ...] = ()
    zero_score_profiles: tuple[str, ...] = ()
    require_consistency_pass: bool = False
    llm_augmentation_mode: str = LLMAugmentationMode.OFF.value
    expected_rejection_reasons: tuple[str, ...] = ()
    forbidden_accepted_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class MutationFailure:
    """One concise mutation failure."""

    kind: str
    message: str


@dataclass(frozen=True)
class MutationResult:
    """Result for one deterministic mutation case."""

    case_id: str
    category: str
    selected_profile: str
    failures: tuple[MutationFailure, ...] = ()
    consistency_result: ConsistencyResult | None = None
    augmentation_accepted: int = 0
    augmentation_filtered: int = 0
    augmentation_rejected: int = 0

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(frozen=True)
class MutationSummary:
    """Aggregate deterministic mutation-test telemetry."""

    results: tuple[MutationResult, ...]

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def passed_cases(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def failed_cases(self) -> int:
        return self.total_cases - self.passed_cases

    @property
    def passed(self) -> bool:
        return self.failed_cases == 0

    @property
    def categories_covered(self) -> tuple[str, ...]:
        return tuple(sorted({result.category for result in self.results}))

    @property
    def profile_drift_failures(self) -> int:
        return _failure_count(self.results, "profile_drift")

    @property
    def contamination_failures(self) -> int:
        return _failure_count(self.results, "contamination")

    @property
    def unsafe_acceptance_failures(self) -> int:
        return _failure_count(self.results, "unsafe_acceptance")

    @property
    def failures(self) -> tuple[tuple[MutationResult, MutationFailure], ...]:
        return tuple(
            (result, failure)
            for result in self.results
            for failure in result.failures
        )


def build_mutation_cases() -> tuple[MutationCase, ...]:
    """Build the fixed deterministic mutation suite."""

    return (
        _case(
            "negated_developer_tool_list",
            "negation",
            (
                "No SDK, CLI, logs, or observability workflow is planned. "
                "This is a simple workflow assistant for office notes."
            ),
            forbidden_profiles=("developer_tool",),
            zero_score_profiles=("developer_tool",),
        ),
        _case(
            "negated_marketplace_list",
            "negation",
            (
                "No marketplace, sellers, buyers, listings, or transaction loop is planned. "
                "This is internal scheduling software."
            ),
            forbidden_profiles=("marketplace",),
            zero_score_profiles=("marketplace",),
        ),
        _case(
            "negated_creator_tools_list",
            "negation",
            (
                "No creator platform, fan community, content calendar, distribution channel, "
                "platform dependency, or monetization workflow is planned. This is a simple "
                "marketing report app."
            ),
            forbidden_profiles=("creator_tools",),
            zero_score_profiles=("creator_tools",),
        ),
        _case(
            "weak_booking_reviews_noise",
            "weak_keyword",
            (
                "A booking and reviews management dashboard for solo service businesses "
                "with reminders and reports."
            ),
            forbidden_profiles=("marketplace",),
            zero_score_profiles=("marketplace",),
        ),
        _case(
            "weak_content_marketing_noise",
            "weak_keyword",
            (
                "A content marketing analytics dashboard for campaigns, distribution channel "
                "attribution, and monetization reports."
            ),
            forbidden_profiles=("creator_tools",),
            zero_score_profiles=("creator_tools",),
        ),
        _case(
            "weak_logs_dashboard_noise",
            "weak_keyword",
            (
                "A logs and dashboard reporting SaaS for managers to review weekly uptime "
                "summaries."
            ),
            forbidden_profiles=("developer_tool",),
        ),
        _case(
            "marketplace_structural_anchor",
            "structural_anchor",
            (
                "A two-sided marketplace for local repair jobs that balances supply and "
                "demand, liquidity, cold start density, trust and safety, booking, reviews, "
                "and repeat transaction frequency."
            ),
            expected_profile="marketplace",
            require_consistency_pass=True,
        ),
        _case(
            "creator_tools_structural_anchor",
            "structural_anchor",
            (
                "A creator tool for newsletter creators and streamers that improves creator "
                "workflow, content production cadence, audience growth, fan community "
                "engagement, monetization, and platform dependency risk."
            ),
            expected_profile="creator_tools",
            require_consistency_pass=True,
        ),
        _case(
            "developer_tool_structural_anchor",
            "structural_anchor",
            (
                "A developer workflow CLI tool for debugging production logs, observability "
                "traces, setup complexity, integration burden, API compatibility, and "
                "time-to-first-value."
            ),
            expected_profile="developer_tool",
            require_consistency_pass=True,
        ),
        _case(
            "ai_saas_with_marketplace_noise",
            "contamination",
            (
                "An AI SaaS workflow assistant for finance teams that automates invoice "
                "exception review, reliability checks, buyer workflow ownership, retention "
                "triggers, and differentiation; the page also has vague booking and reviews "
                "wording but no two-sided marketplace."
            ),
            expected_profile="ai_saas",
            forbidden_profiles=("marketplace",),
            require_consistency_pass=True,
        ),
        _case(
            "enterprise_with_devtool_noise",
            "contamination",
            (
                "An enterprise B2B workflow platform for procurement teams with budget owner "
                "clarity, stakeholder alignment, rollout planning, security/compliance review, "
                "audit controls, and ROI proof, while engineers also mention logs and "
                "observability dashboards."
            ),
            expected_profile="enterprise_b2b",
            require_consistency_pass=True,
        ),
        _case(
            "marketplace_with_saas_dashboard_noise",
            "contamination",
            (
                "A two-sided marketplace for local pet services with supply-side providers, "
                "demand-side customers, liquidity thresholds, cold-start neighborhoods, "
                "trust/safety reviews, booking, and transaction frequency, plus an admin SaaS "
                "dashboard for operators."
            ),
            expected_profile="marketplace",
            require_consistency_pass=True,
        ),
        _case(
            "medical_device_with_business_roi_noise",
            "contamination",
            (
                "A medical device concept for remote monitoring with intended use limits, "
                "patient safety boundaries, clinical validation needs, regulatory pathway "
                "uncertainty, and conservative confidence, despite business ROI language from "
                "sales planning."
            ),
            expected_profile="medical_device",
            require_consistency_pass=True,
        ),
        _case(
            "medical_noisy_unsafe_augmentation",
            "unsafe_confidence",
            (
                "A medical device concept for at-home respiratory monitoring that still needs "
                "intended use definition, patient safety evidence, clinical validation, and "
                "regulatory pathway review."
            ),
            expected_profile="medical_device",
            require_consistency_pass=True,
            llm_augmentation_mode=LLMAugmentationMode.TEST_NOISY.value,
            expected_rejection_reasons=(
                "unsafe medical claim",
                "unsupported confidence escalation",
            ),
            forbidden_accepted_terms=(
                "safe for patients",
                "clinically validated",
                "regulatory cleared",
                "high confidence",
                "concept is proven",
            ),
        ),
        _case(
            "general_noisy_confidence_escalation",
            "unsafe_confidence",
            (
                "A broad product concept for teams to organize notes, tasks, and planning "
                "rituals without a clear target user, severe problem, adoption evidence, or "
                "specialized domain anchor."
            ),
            require_consistency_pass=True,
            llm_augmentation_mode=LLMAugmentationMode.TEST_NOISY.value,
            expected_rejection_reasons=("unsupported confidence escalation",),
            forbidden_accepted_terms=("high confidence", "concept is proven", "safe to proceed"),
        ),
        _case(
            "marketplace_noisy_profile_contamination",
            "unsafe_confidence",
            (
                "A two-sided marketplace for home repair with supply-side contractors, "
                "demand-side homeowners, cold-start neighborhoods, liquidity, booking, "
                "trust/safety, and repeat transaction frequency."
            ),
            expected_profile="marketplace",
            require_consistency_pass=True,
            llm_augmentation_mode=LLMAugmentationMode.TEST_NOISY.value,
            expected_rejection_reasons=(
                "profile contamination",
                "unsupported confidence escalation",
            ),
            forbidden_accepted_terms=("procurement path", "security/compliance requirements"),
        ),
    )


def run_mutation_tests(
    cases: Sequence[MutationCase] | None = None,
) -> MutationSummary:
    """Run deterministic mutation cases through existing pipeline contracts."""

    mutation_cases = tuple(cases) if cases is not None else build_mutation_cases()
    return MutationSummary(
        results=tuple(_run_mutation_case(mutation_case) for mutation_case in mutation_cases)
    )


def format_mutation_summary(summary: MutationSummary) -> str:
    """Format mutation results as concise deterministic telemetry."""

    category_count = len(summary.categories_covered)
    if summary.passed:
        return (
            "Mutation tests passed: "
            f"{summary.passed_cases}/{summary.total_cases} cases, "
            f"{category_count} categories, "
            f"{summary.profile_drift_failures} profile drift failures, "
            f"{summary.contamination_failures} contamination failures, "
            f"{summary.unsafe_acceptance_failures} unsafe acceptance failures."
        )

    lines = [
        "Mutation test failures: "
        f"{summary.failed_cases}/{summary.total_cases} cases failed across "
        f"{category_count} categories.",
        (
            "Failure counts: "
            f"profile_drift={summary.profile_drift_failures}, "
            f"contamination={summary.contamination_failures}, "
            f"unsafe_acceptance={summary.unsafe_acceptance_failures}."
        ),
    ]
    for result, failure in summary.failures:
        lines.append(
            f"- {result.case_id} [{result.category}/{failure.kind}]: {failure.message}"
        )
    return "\n".join(lines)


def _run_mutation_case(mutation_case: MutationCase) -> MutationResult:
    result = run_research_council(
        mutation_case.input_data,
        llm_advisor_config=mutation_case.llm_augmentation_mode,
    )
    payload = result_to_json_dict(result)
    profile = _mapping(payload.get("profile"))
    selected_profile = str(profile.get("profile_id", ""))
    score_by_profile = _mapping(profile.get("score_by_profile"))
    matched_keywords = _mapping(profile.get("matched_keywords"))
    augmentation = _mapping(payload.get("optional_llm_augments"))
    consistency = evaluate_profile_consistency(selected_profile, payload)

    failures: list[MutationFailure] = []
    if (
        mutation_case.expected_profile is not None
        and selected_profile != mutation_case.expected_profile
    ):
        failures.append(
            MutationFailure(
                "profile_drift",
                (
                    f"expected {mutation_case.expected_profile}, "
                    f"selected {selected_profile or '<missing>'}"
                ),
            )
        )

    for forbidden_profile in mutation_case.forbidden_profiles:
        if selected_profile == forbidden_profile:
            failures.append(
                MutationFailure(
                    "profile_drift",
                    f"forbidden profile selected: {forbidden_profile}",
                )
            )

    for profile_id in mutation_case.zero_score_profiles:
        score = _int_value(score_by_profile.get(profile_id))
        matches = tuple(str(item) for item in _sequence(matched_keywords.get(profile_id)))
        if score or matches:
            failures.append(
                MutationFailure(
                    "profile_drift",
                    (
                        f"negated/weak {profile_id} signal scored {score} "
                        f"with matches: {', '.join(matches) or '<none>'}"
                    ),
                )
            )

    if (
        mutation_case.require_consistency_pass
        and consistency is not None
        and not consistency.passed
    ):
        failures.append(MutationFailure("contamination", consistency.message))

    rejected_reasons = _rejected_reason_text(augmentation)
    for reason in mutation_case.expected_rejection_reasons:
        if _normalize_text(reason) not in rejected_reasons:
            failures.append(
                MutationFailure(
                    "unsafe_acceptance",
                    f"missing rejection reason: {reason}",
                )
            )

    accepted_text = _accepted_augmentation_text(augmentation)
    accepted_matches = tuple(
        term
        for term in mutation_case.forbidden_accepted_terms
        if _normalize_text(term) in accepted_text
    )
    if accepted_matches:
        failures.append(
            MutationFailure(
                "unsafe_acceptance",
                "forbidden accepted augmentation wording: "
                + ", ".join(accepted_matches),
            )
        )

    return MutationResult(
        case_id=mutation_case.case_id,
        category=mutation_case.category,
        selected_profile=selected_profile,
        failures=tuple(failures),
        consistency_result=consistency,
        augmentation_accepted=_int_value(augmentation.get("accepted_count")),
        augmentation_filtered=_int_value(augmentation.get("filtered_count")),
        augmentation_rejected=_int_value(augmentation.get("rejected_count")),
    )


def _case(
    case_id: str,
    category: str,
    raw_idea: str,
    **kwargs: Any,
) -> MutationCase:
    return MutationCase(
        case_id=case_id,
        category=category,
        input_data=ResearchCouncilInput(raw_idea=raw_idea, goal=_MUTATION_GOAL),
        **kwargs,
    )


def _failure_count(results: Sequence[MutationResult], kind: str) -> int:
    counter: Counter[str] = Counter()
    for result in results:
        counter.update(failure.kind for failure in result.failures)
    return counter[kind]


def _accepted_augmentation_text(augmentation: Mapping[str, Any]) -> str:
    validated = _mapping(augmentation.get("validated_augments"))
    parts: list[str] = []
    for category in sorted(validated):
        for item in _mapping_sequence(validated.get(category)):
            parts.append(str(item.get("text", "")))
    return _normalize_text(" ".join(parts))


def _rejected_reason_text(augmentation: Mapping[str, Any]) -> str:
    rejected = _mapping_sequence(augmentation.get("rejected_augments_summary"))
    return _normalize_text(
        " ".join(str(item.get("rejection_reason", "")) for item in rejected)
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _sequence(value: Any) -> tuple[Any, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(value)


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "MutationCase",
    "MutationFailure",
    "MutationResult",
    "MutationSummary",
    "build_mutation_cases",
    "format_mutation_summary",
    "run_mutation_tests",
]
