# Execution Status Transition Policy (Minimum)

[Document Type]
- policy

## 목적
- 본 문서는 `execution_result`를 task 상태 전이와 연결할 때의 **최소 정책**을 정의한다.
- 아래 정책은 `_apply_execution_result`(`adapters/discord/bot_minimal.py`)로 구현돼 있다. 현재 적용 방식은 "현재 적용 상태" 절을 따른다.

## 적용 범위
- 대상: Owner가 승인한 실행(`/approve` 승인, `/run`, `/retry`, `/go`) 뒤 생성되는 실행 결과(`execution_result_dry_run`, `execution_result`).
- 본 정책은 **execution 이후 후보 전이**만 다룬다.
- `/approve` 자체 전이(`NEEDS_APPROVAL -> DOING/FAILED`) 규칙은 기존 contract를 그대로 따른다.

## 기본 전이 후보 정책

### 1) 성공(success)
- 조건: `executed=true` 그리고 `success=true`
- 기본 후보 전이: `DOING -> DONE`

### 2) 실패(failure)
- 조건: `executed=true` 그리고 `success=false`
- 기본 후보 전이: `DOING -> FAILED`

### 3) 미실행(not executed)
- 조건: `executed=false`
- 정책: 상태 자동 변경 없음

### 4) dry-run 결과
- 대상: `execution_result_dry_run`
- 정책: 상태 변경 없음

## 현재 적용 상태
- 위 전이는 `_apply_execution_result`가 실행 결과 메타데이터와 함께 한 번의 원자적 쓰기로 적용한다(task-0053, task-0055).
- 이 적용은 Owner가 승인한 실행(`/approve` 승인, `/run`, `/retry`, `/go`)의 결과로만 일어난다. 그런 실행 없이 스스로 일어나는 전이는 없다.
- 미실행 결과는 메타데이터만 기록하고 상태를 바꾸지 않는다.
- 허용 전이 쌍과 발생 경로는 `docs/task-model.md` 5-1, 5-2를 따른다.

## Future Scope
- 전이 적용 전 검증 조건(근거/로그/리뷰) 최소 기준 정의
- 상태 전이 적용 이력 기록 포맷 정의

## Out of Scope (이번 단계)
- 코드 변경(approve/execution/task writer)
- whitelist 확장
- 기존 상태 전이 규칙 변경
