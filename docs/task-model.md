# Task Model (Minimum)

`jarvis-core`에서 외부 명령을 내부 작업(Task)으로 기록/추적하기 위한 최소 데이터 구조를 정의한다.

## 1) Task ID 구조
- 형식: `task-####-slug`
- 규칙:
  - `####`: 4자리 순번(예: `0001`, `0002`)
  - `slug`: 작업 목적을 설명하는 짧은 소문자 하이픈 문자열
- 예시:
  - `task-0001-bootstrap`
  - `task-0002-report-system`

## 2) 상태값 정의 (기존 상태 재사용)
아래 상태값은 `reports/README.md`의 정의를 재사용한다.

- `TODO`: 시작 전 상태
- `DOING`: 진행 중 상태
- `BLOCKED`: 외부 요인으로 진행 불가
- `DONE`: 검증까지 완료
- `FAILED`: 시도했으나 목표 달성 실패
- `NEEDS_APPROVAL`: 승인 필요 상태

## 3) 필수 필드
모든 Task는 아래 필드를 반드시 포함한다.

- `id`: Task 고유 식별자 (`task-####-slug`)
- `title`: 사람이 읽는 작업 제목
- `status`: 현재 상태 (`TODO | DOING | BLOCKED | DONE | FAILED | NEEDS_APPROVAL`)
- `repo`: 작업 대상 저장소 식별자 (예: `jarvis-core`, `subrepo-abc`)
- `created_at`: 생성 시각 (UTC, `YYYY-MM-DD HH:mm UTC`)
- `updated_at`: 마지막 수정 시각 (UTC, `YYYY-MM-DD HH:mm UTC`)
- `summary`: 현재 작업 요약(목표/진행상황/핵심 메모)

## 4) 저장 방식 선택
이번 단계에서는 **Markdown(`.md`) 파일 저장 방식**을 사용한다.

선택 이유:
1. 사람이 바로 읽고 수정할 수 있다.
2. 코드/도구 없이도 Git diff로 변경 이력을 쉽게 추적할 수 있다.
3. 초기 단계에서 구조/기록 중심 원칙에 맞고 운영 부담이 작다.
4. 추후 Discord 연동 시에도 텍스트 기반 파싱으로 확장 가능하다.

## 5) 상태 변경 흐름
기본 흐름과 예외 흐름을 함께 사용한다.

- 기본: `TODO → DOING → DONE`
- 차단 해소 흐름: `TODO → BLOCKED → DOING → DONE`
- 승인 기반 흐름: `TODO → NEEDS_APPROVAL → DOING`

운영 규칙:
- `DONE`은 검증 근거가 있을 때만 사용한다.
- `BLOCKED`는 차단 사유를 `summary`에 명시한다.
- `NEEDS_APPROVAL`는 승인 요청 항목/사유를 `summary`에 남긴다.

## 6) 새 Task 생성 체크리스트
새 Task를 만들 때 아래 항목을 순서대로 확인한다.

1. `memory/tasks/task-template.md`를 복사해 새 파일(`task-####-slug.md`)을 만든다.
2. 파일명과 `id`가 동일한지 확인한다.
3. `status`가 6개 허용값 중 하나인지 확인한다.
4. `repo`, `created_at`, `updated_at`를 실제 값으로 채운다.
5. `summary`를 1~3문장으로 작성하고 범위/확인 필요사항을 반영한다.
6. 커밋 전 최소 1회 자체 검토로 누락 필드가 없는지 확인한다.

## 7) updated_at 갱신 규칙
- `status`가 바뀌면 반드시 `updated_at`를 현재 UTC 시각으로 갱신한다.
- `summary`, `title`, `repo` 등 본문 의미가 바뀌어도 `updated_at`를 갱신한다.
- 오탈자만 수정해도 이력이 중요하면 갱신하고, 단순 포맷 정리는 팀 규칙에 따라 생략할 수 있다.

## 8) DONE 전환 최소 검증 근거
`status: DONE`으로 바꾸기 전에 아래 최소 근거를 남긴다.

1. 완료 산출물(문서/커밋/PR/리포트) 식별 정보 1개 이상.
2. 사람이 재확인 가능한 검증 흔적(체크 결과, 리뷰 코멘트, 보고서 링크) 1개 이상.
3. 범위 내 미완료 항목이 없거나, 남아 있다면 후속 Task로 분리했다는 메모.

## 9) BLOCKED / NEEDS_APPROVAL 시 summary 필수 기재 정보
- `BLOCKED`: 무엇이 막았는지(원인), 누가/무엇이 해소 가능한지(의존 주체), 다음 재시도 조건을 반드시 남긴다.
- `NEEDS_APPROVAL`: 어떤 항목의 승인이 필요한지(대상), 왜 필요한지(사유), 승인되면 바로 할 다음 작업을 반드시 남긴다.
