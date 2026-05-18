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


__all__ = [
    "BenchmarkHistoryEntry",
    "BenchmarkTrendSummary",
    "HISTORY_SCHEMA_VERSION",
    "append_benchmark_history",
    "benchmark_history_entry_from_json_dict",
    "benchmark_history_entry_from_snapshot",
    "benchmark_history_entry_to_json_dict",
    "compare_latest_to_previous",
    "format_benchmark_trend_summary",
    "history_to_json",
    "load_benchmark_history",
]
