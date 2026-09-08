# task-0032 work-order: ChatGPT Team Manager 연동 방식 조사/설계

- task_id: `task-0032-chatgpt-team-manager-integration-research`
- content authority: ChatGPT (팀장), Owner를 통해 전달
- received_at: `2026-08-26 11:31 UTC` (Discord DM)
- recorded_by: Claude Code (mechanical transcription only, 내용 재정의 없음)
- 관련: task-0031(Phase A 완료·커밋 `9bfb9b7`, 이번 task에서 코드 수정 안 함)

## 원문 (Owner가 전달한 그대로)

task-0032: ChatGPT Team Manager 연동 방식 조사/설계

Phase A 코드는 수정하지 않는다.
API key 발급하지 않는다.
Discord bot token 발급하지 않는다.
외부 API 호출하지 않는다.
OpenAI API를 사용할 경우 정확히 무엇이 가능한지 조사한다.
ChatGPT 웹 세션과 OpenAI API의 차이를 명확히 정리한다.
Discord → Team Manager → Claude Code → Discord의 실제 메시지 흐름을 설계한다.
Owner 승인 없이 실행/자동화하지 않는다.
최종적으로 Phase B에서 무엇을 발급하고 얼마까지 비용이 발생할 수 있는지까지 제시한다.

## 실행 경계 (원문에 이미 명시된 조건, 재정의 아님)

- `adapters/team-manager-bot/` Phase A 코드 수정 금지.
- API key 발급 금지.
- Discord bot token 발급 금지.
- 외부 API 호출 금지.
- Owner 승인 없는 실행/자동화 금지.
- 산출물: OpenAI API로 가능한 것 조사, ChatGPT 웹 세션 vs OpenAI API 차이 정리,
  Discord→Team Manager→Claude Code→Discord 메시지 흐름 설계, Phase B 발급/비용 제시.
