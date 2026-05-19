"""Deterministic benchmark snapshot export helpers for Research Council."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from .evaluation import RegressionSummary, build_benchmark_analytics
from .scenario_templates import build_scenario_summary, generate_scenarios


SNAPSHOT_SCHEMA_VERSION = 1
DEFAULT_BENCHMARK_VERSION = "research-council-benchmark-v1"
BENCHMARK_PACK_ID = "research_council_core"
BENCHMARK_PACK_VERSION = "1"


@dataclass(frozen=True)
class BenchmarkVersionInfo:
    """Stable version metadata for a benchmark snapshot."""

    snapshot_schema_version: int
    benchmark_version: str
    benchmark_hash: str
    fixture_count: int


@dataclass(frozen=True)
class BenchmarkRunMetadata:
    """Bounded run metadata without local paths or machine identifiers."""

    augmentation_mode: str
    deterministic: bool = True


@dataclass(frozen=True)
class BenchmarkSnapshot:
    """Serializable benchmark telemetry snapshot."""

    version_info: BenchmarkVersionInfo
    run_metadata: BenchmarkRunMetadata
    total_cases: int
    profiles_covered: tuple[str, ...]
    hard_cases: int
    realistic_cases: int
    synthetic_cases: int
    overlap_cases: int
    total_invariants: int
    failed_invariants: int
    consistency_checks: int
    consistency_failures: int
    augmentation_counts: Mapping[str, int]
    cases_by_profile: Mapping[str, int]
    hard_cases_by_profile: Mapping[str, int]
    evidence_gap_distribution: Mapping[str, int]
    confidence_impact_distribution: Mapping[str, int]
    contamination_failures_by_profile: Mapping[str, int]
    missing_required_terms_by_profile: Mapping[str, int]
    forbidden_contamination_by_profile: Mapping[str, int]
    case_ids: tuple[str, ...]
    selected_profiles_by_case: Mapping[str, str]
    scenario_template_coverage: Mapping[str, Any] = field(default_factory=dict)
    benchmark_pack_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkDiffSummary:
    """Lightweight deterministic comparison between two benchmark snapshots."""

    total_cases_delta: int = 0
    total_invariants_delta: int = 0
    failed_invariants_delta: int = 0
    consistency_failures_delta: int = 0
    augmentation_rejected_delta: int = 0
    profiles_added: tuple[str, ...] = ()
    profiles_removed: tuple[str, ...] = ()
    benchmark_hash_changed: bool = False


def export_benchmark_snapshot(
    summary: RegressionSummary,
    path: str | Path,
    *,
    augmentation_mode: str = "off",
    benchmark_version: str = DEFAULT_BENCHMARK_VERSION,
) -> BenchmarkSnapshot:
    """Write a deterministic benchmark snapshot JSON file and return it."""

    snapshot = build_benchmark_snapshot(
        summary,
        augmentation_mode=augmentation_mode,
        benchmark_version=benchmark_version,
    )
    Path(path).write_text(snapshot_to_json(snapshot), encoding="utf-8")
    return snapshot


def build_benchmark_snapshot(
    summary: RegressionSummary,
    *,
    augmentation_mode: str = "off",
    benchmark_version: str = DEFAULT_BENCHMARK_VERSION,
) -> BenchmarkSnapshot:
    """Build a deterministic snapshot from an evaluated benchmark summary."""

    snapshot_without_hash = _build_benchmark_snapshot_with_hash(
        summary,
        augmentation_mode=augmentation_mode,
        benchmark_version=benchmark_version,
        benchmark_hash="",
    )
    benchmark_hash = _benchmark_hash(
        benchmark_snapshot_to_json_dict(snapshot_without_hash)
    )
    return _build_benchmark_snapshot_with_hash(
        summary,
        augmentation_mode=augmentation_mode,
        benchmark_version=benchmark_version,
        benchmark_hash=benchmark_hash,
    )


def load_benchmark_snapshot(path: str | Path) -> BenchmarkSnapshot:
    """Load a benchmark snapshot JSON file."""

    return benchmark_snapshot_from_json_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def benchmark_snapshot_to_json_dict(snapshot: BenchmarkSnapshot) -> dict[str, Any]:
    """Convert a benchmark snapshot to a deterministic JSON-ready mapping."""

    return {
        "version_info": {
            "snapshot_schema_version": snapshot.version_info.snapshot_schema_version,
            "benchmark_version": snapshot.version_info.benchmark_version,
            "benchmark_hash": snapshot.version_info.benchmark_hash,
            "fixture_count": snapshot.version_info.fixture_count,
        },
        "run_metadata": {
            "augmentation_mode": snapshot.run_metadata.augmentation_mode,
            "deterministic": snapshot.run_metadata.deterministic,
        },
        "total_cases": snapshot.total_cases,
        "profiles_covered": list(snapshot.profiles_covered),
        "hard_cases": snapshot.hard_cases,
        "realistic_cases": snapshot.realistic_cases,
        "synthetic_cases": snapshot.synthetic_cases,
        "overlap_cases": snapshot.overlap_cases,
        "total_invariants": snapshot.total_invariants,
        "failed_invariants": snapshot.failed_invariants,
        "consistency_checks": snapshot.consistency_checks,
        "consistency_failures": snapshot.consistency_failures,
        "augmentation_counts": _sorted_count_mapping(snapshot.augmentation_counts),
        "cases_by_profile": _sorted_count_mapping(snapshot.cases_by_profile),
        "hard_cases_by_profile": _sorted_count_mapping(snapshot.hard_cases_by_profile),
        "evidence_gap_distribution": _sorted_count_mapping(
            snapshot.evidence_gap_distribution
        ),
        "confidence_impact_distribution": _sorted_count_mapping(
            snapshot.confidence_impact_distribution
        ),
        "contamination_failures_by_profile": _sorted_count_mapping(
            snapshot.contamination_failures_by_profile
        ),
        "missing_required_terms_by_profile": _sorted_count_mapping(
            snapshot.missing_required_terms_by_profile
        ),
        "forbidden_contamination_by_profile": _sorted_count_mapping(
            snapshot.forbidden_contamination_by_profile
        ),
        "case_ids": list(snapshot.case_ids),
        "selected_profiles_by_case": {
            key: snapshot.selected_profiles_by_case[key]
            for key in sorted(snapshot.selected_profiles_by_case)
        },
        "scenario_template_coverage": _scenario_template_coverage_mapping(
            snapshot.scenario_template_coverage
        ),
        "benchmark_pack_metadata": _benchmark_pack_metadata_mapping(
            snapshot.benchmark_pack_metadata
        ),
    }


def benchmark_snapshot_from_json_dict(payload: Mapping[str, Any]) -> BenchmarkSnapshot:
    """Convert a JSON mapping into a benchmark snapshot."""

    version_info = _mapping(payload.get("version_info"))
    run_metadata = _mapping(payload.get("run_metadata"))
    return BenchmarkSnapshot(
        version_info=BenchmarkVersionInfo(
            snapshot_schema_version=_int_value(
                version_info.get("snapshot_schema_version")
            ),
            benchmark_version=str(version_info.get("benchmark_version", "")),
            benchmark_hash=str(version_info.get("benchmark_hash", "")),
            fixture_count=_int_value(version_info.get("fixture_count")),
        ),
        run_metadata=BenchmarkRunMetadata(
            augmentation_mode=str(run_metadata.get("augmentation_mode", "off")),
            deterministic=bool(run_metadata.get("deterministic", True)),
        ),
        total_cases=_int_value(payload.get("total_cases")),
        profiles_covered=tuple(str(item) for item in payload.get("profiles_covered", ())),
        hard_cases=_int_value(payload.get("hard_cases")),
        realistic_cases=_int_value(payload.get("realistic_cases")),
        synthetic_cases=_int_value(payload.get("synthetic_cases")),
        overlap_cases=_int_value(payload.get("overlap_cases")),
        total_invariants=_int_value(payload.get("total_invariants")),
        failed_invariants=_int_value(payload.get("failed_invariants")),
        consistency_checks=_int_value(payload.get("consistency_checks")),
        consistency_failures=_int_value(payload.get("consistency_failures")),
        augmentation_counts=_count_mapping(payload.get("augmentation_counts")),
        cases_by_profile=_count_mapping(payload.get("cases_by_profile")),
        hard_cases_by_profile=_count_mapping(payload.get("hard_cases_by_profile")),
        evidence_gap_distribution=_count_mapping(payload.get("evidence_gap_distribution")),
        confidence_impact_distribution=_count_mapping(
            payload.get("confidence_impact_distribution")
        ),
        contamination_failures_by_profile=_count_mapping(
            payload.get("contamination_failures_by_profile")
        ),
        missing_required_terms_by_profile=_count_mapping(
            payload.get("missing_required_terms_by_profile")
        ),
        forbidden_contamination_by_profile=_count_mapping(
            payload.get("forbidden_contamination_by_profile")
        ),
        case_ids=tuple(str(item) for item in payload.get("case_ids", ())),
        selected_profiles_by_case={
            str(key): str(value)
            for key, value in _mapping(payload.get("selected_profiles_by_case")).items()
        },
        scenario_template_coverage=_scenario_template_coverage_mapping(
            payload.get("scenario_template_coverage")
        ),
        benchmark_pack_metadata=_benchmark_pack_metadata_mapping(
            payload.get("benchmark_pack_metadata")
        ),
    )


def snapshot_to_json(snapshot: BenchmarkSnapshot) -> str:
    """Serialize a benchmark snapshot with deterministic key ordering."""

    return json.dumps(
        benchmark_snapshot_to_json_dict(snapshot),
        indent=2,
        sort_keys=True,
    ) + "\n"


def compare_benchmark_snapshots(
    base: BenchmarkSnapshot,
    current: BenchmarkSnapshot,
) -> BenchmarkDiffSummary:
    """Compare two benchmark snapshots with a compact numeric summary."""

    base_profiles = set(base.profiles_covered)
    current_profiles = set(current.profiles_covered)
    return BenchmarkDiffSummary(
        total_cases_delta=current.total_cases - base.total_cases,
        total_invariants_delta=current.total_invariants - base.total_invariants,
        failed_invariants_delta=current.failed_invariants - base.failed_invariants,
        consistency_failures_delta=(
            current.consistency_failures - base.consistency_failures
        ),
        augmentation_rejected_delta=(
            _count_value(current.augmentation_counts, "rejected")
            - _count_value(base.augmentation_counts, "rejected")
        ),
        profiles_added=tuple(sorted(current_profiles - base_profiles)),
        profiles_removed=tuple(sorted(base_profiles - current_profiles)),
        benchmark_hash_changed=(
            current.version_info.benchmark_hash != base.version_info.benchmark_hash
        ),
    )


def _build_benchmark_snapshot_with_hash(
    summary: RegressionSummary,
    *,
    augmentation_mode: str,
    benchmark_version: str,
    benchmark_hash: str,
) -> BenchmarkSnapshot:
    analytics = build_benchmark_analytics(summary)
    return BenchmarkSnapshot(
        version_info=BenchmarkVersionInfo(
            snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
            benchmark_version=benchmark_version,
            benchmark_hash=benchmark_hash,
            fixture_count=analytics.total_cases,
        ),
        run_metadata=BenchmarkRunMetadata(
            augmentation_mode=str(augmentation_mode),
            deterministic=True,
        ),
        total_cases=analytics.total_cases,
        profiles_covered=tuple(analytics.profiles_covered),
        hard_cases=analytics.hard_cases,
        realistic_cases=analytics.realistic_cases,
        synthetic_cases=analytics.synthetic_cases,
        overlap_cases=analytics.overlap_cases,
        total_invariants=analytics.total_invariants,
        failed_invariants=analytics.failed_invariants,
        consistency_checks=analytics.consistency_checks,
        consistency_failures=analytics.consistency_failures,
        augmentation_counts={
            "accepted": analytics.augmentation_accepted,
            "filtered": analytics.augmentation_filtered,
            "rejected": analytics.augmentation_rejected,
        },
        cases_by_profile=_sorted_count_mapping(analytics.cases_by_profile),
        hard_cases_by_profile=_sorted_count_mapping(analytics.hard_cases_by_profile),
        evidence_gap_distribution=_sorted_count_mapping(
            analytics.evidence_gaps_by_profile
        ),
        confidence_impact_distribution=_sorted_count_mapping(
            analytics.confidence_impact_distribution
        ),
        contamination_failures_by_profile=_sorted_count_mapping(
            analytics.contamination_failures_by_profile
        ),
        missing_required_terms_by_profile=_sorted_count_mapping(
            analytics.missing_required_terms_by_profile
        ),
        forbidden_contamination_by_profile=_sorted_count_mapping(
            analytics.forbidden_contamination_by_profile
        ),
        case_ids=tuple(sorted(evaluation.case_id for evaluation in summary.evaluations)),
        selected_profiles_by_case={
            evaluation.case_id: evaluation.profile_id
            for evaluation in sorted(summary.evaluations, key=lambda item: item.case_id)
        },
        scenario_template_coverage=_scenario_template_coverage_metadata(),
        benchmark_pack_metadata=_benchmark_pack_metadata(summary),
    )


def _benchmark_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sorted_count_mapping(value: Mapping[str, int]) -> dict[str, int]:
    return {str(key): int(value[key]) for key in sorted(value)}


def _count_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _int_value(item) for key, item in sorted(value.items())}


def _scenario_template_coverage_metadata() -> dict[str, Any]:
    summary = build_scenario_summary(generate_scenarios())
    from .mutation_tests import build_template_mutation_cases

    return _scenario_template_coverage_mapping(
        {
            "coverage_type": "generated_metadata",
            "total_scenarios": summary.total_scenarios,
            "categories_count": len(summary.categories_covered),
            "profiles_count": len(summary.profiles_covered),
            "template_mutation_subset_count": len(build_template_mutation_cases()),
            "categories_covered": summary.categories_covered,
            "profiles_covered": summary.profiles_covered,
        }
    )


def _scenario_template_coverage_mapping(value: Any) -> dict[str, Any]:
    mapping = _mapping(value)
    return {
        "coverage_type": str(mapping.get("coverage_type", "")),
        "total_scenarios": _int_value(mapping.get("total_scenarios")),
        "categories_count": _int_value(mapping.get("categories_count")),
        "profiles_count": _int_value(mapping.get("profiles_count")),
        "template_mutation_subset_count": _int_value(
            mapping.get("template_mutation_subset_count")
        ),
        "categories_covered": _string_list(mapping.get("categories_covered")),
        "profiles_covered": _string_list(mapping.get("profiles_covered")),
    }


def _benchmark_pack_metadata(summary: RegressionSummary) -> dict[str, Any]:
    scenario_summary = build_scenario_summary(generate_scenarios())
    from .mutation_tests import build_mutation_cases, build_template_mutation_cases

    return _benchmark_pack_metadata_mapping(
        {
            "pack_id": BENCHMARK_PACK_ID,
            "pack_version": BENCHMARK_PACK_VERSION,
            "golden_case_count": len(summary.evaluations),
            "mutation_case_count": len(build_mutation_cases()),
            "template_mutation_subset_count": len(build_template_mutation_cases()),
            "scenario_template_count": scenario_summary.total_scenarios,
            "scenario_template_category_count": len(scenario_summary.categories_covered),
            "profile_count": len(scenario_summary.profiles_covered),
        }
    )


def _benchmark_pack_metadata_mapping(value: Any) -> dict[str, Any]:
    mapping = _mapping(value)
    return {
        "pack_id": str(mapping.get("pack_id", "")),
        "pack_version": str(mapping.get("pack_version", "")),
        "golden_case_count": _int_value(mapping.get("golden_case_count")),
        "mutation_case_count": _int_value(mapping.get("mutation_case_count")),
        "template_mutation_subset_count": _int_value(
            mapping.get("template_mutation_subset_count")
        ),
        "scenario_template_count": _int_value(mapping.get("scenario_template_count")),
        "scenario_template_category_count": _int_value(
            mapping.get("scenario_template_category_count")
        ),
        "profile_count": _int_value(mapping.get("profile_count")),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _count_value(value: Mapping[str, int], key: str) -> int:
    return int(value.get(key, 0))


__all__ = [
    "BenchmarkDiffSummary",
    "BenchmarkRunMetadata",
    "BenchmarkSnapshot",
    "BenchmarkVersionInfo",
    "BENCHMARK_PACK_ID",
    "BENCHMARK_PACK_VERSION",
    "DEFAULT_BENCHMARK_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "benchmark_snapshot_from_json_dict",
    "benchmark_snapshot_to_json_dict",
    "build_benchmark_snapshot",
    "compare_benchmark_snapshots",
    "export_benchmark_snapshot",
    "load_benchmark_snapshot",
    "snapshot_to_json",
]
