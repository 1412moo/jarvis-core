# Approve Draft Flow

## 목적
- `/approve` 파싱 결과를 즉시 상태 변경으로 연결하지 않고 `draft` 단계를 거쳐 검토 가능한 변경 초안으로 분리한다.
- `draft`는 parser 출력과 실제 반영(file writer) 사이에서 **상태 전이 의도**를 명시적으로 구조화하는 중간 계층이다.
- 현재 구조(`parser -> draft -> file writer -> memory/tasks`)에서 `draft`는 다음 역할을 가진다.
  - 파싱 결과를 표준 초안 포맷으로 정규화
  - 상태 전이 가능 여부를 1차 판단
  - 반영 전 hold 사유를 문서화 가능한 형태로 남김

## 입력
- `draft` 입력은 parser가 반환한 `approve_parse` 결과를 사용한다.

### approve_parse 형식
- `result_type`: 문자열, `approve_parse` 고정
- `task_id`: 문자열, 승인 대상 task 식별자
- `decision`: 문자열, `approve` 또는 `reject`

예시:
```json
{
  "result_type": "approve_parse",
  "task_id": "TASK-2026-0012",
  "decision": "approve"
}
```

## draft 출력 형식
- `draft`는 실제 파일 반영 전 단계의 초안 객체를 생성한다.
- 이 단계에서는 markdown 파일을 수정하지 않는다.

### 공통 필드
- `draft_type`: 문자열, `approve_status_transition_draft`
- `task_id`: 문자열
- `decision`: 문자열 (`approve` | `reject`)
- `proposed_transition`: 객체, 상태 전이 초안
- `apply_ready`: 불리언, file writer 전달 가능 여부
- `hold_reason`: 문자열 또는 null, hold 시 사유

### approve 초안
- `decision=approve`이면 `NEEDS_APPROVAL -> DOING` 전이 초안을 생성한다.

### reject 초안
- `decision=reject`이면 `NEEDS_APPROVAL -> FAILED` 전이 초안을 생성한다.

예시:
```json
{
  "draft_type": "approve_status_transition_draft",
  "task_id": "TASK-2026-0012",
  "decision": "reject",
  "proposed_transition": {
    "from": "NEEDS_APPROVAL",
    "to": "FAILED"
  },
  "apply_ready": true,
  "hold_reason": null
}
```

## 상태 전이 초안

### approve일 때
- 목표 전이: `NEEDS_APPROVAL -> DOING`
- 초안에는 다음이 포함되어야 한다.
  - 전이 전 상태(`from=NEEDS_APPROVAL`)
  - 전이 후 상태(`to=DOING`)
  - 사용자 결정(`decision=approve`)

### reject일 때
- 목표 전이: `NEEDS_APPROVAL -> FAILED`
- 초안에는 다음이 포함되어야 한다.
  - 전이 전 상태(`from=NEEDS_APPROVAL`)
  - 전이 후 상태(`to=FAILED`)
  - 사용자 결정(`decision=reject`)

## 유효성 검증 책임 분리

### parser 책임
- `/approve <task-id> approve|reject` 형식 파싱
- `task_id`, `decision` 토큰 추출
- `decision` 값이 `approve|reject`인지 확인

### draft 책임
- `result_type=approve_parse` 여부 확인
- `decision`에 따라 목표 상태 전이 초안 생성
- 구조적으로 전이 불가한 입력은 `apply_ready=false`와 `hold_reason`으로 반환

### file writer(후속 단계) 책임
- 대상 task 존재 여부 최종 확인
- 현재 상태가 `NEEDS_APPROVAL`인지 최종 확인
- 초안(`proposed_transition`)과 실제 markdown 반영 가능 여부 최종 확인

## 현재 비범위
- 실제 markdown 파일 수정
- memory/tasks 반영
- executor 연결
- GitHub API
- 자동 실행
