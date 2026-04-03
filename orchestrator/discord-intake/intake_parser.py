"""Rule-based minimal intake parser for Discord-like slash commands.

Scope (MVP):
- classify supported commands: /task, /status, /report, /approve
- validate required arguments
- return normalized payload draft
- return hold/error reason when needed

Out of scope:
- Discord API integration
- network calls
- task file creation or external side effects
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import re

SUPPORTED_COMMANDS = {"/task", "/status", "/report", "/approve"}
VALID_APPROVAL_DECISIONS = {"approve", "reject"}
VALID_REPORT_PERIODS = {"today", "weekly"}
HOLD_KEYWORDS = ["삭제", "delete", "drop", "destroy", "배포", "운영", "prod", "production"]


@dataclass
class ParseResult:
    command_name: str | None
    required_args_present: bool
    normalized_payload: dict[str, Any]
    hold_reason: str | None = None
    error_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_name": self.command_name,
            "required_args_present": self.required_args_present,
            "normalized_payload": self.normalized_payload,
            "hold_reason": self.hold_reason,
            "error_reason": self.error_reason,
        }


def _tokenize(text: str) -> list[str]:
    return [t for t in text.strip().split() if t]


def _contains_hold_risk(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in HOLD_KEYWORDS)


def parse_intake(command_text: str) -> ParseResult:
    tokens = _tokenize(command_text)
    if not tokens:
        return ParseResult(
            command_name=None,
            required_args_present=False,
            normalized_payload={"raw": command_text, "args": []},
            error_reason="empty_input",
        )

    command_name = tokens[0]
    args = tokens[1:]

    if command_name not in SUPPORTED_COMMANDS:
        return ParseResult(
            command_name=command_name,
            required_args_present=False,
            normalized_payload={"raw": command_text, "args": args},
            error_reason="unsupported_command",
        )

    # /task <request...>
    if command_name == "/task":
        request = " ".join(args).strip()
        if not request:
            return ParseResult(
                command_name=command_name,
                required_args_present=False,
                normalized_payload={"request": "", "status": "TODO"},
                error_reason="missing_required_arg:request",
            )

        hold_reason = "needs_approval:risky_keyword_detected" if _contains_hold_risk(request) else None
        return ParseResult(
            command_name=command_name,
            required_args_present=True,
            normalized_payload={
                "request": request,
                "repo_hint": None,
                "priority": None,
                "due": None,
                "status": "TODO",
            },
            hold_reason=hold_reason,
        )

    # /status <task_id|scope>
    if command_name == "/status":
        target = args[0] if args else ""
        if not target:
            return ParseResult(
                command_name=command_name,
                required_args_present=False,
                normalized_payload={"target": ""},
                error_reason="missing_required_arg:task_id_or_scope",
            )

        return ParseResult(
            command_name=command_name,
            required_args_present=True,
            normalized_payload={"target": target, "repo": None, "limit": None},
        )

    # /report <period>
    if command_name == "/report":
        period = args[0] if args else ""
        if not period:
            return ParseResult(
                command_name=command_name,
                required_args_present=False,
                normalized_payload={"period": ""},
                error_reason="missing_required_arg:period",
            )

        normalized_period = period.lower()
        if normalized_period not in VALID_REPORT_PERIODS:
            return ParseResult(
                command_name=command_name,
                required_args_present=True,
                normalized_payload={"period": normalized_period, "repo": None, "format": "summary"},
                hold_reason="unrecognized_period_requires_confirmation",
            )

        return ParseResult(
            command_name=command_name,
            required_args_present=True,
            normalized_payload={"period": normalized_period, "repo": None, "format": "summary"},
        )

    # /approve <target> <decision>
    if command_name == "/approve":
        target = args[0] if len(args) > 0 else ""
        decision = args[1].lower() if len(args) > 1 else ""
        reason = " ".join(args[2:]).strip() or None

        if not target:
            return ParseResult(
                command_name=command_name,
                required_args_present=False,
                normalized_payload={"target": "", "decision": "", "reason": None, "scope": None},
                error_reason="missing_required_arg:target",
            )
        if not decision:
            return ParseResult(
                command_name=command_name,
                required_args_present=False,
                normalized_payload={"target": target, "decision": "", "reason": reason, "scope": None},
                error_reason="missing_required_arg:decision",
            )

        if decision not in VALID_APPROVAL_DECISIONS:
            return ParseResult(
                command_name=command_name,
                required_args_present=True,
                normalized_payload={"target": target, "decision": decision, "reason": reason, "scope": None},
                hold_reason="invalid_decision_requires_confirmation",
            )

        target_ok = bool(re.match(r"^task-\d{4}$", target))
        hold_reason = None if target_ok else "unrecognized_target_format"

        return ParseResult(
            command_name=command_name,
            required_args_present=True,
            normalized_payload={"target": target, "decision": decision, "reason": reason, "scope": None},
            hold_reason=hold_reason,
        )

    return ParseResult(
        command_name=command_name,
        required_args_present=False,
        normalized_payload={"raw": command_text, "args": args},
        error_reason="internal_unreachable_branch",
    )


def main() -> None:
    samples = [
        "/task 보고 시스템 개선",
        "/status task-0002",
        "/report today",
        "/approve task-0007 approve",
        "/approve wrong-target maybe",
    ]
    for sample in samples:
        result = parse_intake(sample)
        print(json.dumps({"input": sample, "result": result.to_dict()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
