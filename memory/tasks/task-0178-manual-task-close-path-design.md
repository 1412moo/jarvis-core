# task-0178-manual-task-close-path-design

- id: `task-0178-manual-task-close-path-design`
- title: `수동 SOP task 공식 종료 경로 설계`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-21 05:31 UTC`
- updated_at: `2026-10-21 06:20 UTC`
- summary: `Claude Code 세션 등에서 Owner 결정으로 만든 수동 SOP task를 공식으로 종료하는 경로를 설계한다. 지금은 DOING인 수동 task를 닫을 방법이 없어 task-0175·task-0031이 DOING으로 남아 있고, FAILED로 바꾸면 Discord /go가 그 task를 Worker로 실행할 수 있다. 이 task는 설계 문서까지만 만들고 코드·SOP·상태는 바꾸지 않는다. 구현은 설계 승인 뒤 별도 task로 한다.`
- source_command: `Owner 지시: 수동 task 종료 경로 설계 task 등록 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `5ccbd92b2c16abe1dc478c43b722ee66825e8432` (등록 시점 main HEAD = origin/main). Start 때 다시 확인한다 |
| 등록 방식 | 이 기록을 `TODO`로 작업 트리에만 만들었다(커밋·stage 없음). Start 승인 뒤 candidate에 포함한다 |
| budget | `retry_budget=2`, `retry_count=1`, `repair_budget=2`, `repair_count=2` (SOP §5 기본값 1에서 Owner가 이 task에 한해 둘 다 2로 증액. retry 1은 Reviewer 1 재검토, repair 1·2는 아래 "Repair 1"·"Repair 2") |

## Owner 결정 (원문)

```text
수동 task 종료 경로 설계 task 등록해
```

## 문제 (등록 시점 코드 기준)

- 상태 writer(`orchestrator/discord-intake/task_file_writer.py`의 `TASK_STATUS_TRANSITIONS`)는 `DOING → FAILED`를 허용하지만, 수동 task에 그 전이를 거는 진입점이 없다. Console에는 Start·Complete·Hold·Resume·Evidence만 있고, Discord `/go <id> recover`는 `source_command`가 `/task`인 Worker 경로 task만 받는다.
- `DOING → DONE`(Console Complete)은 SOP §8 완료 조건(같은 candidate의 Reviewer PASS와 QA PASS)을 채운 task에만 맞다. 중단된 task-0175처럼 그 조건을 채울 수 없는 task는 DOING으로 남는다(task-0031도 DOING).
- FAILED가 된 task는 Discord `/go <id>`가 `source_command`를 보지 않고 `FAILED → TODO → DOING`으로 바꾼 뒤 Worker 작업을 시작한다(기본 작업 종류 Studyroom). 수동 task를 FAILED로 닫으면 이 경로로 다시 실행될 수 있다.
- `/retry`와 `/run`은 수동 task를 막지 않고, 실행 대상 여부를 title·summary의 키워드(`script`, `run`, `demo`, `test`, `검증`)로 정한다. task-0031은 키워드가 걸려 DOING 상태에서도 `/run` 대상일 수 있다(실제 효과는 미확인).

## 범위 (Start 승인으로 확정)

| 구분 | 경로 |
| --- | --- |
| owned | `docs/task-0178-manual-task-close-design.md`, `memory/tasks/task-0178-manual-task-close-path-design.md` |
| deny | `jarvis.bat`, 모든 코드(`apps/`, `adapters/`, `orchestrator/`, `scripts/`), SOP·task-model·AGENTS.md·agent 정의, 다른 task 기록(task-0031·0175 포함), master-plan(DONE 뒤 별도 기록 커밋 제외), 보호 worktree |

이 task는 설계 문서만 만든다. 어떤 task의 상태도 바꾸지 않는다.

## 설계 문서가 다룰 것

1. 종료 방식 비교와 추천: (A) 기존 `FAILED` 재사용 + Console 종료 동작, (B) A + Owner 사유 필드 + 재실행 차단, (C) 새 종결 상태(예: `CLOSED`), (D) 현상 유지. 등록 전 조사에서는 B를 우선 후보로 보았다.
2. 대상 판정: 어떤 task를 "수동 task"로 볼지(`source_command`가 `/task`가 아닌 task 등)와 Worker 경로 task와의 구분.
3. Owner 사유 기록: 필드 이름·길이·문자 규칙, 상태와 같은 원자적 쓰기, Console Preview/Confirm 문구(예: `CLOSE TASK`).
4. 재실행 차단: 종료된 task를 `/go`·`/retry`·`/run`이 거부하는 조건과 거부 사유 문자열, 다시 열려면 필요한 Owner 경로.
5. 수동 task의 `/run`·`/retry` 키워드 선택 문제를 이 설계에 포함할지 분리할지.
6. 영향 범위: writer, Console(API·화면), Discord(`/go`·`/retry`·`/run`·`/report`), task-model §5·§11, SOP §8, validator, 기존 task 호환(필드가 없는 기존 FAILED task는 동작이 같아야 함).
7. 구현 task의 테스트 계획(Console smoke, Discord self-check, writer 테스트, Worker smoke)과 위험.
8. task-0175·task-0031을 새 경로로 닫을지는 구현 뒤 Owner가 건별로 정한다는 원칙.

## 실행 계획

1. Owner Start 승인 → Console Start(Preview 확인 뒤 `START TASK`).
2. 읽기 전용 조사로 위 1~8을 확인하고 `docs/task-0178-manual-task-close-design.md` 작성, 이 기록에 Manager 요약(출처 칸, 짧게).
3. 사전 점검 → self-review 1회 → candidate(설계 문서 + 이 기록).
4. Reviewer → 같은 candidate로 QA(문서 전용: 링크·경로가 실제로 있는지, 코드 무변경, `check_task_record`, validator, `git diff --check`).
5. Evidence·Complete, DONE checkpoint, master-plan 기록. push는 별도 승인.

## Owner 결정 필요 (Start 전)

| # | 결정 | 권고 |
| --- | --- | --- |
| G1 | 이 task를 설계 문서까지만 할지(구현은 별도 task) | 설계까지만 |
| G2 | 수동 task의 `/run`·`/retry` 키워드 선택 문제를 이 설계에 포함할지 | 포함(같은 재실행 차단 장치로 다룰 수 있음) |
| G3 | Hold·Evidence·Complete처럼 Console Preview/Confirm을 Manager가 진행할지 | Manager가 진행하고 보고(task-0176 repair 1과 같게) |

## Owner 결정: G1~G3와 Start (원문)

```text
[Manager 권고]
G1: 설계 문서까지만 하고 구현은 별도 task로 한다.
G2: 수동 task의 /run·/retry 키워드 선택 문제를 이 설계에 포함한다.
G3: Console Preview/Confirm(Start·Evidence·Complete)은 Manager가 진행하고 보고한다.

[Owner 답]
권고대로 승인, Start
```

## Start

Console Start Preview(TODO → DOING, `no_execution: true`)를 확인하고 `START TASK`로 Confirm했다. receipt: previous `TODO`, current `DOING`, updated_at `2026-10-21 05:33 UTC`. 기록에서 바뀐 것은 status 줄뿐이다. HEAD = baseline `5ccbd92`, tracked 변경 없음. Console은 Start 뒤 껐다.

## 구현

- `docs/task-0178-manual-task-close-design.md`: 문제, 현재 위험(`/go`의 FAILED 재실행, `/run`·`/retry`의 키워드 실행과 자동 DONE/FAILED 기록, task-0031 해당), 대안 A~D 비교, 추천안 C(새 종결 상태 `CLOSED` + `closed_reason`, `DOING → CLOSED`만, Console `CLOSE TASK`), 영향 범위, `/run`·`/retry` 수동 task 차단 제안(G2), 테스트 계획, 위험, 적용 원칙.
- 추천이 등록 때 적은 우선 후보(B)에서 C로 바뀌었다. 조사 결과 B는 재실행 방지를 여러 명령의 차단 코드에 의존하지만, C는 실행 명령들이 원래 받지 않는 상태를 써서 구조적으로 막기 때문이다(문서 3절).
- 2절의 `/run task-0031` 위험은 코드를 읽어 확인했고 실행하지 않았다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "수동 task 종료 경로 설계 task 등록해" | 이 task를 TODO로 등록했다("문제"·"범위"·"설계 문서가 다룰 것") |
| B1 | Owner 결정: G1~G3와 Start (원문) | "[Manager 권고]" / "G1: 설계 문서까지만 하고 구현은 별도 task로 한다." | G1: 결과물은 설계 문서 `docs/task-0178-manual-task-close-design.md`와 이 기록뿐이고 코드·SOP·task 상태는 바꾸지 않았다. 구현은 별도 task다 |
| B2 | Owner 결정: G1~G3와 Start (원문) | "G2: 수동 task의 /run·/retry 키워드 선택 문제를 이 설계에 포함한다." | G2: 설계 문서 2절(현재 위험)과 6절(`/run`·`/retry` 수동 task 차단 제안)에 포함했다 |
| B3 | Owner 결정: G1~G3와 Start (원문) | "G3: Console Preview/Confirm(Start·Evidence·Complete)은 Manager가 진행하고 보고한다." | G3: Console Start는 Manager가 Preview 확인 뒤 Confirm했고, Evidence·Complete도 Manager가 진행하고 보고한다 |
| B4 | Owner 결정: G1~G3와 Start (원문) | "[Owner 답]" / "권고대로 승인, Start" | Owner 답으로 권고 G1~G3을 승인하고 Start를 지시했다 |
| C1 | Owner 결정: Repair 2 (원문) | "repair와 retry 예산을 각각 1회 추가한다." / "retry_count=1로 수정하고 새 candidate를 만든다." | repair·retry 예산을 각 1회 늘려 2로 하고, budget 행을 `retry_count=1`로 고친 새 candidate를 만들었다("Repair 2") |
| C2 | Owner 결정: Repair 2 (원문) | "Reviewer가 PASS하면 QA와 Evidence·Complete까지 진행한다." | 새 candidate에서 Reviewer PASS면 QA, Evidence, Complete까지 Manager가 진행한다 |
| C3 | Owner 결정: Repair 2 (원문) | "새 candidate에서도 Reviewer가 형식 이탈을 하면 추가 retry 1회만 사용한다." / "유효한 지적이 다시 나오면 무조건 고치지 말고, 그 지적을 보고한 뒤 Owner가 결정한다." | 새 candidate의 Reviewer가 형식 이탈이면 retry 1회만 쓰고, 유효한 지적이면 고치지 않고 보고해 Owner가 정한다 |
| C4 | Owner 결정: Repair 2 (원문) | "push는 하지 않는다." | push하지 않는다 |

## 사전 점검과 Self-review

- 사전 점검 1회차(`check_task_record.py --baseline 5ccbd92`): PASS, violations 0, staged 2, 인용 누락 0.
- self-review 1회: 지적 3건(minor). candidate 전이라 repair가 아니다. 처리: (1) `source_command` 없는 기록 수의 기준을 "baseline `5ccbd92`에서 추적되는 129건 중 task-0001~0003의 3건"으로 밝혔다(다시 세어 3건 확인). (2) 5절에 `/go`·`accept`·`recover`·`/retry`·`/run`이 `CLOSED`에 돌려줄 현재 거부 사유 문자열을 적었다. (3) 5절에 task-model §11은 바뀌지 않는 이유를 적었다.
- updated_at은 이 편집 시각 2026-10-21 05:37 UTC다(편집 스크립트가 UTC 시계를 읽어 넣음).

## Candidate 1과 Reviewer 1

- candidate `9cf22bf607445dec2bc3fd82923bb29447359f45`(parent `5ccbd92`).
- Reviewer 1 첫 검토: 허용 명령에 `git -C`를 붙인 `self_deviations` 1건으로 무효. SOP §5에 따라 같은 candidate를 1회 재검토했다(`retry_count=1`).
- 재검토: FINDINGS minor 1, `self_deviations` 없음. 설계 문서 6절의 "수동 task(3절의 판정)"이 실제 판정이 있는 4절 3항이 아니라 대안 비교 표(3절)를 가리킨다는 지적이다. 사실이다.

## Repair 1

- 설계 문서 6절의 "3절의 판정"을 "4절 3항의 판정"으로 고쳤다. 다른 내용은 바꾸지 않았다.
- 기준선 budget 행을 `repair_count=1`로 고쳤다(예산 1/1 소진). 새 candidate에서 유효한 지적이 나오면 고치지 않고 Owner에게 보고한다.
- updated_at은 이 repair 편집 시각 2026-10-21 05:43 UTC다(편집 스크립트가 UTC 시계를 읽어 넣음).

## Candidate 2와 Reviewer 2

- candidate `e92d91f7a3627fc516e2bf09c8c3cf424efb27a8`(parent `9cf22bf`).
- Reviewer 2: 허용되지 않은 grep 형식(정규식 alternation, `-c`) `self_deviations` 2건으로 무효. 그 보고는 기준선 budget 행이 `retry_count=0`으로 남아 Reviewer 1 재검토(retry 1회)와 어긋난다고 적었다(사실). retry·repair 예산이 소진돼 Owner에게 보고했다.

## Owner 결정: Repair 2 (원문)

```text
repair와 retry 예산을 각각 1회 추가한다.

retry_count=1로 수정하고 새 candidate를 만든다.

Reviewer가 PASS하면 QA와 Evidence·Complete까지 진행한다.

새 candidate에서도 Reviewer가 형식 이탈을 하면 추가 retry 1회만 사용한다.

유효한 지적이 다시 나오면 무조건 고치지 말고, 그 지적을 보고한 뒤 Owner가 결정한다.

push는 하지 않는다.
```

## Repair 2

- 기준선 budget 행을 `retry_count=1`로 고치고, 이 결정에 따라 `retry_budget=2`, `repair_budget=2`, `repair_count=2`로 적었다. 설계 문서는 바꾸지 않았다.
- 새 candidate에서 Reviewer가 형식 이탈을 하면 retry 1회만 쓰고, 유효한 지적이 나오면 고치지 않고 Owner에게 보고한다.
- updated_at은 이 repair 편집 시각 2026-10-21 06:20 UTC다(편집 스크립트가 UTC 시계를 읽어 넣음).
