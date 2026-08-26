# ChatGPT–Discord–Claude Code Auto-Collaboration v0.1 (Design & Approval Plan)

Status: **설계/승인 계획 문서. 구현 없음.** task-0031의 work-order
(`prompts/task-0031-chatgpt-discord-claude-auto-collab-work-order.md`)에 따라
작성한다. credential 발급, API 사용, 외부 연결, 배포는 이 문서에 포함된
어떤 phase도 별도 Owner 승인 없이는 실행하지 않는다.

이 문서는 `docs/ai-team-operating-model.md`(Phase 1, 커밋 `1f222bf`/`1e21cec`)와
task-0030 조사 결과(Discord, 2026-08-26)를 전제로 한다. 두 문서의 규칙을
재정의하지 않는다.

## 1. 목표

Phase 1(Owner 수동 중계)이 표준 운영으로 이미 채택된 상태에서, 그 위에
**ChatGPT–Discord–Claude Code 왕복 일부를 자동화**하는 구조를 단계적으로
검토·승인 가능한 형태로 설계한다. "구현"이 아니라 "무엇을, 어떤 순서로,
어디까지 승인받아야 하는지"를 고정하는 계획이다.

## 2. Non-Goals (이번 문서에서 하지 않는 것)

- credential 발급/저장
- 외부 API 실제 호출
- Discord bot 신규 등록/연결
- 어떤 형태의 배포/호스팅
- `docs/master-plan.md` §6 잠긴 기능 재오픈 그 자체(재오픈은 별도 절차, §6 참고)
- `docs/ai-team-operating-model.md`의 규칙 변경

## 3. 전제 (task-0030 조사 결과 요약)

| 항목 | 결론 |
| --- | --- |
| Codex/ChatGPT 계정 연결 | Owner의 ChatGPT 구독과 별개로 신규 OpenAI API key 필요 |
| Discord 송수신 | 신규 Discord Bot Application + token 필요(양방향이므로) |
| Claude Discord Plugin과 관계 | 완전히 별도 identity/token, `access.json` 비접촉 |
| 실행 경계 | 봇은 work-order 텍스트만 생성, 파일 쓰기/커밋 권한은 주지 않음 |
| 필요 자원 | 신규 credential + 사용량 비용 + (상시구동 시) 배포, 전부 approval-gated |
| Lock 상태 | `master-plan.md` §6 "Hermes의 자동 Codex/ChatGPT 호출" 등 재오픈 필요 |
| 이름 충돌 | "Codex"는 이미 이 repo에서 "프롬프트 기반 로컬 실행 세션"을 의미함 — 신규 역할에 재사용 시 충돌 |

## 4. 재사용 가능한 기존 컴포넌트

- `adapters/discord/bot_minimal.py` — `discord.py` 기반 봇 골격, 동일 구조 재사용 가능
- `orchestrator/discord-nl-intent/llm_provider.py` — LLM 연결용으로 이미 예약된 stub hook(`call_llm_for_intent`), 범위는 "자유 텍스트 → 기존 고정 명령 번역"으로 한정됨(팀장 판단 아님)
- `orchestrator/discord-intake/`, `docs/task-model.md` — Task 생성/조회 공통 계약, 변경 없이 재사용
- `prompts/<task-id>-work-order.md` 관행(오늘 채택) — 봇이 있든 없든 work-order 파일화 절차는 동일

## 5. 명칭 제안 (충돌 회피, 승인 필요)

"Codex"를 이 신규 역할에 그대로 쓰지 않을 것을 제안한다. 후보(택 1, Owner/ChatGPT 결정):

- `team-manager-bot`
- `chatgpt-relay-bot`
- (Owner가 지정하는 다른 이름)

Discord 표시 이름도 기존 "jarvis-bot"(Claude Code Plugin으로 추정)과 시각적으로
구분되게 정한다.

## 6. Phase 구성 (각 Phase 종료 지점마다 별도 Owner 승인)

### Phase A — 무자격 스캐폴딩 (credential 없이 코드/구조만)
- 범위: 신규 봇 프로세스의 뼈대만 작성. LLM 호출부는 `llm_provider.py`처럼 **항상 stub(None 반환)**.
- 트리거: 실제 대화/명령 실행 불가, 로컬 self-check만 가능.
- 필요 자원: 없음(credential/API/배포 전부 미사용).
- 여전히 별도 work package + 승인 필요(신규 코드이므로 §2.2 무관하게 일반 AGENTS.md 흐름은 따름). **이번 문서 자체는 Phase A 착수 승인이 아니다.**

### Phase B — Credential 발급 승인
- Owner가 신규 Discord bot token + OpenAI API key 발급을 결정.
- 비용 한도(예: 월 예산 상한) 및 사용 범위를 Owner가 명시.
- 이 phase의 산출물은 "승인 여부와 조건"이며, 실제 발급 행위는 Owner 또는 Owner 지시 하에만 수행.

### Phase C — 실제 LLM 연결
- Phase B 승인 후에만, `llm_provider.py` 패턴과 동일하게 **좁은 범위**(자유 텍스트 → 기존 고정 명령 번역, 또는 팀장 요약 생성 등 사전에 문서화된 정확한 함수 하나)로 한정해 연결.
- 팀장의 "판단"(무엇을 승인 필요로 볼지, 다음 업무를 무엇으로 정할지)은 이 phase에서도 자동화하지 않는다 — §7 참고.

### Phase D — 배포/상시 구동 (선택, 별도 승인)
- Owner PC가 꺼져 있어도 동작해야 하는 경우에만 검토.
- 신규 공격 표면 + 호스팅 비용 발생. Phase A-C와 독립적으로 승인.

## 7. Owner 승인 gate 보존 원칙 (모든 Phase 공통, 재정의 불가 조건)

1. 봇은 `~/.claude/channels/discord/access.json`, `memory/tasks/*.md`, `prompts/*.md`에 **직접 쓰기 권한을 갖지 않는다**. 파일 반영은 지금처럼 Owner 경유 → Claude Code가 수행.
2. `NEEDS_APPROVAL` 승인은 Owner 본인이 작성한 메시지로만 성립한다 — 봇이 승인을 대신 판단하거나 추정하지 않는다.
3. §2.2(`ai-team-operating-model.md`)의 자율/승인 경계는 봇 유무와 무관하게 그대로 유지된다.
4. 각 Phase는 이전 Phase의 승인 없이 시작하지 않는다 — Phase 순서를 건너뛰지 않는다.

## 8. Owner/ChatGPT가 결정할 것 (이 문서에 대한 승인 대상)

1. 이 Phase A-D 구성 자체를 승인할지, 아니면 다른 구조를 원하는지.
2. Phase A(무자격 스캐폴딩)을 별도 work package로 착수해도 될지 — 이것도 이 문서 승인과는 별개로 다시 확인 필요.
3. 신규 역할의 명칭(§5).
4. Phase B(credential/비용) 승인 여부와 조건 — **아직 요청 대상 아님, 이 문서가 먼저 승인된 뒤 별도로 다룸.**
