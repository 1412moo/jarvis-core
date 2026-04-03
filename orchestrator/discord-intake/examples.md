# Discord Command Intake 예시 (MVP)

아래 예시는 `intake_parser.py` + `task_draft_builder.py` 기준 최소 동작 예시다.

## 1) `/task 보고 시스템 개선`
- 입력
  - `/task 보고 시스템 개선`
- parser 결과(요약)
  - `command_name="/task"`
  - `required_args_present=true`
  - `normalized_payload.request="보고 시스템 개선"`
  - `hold_reason=null`, `error_reason=null`
- draft 결과(요약)
  - `result_type="task_draft"`
  - `title="보고 시스템 개선"`
  - `status="TODO"`
  - `repo="jarvis-core"`
  - `source_command="/task"`

## 2) `/task production 삭제`
- 입력
  - `/task production 삭제`
- parser 결과(요약)
  - `command_name="/task"`
  - `required_args_present=true`
  - `hold_reason="needs_approval:risky_keyword_detected"`
- draft 결과(요약)
  - `result_type="hold"`
  - `reason="hold_input:needs_approval:risky_keyword_detected"`
  - 이번 단계에서는 보류 draft를 만들지 않음

## 3) `/status task-0002`
- 입력
  - `/status task-0002`
- parser 결과(요약)
  - `command_name="/status"`
  - `required_args_present=true`
  - `hold_reason=null`, `error_reason=null`
- draft 결과(요약)
  - `result_type="hold"`
  - `reason="non_task_command_not_supported_for_draft"`
  - `/status`, `/report`, `/approve`는 아직 draft 생성 대상 아님

## 로컬 확인 커맨드
```bash
python3 orchestrator/discord-intake/intake_parser.py
python3 orchestrator/discord-intake/task_draft_builder.py
```

## 4) task draft → task file 생성
- 입력(draft 예시)
  - `title="parser-output-validation-rules"`
  - `status="TODO"`
  - `repo="jarvis-core"`
  - `summary="파서 결과 검증 규칙 보강"`
- writer 결과(요약)
  - `result_type="created"`
  - `file_path="memory/tasks/task-0004-parser-output-validation-rules.md"` (번호는 실행 시점에 따라 달라짐)
  - `task_id="task-0004-parser-output-validation-rules"`

## 로컬 확인 커맨드 (확장)
```bash
python3 orchestrator/discord-intake/intake_parser.py
python3 orchestrator/discord-intake/task_draft_builder.py
python3 orchestrator/discord-intake/task_file_writer.py
```
