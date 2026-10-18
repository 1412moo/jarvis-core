# task-0164-worker-pipeline-hardening-and-radar-kind

- id: `task-0164-worker-pipeline-hardening-and-radar-kind`
- title: `Worker 파이프라인: 프로세스 간 잠금·멈춘 DOING 표시·작업 종류 레지스트리와 Daily AI Radar 작업 종류 추가`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-17 15:52 UTC`
- updated_at: `2026-10-17 17:05 UTC`
- summary: `Discord Worker 파이프라인(run_pipeline)을 재사용해, 두 번째 봇·두 번째 실행을 막는 프로세스 간 파일 잠금과 실행 기록 없는 DOING 표시(상태 변경 없음)를 더하고, Studyroom 한 종류로 고정된 ALLOWED_PREFIX·TEST_COMMAND·WORK_KIND를 작업 종류 레지스트리로 묶어 apps/daily-ai-radar를 두 번째 작업 종류로 등록한다. SOP §10.1 표와 validator가 레지스트리의 모든 작업 종류와 일치하도록 함께 고치고 Worker smoke로 두 종류를 실제 실행 경로에서 검증하며, Studyroom 동작·repair 상한 1·자동 루프 정책은 그대로이고 push는 하지 않는다.`
- source_command: `Owner 승인: task-0164 A안(SOP·validator 포함), S1~S5 한 task`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `9c322e0740b4d4dc7e10cb2321eb824d0599dd47` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 환경 | Windows ACP 949, Python 3.12.10 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (Owner: "repair는 최대 1회로 유지"). 시작 시점 값이며 뒤에 Owner가 `repair_budget`을 2로 늘렸다(R2, 아래 이력) |

## 조사 결과 (read-only, 등록 전 확인)

1. `orchestrator/worker/claude_worker.py`는 Studyroom 한 종류를 모듈 상수 `WORK_KIND`·`ALLOWED_PREFIX`·`TEST_COMMAND`로 고정하고,
   `_scope_violations`·`_run_tests`·`worker_prompt`·`reviewer_call`·`QA_CHECKS`·`_plan_resume`·`_candidate_chain`(커밋 제목
   `feat(studyroom): …`)·`find_owner_review_attempt`가 이를 직접 쓴다.
2. `adapters/discord/bot_minimal.py`: `WORK_KIND_MARKERS = ("studyroom", "스터디룸")`로 `/work`만 거르고 `/go`는 표지어를 보지 않는다.
   동시 실행은 프로세스 안 `_WORKER_LOCK`(threading.Lock)뿐이다. `/go`는 TODO·FAILED만 받아 DOING이면
   `status_not_startable:DOING`이다.
3. SOP §10.1은 범위 확대 시 표 갱신을 요구하고, `scripts/validate_multi_agent_sop.py`(`_validate_pipeline_parity`)는
   `ALLOWED_PREFIX`·`PROTECTED_PATHS`·`TEST_COMMAND` 모듈 상수를 AST로 읽어 표와 대조한다(`pipeline_scope_parity`). 실패 사유
   코드는 정해진 패턴(`resume_*`, `repair_no_*`, `reviewer_findings_not_repairable`, `reviewer_self_deviation`,
   `qa_unverified_owner_review`, `accept_*`)만 §10.2와 대조한다.
4. `orchestrator/worker/run_smoke_tests.py`(이번 허용 파일 아님)는 `claude_worker._run_tests`를 인자 하나짜리 lambda로 바꾸고,
   `worker_prompt`·`reviewer_call`·`QA_CHECKS`를 인자 없이 쓰며, `claude_worker.WORKTREE_ROOT`를 임시 경로로 바꾼다. 그래서 기존 함수
   서명과 이 이름들을 유지해야 Worker smoke를 고치지 않고 통과한다.
5. `apps/daily-ai-radar/run_smoke_tests.py`는 저장소 루트에서 실행해 통과하고 작업 트리를 바꾸지 않는다(등록 전 1회 실행으로 확인).

## Owner 결정 (원문)

```text
task-0164: Worker 파이프라인 범위 확대(선행 hardening + Radar)
이번 작업은 새 오케스트레이터를 만들지 않는다. 기존 `run_pipeline`을 그대로 재사용하고, 범위를 최소로 넓힌다.
목표

1. 프로세스 간 Worker 잠금 추가(두 번째 봇/두 번째 실행 차단)
2. 실행 기록 없는 `DOING` 감지 표시(복구는 하지 말고 표시만)
3. Worker 작업 종류 레지스트리 도입
4. 두 번째 작업 종류로 `apps/daily-ai-radar` 등록
5. 기존 Studyroom 파이프라인 동작은 그대로 유지

범위
허용:

* `orchestrator/worker/claude_worker.py`
* `adapters/discord/bot_minimal.py`
* Worker 관련 README(필요 시)
* task 기록

금지:

* `jarvis.bat`
* Console 기능 변경
* Scheduler 구현
* Background worker 구현
* 자동 push
* 자동 Resume
* task 모델 변경
* master-plan(완료 후에만)

핵심 원칙

* `run_pipeline`은 유지한다.
* 새 dispatcher를 만들지 않는다.
* Studyroom 기존 동작은 회귀 없이 유지한다.
* Radar는 두 번째 작업 종류만 추가한다.

구현
S1. 프로세스 간 잠금
현재 `_WORKER_LOCK`은 프로세스 내부만 막는다.
추가:

* 저장소 밖 파일 잠금
* 두 번째 프로세스는 `worker_busy`로 즉시 종료
* 성공 시 잠금 해제

S2. 멈춘 DOING 감지
`/go` 거절 시

* 단순 busy와
* 실행 기록 없는 DOING

을 구분해서 표시.
상태 변경은 금지.
S3. 작업 종류 레지스트리
현재 상수

* `ALLOWED_PREFIX`
* `TEST_COMMAND`
* `WORK_KIND`

을 작업 종류별 표 하나로 묶는다.
Studyroom 값은 그대로 첫 항목.
S4. Radar 등록
추가 작업 종류:

* `apps/daily-ai-radar/`
* smoke 테스트 그대로 사용

S5. Discord 진입점
`WORK_KIND_MARKERS`가

* studyroom
* radar

를 고르게 한다.
검증
T1
기존 Studyroom 경로 회귀 없음.
T2
Radar 작업 선택 확인.
T3
프로세스 간 잠금 검증.
두 번째 실행은 `worker_busy`.
T4
실행 기록 없는 `DOING` 표시 확인.
T5
Worker smoke 전부 통과.
T6
validator
`git diff --check`
T7
변형 검증

* 잠금 제거
* 레지스트리 제거
* Radar 제거

각각 새 검사가 잡는지 확인.
SOP

* task 등록
* Console Start
* 구현
* Reviewer
* repair(필요 시)
* QA
* Console Complete

순서를 그대로 유지.
승인 규칙
Owner 개입은

* `/work`
* `/go`
* push

만 남긴다.
자동 루프는 기존 정책을 유지한다.
보고 형식
각 단계마다 반드시 아래 형식으로 보고.

* candidate 해시
* 변경 파일 수
* Reviewer 결과
* QA 결과
* git status
* 다음 승인 필요 여부

임의로 Complete, push, master-plan 수정은 하지 말고 승인 대기.
```

```text
A안으로 진행 승인합니다.
`docs/jarvis-multi-agent-sop-v0.1.md`와 `scripts/validate_multi_agent_sop.py`를 허용 파일에 추가해서 S1~S5를 하나의 task로 진행하세요.
진행 조건:

* task-0164 등록 후 Console Start부터 구현 → Reviewer → 제한된 repair → 재검증 → QA까지 이어서 진행해도 됩니다.
* 기존 Studyroom 경로와 SOP 계약을 유지하고, 레지스트리의 모든 작업 종류가 SOP §10.1 표와 validator에서 일치하는지 검증하세요.
* 프로세스 간 잠금과 멈춘 DOING 감지는 상태를 임의로 변경하지 않는 범위로 제한하세요.
* repair는 최대 1회로 유지하세요.
* `jarvis.bat`은 열기·읽기·수정·스테이징·커밋하지 마세요.
* 실제 봇 기동이나 Discord 외부 메시지 전송은 하지 마세요.
* 예상하지 못한 범위 확대, 검증 실패, 안전성 문제가 생기면 멈추고 보고하세요.

별도 승인 사항: Console Complete, DONE checkpoint 커밋, master-plan 수정, push는 실행하지 말고 각각 승인 대기하세요. 특히 push는 최종 검증 결과를 보고한 뒤 승인받으세요.
작업이 끝나면 변경 파일, candidate 및 checkpoint 커밋, Reviewer·QA 결과, 회귀·변형 검증 결과, `git status`를 한 번에 보고하세요.
```
Worker smoke 범위 추가 승인(원문):

```text
A안으로 승인합니다.

1. 허용 파일에 `orchestrator/worker/run_smoke_tests.py`를 추가하세요.
2. 기존 `bot: non-Studyroom request is held` 검사는 삭제하지 말고, 새 동작에 맞게 수정하세요. 지원하지 않는 요청이 hold되고, 사유가 `unsupported_work_kind:`로 시작하며 등록된 작업 종류(`studyroom_content`, `daily_ai_radar`)가 포함되는지 확인하도록 하세요.
3. Worker smoke에 Radar 작업 종류 선택 및 해당 작업 종류의 설정(허용 경로와 테스트 명령)을 검증하는 회귀 검사를 추가하세요. 단순히 레지스트리에 이름이 존재하는지만 검사하지 말고, 실제 선택 경로가 올바른 설정을 전달하는지 확인하세요.
4. 기존 Studyroom 경로의 동작은 그대로 유지하세요.

이후 전체 Worker smoke와 관련 self-check, SOP validator, discord-intake smoke, Console smoke, `git diff --check`를 실행하세요. 가능하면 잠금의 프로세스 간 배타성, 프로세스 종료 후 잠금 해제, `DOING` 감지의 상태 비변경도 검증하세요.
안전 조건

* repair 예산은 기존대로 최대 1회입니다.
* `jarvis.bat`은 열기·읽기·수정·스테이징·커밋하지 마세요.
* 실제 봇 기동이나 Discord 외부 메시지 전송은 하지 마세요.
* 예상하지 못한 범위 변경이나 검증 실패가 발생하면 멈추고 보고하세요.

모든 검사가 통과하면 candidate 커밋을 만들고 Reviewer → 필요 시 repair 1회 → 새 Reviewer → QA 순서로 진행하세요. Console Complete, DONE checkpoint, master-plan 수정, push는 여전히 별도 승인 사항이며 실행하지 마세요.
이번 수정의 핵심은 기존 검사를 느슨하게 만드는 게 아니라, Studyroom과 Radar 두 작업 종류를 모두 실제 실행 경로에서 검증하는 것입니다.
```
Reviewer 2 retry FINDINGS 뒤 repair 2 승인(원문):

```text
A안으로 진행하세요. `repair_count` 예산을 2회로 늘리는 것도 승인합니다.
수정 기준

1. Studyroom 표지어가 있으면 `radar` 또는 `레이더`가 함께 있어도 Studyroom으로 선택합니다.
2. Studyroom 표지어 없이 Radar 표지어만 있는 경우에만 Radar로 선택합니다.
3. 둘 다 없는 `/work` 요청은 기존처럼 hold합니다.
4. 둘 다 없는 기존 `/go` 작업은 기존 Studyroom 동작을 유지합니다.
5. `/task`로 생성된 기존 작업도 제목의 일반 단어만으로 작업 종류가 뜻밖에 바뀌지 않도록 확인하세요. Radar 작업은 명시적인 식별 규칙을 사용하고, 필요하면 작업 종류 선택 방식을 별도로 설계하되 임의로 기존 작업을 재분류하지 마세요.

검증 및 진행

* 선택 함수와 실제 `/work` → `/go` → 파이프라인 경로를 모두 검사합니다.
* Studyroom과 Radar 각각의 회귀 테스트를 유지하고 추가합니다.
* SOP와 task 기록도 실제 동작과 일치하도록 수정합니다.
* Reviewer → 필요한 수정(최대 2회) → 새 Reviewer → QA 순서로 진행합니다.
* 기존의 잠금·멈춘 DOING 검사와 T7 변형 검사도 회귀하지 않았는지 확인합니다.
* `jarvis.bat`은 열거나 읽거나 수정·스테이징·커밋하지 마세요. 실제 봇 실행, 외부 Discord 메시지, push도 하지 마세요.

검증이 끝나면 결과와 candidate 커밋을 보고하세요. Console Complete, DONE 체크포인트, master-plan 수정, push는 별도 승인 전까지 진행하지 마세요.
```

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| P0 | "task-0164 등록 후 Console Start부터 구현 → Reviewer → 제한된 repair → 재검증 → QA까지 이어서 진행해도 됩니다." / SOP 순서 "task 등록 · Console Start · 구현 · Reviewer · repair(필요 시) · QA · Console Complete" | 이 기록 등록 → Console Project Control 화면의 Start → 구현 → candidate → Reviewer → (FINDINGS면 repair 1회 → 새 candidate → Reviewer) → QA까지 이어서 진행하고, Complete 전에 멈춘다 |
| P1 | "별도 승인 사항: Console Complete, DONE checkpoint 커밋, master-plan 수정, push는 실행하지 말고 각각 승인 대기하세요. 특히 push는 최종 검증 결과를 보고한 뒤 승인받으세요." / "임의로 Complete, push, master-plan 수정은 하지 말고 승인 대기." | Complete·DONE checkpoint·master-plan·push는 하지 않는다. QA 기록 checkpoint는 SOP 진행(재검증 기록)에 포함해 만들고 보고한다 |
| P2 | Block 1 "보고 형식 각 단계마다 반드시 아래 형식으로 보고. * candidate 해시 * 변경 파일 수 * Reviewer 결과 * QA 결과 * git status * 다음 승인 필요 여부" / Block 2 "작업이 끝나면 변경 파일, candidate 및 checkpoint 커밋, Reviewer·QA 결과, 회귀·변형 검증 결과, `git status`를 한 번에 보고하세요." | Owner에게 보고하는 단계(중간 보고와 최종 보고)마다 Block 1의 여섯 항목 형식을 쓴다. Block 2에 따라 Start부터 QA까지는 이어서 진행하고, 끝나면 Block 2의 항목을 한 번에 보고한다 |
| S1 | 프로세스 간 잠금: "저장소 밖 파일 잠금", "두 번째 프로세스는 `worker_busy`로 즉시 종료", "성공 시 잠금 해제" | `claude_worker`에 OS 파일 잠금(Windows `msvcrt.locking`, 그 밖 `fcntl.flock`)을 `WORKTREE_ROOT` 아래 잠금 파일로 둔다(저장소 밖, 프로세스가 죽으면 OS가 해제). 봇은 `_WORKER_LOCK`과 이 잠금을 함께 잡고, 하나라도 못 잡으면 `worker_busy`로 거절하며 상태를 바꾸지 않는다. 실행이 끝나면(성공·실패 모두) 둘 다 해제한다 |
| S2 | 멈춘 DOING: "`/go` 거절 시 단순 busy와 실행 기록 없는 DOING을 구분해서 표시. 상태 변경은 금지." / Block 2 "프로세스 간 잠금과 멈춘 DOING 감지는 상태를 임의로 변경하지 않는 범위로 제한하세요." | `/go`가 DOING task를 받으면, Worker 잠금이 잡혀 있으면 `worker_busy`, 잠금이 비어 있고 실행 기록이 없으면 `doing_without_execution_record`(멈춘 DOING 안내 문구), 그 밖은 기존 `status_not_startable:DOING`. 어느 경우도 상태·기록을 바꾸지 않고 복구하지 않는다 |
| S3 | 레지스트리: "`ALLOWED_PREFIX`·`TEST_COMMAND`·`WORK_KIND`을 작업 종류별 표 하나로 묶는다. Studyroom 값은 그대로 첫 항목." | `WORK_KINDS`(작업 종류별 이름·표지어·허용 경로·테스트 스크립트·커밋 범위)를 두고 Studyroom을 첫 항목으로 둔다. 기존 이름(`WORK_KIND`·`ALLOWED_PREFIX`·`TEST_COMMAND`·`QA_CHECKS`)은 첫 항목에서 만든 호환 이름으로 남긴다. 실행 중 종류는 `run_pipeline`·`accept_candidate`에 더한 선택 키워드 인자 `work_kind`(기본값 Studyroom)로 정한다. 두 함수의 기존 위치·키워드 인자는 그대로이고 그 밖의 함수 서명(`_run_tests`, `worker_prompt`, `reviewer_call` 등)은 바꾸지 않는다 |
| S4 | Radar 등록: "`apps/daily-ai-radar/`", "smoke 테스트 그대로 사용" | 두 번째 항목: 허용 경로 `apps/daily-ai-radar/`, 테스트 `apps/daily-ai-radar/run_smoke_tests.py`(수정 없음) |
| S5 | Discord 진입점: "`WORK_KIND_MARKERS`가 studyroom · radar를 고르게 한다." | 표지어로 종류를 고른다(Studyroom: studyroom·스터디룸, Radar: 앱 이름 daily ai radar·daily-ai-radar·daily_ai_radar·데일리 ai 레이더). 표지어가 함께 있으면 Studyroom이 우선한다(R2). `/work`는 표지어가 없으면 hold, `/go`는 표지어가 없으면 기존처럼 Studyroom |
| A1 | A안: "`docs/jarvis-multi-agent-sop-v0.1.md`와 `scripts/validate_multi_agent_sop.py`를 허용 파일에 추가" / "레지스트리의 모든 작업 종류가 SOP §10.1 표와 validator에서 일치하는지 검증하세요." | SOP §10.1 표에 작업 종류별 값을 적고, validator가 `WORK_KINDS`를 AST로 읽어 종류 이름·허용 경로·테스트 스크립트를 종류별로 표와 대조하게 한다. 새 음성 검사(종류 누락, Radar 경로 변경 등)를 더한다 |
| F0 | Block 1 "범위 허용: * `orchestrator/worker/claude_worker.py` * `adapters/discord/bot_minimal.py` * Worker 관련 README(필요 시) * task 기록" | 기본 허용 파일은 이 네 가지이고, A1(SOP·validator)과 A2(Worker smoke)로 추가된 것만 더한다. Worker README는 필요하지 않아 만들지 않았다. 그 밖의 파일은 바꾸지 않는다(아래 File ownership) |
| V0 | Block 1 "검증 T1 기존 Studyroom 경로 회귀 없음. T2 Radar 작업 선택 확인. T3 프로세스 간 잠금 검증. 두 번째 실행은 `worker_busy`. T4 실행 기록 없는 `DOING` 표시 확인. T5 Worker smoke 전부 통과. T6 validator `git diff --check` T7 변형 검증 * 잠금 제거 * 레지스트리 제거 * Radar 제거 각각 새 검사가 잡는지 확인." / Block 3 "이후 전체 Worker smoke와 관련 self-check, SOP validator, discord-intake smoke, Console smoke, `git diff --check`를 실행하세요." | T1~T7과 Block 3의 실행 목록은 Owner 조건이다. 아래 "검증 계획"의 T1~T7로 모두 실행하고, 결과는 "Implementer 검증"(candidate 전)과 QA 절(candidate 기준)에 적는다 |
| R2 | Reviewer 2 retry 뒤 Owner 결정: "A안으로 진행하세요. `repair_count` 예산을 2회로 늘리는 것도 승인합니다." | repair 예산을 2로 늘려 repair 2를 진행한다(`repair_count=2`, 소진) |
| R3 | 수정 기준: "1. Studyroom 표지어가 있으면 `radar` 또는 `레이더`가 함께 있어도 Studyroom으로 선택합니다." / "2. Studyroom 표지어 없이 Radar 표지어만 있는 경우에만 Radar로 선택합니다." / "3. 둘 다 없는 `/work` 요청은 기존처럼 hold합니다." / "4. 둘 다 없는 기존 `/go` 작업은 기존 Studyroom 동작을 유지합니다." / "5. `/task`로 생성된 기존 작업도 제목의 일반 단어만으로 작업 종류가 뜻밖에 바뀌지 않도록 확인하세요. Radar 작업은 명시적인 식별 규칙을 사용하고, 필요하면 작업 종류 선택 방식을 별도로 설계하되 임의로 기존 작업을 재분류하지 마세요." | 1·2: `select_work_kind()`가 레지스트리 순서(Studyroom 먼저)로 처음 맞는 종류를 고른다. 3: `/work`는 표지어가 없으면 hold. 4: `/go`는 표지어가 없으면 Studyroom. 5: Radar 표지어를 일반 단어 radar·레이더가 아니라 앱 이름(daily ai radar·daily-ai-radar·daily_ai_radar·데일리 ai 레이더)으로 한정했다. 그래서 `/task` 제목이 radar·레이더를 포함해도 Studyroom으로 남는다. 저장소에서 제목에 radar·레이더가 있는 task는 이 task(DOING, 수동 SOP task) 하나뿐이라 재분류되는 startable task는 없다(조회로 확인). 모호함 거절은 없앴다 |
| R4 | 검증 및 진행: "선택 함수와 실제 `/work` → `/go` → 파이프라인 경로를 모두 검사합니다." / "Studyroom과 Radar 각각의 회귀 테스트를 유지하고 추가합니다." / "SOP와 task 기록도 실제 동작과 일치하도록 수정합니다." / "Reviewer → 필요한 수정(최대 2회) → 새 Reviewer → QA 순서로 진행합니다." / "기존의 잠금·멈춘 DOING 검사와 T7 변형 검사도 회귀하지 않았는지 확인합니다." / "`jarvis.bat`은 열거나 읽거나 수정·스테이징·커밋하지 마세요. 실제 봇 실행, 외부 Discord 메시지, push도 하지 마세요." / "검증이 끝나면 결과와 candidate 커밋을 보고하세요. Console Complete, DONE 체크포인트, master-plan 수정, push는 별도 승인 전까지 진행하지 마세요." | self-check(선택 함수)와 Worker smoke(실경로) 모두에서 Studyroom 우선·일반 단어 무시·Radar 실행을 확인하고 기존 검사를 유지한다. SOP §10.1과 이 기록을 실제 동작에 맞췄다. 잠금·멈춘 DOING 검사와 T7 변형(M1~M3)을 다시 실행하고 새 변형(M4 우선순위 뒤집기, M5 일반 단어 표지어 복귀)을 더한다. 새 candidate에 Reviewer → QA 뒤 결과와 candidate를 보고한다. `jarvis.bat`·실제 봇·Discord·push 없음, Complete·DONE checkpoint·master-plan·push는 하지 않는다 |
| X1 | 금지: "`jarvis.bat`" / "Console 기능 변경" / "Scheduler 구현" / "Background worker 구현" / "자동 push" / "자동 Resume" / "task 모델 변경" / "master-plan(완료 후에만)" / "새 dispatcher를 만들지 않는다." | 해당 파일·기능을 만들거나 바꾸지 않는다. `run_pipeline`·`accept_candidate`는 그대로 쓰고 인자만 더한다 |
| X2 | "기존 Studyroom 경로와 SOP 계약을 유지" / "Studyroom 기존 동작은 회귀 없이 유지한다." / "자동 루프는 기존 정책을 유지한다." / "repair는 최대 1회로 유지하세요." | Studyroom 값·파이프라인 상한 `REPAIR_BUDGET_MAX = 1`·§10.2 규칙을 바꾸지 않는다. 이 task 자체의 SOP repair 예산은 처음 1회였고 R2에서 Owner가 2회로 늘렸다. 기존 Worker smoke 354건 중 Studyroom 동작 검사는 그대로 두고, A2 승인에 따라 hold 사유 검사 1건의 기대값만 바꾼다(검사 수는 새 검사를 더해 repair 2 뒤 368) |
| X3 | "실제 봇 기동이나 Discord 외부 메시지 전송은 하지 마세요." / "예상하지 못한 범위 확대, 검증 실패, 안전성 문제가 생기면 멈추고 보고하세요." | 봇을 띄우지 않고 실제 claude도 부르지 않는다(검증은 Worker smoke의 가짜 claude와 self-check). 이상이 생기면 멈추고 보고한다 |
| X4 | "Owner 개입은 `/work` · `/go` · push만 남긴다." | 파이프라인 경로의 Owner 개입 지점을 늘리지 않는다 |
| A2 | Worker smoke 범위 추가 승인: "허용 파일에 `orchestrator/worker/run_smoke_tests.py`를 추가하세요." / "기존 `bot: non-Studyroom request is held` 검사는 삭제하지 말고, 새 동작에 맞게 수정하세요. 지원하지 않는 요청이 hold되고, 사유가 `unsupported_work_kind:`로 시작하며 등록된 작업 종류(`studyroom_content`, `daily_ai_radar`)가 포함되는지 확인하도록 하세요." | 그 검사를 지우지 않고 기대값만 바꿨다: hold, 사유가 `unsupported_work_kind:`로 시작, 두 종류 이름 포함 |
| A3 | "Worker smoke에 Radar 작업 종류 선택 및 해당 작업 종류의 설정(허용 경로와 테스트 명령)을 검증하는 회귀 검사를 추가하세요. 단순히 레지스트리에 이름이 존재하는지만 검사하지 말고, 실제 선택 경로가 올바른 설정을 전달하는지 확인하세요." / "이번 수정의 핵심은 기존 검사를 느슨하게 만드는 게 아니라, Studyroom과 Radar 두 작업 종류를 모두 실제 실행 경로에서 검증하는 것입니다." | 실제 `/work`→`/go`→`_run_worker_job`→`run_pipeline` 경로로 Radar task를 DONE까지 돌리고, Worker 프롬프트·Reviewer 호출의 허용 경로·테스트 명령, Radar smoke 실행(테스트·QA), 커밋 제목, 두 방향의 범위 위반(Radar 종류의 Studyroom 수정, Studyroom 종류의 Radar 수정)을 확인한다 |
| A4 | "기존 Studyroom 경로의 동작은 그대로 유지하세요." / "가능하면 잠금의 프로세스 간 배타성, 프로세스 종료 후 잠금 해제, `DOING` 감지의 상태 비변경도 검증하세요." | 기존 Studyroom 검사는 그대로 두었다. 별도 Python 프로세스가 잠금을 잡은 상태의 `/go`(`worker_busy`, 파일 불변), 그 프로세스를 끝낸 뒤 잠금 해제, 멈춘 DOING 보고와 파일 불변을 Worker smoke에 더했다 |
| A5 | "모든 검사가 통과하면 candidate 커밋을 만들고 Reviewer → 필요 시 repair 1회 → 새 Reviewer → QA 순서로 진행하세요. Console Complete, DONE checkpoint, master-plan 수정, push는 여전히 별도 승인 사항이며 실행하지 마세요." / 안전 조건(repair 최대 1회, `jarvis.bat` 금지, 실제 봇·Discord 금지, 이상 시 중단) | 아래 검증이 모두 통과한 뒤 candidate를 만들고 그 순서로 진행한다(repair 횟수는 뒤에 R2로 2회까지 늘어남). Complete·DONE checkpoint·master-plan·push는 하지 않는다 |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`, `adapters/discord/bot_minimal.py`, `orchestrator/worker/run_smoke_tests.py`(A2 승인으로 추가), `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1 표와 관련 문장), `scripts/validate_multi_agent_sop.py`(파이프라인 대조와 음성 검사), 필요 시 Worker README, 이 기록 |
| deny | `jarvis.bat`, `.env`, `apps/jarvis-console/`, `apps/daily-ai-radar/`(사용만), `docs/task-model.md`, `docs/master-plan.md`, 다른 task 기록, 그 밖의 모든 파일 |

## 검증 계획

| # | 항목 |
| --- | --- |
| T1 | Studyroom 회귀 없음: Worker smoke 354/0 그대로, 레지스트리 첫 항목 값이 기존 상수와 같음 |
| T2 | Radar 선택: 표지어별 종류 선택(Studyroom·Radar·없음·둘 다), Radar 종류의 허용 경로·테스트 명령·범위 검사 |
| T3 | 프로세스 간 잠금: 다른 핸들이 잡은 잠금에서 `/go`가 `worker_busy`이고 상태가 그대로이며, 실행이 끝나면 잠금이 풀림 |
| T4 | 실행 기록 없는 DOING: `/go`가 `doing_without_execution_record`를 내고 상태·파일이 그대로, 잠금이 잡혀 있으면 `worker_busy` |
| T5 | Worker smoke 전부 통과(파일 수정 없이) |
| T6 | SOP validator PASS(새 음성 검사 포함), Discord self-check, discord-intake smoke, Console smoke, `git diff --check`, 변경 범위 |
| T7 | 변형: 파일 잠금 제거, 레지스트리 제거(종류 하나로 되돌림), Radar 항목 제거가 각각 새 검사(self-check·validator)에서 실패로 드러나는지 |

검증에서 실제 봇·Discord·claude를 실행하지 않는다.

## 구현 착수

2026-10-17 15:53 UTC에 Console Project Control 화면에서 Start(Preview → Confirm Start)로 `TODO→DOING`을 적용했다(Receipt "Updated",
상태 표시 "Task write succeeded: TODO → DOING; Overview refresh succeeded.").

중간 보고: 첫 구현 뒤 Worker smoke 354건 중 `bot: non-Studyroom request is held` 1건이 실패했다. 그 검사가 hold 사유에
`studyroom_content_only` 문자열을 요구했는데 Radar 추가로 사유가 바뀌었기 때문이다. smoke 파일이 허용 파일 밖이라 멈추고 보고했고,
Owner가 A2~A5(위 원문)로 smoke 파일을 범위에 넣었다.

## 구현

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `WorkKind`와 `WORK_KINDS`(Studyroom 첫 항목, Radar 두 번째), `work_kind_by_name`·`work_kinds_for_text`. 기존 이름 `WORK_KIND`·`ALLOWED_PREFIX`·`TEST_COMMAND`·`QA_CHECKS`는 첫 항목에서 만든다. 실행 중 종류는 `ContextVar`로 두고 `run_pipeline(work_kind=)`·`accept_candidate(work_kind=)`가 정한다(본문은 `_run_pipeline`·`_accept_candidate`로 이름만 옮김, 기존 함수 서명 유지). 범위 검사·테스트 명령·Worker 프롬프트·Reviewer 호출의 QA 설명과 경로·커밋 제목·accept의 커밋 사슬 확인이 그 종류를 쓴다. 저장소 밖 OS 파일 잠금 `acquire_process_lock`·`release_process_lock`·`process_lock_held`(`WORKTREE_ROOT/.jarvis-worker.lock`). `WorkerRunResult.work_kind` |
| `adapters/discord/bot_minimal.py` | `WORK_KIND_MARKERS`를 레지스트리에서 만든다. `_acquire_worker_locks`·`_release_worker_locks`로 프로세스 안 잠금과 파일 잠금을 함께 잡고 푼다. `/work` 종류 선택(`claude_worker.select_work_kind`, Studyroom 우선; 없으면 `unsupported_work_kind:…` hold, repair 2 전에는 두 종류면 `ambiguous_work_kind`로 hold하던 것을 없앰). `/go`는 제목으로 종류를 정하고(없으면 Studyroom), DOING이면 잠금이 잡혀 있을 때 `worker_busy`, 비어 있고 실행 기록이 없으면 `doing_without_execution_record`(안내 문구, 상태 불변). `/work` 답장과 도움말에 작업 종류. self-check 4건 추가 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §10.1 표를 종류별 값(`값`(종류) 형식)과 잠금·멈춘 DOING 설명으로 바꾸고, 범위가 task-0164로 넓어졌음을 적었다 |
| `scripts/validate_multi_agent_sop.py` | `_work_kinds()`로 `WORK_KINDS`를 AST에서 읽어 종류 이름·허용 경로·테스트 스크립트를 종류별로 §10.1과 대조. 음성 검사 4건 추가(SOP에서 Radar 종류 누락, 코드에서 종류 이름 변경, 코드에서 Radar 경로 변경, SOP에서 Radar 테스트 변경) |
| `orchestrator/worker/run_smoke_tests.py` | 가짜 Worker `radar` 모드(Radar README에 한 줄 추가). 기존 hold 검사 기대값 변경, 두 종류 hold 검사, Radar 실경로 검사 7건, `process_lock_flow`(별도 프로세스 잠금·해제·멈춘 DOING) 4건 |

`run_pipeline`·`accept_candidate`의 본문 흐름, `REPAIR_BUDGET_MAX = 1`, §10.2 규칙, Studyroom 값은 바꾸지 않았다. 새 dispatcher·scheduler·background worker·자동 push·자동 resume은 없다.

## Implementer 검증 (작업 트리 기준, candidate 전)

| # | 결과 |
| --- | --- |
| T1·T5 | Worker smoke 366/0(기존 354 + 새 12, 기존 Studyroom 검사 전부 통과, 기존 hold 검사는 새 기대값으로 통과) |
| T2 | Worker smoke Radar 실경로: `/work`가 `daily_ai_radar`·`apps/daily-ai-radar/`·`-B apps/daily-ai-radar/run_smoke_tests.py` 선택, `/go`→`_run_worker_job`이 DONE, 변경 파일 `apps/daily-ai-radar/README.md`, Worker 프롬프트에 Radar 경로만, Reviewer 호출에 Radar 테스트 명령과 경로, test_summary에 "Daily AI Radar smoke tests passed", QA `tests_rerun` 통과, 후보 커밋 제목 `feat(daily-ai-radar): …`, 두 방향 범위 위반 `scope_violation`. self-check `worker_kind_selected_by_marker`·`worker_kind_registry_studyroom_first_radar_second` PASS |
| T3 | Worker smoke: 별도 Python 프로세스가 잠금을 잡은 동안 `/go`는 `worker_busy`이고 파일 불변, 프로세스 안 잠금도 남지 않음. 그 프로세스를 끝내면 잠금 해제. self-check `worker_lock_across_processes_refuses_with_worker_busy` PASS |
| T4 | Worker smoke: 다른 프로세스가 실행 중이면 DOING task도 `worker_busy`, 잠금이 비면 `doing_without_execution_record`이고 파일 불변, 답장에 "멈춘 DOING". self-check `go_reports_doing_without_execution_record_and_changes_nothing` PASS |
| T6 | self-check 98/0(설정 없음·`PYTHONUTF8=1`, `.env` 없는 임시 worktree), SOP validator PASS(음성 검사 133, 129에서 +4), discord-intake 139/0, Console smoke PASS, `git diff --check` 통과, 변경 파일 5개와 이 기록 |
| T7 | 작업 트리 복사본 임시 worktree에서 변형 3종: 파일 잠금 제거(프로세스 안 잠금만) → Worker smoke 2건·self-check 2건 실패. 레지스트리 무시(항상 Studyroom) → Worker smoke Radar 5건 실패. Radar 항목 제거 → Worker smoke 실패(Radar 검사 뒤 진행 중단, 종료 1), self-check 2건 실패, validator `pipeline_scope_parity` 4건. 실행 뒤 임시 worktree 삭제, 메인 checkout 실행 전후 같음 |

검증에서 실제 봇·Discord·claude를 실행하지 않았다(Worker smoke는 가짜 claude, self-check는 임시 저장소와 대역).

## Reviewer와 repair 이력

| 회차 | candidate | 결과 |
| --- | --- | --- |
| Reviewer 1 | `3d69bc8c4b95d464178611841d8eb7d2bf3f18af` | FINDINGS(minor 4, 모두 이 기록), `self_deviations` 없음: Block 1 기본 허용 파일 목록 행 없음, T1~T7과 Block 3 실행 목록 행 없음, P2에 단계별 보고 형식 빠짐, S3가 "기존 함수 서명은 바꾸지 않는다"라고 했으나 `run_pipeline`·`accept_candidate`에 선택 인자가 늘어남. 코드 지적 없음 |
| repair 1 | (이 기록 수정) | Manager가 budget 안에서 진행. F0(기본 허용 파일)·V0(T1~T7과 실행 목록) 행 추가, P2에 Block 1 단계별 보고 형식과 Block 2 최종 보고를 함께 적음, S3를 "선택 키워드 인자 `work_kind` 추가, 기존 인자 유지"로 고침, S2에 Block 2 문장 인용 추가. 코드 변경 없음. `repair_count=1`(budget 1 소진) |
| Reviewer 2 | `922712fec5703c326064f4447eef518625a0d541` | PASS였으나 `self_deviations` 1건(출력 초과 공개)이 있고, Manager가 승인 원문을 참조로만 넘긴 호출 결함이 있어 무효. 같은 candidate로 retry(`retry_count=1`, retry budget 소진) |
| Reviewer 2 retry | `922712fec5703c326064f4447eef518625a0d541` | FINDINGS(minor 1), `self_deviations` 없음: 두 표지어가 함께 있는 요청을 hold·거절하는 규칙이 Studyroom 기존 동작(표지어만 있으면 Studyroom)을 바꾼다. 코드 동작 지적 |
| repair 2 | (코드·SOP·smoke·이 기록) | Owner가 repair budget을 2로 늘리고 수정 기준을 정했다(R2). `select_work_kind()`(레지스트리 순서 우선, Studyroom 먼저), Radar 표지어를 앱 이름으로 한정, 모호함 거절 제거. self-check 선택 검사와 Worker smoke 실경로 검사(두 표지어 요청이 Studyroom으로 DONE, `/task` 제목의 일반 단어 radar·레이더가 Studyroom으로 DONE, `/work`의 일반 단어 hold)로 바꾸고 SOP §10.1 문구를 맞췄다. `repair_count=2`(2회 중 2회 사용, 소진) |
| Reviewer 3 | `7003cb50924ecdeceba6b3b7cc8affcc105b5911` | FINDINGS(minor 3, 모두 이 기록), `self_deviations` 없음: Manager 요약 표에 Owner 문장 "Radar는 두 번째 작업 종류만 추가한다.", "새 오케스트레이터를 만들지 않는다. 기존 `run_pipeline`을 그대로 재사용하고, 범위를 최소로 넓힌다.", "S1~S5를 하나의 task로 진행하세요."가 인용되지 않음. 코드·SOP·테스트 동작 지적 없음. repair·retry 예산이 모두 소진되어 Owner에게 보고했고, Owner가 SOP §8로 수용했다(아래 원문) |

## repair 2 검증 (작업 트리 기준, 새 candidate 전)

| # | 결과 |
| --- | --- |
| T1·T5 | Worker smoke 368/0. 기존 Studyroom 검사 통과, `/work` 일반 단어 hold 검사와 Studyroom 우선 실경로 검사 2건(두 표지어 요청이 Studyroom으로 DONE, `/task` 제목의 일반 단어 radar·레이더가 `/go`에서 Studyroom으로 DONE) 포함 |
| T2 | Radar 실경로 검사 7건 그대로 통과(표지어 `Daily AI Radar`). self-check `worker_kind_selected_by_marker`가 Studyroom 우선·일반 단어 무시·공백이 여러 개인 `Daily  AI  Radar` 선택까지 확인 |
| T3·T4 | 별도 프로세스 잠금·해제·멈춘 DOING 검사(Worker smoke 4건, self-check 2건) 통과 |
| T6 | self-check 98/0(설정 없음·`PYTHONUTF8=1`, `.env` 없는 임시 worktree), SOP validator PASS(음성 검사 133), discord-intake 139/0, Console smoke PASS, `git diff --check` 통과 |
| T7 | 작업 트리 복사본 임시 worktree에서 변형 5종 모두 검출: M1 파일 잠금 제거 → Worker smoke 2·self-check 2 실패. M2 레지스트리 무시 → Worker smoke Radar 5 실패. M3 Radar 항목 제거 → Worker smoke 중단(종료 1)·self-check 2·validator `pipeline_scope_parity` 4. M4 우선순위 뒤집기 → Worker smoke 1·self-check 1. M5 일반 단어를 Radar 표지어로 복귀 → Worker smoke 2·self-check 1 |

## Reviewer 3 minor 수용 (SOP §8)

Owner 결정(원문):

```text
1번으로 승인합니다. Reviewer 3의 minor 3건은 SOP §8에 따라 수용하고, candidate `7003cb50924ecdeceba6b3b7cc8affcc105b5911`로 QA를 진행하세요.
수용 기록에는 다음을 명시하세요.

* Radar는 두 번째 작업 종류만 추가한다.
* 새 오케스트레이터를 만들지 않고 기존 `run_pipeline`을 재사용하며 변경 범위를 최소화한다.
* S1~S5를 task-0164 하나로 진행한다.
* Reviewer 3의 minor 3건은 작업 기록의 Manager 요약 표에 승인 원문 일부가 인용되지 않은 문제이며, 코드·SOP·테스트 동작에 대한 지적은 아니라는 판단으로 수용한다.

QA는 candidate 커밋을 기준으로 독립적으로 실행하고, Studyroom/Radar 경로, 잠금, 멈춘 DOING 감지, 관련 smoke와 validator를 확인하세요. QA 결과가 나오면 보고하고 멈추세요.
`jarvis.bat`은 건드리지 말고, Console Complete, DONE 체크포인트, master-plan 수정, push는 별도 승인 전까지 진행하지 마세요. SOP 운영 규칙 개선도 이번 task에 끼워 넣지 말고 task-0164 종료 후 별도 결정 사항으로 남기세요.
```

| 수용 항목 | 기록 |
| --- | --- |
| Radar 범위 | Radar는 두 번째 작업 종류만 추가한다. 레지스트리는 Studyroom(첫 항목)과 Radar 두 항목뿐이다 |
| 오케스트레이터 | 새 오케스트레이터를 만들지 않고 기존 `run_pipeline`을 재사용하며 변경 범위를 최소화한다. `run_pipeline`·`accept_candidate`는 선택 인자 `work_kind`만 더했다 |
| task 단위 | S1~S5를 task-0164 하나로 진행한다 |
| 수용 근거 | Reviewer 3의 minor 3건은 이 기록의 Manager 요약 표에 승인 원문 일부가 인용되지 않은 문제이며, 코드·SOP·테스트 동작에 대한 지적은 아니라는 판단으로 수용한다 |
| 효력 | candidate `7003cb50924ecdeceba6b3b7cc8affcc105b5911`에만 유효하다. candidate가 바뀌면 다시 Reviewer를 받는다 |

SOP 운영 규칙(Manager 요약 표 인용 규칙) 개선은 이 task에 넣지 않고 task-0164 종료 뒤 별도 결정 사항으로 남긴다.

## QA (candidate `7003cb50924ecdeceba6b3b7cc8affcc105b5911`)

2026-10-18, `.env` 없는 detached 임시 worktree에서 candidate 커밋 그대로 실행했다. 비교 기준은 `origin/main` `9c322e0`.

| 검사 | 결과 |
| --- | --- |
| Worker smoke | 368/0. Studyroom 기존 경로(`/go` TODO→DOING, 성공 답장·DONE), 두 표지어 요청과 `/task` 제목의 일반 단어 radar·레이더가 Studyroom으로 DONE, `/work` 일반 단어 hold, Radar 실경로 7건, 프로세스 간 잠금(`worker_busy`·파일 불변)·종료 뒤 해제, 다른 Worker 실행 중 DOING은 `worker_busy`, 실행 기록 없는 DOING은 보고만 하고 불변 |
| Discord self-check | 98/0, 설정 없음과 `PYTHONUTF8=1` 두 환경. 새 4건(`worker_kind_registry_studyroom_first_radar_second`, `worker_kind_selected_by_marker`, `worker_lock_across_processes_refuses_with_worker_busy`, `go_reports_doing_without_execution_record_and_changes_nothing`) 통과 |
| SOP validator | PASS, 음성 검사 133/0 |
| discord-intake smoke | 139/0 |
| Console smoke | PASS |
| Radar smoke(수정 없음) | PASS |
| `git diff --check` | 통과 |
| 변경 범위 | `bot_minimal.py`, SOP 문서, 이 기록, `claude_worker.py`, Worker smoke, validator 6개. `apps/daily-ai-radar/` 변경 없음, `jarvis.bat` 트리에 없음 |
| 변형 M1~M5 | candidate 복사본 임시 worktree에서 모두 검출: M1 파일 잠금 제거 → Worker smoke 2·self-check 2. M2 레지스트리 무시 → Worker smoke 5. M3 Radar 항목 제거 → Worker smoke 중단(종료 1)·self-check 2·validator `pipeline_scope_parity`. M4 우선순위 뒤집기 → Worker smoke 1·self-check 1. M5 일반 단어 표지어 복귀 → Worker smoke 2·self-check 1 |
| 실행 뒤 | QA 트리 변경 없음, 임시 worktree 삭제, 메인 checkout 실행 전후 같음 |

판정: PASS. 실제 봇·Discord·claude는 실행하지 않았다(Worker smoke는 가짜 claude). Console Complete·DONE checkpoint·master-plan·push는 별도 승인 대기.
