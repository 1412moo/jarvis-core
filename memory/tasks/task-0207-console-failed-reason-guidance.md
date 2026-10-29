# task-0207-console-failed-reason-guidance

- id: `task-0207-console-failed-reason-guidance`
- title: `FAILED 카드에 실패 사유를 읽을 수 있는 말로 표시`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-29 11:52 UTC`
- updated_at: `2026-10-29 14:46 UTC`
- summary: `FAILED task 카드는 execution_summary의 코드(예: scope:no_changes)와 일반 안내만 보여 준다. Task View 투영이 FAILED 항목에만 failure_guidance를 붙여 기록된 사유 코드의 한국어 설명과, 그 사유와 task 경로에 맞는 기존 복구 방법(/go 재시도·resume·accept, Console Close)을 글로 보여 준다. 읽기 전용이며 task 기록, 상태 계약, API 경로, 쓰기 흐름은 바꾸지 않고 push는 하지 않는다.`
- completion_evidence: `candidate 0b10771ec7c6e67b1f0df15b5bc4adc93295d8d2 (baseline ab4f340). Reviewer FINDINGS 3 minor, all accepted by the Owner (SOP 8), self_deviations 0, repair 0. QA PASS in a fresh CRLF worktree: 5 scope files, Console smoke with and without PYTHONUTF8, intake smoke, self-check 109/109, validator, diff --check, node --check, Worker smoke 642/0. Browser: a temporary FAILED card showed the guidance rows.`
- source_command: `Owner 지시: Console 다음 작업 후보 2 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `ab4f340ebf95caff8a1d977f01abd28c94efad53` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 제안: 다음 작업]
| **1 (추천)** | **Console 후보 2: FAILED 카드에 실패 사유를 읽을 수 있는 말로 표시** | 지금은 `scope:no_changes` 같은 코드만 보입니다. 이걸 원인과 다음 조치(`/go` retry, `resume`, Close) 한 줄로 바꿔 보여 줍니다. | 낮음. 읽기 전용이고 `run_web_app.py`의 사유 코드 매핑과 `app.js`만 바뀌며, 상태 계약은 그대로입니다. |

[Owner 답]
후보 2 시작
```

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문 1]
FAILED 카드의 실패 사유 설명은 어느 언어로 표시할까요?

[Owner 답 1]
한국어 (Recommended)

[Manager 질문 2]
사유 설명과 함께 다음 조치도 보여 줄까요?

[Owner 답 2]
사유별로 가능한 조치 안내 (Recommended)
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님):

- 답 1: "Discord /go 응답과 Worker 답 라벨(task-0205)처럼 한국어로 씁니다. 카드의 다른 항목 이름(Status, Next action 등)은 영어 그대로 둡니다."
- 답 2: "사유마다 이미 있는 경로 중 맞는 것만 글로 적습니다(/go <id> 재시도, resume, accept, Console Close). 버튼이나 실행은 추가하지 않는 읽기 전용입니다. 알 수 없는 코드에는 원래 코드와 '기록을 직접 확인' 안내를 보여 줍니다."

## 조사 (등록 전)

- Worker는 실패를 `execution_summary`에 `<stage>:<reason>`으로 남긴다(`orchestrator/worker/claude_worker.py`의 `record_result(False, f"{result.stage}:{result.reason}")`). 예외는 `qa:qa_unverified_owner_review candidate=<40hex> baseline=<40hex> attempt=<N>`(SOP §10 9항)과 Owner recover의 `recover:stalled_doing`(`adapters/discord/bot_minimal.py`의 `RECOVER_SUMMARY`)이다. 사유 코드는 `StageFailure`의 두 번째 인자다.
- Console 카드는 `Execution result`·`Execution summary`(task-0155)에 그 코드를 그대로 보이고, FAILED의 `Next action`은 일반 문장 "Review the summary and decide the recovery outside Jarvis Console."이다.
- FAILED task의 복구 경로(`adapters/discord/bot_minimal.py` `/go` 처리, SOP §10): `/go <id>`(재시도, FAILED → TODO → DOING, 새 attempt), `/go <id> resume`(직전 attempt의 허용 경로 변경을 옮김, 읽기 전용 요청은 `resume_not_for_read_only`로 거부), `/go <id> accept`(9항 실패 기록이 있을 때만). 세 형태 모두 `source_command`가 `/task`인 Worker 경로 task만 받는다(`go_requires_worker_path`). Console Close는 모든 FAILED task를 받는다(task-0206).
- 등록 시점에 FAILED인 task 기록은 없다(task-0200은 CLOSED). 화면 확인은 smoke fixture와 임시 사본으로 한다.

## 설계

1. 서버(`apps/jarvis-console/run_web_app.py`): 상수 `TASK_FAILURE_SUMMARY_PATTERN`(`^<stage>:<reason>`, 뒤에 공백으로 시작하는 꼬리 허용)과 `TASK_FAILURE_REASONS`(사유 코드 → 한국어 설명과 맞는 복구 방법 묶음)를 둔다. 함수 `task_failure_guidance(task_view)`는 유효한 FAILED task에만 `{"code", "known", "meaning", "options"}`를 돌려주고, 그 밖에는 `None`이다. `project_task_view_items()`가 값이 있는 항목에만 `failure_guidance`를 붙인다(task-0205 `worker_report`와 같은 방식). `parse_task_view_text()`, 그룹·순위·`next_action`, counts, 쓰기 흐름은 그대로다.
2. 복구 방법 글: Worker 경로 task는 사유에 맞는 것만 `/go <task-id>`(재시도), `/go <task-id> resume`(읽기 전용 요청 제외), `/go <task-id> accept`를 적고, 마지막에 항상 Console Close를 적는다. 수동 task는 `/go`가 받지 않는다는 문장과 Console Close만 적는다. 코드가 없거나 형식이 다르거나 표에 없으면 `known: false`, 설명은 "Console이 모르는 사유"이며 복구 방법은 "task 기록을 직접 확인"과 Console Close다.
3. 화면(`apps/jarvis-console/web/app.js`): `item.failure_guidance`가 있을 때만 `실패 의미`·`가능한 조치` 두 줄을 읽기 전용으로 보인다(escape, 버튼 없음).
4. 테스트(`apps/jarvis-console/run_smoke_tests.py`): 알려진 코드, 꼬리가 붙은 `qa_unverified_owner_review`, 수동 task, 모르는 코드, 코드 없음, FAILED가 아닌 task(없음), 표의 모든 사유가 실제 Worker·봇 코드에 있는 문자열인지, 화면 소스.
5. 문서: `apps/jarvis-console/README.md`의 실행 결과 절.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/web/app.js`, `apps/jarvis-console/run_smoke_tests.py`, `apps/jarvis-console/README.md`, `memory/tasks/task-0207-console-failed-reason-guidance.md` |
| deny | `jarvis.bat`, Discord 봇 코드, Worker 코드(`orchestrator/worker/`), writer, 상태 계약 문서(`docs/task-model.md`), 다른 task 기록, AGENTS·agent 정의·validator, 외부 API·credential, push |

## 계획

1. Console Start(TODO → DOING).
2. 구현: 서버, 화면, smoke test, README.
3. 검사: Console smoke(PYTHONUTF8 없이·있이), SOP validator, `git diff --check`, `node --check app.js`, 실제 브라우저에서 FAILED 사본 카드(임시, 커밋 안 함).
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete → checkpoint → master-plan. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-29 11:53 UTC`). Console은 구현 전에 껐다.

## 구현

- `apps/jarvis-console/run_web_app.py`: 상수 `TASK_FAILURE_SUMMARY_PATTERN`, 복구 방법 이름 셋(`retry`·`resume`·`accept`), `TASK_FAILURE_REASONS`(사유 코드 30개 → 한국어 설명과 맞는 복구 방법), `TASK_FAILURE_UNKNOWN_MEANING`, `TASK_FAILURE_MANUAL_NOTE`, `TASK_FAILURE_CLOSE_OPTION`. 함수 `task_failure_option_text()`(복구 방법 한 줄, 실제 task id를 넣음)와 `task_failure_guidance()`(유효한 FAILED task만, 그 밖에는 None). `project_task_view_items()`가 값이 있는 항목에만 `failure_guidance`를 붙인다. `parse_task_view_text()`, 그룹·순위·`next_action`, counts, 쓰기 흐름은 그대로다.
- 사유 표는 실제로 기록에 남는 코드만 담았다. `accept_*` 거절과 `accept_transition_failed`는 승인 전이 전이라 실패 기록을 바꾸지 않으므로(`claude_worker.py` accept 실행의 `if not approved` 분기, SOP §10 12항) 넣지 않았다. 그런 코드가 기록에 있으면 모르는 사유로 보인다. `checkpoint:task_result_not_recorded`도 넣지 않았다. 반영(ff-only) 뒤 기록 단계의 실패라 candidate가 이미 main에 있어 `/go` 재시도·resume 안내가 맞지 않으므로 모르는 사유로 두어 기록을 직접 보게 한다.
- 복구 방법: `accept`는 `qa_unverified_owner_review`에만, 그리고 기록이 Worker의 `OWNER_REVIEW_RECORD_PATTERN`과 같은 완전한 형식(`candidate=<40hex> baseline=<40hex> attempt=<N>`, Console 상수 `TASK_FAILURE_OWNER_REVIEW_PATTERN`)일 때만 붙는다. 형식이 다르면 봇이 `accept_record_invalid`로 거부하므로 accept 줄을 빼고 재시도와 Close만 보인다. 봇은 그 밖에 `execution_result`의 `error_reason`과 같은지도 보는데, Console은 `execution_result`를 읽지 않으므로 그 검사는 하지 않는다. `resume`은 직전 attempt의 변경이 남을 수 있는 사유(Worker·Reviewer 시간 초과, Worker 오류, 테스트·QA 실패, Reviewer 판정, repair 무변경, 반영 직전 main 이동, recover)에만 붙이고, 범위 위반·무변경·resume 거절·환경 문제·읽기 전용 경로 사유에는 붙이지 않는다. 문장에 "읽기 전용 요청은 받지 않는다"를 적었다(`resume_not_for_read_only`).
- `apps/jarvis-console/web/app.js`: `failureGuidanceMarkup()`(`실패 의미`, `가능한 조치` 목록, 모두 escape, 버튼·fetch 없음)와 카드에서 `item.failure_guidance`가 있을 때만 부르는 한 줄.
- `apps/jarvis-console/run_smoke_tests.py`: `_test_task_failure_guidance`(알려진 코드, 꼬리 붙은 Owner-review 기록, recover, 수동 task, 모르는·형식이 다른·없는 코드, FAILED가 아닌 상태와 invalid, 표의 사유가 Worker·봇 소스에 있는 문자열인지, accept 규칙, 투영, node 렌더 harness).
- `apps/jarvis-console/README.md`: 실행 결과 절에 새 두 줄의 설명.

## Implementer 검증 (작업 트리)

- `python -B apps/jarvis-console/run_smoke_tests.py`(PYTHONUTF8 없이) 통과, `PYTHONUTF8=1`로도 통과.
- SOP validator PASS(negative_failures 0), `git diff --check` 통과, `node --check app.js` 통과.
- 실제 Console(127.0.0.1:8790): 임시 FAILED 기록(`task-0999-temp-failed-guidance-check`, Worker 경로, `qa:qa_unverified_owner_review …` 꼬리 포함)을 만들어 카드에 `실패 의미`와 `가능한 조치`(accept, 재시도, Console Close 순서)가 보이고 Next action은 그대로이며 콘솔 오류가 없음을 확인했다. 임시 기록은 확인 뒤 지웠고 서버는 껐다.
- Worker·봇·writer 코드는 바꾸지 않았으므로 Worker smoke와 Discord self-check는 돌리지 않았다(QA에서 돌린다).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안: 다음 작업]" | 제안의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "\| **1 (추천)** \| **Console 후보 2: FAILED 카드에 실패 사유를 읽을 수 있는 말로 표시** \| 지금은 `scope:no_changes` 같은 코드만 보입니다." | FAILED 카드에 기록된 사유 코드의 설명을 더한다(`실패 의미` 줄). 기존 `Execution summary` 줄의 코드는 그대로 둔다 |
| A3 | Owner 결정 (원문) | "이걸 원인과 다음 조치(`/go` retry, `resume`, Close) 한 줄로 바꿔 보여 줍니다." | 원인은 `실패 의미` 한 줄, 다음 조치는 `가능한 조치` 한 항목이다. 사유에 맞는 조치가 여럿일 수 있어(예: accept와 재시도와 Close) 각 조치를 목록의 한 줄로 적었다. 조치 이름은 제안대로 `/go` 재시도·`resume`·Close이고, 답 A14의 선택지 설명대로 `qa_unverified_owner_review`에는 accept도 적는다. 코드를 지우고 바꿔 끼우지 않고 설명을 더했다(A2) |
| A4 | Owner 결정 (원문) | "읽기 전용이고 `run_web_app.py`의 사유 코드 매핑과 `app.js`만 바뀌며, 상태 계약은 그대로입니다." | 제품 코드는 `run_web_app.py`(사유 매핑, 투영에 키 하나)와 `app.js`(두 줄 렌더)만 바뀐다. 그 검사(`run_smoke_tests.py`), Console README, 이 task 기록은 SOP가 요구하는 검사·문서·기록이라 범위 표 owned에 넣었다. 쓰기 경로, 전이 표, task 기록 형식, API 경로, `next_action`은 바꾸지 않았다(diff 기준) |
| A5 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A6 | Owner 결정 (원문) | "후보 2 시작" | 후보 2 착수 승인. 세부는 A10·A14의 답으로 정했다 |
| A7 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 1]" | 질문의 표지 |
| A8 | Owner 결정 (원문, 착수 전 bounded question) | "FAILED 카드의 실패 사유 설명은 어느 언어로 표시할까요?" | A10의 질문 |
| A9 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 1]" | 답의 표지 |
| A10 | Owner 결정 (원문, 착수 전 bounded question) | "한국어 (Recommended)" | 설명·조치 문장과 새 두 줄의 이름(`실패 의미`, `가능한 조치`)을 한국어로 썼다. 선택지 설명대로 카드의 다른 항목 이름은 영어 그대로다. 명령 형태(`/go <id> resume` 등)와 `Console Close`, `closed_reason`은 실제 이름이라 그대로 적었다 |
| A11 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 2]" | 질문의 표지 |
| A12 | Owner 결정 (원문, 착수 전 bounded question) | "사유 설명과 함께 다음 조치도 보여 줄까요?" | A14의 질문 |
| A13 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 2]" | 답의 표지 |
| A14 | Owner 결정 (원문, 착수 전 bounded question) | "사유별로 가능한 조치 안내 (Recommended)" | 선택지 설명대로: 사유마다 이미 있는 경로 중 맞는 것만 적는다(`TASK_FAILURE_REASONS`, accept는 Owner-review 기록에만, resume은 직전 변경이 남을 수 있는 사유에만, Worker 경로가 아니면 `/go` 대신 안내 문장). 모든 FAILED에 Console Close를 적는다(task-0206). 버튼·실행·fetch는 더하지 않았다(smoke harness). 모르는·형식이 다른·없는 코드는 원래 코드(있으면)를 `code`에 두고 "task 기록을 직접 확인" 안내를 보인다. 원래 코드는 기존 `Execution summary` 줄에 그대로 보인다 |

## Self-review

`self-reviewer`(`claude -p --agent self-reviewer --tools Read,Grep,Glob`, 첫 사전 점검 PASS 뒤 1회, API 환산 약 $0.49)의 지적 3건(모두 minor)을 모두 고쳤다.

1. 꼬리가 없거나 형식이 틀린 `qa:qa_unverified_owner_review` 기록에도 accept를 보임(봇은 `accept_record_invalid`로 거부) → Worker 형식과 같은 `TASK_FAILURE_OWNER_REVIEW_PATTERN`이 전체 일치할 때만 accept를 붙인다. smoke에 꼬리 없음·짧은 hash·attempt 0·뒤 꼬리 네 경우와, 그 패턴이 `claude_worker.py`의 패턴 문자열과 같은지를 더했다. README와 구현 절에 조건과 Console이 `execution_result`를 보지 않는다는 한계를 적었다.
2. 수동 task 안내가 "Jarvis 밖에서 복구한다"라 바로 뒤의 Console Close와, 봇의 "수동 task의 상태 변경은 Jarvis Console을 씁니다"와 어긋남 → "이 task의 재작업은 Jarvis 밖에서 하고, 상태는 Console로 바꾼다"로 고쳤다.
3. `checkpoint:task_result_not_recorded`를 뺀 판단이 기록에 없음 → 구현 절에 이유(반영 뒤 기록 단계 실패라 `/go` 안내가 맞지 않음)를 적었다.

수정 뒤 Console smoke 통과. 사전 점검 결과는 아래 candidate 직전 실행이다.

## Reviewer 결과

- candidate `0b10771ec7c6e67b1f0df15b5bc4adc93295d8d2`(baseline `ab4f340`, 단일 커밋, scope 5파일): Reviewer **FINDINGS**, 지적 3건 모두 minor, self_deviations 0.
  1. 승인 문장은 `run_web_app.py`와 `app.js`만 바뀐다고 했는데 smoke test, README, 이 task 기록까지 5파일이 바뀐다. A4의 근거("SOP가 요구하는 검사·문서·기록")는 승인 원문에 없다.
  2. 승인 문장은 원인과 조치를 "한 줄로 바꿔" 보여 준다고 했는데 candidate는 코드를 두고 `실패 의미`·`가능한 조치`(목록) 두 줄을 더하고, 승인 문장에 없는 accept를 넣었다. A3의 accept 근거는 Owner 원문이 아닌 선택지 설명이다.
  3. A10·A14가 근거로 든 선택지 설명은 Owner 원문 블록 밖의 Manager 문구다.
- Reviewer가 직접 돌리지 않은 항목(Console smoke 두 방식, validator, diff check, node check, 브라우저, Worker smoke, Discord self-check)은 아래 QA와 Implementer 검증에서 확인했다.

## Owner 결정 (원문, Reviewer minor 지적 수용)

```text
[Manager 질문]
Reviewer minor 지적 3건(범위 5파일, 두 줄+목록 형태와 accept, 선택지 설명에 기댁 세부 규칙)을 어떻게 처리할까요?

[Owner 답]
3건 모두 수용, QA 진행 (Recommended)
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님): "지금 구현(5파일, 실패 의미 한 줄 + 조치 목록, Owner-review 기록에만 accept, 선택지 설명의 세부 규칙)을 Owner가 인정합니다. 수용 원문을 기록하고 같은 candidate 0b10771로 QA를 돌립니다. repair 예산은 쓰지 않습니다."

SOP §8 Owner minor finding 수용(수동 경로): 지적 1·2·3 모두 수용, candidate `0b10771`에만 효력. retry 0, repair 0.

## QA 결과

QA PASS(새 detached worktree, `core.autocrlf=true`로 CRLF 체크아웃, HEAD = candidate `0b10771ec7c6e67b1f0df15b5bc4adc93295d8d2`): baseline..candidate 변경 파일 5개, `jarvis.bat` 트리에 없음, Console smoke PYTHONUTF8 없이·있이 통과, discord-intake smoke 종료 0, Discord `--self-check-suite` 109/109(종료 0), SOP validator PASS, `git diff --check` 통과, `node --check app.js` 통과, Worker smoke total=642 failed=0, 검사 뒤 작업 트리 깨끗. QA worktree는 지웠다. Docs는 `not_required`(README가 candidate 안에 있음).

## Owner 결정 (원문, Complete)

```text
[Manager 질문]
task-0207을 Console Complete로 DONE 처리할까요? (Reviewer minor 3건 Owner 수용, QA PASS, 완료 증거 기록됨)

[Owner 답]
Complete 진행 (Recommended)
```

## Complete

Record Completion Evidence(Preview 확인 뒤 Confirm, updated_at `2026-10-29 12:30 UTC`)로 completion_evidence를 남긴 뒤, Owner 결정에 따라 Console Complete Preview(DOING → DONE, 증거 표시)를 확인하고 `Confirm Complete`로 DONE이 됐다(updated_at `2026-10-29 14:46 UTC`). Console은 끈 상태다. push는 하지 않았다.
