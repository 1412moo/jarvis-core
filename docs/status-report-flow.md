# /status, /report Flow

[Document Type]
- flow

## 1) 목적
- `/status`, `/report`, `/report today`의 처리 흐름/단계 경계를 정의한다.
- 데이터 payload 스키마는 `docs/status-report-contract.md`를 기준으로 한다.

## 2) `/status` 처리 흐름
1. 명령 토큰 수 검사: 정확히 2개(`/status <task-id>`)가 아니면 usage 오류.
2. `task_id` 공백/형식 검사.
   - 공백이면 `empty_task_id` 오류.
   - 패턴 미일치면 `invalid_task_id_format` 오류.
3. `memory/tasks/<task_id>.md` 존재 검사.
   - 없으면 `not_found` 반환.
4. task 메타데이터(`id/title/status/updated_at/summary`) 파싱.
5. 필수 필드 누락 시 `task_file_missing_fields:*` 오류.
6. 정상 시 `status` payload 반환.

## 3) `/report` 처리 흐름
1. 명령 토큰 수 검사: `/report` 단독이 아니면 usage 오류.
2. `memory/tasks` 디렉터리 검사.
   - 없으면 `report_empty` 반환.
3. `*.md`를 순회하며 task 메타데이터 파싱.
4. 필수 필드 누락/ID 형식 불일치 task는 집계에서 제외.
5. status별 counts 집계 + `updated_at` 내림차순 recent(최대 5개) 생성.
6. 파싱된 task가 0개면 `report_empty`, 그 외 `report` 반환.

## 4) `/report today` 처리 흐름
1. 명령 토큰 검사: 정확히 `/report today`가 아니면 usage 오류.
2. `memory/tasks` 디렉터리 검사.
   - 없으면 `report_empty` 반환.
3. metadata 파싱 가능 task만 대상으로 `updated_at` 날짜(UTC, `YYYY-MM-DD`)가 오늘과 같은 항목만 필터.
4. 필터 결과를 `/report`와 동일한 집계 규칙으로 반환.

## 5) 단계 경계 / 비범위
- 본 흐름은 **조회/집계**만 다루며 task 상태 변경을 수행하지 않는다.
- DB/API/UI 연동은 비범위다.
- 신규 명령 추가, status 전이 규칙 변경은 비범위다.
- `_format_reply`의 문자열 메시지는 표현 계층이며 payload contract 변경 없이 조정 가능하다.
