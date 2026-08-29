# task-0047-local-buzz-relay-handson-spike

- id: `task-0047-local-buzz-relay-handson-spike`
- title: `Docker Desktop 기반 로컬 Buzz Relay + WebSocket Agent Bridge 핸즈온 스파이크 (S1~S7)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-28 09:00 UTC`
- updated_at: `2026-08-28 06:15 UTC`
- summary: `task-0046(로컬 Buzz Relay/Agent Bridge 조사) 결과를 실제로 손으로 검증하는 스파이크. 목표는 Hostinger/VPS가 아니라 Windows 로컬 PC 한 대에서 Buzz Relay + WebSocket + Local Agent Bridge가 실제 동작하는지 확인하는 것(task-0046 §6 스파이크 목록: S1 CLI stdio 왕복 → S2 Docker 전제 확인 → S3 Relay 단독 기동 → S4 AUTH 챌린지 → S5 NIP-42 완주 → S6 채널 구독 왕복+kind 실측 → S7 bridge 결합 왕복. S8/S9는 선택). 착수 조건: (1) Phase 1 완료 조건 충족(task-0039 기준, 6개 하위 task 중 4개 이상 — 현재 task-0040+task-0041+task-0043+task-0045로 4/6 충족, task-0042/task-0044는 선택적 잔여 항목이며 필수 선행조건 아님), (2) Docker Desktop 설치를 포함한 별도 Owner 승인. 착수 시 이 스파이크의 목적은 task-0038 Phase 2 Gate G2를 "ACP 경로 단독"이 아니라 "WebSocket 직결 Agent Bridge 경로 포함"으로 재정의한 근거(task-0038 §6.0 addendum, 2026-08-28)를 실기동으로 검증하는 것이다. 실제 Buzz 통합 구현은 이 스파이크가 성공한 뒤에만 결정한다. 현재는 착수 전(TODO). [2026-08-28 11:20 UTC 정정] 착수 조건 (1)의 "Phase 1(task-0041~0044) 완료"라는 구버전 표현은 task-0039가 Phase 1 완료 게이트를 "6개 중 4개 이상"으로 확정(2026-08-28 10:40 UTC)하기 전에 쓰인 문구였다. task-0039와 docs/master-plan.md 기준으로 Phase 1은 이미 완료됐다(task-0040+task-0041+task-0043+task-0045 = 4/6). task-0042/task-0044는 선택적 잔여 항목으로 계속 진행 가능하나 이 스파이크의 착수를 막지 않는다. 남은 유일한 착수 조건은 (2) Docker Desktop 설치 및 핸즈온 스파이크 실행에 대한 별도 Owner 승인이며, 아직 미승인 상태다.`
- source_command: `Owner 직접 지시 (2026-08-28, task-0046 결과 확인 후): "task-0041~0044 완료 후, 별도 승인 하에 Docker Desktop 기반 로컬 Buzz Relay 핸즈온 스파이크(S1~S7)를 진행한다"`

---

## [2026-08-28 06:15 UTC] 실행 결과 — S1~S7 전건 실측 완료, status TODO → DONE

이 섹션은 append-only 기록이다. 위 원본 착수 기록은 수정하지 않았다.

**실행 환경**: Windows 11 로컬 PC, Docker Desktop(WSL2 백엔드), Owner 승인 하 진행. 스파이크에 쓰인 모든 코드·설정 파일은 jarvis-core 저장소 **바깥**의 세션 스크래치패드(`buzz-spike/`)에서만 생성·실행했다. jarvis-core 애플리케이션 코드는 이 스파이크로 전혀 수정되지 않았다.

**중단 지점**: 1차 실행에서 S1(CLI stdio 왕복)은 PASS, S2(Docker 엔진)는 재부팅 필요로 BLOCKED, S3~S7은 미실행 상태로 세션이 종료됨. 재부팅 후 이 실행에서 S2 재검증부터 S7까지 이어서 완료했다.

### S1 — CLI stdio 왕복: **PASS**
- Claude CLI: JSON 왕복 PASS
- Codex CLI: JSON 왕복 PASS
- agy CLI: JSON 왕복 PASS
(1차 실행에서 확인, 이번 재개 세션에서 재검증하지 않음 — 재개 지침상 이미 PASS로 확정된 항목)

### S2 — Docker 전제 확인: **PASS**
- `wsl --status`: `docker-desktop` distro 정상
- `docker info`: `OSType: linux`, WSL2 백엔드, Server Version 29.7.2 정상 응답
- `docker ps`: 정상 응답 (빈 목록) — 엔진 왕복 확인

### S3 — Relay 단독 기동: **PASS**
- block/buzz 저장소의 `deploy/compose/compose.yml`을 스크래치패드로 fetch, 로컬 전용 `.env`(랜덤 생성 시크릿, `RELAY_URL=ws://localhost:3000`, `BUZZ_REQUIRE_AUTH_TOKEN=false`, `BUZZ_REQUIRE_RELAY_MEMBERSHIP=false`, Caddy/TLS 미사용)로 구성
- `docker compose up -d` → `postgres`/`redis`/`minio`/`minio-init`/`relay` 5개 컨테이너 전부 기동, 4개 지속 서비스(`postgres`/`redis`/`minio`/`relay`) 모두 healthy
- `curl http://127.0.0.1:3000/_liveness` → HTTP 200
- `curl http://127.0.0.1:3000/_readiness` → HTTP 200
- `curl -H "Accept: application/nostr+json" http://127.0.0.1:3000/` → NIP-11 JSON 정상 반환 (`supported_nips` 목록에 42 포함)
- 스파이크 종료 시 `docker compose down -v`로 컨테이너·볼륨 전량 정리 완료 (잔존 리소스 없음, `docker ps -a` 재확인)

### S4 — 헤드리스 AUTH 챌린지 수신: **PASS**
- 서명 없는 순수 WebSocket 클라이언트(Node `ws`)로 `ws://localhost:3000/` 접속만 수행
- 접속 직후 `["AUTH","<challenge>"]` 프레임을 클라이언트 요청 없이 선제 수신 (task-0046 §1.3의 "proactive AUTH challenge" 서술과 실측 일치)

### S5 — NIP-42 인증 완주: **PASS**
- `nostr-tools`(순수 JS, `@noble/curves` 기반 — 네이티브 빌드 불필요)로 로컬 키페어 생성
- kind 22242 이벤트에 `["relay","ws://localhost:3000"]`, `["challenge","<challenge>"]` 태그를 넣고 Schnorr 서명 → `["AUTH", event]` 전송
- `["OK","<event-id>",true,""]` 수신, 연결이 인증 타임아웃(5초) 이후에도 유지됨을 확인

### S6 — 채널 구독 + 왕복 + kind 실측: **PASS** (가장 중요한 게이트)
- **1차 시도 실패 관찰**: 채널을 생성하기 전에 그 `channel_id`로 `["REQ","sub1",{"#h":[channel_id]}]` 구독을 걸었더니 `["CLOSED","sub1","restricted: not a channel member"]`로 거부됨. 이는 task-0046 문서에 명시되지 않았던 순서 제약이며, 이번 실측으로 새로 확정한 사실이다.
- **성공한 순서**: 채널 생성(kind 9007, NIP-29 create-group 관례, 태그 `["h",channel_id]`+`["name",...]`) → 구독(REQ) → EOSE → 메시지 게시(kind 9, 태그 `["h",channel_id]`)
- 자신이 게시한 메시지가 동일 구독을 통해 그대로 되돌아옴을 확인 (content 마커 일치)
- **채널 생성 시 relay가 자동 발행하는 사이드카 이벤트를 실측 채록**: kind 39000(NIP-29 그룹 메타데이터: name/visibility/type), 39001(관리자 목록), 39002(멤버 목록), 40099(Buzz 자체 시스템 메시지, `content={"actor":<pubkey>,"type":"channel_created"}`)
- **채널 메시지의 실제 kind = 9 (KIND_STREAM_MESSAGE)** — relay가 그대로 저장·재브로드캐스트함을 실측 확인. task-0038이 추정했던 kind 40002(KIND_STREAM_MESSAGE_V2)로의 변환은 관찰되지 않았고, countdown-bot 예제의 kind 1도 아니었다. `crates/buzz-core/src/kind.rs`의 실제 소스 주석과도 일치. → task-0046 §7의 미확인 항목 #1을 실측으로 확정.

### S7 — local Agent Bridge 결합 왕복: **PASS**
- 채널에 `@agent` 멘션이 포함된 메시지 게시
- bridge 스크립트가 해당 이벤트를 감지 → **실제 `claude -p --output-format json` 서브프로세스를 호출**(스텁/목업 아님, 실제 모델 API 호출 및 실비용 발생)
- 실제 모델 응답 수신 → 서명된 kind 9 이벤트로 재게시(`["e", 원본_event_id]` 태그로 스레드 연결)
- 동일 WebSocket 구독(`sub1`)에서 그 응답 이벤트를 수신 — 전 구간이 stub 없는 실제 왕복임을 확인
- **Windows 관련 구현 실측 (향후 실제 bridge 구현 시 참고용, 이번에는 구현하지 않음)**:
  - `claude`는 npm이 만든 `claude.cmd` shim이므로 Node `child_process.execFile('claude', ...)`을 `shell:true` 없이 호출하면 `spawn EINVAL`로 실패한다.
  - `shell:true` + 배열 인자로 프롬프트를 argv에 직접 넣으면 Node가 인자를 이스케이프하지 않고 그대로 이어붙이므로(Node `DEP0190` 경고), `@`/`:`/`[]` 등 특수문자가 포함된 프롬프트가 셸에서 잘못 분리되어 claude가 빈 프롬프트로 오인하는 것을 실측으로 확인했다(1차 실행에서 "your message came through empty" 응답 관찰).
  - **해결**: `claude -p` 호출 시 위치 인자로 프롬프트를 넘기지 않고, 자식 프로세스의 **stdin으로 프롬프트 텍스트를 전달**하면(`claude -p --output-format json`, 위치 인자 생략 시 stdin에서 프롬프트를 읽음) 특수문자가 그대로 보존되어 정확한 왕복이 확인됨(2차 실행에서 정확한 토큰 응답 확인).

### G2 (task-0038) — WebSocket Direct Path: **PASS**
S3~S7 전 구간이 스텁 없이 실측으로 통과했으므로, task-0038이 정의한 "Phase 2 Gate G2(WebSocket 직결 Agent Bridge 경로)"는 로컬 환경에서 **실제 동작으로 PASS**했다. 상세 근거와 범위 한정은 task-0038 report 및 task-0046 memory 문서의 별도 append 기록을 참조.

### 명시적 한계 (금지 표현 점검)
- **이번 스파이크에서 실제 Agent Bridge 구현은 하지 않았다.** S7에서 사용한 bridge 스크립트는 jarvis-core 저장소 밖 스크래치패드의 1회성 검증 스크립트이며, jarvis-core에 통합되지 않았다.
- S8(Desktop 접속)·S9(재부팅 내성)는 선택 항목으로 이번 범위에서 실행하지 않았다(지침에 따라 실행 금지).
- 실제 jarvis-core 통합 여부는 이 스파이크 결과와 별개로 Owner의 후속 결정 사항이다.
- "완벽하게 동작함", "문제 없음", "전체 완료" 같은 과장 표현을 쓰지 않았다. PASS는 각 항목에 기재된 구체적 실측 근거(HTTP 상태 코드, 수신한 프레임, kind 번호, 이벤트 id)에 한정된다.
