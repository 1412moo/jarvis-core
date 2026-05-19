"""Deterministic benchmark snapshot history helpers for Research Council."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .benchmark_snapshot import (
    BenchmarkSnapshot,
    benchmark_snapshot_from_json_dict,
    benchmark_snapshot_to_json_dict,
    load_benchmark_snapshot,
    validate_benchmark_pack_metadata,
)


HISTORY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BenchmarkHistoryEntry:
    """One deterministic history entry derived from a benchmark snapshot."""

    snapshot_schema_version: int
    benchmark_version: str
    benchmark_hash: str
    fixture_count: int
    augmentation_mode: str
    total_cases: int
    hard_cases: int
    realistic_cases: int
    synthetic_cases: int
    overlap_cases: int
    total_invariants: int
    failed_invariants: int
    consistency_checks: int
    consistency_failures: int
    profiles_covered: tuple[str, ...]
    augmentation_counts: Mapping[str, int]
    cases_by_profile: Mapping[str, int]
    confidence_impact_distribution: Mapping[str, int]
    evidence_gap_distribution: Mapping[str, int]
    case_ids: tuple[str, ...]
    selected_profiles_by_case: Mapping[str, str]
    scenario_template_coverage: Mapping[str, Any] = field(default_factory=dict)
    benchmark_pack_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkTrendSummary:
    """Latest-vs-previous trend summary for benchmark history."""

    entries: int
    changed: bool = False
    regressions: tuple[str, ...] = ()
    total_cases_delta: int = 0
    hard_cases_delta: int = 0
    realistic_cases_delta: int = 0
    total_invariants_delta: int = 0
    failed_invariants_delta: int = 0
    consistency_failures_delta: int = 0
    augmentation_accepted_delta: int = 0
    augmentation_filtered_delta: int = 0
    augmentation_rejected_delta: int = 0
    profiles_added: tuple[str, ...] = ()
    profiles_removed: tuple[str, ...] = ()
    case_ids_added: tuple[str, ...] = ()
    case_ids_removed: tuple[str, ...] = ()
    selected_profile_changes: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    confidence_impact_delta: Mapping[str, int] = field(default_factory=dict)
    evidence_gap_delta: Mapping[str, int] = field(default_factory=dict)
    scenario_template_coverage_delta: Mapping[str, int] = field(default_factory=dict)
    scenario_template_coverage_changed: bool = False
    benchmark_pack_metadata_delta: Mapping[str, int] = field(default_factory=dict)
    benchmark_pack_metadata_changed: bool = False
    benchmark_hash_changed: bool = False

    @property
    def regression_count(self) -> int:
        return len(self.regressions)


@dataclass(frozen=True)
class ProfileDiffView:
    """Per-profile benchmark deltas for the diff viewer."""

    profile_id: str
    case_count_delta: int = 0
    evidence_gap_delta: int = 0


@dataclass(frozen=True)
class BenchmarkDiffView:
    """Human-readable deterministic diff view between benchmark snapshots."""

    entries: int
    changed: bool = False
    regressions: tuple[str, ...] = ()
    total_cases_delta: int = 0
    hard_cases_delta: int = 0
    realistic_cases_delta: int = 0
    total_invariants_delta: int = 0
    failed_invariants_delta: int = 0
    consistency_failures_delta: int = 0
    augmentation_accepted_delta: int = 0
    augmentation_filtered_delta: int = 0
    augmentation_rejected_delta: int = 0
    profiles_added: tuple[str, ...] = ()
    profiles_removed: tuple[str, ...] = ()
    case_ids_added: tuple[str, ...] = ()
    case_ids_removed: tuple[str, ...] = ()
    selected_profile_changes: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    profile_diffs: tuple[ProfileDiffView, ...] = ()
    confidence_impact_delta: Mapping[str, int] = field(default_factory=dict)
    scenario_template_coverage_delta: Mapping[str, int] = field(default_factory=dict)
    scenario_template_coverage_changed: bool = False
    benchmark_pack_metadata_delta: Mapping[str, int] = field(default_factory=dict)
    benchmark_pack_metadata_changed: bool = False
    benchmark_pack_contract_violations: tuple[str, ...] = ()
    benchmark_hash_changed: bool = False

    @property
    def regression_count(self) -> int:
        return len(self.regressions)


def append_benchmark_history(
    snapshot: BenchmarkSnapshot | str | Path | Mapping[str, Any],
    history_path: str | Path,
) -> tuple[BenchmarkHistoryEntry, ...]:
    """Append one snapshot-derived entry to a deterministic JSON history file."""

    history = load_benchmark_history(history_path)
    entry = benchmark_history_entry_from_snapshot(_coerce_snapshot(snapshot))
    updated = history + (entry,)
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(history_to_json(updated), encoding="utf-8")
    return updated


def build_benchmark_diff_view(
    before: BenchmarkSnapshot | BenchmarkHistoryEntry | str | Path | Mapping[str, Any],
    after: BenchmarkSnapshot | BenchmarkHistoryEntry | str | Path | Mapping[str, Any],
) -> BenchmarkDiffView:
    """Build a deterministic diff view between two benchmark snapshots."""

    before_entry = _coerce_history_entry(before)
    after_entry = _coerce_history_entry(after)
    trend = compare_latest_to_previous((before_entry, after_entry))
    return _diff_view_from_trend(
        trend,
        before_entry=before_entry,
        after_entry=after_entry,
    )


def build_benchmark_diff_view_from_history(
    history: Sequence[BenchmarkHistoryEntry],
) -> BenchmarkDiffView:
    """Build a deterministic diff view from the latest two history entries."""

    entries = tuple(history)
    if len(entries) < 2:
        return BenchmarkDiffView(entries=len(entries))
    return build_benchmark_diff_view(entries[-2], entries[-1])


def load_benchmark_history(path: str | Path) -> tuple[BenchmarkHistoryEntry, ...]:
    """Load benchmark history entries from a JSON file."""

    history_path = Path(path)
    if not history_path.exists():
        return ()
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return ()
    entries = payload.get("entries", ())
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes, bytearray)):
        return ()
    return tuple(
        benchmark_history_entry_from_json_dict(entry)
        for entry in entries
        if isinstance(entry, Mapping)
    )


def compare_latest_to_previous(
    history: Sequence[BenchmarkHistoryEntry],
) -> BenchmarkTrendSummary:
    """Compare the latest history entry to the previous entry."""

    entries = tuple(history)
    if len(entries) < 2:
        return BenchmarkTrendSummary(entries=len(entries))

    previous = entries[-2]
    latest = entries[-1]
    profiles_added, profiles_removed = _set_deltas(
        previous.profiles_covered,
        latest.profiles_covered,
    )
    case_ids_added, case_ids_removed = _set_deltas(previous.case_ids, latest.case_ids)
    selected_profile_changes = _selected_profile_changes(
        previous.selected_profiles_by_case,
        latest.selected_profiles_by_case,
    )
    confidence_impact_delta = _mapping_delta(
        previous.confidence_impact_distribution,
        latest.confidence_impact_distribution,
    )
    evidence_gap_delta = _mapping_delta(
        previous.evidence_gap_distribution,
        latest.evidence_gap_distribution,
    )
    scenario_template_coverage_delta = _scenario_template_coverage_delta(
        previous.scenario_template_coverage,
        latest.scenario_template_coverage,
    )
    scenario_template_coverage_changed = (
        _scenario_template_coverage_mapping(previous.scenario_template_coverage)
        != _scenario_template_coverage_mapping(latest.scenario_template_coverage)
    )
    benchmark_pack_metadata_delta = _benchmark_pack_metadata_delta(
        previous.benchmark_pack_metadata,
        latest.benchmark_pack_metadata,
    )
    benchmark_pack_metadata_changed = (
        _benchmark_pack_metadata_mapping(previous.benchmark_pack_metadata)
        != _benchmark_pack_metadata_mapping(latest.benchmark_pack_metadata)
    )

    trend = BenchmarkTrendSummary(
        entries=len(entries),
        changed=previous.benchmark_hash != latest.benchmark_hash,
        total_cases_delta=latest.total_cases - previous.total_cases,
        hard_cases_delta=latest.hard_cases - previous.hard_cases,
        realistic_cases_delta=latest.realistic_cases - previous.realistic_cases,
        total_invariants_delta=latest.total_invariants - previous.total_invariants,
        failed_invariants_delta=latest.failed_invariants - previous.failed_invariants,
        consistency_failures_delta=(
            latest.consistency_failures - previous.consistency_failures
        ),
        augmentation_accepted_delta=(
            _count_value(latest.augmentation_counts, "accepted")
            - _count_value(previous.augmentation_counts, "accepted")
        ),
        augmentation_filtered_delta=(
            _count_value(latest.augmentation_counts, "filtered")
            - _count_value(previous.augmentation_counts, "filtered")
        ),
        augmentation_rejected_delta=(
            _count_value(latest.augmentation_counts, "rejected")
            - _count_value(previous.augmentation_counts, "rejected")
        ),
        profiles_added=profiles_added,
        profiles_removed=profiles_removed,
        case_ids_added=case_ids_added,
        case_ids_removed=case_ids_removed,
        selected_profile_changes=selected_profile_changes,
        confidence_impact_delta=confidence_impact_delta,
        evidence_gap_delta=evidence_gap_delta,
        scenario_template_coverage_delta=scenario_template_coverage_delta,
        scenario_template_coverage_changed=scenario_template_coverage_changed,
        benchmark_pack_metadata_delta=benchmark_pack_metadata_delta,
        benchmark_pack_metadata_changed=benchmark_pack_metadata_changed,
        benchmark_hash_changed=(previous.benchmark_hash != latest.benchmark_hash),
    )
    return BenchmarkTrendSummary(
        **{
            **trend.__dict__,
            "regressions": _regression_signals(trend),
        }
    )


def format_benchmark_trend_summary(summary: BenchmarkTrendSummary) -> str:
    """Format benchmark history trend telemetry concisely."""

    return (
        "Benchmark history updated: "
        f"entries={summary.entries}, "
        f"changed={str(summary.changed).lower()}, "
        f"regressions={summary.regression_count}. "
        "Deltas: "
        f"cases={summary.total_cases_delta}, "
        f"hard_cases={summary.hard_cases_delta}, "
        f"realistic_cases={summary.realistic_cases_delta}, "
        f"invariants={summary.total_invariants_delta}, "
        f"failed_invariants={summary.failed_invariants_delta}, "
        f"consistency_failures={summary.consistency_failures_delta}, "
        "augmentation="
        f"{summary.augmentation_accepted_delta}/"
        f"{summary.augmentation_filtered_delta}/"
        f"{summary.augmentation_rejected_delta}."
    )


def format_benchmark_diff_view(view: BenchmarkDiffView) -> str:
    """Format a concise, deterministic benchmark diff report."""

    drift_categories = categorize_benchmark_drift(view)
    lines = [
        (
            "Benchmark diff: "
            f"changed={str(view.changed).lower()}, "
            f"regressions={view.regression_count}"
        ),
        f"- cases: {_signed(view.total_cases_delta)}",
        f"- hard_cases: {_signed(view.hard_cases_delta)}",
        f"- realistic_cases: {_signed(view.realistic_cases_delta)}",
        f"- invariants: {_signed(view.total_invariants_delta)}",
        f"- failed_invariants: {_signed(view.failed_invariants_delta)}",
        f"- consistency_failures: {_signed(view.consistency_failures_delta)}",
        (
            "- augmentation: "
            f"accepted={_signed(view.augmentation_accepted_delta)}, "
            f"filtered={_signed(view.augmentation_filtered_delta)}, "
            f"rejected={_signed(view.augmentation_rejected_delta)}"
        ),
        (
            "- scenario_templates: "
            f"changed={str(view.scenario_template_coverage_changed).lower()}, "
            f"scenarios={_signed(_count_value(view.scenario_template_coverage_delta, 'scenarios'))}, "
            f"categories={_signed(_count_value(view.scenario_template_coverage_delta, 'categories'))}, "
            f"profiles={_signed(_count_value(view.scenario_template_coverage_delta, 'profiles'))}, "
            f"subset={_signed(_count_value(view.scenario_template_coverage_delta, 'subset'))}"
        ),
        (
            "- benchmark_pack: "
            f"changed={str(view.benchmark_pack_metadata_changed).lower()}, "
            f"golden={_signed(_count_value(view.benchmark_pack_metadata_delta, 'golden'))}, "
            f"mutation={_signed(_count_value(view.benchmark_pack_metadata_delta, 'mutation'))}, "
            f"templates={_signed(_count_value(view.benchmark_pack_metadata_delta, 'templates'))}, "
            f"profiles={_signed(_count_value(view.benchmark_pack_metadata_delta, 'profiles'))}"
        ),
        "- drift_categories: "
        + (",".join(drift_categories) if drift_categories else "none"),
        "- profiles: " + _format_added_removed(view.profiles_added, view.profiles_removed),
        "- case_ids: " + _format_added_removed(view.case_ids_added, view.case_ids_removed),
        f"- benchmark_hash_changed: {str(view.benchmark_hash_changed).lower()}",
    ]
    if view.profile_diffs:
        lines.append(
            "- profile_deltas: "
            + ", ".join(
                (
                    f"{profile.profile_id}(cases={_signed(profile.case_count_delta)}, "
                    f"evidence_gaps={_signed(profile.evidence_gap_delta)})"
                )
                for profile in view.profile_diffs
            )
        )
    if view.confidence_impact_delta:
        lines.append(
            "- confidence_impacts: " + _format_count_delta(view.confidence_impact_delta)
        )
    if view.selected_profile_changes:
        lines.append(
            "- selected_profile_changes: "
            + ", ".join(
                f"{case_id}:{before}->{after}"
                for case_id, (before, after) in sorted(
                    view.selected_profile_changes.items()
                )
            )
        )
    if view.regressions:
        lines.append("- regression_signals: " + ", ".join(view.regressions))
    return "\n".join(lines)


def format_benchmark_governance_summary(view: BenchmarkDiffView) -> str:
    """Format a compact CI-oriented benchmark governance summary."""

    categories = categorize_benchmark_drift(view)
    category_text = ",".join(categories) if categories else "none"
    status = "warning" if categories else "stable"
    severity = classify_benchmark_governance_severity(view)
    regressions = sum(
        1 for signal in view.regressions if signal != "benchmark_hash changed"
    )
    recommended_action = _recommended_benchmark_governance_action(severity)
    fields = (
        ("status", status),
        ("categories", category_text),
        ("regressions", str(regressions)),
        ("severity", severity),
        ("recommended_action", recommended_action),
        ("profile_change_rollup", _format_profile_change_rollup(view)),
        ("policy_reason", _governance_policy_reason(severity)),
        (
            "escalation_reason",
            _governance_escalation_reason(
                categories,
                regressions=regressions,
                benchmark_hash_changed=view.benchmark_hash_changed,
            ),
        ),
        ("compatibility_tier", _governance_compatibility_tier(categories)),
    )
    return "Benchmark governance: " + _format_key_value_fields(fields)


def classify_benchmark_governance_severity(view: BenchmarkDiffView) -> str:
    """Classify benchmark governance severity for CI-friendly output."""

    categories = categorize_benchmark_drift(view)
    if "regression" in categories or "contract_mismatch" in categories:
        return "critical"
    if "composition_change" in categories:
        return "warning"
    if view.benchmark_hash_changed:
        return "info"
    return "stable"


def _recommended_benchmark_governance_action(severity: str) -> str:
    return {
        "stable": "continue",
        "info": "review_metadata_change",
        "warning": "review_composition_change",
        "critical": "block_and_review",
    }.get(severity, "review_metadata_change")


def _governance_policy_reason(severity: str) -> str:
    return {
        "stable": "stable_no_drift",
        "info": "info_hash_change",
        "warning": "warning_composition_change",
        "critical": "critical_regression_or_contract_mismatch",
    }.get(severity, "unknown_policy_reason")


def _governance_escalation_reason(
    categories: Sequence[str],
    *,
    regressions: int,
    benchmark_hash_changed: bool,
) -> str:
    category_set = set(categories)
    if "regression" in category_set and "contract_mismatch" in category_set:
        return "regression_and_contract_mismatch"
    if "contract_mismatch" in category_set:
        return "contract_mismatch"
    if "regression" in category_set or regressions > 0:
        return "regression_count_gt_0"
    if "composition_change" in category_set:
        return "composition_change"
    if benchmark_hash_changed:
        return "hash_change_only"
    return "no_escalation"


def _governance_compatibility_tier(categories: Sequence[str]) -> str:
    category_set = set(categories)
    if "regression" in category_set or "contract_mismatch" in category_set:
        return "breaking_contract_change"
    if "composition_change" in category_set:
        return "additive_contract_change"
    return "compatible"


def _format_key_value_fields(fields: Sequence[tuple[str, str]]) -> str:
    return " ".join(f"{key}={value}" for key, value in fields)


def _format_profile_change_rollup(view: BenchmarkDiffView) -> str:
    return (
        f"added:{len(view.profiles_added)},"
        f"removed:{len(view.profiles_removed)},"
        f"deltas:{len(view.profile_diffs)},"
        f"selection_changes:{len(view.selected_profile_changes)}"
    )


def classify_benchmark_governance_gate(view: BenchmarkDiffView) -> str:
    """Classify opt-in benchmark governance CI gate result."""

    if classify_benchmark_governance_severity(view) == "critical":
        return "fail"
    return "pass"


def categorize_benchmark_drift(view: BenchmarkDiffView) -> tuple[str, ...]:
    """Categorize benchmark drift with conservative governance labels."""

    categories: list[str] = []
    if (
        view.failed_invariants_delta > 0
        or view.consistency_failures_delta > 0
        or any(signal != "benchmark_hash changed" for signal in view.regressions)
    ):
        categories.append("regression")
    if (
        view.profiles_added
        or view.profiles_removed
        or view.case_ids_added
        or view.case_ids_removed
        or view.scenario_template_coverage_changed
        or view.benchmark_pack_metadata_changed
    ):
        categories.append("composition_change")
    if view.benchmark_pack_contract_violations:
        categories.append("contract_mismatch")
    return tuple(categories)


def benchmark_history_entry_from_snapshot(
    snapshot: BenchmarkSnapshot,
) -> BenchmarkHistoryEntry:
    """Build a bounded history entry from one snapshot."""

    payload = benchmark_snapshot_to_json_dict(snapshot)
    version_info = _mapping(payload.get("version_info"))
    run_metadata = _mapping(payload.get("run_metadata"))
    return BenchmarkHistoryEntry(
        snapshot_schema_version=_int_value(version_info.get("snapshot_schema_version")),
        benchmark_version=str(version_info.get("benchmark_version", "")),
        benchmark_hash=str(version_info.get("benchmark_hash", "")),
        fixture_count=_int_value(version_info.get("fixture_count")),
        augmentation_mode=str(run_metadata.get("augmentation_mode", "off")),
        total_cases=_int_value(payload.get("total_cases")),
        hard_cases=_int_value(payload.get("hard_cases")),
        realistic_cases=_int_value(payload.get("realistic_cases")),
        synthetic_cases=_int_value(payload.get("synthetic_cases")),
        overlap_cases=_int_value(payload.get("overlap_cases")),
        total_invariants=_int_value(payload.get("total_invariants")),
        failed_invariants=_int_value(payload.get("failed_invariants")),
        consistency_checks=_int_value(payload.get("consistency_checks")),
        consistency_failures=_int_value(payload.get("consistency_failures")),
        profiles_covered=tuple(str(item) for item in payload.get("profiles_covered", ())),
        augmentation_counts=_count_mapping(payload.get("augmentation_counts")),
        cases_by_profile=_count_mapping(payload.get("cases_by_profile")),
        confidence_impact_distribution=_count_mapping(
            payload.get("confidence_impact_distribution")
        ),
        evidence_gap_distribution=_count_mapping(payload.get("evidence_gap_distribution")),
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


def benchmark_history_entry_to_json_dict(
    entry: BenchmarkHistoryEntry,
) -> dict[str, Any]:
    """Convert one history entry to a stable JSON mapping."""

    return {
        "snapshot_schema_version": entry.snapshot_schema_version,
        "benchmark_version": entry.benchmark_version,
        "benchmark_hash": entry.benchmark_hash,
        "fixture_count": entry.fixture_count,
        "augmentation_mode": entry.augmentation_mode,
        "total_cases": entry.total_cases,
        "hard_cases": entry.hard_cases,
        "realistic_cases": entry.realistic_cases,
        "synthetic_cases": entry.synthetic_cases,
        "overlap_cases": entry.overlap_cases,
        "total_invariants": entry.total_invariants,
        "failed_invariants": entry.failed_invariants,
        "consistency_checks": entry.consistency_checks,
        "consistency_failures": entry.consistency_failures,
        "profiles_covered": list(entry.profiles_covered),
        "augmentation_counts": _sorted_count_mapping(entry.augmentation_counts),
        "cases_by_profile": _sorted_count_mapping(entry.cases_by_profile),
        "confidence_impact_distribution": _sorted_count_mapping(
            entry.confidence_impact_distribution
        ),
        "evidence_gap_distribution": _sorted_count_mapping(
            entry.evidence_gap_distribution
        ),
        "case_ids": list(entry.case_ids),
        "selected_profiles_by_case": {
            key: entry.selected_profiles_by_case[key]
            for key in sorted(entry.selected_profiles_by_case)
        },
        "scenario_template_coverage": _scenario_template_coverage_mapping(
            entry.scenario_template_coverage
        ),
        "benchmark_pack_metadata": _benchmark_pack_metadata_mapping(
            entry.benchmark_pack_metadata
        ),
    }


def benchmark_history_entry_from_json_dict(
    payload: Mapping[str, Any],
) -> BenchmarkHistoryEntry:
    """Convert a JSON mapping into one history entry."""

    return BenchmarkHistoryEntry(
        snapshot_schema_version=_int_value(payload.get("snapshot_schema_version")),
        benchmark_version=str(payload.get("benchmark_version", "")),
        benchmark_hash=str(payload.get("benchmark_hash", "")),
        fixture_count=_int_value(payload.get("fixture_count")),
        augmentation_mode=str(payload.get("augmentation_mode", "off")),
        total_cases=_int_value(payload.get("total_cases")),
        hard_cases=_int_value(payload.get("hard_cases")),
        realistic_cases=_int_value(payload.get("realistic_cases")),
        synthetic_cases=_int_value(payload.get("synthetic_cases")),
        overlap_cases=_int_value(payload.get("overlap_cases")),
        total_invariants=_int_value(payload.get("total_invariants")),
        failed_invariants=_int_value(payload.get("failed_invariants")),
        consistency_checks=_int_value(payload.get("consistency_checks")),
        consistency_failures=_int_value(payload.get("consistency_failures")),
        profiles_covered=tuple(str(item) for item in payload.get("profiles_covered", ())),
        augmentation_counts=_count_mapping(payload.get("augmentation_counts")),
        cases_by_profile=_count_mapping(payload.get("cases_by_profile")),
        confidence_impact_distribution=_count_mapping(
            payload.get("confidence_impact_distribution")
        ),
        evidence_gap_distribution=_count_mapping(payload.get("evidence_gap_distribution")),
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


def history_to_json(history: Sequence[BenchmarkHistoryEntry]) -> str:
    """Serialize benchmark history with deterministic key ordering."""

    return json.dumps(
        {
            "history_schema_version": HISTORY_SCHEMA_VERSION,
            "entries": [
                benchmark_history_entry_to_json_dict(entry) for entry in history
            ],
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def _diff_view_from_trend(
    trend: BenchmarkTrendSummary,
    *,
    before_entry: BenchmarkHistoryEntry,
    after_entry: BenchmarkHistoryEntry,
) -> BenchmarkDiffView:
    return BenchmarkDiffView(
        entries=trend.entries,
        changed=trend.changed,
        regressions=trend.regressions,
        total_cases_delta=trend.total_cases_delta,
        hard_cases_delta=trend.hard_cases_delta,
        realistic_cases_delta=trend.realistic_cases_delta,
        total_invariants_delta=trend.total_invariants_delta,
        failed_invariants_delta=trend.failed_invariants_delta,
        consistency_failures_delta=trend.consistency_failures_delta,
        augmentation_accepted_delta=trend.augmentation_accepted_delta,
        augmentation_filtered_delta=trend.augmentation_filtered_delta,
        augmentation_rejected_delta=trend.augmentation_rejected_delta,
        profiles_added=trend.profiles_added,
        profiles_removed=trend.profiles_removed,
        case_ids_added=trend.case_ids_added,
        case_ids_removed=trend.case_ids_removed,
        selected_profile_changes=trend.selected_profile_changes,
        profile_diffs=_profile_diff_views(before_entry, after_entry),
        confidence_impact_delta=trend.confidence_impact_delta,
        scenario_template_coverage_delta=trend.scenario_template_coverage_delta,
        scenario_template_coverage_changed=trend.scenario_template_coverage_changed,
        benchmark_pack_metadata_delta=trend.benchmark_pack_metadata_delta,
        benchmark_pack_metadata_changed=trend.benchmark_pack_metadata_changed,
        benchmark_pack_contract_violations=validate_benchmark_pack_metadata(
            after_entry.benchmark_pack_metadata
        ),
        benchmark_hash_changed=trend.benchmark_hash_changed,
    )


def _profile_diff_views(
    before_entry: BenchmarkHistoryEntry,
    after_entry: BenchmarkHistoryEntry,
) -> tuple[ProfileDiffView, ...]:
    case_delta = _mapping_delta(before_entry.cases_by_profile, after_entry.cases_by_profile)
    evidence_delta = _mapping_delta(
        before_entry.evidence_gap_distribution,
        after_entry.evidence_gap_distribution,
    )
    profile_ids = sorted(set(case_delta) | set(evidence_delta))
    return tuple(
        ProfileDiffView(
            profile_id=profile_id,
            case_count_delta=case_delta.get(profile_id, 0),
            evidence_gap_delta=evidence_delta.get(profile_id, 0),
        )
        for profile_id in profile_ids
    )


def _coerce_history_entry(
    value: BenchmarkSnapshot | BenchmarkHistoryEntry | str | Path | Mapping[str, Any],
) -> BenchmarkHistoryEntry:
    if isinstance(value, BenchmarkHistoryEntry):
        return value
    return benchmark_history_entry_from_snapshot(_coerce_snapshot(value))


def _coerce_snapshot(snapshot: BenchmarkSnapshot | str | Path | Mapping[str, Any]) -> BenchmarkSnapshot:
    if isinstance(snapshot, BenchmarkSnapshot):
        return snapshot
    if isinstance(snapshot, (str, Path)):
        return load_benchmark_snapshot(snapshot)
    return benchmark_snapshot_from_json_dict(snapshot)


def _regression_signals(summary: BenchmarkTrendSummary) -> tuple[str, ...]:
    signals: list[str] = []
    if summary.failed_invariants_delta > 0:
        signals.append("failed_invariants increased")
    if summary.consistency_failures_delta > 0:
        signals.append("consistency_failures increased")
    if summary.profiles_removed:
        signals.append("profiles_covered decreased")
    if summary.hard_cases_delta < 0:
        signals.append("hard_cases decreased")
    if summary.realistic_cases_delta < 0:
        signals.append("realistic_cases decreased")
    if summary.benchmark_hash_changed:
        signals.append("benchmark_hash changed")
    return tuple(signals)


def _selected_profile_changes(
    previous: Mapping[str, str],
    latest: Mapping[str, str],
) -> dict[str, tuple[str, str]]:
    changed: dict[str, tuple[str, str]] = {}
    for case_id in sorted(set(previous) & set(latest)):
        if previous[case_id] != latest[case_id]:
            changed[case_id] = (previous[case_id], latest[case_id])
    return changed


def _set_deltas(
    previous: Sequence[str],
    latest: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    previous_set = set(previous)
    latest_set = set(latest)
    return (
        tuple(sorted(latest_set - previous_set)),
        tuple(sorted(previous_set - latest_set)),
    )


def _mapping_delta(
    previous: Mapping[str, int],
    latest: Mapping[str, int],
) -> dict[str, int]:
    keys = sorted(set(previous) | set(latest))
    return {
        key: _count_value(latest, key) - _count_value(previous, key)
        for key in keys
        if _count_value(latest, key) - _count_value(previous, key)
    }


def _scenario_template_coverage_delta(
    previous: Mapping[str, Any],
    latest: Mapping[str, Any],
) -> dict[str, int]:
    previous_coverage = _scenario_template_coverage_mapping(previous)
    latest_coverage = _scenario_template_coverage_mapping(latest)
    fields = {
        "scenarios": "total_scenarios",
        "categories": "categories_count",
        "profiles": "profiles_count",
        "subset": "template_mutation_subset_count",
    }
    return {
        label: _int_value(latest_coverage.get(field)) - _int_value(previous_coverage.get(field))
        for label, field in fields.items()
        if _int_value(latest_coverage.get(field)) - _int_value(previous_coverage.get(field))
    }


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


def _benchmark_pack_metadata_delta(
    previous: Mapping[str, Any],
    latest: Mapping[str, Any],
) -> dict[str, int]:
    previous_metadata = _benchmark_pack_metadata_mapping(previous)
    latest_metadata = _benchmark_pack_metadata_mapping(latest)
    fields = {
        "golden": "golden_case_count",
        "mutation": "mutation_case_count",
        "templates": "scenario_template_count",
        "profiles": "profile_count",
    }
    return {
        label: _int_value(latest_metadata.get(field)) - _int_value(previous_metadata.get(field))
        for label, field in fields.items()
        if _int_value(latest_metadata.get(field)) - _int_value(previous_metadata.get(field))
    }


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


def _sorted_count_mapping(value: Mapping[str, int]) -> dict[str, int]:
    return {str(key): int(value[key]) for key in sorted(value)}


def _count_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): _int_value(item) for key, item in sorted(value.items())}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _count_value(value: Mapping[str, int], key: str) -> int:
    return int(value.get(key, 0))


def _signed(value: int) -> str:
    return f"{value:+d}"


def _format_added_removed(added: Sequence[str], removed: Sequence[str]) -> str:
    parts: list[str] = []
    if added:
        parts.append("added=" + ",".join(added))
    if removed:
        parts.append("removed=" + ",".join(removed))
    return "; ".join(parts) if parts else "no change"


def _format_count_delta(value: Mapping[str, int]) -> str:
    return ", ".join(f"{key}={_signed(value[key])}" for key in sorted(value))


__all__ = [
    "BenchmarkDiffView",
    "BenchmarkHistoryEntry",
    "ProfileDiffView",
    "BenchmarkTrendSummary",
    "HISTORY_SCHEMA_VERSION",
    "append_benchmark_history",
    "benchmark_history_entry_from_json_dict",
    "benchmark_history_entry_from_snapshot",
    "benchmark_history_entry_to_json_dict",
    "build_benchmark_diff_view",
    "build_benchmark_diff_view_from_history",
    "categorize_benchmark_drift",
    "classify_benchmark_governance_gate",
    "classify_benchmark_governance_severity",
    "compare_latest_to_previous",
    "format_benchmark_diff_view",
    "format_benchmark_governance_summary",
    "format_benchmark_trend_summary",
    "history_to_json",
    "load_benchmark_history",
]
