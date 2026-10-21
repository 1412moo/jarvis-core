# task-0179-retire-run-retry

- id: `task-0179-retire-run-retry`
- title: `Discord /run·/retry 폐기`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-21 07:07 UTC`
- updated_at: `2026-10-21 09:43 UTC`
- summary: `Discord /run과 /retry를 폐기한다. 두 명령은 키워드로 고른 task에 허용 목록의 smoke 테스트를 실행하고 DONE/FAILED를 Owner 검토 없이 기록할 수 있었고(task-0178 설계 2절, task-0031 해당), 수동 task를 막으면 정당한 대상이 남지 않는다. 이제 두 명령은 아무것도 실행하거나 바꾸지 않고 /approve·/go·Console을 쓰라는 안내만 돌려준다. 실행 흐름은 /approve가 계속 쓴다. task-0167의 수동 task /retry 유지 결정을 Owner가 뒤집었다.`
- source_command: `Owner 결정: /run·/retry 폐기 A안 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `61bea07fb1a3bd0980e0ee6fa46c437bdc5c83d1` (등록 시점 main HEAD) |
| budget | `retry_budget=1`, `retry_count=1`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, 사용 내역은 Repair 절) |

## Owner 결정 (원문)

```text
[Manager 선택지 A]
A. /run·/retry 공식 폐기: 두 명령이 모든 task에 "폐기된 명령, /go나 Console을 쓰라"는 안내만 돌려주고 아무것도 실행하지 않습니다. 실행 흐름 자체는 /approve가 계속 쓰므로 그 테스트는 /approve 쪽으로 옮깁니다.

[Owner 답 1]
A안으로 가는 방향에 동의하지만, 폐기 결정 전에 /run·/retry가 현재 코드와 Discord 명령 등록에서 어떤 역할을 하는지 마지막으로 확인하는 게 좋겠어.

[Manager 확인 결과 요약]
두 명령은 텍스트 명령 라우터와 Owner 전용 명령 목록에만 있고, 자연어 경로가 만들지 않으며 다른 코드가 부르지 않는다. 실행 흐름은 /approve가 계속 쓴다. 폐기하면 라우터·/help·안내 문구·결과 형식, self-check 약 12개, Worker smoke 2개, README와 실행 전이 정책 문서를 바꾼다. task-0167의 수동 task /retry 유지 결정을 뒤집는다.

[Owner 답 2]
A안으로 진행해
```

## Owner 결정 2: task-model 범위 (원문)

```text
[Manager 선택지]
1 (권장): task-model §5-2 두 줄 수정을 이번 범위에 포함합니다. 기준 문서가 코드와 계속 맞게 유지됩니다.
2: task-model 수정을 빼고, 어긋남은 따로 기록한 뒤 별도 task로 고칩니다.

[Owner 답]
1로 진행
```

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`, `orchestrator/worker/run_smoke_tests.py`, `orchestrator/discord-nl-intent/run_smoke_tests.py`, `adapters/discord/README.md`, `docs/execution-status-transition-policy.md`, `docs/task-model.md`(§5-2 전이 경로 표의 /run·/retry 표기만), `memory/tasks/task-0179-retire-run-retry.md` |
| deny | `jarvis.bat`, writer·Console·Worker 실행 코드(`orchestrator/worker/claude_worker.py` 등), 다른 task 기록, SOP·agent 정의, task-model의 §5-2 밖, 보호 worktree |

## 계획

1. `/run`·`/retry`를 라우터에서 폐기 응답(`command_retired`)으로 바꾸고, 두 실행 함수와 그 결과 형식·허용 상태 상수를 지운다. 폐기 응답은 task 파일을 읽지도 바꾸지도 않는다. Owner 전용 명령 목록에는 남겨 둔다(권한 검사 순서 유지).
2. `/help`·지원 명령 안내를 폐기 표시로 바꾼다.
3. self-check: `/run`·`/retry` 실행·상태 테스트를 폐기 테스트(어떤 상태의 task에도 파일이 그대로, 실행 없음, 안내 문구)로 바꾼다. 실행 흐름의 성공·미실행·실패는 기존 `/approve` 테스트가 다룬다. task-0167의 `/retry` 회귀 테스트도 폐기 테스트로 바꾼다.
4. Worker smoke의 `/retry` 검사 2개를 폐기 응답과 파일 무변경으로 바꾼다. discord-nl-intent smoke 주석을 고친다.
5. README와 실행 전이 정책 문서에서 두 명령을 폐기로 적는다.
6. 사전 점검 → self-review → candidate → Reviewer → QA(Discord self-check, Worker smoke, discord-nl-intent smoke, Console smoke, validator) → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-21 07:07 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `adapters/discord/bot_minimal.py`: `_run_retry`·`_run_run`과 `RETRY_ALLOWED_STATUSES`·`RUN_ALLOWED_STATUSES`를 지우고 `RETIRED_COMMANDS`와 `_run_retired`(task 파일을 읽지 않고 `command_retired` 반환)로 바꿨다. 라우터, `/help` 줄(폐기 안내), 결과 형식(`retry_result`·`retry_not_allowed`·`run_result`·`run_not_allowed` 삭제, `command_retired` 추가), 지원 명령 안내 문구를 고쳤다. Owner 전용 명령 목록에는 두 명령을 남겼다(주석에 이유를 적음). 실행 흐름·알림 상수·argparse 설명의 낡은 `/run`·`/retry` 언급도 고쳤다. self-check: `/run`·`/retry`의 실행·상태 검사 15개와 task-0167의 `/retry` 회귀 검사 1개(모두 16개)를 빼고, 그중 `/approve`가 다루지 않던 두 가지(실행 메타데이터 저장, 실패 실행의 error·message 표시)를 `/approve` 성공·실패 검사 옆에 `approve_execution_metadata_persisted`·`status_execution_error_metadata_visible`로 옮겼다. 폐기 검사 2개(DOING·FAILED·NEEDS_APPROVAL fixture에 두 명령을 보내도 파일 그대로, 인자 없는 형식도 폐기 응답, `/runx`·`/retryfoo` 같은 다른 단어는 폐기 응답이 아님, 안내 문구)를 더했다. 라우터는 첫 단어가 정확히 `/run`·`/retry`일 때만 폐기 응답을 돌려준다. 알림 검사의 가짜 결과 목록과 `/help` 검사를 새 동작에 맞췄다.
- `orchestrator/worker/run_smoke_tests.py`: `/retry` 검사 2개를 Worker 경로·수동 task 모두 폐기 응답과 파일 무변경으로 바꿨다.
- `orchestrator/discord-nl-intent/run_smoke_tests.py`: 주석만 고쳤다.
- `adapters/discord/README.md`, `docs/execution-status-transition-policy.md`, `docs/task-model.md` §5-2: 두 명령을 폐기로 적고 실행 경로를 `/approve`·`/go`로 줄였다. task-model은 처음 범위에서 뺐으나 §5-2 표가 코드와 어긋나게 되어 Owner 결정 2에 따라 그 표기만 범위에 넣었다.

## Implementer 검증 (작업 트리)

- Discord self-check suite: ok, checks 104(이전 116에서 16개를 빼고 옮긴 검사 2개와 폐기 검사 2개를 더함, 모두 통과).
- Worker smoke: total=494 failed=0(`/retry` 폐기 검사 2개 포함). discord-nl-intent smoke: 35건 모두 통과. Console smoke 통과. SOP validator PASS. `git diff --check` 통과.

## Repair

- candidate `41dbb16ec27e8900748f118660b5627191ebbbc2`: 첫 Reviewer 호출은 Manager가 승인 원문 표시 줄을 빠뜨려 BLOCKED였다(source 변경 없는 retry 1회, `retry_count=1`). 재호출 Reviewer는 minor 2건을 냈고 자기 형식 이탈이 있어 검토 자체는 무효다.
- repair 1(`repair_count=1`): 두 지적을 고쳤다. `_run_notification_publisher` docstring의 낡은 `/run`·`/retry` 언급을 실행 흐름으로 바꿨고, README의 선필터 안내 인용을 코드 응답(`/work`·`/go` 포함)과 같게 맞췄다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 선택지 A]" / "/run·/retry 공식 폐기: 두 명령이 모든 task에 "폐기된 명령, /go나 Console을 쓰라"는 안내만 돌려주고 아무것도 실행하지 않습니다." / "실행 흐름 자체는 /approve가 계속 쓰므로 그 테스트는 /approve 쪽으로 옮깁니다." | A안(두 명령 공식 폐기)이 Manager가 제시한 선택지다. 두 명령은 어떤 task에도 아무것도 실행하거나 바꾸지 않고 안내만 돌려준다. `/approve`에 이미 있던 성공·미실행·실패 전이 검사는 그대로 두고, `/approve`가 다루지 않던 실행 메타데이터 저장과 실패 표시 검사 2개를 `/approve` 쪽으로 옮겼다 |
| A2 | Owner 결정 (원문) | "[Owner 답 1]" / "A안으로 가는 방향에 동의하지만, 폐기 결정 전에 /run·/retry가 현재 코드와 Discord 명령 등록에서 어떤 역할을 하는지 마지막으로 확인하는 게 좋겠어." | Owner 답 1에 따라 폐기 전에 코드와 Discord 등록에서 두 명령의 역할을 읽기 전용으로 확인했다(Manager 확인 결과 요약) |
| A3 | Owner 결정 (원문) | "[Manager 확인 결과 요약]" / "두 명령은 텍스트 명령 라우터와 Owner 전용 명령 목록에만 있고, 자연어 경로가 만들지 않으며 다른 코드가 부르지 않는다." / "실행 흐름은 /approve가 계속 쓴다." / "폐기하면 라우터·/help·안내 문구·결과 형식, self-check 약 12개, Worker smoke 2개, README와 실행 전이 정책 문서를 바꾼다." / "task-0167의 수동 task /retry 유지 결정을 뒤집는다." | 확인 결과: 텍스트 라우터와 Owner 전용 명령 목록에만 있고, 자연어 경로·다른 코드가 쓰지 않으며, 실행 흐름은 `/approve`가 쓴다. 목록의 곳을 모두 바꿨다. 목록과 다른 점: self-check는 약 12개가 아니라 16개를 빼고 4개를 더했고(구현 절), 목록에 없던 `docs/task-model.md` §5-2 두 줄도 바꿨다(A5). task-0167의 수동 task `/retry` 유지 결정은 이 결정으로 뒤집혔다 |
| A4 | Owner 결정 (원문) | "[Owner 답 2]" / "A안으로 진행해" | Owner가 A안으로 진행을 지시했다. 이 task의 Start를 Console로 했다 |
| A5 | Owner 결정 2: task-model 범위 (원문) | "[Manager 선택지]" / "1 (권장): task-model §5-2 두 줄 수정을 이번 범위에 포함합니다." / "기준 문서가 코드와 계속 맞게 유지됩니다." / "2: task-model 수정을 빼고, 어긋남은 따로 기록한 뒤 별도 task로 고칩니다." / "[Owner 답]" / "1로 진행" | Owner가 선택지 2(별도 task)가 아닌 1을 골랐다. `docs/task-model.md`는 §5-2 전이 경로 표의 `/run`·`/retry` 표기 두 줄만 바꿨고, 범위 표의 owned에 그 한정으로 넣었다 |
