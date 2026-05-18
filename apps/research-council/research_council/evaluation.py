"""Deterministic golden-case evaluation harness for Research Council.

The harness checks stable invariants rather than exact output snapshots. It
does not call LLMs, perform network work, use embeddings, or grade semantics.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from .json_export import result_to_json_dict
from .llm_advisor import LLMAdvisorConfig, LLMAugmentationMode
from .pipeline import run_research_council
from .schemas import ResearchCouncilInput


DEFAULT_GOLDEN_CASES_ROOT = Path(__file__).resolve().parents[1] / "golden_cases"

QUALITY_SIGNAL_NAMES = (
    "profile_adherence",
    "evidence_coverage",
    "risk_specificity",
    "next_step_actionability",
    "caveat_appropriateness",
)


TermGroup = tuple[str, ...]


required_profile_terms: Mapping[str, tuple[TermGroup, ...]] = {
    "ai_saas": (
        ("workflow",),
        ("buyer",),
        ("retention",),
        ("differentiation",),
        ("reliability", "output quality", "output reliability"),
    ),
    "developer_tool": (
        ("developer workflow",),
        ("setup complexity",),
        ("integration burden",),
        ("time-to-value", "time-to-first-value"),
        ("compatibility", "ecosystem compatibility"),
    ),
    "enterprise_b2b": (
        ("procurement", "procurement path"),
        ("stakeholder alignment",),
        ("budget owner",),
        ("security/compliance", "security compliance", "security review"),
        ("rollout", "rollout complexity"),
        ("ROI", "ROI proof"),
    ),
    "marketplace": (
        ("liquidity",),
        ("supply-side", "supply side", "supply-side acquisition"),
        ("demand-side", "demand side", "demand-side acquisition"),
        ("cold-start", "cold start"),
        ("trust/safety", "trust and safety"),
        ("transaction frequency", "repeat transaction"),
    ),
    "creator_tools": (
        ("creator workflow",),
        ("content production", "content production frequency"),
        ("creator retention", "retention trigger"),
        ("audience growth", "fan/community engagement", "fan community"),
        ("monetization", "willingness to pay by creator segment"),
        ("platform dependency", "audience lock-in", "audience lock in"),
    ),
    "medical_device": (
        ("patient safety",),
        ("clinical validation",),
        ("regulatory", "regulatory pathway"),
        ("intended use",),
        ("conservative", "confidence blocker"),
    ),
    "general": (
        ("target user",),
        ("problem severity", "pain intensity"),
        ("alternatives", "competing alternatives", "substitutes"),
        ("adoption evidence", "adoption trigger"),
    ),
}


contamination_terms: Mapping[str, tuple[str, ...]] = {
    "ai_saas": (
        "buyer/workflow integration",
        "generic ai wrapper",
        "ai-wrapper risk",
        "willingness to pay",
    ),
    "developer_tool": (
        "developer workflow",
        "setup complexity",
        "time-to-first-value",
        "developer-tool blocker",
        "DX friction",
    ),
    "enterprise_b2b": (
        "procurement path",
        "security/compliance requirements",
        "stakeholder alignment",
        "enterprise B2B blocker",
    ),
    "marketplace": (
        "liquidity threshold",
        "cold-start",
        "marketplace blocker",
        "supply-side acquisition",
        "demand-side acquisition",
    ),
    "creator_tools": (
        "creator workflow",
        "content production frequency",
        "creator retention",
        "audience growth loop",
        "fan/community engagement",
        "creator-tools blocker",
    ),
    "medical_device": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "regulatory clearance",
    ),
}


forbidden_profile_terms: Mapping[str, tuple[str, ...]] = {
    "ai_saas": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "liquidity threshold",
        "marketplace blocker",
        "procurement path",
        "enterprise B2B blocker",
        "developer-tool blocker",
        "creator-tools blocker",
        "creator retention",
        "fan/community engagement",
    ),
    "developer_tool": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "procurement path",
        "enterprise B2B blocker",
        "liquidity threshold",
        "marketplace blocker",
        "creator-tools blocker",
        "creator retention",
        "content production frequency",
    ),
    "enterprise_b2b": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "liquidity threshold",
        "marketplace blocker",
        "developer-tool blocker",
        "time-to-first-value",
        "DX friction",
        "creator-tools blocker",
        "creator retention",
        "fan/community engagement",
    ),
    "marketplace": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "procurement path",
        "security/compliance requirements",
        "enterprise B2B blocker",
        "developer-tool blocker",
        "setup complexity",
        "time-to-first-value",
        "DX friction",
        "buyer/workflow integration",
        "generic ai wrapper",
        "AI-wrapper risk",
        "creator-tools blocker",
        "creator retention",
        "content production frequency",
    ),
    "creator_tools": (
        "patient safety",
        "clinical validation",
        "regulatory pathway",
        "liquidity threshold",
        "marketplace blocker",
        "supply-side acquisition",
        "demand-side acquisition",
        "procurement path",
        "security/compliance requirements",
        "enterprise B2B blocker",
        "developer-tool blocker",
        "setup complexity",
        "time-to-first-value",
        "DX friction",
        "buyer/workflow integration",
        "generic ai wrapper",
        "AI-wrapper risk",
    ),
    "medical_device": (
        "buyer/workflow integration",
        "generic ai wrapper",
        "AI-wrapper risk",
        "liquidity threshold",
        "marketplace blocker",
        "developer-tool blocker",
        "setup complexity",
        "time-to-first-value",
        "enterprise B2B blocker",
        "procurement path",
        "creator-tools blocker",
        "creator retention",
    ),
    "general": (
        "AI-wrapper risk",
        "marketplace blocker",
        "enterprise B2B blocker",
        "developer-tool blocker",
        "creator-tools blocker",
        "patient safety risk unresolved",
        "clinical validation evidence missing",
        "regulatory pathway unclear",
    ),
}


cross_profile_checks: Mapping[str, Mapping[str, Any]] = {
    profile_id: {
        "required_profile_terms": required_profile_terms[profile_id],
        "forbidden_profile_terms": forbidden_profile_terms[profile_id],
    }
    for profile_id in required_profile_terms
}


@dataclass(frozen=True)
class InvariantResult:
    """One deterministic invariant check result."""

    case_id: str
    invariant: str
    passed: bool
    message: str


@dataclass(frozen=True)
class ConsistencyResult:
    """One deterministic cross-profile consistency check result."""

    profile_id: str
    scope: str
    missing_required_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.missing_required_terms and not self.forbidden_terms

    @property
    def message(self) -> str:
        if self.passed:
            return "profile consistency passed"

        details = ["profile consistency failed"]
        if self.missing_required_terms:
            details.append(
                "missing required profile reasoning: "
                + ", ".join(self.missing_required_terms)
            )
        if self.forbidden_terms:
            details.append(
                "forbidden contamination detected: "
                + ", ".join(self.forbidden_terms)
            )
        details.append("profile drift detected")
        return "; ".join(details)

    def as_invariant_result(self, case_id: str) -> InvariantResult:
        return InvariantResult(
            case_id=case_id,
            invariant="profile consistency",
            passed=self.passed,
            message=self.message,
        )


@dataclass(frozen=True)
class CaseMetrics:
    """Bounded numeric metrics captured from one evaluated case."""

    evidence_entries: int = 0
    evidence_gaps: int = 0
    confidence_impact_counts: Mapping[str, int] = field(default_factory=dict)
    augmentation_accepted: int = 0
    augmentation_filtered: int = 0
    augmentation_rejected: int = 0


@dataclass(frozen=True)
class CaseEvaluation:
    """Evaluation result for one golden case."""

    case_id: str
    path: str
    profile_id: str
    selected_by: str
    invariant_results: tuple[InvariantResult, ...]
    consistency_result: ConsistencyResult | None = None
    tags: tuple[str, ...] = ()
    metrics: CaseMetrics = field(default_factory=CaseMetrics)

    @property
    def passed(self) -> bool:
        consistency_passed = (
            self.consistency_result is None or self.consistency_result.passed
        )
        return all(result.passed for result in self.invariant_results) and consistency_passed

    @property
    def failures(self) -> tuple[InvariantResult, ...]:
        failures = [result for result in self.invariant_results if not result.passed]
        if self.consistency_result is not None and not self.consistency_result.passed:
            failures.append(self.consistency_result.as_invariant_result(self.case_id))
        return tuple(failures)


@dataclass(frozen=True)
class RegressionSummary:
    """Aggregated golden-case regression summary."""

    evaluations: tuple[CaseEvaluation, ...]

    @property
    def passed(self) -> bool:
        return all(evaluation.passed for evaluation in self.evaluations)

    @property
    def case_count(self) -> int:
        return len(self.evaluations)

    @property
    def invariant_count(self) -> int:
        return sum(len(evaluation.invariant_results) for evaluation in self.evaluations)

    @property
    def consistency_check_count(self) -> int:
        return sum(
            1
            for evaluation in self.evaluations
            if evaluation.consistency_result is not None
        )

    @property
    def profile_coverage_count(self) -> int:
        return len({evaluation.profile_id for evaluation in self.evaluations if evaluation.profile_id})

    @property
    def hard_case_count(self) -> int:
        return sum(1 for evaluation in self.evaluations if "hard_case" in evaluation.tags)

    @property
    def augmentation_stress_count(self) -> int:
        return sum(
            1 for evaluation in self.evaluations if "augmentation_stress" in evaluation.tags
        )

    @property
    def check_count(self) -> int:
        return self.invariant_count + self.consistency_check_count

    @property
    def failed_count(self) -> int:
        return sum(len(evaluation.failures) for evaluation in self.evaluations)

    @property
    def failures(self) -> tuple[InvariantResult, ...]:
        return tuple(
            failure
            for evaluation in self.evaluations
            for failure in evaluation.failures
        )


@dataclass(frozen=True)
class AugmentationAnalytics:
    """Aggregate counts for optional augmentation validation paths."""

    accepted: int = 0
    filtered: int = 0
    rejected: int = 0


@dataclass(frozen=True)
class ProfileAnalytics:
    """Benchmark metrics grouped by selected profile."""

    profile_id: str
    cases: int = 0
    hard_cases: int = 0
    invariants: int = 0
    failed_invariants: int = 0
    consistency_checks: int = 0
    consistency_failures: int = 0
    contamination_failures: int = 0
    missing_required_terms: int = 0
    forbidden_contamination: int = 0
    evidence_entries: int = 0
    evidence_gaps: int = 0
    confidence_impact_distribution: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkAnalytics:
    """Deterministic analytics derived from golden-case evaluation results."""

    total_cases: int
    hard_cases: int
    profiles_covered: tuple[str, ...]
    total_invariants: int
    failed_invariants: int
    consistency_checks: int
    consistency_failures: int
    augmentation: AugmentationAnalytics
    profile_analytics: Mapping[str, ProfileAnalytics] = field(default_factory=dict)
    confidence_impact_distribution: Mapping[str, int] = field(default_factory=dict)

    @property
    def profiles_covered_count(self) -> int:
        return len(self.profiles_covered)

    @property
    def augmentation_accepted(self) -> int:
        return self.augmentation.accepted

    @property
    def augmentation_filtered(self) -> int:
        return self.augmentation.filtered

    @property
    def augmentation_rejected(self) -> int:
        return self.augmentation.rejected

    @property
    def cases_by_profile(self) -> Mapping[str, int]:
        return {
            profile_id: analytics.cases
            for profile_id, analytics in self.profile_analytics.items()
        }

    @property
    def hard_cases_by_profile(self) -> Mapping[str, int]:
        return {
            profile_id: analytics.hard_cases
            for profile_id, analytics in self.profile_analytics.items()
        }

    @property
    def evidence_entries_by_profile(self) -> Mapping[str, int]:
        return {
            profile_id: analytics.evidence_entries
            for profile_id, analytics in self.profile_analytics.items()
        }

    @property
    def evidence_gaps_by_profile(self) -> Mapping[str, int]:
        return {
            profile_id: analytics.evidence_gaps
            for profile_id, analytics in self.profile_analytics.items()
        }

    @property
    def contamination_failures_by_profile(self) -> Mapping[str, int]:
        return {
            profile_id: analytics.contamination_failures
            for profile_id, analytics in self.profile_analytics.items()
        }

    @property
    def missing_required_terms_by_profile(self) -> Mapping[str, int]:
        return {
            profile_id: analytics.missing_required_terms
            for profile_id, analytics in self.profile_analytics.items()
        }

    @property
    def forbidden_contamination_by_profile(self) -> Mapping[str, int]:
        return {
            profile_id: analytics.forbidden_contamination
            for profile_id, analytics in self.profile_analytics.items()
        }


@dataclass(frozen=True)
class _GoldenCase:
    case_id: str
    path: str
    input_data: ResearchCouncilInput
    profile: str | None
    expected: Mapping[str, Any]
    tags: tuple[str, ...] = ()


def evaluate_golden_cases(
    root: str | Path | None = None,
    *,
    llm_advisor_config: LLMAdvisorConfig | LLMAugmentationMode | str | None = None,
) -> RegressionSummary:
    """Evaluate all golden-case JSON files under ``root`` deterministically."""

    cases_root = Path(root) if root is not None else DEFAULT_GOLDEN_CASES_ROOT
    evaluations = tuple(
        evaluate_case(path, llm_advisor_config=llm_advisor_config)
        for path in _case_paths(cases_root)
    )
    return RegressionSummary(evaluations=evaluations)


def evaluate_case(
    case: str | Path | Mapping[str, Any],
    *,
    llm_advisor_config: LLMAdvisorConfig | LLMAugmentationMode | str | None = None,
) -> CaseEvaluation:
    """Evaluate one golden case path or already-loaded mapping."""

    golden_case = _load_case(case)
    try:
        result = run_research_council(
            golden_case.input_data,
            profile=golden_case.profile,
            llm_advisor_config=llm_advisor_config,
        )
        payload = result_to_json_dict(result)
    except Exception as exc:  # pragma: no cover - exercised through smoke on failure
        failure = InvariantResult(
            case_id=golden_case.case_id,
            invariant="case execution",
            passed=False,
            message=f"case execution failed: {exc}",
        )
        return CaseEvaluation(
            case_id=golden_case.case_id,
            path=golden_case.path,
            profile_id="",
            selected_by="",
            invariant_results=(failure,),
            consistency_result=None,
            tags=golden_case.tags,
        )

    profile = payload.get("profile", {})
    profile_id = str(profile.get("profile_id", ""))
    selected_by = str(profile.get("selected_by", ""))
    scopes = _build_scopes(payload)
    metrics = _case_metrics(payload)
    checks: list[InvariantResult] = []
    checks.extend(_profile_invariants(golden_case, payload))
    checks.extend(_contains_invariants(golden_case, scopes))
    checks.extend(_not_contains_invariants(golden_case, scopes))
    checks.extend(_label_invariants(golden_case, payload, scopes))
    consistency_result = evaluate_profile_consistency(profile_id, payload, scopes=scopes)
    return CaseEvaluation(
        case_id=golden_case.case_id,
        path=golden_case.path,
        profile_id=profile_id,
        selected_by=selected_by,
        invariant_results=tuple(checks),
        consistency_result=consistency_result,
        tags=golden_case.tags,
        metrics=metrics,
    )


def format_regression_summary(summary: RegressionSummary) -> str:
    """Format a concise regression report without snapshot diffs."""

    if summary.passed:
        consistency_text = (
            f", {summary.consistency_check_count} consistency checks"
            if summary.consistency_check_count
            else ""
        )
        coverage_text = (
            f", {summary.profile_coverage_count} profiles"
            if summary.profile_coverage_count
            else ""
        )
        hard_case_text = (
            f", {summary.hard_case_count} hard cases"
            if summary.hard_case_count
            else ""
        )
        augmentation_text = (
            f", {summary.augmentation_stress_count} augmentation stress cases"
            if summary.augmentation_stress_count
            else ""
        )
        return (
            "Golden cases passed: "
            f"{summary.case_count} cases, {summary.invariant_count} invariants"
            f"{consistency_text}{coverage_text}{hard_case_text}{augmentation_text}."
        )

    lines = [
        "Golden case regression failures: "
        f"{summary.failed_count}/{summary.check_count} checks failed "
        f"across {summary.case_count} cases."
    ]
    for evaluation in summary.evaluations:
        for failure in evaluation.failures:
            lines.append(f"- {evaluation.case_id}: {failure.message}")
    return "\n".join(lines)


def build_benchmark_analytics(summary: RegressionSummary) -> BenchmarkAnalytics:
    """Build deterministic benchmark analytics from evaluated cases."""

    profile_ids = tuple(
        sorted({evaluation.profile_id for evaluation in summary.evaluations if evaluation.profile_id})
    )
    profile_analytics = {
        profile_id: _build_profile_analytics(profile_id, summary.evaluations)
        for profile_id in profile_ids
    }
    confidence_distribution: Counter[str] = Counter()
    for evaluation in summary.evaluations:
        confidence_distribution.update(evaluation.metrics.confidence_impact_counts)

    return BenchmarkAnalytics(
        total_cases=summary.case_count,
        hard_cases=summary.hard_case_count,
        profiles_covered=profile_ids,
        total_invariants=summary.invariant_count,
        failed_invariants=sum(
            1
            for evaluation in summary.evaluations
            for result in evaluation.invariant_results
            if not result.passed
        ),
        consistency_checks=summary.consistency_check_count,
        consistency_failures=sum(
            1
            for evaluation in summary.evaluations
            if evaluation.consistency_result is not None
            and not evaluation.consistency_result.passed
        ),
        augmentation=AugmentationAnalytics(
            accepted=sum(
                evaluation.metrics.augmentation_accepted
                for evaluation in summary.evaluations
            ),
            filtered=sum(
                evaluation.metrics.augmentation_filtered
                for evaluation in summary.evaluations
            ),
            rejected=sum(
                evaluation.metrics.augmentation_rejected
                for evaluation in summary.evaluations
            ),
        ),
        profile_analytics=profile_analytics,
        confidence_impact_distribution=_sorted_count_mapping(confidence_distribution),
    )


def format_benchmark_analytics(analytics: BenchmarkAnalytics) -> str:
    """Format analytics as concise, snapshot-free benchmark telemetry."""

    lines = [
        "Benchmark analytics:",
        (
            "- totals: "
            f"cases={analytics.total_cases}, hard_cases={analytics.hard_cases}, "
            f"profiles_covered={analytics.profiles_covered_count}, "
            f"invariants={analytics.total_invariants}, "
            f"failed_invariants={analytics.failed_invariants}"
        ),
        (
            "- consistency: "
            f"checks={analytics.consistency_checks}, "
            f"failures={analytics.consistency_failures}, "
            "missing_required_terms="
            f"{sum(analytics.missing_required_terms_by_profile.values())}, "
            "forbidden_contamination="
            f"{sum(analytics.forbidden_contamination_by_profile.values())}"
        ),
        (
            "- augmentation: "
            f"accepted={analytics.augmentation_accepted}, "
            f"filtered={analytics.augmentation_filtered}, "
            f"rejected={analytics.augmentation_rejected}"
        ),
        "- cases_by_profile: " + _format_count_mapping(analytics.cases_by_profile),
        "- hard_cases_by_profile: "
        + _format_count_mapping(analytics.hard_cases_by_profile),
        "- evidence_gaps_by_profile: "
        + _format_count_mapping(analytics.evidence_gaps_by_profile),
        "- confidence_impacts: "
        + _format_count_mapping(analytics.confidence_impact_distribution),
    ]
    return "\n".join(lines)


def _build_profile_analytics(
    profile_id: str,
    evaluations: Sequence[CaseEvaluation],
) -> ProfileAnalytics:
    profile_evaluations = tuple(
        evaluation for evaluation in evaluations if evaluation.profile_id == profile_id
    )
    confidence_distribution: Counter[str] = Counter()
    for evaluation in profile_evaluations:
        confidence_distribution.update(evaluation.metrics.confidence_impact_counts)

    return ProfileAnalytics(
        profile_id=profile_id,
        cases=len(profile_evaluations),
        hard_cases=sum(
            1 for evaluation in profile_evaluations if "hard_case" in evaluation.tags
        ),
        invariants=sum(
            len(evaluation.invariant_results) for evaluation in profile_evaluations
        ),
        failed_invariants=sum(
            1
            for evaluation in profile_evaluations
            for result in evaluation.invariant_results
            if not result.passed
        ),
        consistency_checks=sum(
            1
            for evaluation in profile_evaluations
            if evaluation.consistency_result is not None
        ),
        consistency_failures=sum(
            1
            for evaluation in profile_evaluations
            if evaluation.consistency_result is not None
            and not evaluation.consistency_result.passed
        ),
        contamination_failures=sum(
            1
            for evaluation in profile_evaluations
            if evaluation.consistency_result is not None
            and bool(evaluation.consistency_result.forbidden_terms)
        ),
        missing_required_terms=sum(
            len(evaluation.consistency_result.missing_required_terms)
            for evaluation in profile_evaluations
            if evaluation.consistency_result is not None
        ),
        forbidden_contamination=sum(
            len(evaluation.consistency_result.forbidden_terms)
            for evaluation in profile_evaluations
            if evaluation.consistency_result is not None
        ),
        evidence_entries=sum(
            evaluation.metrics.evidence_entries for evaluation in profile_evaluations
        ),
        evidence_gaps=sum(
            evaluation.metrics.evidence_gaps for evaluation in profile_evaluations
        ),
        confidence_impact_distribution=_sorted_count_mapping(confidence_distribution),
    )


def _case_metrics(payload: Mapping[str, Any]) -> CaseMetrics:
    evidence = _mapping_list(payload.get("evidence_ledger"))
    confidence_distribution: Counter[str] = Counter()
    evidence_gaps = 0
    for entry in evidence:
        impact = str(_mapping_get(entry, "confidence_impact")).strip() or "unspecified"
        confidence_distribution[impact] += 1
        if _mapping_get(entry, "evidence_type") == "missing":
            evidence_gaps += 1

    augmentation = payload.get("optional_llm_augments")
    if not isinstance(augmentation, Mapping):
        augmentation = {}

    return CaseMetrics(
        evidence_entries=len(evidence),
        evidence_gaps=evidence_gaps,
        confidence_impact_counts=_sorted_count_mapping(confidence_distribution),
        augmentation_accepted=_int_value(_mapping_get(augmentation, "accepted_count")),
        augmentation_filtered=_int_value(_mapping_get(augmentation, "filtered_count")),
        augmentation_rejected=_int_value(_mapping_get(augmentation, "rejected_count")),
    )


def _sorted_count_mapping(counts: Mapping[str, int]) -> Mapping[str, int]:
    return {
        key: int(counts[key])
        for key in sorted(counts)
        if key and int(counts[key]) != 0
    }


def _format_count_mapping(counts: Mapping[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def evaluate_profile_consistency(
    profile_id: str,
    payload: Mapping[str, Any],
    *,
    scopes: Mapping[str, str] | None = None,
) -> ConsistencyResult | None:
    """Check selected-profile reasoning discipline without semantic grading."""

    canonical_profile_id = _consistency_profile_id(profile_id)
    check = cross_profile_checks.get(canonical_profile_id)
    if check is None:
        return None

    scope_name = "profile_consistency_text"
    scope_text = (
        scopes.get(scope_name, "") if scopes is not None else _profile_consistency_text(payload)
    )
    required_groups = tuple(check.get("required_profile_terms", ()))
    forbidden_terms = _terms(check.get("forbidden_profile_terms"))
    missing_required = tuple(
        _format_term_group(term_group)
        for term_group in required_groups
        if not any(_contains_term(scope_text, term) for term in term_group)
    )
    matched_forbidden = tuple(
        term for term in forbidden_terms if _contains_term(scope_text, term)
    )
    return ConsistencyResult(
        profile_id=canonical_profile_id,
        scope=scope_name,
        missing_required_terms=missing_required,
        forbidden_terms=matched_forbidden,
    )


def _case_paths(root: Path) -> tuple[Path, ...]:
    if not root.exists():
        raise FileNotFoundError(f"golden case root not found: {root}")
    return tuple(sorted(path for path in root.rglob("*.json") if path.is_file()))


def _load_case(case: str | Path | Mapping[str, Any]) -> _GoldenCase:
    if isinstance(case, Mapping):
        return _coerce_case(case, path="")

    path = Path(case)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"golden case must contain an object: {path}")
    return _coerce_case(payload, path=str(path))


def _coerce_case(payload: Mapping[str, Any], *, path: str) -> _GoldenCase:
    input_payload = payload.get("input")
    if not isinstance(input_payload, Mapping):
        raise ValueError(f"golden case input must be an object: {path or '<mapping>'}")

    case_id = str(payload.get("case_id") or Path(path).stem or "unnamed_case").strip()
    if not case_id:
        raise ValueError(f"golden case id must be non-empty: {path or '<mapping>'}")

    expected = payload.get("expected", {})
    if not isinstance(expected, Mapping):
        raise ValueError(f"golden case expected must be an object: {case_id}")

    profile = payload.get("profile")
    return _GoldenCase(
        case_id=case_id,
        path=path,
        input_data=ResearchCouncilInput(
            raw_idea=_required_string(input_payload, "raw_idea", case_id),
            goal=_required_string(input_payload, "goal", case_id),
            context=_optional_string(input_payload.get("context")),
            constraints=_string_tuple(input_payload.get("constraints")),
            provided_evidence=_string_tuple(input_payload.get("provided_evidence")),
        ),
        profile=str(profile).strip() if profile else None,
        expected=expected,
        tags=_case_tags(payload, expected),
    )


def _profile_invariants(
    golden_case: _GoldenCase,
    payload: Mapping[str, Any],
) -> tuple[InvariantResult, ...]:
    expected = golden_case.expected
    profile = payload.get("profile", {})
    actual_profile_id = str(_mapping_get(profile, "profile_id"))
    actual_selected_by = str(_mapping_get(profile, "selected_by"))
    checks: list[InvariantResult] = []

    expected_profile_id = str(expected.get("profile_id", "")).strip()
    if expected_profile_id:
        passed = actual_profile_id == expected_profile_id
        checks.append(
            InvariantResult(
                case_id=golden_case.case_id,
                invariant="profile_id",
                passed=passed,
                message=(
                    "profile invariant passed"
                    if passed
                    else (
                        "profile mismatch: expected "
                        f"{expected_profile_id}, got {actual_profile_id or '<missing>'}"
                    )
                ),
            )
        )

    expected_selected_by = str(expected.get("selected_by", "")).strip()
    if expected_selected_by:
        passed = actual_selected_by == expected_selected_by
        checks.append(
            InvariantResult(
                case_id=golden_case.case_id,
                invariant="selected_by",
                passed=passed,
                message=(
                    "profile selection invariant passed"
                    if passed
                    else (
                        "profile selection mismatch: expected "
                        f"{expected_selected_by}, got {actual_selected_by or '<missing>'}"
                    )
                ),
            )
        )
    return tuple(checks)


def _contains_invariants(
    golden_case: _GoldenCase,
    scopes: Mapping[str, str],
) -> tuple[InvariantResult, ...]:
    checks: list[InvariantResult] = []
    for invariant in _mapping_list(golden_case.expected.get("contains")):
        name = _invariant_name(invariant, "contains")
        scope = str(invariant.get("scope", "result_text"))
        scope_text = scopes.get(scope)
        if scope_text is None:
            checks.append(_failed(golden_case.case_id, name, f"unknown scope: {scope}"))
            continue

        required_terms = _terms(invariant.get("all") or invariant.get("terms"))
        any_terms = _terms(invariant.get("any"))
        if not required_terms and not any_terms:
            checks.append(_failed(golden_case.case_id, name, "empty contains invariant"))
            continue

        missing_required = [
            term for term in required_terms if not _contains_term(scope_text, term)
        ]
        found_any = not any_terms or any(_contains_term(scope_text, term) for term in any_terms)
        if not missing_required and found_any:
            checks.append(_passed(golden_case.case_id, name))
            continue

        details: list[str] = []
        if missing_required:
            details.append("missing required terms: " + ", ".join(missing_required))
        if not found_any:
            details.append("missing one of: " + ", ".join(any_terms))
        checks.append(
            _failed(
                golden_case.case_id,
                name,
                f"missing invariant in {scope}: {'; '.join(details)}",
            )
        )
    return tuple(checks)


def _not_contains_invariants(
    golden_case: _GoldenCase,
    scopes: Mapping[str, str],
) -> tuple[InvariantResult, ...]:
    checks: list[InvariantResult] = []
    for invariant in _mapping_list(golden_case.expected.get("not_contains")):
        name = _invariant_name(invariant, "not_contains")
        scope = str(invariant.get("scope", "result_text"))
        scope_text = scopes.get(scope)
        if scope_text is None:
            checks.append(_failed(golden_case.case_id, name, f"unknown scope: {scope}"))
            continue

        terms = _terms(invariant.get("terms"))
        matched_terms = [term for term in terms if _contains_term(scope_text, term)]
        if not matched_terms:
            checks.append(_passed(golden_case.case_id, name))
            continue

        checks.append(
            _failed(
                golden_case.case_id,
                name,
                f"unexpected wording in {scope}: {', '.join(matched_terms)}",
            )
        )
    return tuple(checks)


def _label_invariants(
    golden_case: _GoldenCase,
    payload: Mapping[str, Any],
    scopes: Mapping[str, str],
) -> tuple[InvariantResult, ...]:
    checks: list[InvariantResult] = []
    for invariant in _mapping_list(golden_case.expected.get("labels")):
        invariant_type = str(invariant.get("type", "")).strip()
        if invariant_type == "unsupported_claim_confidence_not":
            checks.append(_unsupported_claim_confidence_check(golden_case, payload, invariant))
        elif invariant_type == "evidence_confidence_impact":
            checks.append(_evidence_confidence_impact_check(golden_case, payload, invariant))
        elif invariant_type == "reasoning_trace_present":
            checks.append(_reasoning_trace_present_check(golden_case, payload, invariant))
        elif invariant_type == "confidence_rationale_present":
            checks.append(_confidence_rationale_present_check(golden_case, scopes, invariant))
        elif invariant_type == "quality_signals_present":
            checks.append(_quality_signals_present_check(golden_case, payload, invariant))
        elif invariant_type == "recommendation_decision_in":
            checks.append(_recommendation_decision_check(golden_case, payload, invariant))
        elif invariant_type == "llm_augmentation_summary":
            checks.append(_llm_augmentation_summary_check(golden_case, payload, invariant))
        else:
            name = _invariant_name(invariant, "label")
            checks.append(
                _failed(
                    golden_case.case_id,
                    name,
                    f"unknown label invariant type: {invariant_type or '<missing>'}",
                )
            )
    return tuple(checks)


def _unsupported_claim_confidence_check(
    golden_case: _GoldenCase,
    payload: Mapping[str, Any],
    invariant: Mapping[str, Any],
) -> InvariantResult:
    name = _invariant_name(invariant, "unsupported claim confidence")
    forbidden = {
        _normalize_text(term)
        for term in _terms(invariant.get("forbidden") or ("high",))
    }
    offenders: list[str] = []
    for claim in _mapping_list(payload.get("claims")):
        source_label = _normalize_text(_mapping_get(claim, "source_label"))
        confidence = _normalize_text(_mapping_get(claim, "confidence"))
        if source_label != "user provided" and confidence in forbidden:
            offenders.append(f"{_mapping_get(claim, 'id')}={confidence}")

    if not offenders:
        return _passed(golden_case.case_id, name)
    return _failed(
        golden_case.case_id,
        name,
        "unexpected high confidence on unsupported claims: " + ", ".join(offenders),
    )


def _evidence_confidence_impact_check(
    golden_case: _GoldenCase,
    payload: Mapping[str, Any],
    invariant: Mapping[str, Any],
) -> InvariantResult:
    name = _invariant_name(invariant, "evidence confidence impact")
    expected_impact = str(invariant.get("impact", "")).strip()
    expected_category = str(invariant.get("category", "")).strip()
    minimum = int(invariant.get("minimum", 1))
    count = 0
    for entry in _mapping_list(payload.get("evidence_ledger")):
        impact_matches = (
            not expected_impact
            or str(_mapping_get(entry, "confidence_impact")) == expected_impact
        )
        category_matches = (
            not expected_category
            or _entry_gap_category(entry) == expected_category
            or str(_mapping_get(entry, "trace_category")) == expected_category
        )
        if impact_matches and category_matches:
            count += 1

    if count >= minimum:
        return _passed(golden_case.case_id, name)
    category_text = f" for {expected_category}" if expected_category else ""
    impact_text = expected_impact or "any confidence impact"
    return _failed(
        golden_case.case_id,
        name,
        (
            f"missing confidence blocker: expected at least {minimum} "
            f"{impact_text} evidence entries{category_text}, got {count}"
        ),
    )


def _reasoning_trace_present_check(
    golden_case: _GoldenCase,
    payload: Mapping[str, Any],
    invariant: Mapping[str, Any],
) -> InvariantResult:
    name = _invariant_name(invariant, "reasoning trace present")
    entry_scope = str(invariant.get("scope", "all_evidence"))
    entries = _mapping_list(payload.get("evidence_ledger"))
    if entry_scope == "missing_evidence":
        entries = tuple(entry for entry in entries if _mapping_get(entry, "evidence_type") == "missing")

    missing_ids = [
        str(_mapping_get(entry, "id"))
        for entry in entries
        if not _sequence_has_text(_mapping_get(entry, "reasoning_trace"))
    ]
    if entries and not missing_ids:
        return _passed(golden_case.case_id, name)
    if not entries:
        return _failed(golden_case.case_id, name, f"missing invariant: no entries in {entry_scope}")
    return _failed(
        golden_case.case_id,
        name,
        "missing reasoning_trace on evidence entries: " + ", ".join(missing_ids),
    )


def _confidence_rationale_present_check(
    golden_case: _GoldenCase,
    scopes: Mapping[str, str],
    invariant: Mapping[str, Any],
) -> InvariantResult:
    name = _invariant_name(invariant, "confidence rationale present")
    has_trace_rationale = _contains_term(scopes.get("reasoning_trace", ""), "confidence")
    has_markdown_rationale = _contains_term(scopes.get("markdown_report", ""), "confidence rationale")
    if has_trace_rationale and has_markdown_rationale:
        return _passed(golden_case.case_id, name)
    missing = []
    if not has_trace_rationale:
        missing.append("reasoning_trace confidence rationale")
    if not has_markdown_rationale:
        missing.append("markdown confidence rationale")
    return _failed(
        golden_case.case_id,
        name,
        "missing confidence rationale: " + ", ".join(missing),
    )


def _quality_signals_present_check(
    golden_case: _GoldenCase,
    payload: Mapping[str, Any],
    invariant: Mapping[str, Any],
) -> InvariantResult:
    name = _invariant_name(invariant, "quality signals present")
    signal_names = tuple(_terms(invariant.get("signals"))) or QUALITY_SIGNAL_NAMES
    quality_signals = payload.get("quality_signals")
    if not isinstance(quality_signals, Mapping):
        return _failed(golden_case.case_id, name, "missing quality_signals object")

    missing = [signal for signal in signal_names if signal not in quality_signals]
    invalid_statuses = [
        signal
        for signal in signal_names
        if signal in quality_signals
        and _mapping_get(quality_signals[signal], "status") not in {"strong", "partial", "weak"}
    ]
    if not missing and not invalid_statuses:
        return _passed(golden_case.case_id, name)

    details: list[str] = []
    if missing:
        details.append("missing quality_signals: " + ", ".join(missing))
    if invalid_statuses:
        details.append("invalid quality signal status: " + ", ".join(invalid_statuses))
    return _failed(golden_case.case_id, name, "; ".join(details))


def _recommendation_decision_check(
    golden_case: _GoldenCase,
    payload: Mapping[str, Any],
    invariant: Mapping[str, Any],
) -> InvariantResult:
    name = _invariant_name(invariant, "recommendation decision")
    allowed = {_normalize_text(term) for term in _terms(invariant.get("values"))}
    decision = _normalize_text(_mapping_get(payload.get("recommendation", {}), "decision"))
    if decision in allowed:
        return _passed(golden_case.case_id, name)
    return _failed(
        golden_case.case_id,
        name,
        f"missing invariant: recommendation decision {decision or '<missing>'} not in {sorted(allowed)}",
    )


def _llm_augmentation_summary_check(
    golden_case: _GoldenCase,
    payload: Mapping[str, Any],
    invariant: Mapping[str, Any],
) -> InvariantResult:
    name = _invariant_name(invariant, "LLM augmentation summary")
    augmentation = payload.get("optional_llm_augments")
    if not isinstance(augmentation, Mapping):
        return _failed(golden_case.case_id, name, "missing optional_llm_augments object")

    mode = str(_mapping_get(augmentation, "mode"))
    expected_modes = {_normalize_text(mode_name) for mode_name in _terms(invariant.get("modes"))}
    if expected_modes and _normalize_text(mode) not in expected_modes:
        return _passed(golden_case.case_id, name)

    failures: list[str] = []
    for field_name, label in (
        ("accepted_count", "accepted"),
        ("filtered_count", "filtered"),
        ("rejected_count", "rejected"),
    ):
        actual_count = _int_value(_mapping_get(augmentation, field_name))
        minimum = invariant.get(f"min_{label}")
        maximum = invariant.get(f"max_{label}")
        if minimum is not None and actual_count < int(minimum):
            failures.append(f"{label} count {actual_count} below {minimum}")
        if maximum is not None and actual_count > int(maximum):
            failures.append(f"{label} count {actual_count} above {maximum}")

    rejected = _mapping_list(augmentation.get("rejected_augments_summary"))
    reason_text = " ".join(str(_mapping_get(item, "rejection_reason")) for item in rejected)
    missing_reasons = [
        reason
        for reason in _terms(invariant.get("rejection_reasons"))
        if not _contains_term(reason_text, reason)
    ]
    if missing_reasons:
        failures.append("missing rejection reasons: " + ", ".join(missing_reasons))

    if bool(invariant.get("require_no_rejected_text")):
        text_leaks = [
            str(_mapping_get(item, "id") or "<unknown>")
            for item in rejected
            if str(_mapping_get(item, "text")).strip()
        ]
        if text_leaks:
            failures.append("rejected summaries expose text: " + ", ".join(text_leaks))

    if bool(invariant.get("require_allowed_scopes")):
        allowed = set(_terms(augmentation.get("allowed_scopes")))
        validated = augmentation.get("validated_augments")
        categories = set(str(category) for category in validated) if isinstance(validated, Mapping) else set()
        unexpected = sorted(categories - allowed)
        if unexpected:
            failures.append("unexpected augmentation scopes: " + ", ".join(unexpected))

    if not failures:
        return _passed(golden_case.case_id, name)
    return _failed(golden_case.case_id, name, "; ".join(failures))


def _build_scopes(payload: Mapping[str, Any]) -> dict[str, str]:
    evidence = _mapping_list(payload.get("evidence_ledger"))
    generated_evidence = tuple(
        entry for entry in evidence if _mapping_get(entry, "evidence_type") != "provided"
    )
    analysis_claims = tuple(
        claim
        for claim in _mapping_list(payload.get("claims"))
        if _mapping_get(claim, "source_label") != "user_provided"
    )
    reasoning_trace = " ".join(
        _stringify(_mapping_get(entry, "reasoning_trace")) for entry in evidence
    )
    confidence_rationale = " ".join(
        trace
        for trace in _iter_text_values(reasoning_trace)
        if _contains_term(trace, "confidence")
    )
    scopes = {
        "profile": _stringify(payload.get("profile", {})),
        "claims": _stringify(payload.get("claims", ())),
        "analysis_claims": _stringify(analysis_claims),
        "evidence_ledger": _stringify(evidence),
        "reviewer_critiques": _stringify(payload.get("reviewer_critiques", ())),
        "experiments": _stringify(payload.get("experiments", ())),
        "recommendation": _stringify(payload.get("recommendation", {})),
        "warnings": _stringify(payload.get("warnings", ())),
        "reasoning_trace": reasoning_trace,
        "confidence_rationale": confidence_rationale,
        "quality_signals": _stringify(payload.get("quality_signals", {})),
        "optional_llm_augments": _stringify(_accepted_llm_augments(payload)),
        "markdown_report": _stringify(payload.get("markdown_report", {})),
    }
    scopes["profile_consistency_text"] = _profile_consistency_text(
        payload,
        analysis_claims=analysis_claims,
        generated_evidence=generated_evidence,
    )
    scopes["analysis_text"] = " ".join(
        scopes[scope_name]
        for scope_name in (
            "analysis_claims",
            "evidence_ledger",
            "reviewer_critiques",
            "experiments",
            "recommendation",
            "warnings",
            "reasoning_trace",
            "confidence_rationale",
            "quality_signals",
            "optional_llm_augments",
        )
    )
    scopes["result_text"] = " ".join(scopes.values())
    return scopes


def _profile_consistency_text(
    payload: Mapping[str, Any],
    *,
    analysis_claims: Sequence[Mapping[str, Any]] | None = None,
    generated_evidence: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    if analysis_claims is None:
        analysis_claims = tuple(
            claim
            for claim in _mapping_list(payload.get("claims"))
            if _mapping_get(claim, "source_label") != "user_provided"
        )
    if generated_evidence is None:
        generated_evidence = tuple(
            entry
            for entry in _mapping_list(payload.get("evidence_ledger"))
            if _mapping_get(entry, "evidence_type") != "provided"
        )

    generated_reasoning_trace = " ".join(
        _stringify(_mapping_get(entry, "reasoning_trace"))
        for entry in generated_evidence
    )
    return " ".join(
        _stringify(part)
        for part in (
            analysis_claims,
            generated_evidence,
            payload.get("reviewer_critiques", ()),
            payload.get("recommendation", {}),
            payload.get("warnings", ()),
            generated_reasoning_trace,
            payload.get("quality_signals", {}),
            _accepted_llm_augments(payload),
        )
    )


def _accepted_llm_augments(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    augmentation = payload.get("optional_llm_augments")
    if not isinstance(augmentation, Mapping):
        return {}
    validated_augments = augmentation.get("validated_augments")
    if not isinstance(validated_augments, Mapping):
        return {}
    return validated_augments


def _consistency_profile_id(profile_id: str) -> str:
    normalized = _normalize_text(profile_id)
    if normalized == "generic":
        return "general"
    return normalized.replace(" ", "_")


def _format_term_group(term_group: Sequence[str]) -> str:
    terms = tuple(str(term).strip() for term in term_group if str(term).strip())
    return " / ".join(terms)


def _required_string(payload: Mapping[str, Any], field_name: str, case_id: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{case_id}.{field_name} must be a non-empty string")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _case_tags(payload: Mapping[str, Any], expected: Mapping[str, Any]) -> tuple[str, ...]:
    tags = list(_string_tuple(payload.get("tags")))
    for tag in _string_tuple(expected.get("tags")):
        if tag not in tags:
            tags.append(tag)
    return tuple(tags)


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = (value,)
    if not isinstance(value, Sequence):
        raise ValueError("expected a string sequence")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _mapping_list(value: Any) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _mapping_get(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field_name, "")
    return ""


def _invariant_name(invariant: Mapping[str, Any], fallback: str) -> str:
    return str(invariant.get("name") or fallback).strip()


def _terms(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = (value,)
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _contains_term(text: str, term: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_term = _normalize_text(term)
    return bool(normalized_term and normalized_term in normalized_text)


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _sequence_has_text(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if not isinstance(value, Sequence):
        return False
    return any(str(item).strip() for item in value)


def _entry_gap_category(entry: Mapping[str, Any]) -> str:
    notes = str(entry.get("notes", ""))
    match = re.search(r"\bgap_category=([a-z_]+)\b", notes)
    return match.group(1) if match else ""


def _iter_text_values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        values: list[str] = []
        for item in value.values():
            values.extend(_iter_text_values(item))
        return tuple(values)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values = []
        for item in value:
            values.extend(_iter_text_values(item))
        return tuple(values)
    return (str(value),)


def _stringify(value: Any) -> str:
    return " ".join(_iter_text_values(value))


def _passed(case_id: str, invariant: str) -> InvariantResult:
    return InvariantResult(
        case_id=case_id,
        invariant=invariant,
        passed=True,
        message=f"invariant passed: {invariant}",
    )


def _failed(case_id: str, invariant: str, message: str) -> InvariantResult:
    return InvariantResult(
        case_id=case_id,
        invariant=invariant,
        passed=False,
        message=message,
    )


__all__ = [
    "AugmentationAnalytics",
    "BenchmarkAnalytics",
    "CaseEvaluation",
    "CaseMetrics",
    "DEFAULT_GOLDEN_CASES_ROOT",
    "ConsistencyResult",
    "InvariantResult",
    "ProfileAnalytics",
    "RegressionSummary",
    "build_benchmark_analytics",
    "contamination_terms",
    "cross_profile_checks",
    "evaluate_case",
    "evaluate_golden_cases",
    "evaluate_profile_consistency",
    "format_benchmark_analytics",
    "format_regression_summary",
    "forbidden_profile_terms",
    "required_profile_terms",
]
