# task-0034-local-team-manager-approval-boundary

- id: `task-0034-local-team-manager-approval-boundary`
- title: `Local Team Manager 운영 경계 및 승인 구조 검증`
- status: `NEEDS_APPROVAL`
- repo: `jarvis-core`
- created_at: `2026-08-26 11:46 UTC`
- updated_at: `2026-08-26 11:46 UTC`
- summary: `master-plan.md §6의 잠긴 기능 중 background worker/unattended execution과 자동 prompt rendering·실행이 로컬 Team Manager에도 적용됨을 확인했다(외부 API/LLM/credential은 로컬 경로에 문자 그대로는 미적용). Owner 승인 식별은 기존 adapters/discord의 /approve 계약 재사용을 제안한다. 최소 Phase B로는 상시 봇 대신 Owner가 수동 호출하는 1회성 로컬 CLI 조언 도구를 제안했고 어떤 lock도 건드리지 않는다. 설치·다운로드·코드 구현 없음. NEEDS_APPROVAL 사유는 최소 Phase B 범위와 승인 식별 방식의 Owner 확정이 필요하기 때문이다. 전체 원문은 아래 요약(원문) 절에 그대로 보존했다.`
- source_command: `Discord work-order (task-0034)`

## 요약 (원문)

이 절은 task-0054에서 옮긴 원본 summary 전문이다. summary 필드가 500자 상한을 넘어 canonical 검증에 실패했기 때문이며, 내용은 한 글자도 줄이지 않고 그대로 보존했다.

master-plan.md §6 잠긴 기능 중 "background worker/unattended execution"과 "자동 prompt rendering 또는 실행"이 로컬 Team Manager에도 명확히 적용됨을 확인했다("외부 API/LLM/credential"은 로컬 경로엔 문자 그대로는 미적용). Owner 승인 메시지 식별은 기존 adapters/discord의 /approve <task-id> approve|reject 계약 재사용을 제안. 가장 작은 Phase B로 "상시 봇 대신 Owner가 수동 호출하는 1회성 로컬 CLI 조언 도구"를 제안(어떤 lock도 건드리지 않음). 설치/다운로드/코드 구현 없음. work-order: prompts/task-0034-local-team-manager-approval-boundary-work-order.md. NEEDS_APPROVAL 사유: 제안한 최소 Phase B 범위와 승인 메시지 식별 방식을 Owner/ChatGPT가 확정해야 다음 단계로 진행 가능.
