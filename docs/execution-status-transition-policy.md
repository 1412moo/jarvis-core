# Execution Status Transition Policy (Minimum)

[Document Type]
- policy

## 목적
- 본 문서는 `execution_result`를 task 상태 전이와 연결할 때의 **최소 정책**을 정의한다.
- 현재 단계는 정책 문서화만 수행하며, 자동 전이 구현은 포함하지 않는다.

## 적용 범위
- 대상: `/approve` 이후 생성될 수 있는 실행 결과(`execution_result_dry_run`, `execution_result`).
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

## 자동 적용을 아직 하지 않는 이유
- 현재 실행 contract 범위는 결과 스키마 정리 중심이며, 상태 자동 전이 처리기는 미구현이다.
- 오탐/미탐을 줄이기 위한 검증·승인 단계 없이 자동 반영하면 운영 리스크가 크다.
- 따라서 본 단계에서는 "전이 후보 정책"만 문서화하고 실제 반영은 보류한다.

## Future Scope
- 후보 전이를 task writer에 안전하게 연결하는 절차 정의
- 전이 적용 전 검증 조건(근거/로그/리뷰) 최소 기준 정의
- 상태 전이 적용 이력 기록 포맷 정의

## Out of Scope (이번 단계)
- 자동 상태 전이 구현
- 코드 변경(approve/execution/task writer)
- whitelist 확장
- 기존 상태 전이 규칙 변경
