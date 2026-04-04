# /status, /report Command Contract

[Document Type]
- contract

## 1) 목적
- Discord adapter에서 `/status`, `/report`, `/report today`가 반환하는 **데이터 구조/필드/결과 타입**을 고정한다.
- 처리 순서/단계 경계는 `docs/status-report-flow.md`에서 다룬다.

## 2) 공통 규칙
- 에러 payload: `{"result_type":"error","reason":"..."}`
- usage 오류는 `reason="usage:..."` 포맷을 사용한다.
- 본 문서의 payload는 `adapters/discord/bot_minimal.py`의 `_run_status_lookup`, `_run_report`, `_run_report_today`, `_build_report_payload` 기준이다.

## 3) `/status` contract

### 3.1 성공
```json
{
  "result_type": "status",
  "id": "task-0001-sample",
  "title": "...",
  "status": "TODO|DOING|BLOCKED|DONE|FAILED|NEEDS_APPROVAL",
  "updated_at": "YYYY-MM-DD HH:MM UTC",
  "summary": "..."
}
```

### 3.2 not_found
```json
{
  "result_type": "not_found",
  "task_id": "task-0001-sample"
}
```

### 3.3 오류/usage
- usage: `{"result_type":"error","reason":"usage:/status <task-id>"}`
- invalid task id format: `{"result_type":"error","reason":"invalid_task_id_format"}`
- task 파일 메타데이터 누락: `{"result_type":"error","reason":"task_file_missing_fields:<comma-separated-fields>"}`

## 4) `/report` contract

### 4.1 성공 (`report`)
```json
{
  "result_type": "report",
  "total": 3,
  "counts": {
    "TODO": 1,
    "DOING": 1,
    "BLOCKED": 0,
    "DONE": 1,
    "FAILED": 0,
    "NEEDS_APPROVAL": 0
  },
  "recent": [
    {
      "id": "task-0001-sample",
      "title": "...",
      "status": "DOING",
      "updated_at": "YYYY-MM-DD HH:MM UTC",
      "summary": "..."
    }
  ]
}
```

### 4.2 빈 결과 (`report_empty`)
```json
{
  "result_type": "report_empty",
  "total": 0,
  "counts": {
    "TODO": 0,
    "DOING": 0,
    "BLOCKED": 0,
    "DONE": 0,
    "FAILED": 0,
    "NEEDS_APPROVAL": 0
  },
  "recent": []
}
```

### 4.3 usage
- `/report` usage 오류: `{"result_type":"error","reason":"usage:/report"}`
- `/report today` usage 오류: `{"result_type":"error","reason":"usage:/report today"}`

## 5) 응답 정책 주의
- `not_found`는 에러 payload와 분리된 결과 타입이다.
- `recent`는 최신 `updated_at` 순으로 최대 5개다.
- `updated_at` 파싱 실패 항목은 정렬 우선순위가 낮아질 수 있다(파싱 실패 시 timestamp 0 처리).
