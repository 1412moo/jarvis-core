# task-0165-worker-progress-report-and-escalation

- id: `task-0165-worker-progress-report-and-escalation`
- title: `Worker 파이프라인 R1: Discord 단계별 진행 보고·Owner 에스컬레이션·봇 시작 시 멈춘 DOING 점검`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-18 10:24 UTC`
- updated_at: `2026-10-18 10:35 UTC`
- summary: `기존 run_pipeline·accept_candidate와 Discord /go 경로를 그대로 쓰면서, 실제로 일어난 단계(Worker·Reviewer·repair·QA·통합)마다 같은 채널에 한 줄씩 보고하고, 실패와 Owner 판단 필요를 구분해 설정된 Owner를 멘션하며, 봇 시작 시 실행 기록 없는 DOING을 읽기 전용으로 한 번 보고한다. 보고가 실패해도 파이프라인 결과와 상태는 바뀌지 않는다. 연속 실행·자동 재시도·DOING→FAILED·Radar 자동화·Scheduler·Console 제어·push는 하지 않는다.`
- source_command: `Owner 요청: task-0165 R1 진행 보고·에스컬레이션 구현`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `8349dd2f9982557b8bc3a4be511ca64cd14022d7` (main HEAD = origin/main, fetch 뒤 확인) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 환경 | Windows ACP 949, Python 3.12.10 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (기본값) |

## 조사 결과 (read-only, 등록 전 확인)

1. `/go`는 `_run_go`가 잠금(task-0164의 프로세스 안 잠금과 파일 잠금)을 잡고 `TODO→DOING`을 적용한 뒤 `work_started`를 돌려준다.
   `on_message`는 그 답장(▶️ 승인됨…)을 먼저 보내고, `asyncio.to_thread(_run_worker_job, …)`로 파이프라인을 돌린 뒤 결과를
   `message.channel.send(_format_reply(job))`로 한 번 보낸다(`bot_minimal.py` `on_message`). 그 사이에는 아무 보고가 없다.
2. `run_pipeline`(`claude_worker.py`)은 `result.stage`를 preflight → worktree → (resume) → worker → scope → tests → candidate →
   reviewer → (repair → scope … reviewer) → qa → integrate → checkpoint → done 순서로 바꾼다. Reviewer 무효 재검토(retry)는 같은
   reviewer 단계 안에서 일어난다. `accept_candidate`는 accept(QA 재실행) → approval → integrate → checkpoint 순서다.
3. 최종 실패 답장(`_format_work_reply`)은 단계·사유·상세·다음 선택지를 이미 보여 주고, repair 예산 소진,
   `reviewer_findings_not_repairable`, `qa_unverified_owner_review`에는 "Owner 결정/확인이 필요합니다" 줄을 더한다. 멘션은 없다.
   `qa_unverified_owner_review` 줄은 Discord 2000자 안에 들어가도록 나머지 줄 길이를 보고 줄인다(task-0150).
4. Owner ID는 `_load_owner_ids()`가 환경변수 `JARVIS_OWNER_DISCORD_USER_IDS`(쉼표 구분)에서 읽고, 비어 있으면 봇이 시작하지 않는다
   (fail-closed). 값은 출력하지 않는다.
5. 보고 채널을 정하는 설정은 없다. `/go` 결과는 그 명령이 온 채널로 간다. 봇 시작 시점에는 이 채널이 없다.
6. 멈춘 DOING 판정(task-0164): `_worker_running()`이 거짓이고 `_read_execution_review_metadata(task_file).get("executed") is None`.
   현재 저장소의 DOING은 task-0031(수동 SOP task, `source_command: Discord work-order (task-0031)`, 2026-08-26 이후 갱신 없음) 하나다.
   `/work`로 만든 Worker task는 `source_command: /task`다. 같은 판정을 그대로 쓰면 task-0031이 봇을 켤 때마다 보고된다.
7. `on_ready`는 discord.py에서 재연결 때도 다시 불릴 수 있다.
8. Worker smoke(`orchestrator/worker/run_smoke_tests.py`)는 가짜 claude로 `run_pipeline`과 `bot._run_worker_job`을 직접 부른다.

## 구현 계획

| # | 내용 |
| --- | --- |
| I1 | `claude_worker.run_pipeline`·`accept_candidate`에 선택 키워드 인자 `progress: Callable[[str], None] \| None = None`을 더한다. 실제로 그 단계에 들어갈 때만 한 번 부른다: `worker`(또는 `resume`), `reviewer`(candidate마다, repair 뒤 재검토 포함, 무효 재검토 retry는 따로 부르지 않음), `repair`(실제로 repair할 때만), `qa`, `integrate`. accept는 `qa`, `integrate`. 콜백 예외는 잡아서 무시하고(보고 실패) 파이프라인의 결과·기록·상태를 바꾸지 않는다. 기존 인자·반환값·다른 함수 서명은 그대로 |
| I2 | `bot_minimal._run_worker_job`에 선택 인자 `progress`를 더해 그대로 넘긴다. 단계 이름을 짧은 한국어 한 줄로 바꾸는 `_progress_line(task_id, stage, repairs)`를 둔다(멘션 없음) |
| I3 | `on_message`의 Worker 경로: 이벤트 루프와 채널을 잡은 콜백을 만들어 Worker 스레드에서 `asyncio.run_coroutine_threadsafe(channel.send(line), loop).result(timeout)`로 보낸다. 순서가 보장되고, 실패·시간 초과는 콘솔에 사유만 남기고 계속한다 |
| I4 | 최종 답장: 실패면 첫 줄 앞에 Owner 멘션(`<@id>`, 설정된 ID 전부)을 붙이고, Owner 판단 필요(`qa_unverified_owner_review`, `reviewer_findings_not_repairable`, repair 예산 소진 `reviewer_findings`, accept 경로의 `accept_*` 중 재시도 가능)와 일반 실패를 첫 줄에서 구분한다(🟡 Owner 판단 필요 / ❌ 실패). 성공에는 멘션하지 않는다. 길이 계산(task-0150)에 멘션을 포함한다 |
| I5 | 봇 시작 점검: `on_ready`에서 프로세스당 한 번만(모듈 플래그) 멈춘 DOING을 읽기 전용으로 찾아 보고한다. 상태·파일·잠금을 바꾸지 않고 재실행·복구하지 않는다. 대상 범위와 보고 위치는 아래 D1·D2 결정에 따른다 |
| I6 | self-check: 단계 문구, 멘션 구분, 시작 점검의 읽기 전용(파일 해시 불변)과 1회성, 보고 실패 시 결과 불변 |
| I7 | Worker smoke: 가짜 claude로 정상 경로의 보고 순서(`worker, reviewer, qa, integrate`), repair 경로(`worker, reviewer, repair, reviewer, qa, integrate`), Worker·Reviewer·QA 실패에서 멈춘 지점까지의 보고와 최종 결과, 콜백이 예외를 던져도 DONE/FAILED와 기록이 같음, accept 경로(`qa, integrate`), task-0164 잠금 검사 유지 |
| I8 | SOP §10.1 진입 행에 진행 보고·멘션·시작 점검 한 문장(validator 대조 대상 값은 바꾸지 않음) |

## 변경 예정 파일

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`, `adapters/discord/bot_minimal.py`, `orchestrator/worker/run_smoke_tests.py`, `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1 진입 행 한 문장), 이 기록 |
| deny | `jarvis.bat`, `.env`, `apps/`, `docs/master-plan.md`(Complete 뒤 별도 승인), `docs/task-model.md`, `scripts/validate_multi_agent_sop.py`(대조 값이 바뀌지 않으면 손대지 않음), 다른 task 기록 |

## Owner 결정이 필요한 항목 (Start 전)

| # | 질문 | 선택지 | Manager 권고 |
| --- | --- | --- | --- |
| D1 | 시작 점검이 보고할 DOING 범위 | (a) 실행 기록 없는 DOING 전부 (task-0031도 매번 보고) / (b) `/work`로 만든 Worker task(`source_command: /task`)만, 나머지는 보고하지 않음 / (c) (b) 목록 + "그 밖의 DOING N건은 Worker 경로가 아니라 제외" 한 줄 | (c). 재분류 없이 출처 필드로 나누기만 하고, 제외된 수를 숨기지 않는다 |
| D2 | 봇 시작 점검을 보낼 곳 (시작 시점에는 명령 채널이 없음) | (a) 설정된 Owner에게 DM / (b) 새 환경변수 채널 ID / (c) 콘솔에만 출력하고 다음 `/go`·`/status` 답장에 한 번 덧붙임 | (a). 새 설정이 필요 없고 Owner ID를 재사용한다. DM 전송이 실패하면 콘솔에 사유만 남긴다 |

중복 보고 처리: 같은 프로세스에서 `on_ready`가 여러 번 불려도 모듈 플래그로 한 번만 보낸다. 봇을 다시 켜면 다시 보고한다(재시작 뒤 확인이 목적이라 의도된 동작).

## Manager 요약

아래 행은 Owner 요청(원문 블록 "Owner 요청")과 D1·D2 결정(원문 블록 "Owner 결정 D1·D2와 Start 승인")의 조건 문장을 빠짐없이 인용한다.

| # | 승인 조건 (원문 인용) | Manager 해석과 충족 방법 |
| --- | --- | --- |
| G1 | "`task-0164`까지 완료된 현재 코드를 기준으로, Jarvis Worker 파이프라인이 실행되는 동안 Discord에 진행 상황을 보고하도록 구현한다." / "현재 Worker → Reviewer → 제한된 repair → QA → 통합 → DONE 파이프라인은 이미 구현되어 있다. 새 오케스트레이터를 만들지 말고 기존 흐름에 최소한의 변경으로 보고 기능을 추가한다." | baseline `8349dd2`(task-0164 push 뒤). `run_pipeline`·`accept_candidate`에 선택 인자 `progress` 하나와 단계 진입 지점의 호출만 더했다. 새 오케스트레이터·dispatcher 없음 |
| C1 | "1. `docs/master-plan.md`, SOP, 최근 완료 task 기록을 먼저 확인한다." / "2. 실제 저장소 상태와 `main` 및 `origin/main`의 동기화 여부를 확인한다." | 등록 전에 master-plan §6 잠긴 기능, SOP §9·§10, task-0164 기록을 읽었고, fetch 뒤 `main`=`origin/main`=`8349dd2`를 확인했다(기준선) |
| C2 | "3. task-0164에서 추가한 Worker 레지스트리와 프로세스 간 잠금 기능을 재사용한다." | 작업 종류는 `_go_work_kind`·`WORK_KINDS` 그대로, 시작 점검의 "실행 중" 판정은 `_worker_running()`(프로세스 안 잠금과 파일 잠금), 멈춘 DOING 판정은 task-0164의 `executed` 없음 조건을 그대로 쓴다 |
| C3 | "4. 기존 코드와 테스트를 확인하고, 구현 계획과 변경 파일 목록을 먼저 제시한다." / "5. 기존 SOP 및 승인 절차에 따라 task 등록과 시작 승인을 받는다. 승인 절차를 임의로 생략하지 않는다." | 조사 결과·구현 계획·변경 예정 파일을 이 기록에 적어 TODO로 등록하고 Start Preview만 연 뒤 보고했다. Owner의 D1·D2 결정과 Start 승인 뒤 Console Start Confirm(10:35 UTC)으로 `TODO→DOING` |
| A1 | "기존 `run_pipeline` 및 Discord `/go` 실행 경로를 재사용한다." / "가능한 경우 기존 실행 단계의 전환 지점에서 콜백을 통해 진행 상황을 보고한다." | `result.stage`가 바뀌는 지점에서 `_report_progress(progress, 단계)`를 부른다. `/go` → `_run_worker_job` → `run_pipeline` 경로는 그대로이고 콜백만 넘긴다 |
| A2 | "필요한 보고 단계: * 작업 시작 * Worker 실행 * Reviewer 검토 * repair 진행(실제로 repair가 발생한 경우) * QA 실행 * 통합 및 완료 처리 * 최종 성공 또는 실패" | 작업 시작은 기존 `/go` 답장(▶️ 승인됨…), 그다음 `worker`(또는 `resume`)·`reviewer`·`repair`(실제 repair 때만)·repair 뒤 `reviewer`·`qa`·`integrate` 한 줄씩, 최종은 기존 결과 답장(✅ 또는 실패 답장) |
| A3 | "각 단계에서 메시지를 반복해서 보내지 말고, 단계별로 한 번씩 간결하게 보고한다. 실제로 발생하지 않은 단계를 보고하지 않는다." | 단계 진입 시 한 번만 부른다. Reviewer 무효 검토의 재시도는 같은 검토로 보고 다시 보내지 않는다. 실패한 지점 뒤 단계는 부르지 않는다(Worker smoke로 경로별 확인) |
| A4 | "보고 기능에 오류가 생겨도 본래 Worker 파이프라인이 불필요하게 실패하지 않도록 한다. 단, 실행 결과와 상태를 왜곡하거나 실제 실패를 숨겨서는 안 된다." | `_report_progress`와 봇의 `_make_progress`가 각각 예외를 잡는다(콘솔에는 예외 종류만). 항상 예외를 던지는 콜백으로 성공 run은 DONE·기록·main 반영이 같고, 실패 run은 `scope_violation`·FAILED 기록이 같음을 확인했다. 최종 결과 답장은 바꾸지 않았다 |
| B1 | "실패하거나 Owner의 판단이 필요한 경우, 현재 작업 ID와 상황, 필요한 조치를 Discord에 명확히 보고한다." | 기존 실패 답장(작업 ID, 단계, 사유, 상세, 다음 선택지)을 그대로 두고 첫 줄만 바꾼다 |
| B2 | "* 실패 또는 Owner 판단 필요 상황에서는 설정된 Owner를 직접 멘션한다." / "* 일반적인 진행 단계에서는 Owner를 멘션하지 않는다." | 실패 답장 첫 줄 앞에 `<@OwnerID>`. 진행 줄·성공 답장·시작 답장에는 멘션 없음. Owner 판단 필요(`qa_unverified_owner_review`, `reviewer_findings_not_repairable`, repair 예산 소진, record를 유지한 accept 거절)는 "🟡 Owner 판단 필요", 그 밖은 "❌ 실패" |
| B3 | "* Owner ID는 기존 설정 및 권한 체계를 확인해 재사용한다." / "* ID를 추측하거나 토큰·비밀정보를 로그나 메시지에 노출하지 않는다." | 명령 권한 검사와 같은 `_load_owner_ids()`(`JARVIS_OWNER_DISCORD_USER_IDS`)를 쓴다. ID는 멘션 안에만 들어가고 콘솔 로그에는 ID·토큰을 쓰지 않는다. 검증은 가짜 ID로만 했다 |
| C4 | "task-0164에서 구현한 stale DOING 감지 기능을 재사용한다." / "봇 시작 시 실행 기록이 없는 DOING 작업을 확인하고, 발견하면 Owner에게 보고한다." / "이 점검은 읽기 전용이어야 한다." | `on_ready`에서 `_startup_check_once`가 `_stalled_doing_scan`(읽기만)을 돌리고, Worker 경로의 멈춘 DOING이 있으면 Owner에게 DM한다. 파일 쓰기 없음(바이트 비교로 확인) |
| C5 | "* task 상태를 변경하지 않는다." / "* 자동으로 재실행하거나 복구하지 않는다." / "* 기존 task를 임의로 재분류하지 않는다." / "* 중복 보고가 발생할 가능성과 처리 방식을 검토하고 결과를 설명한다." | 상태·파일·잠금을 바꾸지 않고 재실행·복구하지 않는다. 출처 필드(`source_command`)로 목록과 건수를 나누기만 하고 어떤 필드도 쓰지 않는다. 중복: `on_ready` 재호출은 모듈 플래그로 프로세스당 한 번, 봇 재시작 때는 다시 보고(의도). 다른 프로세스가 Worker를 실행 중이면 아무것도 멈춤으로 보지 않는다 |
| D1 | "D1 (c): Worker 경로의 실행 기록 없는 DOING 작업을 보고하고, 그 밖의 DOING 작업은 별도 건수로 표시하세요. 기존 task의 상태나 분류는 변경하지 마세요." | Worker 경로 = `source_command`가 `/task`(`/work`가 만든 task). 그 목록(최대 10건, 넘치면 "외 N건")과 "그 밖의 DOING N건은 … 제외" 한 줄. 상태·분류 불변 |
| D2 | "D2 (a): 봇 시작 시 Owner에게 Discord DM으로 보고하세요. DM 전송에 실패하면 콘솔에 사유만 남기세요." | 설정된 Owner마다 `client.fetch_user(id).send(text)`. 실패하면 콘솔에 예외 종류만(`[startup-check] DM to an Owner failed (…)`). Worker 경로의 멈춘 DOING이 없으면 DM을 보내지 않고 콘솔에 건수만 남긴다 |
| X1 | "이번 작업은 R1만 구현한다." / "* 여러 task의 연속 실행 및 큐 * 자동 재시도 또는 자동 복구 * `DOING → FAILED` 신규 상태 전이 * Radar 자동 실행 또는 Radar 결과의 task 자동 생성 * Scheduler 및 백그라운드 자동 실행 * 자동 push * Console 제어 기능 추가" / "자동 복구, 연속 실행, Scheduler 등 R1 범위를 넘어서는 기능은 추가하지 마세요." | 이 중 어느 것도 만들지 않았다. 새 상태 전이·큐·타이머·Console 변경 없음. 봇 시작 점검은 `on_ready` 1회 읽기이며 주기 실행이 아니다 |
| V1 | "기존 테스트를 수정할 때는 실제 동작을 검증하도록 한다. 단순히 테스트 기대값을 변경해 통과시키지 않는다." | 기존 검사 중 기대값이 바뀐 것은 `owner review reply: … failure reply unchanged` 3건뿐이고, 정확한 문자열 비교를 그대로 두고 앞에 붙는 멘션만 기대값에 더했다(실제 동작 변경). 나머지는 새 검사 |
| V2 | "최소 검증 항목: 1. 정상 실행 시 시작부터 완료까지 단계별 보고 순서가 정확하다. 2. repair가 발생하면 해당 보고가 나타나고, 발생하지 않으면 나타나지 않는다. 3. Worker·Reviewer·QA 실패 시 실패 보고와 Owner 멘션이 정확하다. 4. Owner 판단이 필요한 상황은 일반 실패와 구분해 보고한다. 5. Discord 보고 자체가 실패해도 본래 작업 실행 결과를 왜곡하지 않는다. 6. 봇 시작 시 stale DOING을 감지해 보고하지만 task 상태는 바꾸지 않는다. 7. 두 번째 Worker 실행 차단 등 task-0164의 기존 잠금 및 중복 실행 방지 기능이 유지된다. 8. 기존 Worker smoke, Discord self-check, SOP validator, Console 관련 테스트를 영향 범위에 맞게 실행한다. 9. `git diff --check`와 변경 파일 범위를 확인한다." | 아래 "Implementer 검증" 표의 V2-1~V2-9가 항목별 결과다 |
| V3 | "테스트에서 가능한 한 기존 fake Worker/Claude 방식을 사용한다. 실제 외부 서비스나 실작업을 불필요하게 실행하지 않는다." | Worker smoke의 가짜 claude, self-check의 가짜 DM·임시 디렉터리만 썼다. 실제 봇·Discord·claude 실행 없음 |
| S1 | "* `jarvis.bat`은 절대로 열거나 읽거나 수정하거나 스테이징·커밋하지 않는다." / "`jarvis.bat`은 절대 열거나 읽거나 수정하지 마세요." | 손대지 않았다. Worker smoke의 `jarvis.bat` 검사도 그대로 통과 |
| S2 | "* task 상태를 임의로 DONE으로 변경하지 않는다." / "* SOP나 master-plan의 잠긴 정책을 임의로 해제하지 않는다." / "* 테스트 실패를 숨기거나 범위를 무단으로 넓히지 않는다." / "* 기존 작업물과 사용자 변경사항을 덮어쓰지 않는다." | DONE은 Console Complete 승인 뒤에만. master-plan §6·SOP §9 잠금은 그대로이고 SOP §10.1 진입 행에 이번 동작 한 문장만 더했다. 변경 파일은 아래 File ownership 안 |
| S3 | "* push하지 않는다. push는 별도 Owner 승인을 기다린다." / "* 변경 사항은 기존 SOP의 task 시작, 검토, QA, Console Complete, DONE checkpoint 승인 절차를 따른다." / "* task 등록·상태 변경·커밋은 현재 SOP가 요구하는 승인 및 체크포인트 절차에 따른다." / "구현 후 Reviewer와 QA까지 기존 SOP에 따라 진행하고 결과를 보고한 뒤 멈추세요. Console Complete, DONE checkpoint, master-plan 수정, push는 각각 별도 승인을 기다리세요." | candidate → Reviewer → (repair 1회까지) → QA → QA 기록 checkpoint 뒤 보고하고 멈춘다. Complete·DONE checkpoint·master-plan·push 하지 않음 |
| R1 | "6. 완료 보고 다음 항목을 보고하고 멈춘다. 1. 변경 파일 및 핵심 변경 사항 2. Discord 진행 보고 예시 3. Owner 멘션 및 에스컬레이션 동작 4. stale DOING 시작 점검 결과 5. 실행한 테스트와 각각의 실제 결과 6. Reviewer 및 QA 결과와 미해결 문제 7. 현재 task 상태와 승인 대기 항목 8. 커밋 및 push 여부 9. 다음 단계 R2를 진행하기 전에 필요한 결정" / "R1 구현과 검증 결과를 보고한 뒤 멈추고, 다음 작업이나 push는 별도 승인을 기다린다." / "위 조건으로 task-0165의 Start Confirm을 진행하고 구현을 시작하세요." / "기존에 제시한 구현 범위와 검증 계획을 유지하고" | 구현 계획 I1~I8과 변경 예정 파일을 그대로 지켰다. 최종 보고는 이 아홉 항목 순서로 하고 멈춘다 |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`, `adapters/discord/bot_minimal.py`, `orchestrator/worker/run_smoke_tests.py`, `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1 진입 행 한 문장), 이 기록 |
| deny | `jarvis.bat`, `.env`, `apps/`, `docs/master-plan.md`, `docs/task-model.md`, `scripts/validate_multi_agent_sop.py`, 다른 task 기록, 그 밖의 모든 파일 |

## 구현

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `PROGRESS_STAGES`, `_report_progress(progress, stage)`(예외를 잡아 무시). `run_pipeline`·`_run_pipeline`·`accept_candidate`·`_accept_candidate`에 선택 키워드 인자 `progress`. 호출 지점: Worker 실행 전(`worker`) 또는 resume 복사 전(`resume`), candidate마다 Reviewer 호출 전(`reviewer`, 무효 검토 재시도 제외), repair Worker 전(`repair`), QA 전(`qa`), 통합 전(`integrate`). accept는 QA 재실행 전(`qa`)과 승인 뒤 통합 전(`integrate`). 기존 인자·반환값·실패 처리·기록은 그대로 |
| `adapters/discord/bot_minimal.py` | `_run_worker_job(progress=)`을 파이프라인에 그대로 넘김. `_progress_line`·`_make_progress`(단계 한 줄, repair 횟수, 보내기 실패는 콘솔에 예외 종류만). `on_message`의 Worker 경로가 `run_coroutine_threadsafe(...).result(15초)`로 같은 채널에 순서대로 보냄. `_owner_mention`·`_needs_owner_decision`과 실패 답장 첫 줄(멘션 + 🟡/❌). `_task_source_command`·`_stalled_doing_scan`·`_format_startup_report`·`_startup_check_once`와 `on_ready`의 DM. self-check 4건 |
| `orchestrator/worker/run_smoke_tests.py` | `run_case(progress=)`, `progress_flow`(정상·repair·무효 검토 재시도·Worker 실패·Reviewer 실패·QA Owner 확인·QA 실패·예외를 던지는 콜백의 성공·실패), bot 경로의 진행 줄과 멘션, 시작 점검(다른 프로세스 실행 중, 멈춘 `/work` task, 파일 불변), accept 경로의 단계(QA 전 거절·QA 실패·성공), 기존 실패 답장 비교 3건에 멘션 기대값 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §10.1 진입 명령 행에 진행 보고·멘션·시작 점검 한 문장 |

## 구현 착수

2026-10-18 10:35 UTC에 Console Project Control 화면에서 Start(Preview → Confirm Start)로 `TODO→DOING`을 적용했다(파일의 status·updated_at만 바뀜).

## Implementer 검증 (작업 트리 기준, candidate 전)

`.env` 없는 임시 worktree(`8349dd2` + 변경 파일 복사)에서 실행했다. Owner ID는 가짜 값만 썼다.

| # | 결과 |
| --- | --- |
| V2-1 | Worker smoke: 정상 run의 보고가 `worker, reviewer, qa, integrate` 순서. bot 경로에서도 🔧·🔍·🧪·📦 네 줄이 한 번씩, 멘션 없음 |
| V2-2 | repair run은 `worker, reviewer, repair, reviewer, qa, integrate`, repair 없는 run에는 `repair`가 없음. 무효 검토 재시도는 Reviewer 한 번으로 보고 |
| V2-3 | Worker 실패는 `worker`까지, Reviewer 실패(`reviewer_blocked`)는 `reviewer`까지, QA 실패(`qa_failed`)는 `qa`까지 보고하고 `integrate`는 없음. bot 경로의 실패 답장 첫 줄이 `<@가짜ID> ❌ 실패: …` |
| V2-4 | `qa_unverified_owner_review`·`reviewer_findings_not_repairable`·repair 예산 소진은 `🟡 Owner 판단 필요`, 일반 실패는 `❌ 실패`(self-check와 Worker smoke). 성공·시작 답장에는 멘션 없음. Owner ID가 없으면 멘션도 없음 |
| V2-5 | 항상 예외를 던지는 콜백: 성공 run은 DONE·성공 기록·main 2커밋 전진, 실패 run은 `scope:scope_violation` 기록·main 불변으로 콜백 없을 때와 같음. self-check: 보내기 실패가 예외를 내지 않음 |
| V2-6 | self-check: Worker 경로 DOING(기록 없음) 1건만 목록, 수동 DOING과 기록 있는 DOING은 "그 밖의 DOING 2건", TODO 제외, DM 1회, 두 번째 호출은 건너뜀, DM 실패는 `RuntimeError`만 남김, Worker 실행 중이면 보고 없음, 파일 바이트 불변. Worker smoke: `/work`로 만든 멈춘 task만 목록에 오르고 파일 불변, 다른 프로세스가 잠금을 잡은 동안은 보고 없음 |
| V2-7 | task-0164 잠금·멈춘 DOING 검사(Worker smoke 4건, self-check 2건) 그대로 통과 |
| V2-8 | Worker smoke 402/0(368 + 새 34), self-check 102/0(설정 없음·`PYTHONUTF8=1`), SOP validator PASS(음성 검사 133), discord-intake 140/0(실제 task 기록마다 검사하므로 이 기록 1건이 늘었음), Console smoke PASS |
| V2-9 | `git diff --check`와 변경 범위는 candidate 커밋 뒤 QA에서 확인 |
| 변형 | M1 Reviewer 단계 보고 제거 → Worker smoke 7 실패. M2 보고 예외를 삼키지 않음 → Worker smoke 2·self-check 1. M3 멘션 제거 → Worker smoke 5·self-check 1. M4 Owner 판단 구분 제거 → Worker smoke 1·self-check 1. M5 시작 점검이 모든 DOING을 목록에 올림 → Worker smoke 1·self-check 1. M6 프로세스당 1회 제거 → self-check 1. M7 실행 중 Worker 무시 → Worker smoke 1·self-check 1. 실행 뒤 임시 worktree 삭제, 메인 checkout 전후 같음 |

검증에서 실제 봇·Discord·claude를 실행하지 않았다.

## Owner 결정 D1·D2와 Start 승인 (원문)

```text
D1은 (c), D2는 (a)로 결정합니다.

* D1 (c): Worker 경로의 실행 기록 없는 DOING 작업을 보고하고, 그 밖의 DOING 작업은 별도 건수로 표시하세요. 기존 task의 상태나 분류는 변경하지 마세요.
* D2 (a): 봇 시작 시 Owner에게 Discord DM으로 보고하세요. DM 전송에 실패하면 콘솔에 사유만 남기세요.

위 조건으로 task-0165의 Start Confirm을 진행하고 구현을 시작하세요.
기존에 제시한 구현 범위와 검증 계획을 유지하고, `jarvis.bat`은 절대 열거나 읽거나 수정하지 마세요. 자동 복구, 연속 실행, Scheduler 등 R1 범위를 넘어서는 기능은 추가하지 마세요.
구현 후 Reviewer와 QA까지 기존 SOP에 따라 진행하고 결과를 보고한 뒤 멈추세요. Console Complete, DONE checkpoint, master-plan 수정, push는 각각 별도 승인을 기다리세요.
```

## Owner 요청 (원문)

```text
Jarvis task-0165 — R1 진행 보고·에스컬레이션 구현
목표
`task-0164`까지 완료된 현재 코드를 기준으로, Jarvis Worker 파이프라인이 실행되는 동안 Discord에 진행 상황을 보고하도록 구현한다.
현재 Worker → Reviewer → 제한된 repair → QA → 통합 → DONE 파이프라인은 이미 구현되어 있다. 새 오케스트레이터를 만들지 말고 기존 흐름에 최소한의 변경으로 보고 기능을 추가한다.
1. 작업 시작 전 확인

1. `docs/master-plan.md`, SOP, 최근 완료 task 기록을 먼저 확인한다.
2. 실제 저장소 상태와 `main` 및 `origin/main`의 동기화 여부를 확인한다.
3. task-0164에서 추가한 Worker 레지스트리와 프로세스 간 잠금 기능을 재사용한다.
4. 기존 코드와 테스트를 확인하고, 구현 계획과 변경 파일 목록을 먼저 제시한다.
5. 기존 SOP 및 승인 절차에 따라 task 등록과 시작 승인을 받는다. 승인 절차를 임의로 생략하지 않는다.

2. 구현 범위
A. Discord 진행 보고
기존 `run_pipeline` 및 Discord `/go` 실행 경로를 재사용한다.
가능한 경우 기존 실행 단계의 전환 지점에서 콜백을 통해 진행 상황을 보고한다.
필요한 보고 단계:

* 작업 시작
* Worker 실행
* Reviewer 검토
* repair 진행(실제로 repair가 발생한 경우)
* QA 실행
* 통합 및 완료 처리
* 최종 성공 또는 실패

각 단계에서 메시지를 반복해서 보내지 말고, 단계별로 한 번씩 간결하게 보고한다. 실제로 발생하지 않은 단계를 보고하지 않는다.
보고 기능에 오류가 생겨도 본래 Worker 파이프라인이 불필요하게 실패하지 않도록 한다. 단, 실행 결과와 상태를 왜곡하거나 실제 실패를 숨겨서는 안 된다.
B. Owner 에스컬레이션
실패하거나 Owner의 판단이 필요한 경우, 현재 작업 ID와 상황, 필요한 조치를 Discord에 명확히 보고한다.

* 실패 또는 Owner 판단 필요 상황에서는 설정된 Owner를 직접 멘션한다.
* Owner ID는 기존 설정 및 권한 체계를 확인해 재사용한다.
* ID를 추측하거나 토큰·비밀정보를 로그나 메시지에 노출하지 않는다.
* 일반적인 진행 단계에서는 Owner를 멘션하지 않는다.

C. 봇 시작 시 멈춘 작업 점검
task-0164에서 구현한 stale DOING 감지 기능을 재사용한다.
봇 시작 시 실행 기록이 없는 DOING 작업을 확인하고, 발견하면 Owner에게 보고한다.
이 점검은 읽기 전용이어야 한다.

* task 상태를 변경하지 않는다.
* 자동으로 재실행하거나 복구하지 않는다.
* 기존 task를 임의로 재분류하지 않는다.
* 중복 보고가 발생할 가능성과 처리 방식을 검토하고 결과를 설명한다.

3. 범위 제한
이번 작업은 R1만 구현한다.
다음 기능은 구현하지 않는다.

* 여러 task의 연속 실행 및 큐
* 자동 재시도 또는 자동 복구
* `DOING → FAILED` 신규 상태 전이
* Radar 자동 실행 또는 Radar 결과의 task 자동 생성
* Scheduler 및 백그라운드 자동 실행
* 자동 push
* Console 제어 기능 추가

4. 테스트 및 검증
기존 테스트를 수정할 때는 실제 동작을 검증하도록 한다. 단순히 테스트 기대값을 변경해 통과시키지 않는다.
최소 검증 항목:

1. 정상 실행 시 시작부터 완료까지 단계별 보고 순서가 정확하다.
2. repair가 발생하면 해당 보고가 나타나고, 발생하지 않으면 나타나지 않는다.
3. Worker·Reviewer·QA 실패 시 실패 보고와 Owner 멘션이 정확하다.
4. Owner 판단이 필요한 상황은 일반 실패와 구분해 보고한다.
5. Discord 보고 자체가 실패해도 본래 작업 실행 결과를 왜곡하지 않는다.
6. 봇 시작 시 stale DOING을 감지해 보고하지만 task 상태는 바꾸지 않는다.
7. 두 번째 Worker 실행 차단 등 task-0164의 기존 잠금 및 중복 실행 방지 기능이 유지된다.
8. 기존 Worker smoke, Discord self-check, SOP validator, Console 관련 테스트를 영향 범위에 맞게 실행한다.
9. `git diff --check`와 변경 파일 범위를 확인한다.

테스트에서 가능한 한 기존 fake Worker/Claude 방식을 사용한다. 실제 외부 서비스나 실작업을 불필요하게 실행하지 않는다.
5. 거버넌스 및 보호 규칙

* `jarvis.bat`은 절대로 열거나 읽거나 수정하거나 스테이징·커밋하지 않는다.
* task 상태를 임의로 DONE으로 변경하지 않는다.
* SOP나 master-plan의 잠긴 정책을 임의로 해제하지 않는다.
* 테스트 실패를 숨기거나 범위를 무단으로 넓히지 않는다.
* 기존 작업물과 사용자 변경사항을 덮어쓰지 않는다.
* push하지 않는다. push는 별도 Owner 승인을 기다린다.
* 변경 사항은 기존 SOP의 task 시작, 검토, QA, Console Complete, DONE checkpoint 승인 절차를 따른다.
* task 등록·상태 변경·커밋은 현재 SOP가 요구하는 승인 및 체크포인트 절차에 따른다.

6. 완료 보고
다음 항목을 보고하고 멈춘다.

1. 변경 파일 및 핵심 변경 사항
2. Discord 진행 보고 예시
3. Owner 멘션 및 에스컬레이션 동작
4. stale DOING 시작 점검 결과
5. 실행한 테스트와 각각의 실제 결과
6. Reviewer 및 QA 결과와 미해결 문제
7. 현재 task 상태와 승인 대기 항목
8. 커밋 및 push 여부
9. 다음 단계 R2를 진행하기 전에 필요한 결정

R1 구현과 검증 결과를 보고한 뒤 멈추고, 다음 작업이나 push는 별도 승인을 기다린다.
```
