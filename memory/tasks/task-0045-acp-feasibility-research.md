# task-0045-acp-feasibility-research

- id: `task-0045-acp-feasibility-research`
- title: `ACP(Agent Communication Protocol)로 Claude Code/Codex/Gemini를 통합 인터페이스로 붙일 수 있는지 조사`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-27 10:20 UTC`
- updated_at: `2026-08-28 10:15 UTC`
- summary: `ACP(Agent Client Protocol) 실현 가능성을 문서·GitHub 이슈트래커 조사로 확인 완료(설치/코드변경/API키 없음). ACP는 Zed Industries가 만들고 현재 커뮤니티(agentclientprotocol 조직)가 관리하는 실재 프로토콜(JSON-RPC over stdio) — task-0038의 용어 사용 자체는 정확했다. 그러나 핵심 전제는 정정 필요: Claude Code는 공식 ACP 미지원(anthropics/claude-code #6686 "not planned"으로 closed, 공식문서 언급 없음) — 존재하는 건 인증모델이 다른 5개 이상의 서드파티 wrapper(SDK 기반 API키형 vs CLI-wrap 구독형)뿐이다. Codex도 공식 미지원으로 보이며 마찬가지로 외부 wrapper뿐(closure 사유 미확인). Antigravity CLI(agy)는 ACP 완전 미지원을 로컬에서 직접 확인(`agy --help`/builtin skill 문서 15개 grep 0건) + GitHub 기능요청(#31, 2026-05-20 개설, 여전히 OPEN) — MCP만 지원, ACP는 미구현. Gate G2("buzz-acp가 Windows에서 Claude Code를 실제로 구동하는가")는 **낮음~불명**으로 판정: Windows Buzz Desktop 설치판은 buzz-acp 하네스 바이너리 자체가 누락된 이슈(#4491, 2026-08-03 개설)가 있었고, Windows Defender가 buzz-acp.exe를 트로이목마로 오탐하는 이슈(#3612)도 확인됨. 다만 소스 빌드 경로로는 실제 성공 field report(2026-07-23, PATH 치환 버그 등 2개 우회 필요)가 존재해 "완전 불가능"은 아니다 — 문서 조사만으로는 확정 불가, 핸즈온 스파이크 필요가 결론. Owner가 Phase 2(Buzz 통합) 착수 여부를 재검토해야 하는 전략적 함의가 있어 NEEDS_APPROVAL로 표시. 보고서: reports/task-0045-acp-feasibility-research.md. [2026-08-28 10:15 UTC 해소] task-0046 후속 조사로 Gate G2가 "ACP 경로 단독"이 아니라 "WebSocket 직결 Agent Bridge 경로 포함"으로 재정의됨(task-0038 §6.0 addendum) — 이 task가 제기한 전략적 함의는 해소·반영 완료되어 status DONE 처리. 실제 핸즈온 검증은 task-0047(TODO, Phase 1 완료 후 별도 승인)로 이관.`
- source_command: `task-0038 승인 항목 ③(Phase 1 착수) 하위 실행 단위`
