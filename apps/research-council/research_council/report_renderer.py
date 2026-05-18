"""Markdown rendering for Research Council result-like data.

The renderer does not collect evidence, create citations, or infer external
facts. It only formats the structured data it receives into an early research
brief and marks absent fields explicitly.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
import re
from typing import Any


_MISSING = "Missing from result."


def render_markdown_report(result: Any) -> str:
    """Render a ResearchCouncilResult-like object as a Markdown research brief.

    ``result`` may be a schema dataclass instance, a plain object with matching
    attributes, or a dictionary with matching keys.
    """

    markdown_report = _field(result, "markdown_report")
    title = _first_text(
        _field(markdown_report, "title"),
        _field(result, "title"),
        default="Research Council Brief",
    )

    claims = _as_list(_field(result, "claims"))
    evidence_ledger = _as_list(_field(result, "evidence_ledger"))
    reviewer_critiques = _as_list(_field(result, "reviewer_critiques"))
    experiments = _as_list(_field(result, "experiments"))
    recommendation = _field(result, "recommendation")
    profile = _field(result, "profile")
    warnings = _as_list(_field(result, "warnings"))

    input_data = _first_present(
        _field(result, "input"),
        _field(result, "input_data"),
        _field(result, "research_input"),
    )
    raw_idea = _first_text(
        _field(result, "raw_idea"),
        _field(input_data, "raw_idea"),
        default=_MISSING,
    )
    goal = _first_text(
        _field(result, "goal"),
        _field(input_data, "goal"),
        default=_MISSING,
    )
    input_summary = _first_text(_field(result, "input_summary"), default=_MISSING)
    context = _first_text(_field(input_data, "context"), _field(result, "context"), default="")
    constraints = _as_list(_field(input_data, "constraints") or _field(result, "constraints"))
    provided_evidence = _as_list(
        _field(input_data, "provided_evidence") or _field(result, "provided_evidence")
    )

    missing_evidence = [
        entry for entry in evidence_ledger if _clean_text(_field(entry, "evidence_type"), "") == "missing"
    ]
    provided_evidence_entries = [
        entry for entry in evidence_ledger if _clean_text(_field(entry, "evidence_type"), "") == "provided"
    ]
    needs_evidence_claims = [
        claim for claim in claims if _clean_text(_field(claim, "source_label"), "") == "needs_evidence"
    ]

    lines: list[str] = [f"# {title}", ""]
    lines.extend(
        _render_executive_summary(
            claims=claims,
            evidence_ledger=evidence_ledger,
            provided_evidence_entries=provided_evidence_entries,
            missing_evidence=missing_evidence,
            reviewer_critiques=reviewer_critiques,
            experiments=experiments,
            recommendation=recommendation,
            profile=profile,
            warnings=warnings,
        )
    )
    lines.extend(
        _render_input_section(
            raw_idea=raw_idea,
            goal=goal,
            input_summary=input_summary,
            context=context,
            constraints=constraints,
            provided_evidence=provided_evidence,
        )
    )
    lines.extend(_render_claims(claims))
    lines.extend(_render_evidence_ledger(evidence_ledger))
    lines.extend(_render_critiques(reviewer_critiques))
    lines.extend(_render_experiments(experiments))
    lines.extend(_render_recommendation(recommendation))
    lines.extend(_render_unknowns(missing_evidence, needs_evidence_claims, evidence_ledger))
    lines.extend(_render_next_steps(recommendation, reviewer_critiques, experiments))

    return "\n".join(lines).rstrip() + "\n"


def _render_executive_summary(
    *,
    claims: list[Any],
    evidence_ledger: list[Any],
    provided_evidence_entries: list[Any],
    missing_evidence: list[Any],
    reviewer_critiques: list[Any],
    experiments: list[Any],
    recommendation: Any,
    profile: Any,
    warnings: list[Any],
) -> list[str]:
    recommendation_summary = _first_text(_field(recommendation, "summary"), default=_MISSING)
    decision = _first_text(_field(recommendation, "decision"), default=_MISSING)
    profile_summary = _profile_summary(profile)

    lines = [
        "## Executive Summary",
        "",
        "This local-only brief uses the supplied input and evidence ledger. "
        "It does not add web research, external evidence, or citations.",
        "",
        f"- Claims reviewed: {len(claims)}",
        (
            "- Evidence ledger: "
            f"{len(provided_evidence_entries)} provided; {len(missing_evidence)} missing; "
            f"{len(evidence_ledger)} total"
        ),
        f"- Reviewer critiques: {len(reviewer_critiques)}",
        f"- Minimum viable experiments: {len(experiments)}",
        f"- Recommendation decision: {_code(decision)}",
        f"- Recommendation summary: {recommendation_summary}",
    ]
    if profile_summary:
        lines.insert(8, f"- Selected profile: {profile_summary}")
    if warnings:
        lines.extend(["", "Warnings:"])
        for warning in warnings:
            lines.append(f"- {_clean_text(warning)}")
    lines.append("")
    return lines


def _render_input_section(
    *,
    raw_idea: str,
    goal: str,
    input_summary: str,
    context: str,
    constraints: list[Any],
    provided_evidence: list[Any],
) -> list[str]:
    lines = [
        "## Input Idea and Goal",
        "",
        f"- Raw idea: {raw_idea}",
        f"- Goal: {goal}",
        f"- Input summary: {input_summary}",
    ]
    if context:
        lines.append(f"- Context: {context}")
    if constraints:
        lines.append("- Constraints:")
        lines.extend(f"  - {_clean_text(item)}" for item in constraints)
    if provided_evidence:
        lines.append("- User-provided evidence:")
        lines.extend(f"  - {_clean_text(item)}" for item in provided_evidence)
    lines.append("")
    return lines


def _render_claims(claims: list[Any]) -> list[str]:
    lines = ["## Structured Claims", ""]
    if not claims:
        return lines + ["No structured claims were supplied.", ""]

    for claim in claims:
        claim_id = _first_text(_field(claim, "id"), default="claim-without-id")
        source_label = _code(_field(claim, "source_label"), "missing source label")
        confidence = _code(_field(claim, "confidence"), "missing confidence")
        lines.append(
            f"- {_code(claim_id)} [{source_label}, {confidence}]: "
            f"{_clean_text(_field(claim, 'text'))}"
        )
        rationale = _first_text(_field(claim, "rationale"), default="")
        if rationale:
            lines.append(f"  Rationale: {rationale}")
    lines.append("")
    return lines


def _render_evidence_ledger(evidence_ledger: list[Any]) -> list[str]:
    lines = ["## Evidence Ledger", ""]
    if not evidence_ledger:
        return lines + ["No evidence ledger entries were supplied. Missing evidence is therefore unknown.", ""]

    provided_entries = [
        entry for entry in evidence_ledger if _clean_text(_field(entry, "evidence_type"), "") == "provided"
    ]
    missing_entries = [
        entry for entry in evidence_ledger if _clean_text(_field(entry, "evidence_type"), "") == "missing"
    ]

    if provided_entries:
        lines.append("Provided local input:")
        for entry in provided_entries:
            entry_id = _first_text(_field(entry, "id"), default="evidence-without-id")
            claim_id = _first_text(_field(entry, "claim_id"), default="missing claim id")
            lines.append(
                f"- {_code(entry_id)} -> {_code(claim_id)}: "
                f"{_clean_text(_field(entry, 'summary'))}"
            )
        lines.append("")

    if missing_entries:
        lines.append("Missing evidence entries:")
        for entry in missing_entries:
            entry_id = _first_text(_field(entry, "id"), default="evidence-without-id")
            claim_id = _first_text(_field(entry, "claim_id"), default="missing claim id")
            category = _gap_category(entry)
            category_text = f" [{category}]" if category else ""
            lines.append(
                f"- {_code(entry_id)}{category_text} for {_code(claim_id)}: "
                f"{_clean_text(_field(entry, 'summary'))}"
            )
        lines.append("")
        return lines

    lines.append("No explicit missing evidence entries were supplied.")
    lines.append("")
    return lines


def _render_critiques(reviewer_critiques: list[Any]) -> list[str]:
    lines = ["## Reviewer Critiques", ""]
    if not reviewer_critiques:
        return lines + ["No reviewer critiques were supplied.", ""]

    for critique in reviewer_critiques:
        critique_id = _first_text(_field(critique, "id"), default="critique-without-id")
        claim_id = _first_text(_field(critique, "claim_id"), default="")
        scope = _code(claim_id) if claim_id else "whole brief"
        lines.extend(
            [
                (
                    f"- {_code(critique_id)} "
                    f"{_clean_text(_field(critique, 'reviewer_role'), 'Missing reviewer role.')} "
                    f"({_code(_field(critique, 'severity'), 'missing severity')}, scope {scope}): "
                    f"{_clean_text(_field(critique, 'finding'))}"
                ),
                f"  Suggested action: {_clean_text(_field(critique, 'suggested_action'))}",
            ]
        )
    lines.append("")
    return lines


def _render_experiments(experiments: list[Any]) -> list[str]:
    lines = ["## Minimum Viable Experiments", ""]
    if not experiments:
        return lines + ["No minimum viable experiments were supplied.", ""]

    for experiment in experiments:
        experiment_id = _first_text(_field(experiment, "id"), default="experiment-without-id")
        title = _first_text(_field(experiment, "title"), default="Untitled experiment")
        claim_ids = _as_list(_field(experiment, "hypothesis_claim_ids"))
        claim_text = ", ".join(_code(claim_id) for claim_id in claim_ids) if claim_ids else _MISSING
        lines.extend(
            [
                f"### {_clean_heading(experiment_id)}: {title}",
                "",
                f"- Hypothesis claims: {claim_text}",
                f"- Method: {_clean_text(_field(experiment, 'method'))}",
                f"- Success metric: {_clean_text(_field(experiment, 'success_metric'))}",
                f"- Minimum sample: {_clean_text(_field(experiment, 'minimum_sample'))}",
                f"- Risk: {_clean_text(_field(experiment, 'risk'))}",
                "",
            ]
        )
    return lines


def _render_recommendation(recommendation: Any) -> list[str]:
    return [
        "## Recommendation",
        "",
        f"- Decision: {_code(_field(recommendation, 'decision'), 'missing decision')}",
        f"- Summary: {_clean_text(_field(recommendation, 'summary'))}",
        f"- Rationale: {_clean_text(_field(recommendation, 'rationale'))}",
        f"- Immediate next step: {_clean_text(_field(recommendation, 'next_step'))}",
        "",
    ]


def _render_unknowns(
    missing_evidence: list[Any], needs_evidence_claims: list[Any], evidence_ledger: list[Any]
) -> list[str]:
    lines = ["## Unknowns / Evidence Gaps", ""]
    if not evidence_ledger:
        lines.extend(["- Evidence ledger is missing, so support for all claims is unknown."])
    if missing_evidence:
        lines.append("- Missing evidence entries by category:")
        for category, entries in _entries_by_gap_category(missing_evidence).items():
            claim_ids = ", ".join(
                _code(_first_text(_field(entry, "claim_id"), default="missing claim id"))
                for entry in entries
            )
            first_summary = _clean_text(_field(entries[0], "summary"))
            lines.append(f"  - {category}: {claim_ids}. {first_summary}")
    elif evidence_ledger:
        lines.append("- No explicit missing evidence entries were supplied.")

    if needs_evidence_claims:
        lines.append("- Claims marked `needs_evidence`:")
        for claim in needs_evidence_claims:
            claim_id = _first_text(_field(claim, "id"), default="claim-without-id")
            lines.append(f"  - {_code(claim_id)}: {_clean_text(_field(claim, 'text'))}")
    lines.append("")
    return lines


def _render_next_steps(recommendation: Any, reviewer_critiques: list[Any], experiments: list[Any]) -> list[str]:
    lines = ["## Next Steps", ""]

    next_step = _first_text(_field(recommendation, "next_step"), default="")
    if not next_step:
        return lines + ["No next steps were supplied.", ""]

    lines.append(f"- Do next: {next_step}")
    primary_experiment = _primary_experiment_from_next_step(next_step, experiments)
    if primary_experiment:
        lines.append(
            "- Use secondary experiments only after the primary blocker result is known."
        )
    lines.append("")
    return lines


def _field(value: Any, name: str, default: Any = None) -> Any:
    value = _to_plain(value)
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _first_text(*values: Any, default: str) -> str:
    for value in values:
        text = _clean_text(value, "")
        if text:
            return text
    return default


def _as_list(value: Any) -> list[Any]:
    value = _to_plain(value)
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, (str, bytes)):
        return [value.decode() if isinstance(value, bytes) else value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def _clean_text(value: Any, missing: str = _MISSING) -> str:
    value = _to_plain(value)
    if value is None:
        return missing
    text = str(value).strip()
    if not text:
        return missing
    return " ".join(text.split())


def _clean_heading(value: Any) -> str:
    return _clean_text(value, "Untitled").replace("#", "").strip() or "Untitled"


def _code(value: Any, missing: str = _MISSING) -> str:
    text = _clean_text(value, missing)
    escaped = text.replace("`", "\\`")
    return f"`{escaped}`"


def _to_plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value


def _gap_category(entry: Any) -> str | None:
    notes = _first_text(_field(entry, "notes"), default="")
    match = re.search(r"\bgap_category=([a-z_]+)\b", notes)
    if match:
        return match.group(1)
    return None


def _entries_by_gap_category(entries: list[Any]) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = {}
    for entry in entries:
        grouped.setdefault(_gap_category(entry) or "uncategorized", []).append(entry)
    return grouped


def _primary_experiment_from_next_step(next_step: str, experiments: list[Any]) -> Any | None:
    for experiment in experiments:
        experiment_id = _first_text(_field(experiment, "id"), default="")
        if experiment_id and experiment_id in next_step:
            return experiment
    return None


def _profile_summary(profile: Any) -> str:
    profile_id = _first_text(_field(profile, "profile_id"), default="")
    selected_by = _first_text(_field(profile, "selected_by"), default="")
    if not profile_id:
        return ""
    if selected_by:
        return f"{_code(profile_id)} ({selected_by.replace('_', ' ')})"
    return _code(profile_id)


__all__ = ["render_markdown_report"]
