# Discord Command Intake (최소 구현 뼈대)

[Document Type]
- flow

## 목적
이 디렉터리는 Discord 명령 문자열을 **수신했다고 가정**하고,
명령을 분류/검증하여 정규화된 payload 초안을 반환하는 최소 구조를 제공한다.

이번 단계는 실제 Discord bot이 아니라 **로컬 파서 + task draft 생성기 뼈대**만 다룬다.

## 처리 흐름 (현재)
1. `intake_parser.py`
   - 명령 분류
   - 필수 인자 검증
   - normalized payload / hold / error 반환
2. `task_draft_builder.py`
   - parser 결과를 받아 draft 생성 가능 여부 판단
   - `/task`만 task draft object 생성
   - hold/error 또는 `/status`/`/report`/`/approve`는 hold result 반환
3. `task_file_writer.py`
   - task draft object를 받아 `memory/tasks/*.md` 파일 1개 생성
   - 번호 스캔/slug/id 생성/충돌 회피를 로컬 규칙으로 처리

## bot_minimal.py 연결 경계
- `adapters/discord/bot_minimal.py`에서 intake 계층을 직접 소비하는 경로는 현재 `/task`만 해당한다.
  - `/task` → `parse_intake` → `build_task_draft` → `write_task_file`
- `/status`, `/report`, `/approve`는 `bot_minimal.py` 내부 전용 파서/조회/전이 로직을 사용하며 intake 계층 parser/draft/file writer를 직접 호출하지 않는다.

## 범위
- 포함
  - `/task`, `/status`, `/report`, `/approve` 분류
  - 필수 인자 존재 여부 검증
  - 정규화 payload 초안 반환
  - hold/error reason 반환
  - parser 결과 기반 task draft object 생성(오직 `/task`)
- 제외
  - Discord API 연결
  - 토큰/비밀정보
  - 네트워크 호출
  - 외부 시스템 실행
  - GitHub 작업 실행

## 파일 구성
- `intake_parser.py`: 규칙 기반 파서 최소 구현
- `task_draft_builder.py`: parser 출력 → task draft/hold 변환기
- `command_schema.md`: 명령별 입력/검증/출력 스키마
- `examples.md`: 최소 동작 예시
- `task_file_writer.py`: draft → task markdown 파일 생성기(MVP)

## 로컬 실행
```bash
python3 orchestrator/discord-intake/intake_parser.py
python3 orchestrator/discord-intake/task_draft_builder.py
python3 orchestrator/discord-intake/task_file_writer.py
```

실행 시 샘플 입력들에 대한 JSON 형태 분류/초안 결과를 출력한다.


## End-to-End 로컬 데모 실행
`run_intake_demo.py`는 parser → draft → file writer를 한 번에 실행하는 로컬 데모 런너다.

```bash
python3 orchestrator/discord-intake/run_intake_demo.py '/task report-system-improvement'
```

dry-run(파일 미생성) 모드:
```bash
python3 orchestrator/discord-intake/run_intake_demo.py --no-write '/task report-system-improvement'
```

단계별 출력:
- `PARSER RESULT`
- `DRAFT RESULT` (parser hold/error가 아니면 출력)
- `FILE RESULT` (draft가 task_draft일 때만 출력)
  - `--no-write` 사용 시 `result_type="would_create"`를 출력하며 실제 파일은 만들지 않음

중단 규칙:
- parser가 hold/error면 즉시 중단
- draft가 hold/error면 file writer 미실행
- file writer가 실패하면 reason 출력

dry-run 최종 판정(`--no-write`)은 아래 중 하나를 항상 출력한다.
- `DRY_RUN_OUTCOME: would_create`
- `DRY_RUN_OUTCOME: hold`
- `DRY_RUN_OUTCOME: error`

입력 예시:
- 성공 예시: `/task report-system-improvement`
- hold 예시: `/task production 삭제` (위험 키워드)
- 잘못된 입력 예시: `/hello something` (지원하지 않는 명령)

## Smoke Test 실행
대표 입력 3종(생성 가능/hold/잘못된 입력)을 dry-run 경로로 검증한다.

```bash
python3 orchestrator/discord-intake/run_smoke_tests.py
```

성공 기준:
- 프로세스 exit code가 `0`
- 요약 JSON의 `failed`가 `0`
- 각 케이스의 `actual_outcome`이 기대값과 일치
