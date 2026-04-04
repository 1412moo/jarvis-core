# Intake Parser → Task Draft 연결 규칙 (MVP 브리지)

[Document Type]
- contract

이 문서는 Discord intake parser의 정규화 결과(`ParseResult`)를 받아,
실제 파일 생성 없이 **task draft object**를 만드는 최소 브리지 규칙을 정의한다.

## 1) 목적과 범위

- 목적
  - `orchestrator/discord-intake/intake_parser.py` 출력과 Task 초안 규칙을 연결한다.
  - 어떤 입력에서 draft를 만들고, 어떤 입력은 hold로 반환할지 기준을 고정한다.
- 포함
  - `/task` 명령의 draft 생성 규칙
  - hold/error 처리 기준
  - `repo`, `summary` 생성 최소 규칙
- 제외
  - `memory/tasks` 파일 생성
  - GitHub/Discord API 호출
  - 네트워크/DB/외부 side effect

## 2) 입력-출력 계약

### 2.1 입력
- intake parser 공통 출력 구조
  - `command_name`
  - `required_args_present`
  - `normalized_payload`
  - `hold_reason`
  - `error_reason`

### 2.2 출력
두 가지 중 하나를 반환한다.

1. task draft object
- `title`
- `status`
- `repo`
- `summary`
- `source_command` (현재 구현값: 명령 전체 원문이 아니라 command name, 즉 `/task`)

2. hold result
- `result_type = "hold"`
- `reason`
- `source_command`

## 3) 명령별 draft 생성 기준

### 3.1 `/task`
- 조건
  - `required_args_present == true`
  - `hold_reason is None`
  - `error_reason is None`
- 결과
  - task draft object 생성

### 3.2 `/status`, `/report`, `/approve`
- 이번 단계에서는 draft 생성 대상이 아니다.
- 결과는 hold 반환:
  - `reason = "non_task_command_not_supported_for_draft"`

## 4) hold/error 상태 처리 기준

### 4.1 error 상태
- `error_reason`가 있으면 draft를 만들지 않는다.
- hold result 반환:
  - `reason = "error_input:<error_reason>"`

### 4.2 hold 상태
- `hold_reason`가 있으면 draft를 만들지 않는다.
- hold result 반환:
  - `reason = "hold_input:<hold_reason>"`

### 4.3 보류 draft 생성 여부
- 이번 단계에서는 **보류 draft를 생성하지 않는다**.
- 즉, hold/error는 모두 `hold result`로만 반환한다.

## 5) repo 결정 기준 (재정리)

- 기본값: `jarvis-core`
- `normalized_payload.repo_hint`가 있고 비어 있지 않으면 우선 사용
- 단, 이번 단계는 parser 기본 출력이 `repo_hint=None`이므로 대부분 `jarvis-core`

## 6) summary 생성 규칙 (재정리)

`/task`의 `normalized_payload.request`를 이용해 1~2문장 요약을 만든다.

필수 포함 요소:
1. 요청 목표(요청 원문 기반)
2. 이번 단계 범위 제한(초안 생성까지만)

예시 형태:
- `요청 사항(<request>)을 작업 초안으로 정리한다. 이번 단계는 draft object 생성 규칙 정의까지만 포함한다.`

## 7) 상태/제목 규칙

- `status`: 항상 `TODO`
- `title`: 요청 문자열을 짧게 정리
  - 최소 구현은 요청 원문 사용
  - 필요 시 공백 정리만 적용

## 8) 구현 메모

- 함수형(순수 함수) 우선
- 파일 저장 금지
- 네트워크 호출 금지
- Discord 연결 금지
