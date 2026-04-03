"""Minimal Discord bot adapter for jarvis-core intake pipeline.

Scope (this step):
- Accept only text command: /task <내용>
- Reuse existing intake pipeline:
  intake_parser -> task_draft_builder -> task_file_writer
- Reply with success/hold/error only

Out of scope:
- /status, /report, /approve
- GitHub execution/report automation/DB/web UI
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    import discord
except ModuleNotFoundError:
    discord = None  # type: ignore[assignment]


THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
INTAKE_DIR = REPO_ROOT / "orchestrator" / "discord-intake"
if str(INTAKE_DIR) not in sys.path:
    sys.path.insert(0, str(INTAKE_DIR))

from intake_parser import parse_intake
from task_draft_builder import build_task_draft
from task_file_writer import write_task_file


def _load_env_file(env_path: Path) -> None:
    """Very small .env loader to avoid extra dependencies."""
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _error_payload(reason: str) -> dict[str, Any]:
    return {"result_type": "error", "reason": reason}


def _run_task_pipeline(command_text: str) -> dict[str, Any]:
    parser_result = parse_intake(command_text).to_dict()
    if parser_result.get("error_reason"):
        return _error_payload(str(parser_result.get("error_reason")))

    if parser_result.get("hold_reason"):
        return {"result_type": "hold", "reason": str(parser_result.get("hold_reason"))}

    draft_result = build_task_draft(parser_result).to_dict()
    if draft_result.get("result_type") != "task_draft":
        hold = draft_result.get("hold") or {}
        return {"result_type": "hold", "reason": str(hold.get("reason") or "draft_not_created")}

    task_draft = draft_result.get("task_draft") or {}
    file_result = write_task_file(task_draft).to_dict()

    if file_result.get("result_type") == "created":
        file_path = str(file_result.get("file_path") or "")
        return {
            "result_type": "success",
            "task_id": str(file_result.get("task_id") or ""),
            "file_name": Path(file_path).name,
            "file_path": file_path,
        }

    if file_result.get("result_type") == "hold":
        return {"result_type": "hold", "reason": str(file_result.get("reason") or "unknown_hold")}

    return _error_payload(str(file_result.get("reason") or "task_file_writer_failed"))


def _format_reply(pipeline_result: dict[str, Any]) -> str:
    result_type = pipeline_result.get("result_type")
    if result_type == "success":
        return (
            "✅ task 생성 완료\n"
            f"- task_id: `{pipeline_result.get('task_id')}`\n"
            f"- file: `{pipeline_result.get('file_name')}`"
        )
    if result_type == "hold":
        return f"⏸️ hold\n- reason: `{pipeline_result.get('reason')}`"
    return f"❌ error\n- reason: `{pipeline_result.get('reason')}`"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal Discord /task bot")
    parser.add_argument(
        "--env-file",
        default=str(THIS_DIR / ".env"),
        help="Optional .env file path (default: adapters/discord/.env)",
    )
    parser.add_argument(
        "--self-check",
        help="Run local pipeline check without Discord connection. Example: --self-check '/task 문서 정리'",
    )
    return parser.parse_args()


def _validate_required_env() -> tuple[bool, str | None]:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        return False, "missing_env:DISCORD_BOT_TOKEN"
    return True, None


async def _start_discord_bot() -> None:
    if discord is None:
        raise RuntimeError("missing_dependency:discord.py")

    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        print(f"[discord] connected as {client.user}")

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

        content = (message.content or "").strip()
        if not content.startswith("/"):
            return

        if not content.startswith("/task"):
            await message.reply("이 봇은 현재 `/task <내용>`만 지원합니다.")
            return

        result = _run_task_pipeline(content)
        await message.reply(_format_reply(result))

    token = os.environ["DISCORD_BOT_TOKEN"].strip()
    try:
        await client.start(token)
    except Exception as exc:  # noqa: BLE001 - entrypoint level reporting only
        raise RuntimeError(f"discord_connection_failed:{exc}") from exc


def main() -> None:
    args = _parse_args()
    _load_env_file(Path(args.env_file))

    if args.self_check:
        command_text = args.self_check.strip()
        if not command_text:
            print(json.dumps(_error_payload("empty_input"), ensure_ascii=False))
            raise SystemExit(2)
        print(json.dumps(_run_task_pipeline(command_text), ensure_ascii=False, indent=2))
        return

    is_valid, reason = _validate_required_env()
    if not is_valid:
        print(json.dumps(_error_payload(str(reason)), ensure_ascii=False))
        raise SystemExit(2)

    try:
        asyncio.run(_start_discord_bot())
    except RuntimeError as exc:
        print(json.dumps(_error_payload(str(exc)), ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
