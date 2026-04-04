# Approve File Writer Contract

[Document Type]
- contract

## 목적
- 본 문서는 `approve draft`와 `file writer` 사이의 데이터 계약을 정의한다.
- `approve_writer_input`/`approve_writer_result`의 단일 기준 문서(source of truth)로 사용한다.

## approve_writer_input

### 필수 필드
- `draft_type`: 문자열, `approve_status_transition_draft` 고정
- `task_id`: 문자열, 반영 대상 task 식별자
- `proposed_transition`: 객체
  - `from`: 문자열, 기대 현재 상태(`NEEDS_APPROVAL`)
  - `to`: 문자열, 목표 상태(`DOING` 또는 `FAILED`)
- `apply_ready`: 불리언, 반영 시도 가능 여부

### 선택 필드
- `hold_reason`: 문자열 또는 null

## approve_writer_result

### 공통 필드
- `result_type`: 문자열, `approve_file_write_result`
- `task_id`: 문자열
- `applied`: 불리언

### applied=true
- `applied_transition`: 객체
  - `from`: 문자열
  - `to`: 문자열

### applied=false
- `reason`: 문자열
- `kind`: 문자열, `hold` 또는 `error`

## 처리 조건
- `apply_ready=true`이고 대상 task 상태가 `proposed_transition.from`과 일치하면 `proposed_transition.to`로 반영한다.
- 아래 조건에서는 상태를 변경하지 않고 `applied=false`로 반환한다.
  - 입력 필드 누락/타입 불일치
  - `draft_type` 불일치
  - `apply_ready=false`
  - 대상 task 미존재
  - 현재 상태와 `proposed_transition.from` 불일치
  - 파일 쓰기 실패

## 범위
- 본 계약은 markdown task 상태 반영 입력/출력 형식까지만 다룬다.
