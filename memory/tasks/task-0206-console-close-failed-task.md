# task-0206-console-close-failed-task

- id: `task-0206-console-close-failed-task`
- title: `FAILED task를 Console Close로 닫기`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-29 03:46 UTC`
- updated_at: `2026-10-29 05:12 UTC`
- summary: `FAILED task는 다른 task로 대체돼도 Console Needs attention에 영구히 남는다(예: task-0200, 같은 요청을 task-0202가 DONE). Console Close가 DOING 수동 task에 더해 FAILED task(수동·Worker 경로 모두)도 받게 하여 FAILED → CLOSED 전이를 closed_reason과 함께 연다. Close는 기록 세 줄만 바꾸고 보존된 attempt worktree는 그대로 두며 Preview에서 경고한다. QA 뒤 이 task 안에서 Console Close로 task-0200을 닫는다.`
- completion_evidence: `candidate 3cce5658dc38621b5c114944348ed6c8ae6c66cf (baseline 91997ff). Reviewer PASS, findings 0, self_deviations 0, repair 0. QA PASS in a fresh CRLF worktree: 10 scope files, Console smoke with and without PYTHONUTF8, intake smoke, self-check 109/109, validator, diff --check, node --check, Worker smoke 642/0, a task-0200 copy closes changing three lines. task-0200 closed via Console Close with the Owner reason; its worktree kept.`
- source_command: `Owner 지시: Console 다음 작업 후보 1 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `91997fff3f8f1f985b5850905b2c5258a22400f7` (등록 시점 main HEAD, origin/main보다 1커밋 앞섬: task-0200 기록 보존 커밋, push 안 함) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 제안: 다음 Console 후보]
| **1 (추천)** | **다른 task로 대체된 FAILED task 닫기** (`FAILED → CLOSED` + `closed_reason`, Console Close에서 실행) | task-0200처럼 다른 task로 해결된 실패가 "Needs attention"에 영구히 남지 않음. 주의 그룹이 실제 할 일만 보여 줌 | `docs/task-model.md` 전이 표(11 → 12쌍)와 §13, writer, Console Close 미리보기 조건, smoke | 상태 계약 변경이라 Owner 승인이 필요함. CLOSED는 최종 상태라 `/go` 재시도가 막힘. 보존된 Worker worktree가 남을 수 있음 | writer와 Console smoke, Discord self-check(`/report` 집계), validator, 브라우저 확인 |

[Owner 답]
다음작업 시작해 console 후보 1
```

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문 1]
어떤 FAILED task를 Close로 닫을 수 있게 할까요?

[Owner 답 1]
FAILED 전부 (Recommended)

[Manager 질문 2]
Worker FAILED task를 닫을 때 보존된 attempt worktree는 어떻게 할까요?

[Owner 답 2]
그대로 두고 경고만 (Recommended)

[Manager 질문 3]
구현이 끝난 뒤 task-0200은 누가 닫을까요?

[Owner 답 3]
이번 task 안에서 닫기
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님):

- 답 1: "수동 task와 Worker 경로 task를 구분하지 않고 FAILED면 Close 가능. task-0200(Worker 경로)도 닫을 수 있음. SOP §8의 'Worker 파이프라인 task는 Close 대상이 아니다' 문장을 'FAILED인 Worker task는 닫을 수 있다'로 고쳐야 함."
- 답 2: "Close는 기록 세 줄(status·updated_at·closed_reason)만 바꾸고 파일 시스템은 건드리지 않음. Preview에 '보존된 worktree는 남고 /go 재시도·resume·accept가 더는 안 된다'고 표시."
- 답 3: "QA 뒤 같은 task에서 Console Close로 task-0200까지 닫음."

## 조사 (등록 전)

- 지금 Close는 `DOING` → `CLOSED` 한 쌍뿐이고 `source_command`가 `/task`인 Worker 경로 task를 거부한다(writer `close_task_file`의 `close_requires_manual_task`, Console Preview 같은 사유, 화면 `closeEligible`). 근거는 task-0178 설계: Worker 경로의 DOING은 `/go <id> recover`가 FAILED로 끝낸다. FAILED에서 나가는 전이는 `FAILED` → `TODO`(`/go` 재시도·resume·accept)뿐이라 FAILED task는 Task View Needs attention(순위 30)에 계속 남는다.
- task-0200(`source_command: /task`, FAILED, `scope:no_changes`)은 같은 요청을 task-0202가 task-0201 읽기 전용 경로로 다시 실행해 DONE이 됐다. 기록은 `91997ff`에서 커밋됐다.
- FAILED는 실행이 끝난 뒤의 상태다. `/go` 재시도·resume·accept는 실행 전에 `FAILED` → `TODO` → `DOING`을 먼저 쓰므로, FAILED인 동안 그 task의 Worker는 돌지 않는다. Preview 뒤 상태가 바뀌면 digest 검사가 Confirm을 `stale`로 막는다.
- Discord 쪽은 이미 `CLOSED`를 받지 않는다(`status_not_startable:CLOSED`, `accept_requires_failed:CLOSED`, `recover_requires_doing:CLOSED`, task-0180). `/report` 집계와 `/retro today` follow-up(FAILED·BLOCKED만)도 바꿀 것이 없다. 닫힌 task는 follow-up에서 빠진다.
- SOP §8 마지막 문장 "§10 Worker 파이프라인 task는 Close 대상이 아니다."는 Owner 답 1로 고친다.

## 설계

1. writer(`orchestrator/discord-intake/task_file_writer.py`): `TASK_STATUS_TRANSITIONS`와 `TASK_CLOSE_TRANSITIONS`에 `("FAILED", "CLOSED")`를 더한다(11 → 12쌍). `close_task_file`의 Worker 경로 거부는 출발 상태가 `DOING`일 때만 적용한다. FAILED는 `source_command`와 관계없이 받는다. 일반 전이 writer와 실행 결과 writer는 기존 `TASK_CLOSE_TRANSITIONS` 검사로 새 쌍도 거부한다.
2. Console(`apps/jarvis-console/run_web_app.py`): `TASK_CLOSE_ACTIONS`의 허용 상태를 `DOING`·`FAILED`로, Preview의 `close_requires_manual_task`는 DOING일 때만. 경고 문구를 고쳐 FAILED task도 닫을 수 있고, 닫으면 보존된 Worker attempt worktree는 그대로 남으며 `/go` 재시도·resume·accept가 더는 그 task를 받지 않는다고 적는다. 파일 시스템은 건드리지 않는다.
3. 화면(`apps/jarvis-console/web/app.js`): `closeEligible`에 FAILED를 더한다(Worker 경로 포함).
4. 테스트(`apps/jarvis-console/run_smoke_tests.py`): 전이 수 12, `TASK_CLOSE_TRANSITIONS` 두 쌍, writer가 FAILED 수동·Worker 경로를 바이트 단위로 닫음, DOING Worker 경로는 여전히 거부, Console Preview/Confirm로 FAILED Worker task 닫기와 경고 문구, 닫힌 뒤 모든 동작 거부, 화면 소스.
5. 문서: `docs/task-model.md`(2절 CLOSED 정의, 5-1 표·문단·"11쌍", 5-2 Close 행, 13절), SOP §8 마지막 문장, `apps/jarvis-console/README.md` Close 절, `adapters/discord/README.md` CLOSED 줄, `reports/README.md` CLOSED 정의.
6. 이 task가 닫는 기록은 task-0200 하나다. QA PASS 뒤 Console Close Preview → `CLOSE TASK` Confirm으로 닫고 closed_reason은 Owner가 정한다. 그 변경은 checkpoint에 담는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/discord-intake/task_file_writer.py`, `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/web/app.js`, `apps/jarvis-console/run_smoke_tests.py`, `apps/jarvis-console/README.md`, `adapters/discord/README.md`, `docs/task-model.md`, `docs/jarvis-multi-agent-sop-v0.1.md`(§8 마지막 문장만), `reports/README.md`, `memory/tasks/task-0206-console-close-failed-task.md` |
| deny | `jarvis.bat`, Discord 봇 코드(`adapters/discord/bot_minimal.py`), Worker 코드(`orchestrator/worker/`), 감사 체인, worktree 삭제·정리, AGENTS·agent 정의·validator, task-0200을 뺀 다른 task 기록(task-0200은 QA 뒤 Console Close로만), 외부 API·credential, push |

## 계획

1. Console Start(TODO → DOING).
2. 구현: writer, Console 서버·화면, smoke test, 문서.
3. 검사: Console smoke(PYTHONUTF8 없이), discord-intake smoke, Discord self-check, Worker smoke, SOP validator, `git diff --check`, `node --check app.js`, 실제 브라우저에서 task-0200 카드에 Close가 보이는지(닫지는 않음).
4. 사전 점검 → self-review → candidate(`commit_candidate.py --require-quotes`) → Reviewer → QA → Owner의 closed_reason으로 task-0200 Close → Evidence·Complete → checkpoint → master-plan. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-29 03:48 UTC`). Console은 Start 뒤 껐다.

## 구현

- `orchestrator/discord-intake/task_file_writer.py`: `TASK_STATUS_TRANSITIONS`와 `TASK_CLOSE_TRANSITIONS`에 `("FAILED", "CLOSED")`를 더했다(전이 12쌍, 닫기 2쌍). `close_task_file`의 `close_requires_manual_task` 거부를 출발 상태가 `DOING`일 때로 좁혔다. docstring과 주석. 일반 전이 writer와 실행 결과 writer는 기존 `TASK_CLOSE_TRANSITIONS` 검사 그대로 새 쌍도 `close_transition_requires_close_writer`로 거부한다.
- `apps/jarvis-console/run_web_app.py`: `TASK_CLOSE_ACTIONS["close"]` 허용 상태를 `DOING`·`FAILED`로, Preview의 `close_requires_manual_task`는 `DOING`일 때만. `TASK_CLOSE_WARNING`에 FAILED task도 닫을 수 있고, 보존된 Worker attempt worktree는 그대로 남으며 `/go` retry·resume·accept가 더는 받지 않는다는 문장을 더했다. Confirm·receipt 흐름은 그대로다.
- `apps/jarvis-console/web/app.js`: `closeEligible`에 `view.status === "FAILED"`(source_command 무관)를 더했다. 그래서 FAILED 카드의 배지가 "Read-only"에서 "Preview + Confirm required"로 바뀐다.
- `apps/jarvis-console/run_smoke_tests.py`: `_test_task_close`에 규칙 일치(두 쌍, 허용 상태 둘), writer가 FAILED 수동·Worker 경로를 바이트 단위로 닫음과 일반·실행 결과 writer의 거부, 거부 상태 목록에서 FAILED 제거, Console Preview/Confirm로 FAILED Worker·수동 task 닫기(경고 문구, 닫힌 뒤 Start·Complete·Hold·Resume·Close 거부), 화면 소스 검사를 더했다. 전이 표 검사를 12쌍으로, 배지 harness에서 FAILED를 Preview + Confirm 쪽으로 옮겼다.
- 문서: `docs/task-model.md`(2절 CLOSED 정의, 5-1 "12쌍"·표 한 행·Close 문단, 5-2 Close 행, 13절), `docs/jarvis-multi-agent-sop-v0.1.md` §8 마지막 문장, `apps/jarvis-console/README.md` Close 절, `adapters/discord/README.md` CLOSED 줄, `reports/README.md` CLOSED 정의.

## Implementer 검증 (작업 트리)

- `python -B apps/jarvis-console/run_smoke_tests.py`(PYTHONUTF8 없이) 통과. 첫 실행은 배지 harness가 FAILED를 Read-only로 기대해 실패했고, 설계 3의 결과이므로 harness 목록을 고쳤다.
- `orchestrator/discord-intake/run_smoke_tests.py` 종료 0, Discord `--self-check-suite` ok 109/109, SOP validator PASS(negative_checks 172), `git diff --check` 통과, `node --check app.js` 통과.
- Worker smoke total=642 failed=0(종료 0). self-review 반영 전 코드에서 돌렸고, 그 뒤 writer는 docstring 한 줄만 바뀌었다.
- 실제 Console(127.0.0.1:8790, 실제 기록): task-0200 카드에 Close 사유 입력과 "Close Task" 버튼이 보이고 콘솔 오류는 없었다. 같은 task에 Close Preview만 요청하면(사유 "preview only check", Confirm 안 함) 200, `FAILED → CLOSED`, `reversible: false`, 새 경고 문구였고 task-0200 기록은 바뀌지 않았다(status `FAILED`, git 변경 없음). 서버는 확인 뒤 껐다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안: 다음 Console 후보]" | 제안의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "\| **1 (추천)** \| **다른 task로 대체된 FAILED task 닫기** (`FAILED → CLOSED` + `closed_reason`, Console Close에서 실행) \| task-0200처럼 다른 task로 해결된 실패가 "Needs attention"에 영구히 남지 않음." | `FAILED → CLOSED` 전이를 열고 `closed_reason`을 함께 쓰며 Console Close로만 실행한다(구현 writer·Console). 닫힌 task는 Closed 그룹으로 가서 Needs attention에서 빠진다(기존 CLOSED 그룹 규칙). 어떤 실패가 "대체됐는지"는 Jarvis가 판정하지 않고 Owner가 closed_reason에 적는다 |
| A3 | Owner 결정 (원문) | "주의 그룹이 실제 할 일만 보여 줌 \| `docs/task-model.md` 전이 표(11 → 12쌍)와 §13, writer, Console Close 미리보기 조건, smoke \| 상태 계약 변경이라 Owner 승인이 필요함." | 전이 표를 12쌍으로, §13을 고쳤고 writer·Console Preview 조건·smoke를 바꿨다. Owner 승인은 A7과 답 A11·A15·A19다. 짝 문서(SOP §8, README 셋, task-model 2절·5-2)는 같은 규칙을 적은 곳이라 함께 고쳤다(범위 표 owned) |
| A4 | Owner 결정 (원문) | "CLOSED는 최종 상태라 `/go` 재시도가 막힘." | CLOSED에서 나가는 전이는 그대로 없고 Discord `/go` 각 형태가 CLOSED를 거부하는 것도 그대로다(task-0180). Preview 경고에 retry·resume·accept가 더는 안 된다고 적었다 |
| A5 | Owner 결정 (원문) | "보존된 Worker worktree가 남을 수 있음 \| writer와 Console smoke, Discord self-check(`/report` 집계), validator, 브라우저 확인 \|" | worktree는 건드리지 않고 경고만 한다(A15). 검증은 writer·Console smoke, Discord self-check 109, validator, 브라우저 확인을 했다(Implementer 검증) |
| A6 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A7 | Owner 결정 (원문) | "다음작업 시작해 console 후보 1" | 후보 1 착수 승인. 세부 범위는 A9~A19의 답으로 정했다 |
| A8 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 1]" | 질문의 표지 |
| A9 | Owner 결정 (원문, 착수 전 bounded question) | "어떤 FAILED task를 Close로 닫을 수 있게 할까요?" | A11의 질문 |
| A10 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 1]" | 답의 표지 |
| A11 | Owner 결정 (원문, 착수 전 bounded question) | "FAILED 전부 (Recommended)" | FAILED는 `source_command`와 관계없이 닫는다(writer는 DOING일 때만 Worker 경로 거부, Console 허용 상태와 화면 조건). 선택지 설명대로 SOP §8 마지막 문장을 고쳤다. DOING Worker 경로 거부는 그대로다 |
| A12 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 2]" | 질문의 표지 |
| A13 | Owner 결정 (원문, 착수 전 bounded question) | "Worker FAILED task를 닫을 때 보존된 attempt worktree는 어떻게 할까요?" | A15의 질문 |
| A14 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 2]" | 답의 표지 |
| A15 | Owner 결정 (원문, 착수 전 bounded question) | "그대로 두고 경고만 (Recommended)" | Close는 status·updated_at·closed_reason 세 줄만 바꾼다(테스트의 바이트 비교). writer는 FAILED 거부 조건만 바뀌었고 task 기록 한 파일만 쓰며, worktree를 지우거나 고치는 코드는 더하지 않았다(diff 기준). Preview 경고 `TASK_CLOSE_WARNING`에 worktree가 남는다는 문장을 더했다 |
| A16 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 3]" | 질문의 표지 |
| A17 | Owner 결정 (원문, 착수 전 bounded question) | "구현이 끝난 뒤 task-0200은 누가 닫을까요?" | A19의 질문 |
| A18 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 3]" | 답의 표지 |
| A19 | Owner 결정 (원문, 착수 전 bounded question) | "이번 task 안에서 닫기" | candidate에는 task-0200 변경이 없다. QA PASS 뒤 Console Close로 닫고(closed_reason은 Owner가 정함) 그 변경을 checkpoint에 담는다. 아직 하지 않았다 |
| A20 | Owner 결정 (원문, task-0200 closed_reason) | "[Manager 질문]" | 질문의 표지(QA 뒤 추가, candidate 밖) |
| A21 | Owner 결정 (원문, task-0200 closed_reason) | "task-0200을 Console Close로 닫을 때 closed_reason을 무엇으로 할까요?" | A22의 질문 |
| A22 | Owner 결정 (원문, task-0200 closed_reason) | "task-0202로 대체 (Recommended)" | 선택지 설명 문장을 그대로 closed_reason으로 써서 task-0200을 닫았다(Reviewer·QA 결과 절) |
| A23 | Owner 결정 (원문, Complete) | "task-0206을 Console Complete로 DONE 처리할까요? (Reviewer PASS, QA PASS, task-0200 Close 완료, 완료 증거 기록됨)" | A24의 질문(QA 뒤 추가, candidate 밖) |
| A24 | Owner 결정 (원문, Complete) | "Complete 진행 (Recommended)" | Console Complete로 DONE(Complete 절). push는 하지 않았다 |

## Self-review

`self-reviewer`(`claude -p --agent self-reviewer --tools Read,Grep,Glob`, 첫 사전 점검 PASS 뒤 1회, API 환산 약 $0.50)의 지적 7건(모두 minor)을 모두 고쳤다.

1. Console README 기능 목록의 Close 줄이 수동 DOING만 적음 → "a manual `DOING` Task or any `FAILED` Task"로 고침.
2. `app.js`의 task-0180 주석이 "manual DOING Task only" → DOING에 한정한 문장으로 고침.
3. writer `close_task_file` docstring 첫 줄이 DOING만 적음 → "a manual DOING or a FAILED Task"로 고침.
4. 기록의 Worker smoke 줄이 없는 절을 가리킴 → 결과(642/0)를 적음.
5. A15 해석의 "writer 변경 없음"이 사실과 다름 → 거부 조건만 바뀌었고 worktree 코드가 없다는 것으로 고침.
6. A3 해석이 질문·표지 행까지 Owner 승인으로 적음 → "A7과 답 A11·A15·A19"로 고침.
7. FAILED에서 닫은 task에 Close 재시도를 검사하지 않으면서 기록은 "모든 동작 거부"라 적음 → 테스트에 Close 재시도 거부를 더하고 기록 문장을 동작 다섯 개로 적음.

수정 뒤 Console smoke와 discord-intake smoke 다시 통과, `node --check` 통과. 사전 점검 결과는 아래 candidate 직전 실행이다.

## Owner 결정 (원문, task-0200 closed_reason)

```text
[Manager 질문]
task-0200을 Console Close로 닫을 때 closed_reason을 무엇으로 할까요?

[Owner 답]
task-0202로 대체 (Recommended)
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님): "같은 요청을 task-0202가 읽기 전용 경로(task-0201)로 다시 실행해 DONE. 이 시도는 scope:no_changes 실패 그대로 둔다."

## Reviewer·QA 결과

- candidate `3cce5658dc38621b5c114944348ed6c8ae6c66cf`(baseline `91997ff`, 단일 커밋, scope 10파일): Reviewer PASS, findings 0, self_deviations 0. Reviewer가 직접 돌리지 않은 항목(smoke, self-check, validator, 브라우저, Worker smoke, task-0200 Close)은 QA와 아래 Close에서 확인했다. retry 0, repair 0.
- QA PASS(새 detached worktree, `core.autocrlf`로 CRLF 체크아웃): 변경 파일 10개, Console smoke PYTHONUTF8 없이·있이 통과, discord-intake smoke 종료 0, Discord `--self-check-suite` ok 109/109, SOP validator PASS, `git diff --check` 통과, `node --check app.js` 통과, Worker smoke total=642 failed=0, `jarvis.bat` 트리에 없음, 작업 트리 깨끗. worktree 안 task-0200 사본을 Console 함수로 닫으면 status·closed_reason·updated_at만 바뀌고 뒤이은 Start·Complete·Hold·Resume Preview가 거부됐다(사본은 되돌림). `check_no_secrets.py` 전체 검사는 findings 7로 FAIL이었으나 7건 모두 스캐너 자신의 자체 검사 견본(`scripts/check_no_secrets.py:242-248`)이고 baseline main에서도 같아 이 candidate와 무관하다. QA worktree는 지웠다.
- task-0200 Close(Owner 답 3과 위 closed_reason 결정): 실제 Console(127.0.0.1:8790)에서 사유를 입력하고 Preview(`FAILED → CLOSED`, Reopen Not possible, 새 경고 문구)를 확인한 뒤 `Confirm Close`. 기록은 status `CLOSED`, closed_reason(위 선택지 설명 문장), updated_at `2026-10-29 04:28 UTC` 세 줄만 바뀌었다. task-0200의 attempt worktree(`jarvis-core-worktrees/task-0200-...`)는 Owner 답 2대로 그대로 두었다.

## Owner 결정 (원문, Complete)

```text
[Manager 질문]
task-0206을 Console Complete로 DONE 처리할까요? (Reviewer PASS, QA PASS, task-0200 Close 완료, 완료 증거 기록됨)

[Owner 답]
Complete 진행 (Recommended)
```

## Complete

Record Completion Evidence(Preview 확인 뒤 Confirm, updated_at `2026-10-29 04:29 UTC`)로 completion_evidence를 남긴 뒤, Owner 결정에 따라 Console Complete Preview(DOING → DONE, 증거 표시)를 확인하고 `Confirm Complete`로 DONE이 됐다(updated_at `2026-10-29 05:12 UTC`). Console은 끈 상태다. push는 하지 않았다.
