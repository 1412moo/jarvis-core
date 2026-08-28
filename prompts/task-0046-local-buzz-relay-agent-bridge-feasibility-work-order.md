# task-0046 work-order: 로컬(Windows) Buzz Relay/WebSocket + Agent Bridge 연결 가능성 조사

- task_id: `task-0046-local-buzz-relay-agent-bridge-feasibility`
- content authority: Owner (직접 전달, Claude Code 세션)
- received_at: `2026-08-27 13:00 UTC`
- recorded_by: Claude Code (mechanical transcription only, 내용 재정의 없음)
- 관련: task-0038(Buzz 생태계 조사), task-0045(ACP feasibility — Claude Code/Codex 공식 ACP 미지원 확인)

## 원문 (Owner가 전달한 그대로)

task-0045 후속으로 로컬 Buzz 연결 가능성을 조사해줘.

목표는 Hostinger/VPS를 사용하는 방식이 아니라 Windows 로컬 PC 한 대에서 Buzz를 실행하고,
Buzz의 Relay/WebSocket 구조를 이용해 Claude Code/Codex/Gemini 등의 로컬 agent와 연결할 수
있는지 확인하는 것이다.

먼저 Buzz의 현재 소스/문서와 기존 task-0038, task-0045 결과를 다시 확인해라.

특히 다음을 조사해라:

1. Buzz를 Hostinger/VPS 없이 Windows 로컬에서 실행할 수 있는가?
2. Buzz Relay를 로컬에서 실행할 수 있는가?
3. Buzz Desktop ↔ 로컬 Relay가 WebSocket으로 연결되는 구조가 정확히 어떻게 되는가?
4. Hostinger가 제공하는 것은 정확히 무엇이며, 그중 로컬에서는 무엇을 생략할 수 있는가?
5. buzz-acp가 반드시 필요한 구조인지, 아니면 Buzz Relay/WebSocket과 별도의 local agent
   bridge를 만들어 Claude Code/Codex/Gemini CLI를 연결할 수 있는지 조사해라.
6. Claude Code/Codex/Gemini가 공식 ACP를 지원하지 않는다는 task-0045 결과를 전제로, ACP를
   사용하지 않는 대안을 조사해라.
7. Windows에서 가능한 가장 단순한 로컬 구조를 제안해라.
8. 실제 설치/구현 전에 필요한 최소한의 핸즈온 검증 항목을 정의해라.

## 실행 경계 (원문에 이미 명시된 조건, 재정의 아님)

- Hostinger 가입/결제하지 않는다.
- VPS를 만들지 않는다.
- Buzz를 설치하거나 실제 연결 구현하지 않는다.
- API key를 발급하거나 외부 서비스에 연결하지 않는다.
- 기존 Jarvis-Core 코드를 변경하지 않는다.
- 조사 결과와 필요한 최소 검증 절차만 문서화한다.

## 결론 형식 (원문 지정)

결과는 `reports/` 아래 별도 조사 보고서로 작성하고, 다음 세 가지로 명확하게 판정한다.

- A. 로컬 Buzz Relay/WebSocket 실행 가능 여부
- B. 로컬 Agent Bridge 방식의 기술적 가능성
- C. 실제 구현 전에 필요한 최소 핸즈온 스파이크

전제: "Hostinger 방식과 완전히 똑같이 만들 필요가 없다" — 목표는 24시간 외부 서버가 아니라
Windows PC가 켜져 있는 동안 로컬에서 Buzz + Jarvis-Core + AI agents가 협업하는 것이다.
