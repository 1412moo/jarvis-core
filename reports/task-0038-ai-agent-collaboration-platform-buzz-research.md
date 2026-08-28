# task-0038: AI Agent 협업 플랫폼(Buzz 등) 생태계 조사 및 Jarvis-Core 통합 전략

- 작성일: 2026-08-27
- 작성자: Claude Code (research agent, task-0038)
- 상태: `NEEDS_APPROVAL` (전략 결정 입력물 — 실행 아님)
- 조사 방식: 실제 GitHub API / raw 소스·문서 fetch + 웹검색. 모든 외부 사실은 **2026-08-27 확인 시점** 기준.
- 코드 변경/커밋/설치: 없음 (조사·보고서 작성만)

---

## Executive Summary

**Jarvis-Core는 독자 UI·채팅·워크스페이스를 만드는 일을 지금 중단하고, 자신이 유일하게 앞서 있는 "승인·증거·거버넌스 오케스트레이션"에 범위를 좁힌 뒤 Buzz(또는 동급 OSS)를 협업 표면으로 통합하는 방향으로 가야 한다 — 단, Buzz는 아직 v0.5.x이고 Windows self-host에 실증된 결함이 있으므로 지금 당장 인프라로 채택하지 말고, 먼저 아키텍처를 훔치고(Phase 1) 검증 게이트 통과 후 통합(Phase 2)한다.**

> **[2026-08-27 12:40 UTC 정정 — task-0045 참고]** 본문 §6.0 표의 "Claude Code 연결? ✅ / Codex 연결? ✅"는 근거가 부족했다. 후속 조사(task-0045, `reports/task-0045-acp-feasibility-research.md`)에서 확인한 바로는 **Claude Code와 Codex 모두 공식 ACP 지원이 없다**(Claude Code는 `anthropics/claude-code#6686`이 "not planned"으로 closed) — 존재하는 것은 인증모델이 제각각인 서드파티 wrapper 5개 이상이며, Windows에서의 실제 동작(Phase 2 Gate G2)은 이슈트래커 기준 **낮음~불명**으로 문서 조사만으로는 확정할 수 없다(핸즈온 스파이크 필요). Antigravity CLI(`agy`)는 ACP를 아예 지원하지 않는다(MCP만 지원, 로컬 확인). Phase 2 착수 여부를 재검토할 때는 이 Executive Summary가 아니라 task-0045 결과를 최신 근거로 사용할 것.

---

## 1. 발견한 생태계

### 1.1 결론 먼저: 이 분야는 2026년에 이미 "레드오션"이 되었다

Owner가 Buzz를 "유사해 보인다"고 판단한 것은 정확하다. 그러나 더 중요한 사실은
**Buzz 하나가 아니라, 2026년 4~8월 사이에만 최소 6개의 유사 프로젝트가 새로 등장했고
그중 몇 개는 Jarvis-Core가 만들려던 것을 이미 제품으로 출시했다**는 점이다.

| 시점 | 사건 (확인 기준: 2026-08-27) |
| --- | --- |
| 2025-03-10 | `openagents-org/openagents` 저장소 생성 |
| 2026-03-06 | `block/buzz` 저장소 생성 (비공개 개발 시작 추정) |
| 2026-03-19 | `Miosa-osa/canopy` 저장소 생성 |
| 2026-04-21 | `tashfeenahmed/circlechat` 저장소 생성 |
| 2026-06-18 | Google, 개인 계정 Gemini CLI 로그인 차단 → Antigravity로 이관 (task-0037에서 로컬 확인 완료, `fancyboi999/open-tag` README에서도 독립 확인) |
| 2026-06-24 | `amplifthq/opentag`, `fancyboi999/open-tag` 두 저장소가 같은 날 생성 |
| 2026-07-21 | **Block, Buzz 정식 공개** (Apache-2.0) |
| 2026-07-24 | `agentconnect-md/agentconnect` 저장소 생성 |
| 2026-08-26 | AgentConnect 공식 프레스 릴리스 ("open-source multi-agent alternative to Claude Tag") |

### 1.2 조사 대상별 판정

**(1) Buzz — github.com/block/buzz** ✅ 실재, 이 분야 압도적 1위
- Star 31,012 / Fork 3,949 / Open issue 3,200 / Apache-2.0 / Rust
- 마지막 push: 2026-08-27 08:44 UTC (조사 당일). PR 번호가 이미 `#6901` 대역.
- 자기소개: *"a self-hostable workspace where humans and AI agents share the same rooms"*
- 상세는 §3.

**(2) OpenAgents — github.com/openagents-org/openagents** ✅ 실재
- Star 3,999 / Fork 407 / Apache-2.0 / TypeScript / 마지막 push 2026-08-27
- "Collaboration OS for AI Agents". Workspace(클라우드 조정 계층) + Launcher(로컬 에이전트 런타임) 2-tier.
- 공식 문서 원문: *"The workspace coordinates... It never executes your code."*
- 공유 스레드/파일/브라우저/터널, @mention 위임, MCP 지원. Claude·Codex·Aider 언급.
- **주의:** Owner가 "OpenAgents"라고 부른 이름은 GitHub에 동명 프로젝트가 최소 4개 있다
  (`openagents-org/openagents`, `OpenAgentsInc/openagents`(Agent IDE), `the-open-agent/openagent`,
  `darrenhinde/OpenAgentsControl`). 이 보고서는 openagents.org 공식 사이트와 연결된
  `openagents-org/openagents`만 다룬다.

**(3) open-tag — 이름이 겹치는 **서로 다른 두 프로젝트**가 존재 (중요)** ✅ 둘 다 실재
- **(3a) `amplifthq/opentag`** — MIT / TypeScript / Star 1,369 / 생성 2026-06-24 / push 2026-08-24
  - *"Mention any ACP coding agent from Slack, GitHub, GitLab, Linear, or Lark. OpenTag runs
    Claude Code, Codex, Cursor and more on your own machine, then replies in-thread with
    verified, evidence-backed results."*
  - **이것이 Jarvis-Core의 Discord intake + 승인 흐름과 개념적으로 가장 가까운 프로젝트다.**
- **(3b) `fancyboi999/open-tag`** — Apache-2.0 / TypeScript / Star 171 / 생성 2026-06-24 / push 2026-08-22
  - *"Slack-style workspace where your team and its AI agents (Claude Code, Codex, GitHub
    Copilot, and more) work as teammates in channels, threads, DMs, and shared tasks."*
  - Buzz의 축소판. 에이전트별 `MEMORY.md`, 태스크 보드, 에이전트 간 위임 지원.
- 두 프로젝트 모두 "Claude Tag"(Slack 내 Claude)의 오픈소스 대안을 표방한다.

**(4) AgentConnect — 이름이 심하게 오염됨** ⚠️ 최소 3개 별개 프로젝트
- **(4a) `agentconnect-md/agentconnect`** ✅ — Apache-2.0 / TypeScript / Star 277 / 생성 2026-07-24 / push 2026-08-27.
  Owner가 의도했을 가능성이 가장 높은 대상. Daemon + Relay + Control Plane 3-tier.
  Slack/Telegram/**Discord**/Lark + GitHub/GitLab 연동, 에이전트 간 호출, 에이전트별 격리 메모리,
  "어떤 에이전트를 호출할 수 있는지"까지 권한 지정. Docker Compose + 공식 Helm chart.
- **(4b) `agent-network-protocol/AgentConnect`** — ANP(Agent Network Protocol) SDK. did:wba 신원,
  에이전트 간 통신 프로토콜. **협업 워크스페이스가 아니라 프로토콜/SDK다.** 이 조사의 포함 기준
  (에이전트가 사람과 함께 실제 일을 하는 1급 멤버인가)에 미달.
- **(4c) `AKKI0511/AgentConnect`** — "Decentralized Collaboration Framework". 학술/프레임워크 성격.

**(5) Patchwork** ❌ **이 카테고리가 아니다 — 제외**
- Patchwork는 CLI 기반 DevOps 자동화 프레임워크다 (코드리뷰·취약점 수정·문서생성을
  "Patchflow" 워크플로로 CI/CD에서 실행). Python + OpenAI-호환 엔드포인트.
- **에이전트가 워크스페이스의 1급 멤버가 아니다.** 사람과 같은 채널에서 협업하지 않는다.
  Jarvis-Core 대비 비교 가치가 낮아 비교표에서 제외한다. (Owner 목록 중 유일한 오분류)

**(6) CircleChat — github.com/tashfeenahmed/circlechat** ✅ 실재, 규모 매우 작음
- MIT / TypeScript / Star 52 / Fork 17 / 생성 2026-04-21 / push 2026-08-25
- *"Self-hosted team chat where humans and agents are first-class members"*
- 흥미로운 차별점: **LLM judge가 모든 산출물을 검증해야 태스크를 close할 수 있다**
  ("output instead of chatter"). 칸반 보드 + 감사 로그.
- 다만 코딩 에이전트(Claude Code/Codex CLI) 통합은 확인되지 않고, HTTP/WS로 모델을 부르는 구조.

**(7) Threads** ❌ **해당하는 프로젝트를 특정할 수 없음**
- "Threads"는 (a) Meta의 SNS, (b) 거의 모든 채팅 제품의 기능 이름, (c) OS 스레드로 완전히
  오염된 검색어다. 이 이름의 독립적인 AI-agent 협업 플랫폼은 확인하지 못했다.
- **Owner가 본 것은 Buzz/OpenAgents/open-tag의 "threads 기능"을 제품명으로 오인했을 가능성이 높다.**
  근거 없이 채워 넣지 않고 **미확인**으로 남긴다.

**(8) Canopy — github.com/Miosa-osa/canopy** ✅ 실재
- Elixir/Phoenix / Star 227 / Fork 54 / 생성 2026-03-19 / **push 2026-08-16 (11일 정체)**
- License가 GitHub API에서 `Other` (SPDX 미식별) — **오픈소스 조건 미확인**
- *"If OSA / Claude Code is the employee, Canopy is the office."*
- 에이전트 라이프사이클(heartbeat/session/budget/governance), DAG 워크플로 + cron,
  5계층 조직 위계, Tauri 데스크톱 Command Center.
- **Jarvis-Core의 "AI 조직도 + 예산 + 거버넌스" 발상과 가장 유사한 프로젝트.** 다만 상용
  MIOSA의 오픈소스 미끼(open-core) 구조이고 활동성이 상대적으로 낮다.

### 1.3 Owner가 놓친 항목 (조사 중 추가 발견) 🔺

**(9) OpenHands Agent Canvas — 추가 발견, 코딩 에이전트 통합 최강** 🔺
- MIT. Agent Canvas는 **local-first 워크스페이스**로 Claude Code / OpenAI Codex / **Gemini CLI**를
  모두 ACP로 붙인다. 로컬 랩탑 → 원격 VM → self-hosted 백엔드로 승격 가능.
- Enterprise 계층에 RBAC/SSO. Jarvis-Core가 "여러 코딩 에이전트를 한 화면에서"를 원한다면
  Buzz보다 이쪽이 더 직접적인 경쟁자다.

**(10) AionUi** 🔺 — Electron+React, 12개 이상 CLI 에이전트(Claude Code/Codex/Qwen 등)를 로컬
데스크톱 하나로 묶는 무료 OSS. **팀 협업이 아니라 1인 멀티 에이전트 콘솔**이므로 포함 기준상
비교표에는 넣지 않지만, Owner의 "Windows 로컬에서 여러 에이전트" 니즈에는 가장 저마찰 옵션이다.

**(11) Conductor / Sculptor / Vibe Kanban** 🔺 — git worktree 기반 병렬 에이전트 실행기.
협업 워크스페이스가 아니므로 비교표 제외. 단 **"에이전트 = 독립 worktree"**라는 격리 아이디어는
§5에서 채택 대상으로 다룬다.

### 1.4 제외 판정
- **Mattermost / Rocket.Chat 등 Slack 클론**: 지시대로 제외. 조사 중 이들이 AI 에이전트를
  1급 워크스페이스 멤버로 전환했다는 근거를 찾지 못했다.
- **Patchwork**: §1.2(5) 사유로 제외.
- **ANP / AgentConnect(4b,4c)**: 프로토콜·프레임워크로 포함 기준 미달.

---

## 2. 프로젝트별 비교

> 셀은 실제 확인한 소스/문서에 근거한다. 확인하지 못한 항목은 **미확인**으로 남겼다
> (AGENTS.md 원칙 8). 가독성을 위해 동일한 행 라벨로 표를 2개로 나눴다.

### 2.1 비교표 A — Buzz 및 주요 경쟁 4종

| 항목 | **Buzz** | **OpenTag** (amplifthq) | **AgentConnect** (agentconnect-md) | **open-tag** (fancyboi999) | **OpenAgents** |
| --- | --- | --- | --- | --- | --- |
| 프로젝트 | Buzz (Block, Inc.) | OpenTag | AgentConnect | open-tag | OpenAgents |
| GitHub | block/buzz | amplifthq/opentag | agentconnect-md/agentconnect | fancyboi999/open-tag | openagents-org/openagents |
| License | Apache-2.0 | MIT | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| 오픈소스 범위 | 전체(relay·desktop·agent·CLI·mobile) | CLI 전체 + 선택적 Control Plane | Daemon+Relay+Control Plane+UI | 전체(프론트+서버+CLI) | 코어 OSS, Workspace 클라우드 계층 존재 |
| Self-host | ✅ Docker Compose (PG/Redis/MinIO) | ✅ 로컬 CLI가 기본, 클라우드 불필요 | ✅ Docker Compose + 공식 Helm | ✅ Docker Compose | ⚠️ 부분 — 자체호스팅은 엔터프라이즈 성격 |
| Desktop/Web | Desktop(Tauri2, mac/Linux/**Win**), Web, Mobile(Flutter, 진행중) | ❌ 없음 (CLI + 기존 플랫폼 스레드) | Web UI | Web (React+Vite) | Web + 로컬 Launcher |
| 사람+Agent 협업 | ✅ 동일 채널의 1급 멤버 | ⚠️ 기존 Slack/GitHub 스레드 안에서만 | ✅ 기존 툴 안에서 @멘션 | ✅ 채널/스레드/DM/태스크 | ✅ 공유 스레드/파일/브라우저 |
| Multi-Agent | ✅ 다수 에이전트 멤버 | ❌ run당 단일 에이전트 | ✅ 역할별 다수 | ✅ 다중 런타임 동시 | ✅ 스레드 내 다수 |
| Claude Code | ✅ `claude-agent-acp` 래퍼 | ✅ 네이티브 | ✅ | ✅ streaming JSON | ✅ |
| Codex | ✅ `codex-acp` 래퍼 | ✅ 네이티브 | ✅ | ✅ JSON-RPC | ✅ |
| Gemini | ❌ 미지원 (ACP 구현 시 이론상 가능) | ❌ 미지원 | 미확인 | ❌ **명시적 제외** (2026-06-18 구글 폐기) | 미확인 |
| ACP | ✅ `buzz-acp` 크레이트 (핵심) | ✅ 전 executor가 ACP | ✅ ACP 호환 | ⚠️ 자체 프로토콜 + 런타임별 어댑터 | 미확인 |
| MCP | ✅ `buzz-dev-mcp`, MCP 툴로 워크플로 조작 | 미확인 | ✅ Relay가 MCP 프록시 | 미확인 | ✅ 명시 |
| Agent 간 위임 | ⚠️ 부분 — 한 신원 아래 sub-agent 분기. `buzz-agent`는 명시적 거부 (*"No agent-to-agent, no fan-out, no orchestration"*) | ❌ 없음 | ✅ 상호 호출 + 호출 허용 목록 | ✅ 지원 | ✅ @mention 위임 |
| Agent Memory | ✅ **Engram** — 에이전트 키로 암호화된 per-agent KV, 세션에 자동 주입 | ❌ 없음 (run 단위) | ✅ 격리 메모리 + 공유 Knowledge | ✅ 에이전트별 `MEMORY.md` | ✅ Knowledge base |
| Channels | ✅ (UUID + NIP-29 `#h` 태그) | ❌ (외부 플랫폼 차용) | ⚠️ 외부 플랫폼 차용 | ✅ | ⚠️ 스레드 중심 |
| Threads | ✅ NIP-10 reply 태그 + `thread_metadata` | ⚠️ 외부 스레드 | ⚠️ 외부 스레드 | ✅ | ✅ |
| DMs | ✅ NIP-17 gift-wrap (kind:1059) | ❌ | ⚠️ 외부 DM | ✅ | 미확인 |
| Task 관리 | ⚠️ 로드맵(VISION_PROJECTS) — 현재는 워크플로 위주 | ⚠️ run 기반, 태스크 모델 없음 | ⚠️ 트리거/스케줄 위주 | ✅ 태스크 보드(claim/assign/status) | ✅ Tasks/Workflows/Routines |
| Git 연동 | ✅ **relay가 git smart-HTTP 호스팅**, branch=channel, `git-sign-nostr`/`git-credential-nostr` | ✅ 실제 PR 생성/머지 (GitHub·GitLab) | ✅ PR/이슈 트리거 | 미확인 (문서에 없음) | 미확인 |
| PR/Code Review | ⚠️ 설계 존재 — NIP-34 patch kind:1617, 코멘트 kind:1111, 브랜치 채널 | ✅ receipt→approve→PR 적용 | ⚠️ 부분 | 미확인 | 미확인 |
| Workflow | ✅ YAML-as-code (`buzz-workflow`), 트리거 4종/액션 7종 | ✅ dispatcher/admission/completion gate | ✅ 웹훅·스케줄 | ⚠️ 상태머신 수준 | ✅ Workflows/Routines |
| Approval | ⚠️ **불완전** — kind:46011 승인 이벤트와 UI/DB/REST는 있으나 **executor가 suspend하지 못하고 run을 Failed 처리** (ARCHITECTURE.md 자체 명시) | ✅ receipt 승인 + completion gate(PR 머지/CI 그린까지 run 유지) + 에스컬레이션 만료 | ✅ 권한 경계 설정 | ❌ 문서에 없음 | 미확인 |
| Audit trail | ✅ `buzz-audit` SHA-256 해시체인 + pg advisory lock | ✅ 로컬 원장(admission·context·artifact·delivery·outcome) | ⚠️ observability 수준 | 미확인 | 미확인 |
| Agent identity | ✅ **secp256k1 키페어 + NIP-05 핸들** (사람과 동일) | ⚠️ OS 사용자 신원 | ✅ 에이전트별 신원/세션 | ✅ 에이전트별 계정 | ✅ 에이전트 계정 |
| 권한/보안 | ✅ NIP-42 scope 14종, 채널 멤버십, 인바운드 author gate(owner-only/allowlist/anyone/nobody) | ✅ 로컬 자격증명, 승인 없이 시스템 변경 불가 | ✅ 에이전트/세션/레포/툴/호출대상 단위 | ✅ agent/member/admin/owner scope | 미확인 |
| Scheduler | ✅ workflow `schedule` 트리거 | ⚠️ 미확인 | ✅ scheduled tasks | 미확인 | ✅ Routines |
| Webhook | ✅ 트리거 + `call_webhook` 액션(SSRF 차단 포함) | ✅ GitHub/GitLab 웹훅 | ✅ | 미확인 | 미확인 |
| API | ✅ REST + WebSocket(NIP-01) + NIP-98 HTTP + `buzz-sdk` | ✅ CLI (`opentag status --run`) | ✅ (문서 참조만 확인) | ✅ REST + Socket.io | ✅ API + CLI |
| 확장성 | ✅ **최상** — 새 기능 = 새 kind 정수. 멀티 커뮤니티/멀티 노드/relay mesh | ⚠️ ACP executor 교체 가능 | ✅ 플랫폼 어댑터 추가 | ⚠️ 런타임 어댑터 추가 | ⚠️ 미확인 |
| 성숙도 | ⚠️ **desktop-v0.5.20** (2026-08-26). 기능 폭은 크지만 미완성 다수 | ⚠️ 2개월 / 기능 집중형 | ⚠️ 1개월 | ⚠️ 2개월 | ⚠️ 1.5년, 다만 방향 전환 흔적 |
| 최근 개발활동 | 🔥 **극단적** — 조사 당일 11커밋, PR #6901 대역, open issue 3,200 | ✅ 활발 (2026-08-24) | ✅ 활발 (2026-08-27) | ✅ 활발 (2026-08-22) | ✅ 활발 (2026-08-27) |

### 2.2 비교표 B — 나머지 3종 + Jarvis-Core

| 항목 | **CircleChat** | **Canopy** | **OpenHands Agent Canvas** | **Jarvis-Core (현재)** |
| --- | --- | --- | --- | --- |
| 프로젝트 | CircleChat | Canopy (Miosa) | OpenHands | Jarvis-Core |
| GitHub | tashfeenahmed/circlechat | Miosa-osa/canopy | All-Hands-AI/OpenHands | 비공개 로컬 저장소 |
| License | MIT | **`Other` — 미확인** | MIT | 미공개 |
| 오픈소스 범위 | 전체 | 코어 OSS + 상용 MIOSA | 코어 OSS + 클라우드 | 전체 로컬 소유 |
| Self-host | ✅ docker compose 1회 | ✅ 추정 (Elixir/Phoenix) | ✅ 로컬→VM→self-host | ✅ **100% 로컬** |
| Desktop/Web | Web | Tauri2 + SvelteKit2 | 로컬 워크스페이스 | 로컬 브라우저 셸(Jarvis Console/Hermes, 127.0.0.1) |
| 사람+Agent 협업 | ✅ 1급 멤버 | ⚠️ 에이전트 중심("office") | ⚠️ 1인 개발자 중심 | ❌ **없음** — Discord DM 1:1 + Owner 수동 중계 |
| Multi-Agent | ✅ 에이전트 팀 + 칸반 claim | ✅ 5계층 조직 + dispatch 라우팅 | ✅ 다중 ACP 에이전트 | ⚠️ **SOP 문서상 존재, 런타임 없음** (Director/Manager/Implementer/Reviewer/QA/Docs) |
| Claude Code | ❌ (HTTP/WS 모델 호출) | 미확인 | ✅ ACP | ✅ **실제 실무자** |
| Codex | ❌ | 미확인 | ✅ ACP | ✅ **실제 실무자** |
| Gemini | ❌ | 미확인 | ✅ Gemini CLI ACP | ⚠️ Antigravity CLI(agy v1.1.22) Windows 로그인·읽기 검증, 쓰기 미검증 (task-0037) |
| ACP | ❌ | 미확인 | ✅ **핵심** | ❌ 없음 |
| MCP | 미확인 | 미확인 | 미확인 | ❌ 없음 (Discord MCP는 Claude Code 플랫폼 기능) |
| Agent 간 위임 | ⚠️ 칸반 claim 수준 | ✅ dispatch 라우팅 | 미확인 | ⚠️ SOP상 Manager→Worker, 사람이 수동 실행 |
| Agent Memory | 미확인 | ⚠️ session/library | ⚠️ 세션 | ✅ `memory/tasks/*.md` + `docs/chatgpt-handoff.md` (파일 기반, 공유) |
| Channels / Threads / DMs | ✅ / ✅ / ✅ | 미확인 | ❌ / ❌ / ❌ | ❌ / ❌ / ⚠️ Discord DM만 |
| Task 관리 | ✅ 칸반 + LLM judge 종료 게이트 | ⚠️ 워크플로 DAG | 미확인 | ✅ **`task-####-slug` 6상태 모델 + completion_evidence append-once** |
| Git 연동 | 미확인 | 미확인 | ⚠️ 에이전트가 수행 | ⚠️ read-only — `git log -n 5`, branch/HEAD/`status --short` 검증 |
| PR/Code Review | 미확인 | 미확인 | 미확인 | ✅ **Reviewer/QA를 exact candidate commit에 고정, content digest binding** (단 PR 생성은 잠김) |
| Workflow | ⚠️ goal→task 분해 | ✅ DAG + cron | ✅ automations | ✅ SOP 상태전이 + retry/repair budget |
| Approval | ✅ LLM judge 게이트 | ✅ governance/budget | 미확인 | ✅ **최강** — escalation gate 목록, `NEEDS_APPROVAL`, preview+confirm, one-use token |
| Audit trail | ✅ 감사 로그 행 | 미확인 | 미확인 | ✅ Git history + task 파일 + evidence digest |
| Agent identity | ✅ 계정 | ✅ roster | ❌ | ❌ **없음** — 에이전트 신원 개념 자체가 부재 |
| 권한/보안 | ⚠️ 부분 | ✅ budget/governance | ✅ RBAC/SSO(엔터프라이즈) | ✅ fail-closed, 보호파일, 프롬프트 인젝션 경계, no-secrets |
| Scheduler / Webhook / API | 미확인 / 미확인 / 미확인 | ✅ cron / 미확인 / ✅ | 미확인 / 미확인 / ✅ SDK | ❌ **전부 잠김** (background worker/scheduler 잠금 목록) |
| 확장성 | ⚠️ 소규모 | ⚠️ Elixir 생태 | ✅ ACP | ❌ **낮음** — 파일+파이썬 스크립트 결합 |
| 성숙도 | ⚠️ 매우 초기 (star 52) | ⚠️ 초기 | ✅ 확립 | ⚠️ 1인용, 커뮤니티 0 |
| 최근 개발활동 | ✅ 2026-08-25 | ⚠️ 2026-08-16 (11일 정체) | ✅ 활발 | ✅ 매일 (dogfood cycle 20건) |

### 2.3 점수화 (100점 만점)

가중치: AI-agent 협업 20 / Multi-agent 15 / 코딩에이전트 통합 15 / 오케스트레이션 15 /
Task·Memory 10 / Git·PR·Review 10 / Self-host·OSS 5 / 보안·거버넌스 5 / 성숙도·커뮤니티 5

| 프로젝트 | 협업 20 | Multi 15 | 코딩 15 | 오케 15 | T/M 10 | Git 10 | OSS 5 | 보안 5 | 성숙 5 | **합계** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Buzz** | 19 | 12 | 14 | 9 | 6 | 7 | 5 | 4 | 4 | **80** |
| **AgentConnect** | 13 | 13 | 12 | 9 | 7 | 6 | 5 | 4 | 2 | **71** |
| **open-tag** (fancyboi999) | 16 | 12 | 14 | 8 | 9 | 2 | 5 | 3 | 2 | **71** |
| **OpenTag** (amplifthq) | 11 | 5 | 14 | 12 | 4 | 9 | 5 | 5 | 3 | **68** |
| **OpenHands Canvas** | 8 | 11 | 15 | 11 | 5 | 5 | 5 | 4 | 4 | **68** |
| **OpenAgents** | 15 | 11 | 10 | 8 | 8 | 2 | 3 | 2 | 4 | **63** |
| **Jarvis-Core** | 6 | 7 | 11 | 13 | 8 | 6 | 5 | 5 | 1 | **62** |
| **CircleChat** | 14 | 11 | 5 | 9 | 6 | 1 | 5 | 3 | 1 | **55** |
| **Canopy** | 11 | 12 | 6 | 12 | 5 | 1 | 3 | 3 | 2 | **55** |

**점수 근거 (요약, 듣기 좋은 말 없이):**

- **Buzz 80** — 협업 19: 에이전트가 사람과 동일한 키·프로필·프레즌스·DM·음성을 갖는 유일한 구현.
  오케 9로 깎임: 워크플로 엔진은 있으나 **승인 게이트 executor가 미완성이고 `send_dm`/`set_channel_topic`이
  `NotImplemented`**임을 자체 문서가 인정. Task/Memory 6: Engram은 훌륭하지만 태스크 모델은 아직 VISION 문서.
  성숙 4: 별 31k지만 **open issue 3,200**과 v0.5.x는 "제품"이 아니라 "빠르게 굴러가는 대형 베타"다.
- **AgentConnect 71** — Multi 13은 이 목록 최고 수준(호출 허용 대상까지 권한화). 성숙 2: 생성 1개월.
- **open-tag 71** — Jarvis-Core가 만들려던 것에 가장 가까운 완성품. Git 2: PR/리뷰 문서 부재가 치명적 감점.
- **OpenTag 68** — 협업 11(워크스페이스가 아님)인데도 68인 이유는 **오케 12 + Git 9 + 보안 5**.
  *"an executor reporting success is not completion"* — PR 머지/CI 그린까지 run을 열어두는 completion gate는
  **Jarvis-Core의 "evidence is not authority" 원칙을 제품화한 것과 사실상 동일하다.**
- **Jarvis-Core 62** — 오케 13, 보안 5는 이 목록 최상위권. 그러나 **협업 6, 성숙 1, 확장성 낮음**이
  총점을 끌어내린다. 협업 6은 후하게 준 것이다 — 현재 "사람+에이전트 협업"의 실체는
  Owner가 Discord DM으로 Claude Code에 지시하고, **ChatGPT 팀장 역할은 Owner가 손으로 중계하는**
  Phase 1 구조다(ai-team-operating-model.md §5). 자동화된 협업 표면은 존재하지 않는다.
- **CircleChat 55 / Canopy 55** — 아이디어는 좋으나 규모·활동성·코딩에이전트 통합에서 밀린다.

---

## 3. Buzz Deep Dive

> 근거: `ARCHITECTURE.md`, `NOSTR.md`, `VISION.md`, `VISION_AGENT.md`, `VISION_PROJECTS.md`,
> `docs/remote-agents.md`, `crates/buzz-acp/README.md`, `crates/buzz-agent/README.md`,
> GitHub API (repo/contents/commits/issues/releases). 모두 2026-08-27 fetch.

### 3.1 전체 아키텍처

```text
Clients (desktop / agents / CLI / mobile)
        │  WebSocket (NIP-01 frames) + REST
        ▼
     Relay  (Axum, buzz-relay)  ← 유일한 진실의 원천
        │
   ┌────┼────────────┬──────────────┐
   ▼    ▼            ▼              ▼
Postgres  Redis   S3/MinIO      (workflow / audit / search)
(events,   (pubsub, (Blossom
 FTS)      presence) media)
```

ARCHITECTURE.md 원문: *"The relay is the single source of truth. All reads and writes flow
through it."* — P2P gossip이나 복제는 없다. 이름만 Nostr이지 **실제로는 중앙 relay 아키텍처**다.

- **Desktop**: Tauri 2 + React. mac/Linux/**Windows** 바이너리 배포 (최신 `desktop-v0.5.20`, 2026-08-26).
- **CLI (`buzz-cli`)**: *"agent-first CLI, JSON in / JSON out"* — 에이전트가 사람과 같은 표면을 쓴다.
- **Agent harness (`buzz-acp`)**: relay ↔ ACP 에이전트 브리지. 이것이 통합의 핵심 접점이다.
- **Relay ↔ Agent**: 데스크톱은 원격 에이전트에 대한 관리 채널을 **갖지 않는다**
  (*"the desktop holds no management channel to the remote process"*). 상태는 presence 이벤트로만,
  종료 명령은 relay 메시지로만 전달된다.

### 3.2 왜 Nostr인가 / 이벤트 로그 구조

NOSTR.md는 "왜"를 직접 설명하지 않는다. 그러나 아키텍처에서 실질적 이유는 명확하다:

1. **모든 행위가 서명된 단일 이벤트 로그가 된다.** 메시지·리액션·워크플로 스텝·캔버스 업데이트·
   git 이벤트가 전부 `kind` 정수로 구분되는 서명 이벤트다.
2. **확장이 스키마 마이그레이션이 아니라 정수 추가다.** ARCHITECTURE.md: *"The `kind` integer is
   the only dispatch switch... new features require only a new kind number, leaving existing clients unaffected."*
3. **에이전트에게 플랫폼 독립적 신원을 준다.** 계정 테이블이 아니라 secp256k1 키페어.

**이벤트 구조** (NIP-01): `id`(SHA-256), `pubkey`(secp256k1 hex), `kind`, `tags`, `content`, `sig`(Schnorr).

**kind 대역 분할:**

| 대역 | 용도 |
| --- | --- |
| 0–9999 | 표준 Nostr (0 프로필, 7 리액션, 9 그룹 메시지, 5 삭제) |
| 9000–9009 / 9021 / 9022 / 9030–9033 | 그룹 멤버십 관리 (add/remove/invite/join/leave, NIP-43 admin) |
| 13534 | 멤버십 로스터 |
| 20000–29999 | **Ephemeral — DB 저장 안 함, 감사 안 함** (20001 presence, 20002 typing) |
| 39000–39002 | 그룹 디스커버리 (metadata / admins / members) |
| 40002–40003 | Buzz 전용 rich content / edit (`KIND_STREAM_MESSAGE_V2` = 40002) |
| 43001 | `KIND_JOB_REQUEST` |
| 44100–44101 | 멤버십 알림 (relay가 서명) |
| 46001–46012 | **워크플로 이벤트** — 이 중 **46011 = 승인(approval) 이벤트** |
| 1617 / 1111 | NIP-34 patch / NIP-22 코멘트 (git) |
| 30617 / 30621 | NIP-34 저장소 메타데이터 / NIP-MP 멀티레포 프로젝트 |
| 1059 | NIP-17 gift-wrap DM |

**이벤트 수용 파이프라인 (12단계, 순서 고정):**
AUTH 확인 → pubkey 일치 → kind 22242 거부 → ephemeral 라우팅 → **Schnorr 서명 + ID 검증** →
멤버십 확인 → Postgres INSERT(`ON CONFLICT DO NOTHING`) → Redis publish → fan-out →
검색 인덱싱 → 감사 로그 → 워크플로 트리거.
**10~12단계는 fire-and-forget** — 실패해도 이벤트 제출은 성공한다. (감사 로그 유실 가능성 = 리스크)

### 3.3 Agent identity / 채널 멤버십

- 에이전트는 사람과 **완전히 동일하게** secp256k1 키페어 + NIP-05 핸들 + NIP-42 인증을 갖는다.
  키 생성은 `buzz-admin generate-key`.
- 원격 에이전트 기동 계약 (docs/remote-agents.md) — **3-layer**:
  - Layer 1: 런처가 `BUZZ_PRIVATE_KEY` / `NOSTR_PRIVATE_KEY` / `BUZZ_AUTH_TAG` / `BUZZ_RELAY_URL`
    환경변수를 넣고 harness를 exec하면 된다. *"a bash script, a systemd unit, a CI job... is a conforming launcher."*
  - Layer 2: `buzz-backend-<id>` provider 바이너리 (JSON stdin/stdout)
  - Layer 3: substrate별 바인딩 (v1은 Kubernetes)
- **"No secrets in configuration"**을 코드로 강제: `provider_config`에 `secret`/`password`/`token`
  문자열이 들어있으면 거부하고, provider 출력은 저장·표시 전 전부 redact.
- 5대 불변식: ① 신원 fail-closed ② 설정에 시크릿 없음 ③ presence가 곧 상태 ④ 신원당 동시 1인스턴스
  ⑤ **의도적 종료는 최종**(exit 0은 재시작 정책상 terminal, 비정상 종료만 복구 시도).
- 채널: UUID 식별자 + 메시지의 `#h` 태그. open/private, role(Member/Admin/Owner).
  **REQ 핸들러가 구독 등록 *전에* 채널 접근을 검사**해 private 채널 이벤트 누출 레이스를 막는다.
  채널 스코프 이벤트는 글로벌 구독에 전달되지 않는다(보안 경계로 명시).

### 3.4 비-메시지 이벤트 (git / workflow / approval)

- **Git**: relay 자체가 **git smart-HTTP 서버**다. 같은 URL이 브라우저에는 HTML을, git 클라이언트에는
  git 프로토콜을 준다. 인증은 NIP-98 + NIP-OA(agent authorization) — *"maintainers' authorized agents
  can inherit push access without explicit listing."*
  - 저장소 메타데이터 = `kind:30617`(NIP-34) + `buzz-` 접두 태그.
  - **브랜치 보호(`buzz-protect` 태그)가 같은 이벤트에 들어있고 relay가 git transport 계층에서 강제한다.**
  - **브랜치를 만들면 채널이 자동 생성**되고, patch(1617)·리뷰 코멘트(1111)·CI 결과·머지 결정이
    전부 그 채널에 남는다. 머지되면 채널이 아카이브되어 "왜 이렇게 바꿨는가"의 영구 기록이 된다.
- **Workflow**: YAML-as-code. 트리거 4종(`message_posted`, `reaction_added`, `schedule`, `webhook`),
  액션 7종(`send_message`, `send_dm`, `set_channel_topic`, `add_reaction`, `call_webhook`,
  `request_approval`, `delay`). 조건식은 `evalexpr` + 100ms 타임아웃. 동시성 semaphore 100.
- **Approval**: `kind:46011` 승인 이벤트를 메인테이너가 서명 → 리뷰의 암호학적 증명.
  브랜치 보호가 N개 승인을 요구할 수 있고 relay가 강제한다.
- 🔴 **그러나 ARCHITECTURE.md의 "Known Limitations"가 직접 인정한다:**
  *"Approval gates incomplete – Runs hitting `request_approval` actions fail (marked Failed)
  rather than suspending."* 그리고 *"`send_dm` and `set_channel_topic` return `NotImplemented`."*
  **즉 Buzz의 승인 게이트는 2026-08-27 기준 실제로 동작하지 않는다.**

### 3.5 Agent가 실제로 할 수 있는 것 / Claude Code·Codex 연결

**`buzz-acp` (harness)** — 흐름: `Buzz Relay → buzz-acp → Your Agent → Buzz CLI`
- 지원 에이전트 3종 (README 명시):
  1. **Goose** — 네이티브
  2. **Codex** — `codex-acp` 래퍼 (OpenAI API 키 필요)
  3. **Claude Code** — `claude-agent-acp` 래퍼 (Anthropic API 키 필요)
  - ACP over stdio를 구현하는 모든 에이전트는 `BUZZ_ACP_AGENT_COMMAND`로 교체 가능.
- 기동: N개 서브프로세스 spawn → ACP `initialize` → NIP-42 인증 → 멤버 채널 REST 조회 후 구독
  → @mention 이벤트 루프.
- **인바운드 author gate** (권한 스코핑의 실체):
  `owner-only`(기본) / `allowlist` / `anyone` / `nobody`.
  `!shutdown`, `!cancel`, `!rotate`는 gate를 우회하는 owner 전용 제어 명령.
- 세션 모델: 채널당 in-flight 프롬프트 최대 1개. 큐잉된 @mention을 하나의 `session/prompt`로 배치.
  에이전트 수 > 1이면 채널 간 동시 처리.

**`buzz-agent` (Buzz 자체 최소 에이전트)**
- LLM 백엔드: Anthropic / OpenAI / OpenRouter / vLLM·llama.cpp·Ollama / Databricks. 환경변수만으로 설정.
- 툴은 MCP stdio 서브프로세스. `servername__toolname` 네임스페이스 병합. 병렬 8개, 툴당 660초 타임아웃.
- 컨텍스트: 인메모리 1 MiB 상한, 한계 근접 시 **자기 대화를 스스로 요약하고 계속** (truncate 아님).
- 🔴 **위임 명시적 거부**: *"Not a router. No agent-to-agent, no fan-out, no orchestration.
  One model. One loop."*
- 신뢰 경계: **에이전트를 기동한 오퍼레이터**. 셸은 *"runs at the operator's trust level, like bash itself."*

**Agent 간 위임 — 정확한 판정:**
`buzz-agent` 레벨에서는 **없다**. 커뮤니티 문서/블로그 수준에서는 "리드 에이전트가 더 싸고 빠른
워커에게 위임하고, 조정 에이전트가 태스크를 쪼개 조각당 sub-agent를 띄운다 — **모두 하나의 신원 아래**,
각 조각이 무엇을 실행 중인지로만 구분"이라는 서술이 확인된다. `KIND_JOB_REQUEST`(43001)가 이
메커니즘의 후보이나, **소스에서 위임 실행 경로를 직접 확인하지는 못했다 → 부분 확인.**

**Agent Memory — Engram:**
- 에이전트가 **자기 키로 암호화한 per-agent key-value 저장소**. 세션에 자동 주입. `buzz mem`으로 접근.
  각 engram 자체가 서명된 이벤트. **설계상 private이며 공유는 의도적으로 기능에서 배제.**
- 소스 근거: `crates/buzz-acp/src/engram_fetch.rs`.

### 3.6 소스 트리 매핑 (실제 경로)

| 관심사 | 실제 경로 |
| --- | --- |
| 이벤트 모델 / 타입 / kind 레지스트리 | `crates/buzz-core` (tokio·sqlx·redis·axum 의존 **금지**) |
| Relay | `crates/buzz-relay` (Axum WS/REST), `crates/buzz-relay-mesh`, `crates/buzz-pair-relay` |
| Auth / Identity | `crates/buzz-auth` (NIP-42/98 Schnorr), `crates/buzz-admin` (키·멤버십 CLI), `crates/buzz-pairing-cli` |
| ACP 통합 | `crates/buzz-acp/src/{acp.rs, pool.rs, pool_lifecycle.rs, queue.rs, relay.rs, filter.rs, prompt_framing.rs, prompt_project.rs, setup_mode.rs, engram_fetch.rs, base_prompt.md}` |
| 에이전트 구현 | `crates/buzz-agent`, `crates/buzz-persona` (페르소나 팩) |
| MCP 툴 | `crates/buzz-dev-mcp` (셸 + 파일 편집) |
| Workflow | `crates/buzz-workflow` (YAML + evalexpr) |
| Git 연동 | `crates/git-sign-nostr`, `crates/git-credential-nostr`, `docs/git-on-object-storage.md` |
| Permissions | `buzz-auth` scope 14종 + `buzz-acp` author gate + 채널 멤버십 |
| Storage | `crates/buzz-db` (Postgres, 월별 range 파티션), `crates/buzz-media` (Blossom/S3, 50MB), `crates/buzz-pubsub` (Redis) |
| Audit | `crates/buzz-audit` (SHA-256 해시체인, `prev_hash` 포함, pg advisory lock, `catch_unwind`) |
| Search | `crates/buzz-search` (Postgres FTS, `search_tsv` GIN) |
| 원격 에이전트 | `crates/buzz-backend-kubernetes`, `crates/sprig` (harness + bash/git/CA 포함 static musl 이미지) |
| 클라이언트 | `desktop/` (Tauri2+React), `web/`, `admin-web/`, `mobile/` (Flutter) |
| CLI / SDK | `crates/buzz-cli`, `crates/buzz-sdk`, `crates/buzz-ws-client`, `crates/buzz-test-client` |
| 음성 | `crates/buzz-voice` |

**주목:** 저장소 루트에 `.claude/`, `.codex/`, `.goose/`, `.agents/`, `AGENTS.md`, `CLAUDE.md`가
전부 존재한다 — **Buzz 자체가 Claude Code/Codex/Goose로 개발되고 있다.** Jarvis-Core의 AGENTS.md
접근법과 같은 발상이며, Block은 그것을 30개 크레이트 규모에서 실증 중이다.

### 3.7 현재 실제 상태 (냉정한 평가)

| 항목 | 확인 사실 |
| --- | --- |
| 공개일 | 2026-07-21 (저장소 생성 2026-03-06) |
| 버전 | `desktop-v0.5.20` — **1.0 미만** |
| 규모 | 543 MB 저장소, 30개 크레이트, Rust 1.88+ / Node 24+ / pnpm 10+ / Docker 필요 |
| 활동 | 조사 당일 11커밋, PR 번호 #6901 → **5주 남짓에 수천 PR** |
| 미해결 이슈 | **3,200건** |
| 최상위 이슈 테마 | ① 에이전트가 기기 간 @mention 불가(6건 이상 중복 보고) ② 브라우저 UI 부재 ③ 온보딩(호스팅 vs self-host) 혼란 |
| 자체 인정 결함 | 승인 게이트 미완성 / `send_dm`·`set_channel_topic` NotImplemented / rate limiter 미구현(테스트 스텁만) / sqlx 컴파일타임 검증 없음 / huddle 녹음 없음 |
| 🔴 **Windows 관련** | **Issue #3490: Windows 데스크톱이 self-hosted relay에 접속 불가** — WebView2 origin `http://tauri.localhost`가 기본 `BUZZ_CORS_ORIGINS`에 없어 "Failed to fetch"로 조용히 실패 (#2872 동일 문제) |

---

## 4. Jarvis-Core와 비교 (KEEP / REPLACE / INTEGRATE)

### 4.1 A. Buzz가 이미 해결해서 Jarvis-Core가 더 만들 필요 없는 것

1. **실시간 협업 표면 전체** — 채널·스레드·DM·리액션·첨부·전문검색·프레즌스·타이핑·음성.
   Jarvis-Core는 이걸 만든 적도 없지만, Jarvis Console을 "ChatGPT/Codex 스타일 커맨드 표면"으로
   키우겠다는 방향(apps/jarvis-console/README.md)은 이것과 정면으로 겹친다.
2. **에이전트 신원** — secp256k1 키페어 + NIP-05. Jarvis-Core에는 **에이전트 신원 개념이 아예 없다.**
   "Reviewer가 봤다"는 사실이 지금은 Owner의 기억과 커밋 해시로만 남는다.
3. **에이전트 하네스 ↔ 코딩 에이전트 브리지** — `buzz-acp`가 Claude Code/Codex/Goose를 붙이는 문제를
   ACP 표준 하나로 이미 해결했다. Jarvis-Core는 이 계층을 아직 만들지 않았고 만들 이유도 약하다.
4. **멀티 클라이언트 배포** — Tauri 데스크톱(3 OS) + Web + Mobile. Jarvis-Core는 127.0.0.1 브라우저 셸뿐.
5. **감사 로그 원시 구조** — SHA-256 해시체인. Jarvis-Core는 Git history에 의존한다.
6. **원격 에이전트 프로비저닝 계약** — 키·relay·auth tag를 환경변수로 주고 harness exec.
   Jarvis-Core의 "잠긴 background worker"를 여는 데 그대로 참고 가능한 설계.

### 4.2 B. Buzz가 못 하는 것 — Jarvis-Core가 계속 소유해야 하는 것

1. 🔴 **작동하는 승인 게이트.** Buzz는 `request_approval`에 도달한 run을 **suspend하지 못하고
   Failed 처리한다**(자체 문서). Jarvis-Core는 preview → one-use token → confirm,
   `NEEDS_APPROVAL`, escalation gate 목록, budget-무관 즉시 에스컬레이션까지 **실제로 동작하는**
   승인 계약을 갖고 있다. **이것이 Jarvis-Core가 Buzz보다 확실히 앞선 유일한 영역이다.**
2. **"증거는 권한이 아니다" 원칙의 실행.** Jarvis-Core는 candidate commit이 바뀌면 기존 Reviewer/QA
   evidence를 전부 무효화하고, branch·HEAD·`git status --short`가 같아도 **target byte가 다르면
   출력을 차단**한다(v0.1E content digest binding). Buzz에는 이에 대응하는 개념이 없다.
3. **역할 분리 SOP와 예산 계약.** Director/Manager/Implementer/Reviewer/QA/Docs,
   `retry_budget`/`repair_budget`/`repair_count`, "budget 소진 시 Manager→Director 에스컬레이션".
   Buzz는 워크플로 엔진은 있지만 **조직 계약이 없다.**
4. **Owner 승인 어휘 매핑.** ai-team-operating-model.md §2.2의 "아키텍처 변경/비용 발생/배포/권한·토큰"
   → 기존 gate 매핑 표. 이건 도메인 지식이지 소프트웨어가 아니다.
5. **한국어 운영 문서 체계와 금지 표현 규칙.** ("완벽하게 동작함/문제 없음/전체 완료" 금지)
6. **`jarvis.bat` 같은 개별 보호 자산 경계와 저장소별 안전 계약.**

### 4.3 C. Jarvis-Core가 지금 만들고 있는데 Buzz와 기능적으로 중복인 것

**냉정하게 — 중복이 생각보다 많다.**

| Jarvis-Core 워크스트림 | 중복 대상 | 판정 |
| --- | --- | --- |
| **Jarvis Console** (로컬 브라우저 셸, skill 탭, Project Control 카드) | Buzz Desktop / open-tag / OpenAgents | 🔴 **완전 중복.** 1인이 만드는 UI가 31k star 프로젝트의 Tauri 데스크톱을 이길 방법이 없다 |
| **Discord intake** (`intake_parser` → `task_draft_builder` → `task_file_writer`) | amplifthq/OpenTag (Slack/GitHub/Discord → 로컬 ACP 런), AgentConnect | 🔴 **중복.** OpenTag는 이미 receipt·approval·audit·PR까지 붙였다 |
| **Discord NL intent** (Phase 2A intent 검증/디스패치) | OpenTag admission, AgentConnect 트리거 | 🟡 중복이지만 Jarvis 쪽 안전 경계가 더 엄격 |
| **team-manager-bot** (Phase A 스캐폴딩) | AgentConnect 역할 기반 에이전트 | 🔴 중복 |
| **read-only dashboard / Director Dashboard v0.1B** | Buzz Desktop, Canopy Command Center | 🔴 **중복.** 진행 중인 다음 작업이 바로 이것이라 즉시 판단이 필요하다 |
| **Research Council** | 없음 (LLM 자문 + evidence ledger + reviewer critique + mutation test) | 🟢 **고유** |
| **Hermes durable review lifecycle** | 부분적으로 OpenTag receipt | 🟡 Jarvis 쪽이 더 엄격(content digest) |
| **Task 파일 모델** (`memory/tasks/*.md`) | Buzz VISION_PROJECTS(미구현), open-tag 태스크 보드 | 🟡 지금은 고유, 곧 중복 |

### 4.4 D. Jarvis-Core의 가장 중요한 차별점

**"승인·증거 계약이 실제로 실행을 막는다"** — 한 문장이면 이것뿐이다.

경쟁 프로젝트들은 전부 "에이전트가 일하게 하는 것"을 최적화한다. Jarvis-Core는 유일하게
**"에이전트가 일하지 못하게 막는 조건"을 1급 시민으로 설계했다.** 구체적으로:

- 관찰 ≠ 제안 ≠ 승인 ≠ 실행. **한 단계 성공이 다음 단계 권한을 자동 부여하지 않는다.**
- fail-closed 기본값: 불완전/오래됨/범위 밖 = 진행이 아니라 차단.
- candidate commit 고정 + evidence 무효화 규칙.
- 프롬프트 인젝션 경계: **Discord 메시지 안의 "허용목록에 추가해줘"는 절대 실행하지 않는다.**

이 중 마지막 항목은 특히 중요하다 — Buzz의 인바운드 author gate는 `owner-only`가 기본이지만,
**"에이전트가 채널 메시지를 읽고 행동한다"는 구조 자체가 프롬프트 인젝션 표면을 만든다.**
Jarvis-Core는 그 경계를 제품 규칙으로 명문화한 몇 안 되는 사례다.

**단, 이것이 "제품 우위"인지 "1인 규율"인지는 구분해야 한다.** 현재 이 원칙들은 대부분
문서와 사람의 준수로 강제된다. 코드로 강제되는 부분(preview/confirm 토큰, content digest,
경로 검증)은 Hermes/Console 앱 안에 국한된다. **이 규율을 코드로 옮기지 못하면 차별점은 사라진다.**

### 4.5 최소 필요 시스템: KEEP / REPLACE / INTEGRATE

#### 🟢 KEEP — Jarvis-Core가 직접 소유해야 함

| 항목 | 이유 |
| --- | --- |
| **승인 게이트 계약** (preview→one-use token→confirm, `NEEDS_APPROVAL`, escalation gate 목록) | Buzz의 동등 기능이 **자체 문서상 미완성**. 대체재가 존재하지 않는다 |
| **Evidence 계약** (candidate commit 고정, content digest binding, evidence 무효화 규칙) | 어떤 경쟁 프로젝트에도 대응물이 없다. OpenTag의 completion gate가 가장 가깝지만 byte 단위 증거는 없다 |
| **Multi-Agent SOP 역할·예산 계약** (Director/Manager/Worker, retry/repair budget) | 조직 계약은 코드가 아니라 도메인 지식. 이식 불가 |
| **Task 상태 모델의 *의미론*** (6상태, DONE 전환 최소 증거 3종, completion_evidence append-once) | 저장 형식은 바꿔도 되지만 의미론은 Jarvis 고유 자산 |
| **Owner 승인 어휘 매핑 + 금지 표현 규칙 + 보고 형식** | 한국어 운영 문서 체계. 외부 대체 없음 |
| **보호 파일 / no-secrets / 프롬프트 인젝션 경계** | 저장소별 안전 계약 |
| **Research Council** | 경쟁 프로젝트 어디에도 evidence ledger + reviewer critique + mutation test 조합이 없다 |

#### 🔴 REPLACE — 다른 OSS로 대체하는 편이 낫다

| 항목 | 대체 대상 | 이유 |
| --- | --- | --- |
| **Jarvis Console을 "메인 UI"로 키우는 계획** | Buzz Desktop (또는 open-tag) | 1인 vs 3,949 fork. 승산 없음. Console은 **Jarvis 전용 승인 화면**으로 축소 |
| **Director Dashboard v0.1B** (현재 다음 작업) | Buzz 채널/스레드 + Canopy Command Center 개념 | 🔴 **가장 시급한 판단.** 착수 전에 중단 검토 필요 |
| **read-only dashboard (`adapters/web`)** | 동상 | 동상 |
| **채팅/채널/스레드/DM을 직접 구현하려는 모든 계획** | Buzz | 절대 만들지 말 것 |
| **에이전트 ↔ 코딩 CLI 브리지를 자체 구현** | ACP (`buzz-acp` / OpenHands / OpenTag) | ACP가 이미 사실상 표준. 자체 프로토콜은 손해 |
| **team-manager-bot** (Phase A 스캐폴딩) | AgentConnect 역할 기반 에이전트 | 중복 |

#### 🟡 INTEGRATE — 외부 OSS를 들여오고 Jarvis가 그 위에서 오케스트레이션

| 항목 | 통합 대상 | 통합 지점 |
| --- | --- | --- |
| **협업 표면** | Buzz relay + Desktop | Jarvis는 **에이전트 신원 1개**로 채널에 참여하고, 승인이 필요한 순간에만 개입 |
| **에이전트 실행 하네스** | `buzz-acp` 또는 OpenHands ACP | Claude Code/Codex/Gemini를 ACP 하나로 통일 |
| **에이전트 신원·키 관리** | Buzz `buzz-admin generate-key` + NIP-42 | 역할별(Reviewer/QA/Implementer) 별도 키 발급 |
| **에이전트 메모리** | Buzz Engram | `memory/tasks/`는 **공유 진실**, Engram은 **에이전트 사적 컨텍스트**로 역할 분리 |
| **감사 로그** | `buzz-audit` 해시체인 개념 | 단, fire-and-forget 유실 리스크 때문에 Jarvis 승인 기록은 **이중 기록** |
| **Discord intake** | **유지하되 OpenTag 패턴으로 재설계** | 현재 자체 파서 → ACP 기반 admission/receipt 구조로 |
| **Git/PR 실행** | OpenTag의 receipt→approve→PR 모델 | Jarvis 승인 게이트가 receipt의 승인 조건을 소유 |

---

## 5. 추천 Architecture

### 5.1 4개 전략의 실질 평가

#### 전략 A — Jarvis-Core 완전 독립 (Buzz 미사용)

- **장점**: 통제권 100%, 의존성 0, 승인 계약이 어떤 외부 릴리스에도 흔들리지 않음.
  Windows 로컬 환경에서 오늘 당장 동작함(실제로 동작 중).
- **단점**: 협업 표면 6/20점을 자력으로 메워야 한다. 채널·스레드·DM·프레즌스·데스크톱 앱·모바일을
  1인이 만드는 것은 **불가능**하다. 지금 속도(dogfood cycle 20건, Console v0.1G)로는
  Buzz가 하루에 하는 커밋 수를 몇 달에 따라간다.
- **장기 경쟁력**: 🔴 **낮음.** 다만 "경쟁"이 목표가 아니라 "Owner 1인의 안전한 개발 파이프라인"이
  목표라면 A는 여전히 **실패하지 않는 선택**이다. 이 구분이 중요하다.
- **판정**: 목표가 개인 도구면 A로 충분. 목표가 "AI 팀 운영 시스템"이면 A는 패배 경로.

#### 전략 B — Buzz를 Jarvis-Core의 UI/통신 계층으로 (Human → Buzz → Jarvis-Core → Agent)

- **실현 가능성: ✅ 아키텍처상 가능하다.** 근거:
  - `buzz-cli`가 *"agent-first CLI, JSON in / JSON out"* — Jarvis가 파이썬에서 그대로 호출 가능.
  - `buzz-acp`의 인바운드 author gate가 `owner-only`/`allowlist`를 지원 → **Jarvis 전용 에이전트가
    Owner 메시지만 받도록 잠글 수 있다.**
  - 원격 에이전트 Layer 1 계약이 *"a bash script... is a conforming launcher"* → Jarvis가
    환경변수 4개만 세팅하고 harness를 exec하면 정식 런처가 된다.
  - relay는 REST + WebSocket + NIP-98 HTTP를 모두 노출.
- **구체적 통합 지점 (필요한 것 전부):**
  1. Jarvis 전용 Nostr 키페어 발급 (`buzz-admin generate-key`) → `jarvis-orchestrator` 신원
  2. Jarvis가 relay에 NIP-42로 붙는 WS 클라이언트 (파이썬 구현 또는 `buzz-cli` 서브프로세스 호출)
  3. **@jarvis 멘션 → 기존 `intake_parser` 재사용 → task 파일 생성** (기존 자산 그대로 살림)
  4. **승인 요청을 Buzz 채널 메시지로 발행**하고 Owner의 리액션/응답을 승인 신호로 수신
     — 🔴 **단, Buzz의 `kind:46011` 승인 이벤트는 executor가 미완성이므로 Jarvis가 자체 검증해야 함**
  5. Reviewer/QA/Implementer를 **각각 별도 키의 Buzz 에이전트**로 등록 → 누가 무엇을 했는지 서명으로 증명
  6. Jarvis가 candidate commit 고정과 content digest 검증을 수행하고 **결과만** 채널에 게시
- **리스크**: relay가 죽으면 Jarvis 파이프라인 전체가 멈춘다. Buzz v0.5.x의 breaking change 노출.
  🔴 **Windows 데스크톱의 self-host relay 접속 결함(#3490)이 미해결이면 Owner가 자기 relay에 못 붙는다.**
- **판정**: ✅ **가장 합리적. 단 지금 즉시가 아니라 검증 게이트 뒤에.**

#### 전략 C — Buzz의 아키텍처/코드 아이디어만 차용 (의존 없음)

훔칠 가치가 있는 것 — 우선순위 순:

1. 🥇 **"kind 정수 하나로 모든 것을 표현하는 append-only 서명 이벤트 로그"**
   Jarvis-Core의 태스크 상태는 지금 **마크다운 파일을 덮어쓰는 방식**이다. `updated_at`을 갱신하면
   이전 상태는 Git history에만 남는다. 이벤트 로그로 바꾸면 상태 전이 자체가 1급 증거가 된다.
   **이것이 Buzz에서 배울 수 있는 단연 최고 가치의 아이디어다.**
2. 🥈 **역할별 키페어 = 에이전트 신원.** Reviewer 키로 서명된 리뷰 결과는 "누가 봤는가"를
   Owner의 기억이 아니라 암호학으로 증명한다. Jarvis의 "evidence is not authority" 원칙에 정확히 부합.
3. 🥉 **원격 에이전트 5대 불변식** — 특히 ③ presence가 곧 상태, ⑤ 의도적 종료는 최종.
   Jarvis의 "잠긴 background worker"를 언젠가 열 때 이 계약을 그대로 쓸 수 있다.
4. **"No secrets in configuration" 강제** — `provider_config`에 secret/password/token 문자열이
   있으면 거부하고 출력을 redact. Jarvis의 AGENTS.md 원칙 5를 **코드로 강제하는** 방법.
5. **`buzz-core`의 zero-I/O 규칙** — tokio/sqlx/redis/axum 의존 금지. Jarvis의
   "transport-neutral core contract" 발상과 동일하며, Buzz가 더 엄격하게 강제한다.
6. **ephemeral kind 대역(20000–29999)은 저장·감사하지 않음** — 상태와 잡음을 구조로 분리.
7. **fire-and-forget 단계 명시** — 어느 실패가 트랜잭션을 깨고 어느 실패가 안 깨는지 문서화.
   (단 Jarvis는 감사 로그를 fire-and-forget으로 두면 **안 된다** — §7 참조)

- **판정**: ✅ **즉시 실행 가능하고 리스크가 0에 가깝다.** Phase 1의 핵심.

#### 전략 D — Buzz 기반/포크로 Jarvis 구축

- **재사용 가능 코드량**: 이론상 매우 많다(relay/auth/audit/ACP 전부). 실질적으로는 **거의 0.**
- **왜 0인가 — 구체적 근거:**
  - 543 MB 저장소, **30개 크레이트**, Rust 1.88+ / Node 24+ / pnpm 10+ / Docker 필수 스택.
  - Jarvis-Core는 **Python + 마크다운**이다. 언어·런타임·빌드 체인이 전부 다르다.
  - **5개월 만에 PR #6901.** 포크하는 순간 하루 10~30커밋씩 divergence가 쌓인다.
    1인이 rebase를 따라갈 수 없다.
  - open issue 3,200건은 곧 **포크가 상속하는 미해결 부채 3,200건**이다.
- **기존 Jarvis 기능 이식 비용**: Hermes durable review, content digest binding, Owner Decision
  contract, Research Council, task 모델 — 전부 Python. Rust 재작성 = 사실상 재개발.
- **락인 리스크**: Nostr 이벤트 모델·Postgres 파티셔닝·Redis pubsub에 종속. 빠져나오기 어렵다.
- **판정**: 🔴 **명확히 거부.** 이건 전략이 아니라 자살이다.

### 5.2 Owner 제안 아키텍처 검증

Owner의 스트로맨:
```text
Human → AI Workspace → (Claude/Codex/Gemini/Research/Reviewer/...) → Jarvis-Core → Tasks/Memory/Governance → Git/PR/Review/Approval
```

**문제점 3가지:**

1. 🔴 **에이전트가 Jarvis-Core "위"에 있다.** 이 배치에서는 에이전트가 Jarvis를 **호출**한다.
   즉 에이전트가 승인 게이트를 우회할 수 있는 경로가 구조적으로 열린다. Jarvis-Core의 제1원칙
   ("한 단계 성공이 다음 단계 권한을 자동 부여하지 않는다")과 모순된다.
2. 🔴 **Approval이 맨 아래 Git/PR 옆에 있다.** 승인은 실행의 **결과물**이 아니라 **선행 조건**이다.
   Buzz가 정확히 이 실수를 했고, 그래서 `request_approval`이 suspend 대신 Fail한다.
3. 🟡 Workspace와 Jarvis-Core 사이의 신뢰 경계가 표현되지 않았다.

**수정 제안:**

```text
                          Human (Owner)
                               │
                    ┌──────────┴──────────┐
                    │                     │  (승인은 워크스페이스를
                    ▼                     │   경유하되 별도 채널로 검증)
        ┌───────────────────────┐         │
        │   AI Workspace (Buzz) │         │
        │   채널·스레드·DM·신원   │         │
        │   프레즌스·감사·검색     │         │
        └───────────┬───────────┘         │
                    │  @mention / 이벤트    │
        ════════════╪═══════════════════   │  ← 신뢰 경계
                    ▼                      ▼
        ┌──────────────────────────────────────────┐
        │            JARVIS-CORE                   │
        │        (Control Plane / 권한의 원천)        │
        │                                          │
        │  Intake → Task → Plan → **APPROVAL GATE**│
        │                              │           │
        │  Evidence Ledger ◄───────────┤           │
        │  Governance (SOP/budget/role)│           │
        │  Memory (append-only 이벤트로그)│          │
        └──────────────────────────────┼───────────┘
                                       │ 승인된 bounded 작업만 하달
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
             Implementer          Reviewer              QA
             (Claude Code)        (Codex)          (Claude Code)
                  │  ACP 하네스, 역할별 키페어, 격리된 worktree
                  ▼
        ┌──────────────────────────────────────────┐
        │   Git / PR — Jarvis 승인 없이는 push 불가    │
        └──────────────────────────────────────────┘
                    │ 결과·증거만 역방향 게시
                    └──────────────► Workspace 채널
```

**핵심 차이 3가지:**
1. **Jarvis-Core가 에이전트 "위"에 있다.** 에이전트는 Jarvis가 하달한 bounded 작업만 수행한다.
2. **APPROVAL GATE가 실행 앞에 있다.** 게이트를 통과하지 않은 작업은 애초에 하달되지 않는다.
3. **Workspace는 표면일 뿐 권한의 원천이 아니다.** Buzz relay가 죽어도 Jarvis의 승인 계약은 유효하다.
   Buzz 채널 메시지는 **입력**이고, 승인은 **Jarvis가 검증한 Owner 의사**다.
   (§7의 프롬프트 인젝션 방어와 직결)

---

## 6. 가장 현실적인 실행 전략 (Phase 1 / 2 / 3)

### 6.0 먼저: 실행 가능성 실사 (Owner의 실제 환경 = Windows 11, `C:\work\jarvis-core`)

| 질문 | 답 | 근거 |
| --- | --- | --- |
| Windows에서 가능한가? | 🟡 **부분.** relay는 Docker Desktop으로 가능. **데스크톱 앱 ↔ self-host relay는 미해결 결함**(#3490, #2872) | GitHub Issue 확인 |
| Claude Code 연결? | ✅ `claude-agent-acp` 래퍼 (Anthropic API 키 필요) | `buzz-acp/README.md` |
| Codex 연결? | ✅ `codex-acp` 래퍼 (OpenAI API 키 필요) | 동상 |
| Gemini 연결? | ❌ **Buzz 미지원.** Gemini CLI는 2026-06-18 개인계정 폐기. Antigravity CLI(agy)는 ACP 미확인 | task-0037 + open-tag README |
| 기존 Discord intake 유지 가능? | ✅ **가능.** `intake_parser`/`task_draft_builder`/`task_file_writer`는 순수 파이썬 함수라 입력 소스만 바꾸면 됨 | 로컬 소스 확인 |
| 기존 task 시스템 유지 가능? | ✅ 유지 가능. 단 §7 권고대로 append-only 이벤트 로그로 진화시킬 것 | — |
| Research Council 유지 가능? | ✅ **완전 독립.** 어떤 통합에도 영향 없음 | `apps/research-council/` |
| GitHub workflow 연결? | 🟡 Buzz는 **자체 git 호스팅**(relay smart-HTTP)이라 GitHub와는 별개 경로. GitHub 연동이 필요하면 **OpenTag 쪽이 직접적** | VISION_PROJECTS + OpenTag README |
| 로컬 에이전트 실행? | ✅ `buzz-acp`를 로컬에서 실행. Docker/K8s 불필요 | `buzz-acp/README.md` |
| 동시 다중 에이전트? | ✅ `--agents N`. 채널당 in-flight 프롬프트 1개, 채널 간 동시 처리 | 동상 |
| 에이전트 워크스페이스 격리? | 🟡 Buzz 자체로는 **미보장** — 셸이 *"runs at the operator's trust level, like bash itself"*. **git worktree 격리는 Jarvis가 직접 해야 함**(Conductor 패턴) | `buzz-agent/README.md` |
| 에이전트 간 위임? | 🟡 부분 — `buzz-agent`는 명시적 거부. AgentConnect가 이 항목은 더 낫다 | 동상 |
| 사람 승인 강제 가능? | 🔴 **Buzz 단독으로는 불가.** 승인 게이트 executor 미완성. **Jarvis-Core가 반드시 소유해야 하는 이유** | `ARCHITECTURE.md` Known Limitations |

### Phase 1 — 아키텍처를 훔친다 (즉시, 외부 의존 0)

목표: **Buzz를 설치하지 않고** 얻을 수 있는 이득을 전부 확보한다. 리스크 0.

1. 🔴 **Director Dashboard v0.1B 착수를 보류하고 재검토한다.** (master-plan.md의 "현재 다음 작업")
   Buzz Desktop과 정면 중복이다. Owner 결정 필요.
2. **Task 상태를 append-only 이벤트 로그로 전환한다.** 파일 덮어쓰기 → 이벤트 append.
   `memory/tasks/task-XXXX.md`는 **이벤트에서 파생된 뷰**가 된다. (Buzz kind 모델 차용)
3. **역할별 신원을 도입한다.** Implementer/Reviewer/QA/Docs가 각각 서명 키를 갖고,
   리뷰 결과·QA 결과에 서명한다. Nostr을 쓸 필요는 없다 — Ed25519 로컬 키로 충분하다.
4. **"No secrets in configuration"을 코드로 강제한다.** 설정값에 secret/password/token 문자열이
   있으면 거부 + 출력 redact. AGENTS.md 원칙 5를 문서에서 코드로 승격.
5. **감사 기록을 해시체인으로 만든다.** 각 승인/증거 기록에 `prev_hash` 포함.
   🔴 단 Buzz와 달리 **fire-and-forget으로 두지 않는다** — 감사 기록 실패는 작업 실패다.
6. **ACP를 조사한다** (구현 아님). Claude Code/Codex/Gemini를 하나의 인터페이스로 붙일 수 있는지
   Owner 환경에서 검증. 이것이 Phase 2의 선행 조건.

**Phase 1 완료 조건**: 위 6개 중 최소 4개 완료 + Buzz 설치 없음 + 기존 승인 계약 무손실.

### Phase 2 — 격리된 검증 스파이크 후 통합 결정 (Phase 1 완료 후)

**게이트: 아래 3가지가 전부 통과해야 Phase 2 통합에 착수한다.**

| 게이트 | 검증 방법 | 실패 시 |
| --- | --- | --- |
| G1. Windows에서 self-host relay + 데스크톱이 실제로 붙는가 | Docker Compose로 relay 기동 후 Windows 데스크톱 join 시도. Issue #3490 재현 여부 확인 | 🔴 **Phase 2 중단.** Buzz 대신 Discord 유지 |
| G2. `buzz-acp`가 Windows에서 Claude Code를 실제로 구동하는가 | `claude-agent-acp` 래퍼로 @mention → 응답 1회 왕복 | 🔴 중단 |
| G3. Buzz 1.0 또는 승인 게이트 executor 완성 | CHANGELOG / ARCHITECTURE.md Known Limitations 재확인 | 🟡 통합하되 **승인은 100% Jarvis가 소유** |

> **[2026-08-28 09:00 UTC G2 재정의 — task-0045/task-0046 근거, Owner 승인]** task-0045에서 Claude Code/Codex/Antigravity(agy) 모두 공식 ACP 미지원이 확인되어 원래 G2("`buzz-acp`가 Windows에서 Claude Code를 구동하는가")는 좁은 단일 경로였다. task-0046에서 Buzz Relay의 WebSocket이 Buzz 고유 프로토콜이 아니라 표준 Nostr(NIP-01/42/45)이고, Buzz 공식 예제 `examples/countdown-bot`이 ACP/MCP 없이 WebSocket에 직접 연결하는 사례로 확인됨에 따라, **G2는 "ACP 경로(`buzz-acp`)" 단독이 아니라 "WebSocket 직결 local agent bridge 경로"까지 포함해 재정의한다.** 즉 G2는 다음 중 하나만 통과해도 충족된 것으로 본다: (a) `buzz-acp` ACP 경로가 Windows에서 동작, 또는 (b) WebSocket 직결 bridge(Claude/agy의 `stream-json`, Codex의 `exec --json`/app-server를 Relay의 NIP-01/42/45 이벤트에 연결)가 동작. 검증 방법은 (b) 경로 기준 task-0046 §6의 스파이크 S1~S7(특히 S6 채널 구독 왕복 + kind 실측)을 사용한다. **단, 실제 스파이크는 Phase 1(task-0041~0044) 완료 후 별도 Owner 승인 하에만 착수한다** — 지금 Docker Desktop 설치나 스파이크를 실행하지 않는다(task-0047로 별도 추적).

> **[2026-08-28 정정 — task-0039 기준 정합화]** 위 문장의 "Phase 1(task-0041~0044) 완료 후"는 task-0039가 Phase 1 완료 게이트를 확정하기 전에 쓰인 구버전 표현이다. task-0039가 정의한 공식 게이트는 "6개 하위 task(task-0040~0045) 중 4개 이상 완료"이며, 현재 task-0040+task-0041+task-0043+task-0045 = 4/6로 이미 충족되어 **Phase 1은 완료**됐다. task-0042(서명키)/task-0044(감사 해시체인)는 선택적 잔여 항목이며 task-0047(스파이크) 착수의 필수 선행조건이 아니다. task-0047의 실제 남은 착수 조건은 (1) 위 Phase 1 게이트 충족(완료됨)과 (2) Docker Desktop 설치 및 스파이크 실행에 대한 별도 Owner 승인(아직 미승인)뿐이다. 이 정정은 위 원문 기록을 대체하지 않고 현재 기준을 명시하는 정합화다.

게이트 통과 시 통합 순서:

1. `jarvis-orchestrator` 신원 발급, 전용 채널 1개 생성
2. **@jarvis 멘션 → 기존 `intake_parser` 재사용 → task 이벤트 생성** (Discord intake 자산 재활용)
3. 승인 요청을 Buzz 채널에 게시하되, **Owner의 승인은 Jarvis가 별도로 검증한다**
   (채널 메시지 = 입력, 승인 판정 = Jarvis 소유 — §7 인젝션 방어)
4. Reviewer/QA를 별도 키의 Buzz 에이전트로 등록, git worktree로 격리
5. Discord intake는 **최소 3개월 병행 유지**. 롤백 경로 확보.

**Phase 2를 하지 않아도 되는 조건**: G1이 실패하고 Owner가 Discord로 충분하다고 판단하면,
Phase 1 성과만으로 프로젝트는 이미 크게 개선된다. **Phase 2는 선택이지 필수가 아니다.**

### Phase 3 — 장기 (Phase 2 실사용 검증 후에만)

1. Jarvis 승인 게이트를 Buzz에 **업스트림 기여**한다. Buzz의 자체 인정 결함이고 Jarvis가
   가장 잘 아는 영역이다. 3,200개 이슈를 가진 프로젝트에 1,000줄짜리 승인 executor를 기여하는 것이,
   30 크레이트를 포크하는 것보다 100배 효율적이다.
2. `memory/tasks/` ↔ Buzz Engram 역할 분리 확정: 공유 진실 vs 에이전트 사적 컨텍스트.
3. Git/PR 실행 경로를 OpenTag의 receipt 모델로 연다 (현재 master-plan §6에서 잠김).
4. 모바일 승인 (master-plan 단계 5) — Buzz mobile이 안정화되면 자체 개발 불필요.

---

## 7. 하지 말아야 할 것

### 7.1 전략적 금지

1. 🔴 **Buzz를 포크하지 마라.** 543MB / 30 크레이트 / 5개월에 PR 6,900개 / 미해결 이슈 3,200건.
   1인이 유지할 수 없다. (전략 D 거부)
2. 🔴 **채팅·채널·스레드·DM·데스크톱 앱을 직접 만들지 마라.** Jarvis Console을 "메인 UI"로
   키우는 계획은 지금 중단해야 한다. Console은 **Jarvis 전용 승인 화면**으로 축소하는 것이 맞다.
3. 🔴 **Buzz를 지금 즉시 프로덕션 인프라로 채택하지 마라.** v0.5.20 / 승인 게이트 미완성 /
   Windows self-host 결함 미해결. Phase 2 게이트를 반드시 먼저 통과시켜라.
4. 🔴 **승인 게이트를 외부 시스템에 위임하지 마라.** Buzz도 OpenTag도 AgentConnect도
   Jarvis만큼 엄격하지 않다. 이것을 넘기는 순간 Jarvis-Core에는 남는 것이 없다.
5. 🟡 **자체 에이전트 통신 프로토콜을 만들지 마라.** ACP가 사실상 표준이 되었다
   (Buzz, OpenTag, AgentConnect, OpenHands가 전부 ACP). 자체 프로토콜은 순수한 손실이다.
6. 🟡 **"Buzz가 있으니 Jarvis-Core는 의미 없다"고 결론내지 마라.** 점수표에서 Buzz가 80,
   Jarvis-Core가 62지만, **오케스트레이션 13 vs 9, 보안·거버넌스 5 vs 4**로 Jarvis가 앞선다.
   문제는 협업 표면(6 vs 19)이고, 그건 만들 게 아니라 **빌려올** 영역이다.

### 7.2 보안·운영 리스크와 금지 사항

| 리스크 | 실체 | 방어 |
| --- | --- | --- |
| **에이전트의 repo 권한 획득** | Buzz NIP-OA는 *"maintainers' authorized agents inherit push access without explicit listing"* — 🔴 **명시적 나열 없는 권한 상속** | ❌ **NIP-OA 권한 상속을 절대 켜지 마라.** push는 Jarvis 승인 게이트를 통과한 경우만 |
| **에이전트별 자격증명 격리** | Buzz는 키페어 격리는 하지만, 셸은 오퍼레이터 신뢰 수준으로 실행 | 역할별 키 + **역할별 git worktree** + 역할별 OS 계정 분리 검토 |
| **API 키 관리** | `claude-agent-acp`는 `ANTHROPIC_API_KEY`, `codex-acp`는 OpenAI 키 필요 | AGENTS.md 원칙 5 유지 — 저장소에 절대 저장 금지. 환경변수 + Owner 승인(비용 발생 gate) |
| **private repo 접근** | Buzz relay가 git을 호스팅하면 코드가 relay DB/S3에 들어간다 | 🔴 **jarvis-core 소스를 Buzz relay에 호스팅하지 마라.** Buzz는 조정 계층, git은 로컬/GitHub 유지 |
| 🔴 **프롬프트 인젝션** | **최대 리스크.** "에이전트가 채널 메시지를 읽고 행동한다"는 구조 자체가 인젝션 표면이다. Buzz의 author gate(`owner-only`)는 완화일 뿐 해결이 아니다 — Owner 계정이 탈취되거나 Owner가 붙여넣은 외부 텍스트에 지시가 섞이면 무력화 | ① author gate `owner-only` 고정 ② **채널 메시지는 절대 승인으로 취급하지 않는다** — 승인은 Jarvis가 별도 확인 경로로 검증 ③ 기존 `/discord:access` 규칙(터미널 전용)을 Buzz에도 동일 적용 |
| **에이전트 무한 상호 호출** | `buzz-agent`는 위임 자체를 거부해 이 리스크가 없음. AgentConnect는 호출 허용목록으로 제한 | Jarvis SOP의 `retry_budget=1`/`repair_budget=1` 유지. 위임 도입 시 **호출 깊이 상한 필수** |
| **권한 상승** | Buzz 워크플로 `call_webhook`은 SSRF 차단(`is_private_ip`)이 있으나, rate limiter는 **트레이트만 있고 구현 없음(테스트 스텁)** | 🔴 **워크플로 액션을 신뢰하지 마라.** Jarvis 쪽에서 독립적으로 rate limit |
| **미승인 push/merge** | Buzz의 브랜치 보호는 relay가 강제하지만 승인 executor가 미완성 | 🔴 **Buzz 브랜치 보호를 유일한 방어선으로 삼지 마라.** Jarvis가 이중 검증 |
| **감사 추적 유실** | 🔴 Buzz 이벤트 파이프라인 10~12단계(검색·감사·워크플로)는 **fire-and-forget** — *"A failure in any of these does not fail the event submission."* 즉 **감사 로그가 조용히 유실될 수 있다** | 🔴 **승인·증거 기록은 Jarvis 로컬에 반드시 이중 기록.** Buzz 감사 로그를 단일 진실로 삼지 마라 |
| **self-host 데이터 보안** | Postgres + Redis + MinIO 스택. 이벤트 전문이 FTS 인덱싱됨 (일부 kind는 저장 단계에서 제외) | 로컬 전용 바인딩, 외부 노출 금지. Owner 개인정보/자격증명이 채널에 흐르지 않게 운영 규칙 |
| 🔴 **relay 침해** | **relay가 유일한 진실의 원천이다.** 침해되면 모든 채널·git·승인 이벤트가 노출·조작 가능. relay owner 키는 `RELAY_OWNER_PRIVATE_KEY`로 부트스트랩 | ① self-host relay를 로컬/사설망에 한정 ② relay를 승인 권한의 원천으로 만들지 않음(§5.2) ③ **relay가 죽어도 Jarvis 승인 계약이 유효한 구조 유지** |
| **신원·키 관리** | 에이전트 키 유출 = 그 에이전트로 위장한 서명 가능. `!rotate` 명령 존재 | 키 로테이션 절차 문서화. 키는 저장소 밖(`%LOCALAPPDATA%`) — 기존 Review store 패턴 재사용 |

---

## 8. 최종 Verdict

# ✅ INTEGRATE BUZZ + JARVIS

### 단, 조건부·단계적 통합이다. "지금 Buzz를 깔자"가 아니다.

**핵심 논거 5가지:**

**1. 점수표가 말하는 것은 "Jarvis가 진다"가 아니라 "Jarvis가 잘못된 곳에서 싸우고 있다"이다.**
Buzz 80 vs Jarvis 62. 그러나 항목별로 보면 Jarvis는 **오케스트레이션 13 vs 9, 보안·거버넌스 5 vs 4**로
앞서고, **협업 20점 항목에서 6 vs 19로 13점을 잃는다.** 총점 차이 18점 중 13점이 한 항목에서 나온다.
**그 한 항목은 만들 것이 아니라 빌려올 것이다.**

**2. KEEP JARVIS(전략 A)를 거부하는 이유:** 협업 표면 없이는 "AI 팀 운영 시스템"이 될 수 없다.
현재 "AI 팀"의 실체는 Owner가 ChatGPT와 Claude Code 사이를 **손으로 중계하는 Phase 1 구조**다
(ai-team-operating-model.md §5). 이건 팀이 아니라 1인 파이프라인이다.
— 다만 정직하게 덧붙인다: **Owner의 목표가 "개인용 안전한 개발 도구"라면 전략 A로 충분하고,
그 경우 이 보고서의 Phase 1만 실행하면 된다.** 목표 정의가 먼저다.

**3. ADOPT BUZZ를 거부하는 이유:** Buzz의 승인 게이트는 **자체 문서가 미완성이라고 인정한다**
(*"Runs hitting `request_approval` actions fail (marked Failed) rather than suspending"*).
감사 로그는 fire-and-forget이라 유실 가능하다. Windows self-host는 미해결 결함이 있다.
**Jarvis-Core가 가장 잘하는 것을, Buzz는 가장 못한다.** 통째로 넘기면 남는 게 없다.

**4. FORK BUZZ를 거부하는 이유:** 543MB / 30 크레이트 / Rust vs Python / 5개월에 PR 6,900개 /
미해결 이슈 3,200건. 1인 유지 불가능. 재사용 가능 코드는 이론상 많고 실질적으로 0이다.

**5. REBUILD를 거부하는 이유:** Jarvis-Core의 승인·증거 계약은 지난 수개월의 실사용 검증을 거친
자산이다(Hermes v0.1A~v0.1G, Multi-Agent SOP v0.1B pilot에서 실제 P2 finding → repair → 재검증 완료).
버릴 이유가 없다.

### 실행 지시 요약

| 시점 | 행동 |
| --- | --- |
| **즉시** | Director Dashboard v0.1B 착수 **보류** → Buzz Desktop과 중복 여부 Owner 판단 |
| **Phase 1 (외부 의존 0)** | Task를 append-only 이벤트 로그로 / 역할별 서명 키 / no-secrets 코드 강제 / 감사 해시체인(fire-and-forget 금지) / ACP 조사 |
| **Phase 2 게이트** | G1 Windows self-host relay 접속 / G2 buzz-acp+Claude Code 왕복 / G3 승인 executor 상태 — **3개 전부 통과해야 착수** |
| **Phase 2** | Buzz를 협업 표면으로. 승인 판정은 100% Jarvis 소유. Discord 3개월 병행 |
| **Phase 3** | 승인 게이트를 Buzz에 업스트림 기여 / Git·PR 실행 경로 개방 / 모바일 승인 |
| **영구 금지** | 포크 / 자체 채팅 UI / 승인 게이트 외부 위임 / Buzz relay에 jarvis-core 소스 호스팅 / NIP-OA 권한 상속 |

### 듣기 좋은 말 없이 한 문장

**Jarvis-Core가 지난 몇 달간 만든 것 중 절반은 이제 세상에 더 잘 만들어진 오픈소스가 있고,
나머지 절반(승인·증거·거버넌스)은 그 오픈소스들이 전부 못 만든 것이다. 전자를 버리고 후자에
전부를 걸어라.**

---

## 검증 내역

| 확인 항목 | 방법 | 결과 |
| --- | --- | --- |
| jarvis-core 실제 구조 | 로컬 파일 직접 read (`AGENTS.md`, `docs/master-plan.md`, `docs/ai-team-operating-model.md`, `docs/task-model.md`, `docs/architecture.md`, `reports/README.md`, `orchestrator/discord-intake/README.md`, `apps/*/README.md`, `memory/tasks/task-0037-*.md`, 파일 트리) | 완료 |
| Buzz 저장소 메타 | GitHub API `/repos/block/buzz` | star 31,012 / issue 3,200 / Apache-2.0 / push 2026-08-27 |
| Buzz 소스 트리 | GitHub API `/contents/`, `/contents/crates`, `/contents/crates/buzz-acp/src`, `/contents/docs` | 크레이트 30개, 파일 경로 확인 |
| Buzz 아키텍처 | raw `ARCHITECTURE.md`, `NOSTR.md`, `VISION.md`, `VISION_AGENT.md`, `VISION_PROJECTS.md`, `docs/remote-agents.md`, `crates/buzz-acp/README.md`, `crates/buzz-agent/README.md` | 완료 |
| Buzz 개발 활동 | GitHub API `/commits?per_page=30`, `/releases/latest` | 조사 당일 11커밋 / `desktop-v0.5.20` (2026-08-26) |
| Buzz 이슈 | GitHub API issue search (reactions 정렬) + 웹검색 | 상위 테마 + Windows 결함 #3490/#2872 확인 |
| 경쟁 프로젝트 메타 | GitHub API `/repos/{openagents-org/openagents, Miosa-osa/canopy, agentconnect-md/agentconnect, fancyboi999/open-tag, amplifthq/opentag, tashfeenahmed/circlechat}` | 6건 확인 |
| 경쟁 프로젝트 내용 | raw README (open-tag, opentag, agentconnect) + 공식 문서 (openagents.org) + 웹검색 | 완료 |

## 미확인 / 확인하지 못한 항목

1. **"Threads"라는 이름의 독립 프로젝트** — 특정 불가. 검색어 오염. **미확인**
2. **Buzz의 에이전트 간 위임 실행 경로** — `KIND_JOB_REQUEST`(43001) 존재와 커뮤니티 서술은 확인했으나
   **소스에서 위임 실행 코드를 직접 읽지 못했다.** 부분 확인
3. **Canopy 라이선스** — GitHub API가 `Other` 반환, SPDX 미식별. **오픈소스 조건 미확인**
4. **Canopy / CircleChat / OpenAgents의 세부 기능 다수** — README 수준까지만 확인. 소스 미검증
5. **Buzz Windows 결함(#3490)의 현재 해결 여부** — 이슈 존재는 확인, **클로즈 여부 미확인**
6. **Antigravity CLI(agy)의 ACP 지원 여부** — 미확인 (Phase 1 항목 6에서 검증 필요)
7. **AgentConnect의 API/웹훅 상세** — README가 문서 링크만 제공, 실물 미확인
8. **실제 성능·안정성** — 어떤 프로젝트도 설치·실행하지 않았다. 지시된 제약(설치 금지) 준수

## 금지 표현 점검

"완벽하게 동작함", "문제 없음", "전체 완료" 표현을 사용하지 않았다.
확인된 사실은 출처와 함께, 미확인 항목은 **미확인**으로 명시했다.

## 참고 출처

- [block/buzz (GitHub)](https://github.com/block/buzz) · [buzz.xyz](https://buzz.xyz)
- [Block — Introducing Buzz](https://block.xyz/inside/introducing-buzz-where-humans-and-agents-work-together)
- [Buzz! 🐝 — Block Engineering Blog](https://engineering.block.xyz/blog/buzz)
- [SiliconANGLE — Block launches Buzz (2026-07-21)](https://siliconangle.com/2026/07/21/block-launches-buzz-open-source-workspace-humans-ai-agents/)
- [Buzz Issue #3490 — Windows desktop cannot join self-hosted relay](https://github.com/block/buzz/issues/3490)
- [Buzz Issue #2872 — CORS omits Tauri webview origins](https://github.com/block/buzz/issues/2872)
- [amplifthq/opentag](https://github.com/amplifthq/opentag) · [docs.getopentag.com](https://docs.getopentag.com/)
- [fancyboi999/open-tag](https://github.com/fancyboi999/open-tag) · [getopentag.com](https://getopentag.com/)
- [agentconnect-md/agentconnect](https://github.com/agentconnect-md/agentconnect)
- [openagents-org/openagents](https://github.com/openagents-org/openagents) · [openagents.org](https://openagents.org/)
- [Miosa-osa/canopy](https://github.com/Miosa-osa/canopy) · [opencanopy.ai](https://opencanopy.ai/)
- [tashfeenahmed/circlechat](https://github.com/tashfeenahmed/circlechat)
- [OpenHands — Agent Canvas / ACP](https://www.openhands.dev/blog/use-any-coding-agent-in-openhands-with-acp) · [docs.openhands.dev ACP Agents](https://docs.openhands.dev/openhands/usage/agent-canvas/acp-agents)
- [Patchwork (DEV.co 소개)](https://dev.co/devops/open-source/patchwork) — 카테고리 불일치로 제외
- [MemClaw — Buzz gives every agent an identity (Engram 설명)](https://memclaw.net/blog/buzz-agents-get-an-identity/)
