# task-0038-ai-agent-collaboration-platform-buzz-research

- id: `task-0038-ai-agent-collaboration-platform-buzz-research`
- title: `AI Agent 협업 플랫폼(Buzz 등) 생태계 조사 및 Jarvis-Core 통합 전략 결정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-27 06:25 UTC`
- updated_at: `2026-08-27 10:20 UTC`
- summary: `조사 완료. 최종 verdict는 INTEGRATE BUZZ + JARVIS(조건부·단계적)이며 전체 보고서는 reports/task-0038-ai-agent-collaboration-platform-buzz-research.md에 있다. 100점 점수화에서 Buzz 80, Jarvis-Core 62였고 격차 대부분이 협업 표면 한 항목에서 발생했다. Buzz는 승인 게이트 executor 미완성, 감사 로그 fire-and-forget 유실 가능, Windows self-host 결함 때문에 ADOPT/FORK를 거부했다. 권고는 Phase 1에서 외부 의존 0으로 아키텍처만 차용하고 Phase 2는 게이트 3종 통과 시에만 통합하되 승인 판정은 Jarvis가 100% 소유하는 것이다. Owner 승인 3건 완료. 전체 원문은 아래 요약(원문) 절에 그대로 보존했다.`
- source_command: `Direct instruction via Claude Code session (task-0038, no Discord channel tag)`

## 요약 (원문)

이 절은 task-0054에서 옮긴 원본 summary 전문이다. summary 필드가 500자 상한을 넘어 canonical 검증에 실패했기 때문이며, 내용은 한 글자도 줄이지 않고 그대로 보존했다.

조사 완료. 최종 verdict = INTEGRATE BUZZ + JARVIS (조건부·단계적). 전체 보고서: reports/task-0038-ai-agent-collaboration-platform-buzz-research.md. 근거 요약 — 점수화(100점)에서 Buzz 80 / AgentConnect 71 / open-tag(fancyboi999) 71 / OpenTag(amplifthq) 68 / OpenHands Agent Canvas 68 / OpenAgents 63 / Jarvis-Core 62 / CircleChat 55 / Canopy 55. Jarvis-Core는 오케스트레이션(13 vs 9)과 보안·거버넌스(5 vs 4)에서 Buzz보다 앞서지만 협업 표면에서 6 vs 19로 총점 차 18점 중 13점을 한 항목에서 잃는다. Buzz는 승인 게이트 executor가 자체 문서상 미완성(request_approval이 suspend 대신 Failed 처리), 감사 로그가 fire-and-forget이라 유실 가능, Windows self-host 데스크톱 접속 결함(issue #3490/#2872) 미확인 상태 → ADOPT/FORK 거부(543MB·30크레이트·5개월에 PR 6,900개·미해결 이슈 3,200건, Rust vs Python). 권고: Phase 1은 외부 의존 0으로 Buzz 아키텍처만 차용(append-only 이벤트 로그 task 모델, 역할별 서명 키, no-secrets 코드 강제, 감사 해시체인, ACP 조사), Phase 2는 게이트 3종(Windows self-host relay 접속 / buzz-acp+Claude Code 왕복 / 승인 executor 상태) 전부 통과 시에만 Buzz를 협업 표면으로 통합하되 승인 판정은 100% Jarvis 소유. 승인 요청 항목: (1) 진행 중인 Director Dashboard v0.1B 착수 보류 여부 — Buzz Desktop과 정면 중복 판정, (2) Jarvis Console을 메인 UI에서 Jarvis 전용 승인 화면으로 축소하는 방향 전환, (3) Phase 1 6개 항목 착수 승인. 사유: 제품 방향(아키텍처) 변경이며 기존 master-plan의 다음 작업을 바꾸므로 Owner 결정 사항. 승인 지연 시 영향: Buzz와 중복되는 Dashboard/Console 작업에 공수가 계속 투입된다. 코드 변경·커밋·설치 없음(조사·보고서 작성만). work-order: prompts/task-0038-ai-agent-collaboration-platform-buzz-research-work-order.md. [2026-08-27 10:20 UTC Owner 승인 결과] ① Director Dashboard v0.1B 착수 보류 — 승인. ② Jarvis Console을 메인 UI에서 승인 전용 화면으로 방향 전환 — 지금 승인(docs/master-plan.md, apps/jarvis-console/README.md에 방향 전환 기록 완료; 실제 UI 축소 구현은 별도 후속 task). ③ Phase 1(task-0039) 6개 항목 전체 착수 — 승인, task-0039 status DOING 전환, 하위 실행 단위는 task-0040~0045로 분해.
