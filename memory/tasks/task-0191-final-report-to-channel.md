# task-0191-final-report-to-channel

- id: `task-0191-final-report-to-channel`
- title: `Worker 최종 보고는 채널로`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-24 06:17 UTC`
- updated_at: `2026-10-24 06:26 UTC`
- summary: `Discord /go Worker 실행의 최종 결과 보고(완료, 실패, Owner 판단 필요)를 작업 스레드가 아니라 채널에 보낸다. /go가 스레드 안에서 왔으면 그 스레드의 상위 채널이다. 채널 전송이 실패하면 작업 스레드로 보낸다. 단계 진행 줄과 팀장 계획은 지금처럼 스레드에 남는다. 판정·반영 로직은 바꾸지 않는다.`
- source_command: `Owner 지시: 최종 보고를 채널로 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `c642bde71010309a8f2b936a67afd2857412cb7d` (등록 시점 main HEAD, task-0189까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Owner 지시] (Discord 실행 기록 첨부: task-0190-research-council-readme-1의 진행 줄과 완료 보고가 모두 작업 스레드에 올라옴)
진행은 잘되는거같은데 하나 수정해야할게 보이네. 디스코드에 챗보내면 이채널에 보고한다고 하는데 새로 만든 쓰레드에서 작업하고 그 쓰레드에 보고하는데 마지막에 보고하는건 채널에 해야하는게 맞는거같아
```

## 설계

1. `adapters/discord/bot_minimal.py`에 `_result_channel(message)`를 더한다. `/go` 메시지의 채널이 스레드면 그 상위 채널, 아니면 그 채널이다. 상위 채널을 알 수 없으면 메시지의 채널을 쓴다.
2. `/go` 백그라운드 보고(`_report_worker`)의 최종 결과 전송만 바꾼다: 먼저 `_result_channel(message)`, 실패하면 작업 스레드. 결과가 성공이든 실패든 Owner 판단 필요든 같은 경로다. 보고 실패는 지금처럼 판정과 기록을 바꾸지 않는다.
3. 단계 진행 줄, 팀장 계획(`/work`의 팀장 결과), `/go` 직후의 승인 응답은 바꾸지 않는다. 승인 응답의 "끝나면 이 채널에 보고합니다"는 `/go`를 채널에서 보냈을 때 사실과 맞는다. `/go`를 스레드 안에서 보내면 승인 응답은 그 스레드에 달리고 결과는 상위 채널로 간다. 문구 변경은 이번 범위 밖이다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`(새 `_result_channel`, `_report_worker`의 최종 결과 전송 한 줄, 그 위의 task-0183 주석 한 줄만), `orchestrator/worker/run_smoke_tests.py`(스레드 검사 옆), `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1의 Discord 알림 문단), `adapters/discord/README.md`(작업 스레드 설명과 4항), `memory/tasks/task-0191-final-report-to-channel.md` |
| deny | `jarvis.bat`, `apps/`, `orchestrator/worker/claude_worker.py`, 팀장 코드, 판정·repair·QA·반영 로직, writer·Console, AGENTS·agent 정의, validator, 다른 task 기록, 외부 API·credential, 보호 worktree |

## 계획

1. 헬퍼와 최종 결과 전송 변경.
2. 검사: 채널의 메시지는 그 채널, 스레드의 메시지는 상위 채널, 상위 채널을 못 읽으면 그 스레드, 채널 전송 실패 시 작업 스레드로.
3. 문서: SOP §10.1 알림 문단, Discord README.
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push와 봇 재시작은 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-24 06:17 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다. 등록 시점 main에는 봇이 task-0190에서 만든 커밋 2개(`ac0ed5e`, `c642bde`)가 push 전으로 있었고, baseline은 그 위다.

## 구현

- `adapters/discord/bot_minimal.py`: `_result_channel(message)`를 더했다. 메시지 채널이 discord 스레드면 상위 채널(`parent`), 상위 채널이 없거나 읽다 오류가 나면 그 스레드, 스레드가 아니면 그 채널을 돌려준다. `/go` 백그라운드 보고의 최종 결과 전송 한 줄을 `_send_safely(_result_channel(message), channel, ...)`로 바꿔, 채널 먼저 보내고 실패하면 작업 스레드로 보낸다. 진행 줄, 팀장 결과, 승인 응답은 바꾸지 않았다. 바로 위의 task-0183 주석(진행 줄과 결과가 스레드로 간다)은 진행 줄만 스레드로 간다고 고쳤다.
- `orchestrator/worker/run_smoke_tests.py`: 스레드 검사 옆에 검사 5개를 더했다. 채널 메시지는 그 채널, 스레드 메시지는 상위 채널, 상위 채널이 없거나 읽을 수 없으면 그 스레드, 최종 결과 전송 줄이 결과 채널을 먼저 쓰는지(소스 확인), 채널 전송 실패 시 작업 스레드로 가는지.
- 문서: SOP §10.1의 Discord 알림 문단과 Discord README의 작업 스레드 설명·4항을 새 경로로 고쳤다. README의 "스레드 전송이 실패하면 … 최종 결과 모두 원래 채널로" 문장에서 최종 결과를 뺐다.

## Implementer 검증 (작업 트리)

- Worker smoke total=595 failed=0(이전 590에 5개), Discord self-check ok 109, SOP validator PASS.
- 사전 점검(`check_task_record`, baseline `c642bde`): status=PASS, staged_files 5, violations 0.
- 실제 Discord 동작(채널에 보고되는지)은 봇을 다시 시작한 뒤 Owner의 다음 `/go`로만 확인할 수 있다. 이 task의 검사는 위 헬퍼와 전송 순서까지다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "새로 만든 쓰레드에서 작업하고 그 쓰레드에 보고하는데 마지막에 보고하는건 채널에 해야하는게 맞는거같아" | `/go` 실행의 마지막 보고(완료·실패·Owner 판단 필요)를 채널로 보낸다. 작업 중 진행 줄은 지금처럼 스레드에 남긴다. `/go`가 스레드 안에서 왔으면 그 상위 채널로 보낸다. 채널로 못 보내면 결과를 잃지 않도록 스레드로 보낸다 |
| A2 | Owner 결정 (원문) | "디스코드에 챗보내면 이채널에 보고한다고 하는데" | 승인 응답의 "끝나면 이 채널에 보고합니다" 문구는 바꾸지 않았다. `/go`를 채널에서 보내면 실제 동작이 그 문구와 맞는다. 스레드 안에서 보내면 승인 응답은 스레드에, 결과는 상위 채널에 간다. 이 경우의 문구 변경은 이번 범위 밖이다 |

## Self-review

candidate 전 1회. minor 3건을 모두 반영했다: 결과도 스레드로 간다고 적힌 task-0183 주석 한 줄을 고치고 owned 범위에 그 주석을 적었다. README에서 최종 결과의 옛 대체 경로를 뺐다. 설계 3항과 A2의 "문구와 동작이 맞는다"를 `/go`를 채널에서 보낸 경우로 좁혔다. 고친 뒤 다시 돌린 결과: Worker smoke total=595 failed=0, validator PASS, 사전 점검 PASS(staged_files 5, violations 0).
