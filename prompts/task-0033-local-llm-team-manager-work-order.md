# task-0033 work-order: 로컬 LLM 기반 Team Manager 아키텍처 조사·설계

- task_id: `task-0033-local-llm-team-manager`
- content authority: ChatGPT (팀장), Owner를 통해 전달
- received_at: `2026-08-26 11:42 UTC` (Discord DM)
- recorded_by: Claude Code (mechanical transcription only, 내용 재정의 없음)
- 관련: task-0031(Phase A, 코드 무수정), task-0032(OpenAI API 경로 조사, 대안 비교 대상)

## 원문 (Owner가 전달한 그대로)

OpenAI API를 사용하지 않고 로컬 LLM을 Team Manager로 사용하는 아키텍처를
조사·설계하라. 기존 Phase A 코드는 수정하지 말고, 현재 PC 하드웨어를 먼저
확인한 뒤 실행 가능한 로컬 모델 후보와 inference backend(Ollama, llama.cpp,
LM Studio, vLLM 등)를 비교하고, Discord → Team Manager → Claude Code →
Discord 전체 흐름을 설계하라. 실제 모델 다운로드, credential 발급, 외부 API
연결, 코드 구현은 하지 말고 설계/조사만 수행하라.

## 실행 경계 (원문에 이미 명시된 조건, 재정의 아님)

- `adapters/team-manager-bot/` Phase A 코드 수정 금지.
- 모델 다운로드 금지.
- credential 발급 금지.
- 외부 API 연결 금지.
- 코드 구현 금지 — 설계/조사만.
