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
