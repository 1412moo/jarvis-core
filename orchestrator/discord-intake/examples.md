# Discord Command Intake 예시 (MVP)

아래 예시는 `intake_parser.py` 기준 최소 동작 예시다.

## 1) `/task 보고 시스템 개선`
- 분류: `/task`
- required args: `true`
- normalized payload(요약):
  - `request="보고 시스템 개선"`
  - `status="TODO"`
- hold/error: 없음

## 2) `/status task-0002`
- 분류: `/status`
- required args: `true`
- normalized payload(요약):
  - `target="task-0002"`
- hold/error: 없음

## 3) `/report today`
- 분류: `/report`
- required args: `true`
- normalized payload(요약):
  - `period="today"`
  - `format="summary"`
- hold/error: 없음

## 4) `/approve task-0007 approve`
- 분류: `/approve`
- required args: `true`
- normalized payload(요약):
  - `target="task-0007"`
  - `decision="approve"`
- hold/error: 없음

## 5) 잘못된 입력: `/approve task-0007 maybe`
- 분류: `/approve`
- required args: `true` (필수 인자 자체는 존재)
- normalized payload(요약):
  - `target="task-0007"`
  - `decision="maybe"`
- hold/error:
  - `hold_reason="invalid_decision_requires_confirmation"`

## 로컬 확인 커맨드
```bash
python3 orchestrator/discord-intake/intake_parser.py
```
