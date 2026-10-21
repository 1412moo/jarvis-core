# task-0178 수동 SOP task 공식 종료 경로 설계

상태: 설계(구현 전). 이 문서는 코드·SOP·task 상태를 바꾸지 않는다. 구현은 Owner가 이 설계를
승인한 뒤 별도 task로 한다. 아래 "현재 동작"은 baseline `5ccbd92` 시점의 코드를 읽어 확인한
사실이며, 명령을 실제로 실행해 확인하지는 않았다(실행하면 task 상태가 바뀔 수 있다).

## 1. 문제

수동 SOP task(Owner 결정으로 Claude Code 세션 등에서 만든 task)를 공식으로 닫을 방법이 없다.

- `DOING → DONE`(Console Complete)은 SOP §8 완료 조건(같은 candidate의 Reviewer PASS와 QA PASS)을
  채운 task에만 맞다. 중단된 task-0175처럼 그 조건을 채울 수 없는 task는 `DOING`으로 남는다.
  task-0031도 `DOING`이다.
- 상태 writer(`orchestrator/discord-intake/task_file_writer.py`의 `TASK_STATUS_TRANSITIONS`)는
  `DOING → FAILED`를 허용하지만, 수동 task에 그 전이를 거는 진입점이 없다. Console 동작은 Start,
  Complete, Hold, Resume, Record Completion Evidence뿐이고, Discord `/go <id> recover`는
  `source_command`가 `/task`인 Worker 경로 task만 받는다(`adapters/discord/bot_minimal.py` `_run_recover`).

## 2. 현재 동작 중 위험 (재실행·자동 전이)

| 진입점 | 수동 task에 대한 현재 동작 |
| --- | --- |
| `/go <id>` | `FAILED`인 task를 `source_command`를 보지 않고 `FAILED → TODO → DOING`으로 바꾼 뒤 Worker 작업을 시작한다(기본 작업 종류 Studyroom). 수동 task를 `FAILED`로 닫으면 이 경로로 다시 실행될 수 있다. |
| `/retry <id>` | `FAILED`·`DOING` task를 받는다. `source_command`가 `/task`인 Worker 경로 task만 거부하고 나머지(수동 task 포함)는 아래 `/run`과 같은 실행 흐름으로 보낸다. |
| `/run <id>` | `DOING` task를 받는다. 실행 대상인지는 title·summary의 키워드로 정한다(`_build_execution_candidate`: `script`·`run`·`demo` → script, `smoke`·`demo`가 있으면 target `discord_intake_smoke_tests`; `test`·`검증` → test). |

`/run`·`/retry`의 실행 흐름(`_run_execution_flow`)은 허용 목록(`EXECUTION_SCRIPT_WHITELIST`)에 있는
smoke 테스트를 실제로 실행하고, 그 결과로 `DOING → DONE`(성공) 또는 `DOING → FAILED`(실패)를
자동 기록한다(`_apply_execution_result`). 키워드 판정을 코드로 대조하면 task-0031의
title·summary는 `script` 실행과 허용 목록의 target에 해당한다. 따라서 `/run task-0031`은
Owner 검토 없이 smoke 테스트를 돌리고 task-0031을 DONE 또는 FAILED로 바꿀 수 있다(실행 확인은 하지 않음).
task-0175는 키워드에 해당하지 않는다.

## 3. 대안 비교

| 안 | 내용 | 장점 | 위험·비용 |
| --- | --- | --- | --- |
| A | 기존 `FAILED` 재사용, Console에 종료 동작만 추가 | 변경이 가장 작다 | `/go`가 다시 실행할 수 있다. 사유를 남길 자리가 없다. Task View·`/report`에서 영구히 "주의 필요"로 보인다. |
| B | A + Owner 사유 필드 + `/go`·`/retry`·`/run` 재실행 차단 | 상태 7개 유지 | 세 명령(과 `/go resume`·`accept`)에 차단 조건을 빠짐없이 넣어야 한다. 하나라도 빠지면 재실행된다. FAILED가 "실행 실패"와 "Owner 종료"를 함께 뜻하게 된다. |
| C | 새 종결 상태 `CLOSED` + Owner 사유 필드 | `/go`·`/retry`·`/run`의 허용 상태(`TODO`·`FAILED`·`DOING`)에 들어 있지 않아 **구조적으로** 재실행되지 않는다. 의미가 분명하다(실패가 아닌 Owner 종료). | 상태 어휘를 늘리는 변경이라 영향 범위가 넓다(아래 5절). task-0098(ON_HOLD 추가) 수준의 Owner 결정이 필요하다. |
| D | 현상 유지 | 변경 없음 | task-0175·0031이 DOING으로 남고, 2절의 `/run` 위험이 그대로다. |

**추천: C.** 이 기능의 핵심 요구는 "닫힌 task가 다시 실행되지 않는 것"이다. B는 그 보장을 여러
명령의 차단 코드에 의존하지만, C는 실행 명령들이 원래 받지 않는 상태를 써서 보장한다.

## 4. 추천안(C) 상세

1. 상태: `CLOSED` — "Owner가 완료 조건 없이 의도적으로 종료함". 다시 열지 않는다(다시 하려면 새 task).
2. 전이: `DOING → CLOSED` 하나만 연다. 다른 출발 상태(`TODO`·`NEEDS_APPROVAL`·`ON_HOLD`·`FAILED`)는
   이번 범위에서 제외하고, 필요하면 별도 결정으로 넓힌다.
3. 대상: `source_command`가 `/task`가 아닌 task(수동 task). Worker 경로 task는 기존 `/go <id> recover`를 쓴다.
   `source_command`가 없는 기존 기록(baseline `5ccbd92`에서 추적되는 task 기록 129건 중 task-0001~0003의 3건)은 수동 task로 본다.
4. 사유: 새 메타데이터 `closed_reason`. 규칙은 `completion_evidence`와 같다(1~500자, 백틱·제어 문자 금지,
   공백 정규화). 상태 변경과 같은 원자적 쓰기로 함께 쓰고, `CLOSED`가 아닌 task에는 둘 수 없다.
   Jarvis는 사유의 내용을 판정하지 않는다.
5. 경로: Console `Close` 동작(Preview → `CLOSE TASK` Confirm). Preview는 현재 상태, 전이, 사유, "실행하지
   않으며 다시 열 수 없음" 안내를 보여 준다. Discord에는 종료 명령을 두지 않는다.
6. 보이는 곳: Task View에 `Closed` 그룹(Completed 뒤), `/report`의 상태 줄에 `CLOSED`.
   `/retro today` follow-up 대상에는 넣지 않는다.

## 5. 영향 범위 (구현 task용)

- writer: `TASK_ALLOWED_STATUSES`, `TASK_STATUS_TRANSITIONS`(`DOING → CLOSED`), `closed_reason` 검증과
  전용 쓰기 함수(Hold writer처럼 일반 전이 writer는 이 쌍을 거부).
- Console: API(preview/confirm), 화면, Task View 상태 규칙과 그룹, smoke test.
- Discord: `REPORT_STATUS_ORDER`와 그 self-check(상태 목록이 `TASK_ALLOWED_STATUSES`와 같은지), `/review-task` 안내.
  `/go`·`/retry`·`/run`은 `CLOSED`를 원래 받지 않으므로 코드 변경 없이 거부되는지 테스트로 고정한다. 현재 코드의 거부 사유:
  `/go` → `status_not_startable:CLOSED`, `/go <id> accept` → `accept_requires_failed:CLOSED`,
  `/go <id> recover` → `recover_requires_doing:CLOSED`, `/retry` → `retry_allowed_only_for:FAILED,DOING`,
  `/run` → `run_allowed_only_for:DOING`.
- 문서: task-model §2·§3·§5-1·§5-2·새 절(`closed_reason`), SOP §8(DONE이 아닌 종결이 있음을 명시), README·status-report 계약.
  task-model §11(`completion_evidence`)은 바뀌지 않는다. `closed_reason`은 그 형식 규칙을 따르되 별도 필드로 두며,
  `CLOSED` task에 `completion_evidence`가 있어도(종료 전에 기록된 경우) 그대로 둔다.
- validator: `_validate_transition_contract` 등 전이 표와 코드의 일치 검사.
- 호환: 기존 7개 상태의 task는 동작이 같아야 한다.

## 6. `/run`·`/retry` 키워드 선택 문제 (G2)

C는 "닫힌 task"의 재실행만 막는다. 2절의 위험은 **아직 DOING인** 수동 task(task-0031 등)에도 있다.
제안: `/run`·`/retry`가 수동 task(3절의 판정)를 `manual_task_not_runnable`로 거부한다.

- 확인이 필요한 점: `/run`·`/retry`가 정당하게 다루는 task가 실제로 어떤 `source_command`를 갖는지.
  등록 시점 기록에서 `source_command`가 `/task`인 task는 7건(모두 DONE)이고, `/retry`는 그 값을 이미
  거부한다. 구현 task는 먼저 두 명령의 정당한 대상을 기록과 테스트에서 확정하고, 대상이 남지 않으면
  두 명령을 수동 task에 대해 막는 것만으로 충분한지 판단한다.
- 이 차단은 C와 독립적으로 먼저 구현할 수 있다. 위험이 지금도 있으므로 C보다 먼저 하는 것을 권한다.

## 7. 테스트 계획 (구현 task)

- writer: `DOING → CLOSED`만 허용, `closed_reason` 필수·형식, 다른 상태에서 거부, Worker 경로 task 거부.
- Console smoke: Close Preview/Confirm, 잘못된 문구·만료 토큰 거부, Task View `Closed` 그룹.
- Discord self-check: `/go`·`/retry`·`/run`이 `CLOSED`를 거부, `/report` 상태 줄과 합계, `/run`·`/retry`의
  수동 task 거부(6절).
- Worker smoke, SOP validator, `git diff --check`.

## 8. 위험

- 상태 어휘 확장은 상태를 나열하는 모든 곳(코드·문서·validator)에 영향을 준다. 빠진 곳은 self-check와
  validator가 잡도록 구현 task에서 검사를 함께 넣는다.
- `CLOSED`는 되돌릴 수 없게 설계했다. 잘못 닫으면 새 task로 다시 시작해야 한다. Preview에 이 점을 분명히 보인다.
- 6절의 차단은 정당한 `/run`·`/retry` 사용을 막을 수 있다. 대상 확정 전에는 구현하지 않는다.

## 9. 적용 원칙

- task-0175·task-0031을 새 경로로 닫을지는 구현 뒤 Owner가 건별로 정한다. 이 설계와 구현 task는 어떤 task도
  자동으로 닫지 않는다.
