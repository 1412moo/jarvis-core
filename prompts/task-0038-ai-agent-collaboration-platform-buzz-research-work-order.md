# task-0038 work-order: Jarvis-Core AI Agent 협업 플랫폼 조사 및 통합 전략

- task_id: `task-0038-ai-agent-collaboration-platform-buzz-research`
- content authority: Owner (직접 전달, Claude Code 세션)
- received_at: `2026-08-27 06:25 UTC`
- recorded_by: Claude Code (mechanical transcription only, 내용 재정의 없음)

## 원문 (Owner가 전달한 그대로)

# Jarvis-Core AI Agent 협업 플랫폼 조사 및 통합 전략

## 목적

현재 개발 중인 `jarvis-core`의 방향성을 재검토한다.

최근 Block이 공개한 오픈소스 프로젝트 **Buzz (buzz.xyz / github.com/block/buzz)**를 발견했다.

Buzz가 단순한 Slack/Discord 대체제가 아니라,

> 인간 + 여러 AI Agent가 같은 workspace/channel에서 협업하고,
> Agent가 실제 작업·코드·Git·리뷰·workflow에 참여하는 환경

을 목표로 하고 있다는 점에서 현재 우리가 Jarvis-Core를 통해 만들고 있는 방향과 상당히 유사해 보인다.

따라서 단순히 Buzz 하나만 평가하지 말고, **2026년 현재 존재하는 유사한 AI-agent collaboration / AI employee workspace / multi-agent team / Slack-for-agents 계열 프로젝트를 폭넓게 조사한 뒤**, Jarvis-Core가 앞으로 어떤 위치를 가져야 하는지 결정한다.

(전체 조사 항목 1~13, 보고서 목차, 점수화 기준, 원칙은 Owner 원문 그대로이며 아래 work-order 실행 경계에 요약 없이 위임 프롬프트로 그대로 전달됨 — 세부 문항은 task-0038 실행 에이전트에게 전달된 프롬프트 참조.)

## 실행 경계 (원문에 이미 명시된 조건, 재정의 아님)

- 실제 GitHub/공식 자료 기반 조사. 블로그/SEO 글만으로 판단 금지.
- Buzz는 architecture + 실제 source code 구조까지 확인.
- jarvis-core 코드 변경/커밋 없음 (조사·보고서 작성만).
- 결론은 Owner가 듣고 싶어할 결론에 맞추지 않는다 — 근거 기반 정직한 판단.
- 최종 결과는 Owner 지정 목차(Executive Summary ~ 8. 최종 Verdict) 순서로 작성.
- 미확인 사항은 완료로 기록하지 않는다(AGENTS.md 원칙 8 준수).
