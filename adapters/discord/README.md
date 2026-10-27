# Discord Minimal Bot Adapter (`/task`, `/plan`, `/review-task`, `/approve`, `/status`, `/report`, `/retro today`, `/help`)

## 현재 구현 범위
이 단계의 구현은 **`/task <request>`, `/plan <request>`, `/review-task <task-id>`, `/approve <task-id> approve|reject`, `/status <task-id>`, `/report`, `/report today`, `/retro today`, `/help`**를 처리한다.

- 처리 방식: Discord 일반 메시지 기반 (`/task ...` 텍스트)
- intake 재사용: `parser -> draft -> file writer`
- 성공 시 실제 `memory/tasks/*.md` 파일 생성 (`/task`만)
- hold/error 시 생성 중단 + 이유 응답
- read-only 명령: `/help`, `/plan`, `/review-task`, `/status`, `/report`, `/report today`, `/retro today`
- 상태 변경/실행 명령: `/task`, `/approve`
- `/run`, `/retry`는 폐기됐다(task-0179). 어떤 task에도 아무것도 실행하거나 바꾸지 않고 `/approve`·`/go`·Jarvis Console을 쓰라는 안내만 돌려준다. 두 명령은 키워드로 고른 task(수동 SOP task 포함)에 허용 목록의 smoke 테스트를 실행하고 DONE/FAILED를 Owner 검토 없이 기록할 수 있었다.
- `/retro today`는 `updated_at`의 **UTC 날짜 기준 오늘** task만 집계해 회고 요약을 만든다.
- `CLOSED`(Owner가 Jarvis Console Close로 완료 조건 없이 종료한 수동 task, task-0180)는 `/report`·`/report today`·`/retro today` 상태 줄의 마지막에 집계되고 `/retro today`의 follow-up 대상이 아니다. Discord에는 종료 명령이 없고, `/go`·`/go <id> accept`·`/go <id> recover`는 `CLOSED` task를 받지 않는다(`status_not_startable:CLOSED`, `accept_requires_failed:CLOSED`, `recover_requires_doing:CLOSED`).
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

### 4) 상시 실행 (Windows, task-0194)
Claude 세션이나 터미널과 무관하게 봇을 띄워 두려면 `scripts/discord_bot_service.ps1`을 쓴다(Windows PowerShell 5.1).
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/discord_bot_service.ps1 -Register   # 로그인 때 자동 실행 작업 등록
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/discord_bot_service.ps1 -Start      # 지금 시작
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/discord_bot_service.ps1 -Status     # 등록·프로세스·로그 위치
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/discord_bot_service.ps1 -Stop       # 감시자와 봇 종료
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/discord_bot_service.ps1 -Unregister # 등록 해제
```
- `-Register`는 현재 사용자의 로그인 때 `-Run`(감시 루프)을 실행하는 작업 스케줄러 작업 `JarvisDiscordBot`을 현재 사용자·제한 권한으로 만든다. 설계상 관리자 권한 없이 등록되고 `-WindowStyle Hidden`으로 창을 숨기지만, 로그인 때 콘솔 창이 잠깐 보일 수 있다. 두 가지는 실제 등록 때 확인한다.
- 감시 루프는 로그온 세션마다 하나만 돈다(같은 사용자가 세션을 둘 쓰면 감시자도 둘일 수 있다). 다른 `bot_minimal.py` 봇 프로세스(`--self-check` 계열 제외)가 이미 있으면 새 봇을 띄우지 않고 기다린다. 봇이 끝나면 10초부터 두 배씩 최대 300초 기다렸다가 다시 띄우고, 10분 넘게 돈 뒤 끝났으면 대기를 처음으로 되돌린다.
- 로그는 저장소 밖 `%LOCALAPPDATA%\jarvis-core\logs`에 남는다. 감시자 줄은 `discord-bot.log`(5MB를 넘으면 `.1`로 한 번 돌림)에 바로 쌓이고, 실행 중인 봇의 출력은 `discord-bot.out.log`·`discord-bot.err.log`에 쌓였다가 봇이 끝나거나 다음에 띄우기 전에 `discord-bot.log`로 옮겨진다. 실행 중의 두 파일은 돌리지 않는다. 스크립트는 토큰을 읽거나 쓰지 않고, 봇이 `.env`에서 직접 읽는다.
- heartbeat(task-0196): 감시자는 봇을 기다리는 동안 10분마다 `discord-bot.log`에 heartbeat 줄을 남기고, 같은 폴더의 `supervisor-JarvisDiscordBot.json`에 pid·시작·마지막 heartbeat·봇 pid·실행 횟수·정상 종료 여부를 적는다. 정상으로 끝나면 "supervisor ended"와 종료 표시를 남기고, 강제로 끝나면 남기지 못한다. `-Stop`으로 끝낸 감시자는 `-Stop`이 대신 종료를 기록한다("supervisor stopped by -Stop"). 봇 실행·종료·재시작 대기 중에도 감시자가 살아 있다는 표시를 갱신하므로, 봇이 금방 끝나 재시작을 되풀이해도 heartbeat가 끊기지 않는다. 한계: 강제로 끝난 감시자가 언제 끝났는지는 마지막 heartbeat 뒤 한 간격(기본 10분) 안이라는 것만 알 수 있고, 상태 파일의 pid를 다른 프로세스가 다시 쓰면 "기록 없이 끝남" 경고를 놓칠 수 있다. 그래서 경고가 없다는 것이 감시자가 살아 있다는 증거는 아니며, 감시자 pid 줄도 함께 본다. `-Status`는 마지막 heartbeat 시각을 보이고, 봇만 있고 감시자가 없을 때, 감시자가 기록 없이 끝났을 때, 살아 있고 종료 기록이 없는 감시자의 heartbeat가 간격의 두 배 넘게 없을 때 `WARNING` 줄을 띄운다. 감시자 찾기는 같은 인스턴스 이름의 감시자로 한정한다.
- `-SelfTest`는 아무것도 띄우지 않고 저장소·봇 파일·python·로그 폴더를 확인한다. `-SmokeTest`는 임시 폴더에서 대역 봇으로 감시 루프(실행, 두 번째 감시자 거절, 이미 떠 있는 봇이 있으면 띄우지 않음, 봇이 끝나면 10초 뒤 다시 띄움, 강제로 끝난 감시자의 mutex 넘겨받기, heartbeat와 정상 종료 기록, 금방 끝나는 봇의 재시작 대기 중 heartbeat, 감시자를 강제로 끝낸 뒤의 `-Status` 경고, `-Stop`의 종료 기록, 재시작 대기 계산, 로그 돌림)를 확인한다. 둘 다 Discord에 접속하지 않고 작업도 등록하지 않는다.
- `jarvis.bat`이 봇을 띄우는지는 확인하지 않았다. 감시 루프는 먼저 떠 있는 봇을 보면 두 번째를 띄우지 않지만, 감시 루프의 봇이 떠 있는 동안 다른 경로(손으로 실행, `jarvis.bat` 등)로 봇을 또 띄우는 것은 막지 못한다. 그때는 `-Status`로 봇 프로세스가 둘인지 확인한다.

---

## 동작 규칙
### `/task <내용>`
1. 슬래시 형태 문자열이 아니면 무시
2. 지원 명령(`/help`, `/plan`, `/task`, `/status`, `/review-task`, `/retro today`, `/report`, `/report today`, `/approve`, 폐기 안내용 `/run`·`/retry`)이 아니면 거절 응답
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

### `/run`, `/retry` (폐기, task-0179)
1. 인자와 상관없이 `command_retired`를 돌려준다. task 파일을 읽거나 바꾸지 않고 아무것도 실행하지 않는다.
2. 응답은 승인된 task 실행은 `/approve <task-id> approve`, Worker 작업은 `/go <task-id>`, 상태 변경은 Jarvis Console을 쓰라고 안내한다.
3. 두 명령은 Owner 전용 명령 목록에 남아 있어 권한 검사는 그대로다.

### `/work <요청>` 과 `/go <task-id>` (Jarvis v0.2, task-0142)
Owner 전용. 작업 종류는 `studyroom_content`(Studyroom 앱 전체 `apps/studyroom/`, task-0185부터. 앱 실행 스크립트 `apps/studyroom/studyroom.bat`은 보호 경로), `daily_ai_radar`(`apps/daily-ai-radar/`), `research_council`(`apps/research-council/`, task-0189부터. 외부 LLM 호출 파일 `research_council/openrouter_advisor.py`, LIVE 모드 스위치가 있는 `research_council/llm_advisor.py`, `.env.example`은 보호 경로)다. Worker 지시는 네트워크·외부 API·새 의존성 추가를 금지한다. 이것은 지시이고, 코드 검사로 막는 것은 보호 경로와 허용 경로 밖 변경, 그리고 research_council에서 네트워크 모듈·openrouter·LIVE 모드·환경 변수 읽기 같은 금지 문구를 담은 새 줄(`forbidden_addition`)이다. 금지 문구는 정해진 목록이라 완전한 네트워크 격리가 아니며, 목록 밖은 Worker 지시와 Reviewer 검토가 맡는다.
1. `/work <요청>`: 요청에 작업 종류 표지어가 있으면 기존 `/task` 경로로 TODO task를 만들고 계획(수정 허용 경로, 테스트, 승인 명령)을 답한다. 아무것도 실행하지 않는다.
   - 표지어가 없으면 팀장(Lead, task-0183)이 맡는다. 봇은 "팀장 검토 시작"을 답하고, 읽기 전용 Claude 팀장이 커밋된 파일만 있는 임시 worktree(`jarvis.bat`·`.env` 없음)에서 저장소를 살펴 계획(작업 종류, 단계, 위험도, Owner 결정 필요 여부, Worker 지시)을 세워 `/work` 메시지에 연 스레드에 올린다(스레드를 열 수 없으면 같은 채널). 계획에는 수정 허용 경로도 보인다. 등록된 작업 종류면 그 종류의 TODO task(제목은 표지어 + 팀장 제목, summary는 Owner의 `/work` 원문)를 만들어 `/go <task-id>`를 안내한다. 종류가 없거나, 팀장 답이 형식에 맞지 않거나, 다른 팀장이 실행 중이거나(`lead_busy`), 제목이 다른 종류를 고르게 되거나(`lead_task_kind_conflict`), 원문이 너무 길면(`lead_request_too_long`) 아무 task도 만들지 않고 이유를 보고한다(실패 시에는 사유 코드만 보내고 모델 응답이나 오류 출력은 보내지 않는다). `/go` 때 작업 종류는 제목에서 정하고, Worker와 Reviewer는 Owner의 `/work` 원문만 받는다(팀장 제안 지시는 Owner 참고용).
   - 읽기 전용 확인·보고(task-0201): 요청에 수정하지 마, 수정하지 말, 수정 금지, 고치지 마, 고치지 말, 변경하지 마, 변경하지 말, 변경 금지, 보고만, 확인만, 읽기 전용, read-only, read only, readonly 중 하나가 있으면(대소문자 무시, 연속 공백은 하나로 봄) 작업 종류 표지어와 관계없이 팀장을 거치지 않고 읽기 전용 TODO task를 만들고 "작업 준비됨 (읽기 전용)"으로 답한다. `/go` 뒤 Worker는 커밋된 파일만 있는 임시 worktree에서 Read·Grep·Glob만으로 한 번 답한다. 파일이 바뀌면 `report_changed_files`, 답이 비면 `report_empty`로 실패하고, 바뀐 파일이 없으면 성공이다. Reviewer·QA·main 반영은 없고, 답은 "검증 안 된 Worker 답"으로 채널에 보낸다(멘션 무력화). 전문은 성공할 때마다 저장소 밖 `%LOCALAPPDATA%\jarvis-core\reports\<task-id>.md`(앞선 시도의 worktree나 브랜치가 남아 있으면 `<task-id>-r<N>.md`, 다시 실행하면 같은 이름을 덮어씀. `JARVIS_REPORT_DIR`로 변경)에 두고, 답이 한 메시지(2000자)를 넘으면 앞부분만 보내며 그 경로를 적는다. 파일을 쓰지 못했으면 그 사실을 보고에 적는다. task는 `DONE`이 되고 task 기록만 checkpoint commit한다(push 없음). 읽기 전용 task에는 `resume`을 받지 않으며 다시 실행은 `/go <task-id>`다. 문구를 빠뜨리면 기존처럼 수정 작업으로 돈다.
   - 자연어 호출(task-0184): 슬래시 없이 `자비스, <요청>`(또는 `jarvis: <요청>`, 쉼표·콜론, 전각 포함)이나 봇 멘션 뒤 요청을 보내면 `/work <요청>`과 똑같이 처리한다. Owner 전용 권한 검사와 이후 경로(팀장, 원문 보존, 작업 스레드)가 같다. 호출어가 메시지 맨 앞에 없으면 기존 자연어 해석(`/status`·`/report`)으로 가고, 일반 대화는 팀장을 부르지 않는다.
   - 작업 스레드: 봇은 `/work` 메시지에 스레드를 열어 팀장 계획을 올린다. 그 스레드에서 `/go`를 보내면(또는 `/go`가 연 새 스레드에) Worker 진행, Reviewer 판정과 지적 요지, Worker 수정 결과(변경 파일·테스트 요약), 재검토 판정이 모인다. 최종 결과는 스레드가 아니라 채널로 간다(task-0191, 아래 4항). 지적 요지와 수정 결과는 파이프라인 결과 값만 쓰고 프롬프트 전문은 보내지 않으며, 본문의 `@` 멘션은 무력화한다. 스레드를 열 수 없거나 스레드 전송이 실패하면 진행 줄과 팀장 계획 모두 원래 채널로 보내고(채널 전송까지 실패한 진행 줄은 버림), 알림 실패는 작업 판정을 바꾸지 않는다.
2. `/go <task-id>`: Owner 승인. `TODO -> DOING`(FAILED면 `FAILED -> TODO -> DOING` 재시도)과 감사 기록 후 즉시 "시작" 응답. 동시에 한 작업만 실행한다. `/work`로 만든 task(`source_command`가 `/task`)만 시작하고, 수동 task는 잠금이나 기록 변경 없이 `go_requires_worker_path`로 거부한다(task-0182).
3. 백그라운드에서 `orchestrator/worker/claude_worker.py`가 실행된다: 저장소 밖 worktree(`C:\work\jarvis-core-worktrees\<task-id>`, `JARVIS_WORKTREE_ROOT`로 변경 가능) → Claude Code Worker(`claude -p`, Bash 없음, 파일 편집만. task-0195부터 `--tools`로 Read·Edit·Write·Glob·Grep만 보이고 `--strict-mcp-config`로 MCP 서버를 싣지 않음) → 허용 경로 검사 → Studyroom smoke → candidate commit → Reviewer(`claude -p --agent reviewer`, git 읽기 명령만 허용. 보이는 도구는 Read·Grep·Glob·Bash뿐이고 MCP 서버 없음) → 결정론적 QA → main이 baseline 그대로일 때만 ff-only 반영 → task `DONE` 기록 → checkpoint commit.
4. 끝나면 결과를 채널에 보고한다(task-0191). 보고에는 이번 실행의 Worker·Reviewer 호출이 스스로 알린 사용량 한 줄("사용량(API 환산 추정): Worker n회 $x, Reviewer m회 $y, 합계 t초")이 붙는다(task-0199, 구독 사용이면 실제 청구액이 아님). 같은 값이 호출마다 저장소 밖 `%LOCALAPPDATA%\jarvis-core\logs\agent-usage.jsonl`(환경 변수 `JARVIS_USAGE_LOG`로 변경)에 한 줄씩 쌓인다. 프롬프트와 답 내용은 남기지 않는다. `/go`를 스레드 안에서 보냈으면 그 스레드의 상위 채널이고, 상위 채널을 알 수 없거나 채널 전송이 실패하면 작업 스레드로 보낸다. 실패·timeout·범위 위반이면 task를 `FAILED`로 기록하고 단계, 사유, 선택지(`/go` 재시도, `/status`, 보존된 worktree·브랜치)를 보고한다.
5. push, 외부 API, credential, `jarvis.bat` 접근은 하지 않는다. 검증: `python -B orchestrator/worker/run_smoke_tests.py`(가짜 claude 사용).

### `/help`
1. 지원 명령 목록을 고정 텍스트로 안내한다.
2. usage 불일치는 `error(reason=usage:/help)` 반환

### Discord 일반 메시지 선필터의 현재 거절 안내 문구
- 코드의 일반 메시지 선필터 응답은 현재 아래 목록을 안내한다.
- ``이 봇은 현재 `/help`, `/plan <request>`, `/task <내용>`, `/status <task-id>`, `/review-task <task-id>`, `/report`, `/report today`, `/retro today`, `/approve <task-id> approve|reject`, `/work <요청>`, `/go <task-id>`만 지원합니다.``
- 참고: `_run_command()` 라우팅은 `/run`·`/retry`를 폐기 안내(`command_retired`)로 보낸다(task-0179).

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
- ON_HOLD: 0
- DONE: 3
- FAILED: 0
- NEEDS_APPROVAL: 0
- CLOSED: 0

최근 업데이트:
1. task-0003-discord-report — DONE — 2026-04-03 01:10 UTC
2. task-0002-discord-status — DONE — 2026-04-03 00:55 UTC
3. task-0001-bootstrap — DONE — 2026-04-03 00:40 UTC
```

### report today success
```text
📊 task report
- total: 2
- TODO: 0
- DOING: 0
- BLOCKED: 0
- ON_HOLD: 0
- DONE: 2
- FAILED: 0
- NEEDS_APPROVAL: 0
- CLOSED: 0

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
- ON_HOLD: 0
- DONE: 0
- FAILED: 0
- NEEDS_APPROVAL: 0
- CLOSED: 0

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
python3 adapters/discord/bot_minimal.py --self-check '/run task-0001-bootstrap'   # 폐기 안내만 돌려준다
python3 adapters/discord/bot_minimal.py --self-check '/retro today'
python3 adapters/discord/bot_minimal.py --self-check '/help'
```
- `--self-check`는 명령 하나의 응답을 그대로 보여준다. 오류 응답도 정상 결과라 종료 코드는 0이고, 빈 입력(`''`)과 공백만 있는 입력은 `empty_input`으로 거절되어 2다.

### 4) 회귀 자체 검사 묶음 (`--self-check-suite`)
```bash
python3 adapters/discord/bot_minimal.py --self-check-suite
```
- Discord 접속 없이 임시 저장소에서 승인·상태·실행 결과 등 핵심 동작 검사를 모두 돌리고 결과를 JSON 하나로 출력한다.
- 종료 코드: 모든 검사가 통과하면 0, 하나라도 실패하면 1이다. 검사 도중 처리되지 않은 예외로 멈춰도 0이 아니다.
- 결과 JSON의 `ok`가 전체 판정이고 `total`이 검사 수다. 실패하면 `failed`에 실패한 검사(`name`, `detail`)가 담긴다.

---

## 아직 구현하지 않은 것
- Discord **공식 slash command 등록/동기화**
- 명령 권한/채널 제한
- 재시도/백오프/운영 모니터링
