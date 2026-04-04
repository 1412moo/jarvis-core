# Approve File Writer Contract

## 목적
- 본 문서는 `approve draft`와 `file writer` 사이의 입력 계약을 정의한다.
- 입력 계약은 `draft` 단계의 상태 전이 의도를 `file writer`가 일관된 규칙으로 반영하기 위해 필요하다.
- 현재 구조(`parser -> draft -> file writer -> memory/tasks`)에서 `file writer`의 역할은 **markdown task 상태 반영 여부를 결정하고 반영 결과를 기록하는 것**으로 한정한다.

## 입력 대상
- `file writer`는 `draft` 단계가 생성한 `approve_status_transition_draft` 객체를 입력으로 받는다.

### 필수 필드
- `draft_type`: 문자열, `approve_status_transition_draft` 고정
- `task_id`: 문자열, 반영 대상 task 식별자
- `proposed_transition`: 객체
  - `from`: 문자열, 기대 현재 상태 (`NEEDS_APPROVAL`)
  - `to`: 문자열, 목표 상태 (`DOING` 또는 `FAILED`)
- `apply_ready`: 불리언, 반영 시도 가능 여부

### 선택 필드
- `hold_reason`: 문자열 또는 null
  - `apply_ready=false`일 때 hold 사유를 설명한다.
  - `apply_ready=true`일 때는 null을 사용한다.

## 처리 규칙
- `file writer`는 입력 계약 위반 여부를 먼저 확인한다.

### apply_ready=true
- 대상 `task_id`의 markdown task를 조회한다.
- 실제 현재 상태가 `proposed_transition.from`과 일치하는지 확인한다.
- 일치하면 상태를 `proposed_transition.to`로 반영한다.
- 반영 결과를 성공으로 기록한다.

### apply_ready=false
- 상태 변경을 수행하지 않는다.
- 입력의 `hold_reason`을 기반으로 hold 결과를 기록한다.

### hold 공통 원칙
- hold 상태에서는 실제 task 상태를 변경하지 않는다.
- hold는 반영 중단 기록이며, 승인 완료로 간주하지 않는다.

## 출력 또는 반영 결과
- `file writer`는 처리 결과를 반영 결과 레코드로 남긴다.

### 성공 시
- 최소 포함 항목:
  - `task_id`
  - `applied=true`
  - `applied_transition` (`from`, `to`)
  - `result_type` (예: `approve_file_write_result`)

### 실패 또는 hold 시
- 최소 포함 항목:
  - `task_id`
  - `applied=false`
  - `hold` 또는 `error` 구분
  - `reason` (hold 사유 또는 반영 실패 사유)

### 범위 명시
- 본 단계의 결과는 markdown 반영 결과까지만 다룬다.
- `memory/tasks` 반영은 별도 후속 단계이며 본 계약 범위에 포함하지 않는다.

## 유효성 검증 책임

### draft 단계에서 이미 검증되어야 하는 것
- `draft_type`이 `approve_status_transition_draft`인지 여부
- `proposed_transition` 구조 존재 여부 (`from`, `to`)
- `apply_ready` 값과 `hold_reason`의 기본 일관성

### file writer 단계에서 다시 확인할 수 있는 것
- 대상 `task_id`의 실제 markdown task 존재 여부
- 실제 현재 상태와 `proposed_transition.from` 일치 여부
- 파일 반영 가능 상태(파일 접근/쓰기 가능 여부)

### file writer가 하지 말아야 하는 판단
- 승인 정책 재해석(approve/reject 의미 재판단)
- 새로운 상태 전이 규칙 생성
- executor 트리거 또는 실행 판단
- `memory/tasks` 후속 처리 결정

## 에러/hold 기준
- 문서 수준 기준으로 아래 경우 hold 또는 반영 중단이 가능하다.
  - 입력 객체 필수 필드 누락 또는 타입 불일치
  - `draft_type` 불일치
  - `apply_ready=false`
  - 대상 task 미존재
  - 현재 상태와 `proposed_transition.from` 불일치
  - 파일 쓰기 실패 등 반영 불가 상황
- 위 경우 모두 상태 변경은 수행하지 않고 사유를 결과에 남긴다.

## 현재 비범위
- 실제 코드 구현
- executor 연결
- GitHub API
- 자동 실행
- `memory/tasks` 후속 처리
