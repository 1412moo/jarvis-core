# Discord Command Intake Schema (MVP)

## 공통 출력 포맷
모든 입력은 아래 구조로 반환한다.

```json
{
  "command_name": "/task",
  "required_args_present": true,
  "normalized_payload": {},
  "hold_reason": null,
  "error_reason": null
}
```

- `command_name`: 인식한 명령 이름 (미인식이면 입력 토큰 또는 `null`)
- `required_args_present`: 필수 인자 충족 여부
- `normalized_payload`: 후속 `command-to-task` 연결을 위한 초안 구조
- `hold_reason`: 즉시 진행 불가/확인 필요 사유
- `error_reason`: 필수값 누락/지원하지 않는 명령 등 즉시 오류

## 명령별 최소 스키마

### 1) `/task`
- 입력: `/task <request...>`
- 필수: `request`
- 출력 payload:
  - `request: str`
  - `repo_hint: null`
  - `priority: null`
  - `due: null`
  - `status: "TODO"`
- hold 규칙(최소): 위험 키워드 포함 시 `needs_approval:risky_keyword_detected`

### 2) `/status`
- 입력: `/status <task_id|scope>`
- 필수: `task_id` 또는 `scope`
- 출력 payload:
  - `target: str`
  - `repo: null`
  - `limit: null`

### 3) `/report`
- 입력: `/report <period>`
- 필수: `period`
- MVP 허용 period: `today`, `weekly`
- 출력 payload:
  - `period: str`
  - `repo: null`
  - `format: "summary"`
- hold 규칙(최소): 미등록 period는 `unrecognized_period_requires_confirmation`

### 4) `/approve`
- 입력: `/approve <target> <decision> [reason...]`
- 필수: `target`, `decision`
- decision 허용값: `approve`, `reject`
- 출력 payload:
  - `target: str`
  - `decision: str`
  - `reason: str | null`
  - `scope: null`
- hold 규칙(최소)
  - decision 미허용값: `invalid_decision_requires_confirmation`
  - target 형식 미확인: `unrecognized_target_format`

## 비범위 재확인
- Discord 이벤트 수신/응답
- 외부 API 호출
- task 자동 생성/상태 변경
- 권한 시스템 및 실제 승인 처리
