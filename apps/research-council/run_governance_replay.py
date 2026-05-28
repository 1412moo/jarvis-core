"""Replay deterministic Research Council benchmark governance from metadata."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys

from research_council.benchmark_history import (
    BenchmarkHistoryEntry,
    benchmark_history_entry_from_json_dict,
    build_benchmark_diff_view,
    build_benchmark_diff_view_from_history,
    classify_benchmark_governance_gate,
    format_benchmark_governance_summary,
)
from research_council.benchmark_snapshot import (
    BenchmarkSnapshot,
    benchmark_snapshot_from_json_dict,
)


class ReplayInputError(ValueError):
    """Raised when replay metadata cannot form a deterministic comparison."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ReplayArgumentParser(argparse.ArgumentParser):
    """Argparse variant that keeps usage failures bounded and path-free."""

    def error(self, message: str) -> None:
        self.exit(2, "Governance replay invalid: usage_error\n")


def main(argv: list[str] | None = None) -> int:
    parser = ReplayArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--history",
        type=Path,
        default=None,
        help="Benchmark history JSON file; compares latest to previous.",
    )
    source.add_argument(
        "--before",
        type=Path,
        default=None,
        help="Earlier benchmark snapshot JSON file.",
    )
    parser.add_argument(
        "--after",
        type=Path,
        default=None,
        help="Later benchmark snapshot JSON file. Required with --before.",
    )
    parser.add_argument(
        "--expected-summary",
        default=None,
        help="Expected first-line governance summary.",
    )
    parser.add_argument(
        "--expected-current-hash",
        default=None,
        help="Expected current benchmark hash.",
    )
    parser.add_argument(
        "--expected-baseline-hash",
        default=None,
        help="Expected baseline benchmark hash.",
    )
    args = parser.parse_args(argv)

    if args.before is not None and args.after is None:
        parser.error("--after is required with --before")
    if args.before is None and args.after is not None:
        parser.error("--before is required with --after")
    if args.history is not None and args.after is not None:
        parser.error("--after cannot be used with --history")

    try:
        replay = _build_replay(args)
    except ReplayInputError as exc:
        print(f"Governance replay invalid: {exc.reason}", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print("Governance replay invalid: missing_file", file=sys.stderr)
        return 2
    except json.JSONDecodeError:
        print("Governance replay invalid: malformed_metadata", file=sys.stderr)
        return 2
    except OSError:
        print("Governance replay invalid: invalid_input", file=sys.stderr)
        return 2

    mismatch = _first_mismatch(
        expected_summary=args.expected_summary,
        expected_baseline_hash=args.expected_baseline_hash,
        expected_current_hash=args.expected_current_hash,
        actual_summary=replay["summary"],
        actual_baseline_hash=replay["baseline_hash"],
        actual_current_hash=replay["current_hash"],
    )
    if mismatch is not None:
        mismatch_name, _expected, actual = mismatch
        print("Governance replay: match=false")
        print(f"- mismatch: {mismatch_name}")
        print(f"- expected: {_expected_label(mismatch_name)}")
        print(f"- actual: {actual}")
        return 1

    print("Governance replay: match=true")
    print(f"- source: {replay['source']}")
    print("- entries_compared: 2")
    print(f"- baseline_hash: {replay['baseline_hash']}")
    print(f"- current_hash: {replay['current_hash']}")
    print(f"- summary: {replay['summary']}")
    print(f"- gate: {replay['gate']}")
    return 0


def _build_replay(args: argparse.Namespace) -> dict[str, str]:
    if args.history is not None:
        history = _load_history_metadata(args.history)
        if len(history) < 2:
            raise ReplayInputError("insufficient_history")
        baseline = history[-2]
        current = history[-1]
        view = build_benchmark_diff_view_from_history(history)
        return _replay_payload(
            source="history",
            baseline_hash=baseline.benchmark_hash,
            current_hash=current.benchmark_hash,
            summary=format_benchmark_governance_summary(view),
            gate=classify_benchmark_governance_gate(view),
        )

    baseline = _load_snapshot_metadata(args.before)
    current = _load_snapshot_metadata(args.after)
    view = build_benchmark_diff_view(baseline, current)
    return _replay_payload(
        source="snapshots",
        baseline_hash=baseline.version_info.benchmark_hash,
        current_hash=current.version_info.benchmark_hash,
        summary=format_benchmark_governance_summary(view),
        gate=classify_benchmark_governance_gate(view),
    )


def _load_history_metadata(path: Path) -> tuple[BenchmarkHistoryEntry, ...]:
    payload = _read_json_mapping(path)
    entries = payload.get("entries", ())
    if not isinstance(entries, Sequence) or isinstance(
        entries, (str, bytes, bytearray)
    ):
        raise ReplayInputError("malformed_metadata")

    history: list[BenchmarkHistoryEntry] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ReplayInputError("malformed_metadata")
        try:
            history.append(benchmark_history_entry_from_json_dict(entry))
        except (TypeError, ValueError) as exc:
            raise ReplayInputError("malformed_metadata") from exc
    return tuple(history)


def _load_snapshot_metadata(path: Path) -> BenchmarkSnapshot:
    try:
        return benchmark_snapshot_from_json_dict(_read_json_mapping(path))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ReplayInputError("malformed_metadata") from exc


def _read_json_mapping(path: Path) -> Mapping[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ReplayInputError("malformed_metadata")
    return payload


def _replay_payload(
    *,
    source: str,
    baseline_hash: str,
    current_hash: str,
    summary: str,
    gate: str,
) -> dict[str, str]:
    return {
        "source": source,
        "baseline_hash": baseline_hash,
        "current_hash": current_hash,
        "summary": summary,
        "gate": gate,
    }


def _first_mismatch(
    *,
    expected_summary: str | None,
    expected_baseline_hash: str | None,
    expected_current_hash: str | None,
    actual_summary: str,
    actual_baseline_hash: str,
    actual_current_hash: str,
) -> tuple[str, str, str] | None:
    checks = (
        ("expected_summary", expected_summary, actual_summary),
        ("expected_baseline_hash", expected_baseline_hash, actual_baseline_hash),
        ("expected_current_hash", expected_current_hash, actual_current_hash),
    )
    for name, expected, actual in checks:
        if expected is not None and expected != actual:
            return name, expected, actual
    return None


def _expected_label(name: str) -> str:
    labels = {
        "expected_summary": "provided_summary",
        "expected_baseline_hash": "provided_baseline_hash",
        "expected_current_hash": "provided_current_hash",
    }
    return labels.get(name, "provided_metadata")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
