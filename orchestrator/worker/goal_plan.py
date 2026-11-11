"""Goal plan v1 (task-0225): the shape of a goal the lead breaks into sub-tasks, and its strict parser.

The Owner gives one goal with /goal. The read-only lead (claude_lead.run_goal_plan) answers with one
JSON object that splits the goal into sub-tasks: each with a registered work kind (or none), a mode
(edit or read_only), a purpose, the repository paths it expects to touch, the sub-tasks it depends on,
acceptance criteria, a risk level, whether the Owner must decide something, and a one-line instruction
for the Worker. This module only checks that answer. It fails closed on any deviation and computes the
execution stages from the dependencies. Nothing here creates a task, assigns a Worker or runs anything.

The plan is the input later stages are meant to reuse (a goal store, a dispatcher, the Worker's
instruction bundle). Its fields are therefore plain data with fixed limits, and plan_digest gives a
stable hash of the checked plan so a later approval can name exactly the plan it approves.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_worker  # noqa: E402

GOAL_PLAN_VERSION = 1
GOAL_MAX_TASKS = 8
GOAL_MAX_ACCEPTANCE = 5
GOAL_MAX_PATHS = 10
GOAL_MAX_TITLE_CHARS = 100
GOAL_MAX_LINE_CHARS = 300
GOAL_MAX_CRITERION_CHARS = 200
GOAL_MAX_PATH_CHARS = 200
GOAL_MAX_SUMMARY_CHARS = 300
GOAL_MAX_FLOW_CHARS = 500
GOAL_MODES = ("edit", "read_only")
GOAL_RISKS = ("low", "medium", "high")
TASK_ID_PATTERN = re.compile(r"^T[1-9][0-9]?$")
PLAN_KEYS = frozenset({"goal_summary", "tasks", "order", "flow"})
TASK_KEYS = frozenset({
    "id", "title", "kind", "mode", "purpose", "paths", "depends_on", "acceptance", "risk",
    "owner_decision", "worker_request",
})


@dataclass
class GoalTask:
    id: str
    title: str
    kind: str | None
    mode: str
    purpose: str
    paths: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    risk: str = ""
    owner_decision: str | None = None
    worker_request: str = ""
    stage: int = 0


@dataclass
class GoalPlan:
    goal_summary: str
    tasks: list[GoalTask]
    order: list[str]
    flow: str
    version: int = GOAL_PLAN_VERSION

    def task(self, task_id: str) -> GoalTask | None:
        return next((task for task in self.tasks if task.id == task_id), None)

    def stages(self) -> list[list[str]]:
        """Sub-task ids grouped by stage, each group in the lead's order. A stage holds the sub-tasks
        whose prerequisites are all in earlier stages; ones in the same stage do not depend on each other."""

        count = max((task.stage for task in self.tasks), default=0)
        return [[task_id for task_id in self.order if self.task(task_id).stage == stage]
                for stage in range(1, count + 1)]

    def to_dict(self) -> dict:
        return asdict(self)


def _line(value: object, max_chars: int, *, allow_backticks: bool = True) -> str | None:
    """One non-empty line within the limit, whitespace runs folded; None for anything else."""

    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    if not value or len(value) > max_chars or (not allow_backticks and "`" in value):
        return None
    return value


def _clean_path(value: object) -> str | None:
    """A repository-relative path as the lead wrote it, with forward slashes. The Policy Gate judges it;
    here it only has to be one short line. Absolute paths and '..' are kept so the gate can refuse them."""

    text = _line(value, GOAL_MAX_PATH_CHARS)
    if text is None or " " in text:
        return None
    return text.replace("\\", "/")


def _strip_fence(text: str) -> str:
    """The answer may come wrapped in one Markdown code fence; only that one wrapper is removed."""

    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```") and stripped.count("```") == 2:
        body = stripped[3:-3]
        first_newline = body.find("\n")
        if first_newline != -1 and body[:first_newline].strip().lower() in ("", "json"):
            body = body[first_newline + 1:]
        return body.strip()
    return stripped


def _stages(tasks: dict[str, GoalTask]) -> bool:
    """Set each sub-task's stage from its prerequisites. False when the dependencies form a cycle."""

    resolved: dict[str, int] = {}
    visiting: set[str] = set()

    def stage_of(task_id: str) -> int | None:
        if task_id in resolved:
            return resolved[task_id]
        if task_id in visiting:
            return None
        visiting.add(task_id)
        depths = [stage_of(dep) for dep in tasks[task_id].depends_on]
        visiting.discard(task_id)
        if any(depth is None for depth in depths):
            return None
        resolved[task_id] = 1 + max(depths, default=0)
        return resolved[task_id]

    for task_id in tasks:
        if stage_of(task_id) is None:
            return False
    for task_id, task in tasks.items():
        task.stage = resolved[task_id]
    return True


def _parse_task(raw: object, kinds: set[str]) -> tuple[GoalTask | None, str]:
    if not isinstance(raw, dict) or set(raw) != TASK_KEYS:
        return None, "task_fields"
    task_id = raw["id"]
    if not isinstance(task_id, str) or not TASK_ID_PATTERN.match(task_id):
        return None, "task_id"
    title = _line(raw["title"], GOAL_MAX_TITLE_CHARS, allow_backticks=False)
    purpose = _line(raw["purpose"], GOAL_MAX_LINE_CHARS)
    worker_request = _line(raw["worker_request"], GOAL_MAX_LINE_CHARS)
    owner_decision = _line(raw["owner_decision"], GOAL_MAX_LINE_CHARS)
    if None in (title, purpose, worker_request, owner_decision):
        return None, f"task_text:{task_id}"
    kind = raw["kind"]
    if not isinstance(kind, str) or (kind != "none" and kind not in kinds):
        return None, f"task_kind:{task_id}"
    mode = raw["mode"]
    if mode not in GOAL_MODES:
        return None, f"task_mode:{task_id}"
    risk = raw["risk"]
    if not isinstance(risk, str) or risk.strip().lower() not in GOAL_RISKS:
        return None, f"task_risk:{task_id}"
    paths_raw, deps_raw, criteria_raw = raw["paths"], raw["depends_on"], raw["acceptance"]
    if not isinstance(paths_raw, list) or len(paths_raw) > GOAL_MAX_PATHS:
        return None, f"task_paths:{task_id}"
    paths = [_clean_path(path) for path in paths_raw]
    if None in paths or len(set(paths)) != len(paths):
        return None, f"task_paths:{task_id}"
    if not isinstance(deps_raw, list) or not all(isinstance(dep, str) for dep in deps_raw) \
            or len(set(deps_raw)) != len(deps_raw):
        return None, f"task_depends_on:{task_id}"
    if not isinstance(criteria_raw, list) or not 1 <= len(criteria_raw) <= GOAL_MAX_ACCEPTANCE:
        return None, f"task_acceptance:{task_id}"
    criteria = [_line(item, GOAL_MAX_CRITERION_CHARS) for item in criteria_raw]
    if None in criteria:
        return None, f"task_acceptance:{task_id}"
    # task-0226: a kind none sub-task whose owner_decision is none is accepted instead of refusing the
    # whole plan; the Policy Gate gives every kind none sub-task needs_owner and names the missing reason.
    return GoalTask(
        id=task_id,
        title=title,
        kind=None if kind == "none" else kind,
        mode=mode,
        purpose=purpose,
        paths=list(paths),
        depends_on=list(deps_raw),
        acceptance=list(criteria),
        risk=risk.strip().lower(),
        owner_decision=None if owner_decision.lower() == "none" else owner_decision,
        worker_request=worker_request,
    ), ""


def parse_goal_answer(text: str) -> tuple[GoalPlan | None, str]:
    """Return (plan, "") or (None, reason). Any deviation from the schema fails closed."""

    try:
        raw = json.loads(_strip_fence(text))
    except (json.JSONDecodeError, TypeError):
        return None, "goal_answer_malformed:json"
    if not isinstance(raw, dict) or set(raw) != PLAN_KEYS:
        return None, "goal_answer_malformed:fields"
    summary = _line(raw["goal_summary"], GOAL_MAX_SUMMARY_CHARS)
    flow = _line(raw["flow"], GOAL_MAX_FLOW_CHARS)
    if summary is None or flow is None:
        return None, "goal_answer_malformed:text"
    raw_tasks = raw["tasks"]
    if not isinstance(raw_tasks, list) or not 1 <= len(raw_tasks) <= GOAL_MAX_TASKS:
        return None, "goal_answer_malformed:tasks"
    kinds = {kind.name for kind in claude_worker.WORK_KINDS}
    tasks: dict[str, GoalTask] = {}
    for item in raw_tasks:
        task, reason = _parse_task(item, kinds)
        if task is None:
            return None, f"goal_answer_malformed:{reason}"
        if task.id in tasks:
            return None, f"goal_answer_malformed:duplicate:{task.id}"
        tasks[task.id] = task
    for task in tasks.values():
        if any(dep not in tasks or dep == task.id for dep in task.depends_on):
            return None, f"goal_answer_malformed:task_depends_on:{task.id}"
    if not _stages(tasks):
        return None, "goal_answer_malformed:cycle"
    order = raw["order"]
    if not isinstance(order, list) or sorted(order, key=str) != sorted(tasks, key=str) or len(order) != len(tasks):
        return None, "goal_answer_malformed:order"
    position = {task_id: index for index, task_id in enumerate(order)}
    if any(position[dep] > position[task.id] for task in tasks.values() for dep in task.depends_on):
        # The expected order must run every prerequisite first.
        return None, "goal_answer_malformed:order_dependency"
    return GoalPlan(goal_summary=summary, tasks=[tasks[task_id] for task_id in order], order=list(order), flow=flow), ""


def plan_digest(plan: GoalPlan) -> str:
    """sha256 of the checked plan in a fixed JSON form, so a later approval can name this exact plan."""

    canonical = json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def goal_prompt(goal: str) -> str:
    kinds = "\n".join(
        f"- {kind.name}: may change only files under {kind.allowed_prefix} (tests: {kind.test_script})"
        for kind in claude_worker.WORK_KINDS
    )
    return (
        "You are the Jarvis-Core team lead. You plan; you never change anything.\n"
        f"Owner goal (verbatim): {goal}\n\n"
        "Read the repository as needed (Read, Grep, Glob only) and break the goal into sub-tasks the Worker "
        "team could do one at a time. The Worker can only run one of these registered work kinds:\n"
        f"{kinds}\n"
        "A sub-task may also be mode read_only: a check and a report that changes no file.\n\n"
        "Rules:\n"
        f"- At most {GOAL_MAX_TASKS} sub-tasks, ids T1, T2, ... Keep each one small enough for one Worker run.\n"
        "- Give a sub-task a kind only if all of its changes stay under that kind's path; otherwise kind none, "
        "and say why in owner_decision. This holds for read_only sub-tasks too: a kind none sub-task never "
        "has owner_decision none.\n"
        "- paths lists the repository-relative files or folders (folders end with /) the sub-task expects to "
        "change; for read_only, the ones it reads. Never list jarvis.bat or any .env file.\n"
        "- depends_on lists the ids that must finish first. order is every id once, prerequisites first.\n"
        f"- acceptance holds 1 to {GOAL_MAX_ACCEPTANCE} checkable completion criteria.\n"
        "- owner_decision is none unless the Owner must decide something first (cost, an external service or "
        "publication, deleting data, security or permissions, a path outside the kind, or an unclear goal); "
        "then give the reason.\n"
        "- worker_request is one line telling the Worker what to change for this sub-task.\n"
        # task-0227: the first live plans mixed English and Korean; every text the Owner reads is Korean.
        "- Write every text value the Owner reads in natural Korean: goal_summary, flow, and each sub-task's "
        "title, purpose, acceptance, owner_decision and worker_request. Keep code identifiers, file paths, "
        "API paths and proper names in their original form where needed. id, kind, mode, risk and paths "
        "stay exactly as the shape below says.\n"
        "- Never read or open jarvis.bat or any .env file. Task records under memory/tasks and design "
        "documents are history, not current rules.\n"
        "- Nothing runs from this plan; the Owner reviews it first.\n\n"
        "Answer with exactly one JSON object and nothing else, in this shape:\n"
        '{"goal_summary": "<one line, at most 300 characters>",\n'
        ' "tasks": [{"id": "T1", "title": "<one line, at most 100 characters, no backticks>",\n'
        '            "kind": "<a kind name above, or none>", "mode": "<edit|read_only>",\n'
        '            "purpose": "<one line>", "paths": ["<path>"], "depends_on": [],\n'
        '            "acceptance": ["<criterion>"], "risk": "<low|medium|high>",\n'
        '            "owner_decision": "<none, or the reason>", "worker_request": "<one line>"}],\n'
        ' "order": ["T1"],\n'
        ' "flow": "<one line, at most 500 characters, on how the goal proceeds>"}\n'
    )
