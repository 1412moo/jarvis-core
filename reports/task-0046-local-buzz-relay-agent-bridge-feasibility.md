# task-0046: Hostinger/VPS 없이 Windows 로컬 PC에서 Buzz Relay/WebSocket + Local Agent Bridge 연결 가능성 조사

- 작성일: 2026-08-27
- 작성자: Claude Code (research agent, task-0046)
- 선행 조사: `reports/task-0038-ai-agent-collaboration-platform-buzz-research.md`(Buzz 생태계), `reports/task-0038-gpt-team-synthesis.md`, `reports/task-0045-acp-feasibility-research.md`(ACP 미지원 확인)
- 조사 방식: `block/buzz` 저장소의 **실제 소스 파일·설정 파일·공식 예제 직접 fetch**(GitHub API + raw.githubusercontent) + GitHub 이슈 원문 + NIP 스펙 원문 + **로컬에 설치된 CLI 3종(`claude`/`codex`/`agy`)의 `--help` 직접 실행**
- 실행 경계 준수: Hostinger/VPS 가입·생성 **없음**, Buzz 설치 **없음**, 실제 연결 구현 **없음**, API key 발급 **없음**, jarvis-core 코드 변경 **없음**. 조사·문서화만.
- 모든 외부 사실은 **2026-08-27 확인 시점** 기준. WebFetch 결과는 대상 문서를 소형 모델이 재요약한 것이므로, 원문 인용이 확실한 부분만 따옴표로 표기했다.

---

## Executive Summary

**결론: 가능하다. 단 "Buzz 전체"가 아니라 "Relay 프로세스 + Postgres + Redis + MinIO 4종 컨테이너"까지는 로컬에서도 반드시 띄워야 하고, 그 위에서 ACP를 완전히 우회하는 local agent bridge를 만드는 것은 Buzz가 스스로 공식 예제로 증명해 놓았다.**

이번 조사에서 확인한 세 가지 핵심 사실이 task-0045의 비관적 전제를 실질적으로 무력화한다.

1. **Buzz Relay의 WebSocket은 Buzz 고유 프로토콜이 아니라 표준 Nostr NIP-01 + NIP-42다.** `crates/buzz-relay/src/protocol.rs`에 정의된 프레임은 `EVENT`/`REQ`/`CLOSE`/`COUNT`/`AUTH`(클라이언트→릴레이)와 `AUTH`/`EVENT`/`NOTICE`/`EOSE`/`OK`/`CLOSED`/`COUNT`(릴레이→클라이언트)가 전부이고, **Buzz 전용 비표준 프레임은 없다.** 즉 프로토콜이 "추론해야 하는 미지의 것"이 아니라 공개 스펙이다.
2. **Buzz 저장소에 `examples/countdown-bot`이라는 공식 예제가 있고, 그 설명이 정확히 이 조사의 질문에 답한다** — *"connects directly to the Buzz relay over WebSocket, authenticates with NIP-42, subscribes to one channel, and replies to deterministic commands"*, 그리고 *"direct WebSocket + NIP-42 instead of MCP"*. **ACP도 MCP도 쓰지 않고 채널에 참여해 응답하는 에이전트가 이미 upstream에 존재한다.** `buzz-acp`는 필수 구조가 아니라 편의 구현이다.
3. **Claude Code / Codex / Antigravity(agy) 세 CLI 모두 ACP는 없지만, 각자 자기 stdio 기계판독 프로토콜을 갖고 있다** — 로컬에서 `--help`로 직접 확인했다. `claude -p --output-format stream-json --input-format stream-json`(양방향 NDJSON), `codex exec --json`(JSONL) + `codex app-server`(스키마 생성기까지 있는 stdio 프로토콜), `agy --print --output-format stream-json --input-format stream-json`. **task-0045가 "ACP가 없다"고 확인한 것은 맞지만, 그것이 "붙일 방법이 없다"는 뜻은 아니었다.**

반대로 로컬화의 실제 비용은 task-0038이 추정한 것보다 **더 크다**. `crates/buzz-relay/src/config.rs`에서 `database_url`과 `redis_url`은 `Option`이 아닌 `String` 필드이고 media(S3/MinIO) 설정도 비활성화 토글이 없다. **Postgres·Redis·MinIO 중 어느 것도 코드 수정 없이는 뺄 수 없다.** 또한 릴리스 자산에는 **standalone relay 바이너리가 없다** — `desktop-v0.5.20`은 데스크톱 설치본뿐이고, relay는 `ghcr.io/block/buzz` **Linux 컨테이너**로만 배포된다. 즉 Windows에서는 Docker Desktop(WSL2 백엔드)이 사실상 필수다.

Windows 결함(#3490 / #2872)에 대한 판정도 갱신한다. **두 이슈 모두 2026-08-27 현재 OPEN이다**(task-0038은 클로즈 여부를 미확인으로 남겼었다). 그러나 원문을 읽어보면 이것은 **코드 결함이 아니라 설정 템플릿의 기본값 누락**이고, #2872 신고자는 *"Verified on the deployment above: adding those two origins and restarting the relay resolves the join failure"*라고 직접 해결을 확인했다. 더 중요한 것은 **이 버그가 브라우저 WebView의 HTTP(REST) 경로에만 적용되고, 헤드리스 WebSocket 클라이언트는 CORS 대상이 아니라는 점**이다. **로컬 agent bridge 경로는 이 버그의 영향권 밖에 있다.**

---

## 1. Buzz Relay / WebSocket 구조 상세

### 1.1 Relay 프로세스와 실제 런타임 요구사항

**relay 바이너리 배포 형태 (확인)**

| 항목 | 확인 사실 | 근거 |
| --- | --- | --- |
| 컨테이너 이미지 | `ghcr.io/block/buzz:main` (또는 `:sha-<7>` 핀) | `deploy/compose/compose.yml`, `deploy/compose/README.md` |
| 빌드 베이스 | `rust:1.95-bookworm` → 런타임 `debian:bookworm-slim` | 루트 `Dockerfile` |
| 이미지에 들어가는 바이너리 | `buzz-relay`, `buzz-admin`, `buzz-pair-relay` — **`buzz-cli`와 `buzz-acp`는 이미지에 없다** | 동상 |
| ENTRYPOINT | `["/usr/local/bin/buzz-relay"]` | 동상 |
| 노출 포트 | 3000(앱) / 8080(헬스) / 9102(메트릭), 비루트 `buzz:buzz` UID 1000 | 동상 |
| 아키텍처 | amd64 / arm64 **네이티브 러너에서 각각 빌드** (`--platform` 지시자 없음) → **Linux 컨테이너만 존재, Windows 네이티브 이미지 없음** | 동상 |
| standalone 서버 바이너리 릴리스 | **없음.** `desktop-v0.5.20`(2026-08-26) 자산은 mac/Linux/Windows 데스크톱 설치본 + updater 매니페스트뿐 | GitHub Releases API |
| Windows 데스크톱 자산 | `Buzz_0.5.20_x64-setup_alpha-unsigned.exe` — 파일명 자체가 **alpha, unsigned** | 동상 |

→ **Windows에서 relay를 돌린다 = Docker Desktop(WSL2 백엔드)에서 Linux 컨테이너를 돌린다**, 또는 Rust 1.95 툴체인으로 소스 빌드. 후자는 task-0045가 확인한 al3rez field report처럼 업스트림 버그 우회가 필요하므로 권장 경로가 아니다.

**의존 서비스 — 무엇이 진짜 필수인가 (Owner 질문 2의 핵심)**

`deploy/compose/compose.yml`에는 **5개 서비스가 있고 profile 게이팅이 전혀 없다** — 즉 전부 필수다.

| 서비스 | 이미지 | relay의 `depends_on` | 생략 가능? |
| --- | --- | --- | --- |
| `relay` | `ghcr.io/block/buzz:main` | — | 당연히 불가 |
| `postgres` | `postgres:17-alpine` | healthy 조건 | 🔴 **불가.** `config.rs`의 `database_url: String`(기본 `postgres://buzz:buzz_dev@localhost:5432/buzz`), `Option` 아님. 이벤트의 단일 진실 저장소 |
| `redis` | `redis:7-alpine` | healthy 조건 | 🔴 **코드 수정 없이는 불가.** `config.rs`의 `redis_url: String`(기본 `redis://localhost:6379`), **`Option` 아님** — 단일 노드라도 pubsub 경로가 Redis를 통한다 |
| `minio` | `minio/minio:RELEASE.2025-09-07T16-13-09Z` | healthy 조건 | 🔴 **코드 수정 없이는 불가.** `media: buzz_media::MediaConfig`가 항상 존재하고 **비활성화 토글이 없다** |
| `minio-init` | `minio/mc:...` | minio healthy 후 1회 실행 | 버킷 생성용 one-shot. 생략 불가(버킷 없으면 미디어 경로 실패) |

`deploy/compose/README.md`가 직접 명시한다: 배포는 *"PostgreSQL database / Redis cache / MinIO object storage / Git data volume"*에 의존하고, `BUZZ_RELAY_PRIVATE_KEY`·`BUZZ_GIT_HOOK_HMAC_SECRET`·DB 자격증명·S3 시크릿은 **재시작 사이에 바뀌면 안 된다**.

**생략 가능한 것 (확인):**

- **Caddy(TLS 리버스 프록시)** — `compose.caddy.yml`로 분리되어 있고 `BUZZ_COMPOSE_TLS=true`일 때만 붙는다. 기본값에서는 relay 포트가 직접 바인딩된다. → **로컬에서 100% 생략 가능.**
- **Typesense(검색)** — 루트 `.env.example`에는 `TYPESENSE_URL=http://localhost:8108` / `TYPESENSE_API_KEY=buzz_dev_key`가 있으나, `deploy/compose/compose.yml`에는 Typesense 서비스가 **없고** `crates/buzz-relay/src/config.rs`에도 Typesense 필드가 **없다**. → 자체호스팅 compose 경로에서는 붙지 않는 것으로 보인다(**정확한 검색 동작 저하 범위는 미확인**).
- **Keycloak / Adminer / Prometheus** — 루트 `docker-compose.yml`(개발 스택)에는 있으나 `deploy/compose/compose.yml`(자체호스팅 스택)에는 **없다**. → 로컬 생략 가능.
- **mesh(다중 노드)** — `config.rs`의 `mesh: MeshConfig { enabled: bool }`이 **기본 false**. ARCHITECTURE.md도 *"The self-hosted default remains one host, one relay process, one implicit community."* → 로컬 단일 노드가 문서상 기본값이다.

### 1.2 WebSocket 엔드포인트 · URL 스킴 · 프레임 포맷

**엔드포인트 (확인, `crates/buzz-relay/src/router.rs`)**

| 경로 | 핸들러 | 비고 |
| --- | --- | --- |
| `GET /` | `nip11_or_ws_handler` | **콘텐츠 협상.** `Upgrade: websocket`이면 WS 업그레이드, `Accept: application/nostr+json`이면 NIP-11 릴레이 정보 JSON |
| `GET /health`, `/_liveness`, `/_readiness`, `/_status`, `/_mesh` | 헬스 프로브 | 스파이크 pass/fail 신호로 직접 사용 가능 |
| `POST /events`, `POST /query`, `POST /count` | `api::bridge::*` | **NIP-98 HTTP 브리지** — WebSocket 없이 REST로 이벤트 제출/조회 가능 |
| `PUT /upload`, `PUT /media/upload`, `GET|HEAD /media/{sha256_ext}` | Blossom 미디어 | |
| `POST /api/invites`, `/api/invites/claim`, `GET /api/join-policy` | 커뮤니티 가입 | **데스크톱 join 플로우가 쓰는 HTTP 경로 — CORS 버그 지점** |
| `GET /workflows/{id}/runs`, `/runs/{run_id}/approvals`, `POST /hooks/{id}` | 워크플로/웹훅 | |
| `GET /huddle/{channel_id}/audio` | `audio::handler::ws_audio_handler` | **별도의 두 번째 WebSocket 업그레이드**(음성 전용) |
| `/operator/*`, `/moderation/*`, git 라우터, admin 라우터 | | |

**URL 스킴**: 로컬 기본값은 `ws://localhost:3000`(루트 `.env.example`의 `RELAY_URL=ws://localhost:3000`, `buzz-acp`의 `BUZZ_RELAY_URL` 기본값도 동일). 공개 배포는 `wss://<domain>`(`deploy/compose/.env.example`의 `RELAY_URL=wss://buzz.example.com`). **경로 접미사 없이 루트(`/`)다.**

**프레이밍 (확인, `crates/buzz-relay/src/protocol.rs`) — 전부 JSON 배열**

클라이언트 → 릴레이 (`ClientMessage`):
```text
["EVENT", <서명된 이벤트 객체>]
["REQ",   "<subscription-id>", <filter1>, <filter2>, ...]   # 필터 최대 10개(NIP-11), sub id 최대 256바이트
["CLOSE", "<subscription-id>"]
["COUNT", "<subscription-id>", <filter...>]                 # NIP-45
["AUTH",  <서명된 이벤트 객체>]                              # NIP-42 응답
```

릴레이 → 클라이언트 (`RelayMessage`):
```text
["AUTH",   "<challenge-string>"]
["EVENT",  "<subscription-id>", <이벤트 객체>]
["NOTICE", "<message>"]
["EOSE",   "<subscription-id>"]
["OK",     "<event-id-hex>", <bool>, "<message>"]
["CLOSED", "<subscription-id>", "<message>"]
["COUNT",  "<subscription-id>", {"count": <n>}]
```

🔵 **결정적 사실: Buzz 전용 비표준 프레임은 정의되어 있지 않다.** 확장은 전부 `kind` 정수로 이루어지고, wire format 자체는 순수 NIP-01/42/45다. **따라서 "프로토콜을 리버스 엔지니어링해야 하는가"라는 리스크는 존재하지 않는다.**

### 1.3 연결 라이프사이클과 NIP-42 인증 핸드셰이크

ARCHITECTURE.md가 5단계를 명시한다: *"Every WebSocket connection follows this exact sequence: **Step 0: Community Binding** / **Step 1: Semaphore Acquire** / **Step 2: NIP-42 Challenge** / **Step 3: Authentication** / **Step 4: Active Loops** / **Step 5: Cleanup**"*

```text
[클라이언트]                                  [buzz-relay]
    │  GET / (Upgrade: websocket)                 │
    │────────────────────────────────────────────►│ Step 0 커뮤니티 바인딩(host/도메인 기준)
    │                                             │ Step 1 전역 세마포어 permit 획득
    │  ["AUTH","<challenge>"]                     │ Step 2 **선제(proactive) 챌린지 발송**
    │◄────────────────────────────────────────────│
    │  ["AUTH", {kind:22242, tags:[              │ Step 3 handlers::auth::handle_auth
    │      ["relay","ws://localhost:3000"],       │        verify_auth_event(event, challenge, relay_url)
    │      ["challenge","<challenge>"],           │        relay_url = nip42_expected_relay_url(
    │      ["auth","<NIP-OA tag>"]  ← 선택        │                       config.relay_url, tenant)
    │  ], sig:<Schnorr>}]                         │
    │────────────────────────────────────────────►│  성공 → AuthState::Authenticated(AuthContext)
    │  ["OK","<event-id>",true,""]                │         set_authenticated_pubkey(conn_id, pubkey)
    │◄────────────────────────────────────────────│  실패 → AuthState::Failed
    │                                             │         "auth-required: verification failed"
    │  ["REQ","sub1",{...filters}] …              │ Step 4 recv_loop / send_loop / heartbeat_loop
    │◄──── ["EVENT","sub1",…] / ["EOSE","sub1"]   │
```

**핵심 제약 (핸즈온 스파이크 설계에 직접 쓰이는 값들):**

| 항목 | 확인 사실 | 근거 |
| --- | --- | --- |
| 챌린지 발송 시점 | **연결 직후 선제 발송** — 클라이언트가 요청하지 않아도 온다 | `connection.rs` (*"send the NIP-42 AUTH challenge"*) |
| 인증 타임아웃 | **5초(`AUTH_TIMEOUT`)**. 초과 시 *"NIP-42 auth timeout — closing connection"* | 동상 |
| 인증 이벤트 kind | **22242** (NIP-42 표준). `created_at`은 현재시각 ±약 10분 이내여야 함 | NIP-42 스펙 원문 |
| 필수 태그 | `["relay", "<relay url>"]`, `["challenge", "<challenge>"]` | NIP-42 스펙 원문 + `buzz-ws-client/src/message.rs`의 `EventBuilder::auth(challenge, url)` |
| Buzz 확장 태그 | `["auth", "<NIP-OA 토큰>"]` **1개까지 허용, 2개 이상이면 무효**(*">1 auth tag ⇒ no valid tag"*). 태그 자체는 이벤트 Schnorr 서명으로 무결성 보호 | `handlers/auth.rs` |
| relay 태그 검증 | `nip42_expected_relay_url(config.relay_url, tenant)`와 비교 — **relay의 `RELAY_URL` 설정값과 정확히 맞아야 한다**(로컬 스파이크 실패 1순위 원인) | 동상 |
| 하트비트 | **30초마다 WS ping, pong 3회 누락 시 끊음** (*"3 missed pongs — closing connection"*) | `connection.rs` + ARCHITECTURE.md |
| 느린 클라이언트 | 지속 backpressure 시 *"sustained backpressure — closing slow client"* | `connection.rs` |
| 동시성 | 전역 연결 세마포어 + 핸들러 세마포어(EVENT/REQ/COUNT) 별도 | 동상 |
| pubkey allowlist | `BUZZ_PUBKEY_ALLOWLIST=true`면 연결 게이팅. 실패 시 일반화된 `auth-required: verification failed` 반환 | NOSTR.md |

**구독 팬아웃의 보안 경계 (bridge 설계에 중요):** ARCHITECTURE.md 원문 — *"Global subs (tier 3) are checked for non-channel-scoped events only. Channel-scoped events are delivered exclusively to subscriptions that carry a matching `channel_id` — global subscriptions are explicitly excluded from channel fan-out as a security boundary."*
→ **bridge는 "전역 구독 하나로 다 받는다"를 할 수 없다. 채널 ID를 명시한 REQ를 채널별로 걸어야 한다.** `buzz-acp`가 REST로 채널 목록을 먼저 조회하는 이유가 이것이다.

### 1.4 Desktop ↔ Relay 연결이 실제로 쓰는 두 경로

Owner 질문 3에 대한 정확한 답은 **"하나가 아니라 두 개"**다.

```text
Buzz Desktop (Tauri2 + React, WebView2)
   │
   ├── (A) WebSocket  ws://host:3000/         → NIP-01/42 이벤트 스트림 (CORS 무관)
   │
   └── (B) HTTP/REST  /api/join-policy, /api/invites/claim, /media/*, /moderation/* 등
                                              → **브라우저 WebView의 fetch → CORS 적용 대상**
                                                 WebView origin = tauri://localhost (mac/Linux)
                                                              또는 http://tauri.localhost (Windows)
```

**#3490 / #2872의 정체**: relay는 `BUZZ_CORS_ORIGINS`를 쉼표 구분 **정확 오리진 목록**으로 파싱하고, `build_cors_layer`(`router.rs`)는 값이 설정되어 있으면 **의도적으로 permissive CORS로 폴백하지 않는다**. `deploy/compose/.env.example`의 기본값이 `BUZZ_CORS_ORIGINS=https://buzz.example.com` 하나뿐이라, 템플릿대로 배포하면 (B) 경로가 전부 preflight에서 막힌다. `curl`과 NIP-11 체크는 성공하므로 릴레이는 멀쩡해 보인다 — 그래서 디버깅이 어렵다.

- **두 이슈 모두 2026-08-27 현재 OPEN** (#2872: 2026-07-25 개설 / #3490: 2026-07-29 개설). *(task-0038의 "클로즈 여부 미확인" 항목을 이번에 확정한다.)*
- **그러나 코드 결함이 아니라 템플릿 기본값 문제**다. #2872 원문: *"Verified on the deployment above: adding those two origins and restarting the relay resolves the join failure."* 제안된 값은 `BUZZ_CORS_ORIGINS=https://buzz.example.com,tauri://localhost,http://tauri.localhost`.
- `config.rs` 주석에 따르면 **`BUZZ_CORS_ORIGINS`가 비어 있으면 permissive CORS(dev 모드)** 다 — 로컬 전용 배포에서는 아예 설정하지 않는 선택지도 존재한다(외부 노출이 없을 때만 허용 가능한 선택).
- 🔵 **가장 중요한 함의: (A) WebSocket 경로는 CORS 대상이 아니다.** 브라우저가 아닌 헤드리스 WS 클라이언트(= local agent bridge)는 이 버그와 **무관하게** 붙을 수 있다. task-0038이 이 결함을 "Phase 2 게이트 G1 실패 시 전체 중단" 사유로 격상했던 것은, **Desktop을 필수 전제로 놓았을 때만** 타당하다.

### 1.5 REST 표면과 `buzz-cli` (WebSocket을 안 쓰는 경로)

`crates/buzz-cli`는 *"JSON in / JSON out"* 계약이다.

- 인증: `BUZZ_RELAY_URL`(기본 **`http://localhost:3000`** — WS가 아니라 HTTP다) + `BUZZ_PRIVATE_KEY`(`nsec1…`), NIP-98 Schnorr 서명.
- 종료코드: 0 성공 / 1 사용자오류 / 2 네트워크 / 3 인증 / 4 기타 / 5 쓰기충돌.
- 명령군: messages(send/edit/delete/get/thread/search/vote), channels(create/join/members/add-member…), reactions, dms, users, workflows(trigger/runs/**approve**), repos, file upload, **mem**(Engram) 등.
- 🔴 **`watch`/`tail`/`stream`/`subscribe` 계열 명령이 없다.** → **`buzz-cli`만으로는 실시간 인바운드를 받을 수 없다.** 폴링(`messages get` 반복)이 아니면 WebSocket이 필요하다.
- ⚠️ `buzz-cli`는 **relay 컨테이너 이미지에 포함되지 않는다**(Dockerfile 확인). 별도로 소스 빌드해야 한다 → bridge를 `buzz-cli` 위에 쌓는 설계는 Rust 툴체인 의존을 되살린다.

---

## 2. Hostinger/VPS가 제공하는 것 vs 로컬에서 생략 가능한 것

Buzz의 자체호스팅 가이드(`deploy/compose/README.md`)가 전제하는 것은 *"A VPS or single-node server environment"*다. 그 VPS가 실제로 제공하는 것을 항목별로 분해하면:

| VPS가 제공하는 것 | 로컬 PC에서 | 판정 | 근거 |
| --- | --- | --- | --- |
| **공개 DNS 이름** (`buzz.example.com`) | `127.0.0.1` / `localhost` | 🟢 **생략 가능** | `RELAY_URL=ws://localhost:3000`이 루트 `.env.example` 기본값 |
| **TLS 인증서 + Let's Encrypt 자동갱신 (Caddy)** | 평문 `ws://` | 🟢 **생략 가능** — `compose.caddy.yml`은 `BUZZ_COMPOSE_TLS=true`일 때만 붙는 별도 파일 | `deploy/compose/README.md` |
| **80/443 인바운드 개방 + 방화벽/포트포워딩** | 루프백 바인딩만 | 🟢 **생략 가능**, 오히려 **하면 안 됨** (§5 보안) | — |
| **24/7 가동** | PC가 켜져 있는 동안만 | 🟢 **생략 가능** — Owner 전제와 일치. 단 §5의 상태 재동기화 이슈 있음 | — |
| **공인 IP로 원격 접속(모바일/외부 협업)** | 불가 | 🟡 **기능 상실을 감수** — 1인 로컬 목표에서는 손실 아님 | — |
| **Linux 커널 / Docker 엔진** | **Docker Desktop + WSL2** | 🔴 **생략 불가.** relay는 Linux 컨테이너로만 배포됨(Windows 네이티브 이미지 없음) | Dockerfile, Releases API |
| **`relay` 프로세스 자체** | 동일하게 필요 | 🔴 **생략 불가** — 유일한 진실의 원천 | ARCHITECTURE.md |
| **PostgreSQL** | 동일하게 필요 | 🔴 **생략 불가** (`database_url: String`) | `config.rs` |
| **Redis** | 동일하게 필요 | 🔴 **코드 수정 없이 생략 불가** (`redis_url: String`, `Option` 아님) | `config.rs` |
| **MinIO/S3 + 버킷 초기화** | 동일하게 필요 | 🔴 **코드 수정 없이 생략 불가** (media 비활성화 토글 없음) | `config.rs`, `compose.yml` |
| **git 데이터 볼륨** (`/data/git`) | 볼륨은 필요, git 호스팅 기능은 안 써도 됨 | 🟡 볼륨 마운트는 유지, **jarvis-core 소스를 여기 올리지 말 것**(task-0038 §7.2 금지사항 승계) | `compose.yml` |
| **안정적 시크릿 저장** (`BUZZ_RELAY_PRIVATE_KEY` 등) | 로컬 `.env`, 저장소 밖 | 🔴 **생략 불가** — README가 재시작 간 불변을 요구 | `deploy/compose/README.md` |
| **백업/스냅샷** | Docker 볼륨 백업 | 🟡 축소 가능하나 **0으로는 못 만듦** (`./run.sh backup-hint`) | 동상 |
| **Keycloak / Adminer / Prometheus** | 불필요 | 🟢 **생략 가능** — 개발 스택(루트 `docker-compose.yml`)에만 존재, `deploy/compose`에는 없음 | 두 compose 파일 비교 |
| **Typesense 검색** | 불필요해 보임 | 🟢 **생략 가능**(자체호스팅 compose에 서비스 없음). 검색 기능 저하 범위는 **미확인** | `compose.yml`, `config.rs` |

**요약 한 줄:** VPS가 주는 것 중 **네트워크·노출·가용성 계층은 전부 버릴 수 있고, 데이터·상태 계층(PG/Redis/S3)은 하나도 못 버린다.** "가벼운 로컬 relay"는 컨테이너 5개짜리이며, 그것이 현재 upstream이 지원하는 최소 형태다.

---

## 3. `buzz-acp`는 필수인가 — 그리고 local agent bridge의 기술적 가능성

### 3.1 `buzz-acp`가 실제로 하는 일 (해부)

`crates/buzz-acp/README.md` 기준 파이프라인:

```text
① BUZZ_PRIVATE_KEY로 신원 로드
② BUZZ_RELAY_URL(기본 ws://localhost:3000)에 WebSocket 접속
③ NIP-42 인증 완주 ("connects to the relay with NIP-42 auth")
④ relay **REST API로 접근 가능한 채널 목록 조회**, 각 채널에 구독
   ("Queries the relay REST API for accessible channels, subscribes to each")
   기본 구독 kind: 9, 40007, 46010. 멤버십 변경 시 자동 재구독
⑤ 수신 이벤트에서 Nostr `p` 태그 기반 @mention 감지 + author gate 적용
   (owner-only 기본 / allowlist / anyone / nobody)
⑥ ─────── ACP 고유 구간 ───────
   BUZZ_ACP_AGENT_COMMAND(기본 goose) + BUZZ_ACP_AGENT_ARGS(기본 acp)로
   서브프로세스 spawn → ACP `initialize` → `session/prompt`
⑦ 응답을 kind 9 EVENT로 서명해 채널에 게시
```

**①~⑤와 ⑦은 ACP와 아무 관련이 없다. ACP가 등장하는 곳은 ⑥ 한 군데뿐이다.**
README 자체가 이를 인정한다: *"The harness works with any agent that implements the ACP spec over stdio."* — 즉 `buzz-acp`는 **"릴레이 클라이언트" + "ACP 어댑터"의 결합**이고, 후자만 교체하면 된다.

`.env.example`이 노출하는 `BUZZ_ACP_SUBSCRIBE`, `BUZZ_ACP_KINDS`, `BUZZ_ACP_CHANNELS`, `BUZZ_ACP_NO_MENTION_FILTER`, `BUZZ_ACP_DEDUP`, `BUZZ_ACP_CONTEXT_MESSAGE_LIMIT`, `BUZZ_ACP_HEARTBEAT_*` 등은 전부 ①~⑤ 계층의 파라미터다 — **bridge를 직접 만들면 이 목록이 곧 요구사항 명세가 된다.**

### 3.2 결정적 반례 — Buzz가 직접 제공하는 비-ACP 봇 예제

🔵 **`examples/countdown-bot`이 Owner 질문 5에 대한 직접적인 답이다.**

`examples/README.md` 설명 (요약 인용): countdown-bot은 *"connects directly to the Buzz relay over WebSocket, authenticates with NIP-42, subscribes to one channel, and replies to deterministic commands"* 하는 **비-AI 봇**이며, README는 이 봇이 *"direct WebSocket + NIP-42 instead of MCP"*를 쓴다고 명시한다. **ACP도 MCP도 `buzz-acp`도 경유하지 않는다.**

| 항목 | countdown-bot 확인 내용 |
| --- | --- |
| 인증 모드 2종 | `BUZZ_BOT_AUTH_MODE=standalone`(봇 자체 키) / `owner-attested`(오너가 서명한 NIP-OA 위임) |
| 환경변수 | `BUZZ_RELAY_URL`, `BUZZ_CHANNEL_ID`(채널 UUID), `BUZZ_BOT_PRIVATE_KEY`, `BUZZ_OWNER_PRIVATE_KEY`, `BUZZ_AUTH_TAG`(선택, 사전계산 태그) |
| owner-attested가 요구하는 relay 설정 | `BUZZ_REQUIRE_RELAY_MEMBERSHIP=true`, `BUZZ_ALLOW_NIP_OA_AUTH=true` |
| 실행 | `BUZZ_RELAY_URL=ws://localhost:3000 BUZZ_CHANNEL_ID=<uuid> … cargo run --manifest-path examples/countdown-bot/Cargo.toml` |
| 구독 kind | **1** (텍스트 메시지) |
| 게시 kind | **0**(프로필), **9**(채널 메시지), **9000**(NIP-29 self-add) |
| 의존성 (Cargo.toml 전량) | `tokio-tungstenite`, `nostr`, `buzz-sdk`, `futures-util`, `url`, `serde_json`, `anyhow`, `tokio` |
| 자기 제한 | *"commands are bounded (`!countdown` and `!fib` max 100)"* — 릴레이 스팸 방지 |

⚠️ **불일치 하나를 그대로 기록한다**: countdown-bot은 kind **1**을 구독하는데 `buzz-acp`는 kind **9 / 40007 / 46010**을 구독하고, task-0038은 Buzz 리치 메시지를 kind **40002**(`KIND_STREAM_MESSAGE_V2`)로 확인했다. **어느 kind가 실제 Desktop 채널 메시지에 대응하는지는 소스에서 확정하지 못했다(미확인)** — 예제가 단순화되었을 가능성이 높다. **스파이크 4에서 반드시 실측해야 하는 항목이다.**

### 3.3 판정: 필수 아님 + 커스텀 bridge 가능

**`buzz-acp`는 구조적으로 필수가 아니다.** relay 입장에서 에이전트는 *"secp256k1 키페어로 NIP-42 인증을 통과하고 채널 이벤트를 구독/게시하는 WebSocket 클라이언트"* 이상도 이하도 아니다. `docs/remote-agents.md`의 Layer 1 계약도 같은 말을 한다: 런처가 넘겨야 하는 것은 *"a keypair, a NIP-OA auth tag, and a relay URL"*이고, *"anything that can set that environment and exec the harness — a bash script, a systemd unit, a CI job … is a conforming launcher"*이며 *"The relay authenticates the keypair and the auth tag — never the launcher."*

**커스텀 local agent bridge에 필요한 것 전량 (구현하지 않고 명세만):**

| # | 요구사항 | 난이도 | 비고 |
| --- | --- | --- | --- |
| 1 | secp256k1 키페어 생성/보관 | 낮음 | `buzz-admin generate-key`로도 발급 가능(relay 이미지에 포함) |
| 2 | WebSocket 클라이언트 | 낮음 | Python `pynostr`는 secp256k1 대신 **coincurve**를 써서 *"pynostr can be used on windows"*라고 README가 명시. 지원 NIP 32종에 **NIP-42 포함** |
| 3 | NIP-42 kind 22242 이벤트 서명(BIP-340 Schnorr) + `relay`/`challenge` 태그 | 중간 | `relay` 태그가 relay의 `RELAY_URL` 설정과 정확 일치해야 함 |
| 4 | 5초 인증 타임아웃 준수 | 낮음 | |
| 5 | 30초 ping에 pong 응답 (3회 누락 시 끊김) | 낮음 | WS 라이브러리 기본 동작이면 대개 충족 |
| 6 | 채널별 REQ 구독 (전역 구독으로는 채널 이벤트 못 받음) | 중간 | REST `/api/…`로 채널 목록 조회 or `BUZZ_CHANNEL_ID` 고정 |
| 7 | `p` 태그 기반 @mention 필터 + author gate | 중간 | **jarvis-core의 프롬프트 인젝션 경계를 여기서 강제해야 함** |
| 8 | 이벤트 → CLI stdio 프로토콜 변환 (§4) | **중간~높음, 실제 작업량의 대부분** | ACP 대신 각 CLI의 네이티브 프로토콜 사용 |
| 9 | 응답 → kind 9 EVENT 서명 후 게시, `["OK", id, true, ""]` 확인 | 낮음 | |
| 10 | 중복 제거/자기 이벤트 무시/재구독 | 중간 | `BUZZ_ACP_DEDUP`, `BUZZ_ACP_NO_IGNORE_SELF`가 같은 문제를 다룸 |

→ **관측 가능한 미지 요소는 "어떤 kind를 구독/게시해야 Desktop UI에 정상으로 보이는가" 하나뿐이고, 나머지는 전부 공개 스펙 + 공식 예제로 커버된다.**

---

## 4. 비-ACP 통합 대안 비교

task-0045는 "Claude Code/Codex/agy 모두 공식 ACP 미지원"을 확인했다. **이번 조사에서 로컬 `--help`를 직접 실행해 확인한 결과, 세 CLI 모두 ACP와 기능적으로 겹치는 자체 stdio 프로토콜을 이미 갖고 있다.**

### 4.1 로컬 직접 확인 결과 (2026-08-27, `C:\work\jarvis-core`에서 실행)

| CLI | 확인된 기계판독 인터페이스 | 양방향 스트리밍? | 세션 연속성 |
| --- | --- | --- | --- |
| **`claude` (Claude Code)** | `-p/--print`, `--output-format text\|json\|stream-json`, `--input-format text\|stream-json`, `--include-partial-messages`, `--replay-user-messages`, `--json-schema`, `--mcp-config`, `--strict-mcp-config`, `--allowed-tools`, `--permission-mode`, `--agents` | ✅ **stdin NDJSON ↔ stdout NDJSON** | ✅ `--session-id <uuid>`, `-r/--resume`, `--continue` |
| **`codex` (Codex CLI)** | `codex exec --json`("Print events to stdout as JSONL"), `--output-schema <FILE>`, `-o/--output-last-message`, `codex exec resume`, **`codex app-server`**(+ `generate-json-schema` / `generate-ts` / `daemon` / `proxy`), **`codex mcp-server`**(stdio MCP 서버) | 🟡 `exec --json`은 이벤트 **출력** 스트림 위주. `app-server`는 양방향이나 **experimental 표기** | ✅ `codex exec resume --last`, `codex resume` |
| **`agy` (Antigravity CLI)** | `--print`, `--output-format text\|json\|stream-json`, **`--input-format text\|stream-json`** — 도움말 원문: *"stream-json reads one NDJSON message per line from stdin and runs a turn for each; it requires --output-format stream-json"*, `--json-schema`, `--mode`, `--sandbox`, `agy mcp` | ✅ **stdin NDJSON ↔ stdout NDJSON** | ✅ `--continue`, `--conversation <id>` |

🔵 **이것이 이번 조사에서 가장 중요한 발견이다.** task-0045는 agy에 대해 *"agy는 툴을 붙이는 MCP는 가능하지만, 다른 에디터/클라이언트가 에이전트를 제어하는 ACP는 불가능"*이라고 판정했는데, **`--input-format stream-json`의 존재는 "외부 프로세스가 agy에 턴 단위로 지시를 밀어넣는" 제어 경로가 실재함을 뜻한다.** ACP 프레이밍이 아닐 뿐, 브리지가 필요로 하는 능력(제어 + 스트리밍 관측)은 충족된다. **세 CLI가 서로 프로토콜이 다르다는 것이 유일한 비용이며, 이는 ACP가 원래 해결하려던 문제 그 자체다 — 즉 "표준화 이득을 포기하고 어댑터 3개를 직접 유지한다"는 명시적 트레이드오프가 된다.**

### 4.2 대안 비교표

| 대안 | 실현성 | 장점 | 단점 / 리스크 | 판정 |
| --- | --- | --- | --- | --- |
| **A. Relay WebSocket 직결 + CLI 네이티브 stdio bridge** | 🟢 **현실적** | 공개 스펙(NIP-01/42) + upstream 공식 예제(countdown-bot) + 세 CLI 전부 stdio 프로토콜 보유. `buzz-acp`·ACP wrapper·Node 툴체인 전부 불필요 → task-0045가 지적한 Windows ACP 버그군을 통째로 회피 | 어댑터 3개를 Jarvis가 직접 유지. CLI들의 stream-json 스키마는 벤더 변경에 노출. Nostr 이벤트 서명을 Python에서 직접 다뤄야 함 | ✅ **1순위** |
| **B. `buzz-acp` + 서드파티 ACP wrapper** (task-0038의 원안) | 🔴 낮음 | 성공 시 하네스 코드를 안 만들어도 됨 | Claude Code 공식 ACP "not planned"(#6686), wrapper 5개 난립, Windows에서 `buzz-acp` 미설치(#4491)·Defender 오탐(#3612)·PATH 프로브 결함(#2342), agy는 ACP 자체가 없음. **의존 계층이 3중(ACP 스펙 + wrapper + buzz-acp)** | 🔴 **비권장** |
| **C. `buzz-cli` 서브프로세스 호출** | 🟡 부분 | JSON in/out, 종료코드 규약 명확, 서명·인증을 CLI에 위임 | **구독/스트리밍 명령이 없어 인바운드 불가**(폴링만). relay 이미지에 미포함이라 Rust 빌드 필요 | 🟡 **아웃바운드 전용 보조** |
| **D. REST 전용 (NIP-98 HTTP 브리지)** — `POST /events`, `POST /query` | 🟡 부분 | WebSocket 상태관리 불필요, 구현 최단. 헬스 엔드포인트로 검증 쉬움 | **푸시 없음 → 폴링 지연 + relay 부하**. 데스크톱과 같은 CORS 계층 위에 있음(헤드리스면 무관) | 🟡 **스파이크/폴백용** |
| **E. MCP 경로** | 🟡 방향이 반대 | 세 CLI 모두 MCP 지원 확정(`claude --mcp-config`, `codex mcp`/`mcp-server`, `agy mcp`). Buzz에도 `buzz-dev-mcp` 존재 | **MCP는 "에이전트가 툴을 부르는" 방향이다. "채널 메시지가 에이전트를 깨우는" 인바운드가 아니다.** Buzz 채널을 MCP 툴로 노출하면 에이전트가 *스스로 폴링*해야 함 | 🟡 **아웃바운드(에이전트→Buzz)에만 적합.** A와 보완 조합 가능 |
| **F. Buzz 워크플로 `call_webhook` → Jarvis HTTP 수신** | 🟡 조건부 | Buzz 쪽 코드 0줄. Jarvis가 이미 아는 HTTP 패턴 | 워크플로 엔진의 자체 인정 결함(승인 게이트 Failed 처리, `send_dm`/`set_channel_topic` NotImplemented, **rate limiter 미구현**)에 의존. Jarvis가 로컬 수신 포트를 열어야 함 | 🟡 **부차 트리거로만** |

**권고 조합: A(인바운드·아웃바운드 주경로) + D(폴백/헬스체크) + E(선택적 툴 노출).** B는 명시적으로 배제한다.

---

## 5. 제안하는 최소 로컬 아키텍처 (Windows 단일 PC)

### 5.1 다이어그램

```text
╔══════════════════════ Windows 11 PC (전원이 켜져 있는 동안만) ══════════════════════╗
║                                                                                    ║
║  ┌──────────── Docker Desktop / WSL2 (Linux 컨테이너) ─────────────┐               ║
║  │                                                                 │               ║
║  │   ┌──────────────────────────────────────────┐                  │               ║
║  │   │  buzz-relay   (ghcr.io/block/buzz)       │                  │               ║
║  │   │  ENTRYPOINT /usr/local/bin/buzz-relay    │                  │               ║
║  │   │  bind 127.0.0.1:3000  (루프백 전용!)      │                  │               ║
║  │   │  RELAY_URL=ws://localhost:3000           │                  │               ║
║  │   │  BUZZ_CORS_ORIGINS=tauri://localhost,    │                  │               ║
║  │   │      http://tauri.localhost   ← #3490 우회 │                  │               ║
║  │   └───┬──────────┬───────────┬───────────────┘                  │               ║
║  │       │          │           │                                  │               ║
║  │   ┌───▼────┐ ┌───▼────┐ ┌────▼────────────┐                     │               ║
║  │   │postgres│ │ redis  │ │ minio + mc init │  ← 3개 전부 필수     │               ║
║  │   │  :17   │ │  :7    │ │  (buzz-media)   │     (코드 수정 없이  │               ║
║  │   └────────┘ └────────┘ └─────────────────┘      제거 불가)      │               ║
║  │                                                                 │               ║
║  │   ✂ 잘라낸 것: Caddy(TLS) · 공개 DNS · 80/443 · Keycloak ·        │               ║
║  │              Adminer · Prometheus · Typesense · relay mesh       │               ║
║  └─────────────────────────────┬───────────────────────────────────┘               ║
║                                │                                                   ║
║        ws://127.0.0.1:3000/  (NIP-01 프레임 / NIP-42 kind 22242 인증)                ║
║        ── CORS 무관, Desktop 없이도 성립 ──                                          ║
║                                │                                                   ║
║   ┌────────────────────────────▼──────────────────────────────┐                    ║
║   │        jarvis-bridge   (Python, 신규 · 지금은 만들지 않음)   │                    ║
║   │   ① 키페어 로드 (저장소 밖, %LOCALAPPDATA%)                  │                    ║
║   │   ② WS 접속 → ["AUTH", challenge] 수신 (5초 내)             │                    ║
║   │   ③ kind 22242 서명 응답 → ["OK", id, true, ""]            │                    ║
║   │   ④ 채널별 ["REQ", sub, {...}] 구독 → EOSE                 │                    ║
║   │   ⑤ p 태그 @mention 필터 + author gate (owner-only 고정)    │                    ║
║   │   ⑥ ══ 신뢰 경계 ══  JARVIS-CORE 승인 게이트에 위임          │                    ║
║   │   ⑦ 승인된 bounded 작업만 CLI 어댑터로 하달                  │                    ║
║   │   ⑧ 결과를 kind 9 EVENT로 서명·게시                         │                    ║
║   └───────┬──────────────────┬──────────────────┬─────────────┘                    ║
║           │ stdio NDJSON     │ JSONL            │ stdio NDJSON                     ║
║           ▼                  ▼                  ▼                                  ║
║   claude -p                codex exec         agy --print                          ║
║   --output-format          --json             --output-format stream-json          ║
║     stream-json                               --input-format  stream-json          ║
║   --input-format                                                                   ║
║     stream-json                                                                    ║
║   (ACP wrapper 없음 · Node 툴체인 없음 · buzz-acp 없음)                              ║
║                                                                                    ║
║   ┌──────────────────────────────────────────────────────────┐                     ║
║   │ Buzz Desktop (Windows, alpha-unsigned .exe)  ── 선택 ──    │                     ║
║   │ WS(A경로)는 정상 / REST(B경로)만 CORS 설정 필요             │                     ║
║   │ 붙지 않아도 bridge는 동작한다 → 필수 전제 아님              │                     ║
║   └──────────────────────────────────────────────────────────┘                     ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

### 5.2 Buzz의 "풀 자체호스팅 스택" 대비 잘라낸 것 / 남긴 것

| 잘라낸 것 | 남긴 것(불가피) |
| --- | --- |
| Caddy 리버스 프록시 + Let's Encrypt | relay 컨테이너 |
| 공개 DNS / 도메인 / `wss://` | Postgres 17 |
| 80/443 개방, 포트포워딩, 방화벽 규칙 | Redis 7 |
| 24/7 가동 보장 | MinIO + 버킷 init |
| Keycloak, Adminer, Prometheus (개발 스택 전용) | git 데이터 볼륨(기능 미사용이어도 마운트) |
| Typesense 검색 | 재시작 간 불변 시크릿(`BUZZ_RELAY_PRIVATE_KEY` 등) |
| relay mesh / 다중 노드 (`mesh.enabled=false` 기본) | Docker Desktop + WSL2 (Linux 컨테이너 런타임) |
| **`buzz-acp` 하네스 + ACP wrapper + Node 툴체인** | Nostr 키페어 관리 |
| **Buzz Desktop (선택 사항으로 강등)** | — |

### 5.3 이 아키텍처에 승계되는 jarvis-core 안전 계약

task-0038 §5.2와 §7.2에서 정한 경계를 그대로 유지한다. 이 아키텍처가 로컬이라고 해서 완화되지 않는다.

- **relay는 표면이지 권한의 원천이 아니다.** 채널 메시지는 **입력**이고, 승인은 Jarvis가 별도 경로로 검증한다. bridge의 ⑥ 단계가 신뢰 경계다.
- **author gate는 `owner-only` 고정.** 채널 메시지 안의 "허용목록에 추가해줘"류 지시는 실행하지 않는다.
- **루프백 바인딩 고정.** `BUZZ_BIND_ADDR` 기본값이 `0.0.0.0:3000`이므로 **명시적으로 `127.0.0.1:3000`으로 바꿔야 한다.** 그러지 않으면 LAN 전체에 노출된다.
- **`BUZZ_CORS_ORIGINS`를 비우면 permissive CORS(dev)** 가 된다 — 루프백 바인딩이 확인된 뒤에만 허용 가능한 선택.
- **jarvis-core 소스를 relay의 git 호스팅에 올리지 않는다.**
- **키는 저장소 밖**(`%LOCALAPPDATA%`), AGENTS.md 원칙 5(no secrets) 유지.
- ⚠️ **PC를 끄면 relay가 죽는다.** Buzz의 원격 에이전트 불변식 ③ *"presence가 곧 상태"*와 ⑤ *"의도적 종료는 최종"*을 고려하면, 재부팅 후 presence·구독 재동기화 동작을 **스파이크에서 실측해야 한다**(미확인).

---

## 6. 최소 핸즈온 스파이크 목록 (순서 / pass·fail 기준)

원칙: **비용이 낮은 것부터, 실패하면 즉시 중단할 수 있는 순서로.** S1은 독립적이므로 S2보다 먼저(또는 병렬로) 돌려 무의미한 인프라 작업을 피한다. **어느 스파이크도 jarvis-core 코드를 건드리지 않는다.**

| # | 스파이크 | 하는 일 | **PASS 신호** | **FAIL 시 판단** | 비용 |
| --- | --- | --- | --- | --- | --- |
| **S1** | **CLI stdio 왕복** (Buzz 무관, 선행) | `claude -p --output-format stream-json --input-format stream-json`에 stdin NDJSON 1건 → stdout 관찰. `codex exec --json "echo test"` 관찰. `agy --print --output-format stream-json --input-format stream-json` 관찰 | 세 CLI 각각에서 **최종 result 메시지를 담은 유효 JSON 라인 수신** + 메시지 스키마 필드명 채록 | 어느 CLI가 실패하면 **그 CLI만** 브리지 대상에서 제외. 세 개 다 실패 시 §4 A안 폐기 | 매우 낮음 (설치 0, 분 단위) |
| **S2** | **Docker 전제 확인** | `docker version`으로 Linux 컨테이너 엔진 확인, 디스크 여유 확인 | Server OS = Linux, WSL2 백엔드 확인 | Docker Desktop 미설치 → **설치 승인이 필요한 Owner 결정 사항으로 에스컬레이션** | 매우 낮음 |
| **S3** | **Relay 단독 기동** (Desktop·에이전트 없음) | `deploy/compose`를 로컬용으로 복사, `BUZZ_COMPOSE_TLS` 미설정(Caddy 제외), `BUZZ_BIND_ADDR=127.0.0.1:3000`, `RELAY_URL=ws://localhost:3000`, `BUZZ_AUTO_MIGRATE=true`, 시크릿 로컬 생성 → `./run.sh start` | ① `curl -fsS http://127.0.0.1:3000/_liveness` 200 ② `curl -H 'Accept: application/nostr+json' http://127.0.0.1:3000`가 **NIP-11 JSON 반환** ③ 5개 컨테이너 healthy 유지 10분 | 컨테이너 crash loop / 마이그레이션 실패 → **판정 A를 "불가능"으로 하향하고 중단.** 이후 스파이크 전부 무의미 | 중간 (이미지 pull, 수백 MB) |
| **S4** | **헤드리스 AUTH 챌린지 수신** | 아무 WS 클라이언트로 `ws://127.0.0.1:3000` 접속만. **서명 불필요** | 접속 후 **5초 이내에 `["AUTH","<challenge>"]` 프레임 수신** | 챌린지가 안 오면 §1.3 이해가 틀린 것 → 재조사. 이 단계 실패는 브리지 설계 전제 붕괴 | 매우 낮음 |
| **S5** | **NIP-42 인증 완주** | `buzz-admin generate-key`로 키 발급 → kind 22242 이벤트에 `["relay", RELAY_URL]` + `["challenge", …]` 태그 넣고 Schnorr 서명 → `["AUTH", event]` 전송. Python이면 `pynostr`(coincurve, Windows 지원) 사용 가능 여부도 같이 확정 | **`["OK","<event-id>",true,""]` 수신**, 연결이 5초 후에도 유지 | `auth-required: verification failed` → 먼저 `relay` 태그와 relay의 `RELAY_URL` 설정 일치 여부 확인. 그래도 실패하면 **판정 B를 "불명"으로 하향** | 낮음 |
| **S6** | **채널 구독 + 왕복 1회** ← **가장 중요한 게이트** | 채널 1개 생성(`buzz-cli` 또는 Desktop), `["REQ","s1",{채널 필터}]` 구독 → `EOSE` 수신 → 사람이 채널에 메시지 게시 → bridge가 `["EVENT","s1",…]` 수신 → kind 9 EVENT 서명해 게시 → **다시 읽히는지 확인**. **구독/게시 kind를 실측 채록**(1 vs 9 vs 40002 vs 40007 불일치 해소) | **인바운드 이벤트 1건 수신 + 아웃바운드 메시지 1건이 채널에 보임.** 실제 kind 번호 확정 | 채널 이벤트가 안 오면 §1.3의 "전역 구독 제외" 경계 재확인 → 그래도 실패면 **판정 B "불명"** | 중간 |
| **S7** | **결합 — 최소 bridge 왕복** | S6 + S1 결합. 채널 @mention → bridge → `claude -p --output-format stream-json` → 응답을 kind 9로 게시 | **채널에서 @mention 1건 → 에이전트 응답 1건이 같은 채널에 게시됨** | 여기서만 실패하면 인프라가 아니라 어댑터 문제 → 반복 개선 가능. 중단 사유 아님 | 중간 |
| **S8** | *(선택)* **Desktop 접속** | `BUZZ_CORS_ORIGINS`에 `tauri://localhost,http://tauri.localhost` 추가 후 재시작 → Windows Desktop(alpha-unsigned)으로 join | join 성공 + 채널 메시지가 UI에 보임 | 실패해도 **전체 중단 사유 아님**(S6/S7이 이미 통과). Desktop 대신 `web/` 또는 Jarvis Console로 대체 판단 | 낮음 |
| **S9** | *(선택)* **전원 사이클 내성** | PC 재부팅 → 컨테이너 자동 기동 → bridge 재접속 시 presence/구독 복구 확인 | 수동 개입 없이 S6 왕복 재현 | 실패 시 "PC 켜져 있는 동안만" 전제에 **재기동 절차 문서화**가 추가로 필요 | 낮음 |

**중단 게이트 요약**: **S3 실패 = 판정 A 붕괴, 즉시 중단.** **S5 또는 S6 실패 = 판정 B가 "가능"에서 "불명"으로 하향, 재조사 필요.** **S7·S8·S9 실패는 중단 사유가 아니다.**

---

## 7. 미확인 항목

1. **Buzz Desktop 채널 메시지의 실제 kind 번호.** countdown-bot은 kind 1 구독, `buzz-acp`는 9/40007/46010 구독, task-0038은 40002(`KIND_STREAM_MESSAGE_V2`)를 확인했다. **소스에서 확정하지 못했다.** → S6에서 실측 필요.
2. **Redis / MinIO를 실제로 뺐을 때 relay가 어디서 실패하는가.** `config.rs`가 `Option`이 아니라는 것은 확인했으나, 기동 시 즉시 패닉인지 첫 사용 시점 실패인지는 확인하지 못했다. (어느 쪽이든 "생략 가능"은 아니다.)
3. **`ghcr.io/block/buzz` 이미지의 실제 아키텍처 매니페스트와 Docker Desktop/WSL2에서의 기동 여부.** Dockerfile과 CI 설명으로 Linux amd64/arm64를 추정했을 뿐 이미지를 pull하지 않았다(제약 준수).
4. **Typesense를 뺀 상태에서 검색 기능이 얼마나 저하되는가.** `deploy/compose`에 서비스가 없고 relay `config.rs`에 필드가 없다는 것까지만 확인.
5. **루트 `.env.example`에 `BUZZ_CORS_ORIGINS`가 실제로 존재하는지.** 이슈 #2872는 #2617이 루트 `.env.example`에 문서화했다고 하나, fetch 요약에서는 해당 변수가 **없다**고 나왔다. 요약 도구의 누락 가능성이 있어 확정하지 못했다.
6. **`buzz-ws-client`의 REQ/구독 구현 위치.** `connection.rs`에는 EVENT 게시와 AUTH만 있고 REQ가 없었다 — 구독 로직이 `buzz-sdk` 또는 `buzz-acp` 쪽에 있는지 확인하지 못했다.
7. **`codex app-server`의 안정성.** `--help`에 `[experimental]`로 표기됨. 스키마 생성기가 있다는 것까지만 확인, 실제 프로토콜 안정성은 미확인.
8. **세 CLI의 stream-json 메시지 스키마 상세**(필드명, 툴 호출 이벤트 형태, 오류 표현). `--help` 수준까지만 확인 — S1에서 실측 필요.
9. **`pynostr`의 최신 버전/유지보수 상태**(PyPI 페이지 로드 실패). GitHub README에서 NIP-42 지원과 coincurve/Windows 언급만 확인.
10. **PC 재부팅 후 presence·구독 복구 동작**(Buzz 불변식 ③⑤와의 상호작용).
11. **`BUZZ_REQUIRE_AUTH_TOKEN=true`가 로컬에서 필요한지 / `BUZZ_API_TOKEN` 발급 절차.** `deploy/compose/.env.example`에 존재는 확인했으나 로컬 최소 설정에서의 필요 여부는 미확인.
12. **task-0045의 미확인 항목 중 #4491(Windows 설치판 `buzz-acp` 누락)의 현재 상태** — 이번 조사는 ACP 경로를 배제하는 방향이라 재확인하지 않았다.

---

## 8. 참고 출처

**Buzz 소스·설정 (raw.githubusercontent.com / api.github.com, 전부 2026-08-27 fetch)**
- `block/buzz` 저장소 메타 — star 31,033 / open issue 3,202 / Apache-2.0 / push 2026-08-27T08:59:17Z
- [`crates/buzz-relay/src/protocol.rs`](https://github.com/block/buzz/blob/main/crates/buzz-relay/src/protocol.rs) — ClientMessage/RelayMessage 프레임 정의
- [`crates/buzz-relay/src/connection.rs`](https://github.com/block/buzz/blob/main/crates/buzz-relay/src/connection.rs) — 연결 라이프사이클, AUTH_TIMEOUT, 하트비트
- [`crates/buzz-relay/src/router.rs`](https://github.com/block/buzz/blob/main/crates/buzz-relay/src/router.rs) — 라우트 표, `nip11_or_ws_handler`
- [`crates/buzz-relay/src/handlers/auth.rs`](https://github.com/block/buzz/blob/main/crates/buzz-relay/src/handlers/auth.rs) — NIP-42 검증, NIP-OA auth 태그
- [`crates/buzz-relay/src/config.rs`](https://github.com/block/buzz/blob/main/crates/buzz-relay/src/config.rs) — database_url/redis_url/media/cors_origins/mesh 필드
- [`crates/buzz-ws-client/src/{connection.rs, message.rs}`](https://github.com/block/buzz/tree/main/crates/buzz-ws-client/src) — tokio-tungstenite 클라이언트, `EventBuilder::auth`
- [`crates/buzz-acp/README.md`](https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md) — 하네스 파이프라인, 환경변수
- [`crates/buzz-cli/README.md`](https://github.com/block/buzz/blob/main/crates/buzz-cli/README.md) — JSON in/out, 종료코드, 명령군
- [`examples/README.md`](https://github.com/block/buzz/blob/main/examples/README.md) 및 [`examples/countdown-bot/{README.md, Cargo.toml}`](https://github.com/block/buzz/tree/main/examples/countdown-bot) — **비-ACP 직결 봇 공식 예제**
- [`deploy/compose/{README.md, compose.yml, .env.example}`](https://github.com/block/buzz/tree/main/deploy/compose) — 자체호스팅 스택
- 루트 [`docker-compose.yml`](https://github.com/block/buzz/blob/main/docker-compose.yml), [`Dockerfile`](https://github.com/block/buzz/blob/main/Dockerfile), [`.env.example`](https://github.com/block/buzz/blob/main/.env.example)
- [`ARCHITECTURE.md`](https://github.com/block/buzz/blob/main/ARCHITECTURE.md) — 연결 5단계, 구독 3티어, Known Limitations
- [`NOSTR.md`](https://github.com/block/buzz/blob/main/NOSTR.md) — 구현 NIP 목록, proactive challenge
- [`docs/remote-agents.md`](https://github.com/block/buzz/blob/main/docs/remote-agents.md) — Layer 1 런처 계약
- GitHub Releases API — `desktop-v0.5.20` (2026-08-26) 자산 목록

**이슈 (원문 확인)**
- [Issue #3490 — Windows desktop cannot join a self-hosted relay (`http://tauri.localhost` CORS)](https://github.com/block/buzz/issues/3490) — **2026-07-29 개설, 2026-08-27 현재 OPEN**
- [Issue #2872 — deploy/compose default BUZZ_CORS_ORIGINS omits Tauri webview origins](https://github.com/block/buzz/issues/2872) — **2026-07-25 개설, 2026-08-27 현재 OPEN**, 신고자가 오리진 2개 추가로 해결 확인

**프로토콜 스펙**
- [NIP-42 — Authentication of clients to relays](https://nips.nostr.com/42) — kind 22242, relay/challenge 태그, ±10분, `auth-required:` / `restricted:` 접두
- [NIP-01 — Basic protocol flow description](https://nips.nostr.com/1)

**클라이언트 라이브러리**
- [holgern/pynostr](https://github.com/holgern/pynostr) — NIP-42 포함 32개 NIP 지원, *"using coincurve instead of secp256k1, so pynostr can be used on windows"*
- [nostr-tools (PyPI)](https://pypi.org/project/nostr-tools/) — 대안 Python 클라이언트

**로컬 직접 실행 (2026-08-27, 본 조사 세션)**
- `claude --help`, `codex --help`, `codex exec --help`, `codex app-server --help`, `agy --help` — 설치·설정 변경 없이 도움말만 실행

**선행 조사**
- `reports/task-0038-ai-agent-collaboration-platform-buzz-research.md`, `reports/task-0038-gpt-team-synthesis.md`, `reports/task-0045-acp-feasibility-research.md`

---

## 9. 최종 판정

### A. 로컬 Buzz Relay/WebSocket 실행 가능 여부 — 🟡 **조건부 가능**

**가능하다. 단 "Relay 하나"가 아니라 "컨테이너 5개"이고, Docker Desktop(WSL2)이 사실상 필수 전제다.**

근거:
- ✅ `deploy/compose`가 *"a VPS or single-node server environment"*를 대상으로 한 **단일 노드 스택**이고, ARCHITECTURE.md도 *"one host, one relay process, one implicit community"*를 자체호스팅 기본값으로 명시한다. Hostinger 같은 특정 벤더에 의존하는 요소는 조사에서 발견되지 않았다.
- ✅ VPS 고유 요소(공개 DNS·TLS/Caddy·80/443 개방·24/7 가동·원격 접속)는 **전부 로컬에서 생략 가능**하다. Caddy는 `BUZZ_COMPOSE_TLS=true`일 때만 붙는 별도 compose 파일이다. `RELAY_URL=ws://localhost:3000`이 upstream 기본값이다.
- 🔴 **조건 1**: Postgres·Redis·MinIO는 `config.rs`에서 `Option`이 아닌 필수 필드이고 media 비활성화 토글도 없다. **코드 수정 없이 "더 가볍게" 만들 수 없다.**
- 🔴 **조건 2**: standalone relay 바이너리 릴리스가 없다. relay는 Linux 컨테이너(`ghcr.io/block/buzz`)로만 배포되며 Windows 네이티브 이미지가 없다 → **Docker Desktop + WSL2 설치가 선행 조건**(Owner 승인이 필요한 환경 변경).
- 🟡 **조건 3**: Windows Desktop을 붙이려면 `BUZZ_CORS_ORIGINS`에 `tauri://localhost,http://tauri.localhost`를 추가해야 한다(#3490/#2872, 둘 다 OPEN). **다만 이는 설정 한 줄이고, 신고자가 해결을 확인했으며, WebSocket 경로에는 애초에 적용되지 않는다.** task-0038이 이 결함을 "Phase 2 전면 중단" 게이트로 놓은 것은 Desktop을 필수로 가정했을 때만 타당하다.
- ⚠️ Windows Desktop 설치본은 `alpha-unsigned`이며, Windows Defender 오탐 전례(#3612)가 있다.

→ **문서·소스 근거로는 "가능"이지만, 실제 기동은 확인하지 않았다(제약 준수). S3이 이 판정을 확정하거나 무너뜨린다.**

### B. 로컬 Agent Bridge 방식의 기술적 가능성 — 🟢 **가능** (설계 수준 근거 확보, 실측 미완)

**`buzz-acp`도 ACP도 구조적으로 필수가 아니다. Buzz upstream이 비-ACP 직결 봇을 공식 예제로 제공한다.**

근거:
1. **프로토콜이 공개 스펙이다.** `protocol.rs`의 프레임은 NIP-01/42/45 표준뿐이고 **Buzz 전용 비표준 프레임이 없다.** 리버스 엔지니어링 리스크 0.
2. **upstream이 직접 증명했다.** `examples/countdown-bot` — *"connects directly to the Buzz relay over WebSocket, authenticates with NIP-42, subscribes to one channel, and replies"*, *"direct WebSocket + NIP-42 instead of MCP"*. 의존성은 `tokio-tungstenite` + `nostr` + `buzz-sdk`뿐이고 ACP는 등장하지 않는다.
3. **`buzz-acp`를 해부하면 7단계 중 ACP 고유 구간은 1개뿐이다.** ①키 로드 ②WS 접속 ③NIP-42 ④REST 채널조회+구독 ⑤@mention 필터 ⑦EVENT 게시는 전부 프로토콜 일반 동작이고, ⑥(에이전트 서브프로세스 프로토콜)만 교체 대상이다.
4. **relay는 런처를 신경 쓰지 않는다.** `docs/remote-agents.md`: *"The relay authenticates the keypair and the auth tag — never the launcher"*, *"a bash script, a systemd unit, a CI job … is a conforming launcher."*
5. **교체될 ⑥의 대체재가 세 CLI 모두에 존재한다** — 로컬 `--help`로 직접 확인: `claude --output-format stream-json --input-format stream-json`(양방향 NDJSON), `codex exec --json` + `codex app-server`, `agy --output-format stream-json --input-format stream-json`. **ACP가 없다는 사실이 "붙일 수 없다"를 뜻하지 않았다.**
6. **Windows 실행환경도 유리하다.** ACP 경로가 겪는 Windows 문제(#4491 하네스 누락, #3612 Defender 오탐, #2342 PATH 프로브, Zed의 좀비 node.exe)는 **전부 Node.js 기반 ACP 브리지 계층에서 발생한다.** 그 계층을 제거하면 문제도 사라진다. Python 쪽은 `pynostr`이 coincurve를 써서 명시적으로 Windows를 지원한다.

**남은 실질 미지수는 하나뿐이다: "어떤 kind를 구독·게시해야 Desktop 채널에 정상으로 보이는가"** (countdown-bot=1, buzz-acp=9/40007/46010, task-0038=40002 불일치). 이는 S6 한 번으로 해소된다.

**정직한 한계**: 이 판정은 **소스·문서·공식 예제 근거이며, 실제로 붙여본 결과가 아니다.** S5·S6을 통과하기 전까지 "가능"은 설계 판단이지 검증된 사실이 아니다.

### C. 실제 구현 전에 필요한 최소 핸즈온 스파이크

**§6의 S1~S7이 필수, S8·S9는 선택.** 요약:

| 순서 | 스파이크 | PASS 신호 | FAIL 시 |
| --- | --- | --- | --- |
| **S1** | CLI stdio 왕복 (Buzz 무관, 설치 0) | 세 CLI에서 유효 NDJSON/JSONL result 수신 + 스키마 채록 | 해당 CLI만 제외 |
| **S2** | Docker Desktop/WSL2 전제 확인 | Linux 엔진 확인 | **Owner 승인 필요 사항으로 에스컬레이션** |
| **S3** | Relay 단독 기동 (Desktop·에이전트 없음) | `/_liveness` 200 + NIP-11 JSON + 5컨테이너 10분 healthy | 🔴 **판정 A 붕괴 → 전체 중단** |
| **S4** | 헤드리스 WS 접속 (서명 불필요) | 5초 내 `["AUTH","<challenge>"]` 수신 | 설계 전제 붕괴 → 재조사 |
| **S5** | NIP-42 인증 완주 (kind 22242) | `["OK","<id>",true,""]` + 연결 유지 | 🔴 **판정 B → "불명" 하향** |
| **S6** | **채널 구독 + 왕복 1회 + kind 실측** | 인바운드 1건 수신 + 아웃바운드 1건 채널 노출, kind 확정 | 🔴 **판정 B → "불명" 하향** |
| **S7** | 결합: @mention → bridge → claude → 채널 게시 | 왕복 1회 성립 | 어댑터 문제, 중단 사유 아님 |
| S8 *(선택)* | Desktop 접속 (`BUZZ_CORS_ORIGINS` 2개 추가) | join 성공 | **중단 사유 아님** — Desktop은 필수 전제가 아님 |
| S9 *(선택)* | 재부팅 후 자동 복구 | 수동 개입 없이 S6 재현 | 재기동 절차 문서화 추가 |

**S1은 인프라 비용이 0이므로 가장 먼저 실행할 것.** S3 실패 시 S4 이후는 전부 무의미하므로 즉시 중단한다.

---

## 10. 금지 표현 점검

"완벽하게 동작함", "문제 없음", "전체 완료" 표현을 사용하지 않았다.
확인된 사실은 소스 경로·이슈 번호·스펙 원문과 함께 제시했고, 확인하지 못한 것은 §7에 **미확인**으로 명시했다. 판정 A·B는 모두 **문서·소스 근거이며 실기동 검증이 아니라는 점**을 각 항목에 명시했다.
