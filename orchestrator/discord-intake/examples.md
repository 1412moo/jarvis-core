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

## 4) no-write 정상 예시 (파일 미생성)
- 입력
  - `/task report-system-improvement`
- 실행
  - `python3 orchestrator/discord-intake/run_intake_demo.py --no-write '/task report-system-improvement'`
- 결과(요약)
  - parser/draft 단계는 동일하게 수행
  - file 단계: `result_type="would_create"`
  - 최종 출력: `DRY_RUN_OUTCOME: would_create`
  - 실제 `memory/tasks/*.md` 파일은 생성되지 않음

## 5) no-write hold 예시
- 입력
  - `/task production 삭제`
- 실행
  - `python3 orchestrator/discord-intake/run_intake_demo.py --no-write '/task production 삭제'`
- 결과(요약)
  - parser: `hold_reason="needs_approval:risky_keyword_detected"`
  - 최종 출력: `DRY_RUN_OUTCOME: hold`
  - 실제 파일 생성 없음

## 6) smoke test 요약 예시
- 실행
  - `python3 orchestrator/discord-intake/run_smoke_tests.py`
- 포함 케이스
  - 생성 가능: `/task report-system-improvement` → `would_create`
  - hold: `/task production 삭제` → `hold`
  - 잘못된 입력: `/hello something` → `error`
- 성공 기준
  - exit code `0`
  - summary JSON에서 `failed=0`

## 개별 모듈 로컬 확인
```bash
python3 orchestrator/discord-intake/intake_parser.py
python3 orchestrator/discord-intake/task_draft_builder.py
python3 orchestrator/discord-intake/task_file_writer.py
```
