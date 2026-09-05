# task-0046-local-buzz-relay-agent-bridge-feasibility

- id: `task-0046-local-buzz-relay-agent-bridge-feasibility`
- title: `Hostinger/VPS 없이 Windows 로컬 PC에서 Buzz Relay/WebSocket + Agent Bridge로 Claude Code/Codex/Gemini 연결 가능성 조사`
- status: `DONE`
- created_at: `2026-08-27 13:00 UTC`
- updated_at: `2026-08-28 11:20 UTC`
- repo: `jarvis-core`
- summary: `조사 완료. VPS 없이 Windows 로컬 PC 한 대에서 Buzz Relay를 돌리고 ACP를 우회하는 local agent bridge로 CLI들을 붙이는 것이 소스·문서 근거상 성립한다. 근거는 Relay WebSocket이 표준 NIP-01/42/45라는 점, upstream이 ACP 없는 공식 봇 예제를 제공한다는 점, 세 CLI 모두 자체 stdio 기계판독 프로토콜을 갖는다는 점이다. 다만 Postgres/Redis/MinIO가 필수 필드라 Docker Desktop이 사실상 전제다. 판정은 조건부 가능이며 S1~S7 스파이크가 필수다. Owner 결정으로 즉시 실행은 보류하고 task-0047로 분리했다. 전체 원문은 아래 요약(원문) 절에 보존했다.`
- source_command: `Direct instruction via Claude Code session (task-0046, no Discord channel tag)`

---


## 요약 (원문)

이 절은 task-0054에서 옮긴 원본 summary 전문이다. summary 필드가 500자 상한을 넘어 canonical 검증에 실패했기 때문이며, 내용은 한 글자도 줄이지 않고 그대로 보존했다.

조사 완료. Hostinger/VPS 없이 Windows 로컬 PC 한 대에서 Buzz Relay를 돌리고 ACP를 완전히 우회하는 local agent bridge로 Claude Code/Codex/agy를 붙이는 것은 소스·문서 근거상 성립한다. 결정적 근거 3가지: (1) Relay WebSocket은 Buzz 고유 프로토콜이 아니라 표준 NIP-01/42/45이고 비표준 프레임이 없다(crates/buzz-relay/src/protocol.rs), (2) Buzz upstream이 ACP·MCP 없이 WS+NIP-42로 직결하는 공식 봇 예제 examples/countdown-bot을 제공한다, (3) task-0045가 "ACP 미지원"으로 확인한 세 CLI 모두 자체 stdio 기계판독 프로토콜을 갖고 있다(로컬 --help 직접 확인: claude/agy는 --input-format/--output-format stream-json 양방향 NDJSON, codex는 exec --json + app-server). 반대로 로컬화 비용은 task-0038 추정보다 크다 — Postgres/Redis/MinIO는 config.rs에서 Option이 아닌 필수 필드라 코드 수정 없이 뺄 수 없고, standalone relay 바이너리 릴리스가 없어 Docker Desktop(WSL2) Linux 컨테이너가 사실상 필수다. Windows CORS 결함 #3490/#2872는 둘 다 현재 OPEN이나 설정 한 줄 문제이며 헤드리스 WebSocket 경로에는 적용되지 않는다. 판정 — A) 로컬 Buzz Relay/WebSocket 실행: 조건부 가능(컨테이너 5개 + Docker Desktop 전제, Caddy/DNS/TLS/24h는 전부 생략 가능). B) 로컬 Agent Bridge: 가능(buzz-acp 7단계 중 ACP 고유 구간은 1개뿐이며 그 대체재가 세 CLI에 모두 존재. 단 설계 근거이지 실기동 검증은 아님). C) 최소 스파이크 S1~S7 필수 + S8/S9 선택 — S1 CLI stdio 왕복(설치 0, 최우선) / S2 Docker 전제 / S3 Relay 단독 기동(실패 시 전체 중단) / S4 AUTH 챌린지 수신 / S5 NIP-42 완주 / S6 채널 구독 왕복 + kind 실측(가장 중요한 게이트) / S7 bridge 결합 왕복. Owner 결정 필요 사항: Docker Desktop 설치 승인 여부와 S1~S7 스파이크 착수 여부(= task-0038 Phase 2 게이트 G1/G2를 ACP 경로에서 WebSocket 직결 경로로 대체할지). 보고서: reports/task-0046-local-buzz-relay-agent-bridge-feasibility.md. 이번 조사에서 설치/구현/API키 발급/외부연결/코드 변경 없음. work-order: prompts/task-0046-local-buzz-relay-agent-bridge-feasibility-work-order.md. [2026-08-28 09:00 UTC Owner 결정] 조사 결과(표준 Nostr WebSocket + countdown-bot 직결 사례)를 중요 발견으로 확정 기록. 단 지금 즉시 Docker Desktop 설치나 S1~S7 스파이크를 실행하지 않는다 — 먼저 승인된 Phase 1 범위(task-0041~0044)를 완료한 뒤, 별도 승인 하에 스파이크를 진행한다. Phase 2 Gate G2는 ACP 경로 단독이 아니라 WebSocket 직결 Agent Bridge 경로도 포함하도록 재정의됨(task-0038 보고서에 반영, 아래 참고). 후속 스파이크 실행은 task-0047(TODO, Phase 1 완료 및 별도 승인 후 착수)로 분리 추적. [2026-08-28 11:20 UTC 정정] 위 "먼저 승인된 Phase 1 범위(task-0041~0044)를 완료한 뒤"라는 문구는 task-0039가 Phase 1 완료 게이트를 "6개 하위 task 중 4개 이상"으로 확정(2026-08-28 10:40 UTC)하기 전에 쓰인 구버전 표현이다. 현재 확정 기준은 task-0039와 docs/master-plan.md를 따른다: Phase 1은 task-0040+task-0041+task-0043+task-0045 = 4/6로 이미 완료됐고, task-0042(서명키)/task-0044(감사 해시체인)는 선택적 잔여 항목이며 Phase 1 완료의 필수 선행조건이 아니다. task-0047의 실제 착수(Docker Desktop 설치 + S1~S7 스파이크)에는 이와 별개로 여전히 Owner의 명시적 착수 승인이 필요하다.

## [2026-08-28 06:15 UTC] append — task-0047 실기동 검증 완료, 판정 B가 "설계 근거"에서 "실측 확인"으로 격상

이 섹션은 append-only 기록이다. 위 원본 조사 결과(판정 A/B/C, §9 등)는 수정하지 않는다.

이 문서 §9 판정 B는 원래 "🟢 가능 (설계 수준 근거 확보, 실측 미완)"이었고, 원문이 스스로 "이 판정은 소스·문서·공식 예제 근거이며, 실제로 붙여본 결과가 아니다. S5·S6을 통과하기 전까지 '가능'은 설계 판단이지 검증된 사실이 아니다"라고 명시했다. **task-0047(로컬 Buzz Relay + Agent Bridge 핸즈온 스파이크)가 이 문서의 S1~S7 스파이크 목록(§6)을 실행해 그 실측을 완료했다.** 상세 실행 로그와 근거는 `memory/tasks/task-0047-local-buzz-relay-handson-spike.md`의 append 섹션을 참조.

**실측 결과 요약 (전부 PASS)**:
- S1 CLI stdio 왕복(claude/codex/agy) — PASS
- S2 Docker Desktop/WSL2 전제 — PASS
- S3 Relay 단독 기동(5개 컨테이너, liveness/readiness/NIP-11) — PASS
- S4 헤드리스 AUTH 챌린지 수신 — PASS
- S5 NIP-42 인증 완주 — PASS
- S6 채널 구독 + 왕복 + kind 실측 — PASS
- S7 local Agent Bridge 결합 왕복(실제 claude CLI 서브프로세스 호출, 스텁 아님) — PASS

**이번 실측으로 새로 확정된 사실 (이 문서 §7 미확인 항목 정정)**:
- §7 항목 1 "Buzz Desktop 채널 메시지의 실제 kind 번호" — **확정: kind 9 (KIND_STREAM_MESSAGE)**. 클라이언트가 제출한 kind 9 메시지가 relay에서 변환 없이 그대로 저장·재브로드캐스트됨을 실측 확인. task-0038이 추정한 kind 40002(V2)로의 변환도, countdown-bot 예제의 kind 1도 아니었다.
- 이 문서에 없던 새 제약 하나를 실측으로 추가 발견: 채널이 생성되기 전에는 그 channel_id로 구독(REQ)할 수 없다(`restricted: not a channel member`). 채널 생성(kind 9007) → 구독 순서가 필수다.
- 채널 생성 시 relay가 발행하는 사이드카 이벤트 kind(39000/39001/39002/40099)를 실측 채록함 — 이 문서 초안에는 없던 신규 관측치다.

**"향후 구현 결정"과 "실제 구현 완료"의 명확한 구분** (혼동 방지):
- task-0047이 검증한 것은 **로컬 환경에서 Relay + WebSocket + NIP-42 + 채널 왕복 + CLI 서브프로세스 결합이 실제로 동작하는가**이며, 이것은 "실기동 가능성 검증"이다.
- task-0047은 **jarvis-core에 실제 Agent Bridge를 구현하지 않았다.** S7에서 사용한 bridge 스크립트는 jarvis-core 저장소 밖의 1회성 검증 스크립트이며 jarvis-core 애플리케이션에 통합되지 않았다.
- 따라서 이 문서의 판정 B는 "🟢 가능 (설계 근거)"에서 **"🟢 가능 (실측 확인, 로컬 스파이크 기준)"으로 격상**하되, "Jarvis-Core에 Agent Bridge를 실제로 구현할지"는 여전히 별도의 Owner 결정 사항으로 남는다. 실기동 검증 완료가 곧 구현 승인을 의미하지 않는다.

**task-0038과의 관계**: 이 실측 결과는 task-0038이 정의한 Phase 2 Gate G2(WebSocket 직결 Agent Bridge 경로)의 실기동 근거가 된다. task-0038 report에 별도 append 기록.

---

## [2026-08-28 17:40 UTC] append — G1/G3 사실관계 확정 (Phase 2 게이트 3종 중 나머지 2개)

이 섹션은 append-only 기록이다. 위 원본 내용과 §[2026-08-28 06:15 UTC] append 섹션은 수정하지 않는다.

task-0038이 정의한 Phase 2 게이트 3종(G1/G2/G3) 중 G2는 위 섹션에서 PASS로 이미 확정됐다.
이번 조사는 나머지 G1(Windows self-host relay + Desktop 접속)과 G3(Buzz 1.0 또는 승인 게이트
executor 완성)의 사실관계를 확정한다. jarvis-core 코드 변경 없음. Owner 확인 하에 CORS/config
계층 재현만 실측했고, unsigned Buzz Desktop 설치파일을 실제로 설치하는 것은 Owner 선택에 따라
이번 조사에서 실행하지 않았다.

**G1_VERDICT: PARTIAL**
- upstream Issue #3490, #2872 — 2026-08-28 기준 여전히 OPEN. 수정 PR #2888("compose 기본값에
  Tauri origin 추가"), #3595("relay가 Desktop WebView origin 항상 허용")도 둘 다 OPEN(미병합).
- `deploy/compose/.env.example`의 `BUZZ_CORS_ORIGINS` 기본값이 오늘도 Tauri origin을 포함하지
  않음(소스 재확인).
- 로컬 실측(Docker relay, task-0047과 동일 compose 재사용, jarvis-core 밖 scratchpad, 종료 시
  `down -v`로 잔존물 없음 확인): (1) 기본 설정 → mac/Windows origin 둘 다 CORS 차단, (2) macOS
  가이드식 설정(`tauri://localhost`만 추가) → mac origin만 허용되고 **Windows origin
  (`http://tauri.localhost`)은 여전히 차단** = Issue #3490을 정확히 재현, (3) 워크어라운드
  (`http://tauri.localhost` 추가) → Windows origin도 허용으로 전환.
- Issue #2872 코멘트(DanTup, 2026-07-26) "Edit2: 내 Windows PC에서 시도해보니 정상 연결됨"이
  이 워크어라운드가 실제 Windows Desktop 앱 연결을 되살린다는 제3자 실사용 증거.
- localhost 접속만으로 충분(HTTP/TLS 불요) — DanTup·#3490 원 보고자 모두 TLS 없는 환경에서
  재현했고, task-0047 S3의 결론과도 일치.

**G3_VERDICT: FAIL**
- upstream `ARCHITECTURE.md` §9 Known Limitations #5(2026-08-28 재확인, 원문): "Approval gates
  not wired end-to-end — executor는 `StepResult::Suspended`를 반환하고 relay에 grant/deny API가
  있지만, engine이 `WaitingApproval` row를 만들기 전에 가로채 승인 게이트에 도달한 run은 Failed로
  처리됨." task-0038이 원래 확인한 것과 실질적으로 동일 — 개선 없음.
- 최신 릴리스 여전히 `desktop-v0.5.20`(1.0 미달), CHANGELOG·공개 PR/이슈 검색에 approval gate
  관련 진행 중인 작업 없음.
- task-0038 게이트 표 기준 G3 FAIL은 🟡(비차단) — "통합하되 승인은 100% Jarvis 소유"이며, 이는
  Jarvis-Core가 Phase 1부터 이미 채택한 원칙과 정확히 일치해 추가로 요구되는 비용이 없다.

**PHASE2_GATE_STATUS 종합**: G1 PARTIAL(🔴 즉시중단 조건 아님, 배포 config에 CORS origin 명시
필요) / G2 PASS(위 섹션) / G3 FAIL(🟡 비차단, Jarvis 승인 독점 원칙 유지로 충족). 세 게이트 중
어느 것도 task-0038이 정의한 🔴 즉시중단 조건을 트리거하지 않았다.

**중요한 구분**: 이 판정은 "Phase 2 통합을 지금 시작해도 된다"는 승인이 아니라 "G1/G3의
사실관계가 확정됐다"는 것뿐이다. 실제 Phase 2 구현 착수는 이 조사와 별개의 Owner 결정을 그대로
요구한다.
