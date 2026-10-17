# task-0164-worker-pipeline-hardening-and-radar-kind

- id: `task-0164-worker-pipeline-hardening-and-radar-kind`
- title: `Worker 파이프라인: 프로세스 간 잠금·멈춘 DOING 표시·작업 종류 레지스트리와 Daily AI Radar 작업 종류 추가`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-17 15:52 UTC`
- updated_at: `2026-10-17 16:26 UTC`
- summary: `Discord Worker 파이프라인(run_pipeline)을 재사용해, 두 번째 봇·두 번째 실행을 막는 프로세스 간 파일 잠금과 실행 기록 없는 DOING 표시(상태 변경 없음)를 더하고, Studyroom 한 종류로 고정된 ALLOWED_PREFIX·TEST_COMMAND·WORK_KIND를 작업 종류 레지스트리로 묶어 apps/daily-ai-radar를 두 번째 작업 종류로 등록한다. SOP §10.1 표와 validator가 레지스트리의 모든 작업 종류와 일치하도록 함께 고치고 Worker smoke로 두 종류를 실제 실행 경로에서 검증하며, Studyroom 동작·repair 상한 1·자동 루프 정책은 그대로이고 push는 하지 않는다.`
- source_command: `Owner 승인: task-0164 A안(SOP·validator 포함), S1~S5 한 task`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `9c322e0740b4d4dc7e10cb2321eb824d0599dd47` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 환경 | Windows ACP 949, Python 3.12.10 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (Owner: "repair는 최대 1회로 유지") |

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

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| P0 | "task-0164 등록 후 Console Start부터 구현 → Reviewer → 제한된 repair → 재검증 → QA까지 이어서 진행해도 됩니다." / SOP 순서 "task 등록 · Console Start · 구현 · Reviewer · repair(필요 시) · QA · Console Complete" | 이 기록 등록 → Console Project Control 화면의 Start → 구현 → candidate → Reviewer → (FINDINGS면 repair 1회 → 새 candidate → Reviewer) → QA까지 이어서 진행하고, Complete 전에 멈춘다 |
| P1 | "별도 승인 사항: Console Complete, DONE checkpoint 커밋, master-plan 수정, push는 실행하지 말고 각각 승인 대기하세요. 특히 push는 최종 검증 결과를 보고한 뒤 승인받으세요." / "임의로 Complete, push, master-plan 수정은 하지 말고 승인 대기." | Complete·DONE checkpoint·master-plan·push는 하지 않는다. QA 기록 checkpoint는 SOP 진행(재검증 기록)에 포함해 만들고 보고한다 |
| P2 | "작업이 끝나면 변경 파일, candidate 및 checkpoint 커밋, Reviewer·QA 결과, 회귀·변형 검증 결과, `git status`를 한 번에 보고하세요." / 보고 형식(candidate 해시, 변경 파일 수, Reviewer 결과, QA 결과, git status, 다음 승인 필요 여부) | QA 뒤 이 항목을 한 번에 보고한다 |
| S1 | 프로세스 간 잠금: "저장소 밖 파일 잠금", "두 번째 프로세스는 `worker_busy`로 즉시 종료", "성공 시 잠금 해제" | `claude_worker`에 OS 파일 잠금(Windows `msvcrt.locking`, 그 밖 `fcntl.flock`)을 `WORKTREE_ROOT` 아래 잠금 파일로 둔다(저장소 밖, 프로세스가 죽으면 OS가 해제). 봇은 `_WORKER_LOCK`과 이 잠금을 함께 잡고, 하나라도 못 잡으면 `worker_busy`로 거절하며 상태를 바꾸지 않는다. 실행이 끝나면(성공·실패 모두) 둘 다 해제한다 |
| S2 | 멈춘 DOING: "`/go` 거절 시 단순 busy와 실행 기록 없는 DOING을 구분해서 표시. 상태 변경은 금지." | `/go`가 DOING task를 받으면, Worker 잠금이 잡혀 있으면 `worker_busy`, 잠금이 비어 있고 실행 기록이 없으면 `doing_without_execution_record`(멈춘 DOING 안내 문구), 그 밖은 기존 `status_not_startable:DOING`. 어느 경우도 상태·기록을 바꾸지 않고 복구하지 않는다 |
| S3 | 레지스트리: "`ALLOWED_PREFIX`·`TEST_COMMAND`·`WORK_KIND`을 작업 종류별 표 하나로 묶는다. Studyroom 값은 그대로 첫 항목." | `WORK_KINDS`(작업 종류별 이름·표지어·허용 경로·테스트 스크립트·커밋 범위)를 두고 Studyroom을 첫 항목으로 둔다. 기존 이름(`WORK_KIND`·`ALLOWED_PREFIX`·`TEST_COMMAND`·`QA_CHECKS`)은 첫 항목에서 만든 호환 이름으로 남긴다. 실행 중 종류는 `run_pipeline`·`accept_candidate`의 인자로 정하고, 기존 함수 서명은 바꾸지 않는다 |
| S4 | Radar 등록: "`apps/daily-ai-radar/`", "smoke 테스트 그대로 사용" | 두 번째 항목: 허용 경로 `apps/daily-ai-radar/`, 테스트 `apps/daily-ai-radar/run_smoke_tests.py`(수정 없음) |
| S5 | Discord 진입점: "`WORK_KIND_MARKERS`가 studyroom · radar를 고르게 한다." | 표지어로 종류를 고른다(Studyroom: studyroom·스터디룸, Radar: radar·레이더). `/work`는 표지어가 없으면 hold, 둘 다면 hold. `/go`는 표지어가 없으면 기존처럼 Studyroom, 둘 다면 상태를 바꾸기 전에 거절한다 |
| A1 | A안: "`docs/jarvis-multi-agent-sop-v0.1.md`와 `scripts/validate_multi_agent_sop.py`를 허용 파일에 추가" / "레지스트리의 모든 작업 종류가 SOP §10.1 표와 validator에서 일치하는지 검증하세요." | SOP §10.1 표에 작업 종류별 값을 적고, validator가 `WORK_KINDS`를 AST로 읽어 종류 이름·허용 경로·테스트 스크립트를 종류별로 표와 대조하게 한다. 새 음성 검사(종류 누락, Radar 경로 변경 등)를 더한다 |
| X1 | 금지: "`jarvis.bat`" / "Console 기능 변경" / "Scheduler 구현" / "Background worker 구현" / "자동 push" / "자동 Resume" / "task 모델 변경" / "master-plan(완료 후에만)" / "새 dispatcher를 만들지 않는다." | 해당 파일·기능을 만들거나 바꾸지 않는다. `run_pipeline`·`accept_candidate`는 그대로 쓰고 인자만 더한다 |
| X2 | "기존 Studyroom 경로와 SOP 계약을 유지" / "Studyroom 기존 동작은 회귀 없이 유지한다." / "자동 루프는 기존 정책을 유지한다." / "repair는 최대 1회로 유지하세요." | Studyroom 값·`REPAIR_BUDGET_MAX = 1`·§10.2 규칙을 바꾸지 않는다. 기존 Worker smoke 354건 중 Studyroom 동작 검사는 그대로 두고, A2 승인에 따라 hold 사유 검사 1건의 기대값만 바꾼다(검사 수는 새 검사 12건을 더해 366) |
| X3 | "실제 봇 기동이나 Discord 외부 메시지 전송은 하지 마세요." / "예상하지 못한 범위 확대, 검증 실패, 안전성 문제가 생기면 멈추고 보고하세요." | 봇을 띄우지 않고 실제 claude도 부르지 않는다(검증은 Worker smoke의 가짜 claude와 self-check). 이상이 생기면 멈추고 보고한다 |
| X4 | "Owner 개입은 `/work` · `/go` · push만 남긴다." | 파이프라인 경로의 Owner 개입 지점을 늘리지 않는다 |
| A2 | Worker smoke 범위 추가 승인: "허용 파일에 `orchestrator/worker/run_smoke_tests.py`를 추가하세요." / "기존 `bot: non-Studyroom request is held` 검사는 삭제하지 말고, 새 동작에 맞게 수정하세요. 지원하지 않는 요청이 hold되고, 사유가 `unsupported_work_kind:`로 시작하며 등록된 작업 종류(`studyroom_content`, `daily_ai_radar`)가 포함되는지 확인하도록 하세요." | 그 검사를 지우지 않고 기대값만 바꿨다: hold, 사유가 `unsupported_work_kind:`로 시작, 두 종류 이름 포함 |
| A3 | "Worker smoke에 Radar 작업 종류 선택 및 해당 작업 종류의 설정(허용 경로와 테스트 명령)을 검증하는 회귀 검사를 추가하세요. 단순히 레지스트리에 이름이 존재하는지만 검사하지 말고, 실제 선택 경로가 올바른 설정을 전달하는지 확인하세요." / "이번 수정의 핵심은 기존 검사를 느슨하게 만드는 게 아니라, Studyroom과 Radar 두 작업 종류를 모두 실제 실행 경로에서 검증하는 것입니다." | 실제 `/work`→`/go`→`_run_worker_job`→`run_pipeline` 경로로 Radar task를 DONE까지 돌리고, Worker 프롬프트·Reviewer 호출의 허용 경로·테스트 명령, Radar smoke 실행(테스트·QA), 커밋 제목, 두 방향의 범위 위반(Radar 종류의 Studyroom 수정, Studyroom 종류의 Radar 수정)을 확인한다 |
| A4 | "기존 Studyroom 경로의 동작은 그대로 유지하세요." / "가능하면 잠금의 프로세스 간 배타성, 프로세스 종료 후 잠금 해제, `DOING` 감지의 상태 비변경도 검증하세요." | 기존 Studyroom 검사는 그대로 두었다. 별도 Python 프로세스가 잠금을 잡은 상태의 `/go`(`worker_busy`, 파일 불변), 그 프로세스를 끝낸 뒤 잠금 해제, 멈춘 DOING 보고와 파일 불변을 Worker smoke에 더했다 |
| A5 | "모든 검사가 통과하면 candidate 커밋을 만들고 Reviewer → 필요 시 repair 1회 → 새 Reviewer → QA 순서로 진행하세요. Console Complete, DONE checkpoint, master-plan 수정, push는 여전히 별도 승인 사항이며 실행하지 마세요." / 안전 조건(repair 최대 1회, `jarvis.bat` 금지, 실제 봇·Discord 금지, 이상 시 중단) | 아래 검증이 모두 통과한 뒤 candidate를 만들고 그 순서로 진행한다. Complete·DONE checkpoint·master-plan·push는 하지 않는다 |

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
| `adapters/discord/bot_minimal.py` | `WORK_KIND_MARKERS`를 레지스트리에서 만든다. `_acquire_worker_locks`·`_release_worker_locks`로 프로세스 안 잠금과 파일 잠금을 함께 잡고 푼다. `/work` 종류 선택(없으면 `unsupported_work_kind:…`, 둘이면 `ambiguous_work_kind:…` hold). `/go`는 제목으로 종류를 정하고(없으면 Studyroom, 둘이면 상태 변경 전 `ambiguous_work_kind`), DOING이면 잠금이 잡혀 있을 때 `worker_busy`, 비어 있고 실행 기록이 없으면 `doing_without_execution_record`(안내 문구, 상태 불변). `/work` 답장과 도움말에 작업 종류. self-check 4건 추가 |
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
