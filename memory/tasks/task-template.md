# task-####-slug

<!-- Omit completion_evidence until Record Completion Evidence appends it after summary. Do not add an empty field row. -->
<!-- 수동 SOP task 본문의 범위 표에는 "| owned | `파일 경로`, `디렉터리/` |" 행을 둔다. candidate 전 scripts/check_task_record.py가 staged 파일과 대조한다(task-0171). -->

- id: `task-####-slug`
  - 규칙: `task-####-slug` 형식(4자리 숫자 + 소문자 하이픈 slug)만 사용한다.
- title: `작업 제목`
  - 규칙: 사람이 즉시 이해할 수 있는 한 줄 제목으로 작성한다.
- status: `TODO`
  - 규칙: `TODO | DOING | BLOCKED | ON_HOLD | DONE | FAILED | NEEDS_APPROVAL | CLOSED` 8개 값만 허용한다.
- repo: `jarvis-core`
  - 규칙: 실제 작업 대상 저장소 식별자를 정확히 기입한다.
- created_at: `YYYY-MM-DD HH:mm UTC`
  - 규칙: Task 파일 최초 생성 시각을 UTC 기준으로 기록하고 이후 변경하지 않는다.
- updated_at: `YYYY-MM-DD HH:mm UTC`
  - 규칙: 상태 또는 summary 등 내용 변경 시마다 UTC 시각으로 갱신한다.
- summary: `이 Task의 범위와 현재 상태를 1~3문장으로 요약`
  - 규칙: 1~3문장으로 범위/진행상황을 쓰고 필요 시 확인 필요사항(리스크, 의존성, 승인 항목)을 포함한다.
