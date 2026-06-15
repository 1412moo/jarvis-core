"""Local Tk launcher for deterministic Research Council demo runs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from research_council import (
    LLMAugmentationMode,
    ResearchCouncilInput,
    list_profiles,
    resolve_domain_profile,
    run_research_council,
    write_result_json,
)


APP_TITLE = "Research Council Local Launcher"
DEFAULT_OUTPUT_ROOT = Path.home() / "ResearchCouncilRuns"
DEFAULT_PROFILE_ID = "ai_saas"
AUGMENTATION_MODE_VALUES = tuple(mode.value for mode in LLMAugmentationMode)
SANDBOX_MESSAGE = "deterministic sandbox, no external LLM calls"
IDEA_ONLY_HELP = (
    "You can start with only an idea. Empty fields will use safe default prompts."
)
DEFAULT_GOAL = (
    "Evaluate whether this idea can become a viable MVP and identify the next "
    "validation step."
)
DEFAULT_CONTEXT = (
    "The user is exploring this as a product or workflow opportunity. The report "
    "should identify assumptions, evidence gaps, risks, and minimum viable experiments."
)
DEFAULT_CONSTRAINTS = (
    "Human review required",
    "No external services",
    "Treat outputs as validation planning, not final proof",
)
REFINEMENT_BASE_CONSTRAINTS = (
    "local-only",
    "no external services",
    "Current output is idea refinement and validation planning only",
    "Treat user-provided notes as evidence leads, not final proof",
    "Separate technical feasibility from business validation",
)
INDUSTRIAL_AUTOMATION_PROFILE = "hardware_device"
INDUSTRIAL_AUTOMATION_ALTERNATIVES = (
    "developer_tool",
    "enterprise_b2b",
    "ai_saas",
)
INDUSTRIAL_AUTOMATION_SIGNALS = (
    ("industrial automation", 5),
    ("manufacturing", 4),
    ("factory", 3),
    ("equipment", 3),
    ("machine", 3),
    ("setup", 3),
    ("simulation", 4),
    ("fault", 3),
    ("downtime", 4),
    ("plc", 4),
    ("장비", 3),
    ("설비", 3),
    ("제조", 3),
    ("공정", 3),
    ("생산", 3),
    ("자동화", 4),
    ("셋업", 3),
    ("가동", 3),
    ("시뮬레이션", 4),
    ("장애", 3),
    ("고장", 3),
    ("정지", 3),
    ("멈추", 3),
    ("원인", 2),
)
HEALTHCARE_SIGNALS = (
    ("healthcare", 4),
    ("home health", 5),
    ("health", 2),
    ("clinical", 4),
    ("patient", 4),
    ("nurse", 4),
    ("medication", 4),
    ("wound", 4),
    ("caregiver", 3),
    ("elderly", 3),
    ("care", 1),
    ("간병", 4),
    ("욕창", 4),
    ("복약", 4),
    ("약", 1),
    ("약품", 4),
    ("백신", 4),
    ("환자", 4),
    ("병원", 4),
    ("간호사", 4),
    ("요양", 4),
    ("보호자", 3),
    ("치매", 4),
    ("노인", 3),
    ("재활", 4),
    ("가족 공유", 3),
    ("병원 전달사항", 5),
    ("홈케어", 4),
)
HEALTHCARE_CONSTRAINTS = (
    "Keep privacy and sensitive health information boundaries explicit",
    "Require human review before any clinical, medication, wound, or care recommendation",
    "Do not treat outputs as diagnosis, treatment, or clinical proof",
    "Validate care workflow safety with caregivers or qualified professionals",
)
EDUCATION_SIGNALS = (
    ("education", 4),
    ("student", 4),
    ("teacher", 4),
    ("school", 3),
    ("middle school", 5),
    ("minor", 4),
    ("parent", 3),
    ("tutor", 3),
    ("math", 3),
    ("learning", 3),
    ("practice drills", 3),
    ("학생", 4),
    ("중학생", 5),
    ("고등학생", 5),
    ("초등학생", 5),
    ("학습", 4),
    ("오답", 4),
    ("문제 추천", 4),
    ("문제추천", 4),
    ("교사", 4),
    ("학부모", 4),
    ("교육", 4),
    ("튜터", 3),
    ("수학", 3),
)
EDUCATION_CONSTRAINTS = (
    "Protect student data and classroom privacy",
    "Keep minor safety and parent/teacher oversight explicit",
    "Validate learning efficacy before making educational outcome claims",
    "Check teacher, parent, and student workflow fit separately",
)
ADULT_LEARNING_SIGNALS = (
    "adult",
    "adults",
)
MINOR_EDUCATION_CONTEXT_SIGNALS = (
    "student",
    "students",
    "teacher",
    "school",
    "middle school",
    "minor",
    "parent",
    "child",
    "children",
    "kid",
    "kids",
    "classroom",
    "학생",
    "중학생",
    "고등학생",
    "초등학생",
    "교사",
    "학부모",
    "학교",
)
ADULT_EDUCATION_CONSTRAINTS = (
    "Validate learning efficacy before making educational outcome claims",
    "Check adult learner workflow and support needs separately",
)
FINTECH_SIGNALS = (
    ("fintech", 5),
    ("bank", 4),
    ("transaction", 3),
    ("subscription", 3),
    ("debt", 4),
    ("payoff", 3),
    ("finance", 4),
    ("financial", 4),
    ("gig worker", 3),
    ("budget", 3),
    ("은행", 4),
    ("계좌", 4),
    ("거래내역", 4),
    ("구독료", 3),
    ("소비패턴", 3),
    ("부채", 4),
    ("상환", 3),
    ("대출", 4),
    ("투자", 4),
    ("자산", 4),
    ("금융", 4),
    ("개인 금융", 5),
)
FINTECH_CONSTRAINTS = (
    "Keep financial advice boundaries explicit",
    "Protect bank, transaction, and personal finance privacy",
    "Validate recommendations before suggesting debt, subscription, or budgeting actions",
    "Treat outputs as planning support, not financial, legal, or investment advice",
)
LOGISTICS_SIGNALS = (
    ("logistics", 5),
    ("route", 4),
    ("fleet", 4),
    ("delivery", 4),
    ("driver", 3),
    ("dispatch", 4),
    ("package", 3),
    ("traffic", 3),
    ("late deliveries", 3),
    ("배달", 4),
    ("배송", 4),
    ("기사", 3),
    ("배달기사", 5),
    ("동선", 4),
    ("경로", 4),
    ("주문", 3),
    ("배차", 4),
    ("물류", 5),
    ("차량", 3),
    ("운송", 4),
)
LOGISTICS_CONSTRAINTS = (
    "Separate planning output from live operations decisions",
    "Validate routing data quality, latency, and exception handling",
    "Check driver workflow, dispatch handoff, and operational accountability",
    "Do not assume prediction accuracy without historical route and delivery data",
)
AUDIT_COMPLIANCE_SIGNALS = (
    ("audit", 5),
    ("evidence readiness", 5),
    ("policy controls", 5),
    ("controls", 3),
    ("compliance", 4),
    ("approvals", 3),
    ("evidence owners", 4),
    ("screenshots", 2),
    ("logs", 2),
    ("quarterly audits", 4),
    ("내부감사", 5),
    ("감사", 4),
    ("통제", 4),
    ("승인내역", 4),
    ("승인", 3),
    ("증적", 4),
    ("증거", 3),
    ("정책 증거", 5),
    ("정책증거", 5),
    ("컴플라이언스", 4),
    ("감사준비", 5),
)
AUDIT_COMPLIANCE_CONSTRAINTS = (
    "Keep audit evidence ownership and human approval boundaries explicit",
    "Do not treat generated output as compliance proof",
    "Validate control mapping, evidence freshness, and reviewer workflow separately",
    "Account for enterprise rollout, security review, and audit-log requirements",
)
CONSUMER_APP_SIGNALS = (
    ("mobile app", 4),
    ("friends", 3),
    ("vote", 3),
    ("split costs", 3),
    ("weekend activities", 3),
    ("모바일 앱", 5),
    ("친구", 4),
    ("모임", 4),
    ("투표", 4),
    ("정산", 3),
    ("비용정산", 5),
    ("일정", 3),
    ("커뮤니티", 3),
    ("동호회", 3),
)
HARDWARE_SENSOR_SIGNALS = (
    ("sensor", 5),
    ("device", 4),
    ("temperature", 4),
    ("alert", 3),
    ("refrigerator", 4),
    ("vaccine", 5),
    ("센서", 5),
    ("장치", 4),
    ("온도", 4),
    ("냉장고", 4),
    ("백신", 5),
    ("약품", 5),
    ("이상 알림", 4),
    ("감지", 3),
    ("알림", 3),
)
COLD_CHAIN_SENSOR_CONSTRAINTS = (
    "Validate sensor calibration, temperature threshold, and alert reliability",
    "Do not assume vaccine, medication, or cold-chain safety without measured logs",
    "Plan bench and field checks for false alarms, missed alerts, and handoff workflow",
    "Require human review for medication, vaccine, or clinical storage decisions",
)


@dataclass(frozen=True)
class LocalRunArtifacts:
    run_dir: Path
    input_json: Path
    report_md: Path
    result_json: Path


@dataclass(frozen=True)
class IdeaRefinement:
    goal: str
    context: str
    constraints: tuple[str, ...]
    provided_evidence: tuple[str, ...]
    recommended_profile: str
    alternative_profiles: tuple[str, ...]
    profile_confidence: str
    profile_rationale: str


def split_lines(value: str) -> tuple[str, ...]:
    """Return non-empty stripped lines from a multiline text box."""

    return tuple(line.strip() for line in value.splitlines() if line.strip())


def default_output_root() -> Path:
    return DEFAULT_OUTPUT_ROOT


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def normalize_output_root(output_root: Path) -> Path:
    resolved_output_root = output_root.expanduser().resolve(strict=False)
    resolved_repo_root = repo_root().resolve(strict=False)
    if is_relative_to(resolved_output_root, resolved_repo_root):
        raise ValueError(
            "Output directory must be outside the repository. "
            f"Choose a folder outside {resolved_repo_root}."
        )
    return resolved_output_root


def profile_ids() -> tuple[str, ...]:
    ids = tuple(profile.id for profile in list_profiles())
    if DEFAULT_PROFILE_ID in ids:
        return ids
    return (DEFAULT_PROFILE_ID, *ids)


def build_input_payload(
    *,
    idea: str,
    goal: str,
    context: str,
    constraints: tuple[str, ...],
    provided_evidence: tuple[str, ...],
) -> dict[str, object]:
    return {
        "idea": idea,
        "goal": goal,
        "context": context,
        "constraints": list(constraints),
        "provided_evidence": list(provided_evidence),
    }


def with_safe_defaults(
    *,
    goal: str,
    context: str,
    constraints: tuple[str, ...],
) -> tuple[str, str, tuple[str, ...]]:
    normalized_constraints = tuple(
        str(item).strip() for item in constraints if str(item).strip()
    )
    return (
        goal.strip() or DEFAULT_GOAL,
        context.strip() or DEFAULT_CONTEXT,
        normalized_constraints or DEFAULT_CONSTRAINTS,
    )


def refine_idea_for_launcher(raw_idea: str) -> IdeaRefinement:
    """Turn a raw idea into editable launcher fields using local deterministic rules."""

    idea = _clean_text(raw_idea)
    if not idea:
        raise ValueError("Idea is required before refinement.")

    industrial_refinement = _industrial_automation_refinement(idea)
    if industrial_refinement is not None:
        return industrial_refinement
    return _generic_refinement(idea)


def format_profile_recommendation(refinement: IdeaRefinement) -> str:
    alternatives = ", ".join(refinement.alternative_profiles) or "none"
    return (
        f"recommended: {refinement.recommended_profile}; "
        f"alternatives: {alternatives}; "
        f"confidence: {refinement.profile_confidence}"
    )


def _industrial_automation_refinement(idea: str) -> IdeaRefinement | None:
    matched_signals, signal_score = _matched_weighted_signals(
        idea,
        INDUSTRIAL_AUTOMATION_SIGNALS,
    )
    if len(matched_signals) < 2 or signal_score < 8:
        return None

    provided_evidence = _industrial_provided_evidence(idea)
    constraints = (
        "local-only",
        "no external services",
        "현재는 아이디어 구체화/검증 계획 단계",
        "사용자 제공 설명은 근거 후보이지 최종 proof가 아님",
        "실제 장비 로그/PLC 데이터/생산 telemetry 없음",
        "기술 가능성과 사업성을 분리해서 평가해야 함",
        "bench/log/operator validation 없이 시뮬레이션 정확도를 가정하지 않음",
    )
    return IdeaRefinement(
        goal=(
            "제조장비 셋업/장애분석 시뮬레이션이 실행 가능한 MVP가 될 수 있는지 "
            "평가하고, 기술 가능성과 사업성을 분리해서 다음 검증 단계를 정한다."
        ),
        context=(
            "사용자는 SI/제조 현장의 장비 셋업, 장시간 가동 확인, 가동 중 문제 "
            "발생 시 장비 정지와 원인 파악이 필요한 상황을 설명했다. report는 "
            "시뮬레이션 기반 사전 검증, 기술 가능성, 작업자 workflow, 장비 안전, "
            "사업 검증을 분리해서 다뤄야 한다."
        ),
        constraints=constraints,
        provided_evidence=provided_evidence,
        recommended_profile=INDUSTRIAL_AUTOMATION_PROFILE,
        alternative_profiles=INDUSTRIAL_AUTOMATION_ALTERNATIVES,
        profile_confidence="medium",
        profile_rationale=(
            "industrial automation/manufacturing-equipment 신호가 감지됐지만 현재 "
            "profile registry에는 전용 industrial_automation profile이 없으므로 "
            "가장 가까운 기존 profile인 hardware_device를 추천한다."
        ),
    )


def _generic_refinement(idea: str) -> IdeaRefinement:
    selection = resolve_domain_profile(
        {
            "raw_idea": idea,
            "goal": DEFAULT_GOAL,
            "context": DEFAULT_CONTEXT,
        }
    )
    selected_profile_id = selection.selected_profile.id
    recommended_profile = selected_profile_id
    audit_compliance_matched = _matches_signal_group(idea, AUDIT_COMPLIANCE_SIGNALS)
    hardware_sensor_matched = _matches_signal_group(idea, HARDWARE_SENSOR_SIGNALS)
    consumer_app_matched = _matches_signal_group(idea, CONSUMER_APP_SIGNALS)
    if audit_compliance_matched:
        recommended_profile = "enterprise_b2b"
    elif hardware_sensor_matched:
        recommended_profile = "hardware_device"
    elif consumer_app_matched:
        recommended_profile = "consumer_app"
    alternative_profiles = _top_alternative_profiles(
        selection.score_by_profile,
        recommended_profile,
    )
    profile_confidence = _profile_confidence(
        score_by_profile=selection.score_by_profile,
        recommended_profile=recommended_profile,
        selected_by=selection.selected_by,
    )
    if audit_compliance_matched and recommended_profile != selected_profile_id:
        profile_confidence = "medium"
    elif (
        (hardware_sensor_matched or consumer_app_matched)
        and recommended_profile != selected_profile_id
    ):
        profile_confidence = "medium"
    elif recommended_profile == "ai_saas" and _matches_domain_specific_constraint_group(idea):
        profile_confidence = "low"
    return IdeaRefinement(
        goal=_goal_for_recommended_profile(recommended_profile),
        context=_generic_context(idea),
        constraints=_generic_constraints_for_idea(idea),
        provided_evidence=(
            f"User-provided raw idea: {_trim_terminal_punctuation(_clip_text(idea, 240))}.",
        ),
        recommended_profile=recommended_profile,
        alternative_profiles=alternative_profiles,
        profile_confidence=profile_confidence,
        profile_rationale=_generic_profile_rationale(
            selected_profile_id=selected_profile_id,
            recommended_profile=recommended_profile,
            selected_by=selection.selected_by,
            audit_compliance_matched=audit_compliance_matched,
            hardware_sensor_matched=hardware_sensor_matched,
            consumer_app_matched=consumer_app_matched,
        ),
    )


def _goal_for_recommended_profile(profile_id: str) -> str:
    if profile_id == "ai_saas":
        return (
            "Evaluate whether this software workflow idea can become a viable MVP, "
            "including buyer urgency, repeat usage, differentiation, and reliability risks."
        )
    if profile_id == "developer_tool":
        return (
            "Evaluate whether this developer workflow tool can become a viable MVP, "
            "including setup, integration, time-to-value, and repeat-use risks."
        )
    if profile_id == "enterprise_b2b":
        return (
            "Evaluate whether this enterprise workflow idea can become a viable MVP, "
            "including buyer, procurement, rollout, security, and ROI risks."
        )
    if profile_id == "hardware_device":
        return (
            "Evaluate whether this hardware or field-operation idea can become a "
            "viable MVP, including technical feasibility, safety, deployment, and "
            "operator workflow risks."
        )
    if profile_id == "consumer_app":
        return (
            "Evaluate whether this consumer app idea can become a viable MVP, including "
            "target user need, retention loop, social or habit behavior, privacy, and "
            "monetization risks."
        )
    return DEFAULT_GOAL


def _generic_context(idea: str) -> str:
    clipped_idea = _trim_terminal_punctuation(_clip_text(idea, 240))
    return (
        f"Raw idea for local Research Council refinement: {clipped_idea}. "
        "The report should distinguish assumptions, missing evidence, risks, and "
        "minimum viable experiments from validated proof."
    )


def _generic_constraints_for_idea(idea: str) -> tuple[str, ...]:
    constraints: list[str] = list(REFINEMENT_BASE_CONSTRAINTS)
    if _matches_signal_group(idea, HEALTHCARE_SIGNALS):
        constraints.extend(HEALTHCARE_CONSTRAINTS)
    if _matches_signal_group(idea, EDUCATION_SIGNALS):
        constraints.extend(_education_constraints_for_idea(idea))
    if _matches_signal_group(idea, FINTECH_SIGNALS):
        constraints.extend(FINTECH_CONSTRAINTS)
    if _matches_signal_group(idea, LOGISTICS_SIGNALS):
        constraints.extend(LOGISTICS_CONSTRAINTS)
    if _matches_signal_group(idea, AUDIT_COMPLIANCE_SIGNALS):
        constraints.extend(AUDIT_COMPLIANCE_CONSTRAINTS)
    if _matches_signal_group(idea, HARDWARE_SENSOR_SIGNALS):
        constraints.extend(COLD_CHAIN_SENSOR_CONSTRAINTS)
    return _unique_ordered(constraints)


def _education_constraints_for_idea(idea: str) -> tuple[str, ...]:
    if _any_signal_matches(idea, ADULT_LEARNING_SIGNALS) and not _any_signal_matches(
        idea,
        MINOR_EDUCATION_CONTEXT_SIGNALS,
    ):
        return ADULT_EDUCATION_CONSTRAINTS
    return EDUCATION_CONSTRAINTS


def _matches_domain_specific_constraint_group(idea: str) -> bool:
    return any(
        _matches_signal_group(idea, signals)
        for signals in (
            HEALTHCARE_SIGNALS,
            EDUCATION_SIGNALS,
            FINTECH_SIGNALS,
            LOGISTICS_SIGNALS,
            HARDWARE_SENSOR_SIGNALS,
        )
    )


def _generic_profile_rationale(
    *,
    selected_profile_id: str,
    recommended_profile: str,
    selected_by: str,
    audit_compliance_matched: bool,
    hardware_sensor_matched: bool,
    consumer_app_matched: bool,
) -> str:
    if audit_compliance_matched and recommended_profile != selected_profile_id:
        return (
            f"Existing deterministic profile scoring selected {selected_profile_id} "
            f"by {selected_by}, but audit/control/compliance signals were found, so "
            "the launcher recommends enterprise_b2b as the editable GUI profile."
        )
    if hardware_sensor_matched and recommended_profile != selected_profile_id:
        return (
            f"Existing deterministic profile scoring selected {selected_profile_id} "
            f"by {selected_by}, but hardware/sensor signals were found, so the "
            "launcher recommends hardware_device as the editable GUI profile."
        )
    if consumer_app_matched and recommended_profile != selected_profile_id:
        return (
            f"Existing deterministic profile scoring selected {selected_profile_id} "
            f"by {selected_by}, but consumer app signals were found, so the "
            "launcher recommends consumer_app as the editable GUI profile."
        )
    return (
        f"Existing deterministic profile scoring selected {recommended_profile} "
        f"by {selected_by}."
    )


def _top_alternative_profiles(
    score_by_profile: dict[str, int],
    recommended_profile: str,
    *,
    limit: int = 3,
) -> tuple[str, ...]:
    ranked = tuple(
        profile_id
        for profile_id, score in sorted(
            score_by_profile.items(),
            key=lambda item: (-item[1], item[0]),
        )
        if profile_id != recommended_profile and score > 0
    )
    if len(ranked) >= limit:
        return ranked[:limit]

    fallbacks = (
        "ai_saas",
        "developer_tool",
        "enterprise_b2b",
        "hardware_device",
        "general",
    )
    alternatives = list(ranked)
    for profile_id in fallbacks:
        if profile_id != recommended_profile and profile_id not in alternatives:
            alternatives.append(profile_id)
        if len(alternatives) >= limit:
            break
    return tuple(alternatives)


def _profile_confidence(
    *,
    score_by_profile: dict[str, int],
    recommended_profile: str,
    selected_by: str,
) -> str:
    if selected_by == "fallback":
        return "low"
    selected_score = score_by_profile.get(recommended_profile, 0)
    other_scores = [
        score
        for profile_id, score in score_by_profile.items()
        if profile_id != recommended_profile
    ]
    runner_up = max(other_scores, default=0)
    if selected_score >= 12 and selected_score - runner_up >= 5:
        return "high"
    if selected_score >= 4:
        return "medium"
    return "low"


def _matches_signal_group(
    text: str,
    signals: tuple[tuple[str, int], ...],
    *,
    min_matches: int = 2,
    min_score: int = 6,
) -> bool:
    matched_signals, signal_score = _matched_weighted_signals(text, signals)
    return len(matched_signals) >= min_matches and signal_score >= min_score


def _unique_ordered(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(cleaned)
    return tuple(unique)


def _industrial_provided_evidence(idea: str) -> tuple[str, ...]:
    evidence = ["사용자가 제공한 SI/제조 장비 셋업/운영 문제 설명."]
    if _any_signal_matches(idea, ("setup", "셋업", "장비", "설비")):
        evidence.append(
            "장비 셋업 또는 commissioning 후 현장 검증이 필요하다는 사용자 설명."
        )
    if _any_signal_matches(idea, ("일주일", "대기", "지키", "standby", "wait")):
        evidence.append("장비 옆에서 장시간 가동 상태를 확인해야 한다는 사용자 설명.")
    if _any_signal_matches(idea, ("장애", "고장", "문제", "fault", "failure", "error")):
        evidence.append("가동 중 문제 발생 시 장비를 멈추고 원인을 파악해야 한다는 사용자 설명.")
    if _any_signal_matches(idea, ("시뮬레이션", "simulation", "미리 검증", "pre validation")):
        evidence.append("시뮬레이션으로 사전 검증해보자는 사용자 제안.")
    if len(evidence) == 1:
        evidence.append(f"User-provided raw idea: {_clip_text(idea, 240)}")
    return tuple(evidence)


def _matched_weighted_signals(
    text: str,
    signals: tuple[tuple[str, int], ...],
) -> tuple[tuple[str, ...], int]:
    matches: list[str] = []
    score = 0
    for keyword, weight in signals:
        if keyword in matches:
            continue
        if _keyword_matches(text, keyword):
            matches.append(keyword)
            score += weight
    return tuple(matches), score


def _any_signal_matches(text: str, signals: tuple[str, ...]) -> bool:
    return any(_keyword_matches(text, signal) for signal in signals)


def _keyword_matches(text: str, keyword: str) -> bool:
    normalized_text = _clean_text(text).lower()
    normalized_keyword = _clean_text(keyword).lower()
    if not normalized_keyword:
        return False
    if len(normalized_keyword) == 1 and not normalized_keyword.isascii():
        pattern = r"(?<!\S)" + re.escape(normalized_keyword) + r"(?!\S)"
        return re.search(pattern, normalized_text) is not None
    if re.fullmatch(r"[a-z0-9 ]+", normalized_keyword):
        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(normalized_keyword).replace(r"\ ", r"\s+")
            + r"(?![a-z0-9])"
        )
        return re.search(pattern, normalized_text) is not None
    return normalized_keyword in normalized_text


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clip_text(value: str, limit: int) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _trim_terminal_punctuation(value: str) -> str:
    return _clean_text(value).rstrip(".!?。！？")


def allocate_run_dir(output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_name = f"research-council-{timestamp}"
    for index in range(1000):
        name = base_name if index == 0 else f"{base_name}-{index:03d}"
        candidate = output_root / name
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"could not allocate run directory under {output_root}")


def run_local_research(
    *,
    idea: str,
    goal: str,
    context: str,
    constraints: tuple[str, ...],
    provided_evidence: tuple[str, ...],
    profile: str,
    llm_augmentation_mode: str,
    output_root: Path,
) -> LocalRunArtifacts:
    idea = idea.strip()
    goal = goal.strip()
    context = context.strip()
    profile = profile.strip() or DEFAULT_PROFILE_ID
    llm_augmentation_mode = llm_augmentation_mode.strip() or LLMAugmentationMode.OFF.value
    goal, context, constraints = with_safe_defaults(
        goal=goal,
        context=context,
        constraints=constraints,
    )

    if not idea:
        raise ValueError("Idea is required.")
    if llm_augmentation_mode not in AUGMENTATION_MODE_VALUES:
        raise ValueError(f"Unknown LLM augmentation mode: {llm_augmentation_mode}")

    output_root = normalize_output_root(output_root)
    run_dir = allocate_run_dir(output_root)
    input_json = run_dir / "input.json"
    report_md = run_dir / "report.md"
    result_json = run_dir / "result.json"

    payload = build_input_payload(
        idea=idea,
        goal=goal,
        context=context,
        constraints=constraints,
        provided_evidence=provided_evidence,
    )
    input_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_research_council(
        ResearchCouncilInput(
            raw_idea=idea,
            goal=goal,
            context=context,
            constraints=constraints,
            provided_evidence=provided_evidence,
        ),
        profile=profile,
        llm_advisor_config=llm_augmentation_mode,
    )
    report_md.write_text(result.markdown_report.markdown, encoding="utf-8")
    write_result_json(result, result_json)
    return LocalRunArtifacts(
        run_dir=run_dir,
        input_json=input_json,
        report_md=report_md,
        result_json=result_json,
    )


def open_path(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(path)], check=False)


def launch_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class LocalLauncher:
        def __init__(self, root: tk.Tk) -> None:
            self.root = root
            self.last_artifacts: LocalRunArtifacts | None = None

            root.title(APP_TITLE)
            root.minsize(900, 760)

            self.profile_var = tk.StringVar(value=DEFAULT_PROFILE_ID)
            self.mode_var = tk.StringVar(value=LLMAugmentationMode.OFF.value)
            self.output_dir_var = tk.StringVar(value=str(default_output_root()))
            self.report_path_var = tk.StringVar(value="")
            self.result_path_var = tk.StringVar(value="")
            self.profile_recommendation_var = tk.StringVar(value="")

            self._build_layout(root)

        def _build_layout(self, root: tk.Tk) -> None:
            frame = ttk.Frame(root, padding=16)
            frame.grid(row=0, column=0, sticky="nsew")
            root.columnconfigure(0, weight=1)
            root.rowconfigure(0, weight=1)

            frame.columnconfigure(1, weight=1)
            frame.rowconfigure(4, weight=1)
            frame.rowconfigure(5, weight=1)
            frame.rowconfigure(6, weight=1)
            frame.rowconfigure(7, weight=1)
            frame.rowconfigure(13, weight=1)

            title = ttk.Label(frame, text=APP_TITLE, font=("", 15, "bold"))
            title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
            subtitle = ttk.Label(frame, text=SANDBOX_MESSAGE)
            subtitle.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))
            idea_only_help = ttk.Label(frame, text=IDEA_ONLY_HELP)
            idea_only_help.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 12))

            ttk.Label(frame, text="Idea").grid(row=3, column=0, sticky="nw")
            self.idea_text = self._text_box(frame, row=3, height=4)

            ttk.Label(frame, text="Goal").grid(row=4, column=0, sticky="nw")
            self.goal_text = self._text_box(frame, row=4, height=3)

            ttk.Label(frame, text="Context").grid(row=5, column=0, sticky="nw")
            self.context_text = self._text_box(frame, row=5, height=4)

            ttk.Label(frame, text="Constraints").grid(row=6, column=0, sticky="nw")
            self.constraints_text = self._text_box(frame, row=6, height=4)

            ttk.Label(frame, text="Provided evidence").grid(row=7, column=0, sticky="nw")
            self.evidence_text = self._text_box(frame, row=7, height=4)

            ttk.Label(frame, text="Profile").grid(row=8, column=0, sticky="w", pady=(10, 0))
            profile_box = ttk.Combobox(
                frame,
                textvariable=self.profile_var,
                values=profile_ids(),
                state="readonly",
            )
            profile_box.grid(row=8, column=1, sticky="ew", pady=(10, 0))

            ttk.Label(frame, text="Profile recommendation").grid(
                row=9,
                column=0,
                sticky="w",
                pady=(8, 0),
            )
            ttk.Entry(
                frame,
                textvariable=self.profile_recommendation_var,
                state="readonly",
            ).grid(row=9, column=1, columnspan=2, sticky="ew", pady=(8, 0))

            ttk.Label(frame, text="LLM augmentation mode").grid(
                row=10,
                column=0,
                sticky="w",
                pady=(8, 0),
            )
            mode_box = ttk.Combobox(
                frame,
                textvariable=self.mode_var,
                values=AUGMENTATION_MODE_VALUES,
                state="readonly",
            )
            mode_box.grid(row=10, column=1, sticky="ew", pady=(8, 0))
            ttk.Label(frame, text=SANDBOX_MESSAGE).grid(
                row=10,
                column=2,
                sticky="w",
                padx=(8, 0),
                pady=(8, 0),
            )

            ttk.Label(frame, text="Output directory").grid(
                row=11,
                column=0,
                sticky="w",
                pady=(8, 0),
            )
            output_entry = ttk.Entry(frame, textvariable=self.output_dir_var)
            output_entry.grid(row=11, column=1, sticky="ew", pady=(8, 0))
            ttk.Button(frame, text="Choose...", command=self.choose_output_dir).grid(
                row=11,
                column=2,
                sticky="ew",
                padx=(8, 0),
                pady=(8, 0),
            )

            buttons = ttk.Frame(frame)
            buttons.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(12, 8))
            buttons.columnconfigure(4, weight=1)
            self.refine_button = ttk.Button(
                buttons,
                text="Idea 구체화",
                command=self.refine_idea,
            )
            self.refine_button.grid(row=0, column=0, sticky="w")
            self.run_button = ttk.Button(buttons, text="Run", command=self.run)
            self.run_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
            self.open_folder_button = ttk.Button(
                buttons,
                text="Open output folder",
                command=self.open_output_folder,
                state="disabled",
            )
            self.open_folder_button.grid(row=0, column=2, sticky="w", padx=(8, 0))
            self.open_report_button = ttk.Button(
                buttons,
                text="Open report",
                command=self.open_report,
                state="disabled",
            )
            self.open_report_button.grid(row=0, column=3, sticky="w", padx=(8, 0))

            ttk.Label(frame, text="Status / output log").grid(row=13, column=0, sticky="nw")
            log_frame = ttk.Frame(frame)
            log_frame.grid(row=13, column=1, columnspan=2, sticky="nsew")
            log_frame.columnconfigure(0, weight=1)
            log_frame.rowconfigure(0, weight=1)
            self.log_text = tk.Text(log_frame, height=8, wrap="word", state="disabled")
            self.log_text.grid(row=0, column=0, sticky="nsew")
            log_scroll = ttk.Scrollbar(
                log_frame,
                orient="vertical",
                command=self.log_text.yview,
            )
            log_scroll.grid(row=0, column=1, sticky="ns")
            self.log_text.configure(yscrollcommand=log_scroll.set)

            ttk.Label(frame, text="report.md").grid(row=14, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(
                frame,
                textvariable=self.report_path_var,
                state="readonly",
            ).grid(row=14, column=1, columnspan=2, sticky="ew", pady=(8, 0))
            ttk.Label(frame, text="result.json").grid(row=15, column=0, sticky="w", pady=(4, 0))
            ttk.Entry(
                frame,
                textvariable=self.result_path_var,
                state="readonly",
            ).grid(row=15, column=1, columnspan=2, sticky="ew", pady=(4, 0))

        def _text_box(self, parent: ttk.Frame, *, row: int, height: int) -> tk.Text:
            box = tk.Text(parent, height=height, wrap="word")
            box.grid(row=row, column=1, columnspan=2, sticky="nsew", pady=(0, 8))
            return box

        def choose_output_dir(self) -> None:
            selected = filedialog.askdirectory(
                initialdir=self.output_dir_var.get() or str(Path.home())
            )
            if selected:
                self.output_dir_var.set(selected)

        def refine_idea(self) -> None:
            try:
                refinement = refine_idea_for_launcher(self.idea_text.get("1.0", "end"))
            except Exception as exc:
                self.append_log(f"Idea refinement failed: {exc}")
                messagebox.showerror(APP_TITLE, str(exc))
                return

            self._replace_text(self.goal_text, refinement.goal)
            self._replace_text(self.context_text, refinement.context)
            self._replace_text(self.constraints_text, "\n".join(refinement.constraints))
            self._replace_text(
                self.evidence_text,
                "\n".join(refinement.provided_evidence),
            )
            self.profile_var.set(refinement.recommended_profile)
            recommendation = format_profile_recommendation(refinement)
            self.profile_recommendation_var.set(recommendation)
            self.append_log("Refined idea locally. Review or edit fields before Run.")
            self.append_log(f"Profile recommendation: {recommendation}")
            self.append_log(f"Rationale: {refinement.profile_rationale}")

        def _replace_text(self, box: tk.Text, value: str) -> None:
            box.delete("1.0", "end")
            box.insert("1.0", value)

        def run(self) -> None:
            self.run_button.configure(state="disabled")
            self.refine_button.configure(state="disabled")
            self.open_folder_button.configure(state="disabled")
            self.open_report_button.configure(state="disabled")
            self.report_path_var.set("")
            self.result_path_var.set("")
            self.append_log("Running deterministic Research Council pass...")
            self.root.update_idletasks()
            try:
                artifacts = run_local_research(
                    idea=self.idea_text.get("1.0", "end"),
                    goal=self.goal_text.get("1.0", "end"),
                    context=self.context_text.get("1.0", "end"),
                    constraints=split_lines(self.constraints_text.get("1.0", "end")),
                    provided_evidence=split_lines(self.evidence_text.get("1.0", "end")),
                    profile=self.profile_var.get(),
                    llm_augmentation_mode=self.mode_var.get(),
                    output_root=Path(self.output_dir_var.get()),
                )
            except Exception as exc:
                self.append_log(f"Run failed: {exc}")
                messagebox.showerror(APP_TITLE, str(exc))
            else:
                self.last_artifacts = artifacts
                self.report_path_var.set(str(artifacts.report_md))
                self.result_path_var.set(str(artifacts.result_json))
                self.open_folder_button.configure(state="normal")
                self.open_report_button.configure(state="normal")
                self.append_log(f"Created input.json: {artifacts.input_json}")
                self.append_log(f"Created report.md: {artifacts.report_md}")
                self.append_log(f"Created result.json: {artifacts.result_json}")
            finally:
                self.run_button.configure(state="normal")
                self.refine_button.configure(state="normal")

        def append_log(self, message: str) -> None:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        def open_output_folder(self) -> None:
            if self.last_artifacts is not None:
                self._open(self.last_artifacts.run_dir)

        def open_report(self) -> None:
            if self.last_artifacts is not None:
                self._open(self.last_artifacts.report_md)

        def _open(self, path: Path) -> None:
            try:
                open_path(path)
            except Exception as exc:
                messagebox.showerror(APP_TITLE, str(exc))

    root = tk.Tk()
    LocalLauncher(root)
    root.mainloop()


def run_self_test(output_dir: Path) -> LocalRunArtifacts:
    artifacts = run_local_research(
        idea="CareNote assistant for family caregivers",
        goal="",
        context="",
        constraints=(),
        provided_evidence=(),
        profile=DEFAULT_PROFILE_ID,
        llm_augmentation_mode=LLMAugmentationMode.OFF.value,
        output_root=output_dir,
    )
    for path in (artifacts.input_json, artifacts.report_md, artifacts.result_json):
        if not path.exists():
            raise RuntimeError(f"self-test did not create {path}")
    if not artifacts.report_md.read_text(encoding="utf-8").startswith(
        "# Research Council Report"
    ):
        raise RuntimeError("self-test report.md did not contain a report")

    input_payload = json.loads(artifacts.input_json.read_text(encoding="utf-8"))
    if input_payload["goal"] != DEFAULT_GOAL:
        raise RuntimeError("self-test input.json did not include the default goal")
    if input_payload["context"] != DEFAULT_CONTEXT:
        raise RuntimeError("self-test input.json did not include the default context")
    if input_payload["constraints"] != list(DEFAULT_CONSTRAINTS):
        raise RuntimeError("self-test input.json did not include default constraints")
    if input_payload["provided_evidence"] != []:
        raise RuntimeError("self-test input.json should allow empty provided evidence")

    report_text = artifacts.report_md.read_text(encoding="utf-8")
    if "Missing evidence entries" not in report_text:
        raise RuntimeError("self-test report.md did not show missing evidence")

    result_payload = json.loads(artifacts.result_json.read_text(encoding="utf-8"))
    if result_payload["profile"]["profile_id"] != DEFAULT_PROFILE_ID:
        raise RuntimeError("self-test result.json did not preserve the selected profile")
    return artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Open the local Research Council Tk launcher, or run a headless "
            "self-test that writes input.json, report.md, and result.json."
        )
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run a headless launcher smoke test instead of opening the GUI.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_root(),
        help="Output root for GUI runs or --self-test runs.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        artifacts = run_self_test(args.output_dir)
        print("Research Council local launcher self-test passed")
        print(f"Run folder: {artifacts.run_dir}")
        print(f"Report: {artifacts.report_md}")
        print(f"Result JSON: {artifacts.result_json}")
        return 0

    launch_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
