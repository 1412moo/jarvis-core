"""Lead stage v0.1 (task-0183): a read-only Claude team lead in front of the Worker pipeline.

For a /work request that names no work kind, the lead reads the repository and answers with a
small plan: which registered work kind fits (or none), a task title, the steps, a risk level,
whether an Owner decision is needed, and a one-line instruction for the Worker.

The lead never changes anything. It runs the same `claude` CLI the Worker uses, from the
repository root, with only Read, Grep and Glob, in plan permission mode, under a time limit.
It takes no Worker lock. Its answer is untrusted data: anything outside the fixed fields fails
closed, and nothing here creates a task or starts a run. The bot does that, and a run still
starts only with the Owner's /go.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_worker  # noqa: E402

LEAD_TIMEOUT_SECONDS = 300
LEAD_ALLOWED_TOOLS = "Read,Grep,Glob"
LEAD_DISALLOWED_TOOLS = "Edit,Write,NotebookEdit,Bash,WebFetch,WebSearch"
LEAD_RISKS = ("low", "medium", "high")
LEAD_MAX_STEPS = 7
LEAD_MAX_TITLE_CHARS = 100
LEAD_MAX_LINE_CHARS = 300
FIELD_PATTERN = re.compile(r"^(kind|title|risk|owner_decision|worker_request):[ \t]*(.*)$")
STEP_PATTERN = re.compile(r"^-[ \t]+(.+)$")

# One lead at a time in this process; a second request is refused rather than queued.
_LEAD_LOCK = threading.Lock()


@dataclass
class LeadPlan:
    kind: str | None
    title: str
    steps: list[str] = field(default_factory=list)
    risk: str = ""
    owner_decision: str | None = None
    worker_request: str = ""


@dataclass
class LeadResult:
    ok: bool
    reason: str = ""
    plan: LeadPlan | None = None
    raw_excerpt: str = ""


def lead_prompt(request: str) -> str:
    kinds = "\n".join(
        f"- {kind.name}: may change only files under {kind.allowed_prefix} (tests: {kind.test_script})"
        for kind in claude_worker.WORK_KINDS
    )
    return (
        "You are the Jarvis-Core team lead. You plan; you never change anything.\n"
        f"Owner request (verbatim): {request}\n\n"
        "Read the repository as needed (Read, Grep, Glob only) and decide how the Worker team should handle "
        "the request. The Worker can only run one of these registered work kinds:\n"
        f"{kinds}\n\n"
        "Rules:\n"
        "- Pick a kind only if the whole request can be done by changing files under that kind's path. "
        "Otherwise answer kind: none and say why in owner_decision.\n"
        "- Never read or open jarvis.bat or any .env file.\n"
        "- Task records under memory/tasks and design documents are history, not current rules.\n"
        "- owner_decision is none unless the Owner must decide something first (cost, external service, "
        "security, deleting data, a path outside the kind, or an unclear request); then give the reason.\n"
        "- worker_request is one line suggesting what the Worker should change. The Owner sees it; the Worker "
        "gets the Owner request itself.\n\n"
        "Answer with exactly this block and nothing else (no backticks):\n"
        "kind: <one of the kind names above, or none>\n"
        "title: <one line, at most 100 characters>\n"
        "steps:\n"
        "- <step>\n"
        "- <step>\n"
        "risk: <low|medium|high>\n"
        "owner_decision: <none, or the reason the Owner must decide>\n"
        "worker_request: <one line>\n"
    )


def _clean_line(value: str, max_chars: int) -> str | None:
    value = " ".join(value.split())
    if not value or len(value) > max_chars or "`" in value:
        return None
    return value


def parse_lead_answer(text: str) -> tuple[LeadPlan | None, str]:
    """Return (plan, "") or (None, reason). Any deviation from the block fails closed."""

    lines = [line.rstrip() for line in text.strip().splitlines() if line.strip()]
    fields: dict[str, str] = {}
    steps: list[str] = []
    in_steps = False
    for line in lines:
        if line.strip() == "steps:":
            if in_steps or steps or "steps" in fields:
                return None, "lead_answer_malformed:steps"
            in_steps = True
            fields["steps"] = ""
            continue
        step = STEP_PATTERN.match(line.strip())
        if in_steps and step:
            steps.append(step.group(1))
            continue
        matched = FIELD_PATTERN.match(line.strip())
        if matched is None:
            return None, "lead_answer_malformed:unexpected_line"
        in_steps = False
        name, value = matched.groups()
        if name in fields:
            return None, f"lead_answer_malformed:duplicate:{name}"
        fields[name] = value
    for name in ("kind", "title", "steps", "risk", "owner_decision", "worker_request"):
        if name not in fields:
            return None, f"lead_answer_malformed:missing:{name}"
    kind_name = fields["kind"].strip()
    if kind_name != "none" and claude_worker.work_kind_by_name(kind_name) is None:
        return None, "lead_answer_malformed:kind"
    title = _clean_line(fields["title"], LEAD_MAX_TITLE_CHARS)
    worker_request = _clean_line(fields["worker_request"], LEAD_MAX_LINE_CHARS)
    owner_decision = _clean_line(fields["owner_decision"], LEAD_MAX_LINE_CHARS)
    risk = fields["risk"].strip().lower()
    clean_steps = [_clean_line(step, LEAD_MAX_LINE_CHARS) for step in steps]
    if title is None or worker_request is None or owner_decision is None:
        return None, "lead_answer_malformed:text"
    if risk not in LEAD_RISKS:
        return None, "lead_answer_malformed:risk"
    if kind_name == "none" and owner_decision.lower() == "none":
        # A plan the Worker cannot take must say why, for the Owner.
        return None, "lead_answer_malformed:reason"
    if not clean_steps or len(clean_steps) > LEAD_MAX_STEPS or None in clean_steps:
        return None, "lead_answer_malformed:steps"
    return (
        LeadPlan(
            kind=None if kind_name == "none" else kind_name,
            title=title,
            steps=[step for step in clean_steps if step],
            risk=risk,
            owner_decision=None if owner_decision.lower() == "none" else owner_decision,
            worker_request=worker_request,
        ),
        "",
    )


def _run_claude(prompt: str, repo_root: Path) -> subprocess.CompletedProcess:
    return claude_worker._run(
        [
            *claude_worker._claude_command(),
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            "plan",
            "--allowedTools",
            LEAD_ALLOWED_TOOLS,
            "--disallowedTools",
            LEAD_DISALLOWED_TOOLS,
        ],
        cwd=repo_root,
        timeout=LEAD_TIMEOUT_SECONDS,
        stdin_text=prompt,
    )


def run_lead(
    request: str,
    repo_root: Path | None = None,
    runner: Callable[[str, Path], subprocess.CompletedProcess] | None = None,
) -> LeadResult:
    """Ask the lead once. Never raises; every failure is a LeadResult with ok False."""

    if not _LEAD_LOCK.acquire(blocking=False):
        return LeadResult(False, "lead_busy")
    try:
        try:
            completed = (runner or _run_claude)(lead_prompt(request), repo_root or claude_worker.REPO_ROOT)
        except subprocess.TimeoutExpired:
            return LeadResult(False, "lead_timeout")
        except claude_worker.StageFailure as exc:
            return LeadResult(False, f"lead_failed:{exc.reason}")
        except Exception as exc:  # noqa: BLE001 - the lead never takes the bot down
            return LeadResult(False, f"lead_failed:{type(exc).__name__}")
        if completed.returncode != 0:
            return LeadResult(False, "lead_failed:exit", raw_excerpt=(completed.stderr or completed.stdout)[:300])
        text = completed.stdout
        try:
            text = str(json.loads(completed.stdout).get("result", completed.stdout))
        except (json.JSONDecodeError, AttributeError):
            pass
        plan, reason = parse_lead_answer(text)
        if plan is None:
            return LeadResult(False, reason, raw_excerpt=" ".join(text.split())[:300])
        return LeadResult(True, plan=plan)
    finally:
        _LEAD_LOCK.release()


def task_title_for(plan: LeadPlan) -> str | None:
    """The TODO task title for a plan with a registered kind: the kind's first marker, then the lead's
    title, so /go settles the same kind from it. None when the plan has no kind, or when the title
    would settle another kind."""

    if plan.kind is None:
        return None
    kind = claude_worker.work_kind_by_name(plan.kind)
    if kind is None:
        return None
    title = f"{kind.markers[0]}: {plan.title}"
    if claude_worker.select_work_kind(title) is not kind:
        return None
    return title[:120].rstrip()
