# Discord Minimal Bot Adapter (`/task`, `/plan`, `/review-task`, `/approve`, `/run`, `/retry`, `/status`, `/report`, `/retro today`, `/help`)

## 현재 구현 범위
이 단계의 구현은 **`/task <request>`, `/plan <request>`, `/review-task <task-id>`, `/approve <task-id> approve|reject`, `/run <task-id>`, `/retry <task-id>`, `/status <task-id>`, `/report`, `/report today`, `/retro today`, `/help`**를 처리한다.

- 처리 방식: Discord 일반 메시지 기반 (`/task ...` 텍스트)
- intake 재사용: `parser -> draft -> file writer`
- 성공 시 실제 `memory/tasks/*.md` 파일 생성 (`/task`만)
- hold/error 시 생성 중단 + 이유 응답
- read-only 명령: `/help`, `/plan`, `/review-task`, `/status`, `/report`, `/report today`, `/retro today`
- 상태 변경/실행 명령: `/task`, `/approve`, `/run`, `/retry`
- `/run`은 `DOING` 상태 task만 허용하며, 실행은 화이트리스트 조합에서만 시도된다.
- `/retry`는 `FAILED/DOING` 상태 task 재실행용이며, 실행 후보가 없으면 중단된다.
- `/retro today`는 `updated_at`의 **UTC 날짜 기준 오늘** task만 집계해 회고 요약을 만든다.
- `/report`는 새로운 report 파일을 생성하지 않는다.

명시적 비범위:
- GitHub API 연동
- 자동 보고 생성
- DB
- 웹 UI

---

## 필요한 환경변수
`.env.example` 기준:

- `DISCORD_BOT_TOKEN` (필수)

토큰은 절대 코드/커밋에 넣지 않는다.

---

## 설치 및 실행 방법
### 1) 의존성 설치
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r adapters/discord/requirements.txt
```

### 2) 환경변수 설정
```bash
cp adapters/discord/.env.example adapters/discord/.env
# adapters/discord/.env 에 DISCORD_BOT_TOKEN 값 입력
```

### 3) 실행
```bash
python3 adapters/discord/bot_minimal.py
```

기본적으로 `adapters/discord/.env`를 자동 로드한다.

---

## 동작 규칙
### `/task <내용>`
1. 슬래시 형태 문자열이 아니면 무시
2. 지원 명령(`/help`, `/plan`, `/task`, `/status`, `/retry`, `/review-task`, `/retro today`, `/report`, `/report today`, `/approve`, `/run`)이 아니면 거절 응답
3. `/task <내용>`을 intake 파이프라인에 전달
4. parser hold면 파일 생성 없이 hold 응답
5. error면 error 응답
6. success면 생성된 `task_id`, `file`명 응답

### `/status <task-id>`
1. 입력 형식 검증: `/status` + task-id 1개만 허용
2. task-id 규칙 검증: `task-####-slug` 형식
3. `memory/tasks/<task-id>.md` 파일 존재 확인
4. 파일이 있으면 아래 메타데이터만 읽어서 응답:
   - id
   - title
   - status
   - updated_at
   - summary
5. 파일이 없으면 `not found` 응답
6. 형식 오류/필수 필드 누락 시 `error` 응답

### `/report`
1. 입력 형식 검증: `/report` 또는 `/report today`만 허용
2. `/report`: `memory/tasks/*.md`를 읽어 상태별 개수 전체 집계
3. `/report today`: `updated_at`의 UTC 날짜가 오늘인 task만 집계
4. 최근 업데이트 task 최대 5건 조회
5. 조회 가능한 task가 없으면 `empty` 응답
6. 이 명령은 read-only이며 report 파일을 생성하지 않음

### `/approve <task-id> approve|reject`
1. 입력 형식 검증: `/approve` + task-id + decision(approve/reject)
2. draft/writer 입력 구성 후 상태 전이 적용 시도
3. 성공 시 `approve_file_write_result(applied=true)` 반환
4. 대상 미존재/상태 불일치 등은 `approve_file_write_result(applied=false, kind, reason)` 반환
5. usage 불일치는 `error(reason=usage:/approve <task-id> approve|reject)` 반환

### `/run <task-id>`
1. 입력 형식 검증: `/run` + task-id 1개만 허용
2. 대상 task status가 `DOING`일 때만 실행 시도
3. 실행 후보(`execution_candidate`)가 없으면 `run_execution_candidate_missing` 반환
4. 실행은 화이트리스트 조합(`action=plan_script_execution`, `target=discord_intake_smoke_tests`)만 허용
5. 결과는 `run_result`와 실행 결과/전이 적용 여부를 포함

### `/retry <task-id>`
1. 입력 형식 검증: `/retry` + task-id 1개만 허용
2. 대상 task status가 `FAILED` 또는 `DOING`일 때만 재실행 시도
3. `FAILED`인 경우 내부적으로 `FAILED -> TODO -> DOING` 준비 전이를 거친 뒤 실행 시도
4. 실행 후보(`execution_candidate`)가 없으면 `retry_execution_candidate_missing` 반환
5. 결과는 `retry_result`와 실행 결과/전이 적용 여부를 포함

### `/help`
1. 지원 명령 목록을 고정 텍스트로 안내한다.
2. usage 불일치는 `error(reason=usage:/help)` 반환

### Discord 일반 메시지 선필터의 현재 거절 안내 문구
- 코드의 일반 메시지 선필터 응답은 현재 아래 목록을 안내한다.
- ``이 봇은 현재 `/help`, `/plan <request>`, `/task <내용>`, `/status <task-id>`, `/retry <task-id>`, `/review-task <task-id>`, `/report`, `/report today`, `/retro today`, `/approve <task-id> approve|reject`만 지원합니다.``
- 참고: `_run_command()` 라우팅에는 `/run <task-id>`도 포함되어 있으며, self-check에서는 해당 명령을 검증한다.

### 안전 규칙
- 빈 입력(`/task`만 입력)은 usage error(`usage:/task <request>`)
- 위험 키워드(예: `delete`, `production`, `삭제`)는 hold 처리
- hold/error는 `memory/tasks` 파일을 생성하지 않음

---

## 응답 예시
### task success
```text
✅ task 생성 완료
- task_id: `task-0004-doc-update`
- file: `task-0004-doc-update.md`
```

### task hold
```text
⏸️ hold
- reason: `needs_approval:risky_keyword_detected`
```

### task error
```text
❌ error: `usage:/task <request>`
```

### status success
```text
📄 task 정보
- id: `task-0001-bootstrap`
- title: `jarvis-core 초기 구조 부트스트랩`
- status: `DONE`
- updated_at: `2026-04-03 00:40 UTC`
- summary: `문서/디렉터리 기준을 정리하고 초기 운영 구조를 확정했다.`
```

### status not_found
```text
⚠️ not found: `task-9999-nope`
```

### status error
```text
❌ error: `invalid_task_id_format`
```

### report success
```text
📊 task report
- total: 3
- TODO: 0
- DOING: 0
- BLOCKED: 0
- DONE: 3
- FAILED: 0
- NEEDS_APPROVAL: 0

최근 업데이트:
1. task-0003-discord-report — DONE — 2026-04-03 01:10 UTC
2. task-0002-discord-status — DONE — 2026-04-03 00:55 UTC
3. task-0001-bootstrap — DONE — 2026-04-03 00:40 UTC
```

### report today success
```text
📊 task report (today, UTC)
- total: 2
- TODO: 0
- DOING: 0
- BLOCKED: 0
- DONE: 2
- FAILED: 0
- NEEDS_APPROVAL: 0

최근 업데이트:
1. task-0003-discord-report — DONE — 2026-04-03 01:10 UTC
2. task-0002-discord-status — DONE — 2026-04-03 00:55 UTC
```

### report empty
```text
📊 task report
- total: 0
- TODO: 0
- DOING: 0
- BLOCKED: 0
- DONE: 0
- FAILED: 0
- NEEDS_APPROVAL: 0

최근 업데이트:
(없음)
```

### report error
```text
❌ error: `usage:/report`
```

---

## 최소 로컬 검증 (Discord 접속 전)
### 1) 문법 검증
```bash
python3 -m py_compile adapters/discord/bot_minimal.py
```

### 2) 환경변수 누락 에러 확인
```bash
python3 adapters/discord/bot_minimal.py
# 기대: {"result_type":"error","reason":"missing_env:DISCORD_BOT_TOKEN"}
```

### 3) Discord 없이 파이프라인 자체 확인 (`--self-check`)
```bash
python3 adapters/discord/bot_minimal.py --self-check '/task 문서 구조 정리'
python3 adapters/discord/bot_minimal.py --self-check '/plan Discord 명령 문서 동기화'
python3 adapters/discord/bot_minimal.py --self-check '/review-task task-0001-bootstrap'
python3 adapters/discord/bot_minimal.py --self-check '/task production 삭제'
python3 adapters/discord/bot_minimal.py --self-check '/task'
python3 adapters/discord/bot_minimal.py --self-check '/status task-0001-bootstrap'
python3 adapters/discord/bot_minimal.py --self-check '/status task-9999-not-found'
python3 adapters/discord/bot_minimal.py --self-check '/status invalid-id'
python3 adapters/discord/bot_minimal.py --self-check '/report'
python3 adapters/discord/bot_minimal.py --self-check '/report today'
python3 adapters/discord/bot_minimal.py --self-check '/report extra'
python3 adapters/discord/bot_minimal.py --self-check '/report today extra'
python3 adapters/discord/bot_minimal.py --self-check '/approve task-0001-bootstrap approve'
python3 adapters/discord/bot_minimal.py --self-check '/approve task-9999-self-check approve'
python3 adapters/discord/bot_minimal.py --self-check '/approve task-0001 approve'
python3 adapters/discord/bot_minimal.py --self-check '/run task-0001-bootstrap'
python3 adapters/discord/bot_minimal.py --self-check '/retry task-0001-bootstrap'
python3 adapters/discord/bot_minimal.py --self-check '/retro today'
python3 adapters/discord/bot_minimal.py --self-check '/help'
```

---

## 아직 구현하지 않은 것
- Discord **공식 slash command 등록/동기화**
- 명령 권한/채널 제한
- 재시도/백오프/운영 모니터링
