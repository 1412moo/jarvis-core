# task-0033-local-llm-team-manager

- id: `task-0033-local-llm-team-manager`
- title: `로컬 LLM 기반 Team Manager 아키텍처 조사·설계`
- status: `NEEDS_APPROVAL`
- repo: `jarvis-core`
- created_at: `2026-08-26 11:42 UTC`
- updated_at: `2026-08-26 11:42 UTC`
- summary: `Owner PC 하드웨어(AMD Ryzen 5 7530U 6C/12T, RAM ~13.9GB, 통합 GPU만, 디스크 여유 351GB)를 확인하고, Ollama/llama.cpp/LM Studio/vLLM을 비교해 이 하드웨어에는 Ollama(llama.cpp 기반) + 7B급 4-bit 양자화 모델을 권고했다. 모델 다운로드/credential 발급/외부 연결/코드 구현 없음. work-order: prompts/task-0033-local-llm-team-manager-work-order.md. NEEDS_APPROVAL 사유: OpenAI API 경로(task-0032) 대비 로컬 경로를 택할지, 모델 후보 중 무엇을 쓸지, master-plan.md §6 잠긴 기능("자동 Codex/ChatGPT 호출", "background worker/unattended execution")이 로컬 모델 기반에도 그대로 적용되는지 해석이 필요해 Owner/ChatGPT 결정 대기.`
- source_command: `Discord work-order (task-0033)`
