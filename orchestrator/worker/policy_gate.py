"""Policy Gate v0 (task-0225): a deterministic verdict for each sub-task of a goal plan.

Each sub-task gets one of three verdicts:
- auto: nothing in the sub-task needs the Owner under the rules below. In this stage it is a label
  only. Nothing runs automatically, and the label grants no permission (SOP section 9 and the
  master-plan's locked features still apply; turning it into a permission is an Owner decision).
- needs_owner: the Owner must decide before the sub-task could start.
- forbidden: the Worker pipeline must never do it. These are the pipeline's existing hard refusals:
  a protected path, an .env file, git internals, or a path outside the repository.

The lead's own words count only in one direction. Its risk "high" and its owner_decision can make a
verdict stricter; nothing the lead says can make one looser. The text checks are fixed lists. They are
deliberately broad (a false needs_owner costs the Owner one look; a false auto would skip the Owner),
and they are not the safety boundary of a later run. The pipeline's scope check, protected paths,
forbidden additions, Reviewer and QA stay the boundary when anything runs.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_worker  # noqa: E402
from goal_plan import GoalPlan, GoalTask  # noqa: E402

POLICY_VERSION = "policy-gate-v0-dry-run"
AUTO = "auto"
NEEDS_OWNER = "needs_owner"
FORBIDDEN = "forbidden"
VERDICT_RANK = {AUTO: 0, NEEDS_OWNER: 1, FORBIDDEN: 2}

# task-0227 repair 4 (Owner decision): a URL to a host other than this machine is always a signal,
# whatever words are around it; a URL to this machine (localhost, 127.0.0.1, [::1]) is not. Repairs 1 to 3
# tried to guess a call from the words next to the URL and each left a new gap, so that guess is gone.
_EXTERNAL_URL = r"https?://(?!(?:localhost|127\.0\.0\.1|\[::1\])(?![\w.\-]))"

# Text signals that always need the Owner, by category. Each entry is a regular expression searched in
# the lower-cased text with whitespace runs folded. English words use ASCII word boundaries; Korean
# words are searched as substrings.
OWNER_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("external_publication", (
        r"\bpush\b", r"\bpull request\b", r"\bpr\b", r"\bdeploy", r"\bpublish", r"\brelease\b", r"\bupload",
        r"배포", r"공개", r"게시", r"업로드", r"푸시", r"외부 전송", r"이메일", r"\bemail\b", r"\bpost to\b",
    )),
    ("data_deletion", (
        r"\bdelete", r"\bremove", r"\brm\b", r"\bdrop\b", r"\bpurge", r"\bwipe", r"\btruncate",
        r"\breset --hard\b", r"삭제", r"제거", r"지우", r"폐기", r"초기화",
    )),
    ("cost", (
        r"\bcost", r"\bbilling\b", r"\bpaid\b", r"\bpayment", r"\bpurchase", r"\bsubscription",
        r"비용", r"결제", r"유료", r"구매", r"구독", r"요금",
    )),
    # task-0227: a path alone is not a call. "api" that is part of a path or file name (/api/, api/,
    # api.py), an http(s) URL scheme and the local module name http.server are not signals; the word
    # "api", words that start with "http" (HTTP, httpx, http_client) and any URL to a host other than this
    # machine still are (repair 4).
    ("external_service", (
        r"(?<![/.])\bapi\b(?!/|\.\w)", r"\bhttp(?!s?://|\.server\b)",
        _EXTERNAL_URL,
        r"\bnetwork", r"\bwebhook", r"\bcrawl", r"\bscrap", r"\bllm\b", r"\bopenrouter\b",
        r"\bopenai\b", r"\bgemini\b", r"\bgpt", r"\bollama\b", r"\bdiscord api\b",
        r"외부 서비스", r"외부 api", r"네트워크", r"크롤", r"스크래핑",
    )),
    ("security_or_permission", (
        r"\bpermission", r"\bchmod\b", r"\bicacls\b", r"\bacl\b", r"\bcredential", r"\bpassword", r"\btoken",
        r"\bsecret", r"\bapi key", r"\bapi_key\b", r"\bowner id", r"\ballowlist\b",
        r"권한", r"보안", r"비밀번호", r"토큰", r"자격 증명", r"자격증명", r"인증", r"api 키",
    )),
    ("install_or_dependency", (
        r"\binstall", r"\bpip\b", r"\bnpm\b", r"\bdependenc", r"\bdownload",
        r"설치", r"의존성", r"다운로드", r"패키지 추가",
    )),
    ("automation_or_schedule", (
        r"\bschedul", r"\bcron\b", r"\bbackground\b", r"\bdaemon\b", r"\bdispatcher\b", r"\bqueue\b",
        r"스케줄", r"백그라운드", r"자동 실행", r"예약 실행", r"상시 실행",
    )),
)
# re.ASCII: a word boundary is judged on ASCII letters only, so "PR이" still holds the word "pr".
_COMPILED_SIGNALS = tuple((category, tuple(re.compile(pattern, re.ASCII) for pattern in patterns))
                          for category, patterns in OWNER_SIGNALS)


@dataclass
class TaskVerdict:
    task_id: str
    verdict: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class GoalVerdict:
    policy_version: str
    tasks: list[TaskVerdict]
    goal_signals: list[str] = field(default_factory=list)

    def of(self, task_id: str) -> TaskVerdict | None:
        return next((item for item in self.tasks if item.task_id == task_id), None)

    def counts(self) -> dict[str, int]:
        counts = {AUTO: 0, NEEDS_OWNER: 0, FORBIDDEN: 0}
        for item in self.tasks:
            counts[item.verdict] += 1
        return counts

    def overall(self) -> str:
        return max((item.verdict for item in self.tasks), key=VERDICT_RANK.__getitem__, default=NEEDS_OWNER)

    def to_dict(self) -> dict:
        return {
            "policy_version": self.policy_version,
            "overall": self.overall(),
            "counts": self.counts(),
            "goal_signals": list(self.goal_signals),
            "tasks": [{"task_id": item.task_id, "verdict": item.verdict, "reasons": list(item.reasons)}
                      for item in self.tasks],
        }


def text_signals(text: str) -> list[str]:
    """The categories whose signals appear in the text, in the fixed category order."""

    folded = " ".join(text.lower().split())
    return [category for category, patterns in _COMPILED_SIGNALS if any(p.search(folded) for p in patterns)]


def _is_protected(path: str) -> bool:
    """A pipeline-protected file itself, any jarvis.bat or .env file, or git internals. A folder that
    merely holds a protected file (apps/studyroom/ holds studyroom.bat) is not: the pipeline's scope
    check still refuses a change to that one file when anything runs."""

    # task-0225 repair 1: compared case-folded, since Windows names a protected file in any letter case.
    parts = PurePosixPath(path.rstrip("/").lower()).parts
    if not parts:
        return False
    if any(part == ".git" or part.startswith(".env") for part in parts):
        return True
    if parts[-1] == "jarvis.bat":
        return True
    return "/".join(parts) in {protected.lower() for protected in claude_worker.PROTECTED_PATHS}


def _outside_repository(path: str) -> bool:
    pure = PurePosixPath(path)
    return (path.startswith("/") or bool(re.match(r"^[a-zA-Z]:", path)) or path.startswith("~")
            or ".." in pure.parts)


def _is_pattern(path: str) -> bool:
    return any(char in path for char in "*?[]")


def _within(path: str, prefix: str) -> bool:
    return path == prefix.rstrip("/") or path.startswith(prefix)


def judge_task(task: GoalTask) -> TaskVerdict:
    """The sub-task's own verdict, before its prerequisites are considered."""

    forbidden: list[str] = []
    owner: list[str] = []
    for path in task.paths:
        if _outside_repository(path):
            forbidden.append(f"path_outside_repository:{path}")
        elif _is_protected(path):
            forbidden.append(f"protected_path:{path}")
        elif _is_pattern(path):
            # A wildcard cannot be checked against the kind's path; the Owner looks at it.
            owner.append(f"path_pattern:{path}")
    kind = claude_worker.work_kind_by_name(task.kind) if task.kind else None
    if kind is None:
        # task-0226: no registered Worker kind can take it, read-only or not, so the Owner decides who
        # does it. A missing lead reason is named too, so the Owner knows the lead gave none.
        owner.append("no_registered_kind")
        if not task.owner_decision:
            owner.append("lead_reason_missing")
    if task.mode == "edit":
        if not task.paths:
            owner.append("paths_missing")
        elif kind is not None:
            for path in task.paths:
                if not _within(path, kind.allowed_prefix) and not _outside_repository(path):
                    owner.append(f"path_outside_kind:{path}")
    text = " ".join([task.title, task.purpose, task.worker_request, *task.acceptance])
    owner.extend(f"signal:{category}" for category in text_signals(text))
    if task.owner_decision:
        owner.append("lead_owner_decision")
    if task.risk == "high":
        owner.append("lead_risk_high")
    if forbidden:
        return TaskVerdict(task.id, FORBIDDEN, forbidden + owner)
    if owner:
        return TaskVerdict(task.id, NEEDS_OWNER, owner)
    return TaskVerdict(task.id, AUTO, [])


def judge_plan(plan: GoalPlan, goal_text: str = "") -> GoalVerdict:
    """Every sub-task's verdict, in plan order. A sub-task whose prerequisite is not auto needs the
    Owner too, because it cannot start before that prerequisite is settled."""

    verdicts: dict[str, TaskVerdict] = {}
    for task_id in plan.order:
        task = plan.task(task_id)
        verdict = judge_task(task)
        for dep in task.depends_on:
            dep_verdict = verdicts[dep].verdict
            if dep_verdict != AUTO:
                verdict.reasons.append(f"depends_on_{dep_verdict}:{dep}")
                if verdict.verdict == AUTO:
                    verdict.verdict = NEEDS_OWNER
        verdicts[task_id] = verdict
    return GoalVerdict(
        policy_version=POLICY_VERSION,
        tasks=[verdicts[task_id] for task_id in plan.order],
        goal_signals=text_signals(goal_text),
    )


# Korean labels for the reason codes shown to the Owner. Unknown codes are shown as they are.
REASON_LABELS = {
    "no_registered_kind": "등록된 작업 종류 밖",
    "lead_reason_missing": "팀장이 Owner 결정 사유를 적지 않음",
    "paths_missing": "변경 경로 없음",
    "path_outside_kind": "작업 종류 허용 경로 밖",
    "path_outside_repository": "저장소 밖 경로",
    "path_pattern": "와일드카드 경로",
    "protected_path": "보호 경로",
    "lead_owner_decision": "팀장이 Owner 결정 필요로 표시",
    "lead_risk_high": "팀장 위험도 high",
    "depends_on_needs_owner": "선행 작업이 Owner 결정 필요",
    "depends_on_forbidden": "선행 작업이 금지",
    "signal:external_publication": "외부 공개·전송",
    "signal:data_deletion": "삭제·제거",
    "signal:cost": "비용",
    "signal:external_service": "외부 서비스·네트워크",
    "signal:security_or_permission": "보안·권한·자격 증명",
    "signal:install_or_dependency": "설치·의존성",
    "signal:automation_or_schedule": "자동·백그라운드 실행",
}


def reason_label(reason: str) -> str:
    code, _, detail = reason.partition(":") if not reason.startswith("signal:") else (reason, "", "")
    label = REASON_LABELS.get(code, code)
    return f"{label} ({detail})" if detail else label
