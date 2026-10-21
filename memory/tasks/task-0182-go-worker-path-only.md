# task-0182-go-worker-path-only

- id: `task-0182-go-worker-path-only`
- title: `Discord /go를 Worker 경로 task로 한정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-21 14:37 UTC`
- updated_at: `2026-10-21 15:10 UTC`
- summary: `Discord /go가 /work로 만든 Worker 경로 task(source_command가 /task)만 시작하게 해, 수동 task가 Worker로 실행되는 길을 막는다. 지금은 /go가 source_command를 보지 않아 수동 TODO·FAILED task도 Worker로 실행되고, 그 task는 실행 중에도 Console Close가 받아들여 SOP §8 문단과 어긋난다. 상태별 기존 거부·안내, accept·recover, Close 코드는 바꾸지 않는다.`
- completion_evidence: `candidate 30e55d755ce9a23c1c1c216c1a6d645c2c7e8a49 (baseline b329f8a). Reviewer PASS, findings 0, self_deviations 0. QA PASS 27/27 in fresh worktrees: 4 scope files; manual TODO, FAILED, resume and accept now refused with go_requires_worker_path and no lock or write; recover, DOING, DONE and resume-on-TODO answers same as baseline; self-check 108 to 109; Worker smoke 494/0 so Worker-path /go still runs; Console, NL smoke, validator, check_task_record PASS. No push.`
- source_command: `Owner 지시: /go와 Close 틈 후속 task 진행 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `b329f8a468dfeed5319e87b54778c3906f8befab` (등록 시점 main HEAD) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |
| 근거 | task-0181 확인 중 발견, task-0178 설계 2절(/go가 수동 FAILED task를 다시 실행할 수 있는 위험) |

## Owner 결정 (원문)

```text
[Manager 제안]
확인 중 발견한 틈 (task-0180 코드, 이번 범위 밖)
- /go는 source_command를 보지 않으므로, 수동으로 만든 TODO task에 /go를 보내면 Worker가 실행됩니다. 그 task는 source_command가 /task가 아니어서, Worker가 도는 동안 DOING 상태에서 Console Close가 받아들여집니다.
- 이 경우 SOP의 "Worker 파이프라인 task는 Close 대상이 아니다"를 코드가 막지 못합니다.
- 고치는 방법은 둘입니다. /go가 /task로 만든 task만 받게 하거나, Close가 실행 기록이 있는 task를 거부하게 하면 됩니다.
1. 위 틈을 고치는 작은 후속 task. 진행할지 정해 주시면 이 세션에서 등록하고 진행하겠습니다.

[Owner 답]
진행해.
```

## 방법 선택 (Manager)

제안한 두 방법 중 /go 쪽을 고친다. Close 쪽(실행 기록이 있는 task 거부)은 Worker가 기록을 쓰기 전의 실행 중 상태를 막지 못하고, /go 쪽은 수동 task가 Worker로 실행되는 일 자체를 없애 task-0178 설계 2절의 /go 위험도 함께 닫는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`(`_run_go`의 시작 직전 검사, 오류 안내, self-check), `orchestrator/worker/run_smoke_tests.py`(필요할 때 fixture·검사), `adapters/discord/README.md`(/go 절), `docs/task-model.md`(§5-2 /go 행 표기), `memory/tasks/task-0182-go-worker-path-only.md` |
| deny | `jarvis.bat`, writer·Console·Worker 실행 코드(`claude_worker.py` 등), SOP·AGENTS·agent 정의, 다른 task 기록, 보호 worktree |

## 계획

1. `_run_go`: 상태 검사(TODO·FAILED만, resume은 FAILED만)를 지난 뒤, Worker 잠금을 잡기 전에 `source_command`가 `/task`가 아니면 `go_requires_worker_path`로 거부한다. accept도 상태 검사 뒤 같은 규칙을 따른다. 파일은 바꾸지 않는다. DOING·CLOSED 등 기존 거부·안내와 recover는 그대로다.
2. 오류 안내 문구와 self-check(수동 TODO·FAILED·resume 거부와 파일 무변경, Worker 경로 TODO는 그대로 시작 가능), 기존 fixture가 Worker 경로를 뜻하면 `source_command`를 맞춘다.
3. 문서: Discord README /go 절, task-model §5-2의 /go 행에 /work로 만든 task만이라고 적는다.
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-21 14:37 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `adapters/discord/bot_minimal.py`: `_run_go`에서 상태 검사(`status_not_startable`, `resume_requires_failed`)를 지난 뒤, Worker 잠금을 잡기 전에 `source_command`가 `/task`가 아니면 `go_requires_worker_path`로 거부한다. `/go <id> accept`도 FAILED 검사 뒤, 기록을 읽기 전에 같은 규칙으로 거부한다(self-review 지적: accept는 이 검사보다 앞에서 분기해 예전에 Worker 기록이 남은 수동 FAILED task를 Worker job에 넣을 수 있었다). 그 앞의 DOING 안내(`stalled_doing`, `doing_without_execution_record` 등), recover(원래 Worker 경로만 받음), CLOSED 거부는 그대로다. 거부 응답 문구를 더했다. self-check: 잠금 검사 fixture의 TODO task를 `/work` 경로(`source_command` `/task`)로 맞추고, 수동 TODO·FAILED, FAILED resume, FAILED accept가 거부되며 잠금과 파일이 그대로인지 보는 `go_refuses_manual_task_before_any_lock_or_write`를 더했다. `/task` TODO fixture는 새 검사를 지나 잠금 단계까지 가서 `worker_busy`를 받으며(기존 잠금 검사), Worker 경로 task의 실제 시작은 Worker smoke가 확인한다.
- `adapters/discord/README.md` /go 절, `docs/task-model.md` §5-2의 /go 두 행: `/work`로 만든 task만이라고 적었다.
- `orchestrator/worker/run_smoke_tests.py`는 바꿀 필요가 없었다(모든 /go 시작 검사가 `/work`로 만든 task를 쓴다).

## Implementer 검증 (작업 트리)

- Discord self-check suite: ok, checks 109(이전 108에 1개). Worker smoke total=494 failed=0. Console smoke 통과, discord-nl-intent smoke 통과, SOP validator PASS.
- 사전 점검(`check_task_record`, baseline `b329f8a`): status=PASS, violations 0, 경고 1건(`orchestrator/worker/run_smoke_tests.py`가 바뀌지 않음, 구현 절대로 변경 불필요).

## Self-review

candidate 전 1회. minor 3건을 candidate 전에 고쳤다: accept에도 같은 검사를 넣고 A1을 실제 경로에 맞게 고쳤으며, Worker 경로 TODO가 새 검사를 지나는 것을 어느 검사가 보는지와 사전 점검 결과를 적었다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안]" / "확인 중 발견한 틈 (task-0180 코드, 이번 범위 밖)" / "- /go는 source_command를 보지 않으므로, 수동으로 만든 TODO task에 /go를 보내면 Worker가 실행됩니다. 그 task는 source_command가 /task가 아니어서, Worker가 도는 동안 DOING 상태에서 Console Close가 받아들여집니다." / "- 이 경우 SOP의 "Worker 파이프라인 task는 Close 대상이 아니다"를 코드가 막지 못합니다." | /go의 시작 경로(TODO, FAILED 재시도, resume)와 accept가 모두 수동 task를 거부하므로 수동 task는 Worker로 실행되지 않는다. recover는 원래 Worker 경로만 받고 재실행하지 않는다. 그래서 Close가 실행 중인 Worker task를 만나는 경로가 없다 |
| A2 | Owner 결정 (원문) | "- 고치는 방법은 둘입니다. /go가 /task로 만든 task만 받게 하거나, Close가 실행 기록이 있는 task를 거부하게 하면 됩니다." | 첫째 방법을 골랐다(방법 선택 절). Close 코드는 바꾸지 않았다 |
| A3 | Owner 결정 (원문) | "1. 위 틈을 고치는 작은 후속 task. 진행할지 정해 주시면 이 세션에서 등록하고 진행하겠습니다." / "[Owner 답]" / "진행해." | 이 task를 등록하고 Console로 Start했다. push는 하지 않는다(별도 승인) |
