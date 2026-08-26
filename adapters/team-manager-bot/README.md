# team-manager-bot (Phase A: credential-free scaffolding)

역할: 승인된 4-Phase 계획(`docs/chatgpt-discord-claude-auto-collab-v0.1-design.md`,
task-0031)의 신규 Discord 역할 명칭. "ChatGPT 팀장"을 Discord에 연결하기 위한
미래 봇의 자리이며, 현재는 **Phase A(무자격 스캐폴딩)만 구현**되어 있다.

## 현재 구현 범위 (Phase A만)

- `bot_minimal.py`: 봇 프로세스의 뼈대. `--self-check <text>`만 실제로 동작한다.
- `llm_provider.py`: `call_llm_for_intent(text) -> None` stub. 네트워크/subprocess/credential
  의존성이 전혀 없다 (`orchestrator/discord-nl-intent/llm_provider.py`의
  Phase 2A stub과 동일한 계약).
- 진짜 Discord 연결(`_TeamManagerBotClient.run()`)은 `NotImplementedError`를
  낸다 — Phase C 이후에만 구현 대상이다.

## 명시적 비범위 (Phase A)

- Discord bot token 생성/설정/연결 — 하지 않음
- OpenAI 또는 다른 외부 API 호출 — 하지 않음
- 비용 발생 — 없음
- 배포/상시 구동 — 하지 않음(이 코드는 실행 중인 프로세스가 아니다)
- 기존 `adapters/discord/`(jarvis-bot)의 어떤 파일도 수정하지 않음 — 완전히 별도
- `~/.claude/channels/discord/access.json` 수정 — 하지 않음(Claude Discord Plugin과 무관)
- `memory/tasks/*.md`, `prompts/*.md` 쓰기 — 이 봇 코드에는 그런 경로 자체가 없음.
  승인 gate 소유권은 `docs/chatgpt-discord-claude-auto-collab-v0.1-design.md` §7에 따라
  모든 Phase에서 Owner/Claude Code에게 남는다.

## 필요한 환경변수 (Phase B 이후에만 값 설정)

`.env.example` 기준 `TEAM_MANAGER_BOT_TOKEN`. Phase A에서는 값을 넣지 않는다.

## 로컬 검증 (Phase A, credential 없이)

```bash
python adapters/team-manager-bot/bot_minimal.py --self-check "hello"
# 기대: {"result_type": "stub_reply", "input": "hello", "llm_result": null, "reply": "..."}

python adapters/team-manager-bot/bot_minimal.py
# 기대: {"result_type": "error", "reason": "missing_env:TEAM_MANAGER_BOT_TOKEN"}
```

```bash
python adapters/team-manager-bot/run_smoke_tests.py
```

## 다음 단계

Phase B(credential 발급/비용 승인), Phase C(실제 LLM 연결), Phase D(배포)는
전부 별도 Owner 승인 대상이다. 자세한 조건은
`docs/chatgpt-discord-claude-auto-collab-v0.1-design.md`를 따른다.
