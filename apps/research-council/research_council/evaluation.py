"""Deterministic golden-case evaluation harness for Research Council.

The harness checks stable invariants rather than exact output snapshots. It
does not call LLMs, perform network work, use embeddings, or grade semantics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .json_export import result_to_json_dict
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


@dataclass(frozen=True)
class InvariantResult:
    """One deterministic invariant check result."""

    case_id: str
    invariant: str
    passed: bool
    message: str


@dataclass(frozen=True)
class CaseEvaluation:
    """Evaluation result for one golden case."""

    case_id: str
    path: str
    profile_id: str
    selected_by: str
    invariant_results: tuple[InvariantResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.invariant_results)

    @property
    def failures(self) -> tuple[InvariantResult, ...]:
        return tuple(result for result in self.invariant_results if not result.passed)


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
class _GoldenCase:
    case_id: str
    path: str
    input_data: ResearchCouncilInput
    profile: str | None
    expected: Mapping[str, Any]


def evaluate_golden_cases(
    root: str | Path | None = None,
) -> RegressionSummary:
    """Evaluate all golden-case JSON files under ``root`` deterministically."""

    cases_root = Path(root) if root is not None else DEFAULT_GOLDEN_CASES_ROOT
    evaluations = tuple(evaluate_case(path) for path in _case_paths(cases_root))
    return RegressionSummary(evaluations=evaluations)


def evaluate_case(case: str | Path | Mapping[str, Any]) -> CaseEvaluation:
    """Evaluate one golden case path or already-loaded mapping."""

    golden_case = _load_case(case)
    try:
        result = run_research_council(
            golden_case.input_data,
            profile=golden_case.profile,
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
        )

    profile = payload.get("profile", {})
    profile_id = str(profile.get("profile_id", ""))
    selected_by = str(profile.get("selected_by", ""))
    scopes = _build_scopes(payload)
    checks: list[InvariantResult] = []
    checks.extend(_profile_invariants(golden_case, payload))
    checks.extend(_contains_invariants(golden_case, scopes))
    checks.extend(_not_contains_invariants(golden_case, scopes))
    checks.extend(_label_invariants(golden_case, payload, scopes))
    return CaseEvaluation(
        case_id=golden_case.case_id,
        path=golden_case.path,
        profile_id=profile_id,
        selected_by=selected_by,
        invariant_results=tuple(checks),
    )


def format_regression_summary(summary: RegressionSummary) -> str:
    """Format a concise regression report without snapshot diffs."""

    if summary.passed:
        return (
            "Golden cases passed: "
            f"{summary.case_count} cases, {summary.invariant_count} invariants."
        )

    lines = [
        "Golden case regression failures: "
        f"{summary.failed_count}/{summary.invariant_count} invariants failed "
        f"across {summary.case_count} cases."
    ]
    for evaluation in summary.evaluations:
        for failure in evaluation.failures:
            lines.append(f"- {evaluation.case_id}: {failure.message}")
    return "\n".join(lines)


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


def _build_scopes(payload: Mapping[str, Any]) -> dict[str, str]:
    evidence = _mapping_list(payload.get("evidence_ledger"))
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
        "markdown_report": _stringify(payload.get("markdown_report", {})),
    }
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
        )
    )
    scopes["result_text"] = " ".join(scopes.values())
    return scopes


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


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = (value,)
    if not isinstance(value, Sequence):
        raise ValueError("expected a string sequence")
    return tuple(str(item).strip() for item in value if str(item).strip())


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
    "CaseEvaluation",
    "DEFAULT_GOLDEN_CASES_ROOT",
    "InvariantResult",
    "RegressionSummary",
    "evaluate_case",
    "evaluate_golden_cases",
    "format_regression_summary",
]
