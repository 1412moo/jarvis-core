# Buzz Bridge (Phase 2 minimum slice)

[Document Type]
- flow

## 목적

task-0038(Buzz 조사) → task-0046/0047(로컬 실측) → Design Review/Revision을
거쳐 승인된 **Phase 2 첫 구현 슬라이스**. 목표는 정확히 이것 하나다:

> Jarvis task 하나가 Buzz channel에서 Claude agent에게 메시지를 보내고,
> agent가 실제 CLI를 통해 응답하며, Jarvis가 그 결과를 추적할 수 있다.

승인이 필요한 실제 작업, Codex/agy, Desktop UI, Buzz 자체 approval workflow,
새 DB/이벤트 로그(task-0041/42/44)는 이 슬라이스에 포함되지 않는다.

## 보안 불변식 (코드가 강제, 문서는 설명일 뿐)

```
Buzz message ≠ approval
Buzz message ≠ authorization
Agent response ≠ execution permission
Agent Bridge ≠ policy engine
Jarvis Orchestrator = task state + approval + delegation authority
```

- `claude_adapter.js`: 모든 CLI 호출은 `--permission-mode plan --restricted
  --disallowedTools Edit,Write,NotebookEdit,Bash`, 격리된 `--add-dir`
  (repo 밖 OS temp 디렉터리), stdin 프롬프트로 **하드코딩**되어 있다.
  `--dangerously-skip-permissions` 계열 플래그는 코드 어디에도 없다. 서브
  프로세스에는 `process.env` 전체가 아니라 고정 화이트리스트(`PATH`,
  `USERPROFILE`, `ANTHROPIC_API_KEY` 등)만 전달한다 — Nostr privkey나 relay
  DB 비밀번호는 애초에 그 목록에 없다.
- `lib/nostr.js`의 `subscribeLive`/`queryOnce`가 매 이벤트마다
  `verifyEvent()`(Schnorr 서명 검증)를 먼저 통과시키고, `bridge.js`의
  `passesInboundGate()`/`orchestrator.js`의 `passesResponseGate()`도
  독립적으로 다시 `verifyEvent()`를 확인한다(각 함수가 단독으로도 정확하도록,
  이중 방어). `event.pubkey` 문자열 일치만으로는 인증이 성립하지 않는다 —
  서명이 그 pubkey의 것인지까지 확인해야 발신자 인증이다.
- `bridge.js`의 `passesInboundGate()`: (a) 유효한 서명 + (b) `event.pubkey
  === JARVIS_ORCHESTRATOR_PUBKEY` + (c) 자기 앞 `p`-tag 멘션 + (d)
  `jarvis-task`/`jarvis-run` 태그, 이 4가지를 **전부** 만족해야 CLI를
  호출한다. Buzz relay의 멤버십/allowlist 설정과 무관하게 bridge 코드
  자체가 다시 검사한다.
- `orchestrator.js`의 `passesResponseGate()`: 유효한 서명 + `e` 태그 == 원본
  event id + `jarvis-run` 태그 == 그 run_id + 서명 pubkey == 그 run에 실제
  위임했던 agent pubkey. 넷 중 하나라도 어긋나면 응답을 버리고 anomaly 로그만
  남긴다 — 절대 실행/승인 신호로 쓰지 않는다.
- Buzz의 `request_approval` 워크플로/`kind:46011`/grant-deny API는 이 코드
  어디에서도 호출하지 않는다.

## 파일 구성

- `lib/nostr.js` — WS 연결, NIP-42 인증, 이벤트 서명 검증(`verifyEvent`),
  채널 이름 기반 발견/생성/구독(`findChannelByName`/`ensureChannel`), 발행,
  reconnect cursor(`nextSinceFilter`) 등 relay와 대화하는 유일한 저수준 모듈.
- `lib/dedupe.js` — bounded seen-event-id set (event log/DB 아님).
- `lib/env.js` — `.env` 로더(`adapters/discord/bot_minimal.py`의
  `_load_env_file`과 동일한 최소 구현, 새 의존성 추가 없음).
- `lib/identities.js` — `configs/buzz-agent-identities.json`(pubkey, tracked)
  + `.env`(privkey, untracked)를 합쳐 두 identity를 로드하는 단일 진입점.
- `lib/constants.js` — 두 프로세스가 공유하는 고정 채널 이름
  (`CHANNEL_NAME`). 채널 식별자는 이 이름으로 매 기동 시 발견되며, 더 이상
  `.env`에 UUID를 수동으로 옮겨 적을 필요가 없다.
- `claude_adapter.js` — Claude CLI stdin invoke, 위 보안 불변식이 여기 있다.
- `bridge.js` — Claude agent bridge 프로세스(inbound gate → CLI → 응답 발행,
  이벤트를 순차 큐로 처리, 개별 이벤트 처리 실패가 프로세스를 죽이지 않음).
- `orchestrator.js` — 최소 orchestrator(channel ensure → 질의 발행 → gate
  검증 → timeout).
- `run_smoke_tests.js` — 오프라인 결정론적 단위 테스트(relay/Docker/CLI
  불필요). 서명 위조/변조 시나리오를 실제 `finalizeEvent`로 만든 이벤트로
  검증한다(가짜 JS 객체가 아님).
- `deploy/compose.yml` + `deploy/.env.example` — 로컬 전용 relay 스택
  (upstream `deploy/compose` 재사용). relay는 digest로, postgres/redis도
  digest로 pin. 포트는 `127.0.0.1`에만 바인딩(LAN 노출 방지).

## 실행

### 1) 오프라인 스모크 테스트 (relay/Docker/CLI 불필요)

```bash
cd orchestrator/buzz-bridge
npm install
node run_smoke_tests.js
```

### 2) 로컬 relay 기동 (Owner가 수동으로, 자동 기동 없음)

```bash
cd orchestrator/buzz-bridge/deploy
cp .env.example .env   # 값을 직접 랜덤 생성값으로 채운다 (커밋 금지)
docker compose up -d
curl http://127.0.0.1:3000/_readiness   # 200이면 준비됨
```

종료 시 `docker compose down`(볼륨 보존) — 스파이크가 아니라 실제 통합
코드이므로 `-v`로 지우지 않는다. 완전 폐기하려는 명시적 의도가 있을 때만
`down -v`.

### 3) identity 준비

```bash
cd orchestrator/buzz-bridge
node -e "const {generateIdentity}=require('./lib/nostr'); console.log(generateIdentity())"
```

두 identity(orchestrator, agent-claude)의 **pubkey**를
`configs/buzz-agent-identities.json`(tracked, 이미 있는 두 항목의 값만
갱신)에, **privkey**를 이 디렉터리의 `.env`(untracked, `.env.example` 참고)에
채운다. `lib/identities.js`가 기동 시 두 파일을 합쳐 읽는다 — pubkey는
`.env`에 넣지 않아도 된다(넣어도 무시된다).

### 4) bridge + orchestrator 실행

```bash
node orchestrator.js "질문 내용" 120000   # 터미널 1: 채널이 없으면 생성, 있으면 재사용, 1회 위임 + 응답 대기
node bridge.js                            # 터미널 2: Claude agent identity로 채널 발견 + 구독
```

채널은 고정 이름(`lib/constants.js`의 `CHANNEL_NAME`)으로 매번 새로 발견된다
— 더 이상 UUID를 `.env`에 수동으로 옮겨 적지 않는다. `bridge.js`는 채널을
직접 만들지 않고 최대 10초간 폴링하며 기다리므로, 최초 1회는 `orchestrator.js`
를 먼저(또는 거의 동시에) 실행해 채널이 생성되게 한다.

`orchestrator.js`는 `status: OK`와 correlation 정보(`taskId`, `runId`,
`outgoingEventId`, 응답 event)를 JSON으로 출력하고 exit 0, 실패/timeout이면
exit 1.

## 이번 슬라이스가 하지 않는 것

- 실제 task 파일(`memory/tasks/*.md`)과의 자동 연결 — `taskId`는 지금
  고정 placeholder 문자열이다.
- Codex/agy bridge.
- 채널/run_id를 넘어선 이벤트 로그·감사 해시체인(task-0041/0044).
- relay 자동 기동/재시작 감시, bridge 프로세스 supervisor(무한 재시도 방지
  원칙에 따라 일부러 만들지 않았다).
- Buzz 자체 approval workflow 사용.
