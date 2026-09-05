# task-0035-local-team-manager-model-benchmark

- id: `task-0035-local-team-manager-model-benchmark`
- title: `로컬 Team Manager 후보 모델 성능/실행 가능성 검증`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-26 11:53 UTC`
- updated_at: `2026-08-26 12:23 UTC`
- summary: `Ollama 설치 후 qwen2.5:7b와 llama3.1:8b를 CPU 전용으로 5종 팀장 시나리오에서 테스트했다. 두 모델 모두 5-7 tok/s로 실시간 대화에는 느리다. Qwen이 한국어 품질과 페르소나 준수는 우세했으나 5턴째에 이전 대화 혼동, 중국어 전환, 이미 거부했던 위험 요청 재수용이라는 안전성 결함을 보였다. Llama는 conflict-handling에서 더 단호했다. 결론은 두 모델 다 상시 Team Manager로는 부적합이며 task-0034의 1회성 로컬 CLI 범위를 권고한다는 것이다. 테스트 후 모델은 unload했고 Ollama는 설치된 채로 남는다. 전체 원문은 아래 요약(원문) 절에 보존했다.`
- source_command: `Discord work-order (task-0035)`

## 요약 (원문)

이 절은 task-0054에서 옮긴 원본 summary 전문이다. summary 필드가 500자 상한을 넘어 canonical 검증에 실패했기 때문이며, 내용은 한 글자도 줄이지 않고 그대로 보존했다.

Ollama(winget) 설치, qwen2.5:7b(4.7GB)와 llama3.1:8b(4.9GB) 다운로드, CPU 전용(100% CPU, GPU 미사용) 로컬 추론으로 5종 팀장 시나리오 테스트 완료. Qwen 5.18-6.67 tok/s(요청당 62-182초), Llama 5.66-6.02 tok/s(72-200초) — 실시간 대화로는 느림. Qwen이 한국어 품질/페르소나 준수 우세, 단 5턴째(context retention 테스트)에서 이전 대화 혼동+중국어 전환+이미 거부했던 위험 요청(force-push+API키 하드코딩)에 재차 응하려는 심각한 안전성 결함 관측. Llama는 conflict-handling에서 더 단호했음(작업을 진행하지 마십시오로 명확히 종료). 결론: 두 모델 다 상시 Team Manager로 쓰기엔 속도/안전성 미흡, 추천 후속은 task-0034의 "1회성 로컬 CLI" 범위로 제한. 테스트 후 두 모델 모두 메모리에서 unload(ollama stop), Ollama 앱/서비스 자체는 설치된 채로 남음(Owner 승인 범위인 "Ollama 설치"에 해당, 상시 로드된 모델은 없음). Discord 연결/토큰/외부API/자동전달/access.json 변경/jarvis-bot·Plugin 수정 전부 없음. work-order: prompts/task-0035-local-team-manager-model-benchmark-work-order.md.
