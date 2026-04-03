# Discord Command Intake 예시 (MVP + E2E)

아래 예시는 `run_intake_demo.py` 기준 end-to-end 동작 예시다.

## 1) 정상 생성 예시
- 입력
  - `/task report-system-improvement`
- 실행
  - `python3 orchestrator/discord-intake/run_intake_demo.py '/task report-system-improvement'`
- 결과(요약)
  - parser: `error_reason=null`, `hold_reason=null`
  - draft: `result_type="task_draft"`
  - file: `result_type="created"`, `task_id="task-####-report-system-improvement"`

## 2) hold 예시
- 입력
  - `/task production 삭제`
- 실행
  - `python3 orchestrator/discord-intake/run_intake_demo.py '/task production 삭제'`
- 결과(요약)
  - parser: `hold_reason="needs_approval:risky_keyword_detected"`
  - pipeline 중단: draft/file writer 미실행

## 3) 잘못된 입력 예시
- 입력
  - `/hello something`
- 실행
  - `python3 orchestrator/discord-intake/run_intake_demo.py '/hello something'`
- 결과(요약)
  - parser: `error_reason="unsupported_command"`
  - pipeline 중단: draft/file writer 미실행

## 개별 모듈 로컬 확인
```bash
python3 orchestrator/discord-intake/intake_parser.py
python3 orchestrator/discord-intake/task_draft_builder.py
python3 orchestrator/discord-intake/task_file_writer.py
```
