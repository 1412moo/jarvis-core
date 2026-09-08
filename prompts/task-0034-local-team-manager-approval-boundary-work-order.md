# task-0034 work-order: Local Team Manager 운영 경계 및 승인 구조 검증

- task_id: `task-0034-local-team-manager-approval-boundary`
- content authority: ChatGPT (팀장), Owner를 통해 전달
- received_at: `2026-08-26 11:45 UTC` (Discord DM)
- recorded_by: Claude Code (mechanical transcription only, 내용 재정의 없음)
- 관련: task-0033(로컬 LLM 조사, 이번 task의 전제)
- 참고: 원문 제목이 "ask-0034"로 표기됐으나 번호 순서와 task-0033 후속 관계상
  task-0034로 확정. 내용은 원문 그대로 transcribe.

## 원문 (Owner가 전달한 그대로, 제목 오타는 위 참고란에만 표기)

task-0034 — Local Team Manager 운영 경계 및 승인 구조 검증

task-0033의 조사 결과를 기반으로 검토한다.

목표는 로컬 LLM Team Manager를 실제로 설치하는 것이 아니라, 현재 확정된 AI
Team Architecture에서 로컬 Team Manager를 도입할 경우 기존 승인 게이트와
충돌하지 않는 운영 경계를 확정하는 것이다.

반드시 지킬 것:

모델 다운로드 금지
Ollama 설치 금지
Discord bot token 발급/사용 금지
외부 API 연결 금지
코드 구현/수정 금지
배포 및 background worker 실행 금지

조사할 것:

docs/master-plan.md §6의 잠긴 기능 중 현재 설계가 정확히 어떤 항목에 해당하는지 확인
Owner 승인 없이 허용 가능한 범위와 반드시 별도 승인이 필요한 범위를 구분
Team Manager가 Claude Code에게 자동으로 작업을 전달하는 것과 Owner가 승인한
작업을 자동 실행하는 것의 차이를 명확히 정의
AI-to-AI 무한 루프 방지 및 왕복 횟수 제한 방안 검토
Owner 승인 메시지를 어떤 형태로 식별할지 설계
현재 Phase 1을 유지하면서 로컬 Team Manager를 시험할 수 있는 가장 작은 Phase B
범위를 제안
Ollama + 모델 설치 이후에도 기존 prompts/, memory/tasks/, access.json 소유권
원칙을 침해하지 않는지 검증

결과는 조사/설계 보고서로만 작성하고, 구현은 하지 않는다.

## 실행 경계 (원문에 이미 명시된 조건, 재정의 아님)

- 모델 다운로드 금지.
- Ollama 설치 금지.
- Discord bot token 발급/사용 금지.
- 외부 API 연결 금지.
- 코드 구현/수정 금지.
- 배포 및 background worker 실행 금지.
- 산출물은 조사/설계 보고서만.
