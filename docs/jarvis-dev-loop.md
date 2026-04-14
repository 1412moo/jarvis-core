# jarvis-core 개발 루프

이 문서는 현재 구현된 명령(`/task`, `/plan`, `/review-task`, `/approve`, `/report`, `/retro today`) 기준으로,
jarvis-core의 개발 루프를 입력/상태 관리 관점에서 정리한다.

## A. 개발 루프 개요

1. `/task <request>` → 작업 생성
   - 작업 요청을 task 파일(`memory/tasks/*.md`)로 생성한다.
2. `/plan <request>` → 계획 초안
   - 요청 기반 계획 초안(`plan_draft`)을 생성한다.
3. `/review-task <task-id>` → 검토
   - 기존 task 메타데이터를 읽어 리뷰 결과를 만든다.
4. `/approve <task-id> approve|reject` → 상태 전이
   - `NEEDS_APPROVAL -> DOING` 또는 `NEEDS_APPROVAL -> FAILED` 전이를 적용한다.
5. `/report` (또는 `/report today`) → 집계
   - task 상태를 집계해 요약 리포트를 반환한다.
6. `/retro today` → 회고
   - 오늘 집계를 기반으로 highlights/risks/next steps를 반환한다.

## B. 각 명령 역할 요약

### 1) `/task <request>`
- 목적: 새 작업(Task) 생성
- 입력 형식: `/task <request>`
- 출력 요약:
  - 성공: `success` + `task_id`, `file_name`
  - 보류: `hold` + `reason`
  - 오류: `error` + `reason`
- read/write 여부: **write** (`memory/tasks/*.md` 생성)

### 2) `/plan <request>`
- 목적: 요청 기반 계획 초안 생성
- 입력 형식: `/plan <request>`
- 출력 요약:
  - `plan_draft` + `goal`, `files_to_check`, `scope_summary`, `out_of_scope`, `codex_prompt`
- read/write 여부: **read-only** (파일 생성/수정 없음)

### 3) `/review-task <task-id>`
- 목적: task 검토 정보 생성
- 입력 형식: `/review-task <task-id>`
- 출력 요약:
  - 성공: `review_task_result` + 상태/리뷰 노트/다음 단계/관련 파일
  - 미존재: `not_found`
  - 오류: `error`
- read/write 여부: **read-only** (`memory/tasks/<task-id>.md` 조회)

### 4) `/approve <task-id> approve|reject`
- 목적: 승인 대기 task 상태 전이 적용
- 입력 형식: `/approve <task-id> approve|reject`
- 출력 요약:
  - 성공: `approve_file_write_result(applied=true)`
  - 미적용: `approve_file_write_result(applied=false, kind, reason)`
  - usage 오류: `error(reason=usage:/approve <task-id> approve|reject)`
- read/write 여부: **read + write** (`memory/tasks/<task-id>.md` 상태/updated_at 갱신)

### 5) `/report` / `/report today`
- 목적: task 상태 집계 조회
- 입력 형식:
  - 전체: `/report`
  - 오늘(UTC): `/report today`
- 출력 요약:
  - 데이터 존재: `report`
  - 데이터 없음: `report_empty`
  - usage 오류: `error`
- read/write 여부: **read-only** (`memory/tasks/*.md` 집계, 파일 생성 없음)

### 6) `/retro today`
- 목적: 오늘 기준 회고 요약 생성
- 입력 형식: `/retro today`
- 출력 요약:
  - `retro_today_result` + `highlights`, `risks`, `recommended_next_steps`
- read/write 여부: **read-only** (`/report today` 결과 기반 계산)

## C. 개발 흐름 예시

1. `/task 개발 루프 문서 정리`
2. `/plan 개발 루프 문서화 단계 정리`
3. `/review-task task-0001-bootstrap`
4. `/approve task-0001-bootstrap approve`
5. `/report`
6. `/retro today`

## D. 현재 범위 vs 비범위

- 현재 범위:
  - 입력/상태 관리 레이어
  - 명령 파싱, task 기록, 상태 전이, 조회/집계, 회고 요약

- 비범위:
  - 실행 레이어
  - 자동화
  - DB
  - 외부 API
- 참고 contract:
  - execution 최소 계약: `docs/execution-contract.md`

