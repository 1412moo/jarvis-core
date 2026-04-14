# Execution Contract (Minimum)

[Document Type]
- contract

## 목적
- 본 문서는 `/approve` 단계에서 생성되는 `execution_candidate`를 다음 실행 레이어에서 소비하기 위한 최소 계약을 정의한다.
- 이번 단계는 **문서화(contract 정의)만** 수행하며, 실제 실행(subprocess 등)은 다루지 않는다.

## 현재 단계 범위
- `approve_file_write_result`에 포함되는 `execution_candidate` 구조를 기준으로 다음 레이어 입력 계약을 정리한다.
- 실행 요청(`execution_request`)과 실행 결과(`execution_result`)의 최소 필드만 정의한다.

## 비범위
- subprocess 실행 구현
- 실행 큐/스케줄러/워커 도입
- DB/API/UI 연동
- 상태 전이 규칙 변경

## approve와 execution 연결 지점
- 연결 위치: `approve_file_write_result.execution_candidate`
- 연결 조건: `/approve`가 성공 적용(`applied=true`)된 뒤, task 메타데이터 기반으로 `execution_candidate`가 생성될 수 있다.
- 현재 구현상 후보 미생성 시 `execution_candidate`는 `null`일 수 있다.

---

## 1) execution_candidate

### 정의
- `/approve` 성공 반영 직후, 다음 실행 레이어에 전달 가능한 **실행 후보 정보**.

### 최소 필드
- `result_type`: 문자열, `execution_candidate` 고정
- `task_id`: 문자열, 대상 task 식별자
- `execution_type`: 문자열, 실행 분류(현재 코드 기준: `script` 또는 `test`)
- `action`: 문자열, 다음 레이어가 참조할 실행 의도(예: `plan_script_execution`, `plan_test_execution`)
- `reason`: 문자열, 후보 생성 근거

### 현재 코드 정합 메모
- 현재 구현은 키워드 기반으로 후보를 생성하며, 조건 불충족 시 `null`을 반환한다.

---

## 2) execution_request

### 정의
- `execution_candidate`를 실제 실행 레이어 입력으로 승격한 요청 객체.

### 최소 필드
- `result_type`: 문자열, `execution_request`
- `task_id`: 문자열
- `execution_type`: 문자열
- `action`: 문자열
- `requested_at`: 문자열(UTC 시각, `YYYY-MM-DD HH:mm UTC` 권장)
- `source`: 문자열(요청 생성 경로 식별자, 예: `approve_file_write_result`)

### 메모
- `execution_request`는 본 단계에서 **스키마만 정의**한다. 생성/저장/전송 로직은 미구현이다.

---

## 3) execution_result

### 정의
- 실행 레이어가 실행 시도 후 반환하는 최소 결과 객체.

### 최소 필드
- `result_type`: 문자열, `execution_result`
- `task_id`: 문자열
- `execution_type`: 문자열
- `action`: 문자열
- `executed`: 불리언, 실행 시도 여부
- `success`: 불리언, 실행 성공 여부
- `output_summary`: 문자열, 실행 출력 요약
- `error_reason`: 문자열, 실패 또는 미실행 사유(없으면 빈 문자열)

### 메모
- `execution_result`도 본 단계에서 **스키마만 정의**한다. 런타임 생성/적재 경로는 아직 없다.

---

## 미구현 명시
- `execution_candidate -> execution_request` 변환 로직
- 실제 실행 수행기(executor) 및 subprocess 처리
- 실행 이력 저장/조회 포맷
- 실패 재시도/백오프/타임아웃 정책
