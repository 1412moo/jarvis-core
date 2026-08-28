# task-0045: ACP(Agent Client Protocol) 기반 Claude Code/Codex/Gemini(Antigravity) 통합 실현 가능성 조사

- 작성일: 2026-08-27
- 작성자: Claude Code (research agent, task-0045)
- 상태: 조사 방식 — 공식 문서(agentclientprotocol.com, zed.dev)·GitHub 저장소/이슈 트래커 fetch + 웹검색 + 로컬 파일(agy 설치본, builtin skill 문서) 직접 확인. 설치/코드변경/API 키 발급/커밋 없음.
- 모든 외부 사실은 **2026-08-27 확인 시점** 기준. WebFetch 요약은 대상 페이지를 소형 모델이 재요약한 결과이므로, 원문 인용이 필요한 곳은 "요약 결과"임을 명시했다.

---

## Executive Summary

**"ACP"는 실제로 Zed Industries가 만들고 현재 커뮤니티(agentclientprotocol 조직)가 관리하는 Agent Client Protocol이 맞다 — task-0038의 용어 사용은 정정할 필요 없이 정확했다.** 그러나 그 안의 핵심 전제 하나는 부정확했다: **Claude Code와 Codex 모두 ACP를 공식 지원하지 않는다** — 둘 다 벤더가 기능 요청을 명시적으로 닫았거나(Claude Code, "not planned") 구현 여부가 불명확한 상태(Codex)이고, 실제로 쓰이는 것은 전부 API 키 기반 SDK 재구현이거나 서드파티 wrapper다. Antigravity CLI(agy)는 ACP를 전혀 지원하지 않으며(로컬 `agy --help`/문서 직접 확인 + 3개월째 미해결 기능요청), MCP만 지원한다. Windows에서 Claude Code를 `buzz-acp`로 구동하는 것은 **문서·이슈트래커 근거만으로 "낮음~불명"** — 설치형 Buzz Desktop 경로는 하네스 바이너리 자체가 최근까지 누락되어 있었고, 소스 빌드 경로는 실제 성공 사례가 있지만 최소 2개의 업스트림 버그를 직접 우회해야 한다.

> **[2026-08-27 15:20 UTC 후속 정정 — task-0046 참고]** 이 결론은 "ACP 경로"에 한정된 판단이었다. 후속 조사(task-0046, `reports/task-0046-local-buzz-relay-agent-bridge-feasibility.md`)에서 Buzz Relay의 WebSocket이 **표준 NIP-01/42/45이며 Buzz 고유 프레임이 없다는 것**과, Buzz 공식 예제(`examples/countdown-bot`)가 **ACP/MCP 없이 WebSocket을 직접 붙이는 봇**이라는 것을 소스에서 확인했다. 즉 ACP를 아예 우회하고 Relay에 직접 연결하는 local agent bridge를 만들면, 이 보고서의 "낮음~불명" 판정과 무관하게 통합이 가능하다는 설계 근거(실기동 검증은 아님)가 나왔다. Phase 2 Gate G2를 재검토할 때는 이 보고서 단독이 아니라 task-0046까지 함께 참고할 것.

---

## 1. ACP란 정확히 무엇인가

- **정체**: Zed Industries(Zed 에디터 제작사)가 만들어 오픈소스로 공개한 **Agent Client Protocol**. 공식 사이트 agentclientprotocol.com, 원 저장소 `github.com/zed-industries/agent-client-protocol`. 이후 **커뮤니티 거버넌스 조직 `github.com/agentclientprotocol`로 이관**되어 현재는 Zed 단독 소유가 아니다.
- **목적**: 코드 에디터/IDE("client")와 코딩 에이전트를 표준 방식으로 연결. "AI 에이전트를 위한 LSP(Language Server Protocol)"로 스스로를 표현한다. 에디터마다 개별 에이전트 통합을 만들어야 했던 문제를 해소.
- **전송 방식**: 로컬 에이전트는 **JSON-RPC 2.0 over stdio**. 원격 에이전트(HTTP/WebSocket)는 공식 문서 원문 그대로 *"a work in progress"* — 아직 미완성.
- **성숙도/버전**: 공식 사이트에서 명확한 semver 버전 번호를 확인하지 못했다 (**미확인**). 공개 시점은 2025-08 전후로 보이며(Tessl.io 블로그, Zed 블로그의 "Claude Code via ACP" 포스트가 2025-09-03), 최소 1년 이상 실사용되며 발전 중.
- **채택 현황**: Zed(자체 최우선 통합), JetBrains(2025-10 Zed와 공동개발 파트너십 발표, IntelliJ/PyCharm/WebStorm 목표), Neovim(CodeCompanion 플러그인으로 안정적 지원), Emacs(커뮤니티 플러그인), VS Code(제한적 커뮤니티 확장). agentclientprotocol.com 자체 agents 목록은 "40개 이상"의 ACP 호환 에이전트 구현을 나열한다(단, 다수가 커뮤니티 wrapper — 아래 참조).
- **task-0038 용어 사용 검증**: task-0038은 "ACP"를 이 프로토콜을 가리키는 데 정확하게 사용했다 — **용어 오염은 없었다.** 다만 task-0038이 표에서 "Claude Code ✅ claude-agent-acp 래퍼 (Anthropic API 키 필요)"라고 단순화한 부분은 **부정확**하다: 실제로는 최소 5개의 서로 다른 커뮤니티 구현이 난립하고, 그중 일부(`agentclientprotocol/claude-agent-acp`)는 API 키가 필요한 SDK 재구현이지만, 다른 일부(`harukitosa/claude-code-acp` 등)는 실제 `claude` CLI 바이너리를 감싸 **Pro/Max 구독으로도 동작**한다고 명시한다. "하나의 래퍼"가 아니라 "인증 모델이 다른 여러 경쟁 구현"이 맞는 그림이다.

## 2. Claude Code의 ACP 지원 현황

- **공식 지원: 없음.** `anthropics/claude-code` GitHub 저장소의 Issue #6686 "Feature Request: Add support for Agent Client Protocol (ACP)"(2025-08-27 개설, `claude acp serve` 서브커맨드 제안)는 **"not planned"로 closed** 상태다. Anthropic 공식 문서(`docs.claude.com`, `platform.claude.com`)를 검색해도 ACP·`--acp` 관련 문서를 찾지 못했다(**공식 문서 부재 확인**).
- **실제 존재하는 것 — 전부 서드파티/커뮤니티**:
  - `zed-industries/claude-agent-acp` (현재 `agentclientprotocol/claude-agent-acp`로 조직 이관, npm `@agentclientprotocol/claude-agent-acp`) — **Zed Industries가 "official Claude Agent SDK"를 사용해 직접 재구현**한 ACP 에이전트. Claude Code CLI 바이너리를 wrap하는 게 아니라 SDK로 다시 만든 것이며, **ANTHROPIC_API_KEY가 필요**(구독 인증 아님). 2025-09-03 Zed 블로그로 공개, Apache 라이선스.
  - `harukitosa/claude-code-acp` — 별도 커뮤니티 프로젝트, README 문구 그대로 "use your Pro/Max subscription from any ACP-compatible editor" — 즉 실제 `claude` CLI를 PTY로 감싸는 방식으로 추정된다.
  - `Xuanwo/acp-claude-code`, `szhongren/claude-code-acp`, `moabualruz/claude-code-cli-acp` — 그 외 최소 3개의 독립 커뮤니티 구현이 더 존재. 표준이 하나로 수렴되지 않은 상태다.
- **Windows 지원 여부**: `agentclientprotocol/claude-agent-acp`의 README에서 Windows/macOS/Linux 관련 명시적 테스트 정보를 찾지 못했다(**미확인**, README 자체에 OS 언급 없음). 그러나 이 패키지를 소비하는 Zed 쪽 이슈 트래커에는 **Windows 전용(`platform:windows`) 라벨이 붙은 실사용 버그가 다수 확인된다** — 5절 참조.

## 3. Codex의 ACP 지원 현황

- **공식 지원: 확인 안 됨 / 사실상 없음으로 보임.** `openai/codex` Issue #2785 "Support the Agent Client Protocol"(2025-08-27 개설)는 **closed** 상태이나, closure가 "구현 완료"인지 "wontfix"인지는 fetch한 내용만으로 판별하지 못했다(**미확인**). 별도로 Issue #9085 "ACP Agent Client Protocol Support"가 존재하는 것도 확인했으나 본문까지는 조사하지 않았다.
- **실제 존재하는 것 — 전부 외부 wrapper**: `agentclientprotocol/codex-acp`(원 `zed-industries/codex-acp`), `cola-io/codex-acp` 등. 이들은 "Codex CLI functionality를 노출하는 ACP server implementation"으로, **Codex App Server를 별도 프로세스로 기동해 ACP 요청 ↔ Codex 이벤트를 번역하는 stdio bridge**다. Codex CLI 자체에 네이티브 `codex acp`류 서브커맨드가 내장돼 있다는 근거는 찾지 못했다(**미확인 — 존재하지 않을 가능성이 높지만 최신 릴리스 노트를 직접 훑지는 않았다**).
- **인증**: ChatGPT 로그인 / API 키(`CODEX_API_KEY`, `OPENAI_API_KEY`) / 커스텀 OpenAI 호환 게이트웨이 중 선택.
- **Windows 지원 여부**: README에 Windows 관련 명시 정보 없음(**미확인**). Zed의 codex-acp 에이전트 페이지에도 Windows 관련 언급이 없었다.

## 4. Gemini/Antigravity CLI의 ACP(또는 대안 프로토콜) 지원 현황

- **로컬 직접 확인 (2026-08-27, 설치된 `agy` 바이너리, 경로 `C:\Users\hsy\AppData\Local\agy\bin\agy.exe`)**: `agy --help` 전체 출력(플래그 15개, 서브커맨드 10개: `agent`/`agents`/`changelog`/`help`/`install`/`mcp`/`mic-serve`/`models`/`plugin`/`plugins`/`update`)에 ACP 관련 항목이 **전혀 없다.**
- 로컬 builtin skill 문서 15개 전부(`C:\Users\hsy\.gemini\antigravity-cli\builtin\skills\**`, `agy-customizations`·`antigravity_guide` 등)를 `ACP|Agent Client Protocol|agentclientprotocol` 패턴으로 grep한 결과 **매치 0건.**
- **GitHub 근거**: `google-antigravity/antigravity-cli` Issue #31 "Feature request: add ACP (Agent Client Protocol) stdio JSON-RPC mode" — **2026-05-20 개설, 조사일(2026-08-27) 기준 여전히 OPEN**, 메인테이너 응답이나 구현 타임라인 없음. 요청 내용은 `gemini-cli --acp`/`claude --acp`/`codex acp`/`cursor-agent acp`와 동일한 모양의 `agy --acp` 플래그를 추가해 달라는 것으로, **agy가 ACP를 아직 구현하지 않았음을 요청자 스스로도 전제하고 있다.**
- **대신 존재하는 것**: agy 프로세스를 외부에서 spawn/PTY로 감싸는 서드파티 브리지 최소 5개(`jameslunardi/agy-agent-acp`, `shubzkothekar/antigravity-acp`, `letrquan/agy-acp`, `shindgew/agy-acp`, `jiridanek/agy-acp`) — 전부 agy 자체의 네이티브 지원이 아니라 **외부에서 CLI를 흉내내는 방식**이다.
- **MCP는 명확히 지원**: `agy mcp` 서브커맨드(add/remove/list/enable/disable)가 실제 존재하고, `~/.gemini/config/mcp_config.json` 글로벌 설정 + stdio/SSE 두 트랜스포트를 지원한다(로컬 문서 `mcp_servers.md` 직접 확인). 즉 **agy는 "툴을 붙이는" MCP는 가능하지만, "다른 에디터/클라이언트가 에이전트를 제어하는" ACP는 불가능**하다 — 이 둘의 역할 차이(MCP=tool access, ACP=agent-to-client control)를 정확히 보여주는 사례다.
- **구 Gemini CLI와의 관계**: agentclientprotocol.com의 agents 목록에는 옛 공식 `google-gemini/gemini-cli`가 "Gemini CLI — Official Google implementation"으로 등재돼 있었다(WebFetch 요약 기준). task-0038이 언급한 OpenHands Agent Canvas의 "Gemini CLI ACP 통합"도 이 바이너리를 겨냥한 것으로 추정된다. 그러나 이 바이너리는 **개인/소비자 Google 계정 로그인이 2026-06-18부로 차단**됐다(task-0037 확인 완료). 결과적으로 **"Gemini(구) ACP 경로"는 로그인 불가로 막혀 있고, "Antigravity(신) ACP 경로"는 프로토콜 자체가 미구현이라 이중으로 막혀 있다.**

## 5. Windows 관련 제약사항

**Zed 자체:**
- Windows 포트는 2025-10 stable 도달, 2026년 기준 핵심 편집·AI 기능 지원(출처: 서드파티 리뷰/블로그 다수 — **원 출처 신뢰도는 GitHub 1차 소스보다 낮음**). 플랫폼 성숙도는 "macOS > Linux > Windows" 순으로 알려짐(동일 출처, 미확인 수준).

**Claude ACP(`claude-agent-acp`) 관련 실사용 버그 — `zed-industries/zed` 이슈 트래커:**
- Issue #37675 "ACP issue on Windows" (2025-09-05 개설, 라벨 `platform:windows` `area:ai/acp`) — ACP 스레드가 "Loading..."에서 무한 정지, Gemini/Claude Code 양쪽에서 재현 보고. Closed 상태지만 해결 방법은 확인하지 못함(**미확인**).
- Issue #48722 "zombie node.exe processes persist after Zed exit on Windows (regression)" — `claude-code-acp` v0.16.0(및 v0.13.1) 기준, Zed 종료 후 ACP 브리지+Claude agent SDK 프로세스 쌍이 좀비로 남음, 하루 사용에 24개 누적 보고 사례. "Closed as duplicate of #46474"이나 근본 수정 여부는 이 이슈 본문에서 확인 못함(**미확인**).
- (참고, Windows 아님) Issue #52054 "Claude ACP isn't inheriting the correct shell environment"는 **macOS(Zed v0.228.0)** 사례로 확인됨 — Windows 문제로 오인하지 않도록 명시해 둔다.

**`buzz-acp`(Block Buzz) 관련 — Gate G2에 가장 직접적:**
- Issue #4491 "Windows: buzz-acp is not shipped by the installer — every agent fails with 'ACP harness command buzz-acp was not found'" (2026-08-03 개설, Buzz Desktop 0.5.3 기준) — **Windows 설치형 데스크톱에는 ACP 어댑터(`claude-agent-acp.cmd`, `codex-acp.cmd`)는 설치되지만 하네스 레이어(`buzz-acp` 자체)가 누락**되어 있어 모든 에이전트가 즉시 실패한다. Closed 상태이나 실제 수정 PR/버전 확인은 하지 못했다(**미확인 — task-0038이 확인한 최신 `desktop-v0.5.20`에서 재현되는지 별도 확인 필요**).
- Issue #3612 — Windows Defender가 `buzz-acp.exe`를 `Trojan:Win32/Bearfoos.A!ml`로 오탐·격리, 시작 실패(Windows error 2).
- Issue #2342 "Windows: Codex ACP setup reports a current adapter as outdated" — Buzz가 어댑터를 `%APPDATA%\Buzz\node-tools`에서 찾는데, 이때 쓰는 제한된 PATH 프로브가 일반 Node.js 설치 경로를 포함하지 않아 `codex-acp.cmd`가 `node.exe`를 찾지 못함.
- Issue #4881, #4903 — 그 외 버그(환경변수 파싱, 온라인 mention 유실).
- **실사용 field report (gist, al3rez, 2026-07-23)**: 소스 빌드 경로로는 **성공이 확인됨.** Rust 1.94/Node 24+/pnpm 10+/Docker Desktop/Git for Windows를 수동 설치, Git Bash 필수(에이전트 shell 툴이 명시적으로 요구), 그리고 **두 가지 업스트림 버그를 직접 우회**해야 했다: ① 에이전트 spawn 시 `command.env("PATH", path)`가 상속된 PATH를 덮어써 Node 실행 파일을 못 찾는 문제 → Node 바이너리를 agent PATH 위치(`~/.local/bin`)에 복사해 우회, ② Tauri `beforeDevCommand`가 POSIX 전용 `exec`를 사용해 Windows `cmd.exe`에서 실패 → `tauri.win.conf.json`을 직접 만들어 우회. 보고서는 "PATH 수정 후 claude-agent-acp가 동작함을 확인했다"고 명시하나, `buzz-acp` 세부 연결까지 상세히 검증했는지는 불명확하다(**부분 확인**).

## 6. Phase 2 Gate G2에 대한 판단

**질문: "`buzz-acp`가 Windows에서 Claude Code를 실제로 구동하는가"**

**판정: 통과 가능성 낮음~불명 (문서 조사만으로는 결론 확정 불가 — 핸즈온 스파이크가 필요하다는 것 자체가 이 조사의 결론이다)**

근거:
1. **가장 쉬운 시나리오(공식 Windows Desktop 설치판 그대로 사용)는 실패로 보는 것이 합리적** — 2026-08-03에 개설된 이슈가 정확히 "설치형에는 하네스 바이너리 자체가 없다"고 보고하며, 이 수정이 반영됐는지 확인하지 못했다.
2. **더 어려운 시나리오(소스 빌드)는 실제 성공 사례가 존재**하지만, Rust/Node/pnpm/Docker 전체 툴체인 설치 + 최소 2개의 업스트림 버그를 직접 코드/설정 레벨에서 우회해야 한다. 이는 이 조사 자체에 부과된 "설치 없음" 제약과 정면으로 배치되는 무게의 작업이며, Jarvis-Core 관점에서도 "표준 하나로 통일해 유지보수 부담을 줄인다"는 ACP 도입의 원래 취지를 상당 부분 상쇄한다.
3. **Claude Code 쪽 자체가 이미 두 겹의 불확실성을 갖는다** — (a) 공식 ACP 지원이 없어 항상 커뮤니티 wrapper에 의존해야 하고, (b) 그 wrapper들조차 인증 모델이 서로 다른 5개 구현으로 분열되어 있어 "buzz-acp가 어떤 걸 호출하는지"부터 확정해야 한다(task-0038은 이를 단일 항목처럼 단순화했다).
4. **buzz-acp를 소비하는 것과 별개로, 같은 npm 패키지(`claude-agent-acp`)를 Windows에서 subprocess로 구동하는 Zed 쪽 트랙에서도 독립적으로 Windows 전용 라벨 버그(무한 로딩, 좀비 프로세스)가 확인된다** — 이는 문제가 Buzz 고유가 아니라 "Windows + Node.js 기반 ACP 브리지"라는 조합 자체에 있을 가능성을 시사하는 두 번째 독립 소스다.
5. 다만 **"완전히 불가능하다"는 결론도 내릴 수 없다** — al3rez의 field report는 실제로 우회 후 작동을 확인했다고 보고한다. 즉 이 조합은 "깨져 있지만 고칠 수 있는 상태"이지 "근본적으로 막힌 상태"는 아니다.

**결론적으로 Gate G2는 "문서만으로 통과/실패를 판정할 수 없는 항목"이다.** 확정하려면 실제로 (a) 최신 Buzz Desktop 설치판을 Windows에 깔아 #4491 재현 여부를 확인하거나, (b) 소스 빌드로 al3rez의 우회를 재현해 `claude-agent-acp`까지 실제로 응답을 받는 스파이크가 필요하다. 이 스파이크는 이 task-0045의 범위(코드 변경/설치 없음) 밖이므로 수행하지 않았다.

## 7. 미확인 항목

- ACP 스펙의 정확한 semver 버전 번호 — 공식 사이트에서 노출되지 않음.
- `anthropics/claude-code` Issue #6686의 실제 코멘트 스레드에 Anthropic 직원의 공식 코멘트가 있는지 — WebFetch 요약 결과 "코멘트 없음"으로 나왔으나 이는 요약 도구의 한계일 수 있어 원문 스레드를 직접 열람하지 못한 채로는 확정할 수 없음.
- `openai/codex` Issue #2785의 정확한 closure 사유(구현되어 닫혔는지, wontfix인지).
- Codex CLI에 네이티브 `codex acp` 서브커맨드가 정말로 존재하지 않는지 — 최신 공식 릴리스 노트를 직접 훑지 않았다.
- `block/buzz` Issue #4491(Windows 설치판에 buzz-acp 하네스 누락)이 task-0038이 확인한 최신 `desktop-v0.5.20`(2026-08-26)에서도 재현되는지.
- Zed 쪽 Windows ACP 버그(#37675, #48722)가 최신 Zed 빌드에서 실제로 재현되는지(이슈는 closed 상태이나 근본 수정 확인은 못함).
- `agentclientprotocol/claude-agent-acp`, `agentclientprotocol/codex-acp`의 정확한 최신 버전/릴리스 날짜, README의 OS 지원 매트릭스(존재한다면).
- Antigravity CLI(agy)가 향후 ACP를 구현할 공개 로드맵이 있는지 — 커뮤니티 요청(#31)만 확인, Google 측 공식 로드맵 문서는 찾지 못함.

## 참고 출처

- [Agent Client Protocol — Overview](https://agentclientprotocol.com/overview/introduction)
- [GitHub - zed-industries/agent-client-protocol (agentclientprotocol/agent-client-protocol)](https://github.com/zed-industries/agent-client-protocol)
- [Zed — Agent Client Protocol](https://zed.dev/acp)
- [Zed Blog — Claude Code: Now in Beta in Zed](https://zed.dev/blog/claude-code-via-acp)
- [Zed — Claude Agent ACP page](https://zed.dev/acp/agent/claude-agent)
- [Zed — Codex CLI ACP page](https://zed.dev/acp/agent/codex-cli)
- [Zed docs — External Agents](https://zed.dev/docs/ai/external-agents)
- [Feature Request: Add support for Agent Client Protocol (ACP) · Issue #6686 · anthropics/claude-code](https://github.com/anthropics/claude-code/issues/6686)
- [GitHub - agentclientprotocol/claude-agent-acp](https://github.com/agentclientprotocol/claude-agent-acp)
- [GitHub - harukitosa/claude-code-acp](https://github.com/harukitosa/claude-code-acp)
- [Support the Agent Client Protocol · Issue #2785 · openai/codex](https://github.com/openai/codex/issues/2785)
- [GitHub - agentclientprotocol/codex-acp](https://github.com/agentclientprotocol/codex-acp)
- [Add Antigravity (agy) adapter: acpx antigravity targeting agy --acp stdio · Issue #362 · openclaw/acpx](https://github.com/openclaw/acpx/issues/362)
- [Feature request: add ACP (Agent Client Protocol) stdio JSON-RPC mode · Issue #31 · google-antigravity/antigravity-cli](https://github.com/google-antigravity/antigravity-cli/issues/31)
- [ACP issue on Windows · Issue #37675 · zed-industries/zed](https://github.com/zed-industries/zed/issues/37675)
- [zombie node.exe processes persist after Zed exit on Windows · Issue #48722 · zed-industries/zed](https://github.com/zed-industries/zed/issues/48722)
- [Claude ACP isn't inheriting the correct shell environment · Issue #52054 · zed-industries/zed](https://github.com/zed-industries/zed/issues/52054)
- [Windows: buzz-acp is not shipped by the installer · Issue #4491 · block/buzz](https://github.com/block/buzz/issues/4491)
- [Cross-platform release failures (Windows Defender quarantine 등) · Issue #3612 · block/buzz](https://github.com/block/buzz/issues/3612)
- [Windows: Codex ACP setup reports a current adapter as outdated · Issue #2342 · block/buzz](https://github.com/block/buzz/issues/2342)
- [Running Buzz (block/buzz) on Windows: setup, the two upstream bugs, and workarounds (gist, al3rez, 2026-07-23)](https://gist.github.com/al3rez/ad3afecfe45d6d36804358b9e3ffab17)
- 로컬 파일: `C:\Users\hsy\.gemini\antigravity-cli\builtin\skills\**` (15개 문서, grep 확인), `agy --help` 실행 출력(2026-08-27, 본 조사 세션에서 직접 실행)
- `memory/tasks/task-0037-gemini-cli-local-dev-environment.md`, `reports/task-0038-ai-agent-collaboration-platform-buzz-research.md`
