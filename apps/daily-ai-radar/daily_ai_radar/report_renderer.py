"""Markdown rendering for Daily AI Radar results."""

from __future__ import annotations

from .schemas import DailyAIRadarResult, RadarItem


def render_markdown_report(result: DailyAIRadarResult) -> str:
    """Render a deterministic Daily AI Radar Markdown report."""

    lines: list[str] = ["# Daily AI Radar Report", ""]
    lines.extend(_render_executive_summary(result))
    lines.extend(_render_candidate_highlights(result.items))
    lines.extend(_render_candidate_details(result.items))
    lines.extend(_render_watch_ignored_items(result.items))
    lines.extend(_render_unknowns(result.unknowns))
    lines.extend(_render_governance_notes())
    return "\n".join(lines).rstrip() + "\n"


def _render_executive_summary(result: DailyAIRadarResult) -> list[str]:
    return [
        "## Executive Summary",
        "",
        f"- Radar date: {result.radar_date}",
        f"- Items reviewed: {result.reviewed_items_count}",
        f"- Candidate count: {result.candidate_count}",
        f"- Human approval required count: {result.human_approval_required_count}",
        f"- Recommended next action: {result.recommended_next_action}",
        (
            "- Safety note: This report is a deterministic local summary of curated "
            "metadata, not implementation approval or verified external research."
        ),
        "",
    ]


def _render_candidate_highlights(items: tuple[RadarItem, ...]) -> list[str]:
    lines = [
        "## Candidate Highlights",
        "",
        "| ID | Topic | Area | Relevance | Risk | Recommendation |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            "| "
            f"`{_inline(item.item_id)}` | "
            f"{_inline(item.title)} | "
            f"`{_inline(item.area)}` | "
            f"{item.relevance_to_jarvis} | "
            f"{item.risk} | "
            f"`{_inline(item.recommendation)}` |"
        )
    lines.append("")
    return lines


def _render_candidate_details(items: tuple[RadarItem, ...]) -> list[str]:
    lines = ["## Candidate Details", ""]
    for item in items:
        lines.extend(
            [
                f"### {_heading(item.item_id)}",
                "",
                f"- What changed: {_sentence(item.summary)}",
                (
                    "- Why it matters for Jarvis: "
                    f"{_why_it_matters(item)}"
                ),
                f"- Evidence reference: `{_code(item.source_url_or_ref)}`",
                f"- Claimed capability: {_sentence(item.claimed_capability)}",
                (
                    "- Scores: "
                    f"relevance_to_jarvis={item.relevance_to_jarvis}, "
                    f"implementation_effort={item.implementation_effort}, "
                    f"risk={item.risk}, urgency={item.urgency}, maturity={item.maturity}"
                ),
                f"- Risk: {_risk_summary(item)}",
                f"- Suggested next step: {_suggested_next_step(item)}",
                f"- Human approval required: {_yes_no(item.human_approval_required)}",
                f"- Recommendation: `{_code(item.recommendation)}`",
                "",
            ]
        )
    return lines


def _render_watch_ignored_items(items: tuple[RadarItem, ...]) -> list[str]:
    lines = ["## Watch / Ignored Items", ""]
    watch_or_ignored = [
        item for item in items if item.recommendation in {"WATCH", "IGNORE"}
    ]
    if not watch_or_ignored:
        lines.append("- No items were classified as `WATCH` or `IGNORE`.")
        lines.append("")
        return lines

    for item in watch_or_ignored:
        if item.recommendation == "WATCH":
            reason = "Keep visible for later review; no immediate implementation action."
        else:
            reason = "No Jarvis action recommended from the current metadata."
        lines.append(f"- `{_code(item.item_id)}` (`{item.recommendation}`): {reason}")
    lines.append("")
    return lines


def _render_unknowns(unknowns: tuple[str, ...]) -> list[str]:
    lines = ["## Unknowns", ""]
    if not unknowns:
        lines.append("- No unknowns were recorded.")
    else:
        lines.extend(f"- {_sentence(unknown)}" for unknown in unknowns)
    lines.append("")
    return lines


def _render_governance_notes() -> list[str]:
    return [
        "## Governance Notes",
        "",
        "- This report is not implementation approval.",
        "- Human approval is required before code changes.",
        "- Vendor claims are treated as unverified until reviewed.",
        "- Full source bodies are not stored by this v0.2 renderer.",
        "- No web crawling, scheduler, LLM/API call, task creation, commit, push, or live agent integration is performed by this renderer.",
        "",
    ]


def _why_it_matters(item: RadarItem) -> str:
    if item.relevance_to_jarvis >= 4:
        return (
            "The curated metadata appears closely related to Jarvis memory, "
            "skills, orchestration, evaluation, safety, or self-improvement goals."
        )
    if item.relevance_to_jarvis >= 3:
        return (
            "The curated metadata may become relevant if a concrete Jarvis workflow "
            "needs this capability."
        )
    return (
        "The curated metadata has limited Jarvis fit based on current bounded scores."
    )


def _risk_summary(item: RadarItem) -> str:
    if item.recommendation == "IGNORE":
        return (
            f"{_risk_label(item.risk)} ({item.risk}/5), but ignored as an "
            "implementation candidate because current Jarvis relevance is low."
        )
    if item.risk >= 4:
        return (
            f"High ({item.risk}/5). Treat this as review-only until human approval "
            "and any needed Research Council analysis are complete."
        )
    if item.risk == 3:
        return "Medium (3/5). Keep review boundaries visible before adoption."
    return f"Low ({item.risk}/5) for metadata review; implementation still requires approval."


def _risk_label(risk: int) -> str:
    if risk >= 4:
        return "High"
    if risk == 3:
        return "Medium"
    return "Low"


def _suggested_next_step(item: RadarItem) -> str:
    if item.recommendation == "NEEDS_HUMAN_REVIEW":
        return "Run human policy or security review before any implementation task is created."
    if item.recommendation == "NEEDS_RESEARCH_COUNCIL":
        return "Send to Research Council for evidence, risk, and minimum experiment analysis."
    if item.recommendation == "DO_NOW":
        return "Proceed only with the next documentation or review action; do not change code without approval."
    if item.recommendation == "WATCH":
        return "Keep on watch and revisit when a concrete Jarvis workflow needs it."
    return "No follow-up action recommended from this metadata."


def _inline(value: str) -> str:
    return " ".join(str(value).split()).replace("|", "\\|")


def _sentence(value: str) -> str:
    return _inline(value)


def _heading(value: str) -> str:
    return _inline(value).replace("#", "").strip() or "untitled"


def _code(value: str) -> str:
    return _inline(value).replace("`", "\\`")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
