# task-0030 work-order: Codex-based ChatGPT Team Manager for Discord

- task_id: `task-0030-codex-chatgpt-team-manager-discord`
- content authority: ChatGPT (팀장), Owner를 통해 전달
- received_at: `2026-08-26 11:06 UTC` (Discord DM)
- recorded_by: Claude Code (mechanical transcription only, 내용 재정의 없음)

## 원문 (Owner가 전달한 그대로)

task-0030: Codex-based ChatGPT Team Manager for Discord

목표: ChatGPT/Codex를 팀장 에이전트로 활용하여 Discord에서 Owner–ChatGPT–Claude
Code 3자 협업이 가능하도록 한다.

우선 기존 jarvis-core 구조를 조사하고, Codex가 Discord와 통신하는 가장 안전하고
최소 변경인 방법을 설계한다.

구현 전에 조사·설계 결과를 보고한다.

특히:

- Codex가 ChatGPT 계정과 어떻게 연결되는지
- Discord 송수신을 어떤 방식으로 붙일지
- Claude Discord Plugin과 어떻게 공존할지
- prompts/ work-order 구조를 어떻게 사용할지
- ChatGPT가 언제 개입하고 언제 Claude에게 자율 위임할지
- Owner 승인 gate를 어떻게 유지할지
- API/credential/비용이 필요한지

를 확인한다.

실제 토큰 생성·변경, 외부 서비스 연결, 배포는 조사 결과 승인 전까지 하지 않는다.

## 실행 경계 (원문에 이미 명시된 조건, 재정의 아님)

- 이번 단계는 조사·설계 보고까지만. 구현 금지.
- 토큰 생성/변경 금지.
- 외부 서비스 연결 금지.
- 배포 금지.
